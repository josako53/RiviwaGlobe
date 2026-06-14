---
tags: [industry-kb, field-collection, feedback-fields]
---
# NGO / Development Organizations — Feedback Collection Fields & Standards

## Industry Identifiers

NGO, CBO, community based organization, development organization, humanitarian aid, advocacy group, faith-based organization, environmental NGO, women's rights, youth organization, health NGO, international NGO, INGO, donor funding, USAID, EU funded, DFID, GIZ, World Bank, UNHCR, UNICEF, WFP, Save the Children, Plan International, ActionAid, Oxfam, beneficiary, community consultation, NGO Act Tanzania, ANGOZA, registration certificate, project cycle, M&E, logframe, field officer, volunteer program, capacity building, grassroots, social protection, community health worker, gender-based violence, livelihoods, humanitarian response, accountability to affected populations (AAP), PSEA, safeguarding, food distribution, cash transfer, WASH, shelter, NFI, protection, ration card, beneficiary list, distribution point, targeting, registration, needs assessment, PDM, WFP-UNHCR, AAP Commitment, FCRM, Sphere, CHS, IOM, IASC, OCHA, wanufaika, usambazaji, orodha ya wanufaika, shirika lisilo la kiserikali, mradi, afisa wa mradi, usimamizi na tathmini

## Why Industry-Specific Fields Matter

NGO and humanitarian feedback involves a layered accountability structure — the beneficiary, the implementing partner, the donor, and the coordinating body (UN cluster, UNHCR, OCHA) all have distinct roles. A complaint about food distribution requires the project name, implementing organization, and aid type before it can be routed; a complaint about staff misconduct in a protection context requires a sensitivity classification before data is shared; and a complaint that involves sexual exploitation and abuse (SEA) requires an entirely different intake pathway with consent controls that generic fields cannot provide.

## Source Standards

