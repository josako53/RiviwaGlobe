---
tags: [industry-kb, field-standards, feedback-fields]
---
# Construction / Real Estate Development — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: contractor, developer, ujenzi, mkandarasi, mjenzi, building site, construction site, eneo la ujenzi, foundation, msingi, slab, sakafu ya saruji, roofing, paa, scaffolding, mkandarasi wa bomba, subcontractor, structural engineer, civil engineer, quantity surveyor, BOQ, Bill of Quantities, building permit, kibali cha ujenzi, CRB, Contractors Registration Board, AQRB, ERB, TBA, Tanzania Buildings Agency, NEMC clearance, project handover, makabidhiano, snag list, orodha ya kasoro, certificate of occupancy, CoO, variation order, retention money, practical completion, earthworks, drainage, borehole, rebar, Y8 Y10 Y12, iron sheets mabati, hollow blocks, NSSF housing, NHC, road construction, bridge, culvert, project delay, kuchelewa mradi, poor workmanship, kazi mbaya, land encroachment, blast damage, dust from site, vumbi la ujenzi, construction noise, kelele za ujenzi, community displacement, project affected, property damage

## Why Industry-Specific Fields Matter

Construction complaints span incompatible issue types — a structural defect liability claim (requiring BOQ reference, contractor licence number, and defect description), a worker safety incident (requiring OSHA notification, injury severity, and witness details), and a community nuisance complaint (requiring proximity data, affected household count, and NEMC status) — each routed to entirely different regulators and resolved under different legal frameworks. Without industry-specific fields, the AI cannot distinguish a civil dispute from a regulatory emergency, route to the right authority, or calculate compensation liability under IFC PS5 or the Tanzania Land Act.

## Source Standards

- IFC Good Practice Note on Addressing Grievances from Project-Affected Communities (2009)
- IFC Performance Standard 1: Assessment and Management of Environmental and Social Risks (2012)
- IFC Performance Standard 4: Community Health, Safety, and Security (2012)
- IFC Performance Standard 5: Land Acquisition and Involuntary Resettlement (2012) and Guidance Note 5
- World Bank Environmental and Social Framework ESS10: Stakeholder Engagement and Information Disclosure — Guidance Note 10 (2018)
- EBRD Grievance Management Guidance Note (2012)
- ISO 45001:2018 Occupational Health and Safety Management Systems, Clause 10.2 (Incident Reporting)
- Tanzania Occupational Safety and Health Act No. 5 of 2003 (Chapter 297) — OSHA notification requirements
- Tanzania National Environment Management Act Cap. 191 (NEMC jurisdiction and notifications)
- Contractors Registration Board (CRB) Act, Tanzania — contractor licensing and disciplinary process
- Architects and Quantity Surveyors Registration Board (AQRB) Act, Tanzania
- Engineers Registration Board (ERB) Act, Tanzania
- Tanzania Land Act Cap. 113 (1999) and Land (Assessment of the Value of Land for Compensation) Regulations
- CAO Ombudsman Advisory Note: A Guide to Designing and Implementing Grievance Mechanisms for Development Projects (IFC/MIGA)

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | IFC GPN (2009): "name of the individual or organization" is a mandatory grievance record field; needed to open formal ticket and communicate resolution |
| complainant_phone | Nambari ya simu | Yes | Required for acknowledgement and status updates; IFC GPN requires communication of resolution back to complainant |
| complainant_email | Barua pepe | Recommended | For written acknowledgement and formal documentation; EBRD GN (2012) requires written records of all communications |
| complainant_type | Aina ya mlalamikaji | Yes | Drives rights framework. Options: Individual / Community Group / Worker / NGO / Neighbouring Business; IFC GPN categorizes complainant types differently |
| anonymity_flag | Je, una hamu ya kukaa bila kutambulika? | Yes | IFC GPN (2009): mechanisms must permit anonymous complaints; flag must be captured even when anonymous to maintain count |
| gender | Jinsia | Yes | World Bank ESS10 GN10: gender-disaggregated grievance data is mandatory for ISR reporting |
| project_name | Jina la mradi | Yes | IFC GPN and World Bank ESS10 Annex A: grievance must be tied to a specific project identification; enables routing to correct contractor |
| contractor_or_developer_name | Jina la mkandarasi / mjenzi | Yes | IFC PS4 para. 22: incidents attributable to contractor conduct must document which contractor is responsible |
| site_address | Anwani ya eneo la ujenzi | Yes | IFC GPN (2009): site location is a core grievance record field; enables field verification |
| gps_coordinates | Kuratibu za GPS | Recommended | World Bank ESS10 / AfDB/AIIB ESIA practice: GPS required for incident mapping and regulatory monitoring |
| project_phase | Hatua ya mradi | Yes | EBRD GN (2012): project phase context determines applicable standards. Options: Design / Excavation / Foundation / Superstructure / Finishing / Commissioning / Post-Handover |
| issue_type | Aina ya tatizo / kategoria | Yes | IFC GPN (2009): categorization explicitly required; determines regulatory routing (CRB, OSHA, NEMC, courts) |
| date_issue_occurred | Tarehe ya tukio | Yes | ISO 45001:2018 Clause 10.2: date of incident separate from date reported; IFC GPN requires both |
| issue_description | Maelezo ya tatizo | Yes | IFC GPN (2009): "what, where, when, who, why" narrative required; minimum content for any investigation |
| date_received | Tarehe ya kupokea malalamiko | Auto | IFC GPN (2009): "date of complaint" explicitly required; auto-capture by system |
| channel_of_submission | Njia ya kuwasilisha | Auto | World Bank ESS10 GN10 para. 101: multiple intake channels must be logged for monitoring |
| desired_outcome | Matokeo unayotaka | Yes | CAO Ombudsman Advisory Note: complainant's desired remedy must be documented before any resolution process begins |
| preferred_contact_method | Njia unayopendelea ya mawasiliano | Yes | Options: SMS / WhatsApp / Simu / Barua pepe; IFC GPN requires communication of outcome back to complainant |

