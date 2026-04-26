# AI Insights Voice Input — Implementation Guide
## ReactJS & Flutter

> Endpoint: `POST /api/v1/analytics/ai/ask-voice`  
> Pattern: mic button alongside the existing text input — one unified UI, two input modes.  
> Both paths return the same `{ answer, transcript, context_used, model }` shape.

---

## Table of Contents

1. [How It Works](#how-it-works)
2. [ReactJS Implementation](#reactjs-implementation)
   - [Hook: useVoiceRecorder](#hook-usevoicerecorder)
   - [Hook: useAskAI](#hook-usaskai)
   - [Component: AskAIInput](#component-askaiinput)
   - [Component: AIAnswerPanel](#component-aianswerpanel)
   - [Full Page Example](#full-page-example)
   - [Styling](#styling)
3. [Flutter Implementation](#flutter-implementation)
   - [Dependencies](#dependencies)
   - [Service: AskAIService](#service-askaiservice)
   - [Provider/State: AskAINotifier](#providerstate-askainotifier)
   - [Widget: AskAIBar](#widget-askaibar)
   - [Widget: AIAnswerCard](#widget-aianswercards)
   - [Full Screen Example](#full-screen-example)
4. [Error Handling Reference](#error-handling-reference)
5. [Supported Audio Formats](#supported-audio-formats)

---

## How It Works

```
[Text input field ─────────────────────] [🎤] [➤ Send]
         │                                │
         │ user types & presses Send       │ user holds mic, speaks, releases
         ▼                                ▼
POST /analytics/ai/ask              POST /analytics/ai/ask-voice
{ question, scope, project_id }     multipart: audio file + scope + project_id
         │                                │
         └──────────────┬─────────────────┘
                        ▼
             { answer, transcript?, model }
                        │
         ┌──────────────┴──────────────┐
         │ transcript shown in input   │  ← user can edit and re-ask
         │ answer shown below          │
         └─────────────────────────────┘
```

**Key decisions:**
- `transcript` is written back into the text field after voice — user sees what Whisper heard and can correct it
- Hold-to-record (not toggle) prevents accidental long recordings
- Both paths share the same answer display component
- `scope`, `project_id`, `org_id`, `context_type` are props — the same component works for project, org, and platform views

---

## ReactJS Implementation

### Hook: useVoiceRecorder

```ts
// hooks/useVoiceRecorder.ts
import { useRef, useState, useCallback } from "react";

export type RecorderState = "idle" | "recording" | "processing";

export interface UseVoiceRecorderReturn {
  state:          RecorderState;
  startRecording: () => Promise<void>;
  stopRecording:  () => Promise<Blob | null>;
  error:          string | null;
}

export function useVoiceRecorder(): UseVoiceRecorderReturn {
  const [state, setState] = useState<RecorderState>("idle");
  const [error, setError] = useState<string | null>(null);
  const recorderRef       = useRef<MediaRecorder | null>(null);
  const chunksRef         = useRef<Blob[]>([]);
  const streamRef         = useRef<MediaStream | null>(null);

  const startRecording = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Prefer webm/opus; fall back to whatever the browser supports
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/ogg;codecs=opus")
        ? "audio/ogg;codecs=opus"
        : "audio/webm";

      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorderRef.current = recorder;
      recorder.start(100); // collect chunks every 100ms
      setState("recording");
    } catch (err: any) {
      setError(
        err.name === "NotAllowedError"
          ? "Microphone permission denied. Please allow mic access."
          : "Could not start recording. Check your microphone."
      );
    }
  }, []);

  const stopRecording = useCallback((): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const recorder = recorderRef.current;
      if (!recorder || recorder.state === "inactive") {
        resolve(null);
        return;
      }
      setState("processing");
      recorder.onstop = () => {
        const mimeType = recorder.mimeType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type: mimeType });
        // Stop all tracks to release the mic indicator
        streamRef.current?.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        recorderRef.current = null;
        setState("idle");
        resolve(blob.size >= 512 ? blob : null);
      };
      recorder.stop();
    });
  }, []);

  return { state, startRecording, stopRecording, error };
}
```

---

### Hook: useAskAI

```ts
// hooks/useAskAI.ts
import { useState, useCallback } from "react";

export interface AskAIOptions {
  scope:        "project" | "org" | "platform";
  contextType?: string;
  projectId?:   string;
  orgId?:       string;
  token:        string;
}

export interface AskAIResult {
  answer:     string;
  transcript: string | null;
  model:      string;
}

export interface UseAskAIReturn {
  result:    AskAIResult | null;
  loading:   boolean;
  error:     string | null;
  askText:   (question: string, opts: AskAIOptions) => Promise<void>;
  askVoice:  (audio: Blob, opts: AskAIOptions) => Promise<void>;
  clear:     () => void;
}

const BASE = "/api/v1";

export function useAskAI(): UseAskAIReturn {
  const [result,  setResult]  = useState<AskAIResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  const askText = useCallback(async (question: string, opts: AskAIOptions) => {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${BASE}/analytics/ai/ask`, {
        method:  "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization:  `Bearer ${opts.token}`,
        },
        body: JSON.stringify({
          question,
          scope:        opts.scope,
          context_type: opts.contextType ?? "general",
          project_id:   opts.projectId ?? null,
          org_id:       opts.orgId     ?? null,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `Request failed (${res.status})`);
      }
      const data = await res.json();
      setResult({ answer: data.answer, transcript: null, model: data.model });
    } catch (e: any) {
      setError(e.message ?? "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }, []);

  const askVoice = useCallback(async (audio: Blob, opts: AskAIOptions) => {
    setLoading(true);
    setError(null);
    try {
      const fd = new FormData();
      const ext = audio.type.includes("ogg") ? "ogg" : "webm";
      fd.append("audio",        audio, `question.${ext}`);
      fd.append("scope",        opts.scope);
      fd.append("context_type", opts.contextType ?? "general");
      fd.append("language",     "sw");
      if (opts.projectId) fd.append("project_id", opts.projectId);
      if (opts.orgId)     fd.append("org_id",     opts.orgId);

      const res = await fetch(`${BASE}/analytics/ai/ask-voice`, {
        method:  "POST",
        headers: { Authorization: `Bearer ${opts.token}` },
        body:    fd,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const msg = err.detail?.error ?? err.detail ?? `Request failed (${res.status})`;
        throw new Error(
          res.status === 415 ? "Unsupported audio format." :
          res.status === 400 ? "Recording too short — please speak for at least 1 second." :
          res.status === 503 ? "Voice transcription is not available right now." :
          msg
        );
      }
      const data = await res.json();
      setResult({ answer: data.answer, transcript: data.transcript, model: data.model });
    } catch (e: any) {
      setError(e.message ?? "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, loading, error, askText, askVoice, clear };
}
```

---

### Component: AskAIInput

```tsx
// components/AskAIInput.tsx
import React, { useEffect, useRef, useState } from "react";
import { useVoiceRecorder } from "../hooks/useVoiceRecorder";
import type { AskAIOptions } from "../hooks/useAskAI";

interface Props {
  opts:          Omit<AskAIOptions, "token"> & { token: string };
  onAskText:     (question: string) => void;
  onAskVoice:    (audio: Blob)      => void;
  transcript:    string | null;   // written back after voice
  loading:       boolean;
}

export const AskAIInput: React.FC<Props> = ({
  opts, onAskText, onAskVoice, transcript, loading,
}) => {
  const [text, setText]           = useState("");
  const { state, startRecording, stopRecording, error: micError } = useVoiceRecorder();
  const inputRef                  = useRef<HTMLInputElement>(null);

  // Write transcript back into the text field
  useEffect(() => {
    if (transcript) {
      setText(transcript);
      inputRef.current?.focus();
    }
  }, [transcript]);

  const handleSend = () => {
    if (text.trim() && !loading) {
      onAskText(text.trim());
    }
  };

  const handleMicDown = async (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    await startRecording();
  };

  const handleMicUp = async (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    const blob = await stopRecording();
    if (blob) onAskVoice(blob);
  };

  const isRecording   = state === "recording";
  const isProcessing  = state === "processing" || loading;

  return (
    <div className="ask-ai-input-wrapper">
      <div className={`ask-ai-input-row ${isRecording ? "recording" : ""}`}>
        <input
          ref={inputRef}
          className="ask-ai-text-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask about your analytics... or hold 🎤 to speak"
          disabled={isRecording || isProcessing}
        />

        {/* Mic button — hold to record */}
        <button
          className={`mic-btn ${isRecording ? "mic-btn--active" : ""}`}
          onMouseDown={handleMicDown}
          onMouseUp={handleMicUp}
          onTouchStart={handleMicDown}
          onTouchEnd={handleMicUp}
          onMouseLeave={isRecording ? handleMicUp : undefined}
          disabled={isProcessing}
          title="Hold to speak"
          aria-label={isRecording ? "Recording — release to send" : "Hold to ask by voice"}
        >
          {isRecording ? "🔴" : "🎤"}
        </button>

        {/* Send button */}
        <button
          className="send-btn"
          onClick={handleSend}
          disabled={!text.trim() || isRecording || isProcessing}
        >
          {isProcessing ? "..." : "➤"}
        </button>
      </div>

      {isRecording && (
        <p className="recording-hint">🎤 Recording — release to send</p>
      )}
      {transcript && (
        <p className="transcript-hint">
          <span className="transcript-label">Heard:</span> "{transcript}"
        </p>
      )}
      {micError && <p className="input-error">{micError}</p>}
    </div>
  );
};
```

---

### Component: AIAnswerPanel

```tsx
// components/AIAnswerPanel.tsx
import React from "react";

interface Props {
  answer:  string | null;
  loading: boolean;
  error:   string | null;
  model?:  string;
  onClear: () => void;
}

export const AIAnswerPanel: React.FC<Props> = ({
  answer, loading, error, model, onClear,
}) => {
  if (loading) {
    return (
      <div className="ai-panel ai-panel--loading">
        <span className="ai-spinner" />
        <p>Thinking...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="ai-panel ai-panel--error">
        <p>⚠ {error}</p>
        <button onClick={onClear} className="clear-btn">Dismiss</button>
      </div>
    );
  }

  if (!answer) return null;

  return (
    <div className="ai-panel ai-panel--answer">
      <div className="ai-panel__header">
        <span className="ai-label">AI Insights</span>
        {model && <span className="ai-model">{model}</span>}
        <button onClick={onClear} className="clear-btn" aria-label="Clear answer">✕</button>
      </div>
      <p className="ai-answer-text">{answer}</p>
    </div>
  );
};
```

---

### Full Page Example

```tsx
// pages/AnalyticsDashboard.tsx
import React from "react";
import { AskAIInput }   from "../components/AskAIInput";
import { AIAnswerPanel } from "../components/AIAnswerPanel";
import { useAskAI }     from "../hooks/useAskAI";
import { useAuth }      from "../hooks/useAuth";   // your own auth hook

interface Props {
  projectId: string;
}

export const AnalyticsDashboard: React.FC<Props> = ({ projectId }) => {
  const { token }                              = useAuth();
  const { result, loading, error, askText, askVoice, clear } = useAskAI();

  const opts = {
    scope:       "project" as const,
    contextType: "general",
    projectId,
    token,
  };

  return (
    <div className="analytics-page">
      <h1>Analytics</h1>

      {/* ... your charts and tables ... */}

      <section className="ai-section">
        <h2>Ask AI</h2>
        <AskAIInput
          opts={opts}
          onAskText={(q) => askText(q, opts)}
          onAskVoice={(blob) => askVoice(blob, opts)}
          transcript={result?.transcript ?? null}
          loading={loading}
        />
        <AIAnswerPanel
          answer={result?.answer ?? null}
          loading={loading}
          error={error}
          model={result?.model}
          onClear={clear}
        />
      </section>
    </div>
  );
};
```

---

### Styling

```css
/* styles/ask-ai.css */

.ask-ai-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 16px 0;
}

.ask-ai-input-row {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1.5px solid #d1d5db;
  border-radius: 10px;
  padding: 6px 10px;
  background: #fff;
  transition: border-color 0.2s;
}

.ask-ai-input-row.recording {
  border-color: #ef4444;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.15);
  animation: pulse-border 1s infinite;
}

@keyframes pulse-border {
  0%, 100% { border-color: #ef4444; }
  50%       { border-color: #fca5a5; }
}

.ask-ai-text-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 14px;
  background: transparent;
  color: #111827;
}

.mic-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 18px;
  padding: 4px 6px;
  border-radius: 6px;
  transition: background 0.15s;
  user-select: none;
  -webkit-user-select: none;
}

.mic-btn:hover   { background: #f3f4f6; }
.mic-btn--active { background: #fee2e2; }
.mic-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.send-btn {
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s;
}

.send-btn:hover    { background: #1d4ed8; }
.send-btn:disabled { background: #93c5fd; cursor: not-allowed; }

.recording-hint {
  font-size: 12px;
  color: #ef4444;
  margin: 0;
  animation: pulse-border 1s infinite;
}

.transcript-hint {
  font-size: 12px;
  color: #6b7280;
  margin: 0;
}

.transcript-label {
  font-weight: 600;
  color: #374151;
}

.input-error {
  font-size: 12px;
  color: #ef4444;
  margin: 0;
}

/* Answer panel */
.ai-panel {
  border-radius: 10px;
  padding: 14px 16px;
  margin-top: 8px;
}

.ai-panel--loading {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f9fafb;
  color: #6b7280;
  font-size: 14px;
}

.ai-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #d1d5db;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.ai-panel--error {
  background: #fef2f2;
  border: 1px solid #fca5a5;
  color: #b91c1c;
  font-size: 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ai-panel--answer {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
}

.ai-panel__header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.ai-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #2563eb;
}

.ai-model {
  font-size: 11px;
  color: #9ca3af;
  margin-left: auto;
}

.clear-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 13px;
  color: #9ca3af;
  padding: 0 4px;
}

.clear-btn:hover { color: #374151; }

.ai-answer-text {
  font-size: 14px;
  line-height: 1.6;
  color: #1e3a5f;
  margin: 0;
  white-space: pre-wrap;
}
```

---

## Flutter Implementation

### Dependencies

Add to `pubspec.yaml`:

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.2.0
  record: ^5.1.0          # audio recording
  path_provider: ^2.1.2   # temp file path
  provider: ^6.1.2        # state management (or use riverpod/bloc)
  permission_handler: ^11.3.0
```

Run: `flutter pub get`

**Android** — `android/app/src/main/AndroidManifest.xml`:
```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.INTERNET" />
```

**iOS** — `ios/Runner/Info.plist`:
```xml
<key>NSMicrophoneUsageDescription</key>
<string>Riviwa uses your microphone so you can ask analytics questions by voice.</string>
```

---

### Service: AskAIService

```dart
// lib/services/ask_ai_service.dart
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

const _base = 'https://riviwa.com/api/v1';

class AskAIResult {
  final String  answer;
  final String? transcript;
  final String  model;
  const AskAIResult({required this.answer, this.transcript, required this.model});
}

class AskAIService {
  final String token;
  AskAIService(this.token);

  Map<String, String> get _headers => {
    'Authorization': 'Bearer $token',
    'Content-Type':  'application/json',
  };

  /// Text-based ask
  Future<AskAIResult> askText({
    required String question,
    required String scope,
    String  contextType = 'general',
    String? projectId,
    String? orgId,
  }) async {
    final res = await http.post(
      Uri.parse('$_base/analytics/ai/ask'),
      headers: _headers,
      body: jsonEncode({
        'question':     question,
        'scope':        scope,
        'context_type': contextType,
        if (projectId != null) 'project_id': projectId,
        if (orgId     != null) 'org_id':     orgId,
      }),
    );
    _assertOk(res);
    final data = jsonDecode(res.body);
    return AskAIResult(
      answer:     data['answer'] as String,
      transcript: null,
      model:      data['model']  as String,
    );
  }

  /// Voice-based ask
  Future<AskAIResult> askVoice({
    required File   audioFile,
    required String scope,
    String  contextType = 'general',
    String? projectId,
    String? orgId,
    String  language    = 'sw',
  }) async {
    final req = http.MultipartRequest(
      'POST',
      Uri.parse('$_base/analytics/ai/ask-voice'),
    )
      ..headers['Authorization'] = 'Bearer $token'
      ..fields['scope']        = scope
      ..fields['context_type'] = contextType
      ..fields['language']     = language;

    if (projectId != null) req.fields['project_id'] = projectId;
    if (orgId     != null) req.fields['org_id']     = orgId;

    final ext = audioFile.path.endsWith('.m4a') ? 'm4a' : 'aac';
    req.files.add(await http.MultipartFile.fromPath(
      'audio',
      audioFile.path,
      // iOS records m4a; Android records aac — both accepted by the endpoint
    ));

    final streamed = await req.send();
    final res      = await http.Response.fromStream(streamed);
    _assertOk(res);

    final data = jsonDecode(res.body);
    return AskAIResult(
      answer:     data['answer']     as String,
      transcript: data['transcript'] as String?,
      model:      data['model']      as String,
    );
  }

  void _assertOk(http.Response res) {
    if (res.statusCode == 200) return;
    final body = jsonDecode(res.body);
    final detail = body['detail'];
    final msg = (detail is Map)
        ? (detail['error'] ?? detail.toString())
        : (detail?.toString() ?? 'Request failed');
    throw AskAIException(res.statusCode, msg);
  }
}

class AskAIException implements Exception {
  final int    statusCode;
  final String message;
  AskAIException(this.statusCode, this.message);

  String get userMessage {
    switch (statusCode) {
      case 415: return 'Unsupported audio format.';
      case 400: return 'Recording too short — please speak for at least 1 second.';
      case 413: return 'Recording too large (max 25 MB).';
      case 503: return 'Voice transcription is unavailable right now.';
      default:  return message;
    }
  }
}
```

---

### Provider/State: AskAINotifier

```dart
// lib/providers/ask_ai_provider.dart
import 'dart:io';
import 'package:flutter/foundation.dart';
import '../services/ask_ai_service.dart';

enum AskAIStatus { idle, loading, success, error }

class AskAIState {
  final AskAIStatus status;
  final String?     answer;
  final String?     transcript;
  final String?     model;
  final String?     error;

  const AskAIState({
    this.status     = AskAIStatus.idle,
    this.answer,
    this.transcript,
    this.model,
    this.error,
  });

  AskAIState copyWith({
    AskAIStatus? status,
    String?      answer,
    String?      transcript,
    String?      model,
    String?      error,
  }) => AskAIState(
    status:     status     ?? this.status,
    answer:     answer     ?? this.answer,
    transcript: transcript ?? this.transcript,
    model:      model      ?? this.model,
    error:      error      ?? this.error,
  );
}

class AskAINotifier extends ChangeNotifier {
  AskAINotifier(this._service);

  final AskAIService _service;
  AskAIState _state = const AskAIState();
  AskAIState get state => _state;

  Future<void> askText({
    required String question,
    required String scope,
    String?         projectId,
    String?         orgId,
    String          contextType = 'general',
  }) async {
    _set(_state.copyWith(status: AskAIStatus.loading, error: null));
    try {
      final result = await _service.askText(
        question:    question,
        scope:       scope,
        contextType: contextType,
        projectId:   projectId,
        orgId:       orgId,
      );
      _set(AskAIState(
        status:     AskAIStatus.success,
        answer:     result.answer,
        transcript: null,
        model:      result.model,
      ));
    } on AskAIException catch (e) {
      _set(AskAIState(status: AskAIStatus.error, error: e.userMessage));
    } catch (e) {
      _set(AskAIState(status: AskAIStatus.error, error: e.toString()));
    }
  }

  Future<void> askVoice({
    required File   audioFile,
    required String scope,
    String?         projectId,
    String?         orgId,
    String          contextType = 'general',
  }) async {
    _set(_state.copyWith(status: AskAIStatus.loading, error: null));
    try {
      final result = await _service.askVoice(
        audioFile:   audioFile,
        scope:       scope,
        contextType: contextType,
        projectId:   projectId,
        orgId:       orgId,
      );
      _set(AskAIState(
        status:     AskAIStatus.success,
        answer:     result.answer,
        transcript: result.transcript,
        model:      result.model,
      ));
    } on AskAIException catch (e) {
      _set(AskAIState(status: AskAIStatus.error, error: e.userMessage));
    } catch (e) {
      _set(AskAIState(status: AskAIStatus.error, error: e.toString()));
    }
  }

  void clear() => _set(const AskAIState());

  void _set(AskAIState s) {
    _state = s;
    notifyListeners();
  }
}
```

---

### Widget: AskAIBar

```dart
// lib/widgets/ask_ai_bar.dart
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:provider/provider.dart';
import 'package:record/record.dart';
import '../providers/ask_ai_provider.dart';

class AskAIBar extends StatefulWidget {
  final String  scope;
  final String? projectId;
  final String? orgId;
  final String  contextType;

  const AskAIBar({
    super.key,
    required this.scope,
    this.projectId,
    this.orgId,
    this.contextType = 'general',
  });

  @override
  State<AskAIBar> createState() => _AskAIBarState();
}

class _AskAIBarState extends State<AskAIBar> {
  final _controller = TextEditingController();
  final _recorder   = AudioRecorder();
  bool  _recording  = false;
  String? _tempPath;

  @override
  void dispose() {
    _controller.dispose();
    _recorder.dispose();
    super.dispose();
  }

  // ── Text submit ─────────────────────────────────────
  void _sendText(AskAINotifier notifier) {
    final q = _controller.text.trim();
    if (q.isEmpty) return;
    notifier.askText(
      question:    q,
      scope:       widget.scope,
      projectId:   widget.projectId,
      orgId:       widget.orgId,
      contextType: widget.contextType,
    );
  }

  // ── Voice: start ─────────────────────────────────────
  Future<void> _startRecording() async {
    final status = await Permission.microphone.request();
    if (!status.isGranted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Microphone permission denied.')),
      );
      return;
    }
    final dir  = await getTemporaryDirectory();
    _tempPath  = '${dir.path}/ask_ai_${DateTime.now().millisecondsSinceEpoch}.m4a';
    await _recorder.start(
      RecordConfig(encoder: AudioEncoder.aacLc, bitRate: 128000, sampleRate: 44100),
      path: _tempPath!,
    );
    setState(() => _recording = true);
  }

  // ── Voice: stop + send ───────────────────────────────
  Future<void> _stopAndSend(AskAINotifier notifier) async {
    await _recorder.stop();
    setState(() => _recording = false);
    if (_tempPath == null) return;

    final file = File(_tempPath!);
    if (!await file.exists()) return;
    if (await file.length() < 512) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Recording too short — please speak for at least 1 second.')),
      );
      return;
    }

    notifier.askVoice(
      audioFile:   file,
      scope:       widget.scope,
      projectId:   widget.projectId,
      orgId:       widget.orgId,
      contextType: widget.contextType,
    );
  }

  @override
  Widget build(BuildContext context) {
    final notifier = context.watch<AskAINotifier>();
    final loading  = notifier.state.status == AskAIStatus.loading;

    // Write transcript back into text field
    final transcript = notifier.state.transcript;
    if (transcript != null && _controller.text != transcript) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _controller.text = transcript;
        _controller.selection = TextSelection.fromPosition(
          TextPosition(offset: transcript.length),
        );
      });
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // ── Input row ──────────────────────────────────
        AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          decoration: BoxDecoration(
            color:        Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: _recording ? Colors.red : const Color(0xFFD1D5DB),
              width: _recording ? 2.0 : 1.5,
            ),
            boxShadow: _recording ? [
              BoxShadow(color: Colors.red.withOpacity(0.15), blurRadius: 8),
            ] : [],
          ),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          child: Row(
            children: [
              // Text field
              Expanded(
                child: TextField(
                  controller: _controller,
                  enabled:    !_recording && !loading,
                  decoration: const InputDecoration(
                    border:      InputBorder.none,
                    hintText:    'Ask about your analytics...',
                    hintStyle:   TextStyle(color: Color(0xFF9CA3AF)),
                    isDense:     true,
                    contentPadding: EdgeInsets.symmetric(vertical: 10),
                  ),
                  onSubmitted: (_) => _sendText(notifier),
                  textInputAction: TextInputAction.send,
                ),
              ),

              // Mic button — hold to record
              GestureDetector(
                onLongPressStart: (_) => _startRecording(),
                onLongPressEnd:   (_) => _stopAndSend(notifier),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 150),
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color:        _recording ? Colors.red.shade50 : Colors.transparent,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(
                    _recording ? Icons.mic : Icons.mic_none,
                    color: _recording ? Colors.red : const Color(0xFF6B7280),
                    size: 22,
                  ),
                ),
              ),

              const SizedBox(width: 4),

              // Send button
              GestureDetector(
                onTap: loading || _recording ? null : () => _sendText(notifier),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 150),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  decoration: BoxDecoration(
                    color: (loading || _recording || _controller.text.isEmpty)
                        ? const Color(0xFF93C5FD)
                        : const Color(0xFF2563EB),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: loading
                      ? const SizedBox(
                          width: 16, height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.send, color: Colors.white, size: 16),
                ),
              ),
            ],
          ),
        ),

        // ── Recording hint ─────────────────────────────
        if (_recording)
          Padding(
            padding: const EdgeInsets.only(top: 6, left: 4),
            child: Row(children: [
              const Icon(Icons.fiber_manual_record, color: Colors.red, size: 12),
              const SizedBox(width: 4),
              Text(
                'Recording — release to send',
                style: TextStyle(fontSize: 12, color: Colors.red.shade600),
              ),
            ]),
          ),

        // ── Transcript hint ────────────────────────────
        if (transcript != null && !_recording)
          Padding(
            padding: const EdgeInsets.only(top: 6, left: 4),
            child: RichText(text: TextSpan(
              style: const TextStyle(fontSize: 12, color: Color(0xFF6B7280)),
              children: [
                const TextSpan(
                  text: 'Heard: ',
                  style: TextStyle(fontWeight: FontWeight.w600, color: Color(0xFF374151)),
                ),
                TextSpan(text: '"$transcript"'),
              ],
            )),
          ),
      ],
    );
  }
}
```

---

### Widget: AIAnswerCard

```dart
// lib/widgets/ai_answer_card.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/ask_ai_provider.dart';

class AIAnswerCard extends StatelessWidget {
  const AIAnswerCard({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AskAINotifier>().state;

    if (state.status == AskAIStatus.idle) return const SizedBox.shrink();

    if (state.status == AskAIStatus.loading) {
      return const Padding(
        padding: EdgeInsets.only(top: 12),
        child: Row(children: [
          SizedBox(
            width: 16, height: 16,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
          SizedBox(width: 10),
          Text('Thinking...', style: TextStyle(color: Color(0xFF6B7280))),
        ]),
      );
    }

    if (state.status == AskAIStatus.error) {
      return Container(
        margin:  const EdgeInsets.only(top: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color:        const Color(0xFFFEF2F2),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: const Color(0xFFFCA5A5)),
        ),
        child: Row(
          children: [
            const Icon(Icons.warning_amber_rounded, color: Color(0xFFB91C1C), size: 18),
            const SizedBox(width: 8),
            Expanded(child: Text(
              state.error ?? 'Something went wrong.',
              style: const TextStyle(color: Color(0xFFB91C1C), fontSize: 13),
            )),
            GestureDetector(
              onTap: () => context.read<AskAINotifier>().clear(),
              child: const Icon(Icons.close, color: Color(0xFF9CA3AF), size: 18),
            ),
          ],
        ),
      );
    }

    // Success
    return Container(
      margin:  const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color:        const Color(0xFFEFF6FF),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFBFDBFE)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color:        const Color(0xFF2563EB),
                borderRadius: BorderRadius.circular(4),
              ),
              child: const Text(
                'AI INSIGHTS',
                style: TextStyle(
                  color:      Colors.white,
                  fontSize:   10,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.5,
                ),
              ),
            ),
            const Spacer(),
            if (state.model != null)
              Text(
                state.model!,
                style: const TextStyle(fontSize: 11, color: Color(0xFF9CA3AF)),
              ),
            const SizedBox(width: 8),
            GestureDetector(
              onTap: () => context.read<AskAINotifier>().clear(),
              child: const Icon(Icons.close, color: Color(0xFF9CA3AF), size: 18),
            ),
          ]),

          const SizedBox(height: 10),

          // Answer text
          Text(
            state.answer ?? '',
            style: const TextStyle(
              fontSize: 14,
              height:   1.6,
              color:    Color(0xFF1E3A5F),
            ),
          ),
        ],
      ),
    );
  }
}
```

---

### Full Screen Example

```dart
// lib/screens/analytics_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/ask_ai_provider.dart';
import '../services/ask_ai_service.dart';
import '../widgets/ask_ai_bar.dart';
import '../widgets/ai_answer_card.dart';

class AnalyticsScreen extends StatelessWidget {
  final String projectId;
  final String token;

  const AnalyticsScreen({
    super.key,
    required this.projectId,
    required this.token,
  });

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AskAINotifier(AskAIService(token)),
      child: Scaffold(
        appBar: AppBar(title: const Text('Analytics')),
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [

              // ... your charts, tables, metric cards ...

              const SizedBox(height: 24),
              const Text(
                'Ask AI',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 8),

              // Input bar (text + voice)
              AskAIBar(
                scope:       'project',
                projectId:   projectId,
                contextType: 'general',
              ),

              // Answer card
              const AIAnswerCard(),
            ],
          ),
        ),
      ),
    );
  }
}
```

---

## Error Handling Reference

| HTTP Code | Cause | User-facing message |
|-----------|-------|---------------------|
| `400` | Audio < 512 bytes | "Recording too short — speak for at least 1 second" |
| `413` | Audio > 25 MB | "Recording too large (max 25 MB)" |
| `415` | Wrong MIME type | "Unsupported audio format" |
| `422` | Whisper returned empty text | "Could not understand the recording — please try again" |
| `503` | No STT provider configured | "Voice input is not available right now" |
| `401` | Token expired | Redirect to login |

---

## Supported Audio Formats

| Format | MIME type | Browser | iOS | Android |
|--------|-----------|---------|-----|---------|
| WebM (Opus) | `audio/webm;codecs=opus` | ✅ Chrome/Firefox/Edge | ✗ | ✅ |
| OGG (Opus) | `audio/ogg;codecs=opus` | ✅ Firefox | ✗ | ✅ |
| M4A (AAC) | `audio/mp4` / `audio/m4a` | Partial | ✅ | ✅ |
| WAV | `audio/wav` | ✅ Safari | ✅ | ✅ |
| MP3 | `audio/mpeg` | ✅ | ✅ | ✅ |

**Recommendation:**
- **Browser:** Use `audio/webm;codecs=opus` — smallest file, widest support, best quality. Fall back to `audio/ogg` for Firefox-only environments.
- **iOS (Flutter):** `AudioEncoder.aacLc` → `.m4a` — the only format iOS records natively.
- **Android (Flutter):** `AudioEncoder.aacLc` → `.m4a` or `.aac` — consistent across devices.
