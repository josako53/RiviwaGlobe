---
tags: [industry-kb, feedback-classification, field-standards]
---
# Training / Professional Development — Feedback Collection Fields & Standards

## Industry Identifiers

corporate training, skills development, professional certification, safety training, technical training institute, ICT training center, language school, soft skills training, e-learning platform, apprenticeship program, VETA, NACTE, CPD, OSHA safety training, NIT, vocational training, facilitator, trainer, instructor, workshop, bootcamp, curriculum, course material, certificate of completion, assessment, exam, competency framework, continuing education, upskilling, reskilling, NBAA training, accounting course, project management training, leadership development, HR training, COSTECH, CPD points, accreditation, in-house training, blended learning, LMS, professional body recognition

## Why Industry-Specific Fields Matter

Training complaints require different fields from general education because the commercial relationship (provider sells a course to a paying client or employer) introduces fee and refund rights, accreditation misrepresentation risks, and CPD regulatory obligations that do not exist in formal schooling. The course title, accrediting body, and whether a certificate was issued determine which regulatory body — VETA, NACTE, or a professional body like NBAA — has jurisdiction over the complaint.

## Source Standards

- ISO 21001:2018 — Applicable to training providers as educational organizations (Clauses 7.4.3, 8.3, 9.1.2, 10.3)
- VETA — Vocational Education and Training Authority (Tanzania), Vocational Education and Training Act Cap. 82
- NACTE — National Accreditation Council for Technical and Vocational Education and Training (Tanzania)
- ACQF Quality Assurance Module 5 — Quality assurance for TVET qualifications (Africa)
- ICB (Institute of Certified Bookkeepers) — Complaints Policy and Code of Professional Conduct
- CPD Standards Office / CPD UK — Accreditation and complaint norms
- OSHA Tanzania — Occupational Safety and Health Authority training standards
- NBAA — National Board of Accountants and Auditors (Tanzania)

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| training_provider_name | Jina la mtoa mafunzo | Yes | Identifies the commercial entity responsible; required by ICB Complaints Policy and ISO 21001 |
| course_programme_title | Jina la kozi/programu | Yes | ACQF Module 5; ISO 21001 — complaint must be tied to a specific course offering |
| training_dates | Tarehe za mafunzo | Yes | ICB Policy — timing is material to complaint validity; determines if issue was pre-, during, or post-training |
| trainer_facilitator_name | Jina la mkufunzi | Optional | ICB Code of Professional Conduct; helps in specific conduct complaints |
| enrollment_booking_reference | Nambari ya usajili | Optional | CPD Standards Office — aids record matching for fee and certificate disputes |
| amount_paid_tzs | Kiasi kilicholipwa (TZS) | Yes (if financial) | ICB Complaints Policy — required for financial remedy assessment |
| issue_type | Aina ya tatizo | Yes | Determines routing to VETA, NACTE, NBAA, OSHA, or internal resolution |
| detailed_description | Maelezo ya kina | Yes | ICB Policy requires written complaint detail; ISO 21001 §8.3 documented information |
| desired_outcome | Matokeo yanayotarajiwa | Yes | ICB Policy §5 specifies possible remedies; must be captured to assess resolution options |
| previous_complaint_to_provider | Je, ulishawasiliana na mtoa mafunzo? | Yes | ICB Policy and ISO 21001 require internal resolution attempt first |
| complainant_name | Jina la mlalamikaji | Yes | Required for all follow-up |
| complainant_contact | Mawasiliano (simu/barua pepe) | Yes | Required for resolution communication |
| supporting_documents | Nyaraka za kuthibitisha | Optional | Receipt, booking confirmation, course syllabus, certificate, correspondence |

### Conditional Fields (collect based on issue type)

**If issue_type = Content Not As Advertised / Poor Delivery:**
- advertised_course_outline → what was promised (attach brochure/website description if available)
- actual_content_delivered → what was actually taught
- number_of_sessions_attended → how many sessions the complainant attended
- delivery_language → English / Swahili / Other (especially relevant for Tanzania context)

**If issue_type = Certificate / Credential Not Issued:**
- course_completion_date → date the course was fully completed
- certificate_promised_date → date the provider said the certificate would be ready
- accreditation_body_claimed → what accreditation body the provider claimed (VETA / NACTE / ICB / NBAA / other)
- certificate_type_expected → competency certificate / attendance certificate / CPD certificate / professional qualification

