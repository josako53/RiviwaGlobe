---
tags: [industry-kb, field-standards, feedback-fields, education, university]
---
# Education / University — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: chuo kikuu, university, chuo, college, institute, shule ya sekondari, secondary school, shule ya msingi, primary school, UDSM, University of Dar es Salaam, MUHAS, Muhimbili, Ardhi University, UOUT, Open University, DUCE, MUCE, SUA, Sokoine, TCU, Tanzania Commission for Universities, NECTA, National Examinations Council, MSOSATO, NECTA exams, certificate, degree, diploma, shahada, degree program, course, mkondo, lecturer, mhadhiri, professor, profesa, student, mwanafunzi, tuition, ada ya masomo, scholarship, bursary, msaada wa masomo, HESLB, Higher Education Students Loans Board, accommodation, malazi, hostel, student loan, mkopo wa elimu, graduation, kuhitimu, transcript, transcript ya masomo, exam, mtihani, grading, alama, academic integrity, uaminifu wa kielimu, plagiarism, sexual harassment, unyanyasaji wa kijinsia, bullying, unyanyasaji, student union, chama cha wanafunzi, discipline, nidhamu, TCU, TCU accreditation, foreign degree recognition, kutambuliwa kwa shahada za nje

## Why Industry-Specific Fields Matter

Education complaints span academic misconduct (grade disputes requiring course code, lecturer name, assessment reference), HESLB loan issues (requiring loan reference and registration number), sexual harassment (requiring safeguarding escalation), accreditation concerns (requiring TCU program registration), and tuition disputes (requiring fee schedule and payment reference). Without education-specific fields, the AI cannot generate a TCU-compliant complaint or route to the correct academic committee vs. disciplinary panel vs. HESLB.

## Source Standards

- Tanzania Education Act, Cap. 353 — education system regulation
- Universities Act, Cap. 346 — TCU mandate and university governance
- Tanzania Commission for Universities (TCU) Regulations 2021
- HESLB Act, Cap. 178 — student loan management
- NECTA Act — national examinations administration
- ISO 21001:2018 — Educational organizations management systems
- ISO 10002:2018 — complaints handling
- UNESCO Recommendation against Sexual Harassment in Education (2019)
- ILO Convention 190 on Violence and Harassment (2019) — workplace and education settings
- Tanzania Gender Policy 2000 and SGBV guidelines — sexual harassment in academic settings

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL education complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Academic record lookup; complaint registration |
| complainant_phone | Nambari ya simu | Yes | For status updates |
| complainant_role | Nafasi ya mlalamikaji | Yes | Student / Parent / Guardian / Staff / External — shapes rights and routing |
| institution_name | Jina la chuo / shule | Yes | Routes complaint to correct institution and regulatory body |
| institution_type | Aina ya taasisi | Yes | University / College / Secondary School / Primary School |
| registration_number | Nambari ya usajili wa mwanafunzi | Yes | Primary student identifier; enables academic record access |
| faculty_or_department | Kitivo / Idara | Conditional | For academic complaints; routes to dean or HOD |
| program_or_course_name | Programu / Mkondo | Recommended | For academic routing |
| academic_year_or_semester | Mwaka wa masomo / Semester | Recommended | Temporal context for academic complaints |
| issue_type | Aina ya tatizo | Yes | Academic / Administrative / Safety / Financial etc. |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; detailed narrative |
| date_of_incident | Tarehe ya tukio | Yes | For limitation period and investigation |
| lecturer_or_staff_involved | Jina la mhadhiri / mfanyakazi aliyehusika | Conditional | For academic and misconduct complaints |
| desired_outcome | Matokeo unayotaka | Yes | Grade review / Disciplinary action / Refund / Apology |
| previous_complaint_to_institution | Je, umeshalalamika chuo moja kwa moja? | Recommended | TCU requires prior institutional complaint |

### CRITICAL: Sexual Harassment / Gender-Based Violence Fields

**If any indication of sexual harassment, assault, or GBV by staff or student:**
- `incident_type_safeguarding` — Aina ya tukio: Sexual harassment / Assault / Threats / Discrimination
- `perpetrator_role` — Cheo cha mtendaji: Lecturer / Senior staff / Fellow student
- `immediate_safety_concern` — Je, mwathirika yuko salama sasa hivi?: Safety first
- `medical_or_counseling_support_sought` — Je, msaada wa kimatibabu au ushauri imani umetafutwa?
- **Escalate immediately to institution's gender desk AND TCU gender unit AND police if criminal**

### Conditional Fields (collect based on issue type)

