---
tags: [industry-kb, field-standards, feedback-fields]
---
# Mining / Extractive Industries — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: mine, mgodi, mining company, kampuni ya madini, gold mine, mgodi wa dhahabu, diamond mine, mgodi wa almasi, tanzanite, coal mine, mgodi wa makaa, salt mining, chumvi, limestone quarry, quarry, artisanal miner, mchimbaji mdogo, ASM, small-scale miner, large-scale mining, exploration, uchunguzi wa madini, blasting, mlipuko, tailings dam, bwawa la taka za madini, overburden, ore, madini, processing plant, kiwanda cha kuchenjua, cyanide, mercury, zebaki, acid mine drainage, land reclamation, ukarabati wa ardhi, resettlement, uhamisho wa makazi, community development fund, CDF, local content, maudhui ya ndani, mining license, leseni ya uchimbaji, TMAA, Tanzania Minerals Audit Agency, MEM Ministry of Energy and Minerals, NEMC, OSHA, Mining Commission, prospecting license, special mining license, SML, primary mining license, PML, CSR, community benefit agreement, CDA, royalty, ada ya madini, blasting hours, dust from mine, vumbi la mgodi, vibration damage, uharibifu wa mtetemo, water contamination maji machafu, crop damage, mazao yaliyoharibiwa, compensation unpaid, fidia haijaliwa, Geita Gold Mine, Bulyanhulu, Buzwagi, North Mara, Mwadui, Merelani, Kabanga Nickel, STAMICO, zama zama, rock fall, kushuka kwa mwamba, entrapment, underground mining, uchimbaji wa chini ya ardhi, open pit, shimo la wazi, shaft, shimo la mgodi

## Why Industry-Specific Fields Matter

Mining grievances span four entirely separate legal systems simultaneously — environmental law (NEMC / EIA compliance), mining law (Tanzania Mining Act 2010 and Mining Commission), occupational safety law (OSHA / OHS Act 2003), and land/resettlement law (Land Act / IFC PS5) — and may additionally invoke indigenous peoples' rights (IFC PS7) and international human rights standards (ICMM 2019 / UN Guiding Principles). A community's complaint about contaminated water requires NEMC case number, GPS coordinates of the water source, affected household count, water source type, and evidence of prior NEMC notification — none of which a generic feedback form captures. Without these fields, the complaint is unactionable by any of the four regulatory bodies with jurisdiction.

## Source Standards