- WFP-UNHCR Joint Feedback Mechanism SOP Template (April 2022) — the most operationally detailed mandatory field specification for humanitarian feedback mechanisms; mandatory fields confirmed from full document read
- UNHCR FCRM Minimum Standards (data.unhcr.org doc 79144) — minimum requirements for complaint and feedback intake
- UNHCR FCRM Guidance Syria Tool 4.4.3 and Jordan SOP Tool 4.4.1.2 — operational field-level detail
- OCHA Accountability to Affected Populations (AAP) Framework — coordination-level commitments and intake requirements
- IASC AAP Commitments 2017 (reliefweb.int) — five operational commitments governing complaint mechanisms, including SEA referral requirements
- Sphere Handbook 2018 CHS Commitment 5 — complaint mechanism design standards including confidentiality and protection requirements
- World Bank ESF ESS10 GRM Register — project-level fields for development project grievance mechanisms
- World Bank GRS Complaint Form (2021) — corporate-level complaint fields for World Bank-financed project impacts
- USAID AFP / SEE-AM Accountability and Feedback Plans — USAID-funded activity feedback field requirements
- Transparency International Complaint Mechanisms Reference Guide (2016) — corruption and misconduct field standards
- Tanzania NGO Act (ANGOZA regulatory framework) — registration and legal compliance fields
- IOM AAP Complaints and Feedback Mechanisms Toolkit (2020) — operational intake field guidance

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL NGO/development complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| project_name | Jina la Mradi | Yes | Identifies which specific project is implicated — one organization often runs multiple projects |
| implementing_organization | Shirika Linalotekeleza | Yes | Identifies the NGO/partner responsible — may differ from donor or coordinating body |
| donor_or_funding_agency | Mfadhili / Shirika la Ufadhili | Recommended | USAID, EU, GIZ, World Bank, UNHCR, WFP, UNICEF etc. — determines accountability framework that applies |
| aid_type | Aina ya Msaada | Yes | Food / Cash transfer / WASH / Shelter / NFI / Health / Education / Protection / Livelihoods / Other — determines issue sub-fields and relevant cluster |
| community_name_or_location | Jina la Kijiji / Kambi / Makazi | Yes | Mandatory per WFP-UNHCR SOP; routes complaint to the correct field team and geographic area |
| issue_type | Aina ya Tatizo | Yes | Exclusion/targeting / Aid quality / Distribution delay / Staff misconduct / Fraud / SEA / GBV / Information failure / Program not delivered / Safety concern / Other — see full classification below |
| date_of_incident | Tarehe ya Tukio | Yes | Establishes timeline; required for investigation and SLA tracking |
| description_of_what_happened | Maelezo ya Kilichotokea | Yes | Full narrative — what, who, where, when, impact |
| number_of_people_affected | Idadi ya Watu Walioathiriwa | Recommended | Individual / Household / Community — enables proportionality and impact assessment per IASC AAP |
| beneficiary_id_or_registration_number | Namba ya Usajili wa Mwanufaika | Recommended | Ration card, UNHCR case number, or program registration number — preferred but not mandatory per WFP-UNHCR SOP; enables fast case lookup |
| safety_concern_or_retaliation_risk | Wasiwasi wa Usalama | Yes | Yes/No — critical per WFP-UNHCR SOP and Sphere; if Yes, triggers confidentiality protocol and may affect whether name is recorded |
| sensitivity_level | Kiwango cha Usiri | Yes | Non-sensitive / Sensitive / Highly Sensitive — per WFP-UNHCR SOP categorization; determines response timeline and data handling |
| anonymous_submission | Wasilisho la Siri | Yes | Yes/No — per WFP-UNHCR SOP: "if the feedback mechanism user does not give consent, recorded anonymously"; affects response pathway |
| consent_to_data_collection | Idhini ya Kukusanya Taarifa | Yes | Mandatory per WFP-UNHCR SOP step — must be confirmed before recording personal data |
| consent_to_referral | Idhini ya Kupelekwa kwa Shirika Lingine | Yes | Mandatory per WFP-UNHCR SOP — whether complaint can be shared with implementing partner, UNHCR, or cluster lead |
| submitter_name | Jina la Mlalamikaji | Conditional | Not mandatory if anonymous; ask after confirming anonymity preference |
| submitter_age | Umri wa Mlalamikaji | Yes | Mandatory per WFP-UNHCR SOP for demographic disaggregation regardless of anonymity |
| submitter_gender | Jinsia ya Mlalamikaji | Yes | Mandatory per WFP-UNHCR SOP for demographic disaggregation regardless of anonymity |
| submitter_contact | Mawasiliano ya Mlalamikaji | Conditional | Phone/WhatsApp — required for response unless anonymous; "not mandatory if anonymous" per WFP-UNHCR SOP |
| preferred_response_channel | Njia Inayopendelewa ya Majibu | Yes | In-person / Phone / WhatsApp / SMS / Community focal point / Other — per WFP-UNHCR SOP and IASC AAP |
| evidence_available | Ushahidi Unaopatikana | Recommended | Distribution receipt / Photograph / Witness names / Written record / None |
| prior_escalation_to_ngo | Imefikishwa kwa Shirika Hapo Awali? | Yes | Yes/No — per IASC AAP and World Bank GRS; if Yes, collect what happened and what response was received |
| desired_outcome | Matokeo Yanayotarajiwa | Recommended | What the beneficiary wants: inclusion in program / Replacement of poor-quality aid / Removal of corrupt staff / Public accountability / Other |

### Conditional Fields (collect based on issue type)

**If issue_type = SEA (Sexual Exploitation and Abuse) or GBV:**
- This complaint receives Highly Sensitive classification immediately
- Do NOT collect identifying details about the alleged perpetrator in the initial intake if it could put the survivor at risk
- sea_gbv_survivor_consent — explicit consent to referral to GBV/PSEA focal point (Yes/No)
- incident_timeframe — recent (within 30 days) / past (more than 30 days ago)
- immediate_safety_needs — Yes/No; if Yes, what support is needed now (shelter, medical, legal)
- preferred_referral_agency — UNHCR / IRC / government social welfare / police / other
- Do not ask: perpetrator's name, graphic details, survivor's relationship history — collect only what is needed for safe referral

