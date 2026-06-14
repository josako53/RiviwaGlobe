---
tags: [industry-kb, field-standards, feedback-fields, social-welfare]
---
# Social Welfare — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: ustawi wa jamii, social welfare, department of social welfare, DSW, msaada wa jamii, social protection, hifadhi ya jamii, cash transfer, uhamisho wa fedha, TASAF, Tanzania Social Action Fund, PSSN, Productive Social Safety Net, NHIF, social health insurance, pension, mstaafu, PSPF, PPF, GEPF, NSSF, disability, ulemavu, orphan, yatima, vulnerable children, watoto walio hatarini, child protection, ulinzi wa mtoto, elderly, wazee, domestic violence, ukatili wa nyumbani, GBV, gender-based violence, women's shelter, makazi ya wanawake, foster care, malezi ya kukaa, adoption, kupanga mtoto kwa familia, child support, msaada wa malezi ya mtoto, social worker, mfanyakazi wa ustawi wa jamii, community welfare, ustawi wa jamii, CRDB social fund, community center, kituo cha jamii, rehabilitation, ukarabati wa kijamii, people with disabilities, PWD, CHAWATA, SHIVYAWATA

## Why Industry-Specific Fields Matter

Social welfare complaints span benefit eligibility disputes (requiring TASAF/PSSN reference, household registration number), child protection failures (requiring immediate safeguarding escalation), domestic violence shelter services (requiring immediate safety protocol), pension disputes (NSSF/PSPF reference), and discrimination against persons with disabilities. Each has a completely different resolution pathway and urgency level. Without welfare-specific fields, the AI cannot distinguish a routine benefit delay from a child protection emergency requiring immediate intervention.

## Source Standards

- Tanzania Social Welfare Act and Department of Social Welfare regulations
- Tanzania Social Action Fund (TASAF) Act and PSSN guidelines
- Child Act, Cap. 13 — child rights and protection
- National Social Security Fund (NSSF) Act, Cap. 50
- Public Service Pension Fund (PSPF) Act
- Persons with Disabilities Act, Cap. 189
- The Prevention and Combating of Violence Against Women and Children Act 2022
- Tanzania National Disability Strategy 2010–2020
- Gender-Based Violence guidelines (MOHCDGEC)
- ISO 10002:2018 — complaints handling
- UNHCR Refugee Act — for refugee social welfare
- UN Convention on the Rights of the Child (CRC) — Tanzania signatory

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL social welfare complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji (hiari kwa usalama) | Optional | Anonymous accepted for safety; especially for GBV |
| complainant_phone | Nambari ya simu (hiari) | Optional | For status updates; keep confidential if safety concern |
| welfare_program_type | Aina ya programu ya ustawi | Yes | TASAF/PSSN / Child protection / Disability / Pension / GBV / Elderly |
| institution_or_provider | Taasisi au mtoa huduma | Yes | DSW / TASAF / NSSF / PSPF / NGO / Shelter — routes complaint |
| beneficiary_id | Nambari ya mnufaika (kama ipo) | Conditional | For TASAF/PSSN and pension complaints |
| household_registration_number | Nambari ya usajili wa kaya (kwa TASAF) | Conditional | PSSN eligibility lookup |
| district_and_ward | Wilaya na Kata | Yes | For geographic routing and DSW referral |
| issue_type | Aina ya tatizo | Yes | Complaint taxonomy |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; detailed narrative |
| immediate_safety_concern | Je, kuna hatari ya usalama ya haraka? | Yes | For GBV and child protection — safety first |
| desired_outcome | Matokeo unayotaka | Yes | Benefit reinstatement / Safety / Compensation / Investigation |

### CRITICAL: Child Protection / GBV Safety Protocol

**If any indication of child abuse, domestic violence, or immediate safety risk:**
- `safety_status` — Hali ya usalama: Safe / At risk / Immediate danger — SAFETY FIRST
- `safe_location_needed` — Je, mahali salama pa kukaa kunahitajika? Yes / No — for GBV shelter routing
- `perpetrator_access` — Je, mtendaji anaweza kumfikia mhusika? Yes / No
- `children_in_household` — Idadi ya watoto katika kaya
- **For child abuse: Immediate DSW referral AND police (Child Act mandates this)**
- **For domestic violence: Connect to GBV shelter FIRST, collect details after**

### Conditional Fields (collect based on issue type)

**If issue_type = TASAF/PSSN Benefit Dispute:**
Also collect:
- `tasaf_beneficiary_id` — Nambari ya mnufaika wa TASAF
- `village_project_committee` — Kamati ya Mradi ya Kijiji (VPC)
- `payment_expected_period` — Kipindi cha malipo kinachostahili
- `payment_amount_expected_tzs` — Kiasi kinachostahili (TZS)
- `payment_received_tzs` — Kiasi kilichopokelewa (TZS)
- `exclusion_reason_given` — Sababu iliyotolewa ya kuondolewa kwenye mpango

