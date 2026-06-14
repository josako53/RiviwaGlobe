---
tags: [industry-kb, field-standards, feedback-fields, consultancy, business-services]
---
# Business Consultancy — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: ushauri wa biashara, business consultancy, management consultant, mshauri wa usimamizi, strategy consultant, mshauri wa mkakati, financial advisor, mshauri wa fedha, HR consultant, mshauri wa rasilimali watu, IT consultant, mshauri wa teknolojia ya habari, marketing consultant, mshauri wa masoko, audit firm, kampuni ya ukaguzi, accounting firm, kampuni ya uhasibu, CPA, certified public accountant, NBAA, National Board of Accountants and Auditors, tax advisory, ushauri wa kodi, feasibility study, utafiti wa uwezekano, business plan, mpango wa biashara, market research, utafiti wa soko, project management, usimamizi wa miradi, PMO, retainer, mkataba wa ushauri, deliverables, matokeo yaliyoahidiwa, proposal, pendekezo, invoice, ankara, NDA, non-disclosure agreement, intellectual property, mali ya akili, conflict of interest, mgongano wa maslahi, BRELA, TRA, NBAA registration

## Why Industry-Specific Fields Matter

Consultancy complaints cover breach of engagement terms (requiring contract reference, scope of work, deliverables), professional negligence (requiring engagement letter, outcome harm), billing disputes (requiring invoice number, hours billed, rate agreed), and unauthorized disclosure of confidential information (requiring NDA reference, data breach). Without consultancy-specific fields, the AI cannot assess whether the complaint is a contractual dispute (civil court) or a professional misconduct matter (NBAA for accountants, Law Society for legal advisors).

## Source Standards

- Tanzania Law of Contract Act, Cap. 433 — contract terms and breach
- National Board of Accountants and Auditors (NBAA) Act, Cap. 286 — professional conduct for accountants
- NBAA Code of Professional Conduct for Accountants
- CPA Tanzania regulations
- Tanzania Engineers Registration Board (ERB) Act — engineering consultants
- ISO 10002:2018 — complaints handling
- ISO 20700:2017 — Guidelines for management consultancy services
- ISO 9001:2015 — quality management for service providers
- FIDIC conditions of contract (reference for engineering and project management)
- Tanzania Intellectual Property Act — IP protection

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL consultancy complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | For complaint registration |
| complainant_phone | Nambari ya simu | Yes | Status updates |
| complainant_organization | Jina la shirika la mlalamikaji | Yes | Corporate vs. individual client distinction |
| consultancy_firm_name | Jina la kampuni ya ushauri | Yes | Regulated entity identification |
| consultant_name | Jina la mshauri aliyehusika | Recommended | For individual accountability |
| engagement_reference | Nambari ya mkataba / barua ya uandikishwaji | Yes | Core contract identifier; required for dispute investigation |
| scope_of_work | Wigo wa kazi (kwa muhtasari) | Yes | For assessing whether deliverables were met |
| contract_start_date | Tarehe ya kuanza mkataba | Yes | For timeline and breach analysis |
| contract_end_date | Tarehe ya kukamilika kwa mkataba | Yes | For determining if breach occurred |
| fees_agreed_tzs | Ada iliyokubaliwa (TZS) | Yes | For billing dispute and overcharge comparison |
| fees_paid_tzs | Ada iliyolipwa (TZS) | Yes | For financial dispute quantification |
| deliverables_promised | Matokeo yaliyoahidiwa | Yes | What was the consultant supposed to deliver?  |
| deliverables_received | Matokeo yaliyopokelewa | Yes | What was actually delivered? |
| issue_type | Aina ya tatizo | Yes | Complaint taxonomy |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; detailed narrative |
| financial_loss_tzs | Hasara ya fedha iliyosababishwa (TZS) | Conditional | For professional negligence claims |
| nbaa_registration_number | Nambari ya usajili wa NBAA (kwa wahasibu) | Conditional | For NBAA professional conduct complaints |
| desired_outcome | Matokeo unayotaka | Yes | Refund / Completion of work / Compensation / Investigation |

### Conditional Fields (collect based on issue type)

**If issue_type = Professional Negligence:**
Also collect:
- `advice_given` — Ushauri uliotolewa: What specific advice led to the harm?
- `client_action_based_on_advice` — Hatua iliyochukuliwa kwa msingi wa ushauri: For causation
- `harm_caused` — Madhara yaliyotokea: Financial loss / Regulatory penalty / Business failure / Reputational damage
- `independent_expert_opinion` — Je, maoni ya mtaalamu huru yamepatikana?: For negligence assessment
- `professional_indemnity_insurance` — Je, mshauri ana bima ya uwajibikaji wa kitaalamu?: Source of compensation

