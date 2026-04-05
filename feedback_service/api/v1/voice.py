# ───────────────────────────────────────────────────────────────────────────
# SERVICE  :  feedback_service     |  Port: 8090  |  DB: feedback_db (5434)
# FILE     :  api/v1/voice.py
# ───────────────────────────────────────────────────────────────────────────
"""
api/v1/voice.py — feedback_service
═══════════════════════════════════════════════════════════════════════════════
Voice-related endpoints for Riviwa feedback intake.

ENDPOINTS:
  POST /voice/feedback/{feedback_id}/voice-note
    Upload a voice note for an existing (draft) feedback record.
    Audio is stored, transcribed, and written to the feedback's voice_note_*
    fields. If the feedback has no description yet, the transcript is used.
    Usable by PAP (self-service) or officer (on behalf of PAP).

  POST /voice/sessions/{session_id}/audio-turn
    Submit a voice turn in an active ChannelSession (MOBILE_APP / WEB_PORTAL
    mic mode, or officer typing for PHONE_CALL). Audio is stored and transcribed.
    The transcript is added to the session as a user turn and fed into the LLM
    pipeline exactly as if the PAP had typed it.

  POST /voice/sessions/{session_id}/tts
    Request TTS synthesis of a text reply for playback to the PAP.
    Used by the PHONE_CALL IVR integration and MOBILE_APP voice reply mode.

  POST /webhooks/whatsapp-voice  (registered in webhooks.py — documented here)
    WhatsApp webhook handler for voice note messages (audio/ogg from Meta).
    Transcribes and routes through the normal ChannelSession pipeline.
    This endpoint is in webhooks.py but calls voice_service internally.
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlmodel import select

from core.dependencies import DbDep, KafkaDep, CurrentUserDep
from models.feedback import ChannelSession, Feedback, FeedbackChannel, SessionStatus
from services.voice_service import VoiceService, AUDIO_MIME_TO_EXT

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/voice", tags=["Voice"])

ALLOWED_MIME_TYPES = set(AUDIO_MIME_TO_EXT.keys())
MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _validate_audio(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported audio format: {file.content_type}. "
                f"Accepted: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
            ),
        )


async def _get_feedback_or_404(feedback_id: uuid.UUID, db) -> Feedback:
    result = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
    fb = result.scalar_one_or_none()
    if not fb:
        raise HTTPException(status_code=404, detail=f"Feedback {feedback_id} not found.")
    return fb


async def _get_session_or_404(session_id: uuid.UUID, db) -> ChannelSession:
    result = await db.execute(
        select(ChannelSession).where(ChannelSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail=f"ChannelSession {session_id} not found.")
    return session


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/feedback/{feedback_id}/voice-note",
    status_code=status.HTTP_200_OK,
    summary="Attach a voice note to a feedback record",
    description="""
Upload an audio recording as the source-of-truth voice note for a feedback item.

**When to use:**
- PAP taps the mic button in the Riviwa mobile app or web portal and records their grievance
- GHC officer records a walk-in PAP conversation during in-person intake (IN_PERSON channel)
- PAP calls and the officer records the call on their device before transcribing

**What happens:**
1. Audio is stored permanently in object storage (legal source of truth)
2. STT transcription is performed (Whisper → Google STT fallback)
3. `voice_note_url`, `voice_note_transcription`, `voice_note_language`,
   `voice_note_duration_seconds`, `voice_note_transcription_confidence`,
   and `voice_note_transcription_service` are set on the feedback record
4. If `feedback.description` is empty, the transcript populates it automatically
5. If transcription confidence < 0.70, the record is flagged for manual review

