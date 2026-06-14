---
tags: [industry-kb, feedback-classification, field-collection]
---
# Insurance — Feedback Collection Fields & Standards

## Industry Identifiers

insurance, insurer, policy, premium, claim, underwriter, broker, agent, TIRA, Tanzania Insurance Regulatory Authority, life insurance, health insurance, motor insurance, third-party, comprehensive, NHIF, CHF, community health fund, reinsurance, microinsurance, funeral insurance, mobile insurance, property insurance, agricultural insurance, crop insurance, livestock insurance, fire insurance, marine insurance, travel insurance, group scheme, corporate cover, annuity, endowment, whole life, term life, cover note, loss adjuster, claims assessor, beneficiary, policyholder, deductible, excess, sum insured, exclusion clause, no-claims bonus, compulsory insurance, certificate of insurance, policy schedule, proposal form, claim form, police abstract, OB number, discharge voucher, beneficiary nomination, endorsement, bancassurance, NHIF Afya card, CHF card, bima ya mazishi, bima ya mazao, bima ya mifugo, Yellow Card, COMESA motor, compulsory third party, CTP

## Why Industry-Specific Fields Matter

A claim rejection in insurance requires fundamentally different data from a premium dispute or a policy misrepresentation — the policy number, claim reference, date of loss, insurer identity, agent or broker license number, and the specific exclusion clause invoked are all mandatory under IAIS ICP 19, TIRA/Insurance Act Section 122, NAIC Model Law 884, and ISO 10002:2018. Without these fields, the AI cannot distinguish a legitimate claim denial (where the exclusion was properly disclosed) from an unfair trade practice (where it was not), and cannot route the case to the TIRA Tanzania Insurance Ombudsman or TIRAMIS portal with the required documentation.

## Source Standards

- IAIS ICP 19 — Conduct of Business (adopted 2017, updated December 2024); formal complaint handling procedure, complaint records available to supervisors, analysis by frequency and nature
- Tanzania Insurance Act No. 10 of 2009, Section 122 — Tanzania Insurance Ombudsman establishment; TIRA supervisory mandate
- TIRA — Tanzania Insurance Regulatory Authority regulatory framework; TIRAMIS portal (tiramis.tira.go.tz)
- NAIC Model Law 884 — National Association of Insurance Commissioners; line of insurance, function, complaint reasons, disposition fields
- ISO 10002:2018 — Quality Management, Guidelines for Complaints Handling (unique reference, remedy sought, date of occurrence, outcome tracking)
- FCA Handbook DISP Annex 1 — General Insurance and Pure Protection product group (complaint cause, resolution timeline, upheld/not-upheld, redress)
- FCA Consumer Duty (2023) — documenting good consumer outcomes; vulnerable customer identification
- AFCA (Australian Financial Complaints Authority) — claim reference, third-party involvement, remediation standards (comparative best practice)
- Bank of Tanzania (Financial Consumer Protection) Regulations 2019 (GN No. 884) — for insurance products distributed by or linked to banks (bancassurance)
- NHIF regulatory framework (Tanzania) — National Health Insurance Fund Act; contribution records, card activation, claims processing

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL insurance complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complaint_reference_number | Nambari ya Malalamiko | Yes (system-generated) | ISO 10002:2018 unique identifier; IAIS ICP 19 (complaint records must be maintained); NAIC; enables TIRAMIS portal submission |
| complainant_full_name | Jina Kamili la Mlalamikaji | Yes | NAIC; ISO 10002:2018; IAIS ICP 19; links to authenticated policy record |
| complainant_phone | Nambari ya Simu | Yes | ISO 10002:2018; NAIC; required for callback and claim status updates |
| complainant_email | Barua Pepe | Recommended | ISO 10002:2018; AFCA; written communication of resolution |
| complainant_address | Anwani ya Mlalamikaji | Yes | ISO 10002:2018; NAIC; TIRA (complainant identification for Ombudsman referral) |
| policy_number | Nambari ya Sera | Yes | NAIC (mandatory — policy and claim numbers required); IAIS ICP 19 (policy identification); TIRA; FCA DISP; AFCA; without this the complaint cannot be matched to the policy record |
| policy_type | Aina ya Sera | Yes | NAIC (line of insurance classification); FCA DISP Annex 1 (product categories within General Insurance); IAIS ICP 19 (product categorisation for conduct analysis) |
| insurer_name | Jina la Kampuni ya Bima | Yes | NAIC; IAIS ICP 19; TIRA; mandatory for TIRAMIS referral |
| agent_or_broker_name | Jina la Wakala / Dalali | Yes (if agent/broker involved) | IAIS ICP 19 (intermediary involvement is a distinct conduct risk dimension); NAIC; TIRA (agent/broker regulation) |
| agent_or_broker_license_number | Nambari ya Leseni ya Wakala | Recommended | TIRA licensing; IAIS ICP 19; verifies whether intermediary is registered and licensed |
| issue_type | Aina ya Tatizo | Yes | NAIC complaint reason taxonomy; FCA DISP Annex 1 (complaint cause); IAIS ICP 19; determines routing and regulatory reporting category |
| complaint_description | Maelezo ya Malalamiko | Yes | ISO 10002:2018; IAIS ICP 19 narrative requirement; FCA DISP |
| date_of_loss_or_incident | Tarehe ya Hasara / Tukio | Yes | NAIC; AFCA; IAIS ICP 19; ISO 10002:2018 (date of occurrence mandatory); establishes policy validity at time of loss |
| date_complaint_received | Tarehe ya Kupokea Malalamiko | Yes (system) | ISO 10002:2018; IAIS ICP 19 (timely handling clock starts here); FCA DISP |
| date_first_raised_with_insurer | Tarehe ya Kuwasiliana Kwanza na Bima | Yes | IAIS ICP 19 (timely handling); TIRA complaint process; FCA DISP timeline; determines whether TIRA escalation is permissible |
| financial_loss_or_claim_amount | Kiasi cha Madai / Hasara ya Fedha | Yes | FCA DISP (redress amount); NAIC; IAIS ICP 19; required for Ombudsman jurisdiction threshold check |
| remedy_sought | Suluhisho Linalohitajika | Yes | ISO 10002:2018 Clause 8.3 (remedy sought must be recorded at intake) |
| supporting_documents_attached | Nyaraka za Ushahidi | Yes | ISO 10002:2018; NAIC; AFCA; affects resolution speed and Ombudsman eligibility |
| complainant_vulnerability_flag | Mlalamikaji Katika Hali Ngumu | Recommended | FCA Consumer Duty; IAIS ICP 19 (fair treatment of vulnerable consumers); triggers priority handling |

