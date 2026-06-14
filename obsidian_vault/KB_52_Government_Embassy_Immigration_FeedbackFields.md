---
tags: [industry-kb, field-standards, feedback-fields, embassy, immigration, consular]
---
# Government Embassy / Immigration — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: embassy, ubalozi, consulate, balozi, visa, ruhusa ya kuingia, passport, pasipoti, immigration, uhamiaji, work permit, kibali cha kazi, residence permit, kibali cha kuishi, citizenship, uraia, naturalization, utarajiwa wa uraia, refugee, mkimbizi, UNHCR, asylum, hifadhi ya kimataifa, deportation, kufukuzwa nchini, border, mpaka, border control, immigration officer, afisa wa uhamiaji, visa rejection, kukataliwa visa, visa delay, kuchelewa kwa visa, entry ban, marufuku ya kuingia, transit visa, visa ya kupita, diplomatic, kidiplomasia, foreign national, raia wa kigeni, consul, mjumbe, DIC, Department of Immigration Tanzania, TRA customs, customs, forodha, work permit application, BRELA, EAC free movement, East Africa Common Market

## Why Industry-Specific Fields Matter

Embassy and immigration complaints cover visa denials (requiring application reference, visa type, rejection reason, supporting documents submitted), work permit issues (requiring employer details, permit type, Ministry of Labour reference), and immigration officer misconduct (requiring officer name, border post, date). Each complaint path leads to a different authority: visa complaints to the relevant foreign embassy; immigration complaints to Tanzania Immigration Department; work permit complaints to Ministry of Labour. Without these specific fields, the AI cannot route or generate a complaint that will be actionable.

## Source Standards

- Tanzania Immigration Act, Cap. 54 — immigration control and alien registration
- Tanzania Immigration Regulations 2014
- Non-Citizens (Employment Regulation) Act, Cap. 436 — work permits
- Ministry of Labour and Employment — work permit processes
- Tanzania Passport Act — passport issuance and services
- Vienna Convention on Consular Relations (VCCR) 1963 — consular duties to nationals abroad
- Vienna Convention on Diplomatic Relations (VCDR) 1961
- UNHCR Handbook on Procedures and Criteria for Refugee Status (2019 edition)
- EAC Protocol on the Establishment of the East African Common Market (2010) — free movement rights
- ISO 10002:2018 — complaints handling

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL embassy / immigration complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Required for complaint registration |
| complainant_phone | Nambari ya simu | Yes | For status updates |
| complainant_email | Barua pepe | Recommended | Most embassy communications are via email |
| complainant_nationality | Uraia wa mlalamikaji | Yes | Determines which embassy or immigration authority is relevant |
| complainant_passport_number | Nambari ya pasipoti | Yes | Primary identifier for immigration and consular records |
| application_reference_number | Nambari ya maombi | Conditional | Required for visa and permit disputes; enables status lookup |
| embassy_or_authority_name | Jina la ubalozi au mamlaka | Yes | Routes complaint to correct entity |
| issue_type | Aina ya tatizo | Yes | Visa / Work Permit / Deportation / Officer Misconduct etc. |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; clear narrative required |
| date_of_incident | Tarehe ya tukio | Yes | For investigation and limitation period |
| country_of_application | Nchi iliyotumika maombi | Yes | Determines jurisdiction of the complaint |
| desired_outcome | Matokeo unayotaka | Yes | Visa approval / Compensation / Disciplinary action |
| legal_representative | Je, una wakili? (jina na mawasiliano) | Recommended | Many immigration complaints benefit from legal representation |

### Conditional Fields (collect based on issue type)

**If issue_type = Visa Refusal:**
Also collect:
- `visa_type` — Aina ya visa: Tourist / Business / Student / Transit / Family / Diplomatic
- `rejection_reason_given` — Sababu ya kukataliwa: Eligibility / Documentation / Background / No reason given
- `rejection_letter_available` — Je, barua ya kukataliwa inapatikana?: Required for appeal
- `documents_submitted` — Nyaraka zilizowasilishwa: List of documents included in application
- `previous_visa_to_same_country` — Je, umewahi kupata visa ya nchi hiyo awali? Yes / No
- `appeal_deadline` — Tarehe ya mwisho ya kukata rufaa: Most visas have a 28–90 day appeal window

**If issue_type = Work Permit:**
Also collect:
- `permit_type` — Aina ya kibali: Class A-G (Tanzania work permit categories)
- `employer_name` — Jina la mwajiri
- `employer_tin_number` — Nambari ya TIN ya mwajiri: Ministry of Labour requirement
- `ministry_of_labour_reference` — Nambari ya maombi ya Wizara ya Kazi
- `permit_start_date` — Tarehe ya kuanza kwa kibali
- `permit_expiry_date` — Tarehe ya kuisha muda wa kibali
- `renewal_applied_date` — Tarehe ya kuomba upya (kama ni ombi la upya)

