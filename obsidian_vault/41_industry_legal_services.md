---
tags: [industry-kb, feedback-classification, field-standards]
---
# Legal Services / Law Firms — Feedback Collection Fields & Standards

## Industry Identifiers

advocate, attorney, lawyer, law firm, legal aid, legal counsel, court, magistrate, High Court, Court of Appeal, land court, small claims court, mediator, arbitrator, notary, commissioner for oaths, company secretary, Tanganyika Law Society (TLS), Judiciary of Tanzania, power of attorney, affidavit, petition, pleading, case file, retainer, legal opinion, conveyancing, title deed, succession, probate, ADR, Zanzibar legal system, Kadhi court, Industrial Court, TLS Ethics Committee, SRA, IBA, legal negligence, missed court deadline, overcharging, conflict of interest, breach of confidentiality, abandonment of case, criminal matter, civil litigation, family law, matrimonial, property transfer, immigration, employment law, legal aid bureau, paralegal

## Why Industry-Specific Fields Matter

Legal service complaints require capture of the lawyer's bar membership, matter type, and court references because the jurisdiction for discipline (Tanganyika Law Society Ethics Committee), service quality (Legal Ombudsman equivalent), and financial recovery depends entirely on these details. A fee dispute and a professional negligence claim that caused a court loss require different regulatory pathways, different evidence, and different timelines — and they cannot be distinguished without the engagement details, matter type, and documented financial loss amount collected at intake.

## Source Standards

- SRA (Solicitors Regulation Authority, UK) — Report a Solicitor form; complaint guidance (required fields confirmed)
- IBA (International Bar Association) — Guide for Establishing and Maintaining Complaints and Discipline Procedures (2007); International Principles on Conduct for the Legal Profession (2011)
- TLS (Tanganyika Law Society) — Ethics Committee Rules of Proceedings (2023); Tanganyika Law Society Act CAP.307 R.E. 2020
- Legal Ombudsman (UK) — Complaint process for service quality issues (parallel model)
- ISO 9001:2015 / ISO 13485 — Quality management complaint fields applied by analogy

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| law_firm_name | Jina la kampuni ya kisheria | Yes | SRA form — "solicitor's or firm's name" (explicitly required); routes to TLS or firm |
| law_firm_address | Anwani ya ofisi ya kampuni | Yes | SRA form — work address required; aids TLS verification |
| lawyer_name | Jina la wakili/mwanasheria | Yes | SRA form; IBA Guide §3 — respondent identification is mandatory |
| bar_membership_number | Nambari ya usajili wa TLS | Optional | TLS Ethics Rules 2023; aids verification of current good standing |
| matter_type | Aina ya kesi/jambo | Yes | IBA Guide 2007; SRA — context determines applicable professional standards |
| case_matter_reference | Nambari ya kesi au faili | Optional | SRA "case reference number"; IBA Guide §3 — aids record retrieval |
| engagement_start_date | Tarehe ya kuanza kushirikiana | Yes | SRA form — "date(s) when the event(s) took place" is required |
| issue_type | Aina ya tatizo | Yes | SRA; IBA Guide §2; TLS Ethics Rules 2023 — classification determines TLS vs. courts vs. internal |
| financial_loss_caused_tzs | Hasara ya kifedha (TZS) | Yes (if applicable) | SRA; Legal Ombudsman — "evidence of financial loss" required for compensation claims |
| detailed_description | Maelezo ya kina ya matukio | Yes | SRA form — "detailed description" (required); IBA Guide §3 |
| desired_outcome | Matokeo yanayotarajiwa | Yes | IBA Guide §5 — remedies include apology, compensation, fee reduction |
| complaint_to_regulatory_body_made | Je, umekwisha lalamika kwa chombo cha udhibiti? | Yes | TLS Ethics Rules 2023; SRA — routing decision for parallel complaints |
| complainant_name | Jina la mlalamikaji | Yes | SRA form — Name (required) |
| complainant_address | Anwani ya mlalamikaji | Yes | SRA form — Address (required) |
| complainant_phone | Simu ya mlalamikaji | Yes | SRA form — Telephone (required) |
| complainant_email | Barua pepe ya mlalamikaji | Yes | SRA form — Email (required) |
| supporting_documents | Nyaraka za kuthibitisha | Optional (but strongly advised) | SRA — "copies of letters, emails, statements, or court materials" explicitly listed |

