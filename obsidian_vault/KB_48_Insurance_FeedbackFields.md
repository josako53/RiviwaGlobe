---
tags: [industry-kb, field-standards, feedback-fields, insurance]
---
# Insurance — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: bima, insurance, policy, polisi ya bima, premium, ada ya bima, claim, madai ya bima, TIRA, Tanzania Insurance Regulatory Authority, underwriter, broker, broker wa bima, agent wa bima, life insurance, bima ya maisha, health insurance, bima ya afya, motor insurance, bima ya gari, property insurance, bima ya mali, fire insurance, bima ya moto, marine insurance, bima ya bahari, crop insurance, bima ya mazao, microinsurance, bima ndogo, reinsurance, indemnity, fidia, excess, deductible, kiasi cha kwanza kinacholipwa na bima, beneficiary, mwenefiti, sum assured, kiasi cha bima, expiry, kuisha muda wa bima, renewal, kuhuisha bima, policy number, nambari ya bima, claim rejection, kukataliwa madai, delayed claim, kuchelewa kwa madai, pre-existing condition, ugonjwa uliokuwepo awali, exclusion, kikwazo cha bima, NHC, National Health Corporation

## Why Industry-Specific Fields Matter

Insurance complaints range from claim rejections (requiring policy number, claim reference, rejection reason, supporting evidence), premium disputes (requiring policy schedule, payment receipts), to agent misconduct (requiring agent license number). Each path leads to a different TIRA investigation track. Without insurance-specific fields, the AI cannot establish whether a claim rejection is valid (policy exclusion), procedural (missing documents), or wrongful (bad faith denial requiring TIRA complaint).

## Source Standards

- Tanzania Insurance Act, Cap. 394 — TIRA regulatory authority and consumer protection
- TIRA Consumer Protection Guidelines 2018
- TIRA Complaints Handling Procedures 2019
- TIRA Motor Vehicle Insurance Regulations
- National Health Corporation (NHC) Act and NHIF Act Cap. 395
- ISO 10002:2018 — complaints handling
- IAIS Insurance Core Principles (ICP 19) — conduct of business
- East African Community Insurance Protocol — cross-border coverage reference

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | TIRA complaint form requires full name |
| complainant_phone | Nambari ya simu | Yes | For complaint status updates |
| complainant_email | Barua pepe | Recommended | TIRA may communicate via email |
| insurer_name | Jina la kampuni ya bima | Yes | Identifies the regulated insurer; TIRA licenses by company |
| policy_number | Nambari ya polisi ya bima | Yes | Primary identifier for all insurance complaints; without it, the insurer cannot locate the record |
| policy_type | Aina ya bima | Yes | Life / Health / Motor / Property / Marine / Crop — determines applicable policy terms and TIRA regulations |
| policy_start_date | Tarehe ya kuanza kwa bima | Recommended | For confirming coverage was active at time of incident |
| policy_expiry_date | Tarehe ya kuisha muda wa bima | Recommended | To verify policy was in force |
| claim_reference_number | Nambari ya madai (kama ipo) | Conditional | Required for claim disputes; enables insurer to locate claim file |
| date_of_incident | Tarehe ya tukio / hasara | Yes | For verifying claim is within policy period |
| issue_type | Aina ya tatizo | Yes | TIRA complaint taxonomy; drives routing and SLA |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018 clause 8.2; TIRA requires incident narrative |
| claim_amount_claimed_tzs | Kiasi kilichodaiwa (TZS) | Conditional | Required for claim disputes |
| claim_amount_offered_tzs | Kiasi kilichotolewa na bima (TZS) | Conditional | For disputed settlement amount complaints |
| rejection_reason_given | Sababu ya kukataliwa madai | Conditional | Required for claim rejection complaints; enables TIRA to assess if rejection is valid |
| agent_or_broker_name | Jina la wakala / broker | Conditional | For agent misconduct complaints; TIRA licenses agents separately |
| desired_outcome | Matokeo unayotaka | Yes | Full settlement / Partial review / Apology / Policy explanation |
| previous_complaint_to_insurer | Je, umeshalalamika kampuni ya bima moja kwa moja? | Yes | TIRA requires prior complaint to insurer before escalation |

### Conditional Fields (collect based on issue type)

**If issue_type = Claim Rejection:**
Also collect:
- `supporting_documents_submitted` — Nyaraka zilizowasilishwa: List of evidence submitted with claim
- `insurer_rejection_letter_available` — Je, barua ya kukataliwa inapatikana?: Required for TIRA review
- `independent_assessment_obtained` — Je, tathmini huru imefanywa?: e.g., independent motor assessor, medical second opinion

