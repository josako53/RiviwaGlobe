---
tags: [industry-kb, field-collection, feedback-fields]
---
# Government / Public Services — Feedback Collection Fields & Standards

## Industry Identifiers

Ministry, district office, ward office, municipal council, Huduma Centre, EGOV portal, NIDA, RITA, BRELA, TRA, TANESCO, DAWASCO, land registry, PPRA, civil service, government tender, local government authority (LGA), Serikali, court registry, immigration department, police station, public school, national hospital, passport office, birth certificate, business license, building permit, public utility, government subsidy, civil servant, constituency office, right of occupancy, tax clearance, procurement, e-Government, PO-PSMGG, e-Mrejesho, malalamiko serikali, halmashauri, ofisi ya wilaya, ofisi ya kata, kata, mtaa, kijiji, diwani, mbunge, DC, RC, WEO, DED, MLHHSD

## Why Industry-Specific Fields Matter

Government service complaints require precise identification of the institution, department, service type, and reference/application numbers because the same presenting problem (delay, denial, billing error) routes to entirely different offices and has different legal timelines depending on whether the agency is TRA, NIDA, BRELA, MLHHSD, or a municipal council. Generic fields produce complaints that cannot be routed, tracked, or escalated within Tanzania's multi-tier public administration structure.

## Source Standards

- Tanzania PO-PSMGG Client Complaint Management Guidelines (2012, revised 2023) — national mandatory framework for all public institutions
- e-Mrejesho electronic complaints platform (emrejesho.gov.go.tz) — operationalizes PO-PSMGG for Malalamiko, Mapendekezo, Maulizo, Pongezi
- Transparency International Complaint Mechanisms Reference Guide (2016) — anti-corruption complaint field standards
- EU Ombudsman Complaint Form (ombudsman.europa.eu) — structured approach for administrative maladministration
- World Bank ESF ESS10 GRM Register fields — project-level GRM standards applicable to government-delivered development projects
- USAID SEE-AM Accountability and Feedback Plans — sector-level feedback field standards
- Tanzania Public Procurement Act / PPRA portal — procurement complaint requirements
- Tanzania Land Act Cap 113, Tax Administration Act, Business Activities Registration Act — regulatory timelines and escalation requirements

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL government service complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| government_institution | Taasisi ya Serikali | Yes | Routes complaint to the correct agency — NIDA, TRA, BRELA, DAWASCO, TANESCO, MLHHSD, Halmashauri, etc. |
| department_or_unit | Idara / Kitengo | Yes | Identifies the specific office within the institution for assignment |
| service_type | Aina ya Huduma | Yes | Determines applicable legal timeline and escalation path (e.g. land title vs. tax clearance vs. ID card) |
| issue_type | Aina ya Tatizo | Yes | Classifies complaint for routing: Delay / Denial / Billing Error / Corruption / Staff Conduct / Document Error / Procurement / Other |
| application_reference_number | Namba ya Maombi / Kumbukumbu | Recommended | Enables agency to locate the specific case without searching by name — critical for follow-up |
| date_of_service_interaction | Tarehe ya Mwingiliano | Yes | Establishes timeline and whether service delivery standard has been breached |
| number_of_visits_or_attempts | Idadi ya Ziara / Majaribio | Recommended | Documents persistence of unresolved issue; supports escalation if citizen has repeatedly engaged |
| payment_receipt_number | Namba ya Risiti ya Malipo | Conditional | Required if complaint involves fee paid but service not delivered or incorrect billing |
| date_payment_made | Tarehe ya Malipo | Conditional | Required when payment dispute is the issue |
| bribe_or_corruption_demand | Ombi la Rushwa | Conditional | Yes/No flag; if Yes → immediate escalation to PCCB / TAKUKURU |
| prior_escalation_attempted | Imefikishwa Juu Hapo Awali? | Yes | Has citizen already reported to supervisor, ombudsman, or anti-corruption body — yes/no; if yes, to whom and when |
| prior_escalation_outcome | Jibu la Kufikisha Juu | Conditional | Required if prior_escalation_attempted = Yes; what happened |
| desired_outcome | Matokeo Yanayotarajiwa | Yes | What the citizen wants: correction, refund, apology, expedited processing, staff action, etc. |
| evidence_available | Ushahidi Unaopatikana | Recommended | Checkbox: Receipt / Official letter / Photograph / Witness / None — enables case strength assessment |
| complainant_full_name | Jina Kamili | Yes | Required by PO-PSMGG for non-anonymous submissions; used for response delivery |
| complainant_phone | Namba ya Simu | Yes | Required for follow-up and resolution notification |
| complainant_email | Barua Pepe | Recommended | Alternative contact; required for written decision notifications |
| anonymous_submission | Wasilisho la Siri | Yes | Yes/No — anonymous complaints receive no personal response but are still actioned per PO-PSMGG |
| consent_to_data_use | Idhini ya Kutumia Taarifa | Yes | Required by PDPA and PO-PSMGG for processing and follow-up contact |
| location_ward_district | Kata / Wilaya | Yes | Identifies jurisdiction; required for LGA, land, and ward-level complaints |

