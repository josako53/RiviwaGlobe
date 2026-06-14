---
tags: [industry-kb, field-standards, feedback-fields]
---
# Personal Development / Coaching — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: life coach, kocha wa maisha, career coach, kocha wa kazi, executive coach, business coach, motivational speaker, msemaji wa motisha, mental health coach, wellness coach, mindset coach, personal trainer, fitness coach, nutrition coach, spiritual coach, NLP (Neuro-Linguistic Programming), CBT (Cognitive Behavioral Therapy), emotional intelligence training, leadership development, mafunzo ya uongozi, self-help program, personal growth workshop, seminar ya maendeleo binafsi, online course, kozi ya mtandaoni, masterclass, bootcamp, coaching program, mentorship platform, youth empowerment, vijana, women empowerment, wanawake, confidence building, resilience training, burnout recovery, ICF (International Coaching Federation), certified coach, accredited program, credentials ya kocha, fake coach, kocha wa bandia, life skills program, counselor, mshauri, psychologist, therapist, mwanasaikolojia, wellness center, kituo cha ustawi, online therapy, tele-counseling

## Why Industry-Specific Fields Matter

Generic feedback fields cannot distinguish between a misrepresentation of coaching credentials (requiring ICF accreditation verification and India CCPA-equivalent consumer protection referral), a breach of client confidentiality by a therapist (requiring professional licensing board notification), and a refund dispute after a cancelled coaching program (requiring consumer protection escalation through FCC Tanzania or relevant body) — all requiring different regulatory bodies, different evidence standards, and different sensitivity levels around mental health disclosure. Without coaching-specific fields, the AI cannot route complaints, detect credential fraud patterns, or protect vulnerable clients from harmful practices.

## Source Standards

- ICF (International Coaching Federation) Ethical Conduct Review process
- ICF Accreditation Complaint Form (March 2024)
- ICF 2024 Ethical Conduct and Compliance Report (complaint category data)
- ICF Global Accreditation Code of Conduct 2024
- India CCPA (Central Consumer Protection Authority) Coaching Class Guidelines 2024
- Tanzania Consumer Protection Act 2008 (Cap 395) — basis for coaching/course refund disputes
- Fair Competition Commission (FCC) Tanzania — misleading advertising and false claims
- Tanzania Medical Council / Health Professions Council — licensed therapist and psychologist oversight

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| `complainant_name` | Jina la mlalamikaji | Yes | ICF ECR: complaint must identify the complainant; required for case management and follow-up |
| `complainant_contact` | Mawasiliano (simu / barua pepe) | Yes | ICF and India CCPA processes require contact for formal complaint correspondence |
| `complainant_relationship` | Uhusiano wako na kocha / mpango | Yes | ICF Accreditation Complaint Form: "relationship with the organization at the time of the alleged breach" — current client / former client / observer / co-participant |
| `coach_or_trainer_name` | Jina la kocha / mkufunzi | Yes | ICF ECR: complaint must identify the coach in question; India CCPA: trainer identification required for qualification verification |
| `coach_credential_claimed` | Cheti / sifa alizodai kocha | Yes | ICF 2024 Compliance Report: misrepresentation of credentials is a formal complaint category; India CCPA 2024 requires actual qualification disclosure |
| `accreditation_body_claimed` | Chombo cha uthibitisho alichodai | Yes | ICF / EMCC / CTI / other — determines which accreditation body can verify the claim and act against false claims |
| `program_or_course_name` | Jina la mpango / kozi | Yes | ICF Accreditation Complaint Form: identifies the program for investigation; India CCPA requires course identification |
| `program_duration_and_format` | Muda na muundo wa mpango | Yes | Online / in-person / hybrid; hours delivered vs. promised — India CCPA requires disclosure of actual course duration |
| `fees_paid` | Ada zilizolipwa (TZS / USD) | Yes | India CCPA 2024: advertising must "transparently disclose key details including course types"; required for refund remedy calculation |
| `payment_date` | Tarehe ya malipo | Yes | For limitation period and refund eligibility |
| `issue_type` | Aina ya tatizo | Yes | ICF 2024 Compliance Report categories and India CCPA 2024 together cover the full complaint taxonomy; determines regulatory routing |
| `issue_description` | Maelezo ya tatizo | Yes | Required by ICF and India CCPA as the primary narrative record; must be specific and dated |
| `date_of_incident` | Tarehe ya tukio / tatizo | Yes | ICF ECR: complaint must be filed "within one year of the date of the alleged breach of conduct"; India CCPA limitation period also applies |
| `evidence_documentation` | Ushahidi (mkataba, matangazo, risiti, mawasiliano) | Yes | ICF Accreditation Complaint Form requires supporting evidence; India CCPA: contracts, promotional materials, receipts are key |
| `desired_outcome` | Matokeo unayotaka | Yes | Refund / credential investigation / professional sanction / coaching improvement — framing helps route to correct pathway |
| `prior_complaint_to_coach_or_organization` | Je, umeshalalamika kwa kocha / shirika moja kwa moja? | Yes | ICF and consumer protection frameworks generally require internal resolution attempt first; determines escalation eligibility |
| `coach_or_organization_response` | Jibu la kocha / shirika (kama lipo) | Conditional | Required at ICF ECR or regulatory escalation stage |

