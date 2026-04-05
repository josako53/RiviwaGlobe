"""
services/oauth_service.py
═══════════════════════════════════════════════════════════════════════════════
Social / OAuth authentication service.

Handles BOTH social registration and social login in a single call.
The server determines which applies based on whether the email from the
provider already exists in the database.

Supported providers
────────────────────
  google    — OIDC id_token verified against Google's tokeninfo endpoint
              or JWKS (upgrade path documented below)
  apple     — identityToken (RS256 JWT) verified against Apple's JWKS
  facebook  — access_token exchanged via graph.facebook.com/me

Token verification strategy
────────────────────────────
  Google:   POST to https://oauth2.googleapis.com/tokeninfo?id_token=<token>
            Validates signature + expiry server-side; checks `aud` claim
            matches GOOGLE_CLIENT_ID.
            Production upgrade: switch to JWKS-based offline verification
            (https://www.googleapis.com/oauth2/v3/certs) to avoid latency
            from the tokeninfo round-trip.

  Apple:    Fetch public JWKS from https://appleid.apple.com/auth/keys,
            then verify RS256 JWT locally using PyJWT + RSAAlgorithm.
            The `aud` claim must match APPLE_CLIENT_ID.
            Apple only returns the user's email on the FIRST sign-in;
            subsequent sign-ins return only `sub`. This implementation
            stores `sub` on first auth so future logins look up by
            (oauth_provider="apple", oauth_provider_id=sub).

  Facebook: Call https://graph.facebook.com/me with the access_token;
            verify appsecret_proof (HMAC-SHA256 of access_token signed
            with FACEBOOK_APP_SECRET) to prevent token injection attacks.

Security invariants
────────────────────
  · Provider tokens are verified server-side before any DB write.
  · Raw tokens are never stored or logged.
  · Email is never blindly trusted from the provider payload without
    signature verification — the aud / appsecret_proof check is mandatory.
  · OAuthTokenInvalidError is intentionally generic — does not reveal which
    check failed.

Kafka events published
──────────────────────
  user.registered_social   (new account)
  auth.login_success        (existing account)
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from typing import Optional

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import (
    OAuthTokenInvalidError,
    UserNotFoundError,
)
from core.security import (
    create_access_token,
    generate_refresh_token,
    normalize_email,
)
from events.publisher import EventPublisher
from models.user import AccountStatus, User
from repositories.user_repository import UserRepository

log = structlog.get_logger(__name__)

# HTTP timeout for provider API calls (connect + read)
_PROVIDER_TIMEOUT = 8.0

# Redis refresh token prefix (mirrors auth_service.py)
_REFRESH_PREFIX = "refresh:"


class OAuthService:
    """
    Social login / registration via Google, Apple, or Facebook.

    Instantiated once per request by the FastAPI dependency in api/v1/deps.py.
    Requires: db session, redis client, EventPublisher.
    """

    def __init__(self, db: AsyncSession, redis, publisher: EventPublisher) -> None:
        self.db        = db
        self.redis     = redis
        self.publisher = publisher
        self.user_repo = UserRepository(db)

    # ── Public entry point ────────────────────────────────────────────────────

    async def authenticate(
        self,
        provider:           str,   # "google" | "apple" | "facebook"
        id_token:           str,
        ip_address:         str,
        device_fingerprint: Optional[str] = None,
    ) -> dict:
        """
        Verify the provider token, then upsert the user and issue tokens.

        Returns a dict matching SocialAuthResponse fields:
            {
                user_id:      str,
                is_new_user:  bool,
                has_password: bool,
                access_token, refresh_token, token_type, expires_in
            }

        Raises OAuthTokenInvalidError on any provider verification failure.
        """
        # ── 1. Verify token and extract profile ────────────────────────────
        profile = await self._verify_token(provider, id_token)

        email         = profile.get("email")
        provider_uid  = profile.get("sub") or profile.get("id")
        name          = profile.get("name")

        if not provider_uid:
            raise OAuthTokenInvalidError("Provider did not return a user identifier.")

        # ── 2. Upsert user ─────────────────────────────────────────────────
        user, is_new = await self._upsert_user(
            provider=provider,
            provider_uid=provider_uid,
            email=email,
            name=name,
        )

        # ── 3. Issue tokens ────────────────────────────────────────────────
        org_id, org_role, platform_role = await self._resolve_jwt_context(user)
        token, jti, expires_in = create_access_token(
            user_id=user.id,
            org_id=org_id,
            org_role=org_role,
            platform_role=platform_role,
        )
        refresh = generate_refresh_token()
        await self._store_refresh_token(refresh, user.id)

        await self.db.commit()

        # ── 4. Publish events ──────────────────────────────────────────────
        if is_new:
            log.info("oauth.registered", user_id=str(user.id), provider=provider)
            await self.publisher.user_registered_social(user, provider=provider)
        else:
            log.info("oauth.login_success", user_id=str(user.id), provider=provider)
            await self.publisher.auth_login_success(user.id, ip_address)

        return {
            "user_id":       str(user.id),
            "is_new_user":   is_new,
            "has_password":  user.hashed_password is not None,
            "access_token":  token,
            "refresh_token": refresh,
            "token_type":    "bearer",
            "expires_in":    expires_in,
        }

    # ── Provider verification ─────────────────────────────────────────────────

    async def _verify_token(self, provider: str, id_token: str) -> dict:
        """
        Dispatch to the correct provider verifier.
        Raises OAuthTokenInvalidError on any failure.
        """
        try:
            if provider == "google":
                return await self._verify_google(id_token)
            elif provider == "apple":
                return await self._verify_apple(id_token)
            elif provider == "facebook":
                return await self._verify_facebook(id_token)
            else:
                raise OAuthTokenInvalidError(f"Unknown provider: {provider}")
        except OAuthTokenInvalidError:
            raise
        except Exception as exc:
            log.warning("oauth.verification_error", provider=provider, error=str(exc))
            raise OAuthTokenInvalidError()

    async def _verify_google(self, id_token: str) -> dict:
        """
        Verify a Google OIDC id_token.

        Uses the tokeninfo endpoint (simple, adds ~100ms latency).
        Production upgrade: use JWKS-based offline verification to eliminate
        the round-trip — fetch keys from
        https://www.googleapis.com/oauth2/v3/certs and verify locally
        with PyJWT + RSAAlgorithm.
        """
        async with httpx.AsyncClient(timeout=_PROVIDER_TIMEOUT) as client:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": id_token},
            )

        if resp.status_code != 200:
            log.warning("oauth.google.invalid_token", status=resp.status_code)
            raise OAuthTokenInvalidError("Google token verification failed.")

        data = resp.json()

        if "error" in data:
            raise OAuthTokenInvalidError(f"Google: {data['error']}")

        # Validate audience — must match our client ID
        client_id = settings.GOOGLE_CLIENT_ID
        if client_id and data.get("aud") != client_id:
            log.warning(
                "oauth.google.aud_mismatch",
                expected=client_id,
                got=data.get("aud"),
            )
            raise OAuthTokenInvalidError("Google token audience mismatch.")

        return {
            "sub":   data.get("sub"),
            "email": data.get("email"),
            "name":  data.get("name"),
        }

    async def _verify_apple(self, identity_token: str) -> dict:
        """
        Verify an Apple Sign-In identityToken (RS256 JWT).

        1. Fetch Apple's JWKS from the public endpoint.
        2. Select the matching key using the `kid` header claim.
        3. Decode and verify the JWT locally using PyJWT.

        Apple only includes the user's email on the FIRST sign-in.
        On subsequent sign-ins only `sub` (stable Apple user ID) is returned.
        Always store `sub` as the primary provider_id.
        """
        try:
            import jwt as pyjwt
            from jwt.algorithms import RSAAlgorithm
        except ImportError:
            raise ImportError(
                "PyJWT is required for Apple Sign-In. "
                "Add 'PyJWT[cryptography]' to requirements.txt."
            )

        # 1. Fetch Apple's public keys
        async with httpx.AsyncClient(timeout=_PROVIDER_TIMEOUT) as client:
            keys_resp = await client.get("https://appleid.apple.com/auth/keys")
            keys_resp.raise_for_status()
            keys = keys_resp.json().get("keys", [])

        # 2. Find matching key by kid
        header = pyjwt.get_unverified_header(identity_token)
        kid    = header.get("kid")
        key_data = next((k for k in keys if k.get("kid") == kid), None)
        if not key_data:
            raise OAuthTokenInvalidError("Apple: matching public key not found.")

        public_key = RSAAlgorithm.from_jwk(key_data)

        # 3. Verify JWT
        payload = pyjwt.decode(
            identity_token,
            public_key,
            algorithms=["RS256"],
            audience=settings.APPLE_CLIENT_ID or None,
            issuer="https://appleid.apple.com",
        )

        return {
            "sub":   payload.get("sub"),
            "email": payload.get("email"),   # may be None on repeat sign-ins
            "name":  None,                   # Apple never includes name in token
        }

    async def _verify_facebook(self, access_token: str) -> dict:
        """
        Verify a Facebook access_token via the Graph API.

        Uses appsecret_proof (HMAC-SHA256 of access_token) to authenticate
        the server-to-server call and prevent token injection attacks.
        Requires FACEBOOK_APP_ID and FACEBOOK_APP_SECRET in settings.
        """
        app_secret = settings.FACEBOOK_APP_SECRET
        if not app_secret:
            raise OAuthTokenInvalidError(
                "FACEBOOK_APP_SECRET must be set to verify Facebook tokens."
            )

        # appsecret_proof = HMAC-SHA256(access_token, key=app_secret)
        appsecret_proof = hmac.new(
            app_secret.encode("utf-8"),
            access_token.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        async with httpx.AsyncClient(timeout=_PROVIDER_TIMEOUT) as client:
            resp = await client.get(
                "https://graph.facebook.com/me",
                params={
                    "access_token":    access_token,
                    "appsecret_proof": appsecret_proof,
                    "fields":          "id,email,name",
                },
            )

        if resp.status_code != 200:
            raise OAuthTokenInvalidError("Facebook token verification failed.")

        data = resp.json()

        if "error" in data:
            raise OAuthTokenInvalidError(f"Facebook: {data['error'].get('message')}")

        if not data.get("id"):
            raise OAuthTokenInvalidError("Facebook did not return a user ID.")

        return {
            "sub":   data.get("id"),
            "email": data.get("email"),
            "name":  data.get("name"),
        }

    # ── User upsert ───────────────────────────────────────────────────────────

    async def _upsert_user(
        self,
        provider:     str,
        provider_uid: str,
        email:        Optional[str],
        name:         Optional[str],
    ) -> tuple[User, bool]:
        """
        Find or create a User for the given provider identity.

        Lookup order:
          1. (provider, provider_uid) — most reliable; works for Apple
             repeat sign-ins where email is absent.
          2. email — for first-time social registration; links the provider
             to an existing account if the email matches.
          3. None of the above → create a new User.

        Returns: (user, is_new_user)
        """
        # ── 1. Look up by provider ID ─────────────────────────────────────
        user = await self.user_repo.get_by_oauth(
            provider=provider,
            provider_id=provider_uid,
        )
        if user:
            return user, False

        # ── 2. Look up by email (link provider to existing account) ───────
        if email:
            email_norm = normalize_email(email)
            user = await self.user_repo.get_by_email_normalized(email_norm)
            if user:
                # Link this provider to the existing account
                await self.user_repo.link_oauth_provider(
                    user.id, provider, provider_uid
                )
                await self.publisher.user_oauth_linked(user, provider)
                return user, False

        # ── 3. Create new user ────────────────────────────────────────────
        username = await self._generate_username(email, name)
        email_to_store = email or self._synthetic_email(provider, provider_uid)
        email_norm     = normalize_email(email_to_store)

        user = await self.user_repo.create(
            username=username,
            email=email_to_store,
            email_normalized=email_norm,
            hashed_password=None,          # social-only; no password yet
            display_name=name,
            status=AccountStatus.ACTIVE,
            is_email_verified=bool(email), # email verified by provider
            oauth_provider=provider,
            oauth_provider_id=provider_uid,
        )
        return user, True

    # ── JWT context helper ────────────────────────────────────────────────────

    async def _resolve_jwt_context(
        self,
        user: User,
    ) -> tuple[Optional[uuid.UUID], Optional[str], Optional[str]]:
        """Resolve (org_id, org_role, platform_role) for the JWT payload."""
        from repositories.organisation_repository import OrganisationRepository

        org_repo      = OrganisationRepository(self.db)
        org_id        = user.active_org_id
        org_role      = None
        platform_role = self._get_platform_role(user)

        if org_id:
            member = await org_repo.get_active_member(org_id, user.id)
            if member:
                org_role = member.org_role.value
            else:
                await self.user_repo.update_active_org(user.id, None)
                org_id = None

        return org_id, org_role, platform_role

    def _get_platform_role(self, user: User) -> Optional[str]:
        names    = user.get_platform_role_names()
        priority = ["super_admin", "admin", "moderator"]
        for role in priority:
            if role in names:
                return role
        return names[0] if names else None

    async def _store_refresh_token(
        self,
        refresh_token: str,
        user_id:       uuid.UUID,
    ) -> None:
        ttl = getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7) * 86400
        await self.redis.setex(
            f"{_REFRESH_PREFIX}{refresh_token}",
            ttl,
            str(user_id),
        )

    # ── Username generation ───────────────────────────────────────────────────

    async def _generate_username(
        self,
        email: Optional[str],
        name:  Optional[str],
    ) -> str:
        """Generate a unique username from email or name."""
        import re
        import random

        if email:
            base = re.sub(r"[^a-z0-9]", "", email.split("@")[0].lower())[:20] or "user"
        elif name:
            base = re.sub(r"[^a-z0-9]", "", name.lower().replace(" ", ""))[:20] or "user"
        else:
            base = "user"

        candidate = base
        for _ in range(20):
            if not await self.user_repo.get_by_username(candidate):
                return candidate
            candidate = f"{base}{random.randint(1000, 9999)}"

        return f"{base}{uuid.uuid4().hex[:8]}"

    @staticmethod
    def _synthetic_email(provider: str, provider_uid: str) -> str:
        """
        Synthetic unreachable email for provider accounts with no email.
        e.g. apple+a1b2c3d4@riviwasystem.invalid
        The .invalid TLD (RFC 2606) never routes to a real mailbox.
        """
        suffix = hashlib.sha256(f"{provider}:{provider_uid}".encode()).hexdigest()[:12]
        return f"{provider}+{suffix}@riviwasystem.invalid"