### Conditional Fields (collect based on issue type)

**If issue_type = claim_denial OR claim_underpayment OR claim_delay:**
- claim_reference_number (Nambari ya Madai) — NAIC mandatory; AFCA; IAIS ICP 19 (claims handling is primary ICP 19 risk area); links to claim file
- date_claim_submitted (Tarehe ya Kuwasilisha Madai) — NAIC; AFCA; IAIS ICP 19 timely handling
- denial_reason_given_by_insurer (Sababu ya Kukataa Madai Iliyotolewa na Bima) — NAIC complaint reason taxonomy; FCA DISP (specific cause); IAIS ICP 19
- exclusion_clause_cited (Kifungu cha Kutengwa Kilichotajwa) — IAIS ICP 19 (non-disclosure of exclusions is core conduct risk); FCA Consumer Duty
- was_exclusion_disclosed_at_sale (Je, Kutengwa Kulielezwa Wakati wa Kununua Sera?) — IAIS ICP 19 fair treatment; NAIC misrepresentation category; determines unfair trade practice flag
- loss_adjuster_report_available (Je, Ripoti ya Mpiga Kura wa Hasara Ipo?) — AFCA; NAIC; enables independent review
- settlement_amount_offered (Kiasi cha Fidia Kilichotolewa) — FCA DISP (redress tracking); NAIC; IAIS ICP 19

**If issue_type = motor_claim (claim_denial, claim_underpayment, loss_adjuster_dispute, third_party_liability):**
- vehicle_registration_number (Nambari ya Usajili wa Gari) — NAIC; TIRA (CTP levy tracking); links to policy and Motor Traffic records
- police_abstract_ob_number (Nambari ya Kumbukumbu ya Polisi / OB Number) — NAIC; TIRA; AFCA; required for accident claim processing
- accident_date (Tarehe ya Ajali) — NAIC; establishes coverage validity
- third_party_involved (Je, Upande wa Tatu Unahusika?) — NAIC (third-party complaints category); IAIS ICP 19; AFCA
- third_party_name_and_contact (Jina na Mawasiliano ya Upande wa Tatu) — NAIC; AFCA; required for liability processing
- third_party_insurer (Kampuni ya Bima ya Upande wa Tatu) — NAIC; third-party claim routing
- estimated_repair_cost (Gharama za Kukarabati Zilizokadiriwa) — FCA DISP; NAIC; loss adjuster dispute basis
- settlement_below_market_value (Je, Fidia ni Chini ya Thamani ya Soko?) — NAIC; AFCA; triggers independent valuation

**If issue_type = policy_misrepresentation OR non_disclosure_of_exclusions OR agent_misconduct:**
- agent_license_number (Nambari ya Leseni ya Wakala) — TIRA; IAIS ICP 19 intermediary conduct risk
- misrepresentation_type (Aina ya Uongo: bidhaa iliyouza / bei / mwisho / masharti) — IAIS ICP 19; NAIC; FCA DISP complaint cause
- was_proposal_form_accurate (Je, Fomu ya Ombi Ilikuwa Sahihi?) — IAIS ICP 19 (utmost good faith); NAIC
- evidence_of_misrepresentation (Ushahidi wa Uongo: maandishi / rekodi ya simu / ushahidi wa shahidi) — ISO 10002:2018; TIRA Ombudsman

**If issue_type = premium_dispute OR unauthorized_premium_deduction:**
- premium_payment_method (Njia ya Malipo ya Premium: simu / benki / wakala / moja kwa moja) — BoT (for bancassurance); NAIC
- disputed_premium_amount (Kiasi cha Premium Kinachoshindaniwa) — FCA DISP redress; NAIC
- payment_reference_or_receipt (Nambari ya Malipo / Risiti) — ISO 10002:2018; NAIC; proof of payment
- policy_period_covered (Kipindi cha Sera Kinachoshughulikiwa) — FCA DISP; NAIC; validates whether policy was active