### Conditional Fields (collect based on issue type)

**If `issue_type = credential_misrepresentation`:**
Also collect:
- `icf_credential_claimed_type` — Aina ya cheti cha ICF alichodai: ACC / PCC / MCC / None — ICF has a public credential verification database
- `icf_member_number_claimed` — Nambari ya uanachama wa ICF alichodai (kama ipo): For verification against ICF public directory
- `actual_qualification_verified` — Sifa halisi zilizothibitishwa (kama umejua): For gap documentation
- `advertising_material_available` — Je, una matangazo yake (website, flyer, social media post)? Yes/No: Key evidence for ICF and FCC Tanzania misrepresentation complaint

**If `issue_type = misleading_advertising` OR `false_success_claims`:**
Also collect:
- `specific_false_claim` — Dai la uongo maalum: "Guaranteed income in 30 days" / "100% success rate" / specific false testimonial — India CCPA 2024 specifically targets these
- `advertising_channel` — Njia ya matangazo: Website / social media / WhatsApp / flyer / TV / radio
- `paid_testimonials_used` — Je, ushuhuda uliolipwa ulitumika bila kufahamisha? Yes/No: India CCPA 2024 explicitly prohibits undisclosed paid testimonials
- `promotional_material_preserved` — Je, una nakala ya matangazo? Yes/No: Critical for FCC Tanzania misleading advertising complaint

**If `issue_type = refund_denied` OR `program_not_delivered`:**
Also collect:
- `sessions_promised` — Idadi ya vipindi vilivyoahidiwa: For delivery gap quantification
- `sessions_delivered` — Idadi ya vipindi vilivyotolewa: Actual delivery vs. promise
- `cancellation_reason` — Sababu ya kufuta (kama ilitolewa): Program cancelled / quality failure / coach unavailable
- `refund_requested_date` — Tarehe ya kuomba kurejesheewa pesa: For limitation period and response timeline
- `refund_policy_in_contract` — Je, sera ya kurejesheewa pesa ilikuwa kwenye mkataba? Yes/No: India CCPA requires clear refund policy disclosure

**If `issue_type = breach_of_confidentiality` OR `data_privacy_breach`:**
Also collect:
- `information_disclosed` — Taarifa zilizofunuliwa bila ruhusa: Client information shared with who
- `disclosure_channel` — Njia ya kufunuliwa: Social media / other clients / family / employer / public
- `harm_from_disclosure` — Madhara kutokana na kufunuliwa: Employment loss / relationship harm / safety risk / psychological harm
- `licensed_professional_flag` — Je, kocha ni mtaalamu aliyeidhinishwa (daktari / mshauri wa kisaikolojia)? Yes/No: Licensed professionals face additional disciplinary action from health regulatory bodies

**If `issue_type = inappropriate_conduct` OR `power_imbalance`:**
Also collect:
- `conduct_type` — Aina ya mwenendo mbaya: Sexual / psychological / financial exploitation
- `ongoing_contact_flag` — Je, kocha bado ana mawasiliano nawe? Yes/No: Safety assessment
- `support_services_needed` — Je, unahitaji msaada wa kisaikolojia? Yes/No: FaithTrust principle applied — client wellbeing referral

**If `issue_type = coercive_practices` OR `cult_like_recruitment`:**
Also collect:
- `isolation_tactics` — Je, ulilazimishwa kuacha mahusiano ya kawaida? Yes/No: High-control group indicator
- `financial_pressure_tactics` — Je, ulishinikizwa kulipa zaidi ya ulivyotarajiwa? Yes/No
- `exit_restriction` — Je, ulikuwa mgumu kujiondoa kwenye mpango? Yes/No

