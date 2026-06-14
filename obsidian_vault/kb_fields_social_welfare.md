---
tags: [industry-kb, field-standards, feedback-fields]
---
# Social Welfare — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: TASAF, PSSN, social welfare, cash transfer, beneficiary, disability grant, OVC, orphan, vulnerable children, food assistance, WFP, UNICEF, UNHCR, social worker, probation officer, child protection, foster care, elderly care, care home, rehabilitation center, approved school, disability certificate, PWD, CHAWAMKU, poverty targeting, MoHCDGEC, community development officer, bursary, HESLB poverty waiver, child maintenance, guardianship, household grant, subsidy, Mtaji wa Binadamu, ustawi wa jamii, msaada wa kijamii, ruzuku, ulemavu, mzee, yatima, mlezi, mtoto wa barabara, jamii maskini

## Why Industry-Specific Fields Matter

Generic feedback fields cannot distinguish between a wrongful exclusion from a cash transfer program (requiring beneficiary ID, program name, and household composition), a child safeguarding report (requiring immediate escalation to child protection authorities), and an elderly residential care complaint (requiring facility name and care standard reference) — all of which have different legal frameworks, mandatory reporting timelines, and escalation paths under Tanzania's Child Act, Persons with Disabilities Act 2010, and TASAF program rules. Without social welfare-specific fields, the AI cannot route, prioritize, or flag cases requiring mandatory reporting.

## Source Standards

- UNICEF HOPE Humanitarian Cash Transfers Grievance Management module
- UNHCR Minimum Standards on Complaints and Feedback Mechanisms (CFM)
- World Bank Grievance Redress Mechanisms in Social Cash Transfer Programs (UNDP/World Bank 2022)
- Zambia MCDSS Social Cash Transfer Grievance Mechanism (paper form model)
- Philippines Conditional Cash Transfer GRS (World Bank brief, 2014)
- FAO AFR100 Grievance Redress Mechanism (field requirements)
- Tanzania Child Act (Cap 13 RE 2019)
- Tanzania Persons with Disabilities Act 2010
- TASAF III Program Implementation Manual

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| `program_name` | Jina la programu / huduma | Yes | UNICEF HOPE and World Bank GRM require program identification to route complaint to correct implementing agency and apply correct SLA rules (TASAF, PSSN, OVC, WFP, etc.) |
| `implementing_agency` | Shirika / ofisi inayohusika | Yes | FAO AFR100 and World Bank GRM both require identification of the organization responsible; determines escalation path and jurisdiction |
| `beneficiary_id` | Nambari ya mwanufaika (hiari) | Optional | Zambia SCT GRM uses serial/ID numbers; UNHCR CFM supports anonymous submission — collect only if willing to share; do not require for anonymous reporting |
| `anonymous_flag` | Je, unataka kubaki bila jina? | Yes | UNHCR CFM mandates anonymous channel option; collect upfront to avoid requesting identifying details later if person wants anonymity |
| `issue_type` | Aina ya tatizo | Yes | UNICEF module and World Bank GRM both require categorization by issue type to determine responsible unit, investigation type, and resolution SLA |
| `issue_description` | Maelezo ya tatizo | Yes | Required by all frameworks (FAO AFR100, UNHCR, World Bank) as the primary narrative record of the grievance |
| `date_of_incident` | Tarehe ya tukio | Yes | FAO AFR100: "Date/time and location of the incident"; required for SLA calculation and limitation period |
| `location_district_ward` | Wilaya / Kata / Kijiji | Yes | World Bank GRM requires geographic disaggregation for program monitoring; TASAF tracks by geographic unit |
| `number_of_dependents_affected` | Idadi ya wategemezi walioathirika | Yes | World Bank GRM guidance requires household size disaggregation to assess impact severity |
| `vulnerability_status` | Hali ya mazingira magumu | Yes | UNHCR and World Bank mandate disaggregated tracking by gender, disability, elderly, OVC, refugee/IDP status to detect disparate impact on vulnerable groups |
| `previous_case_reference` | Nambari ya rufaa ya awali (kama ipo) | Conditional | Zambia SCT and Philippines 4Ps GRS use serial tracking; collect if complainant is following up on an existing case |
| `prior_action_taken` | Hatua ulizochukua tayari | Yes | FAO AFR100: "Any actions already taken to address the issue"; establishes escalation readiness and avoids re-routing to already-tried channels |
| `contact_details` | Mawasiliano yako (ikiwa si bila jina) | Conditional | FAO AFR100: required for non-anonymous complaints; collect only if `anonymous_flag = No` |
| `preferred_contact_channel` | Njia unayopendelea ya mawasiliano | Yes | UNHCR CFM emphasizes accessible channels including toll-free, SMS, in-person, and online; critical for rural and low-literacy contexts |
| `preferred_language` | Lugha unayopendelea | Yes | UNHCR: "information in the language they understand"; critical in multilingual Tanzania (Swahili, English, and regional languages) |
| `desired_outcome` | Matokeo unayotaka | Yes | Required by FAO AFR100 and World Bank GRM to guide resolution options (reinstatement, back-payment, investigation, referral) |