- ICMM "Handling and Resolving Local-Level Concerns and Grievances: Human Rights in the Mining and Metals Sector" (December 2019)
- IFC Good Practice Note on Addressing Grievances from Project-Affected Communities (2009)
- IFC Performance Standard 1: Assessment and Management of Environmental and Social Risks (2012)
- IFC Performance Standard 4: Community Health, Safety, and Security (2012)
- IFC Performance Standard 5: Land Acquisition and Involuntary Resettlement (2012) and Guidance Note 5
- IFC Performance Standard 7: Indigenous Peoples (2012)
- World Bank Environmental and Social Framework ESS10: Stakeholder Engagement and Information Disclosure — Guidance Note 10 (2018)
- EBRD Grievance Management Guidance Note (May 2012)
- ISO 45001:2018 Occupational Health and Safety Management Systems, Clause 10.2 (Incident Reporting)
- Tanzania Mining Act, 2010 (Chapter 123), as amended to 30 November 2019 — Sections 97, 107, 109, 119
- Tanzania Mining (Dispute Resolution) Rules 2021 — Minerals Commission complaint registration
- Tanzania Occupational Safety and Health Act No. 5 of 2003 (Chapter 297) — OSHA notification
- Tanzania National Environment Management Act Cap. 191 — NEMC jurisdiction over mining environmental impacts
- CAO Ombudsman Advisory Note: A Guide to Designing and Implementing Grievance Mechanisms for Development Projects (IFC/MIGA)
- UN Guiding Principles on Business and Human Rights (UNGPs) — Pillar III: Access to Remedy

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | IFC GPN (2009): "name of the individual or organization" is a mandatory grievance record field |
| complainant_phone | Nambari ya simu | Yes | IFC GPN: required for communication of resolution back to complainant; ICMM (2019): "predictable" mechanism requires response capability |
| complainant_email | Barua pepe | Recommended | For written acknowledgement; EBRD GN (2012) requires written records of all communications |
| gender | Jinsia | Yes | World Bank ESS10 GN10: gender-disaggregated grievance data mandatory for ISR reporting |
| anonymity_flag | Je, una hamu ya kukaa bila kutambulika? | Yes | IFC GPN (2009): mechanisms must allow anonymous complaints; ICMM (2019): confidentiality is an effectiveness criterion |
| complainant_type | Aina ya mlalamikaji | Yes | ICMM (2019): individual vs. collective grievance triggers different response processes. Options: Individual / Community Group (Kikundi cha Jamii) / Traditional Authority (Mamlaka ya Jadi) / NGO / Worker (Mfanyakazi) / ASM Cooperative |
| vulnerability_status | Hali ya udhaifu | Yes | IFC PS7 (2012): special provisions for indigenous peoples; World Bank ESS10: disaggregation by vulnerability. Options: None / Indigenous Community (Jamii ya Asili) / Woman-Headed Household / Elderly / Disabled / Child-Affected |
| community_village_name | Jina la kijiji / jamii | Yes | ICMM (2019): community identification is fundamental to any mining grievance; IFC PS7 requires community-level identification |
| sub_village_ward_district | Kijiji kidogo / kata / wilaya | Yes | Tanzania administrative structure; required for routing to Local Government Authority and regional NEMC/OSHA offices |
| gps_coordinates_incident | Kuratibu za GPS za tukio | Recommended | World Bank ESS10 / ICMM (2019): GPS required for mapping, impact attribution, and boundary verification |
| mine_company_name | Jina la mgodi / kampuni ya madini | Yes | IFC GPN; ICMM (2019): mine identification is core to any mining grievance record; routes complaint to correct licence holder |
| mining_licence_number | Nambari ya leseni ya uchimbaji | Recommended | Tanzania Mining Act 2010 (Chapter 123): disputes relate to "areas subject to mineral rights" — licence number identifies the regulated area |
| traditional_community_leader | Jina na cheo cha kiongozi wa jadi | Recommended | IFC PS7 (2012) para. 12: community representatives must be identified; ICMM (2019): culturally appropriate mechanisms require engagement with traditional leaders |
| distance_from_mine_boundary_km | Umbali kutoka mpaka wa mgodi (km) | Recommended | ICMM (2019): impact attribution depends on proximity to mine boundary; enables causal link determination |
| issue_type | Aina ya tatizo / kategoria | Yes | ICMM (2019): grievance categorization explicitly required; determines routing (OSHA / NEMC / Mining Commission / courts / CSR department) |
| date_issue_first_occurred | Tarehe ya kwanza ya tukio | Yes | IFC GPN (2009): date of first occurrence required; ISO 45001:2018 Clause 10.2 for safety incidents; determines limitation period |
| issue_ongoing | Je, tatizo bado linaendelea? (Ndiyo/Hapana) | Yes | ICMM (2019): chronic vs. acute impact distinction drives response type — chronic pollution requires ongoing monitoring, acute incident requires immediate response |
| issue_description | Maelezo kamili ya tatizo | Yes | IFC GPN (2009): "what, where, when, who, why" narrative required; minimum content for any regulatory or CSR investigation |
| date_received | Tarehe ya kupokea malalamiko | Auto | IFC GPN (2009): "date of complaint" explicitly required |
| channel_of_submission | Njia ya kuwasilisha | Auto | ICMM (2019): mechanisms must be accessible via multiple channels; logging channel enables access gap analysis |
| previous_complaint_to_company | Je, kampuni iliripotiwa awali? (Ndiyo/Hapana/Tarehe) | Yes | ICMM (2019): mechanism must document prior internal escalation attempts; required for Mining Commission escalation |
| desired_outcome | Matokeo unayotaka | Yes | CAO Ombudsman Advisory Note: complainant's desired remedy must be documented; options: Compensation / Stop Activity / Environmental Remediation / Employment / Apology / Investigation / Regulatory Action |
| preferred_contact_method | Njia unayopendelea ya mawasiliano | Yes | ICMM (2019): "accessible" mechanism requires preferred language and channel; Options: SMS / Simu / WhatsApp / Kwa njia ya kiongozi wa kijiji |

### Conditional Fields (collect based on issue type)

