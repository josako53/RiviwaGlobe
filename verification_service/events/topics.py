"""events/topics.py — Kafka topic and event-type constants for verification_service."""

VERIFICATION_TOPIC = "riviwa.verification.events"

class VerificationEvents:
    SCANNED      = "verification.scanned"
    FAKE_REPORTED = "verification.fake_reported"
