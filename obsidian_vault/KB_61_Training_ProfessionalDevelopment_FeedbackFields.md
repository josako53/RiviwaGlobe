---
tags: [industry-kb, field-standards, feedback-fields, training, professional-development]
---
# Training / Professional Development — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: mafunzo, training, kozi, course, workshop, seminar, warsha, semina, online course, e-learning, mafunzo ya mtandaoni, professional certification, cheti cha kitaaluma, CPD, continuing professional development, maendeleo ya kitaalamu, VETA, vocational training, mafunzo ya ufundi, certificate course, diploma, short course, bootcamp, conference, mkutano wa kitaalamu, coaching, mentoring, corporate training, mafunzo ya kampuni, skills development, maendeleo ya ujuzi, NACTVET, NITA, National Institute of Transport, NIT, polytechnic, FDC, Folk Development College, TOT, training of trainers, trainer, mwezeshaji, facilitator, mwongozaji, course fee, ada ya kozi, completion certificate, cheti cha kukamilisha, accreditation, ithibati, VETA certificate, NACTVET certificate, course material, vifaa vya mafunzo, online platform, Zoom, Teams, Udemy, Coursera

## Why Industry-Specific Fields Matter

Training complaints range from course quality (requiring course code, trainer name, content assessment), certificate/accreditation issues (requiring VETA/NACTVET registration number), to non-delivery of promised skills (requiring course outline and promised outcomes vs. delivered). Without training-specific fields, the AI cannot verify accreditation with VETA or NACTVET, assess whether a training provider is operating legally, or route a quality complaint to the correct regulatory body.

## Source Standards

- VETA Act, Cap. 82 — Vocational Education and Training Authority
- NACTVET (National Council for Technical and Vocational Education and Training) regulations
- National Institute of Transport (NIT) Act — transport professional training
- Tanzania Employment and Labour Relations Act, Cap. 366 — employer training obligations
- ISO 10002:2018 — complaints handling
- ISO 29993:2017 — Learning services outside formal education
- ISO 21001:2018 — Educational organizations management systems
- Tanzania Consumer Protection (Fair Competition Act, Cap. 285) — misleading training advertisements
- International Labour Organization (ILO) — TVET quality frameworks

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL training complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | For complaint registration |
| complainant_phone | Nambari ya simu | Yes | Status updates |
| training_provider_name | Jina la mtoa mafunzo | Yes | Routes complaint; enables VETA/NACTVET accreditation check |
| course_name | Jina la kozi / mafunzo | Yes | Core identifier |
| course_code | Msimbo wa kozi (kama ipo) | Recommended | For accreditation verification |
| trainer_facilitator_name | Jina la mkufunzi / mwezeshaji | Conditional | For trainer-specific complaints |
| training_mode | Aina ya mafunzo | Yes | In-person / Online / Blended / Distance — shapes evidence type |
| training_dates | Tarehe za mafunzo | Yes | For timeline and scheduling complaints |
| training_location | Mahali pa mafunzo | Conditional | For in-person complaints |
| course_fee_paid_tzs | Ada ya kozi iliyolipwa (TZS) | Yes | For financial disputes and refund calculation |
| receipt_available | Je, risiti inapatikana? | Yes | Proof of payment |
| accreditation_claimed | Je, mtoa mafunzo alidai accreditation? (VETA, NACTVET, n.k.) | Yes | Enables verification; false accreditation claims are consumer fraud |
| certification_promised | Je, cheti kiliahidiwa? Aina gani? | Yes | Basis of consumer expectation |
| issue_type | Aina ya tatizo | Yes | Complaint taxonomy |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; detailed narrative |
| desired_outcome | Matokeo unayotaka | Yes | Refund / Retake course / Certificate delivery / Investigation |

### Conditional Fields (collect based on issue type)

**If issue_type = Certificate Not Issued / Fraudulent Certificate:**
Also collect:
- `course_completion_date` — Tarehe ya kukamilisha kozi
- `certificate_promised_by_date` — Tarehe ambayo cheti kiliahidiwa
- `certificate_verification_method` — Njia ya kuthibitisha cheti: VETA database / NACTVET / Employer verification
- `employer_rejected_certificate` — Je, mwajiri alikataa kutambua cheti? Yes / No: Indicates potential fraud