**If issue_type = Fraud or Corruption:**
- corrupt_actor_description — role/title of the person (field officer, village leader, distribution officer, driver); first name if known
- corruption_type — Bribe demand for aid / Ghost beneficiary registration / Inflated beneficiary numbers / Aid diverted / Money collected for free services / Staff involved in diversion
- amount_or_value — money or aid diverted or demanded
- evidence_available — Transaction record / Signed receipt / Witness testimony / Photos / None
- has_whistleblower_concern — Yes/No — if Yes, maximum anonymity protocol applies

**If issue_type = Aid Quality / Not Received:**
- distribution_date — date of the distribution event
- distribution_point — specific location (village name, camp block, distribution site name)
- item_type_and_quantity_expected — what the beneficiary was supposed to receive
- item_type_and_quantity_received — what was actually received or if nothing
- quality_issue_description — spoiled / expired / insufficient / wrong item / damaged — be specific

**If issue_type = Exclusion / Targeting:**
- registration_date_attempted — when the person tried to register
- reason_given_for_exclusion — what reason was provided, if any
- self_assessed_vulnerability — vulnerability factors that should qualify the person: female-headed household / elderly / disabled / refugee / IDP / malnourished child / chronically ill / Other
- targeting_criteria_communicated — Yes/No — were the selection criteria publicly explained to the community

**If issue_type = Program Not Delivered / Early Termination:**
- promised_activities — what activities were committed during community consultation
- delivered_activities — what was actually implemented
- project_termination_notified — Yes/No — was the community officially notified before project ended
- exit_strategy_communicated — Yes/No

**If complaint involves legal registration issues (NGO Act compliance):**
- organization_registration_status — Registered / Unregistered / Expired certificate / Operating under different name
- angoza_registration_number — if known
- regulatory_violation_type — Unregistered operation / Unsubmitted annual report / Work permit violations / Name mismatch / Unauthorized fundraising

### Issue Type Classification

Per WFP-UNHCR SOP category structure with Riviwa extensions:

| Code | Issue Type | WFP-UNHCR Sensitivity | Response SLA |
|------|------------|----------------------|--------------|
| NGO-01 | Exclusion from targeting or beneficiary list without valid reason | Non-sensitive | 5 working days |
| NGO-02 | Aid not received — absent from distribution despite being registered | Non-sensitive | 5 working days |
| NGO-03 | Insufficient quantity — aid received but below entitlement | Non-sensitive | 5 working days |
| NGO-04 | Poor quality aid — spoiled, expired, damaged, or incorrect item | Non-sensitive | 5 working days |
| NGO-05 | Distribution delay — not distributed on schedule with no notice | Non-sensitive | 5 working days |
| NGO-06 | Transfer modality issue — cash transfer not received, wrong amount, mobile money failure | Non-sensitive | 5 working days |
| NGO-07 | Staff misconduct — rude, abusive, disrespectful, or negligent conduct | Sensitive | 3 working days |
| NGO-08 | Fraud or corruption — bribe demanded for aid, ghost beneficiaries, diversion | Sensitive | 3 working days |
| NGO-09 | Information not provided — no communication about program, eligibility, schedule | Non-sensitive | 5 working days |
| NGO-10 | Program not delivered or terminated without notice | Non-sensitive | 5 working days |
| NGO-11 | Accountability failure — no complaint mechanism available, reports falsified | Sensitive | 3 working days |
| NGO-12 | GBV allegation — gender-based violence by or involving project actors | Highly Sensitive | 24 hours |
| NGO-13 | SEA allegation — sexual exploitation or abuse by staff or volunteer | Highly Sensitive | 24 hours |
| NGO-14 | Child safeguarding — abuse, exploitation, or neglect of child beneficiary | Highly Sensitive | 24 hours |
| NGO-15 | Safety or security concern — threat to life of beneficiary linked to project | Highly Sensitive | 24 hours |
| NGO-16 | Legal compliance — NGO operating unregistered, permit violations, name mismatch | Sensitive | 3 working days |
| NGO-17 | Beneficiary death — death of beneficiary linked to program failure | Highly Sensitive | Immediate |
| NGO-18 | Refugee or IDP rights violation — discrimination, access denial | Sensitive | 3 working days |
| NGO-19 | Other | Non-sensitive | 5 working days |