### Conditional Fields (collect based on issue type)

**If `issue_type = benefit_not_received` OR `wrong_amount_paid`:**
Also collect:
- `payment_period_affected` — Kipindi cha malipo kilichoathirika (mwezi/mwaka): Required to calculate back-payment entitlement
- `expected_amount_tzs` — Kiasi kilichotarajiwa (TZS): For financial remedy calculation
- `actual_amount_received_tzs` — Kiasi kilichopokelewa (TZS): Documents the shortfall
- `payment_method` — Njia ya malipo: Mobile money / Agent / Cash point / Bank; identifies which operator or agent may have diverted funds

**If `issue_type = wrongful_exclusion`:**
Also collect:
- `exclusion_date` — Tarehe ya kutengwa: When the household was removed or denied inclusion
- `targeting_committee_name` — Jina la kamati ya uchaguzi: Identifies which local committee made the exclusion decision
- `reason_given_for_exclusion` — Sababu iliyotolewa: For administrative review
- `household_poverty_evidence` — Ushahidi wa umaskini wa kaya: Documents eligibility basis

**If `issue_type = caseworker_misconduct` OR `bribery`:**
Also collect:
- `officer_name_and_role` — Jina na wadhifa wa ofisa: For investigation; FAO AFR100 collects "names of individuals involved"
- `bribe_amount_requested_tzs` — Kiasi cha rushwa kilichoombwa (TZS): For formal anti-corruption referral
- `witness_names` — Majina ya mashahidi: Supports investigation

**If `issue_type = child_protection` OR `child_abuse`:**
Also collect:
- `child_age` — Umri wa mtoto: Mandatory for Child Act (Cap 13) classification and mandatory reporting threshold
- `child_location` — Mahali alipo mtoto sasa: For immediate welfare action
- `alleged_perpetrator_role` — Wadhifa wa mdaiwa mkosa: Facility staff / carer / family member / unknown
- `immediate_danger_flag` — Je, mtoto yuko hatarini sasa hivi? | Yes/No: Triggers immediate escalation if Yes

**If `issue_type = residential_care_complaint` (elderly / orphanage / rehabilitation center):**
Also collect:
- `facility_name` — Jina la kituo: Required for facility inspection referral
- `facility_operator` — Meneja / mwendeshaji wa kituo: Government / NGO / Private
- `resident_name_or_id` — Jina / nambari ya mkazi (hiari): For case tracking with facility
- `care_standard_alleged_failed` — Kiwango cha huduma kilichokiukwa: Medical care / nutrition / hygiene / physical safety / visitor access

**If `issue_type = disability_services`:**
Also collect:
- `disability_type` — Aina ya ulemavu: Physical / visual / hearing / intellectual / psychosocial
- `assistive_device_involved` — Kifaa cha msaada kinachohusika (kama ipo): Wheelchair / crutches / hearing aid / white cane
- `certificate_or_registration_number` — Nambari ya cheti cha ulemavu (kama ipo): For CHAWAMKU / MoHCDGEC records