### Conditional Fields (collect based on issue type)

**If issue_type = Professional Negligence:**
- negligence_type → missed court deadline / wrong legal advice / failure to file / failure to challenge evidence / failure to disclose settlement offer / unauthorized action
- court_name → court where the matter was pending
- court_file_number → court file or cause number
- relevant_court_dates → key dates (filing deadline, hearing date, appeal window)
- consequence_of_negligence → case dismissed / appeal missed / case lost / financial loss / property loss

**If issue_type = Fee Dispute / Overcharging:**
- fee_agreed_tzs → amount agreed at engagement start
- fee_invoiced_tzs → amount actually billed
- fee_agreement_type → written retainer / verbal agreement / court-fixed scale fee
- fee_agreement_documented → whether fee agreement was in writing (Yes/No)
- disputed_charges → specific charges disputed (appearance fees / disbursements / stamp duty / additional hours)
- itemised_bill_provided → whether a detailed bill was provided (Yes/No)
- documents_withheld_for_fees → whether lawyer is withholding documents pending payment (Yes/No)

**If issue_type = Conflict of Interest:**
- conflict_type → representing opposing party simultaneously / acting for related party without disclosure / personal interest in matter outcome
- conflict_disclosed_at_start → whether any conflict was disclosed at engagement start (Yes/No)
- discovery_of_conflict → how complainant discovered the conflict

**If issue_type = Breach of Confidentiality:**
- information_disclosed → what confidential information was shared
- disclosed_to → opposing party / court / third party / public / unknown
- harm_caused → case prejudiced / financial loss / reputational damage

**If issue_type = Abandoned Case / Withdrawal Without Notice:**
- withdrawal_notice_given → Yes/No
- withdrawal_notice_date → date notice was given (if any)
- new_hearing_date → any hearing date that is now at risk
- alternative_representation_secured → whether complainant has found a new lawyer (Yes/No)
- urgency_level → imminent hearing date (Yes/No + date)

**If issue_type = Land / Property / Conveyancing:**
- property_description → plot number, area, location
- title_deed_status → registered / unregistered / disputed / two owners
- mlhhsd_reference → Ministry of Lands reference if applicable
- stamp_duty_paid → Yes/No
- stamp_duty_receipt → whether receipt was provided by advocate (Yes/No)
- subdivision_consent_obtained → whether all beneficiaries consented to subdivision (Yes/No)

**If issue_type = Dishonesty / Fraud / Misappropriation:**
- funds_misappropriated_tzs → amount misappropriated from client funds or trust account
- funds_source → client funds given for court fees / stamp duty / settlement / other
- evidence_of_fraud → receipts, bank statements, correspondence
- police_report_filed → Yes/No + OB number if filed

**If issue_type = Communication Failure:**
- last_contact_date → date of last meaningful communication from lawyer
- contact_attempts_made → number of times complainant tried to reach lawyer
- updates_expected → what communication was promised and not delivered

### Issue Type Classification

| Code | Issue Type | Regulatory Body | Resolution Target |
|------|-----------|----------------|-------------------|
| LEG-GR-01 | Professional Negligence | TLS Ethics Committee; courts | 30 working days |
| LEG-GR-02 | Missed Court Deadline | TLS Ethics Committee | 21 working days |
| LEG-GR-03 | Fee Dispute / Overcharging | TLS; Legal Ombudsman equivalent | 21 working days |
| LEG-GR-04 | Conflict of Interest | TLS Ethics Committee (2023 Rules) | 21 working days |
| LEG-GR-05 | Breach of Confidentiality | TLS; courts | 14 working days |
| LEG-GR-06 | Communication Failure | TLS; firm internal | 14 working days |
| LEG-GR-07 | Abandoned Case / Withdrawal Without Notice | TLS Ethics Committee | 14 working days |
| LEG-GR-08 | Dishonesty / Fraud / Misappropriation | Police + TLS | Immediate escalation |
| LEG-GR-09 | Land / Property / Conveyancing | TLS; MLHHSD | 30 working days |
| LEG-GR-10 | Court Registry / Judiciary Issue | Judicial Service Commission | 30 working days |
| LEG-GR-11 | Legal Aid Quality Issue | Legal Aid Board / TLS | 21 working days |
| LEG-GR-12 | ADR Process Complaint | TIArb; courts | 21 working days |