**If issue_type = Refund Denied:**
- refund_request_date → date refund was requested
- refund_reason → course cancelled / poor quality / withdrawal before start / medical
- refund_policy_provided → whether a refund policy was communicated at enrollment (Yes/No)
- payment_method → mobile money / bank transfer / cash / invoice

**If issue_type = Accreditation Misrepresented:**
- accreditation_claimed | Ithibati iliyodaiwa → what accreditation was advertised
- accreditation_verification_attempt → whether complainant checked the claimed accreditation (Yes/No + outcome)
- professional_body_affected → NBAA / NACTE / VETA / CPD Standards Office / other

**If issue_type = Discrimination / Unfair Treatment:**
- grounds_of_discrimination → gender / disability / religion / ethnicity / age
- witnesses_present → Yes/No + witness names if consented
- previous_report_to_provider → Yes/No + date and outcome

**If issue_type = Unsafe Training Environment (OSHA):**
- environment_hazard_type → electrical / chemical / physical / fire / structural
- injury_or_illness_occurred → Yes/No
- injury_description → if Yes, describe injury
- osha_report_filed → whether an OSHA Tanzania report was filed (Yes/No)

**If issue_type = CPD Points Dispute:**
- cpd_points_claimed_by_provider → number of CPD points advertised
- cpd_points_on_certificate → number on issued certificate (if received)
- professional_body_requiring_cpd → which professional body requires these CPD points
- cpd_recognition_decision → whether the professional body recognized the CPD (Yes/No/Pending)

### Issue Type Classification

| Code | Issue Type | Regulatory Body | Resolution Target |
|------|-----------|----------------|-------------------|
| TRN-GR-01 | Content Not As Advertised | ISO 21001 / NACTE / VETA | 14 working days |
| TRN-GR-02 | Poor Quality of Delivery | ISO 21001 / NACTE | 14 working days |
| TRN-GR-03 | Certificate / Credential Not Issued | VETA / NACTE / ICB | 14 working days |
| TRN-GR-04 | Refund Denied | Consumer law / ICB Policy | 21 working days |
| TRN-GR-05 | Accreditation Misrepresented | VETA / NACTE / NBAA | 14 working days + regulatory referral |
| TRN-GR-06 | Discrimination / Unfair Treatment | ISO 21001 §5.3 / employment law | 14 working days |
| TRN-GR-07 | Unsafe Training Environment | OSHA Tanzania | Immediate (if injury) |
| TRN-GR-08 | CPD Points Dispute | Professional body (NBAA/ICB) | 21 working days |
| TRN-GR-09 | Scheduling / Communication Failure | Provider internal | 7 working days |
| TRN-GR-10 | Financial Fraud (collected fees, no delivery) | Police / Consumer Protection | Immediate |

### Resolution Standards for This Industry

- **ICB Complaints Policy**: Complaint must be submitted in writing; provider has 14 working days to respond at first instance; if unresolved, escalates to ICB Board and then Disciplinary Tribunal.
- **VETA (Cap. 82)**: VETA may investigate registered training providers; complaints about VETA-accredited providers can be referred to VETA for investigation.
- **NACTE**: Complaints about NACTE-accredited programmes can be referred to NACTE for investigation and possible suspension of accreditation.
- **ISO 21001 §10**: Providers must document complaints, investigate, implement corrective action, and communicate outcome to complainant.
- **CPD Standards Office**: CPD-accredited providers must resolve complaints within their published complaints procedure; escalation to CPD Standards Office for unresolved issues.

### Escalation Triggers (field values that require immediate escalation)