**If issue_type = Billing Dispute:**
Also collect:
- `invoice_number` — Nambari ya ankara
- `hours_billed` — Masaa yaliyotozwa
- `hours_agreed_or_expected` — Masaa yaliyokubaliwa au yanayotarajiwa
- `hourly_rate_agreed` — Ada ya kila saa (TZS): For time-based billing disputes
- `retainer_fee_scope` — Wigo wa ada ya retainer: For retainer agreement disputes
- `expenses_billed` — Gharama za ziada zilizotozwa: Travel, accommodation, materials

**If issue_type = Confidentiality / NDA Breach:**
Also collect:
- `nda_reference` — Nambari ya NDA au kifungu kinachohusika
- `information_disclosed` — Taarifa zilizofunuliwa: Nature of disclosed information
- `to_whom_disclosed` — Taarifa zilifunuliwa kwa nani / wapi
- `business_harm_from_disclosure` — Madhara ya biashara yaliyotokana na ufunuo
- `evidence_of_disclosure` — Ushahidi wa ufunuo: Documents, emails, third party confirmation

**If issue_type = Conflict of Interest:**
Also collect:
- `competing_client_name` — Jina la mteja mshindani (kama inajulikana)
- `nature_of_conflict` — Asili ya mgongano wa maslahi: Working for competitor / Financial interest / Personal relationship
- `harm_caused_by_conflict` — Madhara yaliyotokana na mgongano

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| BC-01 | deliverables_not_met | Agreed work not completed or of poor quality |
| BC-02 | project_delay | Deliverables significantly behind agreed timeline |
| BC-03 | professional_negligence | Incorrect advice caused measurable harm |
| BC-04 | billing_overcharge | Fees exceed agreed rate or scope |
| BC-05 | confidentiality_breach | Client information disclosed without authorization |
| BC-06 | conflict_of_interest | Consultant working for competitors or has undisclosed interest |
| BC-07 | misrepresentation | Qualifications, experience, or capability misrepresented |
| BC-08 | scope_creep_unauthorized | Extra work billed without client authorization |
| BC-09 | intellectual_property | Client IP used without permission |
| BC-10 | abandonment | Consultant abandoned engagement mid-project |
| BC-11 | kickback_corruption | Consultant receiving hidden commissions or kickbacks |
| BC-12 | poor_communication | Consistent failure to update or respond |
| BC-13 | nbaa_audit_failure | Audit firm negligence or misconduct (NBAA jurisdiction) |

### Resolution Standards

- **Firm level:** Most reputable consultancies have client services managers; disputes should be acknowledged within 5 days; resolved or mediated within 30 days.
- **NBAA (accounting/audit):** NBAA investigates professional conduct complaints against registered accountants; investigation within 60 days; can revoke CPA registration.
- **ERB (engineering):** ERB handles engineering consultant misconduct; similar timelines.
- **Civil courts:** Contractual disputes and professional negligence may require litigation; arbitration clauses common in consultancy contracts.
- **TRA (tax advice negligence):** If incorrect tax advice led to TRA penalties, the client may have a negligence claim against the tax advisor.
- **Required for regulatory escalation:** Engagement letter, invoices, deliverable documentation, evidence of harm.

### Escalation Triggers

