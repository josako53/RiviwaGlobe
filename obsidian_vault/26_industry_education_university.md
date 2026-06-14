---
tags: [industry-kb, feedback-classification, field-standards]
---
# Education / University — Feedback Collection Fields & Standards

## Industry Identifiers

NECTA, NACTE, TCU, UDSM, Muhimbili University, Ardhi University, HESLB, O-level, A-level, Form IV, Form VI, CSEE, ACSEE, ward secondary school, private school, national school, vocational training, school fees, bursary, examination results, class teacher, headmaster, principal, lecture, tutorial, student union, academic registration, semester, transcript, graduation, school inspection, BEST, school feeding, capitation grant, district education officer, TIE, PSLE, Standard 7, university placement, course deferral, degree certificate, academic appeal, MUHAS, SUA, MZUMBE, DUCE, OUT, NECTA certificate, grade appeal, continuous assessment, supplementary exam, academic dishonesty, plagiarism, HESLB loan, student loan, bursary committee, PTA, school hostel, dormitory, laboratory, NECTA remarking, Form V selection, intake, university portal, UDSM portal

## Why Industry-Specific Fields Matter

Education complaints require precise identification of the academic context — institution, programme, academic year, and issue type — because the routing, jurisdiction, and resolution standards differ entirely between a primary school under MoE oversight, a technical college under NACTE, a university under TCU, and a national examination body like NECTA. Generic complaint fields cannot distinguish a fee dispute from a grade appeal or identify which regulatory body must be notified.

## Source Standards

- ISO 21001:2018 — Educational organizations management systems (Clauses 7.4.3, 9.1.2, 10.3)
- QAA UK Quality Code for Higher Education 2024 — Concerns, Complaints and Appeals guidance
- OIA Good Practice Framework — Handling Complaints and Academic Appeals
- TCU Client Service Charter — Tanzania Commission for Universities (14 working day resolution commitment)
- NECTA / NACTE regulatory mandate (Tanzania)
- HESLB Act (Tanzania)
- ACQF Quality Assurance Guideline 5 — African Continental Qualifications Framework
- OECD Education at a Glance 2024

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| institution_name | Jina la shule/chuo | Yes | Routes complaint to the correct institution and its regulatory oversight body |
| institution_type | Aina ya taasisi | Yes | Determines jurisdiction: primary school (MoE), secondary (MoE/BEST), technical (NACTE), university (TCU), exam body (NECTA) |
| faculty_department | Idara/Kitivo | Yes (university/college) | Required to route complaint to the correct internal body |
| programme_course_name | Jina la kozi/programu | Yes | Ties complaint to a specific academic unit; needed for ISO 21001 monitoring |
| academic_year_semester | Mwaka wa masomo/Muhula | Yes | Establishes jurisdictional timeframe for OIA/QAA timeliness assessment |
| student_id | Nambari ya msomaji | Optional | Aids identity verification while protecting anonymity where needed |
| complainant_name | Jina la mlalamikaji | Yes | Required for all follow-up and resolution communication |
| complainant_contact | Mawasiliano (simu/barua pepe) | Yes | Required to communicate resolution |
| issue_type | Aina ya tatizo | Yes | Drives routing, escalation rules, and regulatory notification requirements |
| incident_date | Tarehe ya tukio | Yes | OIA/QAA require timeliness assessment; TCU SLA clock starts from incident date |
| detailed_description | Maelezo ya kina | Yes | Required for ISO 21001 documented information; basis for investigation |
| steps_already_taken | Hatua zilizochukuliwa tayari | Yes | QAA Code requires exhaustion of informal resolution before formal complaint |
| internal_appeal_exhausted | Je, rufaa ya ndani imekwisha? | Yes | Prerequisite for escalation to TCU, NECTA, or external body |
| desired_outcome | Matokeo yanayotarajiwa | Yes | OIA GPF §7 requires organisations to understand what resolution is sought |
| consent_to_share | Idhini ya kushiriki taarifa | Yes | QAA Code confidentiality principle — complainant must consent before disclosure to named parties |
| supporting_documents | Nyaraka za kuthibitisha | Optional | Transcripts, grade reports, correspondence, receipts — OIA GPF guidance |

### Conditional Fields (collect based on issue type)