### Conditional Fields (collect based on issue type)

**If issue_type = Corruption / Bribe Demand:**
- corrupt_official_name_or_description (Jina / Maelezo ya Ofisa) — name, badge number, or physical description of the official
- corruption_type — Bribe demand / Nepotism / Misuse of public resources / Contract manipulation / Fraud
- corruption_amount_or_value — amount or value of bribe demanded or paid (TZS)
- witnesses_available — Yes/No; if yes, names and contacts
- evidence_type — Cash receipt / Transaction record / Recording / Document / None

**If issue_type = Billing Error / Incorrect Charge (TANESCO / DAWASCO / TRA / Municipal):**
- billing_period — month and year of disputed bill
- amount_billed — amount on the disputed bill (TZS)
- amount_expected — what citizen believes they owe (TZS)
- meter_reading_dispute — Yes/No (for TANESCO/DAWASCO)
- previous_payments_made — Yes/No; amount and date of last payment made

**If issue_type = Document Error (NIDA / RITA / BRELA / Passport / Land Title):**
- document_type — NIDA Card / Birth Certificate / Marriage Certificate / Land Title / Business Certificate / Passport / Other
- error_description — exactly what is wrong on the document
- correct_information — what the correct information should be
- supporting_proof_available — Yes/No; type of proof (birth record, ID, sworn affidavit)

**If issue_type = Procurement / Tender:**
- tender_reference_number — PPRA tender number
- tender_opening_date — date bids were opened
- disqualification_reason_given — what reason was provided, if any
- payment_overdue_for_completed_work — Yes/No; amount outstanding (TZS); months overdue

**If issue_type = Infrastructure / Public Works:**
- infrastructure_type — Road / Water pipe / Street light / Drainage / Public building / Borehole / Market
- affected_area_size — number of households or street/area description
- duration_of_problem — how long the problem has existed (days/weeks/months)
- safety_risk — Yes/No; description of immediate risk to life or health

### Issue Type Classification

| Code | Issue Type | PO-PSMGG Category |
|------|------------|-------------------|
| GOV-01 | Delayed service — application/process not completed within declared timeline | Ucheleweshaji wa Huduma |
| GOV-02 | Denied service — application rejected or service refused without adequate reason | Kukataa Huduma |
| GOV-03 | Wrong decision — incorrect ruling, assessment, or administrative decision | Uamuzi Mbaya |
| GOV-04 | Bribe or corruption demand — unofficial payment requested for service | Rushwa / Ufisadi |
| GOV-05 | Rude, abusive, or disrespectful staff conduct | Tabia Mbaya ya Mtumishi |
| GOV-06 | Document error — incorrect information on issued government document | Kosa katika Hati |
| GOV-07 | Document lost or not returned — original documents submitted but not returned | Upotezaji wa Hati |
| GOV-08 | Incorrect billing or overcharging — utility bill or tax assessment error | Bili Isiyo Sahihi |
| GOV-09 | Procurement irregularity — tender process violated regulations | Ukiukwaji wa Manunuzi |
| GOV-10 | Infrastructure failure — public works not maintained or repaired | Miundombinu Iliyoharibika |
| GOV-11 | Unauthorized disconnection — TANESCO/DAWASCO cutoff without due process | Kukata Huduma Bila Ruhusa |
| GOV-12 | Payment not processed — fee paid but service account not updated | Malipo Hayakushughulikiwa |
| GOV-13 | Other — does not fit above categories | Nyingine |

