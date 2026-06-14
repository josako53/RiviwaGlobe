---
tags: [industry-kb, field-standards, feedback-fields, government, public-services]
---
# Government / Public Services — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: serikali, government, halmashauri, local government authority, LGA, wizara, ministry, idara ya serikali, baraza la wilaya, district council, manispaa, municipal council, ofisi ya kata, ward office, kitongoji, village office, public service, huduma za umma, huduma za serikali, permit, ruhusa, license, leseni, certificate, cheti, ID, kitambulisho, NIDA, birth certificate, cheti cha kuzaliwa, death certificate, cheti cha kifo, business license, leseni ya biashara, land title, hati ya ardhi, TRA, Tanzania Revenue Authority, tax, kodi, RITA, registration, usajili, passport, pasipoti, driving license, leseni ya udereva, VPO, NECTA, examination certificate, road, barabara, service delivery, utoaji wa huduma, corruption, rushwa, bribery, hongo, procurement, ununuzi wa serikali, PPRA, LAAC, public official, mtumishi wa serikali

## Why Industry-Specific Fields Matter

Government service complaints span multiple distinct categories: service delivery failures (wrong certificate, delayed permit), corruption/bribery (requiring incident details, official name, witness), land administration disputes (requiring title deed number, plot number, Land Authority reference), and procurement irregularities (requiring tender number and PPRA reference). Without government-specific fields, the AI cannot route to the correct ministry, LGA, or anti-corruption body (PCCB) or generate a compliant complaint under the Public Service Act.

## Source Standards

- Tanzania Public Service Act, Cap. 298 — public service conduct and complaints
- Public Service (Amendment) Act 2002 and Public Service Regulations 2003
- Prevention and Combating of Corruption Bureau (PCCB) Act, Cap. 329
- Tanzania Anti-Corruption Strategy (NACS) IV 2017–2022
- Public Procurement Act, Cap. 410 and PPRA Regulations 2013
- Local Government (District Authorities) Act, Cap. 287
- Tanzania Land Act, Cap. 113 and Land Disputes Courts Act, Cap. 216
- Citizens' Service Delivery Standards (President's Office – Public Service Management and Good Governance)
- ISO 10002:2018 — complaints handling
- Freedom of Information Act 2016 (Tanzania) — access to government information
- NIDA Identification and Registration Act, Cap. 261

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL government service complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Public Service Act requires complainant identification |
| complainant_phone | Nambari ya simu | Yes | For complaint status updates |
| complainant_national_id | Nambari ya kitambulisho (NIDA) | Recommended | Verifies citizen status; required for some escalations |
| ministry_or_department | Wizara / Halmashauri / Idara | Yes | Routes complaint to correct government entity |
| service_requested | Huduma iliyoombwa | Yes | Specific service: what was the citizen trying to obtain? |
| application_reference | Nambari ya maombi (kama ipo) | Conditional | For service delays and rejections; enables status lookup |
| issue_type | Aina ya tatizo | Yes | Service delivery failure / Corruption / Land / Tax etc. |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; Public Service Act requires documented complaints |
| government_official_involved | Jina la mtumishi wa serikali aliyehusika | Conditional | Required for corruption and misconduct complaints |
| date_of_incident | Tarehe ya tukio | Yes | For limitation periods and investigation |
| location_of_incident | Mahali pa tukio | Yes | District / Ward / Office name — for jurisdictional routing |
| desired_outcome | Matokeo unayotaka | Yes | Service provision / Disciplinary action / Refund / Investigation |
| evidence_available | Je, ushahidi unapatikana? | Recommended | Receipts, photos, audio recordings; PCCB requires evidence for corruption complaints |

### Conditional Fields (collect based on issue type)

**If issue_type = Corruption / Bribery:**
Also collect:
- `bribe_amount_requested_tzs` — Kiasi cha hongo kilichoombwa (TZS): PCCB requires this for investigation
- `bribe_paid` — Je, hongo ilelipwa? Yes / No: Affects legal status and refund possibility
- `bribe_payment_method` — Njia ya kulipa hongo: Cash / Mobile Money / Bank — for traceability
- `witness_names` — Majina ya mashahidi (kama wapo): PCCB investigation requirement
- `official_rank_or_position` — Cheo / Nafasi ya mtumishi: For accountability routing
- `date_time_of_bribery` — Tarehe na saa ya tukio la hongo
- `audio_video_evidence` — Je, kuna ushahidi wa sauti au picha?: PCCB accepts recordings as evidence