**If issue_type = Grade Dispute / Examination:**
Also collect:
- `course_code` — Msimbo wa kozi: For academic record lookup
- `assessment_type` — Aina ya tathmini: CAT / Final Exam / Assignment / Project / Dissertation
- `grade_received` — Alama iliyopewa
- `grade_expected_basis` — Msingi wa matarajio ya alama: Why does complainant believe grade is wrong?
- `appeal_already_submitted` — Je, rufaa ya kielimu tayari imewasilishwa?: Universities have internal appeal processes
- `remarking_requested` — Je, kupigiwa alama upya kumeombwa? Yes / No

**If issue_type = HESLB Loan Dispute:**
Also collect:
- `heslb_loan_reference` — Nambari ya mkopo wa HESLB
- `loan_amount_expected_tzs` — Kiasi cha mkopo kilichotarajiwa (TZS)
- `loan_amount_received_tzs` — Kiasi kilichopokelewa (TZS)
- `disbursement_period` — Kipindi cha malipo
- `loan_application_reference` — Nambari ya maombi ya mkopo

**If issue_type = Tuition / Fees Dispute:**
Also collect:
- `fee_amount_paid_tzs` — Ada iliyolipwa (TZS)
- `fee_structure_reference` — Muundo wa ada (programu / mwaka): For verification against official fee schedule
- `payment_reference` — Nambari ya marejeleo ya malipo
- `receipt_available` — Je, risiti inapatikana?

**If issue_type = Accommodation / Hostel:**
Also collect:
- `hostel_name` — Jina la nyumba ya wanafunzi
- `room_number` — Nambari ya chumba
- `maintenance_issue_type` — Aina ya tatizo la matengenezo: No water / No electricity / Pest infestation / Broken facilities / Safety
- `safety_concern` — Je, kuna wasiwasi wa usalama? (wizi, unyanyasaji): Immediate escalation trigger

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| ED-01 | grade_dispute | Grade awarded deemed incorrect; academic appeal |
| ED-02 | examination_irregularity | Cheating allegations, leaked papers, wrong results |
| ED-03 | heslb_loan_issue | Loan not disbursed, wrong amount, repayment dispute |
| ED-04 | tuition_fee_dispute | Incorrect fees charged or unauthorized charges |
| ED-05 | sexual_harassment | Sexual harassment or assault by staff or student (SAFEGUARDING) |
| ED-06 | bullying_discrimination | Bullying, tribal, gender, or disability discrimination |
| ED-07 | academic_dishonesty | Plagiarism, cheating, or academic fraud allegations |
| ED-08 | poor_teaching_quality | Lectures not delivered, poor pedagogy, missed classes |
| ED-09 | accommodation_issue | Hostel maintenance, safety, or hygiene problems |
| ED-10 | registration_problem | Enrollment, re-registration, or academic record issues |
| ED-11 | library_resources | Inadequate library, internet, or academic resources |
| ED-12 | staff_misconduct | Unprofessional or corrupt behavior by academic/admin staff |
| ED-13 | accreditation_concern | Program not properly accredited by TCU |
| ED-14 | degree_certificate_delay | Certificate not issued after completion |
| ED-15 | foreign_degree_recognition | TCU refusal to recognize foreign qualification |

### Resolution Standards

- **Institution level:** Most universities have an Academic Appeals Committee and Student Welfare Committee; grades must be appealed within 14–30 days of publication.
- **TCU escalation:** TCU receives complaints against universities; investigation within 60 days. TCU can order grade reviews, refunds, and disciplinary action.
- **HESLB disputes:** HESLB has a loan disputes desk; resolution within 30 days.
- **Sexual harassment:** Institution must investigate within 30 days; TCU gender unit can escalate; criminal acts reported to police.
- **NECTA examination disputes:** Formal remarking request within 60 days of results; NECTA committee review.
- **Required for TCU escalation:** Institution name, program, student registration number, nature of complaint, institution's response.

### Escalation Triggers