**If issue_type = Immigration Officer Misconduct (bribery, harassment):**
Also collect:
- `officer_name_or_badge` — Jina au nambari ya baji ya afisa
- `border_post_or_office` — Kituo cha mpaka au ofisi
- `bribe_amount_tzs` — Kiasi cha hongo kilichoombwa (TZS)
- `bribe_paid` — Je, hongo ilelipwa? Yes / No
- `witnesses_present` — Mashahidi waliopo
- `incident_date_time` — Tarehe na saa ya tukio

**If issue_type = Deportation / Detention:**
Also collect:
- `deportation_order_reference` — Nambari ya amri ya kufukuzwa
- `detention_facility` — Mahali pa kizuizini
- `reason_given_for_deportation` — Sababu iliyotolewa
- `legal_aid_contacted` — Je, msaada wa kisheria umeombwa? Yes / No
- `diplomatic_post_notified` — Je, ubalozi wa nchi yako umearifiwa? Yes / No
- `consular_visit_allowed` — Je, ubalozi unaruhusiwa kutembelea?: Vienna Convention right

**If issue_type = Passport Delay / Error:**
Also collect:
- `application_date` — Tarehe ya maombi
- `promised_collection_date` — Tarehe iliyoahidiwa ya kukusanya
- `passport_error_type` — Aina ya kosa: Wrong name / Wrong DOB / Wrong photo / Missing pages
- `payment_reference` — Nambari ya risiti ya malipo ya pasipoti

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| EM-01 | visa_refusal | Visa application rejected; complainant disputes decision |
| EM-02 | visa_delay | Visa application not processed within stated timeframe |
| EM-03 | work_permit_refusal | Work permit rejected without valid reason |
| EM-04 | work_permit_delay | Work permit processing unreasonably delayed |
| EM-05 | immigration_officer_misconduct | Bribery, harassment, or abuse by immigration officer |
| EM-06 | deportation_dispute | Deportation order contested as wrongful |
| EM-07 | detention_conditions | Poor or illegal detention conditions |
| EM-08 | passport_delay | Passport application not processed within stated time |
| EM-09 | passport_error | Incorrect information on issued passport |
| EM-10 | consular_service_failure | Embassy fails to assist national in distress abroad |
| EM-11 | refugee_status_dispute | Refugee or asylum claim wrongly rejected or delayed |
| EM-12 | citizenship_application | Naturalization application delayed or wrongly rejected |
| EM-13 | border_crossing_issue | Unjust denial of entry or exit |
| EM-14 | residence_permit | Residence permit delay or wrongful cancellation |
| EM-15 | customs_dispute | Incorrect customs assessment or confiscation |

### Resolution Standards

- **Tanzania Immigration Department:** Complaints acknowledged within 5 working days; resolved within 30 days.
- **Ministry of Labour (work permits):** Processing standard is 10–21 working days; appeal within 14 days of rejection.
- **Foreign Embassy complaints:** Resolution depends on the embassy's own complaints process; most EU/UK embassies have 28-day resolution targets. Citizens of Tanzania should direct complaints about foreign embassy conduct to MFA (Ministry of Foreign Affairs).
- **PCCB (immigration bribery):** PCCB handles bribery at border posts; report to toll-free 0800 110 065.
- **Deportation:** Legal challenge must be lodged before execution of order; Legal Aid Provider required; Vienna Convention right to consular access.
- **UNHCR (refugee):** UNHCR must acknowledge asylum requests; Tanzania is signatory to 1951 Refugee Convention.

### Escalation Triggers

