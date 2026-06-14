---
tags: [industry-kb, feedback-classification, field-standards]
---
# Hospital / Clinic — Feedback Collection Fields & Standards

## Industry Identifiers

hospital, clinic, health center, dispensary, outpatient, inpatient, ward, maternity, emergency, OPD, casualty, laboratory, radiology, X-ray, ultrasound, CT scan, MRI, doctor, nurse, clinical officer, medical officer, consultant, surgeon, obstetrician, pediatrician, physiotherapist, NHIF, referral hospital, mission hospital, Muhimbili, MNH, Aga Khan, Regency Medical Centre, Jakaya Kikwete Cardiac Institute, JKCI, Mnazi Mmoja, Bugando, KCMC, Ocean Road Cancer Institute, blood bank, operating theatre, ICU, NICU, triage, prescription, diagnosis, treatment, discharge, admission, zahanati, kituo cha afya, CHW, community health worker, ANC, antenatal, chanjo, immunization, daktari, muuguzi, mkunga, wodi, hospitali, kliniki, dawa, matibabu, upasuaji, kipimo, maabara, rufaa

## Why Industry-Specific Fields Matter

Generic feedback fields cannot capture the clinical, regulatory, and safety dimensions of healthcare complaints — a medication error requires batch number, prescriber name, and harm level data that drive mandatory reporting to TMDA and the Medical Council; without these fields, a potentially preventable death goes untracked and uncorrected. Tanzania's MOHCDGEC, JCI accreditation standards, and WHO-ICPS all mandate specific structured data that generic forms entirely miss.

## Source Standards

- WHO International Classification for Patient Safety (ICPS) 2009 — 10 classification classes
- NHS National Reporting and Learning System (NRLS) — 5-level harm scale, 19 medication error sub-types
- JCI Hospital Accreditation Standards 7th/8th Edition — PCC.3.1 (formerly PFR.3)
- ISO 10002:2018 — Complaint Management System minimum fields
- Tanzania MOHCDGEC National Guide for Complaint, Compliment and Suggestion Management in Health Facilities (Office of PO-PSMGG, 2012 revised)
- Tanzania TMDA (formerly TFDA) — pharmacovigilance and adverse event reporting
- Healthcare Complaints Analysis Tool (HCAT) — 3-domain / 7-category framework (Imperial College London, validated PMC11725527, PMC9819617)
- Severity Assessment Code (SAC) — NZ Health Quality & Safety Commission
- NHS Local Authority Social Services and NHS Complaints Regulations 2009
- Medical Practitioners and Dentists Act (Tanzania) — mandatory emergency treatment provision

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complaint_unique_id | Nambari ya malalamiko | Yes | ISO 10002:2018 — tracking, deduplication, follow-up across all departments |
| date_complaint_received | Tarehe malalamiko yalipokewa | Yes | Statutory timeline compliance — NHS: 3-day acknowledge / 25-day resolve; Tanzania Guide monthly Annex 6 reporting |
| time_complaint_received | Wakati malalamiko yalipokewa | Yes | Distinguishes immediate vs. delayed reporting; SLA measurement |
| channel_received | Njia ya kupokea | Yes | Walk-in / phone / SMS / online / written letter / proxy — multi-channel access equity reporting required by Tanzania Guide |
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Identity verification; legal compliance; JCI PCC.3.1 |
| complainant_relationship_to_patient | Uhusiano na mgonjwa | Yes | Self / family / carer / legal representative / staff — consent verification; NHS Regulations 2009 Reg.13 |
| complainant_phone | Simu ya mlalamikaji | Yes | Response delivery; ISO 10002 mandatory contact field |
| complainant_email | Barua pepe ya mlalamikaji | No | Optional secondary contact for written response |
| patient_full_name | Jina kamili la mgonjwa | Yes | Case linkage; clinical record retrieval |
| patient_date_of_birth | Tarehe ya kuzaliwa ya mgonjwa | Yes | Identity disambiguation — multiple patients with same name |
| patient_hospital_number | Nambari ya hospitali / kadi ya mgonjwa | Yes | Clinical record retrieval; JCI audit trail; links to medical file |
| patient_sex | Jinsia ya mgonjwa | Yes | Demographic pattern analysis; gender-specific clinical risk |
| consent_to_investigate | Idhini ya uchunguzi | Yes | Legal: NHS Regs 2009; JCI PCC.3.1; Tanzania data protection — verbal or signed |
| patient_informed_complaint_lodged | Je, mgonjwa amearifiwa? | Yes | JCI PCC.3.1 Measurable Element — patient participation in resolution is accreditation requirement |
| facility_name | Jina la kituo | Yes | Multi-facility systems; national MOHCDGEC aggregation via Annex 6 |
| department_unit | Idara / Kitengo | Yes | Root cause analysis; staff accountability; Tanzania Guide Annex 5 field |
| date_of_incident | Tarehe ya tukio | Yes | NRLS, WHO-ICPS — incident date is separate from complaint date; patient may complain weeks later |
| time_of_incident | Wakati wa tukio | Yes | Time-specific investigation; shift accountability |
| stage_of_care | Hatua ya matibabu | Yes | HCAT domain mapping; WHO-ICPS Incident Characteristics class 4 — admission / diagnosis / treatment / medication / discharge / post-discharge |
| complaint_category | Aina ya malalamiko | Yes | HCAT 3-domain taxonomy; Tanzania Annex 6 aggregate reporting; drives resolution pathway |
| harm_level | Kiwango cha madhara | Yes | Core to all frameworks — determines urgency, escalation, and reporting obligation |
| is_life_threatening | Je, ni hatari ya maisha? | Yes | Triggers immediate clinical escalation; SAC Level 1 process |
| incident_description | Maelezo ya tukio | Yes | WHO-ICPS class 2; JCI investigation record; legal narrative |
| remedy_sought | Suluhisho anayotaka | Yes | ISO 10002:2018 Section 8.2 — patient's desired outcome guides resolution approach |
| complaint_handler_name | Jina la afisa wa malalamiko | Yes | Accountability; ISO 10002; Tanzania Guide — Designated Complaint Officer |
| date_acknowledged | Tarehe ya kutoa jibu la awali | Yes | NHS: 3 working days; Tanzania Guide; ISO 10002 — acknowledgment SLA |