**If issue_type = Environmental Pollution (Water / Air / Soil):**
Also collect:
- `pollution_type` — Aina ya uchafuzi: Water Contamination / Acid Mine Drainage / Dust and Particulate Matter / Chemical Spill / Tailings Overflow / Mercury Contamination / Cyanide Leak / Waste Rock Dump; ICMM (2019) and NEMC distinguish pollution types for regulatory routing
- `water_source_affected` — Chanzo cha maji kilichoathirika: Well (Kisima) / River (Mto) / Borehole (Borehole) / Piped Water / Stream / Lake; ICMM (2019): water contamination is a high-priority mining grievance; Tanzania Mining Act s.119(b) lists water rights disputes explicitly
- `water_test_done` — Je, maji yalichunguzwa? (Ndiyo/Hapana): Laboratory water testing provides scientific evidence required by NEMC for enforcement action
- `nemc_previously_notified` — Je, NEMC waliarifu? (Ndiyo/Hapana/Nambari ya kesi): Tanzania Environmental Management Act Cap.191 — NEMC has primary jurisdiction over mining environmental impacts
- `nemc_reference_number` — Nambari ya kesi ya NEMC: Cross-referencing regulatory notifications required practice
- `number_of_households_affected` — Idadi ya kaya zilizoathirika: World Bank ESS10 GN10: disaggregated impact data required; ICMM (2019) for community-level impact assessment
- `health_symptoms_experienced` — Dalili za kiafya: e.g., Respiratory / Skin rash / Gastrointestinal / Eye irritation; IFC PS4 (2012) para. 5-10: documentation of health impacts from mining required
- `medical_records_available` — Je, rekodi za daktari zinapatikana? (Ndiyo/Hapana): IFC PS4: medical evidence required to trigger medical support obligations under PS4

**If issue_type = Land Acquisition / Compensation Dispute:**
Also collect:
- `land_area_affected_hectares` — Eneo la ardhi lililoathirika (hekta): IFC PS5 GN5: land area measurement explicitly required for compensation calculation; Tanzania Mining Act s.97
- `land_title_type` — Aina ya hati ya ardhi: Right of Occupancy / Certificate of Title / Customary Land / No Formal Title; determines compensation framework
- `crop_type_affected` — Aina ya mazao yaliyoathirika: IFC PS5 GN5: asset inventory for livelihood restoration programme
- `crop_loss_estimated_value_tzs` — Thamani ya mazao yaliyopotea (TZS): IFC PS5 GN5: damage valuation required; Tanzania Mining Act s.97 compensation basis
- `livestock_type_and_number_lost` — Aina na idadi ya mifugo iliyopotea: IFC PS5 GN5: livestock loss is a standard asset category in mining compensation registers
- `number_of_households_displaced` — Idadi ya kaya zilizohama: IFC PS5: household census required for resettlement plan; World Bank ESS10 disaggregated impact data
- `compensation_offered` — Je, fidia iliotolewa? (Ndiyo/Hapana): IFC PS5; Tanzania Mining Act s.97 compensation tracking
- `compensation_amount_tzs` — Kiasi cha fidia kilichotolewa (TZS): Comparison with asset valuation determines adequacy; IFC PS5 requires replacement value (not depreciated market value)
- `compensation_accepted` — Je, fidia ilikubaliwa? (Ndiyo/Hapana/Inaendelea kujadiliwa): ICMM (2019): resolution must be "based on engagement and dialogue"; forced acceptance is invalid
- `minerals_commission_case_number` — Nambari ya kesi ya Minerals Commission (kama ipo): Tanzania Mining (Dispute Resolution) Rules 2021: complaints are "registered and given a number"; cross-referencing required

**If issue_type = Worker Safety Incident / Occupational Injury:**
Also collect:
- `injury_occurred` — Je, kulikuwa na majeraha? (Ndiyo/Hapana): ISO 45001:2018 Clause 10.2: mandatory field
- `injury_type` — Aina ya jeraha: Rock Fall / Explosion / Entrapment / Electrical / Chemical Exposure / Silica Dust (long-term) / Equipment Accident / Gas Poisoning / Near Miss
- `injury_severity` — Ukali wa jeraha: Fatality / Serious (hospitalization) / Minor / First Aid Only / Near Miss; determines OSHA notification requirement under Tanzania OHS Act 2003
- `number_injured` — Idadi ya walioumia: ISO 45001:2018 Clause 10.2; notification threshold under Tanzania OHS Act
- `osha_notified` — Je, OSHA waliarifu? (Ndiyo/Hapana): Tanzania OHS Act No. 5 of 2003: fatal and serious injuries must be reported to OSHA within 24 hours
- `osha_reference_number` — Nambari ya kesi ya OSHA: Cross-referencing regulatory notification
- `ppe_provided` — Je, vifaa vya kinga (PPE) vilitolewa? (Ndiyo/Hapana/Aina): ISO 45001 compliance indicator; ICMM (2019): safety performance tracking
- `incident_location_underground_surface` — Tukio lilitokea chini ya ardhi au juu? (Chini / Juu / Kiwanda): Determines investigation protocol and reporting category
- `witness_names_contacts` — Majina na nambari za mashahidi: ISO 45001:2018 Clause 10.2: "witness names and contact details" required in incident reports