**If issue_type = Exam Dispute / Grade Appeal:**
- exam_name → specific exam (CSEE, ACSEE, university unit exam, continuous assessment)
- candidate_number → NECTA candidate number or university exam number
- subject_name → specific subject under dispute
- result_obtained → grade or mark received
- result_expected_reason → reason complainant believes result is incorrect
- remarking_applied → whether NECTA/university remarking was already requested (Yes/No)
- remarking_reference → reference number if remarking was applied for

**If issue_type = Fee Dispute:**
- fee_amount_paid_tzs → total amount paid (TZS)
- fee_receipt_number → receipt number if available
- fee_type → school fees / HESLB / building levy / uniform / PTA / lab fees / other
- fee_schedule_reference → whether a government fee schedule applies
- heslb_reference_number → HESLB loan reference if loan disbursement is the issue

**If issue_type = Staff Conduct / Harassment / Discrimination:**
- staff_member_name → name of accused staff member (optional — complainant may wish to protect identity)
- staff_role → teacher / lecturer / administrator / security / other
- harassment_type → physical / sexual / verbal / discriminatory
- witnesses_present → Yes/No; witness names if complainant consents
- previous_report_to_institution → whether previously reported to institution (Yes/No + outcome)

**If issue_type = Certificate / Transcript Delay:**
- certificate_type → degree certificate / transcript / NECTA certificate / NACTE certificate
- application_date → date certificate was applied for
- expected_delivery_date → date institution or NECTA promised delivery
- reference_number → application or tracking reference

**If issue_type = Admission Dispute:**
- application_reference → TCU/university application reference number
- programme_applied_for → exact programme applied for
- programme_assigned → programme incorrectly assigned (if applicable)
- selection_body → TCU central selection / direct university admission / NACTE
- rejection_reason_given → reason given by institution (if any)

**If issue_type = Facilities / Safety:**
- facility_type → dormitory / laboratory / classroom / sanitation / electricity / library / sports
- safety_risk → Yes/No (if Yes → triggers escalation review)
- duration_of_problem → how long the facility issue has persisted

### Issue Type Classification

| Code | Issue Type | Regulatory Body | TCU SLA |
|------|-----------|----------------|---------|
| EDU-GR-01 | Exam Dispute / Grade Appeal | NECTA / NACTE / University Senate | 14 working days (TCU) |
| EDU-GR-02 | Lecturer / Teacher Conduct | University / MoE / TIE | 14 working days |
| EDU-GR-03 | Sexual Harassment / Abuse | University / Police / MoE | Immediate escalation |
| EDU-GR-04 | Discrimination | University / Human Rights body | 14 working days |
| EDU-GR-05 | Facilities / Infrastructure | University / MoE / Local Government | 30 working days |
| EDU-GR-06 | Fee Dispute | University / TCU / MoE / HESLB | 14 working days |
| EDU-GR-07 | Certificate / Transcript Delay | NECTA / NACTE / University Registrar | 14 working days (TCU) |
| EDU-GR-08 | Plagiarism / Academic Integrity Accusation | University Academic Committee | 21 working days |
| EDU-GR-09 | Admission Dispute | TCU / NACTE / University | 14 working days |
| EDU-GR-10 | Student Welfare / Bullying | Institution / Ministry of Education | 14 working days |
| EDU-GR-11 | Capitation Grant / Financial Misuse | CAG / MoE / PO-RALG | Immediate for theft |
| EDU-GR-12 | Physical Punishment of Student | MoE / Police | Immediate escalation |

### Resolution Standards for This Industry

- **TCU Charter**: Complaints involving TCU-registered universities must be resolved within **14 working days**. If unresolved, complaint may be escalated to TCU.
- **QAA / OIA Good Practice**: Formal complaints should produce a written outcome letter explaining the decision and available appeal routes.
- **NECTA Remarking**: NECTA remarking applications must be submitted within prescribed deadlines after results release; NECTA targets result confirmation within 60 days.
- **ISO 21001 §10**: Institutions must document complaints, investigate root causes, implement corrective actions, and monitor recurrence.
- **Financial Issues**: HESLB grievances escalate to HESLB Head Office if not resolved by the university within 14 working days.

### Escalation Triggers (field values that require immediate escalation)