### Conditional Fields (collect based on issue type)

**If issue_type = Structural Defect / Poor Workmanship:**
Also collect:
- `boq_reference` — Nambari ya BOQ: Links complaint to contracted scope; enables comparison of specified vs. delivered materials
- `defect_location_in_building` — Mahali pa kasoro ndani ya jengo: e.g., Foundation / Slab / Roof / Electrical / Plumbing / Walls / Windows; narrows liability
- `structural_engineer_assessed` — Je, mhandisi amekagua? (Ndiyo/Hapana): Determines if formal structural report exists
- `estimated_repair_cost_tzs` — Gharama ya kukarabati (TZS): IFC PS5 GN5: damage valuation required for compensation-linked claims
- `defect_liability_period_active` — Je, kipindi cha dhamana ya kasoro bado kinaendelea? (Ndiyo/Hapana): Determines whether contractor is contractually obligated to remedy
- `contractor_notified_previously` — Je, mkandarasi alishaarifu? (Ndiyo/Hapana/Tarehe): Prior notice requirement for most contract dispute processes

**If issue_type = Project Delay:**
Also collect:
- `agreed_completion_date` — Tarehe ya kukamilika iliyokubaliwa: Baseline for delay measurement
- `current_completion_estimate` — Makadirio ya sasa ya kukamilika: Quantifies delay duration
- `delay_duration_weeks` — Muda wa kuchelewa (wiki): For SLA tracking and penalty calculation if applicable
- `advance_payment_amount_tzs` — Kiasi cha malipo ya awali (TZS): Relevant if delay involves financial retention or fraud risk
- `payment_certificates_issued` — Hati za malipo zilizotolewa: Number and dates; validates payment vs. progress ratio
- `contractor_last_active_on_site` — Tarehe ya mwisho mkandarasi kuonekana eneo: Risk indicator for contractor abandonment

