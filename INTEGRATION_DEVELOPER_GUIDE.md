# Riviwa Integration Developer Guide

> **Version:** 1.0 · **Last updated:** April 2026  
> **Base URL (Production):** `https://api.riviwa.com`  
> **Base URL (Sandbox):** `https://sandbox.riviwa.com`  
> **Integration Service Port (direct):** `8100`

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Integration Patterns](#2-integration-patterns)
3. [Getting Started — Register a Client](#3-getting-started--register-a-client)
4. [Authentication Deep Dive](#4-authentication-deep-dive)
5. [Submit Feedback (the core flow)](#5-submit-feedback-the-core-flow)
6. [Context Sessions — Pre-filling User Data](#6-context-sessions--pre-filling-user-data)
7. [Widget & Mini-App Embedding](#7-widget--mini-app-embedding)
8. [Webhooks — Real-time Notifications](#8-webhooks--real-time-notifications)
9. [Platform Guides](#9-platform-guides)
   - [Flutter / Dart](#91-flutter--dart)
   - [React Native](#92-react-native)
   - [Python (Django / FastAPI)](#93-python-django--fastapi)
   - [PHP (Laravel)](#94-php-laravel)
   - [Node.js / TypeScript](#95-nodejs--typescript)
   - [JavaScript — Website Widget](#96-javascript--website-widget)
10. [Security Best Practices](#10-security-best-practices)
11. [Rate Limits & Quotas](#11-rate-limits--quotas)
12. [Error Handling Reference](#12-error-handling-reference)
13. [Testing Checklist](#13-testing-checklist)
14. [FAQ](#14-faq)

---

## 1. Introduction

Riviwa is a **Grievance & Feedback Management (GRM)** platform. The Integration API lets your application:

| Use case | Description |
|----------|-------------|
| **Mini App** | Embed Riviwa's GRM interface inside your mobile app (like Mixx by Yas / CRDB Bank) |
| **Website Widget** | Drop a JS tag on your site — one script line, fully branded |
| **AI Chatbot Tag** | Attach Riviwa's AI chatbot to your site/app like Google Tag in Bolt/Uber |
| **Server-to-server** | Your backend pushes feedback data directly via API (machine-to-machine) |
| **External Data Bridge** | Riviwa fetches user context (name, phone, account) from your endpoint on demand |

All integrations share the same core primitives:

```
Register Client → Authenticate → Push Context → Submit/Embed → Receive Webhooks
```

---

## 2. Integration Patterns

### Pattern A — Server-Side API (machine-to-machine)
Best for: CRMs, banking systems, ERP integrations.

```
Your Server ──[Client Credentials]──► Riviwa Token
Your Server ──[POST /integration/feedback]──► Riviwa stores feedback
Riviwa ──[Webhook]──► Your Server
```

### Pattern B — Mobile Mini-App (OAuth2 PKCE)
Best for: Flutter, React Native, iOS/Android apps.

```
Your App Backend ──[POST /integration/context]──► session_token
Your App ──opens WebView with session_token──► Riviwa Mini-App
User fills & submits feedback
Riviwa ──[Webhook]──► Your Backend
```

### Pattern C — Website Widget (JS Tag)
Best for: corporate websites, portals.

```html
<script>
  riviwa('init', 'YOUR_CLIENT_ID', {org: 'YOUR_ORG_ID'});
  riviwa('track', 'page_view');
</script>
```

### Pattern D — AI Chatbot (embedded chat tag)
Best for: airline/bank customer support portals.

```
User clicks chat icon
Your page calls POST /integration/widget/session
Riviwa chat widget opens in iframe/drawer
AI collects complaint → auto-submits
```

---

## 3. Getting Started — Register a Client

### Step 1: Contact Riviwa Platform Admin

A platform administrator registers your client and gives you:

| Credential | Description | When shown |
|------------|-------------|------------|
| `client_id` | Public identifier (`rwi_client_xxx`) | Always visible |
| `client_secret` | Private secret (`rwi_secret_xxx`) | **Once only — store securely** |
| `webhook_signing_secret` | HMAC secret for verifying webhooks | **Once only — store securely** |

### Step 2: Store credentials securely

```bash
# .env (server-side only — NEVER commit or expose to frontend)
RIVIWA_CLIENT_ID=rwi_client_xxxxxxxxxxxxx
RIVIWA_CLIENT_SECRET=rwi_secret_xxxxxxxxxxxxx
RIVIWA_WEBHOOK_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
RIVIWA_ORG_ID=your-organisation-uuid
```

> ⚠️ **Never** put `client_secret` or `webhook_signing_secret` in mobile app binaries, browser JavaScript, or public repos.

### Step 3: Choose your sandbox environment

All client IDs registered with `environment: SANDBOX` use the sandbox environment. API keys for sandbox have the prefix `rwi_sandbox_`.

```bash
# Verify your client works
curl -s https://sandbox.riviwa.com/api/v1/integration/.well-known/openid-configuration | jq .issuer
# → "https://riviwa.com"
```

---

## 4. Authentication Deep Dive

### 4.1 Client Credentials Grant (server-to-server)

Use this when your **backend** calls Riviwa directly. Token lifetime is **15 minutes**.

```bash
curl -X POST https://api.riviwa.com/api/v1/integration/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=$RIVIWA_CLIENT_ID" \
  -d "client_secret=$RIVIWA_CLIENT_SECRET" \
  -d "scope=feedback:write feedback:read data:push"
```

**Response:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 900,
  "scope": "feedback:write feedback:read data:push"
}
```

**Token caching pattern (recommended):**

```python
import time, threading

class RiviwaTokenCache:
    def __init__(self):
        self._token = None
        self._expires_at = 0
        self._lock = threading.Lock()

    def get_token(self, client_id, client_secret):
        with self._lock:
            if time.time() < self._expires_at - 60:   # 60s buffer
                return self._token
            resp = self._fetch_token(client_id, client_secret)
            self._token = resp["access_token"]
            self._expires_at = time.time() + resp["expires_in"]
            return self._token
```

### 4.2 Authorization Code + PKCE (mobile / SPA)

Use this when a **user** authenticates and authorises your app to act on their behalf.

**PKCE flow (RFC 7636):**

```
1. App generates code_verifier (random 32+ bytes, base64url)
2. App computes code_challenge = BASE64URL(SHA256(code_verifier))
3. App opens browser/WebView → GET /integration/oauth/authorize?...
4. User logs in to Riviwa → Riviwa issues code
5. App receives code via redirect_uri
6. App exchanges code + code_verifier → access_token + refresh_token
```

```bash
# Step 3 — open this URL in the user's browser
CODE_VERIFIER=$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '=')
CODE_CHALLENGE=$(echo -n "$CODE_VERIFIER" | openssl dgst -sha256 -binary | base64 | tr '+/' '-_' | tr -d '=')

AUTHORIZE_URL="https://api.riviwa.com/api/v1/integration/oauth/authorize\
?response_type=code\
&client_id=$RIVIWA_CLIENT_ID\
&redirect_uri=myapp://callback\
&scope=feedback:write\
&code_challenge=$CODE_CHALLENGE\
&code_challenge_method=S256"
```

```bash
# Step 6 — exchange code for tokens
curl -X POST https://api.riviwa.com/api/v1/integration/oauth/token \
  -d "grant_type=authorization_code" \
  -d "code=$CODE" \
  -d "redirect_uri=myapp://callback" \
  -d "code_verifier=$CODE_VERIFIER" \
  -d "client_id=$RIVIWA_CLIENT_ID"
```

### 4.3 API Key (lightweight auth)

Issue long-lived API keys from the admin panel for integrations that don't need user context.

```bash
curl https://api.riviwa.com/api/v1/integration/webhooks/deliveries \
  -H "X-API-Key: rwi_sandbox_xxxxxxxxxxxxxxxx"
```

### 4.4 Token Refresh

```bash
curl -X POST https://api.riviwa.com/api/v1/integration/oauth/token \
  -d "grant_type=refresh_token" \
  -d "refresh_token=$REFRESH_TOKEN" \
  -d "client_id=$RIVIWA_CLIENT_ID"
```

---

## 5. Submit Feedback (the core flow)

### 5.1 Simple server-side submission

```bash
# 1. Get token
TOKEN=$(curl -s -X POST https://api.riviwa.com/api/v1/integration/oauth/token \
  -d "grant_type=client_credentials&client_id=$RIVIWA_CLIENT_ID&client_secret=$RIVIWA_CLIENT_SECRET&scope=feedback:write" \
  | jq -r .access_token)

# 2. Submit grievance
curl -X POST https://api.riviwa.com/api/v1/integration/feedback \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "feedback_type": "GRIEVANCE",
    "title": "Road construction blocked my shop entrance",
    "description": "Since Monday the contractor blocked the only access road to my shop without notice. I am losing business every day.",
    "priority": "HIGH",
    "channel": "MINI_APP",
    "phone": "+255712345678",
    "name": "Amina Hassan",
    "account_ref": "ACCT-00123",
    "project_id": "d363d9bc-20b3-4590-b08e-157283fe03c0"
  }'
```

**Response (201 Created):**
```json
{
  "feedback_id": "a1b2c3d4-...",
  "reference": "GRM-2026-0042",
  "org_id": "your-org-uuid",
  "feedback_type": "GRIEVANCE",
  "status": "submitted",
  "submitted_at": "2026-04-24T18:36:45.000Z",
  "webhook_queued": true
}
```

### 5.2 Feedback types and when to use them

| Type | Use case | Lifecycle |
|------|----------|-----------|
| `GRIEVANCE` | Formal complaint requiring investigation | Submitted → Acknowledged → In Review → Resolved → Closed |
| `SUGGESTION` | Improvement idea | Submitted → Reviewed → Actioned/Noted |
| `APPLAUSE` | Positive recognition | Submitted → Acknowledged |
| `INQUIRY` | Question or information request | Submitted → Answered |

### 5.3 Check feedback status

```bash
curl https://api.riviwa.com/api/v1/integration/feedback/$FEEDBACK_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

## 6. Context Sessions — Pre-filling User Data

Context sessions let your backend push user data **before** the user launches the Riviwa widget/mini-app so fields are pre-filled. The session is single-use, 30-minute TTL, encrypted at rest.

### Flow diagram

```
Your Backend                    Riviwa                     Your App/Widget
    │                              │                              │
    │─── POST /integration/context ──►│                              │
    │       {phone, name, account_ref}│                              │
    │◄── {session_token, org_id} ────│                              │
    │                              │                              │
    │─── pass session_token ────────────────────────────────────►│
    │                              │                              │
    │                              │◄── GET /context/consume?token=...
    │                              │─── {pre_fill: {phone, name...}} ──►│
    │                              │       (token consumed)       │
```

### Create a context session

```bash
curl -X POST https://api.riviwa.com/api/v1/integration/context \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+255712345678",
    "name": "John Doe",
    "email": "john@example.com",
    "account_ref": "CRDB-ACC-00123",
    "service_id": "uuid-of-service",
    "product_id": "uuid-of-product",
    "ttl_seconds": 1800
  }'
```

**Response:**
```json
{
  "session_token": "xxxxxxxxxxxxxxxxxxxxxxxx",
  "session_id": "uuid",
  "org_id": "your-org-uuid",
  "expires_at": "2026-04-24T19:06:45Z",
  "ttl_seconds": 1800
}
```

Pass `session_token` to your widget as a URL parameter:
```
https://widget.riviwa.com/embed?token=SESSION_TOKEN&org=ORG_ID
```

---

## 7. Widget & Mini-App Embedding

### 7.1 JS Widget (website)

**Step 1:** Get the snippet from your dashboard or API:

```bash
curl https://api.riviwa.com/api/v1/integration/widget/snippet?client_id=$CLIENT_ID \
  -H "Authorization: Bearer $TOKEN"
```

**Step 2:** Add to your website's `<head>` or before `</body>`:

```html
<!-- Riviwa Feedback Widget -->
<script>
  (function(r,i,v,i2,w,a){r['RiviwaObject']=w;r[w]=r[w]||function(){
  (r[w].q=r[w].q||[]).push(arguments)},r[w].l=1*new Date();a=i.createElement(v),
  m=i.getElementsByTagName(v)[0];a.async=1;a.src=i2;m.parentNode.insertBefore(a,m)
  })(window,document,'script','https://widget.riviwa.com/widget.js','riviwa');
  riviwa('init', 'rwi_client_YOUR_CLIENT_ID', {org: 'YOUR_ORG_UUID'});
  riviwa('track', 'page_view');
</script>
<!-- End Riviwa Feedback Widget -->
```

**Step 3 (optional):** Pre-fill user data for logged-in users:

```javascript
// After your user logs in
await fetch('/your-backend/get-riviwa-token', { method: 'POST' })
  .then(r => r.json())
  .then(({ session_token }) => {
    riviwa('identify', session_token);   // pre-fills name/phone/account
  });
```

### 7.2 Mobile Mini-App (WebView)

**Step 1:** Your backend creates a widget session:

```json
POST /api/v1/integration/widget/session
{
  "user_ref": "your-internal-user-id",
  "locale": "sw",
  "theme": "light",
  "ttl_seconds": 1800
}
```

**Response includes `embed_url`:**
```json
{
  "embed_token": "xxxx",
  "embed_url": "https://widget.riviwa.com/embed?token=xxxx&org=ORG_UUID",
  "org_id": "ORG_UUID",
  "ttl_seconds": 1800
}
```

**Step 2:** Open the `embed_url` in a WebView inside your app (see platform guides below).

### 7.3 CORS and allowed origins

The widget config endpoint validates the `Origin` header against your `allowed_origins` list. Configure this during client registration:

```json
{
  "allowed_origins": [
    "https://yourbank.co.tz",
    "https://app.yourbank.co.tz"
  ]
}
```

---

## 8. Webhooks — Real-time Notifications

Riviwa sends a signed HTTP POST to your `webhook_url` when feedback lifecycle events occur.

### 8.1 Subscribed events

| Event | When fired |
|-------|-----------|
| `feedback.submitted` | New feedback received |
| `feedback.acknowledged` | GRM officer acknowledged receipt |
| `feedback.in_review` | Investigation started |
| `feedback.escalated` | Escalated to higher GRM level |
| `feedback.resolved` | Resolution recorded |
| `feedback.closed` | Feedback closed |
| `feedback.dismissed` | Feedback dismissed |

### 8.2 Webhook payload

```json
{
  "event": "feedback.submitted",
  "feedback_id": "a1b2c3d4-...",
  "reference": "GRM-2026-0042",
  "org_id": "your-org-uuid",
  "feedback_type": "GRIEVANCE",
  "source_ref": "YOUR-INTERNAL-REF",
  "submitted_at": "2026-04-24T18:36:45.000Z"
}
```

### 8.3 Verifying webhook signatures

Every delivery includes:
```
X-Riviwa-Signature: sha256=<hex_digest>
X-Riviwa-Timestamp: <unix_timestamp>
X-Riviwa-Event: feedback.submitted
X-Riviwa-Delivery: <uuid>
```

**Verification algorithm:** `HMAC-SHA256(timestamp + "." + body_bytes, signing_secret)`

Reject payloads where `|now - timestamp| > 300 seconds` to prevent replay attacks.

```python
# Python verification
import hmac, hashlib, time

def verify_riviwa_webhook(body: bytes, signature: str, timestamp: str, secret: str) -> bool:
    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > 300:
            return False   # replay attack
        msg = f"{ts}.".encode() + body
        expected = "sha256=" + hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False
```

### 8.4 Respond quickly — async processing pattern

Your endpoint must return `2xx` within **10 seconds** or Riviwa retries. Use a queue:

```python
# Django example
@csrf_exempt
def riviwa_webhook(request):
    if not verify_riviwa_webhook(
        request.body,
        request.headers.get("X-Riviwa-Signature", ""),
        request.headers.get("X-Riviwa-Timestamp", ""),
        settings.RIVIWA_WEBHOOK_SECRET,
    ):
        return HttpResponse(status=403)

    # Queue for async processing — respond immediately
    process_riviwa_event.delay(request.body.decode())
    return HttpResponse(status=200)
```

### 8.5 Retry schedule

| Attempt | Delay after failure |
|---------|-------------------|
| 1st retry | 30 seconds |
| 2nd retry | 5 minutes |
| 3rd retry | 30 minutes |
| Final failure | No more retries — check delivery logs |

---

## 9. Platform Guides

### 9.1 Flutter / Dart

#### Installation

```yaml
# pubspec.yaml
dependencies:
  http: ^1.1.0
  webview_flutter: ^4.4.0
  flutter_secure_storage: ^9.0.0
```

#### Token management service

```dart
// lib/services/riviwa_service.dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class RiviwaService {
  static const String _baseUrl = 'https://api.riviwa.com';
  final _storage = const FlutterSecureStorage();

  // Never hardcode client_secret in app code — fetch from your backend
  Future<String> _getAccessToken() async {
    final cached = await _storage.read(key: 'riviwa_token');
    final expiry = await _storage.read(key: 'riviwa_token_expiry');

    if (cached != null && expiry != null) {
      final expiresAt = DateTime.parse(expiry);
      if (DateTime.now().isBefore(expiresAt.subtract(const Duration(seconds: 60)))) {
        return cached;
      }
    }

    // Fetch token from YOUR backend (which holds the client_secret)
    final resp = await http.post(
      Uri.parse('https://yourbackend.com/api/riviwa-token'),
    );
    final data = jsonDecode(resp.body);
    final token = data['access_token'] as String;
    final expiresIn = data['expires_in'] as int;

    await _storage.write(key: 'riviwa_token', value: token);
    await _storage.write(
      key: 'riviwa_token_expiry',
      value: DateTime.now().add(Duration(seconds: expiresIn)).toIso8601String(),
    );
    return token;
  }

  /// Create a context session and return the embed URL
  Future<String> createWidgetSession({
    required String userRef,
    String locale = 'sw',
    String theme = 'light',
  }) async {
    final token = await _getAccessToken();
    final resp = await http.post(
      Uri.parse('$_baseUrl/api/v1/integration/widget/session'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'user_ref': userRef,
        'locale': locale,
        'theme': theme,
        'ttl_seconds': 1800,
      }),
    );
    if (resp.statusCode != 201) {
      throw Exception('Failed to create widget session: ${resp.body}');
    }
    final data = jsonDecode(resp.body);
    return data['embed_url'] as String;
  }

  /// Submit feedback directly from your backend
  Future<Map<String, dynamic>> submitFeedback({
    required String feedbackType,
    required String title,
    required String description,
    required String phone,
    String? projectId,
    String priority = 'MEDIUM',
  }) async {
    final token = await _getAccessToken();
    final resp = await http.post(
      Uri.parse('$_baseUrl/api/v1/integration/feedback'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'feedback_type': feedbackType,
        'title': title,
        'description': description,
        'phone': phone,
        'priority': priority,
        if (projectId != null) 'project_id': projectId,
      }),
    );
    return jsonDecode(resp.body);
  }
}
```

#### Mini-App WebView screen

```dart
// lib/screens/riviwa_screen.dart
import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../services/riviwa_service.dart';

class RiviwaFeedbackScreen extends StatefulWidget {
  final String userRef;
  const RiviwaFeedbackScreen({super.key, required this.userRef});

  @override
  State<RiviwaFeedbackScreen> createState() => _RiviwaFeedbackScreenState();
}

class _RiviwaFeedbackScreenState extends State<RiviwaFeedbackScreen> {
  late final WebViewController _controller;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _initWebView();
  }

  Future<void> _initWebView() async {
    try {
      final url = await RiviwaService().createWidgetSession(
        userRef: widget.userRef,
        locale: 'sw',
      );
      _controller = WebViewController()
        ..setJavaScriptMode(JavaScriptMode.unrestricted)
        ..setNavigationDelegate(NavigationDelegate(
          onPageFinished: (_) => setState(() => _loading = false),
          onWebResourceError: (e) => setState(() => _error = e.description),
        ))
        ..loadRequest(Uri.parse(url));

      setState(() {});
    } catch (e) {
      setState(() => _error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Feedback')),
        body: Center(child: Text('Error: $_error')),
      );
    }
    return Scaffold(
      appBar: AppBar(
        title: const Text('Submit Feedback'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Stack(
        children: [
          if (!_loading) WebViewWidget(controller: _controller),
          if (_loading) const Center(child: CircularProgressIndicator()),
        ],
      ),
    );
  }
}
```

#### PKCE Authorization Code Flow (Flutter)

```dart
// lib/services/riviwa_auth.dart
import 'dart:convert';
import 'dart:math';
import 'package:crypto/crypto.dart';

class RiviwaPKCE {
  static String generateCodeVerifier() {
    final rand = Random.secure();
    final bytes = List<int>.generate(32, (_) => rand.nextInt(256));
    return base64Url.encode(bytes).replaceAll('=', '');
  }

  static String generateCodeChallenge(String verifier) {
    final bytes = utf8.encode(verifier);
    final digest = sha256.convert(bytes);
    return base64Url.encode(digest.bytes).replaceAll('=', '');
  }

  static String buildAuthUrl({
    required String clientId,
    required String redirectUri,
    required String codeChallenge,
    String scope = 'feedback:write',
  }) {
    final params = {
      'response_type': 'code',
      'client_id': clientId,
      'redirect_uri': redirectUri,
      'scope': scope,
      'code_challenge': codeChallenge,
      'code_challenge_method': 'S256',
    };
    final query = params.entries.map((e) =>
      '${Uri.encodeComponent(e.key)}=${Uri.encodeComponent(e.value)}'
    ).join('&');
    return 'https://api.riviwa.com/api/v1/integration/oauth/authorize?$query';
  }
}
```

---

### 9.2 React Native

#### Installation

```bash
npm install @react-native-async-storage/async-storage react-native-webview
```

#### Token hook

```typescript
// hooks/useRiviwaToken.ts
import { useState, useCallback } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const BASE_URL = 'https://api.riviwa.com';

export function useRiviwaToken() {
  const [loading, setLoading] = useState(false);

  const getToken = useCallback(async (): Promise<string> => {
    const cached = await AsyncStorage.getItem('riviwa:token');
    const expiryStr = await AsyncStorage.getItem('riviwa:token_expiry');

    if (cached && expiryStr) {
      const expiry = new Date(expiryStr);
      if (expiry.getTime() - Date.now() > 60_000) return cached;
    }

    // Call YOUR backend — never put client_secret in app code
    setLoading(true);
    const resp = await fetch('https://yourbackend.com/api/riviwa-token', {
      method: 'POST',
    });
    const { access_token, expires_in } = await resp.json();

    const expiresAt = new Date(Date.now() + expires_in * 1000).toISOString();
    await AsyncStorage.setItem('riviwa:token', access_token);
    await AsyncStorage.setItem('riviwa:token_expiry', expiresAt);
    setLoading(false);
    return access_token;
  }, []);

  return { getToken, loading };
}
```

#### Mini-App WebView component

```tsx
// components/RiviwaWidget.tsx
import React, { useState, useEffect } from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import WebView from 'react-native-webview';
import { useRiviwaToken } from '../hooks/useRiviwaToken';

interface Props {
  userRef: string;
  locale?: 'sw' | 'en';
  onClose?: () => void;
}

export const RiviwaWidget: React.FC<Props> = ({
  userRef,
  locale = 'sw',
  onClose,
}) => {
  const [embedUrl, setEmbedUrl] = useState<string | null>(null);
  const { getToken } = useRiviwaToken();

  useEffect(() => {
    (async () => {
      const token = await getToken();
      const resp = await fetch(
        'https://api.riviwa.com/api/v1/integration/widget/session',
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ user_ref: userRef, locale, ttl_seconds: 1800 }),
        }
      );
      const data = await resp.json();
      setEmbedUrl(data.embed_url);
    })();
  }, [userRef, locale]);

  if (!embedUrl) {
    return (
      <View style={styles.loader}>
        <ActivityIndicator size="large" color="#0066CC" />
      </View>
    );
  }

  return (
    <WebView
      source={{ uri: embedUrl }}
      style={styles.webview}
      javaScriptEnabled
      onNavigationStateChange={(state) => {
        // Detect when widget signals completion
        if (state.url.includes('riviwa://close')) onClose?.();
      }}
    />
  );
};

const styles = StyleSheet.create({
  loader: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  webview: { flex: 1 },
});
```

---

### 9.3 Python (Django / FastAPI)

#### Installation

```bash
pip install httpx pyjwt cryptography
```

#### Riviwa client class (reusable)

```python
# riviwa/client.py
import time
import httpx
from threading import Lock
from dataclasses import dataclass, field
from typing import Optional

BASE_URL = "https://api.riviwa.com"

@dataclass
class RiviwaClient:
    client_id: str
    client_secret: str
    org_id: str
    _token: str = field(default="", init=False, repr=False)
    _token_expires_at: float = field(default=0.0, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def _get_token(self) -> str:
        with self._lock:
            if time.time() < self._token_expires_at - 60:
                return self._token
            resp = httpx.post(
                f"{BASE_URL}/api/v1/integration/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "feedback:write feedback:read data:push",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["access_token"]
            self._token_expires_at = time.time() + data["expires_in"]
            return self._token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    def create_context_session(
        self,
        phone: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        account_ref: Optional[str] = None,
        project_id: Optional[str] = None,
        ttl_seconds: int = 1800,
    ) -> dict:
        payload = {k: v for k, v in {
            "phone": phone, "name": name, "email": email,
            "account_ref": account_ref, "project_id": project_id,
            "ttl_seconds": ttl_seconds,
        }.items() if v is not None}
        resp = httpx.post(
            f"{BASE_URL}/api/v1/integration/context",
            headers=self._headers(), json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    def submit_feedback(
        self,
        feedback_type: str,
        title: str,
        description: str,
        phone: Optional[str] = None,
        name: Optional[str] = None,
        project_id: Optional[str] = None,
        priority: str = "MEDIUM",
        channel: str = "API",
        source_ref: Optional[str] = None,
    ) -> dict:
        payload = {k: v for k, v in {
            "feedback_type": feedback_type,
            "title": title,
            "description": description,
            "phone": phone,
            "name": name,
            "project_id": project_id,
            "priority": priority,
            "channel": channel,
            "source_ref": source_ref,
        }.items() if v is not None}
        resp = httpx.post(
            f"{BASE_URL}/api/v1/integration/feedback",
            headers=self._headers(), json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    def verify_webhook(
        self,
        body: bytes,
        signature: str,
        timestamp: str,
        secret: str,
    ) -> bool:
        import hmac, hashlib
        try:
            ts = int(timestamp)
            if abs(time.time() - ts) > 300:
                return False
            msg = f"{ts}.".encode() + body
            expected = "sha256=" + hmac.new(
                secret.encode(), msg, hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(expected, signature)
        except Exception:
            return False
```

#### Django webhook view

```python
# views.py
import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .riviwa.client import RiviwaClient
from .tasks import handle_riviwa_event  # Celery task

riviwa = RiviwaClient(
    client_id=settings.RIVIWA_CLIENT_ID,
    client_secret=settings.RIVIWA_CLIENT_SECRET,
    org_id=settings.RIVIWA_ORG_ID,
)

@csrf_exempt
def riviwa_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    valid = riviwa.verify_webhook(
        body=request.body,
        signature=request.headers.get("X-Riviwa-Signature", ""),
        timestamp=request.headers.get("X-Riviwa-Timestamp", ""),
        secret=settings.RIVIWA_WEBHOOK_SECRET,
    )
    if not valid:
        return HttpResponse(status=403)

    # Enqueue for async processing — respond in <10s
    event = json.loads(request.body)
    handle_riviwa_event.delay(event)
    return HttpResponse(status=200)
```

#### FastAPI async example

```python
# main.py
from fastapi import FastAPI, Request, HTTPException, Depends
from riviwa.client import RiviwaClient
import os

app = FastAPI()
riviwa = RiviwaClient(
    client_id=os.environ["RIVIWA_CLIENT_ID"],
    client_secret=os.environ["RIVIWA_CLIENT_SECRET"],
    org_id=os.environ["RIVIWA_ORG_ID"],
)

@app.post("/api/submit-complaint")
async def submit_complaint(request: Request):
    body = await request.json()
    result = riviwa.submit_feedback(
        feedback_type="GRIEVANCE",
        title=body["title"],
        description=body["description"],
        phone=body.get("phone"),
        name=body.get("name"),
        project_id=body.get("project_id"),
        priority=body.get("priority", "MEDIUM"),
        source_ref=body.get("reference"),
    )
    return {"feedback_id": result["feedback_id"], "reference": result["reference"]}

@app.post("/webhooks/riviwa")
async def riviwa_webhook(request: Request):
    body = await request.body()
    valid = riviwa.verify_webhook(
        body=body,
        signature=request.headers.get("X-Riviwa-Signature", ""),
        timestamp=request.headers.get("X-Riviwa-Timestamp", ""),
        secret=os.environ["RIVIWA_WEBHOOK_SECRET"],
    )
    if not valid:
        raise HTTPException(status_code=403, detail="Invalid signature")

    event = await request.json()
    # Process asynchronously (e.g. background task)
    print(f"Received: {event['event']} for {event['feedback_id']}")
    return {"received": True}
```

---

### 9.4 PHP (Laravel)

#### Installation

```bash
composer require guzzlehttp/guzzle
```

#### Service class

```php
<?php
// app/Services/RiviwaService.php
namespace App\Services;

use GuzzleHttp\Client;
use Illuminate\Support\Facades\Cache;

class RiviwaService
{
    private Client $http;
    private string $baseUrl;

    public function __construct()
    {
        $this->baseUrl = config('riviwa.base_url', 'https://api.riviwa.com');
        $this->http = new Client(['base_uri' => $this->baseUrl]);
    }

    private function getToken(): string
    {
        return Cache::remember('riviwa_token', 840, function () {
            $resp = $this->http->post('/api/v1/integration/oauth/token', [
                'form_params' => [
                    'grant_type'    => 'client_credentials',
                    'client_id'     => config('riviwa.client_id'),
                    'client_secret' => config('riviwa.client_secret'),
                    'scope'         => 'feedback:write feedback:read data:push',
                ],
            ]);
            $data = json_decode($resp->getBody(), true);
            return $data['access_token'];
        });
    }

    public function createContextSession(array $params): array
    {
        $resp = $this->http->post('/api/v1/integration/context', [
            'headers' => [
                'Authorization' => 'Bearer ' . $this->getToken(),
                'Content-Type'  => 'application/json',
            ],
            'json' => array_filter($params),
        ]);
        return json_decode($resp->getBody(), true);
    }

    public function submitFeedback(array $payload): array
    {
        $resp = $this->http->post('/api/v1/integration/feedback', [
            'headers' => [
                'Authorization' => 'Bearer ' . $this->getToken(),
                'Content-Type'  => 'application/json',
            ],
            'json' => $payload,
        ]);
        return json_decode($resp->getBody(), true);
    }

    public function verifyWebhook(
        string $body,
        string $signature,
        string $timestamp,
        string $secret
    ): bool {
        if (abs(time() - (int)$timestamp) > 300) return false;
        $msg      = $timestamp . '.' . $body;
        $expected = 'sha256=' . hash_hmac('sha256', $msg, $secret);
        return hash_equals($expected, $signature);
    }
}
```

#### Route and controller

```php
<?php
// routes/api.php
Route::post('/webhooks/riviwa', [WebhookController::class, 'riviwa']);
Route::post('/feedback', [FeedbackController::class, 'submit']);
```

```php
<?php
// app/Http/Controllers/WebhookController.php
namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Services\RiviwaService;
use App\Jobs\ProcessRiviwaEvent;

class WebhookController extends Controller
{
    public function riviwa(Request $request, RiviwaService $riviwa)
    {
        $valid = $riviwa->verifyWebhook(
            $request->getContent(),
            $request->header('X-Riviwa-Signature', ''),
            $request->header('X-Riviwa-Timestamp', ''),
            config('riviwa.webhook_secret'),
        );

        if (!$valid) {
            return response()->json(['error' => 'Invalid signature'], 403);
        }

        // Dispatch to queue — respond within 10 seconds
        ProcessRiviwaEvent::dispatch($request->all());
        return response()->json(['received' => true]);
    }
}
```

#### Config file

```php
<?php
// config/riviwa.php
return [
    'base_url'       => env('RIVIWA_BASE_URL', 'https://api.riviwa.com'),
    'client_id'      => env('RIVIWA_CLIENT_ID'),
    'client_secret'  => env('RIVIWA_CLIENT_SECRET'),
    'org_id'         => env('RIVIWA_ORG_ID'),
    'webhook_secret' => env('RIVIWA_WEBHOOK_SECRET'),
];
```

---

### 9.5 Node.js / TypeScript

#### Installation

```bash
npm install axios crypto
npm install -D @types/node
```

#### Riviwa SDK class

```typescript
// src/riviwa/client.ts
import axios, { AxiosInstance } from 'axios';
import crypto from 'crypto';

interface TokenCache {
  token: string;
  expiresAt: number;
}

export class RiviwaClient {
  private http: AxiosInstance;
  private tokenCache: TokenCache | null = null;

  constructor(
    private clientId: string,
    private clientSecret: string,
    private orgId: string,
    private baseUrl = 'https://api.riviwa.com',
  ) {
    this.http = axios.create({ baseURL: baseUrl });
  }

  private async getToken(): Promise<string> {
    if (this.tokenCache && Date.now() < this.tokenCache.expiresAt - 60_000) {
      return this.tokenCache.token;
    }
    const resp = await this.http.post(
      '/api/v1/integration/oauth/token',
      new URLSearchParams({
        grant_type:    'client_credentials',
        client_id:     this.clientId,
        client_secret: this.clientSecret,
        scope:         'feedback:write feedback:read data:push',
      }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
    );
    this.tokenCache = {
      token: resp.data.access_token,
      expiresAt: Date.now() + resp.data.expires_in * 1000,
    };
    return this.tokenCache.token;
  }

  async createContextSession(params: {
    phone?: string;
    name?: string;
    email?: string;
    account_ref?: string;
    project_id?: string;
    ttl_seconds?: number;
  }) {
    const token = await this.getToken();
    const resp = await this.http.post(
      '/api/v1/integration/context',
      params,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    return resp.data;
  }

  async submitFeedback(payload: {
    feedback_type: 'GRIEVANCE' | 'SUGGESTION' | 'APPLAUSE' | 'INQUIRY';
    title: string;
    description?: string;
    phone?: string;
    name?: string;
    project_id?: string;
    priority?: 'LOW' | 'MEDIUM' | 'HIGH';
    channel?: string;
    source_ref?: string;
  }) {
    const token = await this.getToken();
    const resp = await this.http.post('/api/v1/integration/feedback', payload, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return resp.data;
  }

  verifyWebhook(
    body: Buffer,
    signature: string,
    timestamp: string,
    secret: string,
  ): boolean {
    const ts = parseInt(timestamp, 10);
    if (Math.abs(Date.now() / 1000 - ts) > 300) return false;
    const msg = Buffer.concat([Buffer.from(`${ts}.`), body]);
    const expected = `sha256=${crypto
      .createHmac('sha256', secret)
      .update(msg)
      .digest('hex')}`;
    return crypto.timingSafeEqual(
      Buffer.from(expected),
      Buffer.from(signature),
    );
  }
}
```

#### Express webhook handler

```typescript
// src/routes/webhooks.ts
import express from 'express';
import { RiviwaClient } from '../riviwa/client';

const router = express.Router();
const riviwa = new RiviwaClient(
  process.env.RIVIWA_CLIENT_ID!,
  process.env.RIVIWA_CLIENT_SECRET!,
  process.env.RIVIWA_ORG_ID!,
);

// Use raw body parser for signature verification
router.post(
  '/riviwa',
  express.raw({ type: 'application/json' }),
  (req, res) => {
    const valid = riviwa.verifyWebhook(
      req.body,
      req.headers['x-riviwa-signature'] as string ?? '',
      req.headers['x-riviwa-timestamp'] as string ?? '',
      process.env.RIVIWA_WEBHOOK_SECRET!,
    );
    if (!valid) return res.sendStatus(403);

    const event = JSON.parse(req.body.toString());
    console.log(`Riviwa event: ${event.event} → ${event.feedback_id}`);

    // Enqueue for async processing
    setImmediate(() => processRiviwaEvent(event));
    res.sendStatus(200);
  },
);

async function processRiviwaEvent(event: any) {
  // Update your DB, notify your team, etc.
  switch (event.event) {
    case 'feedback.resolved':
      await notifyCustomer(event.feedback_id, event.reference);
      break;
    case 'feedback.escalated':
      await alertManager(event);
      break;
  }
}
```

---

### 9.6 JavaScript — Website Widget

#### Minimal setup (2 lines)

```html
<!DOCTYPE html>
<html>
<head>
  <script>
    (function(r,i,v,i2,w,a){r['RiviwaObject']=w;r[w]=r[w]||function(){
    (r[w].q=r[w].q||[]).push(arguments)},r[w].l=1*new Date();a=i.createElement(v),
    m=i.getElementsByTagName(v)[0];a.async=1;a.src=i2;m.parentNode.insertBefore(a,m)
    })(window,document,'script','https://widget.riviwa.com/widget.js','riviwa');
    riviwa('init', 'rwi_client_YOUR_ID', {org: 'YOUR_ORG_UUID', locale: 'sw'});
  </script>
</head>
<body>
  <!-- Your page content -->
  <button onclick="riviwa('open')">Submit Feedback</button>
</body>
</html>
```

#### Advanced: pre-fill logged-in user data

```javascript
// After user logs in to your portal
async function initRiviwaForUser(user) {
  // Call YOUR backend to create a context session
  const { session_token } = await fetch('/api/riviwa-session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      phone: user.phoneNumber,
      name:  user.fullName,
      account_ref: user.accountNumber,
    }),
  }).then(r => r.json());

  // Identify user in widget — fields will be pre-filled
  riviwa('identify', session_token);

  // Track page views for context
  riviwa('track', 'page_view', {
    page: window.location.pathname,
    service: 'internet_banking',
  });
}

// Open widget on button click
document.getElementById('feedback-btn').addEventListener('click', () => {
  riviwa('open', { type: 'GRIEVANCE' });   // open pre-selected to grievance
});
```

#### Your backend endpoint for context sessions

```javascript
// Express.js — /api/riviwa-session
app.post('/api/riviwa-session', requireAuth, async (req, res) => {
  const token = await riviwa.getToken();
  const session = await fetch('https://api.riviwa.com/api/v1/integration/context', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      phone:       req.body.phone,
      name:        req.body.name,
      account_ref: req.body.account_ref,
      ttl_seconds: 900,  // 15 min for web sessions
    }),
  }).then(r => r.json());

  // Return ONLY the session_token to frontend — never the Bearer token
  res.json({ session_token: session.session_token });
});
```

---

## 10. Security Best Practices

### Credential handling

| ✅ DO | ❌ DON'T |
|-------|---------|
| Store `client_secret` in environment variables | Commit secrets to version control |
| Fetch tokens server-side, proxy to client | Put `client_secret` in mobile app code |
| Use HTTPS everywhere | Use HTTP in production |
| Rotate secrets after suspected compromise | Share secrets between environments |
| Verify webhook signatures | Skip signature verification |
| Use short-lived context sessions (≤30 min) | Reuse context session tokens |

### Token proxy pattern (recommended for mobile apps)

Never give your mobile app `client_secret`. Instead:

```
Mobile App ──[authenticated request]──► Your Backend
Your Backend ──[client_credentials]──► Riviwa (with client_secret)
Your Backend ──[access_token]──► Mobile App
```

Your backend endpoint:
```
POST /api/riviwa-token   (requires user JWT)
→ Returns short-lived Riviwa access_token
```

### IP allowlisting (enterprise)

For banks and hospitals, restrict access by IP:

```json
{
  "allowed_ips": [
    "196.23.1.100",
    "196.23.1.101",
    "10.0.0.0/8"
  ]
}
```

### mTLS (mutual TLS)

For financial institutions requiring maximum security:

```json
{
  "require_mtls": true,
  "mtls_cert_fingerprint": "AA:BB:CC:..."
}
```

---

## 11. Rate Limits & Quotas

| Tier | Requests/minute | Requests/day |
|------|----------------|--------------|
| Sandbox | 20 | 500 |
| Standard | 60 | 10,000 |
| Enterprise | 300 | 100,000 |

**Rate limit response (HTTP 429):**
```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "window": "minute"
}
```

**Retry with exponential backoff:**
```python
import time, random

def with_retry(fn, max_retries=3):
    for attempt in range(max_retries):
        try:
            return fn()
        except RateLimitError:
            if attempt == max_retries - 1:
                raise
            wait = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait)
```

---

## 12. Error Handling Reference

| HTTP | Error Code | Meaning | Action |
|------|-----------|---------|--------|
| 400 | `MISSING_CONTEXT_DATA` | No identity fields provided | Add phone, name, email, or account_ref |
| 400 | `DESCRIPTION_REQUIRED` | No title/description | Add title or description field |
| 400 | `PROJECT_ID_REQUIRED` | No project_id for staff submission | Add project_id |
| 400 | `INVALID_FEEDBACK_TYPE` | Bad feedback_type value | Use GRIEVANCE/SUGGESTION/APPLAUSE/INQUIRY |
| 400 | `SUBMITTER_IDENTITY_REQUIRED` | No submitter identity | Add phone, name, email, or account_ref |
| 401 | `INVALID_API_KEY` | API key not recognised | Check key prefix and environment |
| 401 | `TOKEN_EXPIRED` | JWT expired | Refresh token |
| 401 | `INVALID_TOKEN` | JWT malformed/wrong key | Re-authenticate |
| 401 | `API_KEY_EXPIRED` | API key TTL elapsed | Issue new key from admin panel |
| 403 | `INSUFFICIENT_SCOPE` | Token lacks required scope | Re-request with correct scope |
| 403 | `ORG_MISMATCH` | Requested org ≠ client's org | Don't override org_id |
| 403 | `CLIENT_NOT_ORG_BOUND` | Client has no organisation | Set organisation_id on client |
| 403 | `IP_NOT_ALLOWED` | Caller IP not in allowlist | Add IP to client's allowed_ips |
| 403 | `ORIGIN_NOT_ALLOWED` | Widget origin blocked | Add origin to allowed_origins |
| 404 | `CLIENT_NOT_FOUND` | Client UUID not found | Check client UUID |
| 404 | `SESSION_NOT_FOUND` | Token invalid/consumed | Create new context session |
| 410 | `SESSION_EXPIRED` | Session TTL elapsed | Create new context session |
| 422 | `SUBMISSION_FAILED` | Feedback validation error | Check error message for details |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests | Backoff and retry |
| 503 | `FEEDBACK_SERVICE_UNAVAILABLE` | Downstream service down | Retry in 30 seconds |

---

## 13. Testing Checklist

Before going live, verify each item:

### Authentication
- [ ] Client credentials token issued (`expires_in: 900`)
- [ ] JWT contains `org_id` claim
- [ ] Wrong secret returns 401
- [ ] Token revocation makes token inactive

### Context Sessions
- [ ] Session created with correct `org_id` returned
- [ ] Session consumed once and returns pre-fill data
- [ ] Double-consume returns 404
- [ ] Wrong `org_id` in body returns 403 `ORG_MISMATCH`
- [ ] Session expires after TTL

### Feedback Submission
- [ ] Grievance submitted returns `feedback_id` + `reference`
- [ ] Suggestion, Applause, Inquiry each work
- [ ] Missing identity returns 400
- [ ] Cross-org submission returns 403

### Webhooks
- [ ] Test delivery sends to your endpoint
- [ ] HMAC signature verifies correctly
- [ ] Replay attack (old timestamp) rejected
- [ ] Retry fires after endpoint timeout

### Widget
- [ ] Snippet loads on your domain
- [ ] Wrong origin returns 403
- [ ] `org_id` present in widget config response
- [ ] Pre-fill data appears in widget form

### Rate Limits
- [ ] Burst > 60/min returns 429
- [ ] 429 response includes `window` field

---

## 14. FAQ

**Q: Can I use the same `client_id` for both sandbox and production?**  
A: No. Each environment requires a separate client registration. Sandbox keys have the `rwi_sandbox_` prefix; production keys use `rwi_live_`.

**Q: What if the user doesn't have a project_id?**  
A: Omit `project_id` and include `issue_lga` (district/LGA name). Riviwa's AI service will auto-detect the correct project from the location and description. If it can't detect, the feedback is stored without a project and can be enriched later.

**Q: Can I submit feedback anonymously?**  
A: Not via the integration bridge (which requires submitter identity for accountability). Anonymous submissions go through the consumer web portal.

**Q: How long does the feedback bridge take?**  
A: Typically 200–500ms when the feedback_service is healthy. The bridge has a 15-second timeout. Design your UX to show a loading state.

**Q: What happens if my webhook endpoint is down during an event?**  
A: Riviwa retries 3 times with exponential backoff (30s → 5m → 30m). After 3 failures the delivery is marked `FAILED`. You can manually trigger a retry from the webhook delivery history API.

**Q: Can I receive webhooks for events I didn't cause?**  
A: Yes, if you subscribe to `feedback.resolved` you'll receive it when any GRM officer resolves a feedback submitted through your integration — even days after the original submission.

**Q: How do I handle duplicate webhook deliveries?**  
A: Use the `X-Riviwa-Delivery` UUID header to deduplicate. Store processed delivery IDs for at least 24 hours.

**Q: Is there an SDK?**  
A: Official SDKs for Flutter, React Native, Python, and PHP are on the roadmap. The code samples in this guide are production-ready and can be copied directly.

**Q: What's the maximum payload size for feedback?**  
A: `description` max 10,000 characters. `title`/`subject` max 500 characters. `metadata` object max 10KB.

**Q: Can I change the organisation_id after client registration?**  
A: No — `organisation_id` is permanent once set. Create a new client for a different organisation.

---

## Appendix: Available Scopes

| Scope | Description |
|-------|-------------|
| `feedback:write` | Submit feedback on behalf of users |
| `feedback:read` | Read feedback status and history |
| `data:push` | Create context sessions with user pre-fill data |
| `profile:read` | Read user profile via userinfo endpoint |

---

## Appendix: Webhook Event Reference

| Event | Fired by |
|-------|---------|
| `feedback.submitted` | Any submission through integration bridge |
| `feedback.acknowledged` | GRM officer marks received |
| `feedback.in_review` | Investigation started |
| `feedback.escalated` | Escalated to ward/district/national level |
| `feedback.resolved` | Resolution note recorded |
| `feedback.closed` | Final closure (consumer confirmed) |
| `feedback.dismissed` | Duplicate/out-of-scope |

---

*For technical support: integration@riviwa.com*  
*API status: status.riviwa.com*  
*GitHub Issues: github.com/josako53/RiviwaGlobe/issues*