### Resolution Standards for This Industry

Per WFP-UNHCR Joint SOP (2022), Sphere CHS Commitment 5, and IASC AAP Commitments:

- **General feedback / No response required**: Logged and closed; no SLA
- **Information request**: Response within **5 working days**
- **Non-sensitive complaint**: Resolution or substantive update within **5 working days**
- **Sensitive complaint** (fraud, staff misconduct, security): Substantive response within **3 working days**
- **Highly sensitive complaint** (SEA, ongoing GBV, human trafficking, life-threatening safety): Response initiated within **24 hours**; immediate referral to specialist focal point
- **Complaint due to urgent need** (food emergency, shelter need): Response within **24 hours**
- All complainants must be informed of the outcome unless anonymous
- Partner organization must receive complaint within defined escalation SLA
- PSEA focal point must be notified of any SEA allegation within 24 hours regardless of whether the allegation is confirmed
- World Bank GRS: complaints escalated to corporate level must demonstrate project-level GRM has been exhausted first

### Escalation Triggers (field values requiring immediate escalation)

- `issue_type = NGO-13` (SEA) → Immediate PSEA focal point notification; separate SEA intake pathway; no standard complaint routing
- `issue_type = NGO-12` (GBV ongoing) → Immediate GBV specialist referral; safety plan required before data sharing
- `issue_type = NGO-14` (Child safeguarding) → Immediate child protection escalation; notify UNICEF cluster lead and Ministry of Social Welfare
- `issue_type = NGO-17` (Beneficiary death) → Immediate escalation to implementing organization leadership and donor; mortality review required
- `issue_type = NGO-15` (Safety / life threat) → Emergency response within 24 hours; coordinate with security cluster if relevant
- `safety_concern_or_retaliation_risk = Yes` → Maximum anonymity protocol; do not share identity with implementing partner without explicit consent
- `sensitivity_level = Highly Sensitive` → Restrict data access; do not route through standard complaint system
- `issue_type = NGO-08` (Fraud) + `has_whistleblower_concern = Yes` → Anonymize immediately; route to donor anti-corruption focal point; do not involve implementing partner
- `issue_type = NGO-01` (Exclusion) + `self_assessed_vulnerability` includes disabled / malnourished child / elderly → Priority non-sensitive; fast-track targeting review
- Complaint involves World Bank-financed project and project-level GRM has been exhausted → Eligible for World Bank GRS corporate complaint; advise on GRS process
- Aid confirmed as expired, contaminated, or causing illness → Emergency health referral; notify relevant health cluster and implementing partner simultaneously

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| project_name | Jina la Mradi | Yes | Routes suggestion to the relevant program team |
| implementing_organization | Shirika Linalotekeleza | Yes | Identifies the organization that can action the suggestion |
| activity_or_service_to_improve | Shughuli / Huduma ya Kuboresha | Yes | Pinpoints what needs to change within the program |
| improvement_category | Aina ya Uboreshaji | Yes | Beneficiary engagement / Aid quality / Distribution system / Staff conduct / Accountability / Technology / Exit strategy / Other |
| affected_community_group | Kundi la Jamii Linaoathiriwa | Recommended | Women / Youth / Elderly / PWD / Host community / Refugees / IDPs / Other — for intersectional targeting |
| proposed_improvement_description | Maelezo ya Uboreshaji Unaopendekezwa | Yes | Full description of the suggestion |
| submitter_age | Umri | Recommended | WFP-UNHCR SOP: age recommended for all submissions for disaggregation |
| submitter_gender | Jinsia | Recommended | WFP-UNHCR SOP: gender recommended for all submissions for disaggregation |
| submitter_contact | Mawasiliano | Optional | For follow-up; not required |