**If issue_type = Motor Insurance (accident):**
Also collect:
- `vehicle_registration_number` — Nambari ya usajili wa gari: Primary vehicle identifier
- `accident_date_time` — Tarehe na saa ya ajali
- `police_abstract_number` — Nambari ya muhtasari wa polisi: Required for motor claims in Tanzania
- `other_party_details` — Maelezo ya gari/mtu mwingine aliyehusika: For third-party liability claims
- `assessor_report_available` — Je, ripoti ya mtaalamu wa uharibifu inapatikana?

**If issue_type = Health Insurance Claim Dispute:**
Also collect:
- `nhif_or_nhc_number` — Nambari ya NHIF / NHC: For public health insurance claims
- `hospital_name` — Jina la hospitali iliyotibu: For preauthorization and panel verification
- `preauthorization_obtained` — Je, idhini ya awali ilipatikana?: Many health policies require preauthorization
- `treatment_date` — Tarehe ya matibabu

**If issue_type = Premium Dispute:**
Also collect:
- `premium_amount_expected_tzs` — Ada inayotarajiwa (TZS)
- `premium_amount_charged_tzs` — Ada iliyochukuliwa (TZS)
- `payment_receipts_available` — Je, risiti za malipo zinapatikana?

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| IN-01 | claim_rejection | Claim denied; complainant disputes the rejection |
| IN-02 | delayed_claim_payment | Claim approved but payment unreasonably delayed |
| IN-03 | claim_underpayment | Settlement amount lower than entitled amount |
| IN-04 | policy_cancellation | Policy cancelled without proper notice or justification |
| IN-05 | premium_dispute | Wrong premium amount charged or unauthorized deduction |
| IN-06 | agent_misconduct | Agent misrepresented policy terms, collected premiums without issuing policy |
| IN-07 | policy_not_issued | Premiums paid but policy document never received |
| IN-08 | exclusion_dispute | Claim rejected citing exclusion complainant was not informed of |
| IN-09 | preexisting_condition_dispute | Claim rejected citing pre-existing condition |
| IN-10 | motor_third_party | Third-party victim complaint against motor insurer |
| IN-11 | renewal_issue | Policy not renewed despite payment; coverage gap |
| IN-12 | beneficiary_dispute | Insurer refusing to pay legitimate beneficiary |
| IN-13 | policy_terms_misrepresentation | Policy terms differ from what agent described at sale |
| IN-14 | unlicensed_insurer | Company collecting premiums without TIRA license |
| IN-15 | poor_customer_service | Unresponsive, rude, or unhelpful insurer staff |

### Resolution Standards for This Industry

- **Insurer level (Tanzania):** TIRA Consumer Protection Guidelines require acknowledgement within 5 business days; resolution within 30 days.
- **TIRA escalation:** Complainant may escalate to TIRA Consumer Protection Department after 30 days without resolution or if response is unsatisfactory.
- **TIRA investigation:** TIRA aims to resolve complaints within 60 days of receipt.
- **Claim payment:** TIRA regulations require payment within 30 days of claim approval.
- **Motor third-party:** TIRA Motor Vehicle Insurance Regulations set limits and timelines for third-party victim settlements.
- **Required for TIRA escalation:** Policy number, insurer name, nature of complaint, insurer's response (or evidence of non-response), claim reference number.

### Escalation Triggers

- `issue_type = unlicensed_insurer` — Immediate TIRA referral; criminal matter under Insurance Act Cap. 394
- `issue_type = agent_misconduct` AND premiums collected but no policy issued — TIRA enforcement; potential fraud; advise police report
- `issue_type = claim_rejection` AND `rejection_reason` not in policy exclusion list — Potential bad faith denial; escalate to TIRA within 30 days
- `issue_type = motor_third_party` AND victim has uncompensated injury — TIRA Motor Fund may cover uninsured claims; escalate urgently
- `issue_type = beneficiary_dispute` AND policyholder is deceased — Time-sensitive; escalate to TIRA consumer protection with death certificate
- `claim_amount_claimed_tzs > 50,000,000` — Senior TIRA officer review required; large value disputes have dedicated track

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous feedback accepted |
| insurer_name | Jina la kampuni | Recommended | For targeted routing |
| policy_type | Aina ya bima | Yes | Routes to product team |
| suggestion_category | Kategoria ya mapendekezo | Yes | For routing and analysis |
| suggestion_detail | Maelezo ya mapendekezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| INS-01 | claims_process_speed | Kuharakisha mchakato wa madai |
| INS-02 | digital_policy_management | Usimamizi wa bima kidijitali |
| INS-03 | product_design | Bidhaa mpya za bima zinazofaa zaidi |
| INS-04 | premium_affordability | Ada nafuu zaidi |
| INS-05 | transparency | Uwazi wa masharti ya bima |
| INS-06 | rural_microinsurance | Bima ndogo kwa wakulima na makundi ya pembezoni |
| INS-07 | agent_training | Mafunzo bora kwa mawakala |
| INS-08 | digital_claims | Madai ya kidijitali / kupiga picha na kuwasilisha |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina la mwulizaji | Recommended | Identity verification |
| policy_number | Nambari ya polisi | Conditional | For policy-specific queries |
| query_type | Aina ya swali | Yes | Routes inquiry |
| urgency | Haraka | Yes | Standard / Dharura |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| coverage_check | Nini kinafunikwa na bima yangu? | policy_number, policy_type |
| claim_status | Hali ya madai yangu | claim_reference_number |
| premium_due | Malipo yangu ya bima yanafika lini? | policy_number |
| renewal_process | Jinsi ya kuhuisha bima | policy_number, policy_expiry_date |
| beneficiary_addition | Jinsi ya kuongeza mwenefiti | policy_number |
| exclusion_list | Vitu visivyofunikwa na bima | policy_type |
| tira_license_check | Je, kampuni hii ina leseni ya TIRA? | insurer_name |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| staff_or_agent_name | Jina la mfanyakazi / wakala | Recommended | Staff recognition |
| insurer_name | Kampuni ya bima | Yes | Routes to management |
| specific_aspect_praised | Kipengele kilichotukuka | Yes | Ulipaji wa haraka / Ushauri mzuri / Ukweli wa masharti / Adabu |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | TIRA CSAT benchmarking |

