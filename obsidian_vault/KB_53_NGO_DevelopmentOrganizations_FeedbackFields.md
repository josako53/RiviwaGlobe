---
tags: [industry-kb, field-standards, feedback-fields, ngo, development-organizations]
---
# NGO / Development Organizations — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: NGO, non-governmental organization, shirika lisilo la kiserikali, CBO, community-based organization, shirika la jamii, charity, taasisi ya hisani, foundation, mfuko, development organization, shirika la maendeleo, UNHCR, WFP, UNICEF, WHO, World Bank, donor, mfadhili, beneficiary, mnufaika, project, mradi, program, programu, aid, msaada, humanitarian, ubinadamu, microfinance, VICOBA, SACCOS, social protection, ulinzi wa jamii, empowerment, uwezeshaji, capacity building, ujenzi wa uwezo, M&E, monitoring and evaluation, ufuatiliaji na tathmini, GRM, grievance redress mechanism, community mobilization, community outreach, field officer, afisa wa uwanjani, community development, maendeleo ya jamii, NGO coordinator, project officer, safeguarding, ulinzi wa watoto, PSEA, sexual exploitation and abuse

## Why Industry-Specific Fields Matter

NGO complaints range from beneficiary selection disputes (requiring program name, beneficiary list reference, selection criteria), sexual exploitation by staff (requiring safeguarding escalation path), aid diversion (requiring project reference and donor reference), to poor service delivery (requiring project activity reference). NGOs operating in Tanzania must comply with NGO Act Cap. 56 registration requirements and donor safeguarding standards. Without NGO-specific fields, the AI cannot distinguish routine service feedback from a serious safeguarding incident that requires immediate escalation to the donor's safeguarding hotline and PCCB.

## Source Standards

- Tanzania Non-Governmental Organizations Act, Cap. 56 (NGO Act) and NGO Regulations 2004
- Tanzania NGO Coordination Board (NGO Board) — complaint mechanisms
- IASC Accountability to Affected Populations (AAP) Framework 2021
- CHS Alliance Core Humanitarian Standard (CHS) 2014 — commitments 5 and 8 (feedback and complaints)
- SPHERE Humanitarian Standards 2018 — accountability and complaints
- Inter-Agency Standing Committee PSEA guidelines — Prevention of Sexual Exploitation and Abuse
- UN Secretary-General's Bulletin ST/SGB/2003/13 — Special measures for protection from sexual exploitation and abuse
- Oxfam, IRC, Save the Children — NGO safeguarding policies (reference standards)
- Tanzania Social Welfare Act — for welfare-related NGO activities
- ISO 10002:2018 — complaints handling
- FCDO, USAID, EU — donor safeguarding and GRM requirements

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL NGO complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji (hiari kwa usalama) | Optional | CHS Commitment 8 allows anonymous feedback; safeguarding requires confidentiality |
| complainant_phone | Nambari ya simu (hiari) | Optional | Anonymous option must be available per CHS and IASC AAP |
| ngo_name | Jina la shirika linalolalamikiwa | Yes | Routes to correct organization and regulatory body |
| project_or_program_name | Jina la mradi / programu | Yes | Enables project-level investigation; donor accountability |
| project_location | Mahali pa mradi (wilaya / kijiji) | Yes | Geographic routing for field investigation |
| beneficiary_id | Nambari ya mnufaika (kama ipo) | Conditional | For beneficiary-specific complaints; some programs issue beneficiary IDs |
| issue_type | Aina ya tatizo | Yes | CHS complaint taxonomy; determines urgency and escalation path |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; CHS requires documented complaints |
| date_of_incident | Tarehe ya tukio | Yes | For investigation and donor reporting |
| staff_involved | Jina la mfanyakazi wa NGO aliyehusika | Conditional | For staff misconduct and safeguarding complaints |
| witness_available | Je, kuna shahidi? | Conditional | Required for serious misconduct investigations |
| desired_outcome | Matokeo unayotaka | Yes | CHS Commitment 8 requires response to complainants |
| consent_to_share | Ridhaa ya kushiriki taarifa | Yes | Critical for safeguarding — complainant controls information sharing |

### CRITICAL: Safeguarding Fields (PSEA — Sexual Exploitation and Abuse)

**If any indication of sexual exploitation, abuse, or harassment by NGO staff:**
- **IMMEDIATELY flag as safeguarding — DO NOT continue standard collection**
- `safeguarding_incident_type` — Aina ya tukio la ulinzi: SEA (Sexual Exploitation/Abuse) / Child Protection / Staff Harassment / Fraud
- `victim_age_group` — Kundi la umri wa mwathirika: Child under 18 / Adult — determines reporting requirements (child = mandatory immediate report)
- `incident_location` — Mahali pa tukio
- `immediate_safety_concern` — Je, mwathirika yuko salama sasa hivi?
- `referred_to_support_services` — Je, msaada wa kisaikolojia au kimatibabu umependekezwa?
- **All safeguarding incidents escalate immediately to NGO safeguarding focal point AND donor organization**