### Harm Level Classification (use for harm_level field)

| Code | Level | Description |
|------|-------|-------------|
| 0 | No Harm | Incident occurred, no patient impact |
| 1 | Near Miss | Reached patient but harm was prevented by action or chance |
| 2 | Low Harm | Minor temporary harm, minimal additional treatment needed |
| 3 | Moderate Harm | Significant temporary harm, additional clinical intervention required |
| 4 | Severe Harm | Permanent or life-altering harm; near-death event |
| 5 | Death | Incident contributed to or caused patient death |

*Sources: NHS NRLS 5-level scale; SAC NZ Health Quality & Safety Commission; WHO-ICPS Patient Outcomes class*

### Complaint Category Taxonomy (use for complaint_category field — HCAT framework)

**Domain 1 — Clinical:**
- `clinical_safety` — medication error, surgical error, infection, diagnosis error, equipment failure, wrong patient, wrong site
- `clinical_quality` — clinical competence, treatment outcome, inadequate care plan, monitoring failure

**Domain 2 — Management:**
- `environment` — cleanliness, privacy, noise, broken facilities, infection control failures
- `institutional_processes` — waiting times, appointment scheduling, billing, discharge planning, referral delays, records management

**Domain 3 — Relationship:**
- `listening` — patient not heard, ignored, dismissed, concerns minimized
- `communication` — information not given, poor explanation, language barrier, test results not communicated
- `respect_and_rights` — dignity violation, discrimination, consent violation, confidentiality breach, refusal of emergency treatment

### Conditional Fields (collect based on complaint type)