---

## AI Conversation Guidance for This Industry

- **Get the policy number before anything else.** It is the single key that unlocks the entire claim and coverage history. Ask "Una nambari ya polisi yako ya bima? Inaweza kuonekana kwenye kadi ya bima au hati ya polisi."
- **Clarify the type of insurance first.** Motor, life, health, and property complaints have entirely different fields and resolution paths. "Bima hii ni ya aina gani — gari, maisha, afya, mali, au nyingine?"
- **For claim rejection complaints, ask for the rejection letter.** The rejection reason is the most critical document; without it, TIRA cannot assess whether the rejection was justified. "Je, kampuni ya bima ilitoa barua au ujumbe wa maandishi ukieleza sababu ya kukataliwa?"
- **Do not promise that a rejected claim will be paid.** The AI should say "Tutapeleka tatizo lako kwa TIRA / kampuni ya bima ili uchunguzi ufanywe" rather than validating the complaint's outcome.
- **For agent misconduct, collect agent details carefully.** Many victims don't know the agent's license number; ask for their name, phone number, and the company they claimed to represent.
- **Acknowledge the emotional difficulty of a rejected claim.** Especially for life or health insurance, say "Tunakuelewa hali hii ni ngumu — tutahakikisha tatizo lako linashughulikiwa kwa uzito unaostahili."

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Insurer name | "Bima hii ni ya kampuni gani — jina la kampuni ya bima?" |
| Policy number | "Nambari ya polisi yako ya bima inaonekana kwenye kadi au hati ya bima — inasema nini?" |
| Claim reference | "Madai haya yana nambari ya marejeleo (claim number) — je, una nambari hiyo?" |
| Rejection reason | "Kampuni ya bima ilitoa sababu gani ya kukataliwa? Je, waliandika barua au kutuma ujumbe?" |
| Date of incident | "Tukio lililoleta madai (ajali, ugonjwa, hasara) lilitokea lini?" |
| Vehicle registration | "Nambari ya usajili ya gari inayohusika ni ipi? (kwa bima ya gari)" |
| Beneficiary | "Wewe ni mwenefiti wa polisi hii, au unawakilisha mtu mwingine?" |
| Desired outcome | "Unataka nini kutokea — kulipwa madai, kupata maelezo, au TIRA kufanya uchunguzi?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | unlicensed_insurer | Immediate TIRA referral; police report advised; criminal matter under Cap. 394 |
| issue_type | agent_misconduct AND premiums collected without policy | TIRA enforcement complaint; advise police report; preserve all payment evidence |
| issue_type | claim_rejection AND rejection_reason not in policy | Flag as potential bad faith denial; escalate to TIRA within 30 days |
| issue_type | motor_third_party AND uncompensated injury | Advise TIRA Motor Compensation Fund; escalate urgently |
| previous_complaint_to_insurer | Yes AND unresolved > 30 days | Eligible for TIRA escalation; provide TIRA contact (tira.go.tz) |
| issue_type | beneficiary_dispute AND policyholder deceased | Time-sensitive; escalate to TIRA consumer protection with death certificate |
| claim_amount_offered_tzs | significantly less than claim_amount_claimed_tzs | Request independent assessor report; escalate to TIRA for settlement review |
| issue_type | policy_not_issued AND premiums paid | Potential fraud; TIRA enforcement complaint; preserve payment receipts |

---

*Sources: Tanzania Insurance Act Cap. 394, TIRA Consumer Protection Guidelines 2018, TIRA Complaints Handling Procedures 2019, NHIF Act Cap. 395, ISO 10002:2018, IAIS ICP 19*