**If issue_type = nhif_complaint OR chf_complaint:**
- nhif_membership_number (Nambari ya Uanachama wa NHIF) — NHIF regulations; links to contribution record
- employer_name (Jina la Mwajiri) — NHIF; contribution remittance tracking
- hospital_name (Jina la Hospitali) — NHIF accredited facility verification
- card_status_at_rejection (Hali ya Kadi Wakati wa Kukataliwa) — NHIF; establishes whether rejection was administrative or clinical
- contribution_months_paid (Miezi ya Michango Iliyolipwa) — NHIF eligibility verification

**If issue_type = life_insurance_death_claim:**
- deceased_name (Jina la Marehemu) — NAIC; IAIS ICP 19; claim record
- date_of_death (Tarehe ya Kifo) — NAIC; establishes claim validity
- death_certificate_submitted (Je, Cheti cha Kifo Kimewasilishwa?) — NAIC; IAIS ICP 19; AFCA
- beneficiary_name (Jina la Msaidizi) — NAIC; IAIS ICP 19
- beneficiary_relationship_to_deceased (Uhusiano wa Msaidizi na Marehemu) — NAIC; IAIS ICP 19
- is_beneficiary_minor (Je, Msaidizi ni Mtoto Mdogo?) — IAIS ICP 19 (vulnerable person); FCA Consumer Duty

**If complaint is a repeat / escalation:**
- previous_complaint_reference (Nambari ya Malalamiko ya Awali) — IAIS ICP 19 (pattern analysis); FCA DISP 1.3.3R
- previous_resolution_outcome (Matokeo ya Awali) — IAIS ICP 19; determines TIRA escalation eligibility
- tira_ombudsman_referral_requested (Je, Unataka Kuwasiliana na Kamishna wa Bima wa TIRA?) — TIRA / Insurance Act Sec. 122

### Issue Type Classification

- `claim_denial` — Kukataliwa kwa madai (bila sababu / bila maelezo)
- `claim_payment_delay` — Kuchelewa kwa malipo ya madai
- `claim_underpayment` — Kulipwa kiasi kidogo kuliko kinachostahili
- `policy_cancellation_dispute` — Mgawanyiko wa kufutwa kwa sera
- `premium_dispute` — Mgawanyiko wa premium (ziada / isiyoidhinishwa / isiyo sahihi)
- `policy_misrepresentation` — Udanganyifu wakati wa kuuza sera
- `agent_or_broker_misconduct` — Mwenendo mbaya wa wakala / dalali
- `non_disclosure_of_exclusions` — Kukosa kueleza masharti ya kutengwa
- `policy_renewal_dispute` — Mgawanyiko wa kuhuisha sera
- `policy_lapse_dispute` — Mgawanyiko wa kuisha kwa sera
- `customer_service_failure` — Kushindwa kwa huduma kwa wateja
- `policy_document_error` — Kosa la hati ya sera
- `motor_third_party_liability` — Dhima ya tatu ya gari
- `life_beneficiary_dispute` — Mgawanyiko wa msaidizi wa bima ya maisha
- `health_preauth_or_network_dispute` — Mgawanyiko wa ruhusa ya awali ya afya / mtandao
- `nhif_card_or_contribution_dispute` — Mgawanyiko wa kadi ya NHIF / michango
- `agricultural_or_livestock_claim` — Madai ya bima ya mazao / mifugo
- `motor_loss_adjuster_dispute` — Mgawanyiko na mpiga kura wa hasara ya gari
- `death_claim_dispute` — Mgawanyiko wa madai ya kifo
- `fake_cover_note_or_certificate` — Hati ya bima ya uongo
- `unauthorized_premium_deduction` — Kukata premium bila idhini
- `other` — Nyingine (na maelezo ya bure)

### Resolution Standards for This Industry

- **TIRA / Insurance Act Sec. 122**: Insurers must handle complaints through internal procedure before TIRA Ombudsman referral. TIRAMIS portal (tiramis.tira.go.tz) is the formal escalation channel. Consumer must first exhaust the insurer's internal complaints process.
- **IAIS ICP 19**: Insurers must handle complaints in a timely and fair manner. Records of complaints received must be maintained and analysed by frequency and nature. Complaint data must be available to supervisors. Timely handling and fair outcome are the two primary supervisory benchmarks.
- **NAIC Model Law 884** (comparative): Insurers must acknowledge complaints within 10 working days; provide substantive response within 45 days; maintain records of all complaints for 5 years.
- **FCA DISP** (comparative): Final response within 8 weeks; redress amount recorded; upheld/not-upheld status mandatory in biannual regulatory reporting.
- **ISO 10002:2018**: Investigation findings, decision, date of decision, compensation offered and paid, and closure date must all be recorded.
- **BoT GN 884 (bancassurance channel)**: When insurance is distributed through a bank, BoT complaint regulations apply alongside TIRA — unique reference number, 14-day resolution window, 5-year record retention.

### Escalation Triggers (field values requiring immediate action)