### Resolution Standards for This Industry

Per PO-PSMGG Guidelines and e-Mrejesho platform standards:
- **Acknowledgment**: Within 3 working days of receipt
- **Simple/non-sensitive complaints**: Resolution or substantive update within **14 working days**
- **Complex complaints** (land, procurement, constitutional rights): Within **30 working days** with written explanation if extension needed
- **Corruption complaints**: Forwarded to PCCB/TAKUKURU within **48 hours**; citizen notified of referral
- **Infrastructure safety emergencies**: Escalated to relevant authority within **24 hours**
- Written response required for all formal written complaints (letter or email)
- Complainant must be informed of outcome and right to escalate further

Per EU Ombudsman standards (for complaints about EU-funded government projects):
- Complaint must demonstrate prior contact with the institution has been attempted
- Two-year limitation period from date the citizen became aware of the facts
- All correspondence with the institution must be attached

### Escalation Triggers (field values requiring immediate escalation)

- `bribe_or_corruption_demand = Yes` → forward to PCCB (Prevention and Combating of Corruption Bureau / TAKUKURU) within 48 hours; notify citizen of referral
- `issue_type = GOV-04` AND `corrupt_official_name_or_description` provided → prioritize for anti-corruption investigation
- `infrastructure_type` + `safety_risk = Yes` → emergency escalation to municipal engineering or DED within 24 hours
- `issue_type = GOV-11` AND affected entity = health facility / school / water utility → critical public service; escalate to EWURA/TANESCO senior management immediately
- `issue_type = GOV-07` AND `document_type = Land Title or Certificate of Title` → potential fraud; escalate to MLHHSD
- `issue_type = GOV-09` (Procurement irregularity) AND evidence provided → refer to PPRA
- Government official named as threatening or physically assaulting a citizen → refer to Police and PCCB simultaneously
- Minor or vulnerable person denied legally mandated registration (birth certificate, NIDA) → escalate to RITA/NIDA director

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| target_institution | Taasisi Inayolengwa | Yes | Ensures the suggestion reaches the right ministry or agency |
| service_or_process_to_improve | Huduma / Mchakato wa Kuboresha | Yes | Specifies what exactly should change |
| improvement_category | Aina ya Uboreshaji | Yes | Digital transformation / Staff conduct / Processing speed / Infrastructure / Policy / Accessibility / Other |
| affected_population_group | Kundi Linaloathiriwa | Recommended | General public / Elderly / PWD / Youth / Women / Rural residents / Small business owners / Other |
| proposed_change_description | Maelezo ya Mabadiliko Yanayopendekezwa | Yes | Full description of the suggestion |
| expected_measurable_outcome | Matokeo Yanayotarajiwa | Recommended | What improvement would look like if implemented — enables prioritization |
| submitter_contact | Mawasiliano ya Mtoa Mapendekezo | Optional | For follow-up if the institution wants clarification |

### Industry-Specific Improvement Categories