**If complaint_category = clinical_safety AND involves medication:**

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| drug_name | Jina la dawa | Yes | NRLS medication error taxonomy; links to pharmacy records |
| drug_dosage | Kipimo cha dawa | Yes | Wrong dose is 15% of NRLS medication errors — most common error type |
| error_sub_type | Aina ya kosa la dawa | Yes | NRLS 19-category taxonomy: omission / wrong dose / wrong drug / wrong frequency / wrong patient / wrong route / storage error / labeling error |
| prescriber_name | Jina la daktari aliyeandika agizo | Yes | Prescribing pattern analysis; accountability |
| prescriber_designation | Cheo cha daktari | Yes | Links to Medical Council of Tanganyika for serious errors |
| batch_number | Nambari ya bachi ya dawa | Yes | Product recall scoping; TMDA reporting |
| adverse_effects_description | Maelezo ya madhara | Yes | Pharmacovigilance trigger; patient outcome assessment |
| onset_time_after_drug | Muda uliopita kabla ya madhara | Yes | Naranjo causality algorithm requires this field |
| reported_to_tmda | Je, imeripotiwa TMDA? | Yes | Mandatory if harm_level >= 3 — TMDA 15-day serious ADR reporting rule |

**If complaint_category = clinical_safety AND involves surgery/procedure:**

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| procedure_type | Aina ya upasuaji / utaratibu | Yes | Identifies the specific intervention for investigation |
| operating_theatre_number | Nambari ya chumba cha upasuaji | No | Location specificity for infection control investigation |
| surgical_team_members | Wanachama wa timu ya upasuaji | Yes | WHO Surgical Safety Checklist accountability |
| consent_form_signed | Fomu ya idhini ilisainiwa? | Yes | Legal: signed consent is prerequisite for elective procedures |
| infection_suspected | Je, maambukizi yanashukiwa? | Yes | Triggers infection control investigation; mandatory reporting under IPC protocol |

**If complaint_category = clinical_safety AND involves diagnosis:**

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| presenting_symptoms | Dalili za awali za mgonjwa | Yes | Establishes what was known at time of diagnosis |
| diagnosis_given | Utambuzi uliotolewa | Yes | Documents the potentially erroneous diagnosis |
| correct_diagnosis | Utambuzi uliofuata (sahihi) | No | If known — enables clinical review of diagnostic error pattern |
| delay_duration | Muda wa kuchelewa utambuzi | Yes | Quantifies harm from delayed diagnosis |

**If complaint_category = environment OR institutional_processes:**

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| specific_location | Eneo mahususi | Yes | Facility/ward/area — environmental issues require precise location |
| frequency_of_issue | Mara ngapi tatizo limetokea | Yes | Distinguishes systemic from one-off; prioritization |
| photographs_available | Je, kuna picha? | No | Evidence for environmental complaints (cleanliness, broken equipment) |

**If complaint_category = respect_and_rights AND involves consent violation:**

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| consent_type_violated | Aina ya idhini iliyovunjwa | Yes | Informed consent / treatment consent / research consent / photography consent |
| staff_member_named | Jina la mtumishi aliyehusika | Yes | JCI PCC.3.1; Medical Council investigation |
| witness_name | Jina la shahidi | No | Corroboration for allegations against staff |

**If harm_level >= 3 (Moderate, Severe, or Death):**

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| contributing_factors | Sababu zinazochangia | Yes | WHO-ICPS class 5 — human / system / environmental / organizational / patient factors |
| immediate_cause | Sababu ya haraka | Yes | Proximate cause for root cause analysis |
| detection_method | Njia ya kugundua tukio | Yes | WHO-ICPS class 7 — patient report / staff observation / audit / near miss system |
| mitigating_factors | Mambo yaliyozuia madhara zaidi | No | WHO-ICPS class 8 — what prevented worse outcome |
| ameliorating_actions_taken | Hatua za haraka zilizochukuliwa | Yes | WHO-ICPS class 9; JCI investigation record |
| attending_clinician_name | Jina la daktari aliyehudumia | Yes | Clinical record linkage; JCI audit; Medical Council |
| clinical_notes_reference | Kumbukumbu ya rekodi ya matibabu | Yes | Evidence cross-referencing; JCI survey requirement |
| referred_to_higher_body | Kufikishwa kwa mamlaka ya juu? | Yes | MOHCDGEC / Medical Council / Tanzania Human Rights Commission |
| learning_action_implemented | Hatua ya kujifunza iliyotekelezwa | Yes | WHO-ICPS class 10; NRLS learning system; prevents recurrence |

### Resolution Standards for This Industry

