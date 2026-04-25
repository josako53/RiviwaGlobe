# Staff Roles and GRM Workflow

## Staff Roles

### GRM Officer / GRM Staff
The primary case manager for feedback.

**Responsibilities:**
- Review newly submitted feedback
- Acknowledge receipt within SLA
- Assess validity and urgency
- Assign to committee if needed
- Investigate and take action
- Update status and communicate with submitter
- Escalate when required
- Close resolved cases

**System access:** Full case management — can view all feedback in their organisation/project, update status, add actions, escalate, resolve, close.

### GRM Committee
A group of stakeholders convened to review and decide on complex or sensitive grievances.

**Composition:** Typically includes: community representatives, local government officers, project technical staff, NGO representatives (for World Bank projects).

**Role:** Collective decision-making on contentious cases, especially:
- Land compensation disputes
- Resettlement disagreements
- Allegations against project staff

**System access:** Can be assigned feedback, add comments, record committee decisions.

### Focal Person
A community-level liaison who helps community members access the GRM.

**Responsibilities:**
- Help community members understand how to submit feedback
- Assist with submissions (especially for illiterate or elderly people)
- Communicate updates back to the community
- Report systemic issues to GRM Officers

**System access:** Limited — can submit feedback on behalf of others, view status of cases they submitted.

### Organisation Administrator
Manages the organisation's GRM setup.

**Responsibilities:**
- Configure projects and acceptance flags
- Manage staff accounts and roles
- Set up escalation paths
- Configure feedback categories
- View analytics and reports

### Platform Administrator (Riviwa)
Technical and platform-level administration.

## GRM Workflow — Case Lifecycle

```
SUBMITTED → ACKNOWLEDGED → IN_REVIEW → RESOLVED → CLOSED
                                ↓
                           ESCALATED
                                ↓
                           ACTIONED (for suggestions)
                           NOTED
                           DISMISSED
                           APPEALED
```

### Status Definitions

**SUBMITTED:** Feedback received, not yet reviewed by staff.

**ACKNOWLEDGED:** GRM Officer has read and acknowledged receipt. SLA clock starts here.

**IN_REVIEW:** Active investigation underway. Officer or committee is gathering information.

**ESCALATED:** Case has been moved to a higher authority level because it wasn't resolved at the current level.

**RESOLVED:** A resolution has been provided. The submitter is notified and can accept or appeal.

**ACTIONED:** For suggestions — the suggestion was accepted and action was taken.

**NOTED:** For suggestions or applause — received and recorded, no further action needed.

**DISMISSED:** The grievance was assessed as outside the project's scope or without merit. Reasons must be documented.

**APPEALED:** The submitter has filed an appeal against the resolution. Case re-opened for review.

**CLOSED:** Final state. Case fully completed.

## Actions (Case Notes)

Officers log all activities as actions:
- **Acknowledgement**: Initial receipt confirmation
- **Investigation**: Field visit, evidence gathering
- **Communication**: Letter, call, meeting with submitter
- **Committee Review**: Formal committee decision
- **Resolution**: Final decision and remedy offered
- **Closure**: Case closed after resolution accepted or appeal dismissed

Internal actions (not visible to submitter) vs public actions (visible for transparency).

## Notification Flow

| Event | Who is notified |
|---|---|
| Feedback submitted | GRM Officer (email/in-app) |
| Acknowledged | Consumer (SMS/WhatsApp/email) |
| Status updated | Consumer |
| Escalated | Next-level officer |
| Resolved | Consumer |
| Appeal filed | GRM Officer |
| SLA breach | Officer + supervisor |