- `harassment_type = sexual` OR `staff_conduct = physical punishment` → report to institution head and refer to Police/Ministry of Education within 24 hours
- `safety_risk = Yes` AND `facility_type = structural/electrical` → immediate risk assessment required; notify local government authority
- `issue_type = EDU-GR-11 (financial misuse)` AND evidence of embezzlement → refer to CAG/MoE within 48 hours
- Student is missing from boarding school → notify Police and MoE within 24 hours
- Epidemic or disease outbreak in dormitory with no institutional response → notify MoH and MoE immediately
- `exam_type = NECTA` AND confirmed paper leakage or impersonation → refer to NECTA Directorate and Police immediately
- Child denied emergency medical care by institution → notify MoE and emergency services immediately

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| institution_name | Jina la shule/chuo | Yes | Ties improvement to the specific institution's management system (ISO 21001 §10.3) |
| programme_course_name | Jina la kozi/programu | Yes | Improvement suggestions must be linked to a specific academic unit for action |
| suggestion_category | Aina ya pendekezo | Yes | ISO 21001 §10.3 continual improvement classification |
| suggestion_detail | Maelezo ya pendekezo | Yes | Full description of the improvement idea |
| expected_benefit | Faida inayotarajiwa | Optional | Helps institution evaluate feasibility and impact |
| academic_year | Mwaka wa masomo | Optional | Gives temporal context |
| student_id | Nambari ya msomaji | Optional | Encouraged but not required — ISO 21001 promotes participation |

### Industry-Specific Improvement Categories

| Category Code | Category Name | Swahili |
|--------------|---------------|---------|
| EDU-SG-01 | Course Content / Curriculum | Maudhui ya kozi/Mtaala |
| EDU-SG-02 | Assessment Methods | Mbinu za tathmini |
| EDU-SG-03 | Teaching / Delivery Methods | Mbinu za ufundishaji |
| EDU-SG-04 | Physical Facilities / Resources | Vifaa na miundombinu |
| EDU-SG-05 | Digital Tools / Technology | Zana za kidijitali |
| EDU-SG-06 | Student Support Services | Huduma za wanafunzi |
| EDU-SG-07 | Examination / Results Process | Mchakato wa mitihani |
| EDU-SG-08 | Financial Aid / HESLB Process | Mkopo wa HESLB/Bursary |
| EDU-SG-09 | Campus Life / Welfare | Maisha ya chuo kikuu |
| EDU-SG-10 | Governance / Administration | Utawala wa taasisi |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| institution_name | Jina la shule/chuo | Yes | Routes inquiry to the correct institution or regulatory body |
| inquiry_type | Aina ya swali | Yes | Determines information source and expected response format |
| full_name | Jina kamili | Yes | Required for personalised response (TCU Charter) |
| contact_details | Mawasiliano | Yes | Required for follow-up |
| student_id_or_application_number | Nambari ya msomaji/ombi | Optional | Speeds up record look-up |
| specific_question | Swali maalum | Yes | ISO 21001 §7.4.3 — full question text needed |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Additional Fields Needed |
|-------------|-------------------------|
| Admission status / TCU selection | application_reference, programme_applied_for, selection_year |
| NECTA results / Transcript | candidate_number, exam_year, subject_name |
| HESLB loan status / Disbursement | heslb_application_number, university_name, academic_year |
| Fee structure / Schedule | institution_type, programme_name, academic_year |
| Programme accreditation / Recognition | programme_name, awarding_body (NACTE/TCU) |
| Supplementary / Re-sit exam | unit_code, exam_session, gpa_if_required |
| Degree certificate processing | graduation_year, student_id, certificate_type |
| Transfer between universities | current_institution, target_institution, programme |
| NECTA certificate correction | certificate_number, error_description |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| institution_name | Jina la shule/chuo | Yes | ISO 21001 §9.1.2 satisfaction monitoring — must be institution-linked |
| subject_of_praise | Kinachosifiwa | Yes | Enables institution to recognise and replicate excellent practice |
| named_individual | Jina la mtu anayesifiwa | Optional | Positive feedback loops to staff; ISO 21001 recommends individual recognition |
| description_of_experience | Maelezo ya uzoefu mzuri | Yes | ISO 21001 §9.1.2 learner satisfaction data |
| academic_year_semester | Mwaka wa masomo/Muhula | Optional | Gives temporal context for the positive experience |

### Praise Subject Categories

