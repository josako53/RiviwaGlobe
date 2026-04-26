"""
api/v1/voice.py — Voice input for AI conversations + Twilio phone call channel.

TWO SURFACES:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.  WEB / MOBILE VOICE INPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    POST /ai/conversations/{conversation_id}/voice-message
        · Accept: multipart/form-data  { audio: <file> }
        · Formats: WebM (Opus), OGG, WAV, MP3, M4A, AAC  (≤ 25 MB)
        · Returns: standard chat reply  +  transcript  +  detected_language

    Industry pattern:
      Browser  → MediaRecorder API → Blob → FormData → fetch()
      Flutter  → record package    → File → MultipartRequest
      iOS      → AVAudioRecorder   → File → URLSession multipart
      Android  → MediaRecorder     → File → OkHttp multipart

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2.  PHONE CALL  (Twilio Programmable Voice — IVR loop)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    POST /ai/voice/call/inbound      — Twilio: caller dials in
    POST /ai/voice/call/gather       — Twilio: recording ready
    POST /ai/voice/call/status       — Twilio: call status changes

    Twilio console config:
      Voice webhook URL  →  https://riviwa.com/api/v1/ai/voice/call/inbound
      Status callback    →  https://riviwa.com/api/v1/ai/voice/call/status
      HTTP method        →  POST

    Call flow:
      RING
        → inbound: create PHONE_CALL conversation, say greeting, start <Record>
      SPEAK (up to 30s)
        → gather: download MP3, transcribe (Whisper), AI reply, TTS back, <Record> again
      REPEAT until AI confidence ≥ 0.82 → feedback auto-submitted
        → "Asante. Nambari ya ufuatiliaji: GRV-2026-0001. Kwa heri." → <Hangup>
      HANGUP
        → status: mark conversation closed

    TTS voices used (Google via Twilio):
      Swahili  → Google.sw-TZ-Standard-A
      English  → Google.en-US-Neural2-F

    Security:
      All Twilio webhooks validate X-Twilio-Signature using HMAC-SHA1.
      Set TWILIO_AUTH_TOKEN in .env to enable. Omit → skip (dev only).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import uuid
from typing import Optional

import httpx
import structlog
from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.dependencies import DbDep
from services.voice_ai_service import VoiceAIService
from services.conversation_service import ConversationService

log    = structlog.get_logger(__name__)
router = APIRouter(prefix="/ai", tags=["AI Voice"])

# ── Allowed audio MIME types ──────────────────────────────────────────────────
_ALLOWED_TYPES = {
    "audio/webm", "audio/ogg", "audio/ogg; codecs=opus",
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/wave",
    "audio/x-wav", "audio/mp4", "audio/m4a", "audio/aac",
    "audio/amr",  "audio/opus", "video/webm",
}
_MAX_BYTES = 25 * 1024 * 1024  # 25 MB


# ═══════════════════════════════════════════════════════════════════════════════
# 1. WEB / MOBILE VOICE MESSAGE
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/conversations/{conversation_id}/voice-message",
    summary="Send a voice message in an AI conversation",
    description="""
Upload an audio recording and receive the AI reply in one call.

**Accepted formats**: WebM (Opus), OGG, WAV, MP3, M4A, AAC — up to 25 MB.

**What happens inside**:
1. Whisper transcribes the audio and auto-detects the language
2. `translation_service` confirms the language from the transcript text
3. If the language is not Swahili or English, the transcript is translated to English
4. The English/Swahili text is fed into the existing AI conversation pipeline
5. If the AI reply is in English but the caller spoke another language, the reply
   is translated back before being returned

**Response extras** (beyond the standard chat response):
- `transcript` — raw Whisper transcript
- `detected_language` — BCP-47 code, e.g. `"sw"`, `"en"`, `"fr"`
- `stt_confidence` — Whisper confidence proxy (0–1); below 0.40 may be noisy
- `translated` — `true` if the input was auto-translated before AI processing