- `issue_type = life_insurance_death_claim` AND `is_beneficiary_minor = yes` → Priority escalation; assign dedicated case handler; TIRA Ombudsman referral if insurer non-responsive within 30 days
- `issue_type = claim_denial` AND `was_exclusion_disclosed_at_sale = no` → Unfair trade practice flag; TIRA complaint preparation; escalate to compliance team
- `issue_type = agent_or_broker_misconduct` AND `agent_collected_premium_and_absconded = yes` → Police referral immediately; TIRA agent licensing team notification; BoT if bancassurance channel involved
- `issue_type = nhif_card_or_contribution_dispute` AND `hospital_denied_emergency_treatment = yes` → Life-threatening emergency; immediate escalation to NHIF head office and hospital management
- `issue_type = fake_cover_note_or_certificate` → Police referral; TIRA and traffic authority (TANROADS/Police Traffic) notification; road safety risk
- `financial_loss_or_claim_amount > TZS 5,000,000` AND `claim_delay > 180 days` → Senior management escalation; TIRA formal complaint preparation
- `complainant_vulnerability_flag = yes` AND `issue_type = death_claim_dispute` → Vulnerable person protection; immediate priority queue; TIRA Ombudsman pre-notification
- `is_beneficiary_minor = yes` AND `claim_payment_delayed = yes` → Child protection escalation; welfare check
- `mobile_money_premium_still_deducting_after_cancellation = yes` → Immediate mobile money provider escalation; BoT consumer protection report; TIRA notification
- `issue_type = agricultural_or_livestock_claim` AND `loss_assessor_never_visited = yes` AND `affected_population = smallholder_farmers` → TIRA supervisory alert; escalate to agriculture ministry if declaration-linked

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| suggestion_reference_number | Nambari ya Pendekezo | Yes (system) | ISO 10002:2018 unique identifier for all feedback types |
| submitter_name | Jina la Mtoa Pendekezo | Optional | ISO 10002:2018; allow anonymous for candid input |
| submitter_contact | Mawasiliano ya Mtoa Pendekezo | Optional | ISO 10002:2018; for follow-up if suggestion is implemented |
| insurance_service_area | Eneo la Huduma ya Bima | Yes | NAIC classification; FCA DISP product taxonomy; routes to correct product or operations team |
| specific_product_or_policy_type | Bidhaa / Aina ya Sera Mahususi | Yes | FCA DISP product-level granularity; IAIS ICP 19 (product oversight and governance is a core ICP 19 requirement) |
| suggestion_description | Maelezo ya Pendekezo | Yes | ISO 10002:2018; the substance of the improvement |
| date_submitted | Tarehe ya Kuwasilisha | Yes | ISO 10002:2018 |
| submission_channel | Njia ya Kuwasilisha | Yes | BoT; CGAP multi-channel tracking |

### Industry-Specific Improvement Categories