**If `issue_type = food_assistance`:**
Also collect:
- `distribution_point` — Kituo cha usambazaji wa chakula: For logistics investigation
- `food_condition` — Hali ya chakula: Spoiled / insufficient quantity / wrong commodity / not delivered
- `number_of_households_affected` — Idadi ya kaya zilizoathirika: World Bank requires collective impact quantification

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| SW-01 | `benefit_not_received` | Payment or in-kind benefit due but not received |
| SW-02 | `wrong_amount_paid` | Benefit received at incorrect reduced amount |
| SW-03 | `wrongful_exclusion` | Household wrongly excluded from or removed from program |
| SW-04 | `wrongful_inclusion` | Non-eligible household included; affects resources |
| SW-05 | `discrimination` | Exclusion or mistreatment based on ethnicity, gender, disability, political affiliation |
| SW-06 | `eligibility_dispute` | Complainant disputes the eligibility criteria or decision |
| SW-07 | `caseworker_misconduct` | Officer negligence, bribery, falsification of records |
| SW-08 | `data_privacy_breach` | Personal beneficiary data shared without consent |
| SW-09 | `service_cutoff` | Benefits abruptly stopped without notification or due process |
| SW-10 | `delayed_payment` | Payment released but received significantly later than scheduled |
| SW-11 | `communication_failure` | No information provided to beneficiary about status, changes, or decisions |
| SW-12 | `child_protection` | Child abuse, neglect, or exploitation — requires mandatory reporting |
| SW-13 | `residential_care_complaint` | Complaint about conditions in elderly home, orphanage, remand home, or rehab center |
| SW-14 | `disability_services` | Failure in disability registration, certificate issuance, or assistive device provision |
| SW-15 | `food_assistance_failure` | Spoiled food, missed distribution, wrong commodity, or fraudulent allocation |
| SW-16 | `cooperative_or_group_fraud` | Savings or VSLA group leader misappropriating community funds |

### Resolution Standards for This Industry

- **Program level (Tanzania / TASAF):** Implementing agencies must acknowledge grievances and provide a substantive response; TASAF III program documentation requires resolution within 30 days at local level with escalation to district within 14 days if unresolved.
- **Child protection:** Tanzania Child Act (Cap 13) mandates immediate notification of social welfare authorities and police for any report of child abuse; 24-hour response standard for cases involving immediate danger.
- **Disability services:** Persons with Disabilities Act 2010 establishes rights; CHAWAMKU is the national advocacy body; disability certificate disputes escalate to MoHCDGEC.
- **UNHCR standard (refugee context):** Acknowledge within 3 working days; resolve within 30 days; complex cases within 60 days.
- **Required documentation for escalation:** Beneficiary ID (if available), date of incident, program name, previous complaint reference, evidence of prior attempts to resolve internally.
- **Anti-corruption (bribery by officer):** Refer to Prevention and Combating of Corruption Bureau (PCCB) Tanzania.

### Escalation Triggers (field values that require immediate escalation)

- `issue_type = child_protection` AND `immediate_danger_flag = Yes` — Escalate within 1 hour to child protection services and police; do not delay to collect more fields
- `issue_type = child_protection` AND child is in a government facility — Mandatory report to MoHCDGEC Social Welfare Department within 24 hours regardless of danger level
- `issue_type = residential_care_complaint` AND `care_standard_alleged_failed` includes physical abuse or death — Escalate to facility regulator and police immediately
- `issue_type = caseworker_misconduct` AND `bribe_amount_requested_tzs > 0` — Escalate to PCCB and program management unit; create priority investigation ticket
- `issue_type = benefit_not_received` AND `number_of_households_affected > 50` — Community-level distribution failure; escalate to district program coordinator
- `issue_type = data_privacy_breach` AND beneficiary data shared with unauthorized third party — Escalate to program data protection officer and PDPC Tanzania (when operational)
- `issue_type = food_assistance_failure` AND `food_condition = Spoiled` — Public health risk; escalate to TFDA and district health officer
- `vulnerability_status` includes refugee or asylum seeker AND benefit denied — Escalate to UNHCR focal point

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `submitter_name` | Jina la mtoa maoni (hiari) | Optional | UNHCR CFM permits anonymous suggestions; do not require identification for suggestions |
| `contact_details` | Mawasiliano (hiari) | Optional | For follow-up if implementing agency wants to acknowledge |
| `program_or_service_area` | Programu / huduma inayohusika | Yes | Routes suggestion to correct implementing agency or unit |
| `suggestion_category` | Kategoria ya mapendekezo | Yes | Enables systematic analysis and routing |
| `suggestion_detail` | Maelezo ya mapendekezo | Yes | Free-text narrative; core content |
| `season_or_context` | Muktadha / msimu unaohusika | Recommended | For time-sensitive program cycles (e.g., planting season cash transfers, school term bursaries) |
| `geographic_area` | Eneo / Wilaya | Recommended | World Bank GRM requires geographic disaggregation for program monitoring |