**If `issue_type = harmful_program_content`:**
Also collect:
- `content_that_caused_harm` — Maudhui / mazoea yaliyodhuru: Description of specific harmful elements
- `health_impact` — Athari kwa afya: Psychological / physical / behavioral change
- `medical_professional_consulted` — Je, umepata msaada wa mtaalamu wa afya? Yes/No

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| PD-01 | `credential_misrepresentation` | False claims of ICF membership, credential status, or programme accreditation |
| PD-02 | `misleading_advertising` | False success claims, outcome guarantees, or undisclosed paid testimonials |
| PD-03 | `inappropriate_conduct` | Sexual, psychological, or financial misconduct toward client |
| PD-04 | `breach_of_confidentiality` | Client session content or personal information shared without consent |
| PD-05 | `power_imbalance_exploitation` | Using coaching relationship to exploit client financially or emotionally |
| PD-06 | `refund_denied` | Refund withheld after program cancellation, underdelivery, or quality failure |
| PD-07 | `program_not_delivered` | Promised sessions, content, or outcomes not provided |
| PD-08 | `harmful_program_content` | Content or practices that caused psychological or physical harm |
| PD-09 | `coercive_practices` | Cult-like recruitment or retention; isolation; exit barriers |
| PD-10 | `harassment` | Sexual or psychological harassment of client by coach |
| PD-11 | `unauthorized_icf_branding` | False use of ICF logo, credential marks, or accreditation claims |
| PD-12 | `data_privacy_breach` | Unauthorized collection or sharing of client personal data |
| PD-13 | `unqualified_trainer` | Trainer lacking stated qualifications delivering program |
| PD-14 | `poor_coaching_quality` | Coaching sessions of significantly lower quality than contracted; generic, non-personalized, ineffective |

### Resolution Standards for This Industry

- **ICF Ethical Conduct Review:** ICF investigates complaints against ICF-credentialed coaches; complaint must be filed within one year of the alleged breach; ICF ECR is confidential; potential sanctions include credential revocation.
- **ICF Accreditation Complaint:** For false claims of ICF accreditation; ICF investigates and can issue public corrections and remove falsely claimed credentials from public listings.
- **India CCPA framework (reference for similar jurisdictions):** Coaching organizations must disclose actual qualifications, realistic success rates, refund policy, and cannot use undisclosed paid testimonials.
- **Tanzania Consumer Protection Act 2008:** Provides remedy for misleading advertising, failure to deliver contracted services, and refund disputes; FCC Tanzania enforces.
- **Licensed mental health professionals (Tanzania):** Complaints about licensed psychologists, counselors, or therapists in Tanzania are handled by the Medical Council of Tanzania or Health Professions Council; breach of confidentiality is a disciplinary offense.
- **Refund timeline:** Tanzania Consumer Protection Act basis — refunds for undelivered services should be processed within 14 days of demand; failure enables FCC complaint.
- **ICF limitation period:** One year from the date of the alleged breach.

### Escalation Triggers (field values that require immediate escalation)

- `issue_type = inappropriate_conduct` AND `conduct_type = Sexual` — Escalate to police; safety assessment; do not pressure client to continue engagement with coach
- `issue_type = harmful_program_content` AND `health_impact` includes psychological crisis — Mental health emergency referral; provide crisis support contacts (Befrienders Kenya Tanzania / mental health hotline)
- `issue_type = coercive_practices` AND `isolation_tactics = Yes` — High-control group protocol; contact family if client consents; FCC Tanzania referral
- `issue_type = breach_of_confidentiality` AND `licensed_professional_flag = Yes` AND `harm_from_disclosure` includes safety risk — Escalate to Medical Council of Tanzania / Health Professions Council; police notification if safety risk exists
- `issue_type = credential_misrepresentation` AND `icf_member_number_claimed` cannot be verified in ICF directory — Escalate to ICF Accreditation Complaint; advise FCC Tanzania misleading advertising complaint; public alert if multiple clients affected
- `issue_type = misleading_advertising` AND multiple complainants report same program — Pattern fraud; FCC Tanzania escalation; coordinate multi-complainant filing

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `submitter_name` | Jina la mtoa maoni (hiari) | Optional | Suggestions may be anonymous |
| `program_or_coach_name` | Jina la mpango / kocha | Yes | Routes suggestion to correct entity or accreditation body |
| `suggestion_category` | Kategoria ya mapendekezo | Yes | Systematic routing and analysis |
| `suggestion_detail` | Maelezo ya mapendekezo | Yes | Free text; core content |
| `program_format` | Muundo wa mpango (mtandaoni / ana kwa ana) | Recommended | Format-specific suggestions route to different implementation pathways |