**If issue_type = Blast Damage (Community Property):**
Also collect:
- `property_damage_description` — Maelezo ya uharibifu wa mali: IFC PS5 GN5: property damage valuation required; Tanzania Mining Act s.109 (pollution liability)
- `property_damage_value_tzs` — Thamani ya uharibifu (TZS): Required for compensation claim under Tanzania Mining Act
- `blasting_frequency_agreed` — Mlipuko ulikubalika mara ngapi kwa wiki: Comparison with actual frequency establishes licence breach
- `blasting_frequency_actual` — Mlipuko unafanyika mara ngapi kwa wiki: Tanzania Mining Act and TMAA permit specify permitted blasting hours and frequency
- `photos_evidence_attached` — Picha / ushahidi umeambatishwa? (Ndiyo/Hapana): IFC GPN (2009): photographic evidence is primary support for blast damage claims
- `tmaa_previously_notified` — Je, TMAA waliarifu? (Ndiyo/Hapana): TMAA has jurisdiction over mining operations compliance

**If issue_type = Employment Discrimination / Local Content Failure:**
Also collect:
- `employment_category` — Aina ya mgogoro wa ajira: Hired from Outside Community / Wage Discrimination / Wrongful Dismissal / No Payslip / Skills Training Not Delivered / Union Access Denied
- `local_content_percentage_claimed` — Asilimia inayodaiwa ya maudhui ya ndani: Tanzania Mining Act: local content requirements are licence conditions; percentage claimed vs. actual is the evidence base
- `number_of_workers_affected` — Idadi ya wafanyakazi walioathirika: Scales the scope; individual vs. systemic issue determination
- `tlc_or_union_notified` — Je, Chama cha Wafanyakazi (TLC) kiliarifu? (Ndiyo/Hapana): Tanzania Labour laws: union rights; TLC or CMA (Commission for Mediation and Arbitration) may have jurisdiction

**If issue_type = CSR / Community Development Fund Failure:**
Also collect:
- `cda_or_benefit_agreement_exists` — Je, mkataba wa maendeleo ya jamii (CDA) upo? (Ndiyo/Hapana): Determines contractual basis for community benefit claim
- `promised_benefit_type` — Aina ya faida iliyoahidiwa: Road / School / Clinic / Water / Bursaries / CDF Disbursement / Agricultural Support / Skills Training
- `promised_benefit_value_tzs` — Thamani ya faida iliyoahidiwa (TZS): Quantifies the unfulfilled obligation
- `years_since_promise` — Miaka tangu ahadi: Duration of non-delivery
- `cdf_disbursement_amount_expected_tzs` — Kiasi cha CDF kinachotarajiwa (TZS): Tanzania Mining Act and CDA terms establish disbursement obligations

**If issue_type = Artisanal Mining (ASM) Issues:**
Also collect:
- `asm_licence_status` — Hali ya leseni ya mchimbaji mdogo: Licensed (PML) / Unlicensed / Pending Application / Expired; Tanzania Mining Act: licence status determines rights of the ASM miner
- `tmaa_application_reference` — Nambari ya maombi ya TMAA: For PML applications that have been pending without response
- `large_scale_mine_encroachment` — Je, mgodi mkubwa unaingia kwenye eneo la mchimbaji mdogo? (Ndiyo/Hapana): Tanzania Mining Act: boundaries between LSM and ASM areas are legally defined
- `security_incident` — Je, walinzi wa usalama walihusika? (Ndiyo/Hapana): Security force conduct against ASM miners is a human rights concern under IFC PS4 and UNGPs
- `mercury_use_disclosed` — Je, mchimbaji anatumia zebaki? (Ndiyo/Hapana): Mercury management is a regulatory and health issue; TMAA and NEMC have jurisdiction; Minamata Convention applies

### Issue Type Classification

| Code | Issue Type | Swahili |
|------|-----------|---------|
| MN-01 | water_contamination | Uchafuzi wa maji |
| MN-02 | dust_particulate_matter | Vumbi na chembe chembe kutoka mgodini |
| MN-03 | blast_damage_property_crops | Uharibifu wa mali / mazao kutokana na mlipuko |
| MN-04 | land_acquisition_compensation | Fidia ya ardhi / ununuzi wa ardhi |
| MN-05 | resettlement_displacement | Uhamisho wa makazi / jamii |
| MN-06 | acid_mine_drainage | Maji ya asidi kutoka mgodini |
| MN-07 | tailings_spill_overflow | Kumwagika kwa taka za madini |
| MN-08 | chemical_spill_cyanide_mercury | Kumwagika kwa kemikali / sianidi / zebaki |
| MN-09 | worker_safety_incident | Tukio la usalama la mfanyakazi |
| MN-10 | employment_discrimination | Ubaguzi wa ajira / kutokuajiri wenyeji |
| MN-11 | local_content_failure | Kushindwa kufuata masharti ya maudhui ya ndani |
| MN-12 | wage_dispute | Mgogoro wa mshaharo |
| MN-13 | csr_community_benefit_failure | Kushindwa kutoa faida ya CSR / CDF |
| MN-14 | community_health_impact | Athari za kiafya kwa jamii |
| MN-15 | asm_encroachment_rights | Uvamizi wa eneo la mchimbaji mdogo |
| MN-16 | security_force_misconduct | Mwenendo mbaya wa walinzi wa usalama |
| MN-17 | land_reclamation_failure | Kushindwa kufanya ukarabati wa ardhi |
| MN-18 | boundary_encroachment | Uvamizi wa mpaka wa leseni |
| MN-19 | intimidation_rights_violation | Vitisho dhidi ya walalamikaji |
| MN-20 | royalty_transparency | Uwazi wa ada za madini |
| MN-21 | noise_vibration | Kelele na mtetemo unaosababishwa na mgodi |
| MN-22 | environmental_certificate_lapse | Cheti cha mazingira kimeisha muda wake |

