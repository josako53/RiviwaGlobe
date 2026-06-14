---
tags: [industry-kb, field-standards, feedback-fields, construction, real-estate-development]
---
# Construction / Real Estate Development — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: ujenzi, construction, contractor, mkandarasi, developer, msanidi, building, jengo, nyumba, house, flat, apartment, apartment block, compound, plot, kiwanja, site, eneo la ujenzi, foundation, msingi, roof, paa, cement, saruji, tiles, vigae, painting, kupiga rangi, electrical installation, ufungaji wa umeme, plumbing, mfumo wa maji, drainage, mfereji, defects, mapungufu ya ujenzi, snagging, handover, kukabidhiwa nyumba, delay, kuchelewa kwa ujenzi, engineer, mhandisi, architect, msanifu, BRN, ERB, AQRB, Tanzania Engineers Registration Board, Tanzania Architects and Quantity Surveyors Registration Board, building permit, ruhusa ya ujenzi, occupancy certificate, cheti cha kukaa, municipality, manispaa, off-plan, construction bond, hatua za ujenzi, progress payment, payment milestone, retention, malipo ya ahadi, defect liability period, muda wa ujibu wa mapungufu, punch list, contractor dispute, contract termination

## Why Industry-Specific Fields Matter

Construction complaints span defective construction (requiring building permit number, contractor registration, specific defect description), developer fraud (requiring sale agreement number, payment history), contract disputes (requiring contract reference and payment milestones), and regulatory violations (requiring building permit number and ERB/AQRB investigation). Without construction-specific fields, the AI cannot generate a BRELA/ERB regulatory complaint or establish whether the contractor is licensed, making enforcement action impossible.

## Source Standards

- Tanzania Building (Construction) Regulations under Local Government Acts
- Tanzania Engineers Registration Board (ERB) Act — contractor and engineer licensing
- Tanzania Architects and Quantity Surveyors Registration Board (AQRB) Act
- Tanzania Contractors Registration Board (CRB) Act and Regulations
- Land Act, Cap. 113 and Land Regulations — property rights
- Tanzania Fair Competition Act, Cap. 285 — developer consumer protection
- Tanzania Law of Contract Act, Cap. 433 — construction contract enforcement
- FIDIC Conditions of Contract (Red/Yellow/Silver books) — international reference for construction contracts
- ISO 10002:2018 — complaints handling
- Local Government (Urban Authorities) Act, Cap. 288 — building permits and inspections

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL construction / development complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Complaint registration; contract lookup |
| complainant_phone | Nambari ya simu | Yes | Status updates |
| developer_or_contractor_name | Jina la msanidi / mkandarasi | Yes | Regulated entity identification; CRB/ERB/AQRB lookup |
| project_name | Jina la mradi | Yes | Project identification |
| project_location | Mahali pa mradi | Yes | For local authority and geographic routing |
| contract_reference | Nambari ya mkataba | Yes | Core contractual identifier |
| contract_value_tzs | Thamani ya mkataba (TZS) | Yes | For dispute quantification and regulatory threshold |
| amount_paid_tzs | Kiasi kilicholipwa (TZS) | Yes | For financial dispute quantification |
| building_permit_number | Nambari ya ruhusa ya ujenzi | Conditional | Required for unauthorized construction complaints |
| contractor_crb_number | Nambari ya usajili wa CRB | Recommended | CRB can verify contractor license and class |
| engineer_erb_number | Nambari ya usajili wa ERB (mhandisi) | Conditional | For engineering negligence complaints |
| handover_date_agreed | Tarehe ya kukabidhiwa iliyokubaliwa | Conditional | For delay complaints |
| handover_date_actual | Tarehe ya kukabidhiwa halisi | Conditional | For delay damages calculation |
| issue_type | Aina ya tatizo | Yes | Complaint taxonomy |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; detailed narrative |
| photos_available | Je, picha za tatizo zinapatikana? | Yes | Critical evidence for structural and defect complaints |
| desired_outcome | Matokeo unayotaka | Yes | Repair / Completion / Refund / Compensation / Regulatory action |

### Conditional Fields (collect based on issue type)

**If issue_type = Structural Defect / Poor Construction Quality:**
Also collect:
- `defect_type` — Aina ya mapungufu: Cracks / Leaking roof / Subsidence / Poor finishing / Faulty electrical / Plumbing failure
- `defect_location_in_building` — Mahali pa mapungufu kwenye jengo: Foundation / Walls / Roof / Floor / Wiring / Plumbing
- `independent_engineer_report` — Je, ripoti ya mhandisi huru ipo?: ERB-registered engineer assessment
- `occupancy_status` — Je, jengo linalokumiwa? Yes / No: Occupied buildings with structural defects are safety emergencies
- `defect_liability_period_status` — Je, bado tuko ndani ya muda wa ujibu wa mapungufu (DLP)?: Most contracts = 12 months; within DLP = contractor's obligation to repair

