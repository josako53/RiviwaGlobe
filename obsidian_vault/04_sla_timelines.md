# SLA Timelines — Service Level Agreements

## Acknowledgement SLA (Time to first response)

| Priority | Acknowledgement Deadline |
|---|---|
| CRITICAL | 4 hours |
| HIGH | 8 hours |
| MEDIUM | 24 hours |
| LOW | 48 hours |

## Resolution SLA (Time to full resolution)

| Priority | Resolution Deadline |
|---|---|
| CRITICAL | 72 hours (3 days) |
| HIGH | 168 hours (7 days) |
| MEDIUM | 336 hours (14 days) |
| LOW | 720 hours (30 days) |

## Priority Definitions

**CRITICAL:**
- Immediate risk to life, health, or safety
- Ongoing harm (flooding, exposure to hazardous materials)
- Court orders or legal compliance deadlines
- Media/political attention on unresolved issue

**HIGH:**
- Significant economic impact (loss of livelihood, business)
- Unresolved physical displacement
- Major infrastructure damage caused by project
- Vulnerable person affected (elderly, disabled, woman-headed household)

**MEDIUM:**
- Standard grievances about project activities
- Unresolved minor property damage
- Missing information or communication failure
- Community access issues

**LOW:**
- General inquiries
- Minor suggestions or requests
- Positive feedback requiring acknowledgement
- Low-impact nuisances

## SLA Monitoring

The system automatically:
- Calculates `ack_deadline` = submitted_at + ack_SLA_hours
- Calculates `res_deadline` = submitted_at + res_SLA_hours  
- Sets `ack_sla_breached = True` when acknowledged_at > ack_deadline
- Sets `res_sla_breached = True` when resolved_at > res_deadline
- Tracks `days_unresolved` for all open feedbacks
- Sends alerts when SLA is approaching (75%) and breached (100%)

## Overdue Feedbacks

A feedback is considered overdue when:
- `target_resolution_date` < today AND status is NOT resolved/closed
- The `GET /reports/overdue` endpoint returns all overdue items per project

## World Bank Escalation Timelines

For World Bank-funded projects, escalation timelines are stricter:
- Level 1-2: Must attempt resolution within 14-21 days
- Level 3-4: Within 30-45 days
- Full escalation cycle (all levels): Must not exceed 120 days total
- World Bank engagement: If not resolved after 120 days, project may face non-compliance issues