- **Acknowledgment**: Within 3 working days of receiving complaint (NHS standard; Tanzania Guide)
- **Resolution target**: Within 25 working days (NHS); Tanzania Guide specifies monthly Quality Improvement Team (QIT) review
- **Documentation**: All complaints must be logged in Tanzania Annex 5 / Annex 5a format
- **Monthly reporting**: Aggregate data reported via Annex 6 to Quality Improvement Team (QIT), then Hospital Management Team (HMT)
- **Serious incidents (harm_level 4-5)**: Immediate investigation; report to Medical Council of Tanganyika within 24 hours for clinical negligence; MOHCDGEC notification
- **Medication errors (harm_level >= 3)**: TMDA mandatory reporting within 15 working days; 7-day expedited for fatal/life-threatening
- **Regulatory escalation path**: Complaint Officer → QIT → HMT → MOHCDGEC → Medical Council of Tanganyika → Parliamentary/National Ombudsman

### Escalation Triggers (field values requiring immediate escalation)

- `harm_level = 5 (Death)` → Immediate report to Medical Council of Tanganyika + MOHCDGEC; preserve all records; do not alter clinical notes
- `harm_level = 4 (Severe Harm)` → Report to Medical Council within 24 hours; root cause analysis within 72 hours
- `is_life_threatening = Yes` → Escalate to clinical duty officer immediately before continuing feedback collection
- `complaint_category = clinical_safety` AND `error_sub_type = wrong_blood_transfusion` → Blood Bank emergency protocol; MOHCDGEC notification
- `complaint_category = clinical_safety` AND `error_sub_type = wrong_patient_identity` (newborn/surgery) → Immediate identity verification audit; MOHCDGEC
- `complaint_category = respect_and_rights` AND involves sexual assault by health worker → Criminal matter; refer to police AND Medical Council within 24 hours
- `complaint_category = clinical_safety` AND `error_sub_type = counterfeit_drug` → TMDA emergency notification; batch recall
- `stage_of_care = emergency` AND `remedy_sought includes refusal_of_treatment_due_to_payment` → Legal violation under Medical Practitioners Act; immediate escalation to facility Medical Superintendent
- `complaint_category = clinical_safety` AND involves child → Mandatory reporting trigger; check for child abuse indicators
- `reported_to_tmda = No` AND `harm_level >= 3` AND medication involved → Flag for mandatory TMDA ADR reporting; 15-day clock starts now

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| date_submitted | Tarehe iliyowasilishwa | Yes | Trend analysis; ISO 10002 tracking |
| channel | Njia ya uwasilishaji | Yes | Walk-in / online / SMS / suggestion box / staff relay — access equity monitoring; Tanzania Guide |
| submitter_name | Jina la mwasilishaji | No | Anonymous submissions must be accepted — ISO 10002:2018; Tanzania Guide |
| submitter_contact | Mawasiliano ya mwasilishaji | No | Optional — for follow-up if submitter wishes to be informed of outcome |
| target_department | Idara inayolengwa | Yes | Route to correct department head; cannot implement without knowing scope |
| specific_service_or_process | Huduma au mchakato mahususi | Yes | Actionability — "waiting times" must specify which: triage / lab results / pharmacy / discharge |
| frequency_of_issue | Mara ngapi tatizo hili linatokea | Yes | Distinguishes systemic problems from one-off events; prioritization for QIT |
| proposed_solution | Suluhisho linalopendekezwa | Yes | Makes suggestion actionable; PMC9327649 found 69% of healthcare suggestion box content was complaints — proposals must be separated |
| patient_impact | Athari kwa mgonjwa | Yes | Links to quality improvement priority; justifies urgency |
| urgency_level | Kiwango cha haraka | No | Immediate / short-term / long-term improvement |
| has_patient_safety_implication | Je, ina athari za usalama wa mgonjwa? | Yes | Any suggestion touching medication, equipment, or clinical protocols must be flagged — may require QIT review rather than departmental manager |
| response_provided | Je, jibu limetolewa? | Yes | ISO 10002 requires acknowledgment; Tanzania Guide |

### Industry-Specific Improvement Categories