**If issue_type = Community Nuisance (Dust, Noise, Vibration):**
Also collect:
- `nuisance_type` — Aina ya usumbufu: Dust / Noise / Vibration / Light Pollution / Traffic / Water Runoff (may select multiple)
- `number_of_households_affected` — Idadi ya kaya zilizoathirika: World Bank ESS10 GN10: disaggregated impact data required
- `distance_from_site_meters` — Umbali kutoka eneo la ujenzi (mita): IFC PS4: proximity to site determines impact attribution
- `nemc_complaint_filed` — Je, NEMC waliarifu? (Ndiyo/Hapana/Nambari ya kesi): Tanzania Environmental Management Act Cap. 191 — NEMC has jurisdiction over construction environmental impacts
- `health_symptoms_experienced` — Dalili za kiafya: e.g., Respiratory problems, headaches, sleep disruption; IFC PS4 para. 5-10 requires documentation of health impacts

**If issue_type = Safety Incident / Worker Injury:**
Also collect:
- `injury_occurred` — Je, kulikuwa na majeraha? (Ndiyo/Hapana): ISO 45001:2018 Clause 10.2: mandatory field
- `injury_type` — Aina ya jeraha: e.g., Fall / Crush / Electrical / Chemical / Structural Collapse / Near Miss; ISO 45001 requires classification
- `injury_severity` — Ukali wa jeraha: Fatality / Serious (hospitalization) / Minor / First Aid Only / Near Miss; determines OSHA notification requirement
- `number_injured` — Idadi ya walioumia: ISO 45001:2018 Clause 10.2; Tanzania OHS Act 2003 notification threshold
- `osha_notified` — Je, OSHA waliarifu? (Ndiyo/Hapana): Tanzania OHS Act No. 5 of 2003: fatal and serious injuries must be reported to OSHA authority; field captures compliance status
- `osha_reference_number` — Nambari ya kesi ya OSHA: Cross-referencing regulatory notification is required practice
- `witness_names_contacts` — Majina na nambari za mashahidi: ISO 45001:2018 Clause 10.2: "witness names and contact details" required in incident reports

**If issue_type = Property Damage (Third-Party / Community Property):**
Also collect:
- `property_address_damaged` — Anwani ya mali iliyoharibiwa: IFC PS4 — community-level impacts require identification of affected properties
- `property_type_damaged` — Aina ya mali iliyoharibiwa: House / Commercial Building / Road / Fence / Farm / Vehicle / Borehole
- `estimated_damage_value_tzs` — Thamani ya uharibifu (TZS): IFC PS5: compensation-linked grievances require damage valuation
- `photos_evidence_attached` — Picha / ushahidi umeambatishwa? (Ndiyo/Hapana): EBRD GN; IFC GPN: photographic evidence is primary support for damage claims

**If issue_type = Land Encroachment / Displacement:**
Also collect:
- `land_area_affected_sqm` — Eneo la ardhi lililoathirika (mita za mraba): IFC PS5 GN5: land area measurement required for compensation
- `land_title_type` — Aina ya hati ya ardhi: Right of Occupancy / Certificate of Title / Letter of Allotment / Customary Land
- `compensation_offered` — Je, fidia iliotolewa? (Ndiyo/Hapana/Kiasi): IFC PS5; Tanzania Land Act: compensation tracking required
- `number_of_households_displaced` — Idadi ya kaya zilizohama: World Bank ESS10 GN10; IFC PS5 requires household census for resettlement

**If issue_type = Contract / Payment Dispute:**
Also collect:
- `contract_signed` — Je, mkataba ulitiwa sahihi? (Ndiyo/Hapana): Determines legal standing of claim
- `total_contract_value_tzs` — Thamani yote ya mkataba (TZS): Baseline for percentage-completion vs. payment ratio
- `amount_paid_to_date_tzs` — Kiasi kilicholipwa hadi sasa (TZS): Quantifies financial exposure
- `amount_in_dispute_tzs` — Kiasi kinachogombaniwa (TZS): Required for any mediation or legal process
- `crb_registration_number` — Nambari ya usajili wa CRB: Tanzania CRB Act — contractor registration verification; unregistered contractors have limited legal standing