**If issue_type = Land Dispute / Land Administration:**
Also collect:
- `plot_number` — Nambari ya kiwanja
- `land_title_number` — Nambari ya hati ya ardhi
- `district_and_ward` — Wilaya na Kata ya ardhi
- `land_registry_reference` — Nambari ya usajili wa ardhi (Land Registry)
- `opposing_party` — Mtu / Taasisi inayopinga umiliki
- `land_court_case_number` — Nambari ya kesi ya mahakama ya ardhi (kama ipo)

**If issue_type = Tax Dispute (TRA):**
Also collect:
- `tin_number` — Nambari ya TIN (Taxpayer Identification Number)
- `tax_type` — Aina ya kodi: VAT / Income Tax / Withholding / Import Duty
- `assessment_reference` — Nambari ya tathmini ya kodi
- `dispute_amount_tzs` — Kiasi kinachobiwabishwa (TZS)
- `tax_period` — Kipindi cha kodi kinachohusika

**If issue_type = Certificate / Document Delay:**
Also collect:
- `document_type` — Aina ya hati: Birth certificate / Death certificate / Marriage certificate / Business license / Title deed
- `application_date` — Tarehe ya maombi
- `expected_processing_time` — Muda wa kawaida wa kuchakata (kama ulijulishwa)
- `payments_made` — Malipo yaliyofanywa: Amount and date

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| GV-01 | service_delay | Government service takes longer than official standard |
| GV-02 | service_refusal | Government refuses to provide service without valid reason |
| GV-03 | corruption_bribery | Government official demanding or accepting a bribe |
| GV-04 | document_error | Incorrect information on government-issued document |
| GV-05 | land_dispute | Land allocation, title, or boundary dispute involving government |
| GV-06 | tax_dispute | Incorrect tax assessment, unauthorized tax collection |
| GV-07 | procurement_irregularity | Tender awarded irregularly; contract not honored |
| GV-08 | certificate_delay | Birth, death, marriage, or business certificate delayed |
| GV-09 | staff_misconduct | Rude, discriminatory, or abusive government employee |
| GV-10 | access_denial | Denied access to public records or information |
| GV-11 | permit_license_delay | Business or construction permit delayed or wrongly refused |
| GV-12 | road_infrastructure | Potholed roads, broken drainage, poor street lighting |
| GV-13 | waste_management | Poor solid waste collection; illegal dumping |
| GV-14 | public_facility_condition | Degraded school, health center, court, or government building |
| GV-15 | election_conduct | Election-related complaint (to NEC / INEC) |
| GV-16 | police_misconduct | Police brutality, wrongful arrest, extortion |

### Resolution Standards

- **Ministry/Department level:** Public Service Act requires acknowledgement within 5 working days and resolution within 21 working days.
- **Local Government (LGA):** Halmashauri complaint committees must meet monthly; urgent complaints within 14 days.
- **PCCB (corruption):** PCCB acknowledges complaints within 7 days; investigation typically 60–90 days; major cases may take longer.
- **TRA disputes:** Objection to tax assessment must be lodged within 30 days; TRA Tax Appeals Board hears disputes.
- **Land disputes:** Ward Tribunal → District Land and Housing Tribunal → Court of Appeal track.
- **Required for escalation:** Ministry/department name, service requested, date(s) of contact, name of official involved, reference numbers.

### Escalation Triggers

- `issue_type = corruption_bribery` AND `bribe_amount_requested_tzs > 0` — Immediate PCCB referral; hotline 0800 110 065 (toll-free)
- `issue_type = police_misconduct` AND involves violence or wrongful arrest — Escalate to Police Internal Affairs Unit and CHRAGG (Commission for Human Rights)
- `issue_type = land_dispute` AND involves eviction — Emergency CHRAGG referral and Legal Aid provider
- `issue_type = procurement_irregularity` AND involves public funds — PPRA Controller and Auditor General referral
- `issue_type = service_refusal` AND affects health or life (e.g., birth certificate for NHIF enrollment) — Urgent escalation to ministry headquarters
- `bribe_paid = Yes` — Advise complainant on whistleblower protections under PCCB Act; PCCB can facilitate refund in some cases

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted for government suggestions |
| ministry_or_lga | Wizara / Halmashauri | Recommended | For routing |
| service_type | Aina ya huduma | Yes | Routes to correct improvement team |
| suggestion_category | Kategoria | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| GVS-01 | e_government | Huduma za serikali mtandaoni |
| GVS-02 | service_speed | Kuharakisha utoaji wa huduma |
| GVS-03 | transparency | Uwazi wa mchakato wa serikali |
| GVS-04 | anti_corruption | Kupambana na rushwa |
| GVS-05 | staff_training | Mafunzo ya watumishi wa umma |
| GVS-06 | infrastructure | Kuboresha miundombinu ya umma |
| GVS-07 | citizen_information | Kutoa taarifa bora kwa wananchi |
| GVS-08 | digital_documents | Hati za kidijitali za serikali |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina la mwulizaji | Recommended | For tracking |
| national_id | Nambari ya kitambulisho | Conditional | For citizen-specific queries |
| query_type | Aina ya swali | Yes | Routes to correct information |
| ministry_or_lga | Wizara / Halmashauri | Recommended | Directs to correct office |
| urgency | Haraka | Yes | Standard / Dharura |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| document_status | Hali ya maombi ya hati | application_reference |
| service_requirements | Mahitaji ya huduma | service_type |
| office_location | Mahali pa ofisi | district, service_type |
| tin_registration | Jinsi ya kupata TIN | national_id |
| land_process | Jinsi ya kupata hati ya ardhi | district, plot_number |
| business_license | Jinsi ya kupata leseni ya biashara | business_type, location |
| pccb_process | Jinsi ya kuripoti rushwa | location, ministry_or_lga |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| official_name | Jina la mtumishi wa serikali | Recommended | For commendation recording |
| ministry_or_department | Wizara / Idara | Yes | Routes to management |
| specific_aspect_praised | Kipengele | Yes | Haraka ya huduma / Uadilifu / Ukarimu / Ufanisi |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Public Service Delivery Index |