### Resolution Standards for This Industry

- **TLS Ethics Committee Rules 2023**: Written complaint must be submitted to TLS. Ethics Committee investigates and may recommend reprimand, suspension, or striking off the roll. TLS holds the advocate's response within 21 days of receiving the complaint.
- **TLS Act CAP.307**: TLS has statutory authority to investigate complaints against advocates practising in Tanzania mainland. Complaints must relate to professional conduct.
- **SRA (as model standard)**: Service quality complaints (not regulatory breaches) are distinguished from conduct complaints — service complaints go to the firm's internal complaints process first; conduct complaints go directly to the regulatory body.
- **IBA Guide 2007**: Firms should have a published complaints procedure; complainants should attempt internal resolution first unless urgency prevents this.
- **Legal Ombudsman model**: Financial compensation, apology, and fee reduction are recognised remedies — capture desired_outcome early to align expectations.
- **Tanzania courts**: Professional negligence causing financial loss may be pursued in civil courts independently of TLS disciplinary proceedings.

### Escalation Triggers (field values that require immediate escalation)

- `issue_type = LEG-GR-08` (Dishonesty / Fraud) → refer to Police and TLS immediately; advise complainant to stop all further payments to the advocate
- `urgency_level = Yes` (imminent hearing date AND advocate is unreachable) → flag for same-day human review; advise complainant to seek emergency representation
- `documents_withheld_for_fees = Yes` AND `urgency_level = Yes` → urgent legal intervention required; advise complainant of right to file court application for file return
- Advocate alleged to have colluded with opposing counsel or judge → refer to Judicial Service Commission and PCCB
- Criminal matter: client convicted due to advocate's failure to appear or gross negligence → urgent review; possible application for review/retrial
- Forged court documents or false judgment in use → refer to Police and courts immediately
- Property lost or facing execution based on fraudulent ruling → urgent court application required; flag for immediate human review
- Client detained without consular notification (foreign national) → refer to Ministry of Foreign Affairs and Vienna Convention obligations
- `issue_type = LEG-GR-11` (Legal Aid) AND client faces imminent criminal trial without representation → urgent referral to Legal Aid Board

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| law_firm_name | Jina la kampuni ya kisheria | Yes | IBA Guide 2007 — education and information requirements for improvement |
| suggestion_category | Aina ya pendekezo | Yes | IBA Guide; SRA publishing complaints guidance |
| suggestion_detail | Maelezo ya pendekezo | Yes | Full description of improvement idea |
| matter_type_context | Aina ya kesi (muktadha) | Optional | IBA Guide — contextualises suggestion within specific practice area |

### Industry-Specific Improvement Categories

| Category Code | Category Name | Swahili |
|--------------|---------------|---------|
| LEG-SG-01 | Client Communication / Case Updates | Mawasiliano na mteja kuhusu kesi |
| LEG-SG-02 | Fee Transparency / Written Agreement | Uwazi wa ada na makubaliano ya maandishi |
| LEG-SG-03 | Case Progress Tracking | Ufuatiliaji wa maendeleo ya kesi |
| LEG-SG-04 | Client Portal / Technology | Mfumo wa mtandaoni kwa mteja |
| LEG-SG-05 | Plain Language Explanations | Maelezo ya lugha ya kawaida |
| LEG-SG-06 | Legal Aid Expansion / Access | Upanuzi wa msaada wa kisheria |
| LEG-SG-07 | Court Process Efficiency | Ufanisi wa mchakato wa mahakama |
| LEG-SG-08 | ADR / Mediation Access | Upatikanaji wa usuluhisho wa nje ya mahakama |
| LEG-SG-09 | Community Legal Education | Elimu ya kisheria kwa jamii |
| LEG-SG-10 | Document Management / File Handling | Usimamizi wa nyaraka na faili |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| law_firm_or_lawyer_name | Jina la kampuni au wakili | Yes | SRA; TLS — routes inquiry to correct entity |
| inquiry_type | Aina ya swali | Yes | SRA; TLS — determines information source |
| case_reference_number | Nambari ya kesi (kama ipo) | Optional | SRA; TLS — speeds up record retrieval |
| full_name | Jina kamili | Yes | SRA; TLS — required for personalised response |
| contact_details | Mawasiliano | Yes | SRA; TLS — required for follow-up |
| specific_question | Swali maalum | Yes | SRA; IBA — full question text required |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Additional Fields Needed |
|-------------|-------------------------|
| Case / Matter status | case_reference_number, matter_type, last_known_hearing_date |
| Fee estimate / Cost information | matter_type, case_complexity, stage_of_proceedings |
| Legal aid availability | matter_type, location, income_level (general) |
| Lawyer accreditation / TLS membership | lawyer_name, law_firm_name |
| Document / File retrieval | case_reference, type_of_document_required |
| Court process / Procedure | court_name, type_of_application, stage |
| Land transfer / Conveyancing process | property_type, location, parties_involved |
| Succession / Probate process | deceased_estate_value_range, will_exists |
| Lawyer verification (TLS register) | lawyer_name, law_firm_name |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| law_firm_or_lawyer_name | Jina la kampuni au wakili | Yes | IBA Guide — positive feedback improves conduct standards; ISO 9001 §9.1.2 |
| subject_of_praise | Kinachosifiwa | Yes | IBA Guide; ISO 9001 — enables recognition and replication of excellent practice |
| matter_type | Aina ya kesi | Optional | IBA Guide — contextualises praise within practice area |
| description | Maelezo ya uzoefu mzuri | Yes | ISO 9001 §9.1.2 — client satisfaction data |
| named_individual | Jina la mtu anayesifiwa | Optional | IBA Guide — individual recognition encourages excellence |