### Industry-Specific Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| SWS-01 | `targeting_criteria` | Vigezo vya uchaguzi wa wanufaika |
| SWS-02 | `payment_mechanism` | Mfumo wa malipo |
| SWS-03 | `digital_access` | Upatikanaji wa kidijitali |
| SWS-04 | `grievance_mechanism` | Mfumo wa malalamiko (programu yenyewe) |
| SWS-05 | `disability_inclusion` | Ushirikiano wa watu wenye ulemavu |
| SWS-06 | `child_welfare` | Ustawi wa mtoto |
| SWS-07 | `staff_conduct` | Mwenendo wa wafanyakazi |
| SWS-08 | `communication_transparency` | Uwazi wa mawasiliano na wanufaika |
| SWS-09 | `food_nutrition_quality` | Ubora wa chakula na lishe |
| SWS-10 | `community_development` | Maendeleo ya jamii |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `inquirer_name` | Jina la mwulizaji (hiari) | Optional | Identity not required for inquiries; anonymous inquiries acceptable |
| `inquiry_type` | Aina ya swali | Yes | Routes to correct knowledge base or referral path |
| `program_or_service_of_interest` | Programu / huduma inayohusika | Yes | Ensures accurate information is provided for the right program |
| `location_district` | Wilaya / Mkoa | Recommended | Required for location-specific referrals (nearest office, distribution point) |
| `preferred_language` | Lugha unayopendelea | Yes | UNHCR standard: information in the language the person understands |
| `preferred_response_channel` | Njia unayopendelea ya jibu | Yes | SMS / Simu / Ana kwa ana / WhatsApp — critical for rural and low-literacy contexts |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Swahili | Additional Fields Needed |
|-------------|---------|--------------------------|
| `eligibility_check` | Je, nastahili kupata msaada? | `household_size`, `location_district`, `vulnerability_status` |
| `payment_status` | Je, malipo yangu yako wapi? | `beneficiary_id` (optional), `program_name`, `payment_period` |
| `registration_process` | Jinsi ya kujiandikisha | `program_name`, `location_district` |
| `appeal_status` | Hali ya rufaa yangu | `previous_case_reference`, `program_name` |
| `data_correction` | Kusahihisha taarifa zangu | `beneficiary_id` (optional), `nature_of_error` |
| `disability_registration` | Jinsi ya kupata cheti cha ulemavu | `disability_type`, `location_district` |
| `child_protection_referral` | Niripoti wapi tatizo la mtoto | `child_location`, `urgency_level` |
| `collection_point_location` | Kituo cha karibu cha kupokea msaada | `location_ward`, `program_name` |
| `nearest_office` | Ofisi ya karibu ya ustawi | `location_district` |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `submitter_name` | Jina la mtoa pongezi (hiari) | Optional | For acknowledgement; not required |
| `person_or_program_recognized` | Mtu / programu inayopongezwa | Yes | Routes compliment for staff recognition or program impact reporting |
| `role_of_person_recognized` | Wadhifa wa mtu anayepongezwa | Recommended | Social welfare officer / caseworker / community facilitator / program |
| `what_went_well` | Kilichofanya vizuri | Yes | Captures specific positive behavior or outcome for institutional learning |
| `impact_on_household` | Athari kwa familia yako | Recommended | Enables program impact documentation; World Bank GRM tracks positive outcomes |
| `date_of_interaction` | Tarehe ya huduma iliyopongezwa | Recommended | For correlation with staff or program performance records |
| `program_name` | Jina la programu | Yes | Links compliment to specific implementing program |

---

## AI Conversation Guidance for This Industry

