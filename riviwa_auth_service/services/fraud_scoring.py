"""
services/fraud_scoring.py
──────────────────────────────────────────────────────────────────
ScoringEngine: takes all signals from a registration attempt
and returns a weighted fraud score 0-100 + action recommendation.

Signal weights (must sum to 1.0):
  Email normalization / alias tricks   0.15
  IP / geo / VPN                       0.25
  Device fingerprint                   0.25
  Behavioral (typing, mouse)           0.15
  Velocity (registrations per IP/FP)   0.10
  Geo mismatch (IP vs declared)        0.10

Action thresholds (from config):
  score >= BLOCK  → FraudAction.BLOCK   (hard reject)
  score >= REVIEW → FraudAction.REVIEW  (require gov ID)
  score >= WARN   → FraudAction.WARN    (log + monitor)
  else            → FraudAction.ALLOW

Email-normalisation note
──────────────────────────────────────────────────────────────────
normalize_email() is imported from core.security — the single
source of truth.  Do not re-implement it here.

Dead-signal note: email_normalized_exists
──────────────────────────────────────────────────────────────────
registration_service._check_uniqueness() raises EmailAlreadyExistsError
BEFORE scoring runs when a normalised-email collision is found via a
direct DB uniqueness check.  This means email_normalized_exists will
always arrive as False through the normal registration path.

The field is kept in ScoringInput so the scoring engine can be called
independently (e.g. from admin tooling or ML pipelines that bypass the
registration uniqueness gate).  The registration path should eventually
be refactored so the normalised-email check is removed from the
uniqueness gate and treated purely as a fraud signal — at which point
this scorer becomes live.  Until then the effective email-signal
contribution is 0 for all live registrations, and the email weight
(0.15) goes unused.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import structlog

from core.config import settings
from core.security import normalize_email          # single source of truth
from models.fraud import FraudAction
from schemas.fraud import BehavioralSummary, FingerprintPayload
from services.geo_service import GeoResult

log = structlog.get_logger(__name__)


# ── Signal weights ──────────────────────────────────────────────────────────────
# Must sum to exactly 1.0.

WEIGHT_EMAIL       = 0.15
WEIGHT_IP          = 0.25
WEIGHT_FINGERPRINT = 0.25
WEIGHT_BEHAVIORAL  = 0.15
WEIGHT_VELOCITY    = 0.10
WEIGHT_GEO         = 0.10

assert abs(
    WEIGHT_EMAIL + WEIGHT_IP + WEIGHT_FINGERPRINT
    + WEIGHT_BEHAVIORAL + WEIGHT_VELOCITY + WEIGHT_GEO
    - 1.0
) < 1e-9, "Signal weights must sum to 1.0"


# ── Score input dataclass ────────────────────────────────────────────────────────

@dataclass
class ScoringInput:
    email: str
    email_normalized: str
    ip_address: str
    geo: GeoResult
    fingerprint: Optional[FingerprintPayload] = None
    behavioral: Optional[BehavioralSummary] = None

    # Pre-queried duplicate signals (from repositories)
    #
    # NOTE: email_normalized_exists is always False when called from
    # registration_service because the uniqueness gate fires first (see module
    # docstring).  The field is kept for out-of-band callers.
    email_normalized_exists: bool = False
    ip_user_count: int = 0                     # accounts registered from this IP
    fingerprint_user_count: int = 0            # accounts sharing this fingerprint
    declared_country: Optional[str] = None    # user-declared vs geo-derived country
    registrations_last_hour_from_ip: int = 0  # velocity: last 60 min by IP
    registrations_last_hour_from_fp: int = 0  # velocity: last 60 min by fingerprint


@dataclass
class ScoringResult:
    total_score: int
    action: FraudAction

    score_email: int = 0
    score_ip: int = 0
    score_fingerprint: int = 0
    score_behavioral: int = 0
    score_velocity: int = 0
    score_geo: int = 0

    details: dict = field(default_factory=dict)


# ── Scoring engine ───────────────────────────────────────────────────────────────

class ScoringEngine:

    def score(self, inp: ScoringInput) -> ScoringResult:
        s_email = self._score_email(inp)
        s_ip    = self._score_ip(inp)
        s_fp    = self._score_fingerprint(inp)
        s_beh   = self._score_behavioral(inp)
        s_vel   = self._score_velocity(inp)
        s_geo   = self._score_geo(inp)

        # Use round() before int() to avoid floating-point truncation errors
        # (e.g. 0.15 * 90 = 13.499... truncates to 13 instead of 14).
        raw_total = (
            s_email * WEIGHT_EMAIL
            + s_ip    * WEIGHT_IP
            + s_fp    * WEIGHT_FINGERPRINT
            + s_beh   * WEIGHT_BEHAVIORAL
            + s_vel   * WEIGHT_VELOCITY
            + s_geo   * WEIGHT_GEO
        )
        total  = min(int(round(raw_total)), 100)
        action = self._determine_action(total)

        log.info(
            "fraud_scoring.complete",
            total=total,
            action=action.value,
            s_email=s_email,
            s_ip=s_ip,
            s_fp=s_fp,
            s_beh=s_beh,
            s_vel=s_vel,
            s_geo=s_geo,
        )

        return ScoringResult(
            total_score=total,
            action=action,
            score_email=s_email,
            score_ip=s_ip,
            score_fingerprint=s_fp,
            score_behavioral=s_beh,
            score_velocity=s_vel,
            score_geo=s_geo,
            details={
                "email_normalized_exists":  inp.email_normalized_exists,
                "ip_user_count":            inp.ip_user_count,
                "fingerprint_user_count":   inp.fingerprint_user_count,
                "geo_vpn":                  inp.geo.is_vpn,
                "geo_tor":                  inp.geo.is_tor,
                "geo_high_risk":            inp.geo.is_high_risk_country,
                "fp_webdriver":             inp.fingerprint.webdriver_detected  if inp.fingerprint else None,
                "fp_headless":              inp.fingerprint.headless_detected   if inp.fingerprint else None,
                "behavioral_rapid":         inp.behavioral.rapid_completion     if inp.behavioral  else None,
                "behavioral_paste":         inp.behavioral.paste_detected       if inp.behavioral  else None,
            },
        )

    # ── Individual scorers ──────────────────────────────────────────────────────

    def _score_email(self, inp: ScoringInput) -> int:
        """
        Score 0-100 for email-level fraud signals.

        Currently limited to normalised-email collision detection.  In live
        registration flows this will always return 0 because the uniqueness gate
        in registration_service fires first (see module docstring).  The signal
        becomes effective when the gate is moved to scoring-only.
        """
        score = 0
        if inp.email_normalized_exists:
            score += 90   # gmail dot-trick / + alias reuse → very high signal
        return min(score, 100)

    def _score_ip(self, inp: ScoringInput) -> int:
        score = inp.geo.risk_score   # VPN=25, Tor=40, proxy=20, datacenter=15 …
        if inp.ip_user_count >= 5:
            score += 40
        elif inp.ip_user_count >= 2:
            score += 20
        elif inp.ip_user_count == 1:
            score += 10
        return min(score, 100)

    def _score_fingerprint(self, inp: ScoringInput) -> int:
        if inp.fingerprint is None:
            return 20   # no fingerprint data at all — mildly suspicious
        score = 0
        if inp.fingerprint_user_count >= 2:
            score += 70   # same fingerprint already on another account
        elif inp.fingerprint_user_count == 1:
            score += 35
        if inp.fingerprint.webdriver_detected:
            score += 30
        if inp.fingerprint.headless_detected:
            score += 25
        if inp.fingerprint.inconsistencies_count >= 3:
            score += 15
        return min(score, 100)

    def _score_behavioral(self, inp: ScoringInput) -> int:
        if inp.behavioral is None:
            return 15   # JS collector absent — mild suspicion
        score = 0
        if inp.behavioral.rapid_completion:
            score += 50   # form completed in <3 s — almost certainly a bot
        if inp.behavioral.paste_detected and not inp.behavioral.mouse_movement_count:
            score += 25   # paste with zero mouse movement → scripted
        if inp.behavioral.autofill_detected:
            score += 10   # could be legitimate, low weight
        if inp.behavioral.mouse_movement_count == 0 and not inp.behavioral.touch_device:
            score += 20   # no mouse or touch on a desktop browser
        return min(score, 100)

    def _score_velocity(self, inp: ScoringInput) -> int:
        score = 0
        if inp.registrations_last_hour_from_ip >= 10:
            score += 90
        elif inp.registrations_last_hour_from_ip >= 5:
            score += 60
        elif inp.registrations_last_hour_from_ip >= 2:
            score += 30
        if inp.registrations_last_hour_from_fp >= 3:
            score += 50
        return min(score, 100)

    def _score_geo(self, inp: ScoringInput) -> int:
        score = 0
        # Mismatch: IP-derived country ≠ user-declared country
        if (
            inp.declared_country
            and inp.geo.country_code
            and inp.declared_country.upper() != inp.geo.country_code.upper()
        ):
            score += 30
        return min(score, 100)

    def _determine_action(self, total: int) -> FraudAction:
        if total >= settings.FRAUD_SCORE_BLOCK_THRESHOLD:
            return FraudAction.BLOCK
        if total >= settings.FRAUD_SCORE_REVIEW_THRESHOLD:
            return FraudAction.REVIEW
        if total >= settings.FRAUD_SCORE_WARN_THRESHOLD:
            return FraudAction.WARN
        return FraudAction.ALLOW