### Industry-Specific Improvement Categories

- **Beneficiary accountability**: Public posting of beneficiary lists, transparent selection criteria, community-led verification
- **Complaint mechanism access**: Suggestion boxes in all villages, toll-free hotlines, SMS feedback channels, anonymous reporting
- **Distribution system**: Advance schedule communication, home visits for mobility-impaired beneficiaries, distribution point proximity
- **Aid quality assurance**: Pre-distribution inspection, expiry date checks, quantity verification before distribution
- **Program design**: Community inclusion in design and review, exit strategy planning from project start, handover to government
- **Staff and safeguarding**: Annual code of conduct training, PSEA policy posting, female staff for GBV-sensitive programs
- **Transparency and reporting**: Simplified Swahili project reports for community distribution, community audit mechanisms, published budgets
- **Technology**: SMS feedback, KoboToolbox or ODK for data collection, digital beneficiary IDs to prevent duplication

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| project_name | Jina la Mradi | Yes | Routes inquiry to correct program team |
| implementing_organization | Shirika Linalotekeleza | Yes | Identifies who can answer the question |
| aid_type_or_service | Aina ya Msaada au Huduma | Yes | Determines which program officer or cluster can respond |
| specific_question | Swali Maalum | Yes | The exact information being requested |
| beneficiary_id_or_registration_number | Namba ya Usajili | Conditional | Required for status inquiries about a specific beneficiary's enrollment or entitlement |
| preferred_response_channel | Njia Inayopendelewa ya Majibu | Yes | In-person / Phone / WhatsApp / SMS / Community focal point |
| submitter_contact | Mawasiliano | Conditional | Required for response unless the inquiry is general/public information |

### Common Inquiry Types & Required Data Per Type

**Eligibility and registration inquiry:**
- implementing_organization + project_name + aid_type_or_service + specific_question (eligibility criteria, registration dates, required documents, appeals process)

**Program schedule inquiry (next distribution, next training):**
- implementing_organization + project_name + community_name_or_location + specific_question — provide schedule if in KB

**Status of individual enrollment or entitlement:**
- implementing_organization + project_name + beneficiary_id_or_registration_number + submitter_full_name + specific_question

**Complaint process inquiry:**
- implementing_organization — provide FCRM contact details, complaint channel options, anonymity options, response timeline

**Funding and duration inquiry:**
- project_name + implementing_organization + specific_question (project end date, donor identity, extension plans, handover plans)

**Organization registration and legal status:**
- implementing_organization + specific_question — verify ANGOZA registration or direct to ANGOZA verification portal

**Volunteer and employment inquiry:**
- implementing_organization + specific_question (qualifications, recruitment process, volunteer insurance, paid positions)

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| project_name | Jina la Mradi | Yes | Routes compliment to the relevant program and donor for recognition |
| implementing_organization | Shirika Linalotekeleza | Yes | Identifies the organization to receive the recognition |
| specific_staff_or_team | Afisa au Timu Maalum | Recommended | Individual or team recognition; enables performance acknowledgment |
| service_or_interaction_that_worked | Huduma / Mwingiliano Uliofanya Vizuri | Yes | Documents what worked — feeds program quality evidence and donor reporting |
| date_of_positive_experience | Tarehe ya Uzoefu Mzuri | Recommended | Correlates with program activities and staff assignments |
| impact_on_submitter | Athari kwa Mlalamikaji / Mshiriki | Recommended | How the program or interaction improved the person's situation — powerful for program evidence |
| submitter_age | Umri | Recommended | WFP-UNHCR SOP: age recommended for demographic disaggregation |
| submitter_gender | Jinsia | Recommended | WFP-UNHCR SOP: gender recommended for demographic disaggregation |
| submitter_name | Jina | Optional | Not required; accept anonymous applause |