### Issue Type Classification

| Code | Issue Type | Swahili |
|------|-----------|---------|
| CN-01 | structural_defect_poor_workmanship | Kasoro za muundo / kazi mbaya |
| CN-02 | project_delay_contractor_abandonment | Kuchelewa kwa mradi / kutoroka mkandarasi |
| CN-03 | material_specification_breach | Kutumia vifaa tofauti na vilivyoainishwa |
| CN-04 | contractor_payment_dispute | Mgogoro wa malipo na mkandarasi |
| CN-05 | community_dust_noise_nuisance | Vumbi / kelele kutoka eneo la ujenzi |
| CN-06 | vibration_blast_damage | Uharibifu wa mtetemo / mlipuko |
| CN-07 | worker_safety_incident | Tukio la usalama wa mfanyakazi |
| CN-08 | property_damage_third_party | Uharibifu wa mali za wengine |
| CN-09 | land_encroachment_displacement | Uvamizi wa ardhi / kusogezwa makazi |
| CN-10 | contractor_misconduct_fraud | Ulaghai au mwenendo mbaya wa mkandarasi |
| CN-11 | environmental_violation | Ukiukwaji wa mazingira (NEMC) |
| CN-12 | permit_regulatory_violation | Ukiukwaji wa vibali / kanuni za ujenzi |
| CN-13 | handover_defects_snag | Kasoro baada ya makabidhiano |
| CN-14 | access_road_blockage | Kuzuia barabara / njia za umma |
| CN-15 | water_contamination | Uchafuzi wa maji |

### Resolution Standards for This Industry

- **Contractor defect liability (Tanzania):** Standard construction contracts include a 12-month Defects Liability Period (DLP) after practical completion during which the contractor must remedy defects at no cost. The AI must determine whether the DLP is still active.
- **CRB disciplinary process:** Complaints about registered contractors can be lodged with the Contractors Registration Board (CRB) Tanzania. CRB can suspend or revoke contractor registration. Required documentation: signed contract, BOQ, evidence of defects/breach.
- **OSHA notification (Tanzania OHS Act 2003):** Fatal or serious workplace injuries on construction sites must be reported to the OSHA Authority within 24 hours of occurrence. Failure to report is a criminal offence.
- **NEMC process:** Environmental complaints (dust, water contamination, waste dumping) may be reported to NEMC (National Environment Management Council). NEMC can issue stop orders and levy fines.
- **IFC GPN timelines:** Acknowledgement within 5-10 business days; resolution within 30 days for standard cases; complex cases may extend to 90 days with written explanation to complainant.
- **IFC PS5 compensation:** Land-linked grievances require independent valuation; replacement value (not market depreciated value) is the IFC standard for compensation.

### Escalation Triggers (field values that require immediate escalation)