---

## AI Conversation Guidance for This Industry

- **Identify the government entity precisely.** Tanzania has multiple layers: central government ministries, regional secretariats, district/municipal councils, ward offices. "Ofisi ya serikali inayohusika iko ngazi gani — wizara, halmashauri, au ofisi ya kata?"
- **For corruption complaints, ensure complainant safety.** Ask whether they feel safe reporting this complaint. Explain PCCB whistleblower protection: "PCCB inalinda watu wanaotoa taarifa za rushwa — unaweza kuripoti kwa siri."
- **Never pressure a complainant to reveal bribery.** If they are reluctant to confirm bribery, accept the information they volunteer; escalate based on what is shared.
- **For document delays, confirm whether all required documents were submitted.** Many delays are due to incomplete applications. "Je, nyaraka zote zilizoombwa ziliwasilishwa? Nini kiliombwa nawe?"
- **For land disputes, do not make any assessment of ownership.** Simply collect the facts and route to the Land Tribunal or Legal Aid provider.
- **Tax disputes need TIN number early.** Without the TIN, TRA cannot access the taxpayer file. "Nambari yako ya TIN — inaweza kuonekana kwenye hati yako ya usajili wa TRA."

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Government entity | "Tatizo lako linahusiana na ofisi gani ya serikali au halmashauri?" |
| Service requested | "Ulikuwa ukiomba huduma gani — cheti, ruhusa, leseni, au kitu kingine?" |
| Application reference | "Maombi yako yana nambari ya marejeleo — je, una nambari hiyo?" |
| Official name | "Jina la mtumishi wa serikali aliyehusika ni nani?" |
| Bribery amount | "Kiasi kilichoombwa au kulipwa kama hongo kilikuwa kiasi gani?" |
| Evidence | "Je, una ushahidi wowote — risiti, picha, ujumbe wa simu, au ushahidi mwingine?" |
| Plot number | "Nambari ya kiwanja (plot number) ni ipi? Na ardhi iko wilaya gani?" |
| TIN | "Nambari yako ya TIN inaonekana kwenye kadi ya TIN au hati ya usajili" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | corruption_bribery | PCCB referral; toll-free 0800 110 065; advise whistleblower protection |
| issue_type | police_misconduct AND violence | CHRAGG referral; Police Internal Affairs Unit; Legal Aid provider |
| issue_type | land_dispute AND eviction | Emergency CHRAGG referral; Legal Aid; no eviction without court order |
| issue_type | procurement_irregularity | PPRA referral; Controller and Auditor General notification |
| bribe_paid | Yes | Document evidence carefully; PCCB can investigate refund; protect complainant identity |
| issue_type | document_error AND affects benefits (NHIF, school enrollment) | Urgent correction request; LGA supervisor involvement |
| issue_type | service_refusal AND no valid reason | Escalate to ministry headquarters customer care; cite Public Service Act obligations |
| previous_complaint | lodged > 21 working days without response | Eligible for Public Service Commission escalation |

---

*Sources: Tanzania Public Service Act Cap. 298, PCCB Act Cap. 329, Local Government Act Cap. 287, Tanzania Land Act Cap. 113, TRA Act, Public Procurement Act Cap. 410, ISO 10002:2018, NACS IV 2017–2022*
