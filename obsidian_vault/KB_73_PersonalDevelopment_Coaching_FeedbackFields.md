---
tags: [industry-kb, field-standards, feedback-fields, personal-development, coaching]
---
# Personal Development / Coaching — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: maendeleo ya kibinafsi, personal development, mafunzo ya kujiamini, self-development, mshauri wa maisha, life coach, mkufunzi wa maisha, coaching, coaching session, life skills, ujuzi wa maisha, leadership coaching, mafunzo ya uongozi, career coaching, ushauri wa kazi, motivational speaker, mzungumzaji wa msisitizo, Tony Robbins, motivational seminar, semina ya msisitizo, mindset, fikira, NLP, neuro-linguistic programming, wellness coaching, afya ya akili, mental health coaching, business coaching, mafunzo ya biashara, executive coaching, personal trainer, mwezeshaji wa mazoezi, fitness coaching, confidence, kujiamini, goal setting, kuweka malengo, accountability partner, mshirika wa uwajibikaji, therapy, tiba ya kisaikolojia, counselor, mshauri wa kisaikolojia, healing, uponyaji, vision board, board ya maono, financial coaching, mafunzo ya fedha, relationship coaching, ushauri wa mahusiano, retreat, likizo ya maendeleo, online coaching, mafunzo ya mtandaoni

## Why Industry-Specific Fields Matter

Personal development and coaching complaints are distinctive: they often involve vulnerable individuals in emotionally sensitive engagements, proprietary claims about program outcomes, high fees for services with intangible deliverables, and potential psychological harm from inappropriate coaching methods. Unlike regulated professions, coaching lacks a mandatory licensing framework in Tanzania — making consumer protection through FCC and transparent field collection critical. Without coaching-specific fields, the AI cannot assess whether outcomes promised were measurable or whether the coach used methods that caused psychological harm.

## Source Standards

- Tanzania Fair Competition Act, Cap. 285 — consumer protection for coaching services
- Tanzania Law of Contract Act, Cap. 433 — coaching agreements
- International Coaching Federation (ICF) Code of Ethics (reference standard)
- EMCC (European Mentoring and Coaching Council) Global Code of Ethics (reference)
- Tanzania Medical Practitioners and Dentists Act — boundary between coaching and therapy
- Prevention of Violence Against Women and Children Act 2022 — for exploitation in coaching
- Mental Health Act (Tanzania) — if coaching involves mental health claims
- ISO 10002:2018 — complaints handling
- ISO 20700:2017 — Management consultancy service guidelines (applicable to business coaching)
- PCCB Act Cap. 329 — for financial exploitation with fraudulent intent

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL coaching/personal development complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Complaint registration |
| complainant_phone | Nambari ya simu | Yes | Status updates |
| coach_or_trainer_name | Jina la kocha / mkufunzi | Yes | Individual accountability; ICF/professional body lookup |
| coaching_company_name | Jina la kampuni / programu | Recommended | Organizational accountability |
| coaching_type | Aina ya mafunzo | Yes | Life coaching / Business coaching / Career / Financial / Relationship / Spiritual / Fitness |
| engagement_format | Aina ya engagement | Yes | One-on-one / Group / Online / In-person / Retreat / Seminar |
| engagement_duration | Muda wa engagement | Recommended | Number of sessions / weeks / months |
| total_fees_paid_tzs | Jumla ya ada iliyolipwa (TZS) | Yes | For financial disputes and refund quantification |
| receipt_or_agreement_available | Je, risiti au makubaliano inapatikana? | Yes | Proof of engagement |
| outcomes_promised | Matokeo yaliyoahidiwa | Yes | What specific outcomes were guaranteed? |
| outcomes_achieved | Matokeo yaliyopatikana | Yes | What was actually achieved? |
| issue_type | Aina ya tatizo | Yes | Complaint taxonomy |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; detailed narrative |
| psychological_harm | Je, madhara ya kisaikolojia yametokea? | Yes | Determines whether mental health referral is needed |
| desired_outcome | Matokeo unayotaka | Yes | Refund / Apology / Cease practice / Investigation |