### Praise Subject Categories

| Code | Subject | Swahili |
|------|---------|---------|
| LEG-AP-01 | Case Outcome / Result | Matokeo ya kesi |
| LEG-AP-02 | Professionalism / Ethics | Utaalamu na maadili |
| LEG-AP-03 | Communication Quality | Ubora wa mawasiliano |
| LEG-AP-04 | Speed of Resolution | Kasi ya kumaliza kesi |
| LEG-AP-05 | Accessibility / Client Care | Upatikanaji na huduma kwa mteja |
| LEG-AP-06 | Fee Fairness / Transparency | Uwazi na haki ya ada |
| LEG-AP-07 | Legal Aid Quality | Ubora wa msaada wa kisheria |

---

## AI Conversation Guidance for This Industry

- **Lead with lawyer name, firm name, and matter type — in that order**: These three fields determine jurisdiction (TLS vs. courts), applicable professional rules, and routing. Ask "Tunazungumzia wakili au kampuni gani ya kisheria?" and "Kesi yako inahusiana na nini — ardhi, familia, madai ya biashara, kesi ya jinai, au jambo lingine?" before asking about the nature of the complaint.
- **Collect financial loss and fee dispute as separate, sequential questions**: First ask "Je, tatizo la wakili likusababishia hasara yoyote ya kifedha — kama kupoteza kesi au faini?" and only then, separately, ask "Je, pia kuna tatizo na ada au ankara ya wakili?" Conflating these two questions leads to confused answers and missed data.
- **For urgent situations (imminent hearing dates, property being seized), identify urgency at the start**: After the initial greeting, ask "Je, kuna kitu kinachohitaji kuchukuliwa hatua haraka sana — kama tarehe ya mahakama inakuja au mali inazuiwa?" If yes, flag immediately for human review before completing the full intake.
- **For land / property complaints, ask for plot number and title deed status early**: In Tanzania, land disputes are extremely common and require MLHHSD context. Ask "Mali hiyo ina hati ya kumiliki (title deed) au hati ya haki ya kukaa (right of occupancy)?" early.
- **Never ask if the lawyer committed fraud directly** — instead, ask what happened to the money given and let the complainant describe. Ask "Ulimpa wakili pesa kwa madhumuni gani — kama ada za mahakama au stakabadhi?" and "Je, kuna ushahidi wowote wa matumizi ya pesa hiyo?" — the pattern of answers will surface fraud signals without putting words in the complainant's mouth.

## Swahili Key Phrases for Field Collection