### Industry-Specific Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| PDS-01 | `curriculum_quality` | Ubora wa maudhui ya mafunzo |
| PDS-02 | `accreditation_transparency` | Uwazi wa vyeti na ithibati |
| PDS-03 | `refund_policy_clarity` | Uwazi wa sera ya kurejesheewa pesa |
| PDS-04 | `client_safeguarding` | Kulinda wateja wa kocha |
| PDS-05 | `digital_platform_quality` | Ubora wa jukwaa la kidijitali |
| PDS-06 | `cultural_relevance` | Umuhimu wa kiutamaduni (muktadha wa Afrika Mashariki) |
| PDS-07 | `outcome_measurement` | Kupima matokeo ya kweli ya mafunzo |
| PDS-08 | `pricing_transparency` | Uwazi wa bei na ada zote |
| PDS-09 | `ethics_and_boundaries` | Maadili ya kocha na mipaka ya kitaaluma |
| PDS-10 | `mental_health_integration` | Ushirikiano na huduma za afya ya akili |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `inquirer_name` | Jina la mwulizaji (hiari) | Optional | Not required for general inquiries |
| `inquiry_type` | Aina ya swali | Yes | Routes to correct knowledge base or referral |
| `coach_or_organization_name` | Jina la kocha / shirika (kama linajulikana) | Conditional | For entity-specific inquiries |
| `preferred_response_channel` | Njia unayopendelea ya jibu | Yes | SMS / Simu / WhatsApp / Barua pepe |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Swahili | Additional Fields Needed |
|-------------|---------|--------------------------|
| `credential_verification` | Je, kocha huyu ana sifa halisi za ICF / EMCC? | `coach_or_trainer_name`, `coach_credential_claimed`, `accreditation_body_claimed` |
| `refund_policy_inquiry` | Sera ya kurejesheewa pesa ni nini? | `program_or_course_name`, `fees_paid` |
| `program_eligibility` | Je, mimi ni mtu anayefaa kwa mpango huu? | `program_or_course_name`, `complainant_relationship` context |
| `icf_accreditation_status` | Je, mpango huu una ithibati ya ICF? | `program_or_course_name`, `coach_or_trainer_name` |
| `complaint_process_guidance` | Jinsi ya kuwasilisha malalamiko kwa ICF | `issue_type`, `coach_credential_claimed` |
| `mental_health_vs_coaching` | Tofauti kati ya kocha na mshauri wa kisaikolojia | General inquiry — no extra fields |
| `how_to_find_certified_coach` | Jinsi ya kupata kocha aliyeidhinishwa | `location_district`, `coaching_focus_area` |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `submitter_name` | Jina la mtoa pongezi (hiari) | Optional | For acknowledgement; not required |
| `coach_or_program_recognized` | Kocha / Mpango unaopongezwa | Yes | Routes compliment for coach recognition and program quality tracking |
| `outcome_achieved` | Matokeo uliyofikia | Yes | Specific, measurable outcome if possible; captures real impact data for program M&E |
| `what_coach_did_well` | Kocha alifanya nini vizuri | Yes | Specific positive behavior; routes to coach recognition |
| `program_dates` | Tarehe za mpango | Recommended | For correlation with coach performance records |
| `would_recommend` | Je, ungependekeza kocha / mpango huu kwa mwingine? | Yes | Net Promoter Signal; valuable for coach directory and accreditation body reputation data |
| `coaching_focus_area` | Eneo la mafunzo (kazi, maisha, afya, nk) | Recommended | Enables specialization-specific recognition |

---

## AI Conversation Guidance for This Industry