### Conditional Fields (collect based on issue type)

**If issue_type = Fraudulent Outcome Claims / Misleading Advertising:**
Also collect:
- `specific_promise_made` — Ahadi mahususi iliyotolewa: "Utapata kazi ndani ya siku 30" / "Utaponya ugonjwa wako" etc.
- `medium_of_promise` — Njia ya ahadi: Website / Social media / Flyer / Verbal — for evidence collection
- `evidence_of_promise` — Ushahidi wa ahadi: Screenshot / Recording / Document
- `measurability_of_promise` — Je, ahadi ilikuwa inayoweza kupimika? Yes / No: Vague promises are harder to dispute; specific false promises are FCC complaints

**If issue_type = Financial Exploitation / High-Pressure Sales:**
Also collect:
- `program_price_original_quoted_tzs` — Bei ya awali iliyonukuliwa
- `program_price_paid_tzs` — Bei iliyolipwa kweli kweli
- `upsell_pressure_experienced` — Je, shinikizo la kununua zaidi lilitumika? Yes / No
- `testimonials_relied_upon` — Je, maoni ya wengine yalitumika kushawishi? Yes / No: Fabricated testimonials are FCC violations
- `emotional_manipulation_experienced` — Je, hisia zilitumika kushawishi? (fear of missing out, urgency, shame) Yes / No

**If issue_type = Psychological Harm / Inappropriate Methods:**
Also collect:
- `methods_used` — Njia zilizotumika na kocha: Hypnosis / Regression / Religious elements / Extreme challenges / Isolation
- `harm_type` — Aina ya madhara: Depression worsened / Anxiety triggered / Financial loss / Relationship harm / Identity confusion
- `mental_health_professional_consulted` — Je, mwanasaikolojia au daktari ameshauriwa? Yes / No
- `other_clients_affected` — Je, washirika wengine wa programu wameathirika pia?: Pattern indicator

**If issue_type = Boundary Violations (Romantic / Sexual):**
Also collect:
- `nature_of_boundary_violation` — Aina ya ukiukwaji: Romantic contact / Sexual harassment / Excessive personal contact outside sessions
- `consent_given` — Je, mawasiliano hayo yalikubaliwa? Yes / No
- `impact_on_coaching_relationship` — Athari kwa uhusiano wa coaching
- **If sexual misconduct: Immediate safety assessment + police referral**

**If issue_type = Refund Dispute:**
Also collect:
- `refund_policy_communicated` — Je, sera ya kurudisha pesa ilielezwa kabla ya kuanza?
- `reason_for_withdrawal` — Sababu ya kujiondoa: Course quality / Emergency / Misrepresentation / Health
- `sessions_completed` — Vikao vilivyokamilika: For pro-rated refund calculation
- `sessions_remaining` — Vikao vilivyobaki

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| PD-01 | fraudulent_outcome_claims | Coach promised specific outcomes that were not delivered |
| PD-02 | misleading_advertising | Program benefits, coach qualifications, or testimonials misrepresented |
| PD-03 | financial_exploitation | High-pressure tactics; excessive fees for minimal value |
| PD-04 | refund_refused | Coach refuses refund for incomplete or poor service |
| PD-05 | psychological_harm | Coaching methods caused anxiety, depression, or identity harm |
| PD-06 | boundary_violation | Inappropriate romantic or sexual conduct by coach |
| PD-07 | confidentiality_breach | Personal information shared without consent |
| PD-08 | qualifications_misrepresented | Coach falsely claimed credentials or certifications |
| PD-09 | abandonment | Coach abandoned client mid-program without notice |
| PD-10 | harmful_methods | Extreme, dangerous, or manipulative coaching techniques |
| PD-11 | cult_like_behavior | Isolation, undue influence, or cult-like group dynamics |
| PD-12 | poor_program_quality | Sessions poorly structured; minimal value for fees paid |
| PD-13 | online_platform_failure | Paid online program inaccessible or incomplete |
| PD-14 | impersonating_therapist | Coach practicing therapy or making clinical claims without license |