| Field Being Collected | Swahili Phrase to Use |
|----------------------|----------------------|
| lawyer_name | "Jina la wakili wako ni nani?" |
| law_firm_name | "Ni kampuni gani ya kisheria unayozungumzia?" |
| matter_type | "Kesi yako au jambo lako la kisheria linahusiana na nini — ardhi, familia, biashara, jinai, au kingine?" |
| engagement_start_date | "Ulianza kushirikiana na wakili huyu lini?" |
| issue_type | "Tatizo lako kuu ni nini — ucheleweshaji, kutokufanya kazi vizuri, ada kubwa kupita kiasi, au jambo lingine?" |
| financial_loss_caused_tzs | "Je, tatizo hili limekusababishia hasara ya kifedha? Ni kiasi gani takriban?" |
| desired_outcome | "Unataka nini kifanyike — msamaha, kurejesha pesa, au kitu kingine?" |
| complaint_to_regulatory_body_made | "Je, umeshalalamika kwa TLS au mahakama yoyote kuhusu tatizo hili?" |
| documents_withheld_for_fees | "Je, wakili anashikilia nyaraka zako au faili yako kwa sababu ya madeni ya ada?" |
| urgency_level | "Je, kuna tarehe ya mahakama inayokuja hivi karibuni ambayo inaweza kuathirika?" |
| bar_membership_number | "Je, unajua nambari ya usajili wa wakili huyo katika TLS? Kama hujui, tunaweza kuthibitisha jina lake." |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | LEG-GR-08 (Dishonesty / Fraud) | Immediate escalation; refer to Police and TLS; advise complainant to stop payments |
| urgency_level | Yes (imminent hearing) | Flag for same-day human review; advise complainant to seek emergency representation |
| documents_withheld_for_fees | Yes AND urgency_level = Yes | Advise immediate court application for file return; flag urgent |
| complaint_to_regulatory_body_made | Yes (TLS) | Capture TLS reference number; link to existing TLS case |
| complaint_to_regulatory_body_made | No | Provide TLS Ethics Committee contact details and complaint process |
| bar_membership_number | Unknown | Advise complainant to verify advocate's TLS membership on TLS register before proceeding |
| matter_type | Criminal AND lawyer failed to appear AND conviction resulted | Flag as urgent; advise on application for review or retrial |
| issue_type | LEG-GR-04 (Conflict of Interest) AND conflict_disclosed = No | Flag as TLS Ethics Rules 2023 breach; recommend formal TLS complaint |
| financial_loss_caused_tzs | > TZS 10,000,000 | Recommend legal advice on civil negligence claim independent of TLS disciplinary process |
| issue_type | LEG-GR-09 (Land / Conveyancing) AND title_deed_status = Two owners | Flag as urgent; advise complainant to apply for caution/caveat at MLHHSD immediately |
| issue_type | LEG-GR-11 (Legal Aid) AND imminent_trial = Yes | Urgent referral to Legal Aid Board; note client's right to state-provided representation |
| desired_outcome | Compensation | Explain TLS Ethics Committee can recommend fee reduction or apology; civil court required for damages |

---

## Key Entities & Roles

**Regulatory Bodies:** Tanganyika Law Society (TLS), Judiciary of Tanzania, Tanzania Institute of Arbitrators (TIArb), RITA (Registration Insolvency and Trusteeship Agency), MLHHSD (Ministry of Lands Housing and Human Settlements Development), Attorney General's Office, DPP (Director of Public Prosecutions), Law Reform Commission, PCCB (Prevention and Combating of Corruption Bureau)
**Job Titles:** Advocate, Attorney, Partner, Associate, Legal Clerk, Paralegal, Court Registrar, Magistrate, High Court Judge, Court of Appeal Justice, Arbitrator, Mediator, Notary Public, Commissioner for Oaths, Company Secretary, Legal Aid Officer, Bailiff, Court Process Server, Probate Officer
**Courts:** Primary Court, District Court, Resident Magistrate Court, High Court (mainland), Court of Appeal, Land Division of High Court, Labour Division, Commercial Division (Dar es Salaam), Industrial Court, Small Claims Court, Kadhi Court (Zanzibar), Juvenile Court
**Legal Documents:** Title deed, right of occupancy, power of attorney, affidavit, plaint, written statement of defence, injunction, interim order, judgment, decree, execution order, letters of administration, grant of probate, retainer agreement, fee note, cause list, court summons, witness statement, arbitration award, mediation agreement, stamp duty receipt

---

## Kiswahili / Swahili Equivalents