**If issue_type = Poor Quality / Misleading Content:**
Also collect:
- `course_outline_provided` — Je, muhtasari wa kozi ulitolewa kabla ya kuanza?
- `promised_outcomes` — Matokeo yaliyoahidiwa: "Utapata ujuzi wa X, utaweza Y"
- `actual_content_delivered` — Maudhui yaliyotolewa kweli kweli: For comparison
- `hours_delivered` — Masaa yaliyotolewa: Compared against advertised hours
- `trainer_qualifications_known` — Je, sifa za mkufunzi zinajulikana?

**If issue_type = Online Course Failure / Technical Issue:**
Also collect:
- `platform_name` — Jina la jukwaa: Zoom / Teams / LMS system / Udemy etc.
- `technical_issue_type` — Aina ya tatizo la kiufundi: No access / Audio/video failure / Content locked
- `access_period_promised` — Muda wa ufikiaji ulioahidiwa: Most online courses offer 6–12 month access
- `recordings_available` — Je, rekodi za masomo zinapatikana?: Key feature for paid online courses

**If issue_type = Refund Dispute:**
Also collect:
- `refund_request_date` — Tarehe ya kuomba kurudishiwa pesa
- `reason_for_withdrawal` — Sababu ya kujiondoa: Course cancelled / Poor quality / Personal emergency
- `provider_refund_policy_known` — Je, sera ya kurudisha pesa inajulikana?: For assessment of entitlement
- `days_into_course_at_withdrawal` — Siku ndani ya kozi wakati wa kujiondoa

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| TR-01 | false_accreditation | Provider claiming VETA/NACTVET accreditation without valid registration |
| TR-02 | fraudulent_certificate | Certificate issued is fake, unverifiable, or not recognized |
| TR-03 | poor_training_quality | Content below standard; trainer unqualified; poor delivery |
| TR-04 | course_not_delivered | Paid but course was cancelled, shortened, or never started |
| TR-05 | refund_refused | Provider refuses valid refund for cancelled/poor course |
| TR-06 | certificate_delay | Certificate not issued within promised timeframe after completion |
| TR-07 | misleading_advertising | Course benefits, accreditation, or outcomes misrepresented |
| TR-08 | online_access_failure | Paid online course inaccessible due to platform issues |
| TR-09 | trainer_misconduct | Harassment, discrimination, or unprofessional trainer behavior |
| TR-10 | incorrect_fee | Fee charged differs from advertised amount |
| TR-11 | outcomes_not_met | Skills or knowledge promised not taught or practiced |
| TR-12 | staff_misconduct | Administrative or scheduling issues by provider staff |

### Resolution Standards

- **Provider level:** Training providers should resolve complaints within 14 days; major issues within 30 days.
- **VETA:** Complaints against VETA-registered institutions within 30 days; VETA can revoke accreditation.
- **NACTVET:** Similar to VETA for technical and vocational programs.
- **FCC (consumer protection):** Misleading advertising and refund refusals; investigation within 60 days.
- **Refund entitlement:** If course is cancelled by provider, full refund; if student withdraws before start, typically full refund; after start, pro-rated refund minus reasonable costs.
- **Required for regulatory escalation:** Provider name, course name, accreditation number (if claimed), fee paid, description of complaint, evidence.

### Escalation Triggers