---

## AI Conversation Guidance for This Industry

- **Establish the organization and project before all else.** One community may be served by five NGOs simultaneously. The minimum viable routing information is: which organization and which project. Ask: "Unazungumza kuhusu shirika gani — na ni mradi gani hasa?" before collecting any other details. Without this, no routing is possible.
- **Collect age and gender even for sensitive or anonymous submissions.** Per WFP-UNHCR SOP, age and gender are mandatory demographic fields for all feedback regardless of whether the person is anonymous or identified. Frame naturally: "Ili tuweze kuelewa hali ya watu wanaotoa maoni, ungependa kuniambia una umri wa miaka mingapi na jinsia yako?" This should be a standard question for all NGO feedback.
- **Always ask about safety before collecting identity information.** Before asking for the person's name, ask: "Je, una wasiwasi wowote wa usalama wako kwa kutoa malalamiko haya?" If yes, apply maximum anonymity — do not ask for name, contact, or any identifying information; record only age, gender, location, and issue. Inform the person of what happens with their complaint.
- **Immediately elevate SEA and GBV to a separate pathway.** If any language suggesting sexual exploitation, abuse, or gender-based violence appears (whether explicit or indirect), stop the standard flow and switch to the protection pathway: "Asante kwa kuniambia hili. Hii ni hali nyeti sana na tunataka kukusaidia kwa njia salama. Je, unakubali taarifa yako ipelekwe kwa afisa wa ulinzi ambaye ana mafunzo ya kuhangaika na hali kama hii?" Do not collect details about the incident itself in this intake.
- **Confirm consent to referral before sharing any data with the implementing partner.** This is a mandatory WFP-UNHCR SOP step. Ask: "Je, unakubali malalamiko yako ipelekwe kwa [implementing organization name] ili washughulikie tatizo hili?" For sensitive complaints (fraud, staff misconduct), always ask: "Je, unakubali hili?" before any referral. For SEA/GBV, separate consent is required.
- **For fraud and corruption complaints, offer maximum whistleblower protection proactively.** Say: "Unaweza kutoa taarifa hii kwa siri kabisa — jina lako halitashirikiwa na shirika unalodai. Je, ungependa malalamiko yako yashughulikiwe kwa njia ya siri?" This increases the likelihood of receiving actionable information about diversion and corruption.

## Swahili Key Phrases for Field Collection