- **Digital / e-Government**: Online application portals, mobile-friendly EGOV, SMS status tracking, mobile money payment acceptance, digital document issuance
- **Processing speed**: Published service delivery timelines, dedicated counters for priority groups, appointment booking systems
- **Transparency**: Public complaints registers, published tender results, open budget data at ward/district level
- **Anti-corruption**: Independent corruption hotline, published penalties for civil servants, whistleblower protection
- **Accessibility**: Services at ward level to reduce travel, Swahili-language interfaces, disability access at Huduma Centres
- **Infrastructure**: Road maintenance, public building upkeep, school toilets, market drainage
- **Staff training**: Customer service, technical competence, anti-bribery awareness

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| institution | Taasisi | Yes | Routes the inquiry to the correct agency |
| service_type | Aina ya Huduma | Yes | Determines which team or officer handles the response |
| specific_question | Swali Maalum | Yes | The exact information being requested |
| application_reference_number | Namba ya Maombi | Conditional | Required if inquiry is about a specific pending application |
| date_application_submitted | Tarehe ya Kuwasilisha Maombi | Conditional | Required when asking about status of a specific application |
| submitter_full_name | Jina Kamili | Yes | Required to locate the citizen's records |
| submitter_phone | Namba ya Simu | Yes | For response delivery |
| preferred_response_channel | Njia Inayopendelewa ya Majibu | Yes | SMS / WhatsApp / Email / Phone call / Written letter |

### Common Inquiry Types & Required Data Per Type

**Status inquiry on pending application:**
- institution + service_type + application_reference_number + date_application_submitted + submitter_full_name

**Document correction inquiry (NIDA / RITA / BRELA):**
- institution + document_type + description of error + what correct information should be + supporting_proof_available

**Billing dispute inquiry (TRA / TANESCO / DAWASCO / Municipal):**
- institution + billing_period + amount_billed + amount_expected + date_last_payment

**Process / procedure inquiry (how to apply, what documents needed):**
- institution + service_type + specific_question — no reference number needed; general information response

**Land and property inquiry:**
- service_type (transfer / subdivision / right of occupancy / building permit) + plot_number_or_location + ward_district

**Procurement / tender inquiry:**
- tender_reference_number + tender_opening_date + specific_question (eligibility / results / payment)

**Tax inquiry (TRA):**
- TIN_number (if known) + tax_type (VAT / PAYE / income tax / withholding) + specific_question

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| institution_being_commended | Taasisi Inayopongezwa | Yes | Routes compliment to the relevant institution for internal recognition |
| specific_officer_name | Jina la Afisa Maalum | Recommended | Enables individual recognition and performance tracking |
| service_or_interaction | Huduma / Mwingiliano Uliofanya Vizuri | Yes | Documents exactly what worked well — feeds service improvement data |
| date_of_positive_experience | Tarehe ya Uzoefu Mzuri | Recommended | Helps correlate compliments with staff shifts, process changes, or campaigns |
| what_made_it_exceptional | Kilichoifanya Kuwa Bora | Recommended | Speed / Accuracy / Staff attitude / System worked / No unofficial payment requested / Proactive communication |
| submitter_name | Jina la Mtoa Pongezi | Optional | For acknowledgment; not required |
| submitter_contact | Mawasiliano | Optional | For acknowledgment letter from institution |

---

## AI Conversation Guidance for This Industry

- **Start with the institution and service type before anything else.** The single most important routing field is which government body the citizen is dealing with. Ask: "Ni taasisi gani ya serikali unayozungumza nao?" (Which government institution are you dealing with?) before collecting any other details. Without this, the complaint cannot be routed.
- **Collect the reference or application number if one exists.** Government services in Tanzania almost always generate a reference number at intake (TRA TIN, BRELA registration number, NIDA application slip, PPRA tender reference). Ask: "Je, una namba yoyote ya maombi au kumbukumbu kutoka kwa taasisi hiyo?" This single field unlocks rapid case lookup.
- **Probe for the corruption flag carefully but directly.** If the citizen mentions "kulipa kidogo," "kufanya haraka," "facilitation," or "chai," ask gently but clearly: "Je, mtu yeyote katika ofisi hiyo alikuomba malipo ya ziada au pesa za nje ya rasmi?" — Yes/No. This is a critical escalation trigger.
- **Do not collect full personal details before understanding the issue.** Establish institution, service type, and issue type first. Collect name and phone only after the issue is clear — this reduces friction for sensitive anti-corruption complaints where the citizen may be cautious.
- **For billing disputes (TANESCO/DAWASCO/TRA), always ask for the billing period and amount.** These are non-negotiable for any investigation. Avoid open-ended "describe your bill" — ask specifically: "Bili hiyo inaonyesha kiasi gani? Na ni kwa mwezi gani?"
- **Distinguish between general how-to inquiries and status-of-pending-application inquiries.** For status inquiries, always request the reference number and date submitted. For general how-to, give the information directly if available in the KB without creating a formal record.