- `claims_processing_speed` — Kasi ya kushughulikia madai
- `claims_communication_and_transparency` — Mawasiliano na uwazi wa madai
- `underwriting_and_policy_design` — Uandishi wa sera na muundo wa bidhaa
- `premium_payment_options` — Chaguzi za malipo ya premium
- `digital_app_or_ussd` — Programu ya simu ya bima / USSD
- `agent_or_broker_quality` — Ubora wa wakala / dalali
- `policy_document_clarity` — Uwazi wa hati ya sera (masharti, kutengwa)
- `renewal_process` — Mchakato wa kuhuisha sera
- `nhif_network_and_coverage` — Mtandao wa NHIF na mwambao wa huduma
- `chf_access_in_rural_areas` — Upatikanaji wa CHF vijijini
- `agricultural_insurance_design` — Muundo wa bima ya kilimo / mifugo
- `microinsurance_accessibility` — Upatikanaji wa bima ndogo kwa watu wenye kipato kidogo
- `customer_service_and_communication` — Huduma kwa wateja na mawasiliano
- `tira_transparency_and_regulation` — Uwazi wa TIRA na udhibiti

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| inquiry_reference_number | Nambari ya Swali | Yes (system) | ISO 10002:2018 |
| inquirer_name | Jina la Muulizaji | Yes | NAIC; IAIS ICP 19; links to customer record for accurate, policy-specific answer |
| policy_holder_verification | Uthibitisho wa Mmiliki wa Sera | Yes | KYC; TIRA; NAIC; prevents third-party disclosure of sensitive policy information |
| policy_number | Nambari ya Sera | Conditional | NAIC; TIRA; required for policy-specific or claim-specific inquiries |
| policy_type | Aina ya Sera | Yes | FCA DISP Annex 1; NAIC; routes to correct information source |
| inquiry_type | Aina ya Swali | Yes | NAIC; FCA DISP (complaint vs. inquiry distinction); AFCA |
| claim_reference_number | Nambari ya Madai | Conditional | NAIC; AFCA; required when inquiry relates to an existing claim |
| inquiry_description | Maelezo ya Swali | Yes | ISO 10002:2018 |
| date_of_inquiry | Tarehe ya Swali | Yes | ISO 10002:2018 |
| submission_channel | Njia ya Kuwasilisha | Yes | BoT; CGAP |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Additional Required Fields |
|-------------|---------------------------|
| `policy_status` | policy_number, insurer_name |
| `coverage_details` | policy_number, policy_type, specific_event_or_scenario |
| `premium_balance_or_due_date` | policy_number, payment_method |
| `claim_status` | claim_reference_number, date_claim_submitted |
| `claim_payment_timeline` | claim_reference_number, approval_date_if_known |
| `beneficiary_information` | policy_number, beneficiary_name (for verification) |
| `policy_renewal_terms` | policy_number, renewal_date |
| `exclusions_explanation` | policy_number, specific_scenario_or_event |
| `agent_contact_or_verification` | agent_name_or_code, insurer_name |
| `nhif_service_inquiry` | nhif_membership_number, specific_service_or_hospital |
| `how_to_file_tira_complaint` | insurer_name, nature_of_dispute |
| `agricultural_insurance_eligibility` | crop_type_or_livestock, farming_location, cooperative_membership |
| `free_look_period` | policy_type, date_policy_purchased |
| `no_claims_bonus` | policy_number, previous_claims_history |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| applause_reference_number | Nambari ya Sifa | Yes (system) | ISO 10002:2018 |
| submitter_name | Jina la Mtoa Sifa | Optional | ISO 10002:2018; allow anonymous |
| submitter_contact | Mawasiliano ya Mtoa Sifa | Optional | For staff recognition verification |
| agent_or_staff_commended | Jina la Wakala / Mtumishi Anayesifiwa | Yes | NAIC; IAIS ICP 19 (agent conduct monitoring — commendations are positive conduct data); enables staff recognition |
| insurer_name | Jina la Kampuni ya Bima | Yes | NAIC; IAIS ICP 19; institutional performance tracking |
| branch_or_office | Tawi / Ofisi | Yes | NAIC; IAIS ICP 19; location-specific performance evidence |
| policy_type_or_service_praised | Aina ya Sera / Huduma Iliyoheshimishwa | Yes | ISO 10002:2018 (product/service identification); IAIS ICP 19 (good conduct documentation) |
| specific_positive_outcome | Matokeo Mazuri Yaliyoelezwa | Yes | ISO 10002:2018; FCA Consumer Duty (evidence of good outcomes); IAIS ICP 19 |
| date_of_experience | Tarehe ya Uzoefu | Yes | ISO 10002:2018 |
| date_submitted | Tarehe ya Kuwasilisha | Yes | ISO 10002:2018 |

---

## AI Conversation Guidance for This Industry

- **Identify insurance type before collecting any other field**: Motor, life, health/NHIF, agricultural, and microinsurance complaints have completely different required fields. Ask "Ni aina gani ya bima — bima ya gari, maisha, afya, mazao, au nyingine?" as the very first branching question. This determines whether you need a policy number, claim reference, vehicle registration, NHIF membership number, or death certificate details.
- **Always ask for policy number and insurer name early**: Unlike banking (where account number may be unknown), insurance complainants almost always have a policy number or cover note number. Ask "Je, una nambari ya sera au nambari ya hati ya bima?" — this is the single most important field for routing and it is typically available. If not, ask for the insurer name and agent name together.
- **Handle claim denial complaints with structured precision**: When a customer says their claim was denied, collect in this order: (1) claim reference number, (2) date claim was submitted, (3) the reason the insurer gave for denial, (4) whether that exclusion was explained at the time of sale. This sequence is required by IAIS ICP 19 and NAIC and determines whether this is a legitimate denial or an unfair trade practice requiring TIRA escalation.
- **Treat agent misconduct disclosures seriously but without accusation**: If a customer says "the agent took my money and disappeared" or "the agent sold me the wrong policy," ask calmly: "Je, una nambari ya leseni ya wakala au jina lake kamili?" and "Je, una risiti au ushahidi wowote wa malipo?" without characterizing the agent as fraudulent in the conversation — that is for investigation to determine. Flag the case internally as high-priority.
- **NHIF and CHF require different context from private insurance**: For NHIF/CHF complaints, the key fields are membership number, employer name (for contribution verification), hospital name, and whether the card was rejected or the claim was denied post-treatment. Do not apply motor or life insurance field flows to NHIF complaints — route them through the NHIF-specific conditional field branch.
- **Do not advise TIRA escalation prematurely**: TIRA Ombudsman referral (TIRAMIS portal) is only available after the insurer's internal complaints process has been exhausted. If the customer has not yet contacted the insurer's complaints desk, guide them to do so first. Only suggest TIRA when the customer confirms the insurer gave a final response and they remain dissatisfied.

## Swahili Key Phrases for Field Collection