### Resolution Standards

- **Coach/Program level:** Most reputable coaches resolve complaints within 14 days; refund policies should be in writing.
- **FCC (consumer protection):** Misleading advertising, fraudulent outcome claims; investigation within 60 days.
- **Police (financial fraud):** If coach collected fees with no intention of delivering service; criminal fraud.
- **Medical Practitioners Board:** If coach is practicing therapy without medical/psychological license; complaint to medical board.
- **ICF (International Coaching Federation):** Ethical complaints against ICF-certified coaches; their disciplinary process removes certification.
- **Required for escalation:** Coach name, fee paid, promises made (documented), harm experienced, evidence.

### Escalation Triggers

- `issue_type = boundary_violation` AND sexual misconduct — Police referral (Prevention of Violence Act 2022); support services
- `issue_type = psychological_harm` AND `mental_health_professional_consulted = No` — Refer to mental health services immediately
- `issue_type = cult_like_behavior` AND isolation pattern — Multiple stakeholder intervention; family notification; potential police involvement
- `issue_type = impersonating_therapist` AND clinical claims — Medical Practitioners Board complaint; criminal if harm resulted
- `issue_type = fraudulent_outcome_claims` AND `fee_paid > 1,000,000 TZS` AND no delivery — FCC + police criminal fraud
- `issue_type = qualifications_misrepresented` AND professional certification falsely claimed — ICF/professional body complaint; FCC consumer fraud

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| program_name | Jina la programu | Recommended | For routing |
| coaching_type | Aina ya coaching | Yes | For analysis |
| suggestion_category | Kategoria | Yes | For routing |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| PDS-01 | session_structure | Muundo bora wa vikao |
| PDS-02 | outcome_clarity | Uwazi wa matokeo yanayotarajiwa |
| PDS-03 | coach_qualifications | Sifa halisi za kocha |
| PDS-04 | pricing_transparency | Uwazi wa bei na sera ya kurudisha pesa |
| PDS-05 | emotional_safety | Usalama wa kihisia katika vikao |
| PDS-06 | online_quality | Ubora wa vikao vya mtandaoni |
| PDS-07 | followup_support | Msaada wa kufuatilia baada ya programu |
| PDS-08 | group_dynamics | Mazingira bora ya mafunzo ya kikundi |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina | Recommended | For tracking |
| coaching_type | Aina ya coaching | Yes | Routes to correct answer |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| coach_qualification | Je, kocha huyu ana sifa halisi? | coach_name |
| icf_certification | Je, kocha huyu ana cheti cha ICF? | coach_name |
| refund_rights | Haki zangu za kurudishiwa pesa | coach_name, fee_paid |
| coaching_vs_therapy | Tofauti kati ya coaching na tiba ya kisaikolojia? | — |
| complaint_process | Jinsi ya kulalamika dhidi ya kocha? | coach_name |
| mental_health_referral | Ninahitaji msaada wa kisaikolojia — niende wapi? | location |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| coach_name | Jina la kocha | Yes | Individual recognition |
| program_name | Jina la programu | Recommended | Program recognition |
| specific_aspect_praised | Kipengele | Yes | Mabadiliko halisi ya maisha / Msaada wa kihisia / Ujuzi wa kocha / Thamani kwa bei |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Coach quality benchmarking |
| life_impact | Athari ya programu katika maisha yako | Recommended | Outcome measurement |

---

## AI Conversation Guidance for This Industry