- `process_flow` — Triage systems, appointment booking, discharge planning, referral pathways, patient navigation
- `staff_training` — Communication skills, cultural competency, clinical updates, patient rights awareness
- `facilities_equipment` — Infrastructure, medical equipment, cleanliness, infection control infrastructure
- `communication_systems` — Lab results notification, discharge summaries, SMS alerts, patient portals
- `patient_rights` — Consent processes, complaints box placement, rights charter displays, language access
- `medication_safety` — Allergy screening protocols, dispensing double-checks, prescription error prevention
- `nhif_insurance` — NHIF processing efficiency, dedicated insurance desks, claims transparency
- `staffing_levels` — Nurse-to-patient ratios, night shift coverage, specialist availability
- `infection_control` — Handwashing stations, isolation facilities, PPE availability, waste management

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| inquiry_unique_id | Nambari ya swali | Yes | Tracking; prevents loss of unanswered queries |
| date_received | Tarehe iliyopokelewa | Yes | SLA monitoring |
| time_received | Wakati uliopokelewa | Yes | Shift accountability for response |
| channel | Njia | Yes | Response channel matching — phone inquiry needs phone response |
| inquirer_name | Jina la muulizaji | Yes | Identity for response delivery |
| inquirer_relationship_to_patient | Uhusiano na mgonjwa | Yes | Consent/privacy: third-party inquiries about a patient require patient consent before information is shared |
| patient_hospital_number | Nambari ya hospitali ya mgonjwa | No | Record retrieval for specific patient queries |
| patient_name | Jina la mgonjwa (kama tofauti) | No | Identity disambiguation |
| query_type | Aina ya swali | Yes | Routes to correct department; see taxonomy below |
| specific_question | Swali mahususi | Yes | Context for response — the actual question being asked |
| urgency_level | Kiwango cha haraka | Yes | Routine / urgent / emergency — determines SLA and escalation |
| preferred_response_channel | Njia inayopendelewa ya kujibu | Yes | Accessibility; patient preference; NHS accessibility duty |
| date_responded | Tarehe ya kujibu | Yes | Closure; SLA compliance |
| responded_by | Aliyejibu | Yes | Accountability |

### Common Inquiry Types & Required Data Per Type

**appointment** — Scheduling / rescheduling / cancellation
- Additional fields: `preferred_date`, `specialist_type`, `referral_letter_number` (if referred), `existing_hospital_number`

**test_results** — Laboratory / radiology / pathology results
- Additional fields: `test_type`, `test_date`, `requesting_clinician_name`
- Note: Requires patient identity verification before releasing any result — consent check mandatory

**billing_insurance** — Bill queries / NHIF / insurance claims
- Additional fields: `invoice_number`, `nhif_card_number`, `insurance_provider`, `amount_in_dispute`

**referral_status** — Incoming or outgoing referral processing
- Additional fields: `referring_facility`, `referral_date`, `referral_number`, `specialist_department`

**discharge_documentation** — Discharge summaries / medical certificates / sick notes
- Additional fields: `admission_date`, `discharge_date`, `document_type`

**medication_prescription** — Prescription queries / refills / dosage clarification
- Additional fields: `drug_name`, `prescribing_doctor`, `prescription_date`
- Note: Clinical questions about dosage must be routed to pharmacist or clinician — AI should not answer

**treatment_information** — Procedure information / preparation instructions
- Additional fields: `procedure_name`, `scheduled_date`

**rights_complaints_process** — How to complain / patient rights / escalation paths
- Additional fields: none — provide Tanzania Guide process information; direct to Complaint Officer