### Resolution Standards for This Industry

- **ICMM (2019) effectiveness criteria:** Mechanisms must be Legitimate, Accessible, Predictable, Equitable, Transparent, Rights-Compatible, a Source of Continuous Learning, and Based on Engagement and Dialogue. All eight criteria should guide response protocols.
- **Mining Commission (Tanzania):** Tanzania Mining (Dispute Resolution) Rules 2021: complaints are registered and given a case number. The Minerals Commission has jurisdiction over compensation assessment, boundary disputes, and other prescribed mining disputes under Mining Act s.119. Required documentation: written complaint ("Memorandum of Complaint briefly stating subject matter and relief sought"), evidence of impact, mine licence number.
- **NEMC process (Tanzania):** Environmental complaints referred to NEMC under Environmental Management Act Cap. 191. NEMC can issue enforcement notices, stop orders, and fines. Required: GPS coordinates, description of pollution, evidence, names of affected parties.
- **OSHA process (Tanzania OHS Act 2003):** Fatal or serious workplace injuries must be reported to OSHA within 24 hours. OSHA investigates, can impose improvement notices and prosecution.
- **IFC PS5 compensation standard:** Land-linked grievances require independent valuation; replacement value (not depreciated market value) is the minimum standard. Compensation must be paid before displacement occurs.
- **IFC GPN timelines:** Acknowledgement within 5-10 business days; resolution within 30 days for standard cases; complex community cases may extend to 90 days with written explanation.
- **ICMM (2019) escalation path:** Company CLO → Mine Management → Corporate Level → External Mediation → Minerals Commission / NEMC / OSHA / Courts; path must be communicated to complainants.

### Escalation Triggers (field values that require immediate escalation)

- `issue_type = worker_safety_incident` AND `injury_severity = Fatality` — OSHA notification within 24 hours (OHS Act 2003); emergency escalation; site inspection; criminal liability assessment
- `issue_type = worker_safety_incident` AND `injury_severity = Serious` — OSHA notification within 24 hours; priority case; site work suspension pending investigation
- `issue_type = tailings_spill_overflow` — Environmental catastrophe; immediate NEMC and OSHA notification; potential public health emergency; community evacuation assessment
- `issue_type = chemical_spill_cyanide_mercury` — Public health emergency; notify NEMC, TFDA (Tanzania Food and Drugs Authority), and MEM immediately; advise community not to use affected water
- `issue_type = water_contamination` AND `health_symptoms_experienced` includes gastrointestinal or respiratory — Public health emergency; NEMC and TFDA notification; medical assistance for affected community
- `issue_type = security_force_misconduct` AND `injury_occurred = Yes` — Human rights violation (IFC PS4, UNGPs); escalate to corporate human rights officer; advise police report
- `issue_type = land_acquisition_compensation` AND `number_of_households_displaced > 0` AND `compensation_offered = No` — IFC PS5 violation; escalate to ESG/Social Officer and Minerals Commission
- `issue_type = intimidation_rights_violation` — UNGPs Pillar III: threats against complainants are a human rights violation; escalate to corporate governance and potentially NGO partners
- `environmental_certificate_lapse = Yes` AND production continuing — Regulatory violation; notify NEMC immediately; potential production suspension
- `issue_type = asm_encroachment_rights` AND `security_incident = Yes` — Security force misconduct against ASM miners; IFC PS4 and UNGPs; escalate to corporate security standards officer
- `issue_type = blast_damage_property_crops` AND `number_of_households_affected > 10` — Community-level impact; escalate to Mining Commission and company community affairs
- `vulnerability_status` includes Indigenous Community — IFC PS7 triggers; Free, Prior, and Informed Consent (FPIC) assessment required; escalate to senior social performance officer

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina la mtoa maoni (hiari) | Optional | ICMM (2019): confidentiality is an effectiveness criterion; anonymous suggestions must be permitted |
| contact_details | Mawasiliano (hiari) | Optional | Required only if submitter wants a response |
| community_village | Kijiji / jamii | Yes | Routes suggestion to the mine's Community Liaison Officer for the correct geographical area |
| mine_company_name | Jina la mgodi / kampuni | Yes | Routes suggestion to the correct mine's CSR/community function |
| suggestion_category | Kategoria ya mapendekezo | Yes | See categories below |
| suggestion_detail | Maelezo ya mapendekezo | Yes | Free text; core substance of the suggestion |
| suggested_beneficiary | Wanaofaidika na pendekezo hili | Recommended | Options: Jamii / Wafanyakazi / Mazingira / Wachimbaji Wadogo / Serikali ya Mtaa |
| urgency | Kiwango cha haraka | Yes | Options: Kawaida / Inayohitaji haraka (e.g., safety-related); ICMM (2019) recommends prioritization of suggestions with safety implications |
| channel_submitted | Njia ya kuwasilisha | Auto | Omnichannel analytics |

