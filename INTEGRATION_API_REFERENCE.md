# Riviwa Integration Service — API Reference

**Version:** v1  
**Service port (direct):** `8100`  
**Production base URL:** `https://api.riviwa.com`  
**Sandbox base URL:** `https://sandbox.riviwa.com`  
**All paths are prefixed with:** `/api/v1`

---

## Table of Contents

1. [Authentication Overview](#authentication-overview)
2. [API Versioning](#api-versioning)
3. [Client Management](#client-management)
4. [OAuth2](#oauth2)
5. [Context Sessions](#context-sessions)
6. [Widget & Mini App](#widget--mini-app)
7. [Webhooks](#webhooks)
8. [Feedback Bridge](#feedback-bridge)
9. [Data Models](#data-models)
10. [Error Reference](#error-reference)

---

## Authentication Overview

The integration service supports three authentication mechanisms depending on the caller and the operation:

### 1. Platform Admin JWT (Client Management only)

All `/integration/clients` endpoints require a **Riviwa platform admin JWT** issued by the auth service. The JWT must carry `platform_role: "super_admin"` or `"admin"` in its payload.

```
Authorization: Bearer <platform_admin_jwt>
```

### 2. OAuth2 Bearer Token

An OAuth2 access token obtained via the `/integration/oauth/token` endpoint. JWT-signed with HS256. Required for most partner-facing endpoints.

```
Authorization: Bearer <access_token>
```

Access tokens carry a `scopes` claim. Each endpoint declares its required scope. The default TTL is **15 minutes** (`ACCESS_TOKEN_TTL_SECONDS=900`).

### 3. API Key

A static key issued via `POST /integration/clients/{id}/api-keys`. Pass in the `Authorization` header with the `Bearer` scheme or in an `X-API-Key` header:

```
Authorization: Bearer rwi_live_<key>
```

API keys have an optional expiry (`expires_at`) and a scope subset that must be within the client's `allowed_scopes`.

### Token TTLs (defaults)

| Token type | TTL | Configurable |
|---|---|---|
| Access token (JWT) | 15 minutes | `ACCESS_TOKEN_TTL_SECONDS` |
| Refresh token (opaque) | 30 days | `REFRESH_TOKEN_TTL_SECONDS` |
| Authorization code | 10 minutes | `AUTH_CODE_TTL_SECONDS` |
| Context session token | 30 minutes | `CONTEXT_SESSION_TTL_SECONDS` |

### OAuth2 Scopes

| Scope | Description |
|---|---|
| `feedback:write` | Submit feedback, create context sessions, create widget sessions |
| `feedback:read` | Read feedback status |
| `profile:read` | Access OIDC userinfo endpoint |
| `data:push` | Push pre-fill context to context sessions |

---

## API Versioning

All endpoints are versioned under `/api/v1/`. The OIDC discovery document at `GET /api/v1/integration/.well-known/openid-configuration` provides all endpoint URLs for automatic SDK configuration.

Breaking changes will be introduced under a new version prefix (`/api/v2/`). Non-breaking additions (new response fields, new optional request fields) may be added without a version bump.

---

## Client Management

All endpoints in this section require a **Riviwa platform admin JWT** (`Authorization: Bearer <admin_jwt>`). Partners are registered here before they can use any other integration API.

### Endpoint Summary

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/integration/clients` | Platform Admin JWT | Register a new integration partner |
| `GET` | `/api/v1/integration/clients` | Platform Admin JWT | List all active clients |
| `GET` | `/api/v1/integration/clients/{id}` | Platform Admin JWT | Get a single client |
| `PATCH` | `/api/v1/integration/clients/{id}` | Platform Admin JWT | Update client configuration |
| `DELETE` | `/api/v1/integration/clients/{id}` | Platform Admin JWT | Deactivate a client |
| `POST` | `/api/v1/integration/clients/{id}/rotate-secret` | Platform Admin JWT | Rotate the client secret |
| `POST` | `/api/v1/integration/clients/{id}/api-keys` | Platform Admin JWT | Issue a new API key |
| `GET` | `/api/v1/integration/clients/{id}/api-keys` | Platform Admin JWT | List API keys for a client |
| `DELETE` | `/api/v1/integration/clients/{id}/api-keys/{key_id}` | Platform Admin JWT | Revoke an API key |

---

### POST /api/v1/integration/clients

Register a new integration partner. Returns `client_id` and `client_secret` — the secret is shown **once** and must be stored securely.

**Auth:** Platform Admin JWT

**Request Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Human-readable partner name |
| `description` | string | No | Optional description |
| `client_type` | string | No | `API` \| `MINI_APP` \| `WEB_WIDGET` \| `SDK` \| `CHATBOT` (default: `API`) |
| `environment` | string | No | `LIVE` \| `SANDBOX` (default: `SANDBOX`) |
| `organisation_id` | UUID string | No | Riviwa organisation this client is bound to |
| `allowed_scopes` | array of strings | No | OAuth2 scopes granted to this client (default: `["feedback:write"]`) |
| `allowed_origins` | array of strings | No | CORS origin allowlist for widget/chatbot embeds. Use `["*"]` to allow all. |
| `allowed_ips` | array of strings | No | IP allowlist for enterprise clients (banks, hospitals). Empty = all IPs allowed. |
| `redirect_uris` | array of strings | No | Allowed redirect URIs for Authorization Code flow |
| `webhook_url` | string | No | Partner endpoint to receive outbound webhook events |
| `webhook_events` | array of strings | No | Subscribed webhook event types (see [WebhookEventType](#webhookeventtype)) |
| `data_endpoint_url` | string | No | Partner's data endpoint; Riviwa calls this to enrich user context |
| `require_mtls` | boolean | No | Require mutual TLS (enterprise clients). Default: `false` |
| `rate_limit_per_minute` | integer | No | Requests per minute cap (default: `60`) |
| `rate_limit_per_day` | integer | No | Requests per day cap (default: `10000`) |

**Response — 201 Created**

| Field | Type | Description |
|---|---|---|
| `id` | UUID string | Internal record UUID |
| `client_id` | string | Public OAuth2 client identifier (e.g. `rwi_client_xxx`) |
| `client_secret` | string | Raw client secret — **shown once, store securely** |
| `name` | string | Client name |
| `client_type` | string | Client type |
| `environment` | string | `LIVE` or `SANDBOX` |
| `organisation_id` | UUID string \| null | Bound organisation |
| `allowed_scopes` | array | Granted scopes |
| `created_at` | ISO 8601 datetime | Creation timestamp |
| `warning` | string | Reminder that `client_secret` will not be shown again |
| `webhook_signing_secret` | string | Present only if `webhook_url` was provided — **shown once** |
| `webhook_warning` | string | Present only if `webhook_signing_secret` is returned |

**Errors**

| Code | HTTP | Description |
|---|---|---|
| `MISSING_TOKEN` | 401 | No `Authorization` header |
| `TOKEN_EXPIRED` | 401 | Admin JWT has expired |
| `INVALID_TOKEN` | 401 | Admin JWT signature invalid |
| `INSUFFICIENT_ROLE` | 403 | Caller's `platform_role` is not `super_admin` or `admin` |

**curl example**

```bash
curl -X POST https://api.riviwa.com/api/v1/integration/clients \
  -H "Authorization: Bearer <admin_jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Bank GRM",
    "description": "Acme Bank customer feedback integration",
    "client_type": "API",
    "environment": "LIVE",
    "organisation_id": "a1b2c3d4-0000-0000-0000-000000000001",
    "allowed_scopes": ["feedback:write", "feedback:read"],
    "allowed_ips": ["203.0.113.10"],
    "webhook_url": "https://hooks.acmebank.com/riviwa",
    "webhook_events": ["feedback.submitted", "feedback.resolved"],
    "rate_limit_per_minute": 120
  }'
```

---

### GET /api/v1/integration/clients

List all active integration clients with optional filters.

**Auth:** Platform Admin JWT

**Query Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `environment` | string | No | Filter by `LIVE` or `SANDBOX` |
| `organisation_id` | UUID | No | Filter by bound organisation |

**Response — 200 OK**

| Field | Type | Description |
|---|---|---|
| `total` | integer | Number of results |
| `items` | array | Array of client objects (see [Client Object](#client-object)) |

**curl example**

```bash
curl https://api.riviwa.com/api/v1/integration/clients?environment=LIVE \
  -H "Authorization: Bearer <admin_jwt>"
```

---

### GET /api/v1/integration/clients/{id}

Retrieve a single client by its internal UUID.

**Auth:** Platform Admin JWT

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | UUID | Client internal record UUID |

**Response — 200 OK**

Returns a [Client Object](#client-object).

**Errors**

| Code | HTTP | Description |
|---|---|---|
| `CLIENT_NOT_FOUND` | 404 | No client with that UUID |

**curl example**

```bash
curl https://api.riviwa.com/api/v1/integration/clients/a1b2c3d4-1111-0000-0000-000000000001 \
  -H "Authorization: Bearer <admin_jwt>"
```

---

### PATCH /api/v1/integration/clients/{id}

Update mutable fields on an existing client. Only the fields listed below can be updated.

**Auth:** Platform Admin JWT

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | UUID | Client internal record UUID |

**Request Body** (all fields optional)

| Field | Type | Description |
|---|---|---|
| `name` | string | Partner display name |
| `description` | string | Description |
| `allowed_scopes` | array | Replace scope list |
| `allowed_origins` | array | Replace CORS origin allowlist |
| `allowed_ips` | array | Replace IP allowlist |
| `redirect_uris` | array | Replace redirect URI list |
| `webhook_url` | string | Webhook delivery URL |
| `webhook_events` | array | Subscribed event types |
| `data_endpoint_url` | string | External context data URL |
| `rate_limit_per_minute` | integer | Per-minute request cap |
| `rate_limit_per_day` | integer | Per-day request cap |
| `require_mtls` | boolean | Require mutual TLS |
| `mtls_cert_fingerprint` | string | Expected client certificate fingerprint |

**Response — 200 OK**

Returns the updated [Client Object](#client-object).

**Errors**

| Code | HTTP | Description |
|---|---|---|
| `CLIENT_NOT_FOUND` | 404 | No client with that UUID |

**curl example**

```bash
curl -X PATCH https://api.riviwa.com/api/v1/integration/clients/a1b2c3d4-1111-0000-0000-000000000001 \
  -H "Authorization: Bearer <admin_jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "allowed_scopes": ["feedback:write", "feedback:read"],
    "rate_limit_per_minute": 200,
    "webhook_url": "https://hooks.acmebank.com/riviwa-v2"
  }'
```

---

### DELETE /api/v1/integration/clients/{id}

Deactivate a client. Sets `is_active = false`; does not delete the record. All API keys and tokens issued to this client will stop working immediately.

**Auth:** Platform Admin JWT

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | UUID | Client internal record UUID |

**Response — 204 No Content**

**Errors**

| Code | HTTP | Description |
|---|---|---|
| `CLIENT_NOT_FOUND` | 404 | No client with that UUID |

**curl example**

```bash
curl -X DELETE https://api.riviwa.com/api/v1/integration/clients/a1b2c3d4-1111-0000-0000-000000000001 \
  -H "Authorization: Bearer <admin_jwt>"
```

---

### POST /api/v1/integration/clients/{id}/rotate-secret

Rotate the `client_secret` for a client. The new secret is returned **once** — the old secret is immediately invalidated.

**Auth:** Platform Admin JWT

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | UUID | Client internal record UUID |

**Request Body:** None

**Response — 200 OK**

| Field | Type | Description |
|---|---|---|
| `client_secret` | string | New raw client secret — **shown once** |
| `warning` | string | Reminder to store securely |

**Errors**

| Code | HTTP | Description |
|---|---|---|
| `CLIENT_NOT_FOUND` | 404 | No client with that UUID |

**curl example**

```bash
curl -X POST https://api.riviwa.com/api/v1/integration/clients/a1b2c3d4-1111-0000-0000-000000000001/rotate-secret \
  -H "Authorization: Bearer <admin_jwt>"
```

---

### POST /api/v1/integration/clients/{id}/api-keys

Issue a new API key for the client. The full key is returned **once**.

Key format: `rwi_live_<48_bytes_base64url>` (live environment) or `rwi_sandbox_<48_bytes_base64url>` (sandbox).

**Auth:** Platform Admin JWT

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | UUID | Client internal record UUID |

**Request Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | No | Friendly label for this key (e.g. `"production-server-1"`) |
| `scopes` | array | No | Scope subset — must be within the client's `allowed_scopes`. Defaults to all client scopes. |
| `expires_days` | integer | No | Days until expiry. Omit for non-expiring key. |

**Response — 201 Created**

| Field | Type | Description |
|---|---|---|
| `id` | UUID string | API key record UUID |
| `api_key` | string | Full API key — **shown once, store securely** |
| `prefix` | string | First 8 chars (safe to display in dashboards) |
| `scopes` | array | Scopes granted to this key |
| `expires_at` | ISO 8601 datetime \| null | Expiry, if set |
| `warning` | string | Reminder that the key will not be shown again |

**Errors**

| Code | HTTP | Description |
|---|---|---|
| `CLIENT_NOT_FOUND` | 404 | No client with that UUID |
| `INVALID_SCOPES` | 400 | Requested scopes outside client's `allowed_scopes` |

**curl example**

```bash
curl -X POST https://api.riviwa.com/api/v1/integration/clients/a1b2c3d4-1111-0000-0000-000000000001/api-keys \
  -H "Authorization: Bearer <admin_jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "production-server-1",
    "scopes": ["feedback:write"],
    "expires_days": 365
  }'
```

---

### GET /api/v1/integration/clients/{id}/api-keys

List all API keys (active and revoked) for a client.

**Auth:** Platform Admin JWT

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | UUID | Client internal record UUID |

**Response — 200 OK**

| Field | Type | Description |
|---|---|---|
| `total` | integer | Total number of keys |
| `items` | array | Array of key summary objects |

Each item in `items`:

| Field | Type | Description |
|---|---|---|
| `id` | UUID string | Key record UUID |
| `prefix` | string | First 8 chars (safe to display) |
| `name` | string \| null | Friendly label |
| `scopes` | array | Granted scopes |
| `is_active` | boolean | Whether the key is currently active |
| `expires_at` | ISO 8601 datetime \| null | Expiry timestamp |
| `last_used_at` | ISO 8601 datetime \| null | Last successful use |
| `created_at` | ISO 8601 datetime | Creation timestamp |

**curl example**

```bash
curl https://api.riviwa.com/api/v1/integration/clients/a1b2c3d4-1111-0000-0000-000000000001/api-keys \
  -H "Authorization: Bearer <admin_jwt>"
```

---

### DELETE /api/v1/integration/clients/{id}/api-keys/{key_id}

Revoke an API key. Sets `is_active = false` and records `revoked_at`. The key is immediately invalid.

**Auth:** Platform Admin JWT

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | UUID | Client internal record UUID |
| `key_id` | UUID | API key record UUID |

**Response — 204 No Content**

**Errors**

| Code | HTTP | Description |
|---|---|---|
| `KEY_NOT_FOUND` | 404 | Key does not exist or does not belong to that client |

**curl example**

```bash
curl -X DELETE "https://api.riviwa.com/api/v1/integration/clients/a1b2c3d4-1111-0000-0000-000000000001/api-keys/b2c3d4e5-0000-0000-0000-000000000002" \
  -H "Authorization: Bearer <admin_jwt>"
```

---

### Client Object

Returned by `GET`, `PATCH`, and list endpoints:

| Field | Type | Description |
|---|---|---|
| `id` | UUID string | Internal record UUID |
| `client_id` | string | Public OAuth2 client identifier |
| `name` | string | Display name |
| `description` | string \| null | Description |
| `client_type` | string | `API` \| `MINI_APP` \| `WEB_WIDGET` \| `SDK` \| `CHATBOT` |
| `environment` | string | `LIVE` \| `SANDBOX` |
| `organisation_id` | UUID string \| null | Bound Riviwa organisation |
| `allowed_scopes` | array | OAuth2 scopes granted |
| `allowed_origins` | array | CORS origin allowlist |
| `allowed_ips` | array | IP allowlist |
| `redirect_uris` | array | Allowed redirect URIs |
| `webhook_url` | string \| null | Webhook delivery URL |
| `webhook_events` | array | Subscribed event types |
| `data_endpoint_url` | string \| null | External context data URL |
| `require_mtls` | boolean | Whether mutual TLS is required |
| `rate_limit_per_minute` | integer | Per-minute request cap |
| `rate_limit_per_day` | integer | Per-day request cap |
| `is_active` | boolean | Whether the client is active |
| `created_at` | ISO 8601 datetime | Creation timestamp |
| `last_used_at` | ISO 8601 datetime \| null | Last API call timestamp |

---

## OAuth2

The integration service implements a standards-compliant OAuth2 Authorization Server. OIDC Discovery allows consuming SDKs to auto-configure without hardcoding endpoint URLs.

**Supported flows:**

| Grant type | Use case |
|---|---|
| `authorization_code` + PKCE | Mobile apps, SPAs, mini-apps acting on behalf of a user |
| `client_credentials` | Server-to-server / machine-to-machine calls |
| `refresh_token` | Extend user sessions (Authorization Code flow only) |

### Endpoint Summary

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/integration/oauth/authorize` | Optional user JWT | Authorization endpoint (PKCE) |
| `POST` | `/api/v1/integration/oauth/token` | Client credentials | Token endpoint |
| `POST` | `/api/v1/integration/oauth/revoke` | None (per RFC 7009) | Revoke a token |
| `POST` | `/api/v1/integration/oauth/introspect` | None | Introspect a token (RFC 7662) |
| `GET` | `/api/v1/integration/oauth/userinfo` | Bearer token | OIDC userinfo |
| `GET` | `/api/v1/integration/.well-known/openid-configuration` | None | OIDC Discovery document |
| `GET` | `/api/v1/integration/.well-known/jwks.json` | None | JWKS endpoint |

---

### GET /api/v1/integration/oauth/authorize

Authorization endpoint. The partner's mobile app or SPA redirects the user's browser here to begin the Authorization Code + PKCE flow. On success, Riviwa redirects back to `redirect_uri` with an authorization code.

**Auth:** Optional — pass a Riviwa user JWT in `Authorization: Bearer <jwt>` to bind the issued code to a specific user.

**Query Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `response_type` | string | Yes | Must be `code` |
| `client_id` | string | Yes | The partner's `client_id` |
| `redirect_uri` | string | Yes | Must match one of the client's registered `redirect_uris` |
| `scope` | string | No | Space-separated scopes (default: `feedback:write`) |
| `state` | string | No | Opaque value echoed back in the redirect — use for CSRF protection |
| `code_challenge` | string | Yes | PKCE code challenge (Base64url-encoded SHA-256 of `code_verifier`) |
| `code_challenge_method` | string | No | `S256` (recommended) or `plain`. Default: `S256` |

**Response — 302 Redirect**

Redirects to `redirect_uri?code=<auth_code>&state=<state>` on success, or `redirect_uri?error=<error>&state=<state>` on failure.

**Error redirects**

| Error | Description |
|---|---|
| `unsupported_response_type` | `response_type` was not `code` |
| `code_challenge_required` | PKCE is mandatory |
| `invalid_code_challenge_method` | Only `S256` and `plain` are supported |
| `invalid_client` | `client_id` unknown or inactive |
| `invalid_redirect_uri` | `redirect_uri` not in the client's registered list |
| `invalid_scope` | Requested scope exceeds client's `allowed_scopes` |

**curl example**

```bash
# Step 1: generate PKCE verifier and challenge
CODE_VERIFIER=$(openssl rand -base64 48 | tr -d '+=/' | cut -c1-64)
CODE_CHALLENGE=$(echo -n "$CODE_VERIFIER" | openssl dgst -sha256 -binary | openssl base64 -A | tr '+/' '-_' | tr -d '=')

# Step 2: open in browser / redirect user
curl -v "https://api.riviwa.com/api/v1/integration/oauth/authorize\
?response_type=code\
&client_id=rwi_client_abc123\
&redirect_uri=https%3A%2F%2Fapp.acmebank.com%2Fcallback\
&scope=feedback%3Awrite\
&state=random_csrf_state\
&code_challenge=${CODE_CHALLENGE}\
&code_challenge_method=S256"
```

---

### POST /api/v1/integration/oauth/token

Token endpoint. Accepts `application/x-www-form-urlencoded`. Supports three grant types.

Client authentication can use either **HTTP Basic auth** (`Authorization: Basic base64(client_id:client_secret)`) or **form parameters** (`client_id` + `client_secret` in the body).

#### Grant: authorization_code

Exchange a PKCE authorization code for an access token and refresh token.

**Form Parameters**

| Field | Type | Required | Description |
|---|---|---|---|
| `grant_type` | string | Yes | `authorization_code` |
| `code` | string | Yes | The authorization code received from the authorize redirect |
| `redirect_uri` | string | Yes | Must exactly match the URI used in the authorize request |
| `code_verifier` | string | Yes | Original PKCE code verifier |
| `client_id` | string | Yes* | Client ID (or use HTTP Basic) |

**Response — 200 OK**

| Field | Type | Description |
|---|---|---|
| `access_token` | string | JWT access token |
| `token_type` | string | Always `bearer` |
| `expires_in` | integer | Seconds until access token expiry (900) |
| `refresh_token` | string | Opaque refresh token |
| `scope` | string | Space-separated granted scopes |

**curl example**

```bash
curl -X POST https://api.riviwa.com/api/v1/integration/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code\
&code=<auth_code_from_redirect>\
&redirect_uri=https%3A%2F%2Fapp.acmebank.com%2Fcallback\
&code_verifier=<original_code_verifier>\
&client_id=rwi_client_abc123"
```

---

#### Grant: client_credentials

Machine-to-machine. Returns an access token only (no refresh token).

**Form Parameters**

| Field | Type | Required | Description |
|---|---|---|---|
| `grant_type` | string | Yes | `client_credentials` |
| `client_id` | string | Yes* | Client ID (or use HTTP Basic) |
| `client_secret` | string | Yes* | Client secret (or use HTTP Basic) |
| `scope` | string | No | Space-separated scopes to request (subset of `allowed_scopes`) |

**Response — 200 OK**

| Field | Type | Description |
|---|---|---|
| `access_token` | string | JWT access token |
| `token_type` | string | Always `bearer` |
| `expires_in` | integer | Seconds until expiry (900) |
| `scope` | string | Space-separated granted scopes |

**curl example**

```bash
curl -X POST https://api.riviwa.com/api/v1/integration/oauth/token \
  -H "Authorization: Basic $(echo -n 'rwi_client_abc123:rwi_secret_xyz' | base64)" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&scope=feedback%3Awrite"
```

---

#### Grant: refresh_token

Rotate the refresh token. Issues a new access token + refresh token pair. The old refresh token is revoked (token rotation).

**Form Parameters**

| Field | Type | Required | Description |
|---|---|---|---|
| `grant_type` | string | Yes | `refresh_token` |
| `refresh_token` | string | Yes | The opaque refresh token |
| `client_id` | string | Yes* | Client ID (or use HTTP Basic) |

**Response — 200 OK**

Same as `authorization_code` response: `access_token`, `token_type`, `expires_in`, `refresh_token`, `scope`.

**curl example**

```bash
curl -X POST https://api.riviwa.com/api/v1/integration/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token\
&refresh_token=<opaque_refresh_token>\
&client_id=rwi_client_abc123"
```

**Token errors (all grant types)**

| Code | HTTP | Description |
|---|---|---|
| `invalid_client` | 401 | Unknown client, inactive client, or wrong client_secret |
| `invalid_grant` | 400 | Code expired, already used, redirect_uri mismatch, or PKCE failure |
| `invalid_scope` | 400 | Requested scope exceeds client's allowed scopes |
| `invalid_request` | 400 | Missing required parameter |
| `unsupported_grant_type` | 400 | Grant type is not supported |

---

### POST /api/v1/integration/oauth/revoke

Revoke an access token or refresh token (RFC 7009). Always returns `200 OK` even if the token is unknown or already revoked.

**Auth:** None required (per RFC 7009 spec)

**Form Parameters**

| Field | Type | Required | Description |
|---|---|---|---|
| `token` | string | Yes | The access token (JWT) or refresh token (opaque) to revoke |
| `token_type_hint` | string | No | `access_token` or `refresh_token` (hint only) |
| `client_id` | string | No | Client identifier |
| `client_secret` | string | No | Client secret |

**Response — 200 OK**

```json
{"revoked": true}
```

**curl example**

```bash
curl -X POST https://api.riviwa.com/api/v1/integration/oauth/revoke \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "token=<access_or_refresh_token>&client_id=rwi_client_abc123"
```

---

### POST /api/v1/integration/oauth/introspect

Token introspection (RFC 7662). Returns `active: false` for any invalid, expired, or revoked token.

**Auth:** None required

**Form Parameters**

| Field | Type | Required | Description |
|---|---|---|---|
| `token` | string | Yes | The access token (JWT) to introspect |
| `token_type_hint` | string | No | Hint: `access_token` |

**Response — 200 OK (active token)**

| Field | Type | Description |
|---|---|---|
| `active` | boolean | `true` if the token is valid, not expired, and not revoked |
| `sub` | string | Subject (user UUID or client UUID) |
| `client_id` | string | The client that was issued this token |
| `scope` | string | Space-separated scopes |
| `exp` | integer | Unix timestamp — expiry |
| `iat` | integer | Unix timestamp — issued at |
| `jti` | string | JWT ID |

**Response — 200 OK (inactive token)**

```json
{"active": false}
```

**curl example**

```bash
curl -X POST https://api.riviwa.com/api/v1/integration/oauth/introspect \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "token=<access_token>"
```

---

### GET /api/v1/integration/oauth/userinfo

OIDC userinfo endpoint. Returns the authenticated user's profile. Requires the `profile:read` scope.

**Auth:** `Authorization: Bearer <access_token>` (must have `profile:read` scope)

**Response — 200 OK**

| Field | Type | Description |
|---|---|---|
| `sub` | string | User UUID (or client UUID if no user context) |
| `client_id` | string | The client that issued the token |
| `scopes` | array | Scopes granted on this token |

**Errors**

| Code | HTTP | Description |
|---|---|---|
| `missing_token` | 401 | No Authorization header |
| `invalid_token` | 401 | Token is invalid or expired |
| `insufficient_scope` | 403 | Token does not have `profile:read` scope |

**curl example**

```bash
curl https://api.riviwa.com/api/v1/integration/oauth/userinfo \
  -H "Authorization: Bearer <access_token>"
```

---

### GET /api/v1/integration/.well-known/openid-configuration

OIDC Discovery document. Returns all endpoint URLs so SDKs can auto-configure without hardcoding.

**Auth:** None

**Response — 200 OK**

```json
{
  "issuer": "https://riviwa.com",
  "authorization_endpoint": "https://api.riviwa.com/api/v1/integration/oauth/authorize",
  "token_endpoint": "https://api.riviwa.com/api/v1/integration/oauth/token",
  "revocation_endpoint": "https://api.riviwa.com/api/v1/integration/oauth/revoke",
  "introspection_endpoint": "https://api.riviwa.com/api/v1/integration/oauth/introspect",
  "userinfo_endpoint": "https://api.riviwa.com/api/v1/integration/oauth/userinfo",
  "jwks_uri": "https://api.riviwa.com/api/v1/integration/.well-known/jwks.json",
  "response_types_supported": ["code"],
  "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"],
  "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
  "scopes_supported": ["feedback:write", "feedback:read", "profile:read", "data:push"],
  "code_challenge_methods_supported": ["S256", "plain"],
  "subject_types_supported": ["public"]
}
```

---

### GET /api/v1/integration/.well-known/jwks.json

JWKS endpoint. The integration service currently uses HS256 (shared secret), so no public key is published. Consuming SDKs should use client secret verification or contact Riviwa to negotiate an RS256 keypair.

**Auth:** None

**Response — 200 OK**

```json
{"keys": []}
```

---

## Context Sessions

Context sessions allow a partner server to pre-push user data (phone, name, account reference, pre-selected category/service) **before** the user opens a Riviwa widget or mini-app. The widget then calls `/consume` to retrieve and apply the pre-fill data automatically.

**Flow:**

```
1. Partner server:  POST /integration/context   → { session_token, org_id }
2. Partner opens:   Riviwa widget?session_token=<token>
3. Riviwa widget:   GET  /integration/context/consume?token=<token>
4. Widget pre-fills the form from decrypted data
```

The `session_token` is single-use: the first `/consume` call sets `consumed_at`. Subsequent calls return `SESSION_NOT_FOUND`.

### Endpoint Summary

| Method | Path | Auth | Scope | Description |
|---|---|---|---|---|
| `POST` | `/api/v1/integration/context` | Bearer / API Key | `data:push` | Create a context session |
| `GET` | `/api/v1/integration/context/consume` | None | — | Consume session token (widget use) |
| `GET` | `/api/v1/integration/context/{session_id}` | Bearer / API Key | Any | Check session status |

---

### POST /api/v1/integration/context

Create a pre-fill context session. The session is automatically scoped to the client's bound `organisation_id`.

**Auth:** Bearer token or API key | **Scope:** `data:push`

**Request Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `phone` | string | No* | User phone number (E.164 recommended) |
| `name` | string | No* | User full name |
| `email` | string | No* | User email address |
| `account_ref` | string | No* | Partner's internal account/customer reference |
| `service_id` | UUID string | No | Riviwa service UUID to pre-select |
| `product_id` | UUID string | No | Riviwa product UUID to pre-select |
| `category_id` | UUID string | No | Riviwa feedback category UUID |
| `department_id` | UUID string | No | Riviwa department UUID |
| `project_id` | UUID string | No | Restrict session to a specific Riviwa project |
| `org_id` | UUID string | No | Must match client's bound `organisation_id` if provided |
| `ttl_seconds` | integer | No | TTL override in seconds (max `3600`, default `1800`) |
| `metadata` | object | No | Freeform partner-specific data |

*At least one of `phone`, `name`, `email`, or `account_ref` is required.

**Response — 201 Created**

| Field | Type | Description |
|---|---|---|
| `session_token` | string | Opaque token — **shown once, pass to widget** |
| `session_id` | UUID string | Session record UUID (for status checks) |
| `org_id` | UUID string | Enforced organisation UUID |
| `project_id` | UUID string \| null | Project restriction, if set |
| `expires_at` | ISO 8601 datetime | When the session expires |
| `ttl_seconds` | integer | Effective TTL |
| `warning` | string | Reminder that `session_token` will not be shown again |

**Errors**

| Code | HTTP | Description |
|---|---|---|
| `MISSING_CONTEXT_DATA` | 400 | None of `phone`, `name`, `email`, `account_ref` were provided |
| `ORG_MISMATCH` | 403 | Provided `org_id` does not match client's bound organisation |

**curl example**

```bash
curl -X POST https://api.riviwa.com/api/v1/integration/context \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+255712345678",
    "name": "Jane Doe",
    "account_ref": "ACME-ACC-00123",
    "category_id": "c1c2c3c4-0000-0000-0000-000000000001",
    "project_id": "p1p2p3p4-0000-0000-0000-000000000001",
    "ttl_seconds": 900,
    "metadata": {"branch_code": "DSM01"}
  }'
```

---

### GET /api/v1/integration/context/consume

Called by the Riviwa widget or mini-app to retrieve and consume the pre-fill data. This is a **single-use** endpoint — the first successful call marks the session as consumed.

**Auth:** None (called by the widget, not the partner server)

**Query Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `token` | string | Yes | The `session_token` issued by `POST /integration/context` |

**Response — 200 OK**

| Field | Type | Description |
|---|---|---|
| `session_id` | UUID string | Session record UUID |
| `org_id` | UUID string \| null | Scoping organisation |
| `project_id` | UUID string \| null | Project restriction, if set |
| `pre_fill` | object | Decrypted pre-fill data (`phone`, `name`, `email`, `account_ref`, `category_id`, etc.) |

**Errors**

| Code | HTTP | Description |
|---|---|---|
| `SESSION_NOT_FOUND` | 404 | Token is invalid, already consumed, or does not exist |
| `SESSION_EXPIRED` | 410 | Session TTL has elapsed |
| `DECRYPTION_FAILED` | 500 | Internal encryption error |

**curl example**

```bash
curl "https://api.riviwa.com/api/v1/integration/context/consume?token=<session_token>"
```

---

### GET /api/v1/integration/context/{session_id}

Check the status of a context session without consuming it. Only the owning client can query its own sessions.

**Auth:** Bearer token or API key | **Scope:** Any valid scope

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `session_id` | UUID | Session record UUID returned at creation |

**Response — 200 OK**

| Field | Type | Description |
|---|---|---|
| `session_id` | UUID string | Session UUID |
| `org_id` | UUID string \| null | Scoping organisation |
| `project_id` | UUID string \| null | Project restriction, if set |
| `is_consumed` | boolean | Whether the session has been consumed |
| `is_expired` | boolean | Whether the session TTL has elapsed |
| `expires_at` | ISO 8601 datetime | Expiry timestamp |
| `consumed_at` | ISO 8601 datetime \| null | When the session was consumed |
| `created_at` | ISO 8601 datetime | Creation timestamp |

**Errors**

| Code | HTTP | Description |
|---|---|---|
| `SESSION_NOT_FOUND` | 404 | Session does not exist or belongs to a different client |
| `ORG_MISMATCH` | 403 | Session's org_id does not match the authenticated client's org |

**curl example**

```bash
curl "https://api.riviwa.com/api/v1/integration/context/s1s2s3s4-0000-0000-0000-000000000001" \
  -H "Authorization: Bearer <access_token>"
```

---

## Widget & Mini App

Endpoints for embedding the Riviwa feedback widget as a JS tag on partner websites, or as a WebView within a partner mobile app. All widget sessions are automatically scoped to the client's bound `organisation_id`.

**Two embed modes:**

| Mode | Description |
|---|---|
| JS Widget / Tag | Partner includes a `<script>` tag; the JS SDK calls these APIs |
| Mini App / WebView | Partner mobile app opens a Riviwa WebView with an `embed_token` |

### Endpoint Summary

| Method | Path | Auth | Scope | Description |
|---|---|---|---|---|
| `POST` | `/api/v1/integration/widget/session` | Bearer / API Key | `feedback:write` | Create a widget/mini-app embed session |
| `GET` | `/api/v1/integration/widget/config` | None (origin-checked) | — | Widget JS fetches runtime config |
| `GET` | `/api/v1/integration/widget/snippet` | Bearer / API Key | Any | Get the copy-paste JS embed snippet |

---

### POST /api/v1/integration/widget/session

Create a widget or mini-app embed session. Returns an `embed_token` and a ready-to-use `embed_url`. The `embed_token` is **single-use** and expires after `ttl_seconds`.

**Auth:** Bearer token or API key | **Scope:** `feedback:write`

**Request Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `user_ref` | string | No | Partner's user ID / reference (opaque to Riviwa) |
| `project_id` | UUID string | No | Lock widget to a specific Riviwa project |
| `context_token` | string | No | Pre-existing context session token to merge |
| `ttl_seconds` | integer | No | Session TTL (default `1800`, max `7200`) |
| `locale` | string | No | UI locale hint, e.g. `"sw"` or `"en"` (default: `"en"`) |
| `theme` | string | No | `"light"` \| `"dark"` \| `"auto"` (default: `"light"`) |
| `org_id` | UUID string | No | Must match client's bound `organisation_id` if provided |

**Response — 201 Created**

| Field | Type | Description |
|---|---|---|
| `embed_token` | string | Single-use embed token |
| `session_id` | UUID string | Session record UUID |
| `org_id` | UUID string | Enforced organisation UUID |
| `project_id` | UUID string \| null | Project restriction, if set |
| `expires_at` | ISO 8601 datetime | Token expiry |
| `ttl_seconds` | integer | Effective TTL in seconds |
| `embed_url` | string | Ready-to-use URL for WebView: `https://widget.riviwa.com/embed?token=<token>&org=<org_id>` |
| `warning` | string | Reminder that `embed_token` is single-use |

**Errors**

| Code | HTTP | Description |
|---|---|---|
| `ORG_MISMATCH` | 403 | Provided `org_id` does not match client's bound organisation |

**curl example**

```bash
curl -X POST https://api.riviwa.com/api/v1/integration/widget/session \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_ref": "ACME-USER-00456",
    "project_id": "p1p2p3p4-0000-0000-0000-000000000001",
    "ttl_seconds": 1800,
    "locale": "sw",
    "theme": "light"
  }'
```

---

### GET /api/v1/integration/widget/config

Called by the embedded JS widget to fetch runtime configuration. The server validates the `Origin` header against the client's `allowed_origins` list. Optionally decrypts and returns pre-fill data from a context session token.

**Auth:** None — origin validated against `allowed_origins`

**Query Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `client_id` | string | Yes | The partner's `client_id` |
| `token` | string | No | A context session token for pre-fill data |

**Response — 200 OK** (with CORS headers)

| Field | Type | Description |
|---|---|---|
| `client_id` | string | Partner client identifier |
| `client_name` | string | Partner display name |
| `environment` | string | `LIVE` or `SANDBOX` |
| `org_id` | UUID string \| null | Scoping organisation (authoritative) |
| `scopes` | array | Client's allowed scopes |
| `require_auth` | boolean | Whether `feedback:write` is in scopes |
| `pre_fill` | object | Pre-fill data from context session (if `token` valid) |
| `project_id` | UUID string | Present if session restricts to a project |

**Response headers**

| Header | Value |
|---|---|
| `Access-Control-Allow-Origin` | The request's `Origin` value |
| `Access-Control-Allow-Credentials` | `true` |
| `Vary` | `Origin` |

**Errors**

| Code | HTTP | Description |
|---|---|---|
| `CLIENT_NOT_FOUND` | 404 | Unknown or inactive `client_id` |
| `ORIGIN_NOT_ALLOWED` | 403 | Request `Origin` not in `allowed_origins` |

**curl example**

```bash
curl "https://api.riviwa.com/api/v1/integration/widget/config?client_id=rwi_client_abc123&token=<session_token>" \
  -H "Origin: https://www.acmebank.com"
```

---

### GET /api/v1/integration/widget/snippet

Returns the copy-paste `<script>` tag snippet for website embedding. The snippet bakes in the `org_id` so every page view is automatically scoped to the correct organisation.

**Auth:** Bearer token or API key | **Scope:** Any valid scope

**Query Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `client_id` | string | Yes | The partner's `client_id` |

**Response — 200 OK**

| Field | Type | Description |
|---|---|---|
| `client_id` | string | Partner client identifier |
| `org_id` | UUID string | Bound organisation UUID |
| `snippet` | string | Complete HTML `<script>` tag to paste into the partner's website |
| `widget_js` | string | URL of the Riviwa widget JS bundle |
| `docs_url` | string | Link to widget documentation |

**Errors**

| Code | HTTP | Description |
|---|---|---|
| `CLIENT_NOT_FOUND` | 404 | Unknown, inactive, or mismatched client |

**curl example**

```bash
curl "https://api.riviwa.com/api/v1/integration/widget/snippet?client_id=rwi_client_abc123" \
  -H "Authorization: Bearer <access_token>"
```

**Sample snippet output**

```html
<!-- Riviwa Feedback Widget -->
<script>
  (function(r,i,v,i2,w,a){r['RiviwaObject']=w;r[w]=r[w]||function(){}
  ;(r[w].q=r[w].q||[]).push(arguments)},r[w].l=1*new Date();a=i.createElement(v),
  m=i.getElementsByTagName(v)[0];a.async=1;a.src=i2;m.parentNode.insertBefore(a,m)
  })(window,document,'script','https://widget.riviwa.com/widget.js','riviwa');
  riviwa('init', 'rwi_client_abc123', {org: 'a1b2c3d4-0000-0000-0000-000000000001'});
  riviwa('track', 'page_view');
</script>
<!-- End Riviwa Feedback Widget -->
```

---

## Webhooks

Riviwa delivers outbound webhook events to the partner's configured `webhook_url` when feedback lifecycle events occur. Every delivery is signed so partners can verify authenticity.

### Signature Verification

Each delivery includes these headers:

| Header | Description |
|---|---|
| `X-Riviwa-Signature` | `sha256=<HMAC-SHA256(timestamp + "." + body_bytes, signing_secret)>` |
| `X-Riviwa-Timestamp` | Unix timestamp of the delivery |
| `X-Riviwa-Event` | Event type, e.g. `feedback.submitted` |
| `X-Riviwa-Delivery` | UUID identifying this delivery attempt |
| `User-Agent` | `Riviwa-Webhook/1.0` |

**Verification example (Python)**

```python
import hmac
import hashlib

def verify_signature(body: bytes, timestamp: str, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        msg=(timestamp + "." + body.decode()).encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

### Retry Policy

| Attempt | Delay |
|---|---|
| 1st retry | 30 seconds |
| 2nd retry | 5 minutes |
| 3rd retry | 30 minutes |
| After 3 failures | Status set to `FAILED` — no further automatic retries |

Use the manual retry endpoint to re-trigger failed deliveries.

### Endpoint Summary

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/integration/webhooks/test` | Bearer / API Key | Send a test delivery to the webhook URL |
| `POST` | `/api/v1/integration/webhooks/rotate-secret` | Bearer / API Key | Rotate the webhook signing secret |
| `GET` | `/api/v1/integration/webhooks/deliveries` | Bearer / API Key | List delivery history |
| `GET` | `/api/v1/integration/webhooks/deliveries/{id}` | Bearer / API Key | Get a single delivery with payload |
| `POST` | `/api/v1/integration/webhooks/deliveries/{id}/retry` | Bearer / API Key | Manually retry a failed delivery |

---

### POST /api/v1/integration/webhooks/test

Send a test webhook delivery to the client's configured `webhook_url`. Useful for verifying connectivity and signature validation logic. Test deliveries use a temporary signing key — use `rotate-secret` to obtain a production signing secret.

**Auth:** Bearer token or API key

**Request Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `event_type` | string | No | Event type to simulate (default: `feedback.submitted`) |
| `payload` | object | No | Custom payload dict. Defaults to a sample payload. |

**Response — 200 OK**

| Field | Type | Description |
|---|---|---|
| `delivery_id` | UUID string | Delivery identifier |
| `webhook_url` | string | URL the delivery was sent to |
| `event_type` | string | Simulated event type |
| `success` | boolean | Whether the partner endpoint returned 2xx |
| `status_code` | integer \| null | HTTP status code from the partner endpoint |
| `error` | string \| null | Error message if delivery failed (`TIMEOUT`, etc.) |
| `note` | string | Advisory about test signing keys |

**Errors**

| Code | HTTP | Description |
|---|---|---|
| `NO_WEBHOOK_URL` | 400 | Client has no `webhook_url` configured |

**curl example**

```bash
curl -X POST https://api.riviwa.com/api/v1/integration/webhooks/test \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "feedback.resolved",
    "payload": {"test": true, "custom_field": "hello"}
  }'
```

---

### POST /api/v1/integration/webhooks/rotate-secret

Rotate the webhook HMAC signing secret. The new raw secret is returned **once** — store it immediately and update your signature verification logic.

**Auth:** Bearer token or API key

**Request Body:** None

**Response — 200 OK**

| Field | Type | Description |
|---|---|---|
| `webhook_signing_secret` | string | New raw HMAC signing secret — **shown once** |
| `warning` | string | Advisory to store securely and update signature verification |

**curl example**

```bash
curl -X POST https://api.riviwa.com/api/v1/integration/webhooks/rotate-secret \
  -H "Authorization: Bearer <access_token>"
```

---

### GET /api/v1/integration/webhooks/deliveries

List webhook delivery history for the authenticated client.

**Auth:** Bearer token or API key

**Query Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `event_type` | string | No | Filter by event type (e.g. `feedback.submitted`) |
| `status_filter` | string | No | Filter by status: `PENDING` \| `DELIVERED` \| `FAILED` \| `RETRYING` |
| `limit` | integer | No | Maximum results to return (default: `50`) |
| `offset` | integer | No | Pagination offset (default: `0`) |

**Response — 200 OK**

| Field | Type | Description |
|---|---|---|
| `total` | integer | Total matching records |
| `limit` | integer | Applied limit |
| `offset` | integer | Applied offset |
| `items` | array | Array of delivery summary objects |

Each delivery summary:

| Field | Type | Description |
|---|---|---|
| `id` | UUID string | Delivery record UUID |
| `event_type` | string | Webhook event type |
| `status` | string | `PENDING` \| `DELIVERED` \| `FAILED` \| `RETRYING` |
| `attempt_count` | integer | Number of delivery attempts made |
| `last_status_code` | integer \| null | HTTP status code from last attempt |
| `last_error` | string \| null | Error from last failed attempt |
| `next_retry_at` | ISO 8601 datetime \| null | Scheduled retry time |
| `delivered_at` | ISO 8601 datetime \| null | Successful delivery timestamp |
| `failed_at` | ISO 8601 datetime \| null | Final failure timestamp |
| `created_at` | ISO 8601 datetime | When the delivery was enqueued |

**curl example**

```bash
curl "https://api.riviwa.com/api/v1/integration/webhooks/deliveries?status_filter=FAILED&limit=20" \
  -H "Authorization: Bearer <access_token>"
```

---

### GET /api/v1/integration/webhooks/deliveries/{id}

Retrieve a single delivery record including the full payload.

**Auth:** Bearer token or API key

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | UUID | Delivery record UUID |

**Response — 200 OK**

Same fields as the delivery summary, plus:

| Field | Type | Description |
|---|---|---|
| `payload` | object | Full webhook payload that was sent |

**Errors**

| Code | HTTP | Description |
|---|---|---|
| `DELIVERY_NOT_FOUND` | 404 | Delivery does not exist or belongs to a different client |

**curl example**

```bash
curl "https://api.riviwa.com/api/v1/integration/webhooks/deliveries/d1d2d3d4-0000-0000-0000-000000000001" \
  -H "Authorization: Bearer <access_token>"
```

---

### POST /api/v1/integration/webhooks/deliveries/{id}/retry

Manually trigger a retry for a failed delivery. Only available when `status` is `FAILED` or `RETRYING` and `attempt_count < 10`.

**Auth:** Bearer token or API key

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `id` | UUID | Delivery record UUID |

**Request Body:** None

**Response — 200 OK**

| Field | Type | Description |
|---|---|---|
| `status` | string | `"queued"` — delivery has been queued for immediate retry |
| `delivery_id` | UUID string | Delivery record UUID |

**Errors**

| Code | HTTP | Description |
|---|---|---|
| `DELIVERY_NOT_FOUND` | 404 | Delivery does not exist or belongs to a different client |
| `CANNOT_RETRY` | 400 | Delivery status is not `FAILED` or `RETRYING` |
| `MAX_RETRIES_EXCEEDED` | 400 | `attempt_count` has reached the maximum of 10 |

**curl example**

```bash
curl -X POST "https://api.riviwa.com/api/v1/integration/webhooks/deliveries/d1d2d3d4-0000-0000-0000-000000000001/retry" \
  -H "Authorization: Bearer <access_token>"
```

---

## Feedback Bridge

The Feedback Bridge allows partner servers and embedded widgets to submit feedback (grievances, suggestions, applauses, and inquiries) on behalf of their users, scoped to the client's bound organisation.

**Submission flow:**

```
1. Partner server → POST /integration/feedback   { feedback_type, title, phone, ... }
2. Integration service validates scope + org
3. (Optional) Merges context session pre-fill data
4. (Optional) Fetches enrichment from partner's data_endpoint_url
5. Forwards enriched payload → feedback_service (internal)
6. Fires webhook to partner (feedback.submitted)
7. Returns { feedback_id, reference, status }
```

### Endpoint Summary

| Method | Path | Auth | Scope | Description |
|---|---|---|---|---|
| `POST` | `/api/v1/integration/feedback` | Bearer / API Key | `feedback:write` | Submit feedback on behalf of a user |
| `GET` | `/api/v1/integration/feedback/{feedback_id}` | Bearer / API Key | `feedback:read` | Check feedback status |

---

### POST /api/v1/integration/feedback

Submit feedback through a partner integration. The `org_id` is always derived from the client registration and cannot be overridden.

**Auth:** Bearer token or API key | **Scope:** `feedback:write`

**Request Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `feedback_type` | string | Yes | `GRIEVANCE` \| `SUGGESTION` \| `APPLAUSE` \| `INQUIRY` |
| `title` | string | Yes | Short description of the feedback |
| `description` | string | No | Full description. Defaults to `title` if omitted. |
| `category_id` | UUID string | No | Riviwa feedback category UUID |
| `department_id` | UUID string | No | Riviwa department UUID |
| `project_id` | UUID string | No | Riviwa project UUID (defaults to client's configured project) |
| `priority` | string | No | `LOW` \| `MEDIUM` \| `HIGH` (default: `MEDIUM`) |
| `channel` | string | No | Submission channel hint: `MOBILE_APP` \| `WEB_WIDGET` \| `CHATBOT` \| `api` etc. (default: `api`) |
| `phone` | string | No* | Submitter's phone number |
| `name` | string | No* | Submitter's full name |
| `email` | string | No* | Submitter's email address |
| `account_ref` | string | No* | Partner's internal customer/account reference |
| `context_token` | string | No | Context session token — merges pre-filled data and consumes the session |
| `enrich_from_endpoint` | boolean | No | If `true` and `data_endpoint_url` is configured, fetches additional context from the partner endpoint |
| `source_ref` | string | No | Partner's internal reference for this submission (passed through as-is) |
| `metadata` | object | No | Freeform metadata passed through to feedback_service |

*At least one of `phone`, `name`, `email`, or `account_ref` is required — unless a valid `context_token` is provided that contains one of these fields.

**Response — 201 Created**

| Field | Type | Description |
|---|---|---|
| `feedback_id` | UUID string | Riviwa feedback record UUID |
| `reference` | string | Human-readable feedback reference (e.g. `GRM-2026-00123`) |
| `org_id` | UUID string | Organisation the feedback was submitted to |
| `feedback_type` | string | Normalised feedback type |
| `status` | string | Initial status (typically `SUBMITTED`) |
| `submitted_at` | ISO 8601 datetime | Submission timestamp |
| `webhook_queued` | boolean | Whether a `feedback.submitted` webhook was enqueued |

**Errors**

| Code | HTTP | Description |
|---|---|---|
| `INVALID_FEEDBACK_TYPE` | 400 | `feedback_type` is not one of the allowed values |
| `TITLE_REQUIRED` | 400 | `title` is empty or missing |
| `SUBMITTER_IDENTITY_REQUIRED` | 400 | No user identity provided and no valid `context_token` with identity data |
| `CONTEXT_SESSION_EXPIRED` | 410 | The provided `context_token` has expired |
| `CONTEXT_SESSION_ORG_MISMATCH` | 403 | Context session belongs to a different organisation |
| `ORG_MISMATCH` | 403 | Provided `org_id` does not match client's bound organisation |
| `FEEDBACK_SERVICE_ERROR` | 502 | Feedback service returned an unexpected error |
| `FEEDBACK_SERVICE_UNAVAILABLE` | 503 | Could not reach the feedback service |

**curl example**

```bash
curl -X POST https://api.riviwa.com/api/v1/integration/feedback \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "feedback_type": "GRIEVANCE",
    "title": "Water supply interrupted for 3 days",
    "description": "Our community has had no water supply since Monday morning.",
    "category_id": "c1c2c3c4-0000-0000-0000-000000000001",
    "project_id": "p1p2p3p4-0000-0000-0000-000000000001",
    "priority": "HIGH",
    "channel": "MOBILE_APP",
    "phone": "+255712345678",
    "name": "Jane Doe",
    "account_ref": "ACME-ACC-00123",
    "source_ref": "APP-TKT-00789"
  }'
```

**curl example with context session**

```bash
curl -X POST https://api.riviwa.com/api/v1/integration/feedback \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "feedback_type": "SUGGESTION",
    "title": "Add more payment options",
    "context_token": "<session_token_from_POST_context>",
    "enrich_from_endpoint": true
  }'
```

---

### GET /api/v1/integration/feedback/{feedback_id}

Retrieve the current status of a previously submitted feedback item. The integration service fetches this from `feedback_service` in real-time.

**Auth:** Bearer token or API key | **Scope:** `feedback:read`

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `feedback_id` | UUID | Riviwa feedback record UUID returned at submission |

**Response — 200 OK**

| Field | Type | Description |
|---|---|---|
| `feedback_id` | UUID string | Riviwa feedback UUID |
| `reference` | string | Human-readable reference |
| `org_id` | UUID string | Organisation UUID |
| `project_id` | UUID string \| null | Project UUID |
| `feedback_type` | string | Feedback type |
| `status` | string | Current lifecycle status (e.g. `SUBMITTED`, `ACKNOWLEDGED`, `IN_REVIEW`, `RESOLVED`, `CLOSED`) |
| `priority` | string | Priority level |
| `title` | string | Feedback subject |
| `submitted_at` | ISO 8601 datetime | Submission timestamp |
| `updated_at` | ISO 8601 datetime | Last update timestamp |

**Errors**

| Code | HTTP | Description |
|---|---|---|
| `FEEDBACK_NOT_FOUND` | 404 | No feedback with that UUID |
| `FEEDBACK_SERVICE_ERROR` | 502 | Feedback service returned unexpected error |
| `FEEDBACK_SERVICE_UNAVAILABLE` | 502 | Could not reach the feedback service |

**curl example**

```bash
curl "https://api.riviwa.com/api/v1/integration/feedback/f1f2f3f4-0000-0000-0000-000000000001" \
  -H "Authorization: Bearer <access_token>"
```

---

## Data Models

### ClientType

| Value | Description |
|---|---|
| `API` | Direct server-to-server API integration (default) |
| `MINI_APP` | Embedded mini-app within a partner's mobile application |
| `WEB_WIDGET` | JavaScript widget / script tag on a partner website |
| `SDK` | Official Riviwa SDK (React Native / Flutter) |
| `CHATBOT` | AI chatbot integration (analogous to a Google Tag embed) |

---

### ClientEnvironment

| Value | Description |
|---|---|
| `LIVE` | Production environment — real data |
| `SANDBOX` | Testing/staging — isolated from production |

---

### FeedbackType

| Value | Description |
|---|---|
| `GRIEVANCE` | A complaint or formal grievance |
| `SUGGESTION` | A constructive suggestion or improvement request |
| `APPLAUSE` | Positive feedback / commendation |
| `INQUIRY` | An information request or question |

---

### DeliveryStatus

| Value | Description |
|---|---|
| `PENDING` | Delivery enqueued, not yet attempted |
| `DELIVERED` | Partner endpoint returned 2xx |
| `FAILED` | All retry attempts exhausted — final failure |
| `RETRYING` | Delivery failed; scheduled for retry |

---

### WebhookEventType

| Value | Description |
|---|---|
| `feedback.submitted` | New feedback has been submitted |
| `feedback.acknowledged` | Feedback acknowledged by a handler |
| `feedback.in_review` | Feedback is actively under review |
| `feedback.escalated` | Feedback has been escalated |
| `feedback.resolved` | Feedback has been resolved |
| `feedback.closed` | Feedback case is closed |
| `feedback.dismissed` | Feedback was dismissed |

---

### TokenGrantType

| Value | Description |
|---|---|
| `AUTHORIZATION_CODE` | Issued via PKCE Authorization Code flow |
| `CLIENT_CREDENTIALS` | Issued via machine-to-machine Client Credentials flow |
| `REFRESH_TOKEN` | Issued via Refresh Token rotation |

---

### OAuth2 Scopes

| Scope | Required by |
|---|---|
| `feedback:write` | `POST /integration/feedback`, `POST /integration/widget/session`, `POST /integration/context` |
| `feedback:read` | `GET /integration/feedback/{id}` |
| `profile:read` | `GET /integration/oauth/userinfo` |
| `data:push` | `POST /integration/context` |

---

### Access Token JWT Claims

| Claim | Type | Description |
|---|---|---|
| `iss` | string | Always `https://riviwa.com` |
| `sub` | string | User UUID (Authorization Code flow) or client UUID (Client Credentials) |
| `aud` | string | The `client_id` of the requesting client |
| `jti` | string | Unique JWT ID — used for revocation |
| `exp` | integer | Unix timestamp — expiry |
| `iat` | integer | Unix timestamp — issued at |
| `client_id` | string | Issuing client's `client_id` |
| `scopes` | array | Granted scopes |
| `env` | string | `LIVE` or `SANDBOX` |
| `user_id` | string | Present when issued via Authorization Code flow |
| `org_id` | string | Present when client has a bound `organisation_id` |

---

## Error Reference

All error responses use JSON bodies. Field-level and business errors use the following structure:

```json
{"error": "ERROR_CODE"}
```

or with additional context:

```json
{"error": "ERROR_CODE", "message": "Human-readable description", "detail": {...}}
```

### Complete Error Code Table

| Code | HTTP | Section | Description |
|---|---|---|---|
| `MISSING_TOKEN` | 401 | Client Management | No `Authorization` header present |
| `TOKEN_EXPIRED` | 401 | Client Management | Platform admin JWT has expired |
| `INVALID_TOKEN` | 401 | Client Management / OAuth2 | JWT signature is invalid |
| `INSUFFICIENT_ROLE` | 403 | Client Management | Caller's `platform_role` is not `admin` or `super_admin` |
| `CLIENT_NOT_FOUND` | 404 | Client Management / Widget | No active client matches the identifier |
| `KEY_NOT_FOUND` | 404 | Client Management | API key not found or does not belong to client |
| `INVALID_SCOPES` | 400 | Client Management | Requested scopes are outside the client's `allowed_scopes` |
| `invalid_client` | 401 | OAuth2 | Unknown client, inactive client, or wrong `client_secret` |
| `invalid_grant` | 400 | OAuth2 | Code expired, already used, `redirect_uri` mismatch, PKCE failure, or refresh token invalid |
| `invalid_scope` | 400 | OAuth2 | Requested scope exceeds client's allowed scopes |
| `invalid_request` | 400 | OAuth2 | Missing required parameter |
| `unsupported_grant_type` | 400 | OAuth2 | Grant type not in `["authorization_code","client_credentials","refresh_token"]` |
| `unsupported_response_type` | 400 | OAuth2 | `response_type` must be `code` |
| `code_challenge_required` | 400 | OAuth2 | PKCE is mandatory — `code_challenge` missing |
| `invalid_code_challenge_method` | 400 | OAuth2 | Only `S256` and `plain` are supported |
| `invalid_redirect_uri` | 400 | OAuth2 | `redirect_uri` not in client's registered list |
| `missing_token` | 401 | OAuth2 | No Authorization header on userinfo request |
| `insufficient_scope` | 403 | OAuth2 | Token does not carry `profile:read` scope |
| `MISSING_CONTEXT_DATA` | 400 | Context Sessions | None of `phone`, `name`, `email`, `account_ref` were provided |
| `SESSION_NOT_FOUND` | 404 | Context Sessions | Token is invalid, already consumed, or does not exist |
| `SESSION_EXPIRED` | 410 | Context Sessions | Context session TTL has elapsed |
| `DECRYPTION_FAILED` | 500 | Context Sessions | Internal AES-256-GCM decryption error |
| `ORG_MISMATCH` | 403 | Context / Widget / Feedback | Provided `org_id` does not match client's bound organisation |
| `ORIGIN_NOT_ALLOWED` | 403 | Widget | Request `Origin` not in client's `allowed_origins` |
| `INVALID_FEEDBACK_TYPE` | 400 | Feedback Bridge | `feedback_type` is not `GRIEVANCE`, `SUGGESTION`, `APPLAUSE`, or `INQUIRY` |
| `TITLE_REQUIRED` | 400 | Feedback Bridge | `title` field is empty or missing |
| `SUBMITTER_IDENTITY_REQUIRED` | 400 | Feedback Bridge | No user identity provided and no valid `context_token` with identity data |
| `CONTEXT_SESSION_EXPIRED` | 410 | Feedback Bridge | The supplied `context_token` has expired |
| `CONTEXT_SESSION_ORG_MISMATCH` | 403 | Feedback Bridge | Context session belongs to a different organisation |
| `FEEDBACK_NOT_FOUND` | 404 | Feedback Bridge | Feedback item not found in `feedback_service` |
| `FEEDBACK_SERVICE_ERROR` | 502 | Feedback Bridge | `feedback_service` returned an unexpected HTTP status |
| `FEEDBACK_SERVICE_UNAVAILABLE` | 503 | Feedback Bridge | Could not connect to `feedback_service` |
| `NO_WEBHOOK_URL` | 400 | Webhooks | Client has no `webhook_url` configured |
| `DELIVERY_NOT_FOUND` | 404 | Webhooks | Delivery record not found or belongs to a different client |
| `CANNOT_RETRY` | 400 | Webhooks | Delivery is not in `FAILED` or `RETRYING` state |
| `MAX_RETRIES_EXCEEDED` | 400 | Webhooks | `attempt_count` has reached the limit of 10 |

---

*Generated from source — integration_service v1 · Riviwa Platform*