**If issue_type = Construction Delay:**
Also collect:
- `original_completion_date` — Tarehe ya kukamilika iliyoahidiwa kwenye mkataba
- `current_expected_completion` — Tarehe ya kukamilika inayotarajiwa sasa
- `delay_cause_given` — Sababu ya kuchelewa iliyotolewa na mkandarasi
- `extension_of_time_granted` — Je, muda wa ziada ulitolewa rasmi? Yes / No: FIDIC requires formal EOT notices
- `loss_and_expense_incurred_tzs` — Hasara na gharama zilizotokana na kuchelewa (TZS): Rental, hotel, business loss

**If issue_type = Developer / Off-Plan Fraud:**
Also collect:
- `sale_agreement_reference` — Nambari ya mkataba wa mauzo ya nyumba
- `payment_schedule` — Ratiba ya malipo
- `payments_made_evidence` — Ushahidi wa malipo yaliyofanywa: Receipts, bank transfers
- `title_deed_transfer_promised` — Je, uhamishaji wa hati ya ardhi uliahidiwa? Yes / No
- `title_deed_transferred` — Je, hati ya ardhi imehamishiwa? Yes / No
- `brela_developer_registration` — Je, msanidi amesajiliwa BRELA? Yes / No
- `other_buyers_affected` — Je, wanunuzi wengine wameathirika pia? Yes / No: Fraud pattern indicator

**If issue_type = Non-Payment / Contract Dispute (contractor is complainant):**
Also collect:
- `payment_milestone_due` — Kiwango cha malipo kinachostahili
- `work_completed_percentage` — Asilimia ya kazi iliyokamilika
- `client_approval_of_work` — Je, mteja alithibitisha kazi? Yes / No
- `payment_certificate_issued` — Je, cheti cha malipo kilitolewa?: FIDIC requires payment certificates

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| CN-01 | structural_defect | Structural failure, cracks, subsidence, unsafe construction |
| CN-02 | poor_finishing | Poor quality finishes below contract standard |
| CN-03 | construction_delay | Project significantly delayed beyond contracted date |
| CN-04 | developer_fraud | Off-plan developer collected money but no construction or title |
| CN-05 | contract_breach | Contractor/developer breached specific contract terms |
| CN-06 | non_payment | Client not paying contractor per agreed milestones |
| CN-07 | unauthorized_construction | Building without permit or outside approved plans |
| CN-08 | title_transfer_delay | Developer refusing or delaying property title transfer |
| CN-09 | specification_mismatch | Materials or specifications different from contract |
| CN-10 | subcontractor_failure | Subcontractor quality or conduct issues |
| CN-11 | safety_violation | Construction site safety hazards; worker injury |
| CN-12 | encroachment | Construction encroaching on neighboring property |
| CN-13 | noise_dust_nuisance | Construction nuisance affecting neighbors |
| CN-14 | abandonment | Contractor abandoned project before completion |

### Resolution Standards

- **Contractor/Developer level:** Most construction contracts have a disputes clause; formal notice within 28 days of dispute arising.
- **CRB (Contractors Registration Board):** Complaints against registered contractors; investigation within 60 days; CRB can deregister.
- **ERB:** Engineering professional conduct complaints; similar timeline.
- **AQRB:** Architect and quantity surveyor complaints.
- **Local Authority (Manispaa/Halmashauri):** Building permit violations; enforcement within 30 days; can order demolition of unauthorized construction.
- **Civil courts:** Contract disputes and negligence claims; arbitration if contract includes arbitration clause.
- **Developer fraud:** Criminal matter; police report + PCCB if corruption involved; Land Tribunal for title disputes.

### Escalation Triggers

- `issue_type = structural_defect` AND `occupancy_status = Yes` — Safety emergency; independent structural assessment immediately; occupants may need to evacuate
- `issue_type = developer_fraud` AND multiple buyers affected — Criminal matter; police report + PCCB if corruption; potential class action
- `issue_type = unauthorized_construction` — Local authority enforcement; potential demolition order
- `issue_type = safety_violation` AND worker injury — OSHA (Occupational Safety and Health Authority) report; criminal if negligence caused injury
- `issue_type = developer_fraud` AND `title_deed_transferred = No` — Land Tribunal; urgent; fraud preserves criminal route
- `contract_value_tzs > 50,000,000` — Dispute may require FIDIC arbitration or High Court; legal counsel essential

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| developer_contractor | Msanidi / Mkandarasi | Recommended | For routing |
| project_type | Aina ya mradi | Yes | For analysis |
| suggestion_category | Kategoria | Yes | Routes to correct team |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| CNS-01 | quality_standards | Viwango bora vya ujenzi |
| CNS-02 | timeline_management | Usimamizi bora wa muda wa ujenzi |
| CNS-03 | transparency | Uwazi wa gharama na maendeleo |
| CNS-04 | title_transfer | Uhamishaji wa haraka wa hati za ardhi |
| CNS-05 | local_materials | Matumizi ya malighafi za ndani |
| CNS-06 | safety_culture | Utamaduni wa usalama kwenye maeneo ya ujenzi |
| CNS-07 | green_building | Ujenzi rafiki wa mazingira |
| CNS-08 | affordable_housing | Makazi ya bei nafuu |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina | Recommended | For tracking |
| project_name | Mradi | Conditional | For project-specific queries |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| crb_verification | Je, mkandarasi huyu amesajiliwa CRB? | contractor_name |
| building_permit_process | Jinsi ya kupata ruhusa ya ujenzi | location, building_type |
| title_transfer_process | Jinsi ya kuhamisha hati ya ardhi | current_owner, property_location |
| defect_liability | Muda wa ujibu wa mapungufu ni muda gani? | contract_type |
| fidic_explanation | FIDIC contract ina masharti gani ya malipo? | contract_type |
| developer_verification | Je, msanidi huyu amesajiliwa? | developer_name |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| contractor_developer | Mkandarasi / Msanidi | Yes | Routes to management |
| project_name | Mradi | Recommended | Project recognition |
| specific_aspect_praised | Kipengele | Yes | Ubora wa kazi / Kukamilika kwa wakati / Uwazi / Usalama wa eneo |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Construction quality benchmarking |