**Audio formats accepted:** OGG, WebM, MP3, WAV, AAC, AMR (max 25MB)
""",
)
async def attach_voice_note(
    feedback_id: uuid.UUID,
    db:          DbDep,
    kafka:       KafkaDep,
    token:       CurrentUserDep,
    audio:       UploadFile       = File(..., description="Audio file (OGG, WebM, MP3, WAV, AAC, AMR)"),
    language:    Optional[str]    = Form(default="sw", description="Language hint: 'sw' (Swahili) or 'en' (English)"),
    use_as_description: bool      = Form(default=True, description="If True and description is empty, use transcript as description"),
) -> dict:
    _validate_audio(audio)
    audio_bytes = await audio.read()
    if len(audio_bytes) > MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Audio file exceeds 25MB limit.")

    fb = await _get_feedback_or_404(feedback_id, db)

    svc    = VoiceService()
    result = await svc.transcribe_audio(
        audio_bytes=audio_bytes,
        mime_type=audio.content_type,
        context="feedback",
        object_id=feedback_id,
        language_hint=language or "sw",
    )

    # Persist to Feedback record
    fb.voice_note_url                      = result.audio_url
    fb.voice_note_transcription            = result.text
    fb.voice_note_duration_seconds         = result.duration_seconds
    fb.voice_note_language                 = result.language
    fb.voice_note_transcription_confidence = result.confidence
    fb.voice_note_transcription_service    = result.service

    if use_as_description and not fb.description and result.text:
        fb.description = result.text
        log.info(
            "voice.feedback.description_from_transcript",
            feedback_id=str(feedback_id),
        )

    db.add(fb)
    await db.commit()

    log.info(
        "voice.feedback.voice_note_attached",
        feedback_id=str(feedback_id),
        service=result.service,
        confidence=result.confidence,
        duration=result.duration_seconds,
        flagged=result.flagged_for_review,
        recorded_by=str(token.sub),
    )

    return {
        "feedback_id":      str(feedback_id),
        "voice_note_url":   result.audio_url,
        "transcription":    result.text,
        "language":         result.language,
        "confidence":       result.confidence,
        "duration_seconds": result.duration_seconds,
        "service":          result.service,
        "flagged_for_review": result.flagged_for_review,
        "description_updated": (use_as_description and not bool(fb.description) and bool(result.text)),
    }


@router.post(
    "/sessions/{session_id}/audio-turn",
    status_code=status.HTTP_200_OK,
    summary="Submit a voice turn in an active conversation session",
    description="""
Send a voice turn (audio recording) for an active ChannelSession.

**Used for:**
- PAP holds mic button in the Riviwa app or web portal during a live conversation
- Officer records what the PAP is saying during an in-person or phone intake session
- Processing a standalone WhatsApp voice note that continues an existing session

**What happens:**
1. Audio is stored permanently (object storage, path: sessions/{session_id}/turn_N.ext)
2. STT transcription is performed
3. Turn is appended to `session.turns` JSONB with role="user", audio_url, is_voice=True
4. The LLM is called with the full conversation history (including the new transcript)
5. LLM response is appended as role="assistant" — if TTS is enabled, audio_response_url is returned
6. If the LLM determines enough information has been collected, the Feedback record is auto-submitted