| Code | Subject | Swahili |
|------|---------|---------|
| EDU-AP-01 | Lecturer / Academic Staff | Mhadhiri/Mwalimu |
| EDU-AP-02 | Support / Administrative Staff | Wafanyakazi wa utawala |
| EDU-AP-03 | Specific Course / Programme | Kozi/Programu |
| EDU-AP-04 | Facility / Resource | Vifaa/Miundombinu |
| EDU-AP-05 | Examination / Results Process | Mchakato wa mitihani |
| EDU-AP-06 | Financial Aid Process | Mchakato wa mkopo/bursary |
| EDU-AP-07 | Student Welfare / Support | Huduma za wanafunzi |

---

## AI Conversation Guidance for This Industry

- **Start with institution and level first**: Ask "Ni shule/chuo gani unalozungumza nacho?" and then "Ni ngazi gani ya elimu — sekondari, chuo cha ufundi, au chuo kikuu?" before asking about the issue. This determines jurisdiction immediately.
- **For exam disputes, collect exam specifics before the narrative**: Ask for the exam name (NECTA CSEE/ACSEE, continuous assessment, university unit), the candidate number, and the result obtained before asking the complainant to explain what went wrong. Numerical and reference data are more reliable when collected before emotional narrative.
- **For harassment or physical punishment, validate and protect first**: Express that the matter is serious, confirm that the complainant is safe, then ask for details. Do NOT ask for the accused person's name as the first question — ask for the general nature of the incident and work toward identity details gently.
- **For fee disputes, confirm whether it is a government school fee issue or university fee / HESLB issue** early: these route to different bodies (MoE vs. TCU vs. HESLB) and the resolution pathway is completely different.
- **Never ask for student ID as a mandatory field at the start** — many complainants (especially parents complaining about a school) do not have this ready. Collect it after gathering the institution and issue type, and frame it as helpful rather than required: "Je, una nambari ya usajili wa mtoto wako? Itasaidia kuharakisha uchunguzi, lakini si lazima."

## Swahili Key Phrases for Field Collection

| Field Being Collected | Swahili Phrase to Use |
|----------------------|----------------------|
| institution_name | "Tafadhali niambie jina la shule au chuo unachozungumzia." |
| issue_type | "Tatizo lako linahusiana na nini hasa — mitihani, ada, mwalimu, udahili, au jambo lingine?" |
| incident_date | "Tatizo hili lilitokea lini? Niambie tarehe au mwezi na mwaka." |
| steps_already_taken | "Je, umeshazungumza na mtu yeyote kuhusu tatizo hili — kama mwalimu mkuu au ofisi ya usajili?" |
| desired_outcome | "Unataka nini kifanyike ili tatizo hili lisuluhike? Tueleze tunavyoweza kukusaidia." |
| candidate_number | "Je, una nambari yako ya mtihani wa NECTA? Itasaidia kutafuta matokeo yako." |
| internal_appeal_exhausted | "Je, umeshafuata utaratibu wa ndani wa malalamiko katika taasisi yako? Majibu yao yalikuwa nini?" |
| supporting_documents | "Je, una nyaraka yoyote kama risiti, barua, au nakala ya matokeo? Unaweza kupakia hapa." |
| consent_to_share | "Ili tuweze kuchunguza tatizo hili, tutahitaji kushiriki baadhi ya taarifa na taasisi husika. Je, unakubali?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | EDU-GR-03 (Sexual Harassment) | Immediate escalation to institution head, welfare officer, and if victim is a minor — to Police and MoE |
| issue_type | EDU-GR-12 (Physical Punishment) | Escalate to MoE; if injury sustained → Police referral; document all details immediately |
| internal_appeal_exhausted | Yes | Notify complainant of TCU escalation path; provide TCU Client Service Charter reference |
| internal_appeal_exhausted | No | Advise complainant to first raise issue formally with institution; provide template request letter |
| institution_type | University (TCU-registered) | Apply TCU 14 working day SLA; log TCU reference if escalation is needed |
| exam_type | NECTA CSEE/ACSEE | Provide NECTA contact for remarking; confirm remarking deadline has not passed |
| fee_type | HESLB | Provide HESLB Head Office contact and portal reference; check loan disbursement status |
| safety_risk | Yes | Flag for urgent review within 24 hours; do not close ticket until institution confirms resolution |
| harassment_type | Sexual | Apply Riviwa urgent escalation protocol; create case note flagged for human review |
| issue_type | EDU-GR-11 (Financial Misuse) | Flag for escalation to CAG; advise complainant to retain all receipts and evidence |
| desired_outcome | Compensation | Note that TCU / OIA can recommend compensation; explain process and timeline |
| remarking_applied | Yes | Ask for remarking reference and date; check whether results are still pending or were upheld |