**emergency_access** — Emergency treatment availability / ambulance / casualty
- Urgency: always set to `emergency`; provide direct phone number immediately

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| date_submitted | Tarehe iliyowasilishwa | Yes | Trend analysis; recognition timeliness — delay reduces impact |
| channel | Njia | Yes | Access monitoring |
| submitter_name | Jina la mshukuriaji | No | Anonymous compliments are valid; PMC9327649: 30.5% of healthcare suggestion box submissions are compliments |
| staff_member_praised | Jina la mtumishi anayeshukuriwa | Yes | Recognition delivery; HR record; staff morale — this is the primary purpose of the record |
| staff_designation | Cheo / Jukumu la mtumishi | Yes | Role-specific excellence tracking — nurse / doctor / cleaner / receptionist / pharmacist |
| department_ward | Idara / Wodi | Yes | Department-level performance trending; QIT recognition reports |
| date_of_praised_interaction | Tarehe ya huduma iliyoshukuriwa | Yes | Links to specific encounter for corroboration and specificity |
| specific_action_praised | Tendo mahususi linaloshukuriwa | Yes | Makes compliment meaningful and actionable — enables specific behavior reinforcement in training |
| how_it_helped | Jinsi ilivyosaidia | Yes | Qualitative learning — "explained my diagnosis clearly" feeds communication training; "noticed my allergy" feeds safety protocols |
| category_of_excellence | Aina ya ubora | No | Clinical skill / Communication / Compassion / Efficiency / Environment / Safety action |
| staff_notified | Je, mtumishi amearifiwa? | Yes | Closes loop; motivation; ISO 10002 continuous improvement |
| safety_relevant_experience | Je, kulikuwa na jambo la usalama? | No | If pharmacist caught a prescribing error, or nurse noticed incorrect dosage — positive near-miss that feeds system learning |

---

## AI Conversation Guidance for This Industry

- **Start with the patient's experience, not the form.** Open with "What happened to you / your family member at the health facility?" Let the patient narrate. Extract `incident_description`, `date_of_incident`, `department_unit`, and `harm_level` from the narrative before asking structured follow-up questions. Jumping to form fields immediately feels clinical and cold — exactly the opposite of what a distressed patient needs.

- **Assess urgency before collecting details.** After the first narrative response, always ask: "Is this a medical emergency happening right now, or are you reporting something that already happened?" If it is ongoing, stop data collection and provide emergency contacts (emergency number, ambulance, duty officer). The feedback system must never delay someone who needs immediate care.

- **Harm level is the pivot question — ask it gently.** Ask "Was the patient physically hurt because of this?" or "Did this cause any injury, complications, or hospitalization?" Map the answer to the 0–5 harm scale internally. Do NOT use clinical language like "what was the harm severity level?" to a distressed family member.

- **For medication errors, collect drug name and batch number before the patient discards packaging.** Say: "If you still have the medicine box or packaging, please keep it — the batch number on it is very important for the investigation." This single request can make or break a TMDA product recall.

- **Never ask about staff members in a way that feels accusatory early in the conversation.** Collect staff names after establishing the core incident facts. Phrase as "Do you remember who was treating you or your family member at that time?" rather than "Who did this to you?"

- **For clinical complaints in Swahili, avoid direct medical terminology translations that don't land.** "Tatizo la damu" is understood; "madhara ya transfusion" may not be. Use the patient's own language from their narrative back to them when asking follow-up questions.

- **Compliments need the staff member's name to be useful.** If the submitter says "the nurses were wonderful," gently probe: "Do you remember any of their names? Even a first name helps us make sure they receive recognition." A compliment without a name cannot reach the person who earned it.

## Swahili Key Phrases for Field Collection

| Purpose | Swahili Phrase |
|---------|---------------|
| Opening complaint | "Tafadhali nieleze kilichotokea katika hospitali / kliniki" |
| Date of incident | "Tukio hili lilitokea siku gani na wakati gani?" |
| Department | "Ulikuwa katika idara gani — OPD, wodi, maabara, au mahali pengine?" |
| Harm assessment | "Je, ulijeruhiwa au ulipata madhara ya kimwili kutokana na tukio hili?" |
| Staff name | "Je, unakumbuka jina la daktari, muuguzi, au mtumishi aliyekuwa anakuhudumia?" |
| Drug name and batch | "Dawa hii inaitwa nini? Kama una pakiti ya dawa, angalia nambari ya bachi iliyoandikwa nayo" |
| Urgency check | "Je, hali hii bado inaendelea sasa hivi, au unataka kuripoti kitu kilichotokea awali?" |
| Consent to investigate | "Je, unakubali kwamba hospitali ifanye uchunguzi kuhusu malalamiko yako?" |
| Remedy sought | "Unataka nini kutokea baada ya kuripoti hili — msamaha, uchunguzi, fidia, au kitu kingine?" |
| Suggestion specificity | "Unaweza kunieleza zaidi kuhusu mchakato mahususi unaotaka kuboresha?" |
| Compliment staff name | "Je, unakumbuka jina la muuguzi / daktari huyo — hata jina la kwanza linasaidia ili wapokee pongezi" |
| Follow-up contact | "Je, tungependa kukuwasiliana nawe tutakapokuwa tumefanya uchunguzi — unapendelea simu au barua pepe?" |
| NHIF query | "Kadi yako ya NHIF ilikataliwa — unajua tarehe iliyokataliwa na idara iliyokukatalia?" |
| Emergency redirect | "Hali hii ni ya dharura sasa hivi? Piga simu [nambari ya dharura] mara moja — usisimame hapa" |