- `accreditation_claimed = Yes` AND provider not listed in VETA/NACTVET register — Consumer fraud; VETA enforcement + FCC complaint
- `issue_type = fraudulent_certificate` AND employer rejected — Serious career impact; VETA verification and legal referral
- `issue_type = course_not_delivered` AND full fee paid — FCC consumer protection; potential fraud
- `issue_type = trainer_misconduct` AND sexual harassment — Institution complaint + VETA regulatory complaint + police if criminal
- `refund_refused` AND course cancelled by provider — FCC complaint; consumer is legally entitled to full refund for provider-cancelled courses

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| training_provider | Mtoa mafunzo | Recommended | For routing |
| course_name | Kozi | Recommended | For course-specific feedback |
| suggestion_category | Kategoria | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| TRS-01 | content_relevance | Maudhui yanayohusiana na soko la kazi |
| TRS-02 | trainer_quality | Ubora wa wakufunzi |
| TRS-03 | practical_application | Mafunzo ya vitendo |
| TRS-04 | online_delivery | Ubora wa mafunzo ya mtandaoni |
| TRS-05 | certification_value | Thamani ya vyeti kwa waajiri |
| TRS-06 | fee_affordability | Ada nafuu au mikopo ya mafunzo |
| TRS-07 | flexibility | Muda wa kujifunza unaobadilika |
| TRS-08 | job_placement | Msaada wa kupata kazi baada ya mafunzo |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina | Recommended | For tracking |
| course_name | Kozi | Conditional | For course-specific queries |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| accreditation_check | Je, cheti hiki kinatambuliwa? | provider_name, course_name |
| veta_registration | Je, mtoa mafunzo huu amesajiliwa VETA? | provider_name |
| refund_policy | Sera ya kurudisha pesa ni ipi? | provider_name, course_name |
| certificate_verification | Je, cheti hiki ni halisi? | certificate_number, provider_name |
| course_prerequisites | Ninachohitaji kabla ya kujiunga? | course_name |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| trainer_name | Jina la mkufunzi | Recommended | Trainer recognition |
| provider_name | Mtoa mafunzo | Yes | Routes to management |
| specific_aspect_praised | Kipengele | Yes | Ujuzi wa mkufunzi / Vifaa bora / Matumizi ya vitendo / Cheti kinachotambuliwa |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | ISO 29993 learning service quality |

---

## AI Conversation Guidance for This Industry

- **Verify accreditation immediately for certificate complaints.** VETA and NACTVET maintain public registers. "Mtoa mafunzo huu alisema ana accreditation ya aina gani? VETA / NACTVET / TCU? Tunaweza kuthibitisha kwenye rejista yao."
- **For fraudulent certificate complaints, ask whether an employer has already rejected the certificate.** This is the key evidence that the certificate lacks recognition. "Je, umetumia cheti hiki kwa mwajiri? Walisema nini?"
- **For refund disputes, clarify who cancelled the course.** If the provider cancelled, the student has an unambiguous right to a full refund. If the student withdrew, the refund depends on the timing and the provider's stated policy.
- **For online course complaints, check if recordings were available.** Missing recordings or locked content after payment is a common e-learning complaint with clear evidence. "Je, uliweza kufikia masomo na rekodi zake? Kama ulipia lakini huwezi kufikia — hiyo ni tatizo la wazi."
- **Never validate a certificate as real or fake.** Direct to official verification: "Ukweli wa cheti unaweza kuthibitishwa na VETA au mwajiri wako moja kwa moja."

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Provider name | "Kampuni au taasisi ya mafunzo inaitwa nini?" |
| Course name | "Kozi au mafunzo yanaitwa nini?" |
| Accreditation | "Mtoa mafunzo alidai ana accreditation ya aina gani — VETA, NACTVET, au nyingine?" |
| Fee paid | "Ada ya kozi iliyolipwa ilikuwa kiasi gani? Una risiti?" |
| Certificate promised | "Uliahidiwa kupata cheti cha aina gani baada ya kukamilisha?" |
| Content delivered | "Maudhui ya mafunzo yaliyotolewa kweli kweli yalifikia matarajio yaliyoahidiwa?" |
| Employer reaction | "Je, umetumia cheti hiki kwa mwajiri? Walitoa jibu gani?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| accreditation_claimed | Yes AND not in VETA/NACTVET register | Consumer fraud; VETA enforcement + FCC consumer protection complaint |
| issue_type | fraudulent_certificate AND employer rejected | Serious; VETA verification; legal referral; FCC complaint |
| issue_type | course_not_delivered AND full fee paid | FCC consumer protection; potential fraud investigation |
| issue_type | trainer_misconduct AND sexual harassment | Provider complaint + VETA regulatory complaint + police |
| refund_refused | Yes AND course cancelled by provider | FCC complaint; consumer entitled to full refund |
| issue_type | misleading_advertising | FCC consumer protection + Tanzania Advertising Standards |

---

*Sources: VETA Act Cap. 82, NACTVET Regulations, Tanzania Employment and Labour Relations Act Cap. 366, Fair Competition Act Cap. 285, ISO 29993:2017, ISO 21001:2018, ISO 10002:2018*