- `issue_type = TRN-GR-07` AND `injury_or_illness_occurred = Yes` → OSHA Tanzania must be notified immediately; case flagged urgent
- `issue_type = TRN-GR-10` (financial fraud — collected fees, disappeared) → refer to Police and Consumer Protection within 24 hours
- `accreditation_misrepresented = Yes` AND provider claiming VETA/NACTE without registration → refer to respective regulatory body within 48 hours
- `grounds_of_discrimination = disability` AND training access denied → urgent review; refer to human rights body
- Minor enrolled in adult professional training without supervision or consent → notify provider and relevant authority immediately
- Training materials confirmed to contain hate speech or illegal content → suspend dissemination; refer to law enforcement

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| training_provider_name | Jina la mtoa mafunzo | Yes | ISO 21001 §10.3 — improvement tied to the responsible provider |
| course_title | Jina la kozi | Yes | ACQF Module 5 — improvement must be linked to specific course |
| suggestion_category | Aina ya pendekezo | Yes | ISO 21001 §10.3 continual improvement classification |
| suggestion_detail | Maelezo ya pendekezo | Yes | Full description of the improvement idea |
| industry_sector_context | Sekta inayohusika | Optional | ICB — professional relevance of the suggestion (e.g., banking, mining, agriculture) |

### Industry-Specific Improvement Categories

| Category Code | Category Name | Swahili |
|--------------|---------------|---------|
| TRN-SG-01 | Content Update / Currency | Kuboresha maudhui ya kozi |
| TRN-SG-02 | Delivery Method (online/in-person/blended) | Njia ya kutoa mafunzo |
| TRN-SG-03 | Practical / Applied Component | Sehemu ya vitendo/uzoefu |
| TRN-SG-04 | Assessment Approach | Mbinu za tathmini |
| TRN-SG-05 | Materials / Resources | Nyenzo za mafunzo |
| TRN-SG-06 | Swahili Language Access | Maudhui ya Kiswahili |
| TRN-SG-07 | Accreditation / Recognition | Ithibati na utambuzi |
| TRN-SG-08 | Venue / Logistics | Mahali na mpangilio |
| TRN-SG-09 | Facilitator Quality Standards | Viwango vya mkufunzi |
| TRN-SG-10 | Scheduling / Accessibility | Ratiba na upatikanaji |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| training_provider_name | Jina la mtoa mafunzo | Yes | Routes inquiry to correct provider |
| inquiry_type | Aina ya swali | Yes | VETA mandate; ACQF credentials platform — determines information source |
| full_name | Jina kamili | Yes | ISO 21001 §7.4.3 |
| contact_details | Mawasiliano | Yes | ISO 21001 §7.4.3 |
| specific_question | Swali maalum | Yes | ISO 21001 §7.4.3 — full question required |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Additional Fields Needed |
|-------------|-------------------------|
| Course availability / Schedule | course_name, preferred_dates, delivery_format (in-person/online) |
| Accreditation validity / Status | accreditation_body (VETA/NACTE/NBAA/CPD), provider_name |
| CPD points / Recognition | professional_body, course_name, cpd_points_claimed |
| Cost / Funding / Subsidy | course_name, number_of_participants (if corporate), funding_source |
| Entry requirements | course_name, current_qualification_level |
| Certificate status / Issuance | course_name, completion_date, enrollment_reference |
| In-house / Corporate training | industry_sector, number_of_staff, topic_area, preferred_delivery_language |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| training_provider_name | Jina la mtoa mafunzo | Yes | ISO 21001 §9.1.2 — satisfaction monitoring must be institution-linked |
| course_title | Jina la kozi | Yes | ISO 21001 §9.1.2 — positive feedback tied to specific course |
| subject_of_praise | Kinachosifiwa | Yes | ICB and ISO 21001 — enables recognition and replication of excellence |
| named_trainer | Jina la mkufunzi (kama ipo) | Optional | ICB Code of Conduct — positive feedback to individual trainers is encouraged |
| description | Maelezo ya uzoefu mzuri | Yes | ISO 21001 §9.1.2 — learner satisfaction data |
| outcome_achieved | Matokeo yaliyofikiwa | Optional | ACQF — credentials and competency recognition; valuable for provider marketing |

### Praise Subject Categories

| Code | Subject | Swahili |
|------|---------|---------|
| TRN-AP-01 | Trainer Quality / Expertise | Ubora wa mkufunzi |
| TRN-AP-02 | Material Quality | Ubora wa nyenzo za mafunzo |
| TRN-AP-03 | Outcome / Competency Achieved | Matokeo/ujuzi uliopatikana |
| TRN-AP-04 | Practical Application Value | Thamani ya matumizi ya vitendo |
| TRN-AP-05 | Organisation / Logistics | Mpangilio na usimamizi |
| TRN-AP-06 | Accreditation / Certificate Quality | Ubora wa cheti na ithibati |