- **Insurance type**: "Ni aina gani ya bima unayozungumza — bima ya gari, maisha, afya, mazao, au nyingine?"
- **Policy number**: "Je, una nambari ya sera yako au nambari ya hati ya bima (cover note)?"
- **Insurer name**: "Kampuni yako ya bima inaitwa nini?"
- **Claim reference**: "Je, una nambari ya madai yako au risiti ya kuwasilisha madai?"
- **Date of loss**: "Tukio au hasara ilitokea lini hasa — tarehe gani?"
- **Denial reason**: "Kampuni ya bima ilisema nini hasa sababu ya kukataa madai yako?"
- **Exclusion disclosure**: "Sababu hiyo ya kukataa — je, ilielezwa kwako wakati ulinunua sera?"
- **Agent details**: "Jina la wakala wako wa bima ni nani? Je, ana nambari ya leseni?"
- **NHIF membership**: "Nambari yako ya uanachama wa NHIF ni nini?"
- **Remedy sought**: "Unataka tatizo hili lisuluhishwe vipi — kulipwa fidia, kuhuishwa sera, au kitu kingine?"
- **TIRA escalation**: "Je, umeshajaribu kuwasiliana na kampuni ya bima moja kwa moja? Ulipata jibu gani la mwisho?"
- **Police abstract**: "Kwa ajili ya madai ya gari — je, una nambari ya OB (kumbukumbu ya polisi) kutoka kituo cha polisi?"

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|-------------------|
| `issue_type` | claim_denial AND was_exclusion_disclosed_at_sale = no | Flag as potential unfair trade practice; prepare TIRA complaint packet; escalate to compliance |
| `issue_type` | life_insurance_death_claim AND is_beneficiary_minor = yes | Priority queue; vulnerable person handling protocol; TIRA Ombudsman pre-alert |
| `agent_collected_premium_and_absconded` | yes | Advise police report immediately; notify TIRA agent licensing department; flag for fraud investigation |
| `issue_type` | nhif_card_or_contribution_dispute AND hospital_denied_emergency_treatment = yes | Life-risk escalation; contact NHIF head office and hospital management within 1 hour |
| `issue_type` | fake_cover_note_or_certificate | Police referral; TIRA notification; TANROADS/Traffic Police alert (road safety risk) |
| `claim_delay_days` | ≥ 180 AND financial_loss_or_claim_amount ≥ TZS 5,000,000 | Senior management escalation; TIRA formal complaint preparation |
| `mobile_money_premium_still_deducting_after_cancellation` | yes | Escalate to mobile money operator; BoT consumer protection report; TIRA notification |
| `settlement_below_market_value` | yes (motor total loss) | Request independent vehicle valuation; escalate to TIRA if gap > 20% |
| `loss_assessor_never_visited` | yes AND issue_type = agricultural_or_livestock_claim | TIRA supervisory alert; agriculture ministry referral if disaster-declaration context |
| `tira_ombudsman_referral_requested` | yes | Confirm insurer internal process exhausted; prepare TIRAMIS portal submission package |
| `complainant_vulnerability_flag` | yes | Assign dedicated case handler; priority queue; follow IAIS ICP 19 vulnerable consumer guidelines |
| `previous_resolution_outcome` | unsatisfactory AND days_since_insurer_final_response ≥ 0 | Provide TIRA TIRAMIS portal link and guidance; generate complaint summary document |

---

## Complaint / Grievance Signals — Insurance (Examples)

### Claims Handling & Rejection
- My motor insurance claim was rejected but the accident was clearly not my fault and I have the police abstract
- The insurer took six months to assess my claim and then offered me far less than the repair cost
- I submitted my health insurance claim with all required documents and it has been pending for four months
- The insurance company rejected my claim citing an exclusion clause that was never explained to me when I bought the policy
- The life insurance company is refusing to pay the death benefit to my family despite a valid policy
- The crop insurance assessor never visited my farm before declaring my claim invalid

### Policy & Coverage Issues
- The agent sold me a comprehensive motor policy but the schedule shows it is actually third-party only
- I was never given a copy of my policy document even after paying premiums for six months
- The insurer changed the terms of my policy at renewal without informing me in writing
- My policy was cancelled without notice even though I had paid my premium on time
- The group health scheme my employer enrolled me in does not cover maternity and this was never disclosed

### Premium & Financial Issues
- My motor insurance premium was increased by 50% at renewal with no explanation
- I cancelled my policy within the free-look period but the insurer has not refunded my premium
- The insurer deducted premiums from my mobile money account after I cancelled the policy
- The insurance agent collected my cash premium but did not deposit it and now the insurer says my policy is unpaid

### Agent & Broker Conduct
- The insurance agent who sold me the policy has gone missing and I cannot contact the insurance company through them
- The broker received my premium payment but did not pass it on to the insurer — I found out when my claim was rejected
- The agent issued a fake cover note and disappeared with the premium payment
- The bank-assurance agent bundled insurance with my loan without adequately explaining the cost or my right to choose my own insurer

### NHIF / CHF / Medical Insurance
- My NHIF card was rejected at the hospital even though my employer has been deducting contributions
- My employer is deducting NHIF but I never received my membership card despite registering six months ago
- My family member was discharged early because the NHIF pre-authorisation was not obtained by the hospital in time
- I paid NHIF contributions for 20 years and on retirement I was told I no longer have coverage — this is unjust

---

## Suggestion / Advice Signals — Insurance (Examples)

- Insurance companies should allow customers to upload claim documents via a mobile app to speed up processing
- A dedicated claims tracking system via USSD or WhatsApp would help policyholders follow up without calling
- Insurance companies should offer smaller monthly premium options via mobile money to reach low-income customers
- Microinsurance products should have a simple one-page policy summary in Swahili with clear pictures
- Agricultural insurance should be index-based and linked to satellite rainfall data to remove the need for farm visits
- NHIF should expand its network of accredited facilities in rural areas and smaller towns
- All policy exclusions should be presented to the customer before purchase and require an explicit acknowledgement signature
- Insurance certificates should include a QR code that can be scanned to verify authenticity