### Conditional Fields (collect based on issue type)

**If issue_type = Beneficiary Selection Dispute:**
Also collect:
- `selection_criteria_applied` — Vigezo vya kuchagua wanavyodai vilitumika: For verification against program criteria
- `complainant_eligibility_basis` — Sababu mlalamikaji anajiamini anastahili: Cross-reference with program criteria
- `selection_committee_members` — Wanachama wa kamati ya uchaguzi: For accountability
- `appeal_mechanism_available` — Je, mchakato wa rufaa upo kwenye programu?

**If issue_type = Aid Diversion / Corruption:**
Also collect:
- `aid_type_diverted` — Aina ya msaada uliopotezwa: Cash / Food / NFIs / Medicine / Other
- `amount_or_quantity` — Kiasi au wingi uliopotezwa
- `transaction_evidence` — Ushahidi wa muamala: Receipts, photos, witness accounts
- `donor_reference` — Nambari ya mradi wa mfadhili: For donor reporting (USAID, FCDO, EU grant number)

**If issue_type = Poor Quality Program / Delivery Failure:**
Also collect:
- `activity_type` — Aina ya shughuli: Training / Cash transfer / Food distribution / Health camp / Construction
- `standard_committed` — Kiwango kilichoahidiwa: What was promised in the program document?
- `standard_delivered` — Kiwango kilichotolewa: What was actually received?
- `community_members_affected` — Idadi ya wanajamii walioathirika

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| NG-01 | beneficiary_exclusion | Eligible person not included in program without valid reason |
| NG-02 | beneficiary_selection_fraud | Favorites selected; corruption in beneficiary registration |
| NG-03 | aid_diversion | Aid resources stolen, diverted, or not distributed as planned |
| NG-04 | poor_program_quality | Program activities below committed standard |
| NG-05 | sexual_exploitation_abuse | SEA by NGO staff (PSEA — highest priority) |
| NG-06 | child_protection | Child abuse or harm involving NGO activities |
| NG-07 | staff_misconduct | Fraud, harassment, or unprofessional behavior by staff |
| NG-08 | discrimination | Exclusion based on tribe, gender, religion, disability |
| NG-09 | cash_transfer_dispute | Cash payment incorrect, delayed, or not received |
| NG-10 | data_privacy_breach | Beneficiary data shared without consent |
| NG-11 | safeguarding_failure | Organization failed to protect vulnerable persons |
| NG-12 | project_abandonment | NGO abandoned project or community without notice |
| NG-13 | false_promises | NGO promised outcomes that were never delivered |
| NG-14 | community_consultation_failure | Community not consulted on decisions affecting them |
| NG-15 | reporting_fraud | NGO misrepresented program results to donors |

### Resolution Standards

- **NGO level (Tanzania):** CHS Commitment 8 requires acknowledgement within 5 days; resolution within 30 days.
- **Safeguarding (PSEA):** Immediate acknowledgement; investigation within 72 hours; victim support services within 24 hours.
- **NGO Board of Tanzania:** Regulatory complaints about registered NGOs; NGO Board investigates within 60 days.
- **Donor reporting:** Many donors (FCDO, USAID, EU) require NGOs to report all safeguarding incidents within 24–72 hours.
- **PCCB (aid diversion/corruption):** Criminal investigation; toll-free 0800 110 065.
- **Required for escalation:** NGO name, project name, staff involved, date, description, evidence.

### Escalation Triggers

- `issue_type = sexual_exploitation_abuse` OR `issue_type = child_protection` — IMMEDIATE escalation to NGO safeguarding focal point, donor safeguarding team, and Tanzania Social Welfare; do not delay
- `victim_age_group = Child under 18` AND ANY misconduct — Mandatory child protection report; escalate to Department of Social Welfare within 24 hours
- `issue_type = aid_diversion` AND significant amount — Escalate to PCCB AND donor; NGO Board notification
- `issue_type = project_abandonment` AND community in humanitarian need — Escalate to UNHCR/WFP/UNICEF coordination mechanism and MOHCDGEC
- `issue_type = beneficiary_selection_fraud` AND systematic pattern — Escalate to NGO safeguarding AND donor; potential audit trigger
- `immediate_safety_concern = Yes` (safeguarding) — Before any data collection, ensure victim safety and connect to support services

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous fully accepted per CHS |
| ngo_name | Jina la shirika | Recommended | For routing |
| project_name | Jina la mradi | Recommended | For project-level improvement |
| suggestion_category | Kategoria | Yes | For analysis and routing |
| suggestion_detail | Maelezo | Yes | Core content |
| community_impact | Athari kwa jamii | Recommended | CHS requires community feedback loop |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| NGS-01 | community_participation | Kushirikisha jamii zaidi |
| NGS-02 | program_design | Kuboresha muundo wa programu |
| NGS-03 | transparency | Uwazi wa matumizi ya fedha |
| NGS-04 | feedback_mechanism | Kuboresha mfumo wa malalamiko |
| NGS-05 | staff_accountability | Uwajibikaji wa wafanyakazi |
| NGS-06 | local_hiring | Kuajiri watu wa ndani ya jamii |
| NGS-07 | safeguarding | Kuboresha ulinzi wa wanajamii |
| NGS-08 | exit_planning | Mpango bora wa kumaliza mradi |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina (hiari) | Optional | Anonymous inquiries accepted |
| ngo_name | Jina la shirika | Recommended | Routes to correct program |
| query_type | Aina ya swali | Yes | Routes inquiry |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| beneficiary_eligibility | Je, ninastahili kunufaika na programu? | project_name, location |
| program_registration | Jinsi ya kusajiliwa kwenye programu | project_name |
| aid_distribution_schedule | Ratiba ya ugawaji wa msaada | project_location |
| complaint_process | Jinsi ya kutoa malalamiko | ngo_name |
| program_results | Matokeo ya mradi | project_name |
| ngo_registration_status | Je, NGO hii imesajiliwa Tanzania? | ngo_name |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | CHS: community voice matters |
| staff_name | Jina la mfanyakazi (hiari) | Optional | Staff recognition |
| ngo_name | Jina la shirika | Yes | Routes to management |
| project_name | Mradi unaohusika | Recommended | Project-level recognition |
| specific_aspect_praised | Kipengele | Yes | Msaada halisi / Heshima / Uwazi / Ubora wa kazi |
| community_impact_positive | Athari nzuri kwa jamii | Recommended | CHS Commitment 8 positive feedback loop |