| Field Being Collected | Swahili Phrase |
|----------------------|----------------|
| project_name + implementing_organization | "Unazungumza kuhusu shirika gani na mradi gani hasa unaofanya kazi katika eneo lako?" |
| community_name_or_location | "Unakaa wapi hasa — jina la kijiji, kambi, au mji mdogo?" |
| submitter_age | "Una umri wa miaka mingapi? Hii inatusaidia kuelewa hali ya watu wanaotoa maoni." |
| submitter_gender | "Unaweza kuniambia jinsia yako — mwanaume, mwanamke, au nyingine?" |
| safety_concern | "Kabla sijaendelea — je, una wasiwasi wowote wa usalama wako kwa kutoa malalamiko haya?" |
| consent_to_data_collection | "Je, unakubali tutumie taarifa unazotoa ili kushughulikia malalamiko yako?" |
| consent_to_referral | "Je, unakubali taarifa yako ipelekwe kwa [jina la shirika] ili wachukue hatua?" |
| anonymous_submission | "Je, ungependa malalamiko yako yashughulikiwe kwa siri bila kujulikana, au unaridhika kutaja jina lako?" |
| beneficiary_id | "Je, una namba yoyote ya usajili au kadi yoyote uliyopewa na mradi au shirika hilo?" |
| sensitivity (SEA/GBV) | "Hii ni hali nyeti sana. Tutashughulikia kwa siri na hadhi kamili. Je, unakubali ipelekwe kwa afisa wa ulinzi?" |
| prior_escalation | "Je, umeshawasiliana na shirika hilo moja kwa moja kuhusu tatizo hili? Walikusema nini?" |
| evidence_available | "Je, una ushahidi wowote — kama risiti ya usambazaji, picha, au mashahidi wanaoweza kuthibitisha?" |
| fraud complaint (whistleblower) | "Unaweza kutoa taarifa hii kwa siri kabisa — jina lako halitashirikiwa. Je, ungependa hilo?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | NGO-13 (SEA) | Immediately switch to PSEA pathway; notify PSEA focal point within 24 hours; do not route through standard complaint flow |
| issue_type | NGO-12 (GBV ongoing) | Immediate GBV specialist referral; assess immediate safety needs; do not collect graphic details |
| issue_type | NGO-14 (Child safeguarding) | Immediate child protection escalation; UNICEF + Ministry of Social Welfare notification within 24 hours |
| issue_type | NGO-17 (Beneficiary death) | Escalate immediately to implementing org leadership and donor; trigger mortality review protocol |
| sensitivity_level | Highly Sensitive | Restrict complaint data to designated protection officers only; apply strict access controls |
| safety_concern_or_retaliation_risk | Yes | Apply maximum anonymity; do not share identity with implementing partner; close loop through community focal point only |
| has_whistleblower_concern | Yes | Anonymize immediately; route to donor anti-corruption focal point; bypass implementing partner |
| consent_to_referral | No | Do not share details with implementing partner; record and aggregate for pattern analysis only |
| issue_type | NGO-08 (Fraud) + evidence provided | Route to donor accountability focal point (USAID OIG / EU OLAF / World Bank INT as applicable); document evidence chain |
| issue_type | NGO-01 (Exclusion) + self_assessed_vulnerability = disabled / elderly / malnourished child | Priority fast-track; recommend home visit for registration within 5 days |
| aid_type | Food / Medical supplies + quality_issue = expired / contaminated | Emergency health referral; notify health cluster and implementing partner simultaneously |
| prior_escalation_to_ngo | Yes + prior_escalation_outcome = no response | Bypass implementing partner; escalate directly to donor or UN cluster lead |
| number_of_people_affected | 50+ (community-level) | Treat as systemic issue; tag for cluster-level reporting; not resolved at individual case level |
| issue_type | NGO-16 (Legal compliance) + organization_registration_status = Unregistered | Refer to ANGOZA for verification; notify PO-RALG if operating without certificate |
| donor_or_funding_agency | World Bank + project-level GRM exhausted | Advise on World Bank GRS corporate complaint pathway; provide GRS contact (grievances@worldbank.org) |
| issue_type | NGO-06 (Cash transfer failure) | Route to both implementing organization and mobile money provider; collect transaction reference number |
| anonymous_submission | Yes | Process complaint; remove all personal identifiers; no direct response; close loop through community feedback session |

---

*Framework sources: WFP-UNHCR Joint Feedback Mechanism SOP Template (wfp-unhcr-hub.org, April 2022); UNHCR FCRM Minimum Standards (data.unhcr.org doc 79144); UNHCR FCRM Syria Tool 4.4.3 and Jordan SOP Tool 4.4.1.2; OCHA AAP Framework (unocha.org); IASC AAP Commitments 2017 (reliefweb.int); Sphere Handbook 2018 CHS Commitment 5; World Bank GRS Complaint Form (thedocs.worldbank.org, 2021); World Bank ESF ESS10 Guidance Note (2018); USAID SEE-AM AFP Guidance (usaid.gov); Transparency International Complaint Mechanisms Reference Guide (2016); IOM Complaints and Feedback Mechanisms Toolkit (2020); Tanzania NGO Act / ANGOZA regulatory framework.*