---

## Inquiry / Question Signals — Insurance (Examples)

- What documents do I need to make a motor insurance claim after an accident?
- What is the difference between comprehensive and third-party motor insurance?
- How do I know if my insurance agent is licensed and registered with TIRA?
- What is the free-look period for a life insurance policy in Tanzania?
- Does my travel insurance cover me for medical evacuation from a safari in Serengeti?
- How do I activate my NHIF membership after my employer registers me?
- What is the process for NHIF reimbursement when I pay out of pocket at an accredited hospital?
- How does index-based crop insurance work and who qualifies?
- How do I file a complaint against my insurer with TIRA?

---

## Compliment / Applause Signals — Insurance (Examples)

- My motor claim was assessed within 48 hours and the settlement was fair and paid promptly — very impressed
- I was very pleased that the insurer paid my life claim to my family within 30 days of submitting the death certificate
- The insurance broker explained every exclusion in the policy clearly before I signed — very transparent and professional
- TIRA mediated my dispute with the insurer and I received a fair outcome within six weeks
- The crop insurance assessor visited my farm the next day after I reported the damage and the payout was fair
- The mobile microinsurance product is affordable and the activation via M-Pesa was instant — great innovation
- I am grateful for my broker who fought my rejected claim and got it reversed — excellent advocacy

---

## Key Entities & Roles

**Regulatory Bodies**
- TIRA (Tanzania Insurance Regulatory Authority) — supervisory mandate, TIRAMIS portal, Insurance Ombudsman
- NHIF (National Health Insurance Fund) — mandatory health cover for formal sector employees
- NSSF (National Social Security Fund) — intersects with group life schemes
- EWURA — for some utility-related indemnity covers

**Insurance Company Types**
- Life insurer, general (non-life) insurer, composite insurer, reinsurer, mutual society, captive insurer

**Intermediaries**
- Insurance broker (corporate), insurance agent (individual), bancassurance officer, MNO-based distribution (mobile insurance), microinsurance intermediary, village agent (wakala wa vijiji)

**Roles**
- Underwriter, actuary, claims assessor, loss adjuster (independent), surveyor, risk engineer, compliance officer, policyholder, insured, beneficiary, nominee, principal officer

**Policy Types**
- Third-party motor (TPM), comprehensive motor, marine cargo, fire & allied perils, burglary, money insurance, fidelity guarantee, professional indemnity (PI), public liability, employer's liability, group life, group medical, term life, whole life, endowment, education policy, annuity, travel insurance, critical illness, personal accident, agricultural/crop, livestock, funeral insurance (bima ya mazishi), microinsurance, mobile insurance

**Documents**
- Policy schedule, certificate of insurance, cover note, proposal form, claim form, loss adjuster report, police abstract (OB number), discharge voucher, beneficiary nomination form, no-claims certificate, endorsement, annual benefit statement, premium receipt, NHIF smart card (Afya card), CHF card

**Key Terms**
- Premium, excess/deductible, sum insured, indemnity, subrogation, utmost good faith (ubora wa imani), material fact, pre-existing condition, waiting period, free-look period, grace period, loading, exclusion clause, warranty, condition precedent, pro-rata premium, total loss, constructive total loss (CTL), third-party liability, own damage, no-claims bonus (NCB)

**Tanzania-Specific**
- Compulsory Third Party (CTP) motor levy (TIRA pool), Yellow Card (COMESA regional motor insurance), bima ya mazao (crop insurance), bima ya mifugo (livestock insurance), CHF card (community health), NHIF Afya card, M-Pesa/Airtel Money mobile premium collection

---

## Kiswahili / Swahili Equivalents

**Malalamiko (Complaints)**
- Kampuni ya bima ilikataa madai yangu ya gari ingawa ajali haikuwa kosa langu
- Nimekuwa nikingoja malipo ya madai yangu ya afya kwa miezi minne bila jibu
- Wakala wa bima alichukua malipo yangu ya premium lakini hakuipeleka kampuni ya bima
- Sera yangu ya bima ilifutwa bila onyo ingawa nilikuwa nimelipa kwa wakati
- Madai yangu ya mazao yalikataliwa ingawa uharibifu ulitokea baada ya sera kuanza
- Kadi yangu ya NHIF ilikataliwa hospitalini ingawa mwajiri wangu analipia kila mwezi
- Kampuni ya bima ilitoa fidia ya bei ya chini sana kwa gari langu lililoharibiwa
- Wakala alinithibitishia bima ya kina lakini sera iliyoletwa ni ya tatu peke yake
- Muda wa kuchelewa kwa kampuni ya bima kushughulikia madai ni mrefu sana — miezi sita
- Sera yangu ya maisha imeisha muda wake lakini kiasi cha kulipwa ni kidogo kuliko kilivyoahidiwa