## Action Recommendations Based on Field Values

| If Field | Equals | Recommended Action |
|----------|--------|-------------------|
| harm_level | 5 (Death) | Immediately escalate to facility Medical Superintendent; preserve clinical notes; notify MOHCDGEC and Medical Council of Tanganyika; do not resolve at complaint officer level |
| harm_level | 4 (Severe Harm) | Root cause analysis within 72 hours; Medical Council notification; senior clinical review |
| harm_level | 3 (Moderate Harm) | QIT review within 5 days; department head notified; corrective action plan required |
| harm_level | 1 or 2 | Standard QIT resolution cycle; department head informed; patient acknowledged within 3 days |
| is_life_threatening | Yes | Stop feedback collection; provide emergency contacts; flag for immediate clinical response |
| complaint_category | clinical_safety — medication | TMDA ADR reporting if harm_level >= 3; pharmacy director notified; batch number preserved |
| complaint_category | respect_and_rights — sexual_assault | Police referral + Medical Council within 24 hours; do not handle internally |
| complaint_category | institutional_processes — refused_emergency_treatment | Legal violation under Medical Practitioners Act; Medical Superintendent + MOHCDGEC |
| error_sub_type | wrong_blood_transfusion | Blood Bank emergency protocol; MOHCDGEC notification; immediate patient review |
| reported_to_tmda | No, but harm_level >= 3, medication involved | Generate TMDA ADR report; 15-day mandatory deadline; 7-day if fatal/life-threatening |
| complaint_category | clinical_safety, child involved | Check child abuse indicators; mandatory reporting to social welfare if suspected |
| channel | SMS or online | Auto-acknowledge within 1 hour; assign complaint ID; human follow-up within 1 working day |
| urgency_level | emergency (inquiry) | Provide direct emergency numbers immediately; do not route through standard inquiry queue |
| staff_member_praised | named specifically | Notify staff member and line manager within 24 hours; log in HR recognition record |
| safety_relevant_experience | Yes (compliment) | Convert positive near-miss into learning report; share at clinical governance meeting |
| has_patient_safety_implication | Yes (suggestion) | Route to QIT directly, not just department manager; flag for next clinical governance meeting |
| nhif_card_number | provided + rejected | Route to NHIF desk officer; check registration validity; log as NHIF process complaint |

---

## Key Entities & Roles (Tanzania Context)

**Staff Titles:** Doctor (Daktari), Nurse (Muuguzi), Clinical Officer, Medical Officer, Specialist/Consultant, Obstetrician, Pediatrician, Surgeon, Radiologist, Pathologist, Pharmacist (Mfamasia), Laboratory Technician, Physiotherapist, Nutritionist/Dietitian, Health Records Officer, Ward Attendant, Orderly, Community Health Worker (CHW), Hospital Administrator, Medical Superintendent, Complaint Officer

**Departments:** OPD, Casualty/Emergency, Maternity Ward, NICU, ICU, Surgical Ward, Medical Ward, Paediatric Ward, Laboratory, Radiology, Pharmacy, Blood Bank, Physiotherapy, Nutrition Unit, Health Records

**Insurance:** NHIF, iCHF (improved Community Health Fund), Employer Insurance, AAR, Jubilee, Resolution Health

**Regulatory Bodies:** MOHCDGEC, TMDA (Tanzania Medicines and Medical Devices Authority), Medical Council of Tanganyika, Nursing Council of Tanzania, NACP, WHO, Office of PO-PSMGG

**Key Facilities:** Muhimbili National Hospital (MNH), JKCI, Ocean Road Cancer Institute, Aga Khan Hospital, Regency, Mnazi Mmoja, Bugando Medical Centre, KCMC, zahanati (dispensary), vituo vya afya (health centers)