- **Treat credential verification as the first substantive question after understanding the issue type.** If a complaint involves any coaching or training service, ask "Kocha huyu alidai kuwa na sifa gani — kwa mfano, cheti cha ICF, au sifa nyingine?" early. Credential claims are either verifiable or falsifiable, and this single field determines whether you are dealing with a professional dispute or a fraud case.
- **For complaints involving personal distress or mental health, lead with wellbeing before collecting fields.** If the person mentions depression, trauma, anxiety, or psychological harm, first ask "Je, uko sawa sasa hivi? Je, unahitaji msaada wa haraka wa kisaikolojia?" and provide mental health support contacts before continuing the complaint process.
- **Never request therapy session content.** If the complaint involves a therapist or counselor, collect the type of breach (confidentiality, misconduct, overcharging) without asking the client to re-describe their private session content. Say "Sihitaji maelezo ya yaliyojadiliwa kwenye kipindi chako — ninahitaji tu kuelewa aina ya tatizo na jinsi ilivyotokea."
- **For refund disputes, collect the amount and the gap between sessions promised and delivered before asking for evidence uploads.** Ask "Uliahidiwa vipindi vingapi? Na ulihudhuria vipindi vingapi kabla tatizo kulitokea?" then "Je, malipo yako yalikuwa kiasi gani?" — these two fields quantify the claim before asking the client to gather receipts.
- **For coercive or cult-like practice complaints, collect safety information before program details.** Ask "Je, uko salama sasa hivi? Je, uko huru kuwasiliana na familia au marafiki zako?" before asking about the program name or fees. High-control program victims may be isolated and the AI's first priority is safety assessment.
- **Do not ask the complainant to confront the coach directly.** For misconduct and harassment complaints, say "Usijaribu kuwasiliana na kocha mwenyewe kuhusu tatizo hili — tutakusaidia kupitia njia sahihi" — this prevents re-traumatization and preserves the complaint record.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Coach name | "Jina la kocha au mkufunzi ni nini?" |
| Credential claimed | "Kocha huyu alidai kuwa na sifa gani — kwa mfano, cheti cha ICF, digrii ya saikolojia, au sifa nyingine?" |
| Program name | "Jina la mpango au kozi ni nini — inahusu nini na ilichukua muda gani?" |
| Fees paid | "Uliingia mkataba gani wa malipo — ulimlipa kiasi gani na jinsi gani?" |
| Issue type | "Tatizo lako linahusiana na nini hasa — sifa za uongo, mwenendo mbaya, siri ilifyuliwa, kurejesheewa pesa, au kitu kingine?" |
| Sessions promised vs delivered | "Uliahidiwa vipindi / masaa ngapi ya mafunzo? Na ulipata vipindi / masaa ngapi kabla tatizo kulitokea?" |
| Safety check | "Je, uko salama sasa hivi na uko huru kuwasiliana na familia au marafiki zako?" |
| Wellbeing check | "Je, uko sawa kiakili na kiemosho? Unahitaji msaada wa haraka wa kisaikolojia?" |
| Evidence | "Una mkataba, matangazo, risiti, au mawasiliano ya barua pepe / ujumbe kuhusu mpango huu?" |
| Would recommend | "Kwa ujumla, ingekuwa salama, ungempendekeza kocha / mpango huu kwa rafiki yako?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| `issue_type` | `inappropriate_conduct` AND `conduct_type = Sexual` | Escalate to police; victim safety assessment; do not route through coach or organization |
| `issue_type` | `harmful_program_content` AND `health_impact` includes psychological crisis | Mental health emergency referral; provide crisis support contacts; create priority welfare ticket |
| `issue_type` | `coercive_practices` AND `isolation_tactics = Yes` | High-control group protocol; FCC Tanzania referral; family safety notification if client consents |
| `issue_type` | `credential_misrepresentation` AND `icf_credential_claimed_type` cannot be verified | Escalate to ICF Accreditation Complaint; advise FCC Tanzania misleading advertising complaint |
| `issue_type` | `breach_of_confidentiality` AND `licensed_professional_flag = Yes` | Escalate to Medical Council of Tanzania or Health Professions Council; licensure disciplinary action |
| `issue_type` | `misleading_advertising` AND multiple complainants same program | Pattern fraud; FCC Tanzania escalation; coordinate multi-complainant filing |
| `issue_type` | `refund_denied` AND `sessions_delivered < sessions_promised × 0.5` | Consumer Protection Act basis; FCC complaint pathway; calculate refund entitlement on pro-rata basis |
| `issue_type` | `data_privacy_breach` | Escalate to relevant professional body (if licensed) and PDPC Tanzania; advise complainant of rights |
| `coach_credential_claimed` | ICF credential AND cannot verify in public ICF directory | Escalate to ICF Accreditation Complaint; credential fraud flag; advise complainant to cease payments |
| `ongoing_contact_flag` | Yes AND `issue_type` involves misconduct | Safety priority; advise client to cease engagement with coach; preserve all evidence before stopping contact |

---

*Sources: ICF Ethical Conduct Review process, ICF Accreditation Complaint Form (March 2024), ICF 2024 Ethical Conduct and Compliance Report, ICF Global Accreditation Code of Conduct 2024, India CCPA Coaching Class Consumer Protection Guidelines 2024, Tanzania Consumer Protection Act 2008 Cap 395, Fair Competition Commission Tanzania, Tanzania Medical Council and Health Professions Council regulatory mandate*