**Mapendekezo (Suggestions)**
- Kampuni za bima zinapaswa kuruhusu upakiaji wa nyaraka za madai kupitia programu ya simu
- Bima ya mazao inapaswa kuwa ya aina ya index inayolipwa moja kwa moja bila ziara ya shamba
- Kadi za NHIF zinapaswa kuwa na mfumo wa uthibitishaji wa haraka hospitalini kwa SMS
- Kampuni za bima zinapaswa kutuma ukumbusho wa SMS siku 30 na 7 kabla ya tarehe ya malipo ya premium
- Wakala wa vijiji wafunzwe na wapate leseni ya kuuza bima ndogo kwa wakulima vijijini

**Maswali (Inquiries)**
- Ninahitaji nyaraka gani kufanya madai ya bima ya gari baada ya ajali?
- Ni muda gani wa kisheria wa kampuni ya bima kulipa madai yaliyoidhinishwa?
- Je, bima ya kina inatofautiana vipi na bima ya tatu nchini Tanzania?
- Ni jinsi gani ya kuweka malalamiko dhidi ya kampuni ya bima kwa TIRA?
- Kadi yangu ya NHIF haikufanya kazi hospitalini — ninafanya nini?
- Ni nini maana ya "ziada" (excess) katika sera ya bima ya gari?
- Je, bima ya safari inanifinika ikiwa nitaumia Safari Serengeti?
- Ninawezaje kujua kama wakala wangu wa bima ana leseni ya TIRA?

**Sifa / Shukrani (Compliments)**
- Kampuni ya bima ilishughulikia madai yangu ya gari kwa siku 48 na malipo yalikuwa ya haki
- Afisa wa madai alinieleza mchakato wote wa madai kwa uwazi na urafiki mkubwa
- Ninapongeza sana wakala wangu ambaye alifuatilia madai yangu yaliyokataliwa na kuyafanya yakubalike
- NHIF iliidhinisha madai yangu ya hospitali kwa wiki moja — huduma ya haraka na nzuri sana
- Bidhaa ya bima ya simu inapatikana kwa bei nafuu na uanzishaji wake ulikuwa wa papo hapo
- Kampuni ya bima ya mazao ilikuwa imetembelea shamba langu siku moja baada ya ripoti — haraka sana

---

## Industry-Specific Escalation Triggers

1. Insurance company denying a life insurance death benefit claim leaving a family without financial support — immediate TIRA Ombudsman referral
2. Agent confirmed to have collected premium payments and absconded without remitting to insurer — fraud; police and TIRA involvement required
3. Patient denied medical treatment at NHIF-accredited hospital due to disputed card status when genuine contributions are on record — health emergency
4. Policyholder in serious accident (injuries, fatalities) where third-party claims are denied or significantly delayed — victim welfare risk
5. Evidence of a fraudulent motor insurance certificate issued by an unlicensed agent — road safety risk; TIRA and police escalation
6. Claim rejection based on a non-disclosed exclusion clause — potential unfair trade practice requiring TIRA complaint
7. Insurer confirmed insolvent or delaying claims across a large number of policyholders — systemic regulatory issue; TIRA escalation required
8. Agricultural insurance company refusing to dispatch loss assessor after declared crop failure affecting smallholder farmers' livelihoods
9. Beneficiary of a life policy who is a minor or widow being deliberately delayed on death claim payment — vulnerable person protection
10. Mobile money premium deductions continuing after policy cancellation — consumer protection breach; BoT and TIRA dual notification
11. Hospital denying emergency treatment pending insurance pre-authorisation when patient's life is at risk — clinical emergency overrides insurance process
12. Bancassurance insurance bundled with a loan without customer knowledge or right-to-refuse disclosure — BoT and TIRA joint jurisdiction

---

## Disambiguation Notes

- Insurance feedback is distinguished from Healthcare feedback by the presence of insurance-specific terms (policy, premium, claim, excess, NHIF, cover note, beneficiary). A complaint about hospital billing rejection can be Healthcare or Insurance depending on whether the issue is clinical (Healthcare) or administrative insurance processing (Insurance).
- Motor insurance complaints may overlap with Transport/Automotive feedback. Distinguishing signals: terms like "claim," "loss adjuster," "comprehensive," "third party," and "excess" confirm Insurance classification. A complaint about a bad repair at a garage without insurance reference is Automotive.
- NHIF and CHF complaints are classified as Insurance when the issue is about coverage, card activation, contribution records, or claim reimbursement. If the issue is about quality of care delivered at the hospital itself, classify as Healthcare.
- Agricultural insurance complaints should be distinguished from general Agriculture/Farming feedback by the presence of policy, premium, claim, loss assessor, and sum insured keywords. Complaints about crop yields, soil, or inputs without mention of insurance belong to Agriculture.
- Life insurance endowment maturity complaints may overlap with Financial Services/Banking/Investment if the policyholder is treating the product as an investment vehicle. The presence of "policy," "premium," "insurer," and "beneficiary" confirms Insurance classification.
- Bancassurance (insurance sold through a bank) falls under both this KB and Finance/Banking KB. When the complaint is about the insurance product itself (coverage, claim, policy terms), use Insurance KB. When the complaint is about the bank channel that sold or deducted premiums without consent, use Finance/Banking KB, but cross-reference both.