### Malalamiko (Complaints)
- "Wakili wangu hakuja mahakamani na kesi yangu iliondolewa — sijui kilichotokea"
- "Nimempa wakili pesa lakini hafanyi kazi yoyote kwa miezi sita"
- "Kesi yangu imechukua miaka mitatu bila hukumu"
- "Wakili alifanya makosa ya kisheria na nimepoteza kesi"
- "Faili yangu imepotezwa ofisini mwa wakili"
- "Nilelipa ada lakini sijapewa risiti wala hati yoyote"
- "Wakili alinipa ushauri mbaya kuhusu ardhi yangu — sasa kuna wamiliki wawili"
- "Msajili wa mahakama anadai pesa za ziada kuliko ada rasmi"

### Mapendekezo (Suggestions)
- "Wakili wote wapewe mfumo wa kuwasiliana na wateja kwa wakati halisi"
- "Mahakama zifungue mfumo wa kielektroniki wa kuwasilisha maandishi"
- "Huduma ya msaada wa kisheria iongezwe wilayani"
- "Orodha ya mashauri ya mahakama iwe kwenye tovuti inayoweza kupigiwa"
- "Upatanisho lazima ufanyike kabla ya shauri la mahakama kwa mashauri ya biashara"

### Maswali (Inquiries)
- "Nifungue kesi mahakama gani kwa mgogoro wa ardhi?"
- "Gharama ya kufungua kesi ya madai ni ngapi?"
- "Naweza kuwakilisha nafsi yangu mahakamani bila wakili?"
- "Jinsi gani ya kupata msaada wa kisheria bila malipo?"
- "Wakili anaweza kuwakilisha pande zote mbili — hii ni halali?"
- "Jinsi ya kuripoti wakili anayedhulumu mteja kwa TLS?"

### Pongezi (Compliments)
- "Wakili wangu alifanya kazi nzuri sana — tulifanikiwa mahakamani"
- "Ninapongeza timu ya kisheria kwa usimamizi mzuri wa kesi yangu"
- "Msaada wa kisheria ulipatikana haraka na kwa ubora"
- "Wakili alinirudishia pesa zilizobaki bila kuomba — asante sana"

---

## Industry-Specific Escalation Triggers

1. Client reports imminent threat of imprisonment or detention and advocate is unreachable — same-day human review
2. Advocate alleged to have colluded with opposing counsel or judge — refer to Judicial Service Commission and PCCB
3. Criminal matter where client was convicted due to advocate's failure to appear or gross negligence — urgent review for retrial application
4. Forged court documents or false judgment being used in fraud against a client
5. Imminent property execution based on fraudulent ruling — urgent court application required
6. Client lost land or property due to forged power of attorney — advocate involved or negligent
7. Advocate misappropriated client funds from trust account — theft of client money; refer to Police and TLS
8. Child custody order not being enforced and child is at immediate risk of harm
9. Forced or coerced false witness statement induced by an officer of the court
10. Advocate threatening client to drop legitimate complaint to TLS
11. Judiciary official demanding bribe for case scheduling, certified copies, or execution orders — refer to PCCB
12. Foreign national detained without consular notification — Vienna Convention violation; refer to Ministry of Foreign Affairs
13. Client facing imminent criminal trial without legal aid representation — urgent Legal Aid Board referral

---

## Disambiguation Notes

- **Legal Services vs. Government Services**: Court registry, bailiff, and judge complaints belong to Legal Services (judiciary) when the complaint targets the judicial process; classify as Government Services if the complaint is about a government ministry or statutory body acting outside court proceedings.
- **Legal Services vs. Real Estate / Property**: Land title transfer complaints belong to Legal Services when an advocate's negligence or conveyancing process is the issue; classify as Real Estate when the complaint targets a developer, estate agent, or property management company.
- **Legal Services vs. Financial / Insurance**: A complaint about a legal dispute arising from a banking or insurance contract is classified by the primary industry (banking/insurance) unless the complaint specifically targets the advocate or legal process handling the claim.
- **ADR vs. Court Services**: Mediation and arbitration complaints are Legal Services; escalate to Government Services only if a statutory tribunal (Fair Competition Tribunal, Labour Court) is involved as a government body rather than a private dispute resolution provider.
- **Company Secretarial vs. Consultancy**: Company registration and secretarial services belong to Legal Services when provided by an advocate or law firm; classify under Business Consultancy when provided by a non-legal business advisory firm.
- **TLS conduct complaint vs. service quality complaint**: TLS Ethics Committee handles conduct breaches (dishonesty, fraud, conflict of interest). Service quality complaints (poor communication, delays) should first go to the firm's internal complaints process — if unresolved, they can then be referred to TLS.