- `issue_type = sexual_harassment` — Immediate escalation to institution gender desk, TCU gender unit, and police if criminal; victim safety first
- `issue_type = accommodation_issue` AND safety concern (theft, assault) — Institution security AND police; accommodation safety review
- `issue_type = accreditation_concern` AND program not listed on TCU register — Student advisement to verify before enrollment; TCU consumer protection complaint
- `issue_type = examination_irregularity` AND leaked papers — NECTA and institution exam board; potential criminal matter
- `issue_type = academic_dishonesty` AND student is complainant not respondent — Due process protection; institution disciplinary committee hearing required
- Previous institutional complaint unresolved after 60 days — Eligible for TCU escalation

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| institution_name | Jina la chuo | Recommended | For routing |
| department_or_program | Idara / Programu | Recommended | For targeted improvement |
| suggestion_category | Kategoria | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| EDS-01 | teaching_quality | Ubora wa ufundishaji |
| EDS-02 | digital_learning | Mafunzo ya kidijitali |
| EDS-03 | library_resources | Rasilimali za maktaba na intaneti |
| EDS-04 | student_welfare | Ustawi wa wanafunzi |
| EDS-05 | gender_safety | Usalama wa kijinsia chuoni |
| EDS-06 | practical_training | Mafunzo ya vitendo |
| EDS-07 | industry_linkage | Uhusiano na sekta ya biashara |
| EDS-08 | scholarship_access | Ufikiaji wa udhamini |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina | Recommended | For tracking |
| registration_number | Nambari ya usajili | Conditional | For student-specific queries |
| institution_name | Chuo | Conditional | For institution-specific queries |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| heslb_application | Jinsi ya kuomba mkopo wa HESLB | registration_number |
| grade_check | Kuangalia alama zangu | registration_number, course_code |
| tcu_accreditation | Je, programu hii imetambuliwa na TCU? | institution_name, program_name |
| transfer_process | Jinsi ya kubadilisha chuo | current_institution |
| certificate_collection | Cheti changu kiko wapi? | registration_number, graduation_date |
| foreign_recognition | Je, shahada ya nje itatambuliwa? | institution_name, country |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| staff_or_lecturer_name | Jina la mhadhiri / mfanyakazi | Recommended | Staff recognition |
| institution_name | Chuo | Yes | Routes to management |
| specific_aspect_praised | Kipengele | Yes | Ufundishaji bora / Msaada wa wanafunzi / Rasilimali / Mazingira |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | ISO 21001:2018 CSAT; TCU quality assurance |

---

## AI Conversation Guidance for This Industry

- **For sexual harassment complaints, prioritize safety and support.** Before collecting any data, say "Usalama wako ndio wa kwanza. Je, uko salama sasa hivi? Kuna usaidizi wa mshauri wa kisaikolojia chuoni na nje ya chuo." Then provide support contacts.
- **For grade disputes, clarify the internal appeal process.** Most universities require students to appeal through the department first, then faculty, then Senate. "Je, umejaribu mchakato wa rufaa wa ndani ya chuo — department yako au kitivo?"
- **Confirm TCU accreditation for program complaints.** If a student paid tuition for a program not accredited by TCU, this is a serious consumer protection issue. "Programu hii imeorodheshwa kwenye rejista ya TCU — tunaweza kuthibitisha hilo kwa TCU."
- **For HESLB disputes, get the loan reference immediately.** HESLB has a searchable database; the reference number enables immediate case lookup. "Nambari ya mkopo wa HESLB inaonekana kwenye hati ya makubaliano ya mkopo."
- **Do not provide academic advice (e.g., whether a grade is fair).** Simply document the complaint and route. "Kama unadhani alama yako si sahihi, haki yako ni kuomba rufaa — mchakato unaofaa ni huu..."
- **For accommodation safety concerns, treat as urgent.** Student hostels where safety is compromised require immediate institutional security response.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Registration number | "Nambari yako ya usajili wa chuo ni ipi?" |
| Institution | "Chuo au taasisi inayohusika inaitwa nini?" |
| Course code | "Kozi inayohusika ina msimbo gani — na mhadhiri wake ni nani?" |
| Grade received | "Alama uliyopewa ni ipi — na alama unayohisi unastahili ni ipi?" |
| HESLB reference | "Nambari ya mkopo wako wa HESLB inaonekana kwenye hati ya makubaliano" |
| Safety (GBV) | "Usalama wako ndio wa kwanza — je, uko salama sasa hivi? Tuna msaada wa dharura" |
| Appeal status | "Je, umeshajaribu mchakato wa rufaa wa ndani ya chuo?" |
| TCU complaint | "Je, tayari umelalamika kwa chuo moja kwa moja? Kama ndiyo, jibu lao lilikuwa nini?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | sexual_harassment | Immediate: institution gender desk + TCU gender unit + police if criminal; victim support referral |
| issue_type | accreditation_concern AND TCU not listed | Urgent student advisement; TCU consumer protection complaint; potential refund if misrepresentation |
| issue_type | examination_irregularity AND leaked papers | NECTA + institution exam board + police; criminal matter |
| previous_complaint_to_institution | unresolved > 60 days | Eligible for TCU escalation; provide TCU contact (tcu.go.tz) |
| issue_type | grade_dispute AND appeal_already_submitted | Route to next level (Faculty → Senate → TCU); provide timeline |
| issue_type | heslb_loan_issue | HESLB disputes desk; loan reference required; 30-day resolution standard |
| issue_type | accommodation_issue AND safety | Institution security immediate response; police if criminal |
| issue_type | foreign_degree_recognition | TCU foreign qualifications assessment office; specific documentation required |

---

*Sources: Tanzania Education Act Cap. 353, Universities Act Cap. 346, TCU Regulations 2021, HESLB Act Cap. 178, NECTA Act, ISO 21001:2018, ISO 10002:2018, UNESCO 2019 Recommendation, ILO Convention 190*