- **Lead with empathy and establish anonymity option immediately.** Many social welfare complainants fear retaliation (loss of benefits) for complaining. Begin with: "Unaweza kushiriki maoni yako bila kutaja jina lako — habari zako zitakuwa salama." Establishing anonymity early builds trust.
- **Identify the program before asking about the problem.** Ask "Ni programu gani unayozungumzia — TASAF, PSSN, OVC, WFP, au nyingine?" first. Different programs have different offices, timelines, and escalation paths; routing without program identification wastes time.
- **For child protection signals, prioritize safety over form completeness.** If the complaint involves a child in immediate danger, collect `child_location` and `immediate_danger_flag` first, then immediately provide emergency contacts (police 112, social welfare office). Do not pause to collect beneficiary ID or program history.
- **Do not ask for national ID (NIDA) for general complaints.** Social welfare complainants are often among the most vulnerable and may not have NIDA. The beneficiary program ID (if they have it) is sufficient for most complaint types; NIDA is only needed for identity verification in fraud investigations.
- **For payment complaints, confirm the payment period before asking about the amount.** Ask "Malipo ya mwezi gani hayakufika?" before asking "Kiasi gani ulichotarajiwa?" — many complainants do not know exact amounts but clearly know which payment cycle is missing.
- **Distinguish between the program and the delivery agent.** A complaint about a mobile money operator not releasing funds is different from a complaint that TASAF did not send the payment. Ask "Je, TASAF walituma pesa lakini mwakala hakukupa, au pesa haikutumwa kabisa?" to correctly route the complaint.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Program name | "Ni programu gani unayozungumzia — TASAF, PSSN, msaada wa OVC, chakula cha WFP, au nyingine?" |
| Anonymity preference | "Je, unataka kubaki bila jina, au unaweza kushiriki jina lako ili tukusaidie vizuri zaidi?" |
| Issue type | "Tatizo lako ni nini hasa — malipo hayakufika, ulikataliwa, ofisa alikufanyia vibaya, au kitu kingine?" |
| Date of incident | "Hili lilitokea lini — ni siku ngapi au wiki ngapi zilizopita?" |
| Location | "Hii ilitokea wilayani gani, katika kata au kijiji gani?" |
| Household affected | "Familia yako ina watu wangapi wanaotegemea msaada huu?" |
| Vulnerability | "Je, kuna mwanakaya mwenye ulemavu, mzee, au mtoto yatima katika familia yako?" |
| Prior action | "Je, umeshajaribu kuwasiliana na ofisi au mtu yeyote kuhusu tatizo hili? Walikusema nini?" |
| Desired outcome | "Unataka nini kitokee baada ya malalamiko yako — kurejeshewa malipo, uchunguzi, au kitu kingine?" |
| Child safety check | "Je, mtoto huyo yuko salama sasa hivi, au yuko katika hatari ya haraka?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| `issue_type` | `child_protection` AND `immediate_danger_flag = Yes` | Escalate within 1 hour; provide police number (112) and district social welfare office; create emergency priority ticket |
| `issue_type` | `child_protection` AND `immediate_danger_flag = No` | Create priority ticket; notify MoHCDGEC Social Welfare Department; advise 24-hour follow-up |
| `issue_type` | `caseworker_misconduct` AND `bribe_amount_requested_tzs > 0` | Refer to PCCB Tanzania; escalate to program management unit; create high-priority investigation ticket |
| `issue_type` | `residential_care_complaint` AND `care_standard_alleged_failed` includes physical abuse | Escalate to facility inspector and police; flag for unannounced inspection |
| `issue_type` | `benefit_not_received` AND `number_of_households_affected > 50` | Community-level failure flag; escalate to district coordinator; create bulk complaint ticket |
| `issue_type` | `wrongful_exclusion` AND `vulnerability_status` includes disability or elderly | Priority review ticket; reference Persons with Disabilities Act 2010 rights |
| `issue_type` | `food_assistance_failure` AND `food_condition = Spoiled` | Escalate to TFDA and district health officer; public health risk flag |
| `vulnerability_status` | Refugee OR asylum_seeker AND benefit denied | Escalate to UNHCR focal point; create priority ticket with UNHCR reference |
| `anonymous_flag` | Yes | Never request identifying details; assign system-generated reference number for follow-up; confirm anonymity is protected |
| `prior_action_taken` | Yes AND no response received from agency | Escalate directly to district or regional level; do not re-route to same office |
| `issue_type` | `data_privacy_breach` | Escalate to program data protection officer; log incident with reference number |

---

*Sources: UNICEF HOPE Grievance Management module, UNHCR Minimum Standards on CFM, World Bank/UNDP GRM in Social Cash Transfer Programs (2022), Zambia MCDSS SCT GRM, Philippines 4Ps GRS (World Bank 2014), FAO AFR100 GRM, Tanzania Child Act Cap 13 RE 2019, Tanzania Persons with Disabilities Act 2010, TASAF III Program Implementation Manual*