Returns the LLM's text reply and optionally a TTS audio URL for playback.
""",
)
async def submit_audio_turn(
    session_id: uuid.UUID,
    db:         DbDep,
    kafka:      KafkaDep,
    audio:      UploadFile    = File(..., description="Audio recording of the PAP's turn"),
    language:   Optional[str] = Form(default=None, description="Override language detection. Default: session.language"),
    tts_reply:  bool          = Form(default=False, description="If True, synthesise TTS audio for the LLM reply"),
) -> dict:
    _validate_audio(audio)
    audio_bytes = await audio.read()
    if len(audio_bytes) > MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Audio file exceeds 25MB limit.")

    session = await _get_session_or_404(session_id, db)

    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session {session_id} is not ACTIVE (status={session.status.value}). Cannot add turns.",
        )

    lang_hint = language or session.language or "sw"
    svc       = VoiceService()
    turn_index = session.turn_count  # 0-based index of this new turn

    # 1. Store + transcribe the audio
    result = await svc.transcribe_audio(
        audio_bytes=audio_bytes,
        mime_type=audio.content_type,
        context="session_turn",
        object_id=session_id,
        language_hint=lang_hint,
        turn_index=turn_index,
    )

    # 2. Update session language if we detected something different
    if result.language and result.language != session.language:
        session.language = result.language

    # 3. Append user voice turn
    session.add_turn(
        role="user",
        content=result.text,
        audio_url=result.audio_url,
        is_voice=True,
        transcription_confidence=result.confidence,
    )
    session.is_voice_session = True

    # 4. Call LLM with updated conversation history
    # The LLM pipeline lives in channels.py / channel_service.py.
    # We import it here to continue the conversation.
    try:
        from services.channel_service import ChannelService  # type: ignore
        channel_svc = ChannelService(db=db, producer=kafka)
        lm_reply    = await channel_svc.process_turn(session, result.text)
    except ImportError:
        # Graceful degradation: return transcript without LLM reply
        # if channel_service is not yet wired
        lm_reply = None
        log.warning(
            "voice.audio_turn.channel_service_unavailable",
            session_id=str(session_id),
        )

    # 5. Optionally synthesise TTS reply
    tts_audio_url: Optional[str] = None
    if tts_reply and lm_reply:
        tts_index = session.turn_count - 1  # index of the assistant turn just added
        tts_result = await svc.synthesise_speech(
            text=lm_reply,
            language=session.language or "sw",
            session_id=session_id,
            turn_index=tts_index,
        )
        tts_audio_url = tts_result.audio_url

    db.add(session)
    await db.commit()

    log.info(
        "voice.session.audio_turn_processed",
        session_id=str(session_id),
        turn_index=turn_index,
        confidence=result.confidence,
        flagged=result.flagged_for_review,
        has_lm_reply=bool(lm_reply),
        tts_generated=bool(tts_audio_url),
    )

    return {
        "session_id":       str(session_id),
        "turn_index":       turn_index,
        "transcription":    result.text,
        "language":         result.language,
        "confidence":       result.confidence,
        "audio_url":        result.audio_url,
        "flagged_for_review": result.flagged_for_review,
        "lm_reply":         lm_reply,
        "tts_audio_url":    tts_audio_url,
        "session_status":   session.status.value,
        "feedback_id":      str(session.feedback_id) if session.feedback_id else None,
    }


@router.post(
    "/sessions/{session_id}/tts",
    status_code=status.HTTP_200_OK,
    summary="Synthesise a TTS audio reply for a session turn",
    description="""
Generate Text-to-Speech audio for a message to be played back to the PAP.

**Used for:**
- PHONE_CALL: playing the LLM's text reply back through the IVR/telephony gateway
- MOBILE_APP / WEB_PORTAL mic mode: playing the LLM's reply as audio in the app

Returns the audio URL and duration. The caller is responsible for streaming
the audio to the PAP via their respective gateway.
""",
)
async def synthesise_tts(
    session_id: uuid.UUID,
    db:         DbDep,
    kafka:      KafkaDep,
    text:       str           = Form(..., description="Text to synthesise"),
    language:   Optional[str] = Form(default=None, description="Language: 'sw' or 'en'. Default: session language."),
    voice_id:   Optional[str] = Form(default=None, description="Optional provider-specific voice ID."),
) -> dict:
    session = await _get_session_or_404(session_id, db)
    lang    = language or session.language or "sw"
    svc     = VoiceService()

    result = await svc.synthesise_speech(
        text=text,
        language=lang,
        session_id=session_id,
        turn_index=session.turn_count,
        voice_id=voice_id,
    )
    log.info(
        "voice.tts.generated",
        session_id=str(session_id),
        language=lang,
        duration=result.duration_seconds,
        service=result.service,
    )
    return {
        "session_id":       str(session_id),
        "audio_url":        result.audio_url,
        "duration_seconds": result.duration_seconds,
        "service":          result.service,
        "language":         lang,
    }