**If issue_type = Pension Dispute (NSSF/PSPF):**
Also collect:
- `nssf_or_pspf_number` — Nambari ya NSSF au PSPF
- `pension_claim_reference` — Nambari ya madai ya pensheni
- `years_of_contribution` — Miaka ya kuchangia
- `pension_amount_expected_tzs` — Kiasi cha pensheni inayotarajiwa (TZS)
- `retirement_date` — Tarehe ya kustaafu
- `employer_name` — Jina la mwajiri wa mwisho (kwa madai ya NSSF)

**If issue_type = Disability Services / Rights:**
Also collect:
- `disability_type` — Aina ya ulemavu: Physical / Visual / Hearing / Intellectual / Multiple
- `disability_card_number` — Nambari ya kadi ya ulemavu (kama ipo)
- `accommodation_requested` — Upatikanaji ulioombwa: Ramp / Braille / Sign language / Wheelchair — for accessibility complaints
- `institution_type` — Aina ya taasisi: Government / Hospital / School / Employer / Transport

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| SW-01 | tasaf_benefit_exclusion | Household wrongly excluded from PSSN benefits |
| SW-02 | tasaf_payment_shortfall | TASAF payment below entitled amount |
| SW-03 | child_abuse | Physical, emotional, or sexual abuse of a child |
| SW-04 | domestic_violence | GBV/domestic violence requiring immediate response |
| SW-05 | child_neglect | Child neglect or abandonment |
| SW-06 | orphan_care_failure | Inadequate care for orphaned or vulnerable children |
| SW-07 | pension_delay | Pension not paid on time after retirement |
| SW-08 | pension_underpayment | Pension amount below statutory entitlement |
| SW-09 | disability_discrimination | Denial of service or access due to disability |
| SW-10 | elderly_neglect | Neglect or abuse of elderly persons |
| SW-11 | foster_care_dispute | Foster placement concerns or irregularities |
| SW-12 | social_worker_misconduct | Unprofessional or corrupt social worker behavior |
| SW-13 | rehab_service_failure | Rehabilitation program not delivering promised services |
| SW-14 | refugee_welfare | Refugee social welfare services failure |
| SW-15 | discrimination_welfare | Welfare benefits withheld on discriminatory basis |

### Resolution Standards

- **DSW (Department of Social Welfare):** Complaints acknowledged within 5 days; resolution within 30 days.
- **TASAF/PSSN:** Beneficiary appeals processed within 30 days; village project committee → district → TASAF headquarters.
- **NSSF/PSPF:** Pension claims must be processed within 30 days of complete documentation; disputes within 60 days.
- **Child protection:** Immediate response required under Child Act; social worker must visit within 24 hours of abuse report.
- **GBV:** GBV shelter services available 24/7; police GBV desk; free legal aid through TANLAP.
- **Disability:** Persons with Disabilities Act requires accessibility; CHAWATA/SHIVYAWATA advocacy organizations support complaints.

### Escalation Triggers

- `issue_type = child_abuse` OR `child_neglect` — Immediate DSW + police; Child Act mandatory reporting; child safety first
- `issue_type = domestic_violence` AND `immediate_safety_concern = Yes` — GBV shelter (24/7) + police GBV desk; safety first before data collection
- `issue_type = elderly_neglect` AND serious harm — DSW immediate investigation; potential criminal matter
- `issue_type = disability_discrimination` AND government institution — CHAWATA advocacy + CHRAGG complaint; Persons with Disabilities Act violation
- `issue_type = pension_delay` AND pensioner in financial distress — NSSF/PSPF emergency processing request; MP/Minister intervention if systemic
- `issue_type = tasaf_benefit_exclusion` AND vulnerable household (elderly, disabled, OVC) — Priority appeal to TASAF district office; social protection network alert

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| program_type | Aina ya programu | Yes | Routes to correct team |
| district | Wilaya | Recommended | Geographic routing |
| suggestion_category | Kategoria | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| SWS-01 | benefit_targeting | Ufikiaji sahihi wa wanaostahili |
| SWS-02 | payment_reliability | Uhakika wa malipo ya TASAF |
| SWS-03 | disability_inclusion | Ujumuishaji wa walemavu |
| SWS-04 | child_protection | Ulinzi bora wa watoto |
| SWS-05 | gbv_services | Huduma bora za GBV |
| SWS-06 | pension_process | Mchakato bora wa pensheni |
| SWS-07 | elderly_care | Huduma bora kwa wazee |
| SWS-08 | community_awareness | Uhamasishaji wa haki za ustawi |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina (hiari) | Optional | Anonymous accepted |
| program_type | Aina ya programu | Yes | Routes to correct answer |
| query_type | Aina ya swali | Yes | Routes to correct answer |
| urgency | Haraka | Yes | Standard / Dharura |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| tasaf_eligibility | Je, kaya yangu inastahili PSSN? | household_size, location |
| nssf_contribution_check | Michango yangu ya NSSF iko? | nssf_number |
| gbv_shelter | Wapi niende kwa msaada wa GBV? | location, safety_status |
| child_protection_report | Jinsi ya kuripoti unyanyasaji wa mtoto? | location |
| disability_card | Jinsi ya kupata kadi ya ulemavu? | disability_type |
| pension_process | Jinsi ya kuomba pensheni ya NSSF? | retirement_date |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| program_name | Programu iliyopongezwa | Yes | Routes to correct team |
| staff_name | Jina la mfanyakazi | Recommended | Staff recognition |
| specific_aspect_praised | Kipengele | Yes | Msaada wa haraka / Huruma / Uadilifu / Huduma bora |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Social welfare service quality |

