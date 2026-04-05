"""events/topics.py — payment_service"""
from __future__ import annotations


class KafkaTopics:
    PAYMENT_EVENTS = "riviwa.payment.events"
    ORG_EVENTS     = "riviwa.org.events"      # consumed for project context


class PaymentEvents:
    """Events published on riviwa.payment.events."""
    INITIATED  = "payment.initiated"
    COMPLETED  = "payment.completed"
    FAILED     = "payment.failed"
    REFUNDED   = "payment.refunded"
    EXPIRED    = "payment.expired"