### Industry-Specific Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| MS-01 | environmental_management | Usimamizi bora wa mazingira |
| MS-02 | water_management | Usimamizi wa maji |
| MS-03 | dust_noise_reduction | Kupunguza vumbi na kelele |
| MS-04 | local_employment_procurement | Ajira na manunuzi ya ndani |
| MS-05 | community_investment_csr | Uwekezaji wa CSR / CDF |
| MS-06 | compensation_process | Mchakato bora wa fidia |
| MS-07 | resettlement_process | Mchakato bora wa uhamisho wa makazi |
| MS-08 | worker_safety | Usalama wa wafanyakazi wa mgodi |
| MS-09 | asm_formalization | Urasimishaji wa wachimbaji wadogo |
| MS-10 | reclamation_rehabilitation | Ukarabati na urejesho wa ardhi |
| MS-11 | community_grievance_access | Upatikanaji bora wa mfumo wa malalamiko |
| MS-12 | transparency_reporting | Uwazi wa taarifa na takwimu za mgodi |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| inquirer_name | Jina la mwulizaji | Recommended | IFC GPN: identity useful for response routing; not required for anonymous inquiries |
| contact_details | Mawasiliano | Yes | Required to deliver response; ICMM (2019): "accessible" mechanism requires response capability |
| community_village | Kijiji / jamii | Yes | Contextualizes inquiry; routes to CLO responsible for that community |
| mine_company_name | Jina la mgodi / kampuni | Yes | Routes to correct mine's information officer or CSR team |
| inquiry_type | Aina ya swali | Yes | Routes to correct knowledge base or officer |
| inquiry_detail | Maelezo ya swali | Yes | Free text; core question |
| urgency | Kiwango cha haraka | Yes | Options: Kawaida / Inayohitaji haraka |
| preferred_contact_method | Njia unayopendelea ya mawasiliano | Yes | ICMM (2019): accessible mechanism; many mining community members prefer Swahili SMS or village-leader-mediated response |
| preferred_language | Lugha unayopendelea | Yes | ICMM (2019): culturally appropriate; World Bank ESS10 GN10: mechanisms must be in local languages. Options: Kiswahili / Sukuma / Nyamwezi / English / Nyingine |
| inquiry_reference_number | Nambari ya marejeleo (otomatiki) | Auto | All interactions must be trackable per IFC GPN |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Swahili | Additional Fields to Collect |
|-------------|---------|------------------------------|
| compensation_process | Mchakato wa fidia ya ardhi au mazao | community_village, land_area_affected_hectares |
| environmental_monitoring | Matokeo ya uchunguzi wa mazingira | pollution_type, water_source_affected |
| employment_criteria | Vigezo vya ajira kwenye mgodi | community_village, mine_company_name |
| resettlement_information | Taarifa za uhamisho wa makazi | community_village, number_of_households_displaced |
| land_boundary | Mipaka ya leseni ya uchimbaji | mining_licence_number, gps_coordinates_incident |
| royalty_cdf_distribution | Usambazaji wa ada za madini na CDF | mine_company_name, community_village |
| safety_procedures | Taratibu za usalama wa mgodi | mine_company_name, incident_location_underground_surface |
| water_quality_results | Matokeo ya uchunguzi wa ubora wa maji | water_source_affected, gps_coordinates_incident |
| mine_closure_plan | Mpango wa kufunga mgodi | mine_company_name, mining_licence_number |
| asm_licence_application | Mchakato wa kuomba leseni ya mchimbaji mdogo | submitter_name, community_village, tmaa_application_reference |
| regulatory_complaint_process | Jinsi ya kuwasilisha malalamiko na TMAA/NEMC/OSHA | issue_type, mine_company_name |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina la mtoa pongezi (hiari) | Optional | ICMM (2019): feedback loops for continuous learning; name optional |
| contact_details | Mawasiliano (hiari) | Optional | If submitter wants acknowledgement |
| community_village | Kijiji / jamii | Yes | Routes compliment to correct CLO and mine community function |
| mine_company_name | Jina la mgodi / kampuni | Yes | Identifies the entity being commended |
| person_team_commended | Jina la mtu / timu inayopongezwa | Recommended | Enables individual recognition; ICMM (2019): recognition is part of positive feedback loop |
| commendation_category | Kategoria ya pongezi | Yes | See categories below |
| commendation_detail | Maelezo ya pongezi | Yes | Free text narrative; captures specific reasons for praise |
| overall_satisfaction_rating | Kiwango cha ridhaa (1-5) | Yes | ICMM (2019): outcome-based evaluation; satisfaction rating is part of mechanism effectiveness assessment |
| date_of_interaction | Tarehe ya tukio / mazungumzo | Recommended | Correlates compliment with specific project phase, personnel, or community event |

