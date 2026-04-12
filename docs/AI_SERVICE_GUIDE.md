# Riviwa AI Service — Deep Technical Guide

> **Service port:** 8085 | **DB:** `ai_db` (PostgreSQL 5440) | **Vector store:** Qdrant 6333  
> **LLM:** Groq `llama-3.3-70b-versatile` (primary) → local Ollama `llama3.2:3b` (fallback)  
> **Embeddings:** `all-MiniLM-L6-v2` (384-dim cosine, via `sentence-transformers`)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [The Three Knowledge Layers](#2-the-three-knowledge-layers)
3. [Qdrant Collections in Detail](#3-qdrant-collections-in-detail)
4. [Obsidian RAG Pipeline](#4-obsidian-rag-pipeline)
5. [Project Knowledge Base (Kafka-Driven)](#5-project-knowledge-base-kafka-driven)
6. [Stakeholder Cache](#6-stakeholder-cache)
7. [Conversation Flow — Step by Step](#7-conversation-flow--step-by-step)
8. [Auto-Classification Pipeline](#8-auto-classification-pipeline)
9. [How to Train / Update the Knowledge Base](#9-how-to-train--update-the-knowledge-base)
10. [Dynamic Improvement Over Time](#10-dynamic-improvement-over-time)
11. [Configuration Reference](#11-configuration-reference)
12. [Operational Runbook](#12-operational-runbook)

---

## 1. Architecture Overview

```
PAP (SMS / WhatsApp / Web / Mobile)
        │
        ▼
  ai_service:8085
        │
        ├── PostgreSQL ai_db ──────────── ai_conversations (turns, extracted fields)
        │                                 ai_project_kb    (project mirror)
        │                                 ai_stakeholder_cache
        │
        ├── Qdrant :6333 ─────────────── ai_projects       (project embeddings)
        │                                 riviwa_knowledge  (Obsidian vault chunks)
        │                                 ai_feedback_kb    (future: indexed feedback)
        │
        ├── Groq API / Ollama ──────────── LLM (conversation + classification)
        │
        ├── feedback_service:8090 ──────── POST /feedback (submit)
        │                                  GET  /feedback/{ref} (follow-up lookup)
        │
        ├── riviwa_auth_service:8000 ────── GET /users/by-phone (check registration)
        │                                   POST /users/register-pap
        │
        └── Kafka consumer ─────────────── riviwa.organisation.events → project sync
                                           riviwa.stakeholder.events → stakeholder sync
                                           riviwa.feedback.events → auto-classification
```

---

## 2. The Three Knowledge Layers

The AI service uses **three distinct knowledge sources**, each serving a different purpose:

| Layer | Storage | Purpose | Update Mechanism |
|-------|---------|---------|-----------------|
| **Project KB** | Qdrant `ai_projects` + PostgreSQL `ai_project_kb` | Match a PAP's location description to the right project | Kafka event `project.published` / `project.updated` |
| **Obsidian Vault** | Qdrant `riviwa_knowledge` | Answer GRM procedure questions; ground replies in org policy | Manual vault edit → `POST /api/v1/ai/admin/reindex-vault` |
| **Conversation History** | PostgreSQL `ai_conversations` | Maintain multi-turn context within a session | Written every turn, read at session resume |

---

## 3. Qdrant Collections in Detail

### 3.1 `ai_projects` — Project Location Index

**Purpose:** Semantic search to identify which infrastructure project a PAP is referring to based on their natural-language location description.

**Vector size:** 384 (all-MiniLM-L6-v2)  
**Distance metric:** Cosine  
**Search threshold:** 0.40 (score must be ≥ 0.40 to count as a match)

**What gets embedded:**
```
"{project_name} {description} {region} {primary_lga} {wards...} {keywords...}"
```

Example searchable text for a project:
```
"Mwanza–Shinyanga Highway Upgrading Road construction in Mwanza Region 
 Mwanza Ilemela Nyakato Buswelu Mkolani"
```

**Point structure in Qdrant:**
```json
{
  "id": "47f208ee-7c15-4641-81eb-936c18c590c7",
  "vector": [0.021, -0.043, 0.117, ...],
  "payload": {
    "project_id": "47f208ee-7c15-4641-81eb-936c18c590c7",
    "name": "Mwanza–Shinyanga Highway Upgrading",
    "region": "Mwanza",
    "primary_lga": "Ilemela",
    "organisation_id": "c1e3a9f2-...",
    "status": "active"
  }
}
```

**How a PAP message triggers a search:**

When the PAP says _"There is a big pothole near Nyakato junction on the tarmac road"_, the service:

1. Extracts location fields from the LLM response: `issue_location_description="Nyakato junction"`, `lga="Ilemela"`
2. Builds query: `"Nyakato junction Ilemela"`
3. Encodes query → 384-dim vector using `all-MiniLM-L6-v2`
4. Calls `qdrant.search(collection="ai_projects", query_vector=..., limit=1, score_threshold=0.40)`
5. If score ≥ 0.40: sets `conv.project_id` and `conv.project_name` on the conversation
6. Falls back to keyword ILIKE search in PostgreSQL if Qdrant returns no results

### 3.2 `riviwa_knowledge` — Obsidian Policy Vault

**Purpose:** Retrieve relevant GRM procedure excerpts, policy rules, and org-specific knowledge to inject into the system prompt as grounding context.

**Vector size:** 384  
**Distance metric:** Cosine  
**Search threshold:** 0.30 (lower — policy docs are more loosely related)

**What gets indexed:**
- Every `.md` file inside `OBSIDIAN_VAULT_PATH` (default: `/opt/riviwa/obsidian_vault/`)
- Split by `#`, `##`, `###` headers → individual chunks
- Long sections (> `RAG_CHUNK_SIZE_WORDS` = 300 words) → further split by paragraph

**Point structure:**
```json
{
  "id": "uuid5(NAMESPACE_URL, 'path/to/file.md:3')",
  "vector": [...],
  "payload": {
    "text": "## Escalation Policy\n\nAll CRITICAL grievances must be...",
    "source": "GRM_Policy.md",
    "chunk_id": "GRM_Policy.md:3",
    "file": "policies/GRM_Policy.md"
  }
}
```

**How it injects into the prompt:**

At every turn, the PAP's message is searched against `riviwa_knowledge`. The top 3 matching chunks are prepended to the system prompt:

```
--- KNOWLEDGE BASE CONTEXT ---

[Source: GRM_Policy.md]
## Escalation Policy
All CRITICAL grievances must be escalated to the PIU coordinator within 4 hours...

[Source: Compensation_Guide.md]
## Land Compensation Procedures
PAPs affected by land acquisition are entitled to replacement cost...

--- END CONTEXT ---

You are Riviwa AI, a GRM assistant for World Bank infrastructure projects...
```

### 3.3 `ai_feedback_kb` — Feedback Knowledge Base (Future)

Reserved collection name (`QDRANT_COLLECTION_FEEDBACK = "ai_feedback_kb"`). Currently not populated. Intended for indexing resolved feedback to enable similarity-based suggestions to officers ("this is similar to GRV-2025-0012 which was resolved by…").

---

## 4. Obsidian RAG Pipeline

### 4.1 Vault Structure

Organise your vault as markdown files. The indexer recursively scans all `.md` files:

```
/opt/riviwa/obsidian_vault/
├── policies/
│   ├── GRM_Policy.md
│   ├── Compensation_Guide.md
│   └── Escalation_Procedures.md
├── projects/
│   ├── Mwanza_Highway_FAQ.md
│   └── Dodoma_Water_Project.md
├── categories/
│   ├── Land_Acquisition.md
│   └── Construction_Impact.md
└── scripts/
    └── SLA_Targets.md
```

### 4.2 How Chunking Works

```
File: GRM_Policy.md
│
├── Header split on /\n(?=#{1,3} )/
│     ├── Chunk 0: "# Overview\nGRM stands for..."            (< 300 words → 1 chunk)
│     ├── Chunk 1: "## Submission Channels\n..."              (< 300 words → 1 chunk)
│     └── Chunk 2: "## Escalation Policy\n..." (> 300 words)
│           ├── Sub-chunk 2a: first 300-word paragraph block
│           └── Sub-chunk 2b: remainder
│
└── Chunks with < 10 words are skipped (headers without content)
```

Each chunk gets a deterministic UUID:
```python
point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "policies/GRM_Policy.md:2"))
```

This means re-indexing the same file **updates** existing points rather than creating duplicates.

### 4.3 Triggering a Re-index

**Via API (admin only):**
```http
POST /api/v1/ai/admin/reindex-vault
Authorization: Bearer <staff_jwt>
```

**Via Docker exec (direct):**
```bash
docker compose exec ai_service python -c "
import asyncio
from services.obsidian_rag_service import get_obsidian_rag
svc = get_obsidian_rag()
total = svc.index_vault()
print(f'Indexed {total} chunks')
"
```

**On service startup:** The vault is indexed automatically at startup if `OBSIDIAN_VAULT_PATH` exists.

### 4.4 Writing Effective Vault Documents

| Do | Avoid |
|----|-------|
| Use clear `##` headers to separate topics | Large undivided blocks of text |
| Write in the same language PAPs use (Swahili + English) | Jargon-only content without plain-language explanation |
| Include specific project names, LGAs, ward names | Generic statements that apply to nothing specifically |
| Document category definitions with examples | Duplicate content across files |
| Add FAQ sections ("What if my land was taken without notice?") | Tables — they don't embed well |

---

## 5. Project Knowledge Base (Kafka-Driven)

### 5.1 Two-Layer Storage

Every project lives in two places simultaneously:

```
auth_service publishes project.published
        │
        ▼
Kafka topic: riviwa.organisation.events
        │
        ▼
ai_service consumer (_upsert_project)
        │
        ├─► PostgreSQL ai_project_kb  ←── queries: list_active(), keyword_search()
        │   (structured data, fast queries)
        │
        └─► Qdrant ai_projects  ←── semantic search_projects()
            (vector embeddings, similarity search)
```

### 5.2 What Triggers an Update

| Kafka Event | Action |
|------------|--------|
| `project.published` | Insert/upsert in `ai_project_kb`, embed into Qdrant with `status="active"` |
| `project.updated` | Re-upsert both; re-embeds with new text (name/description/region changes are reflected immediately) |
| `project.paused` | Status → `"paused"` in both; project still in Qdrant but won't appear in `list_active()` |
| `project.resumed` | Status → `"active"` again |
| `project.completed` | Status → `"completed"` |
| `project.cancelled` | Status → `"cancelled"` |
| `project_stage.activated` | Updates `active_stage_name` in `ai_project_kb` only |

### 5.3 The `ai_project_kb` Table

```
Column                Type      Description
─────────────────     ────────  ─────────────────────────────────────────
id                    UUID      Internal PK
project_id            UUID      FK reference to auth_service project
organisation_id       UUID      FK reference to organisation
name                  str(300)  Project display name
slug                  str(200)  URL slug
description           text      Full description (embedded into Qdrant)
region                str(100)  Tanzanian region (e.g. "Mwanza")
primary_lga           str(100)  Main LGA (e.g. "Ilemela")
wards                 JSONB     {"wards": ["Nyakato", "Buswelu", ...]}
keywords              JSONB     {"keywords": ["highway", "road", "tarmac"]}
active_stage_name     str(200)  Current project stage name
status                str(30)   active | paused | completed | cancelled
accepts_grievances    bool      Whether project takes grievances
accepts_suggestions   bool      Whether project takes suggestions
accepts_applause      bool      Whether project takes applause
vector_indexed        bool      True once Qdrant upsert succeeded
synced_at             datetime  Last Kafka sync timestamp
```

### 5.4 Manually Adding / Updating a Project

If a project wasn't published via Kafka (e.g. imported from a spreadsheet), you can index it directly:

```python
# Inside the ai_service container
from services.rag_service import get_rag
import uuid

rag = get_rag()
project_id = uuid.UUID("your-project-uuid")
searchable_text = "Dodoma Water Supply Phase 2 Clean water infrastructure Dodoma Chamwino Nzuguni Mvumi"

rag.index_project(
    project_id=project_id,
    searchable_text=searchable_text,
    metadata={
        "name": "Dodoma Water Supply Phase 2",
        "region": "Dodoma",
        "primary_lga": "Chamwino",
        "organisation_id": "org-uuid-here",
        "status": "active",
    }
)
```

To **improve match quality**, enrich the searchable text with more location identifiers, common misspellings, and local name variants:
```python
searchable_text = (
    "Dodoma Water Supply Phase 2 maji Dodoma "
    "Chamwino Nzuguni Mvumi Idifu Mtera "  # wards
    "bwawa maji safi bomba"  # Swahili keywords PAPs might use
)
```

---

## 6. Stakeholder Cache

### 6.1 Purpose

When a PAP's submission is marked `is_urgent=true` by the LLM (safety hazard, blocked road, etc.), the service looks up the **project incharge** contact and appends their name and phone number to the reply so the PAP can reach them directly.

### 6.2 The `ai_stakeholder_cache` Table

```
Column           Type      Description
──────────────   ────────  ──────────────────────────────────────────
id               UUID      Internal PK
stakeholder_id   UUID      FK reference to stakeholder_service
project_id       UUID      Project this stakeholder is assigned to
organisation_id  UUID
name             str(300)  Full name
phone            str(30)   Contact phone
email            str(200)  Contact email
role             str(100)  Role string (e.g. "PIU Officer", "incharge")
is_incharge      bool      True if role contains: incharge/coordinator/piu/officer/director
lga              str(100)  LGA assignment
synced_at        datetime  Last Kafka sync
```

### 6.3 Incharge Detection Logic

The consumer auto-detects the incharge flag by scanning the role string:
```python
is_incharge = any(kw in role.lower() for kw in ("incharge", "coordinator", "piu", "officer", "director"))
```

To ensure the correct person is flagged, use one of those keywords in the stakeholder's `role` field in `stakeholder_service`.

### 6.4 Urgency Escalation Flow

```
PAP: "The bridge collapsed and cars cannot pass. People are in danger!"
        │
        ▼
LLM extracts: is_urgent=true
        │
        ▼
StakeholderCacheRepository.get_incharge_for_project(conv.project_id)
        │
        ▼
Appends to reply:
"⚠️ This issue appears urgent. Please contact the Project Officer
 (Eng. John Mwanga) directly at: +255712345678."
```

---

## 7. Conversation Flow — Step by Step

### 7.1 Session Lifecycle

```
START
  │
  ├─ start_conversation()
  │    ├─ Load active projects from ai_project_kb
  │    ├─ Build greeting (language + numbered project list)
  │    ├─ Check PAP registration by phone (auth_service)
  │    └─ Store GREETING turn, stage=GREETING
  │
  ├─ process_message() — repeated per turn
  │    ├─ Timeout check (SESSION_TIMEOUT_MINUTES=60)
  │    ├─ Follow-up check (regex: GRV|SGG|APP-YYYY-NNNN)
  │    │    └─ If match → _handle_followup() → status lookup → return
  │    │
  │    ├─ Build project context string (list_active → build_project_context)
  │    ├─ Search Obsidian vault (obsidian_rag.search(message))
  │    ├─ Call Groq/Ollama (system prompt + project context + vault context + turns)
  │    │
  │    ├─ Merge extracted fields into conv.extracted_data
  │    ├─ Auto-identify project (_identify_project via Qdrant)
  │    ├─ Try PAP registration if name extracted + phone known
  │    ├─ Urgency check → attach incharge contact if is_urgent=true
  │    ├─ Update stage (continue → COLLECTING, confirm → CONFIRMING, etc.)
  │    │
  │    └─ Auto-submit check:
  │         action IN ("submit","confirm") AND confidence >= 0.82
  │              └─ _submit_feedback() → feedback_service POST /feedback
  │                   └─ conv.status = SUBMITTED, stage = DONE
  │
  └─ END (SUBMITTED / ABANDONED / TIMED_OUT / FAILED)
```

### 7.2 The LLM Response Contract

The LLM is instructed to **always return JSON only** (no markdown). The service parses and validates the response:

```json
{
  "reply": "The natural language reply shown to the PAP (in their language)",
  "extracted": {
    "feedback_type": "grievance | suggestion | applause | unknown",
    "subject": "Short summary title",
    "description": "Full detailed description",
    "issue_location_description": "Where the problem is",
    "ward": null,
    "lga": null,
    "region": null,
    "date_of_incident": null,
    "is_anonymous": false,
    "submitter_name": null,
    "category_slug": "other",
    "language": "sw",
    "confidence": 0.0,
    "ready_to_submit": false,
    "is_followup": false,
    "followup_ref": null,
    "is_urgent": false,
    "multiple_issues": false,
    "feedback_items": []
  },
  "action": "continue | confirm | submit | followup | done"
}
```

**Confidence** climbs as the PAP provides more detail. At ≥ 0.80 the LLM switches to summary + confirmation mode (`action="confirm"`). At ≥ 0.82 (`AUTO_SUBMIT_CONFIDENCE`) and after confirmation, the service auto-submits.

### 7.3 Stage Transitions

```
GREETING → IDENTIFY (if unregistered and name needed)
GREETING → COLLECTING (if registered or anonymous)
COLLECTING → CLARIFYING (LLM needs more info)
CLARIFYING → COLLECTING
COLLECTING → CONFIRMING (confidence >= 0.80)
CONFIRMING → DONE (after submission)
any → FOLLOWUP (GRV/SGG/APP reference detected)
any → DONE (abandoned / timed out)
```

### 7.4 Multi-Issue Handling

If the PAP mentions multiple problems in one conversation, the LLM sets `multiple_issues=true` and fills `feedback_items[]`:

```json
"extracted": {
  "multiple_issues": true,
  "feedback_items": [
    {"feedback_type": "grievance", "subject": "Road dust", "description": "...", "category_slug": "construction-impact"},
    {"feedback_type": "grievance", "subject": "Blocked well", "description": "...", "category_slug": "environmental"}
  ]
}
```

Each item is submitted as a separate feedback record. The PAP receives multiple reference numbers in the confirmation message.

---

## 8. Auto-Classification Pipeline

When any feedback reaches `feedback_service` (from any channel, not just AI), the service publishes `feedback.submitted` to Kafka. The `ai_service` consumer picks this up and runs background enrichment:

```
feedback.submitted event
        │
        ▼
_classify_submitted_feedback()
        │
        ├─ Fetch full feedback from feedback_service GET /feedback/{id}/for-ai
        ├─ Skip if project_id AND category_def_id already set
        │
        ├─ _run_ollama_classification()
        │    ├─ Build query from description + location fields
        │    ├─ Search Qdrant ai_projects (top 5, threshold 0.30) for context
        │    └─ Call Ollama with classification prompt (temperature=0.1, max_tokens=200)
        │         └─ Returns: {category_slug, category_confidence, project_id, project_confidence}
        │
        ├─ _resolve_category_def_id(slug, project_id)
        │    └─ GET /api/v1/categories?status=active → find matching slug → return UUID
        │
        ├─ _resolve_project_id(ollama_suggestion, feedback_data)
        │    ├─ Validate Ollama's UUID suggestion
        │    └─ Fallback: Qdrant search (threshold 0.45, stricter)
        │
        └─ PATCH /feedback/{id}/ai-enrich  {project_id, category_def_id, note}
```

**Category slugs available for classification:**
```
compensation, resettlement, land-acquisition, construction-impact, traffic,
worker-rights, safety-hazard, environmental, engagement, design-issue,
project-delay, corruption, communication, accessibility, design, process,
community-benefit, employment, quality, timeliness, staff-conduct,
community-impact, responsiveness, safety, other
```

---

## 9. How to Train / Update the Knowledge Base

There are **four independent ways** to improve the AI's knowledge, each targeting a different layer:

### 9.1 Improve Project Matching (Qdrant `ai_projects`)

**When to use:** The AI incorrectly assigns a PAP to the wrong project, or fails to identify any project.

**Method A — Enrich project description in auth_service**

The best fix is upstream: edit the project in `auth_service` to add more detail to `description`, `region`, `primary_lga`, and wards. The Kafka event `project.updated` will auto-re-index.

**Method B — Add keywords to `ai_project_kb` directly**

```bash
docker compose exec ai_db psql -U ai_admin -d ai_db -c "
UPDATE ai_project_kb
SET keywords = '{\"keywords\": [\"bwawa\", \"daraja\", \"bomba\", \"maji\", \"Chamwino\"]}'
WHERE project_id = 'your-project-uuid';
"
```

Then re-index that project:
```bash
docker compose exec ai_service python -c "
import asyncio
from db.session import AsyncSessionLocal
from repositories.conversation_repo import ProjectKBRepository
from services.rag_service import get_rag
import uuid

async def run():
    async with AsyncSessionLocal() as db:
        repo = ProjectKBRepository(db)
        p = await repo.get_by_project_id(uuid.UUID('your-project-uuid'))
        text = p.get_searchable_text()
        rag = get_rag()
        ok = rag.index_project(p.project_id, text, {'name': p.name, 'region': p.region, 'primary_lga': p.primary_lga, 'status': p.status, 'organisation_id': str(p.organisation_id)})
        print('Indexed:', ok)

asyncio.run(run())
"
```

**Method C — Adjust search threshold**

In `.env`, lower `QDRANT_SCORE_THRESHOLD` for broader matching (risk: false matches), or raise it for stricter matching:

```env
# Default is hardcoded at 0.40 in rag_service.py
# To change, override in conversation_service._identify_project():
# results = self.rag.search_projects(query, top_k=1, score_threshold=0.35)
```

### 9.2 Improve Policy Answers (Qdrant `riviwa_knowledge`)

**When to use:** The AI gives incorrect, generic, or incomplete answers about GRM procedures, SLA targets, or project-specific rules.

**Step 1: Edit or add a markdown file in the Obsidian vault**

```bash
# On the server
nano /opt/riviwa/obsidian_vault/policies/GRM_Policy.md
```

Write clear sections under `##` headers. Keep each section focused on one topic.

**Step 2: Re-index the vault**

```bash
# Via API (preferred — no downtime)
curl -X POST https://riviwa.com/api/v1/ai/admin/reindex-vault \
  -H "Authorization: Bearer <staff_jwt>"

# Via docker exec (alternative)
docker compose exec ai_service python -c "
from services.obsidian_rag_service import get_obsidian_rag
total = get_obsidian_rag().index_vault()
print(f'Indexed {total} chunks')
"
```

Re-indexing is idempotent: same file → same deterministic UUID → upsert (no duplicates).

**Step 3: Verify**

```bash
docker compose exec ai_service python -c "
from services.obsidian_rag_service import get_obsidian_rag
results = get_obsidian_rag().search('what is the SLA for critical grievances', top_k=3)
for text, score, source in results:
    print(f'[{score:.3f}] {source}: {text[:100]}')
"
```

### 9.3 Update the System Prompt

**When to use:** The AI's conversational behavior needs to change (e.g., new questions to ask, different summary format, new feedback types).

Edit `services/ollama_service.py`, line 18-30, the `_SYSTEM_PROMPT` string, then restart:

```bash
docker compose up -d --build ai_service
```

Key parts you can tune:

| Section | What it controls |
|---------|-----------------|
| `Collect naturally: description, location...` | Which fields the LLM tries to extract |
| `Mark is_urgent=true for safety hazards or blocked roads.` | What triggers urgency escalation |
| `At confidence≥0.80 show summary...` | When the LLM switches to confirmation mode |
| The JSON schema at the bottom | Shape of the extracted data object |

### 9.4 Add New Category Slugs (Auto-Classification)

If a new issue category is added to `feedback_service`, add its slug to `_CATEGORY_SLUGS` in `services/classification_service.py`:

```python
_CATEGORY_SLUGS = [
    "compensation", "resettlement", ...,
    "water-supply",   # NEW
    "noise-pollution", # NEW
]
```

Then rebuild:
```bash
docker compose up -d --build ai_service
```

---

## 10. Dynamic Improvement Over Time

### 10.1 Using Conversation Data

Every submitted conversation is stored in `ai_conversations` with the full transcript and extracted fields. This is the richest source of ground-truth training data.

**Query for low-confidence submissions (candidates for review):**
```sql
SELECT id, phone_number, project_name, channel,
       (extracted_data->>'confidence')::float AS confidence,
       extracted_data->>'subject' AS subject,
       started_at
FROM ai_conversations
WHERE status = 'submitted'
  AND (extracted_data->>'confidence')::float < 0.75
ORDER BY started_at DESC;
```

**Query for conversations that failed to identify a project:**
```sql
SELECT id, channel, turn_count, started_at,
       extracted_data->>'issue_location_description' AS location
FROM ai_conversations
WHERE status IN ('submitted', 'timed_out', 'abandoned')
  AND project_id IS NULL
ORDER BY started_at DESC;
```

Use these to:
- Identify which locations are being missed → add those ward/LGA names to project keywords
- Find common complaint themes → create or update Obsidian documents
- Spot language patterns the LLM misunderstands → refine the system prompt

### 10.2 Feedback Loop from GRM Officers

When a GRM officer changes the project or category on a feedback record (overriding the AI classification), that correction is implicit training signal. You can query mismatches:

```sql
-- In feedback_db: find cases where ai enrichment note exists
-- but the officer later changed the category
SELECT unique_ref, category, feedback_type, submitted_at
FROM feedbacks
WHERE id IN (
    SELECT feedback_id FROM feedback_actions
    WHERE action_type = 'ai_enriched'
)
AND category != (
    SELECT enriched_category FROM feedback_actions
    WHERE feedback_id = feedbacks.id AND action_type = 'ai_enriched'
    LIMIT 1
);
```

### 10.3 Scheduled Vault Refresh

For organisations that maintain their Obsidian vault actively, automate nightly re-indexing:

```bash
# Add to crontab on server or as a Docker cron job
0 2 * * * curl -s -X POST http://localhost:8085/api/v1/ai/admin/reindex-vault \
  -H "X-Service-Key: your_internal_key" >> /var/log/vault_reindex.log 2>&1
```

### 10.4 Improving Confidence Calibration

If the AI auto-submits too eagerly (low quality submissions):
```env
AUTO_SUBMIT_CONFIDENCE=0.88   # raise threshold (default 0.82)
```

If the AI asks too many clarifying questions (PAPs drop off):
```env
AUTO_SUBMIT_CONFIDENCE=0.75   # lower threshold
```

### 10.5 Embedding Model Upgrade Path

When upgrading the embedding model (e.g. to `all-mpnet-base-v2` at 768 dims):

1. Update `.env`:
   ```env
   EMBEDDING_MODEL=all-mpnet-base-v2
   ```
2. **Delete both Qdrant collections** (old 384-dim vectors are incompatible with 768-dim):
   ```python
   from qdrant_client import QdrantClient
   client = QdrantClient(host="qdrant", port=6333)
   client.delete_collection("ai_projects")
   client.delete_collection("riviwa_knowledge")
   ```
3. Update `VECTOR_SIZE = 768` in both `rag_service.py` and `obsidian_rag_service.py`
4. Restart `ai_service` — `_ensure_collection()` recreates collections at startup
5. Trigger vault re-index: `POST /api/v1/ai/admin/reindex-vault`
6. Re-publish all projects via Kafka or run the manual bulk re-index script

---

## 11. Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | `""` | If set, routes all chat through Groq instead of local Ollama |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model to use |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Fallback local LLM URL |
| `OLLAMA_MODEL` | `llama3.2:3b` | Fallback local model |
| `OLLAMA_TIMEOUT_SECS` | `60` | Max seconds to wait for LLM response |
| `QDRANT_HOST` | `qdrant` | Qdrant container hostname |
| `QDRANT_PORT` | `6333` | Qdrant gRPC/HTTP port |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | HuggingFace model for embeddings |
| `EMBEDDING_MODEL_PATH` | `/models/sentence-transformers` | Local cache dir for model weights |
| `QDRANT_COLLECTION_PROJECTS` | `ai_projects` | Collection for project vectors |
| `QDRANT_COLLECTION_KNOWLEDGE` | `riviwa_knowledge` | Collection for vault vectors |
| `OBSIDIAN_VAULT_PATH` | `/opt/riviwa/obsidian_vault` | Directory of `.md` knowledge files |
| `RAG_CHUNK_SIZE_WORDS` | `300` | Max words per vault chunk |
| `RAG_TOP_K` | `3` | Number of vault chunks to inject per turn |
| `AUTO_SUBMIT_CONFIDENCE` | `0.82` | Confidence threshold for auto-submit |
| `MAX_TURNS_BEFORE_TIMEOUT` | `30` | Max turns before session ends |
| `SESSION_TIMEOUT_MINUTES` | `60` | Idle timeout in minutes |
| `WHATSAPP_VERIFY_TOKEN` | `riviwa_ai_webhook_verify` | Meta webhook verification token |

---

## 12. Operational Runbook

### Check if Qdrant collections exist and have vectors

```bash
curl http://localhost:6333/collections | python3 -m json.tool
curl http://localhost:6333/collections/ai_projects | python3 -m json.tool
curl http://localhost:6333/collections/riviwa_knowledge | python3 -m json.tool
```

### Force re-index all projects from the DB

```bash
docker compose exec ai_service python -c "
import asyncio
from db.session import AsyncSessionLocal
from repositories.conversation_repo import ProjectKBRepository
from services.rag_service import get_rag

async def run():
    async with AsyncSessionLocal() as db:
        repo = ProjectKBRepository(db)
        projects = await repo.list_active()
        rag = get_rag()
        n = 0
        for p in projects:
            text = p.get_searchable_text()
            ok = rag.index_project(p.project_id, text, {
                'name': p.name, 'region': p.region or '',
                'primary_lga': p.primary_lga or '',
                'organisation_id': str(p.organisation_id),
                'status': p.status,
            })
            if ok:
                n += 1
        print(f'Re-indexed {n}/{len(projects)} projects')

asyncio.run(run())
"
```

### Check conversation statistics

```bash
docker compose exec ai_db psql -U ai_admin -d ai_db -c "
SELECT status, channel, COUNT(*) as count
FROM ai_conversations
GROUP BY status, channel
ORDER BY status, count DESC;
"
```

### Clear stuck ACTIVE sessions older than 2 hours

```bash
docker compose exec ai_db psql -U ai_admin -d ai_db -c "
UPDATE ai_conversations
SET status = 'timed_out'
WHERE status = 'active'
  AND last_active_at < NOW() - INTERVAL '2 hours';
"
```

### Inspect Obsidian vault chunks in Qdrant

```python
from qdrant_client import QdrantClient
client = QdrantClient(host="qdrant", port=6333)
result = client.scroll(collection_name="riviwa_knowledge", limit=10, with_payload=True)
for point in result[0]:
    print(point.payload.get("source"), "→", point.payload.get("text")[:80])
```