---

## AI Conversation Guidance for This Industry

- **Safety comes before data collection for GBV and child protection.** Before collecting any fields, ask "Je, uko salama sasa hivi? Je, kuna watoto wanaohitaji msaada wa haraka?" Then provide emergency contacts (GBV shelter, police 112, DSW). Only collect complaint details after safety is confirmed.
- **For TASAF/PSSN complaints, get the household registration number.** "Kaya yako ina nambari ya usajili wa TASAF / PSSN — inaweza kuonekana kwenye kadi ya mnufaika au karatasi ya programu."
- **For pension complaints, establish the employment history.** "Ulifanya kazi kwa kampuni gani na kwa muda gani? NSSF inaweza kuhitaji historia ya michango."
- **For disability discrimination, do not minimize the experience.** Acknowledge: "Wewe una haki ya kupata huduma sawa na mtu yeyote mwingine — hii ni haki yako kisheria chini ya Sheria ya Watu Wenye Ulemavu."
- **For child abuse reports, mandatory reporting applies.** The AI must escalate to DSW and police regardless of the complainant's wishes — this is required by the Child Act. "Kwa mujibu wa Sheria ya Mtoto, tunalazimika kuripoti tatizo hili kwa Idara ya Ustawi wa Jamii na polisi kwa usalama wa mtoto."
- **For elderly neglect, ask about the living situation.** "Mzee huyu anaishi na nani — familia, peke yake, au katika kituo cha wazee?"

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Safety first | "Kwanza kabla ya kitu kingine — je, uko salama sasa hivi? Kuna hatari yoyote ya haraka?" |
| GBV shelter | "Kuna makazi salama ya wanawake — tunaweza kukusaidia kupata mahali salama pa kukaa sasa hivi" |
| TASAF ID | "Nambari yako ya mnufaika wa TASAF au PSSN inaonekana kwenye kadi yako ya programu" |
| NSSF number | "Nambari yako ya NSSF inaonekana kwenye kadi ya NSSF au taarifa za mwajiri" |
| Disability type | "Aina ya ulemavu inayohusika ni nini — kimwili, macho, masikio, au akili?" |
| Child abuse report | "Tunapaswa kuripoti hali ya mtoto kwa DSW na polisi kwa usalama wake — tunakuunga mkono katika hatua hii" |
| Complainant role | "Wewe ni mhusika mwenyewe, mzazi, mlezi, jirani, au mfanyakazi wa jamii?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | child_abuse OR child_neglect | Immediate DSW + police; Child Act mandatory report; child safety priority |
| issue_type | domestic_violence AND immediate_safety_concern | GBV shelter referral (24/7) + police GBV desk; safety before data collection |
| issue_type | elderly_neglect AND serious harm | DSW immediate investigation; police if criminal abuse |
| issue_type | disability_discrimination AND government institution | CHAWATA advocacy + CHRAGG complaint; Persons with Disabilities Act violation |
| issue_type | tasaf_benefit_exclusion AND vulnerable household | Priority appeal to TASAF district office; social welfare network notification |
| issue_type | pension_delay AND financial distress | NSSF/PSPF emergency processing; document financial hardship |
| immediate_safety_concern | Yes | Safety resources before any other action; do not delay for data |
| issue_type | refugee_welfare | UNHCR + DSW + Refugee Department notification |

---

*Sources: Tanzania Social Welfare Act, TASAF Act, Child Act Cap. 13, NSSF Act Cap. 50, PSPF Act, Persons with Disabilities Act Cap. 189, Prevention of Violence Against Women and Children Act 2022, CRC, ISO 10002:2018, UNHCR Refugee Act*