- `issue_type = worker_safety_incident` AND `injury_severity = Fatality` — Report to OSHA within 24 hours (Tanzania OHS Act); escalate to emergency services; flag for immediate regulatory notification
- `issue_type = worker_safety_incident` AND `injury_severity = Serious` — Notify OSHA; create priority case; investigation required before site resumption
- `issue_type = structural_defect_poor_workmanship` AND structure is occupied / risk of collapse — Emergency evacuation advisory; notify TBA and ERB immediately
- `issue_type = vibration_blast_damage` AND residential buildings cracked — Structural engineer assessment required; notify OSHA and municipal authority
- `issue_type = environmental_violation` AND `nuisance_type = Water Contamination` — Notify NEMC; potential public health emergency
- `issue_type = contractor_misconduct_fraud` AND `advance_payment_amount_tzs > 5000000` AND contractor uncontactable — Criminal fraud escalation; advise police report and CRB notification
- `issue_type = land_encroachment_displacement` AND `number_of_households_displaced > 0` AND no compensation offered — IFC PS5 violation; escalate to organization's Social/ESG officer
- `issue_type = community_dust_noise_nuisance` AND `health_symptoms_experienced` includes respiratory distress — Prioritize; notify NEMC and recommend medical attention
- `issue_type = permit_regulatory_violation` AND construction beyond approved floor count — Municipal authority and TBA notification required

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina la mtoa maoni (hiari) | Optional | IFC GPN (2009): suggestions permitted anonymously; name optional for acknowledgement |
| contact_details | Mawasiliano (hiari) | Optional | Required only if submitter wants a response |
| project_name_or_location | Jina la mradi / eneo | Yes | Links suggestion to specific project for routing to correct project team |
| suggestion_category | Kategoria ya mapendekezo | Yes | Routes to correct department. See categories below |
| suggestion_detail | Maelezo ya mapendekezo | Yes | Free text; core substance of the suggestion |
| suggested_beneficiary | Wanaofaidika na pendekezo hili | Recommended | Helps prioritize: workers / community / client / regulator |
| urgency | Kiwango cha haraka | Yes | Options: Kawaida / Inayohitaji haraka; IFC GPN recommends prioritization of suggestions with safety implications |
| supporting_documents | Nyaraka za kuunga mkono (hiari) | Optional | Photos, drawings, or reference materials |
| channel_submitted | Njia ya kuwasilisha | Auto | Supports omnichannel analytics |

### Industry-Specific Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| CS-01 | safety_practice_improvement | Uboreshaji wa mazoea ya usalama |
| CS-02 | quality_control_method | Njia ya kudhibiti ubora wa kazi |
| CS-03 | community_communication | Mawasiliano bora na jamii |
| CS-04 | dust_noise_reduction | Kupunguza vumbi na kelele |
| CS-05 | local_employment_procurement | Ajira na manunuzi ya ndani |
| CS-06 | environmental_protection | Kulinda mazingira wakati wa ujenzi |
| CS-07 | materials_sourcing | Vyanzo bora vya vifaa vya ujenzi |
| CS-08 | traffic_management | Usimamizi wa usafiri karibu na eneo |
| CS-09 | project_management_process | Mchakato wa usimamizi wa mradi |
| CS-10 | community_benefit_sharing | Mgawanyo wa faida na jamii |
| CS-11 | waste_management | Usimamizi wa taka za ujenzi |
| CS-12 | worker_welfare | Ustawi wa wafanyakazi wa ujenzi |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| inquirer_name | Jina la mwulizaji | Recommended | For personalized and documented response |
| contact_details | Mawasiliano | Yes | Required to deliver response |
| inquiry_type | Aina ya swali | Yes | Routes to correct knowledge base or officer |
| inquiry_detail | Maelezo ya swali | Yes | Free text; core substance of the question |
| project_or_location | Mradi au eneo linalohusu | Recommended | Contextualizes the inquiry for relevant answer |
| urgency | Kiwango cha haraka | Yes | Options: Kawaida / Inayohitaji haraka |
| preferred_response_format | Jinsi unavyotaka jibu | Yes | Options: SMS / Simu / WhatsApp / Barua pepe |
| inquiry_reference_number | Nambari ya marejeleo (otomatiki) | Auto | All interactions must be trackable per IFC GPN |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Swahili | Additional Fields to Collect |
|-------------|---------|------------------------------|
| permits_and_approvals | Vibali na idhini za ujenzi | project_or_location, building_type |
| contractor_verification | Uthibitishaji wa mkandarasi | contractor_name, crb_number (if known) |
| construction_costs | Gharama za ujenzi | project_type, size_sqm, location |
| material_specification | Vipimo vya vifaa | material_type, project_type |
| compensation_process | Mchakato wa fidia | project_name, land_area_sqm |
| resettlement_rights | Haki za watu waliohamishwa | community_name, project_name |
| employment_opportunities | Fursa za kazi | project_location, skills |
| safety_regulations | Kanuni za usalama wa ujenzi | site_type, issue_context |
| environmental_clearance | Idhini ya mazingira (NEMC) | project_type, project_location |
| dispute_resolution | Mchakato wa kutatua migogoro | contract_exists, amount_in_dispute_tzs |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina la mtoa pongezi (hiari) | Optional | For acknowledgement; EBRD GN feedback loops support staff recognition |
| contact_details | Mawasiliano (hiari) | Optional | If submitter wants acknowledgement |
| project_name_or_location | Jina la mradi / eneo | Yes | Routes compliment to correct project team |
| contractor_or_developer_name | Jina la mkandarasi / mjenzi | Yes | Identifies the entity being commended |
| person_team_commended | Jina la mtu / timu inayopongezwa | Recommended | Enables individual recognition and performance tracking |
| commendation_category | Kategoria ya pongezi | Yes | See categories below |
| commendation_detail | Maelezo ya pongezi | Yes | Free text narrative; captures specific reasons for praise |
| overall_satisfaction_rating | Kiwango cha ridhaa (1-5) | Yes | IFC GPN and ICMM (2019): satisfaction capture required for outcome-based evaluation |
| date_of_interaction | Tarehe ya tukio / mazungumzo | Recommended | Correlates with project phase and personnel records |