- `issue_type = professional_negligence` AND `financial_loss_tzs > 5,000,000` — Legal counsel referral; potential professional indemnity insurance claim
- `issue_type = nbaa_audit_failure` AND material misstatement — NBAA complaint; potential regulatory audit; investor impact
- `issue_type = confidentiality_breach` AND trade secrets — Urgent legal injunction; Tanzania IP Act enforcement
- `issue_type = kickback_corruption` — PCCB referral if government contracts involved; FCC if private sector
- `issue_type = conflict_of_interest` AND material — NBAA conduct complaint; legal remedy for contract avoidance

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| firm_name | Kampuni ya ushauri | Recommended | For routing |
| service_type | Aina ya huduma | Yes | Routes to correct team |
| suggestion_category | Kategoria | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| BCS-01 | communication | Mawasiliano bora na wateja |
| BCS-02 | deliverable_quality | Ubora wa kazi inayotolewa |
| BCS-03 | timeline_management | Usimamizi wa muda wa utekelezaji |
| BCS-04 | transparency | Uwazi wa ankara na malipo |
| BCS-05 | local_expertise | Uzoefu zaidi wa soko la Tanzania |
| BCS-06 | digital_tools | Zana za kidijitali katika utoaji wa huduma |
| BCS-07 | conflict_policy | Sera wazi za mgongano wa maslahi |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina | Recommended | For tracking |
| firm_name | Kampuni | Conditional | For firm-specific queries |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| nbaa_registration_check | Je, kampuni hii ina usajili wa NBAA? | firm_name |
| service_quotation | Nukuu ya bei ya huduma | service_type, scope |
| engagement_process | Jinsi ya kuanza na mshauri | service_type |
| professional_indemnity | Je, mshauri ana bima ya uwajibikaji? | firm_name |
| dispute_process | Jinsi ya kutatua mgongano wa mkataba | engagement_reference |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| consultant_name | Jina la mshauri | Recommended | Individual recognition |
| firm_name | Kampuni | Yes | Routes to management |
| specific_aspect_praised | Kipengele | Yes | Ujuzi wa hali ya juu / Matokeo halisi / Uaminifu / Mawasiliano bora |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Service quality benchmarking |

---

## AI Conversation Guidance for This Industry

- **Get the engagement letter/contract reference immediately.** Without a written engagement, the dispute is much harder to resolve. "Je, mkataba wa maandishi au barua ya uandikishwaji (engagement letter) ulisainiwa? Nambari yake au tarehe yake ni ipi?"
- **For negligence complaints, establish causation clearly.** Ask "Ushauri uliotolewa ulikuwa gani hasa? Na kwa msingi wa ushauri huo, hatua gani ulichukua? Na nini kilitokea?" — this establishes the advice → action → harm chain needed for a negligence claim.
- **For NBAA complaints, verify the accountant's registration.** NBAA maintains a public register. "Mshauri huyu ana nambari ya usajili ya NBAA? Tunaweza kuthibitisha kwa NBAA."
- **For billing disputes, ask for the engagement scope first.** Many billing disputes stem from scope creep — the consultant did additional work that wasn't formally authorized. "Mkataba uliofafanua wigo wa kazi (scope) ulikuwa gani? Na kazi iliyotokana na ankara ni nini hasa?"
- **For confidentiality breaches, advise immediate legal counsel.** This is often an injunctive matter requiring fast legal action to prevent further disclosure. "Uvujaji wa siri za biashara unaweza kuhitaji hatua ya kisheria ya haraka — tunashauri wasiliana na wakili leo."
- **Do not assess whether the advice was correct.** Simply document what was advised and what harm occurred; assessment requires expert review.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Firm name | "Kampuni ya ushauri inaitwa nini?" |
| Contract reference | "Mkataba au barua ya uandikishwaji ina nambari ya marejeleo — je, una nambari hiyo?" |
| Deliverables | "Matokeo yaliyoahidiwa kwenye mkataba yalikuwa gani hasa?" |
| What was received | "Matokeo yaliyopokelewa kweli kweli yalikuwa gani?" |
| Fees agreed | "Ada iliyokubaliwa kwenye mkataba ilikuwa kiasi gani?" |
| Fees paid | "Kiasi kilicholipwa hadi sasa ni kiasi gani?" |
| NBAA number | "Mshauri / kampuni ya ukaguzi ina nambari ya usajili ya NBAA — je, inajulikana?" |
| Financial loss | "Hasara ya fedha iliyosababishwa na tatizo hili ni kiasi gani (TZS)?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | professional_negligence AND loss > 5M TZS | Legal counsel referral; professional indemnity insurance claim |
| issue_type | nbaa_audit_failure | NBAA complaint; potential regulatory audit; 60-day investigation |
| issue_type | confidentiality_breach AND trade secrets | Urgent legal injunction; Tanzania IP Act enforcement |
| issue_type | kickback_corruption AND government contract | PCCB referral; PPRA notification |
| issue_type | misrepresentation AND NBAA claimed but not registered | NBAA enforcement; FCC consumer protection complaint |
| issue_type | conflict_of_interest AND material | NBAA conduct complaint; legal advice on contract avoidance |
| financial_loss_tzs | confirmed AND causation established | Legal referral for contractual claim; professional indemnity insurance route |

---

*Sources: Tanzania Law of Contract Act Cap. 433, NBAA Act Cap. 286, NBAA Code of Professional Conduct, Tanzania IP Act, ISO 20700:2017, ISO 10002:2018, PCCB Act Cap. 329, PPRA Act Cap. 410*