- `issue_type = deportation_dispute` AND `legal_aid_contacted = No` — Immediate legal aid referral; deportation without legal review is a rights violation
- `issue_type = detention_conditions` AND conditions involve health risk — Immediate consular notification (Vienna Convention); CHRAGG referral
- `issue_type = immigration_officer_misconduct` AND bribery — PCCB referral; toll-free 0800 110 065
- `issue_type = consular_service_failure` AND national in distress (arrest, medical emergency) — Escalate to MFA and embassy duty officer; 24-hour emergency consular line
- `issue_type = refugee_status_dispute` — UNHCR escalation; complainant cannot be returned to country of persecution (non-refoulement principle)
- `issue_type = visa_refusal` AND complainant is an EAC citizen — EAC Common Market Protocol rights may apply; East African Court of Justice may have jurisdiction

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| embassy_or_authority | Ubalozi / Mamlaka | Recommended | For routing |
| service_type | Aina ya huduma | Yes | Visa / Work Permit / Passport etc. |
| suggestion_category | Kategoria | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| EMS-01 | digital_visa_application | Maombi ya visa mtandaoni |
| EMS-02 | processing_speed | Kuharakisha uchakataaji wa maombi |
| EMS-03 | anti_corruption | Kupambana na hongo mpakani |
| EMS-04 | information_provision | Taarifa bora kuhusu mahitaji |
| EMS-05 | staff_training | Mafunzo ya heshima na uadilifu |
| EMS-06 | eac_free_movement | Utekelezaji wa makubaliano ya EAC |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina la mwulizaji | Recommended | For tracking |
| nationality | Uraia | Conditional | Determines which authority applies |
| query_type | Aina ya swali | Yes | Routes to correct answer |
| urgency | Haraka | Yes | Standard / Dharura |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| visa_requirements | Mahitaji ya visa | destination_country, travel_purpose |
| work_permit_process | Jinsi ya kupata kibali cha kazi | nationality, employer_type |
| passport_renewal | Jinsi ya kuhuisha pasipoti | passport_expiry_date |
| status_check | Hali ya maombi yangu | application_reference_number |
| eac_rights | Haki zangu kama raia wa EAC | nationality, destination_country |
| refugee_process | Jinsi ya kuomba hifadhi | country_of_origin |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| officer_name | Jina la afisa | Recommended | Staff recognition |
| office_or_post | Ofisi / Kituo | Yes | Routes to management |
| specific_aspect_praised | Kipengele | Yes | Haraka / Uadilifu / Msaada / Heshima |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Immigration service quality benchmark |

---

## AI Conversation Guidance for This Industry

- **Establish nationality and destination country first.** These two fields determine which embassy, authority, and legal framework applies to the complaint. "Wewe ni raia wa nchi gani, na tatizo lako linahusiana na nchi gani au ubalozi gani?"
- **For visa refusal complaints, always ask for the rejection letter.** Without it, any appeal is much harder. "Je, barua ya kukataliwa (refusal letter) ilitolewa? Sababu iliyoandikwa ni ipi?"
- **For deportation/detention complaints, prioritize legal aid.** The AI should immediately provide the complainant with Legal Aid contact: "Tanzania Legal Aid Providers Association (TANLAP) au wakili yeyote anaweza kusaidia — hili ni haki yako."
- **Do not attempt to assess whether a visa decision was correct.** Simply collect the facts and route appropriately. "Sitaweza kukuambia kama unaistahili visa au la — hilo linaamuliwa na mamlaka ya nchi hiyo. Nitasaidia kupeleka tatizo lako kwa njia sahihi."
- **For immigration bribery, assure the complainant of PCCB protection.** Collect details carefully; this is a criminal matter. "PCCB wanaweza kuchunguza bila kufunua jina lako — simu yao ya bure ni 0800 110 065."
- **For work permit complaints, ask for the employer's role.** Often the employer (not the employee) is responsible for the permit application; understanding who applied clarifies accountability.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Nationality | "Wewe ni raia wa nchi gani?" |
| Passport number | "Nambari ya pasipoti yako ni ipi?" |
| Application reference | "Maombi yako yana nambari ya marejeleo — je, una nambari hiyo?" |
| Visa type | "Uliomba visa ya aina gani — utalii, biashara, kazi, au nyingine?" |
| Rejection reason | "Sababu iliyotolewa ya kukataliwa ilikuwa nini? Je, ipo kwenye barua?" |
| Officer details | "Jina au nambari ya baji ya afisa aliyehusika ni nani?" |
| Consular notification | "Je, ubalozi wa nchi yako umejulishwa hali yako?" |
| Legal aid | "Je, una wakili au umewahi wasiliana na wasaidizi wa kisheria?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | deportation_dispute | Immediate legal aid referral; advise right to legal hearing before deportation |
| issue_type | detention_conditions AND health risk | Consular notification under Vienna Convention; CHRAGG referral |
| issue_type | immigration_officer_misconduct AND bribery | PCCB referral (0800 110 065); protect complainant identity |
| issue_type | consular_service_failure AND distress abroad | MFA Operations Center escalation; embassy duty officer contact |
| issue_type | refugee_status_dispute | UNHCR escalation; non-refoulement principle applies |
| complainant_nationality | EAC member state AND visa_refusal | Check EAC Common Market Protocol rights; East African Court of Justice may have jurisdiction |
| issue_type | work_permit_delay AND employer has TIN | Ministry of Labour follow-up; provide reference timeline (10–21 working days standard) |
| visa_appeal_deadline | within 7 days | Urgent; advise immediate appeal submission; provide appeal process details |

---

*Sources: Tanzania Immigration Act Cap. 54, Non-Citizens (Employment Regulation) Act Cap. 436, Vienna Convention on Consular Relations 1963, UNHCR Handbook 2019, EAC Common Market Protocol 2010, PCCB Act Cap. 329, ISO 10002:2018*