- **Psychological safety comes first.** Many coaching clients share very personal information and may be vulnerable. "Ninakushukuru kwa uaminifu wako. Taarifa unazoshiriki nazo zitashikiliwa kwa siri kabisa."
- **For psychological harm complaints, always assess mental health status.** "Je, hali yako ya kiafya ya akili imeathirika? Kama unahisi unajisikia vibaya sana, tunaweza kukusaidia kupata msaada wa mwanasaikolojia au daktari."
- **For boundary violations, treat as a safety matter.** "Ukiukwaji wa mipaka na kocha ni suala zito. Usalama wako ndio muhimu zaidi — unahitaji msaada wowote wa haraka?"
- **Distinguish between coaching and therapy.** A coach who claims to treat depression, trauma, or mental illness without a medical license is practicing illegally. "Kocha anayedai anaweza 'kutibu' ugonjwa wa kiakili bila leseni ya matibabu ni suala la kisheria — tunaweza kupeleka tatizo hili kwa Bodi ya Madaktari."
- **For outcome promise complaints, ask for documentation.** Screenshots of social media ads, webinar recordings, or written agreements are the strongest evidence. "Je, ahadi hizo zilielezwa wapi — kwenye tovuti, mitandao ya kijamii, au barua? Una ushahidi wo wote?"
- **Never dismiss or minimize coaching complaints.** Financial loss from coaching programs can be significant (millions of TZS), and psychological harm can be real. Treat with the same seriousness as other service complaints.
- **For cult-like behavior, involve family and mental health services.** This is a complex safeguarding matter. "Hali kama hii inaweza kuhitaji msaada wa familia na wataalam wa afya ya akili — tunaomba kushirikiana nao."

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Coach name | "Kocha au mkufunzi anaitwa nini? Na kampuni au programu inaitwa nini?" |
| Coaching type | "Mafunzo haya yalielezwa kama ya aina gani — maisha, biashara, kazi, mahusiano, afya?" |
| Outcomes promised | "Matokeo mahususi yaliyoahidiwa yalikuwa gani? Kwa mfano, 'utaongeza mapato yako kwa X%' au 'utapata kazi ndani ya Y siku'" |
| Outcomes achieved | "Matokeo yaliyofikiwa kweli kweli yalikuwa gani?" |
| Fee paid | "Ada jumla iliyolipwa ilikuwa kiasi gani? Una risiti au uthibitisho wa makubaliano?" |
| Psychological harm | "Je, mafunzo haya yamekuathiri kiakili? Unajisikiaje kwa sasa?" |
| Mental health support | "Je, umewahi kuona daktari au mwanasaikolojia kuhusu hali hii?" |
| Evidence of promises | "Ahadi hizo zilielezwa wapi — tovuti, picha ya tangazo, au barua pepe? Una ushahidi?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | boundary_violation AND sexual misconduct | Police referral (Violence Against Women Act 2022); support services; immediate safety check |
| issue_type | psychological_harm | Mental health referral; counseling services; assess severity |
| issue_type | impersonating_therapist AND clinical claims | Medical Practitioners Board complaint; criminal if harm |
| issue_type | cult_like_behavior AND isolation | Multi-stakeholder intervention; family notification; police if coercive control |
| issue_type | fraudulent_outcome_claims AND fee > 1M TZS | FCC consumer protection + police criminal fraud investigation |
| issue_type | qualifications_misrepresented AND ICF certification falsely claimed | ICF disciplinary complaint; FCC false advertising |
| issue_type | refund_refused AND program incomplete | FCC consumer protection; Fair Competition Act Cap. 285 |
| psychological_harm | Yes AND mental_health_professional_not_seen | Immediate mental health referral before continuing complaint process |

---

*Sources: Tanzania Fair Competition Act Cap. 285, Tanzania Law of Contract Act Cap. 433, ICF Code of Ethics, EMCC Global Code of Ethics, Prevention of Violence Against Women and Children Act 2022, Medical Practitioners and Dentists Act (Tanzania), ISO 10002:2018, ISO 20700:2017, PCCB Act Cap. 329*