---

## AI Conversation Guidance for This Industry

- **Safeguarding takes absolute priority.** Before collecting any other information, if there is any indication of sexual exploitation, abuse, child harm, or physical violence by NGO staff, the AI must immediately: (1) ensure victim safety, (2) provide emergency support contacts, (3) escalate — and only then continue with data collection.
- **Preserve full anonymity for sensitive complaints.** CHS and IASC AAP both require that GRM systems accept completely anonymous complaints. Never push for identity if the person declines. "Unaweza kutoa malalamiko bila kutoa jina lako — tunakubali malalamiko ya siri."
- **Distinguish between the NGO and the donor.** Complainants often confuse the implementing NGO with the donor government or UN agency. Clarify: "Shirika linaloendesha mradi huu linaitwa nini? (Si mfadhili — watekelezaji wa mradi)"
- **For beneficiary disputes, do not make eligibility determinations.** Collect the facts and route to the program team. "Siwezi kukuambia kama unastahili — hilo linaamuliwa na timu ya programu, lakini tutahakikisha tatizo lako linasikika."
- **For cash transfer disputes, ask for the transfer reference or phone number used.** Most cash transfers via mobile money have a transaction ID that enables quick verification.
- **For project quality complaints, ask what was promised vs. what was received.** This framing — "uliahidiwa nini vs. ulipata nini" — produces the most actionable feedback.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| NGO name | "Shirika gani la NGO au mradi unaohusika?" |
| Project name | "Mradi huu unaitwa nini? Au programu gani inayohusika?" |
| Anonymity assurance | "Unaweza kutoa malalamiko bila kutoa jina lako — hii ni haki yako" |
| Safeguarding | "Kama tukio linaweza kuathiri usalama wa mtu, tutawasiliana na timu ya ulinzi haraka iwezekanavyo" |
| What was promised | "Uliambiwa utapata nini kutoka kwa mradi huu?" |
| What was received | "Kwa kweli ulipata nini? Tofauti ni ipi?" |
| Staff involved | "Mfanyakazi wa NGO aliyehusika anaitwa nini? Cheo chake ni nini?" |
| Evidence | "Je, una ushahidi wowote — picha, barua, ujumbe wa simu, au shahidi?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | sexual_exploitation_abuse | IMMEDIATE: NGO safeguarding focal point + donor safeguarding hotline + Tanzania Social Welfare; victim support first |
| victim_age_group | Child under 18 AND any misconduct | Mandatory child protection report; Department of Social Welfare within 24 hours |
| issue_type | aid_diversion AND donor_reference available | PCCB referral + donor safeguarding/integrity unit notification |
| issue_type | project_abandonment AND humanitarian need | UNHCR/WFP/UNICEF coordination + MOHCDGEC notification |
| immediate_safety_concern | Yes | Victim safety first — connect to support services before data collection |
| issue_type | discrimination | CHRAGG referral; potential violation of Tanzania human rights obligations |
| consent_to_share | No | Keep complaint strictly confidential; only aggregate for systemic analysis; no individual routing without consent |
| issue_type | reporting_fraud | Donor integrity unit notification; NGO Board of Tanzania complaint |

---

*Sources: Tanzania NGO Act Cap. 56, CHS Alliance Core Humanitarian Standard 2014, IASC AAP Framework 2021, SPHERE Standards 2018, UN ST/SGB/2003/13, PCCB Act Cap. 329, ISO 10002:2018, FCDO/USAID/EU safeguarding requirements*