### Commendation Categories

| Code | Category | Swahili |
|------|----------|---------|
| CA-01 | quality_of_workmanship | Ubora wa kazi ya ujenzi |
| CA-02 | on_time_delivery | Kukamilisha mradi kwa wakati |
| CA-03 | community_relations | Mahusiano mazuri na jamii |
| CA-04 | safety_record | Rekodi nzuri ya usalama |
| CA-05 | communication_transparency | Uwazi na mawasiliano mazuri |
| CA-06 | environmental_mitigation | Kulinda mazingira ipasavyo |
| CA-07 | materials_specification_compliance | Kufuata vipimo vya vifaa |
| CA-08 | budget_adherence | Kufuata bajeti iliyokubaliwa |
| CA-09 | post_handover_responsiveness | Kuitika haraka baada ya makabidhiano |
| CA-10 | local_employment | Kuajiri wafanyakazi wa eneo |

---

## AI Conversation Guidance for This Industry

- **Distinguish the role of the person speaking before collecting fields.** Ask "Je, wewe ni mteja (client) wa mradi, mwanajamii anayeathiriwa, mfanyakazi wa eneo, au mtu mwingine?" — a client's complaint about workmanship follows a contract dispute path, a community member's complaint about dust follows an environmental path, and a worker's complaint about safety follows an OSHA path. Do not mix these flows.
- **Identify the contractor and project first, then the issue.** Ask "Mradi/jengo hili liko wapi, na lina mkandarasi gani au mjenzi gani?" before diving into the specific problem. This enables routing to the correct entity and checking CRB registration status.
- **For safety incidents, collect injury facts before any other field.** If the conversation signals a current or recent injury, immediately ask "Je, kuna mtu aliyeumia? Kama ndiyo, wanapokelewa dawa hospitali sasa hivi?" — safety-first before ticket data.
- **For defect complaints, establish timeline relative to handover.** Ask "Nyumba / jengo lilikabidhiwa lini?" — if within 12 months, the Defects Liability Period is likely active and the contractor is legally obligated to remedy. This context changes the advice given.
- **Do not ask for BOQ or contract numbers upfront** — most complainants do not have these immediately. Instead ask "Je, una nakala ya mkataba wako au makubaliano yaliyoandikwa?" and proceed from there. Collect document reference numbers as supporting details, not blockers.
- **For community nuisance complaints, ask about the number of affected households early.** A single-household noise complaint is handled differently from a multi-household community impact claim that may require IFC PS4 community health assessment.
- **For payment disputes, establish advance payment amount before anything else.** High advance payments to contractors who have gone silent are fraud risk signals — flag these for urgent handling.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Complainant role | "Je, wewe ni mteja wa mradi, mwanajamii anayeathiriwa, au mfanyakazi wa eneo hili?" |
| Project / site location | "Mradi huu uko wapi hasa — mtaa, kata, na wilaya?" |
| Contractor name | "Mkandarasi au mjenzi anaitwa nani?" |
| Issue type | "Tatizo lako ni nini hasa — kasoro za ujenzi, kuchelewa, malipo, usalama, au jambo lingine?" |
| Date of incident | "Tatizo hili lilianza lini — tarehe gani au wiki ngapi zilizopita?" |
| Injury occurred | "Je, kulikuwa na mtu aliyeumia? Kama ndiyo, majeraha yalikuwa makubwa?" |
| Households affected | "Je, familia ngapi au majirani ngapi wameathiriwa na tatizo hili?" |
| OSHA notified | "Je, Mamlaka ya Usalama na Afya Kazini (OSHA) waliarifu kuhusu tukio hili?" |
| Advance payment | "Je, ulilipa kiasi gani kama malipo ya awali, na mkandarasi amekwama wapi sasa?" |
| Desired outcome | "Unataka nini kutokea — kurekebisha kasoro, kupata fidia, au kuchukua hatua za kisheria?" |
| Contract status | "Je, mkataba uliandikwa na kutiwa sahihi na pande zote mbili?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| injury_severity | Fatality | Immediate OSHA notification (Tanzania OHS Act 2003); create emergency escalation ticket; contact emergency services |
| injury_severity | Serious (hospitalization) | Notify OSHA within 24 hours; create priority safety ticket; site inspection required |
| issue_type | structural_defect_poor_workmanship AND defect_liability_period_active = Yes | Advise complainant to issue written notice to contractor; contractor has legal obligation to remedy within DLP |
| issue_type | contractor_misconduct_fraud AND contractor uncontactable | Advise police report; notify CRB Tanzania; freeze any pending payments if possible |
| issue_type | environmental_violation AND nemc_complaint_filed = No | Advise complainant to report to NEMC via nemc.or.tz; create case record with NEMC reference number when obtained |
| issue_type | worker_safety_incident AND osha_notified = No | Advise immediate OSHA notification; document failure to notify as a secondary compliance issue |
| issue_type | community_dust_noise_nuisance AND number_of_households_affected > 5 | Escalate to ESG / Community Liaison officer; classify as community-level impact requiring IFC PS4 response |
| issue_type | land_encroachment_displacement AND compensation_offered = No | Escalate to Social Officer; cite IFC PS5 and Tanzania Land Act Cap. 113 compensation obligations |
| crb_registration_number | Not registered / unverified | Flag contractor as potentially unregistered; advise complainant to verify with CRB before proceeding |
| injury_severity | Near Miss | Create safety investigation ticket; ISO 45001 requires near-miss investigation with same rigor as actual incidents |
| issue_type | project_delay_contractor_abandonment AND advance_payment_amount_tzs > 10000000 | Flag as potential fraud; advise legal consultation; notify CRB |
| structural_engineer_assessed | No AND defect involves foundation or slab | Recommend independent structural engineering assessment before occupation or further investment |

---

*Sources: IFC GPN (2009), IFC PS1/PS4/PS5 GN5 (2012), World Bank ESS10 GN10 (2018), EBRD GN (2012), ISO 45001:2018 Clause 10.2, Tanzania OHS Act No. 5 of 2003, Tanzania Environmental Management Act Cap. 191, CRB Act Tanzania, ERB Act Tanzania, AQRB Act Tanzania, Tanzania Land Act Cap. 113, CAO Ombudsman Advisory Note*