**Browser example** (MediaRecorder API):
```js
const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
const chunks = [];
recorder.ondataavailable = e => chunks.push(e.data);
recorder.onstop = async () => {
  const blob = new Blob(chunks, { type: 'audio/webm' });
  const fd = new FormData();
  fd.append('audio', blob, 'recording.webm');
  const res = await fetch(`/api/v1/ai/conversations/${convId}/voice-message`, {
    method: 'POST', body: fd
  });
  const data = await res.json();
  console.log(data.reply, data.transcript, data.detected_language);
};
recorder.start();
// ... stop after user finishes speaking
recorder.stop();
```

**Flutter example**:
```dart
final request = http.MultipartRequest(
  'POST',
  Uri.parse('/api/v1/ai/conversations/$convId/voice-message'),
);
request.files.add(await http.MultipartFile.fromPath('audio', filePath));
final response = await request.send();
```
""",
)
async def voice_message(
    conversation_id: uuid.UUID,
    db:    DbDep,
    audio: UploadFile = File(
        ...,
        description="Audio file — WebM/OGG/WAV/MP3/M4A/AAC, max 25 MB",
    ),
) -> dict:
    # Normalise MIME type
    raw_ct      = (audio.content_type or "audio/webm").lower()
    content_type = raw_ct.split(";")[0].strip()
    if content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "error":     "UNSUPPORTED_AUDIO_FORMAT",
                "received":  audio.content_type,
                "supported": sorted(_ALLOWED_TYPES),
                "hint":      "Most browsers produce audio/webm. "
                             "iOS produces audio/mp4. Android produces audio/mpeg or audio/ogg.",
            },
        )

    audio_bytes = await audio.read()
    if len(audio_bytes) > _MAX_BYTES:
        raise HTTPException(413, {"error": "AUDIO_TOO_LARGE", "max_mb": 25})
    if len(audio_bytes) < 512:
        raise HTTPException(400, {"error": "AUDIO_TOO_SHORT",
                                  "message": "Recording is too short. Please speak for at least 1 second."})

    result = await VoiceAIService().process_voice_turn(
        audio_bytes=audio_bytes,
        content_type=content_type,
        conversation_id=conversation_id,
        db=db,
    )

    if result.get("error"):
        raise HTTPException(422, result)

    log.info(
        "voice_message.processed",
        conv_id=str(conversation_id),
        lang=result.get("detected_language"),
        conf=result.get("stt_confidence"),
        translated=result.get("translated"),
    )
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 2. TWILIO PHONE CALL CHANNEL
# ═══════════════════════════════════════════════════════════════════════════════

# ── Twilio HMAC-SHA1 signature validation ─────────────────────────────────────

def _twilio_sig_valid(request: Request, form: dict) -> bool:
    """
    Validate Twilio's X-Twilio-Signature header.
    Algorithm: HMAC-SHA1 over (url + sorted_params), base64-encoded.
    https://www.twilio.com/docs/usage/webhooks/webhooks-security#validating-signatures-from-twilio
    """
    token = settings.TWILIO_AUTH_TOKEN
    if not token:
        return True  # skip in dev when token not set
    url     = str(request.url)
    params  = "".join(f"{k}{v}" for k, v in sorted(form.items()))
    digest  = base64.b64encode(
        hmac.new(token.encode(), (url + params).encode(), hashlib.sha1).digest()
    ).decode()
    provided = request.headers.get("X-Twilio-Signature", "")
    return hmac.compare_digest(digest, provided)


# ── TwiML builders ────────────────────────────────────────────────────────────

def _say(text: str, lang: str, voice: str) -> str:
    escaped = (text
               .replace("&", "&amp;")
               .replace("<", "&lt;")
               .replace(">", "&gt;"))
    return f'<Say language="{lang}" voice="{voice}">{escaped}</Say>'


def _record(action: str) -> str:
    return (
        f'<Record maxLength="30" trim="trim-silence" timeout="5" '
        f'playBeep="true" action="{action}" />'
    )


def _twiml(*elements: str) -> Response:
    xml = '<?xml version="1.0" encoding="UTF-8"?><Response>' + "".join(elements) + "</Response>"
    return Response(content=xml, media_type="text/xml")


def _twiml_voice(lang_code: str) -> tuple[str, str]:
    """Return (twiml_language, google_voice_name) for a BCP-47 language code."""
    mapping = {
        "sw": ("sw-TZ", "Google.sw-TZ-Standard-A"),
        "en": ("en-US", "Google.en-US-Neural2-F"),
        "fr": ("fr-FR", "Google.fr-FR-Neural2-A"),
        "ar": ("ar-XA", "Google.ar-XA-Standard-A"),
        "pt": ("pt-BR", "Google.pt-BR-Neural2-A"),
        "es": ("es-ES", "Google.es-ES-Neural2-A"),
        "ha": ("sw-TZ", "Google.sw-TZ-Standard-A"),   # Hausa → fallback Swahili voice
    }
    return mapping.get(lang_code, ("sw-TZ", "Google.sw-TZ-Standard-A"))


def _gather_url(call_sid: str, conv_id: str) -> str:
    base = (settings.AI_WEBHOOK_BASE_URL or "https://riviwa.com").rstrip("/")
    return f"{base}/api/v1/ai/voice/call/gather?call_sid={call_sid}&conv_id={conv_id}"


# ── Inbound call ──────────────────────────────────────────────────────────────

@router.post(
    "/voice/call/inbound",
    include_in_schema=False,
    response_class=Response,
)
async def call_inbound(request: Request, db: DbDep) -> Response:
    """
    Twilio dials this when a caller rings the Riviwa GRM number.
    Creates a PHONE_CALL conversation and returns TwiML to greet + start recording.
    """
    form     = dict(await request.form())
    call_sid = form.get("CallSid", str(uuid.uuid4()))

    if not _twilio_sig_valid(request, form):
        log.warning("twilio.inbound.invalid_signature", call_sid=call_sid)
        tl, tv = _twiml_voice("sw")
        return _twiml(_say("Samahani, kuna tatizo la usalama.", tl, tv), "<Hangup/>")

    # Infer preferred language from caller's country
    caller_country = form.get("CallerCountry", "TZ")
    lang           = "sw" if caller_country in ("TZ", "KE", "UG", "RW", "BI") else "en"
    tl, tv         = _twiml_voice(lang)

    conv_svc       = ConversationService(db=db)
    conv, greeting = await conv_svc.start_conversation(
        channel="phone_call",
        language=lang,
        org_id=None,
    )
    conv_id = str(conv.id)

    log.info("twilio.call_inbound", call_sid=call_sid, conv_id=conv_id, lang=lang)

    no_audio_prompt = (
        "Samahani, sikusikia. Tafadhali zungumza baada ya mlio."
        if lang == "sw" else
        "Sorry, I didn't hear you. Please speak after the beep."
    )
    return _twiml(
        _say(greeting, tl, tv),
        _record(_gather_url(call_sid, conv_id)),
        _say(no_audio_prompt, tl, tv),
        f'<Redirect>{_gather_url(call_sid, conv_id)}&amp;retry=1</Redirect>',
    )


# ── Recording ready (main AI loop) ───────────────────────────────────────────

@router.post(
    "/voice/call/gather",
    include_in_schema=False,
    response_class=Response,
)
async def call_gather(
    request:  Request,
    db:       DbDep,
    call_sid: str = Query(default=""),
    conv_id:  str = Query(default=""),
    retry:    int = Query(default=0),
) -> Response:
    """
    Twilio posts here when a <Record> completes.
    Downloads the MP3 recording, transcribes it, feeds to AI, returns TwiML reply.
    """
    form          = dict(await request.form())
    recording_url = form.get("RecordingUrl", "")
    call_sid      = call_sid or form.get("CallSid", "")
    conv_id_str   = conv_id  or form.get("conv_id", "")

    # Resolve conversation UUID
    try:
        conv_uuid = uuid.UUID(conv_id_str)
    except ValueError:
        tl, tv = _twiml_voice("sw")
        return _twiml(_say("Kuna hitilafu. Tafadhali piga tena.", tl, tv), "<Hangup/>")

    # No recording received — silence / too short
    if not recording_url:
        if retry >= 2:
            tl, tv = _twiml_voice("sw")
            return _twiml(
                _say("Samahani, haikuwezekana kupata sauti yako. Tafadhali jaribu tena baadaye.", tl, tv),
                "<Hangup/>",
            )
        tl, tv = _twiml_voice("sw")
        return _twiml(
            _say("Samahani, sikusikia. Tafadhali zungumza baada ya mlio.", tl, tv),
            _record(_gather_url(call_sid, conv_id_str)),
        )

    # Download recording (Twilio delivers as MP3)
    svc         = VoiceAIService()
    audio_bytes = await svc.download_twilio_recording(recording_url)
    if not audio_bytes:
        tl, tv = _twiml_voice("sw")
        return _twiml(
            _say("Samahani, sikuweza kupata sauti yako. Tafadhali zungumza tena.", tl, tv),
            _record(_gather_url(call_sid, conv_id_str)),
        )

    # Transcribe + AI
    result = await svc.process_voice_turn(
        audio_bytes=audio_bytes,
        content_type="audio/mpeg",
        conversation_id=conv_uuid,
        db=db,
    )

    if result.get("error"):
        tl, tv = _twiml_voice("sw")
        return _twiml(
            _say("Samahani, kuna tatizo. Tafadhali zungumza tena.", tl, tv),
            _record(_gather_url(call_sid, conv_id_str)),
        )

    lang      = result.get("detected_language", "sw")
    reply     = result.get("reply", "")
    submitted = result.get("submitted", False)
    tl, tv    = _twiml_voice(lang)

    log.info("twilio.gather.processed",
             call_sid=call_sid, conv_id=conv_id_str,
             lang=lang, submitted=submitted,
             transcript=result.get("transcript", "")[:80])

    if submitted:
        refs     = result.get("submitted_feedback", [{}])
        ref_num  = refs[0].get("unique_ref", "") if refs else ""
        farewell = (
            f"Asante sana. Tatizo lako limewasilishwa. Nambari yako ya ufuatiliaji ni {ref_num}. Kwa heri."
            if lang == "sw" else
            f"Thank you. Your feedback has been submitted. Your reference number is {ref_num}. Goodbye."
        )
        return _twiml(_say(farewell, tl, tv), "<Hangup/>")

    # Continue conversation loop
    no_audio_prompt = (
        "Samahani, sikusikia. Tafadhali zungumza baada ya mlio."
        if lang == "sw" else
        "Sorry, I didn't hear you. Please speak after the beep."
    )
    return _twiml(
        _say(reply, tl, tv),
        _record(_gather_url(call_sid, conv_id_str)),
        _say(no_audio_prompt, tl, tv),
        f'<Redirect>{_gather_url(call_sid, conv_id_str)}&amp;retry=1</Redirect>',
    )


# ── Call status callback ──────────────────────────────────────────────────────

@router.post(
    "/voice/call/status",
    include_in_schema=False,
    response_class=Response,
)
async def call_status(
    request:  Request,
    db:       DbDep,
    conv_id:  str = Query(default=""),
) -> Response:
    """
    Twilio posts here on every call status change (initiated → ringing → in-progress → completed).
    On terminal states (completed, no-answer, busy, failed, canceled) we close the conversation.
    """
    form       = dict(await request.form())
    call_state = form.get("CallStatus", "")
    call_sid   = form.get("CallSid", "")
    conv_id_str = conv_id or form.get("conv_id", "")

    log.info("twilio.call_status", call_sid=call_sid, state=call_state, conv_id=conv_id_str)

    terminal = {"completed", "no-answer", "busy", "failed", "canceled"}
    if call_state in terminal and conv_id_str:
        try:
            from repositories.conversation_repo import ConversationRepository
            from models.conversation import ConversationStatus
            from datetime import datetime, timezone

            repo = ConversationRepository(db)
            conv = await repo.get(uuid.UUID(conv_id_str))
            if conv and conv.status.value not in ("submitted", "closed"):
                conv.status       = ConversationStatus.CLOSED
                conv.completed_at = datetime.now(timezone.utc)
                await repo.save(conv)
                await db.commit()
                log.info("twilio.conversation_closed", conv_id=conv_id_str, reason=call_state)
        except Exception as exc:
            log.error("twilio.status_close_error", error=str(exc))

    return Response(content="", status_code=204)