---

## Key Entities & Roles

**Regulatory & Examination Bodies:** NECTA, NACTE, TCU, TIE, BEST, VETA, HESLB
**Public Universities:** UDSM, MUHAS, Ardhi University, SUA, MZUMBE, DUCE, MUCE, OUT
**Oversight:** Ministry of Education, Science and Technology (MoEST); President's Office Regional Administration and Local Government (PO-RALG) for primary/secondary schools
**Financial Aid:** HESLB, District Bursary Committee
**Key Roles:** Class Teacher, Subject Teacher, Head Teacher, Deputy Principal, Dean of Students, Academic Registrar, University Lecturer, Research Supervisor, District Education Officer (DEO), NACTE Inspector

---

## Kiswahili / Swahili Equivalents

### Malalamiko (Complaints)
- "Mwalimu hayupo zaidi ya anavyokuwepo darasani"
- "Watoto wetu hawana vitabu vya masomo tangu mwezi wa kwanza"
- "Mtoto wangu alipigwa na mwalimu — hili ni kinyume cha sheria"
- "Nilisaidiwa mkopo wa HESLB lakini pesa haijafika chuoni"
- "Matokeo yangu ya NECTA yana makosa ya herufi za jina langu"
- "Shule inatoza ada zaidi ya kiwango cha serikali bila sababu"
- "Mtoto wetu alitumwa nyumbani kwa deni la TZS 20,000 wakati wa mtihani"
- "Matokeo ya mtihani yanashikiliwa kwa sababu ya madeni — hii si haki"

### Mapendekezo (Suggestions)
- "Walimu wapatiwe mafunzo ya kuendelea kila mwaka"
- "HESLB itume pesa haraka kabla ya mwaka wa masomo kuanza"
- "NECTA itoe matokeo ndani ya wiki sita baada ya mtihani"
- "Ingekuwa vizuri kuwa na mfumo wa mtandaoni wa kuangalia matokeo"

### Maswali (Inquiries)
- "Nifanye nini ili mtoto wangu asajiliwe kwenye chaguo la TCU?"
- "Mkopo wa HESLB unaomba nyaraka gani?"
- "Ninawezaje kuomba tathmini upya ya matokeo ya NECTA?"
- "Chuo cha UDSM kinahitaji alama ngapi kwa udaktari?"

### Pongezi (Compliments)
- "Mwalimu wa hisabati amebadilisha mtoto wangu — sasa anapenda somo hilo"
- "Chuo kikuu kilitatua tatizo la usajili wangu kwa siku tatu tu — asante"
- "HESLB ilimaliza ombi langu haraka na pesa ilifika kabla ya muhula"

---

## Industry-Specific Escalation Triggers

- Physical assault or corporal punishment of a student by a teacher or school official
- Sexual harassment or abuse of a student by staff member
- Examination paper leakage or impersonation at NECTA center
- Student suicide or attempted suicide linked to academic pressure, bullying, or abuse
- Student missing from boarding school with no notification to parents
- Confirmed embezzlement of capitation grant or student fee funds
- Structural collapse risk or fire hazard at institution with no response
- Student denied emergency medical care by institution
- Epidemic outbreak in dormitory or campus with no management response
- Academic staff strike exceeding 4 weeks destroying academic calendar
- Child with disability denied exam accommodation in violation of law

---

## Disambiguation Notes

- Fee complaints about **HESLB loan disbursement** → classify as Education (not Banking) if the primary subject is the student loan program administration, not a bank's conduct
- **Teachers' salaries / employment** → classify as Education when impact is on student learning; Labour if purely about employment rights
- **VETA / vocational training** → classify as Education even though linked to employment; institution type is the classifier
- **Student mental health / counseling** → classify as Education if the institution's support services are subject; classify as Healthcare if a medical facility is the primary subject
- **School feeding program** → classify as Education; institutional context overrides food/FMCG classification