---

## AI Conversation Guidance for This Industry

- **Lead with the course, not the complaint**: Ask "Ni kozi gani uliyoshiriki?" and "Ulifanya kozi hiyo lini na kwa mtoa mafunzo yupi?" before diving into what went wrong. Course title and provider name are the two fields that determine all routing decisions.
- **Clarify certificate vs. attendance early**: When a certificate issue is raised, ask "Cheti ulichotazamiwa kilikuwa cha kushiriki tu (attendance) au cha utaalamu (competency/accreditation)?" — this is a critical distinction under VETA/NACTE rules and ICB policy.
- **For refund disputes, confirm the refund policy was communicated**: Ask "Je, wakati wa usajili, walieleza sera ya kurejesha pesa kama kozi inaghairiwa?" — this determines whether the provider is in breach of their own stated policy.
- **For accreditation disputes, ask the complainant what accreditation was claimed in the marketing**: Do not assume — accreditation claims vary widely and the specific body claimed (VETA, NACTE, NBAA, CPD) determines the escalation path entirely.
- **Never ask for payment receipts as the first question**: Establish the nature of the problem first, then gather financial evidence. Leading with money questions can feel transactional and cause complainants to disengage before sharing the full story.

## Swahili Key Phrases for Field Collection

| Field Being Collected | Swahili Phrase to Use |
|----------------------|----------------------|
| training_provider_name | "Ni kampuni au taasisi gani iliyotoa mafunzo hayo?" |
| course_programme_title | "Mafunzo hayo yaliitwa jina gani hasa?" |
| training_dates | "Mafunzo yalifanyika lini — tarehe za kuanza na kumalizia?" |
| issue_type | "Tatizo lako linahusiana na nini hasa — maudhui, mkufunzi, cheti, ada, au jambo lingine?" |
| amount_paid_tzs | "Je, ulilipa kiasi gani kwa mafunzo hayo?" |
| desired_outcome | "Unataka nini kifanyike — kurejesha pesa, cheti, au suluhu nyingine?" |
| previous_complaint_to_provider | "Je, umeshalalamika kwa mtoa mafunzo moja kwa moja? Walisema nini?" |
| accreditation_body_claimed | "Katika tangazo au brochure, walisema mafunzo yana ithibati ya shirika gani?" |
| cpd_points_claimed | "Walitangaza alama ngapi za CPD kwa kozi hii?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | TRN-GR-07 (Unsafe / OSHA) AND injury_occurred = Yes | Immediate escalation; advise complainant to file OSHA Tanzania report; flag for urgent human review |
| issue_type | TRN-GR-10 (Financial Fraud) | Refer to Police; advise complainant to preserve all payment evidence; mark urgent |
| accreditation_claimed | VETA AND not verifiable | Refer complaint to VETA for investigation; provide VETA contact |
| accreditation_claimed | NACTE AND not verifiable | Refer complaint to NACTE; provide NACTE verification process |
| accreditation_claimed | NBAA AND not verifiable | Refer to NBAA Professional Standards; provide NBAA contact |
| refund_policy_provided | No | Flag as potential consumer rights breach; advise complainant of Consumer Protection framework |
| certificate_type_expected | Competency AND certificate_issued = Attendance only | Escalate to provider; note material misrepresentation of course outcome |
| previous_complaint_to_provider | Yes AND no resolution | Advise escalation to VETA / NACTE / relevant professional body |
| delivery_language | English AND complainant expected Swahili | Flag as material misrepresentation if language was not disclosed at enrollment |
| issue_type | TRN-GR-06 (Discrimination) | Apply anti-discrimination escalation protocol; refer to human rights body if unresolved |

---

## Key Entities & Roles

**Regulatory & Accreditation Bodies:** VETA, NACTE, OSHA Tanzania, NBAA, NIT, COSTECH, CPD Standards Office, Ministry of Education Science and Technology
**Job Titles:** Facilitator, Trainer, Instructor, Training Coordinator, Program Manager, Course Developer, Curriculum Designer, Learning and Development Manager, Assessor, Examiner, E-learning Developer
**Certifications:** Certificate of Competency, CPD Certificate, VETA Level I/II/III, NACTE Accreditation, OSHA Safety Certificate, ICT Proficiency Certificate, Professional Diploma, Attendance Certificate
**Formats:** In-person Workshop, Blended Learning, E-learning, In-house Corporate Training, Public Course, Bootcamp, Apprenticeship, Webinar, Virtual Classroom