### Commendation Categories

| Code | Category | Swahili |
|------|----------|---------|
| MA-01 | community_investment | Uwekezaji katika jamii |
| MA-02 | environmental_restoration | Urejesho wa mazingira |
| MA-03 | local_employment | Ajira za wenyeji |
| MA-04 | communication_transparency | Uwazi na mawasiliano na jamii |
| MA-05 | compensation_fairness | Haki ya fidia |
| MA-06 | safety_performance | Rekodi nzuri ya usalama |
| MA-07 | water_land_rehabilitation | Ukarabati wa maji na ardhi |
| MA-08 | asm_support | Msaada kwa wachimbaji wadogo |
| MA-09 | grievance_responsiveness | Kuitika haraka malalamiko ya jamii |
| MA-10 | skills_training | Mafunzo ya ujuzi kwa wenyeji |

---

## AI Conversation Guidance for This Industry

- **Establish whether the speaker is a community member or a worker before any other field.** Ask "Je, unazungumza kama mwanajamii anayeathiriwa na mgodi, au kama mfanyakazi wa mgodi?" — community complaints route to CLO, CSR, and NEMC pathways; worker complaints route to mine safety officer, OSHA, and labour law pathways. These are entirely different flows with different fields.
- **For environmental complaints, collect the water source type and GPS location before describing the problem.** Ask "Chanzo cha maji kilichoathirika ni nini — kisima, mto, borehole, au maji ya bomba?" and "Tunaweza kupata mahali halisi pa GPS au maelezo ya njia ya kufika?" — these two fields determine whether NEMC, TFDA, or public health authorities are the primary responder.
- **For land compensation complaints, ask how many households are affected before quantifying the individual claim.** "Je, familia ngapi au kaya ngapi zimeathiriwa, au ni wewe peke yako?" — this determines whether the response is an individual compensation claim (handled directly) or a collective resettlement issue (requiring community consultation and a Resettlement Action Plan).
- **For safety incidents, immediately collect injury severity and OSHA notification status.** "Je, kulikuwa na mtu aliyeumia au kufariki? Je, OSHA walishaarifu?" — if the answer involves a fatality or serious injury and OSHA has not been notified, this is the single most urgent compliance action and must be flagged before collecting any other field.
- **Never ask for GPS coordinates directly from community members in rural mining areas** — most will not have smartphones. Instead ask "Tunaweza kupata jina la kijiji chako na dira ya kuelekea mgodi?" and collect descriptive location data that a CLO can convert to coordinates during field verification.
- **For ASM complaints, collect licence status before issue details.** "Je, una leseni ya Primary Mining Licence (PML) au bado unaomba?" — an unlicensed ASM miner and a licensed one have very different legal rights, and the complaint pathway (TMAA support vs. criminal risk vs. rights complaint) differs significantly.
- **For blast damage and vibration complaints, collect the agreed vs. actual blasting frequency** — many community benefit agreements and mining licences specify permitted blast frequency and hours. Ask "Mlipuko ulikubalika kufanywa mara ngapi kwa wiki na wakati gani?" vs. "Kwa kweli unafanywa mara ngapi?" — this comparison is the primary evidence for a licence breach complaint.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Speaker role | "Je, unazungumza kama mwanajamii anayeathiriwa na mgodi, au kama mfanyakazi wa mgodi?" |
| Community / village | "Unaitwa kijiji gani, na iko katika kata na wilaya gani?" |
| Mine company name | "Mgodi au kampuni ya madini inayohusika inaitwa nani?" |
| Distance from mine | "Kijiji chako kiko umbali gani kutoka mpaka wa mgodi — ni karibu au mbali?" |
| Water contamination source | "Chanzo cha maji kilichoathirika ni kisima, mto, borehole, au maji ya bomba?" |
| Number of households | "Je, familia ngapi au kaya ngapi zimeathiriwa na tatizo hili?" |
| Land area affected | "Eneo la ardhi lililoathirika ni kubwa kiasi gani — ni hekta ngapi au ekari ngapi?" |
| Injury occurred | "Je, kulikuwa na mtu aliyeumia? Majeraha yalikuwa makubwa kiasi gani?" |
| OSHA notified | "Je, Mamlaka ya Usalama na Afya Kazini (OSHA) walishaarifu kuhusu tukio hili?" |
| Compensation offered | "Je, kampuni imetoa fidia yoyote? Kama ndiyo, kiasi gani, na ilikuwa ya haki?" |
| Prior complaint to company | "Je, uliwahi ripoti tatizo hili moja kwa moja kwa kampuni ya mgodi? Nini jibu lao?" |
| ASM licence status | "Je, una leseni ya mchimbaji mdogo (Primary Mining Licence / PML)?" |
| Traditional leader | "Je, kiongozi wa jadi au mwenyekiti wa kijiji alishafahamu kuhusu tatizo hili?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| injury_severity | Fatality | OSHA notification within 24 hours (Tanzania OHS Act 2003); emergency case; mine management and corporate safety officer notification; site suspension pending investigation |
| injury_severity | Serious (hospitalization) | OSHA notification within 24 hours; priority safety ticket; mine medical facility alert |
| issue_type | tailings_spill_overflow OR chemical_spill_cyanide_mercury | Environmental emergency: notify NEMC immediately; advise community not to use affected water; TFDA notification for food/water safety; escalate to corporate EHS |
| issue_type | water_contamination AND health_symptoms_experienced includes GI / respiratory | Public health emergency: advise medical attention; notify NEMC and TFDA; create priority case |
| issue_type | security_force_misconduct AND injury_occurred = Yes | Human rights violation: escalate to corporate human rights officer; advise police report; IFC PS4 and UNGPs trigger |
| issue_type | intimidation_rights_violation | UN Guiding Principles Pillar III: escalate to corporate governance; consider referral to human rights NGO; document thoroughly |
| issue_type | land_acquisition_compensation AND compensation_offered = No AND number_of_households_displaced > 0 | IFC PS5 violation: escalate to ESG/Social Performance Officer; refer to Minerals Commission; no further displacement without compensation |
| vulnerability_status | Indigenous Community | IFC PS7 trigger: escalate to senior social performance officer; FPIC assessment required; different consultation standards apply |
| environmental_certificate_lapse | Yes | Regulatory violation: notify NEMC; production may not legally continue; create compliance emergency ticket |
| issue_type | asm_encroachment_rights AND asm_licence_status = Licensed (PML) | Licensed ASM miner has legal rights: refer to TMAA; document boundary evidence; escalate if mine is operating outside its SML/ML boundary |
| previous_complaint_to_company | Yes AND company_response = None | ICMM (2019) mechanism failure: escalate internally; complainant may now access external pathways (Minerals Commission, NEMC, courts) |
| issue_type | csr_community_benefit_failure AND cda_or_benefit_agreement_exists = Yes | Contractual breach: document CDA terms vs. actual delivery; route to Minerals Commission under Mining Act s.119; escalate to corporate CSR function |
| nemc_previously_notified | No AND issue_type is environmental | Advise complainant to notify NEMC at eia.nemc.or.tz or email eiasupport@nemc.or.tz; create case record with NEMC reference when obtained |
| osha_notified | No AND injury_severity is Fatality or Serious | Critical compliance failure: notify OSHA immediately; document the gap in notification as a secondary regulatory breach |

---

*Sources: ICMM Grievance Mechanism Guidance (December 2019), IFC GPN (2009), IFC PS1/PS4/PS5 GN5/PS7 (2012), World Bank ESS10 GN10 (2018), EBRD GN (2012), ISO 45001:2018 Clause 10.2, Tanzania Mining Act Chapter 123 s.97/107/109/119 (as amended 2019), Tanzania Mining (Dispute Resolution) Rules 2021, Tanzania OHS Act No. 5 of 2003, Tanzania Environmental Management Act Cap. 191, CAO Ombudsman Advisory Note, UN Guiding Principles on Business and Human Rights (UNGPs)*