## Swahili Key Phrases for Field Collection

| Field Being Collected | Swahili Phrase |
|----------------------|----------------|
| government_institution | "Unapigana na ofisi gani ya serikali — kama vile TRA, NIDA, BRELA, Halmashauri, au nyingine?" |
| service_type | "Huduma gani hasa unayotafuta — kama kitambulisho, leseni ya biashara, hati ya ardhi, au kodi?" |
| application_reference_number | "Je, una namba ya maombi, stakabadhi, au kumbukumbu yoyote waliyokupa?" |
| date_of_service_interaction | "Ulienda ofisini au uliwasilisha maombi yako lini — tarehe gani takriban?" |
| issue_type (corruption) | "Je, mtu yeyote alikuomba malipo ya ziada — nje ya ada rasmi — ili kukusaidia?" |
| prior_escalation_attempted | "Je, umeshajaribu kupiga kilio kwa mkubwa wa ofisi hiyo au taasisi nyingine? Ukapata jibu gani?" |
| desired_outcome | "Unataka nini kutokana na malalamiko haya — haraka ya kushughulikia, kurudishiwa pesa, au hatua dhidi ya mtu maalum?" |
| evidence_available | "Je, una hati yoyote kama risiti, barua, au picha zinazohusiana na tatizo hili?" |
| anonymous_submission | "Je, ungependa malalamiko yako yashughulikiwe kwa siri bila kujulikana, au unaridhika kutaja jina lako?" |
| billing_period | "Bili hii ni ya mwezi na mwaka gani hasa?" |
| infrastructure safety | "Je, tatizo hili linahatarisha usalama wa binadamu — kama jengo la kuanguka, barabara hatari, au maji yenye sumu?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| bribe_or_corruption_demand | Yes | Flag Priority-1; create escalation to PCCB/TAKUKURU; notify citizen of referral within 24h |
| issue_type | GOV-04 (Corruption) | Assign to anti-corruption escalation path; do not route to the same institution being complained about |
| safety_risk | Yes | Emergency escalation to municipal DED or relevant line ministry within 24 hours |
| prior_escalation_attempted | Yes | Skip first-level routing; send directly to senior officer or supervisory body |
| service_type | Land Title / Right of Occupancy | Route to MLHHSD; flag for legal review if document fraud suspected |
| payment_receipt_number | provided | Include in case; request utility or TRA to reconcile against their system |
| issue_type | GOV-09 (Procurement) | Route to PPRA; attach all provided evidence |
| issue_type | GOV-11 (Disconnection) + affected entity = health facility | Critical — escalate to TANESCO/DAWASCO managing director and EWURA simultaneously |
| anonymous_submission | Yes | Process complaint; remove personal identifiers; no direct response to complainant; close loop internally |
| issue_type | GOV-07 (Document lost) + document_type = Land Title | Flag for possible fraud; escalate to MLHHSD Anti-Fraud Unit |
| number_of_visits_or_attempts | 3 or more | Tag as Chronic Non-Resolution; escalate to Regional Commissioner office |

---

*Framework sources: PO-PSMGG Client Complaint Management Guidelines (Tanzania, 2023); e-Mrejesho platform (emrejesho.gov.go.tz); Transparency International Complaint Mechanisms Reference Guide (2016); EU Ombudsman Guide to Complaints (ombudsman.europa.eu); World Bank ESF ESS10 Guidance Note (2018); USAID SEE-AM Accountability and Feedback Plans.*