---

## Kiswahili / Swahili Equivalents

### Malalamiko (Complaints)
- "Mkufunzi alisoma slaidi tu — hakufundisha kitu cha kina"
- "Nilikamilisha kozi lakini sijapata cheti changu mpaka sasa baada ya miezi mitatu"
- "Cheti kilichotolewa kina makosa ya tahajia ya jina langu"
- "Tulilipa ada lakini kozi ilighairiwa bila kurejesha pesa zetu"
- "Walitangaza ithibati ya NACTE lakini cheti hakina nambari ya NACTE"
- "Mkufunzi hakuweza kujibu maswali ya msingi — ilikuwa aibu"
- "Programu haikufuata mtaala ulioorodheshwa kwenye brochure"

### Mapendekezo (Suggestions)
- "Ingekuwa bora kutoa nyenzo za mafunzo kwa Kiswahili kwa watanzania"
- "Mnapaswa kufanya tathmini ya kati ya kozi ili kujua maendeleo ya washiriki"
- "Ni muhimu kupata ithibati ya NACTE ili vyeti vinavyotolewa vitambuliwe na waajiri"
- "Ingekuwa vizuri kutoa mafunzo ya jioni kwa wafanyakazi wanaofanya kazi mchana"

### Maswali (Inquiries)
- "Je, kozi hii ina idhini ya VETA au NACTE?"
- "Cheti nitakachopata kitatambuliwa na waajiri Tanzania?"
- "Gharama za kozi hii ni ngapi kwa mshiriki mmoja?"
- "Je, mna programu ya mafunzo kwa lugha ya Kiswahili?"
- "Ni lini mafunzo yanaanza na yanachukua muda gani kukamilika?"

### Pongezi (Compliments)
- "Mkufunzi alifundisha kwa njia ya kuvutia sana — nilijifunza mengi"
- "Mafunzo haya yameniwezesha kupata kazi nzuri katika kampuni kubwa"
- "Cheti nilichopata kinaonekana kitaalamu na kilitambuliwa mara moja na mwajiri wangu"
- "Nyenzo za kujifunza zilikuwa bora sana na zinafaa kwa mazingira ya Tanzania"

---

## Industry-Specific Escalation Triggers

1. OSHA safety training delivered inaccurately AND participant subsequently suffered a workplace injury attributable to incorrect procedure taught
2. Certificate claiming NACTE or VETA accreditation was issued without actual accreditation — fraudulent documentation
3. Participant disclosed workplace abuse or harassment during training and facilitator failed to act
4. Participants denied access to training based on discriminatory grounds (gender, disability, religion)
5. Online exam platform data breach exposing participant personal and payment information
6. Training provider collected fees from multiple participants and disappeared without delivering training
7. Facilitator made false representations about their qualifications to clients
8. Minor enrolled in adult professional training without appropriate supervision or parental consent
9. Training materials contain content violating Tanzania anti-discrimination law or promoting hate speech
10. Medical emergency during training with no first aid or emergency protocol in place

---

## Disambiguation Notes

- **Training vs. Education**: Training targets specific workplace skills with competency outcomes; education involves broader academic learning in formal institutions. "School," "teacher," "student," "academic year" → Education. "Facilitator," "course," "certificate," "workshop," "CPD" → Training.
- **Training vs. Personal Development / Coaching**: Training delivers defined skills with structured assessment; coaching focuses on personal mindset and goals. "Life goals," "mindset," "inner work," "coach" → Personal Development.
- **Corporate Training vs. Vocational Training**: Corporate training targets employees; vocational training (VETA-aligned) targets individuals seeking trade competencies. Distinction matters for regulatory context.
- **Training vs. Consultancy**: Consultancy delivers advice and deliverables; training builds capability. "Report," "strategy," "deliverable" → Consultancy. "What I learned," "the facilitator taught," "our team now knows how to" → Training.
- **Safety Training vs. Healthcare**: OSHA safety training feedback overlaps with healthcare only if clinical or medical safety dominates — in that case classify Healthcare as primary with Safety Training as context.
