# Escalation Levels and Process

## Overview

Riviwa uses a hierarchical escalation system for grievances. If a complaint is not resolved satisfactorily at one level, it moves to a higher authority. This structure mirrors the World Bank Environmental and Social Framework (ESF) requirements.

## Escalation Hierarchy (Tanzania Infrastructure Projects)

### Level 1: Ward GRM Unit (WARD)
- **Who handles it**: Local GRM Officer at ward or project site level
- **SLA**: Acknowledge within 24 hours; resolve within 14 days
- **Suitable for**: Routine complaints about day-to-day construction activities, minor disputes, information requests
- **Examples**: Dust, noise, blocked access, minor property damage

### Level 2: LGA GRM Unit (LGA_GRM_UNIT)
- **Who handles it**: GRM Coordinator at the Local Government Authority (District Council)
- **SLA**: Acknowledge within 48 hours; resolve within 21 days
- **Suitable for**: Unresolved ward-level issues, compensation disputes, community-level impacts
- **Examples**: Land acquisition disputes, resettlement issues, livelihood impacts

### Level 3: Coordinating Unit (COORDINATING_UNIT)
- **Who handles it**: Project Implementation Unit (PIU) / Regional Coordinator
- **SLA**: Acknowledge within 72 hours; resolve within 30 days
- **Suitable for**: LGA-unresolved issues, cross-cutting issues affecting multiple wards, technical disputes
- **Examples**: Environmental damage, large-scale compensation issues, contractor misconduct

### Level 4: TARURA WBCU (TARURA_WBCU)
- **Who handles it**: World Bank Coordination Unit at TARURA headquarters
- **SLA**: Acknowledge within 5 days; resolve within 45 days
- **Suitable for**: Issues requiring national-level intervention, systemic failures, policy questions
- **Examples**: Repeated contractor violations, large unresolved compensation claims

### Level 5: TANROADS (TANROADS)
- **Who handles it**: Tanzania National Roads Agency
- **SLA**: Acknowledge within 7 days; resolve within 60 days
- **Suitable for**: National road network issues, major contractor disputes

### Level 6: World Bank (WORLD_BANK)
- **Who handles it**: World Bank project team (Washington D.C. / Dar es Salaam)
- **SLA**: Within 60 days
- **Suitable for**: Issues unresolved at all national levels, allegations of serious harm, fraud/corruption
- **Note**: This is the final escalation level. The World Bank can directly intervene in project implementation.

## How Escalation Works

1. Consumer submits grievance → assigned to Level 1 (Ward)
2. If not resolved within SLA, system flags as overdue
3. Consumer can **request escalation** if unsatisfied with response
4. GRM Officer can **escalate** to next level proactively
5. System records: from_level, to_level, reason, escalated_at, escalated_by
6. New level's team is notified
7. Consumer can track current level via tracking number

## Consumer Escalation Request

A consumer who is unsatisfied with a resolution can formally request escalation:
- Available when: feedback is not in CLOSED or DISMISSED status
- Cannot request if already at World Bank level
- Cannot request if there is already a pending escalation request
- Request goes to GRM Officer for approval/rejection
- Officer can approve (escalates) or reject (with explanation)

## Appeal Process

After a grievance is formally resolved:
- Consumer can **appeal** if dissatisfied
- Available only when: status = RESOLVED and consumer is not satisfied
- Appeal grounds must be stated
- Reviewed by higher authority
- Possible outcomes: upheld (re-open), partially upheld, dismissed
- If still unsatisfied: referral to court or mediator

## Escalation Path Configuration

Organisations can define custom escalation paths for their projects. The escalation path determines which levels are used and in what order. This allows non-road projects (water, health, education) to use relevant institutional hierarchies.
