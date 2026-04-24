# Integration Service — Engineering Deep Dive

> **Author:** Riviwa Engineering  
> **Date:** April 2026  
> **Service:** `integration_service` · Port `8100` · DB `integration_db` (port 5442)  
> **Codebase:** `integration_service/` — FastAPI, SQLModel, asyncpg, Redis, APScheduler

---

## Table of Contents

1. [Why a Separate Service?](#1-why-a-separate-service)
2. [Architecture Overview](#2-architecture-overview)
3. [Data Model Design](#3-data-model-design)
4. [Security Architecture](#4-security-architecture)
5. [OAuth2 Server Implementation](#5-oauth2-server-implementation)
6. [Organisation Scoping — The Core Invariant](#6-organisation-scoping--the-core-invariant)
7. [Context Sessions — Encrypted Pre-fill](#7-context-sessions--encrypted-pre-fill)
8. [Webhook Engine](#8-webhook-engine)
9. [Feedback Bridge — Internal Service Protocol](#9-feedback-bridge--internal-service-protocol)
10. [Rate Limiting with Redis](#10-rate-limiting-with-redis)
11. [Audit Logging Middleware](#11-audit-logging-middleware)
12. [Database Migration Strategy](#12-database-migration-strategy)
13. [Deployment and Docker Compose Integration](#13-deployment-and-docker-compose-integration)
14. [Key Engineering Decisions](#14-key-engineering-decisions)
15. [Known Limitations and Future Work](#15-known-limitations-and-future-work)

---

## 1. Why a Separate Service?

Before building, we evaluated two approaches:

### Option A — Extend the auth_service
Add OAuth2 client management and API key endpoints directly to the existing `riviwa_auth_service`.

**Rejected because:**
- `auth_service` already owns user identity, JWT signing, OTP, and fraud detection. Adding partner management would couple two very different domains (user auth vs third-party API access) in a single service.
- Partner clients have completely different rate limits, scopes, and audit requirements from user sessions.
- A security incident in partner key management should not risk exposure of user credentials.

### Option B — New isolated microservice ✅
A dedicated `integration_service` with its own database (`integration_db`), Redis namespace (DB 7), and port (8100).

**Chosen because:**
- **Blast radius isolation:** A compromised partner API key cannot access user passwords, OTP secrets, or internal JWT signing keys.
- **Independent scaling:** High-volume integrations (bank mini-apps) can be scaled without touching user auth.
- **Clean API surface:** Vendors interact with one service on one port — no routing confusion.
- **Audit separation:** Partner audit logs are in `integration_audit_logs`, not mixed with user auth logs.

### The cross-service trust model

```
┌──────────────────────┐     JWT (shared SECRET_KEY)    ┌──────────────────────┐
│   riviwa_auth_service│ ◄───────────────────────────── │  integration_service │
│   (port 8000)        │                                 │  (port 8100)         │
│                      │ ────X-Service-Key──────────────►│                      │
└──────────────────────┘                                 └──────────────────────┘
                                                                    │ X-Service-Key
                                                                    ▼
                                                         ┌──────────────────────┐
                                                         │   feedback_service   │
                                                         │   (port 8090)        │
                                                         └──────────────────────┘
```

- `integration_service` **verifies** JWTs using the shared `AUTH_SECRET_KEY` — it never signs them for user sessions
- `integration_service` **issues** OAuth2 access tokens that embed `org_id` and `scopes`
- `integration_service` calls `feedback_service` internal endpoints using `X-Service-Key` (no JWT needed for internal calls)

---

## 2. Architecture Overview

```
integration_service/
│
├── api/v1/
│   ├── clients.py        # Partner client CRUD + API key management
│   ├── oauth.py          # OAuth2 AS: authorize, token, revoke, introspect, userinfo
│   ├── context.py        # Context sessions (pre-fill data push)
│   ├── widget.py         # Widget/mini-app embed sessions + JS snippet
│   ├── webhooks.py       # Webhook management + delivery history
│   └── feedback_bridge.py # Feedback submission + status check
│
├── core/
│   ├── config.py         # Pydantic-settings (reads .env / env vars)
│   ├── auth.py           # FastAPI auth dependency (AuthContext + org enforcement)
│   └── security.py       # Crypto helpers (API keys, bcrypt, HMAC, AES-256-GCM)
│
├── models/
│   └── integration.py    # 7 SQLModel table definitions
│
├── services/
│   ├── webhook_worker.py # APScheduler delivery engine
│   └── data_bridge.py    # External data fetch from partner endpoint
│
├── db/
│   └── session.py        # Async SQLAlchemy engine + session factory
│
├── alembic/              # DB migrations
├── main.py               # FastAPI app, lifespan, audit middleware
├── Dockerfile            # Multi-stage build
├── entrypoint.sh         # Wait-for-DB → alembic upgrade → uvicorn
└── requirements.txt
```

### Request lifecycle

```
Client Request
    │
    ▼
nginx (/api/v1/integration/* → integration_service:8100)
    │
    ▼
FastAPI middleware (audit_log_middleware)
    │  records: method, path, status_code, duration_ms, ip, user_agent
    ▼
Route handler
    │
    ├── require_integration_auth() [Depends]
    │     ├── X-API-Key header → _auth_by_api_key() → SHA-256 lookup in DB
    │     └── Authorization: Bearer → _auth_by_bearer() → JWT decode + JTI DB check
    │           └── IP allowlist check
    │           └── Redis rate limit check (sliding window)
    │
    ▼
AuthContext { client, scopes, org_id, user_id, auth_method }
    │
    ▼
Business logic (validate org, encrypt/decrypt, call downstream services)
    │
    ▼
Response + async audit log commit
```

---

## 3. Data Model Design

### Why 7 tables?

Each table owns exactly one concern. We deliberately avoided combining related data (e.g., putting API keys inside the `IntegrationClient` row as a JSONB array) to maintain clean foreign-key relationships and allow efficient indexed lookups.

```
integration_clients          — the registered partner (1 client per integration)
        │
        ├── integration_api_keys       — API keys (N per client, hashed)
        ├── oauth_authorization_codes  — PKCE auth codes (short-lived, single-use)
        ├── oauth_tokens               — issued access + refresh tokens
        ├── context_sessions           — pre-fill data sessions (encrypted)
        ├── webhook_deliveries         — outbound delivery log with retry state
        └── integration_audit_logs     — immutable request audit trail
```

### IntegrationClient — the central entity

```python
class IntegrationClient(SQLModel, table=True):
    __tablename__ = "integration_clients"

    id:                 uuid.UUID          # Internal PK (never shown to partner)
    client_id:          str                # Public identifier: rwi_client_xxx
    client_secret_hash: str                # bcrypt hash (shown ONCE at creation)
    name:               str
    client_type:        ClientType         # MINI_APP | WEB_WIDGET | API | SDK | CHATBOT
    environment:        ClientEnvironment  # LIVE | SANDBOX
    organisation_id:    Optional[uuid.UUID]  # Soft FK to auth_db
    allowed_scopes:     List[str]          # JSONB
    allowed_origins:    List[str]          # CORS allowlist
    allowed_ips:        List[str]          # IP allowlist (empty = all allowed)
    redirect_uris:      List[str]          # OAuth2 redirect URIs
    webhook_url:        Optional[str]
    webhook_secret_hash: Optional[str]     # bcrypt hash of HMAC signing secret
    webhook_events:     List[str]          # subscribed event types
    data_endpoint_url:  Optional[str]      # partner's data API (for bridge mode)
    data_endpoint_auth_enc: Optional[str]  # AES-256-GCM encrypted credential
    rate_limit_per_minute: int
    rate_limit_per_day:    int
    require_mtls:       bool
    mtls_cert_fingerprint: Optional[str]
    is_active:          bool
    ...
```

**Design decisions:**

1. **`organisation_id` as a soft FK:** The organisation lives in `auth_db` (a separate PostgreSQL database). We store the UUID directly without a foreign key constraint — this is the standard cross-microservice reference pattern in the Riviwa platform. Validity is enforced at the application layer when needed.

2. **JSONB for lists:** `allowed_scopes`, `allowed_origins`, `allowed_ips`, `webhook_events` are stored as PostgreSQL JSONB arrays. This avoids normalisation tables for simple lists that are always read/written together with the parent row.

3. **`client_type` stored as VARCHAR(32), not a native PG enum:** SQLAlchemy can auto-infer a PostgreSQL native enum from a Python `str, Enum` field. We explicitly override with `sa_column=Column(String(32))` to keep the DB column as a plain VARCHAR. This makes migrations simpler (no `ALTER TYPE ... ADD VALUE` for new client types) and avoids the `::clienttype` cast issues we encountered during development.

4. **Sensitive fields encrypted at rest:** `data_endpoint_auth_enc` stores the partner's API credential for the data bridge. It's AES-256-GCM encrypted before storage using a key from `settings.ENCRYPTION_KEY` (separate from the JWT signing key). Even if an attacker dumps the database, they cannot use the credential without the encryption key.

### ApiKey — hashed, never stored in plain text

```python
class ApiKey(SQLModel, table=True):
    id:         uuid.UUID
    client_id:  uuid.UUID          # FK to integration_clients
    key_prefix: str                # First 12 chars — safe to display (e.g. rwi_sandbox_)
    key_hash:   str                # SHA-256 of full key — unique index
    scopes:     List[str]          # Subset of client's allowed_scopes
    expires_at: Optional[datetime]
    revoked_at: Optional[datetime]
```

**Why SHA-256 for API keys but bcrypt for client secrets?**

- **API keys** are looked up on every request. bcrypt is intentionally slow (cost 12 = ~250ms). For high-throughput API key auth, a 250ms hash check per request would be unacceptable. SHA-256 is cryptographically secure for random high-entropy keys and runs in microseconds.
- **Client secrets** are only checked during token exchange (low frequency). bcrypt's slowness is a feature — it makes brute-force attacks against a leaked database impractical.

**API key format:** `rwi_<env>_<48_chars_base64url>`

```python
def generate_api_key(environment: str = "SANDBOX") -> Tuple[str, str, str]:
    env_tag    = {"LIVE": "live", "SANDBOX": "sandbox"}.get(environment, "sandbox")
    random_part = secrets.token_urlsafe(36)   # 36 bytes → 48 base64url chars
    full_key   = f"rwi_{env_tag}_{random_part}"
    prefix     = full_key[:12]                # e.g. "rwi_sandbox_"
    key_hash   = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, prefix, key_hash
```

The `key_prefix` is the first 12 characters. When displayed in the admin panel (e.g. listing a client's API keys), we show the prefix so the user can identify which key is which without revealing the full key.

### OAuthAuthorizationCode — PKCE codes

```python
class OAuthAuthorizationCode(SQLModel, table=True):
    code_hash:             str       # SHA-256 of the raw code
    code_challenge:        str       # PKCE challenge (S256 or plain)
    code_challenge_method: str
    redirect_uri:          str
    scopes:                List[str]
    user_id:               Optional[uuid.UUID]
    expires_at:            datetime  # 10 minutes
    used_at:               Optional[datetime]  # set on first use
```

The authorization code itself is **never stored** — only its SHA-256 hash. When the client exchanges the code, we hash the incoming code and compare against the stored hash. Setting `used_at` on first use makes the code single-use.

### OAuthToken — access + refresh tokens

```python
class OAuthToken(SQLModel, table=True):
    jti:                str       # JWT ID — used for revocation checks
    client_id:          uuid.UUID
    user_id:            Optional[uuid.UUID]
    grant_type:         TokenGrantType
    scopes:             List[str]
    refresh_token_hash: Optional[str]  # SHA-256 of opaque refresh token
    refresh_expires_at: Optional[datetime]
    expires_at:         datetime
    revoked_at:         Optional[datetime]
```

**JTI (JWT ID) is the revocation key.** Every issued JWT contains a `jti` claim. On the introspect and revoke endpoints, we look up by `jti`. If `revoked_at IS NOT NULL`, the token is treated as invalid regardless of the JWT signature being valid. This is the standard pattern for stateful JWT revocation without short TTLs being a security requirement.

### ContextSession — encrypted pre-fill

```python
class ContextSession(SQLModel, table=True):
    token_hash:          str       # SHA-256 of opaque session token
    pre_filled_data_enc: str       # AES-256-GCM (Fernet) encrypted JSON
    project_id:          Optional[uuid.UUID]
    org_id:              Optional[uuid.UUID]
    expires_at:          datetime
    consumed_at:         Optional[datetime]  # set on first consumption
```

The session token shown to the partner is an opaque random string. We store only its hash (same pattern as API keys). The pre-fill data is encrypted at rest — the payload could contain PII (phone numbers, names, account references). Even if someone queries the `context_sessions` table directly, they cannot read the pre-fill data without the encryption key.

### WebhookDelivery — delivery log

```python
class WebhookDelivery(SQLModel, table=True):
    event_type:      str
    payload:         Dict[str, Any]  # JSONB
    status:          DeliveryStatus  # PENDING | RETRYING | DELIVERED | FAILED
    attempt_count:   int
    last_status_code: Optional[int]
    last_error:      Optional[str]
    next_retry_at:   Optional[datetime]  # indexed — scheduler polls this
    delivered_at:    Optional[datetime]
    failed_at:       Optional[datetime]
```

The `next_retry_at` index is the most performance-critical index in the service. The webhook scheduler runs every 15 seconds and queries:

```sql
SELECT * FROM webhook_deliveries
WHERE status IN ('PENDING', 'RETRYING')
  AND next_retry_at <= NOW()
ORDER BY created_at
LIMIT 50;
```

Without the index on `next_retry_at`, this query would do a full table scan on every poll cycle.

---

## 4. Security Architecture

### Four layers of security

```
Layer 1 — Transport:   HTTPS (nginx TLS termination), optional mTLS for enterprise
Layer 2 — Auth:        API key (SHA-256) or Bearer JWT (HMAC-SHA256 HS256)
Layer 3 — Org scope:   Every request validated against client.organisation_id
Layer 4 — At-rest:     bcrypt (secrets), SHA-256 (API keys), AES-256-GCM (PII)
```

### The AuthContext object

The `require_integration_auth` FastAPI dependency is the single entry point for all auth. It returns an `AuthContext` that the route handler uses for all downstream decisions:

```python
class AuthContext:
    client:      IntegrationClient  # the authenticated partner
    scopes:      list[str]          # token/key scopes
    user_id:     Optional[uuid.UUID]
    auth_method: str               # "api_key" | "bearer"
    org_id:      Optional[uuid.UUID]  # derived from client.organisation_id

    def require_scope(self, scope: str) -> None: ...
    def require_org(self) -> uuid.UUID: ...       # raises 403 if unbound
    def validate_org(self, requested: Optional[uuid.UUID]) -> uuid.UUID: ...
```

Route handlers never touch `client.organisation_id` directly — they always call `ctx.validate_org(body.get("org_id"))`. This centralises the org-scope enforcement logic in one place.

### Sliding window rate limiting

We use Redis (DB 7) for rate limiting with a sliding window approach:

```python
async def _check_rate_limit(redis, client):
    now     = int(time.time())
    min_key = f"rl:min:{client.id}:{now // 60}"   # current minute bucket
    day_key = f"rl:day:{client.id}:{now // 86400}" # current day bucket

    pipe = redis.pipeline()
    pipe.incr(min_key)
    pipe.expire(min_key, 120)    # 2-minute TTL for cleanup
    pipe.incr(day_key)
    pipe.expire(day_key, 172800) # 2-day TTL for cleanup
    results = await pipe.execute()

    if results[0] > client.rate_limit_per_minute:
        raise HTTPException(429, {"error": "RATE_LIMIT_EXCEEDED", "window": "minute"})
    if results[2] > client.rate_limit_per_day:
        raise HTTPException(429, {"error": "RATE_LIMIT_EXCEEDED", "window": "day"})
```

**Why buckets, not a true sliding window?** A true sliding window requires storing every request timestamp in Redis (memory-intensive at scale). The bucket approach divides time into fixed intervals (minute/day). The trade-off is that requests near bucket boundaries can slightly exceed the nominal rate — acceptable for our use case.

**Why Redis DB 7?** Each service uses an isolated Redis database to prevent key collisions:
- DB 0: auth_service (sessions, JTI deny-list, Celery)
- DB 3: notification_service (rate limiting, dedup)
- DB 6: analytics_service
- DB 7: integration_service (rate limiting)

---

## 5. OAuth2 Server Implementation

The integration service implements a subset of OAuth2 (RFC 6749) and OIDC (OpenID Connect Core 1.0). We chose to implement it from scratch rather than using a library like `authlib` because:

1. We need tight integration with our existing `IntegrationClient` and `OAuthToken` models.
2. The scope of supported grants is small and well-defined.
3. We want to keep the dependency tree minimal.

### Grant types implemented

```
Client Credentials  → Machine-to-machine (server → server)
Authorization Code  → User-delegated with PKCE (mobile/SPA)
Refresh Token       → Extended sessions for auth code grant
```

### The PKCE implementation

PKCE (Proof Key for Code Exchange, RFC 7636) prevents authorization code interception attacks, critical for mobile apps where the redirect URI can be intercepted.

```python
def _verify_pkce(code_verifier: str, code_challenge: str, method: str) -> bool:
    if method == "S256":
        digest = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b"=").decode()
        return digest == code_challenge   # constant-time via hmac.compare_digest in caller
    return code_verifier == code_challenge  # plain method (discouraged)
```

**Flow at the token endpoint:**

```python
# 1. Client presents: code + redirect_uri + code_verifier
# 2. Load auth code by hash: code_hash = SHA256(code)
auth_code = await db.execute(
    select(OAuthAuthorizationCode).where(
        OAuthAuthorizationCode.code_hash == hash_code(code),
        OAuthAuthorizationCode.used_at.is_(None),  # single-use check
    )
)

# 3. Validate expiry (10 minutes)
if auth_code.expires_at < datetime.utcnow():
    raise HTTPException(400, {"error": "invalid_grant"})

# 4. Validate redirect_uri matches exactly (prevent open redirect)
if auth_code.redirect_uri != redirect_uri:
    raise HTTPException(400, {"error": "invalid_grant"})

# 5. Verify PKCE
if not _verify_pkce(code_verifier, auth_code.code_challenge, auth_code.code_challenge_method):
    raise HTTPException(400, {"error": "invalid_grant"})

# 6. Mark code used (set used_at — never delete, for audit trail)
auth_code.used_at = datetime.utcnow()
```

### Token structure

Access tokens are HS256 JWTs. We chose symmetric (HS256) over asymmetric (RS256) for simplicity — all services that need to verify tokens already share the `AUTH_SECRET_KEY`. If we later need public key verification (e.g. a partner wants to verify tokens client-side), we would rotate to RS256.

```json
{
  "iss": "https://riviwa.com",
  "sub": "<user_id or client_id>",
  "aud": "<client_id>",
  "jti": "<random 32-byte urlsafe token>",
  "exp": 1777046034,
  "iat": 1777045134,
  "client_id": "rwi_client_xxx",
  "scopes": ["feedback:write", "data:push"],
  "env": "SANDBOX",
  "org_id": "uuid-of-bound-org"
}
```

**The `org_id` claim in the JWT** means downstream services (feedback_service, analytics_service) don't need to call back to integration_service to know which org a request belongs to. The org is baked into the token.

### Token revocation strategy

We use a **deny-list** approach rather than short TTLs. Tokens are valid for 15 minutes, and a single `revoked_at` DB update makes them immediately invalid.

On every authenticated request:
1. Decode JWT (fast, in-memory)
2. Extract `jti`
3. Query `OAuthToken WHERE jti = $1 AND revoked_at IS NULL` (indexed lookup, ~1ms)

The alternative (very short TTLs, e.g. 60 seconds) would force clients to refresh constantly, adding latency and load.

---

## 6. Organisation Scoping — The Core Invariant

The most important invariant in the system:

> **Every request through the integration service is permanently bound to the `organisation_id` registered on the client. It cannot be overridden by any caller.**

### Why this invariant matters

Without it, a compromised API key for Organisation A could submit feedback on behalf of Organisation B, or read Organisation B's analytics data — a data isolation failure.

### Implementation

**Step 1 — Derive `org_id` from `client` in `AuthContext`:**

```python
class AuthContext:
    def __init__(self, client, scopes, user_id=None, auth_method="api_key"):
        ...
        self.org_id: Optional[uuid.UUID] = client.organisation_id  # derived, not passed
```

`org_id` is never taken from the request — it always comes from `client.organisation_id`.

**Step 2 — Two validation methods on `AuthContext`:**

```python
def require_org(self) -> uuid.UUID:
    """Raises 403 if client has no organisation bound."""
    if not self.org_id:
        raise HTTPException(403, {"error": "CLIENT_NOT_ORG_BOUND"})
    return self.org_id

def validate_org(self, requested_org_id: Optional[uuid.UUID]) -> uuid.UUID:
    """
    If the caller provides an org_id in the body, validates it matches
    the client's bound org. Falls back to client's org if None.
    Raises 403 on mismatch.
    """
    bound = self.require_org()
    if requested_org_id and requested_org_id != bound:
        raise HTTPException(403, {"error": "ORG_MISMATCH"})
    return bound  # always returns the client's org, never the caller's
```

**Step 3 — Applied at every data-writing endpoint:**

```python
# In context.py
org_id = ctx.validate_org(
    uuid.UUID(body["org_id"]) if body.get("org_id") else None
)
# org_id is now guaranteed to be == client.organisation_id
session = ContextSession(..., org_id=org_id)
```

**Step 4 — `org_id` propagated to JWT tokens:**

```python
if client.organisation_id:
    payload["org_id"] = str(client.organisation_id)
```

Downstream services can read `org_id` from the JWT without calling back to integration_service.

### Analytics service enforcement

Analytics endpoints now enforce the same invariant for non-admin users:

```python
def assert_org_access(token: TokenClaims, requested_org_id: uuid.UUID) -> None:
    if _is_platform_admin(token):
        return                          # platform admin can see any org
    if token.org_id != requested_org_id:
        raise ForbiddenError("You do not have access to this organisation's data.")
```

Injected into all 19 org-level analytics handlers via `replace_all` Edit on `org_analytics.py`.

---

## 7. Context Sessions — Encrypted Pre-fill

### The problem context sessions solve

When a user taps "Submit Complaint" in a banking app, they've already identified themselves to the bank (KYC'd, account number known). It's a poor UX to ask them to re-enter their name and phone in the Riviwa widget. Context sessions let the bank backend push that data ahead of time.

### Security requirements

1. **PII in transit:** The pre-fill data (phone, name, account number) must never appear in URL parameters or browser history. It's pushed from the partner's **backend** via a server-to-server call, and consumed by the Riviwa widget via a server-side decrypt.

2. **PII at rest:** If the `context_sessions` table is dumped, the pre-fill data should be unreadable without the `ENCRYPTION_KEY`.

3. **Single-use:** A session token shown to the user (in a URL or passed to a WebView) must be usable exactly once. Replaying it should return an error.

4. **Short-lived:** Sessions expire in 30 minutes. A leaked token is useless after expiry.

### Implementation

**Create session (partner backend → Riviwa):**

```python
pre_fill = {"phone": phone, "name": name, "account_ref": account_ref, ...}
encrypted = encrypt_field(json.dumps(pre_fill))   # AES-256-GCM via Fernet

raw_token, token_hash = generate_opaque_token(32) # 32 random bytes → 43 char base64url

session = ContextSession(
    token_hash           = token_hash,     # SHA-256 — stored
    pre_filled_data_enc  = encrypted,      # AES-256-GCM — stored
    org_id               = ctx.validate_org(body.get("org_id")),
    expires_at           = datetime.utcnow() + timedelta(seconds=ttl),
    consumed_at          = None,           # not yet used
)
# raw_token returned to partner (shown once — never stored)
```

**Consume session (Riviwa widget → Riviwa):**

```python
token_hash = hash_code(token)            # SHA-256 of the presented token

session = await db.execute(
    select(ContextSession).where(
        ContextSession.token_hash  == token_hash,
        ContextSession.consumed_at.is_(None),  # single-use check
    )
)
if session.expires_at < datetime.utcnow():
    raise HTTPException(410, {"error": "SESSION_EXPIRED"})

pre_fill = json.loads(decrypt_field(session.pre_filled_data_enc))
session.consumed_at = datetime.utcnow()   # mark consumed atomically
```

**AES-256-GCM via Fernet:**

```python
from cryptography.fernet import Fernet

def _get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY  # 32-byte base64url from environment
    raw = base64.urlsafe_b64decode(key + "==")
    return Fernet(base64.urlsafe_b64encode(raw))

def encrypt_field(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()

def decrypt_field(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()
```

Fernet provides authenticated encryption — it uses AES-128-CBC + HMAC-SHA256. The `ENCRYPTION_KEY` is a 32-byte random value, base64url-encoded, stored only in the `.env` file and environment variables. It's rotated independently of the JWT signing key.

---

## 8. Webhook Engine

### Design goals

1. **Reliability:** At-least-once delivery with exponential backoff retry.
2. **Low latency:** Deliveries should fire within 15 seconds of the triggering event.
3. **Observability:** Every attempt logged to `webhook_deliveries` with status, HTTP code, error string.
4. **Non-blocking:** Webhook delivery never blocks the main request path.

### APScheduler-based delivery worker

We chose APScheduler's `AsyncIOScheduler` over Celery because:
- No separate broker (Redis already used for rate limiting, not as Celery broker in this service)
- Lower operational complexity (no separate worker process)
- The polling frequency (15 seconds) is well within APScheduler's capabilities

```python
# main.py lifespan
scheduler = AsyncIOScheduler(timezone="UTC")
scheduler.add_job(
    _webhook_poll,
    trigger="interval",
    seconds=15,
    id="webhook_delivery",
    replace_existing=True,
)
scheduler.start()
```

### Delivery algorithm

```python
async def process_pending_deliveries() -> None:
    now = datetime.utcnow()
    async with AsyncSessionLocal() as db:
        # Fetch up to 50 deliveries due for (re)delivery
        deliveries = await db.execute(
            select(WebhookDelivery)
            .where(
                WebhookDelivery.status.in_(["PENDING", "RETRYING"]),
                WebhookDelivery.next_retry_at <= now,
            )
            .order_by(WebhookDelivery.created_at)
            .limit(50)
        )
        for delivery in deliveries:
            await deliver_webhook(db, delivery)
        await db.commit()
```

### Payload signing

```python
def sign_webhook_payload(body_bytes: bytes, raw_secret: str) -> Tuple[str, str]:
    ts  = str(int(time.time()))
    msg = f"{ts}.".encode() + body_bytes              # timestamp.body
    sig = hmac.new(raw_secret.encode(), msg, hashlib.sha256).hexdigest()
    return f"sha256={sig}", ts
```

The `timestamp.body` signing pattern (same as Stripe's webhook signatures) prevents:
- **Replay attacks:** Receivers check `|now - timestamp| < 300 seconds`
- **Body tampering:** HMAC covers the full payload

```
Headers sent:
  X-Riviwa-Signature: sha256=<hex>
  X-Riviwa-Timestamp: <unix_ts>
  X-Riviwa-Event:     feedback.submitted
  X-Riviwa-Delivery:  <uuid>
```

### Retry state machine

```
PENDING
   │
   ├─[HTTP 2xx]──────────────────► DELIVERED
   │
   └─[HTTP non-2xx or timeout]
         │
         ├─[attempt 1]──► RETRYING (next_retry_at = +30s)
         ├─[attempt 2]──► RETRYING (next_retry_at = +5m)
         ├─[attempt 3]──► RETRYING (next_retry_at = +30m)
         └─[attempt 4]──► FAILED (final)
```

The retry delays are configurable via `settings.WEBHOOK_RETRY_DELAYS = [30, 300, 1800]`.

---

## 9. Feedback Bridge — Internal Service Protocol

### The problem

The integration service needs to submit feedback to `feedback_service` on behalf of partner users. However:

- `feedback_service`'s public `POST /api/v1/feedback` endpoint requires a GRM officer JWT (`GRMOfficerDep` — org role manager+).
- Integration-submitted feedback has no GRM officer — it comes from an external API call.
- We cannot create a fake GRM officer JWT in the integration service.

### Solution — internal endpoint with X-Service-Key

We added a dedicated endpoint to `feedback_service`:

```
POST /api/v1/feedback/integration/submit   (include_in_schema=False — hidden from docs)
Authorization: X-Service-Key: <INTERNAL_SERVICE_KEY>
```

This endpoint:
1. Validates the `X-Service-Key` header (same pattern used by `ai_service` for internal calls)
2. Maps integration payload fields to `feedback_service` internal field names
3. Calls `submit_from_consumer()` when no `project_id` (AI auto-detects project) or `submit()` when `project_id` is provided

```python
# feedback_service/api/v1/feedback.py
@router.post("/integration/submit", include_in_schema=False)
async def integration_submit_feedback(request, db, kafka):
    service_key = request.headers.get("X-Service-Key", "")
    if service_key != settings.INTERNAL_SERVICE_KEY:
        return JSONResponse(status_code=403, ...)

    # ...
    if data.get("project_id"):
        result = await svc.submit(staff_data, token_sub=None)
    else:
        result = await svc.submit_from_consumer(data, user_id=None, channel_override=channel)
```

**Why two code paths?**
- `submit()` (staff path): fast, no AI, requires `project_id`. Used when partner provides project context.
- `submit_from_consumer()` (consumer path): can detect `project_id` via AI from `issue_lga` + `description`. Slower (~500ms AI call) but handles cases where the partner doesn't know the project.

### Channel normalisation

`FeedbackChannel` stores values like "other", "web_portal", "mobile_app". Integration partners send values like "API", "WEB_WIDGET", "CHATBOT". We resolve through the enum's `_missing_` method:

```python
# In FeedbackChannel enum
@classmethod
def _missing_(cls, value):
    clean = value.strip().lower()
    aliases = {
        "api":         cls.OTHER,
        "web_widget":  cls.WEB_PORTAL,
        "mini_app":    cls.MOBILE_APP,
        "chatbot":     cls.OTHER,
        ...
    }
    return aliases.get(clean)
```

`FeedbackChannel("api")` triggers `_missing_("api")` which returns `FeedbackChannel.OTHER`. No code changes needed in the `submit()` call chain.

### Feedback status check

A second endpoint at `GET /api/v1/feedback/integration/status/{id}` (also `X-Service-Key` protected) is used by the bridge's `GET /integration/feedback/{id}` to return status without a JWT.

---

## 10. Rate Limiting with Redis

### Key design

Rate limit keys include the client UUID and a time bucket:

```
rl:min:<client_uuid>:<now // 60>    TTL: 120s
rl:day:<client_uuid>:<now // 86400> TTL: 172800s (2 days)
```

The TTL is set to **double the bucket size** so Redis doesn't need a cron to clean up expired keys — they naturally expire.

### Graceful degradation

```python
try:
    redis = await _get_redis()
    await _check_rate_limit(redis, ctx.client)
except HTTPException:
    raise           # re-raise rate limit errors
except Exception as exc:
    log.warning("integration.rate_limit_check_failed", error=str(exc))
    # Don't fail the request if Redis is temporarily unavailable
    # Rate limiting is a best-effort defence, not a hard gate
```

If Redis is down, requests pass through. This is intentional — service availability takes priority over rate limiting in this context. A Redis outage should not take down the integration API.

---

## 11. Audit Logging Middleware

Every request is logged to `integration_audit_logs`, regardless of success or failure. This is implemented as an ASGI middleware rather than a dependency so it runs even on requests that fail auth:

```python
@app.middleware("http")
async def audit_log_middleware(request: Request, call_next) -> Response:
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = int((time.monotonic() - start) * 1000)

    # Fire-and-forget — never block the response
    try:
        async with AsyncSessionLocal() as db:
            entry = IntegrationAuditLog(
                client_id   = uuid.UUID(request.state.client_id) if hasattr(request.state, "client_id") else None,
                method      = request.method,
                path        = str(request.url.path),
                status_code = response.status_code,
                duration_ms = duration_ms,
                ip_address  = extract_ip(request),
                user_agent  = request.headers.get("user-agent", "")[:512],
            )
            db.add(entry)
            await db.commit()
    except Exception:
        pass   # Audit logging failure never propagates to the caller
    return response
```

**Key design choices:**
1. `try/except Exception: pass` — audit log failure must never return a 500 to the caller.
2. New `AsyncSessionLocal()` per request — the request's session may already be committed/rolled back by this point.
3. `client_id` comes from `request.state` — the auth dependency sets `request.state.client_id = str(ctx.client.id)` after successful auth.

---

## 12. Database Migration Strategy

### Why manual migrations instead of Alembic autogenerate?

We wrote the initial migration (`a1b2c3d4e5f6`) by hand rather than using `alembic revision --autogenerate` because:

1. The `integration_service` was a fresh service — no existing schema to diff against.
2. SQLModel's `JSONB` columns and explicit `sa_column` overrides sometimes confuse autogenerate.
3. Hand-written migrations are easier to review and give us full control over indexes.

### The `alembic/env.py` — synchronous pattern

Unlike what you might expect from an async FastAPI service, Alembic migrations always run synchronously. This is because Alembic itself is synchronous. The env.py uses `engine_from_config` (sync) not `async_engine_from_config`:

```python
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
```

The connection string uses `postgresql+psycopg://` (sync psycopg3 driver) rather than `postgresql+asyncpg://` (async).

### The `SQLModel.metadata.create_all` safety net

```python
# main.py lifespan
async with engine.begin() as conn:
    await conn.run_sync(SQLModel.metadata.create_all)
```

This runs on every startup. In a fresh environment where Alembic hasn't run yet (e.g., a developer's local machine), it creates all tables from the SQLModel metadata. In production, Alembic has already created the tables so `create_all` is a no-op. For the `ai_service` (which has no Alembic), `create_all` is the only migration mechanism — but `integration_service` uses both as a defence-in-depth approach.

---

## 13. Deployment and Docker Compose Integration

### The entrypoint script pattern

```bash
#!/usr/bin/env bash
set -e

# Wait for PostgreSQL (max ~30s via pg_isready loop)
until pg_isready -h "${INTEGRATION_DB_HOST}" -q; do sleep 1; done

# Run migrations
alembic upgrade head

# Start uvicorn (dev: hot-reload; prod: 2 workers)
if [ "${ENVIRONMENT}" = "development" ]; then
    exec uvicorn main:app --host 0.0.0.0 --port 8100 --reload
else
    exec uvicorn main:app --host 0.0.0.0 --port 8100 --workers 2
fi
```

This pattern is consistent across all Riviwa services. Using `exec` replaces the shell with uvicorn, making uvicorn PID 1 — required for correct signal handling (`SIGTERM` for graceful shutdown).

### Docker Compose integration

Three touch points:
1. **`docker-compose.yml`** — `integration_db` (postgres:15) + `integration_service` services, `integration_db_data` volume, nginx `depends_on`
2. **`docker-compose.override.yml`** — dev mode: `--reload`, bind mount source, DEBUG env
3. **`nginx/nginx.conf`** — two location blocks:
   - `location /api/v1/integration` → `set $integration http://integration_service:8100; proxy_pass $integration;`
   - `location /api/v1/integration/.well-known` → same upstream (OIDC discovery)

### Why `set $var; proxy_pass $var;` instead of `proxy_pass http://integration_service:8100;`?

Nginx resolves DNS in `upstream {}` blocks at startup. If a service container restarts and gets a new IP, nginx continues proxying to the old (dead) IP until its own restart.

The `set $var; proxy_pass $var;` pattern forces nginx to re-resolve the hostname via the Docker embedded DNS resolver (`127.0.0.11`) on every request, honouring the `resolver 127.0.0.11 valid=30s;` directive. This is the solution to the "502 after container restart" problem we encountered during development.

### Service isolation

```
integration_db  ─── integration_service
    5442:5432          8100:8100
       │                   │
       └──────── riviwa-net ──────┘
                    │
              (same network as all other services)
```

`integration_db` is only reachable from within `riviwa-net`. There's no direct public access to port 5442 from outside the Docker network — the port mapping is for local development debugging only and would be removed in a production hardened setup.

---

## 14. Key Engineering Decisions

### Decision 1: SHA-256 for API keys, not bcrypt

**Context:** API keys are verified on every authenticated request.  
**Decision:** SHA-256 (fast) for API keys, bcrypt (slow, cost 12) for client secrets.  
**Rationale:** bcrypt at cost 12 takes ~250ms. At 60 req/min, that's 15 seconds of CPU per minute spent just on key verification. SHA-256 is cryptographically appropriate because API keys are high-entropy random strings (not passwords that users pick). The security argument for bcrypt applies to low-entropy values; it doesn't apply to `secrets.token_urlsafe(36)`.

### Decision 2: HS256 JWT, not RS256

**Context:** Access tokens need to be verifiable by multiple services.  
**Decision:** HS256 (symmetric) using the shared `AUTH_SECRET_KEY`.  
**Rationale:** All Riviwa services already share `AUTH_SECRET_KEY` to verify user JWTs from auth_service. Using the same key for integration tokens means no new infrastructure. RS256 would be needed if external partners needed to verify tokens client-side without contacting Riviwa — a requirement we don't currently have.

### Decision 3: Org_id baked into JWT claims

**Context:** Multiple services need to know which org a request belongs to.  
**Decision:** Include `org_id` in the JWT payload at issuance time.  
**Rationale:** The alternative (look up client → org_id on every request) would add a DB round-trip to every authenticated call. By embedding `org_id` in the JWT, downstream services (analytics, feedback) get it for free from the token they're already decoding.

### Decision 4: APScheduler over Celery for webhooks

**Context:** Need a periodic job to deliver outbound webhooks with retries.  
**Decision:** APScheduler `AsyncIOScheduler` running in the same process.  
**Rationale:** Integration service doesn't use Kafka (it's a synchronous API, not event-driven). Adding Celery would require a Redis Celery broker config and a separate worker container. APScheduler shares the event loop with uvicorn, supports async tasks natively, and requires zero additional infrastructure.

### Decision 5: Separate internal endpoint for feedback submission

**Context:** Integration bridge needs to create feedback records without GRM officer credentials.  
**Decision:** `POST /api/v1/feedback/integration/submit` protected by `X-Service-Key`.  
**Rationale:** Adding a bypass to the existing `submit_feedback` endpoint would have made its auth logic complex and fragile. A separate endpoint has clear, single-purpose auth and field mapping. The `include_in_schema=False` flag keeps it hidden from public API docs.

### Decision 6: `from __future__ import annotations` removed from models

**Context:** SQLModel relationships use type annotations like `List["ApiKey"]`.  
**Decision:** Remove `from __future__ import annotations` from `models/integration.py`.  
**Rationale:** With that import active, ALL annotations become lazy string literals. SQLAlchemy/SQLModel evaluates `List["ApiKey"]` as the string `"List['ApiKey']"` which it cannot resolve for `Relationship()` fields. Python 3.11 supports `list[str]`, `Optional[uuid.UUID]` natively, so the import is unnecessary.

---

## 15. Known Limitations and Future Work

### Current limitations

| Area | Limitation | Priority |
|------|------------|----------|
| mTLS | `require_mtls` flag stored but not enforced at nginx level | High |
| RS256 | HS256 tokens not verifiable by partner client-side | Medium |
| Refresh token rotation | Old refresh tokens should be invalidated on use (currently done) but there's no family tracking to detect theft | Medium |
| Webhook secret rotation | The `webhook_signing_secret` is stored as bcrypt; we use the hash as the HMAC key for test deliveries — not ideal | Medium |
| AI project detection | Calls `ai_service` synchronously from the feedback bridge path, adding latency | Low |
| Widget JS | `widget.js` and the actual embed UI are not yet built | High (roadmap) |
| Social sign-in | OAuth2 "Login with Google/Apple" for consumers identified as a use case but not implemented | Medium |

### Future work

**mTLS implementation:** Nginx needs client certificate verification config. The `mtls_cert_fingerprint` stored on `IntegrationClient` would be validated against the certificate's SHA-256 fingerprint extracted by nginx (`$ssl_client_fingerprint`).

**Webhook signing secret improvement:** The current `webhook_secret_hash` is a bcrypt hash — irreversible. The webhook worker uses the hash value itself as the HMAC key (not ideal but functional). A better approach: store the signing secret encrypted with AES-256-GCM (same as `data_endpoint_auth_enc`) so the worker can decrypt and use the real secret for proper HMAC signing. This requires a migration to change the column from bcrypt to Fernet-encrypted.

**Replay token detection (refresh token family):** Currently, if a refresh token is stolen and used, the victim's next refresh will fail (JTI not found). We should implement token family tracking — if an already-used refresh token is presented, invalidate the entire grant (access + all refresh tokens in the family), detect theft.

**Rate limiting persistence across restarts:** Current Redis buckets reset when Redis restarts. A persistent rate limit counter (e.g. PostgreSQL-backed for the day bucket) would prevent burst abuse after Redis restarts.

---

*End of document.*

*For questions about this implementation, open an issue at github.com/josako53/RiviwaGlobe*