---

## AI Conversation Guidance for This Industry

- **For structural defects in occupied buildings, assess safety immediately.** Ask "Je, jengo linalokumiwa hivi karibuni na watu? Mapungufu ya kimuundo yanaweza kuwa hatari ya maisha — tunashauri mhandisi huru amuangalie haraka." Evacuation may be needed.
- **For developer fraud, ask about other affected buyers.** Multiple victims signal a systematic fraud. "Je, unajua wanunuzi wengine ambao wamenunua nyumba au kiwanja kutoka kwa msanidi huyu na wana tatizo kama lako?"
- **Get the CRB number before anything else.** "Mkandarasi huyu ana nambari ya usajili wa CRB? Bila usajili wa CRB, kampuni inaweza kufanya kazi haramu."
- **For delay complaints, ask about the original contract date and actual status.** Establish the gap: "Tarehe ya kukamilika iliyoandikwa kwenye mkataba ilikuwa lini? Na sasa hivi ujenzi uko katika hatua gani?"
- **Do not assess whether construction is up to standard.** The AI should route to an ERB-registered engineer for technical assessment. "Ubora wa ujenzi unahitaji tathmini ya mhandisi aliyesajiliwa ERB — siwezi kutathmini hilo, lakini naweza kusaidia kupeleka malalamiko yako."
- **For off-plan buyers, confirm whether title deed has been transferred.** This is the single most important indicator of developer legitimacy. "Hati ya ardhi (title deed) imeshatiwa jina lako? Kama hapana, bado una hatari ya kupoteza nyumba yako."

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Developer/contractor | "Kampuni ya ujenzi au msanidi wa mradi huu inaitwa nini?" |
| CRB number | "Mkandarasi ana nambari ya usajili wa CRB? Inaweza kuonekana kwenye mkataba" |
| Contract reference | "Mkataba wa ujenzi una nambari ya marejeleo — je, una nambari hiyo?" |
| Building permit | "Ruhusa ya ujenzi ya mradi huu ina nambari gani?" |
| Defect description | "Mapungufu ya ujenzi ni gani hasa — eleza mahali, aina, na ukubwa" |
| Safety check | "Je, jengo linalokumiwa na watu hivi karibuni? Tatizo hilo lina hatari ya usalama?" |
| Payment made | "Kiasi kilicholipwa kwa mkandarasi hadi sasa ni kiasi gani? Una risiti?" |
| Title deed | "Hati ya ardhi imeshatiwa jina lako? Au bado iko kwa jina la msanidi?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | structural_defect AND occupied building | Safety emergency; independent structural engineer assessment; potential evacuation |
| issue_type | developer_fraud AND multiple buyers | Criminal referral; police + PCCB; potential class action; Land Tribunal |
| issue_type | unauthorized_construction | Local authority enforcement complaint; potential demolition order |
| issue_type | safety_violation AND worker injury | OSHA report; medical care; criminal if negligence |
| issue_type | developer_fraud AND title_deed_not_transferred | Land Tribunal; urgent criminal complaint; preserve all payment evidence |
| contractor_crb_number | not found in CRB register | Unauthorized contractor; local authority complaint; contract may be void |
| defect_liability_period | still within DLP AND contractor refuses to repair | CRB complaint; contractor has legal obligation to repair free of charge |
| contract_value_tzs | > 50,000,000 | Legal counsel essential; FIDIC arbitration or High Court; complex dispute |

---

*Sources: Tanzania CRB Act, ERB Act, AQRB Act, Land Act Cap. 113, Local Government (Urban Authorities) Act Cap. 288, Tanzania Law of Contract Act Cap. 433, Fair Competition Act Cap. 285, FIDIC Conditions of Contract, ISO 10002:2018, OSHA Tanzania*
