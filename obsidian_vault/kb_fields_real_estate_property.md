---
tags: [industry-kb, field-standards, feedback-fields]
---
# Real Estate / Property Management — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: landlord, mwenye nyumba, tenant, mpangaji, rent, kodi ya nyumba, lease, mkataba wa kukodisha, deposit, amana, property manager, estate agent, wakala wa mali asiyehamika, property developer, mjenzi wa nyumba, MLHHSD, land registry, right of occupancy, RO, certificate of title, hati ya ardhi, conveyancing, stamp duty, caveat, mortgage, plot, kiwanja, bedsitter, studio, gated community, service charge, ada ya huduma, facility manager, caretaker, bwana nyumba, eviction notice, notice ya kuondoka, rent tribunal, mahakama ya kodi, ground rent, title deed, land rent, title transfer, scheme of subdivision, habitation licence, occupation certificate, NSSF housing, NHC, real estate broker, property valuation, off-plan, beacons, survey plan, strata title, derivative right, right of occupancy renewal, BRELA developer registration, property management AGM, block of flats, ghorofa, service apartment, commercial lease, nyumba ya biashara, security deposit withheld, mold, ukungu, pest infestation, wadudu, structural crack, lift broken, water pump failed, property misrepresentation, title fraud, double sale

## Why Industry-Specific Fields Matter

A tenant's deposit dispute (requiring tenancy reference, move-out inspection record, and deduction breakdown), a title fraud complaint (requiring land registry search reference, caveat details, and police report), and a habitability complaint (requiring health impact documentation and prior written notice to landlord) each route to different jurisdictions — Rent Tribunal, land registry/courts, and local authority inspectorate respectively — and are resolved under different sections of the Land Act, Rent Restriction Act, and property management regulations. Generic fields produce unactionable tickets that no regulator can process.

## Source Standards

- RICS Complaints Handling Procedure (CHP) and Complaint Log Template — mandatory for all RICS-regulated firms (1st edition)
- RICS Global Complaints Procedure and two-stage CHP framework (Stage 1: 7 days; Stage 2: 8 weeks)
- US NCREC (North Carolina Real Estate Commission) complaint form field standards
- Pennsylvania State Real Estate Commission complaint form requirements
- Los Angeles Housing Department (LAHD) RSO complaint form — for rent overcharge and habitability
- California Department of Real Estate (DRE) complaint form standards
- EU Environmental Impact Assessment Directive 2011/92/EU as amended by 2014/52/EU, Articles 6 and 11 (public participation and access to justice)
- IFC Performance Standard 5: Land Acquisition and Involuntary Resettlement (2012) — applicable to developer displacement
- Tanzania Land Act Cap. 113 (1999) and Land (Assessment of the Value of Land for Compensation) Regulations
- Tanzania Rent Restriction Act (Cap. 479) and Rent Tribunal procedures
- Tanzania Real Estate Agency Act and BRELA compliance requirements
- MLHHSD (Ministry of Lands, Housing and Human Settlements Development) title and conveyancing procedures
- ISO 10002:2018 Quality management: guidelines for complaints handling in organisations

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | RICS CHP Log: "Full name(s)" explicitly required; IFC GPN (2009): complainant identification is a mandatory record field |
| complainant_phone | Nambari ya simu | Yes | RICS CHP Log: "all available contact information" required; needed to communicate resolution |
| complainant_email | Barua pepe | Recommended | RICS CHP: written correspondence must be documented; recommended for formal acknowledgement |
| complainant_address | Anwani ya mlalamikaji | Recommended | RICS CHP Log: "all available contact information (address, telephone, fax, email)" required |
| special_circumstances | Mazingira maalum / udhaifu | Yes | RICS CHP Log: "any special circumstances or impairments" is an explicit required field; enables accessibility adjustments |
| anonymity_flag | Je, una hamu ya kukaa bila kutambulika? | Yes | IFC GPN (2009): mechanisms must permit anonymous complaints; even anonymous complaints must be counted |
| gender | Jinsia | Yes | World Bank ESS10 GN10: gender-disaggregated data required for monitoring reporting |
| complainant_relationship_to_property | Uhusiano wako na mali | Yes | Determines applicable rights framework. Options: Tenant (Mpangaji) / Buyer (Mnunuzi) / Leaseholder / Owner-Occupier / Neighbour / Agent |
| tenancy_reference_or_lease_number | Nambari ya kukodisha / mkataba | Recommended | Standard across NCREC, Pennsylvania, LAHD complaint forms; links complaint to specific tenancy record |
| property_address_full | Anwani kamili ya mali | Yes | Universally required across all major property complaint forms (NCREC, Pennsylvania, LAHD, DRE California) |
| unit_number | Nambari ya ghorofa / chumba | Recommended | Identifies specific unit within multi-occupancy buildings; standard in tenant complaint templates |
| property_type | Aina ya mali | Yes | Drives applicable regulations. Options: Residential (Nyumba ya Kuishi) / Commercial (Jengo la Biashara) / Industrial / Land (Ardhi) / Mixed Use |
| respondent_name | Jina la mwenye nyumba / mjenzi / wakala | Yes | RICS CHP Log: "Relevant Person (firm or individual name)" is an explicit required field |
| respondent_contact_details | Mawasiliano ya mshtakiwa | Recommended | Required for investigation and to serve notice of complaint |
| property_management_company | Kampuni ya usimamizi wa mali | Recommended | Required where management company is a separate entity from owner |
| multiple_complaints_same_respondent | Je, kuna malalamiko mengine dhidi ya huyu mtu? (Ndiyo/Hapana) | Yes | RICS CHP Log: "whether multiple complaints exist about same individual" is an explicit required field; identifies repeat offenders |
| issue_type | Aina ya tatizo / kategoria | Yes | RICS CHP; LAHD RSO form: categorization required for routing; determines regulatory jurisdiction |
| date_issue_first_arose | Tarehe tatizo lilianza | Yes | RICS CHP and all complaint forms: "date of service or incident" required; starts limitation period |
| issue_description | Maelezo kamili ya tatizo | Yes | RICS CHP Log: full "what, where, when, who, why" description; ISO 10002:2018 clause 8.2: nature of complaint with relevant details required |
| prior_written_notice_to_respondent | Je, mwenye nyumba / wakala aliarifu kwa maandishi? (Ndiyo/Hapana/Tarehe) | Yes | Standard across all tenant complaint forms; demonstrates prior attempt at resolution before formal complaint |
| financial_loss_amount_tzs | Hasara ya fedha / kiasi kinachogombaniwa (TZS) | Yes | RICS CHP Log: financial impact documentation; all forms require quantification of loss |
| photos_evidence_attached | Picha / ushahidi umeambatishwa? (Ndiyo/Hapana) | Yes | RICS CHP: "complainant can enclose evidence such as photographs"; critical for habitability and damage claims |
| desired_outcome | Matokeo unayotaka | Yes | RICS CHP two-stage process: complainant's desired remedy must be documented; options: Refund / Repair / Compensation / Apology / Regulatory Action |
| preferred_contact_method | Njia unayopendelea ya mawasiliano | Yes | Options: SMS / WhatsApp / Simu / Barua pepe; RICS CHP requires written acknowledgement |
| date_received | Tarehe ya kupokea malalamiko | Auto | RICS CHP Log: "date complaint received" AND "date complaint logged" are both explicit required fields |
| logged_by | Imerekodiwa na nani | Auto | RICS CHP Log: "Logged by" is an explicit required field |

### Conditional Fields (collect based on issue type)

**If issue_type = Deposit Dispute (Deposit Withheld / Deducted Improperly):**
Also collect:
- `deposit_amount_paid_tzs` — Kiasi cha amana kilicholipwa (TZS): Required by Pennsylvania, LAHD, NCREC complaint forms; quantifies the claim
- `deposit_return_deadline_passed` — Je, tarehe ya kurudisha amana imepita? (Ndiyo/Hapana): Determines if landlord is in default of legal obligation
- `deduction_reason_provided` — Je, mwenye nyumba alitoa sababu ya kukatwa? (Ndiyo/Hapana/Maandishi): Without written breakdown, deduction is presumed improper under most property law frameworks
- `move_out_inspection_done` — Je, ukaguzi wa kuondoka ulifanywa? (Ndiyo/Hapana): Joint inspection record is primary evidence for deposit disputes
- `move_in_inventory_signed` — Je, orodha ya hali ya nyumba ilitiwa sahihi wakati wa kuingia? (Ndiyo/Hapana): Signed inventory establishes baseline condition

**If issue_type = Illegal / Unlawful Eviction:**
Also collect:
- `eviction_method` — Jinsi ya kufukuzwa: Lock Change / Utility Cutoff / Threats / Physical Force / Court Order (legitimate); determines legality
- `valid_lease_in_force` — Je, mkataba wa kukodisha bado unaendelea? (Ndiyo/Hapana): Determines tenant's legal right to remain
- `eviction_notice_received` — Je, notisi ya kuondoka ilipokelewa? (Ndiyo/Hapana/Siku ngapi): Determines notice adequacy; Tanzania law requires minimum notice period
- `court_order_exists` — Je, amri ya mahakama ilitolewa? (Ndiyo/Hapana): Eviction without court order is unlawful in Tanzania
- `rent_tribunal_case_number` — Nambari ya kesi ya mahakama ya kodi (kama ipo): Cross-reference existing proceedings

**If issue_type = Rent Overcharge / Illegal Rent Increase:**
Also collect:
- `current_monthly_rent_tzs` — Kodi ya sasa ya kila mwezi (TZS): LAHD RSO; Pennsylvania form: rent amount required for overcharge calculation
- `agreed_monthly_rent_tzs` — Kodi iliyokubaliwa kwenye mkataba (TZS): Baseline for dispute quantification
- `rent_increase_notice_days` — Onyo la ongezeko lilitolewa siku ngapi kabla: Determines notice adequacy; Tanzania Rent Restriction Act prescribes minimum notice
- `rent_denomination` — Sarafu ya kodi: TZS / USD; USD rent demands may violate Tanzania foreign exchange regulations
- `receipt_provided` — Je, risiti za kodi zilitolewa? (Ndiyo/Hapana): Lack of receipts prevents complainant from proving payment

**If issue_type = Habitability / Maintenance Failure / Property Conditions Below Standard:**
Also collect:
- `maintenance_issue_type` — Aina ya tatizo la matengenezo: Roof Leak / Water Supply / Electrical Fault / Drainage / Mold / Structural Crack / Pest Infestation / Lift Broken / Fire Safety; may select multiple
- `issue_duration_weeks` — Tatizo limekuwapo kwa wiki ngapi: Quantifies neglect period; extended periods strengthen habitability claim
- `written_maintenance_request_sent` — Je, ombi la matengenezo lilitumwa kwa maandishi? (Ndiyo/Hapana/Tarehe): Prior notice to landlord is required before most habitability escalations
- `health_impact` — Je, tatizo limeathiri afya ya wakazi? (Ndiyo/Hapana): Mold, pest, and electrical faults with health impact trigger higher-priority response
- `health_symptoms` — Dalili za kiafya: e.g., Respiratory / Skin / Stress; required for health-linked habitability claims
- `children_elderly_disabled_affected` — Je, watoto, wazee, au walemavu wanaathirika? (Ndiyo/Hapana): Vulnerability factor that escalates priority

**If issue_type = Title Dispute / Ownership Fraud / Double Sale:**
Also collect:
- `title_type` — Aina ya hati ya ardhi: Right of Occupancy (RO) / Certificate of Title / Derivative Right / Letter of Allotment / Customary Land
- `title_number` — Nambari ya hati ya ardhi: Required for land registry search and verification
- `caveat_registered` — Je, kuna zuio (caveat) kwenye hati? (Ndiyo/Hapana/Nambari): Undisclosed caveat at point of sale is a vendor misrepresentation
- `land_registry_search_done` — Je, utafutaji wa usajili wa ardhi ulifanywa kabla ya ununuzi? (Ndiyo/Hapana): Determines due diligence by buyer
- `purchase_price_tzs` — Bei ya ununuzi (TZS): NCREC, DRE California: purchase price required for all sales-related complaints
- `payment_made_to_seller_tzs` — Kiasi kilicholipwa kwa muuzaji (TZS): Quantifies financial exposure in fraud cases
- `police_report_number` — Nambari ya ripoti ya polisi: Required for title fraud escalation to land registry and courts
- `second_buyer_identified` — Je, mnunuzi mwingine amejulikana? (Ndiyo/Hapana): Confirms double-sale fraud scenario

**If issue_type = Agent / Developer Misconduct:**
Also collect:
- `agent_rics_or_licence_number` — Nambari ya usajili wa wakala: RICS CHP Log: RICS member number required for regulated firms; Tanzania Real Estate Agency Act requires agent registration
- `reservation_fee_paid_tzs` — Ada ya uhifadhi iliyolipwa (TZS): Critical for developer fraud where reservation fees are collected without delivery
- `off_plan_unit` — Je, ni ununuzi wa off-plan? (Ndiyo/Hapana): Off-plan purchases have specific consumer protection considerations
- `agent_disclosed_dual_agency` — Je, wakala alibali pande mbili za muamala? (Ndiyo/Hapana): Non-disclosure of dual agency is an ethical and legal violation
- `misrepresentation_type` — Aina ya udanganyifu: False Photos / Wrong Property Size / Wrong Title Status / Undisclosed Defects / Boundary Dispute

**If issue_type = Legal Notice / Lease Violation:**
Also collect:
- `legal_notice_type` — Aina ya notisi ya kisheria: Eviction Notice / Demand Letter / Court Summons / Statutory Notice
- `legal_notice_date` — Tarehe ya notisi: Pennsylvania court form; LAHD form: date of legal notice required
- `lease_start_date` — Tarehe ya kuanza kukodisha: Establishes tenancy rights timeline
- `lease_expiry_date` — Tarehe ya kumalizika mkataba: Determines if eviction is within or outside lease term

### Issue Type Classification

| Code | Issue Type | Swahili |
|------|-----------|---------|
| RE-01 | deposit_dispute | Mgogoro wa amana |
| RE-02 | illegal_eviction | Kufukuzwa bila kufuata sheria |
| RE-03 | rent_overcharge | Kukusanya kodi zaidi ya kilichokubaliwa |
| RE-04 | habitability_maintenance_failure | Hali mbaya ya nyumba / kutokufanyia matengenezo |
| RE-05 | unauthorized_landlord_entry | Mwenye nyumba kuingia bila ruhusa |
| RE-06 | title_dispute_ownership_fraud | Mgogoro wa hati / udanganyifu wa umiliki |
| RE-07 | double_sale_fraud | Kuuza mali kwa watu wawili wakati mmoja |
| RE-08 | agent_misconduct | Ulaghai au mwenendo mbaya wa wakala |
| RE-09 | developer_fraud_off_plan | Udanganyifu wa mjenzi wa nyumba za off-plan |
| RE-10 | lease_contract_violation | Ukiukwaji wa mkataba wa kukodisha |
| RE-11 | service_charge_dispute | Mgogoro wa ada ya huduma |
| RE-12 | property_misrepresentation | Kuelezea mali kwa njia ya uongo |
| RE-13 | title_processing_delay | Kuchelewa kwa usindikaji wa hati ya ardhi |
| RE-14 | boundary_survey_dispute | Mgogoro wa mipaka ya ardhi |
| RE-15 | discrimination | Ubaguzi dhidi ya mpangaji au mnunuzi |
| RE-16 | mortgage_foreclosure_dispute | Mgogoro wa utekelezaji wa mkopo wa nyumba |
| RE-17 | planning_zoning_violation | Ukiukwaji wa kanuni za mipango miji |
| RE-18 | compulsory_acquisition | Serikali kuchukua ardhi bila fidia ya haki |

### Resolution Standards for This Industry

- **RICS two-stage CHP (reference standard):** Stage 1 — written acknowledgement and substantive response within 7 days. Stage 2 — final written response within 8 weeks from receipt of original complaint. After 8 weeks without resolution, complainant may access ADR (Alternative Dispute Resolution). RICS-regulated firms must provide ADR details.
- **Tanzania Rent Tribunal:** Tenants may lodge rent disputes with the Rent Tribunal. Required documentation: tenancy agreement, rent receipts, evidence of overcharge or improper deposit deduction, written notice to landlord. Tribunal can order refunds and set rent levels.
- **MLHHSD title disputes:** Title fraud and ownership disputes are handled by land courts and MLHHSD. Required: land registry search results, caveat status, purchase documentation, police report for fraud cases.
- **Tanzania Rent Restriction Act:** Landlords must provide minimum notice before rent increases (specific period varies by court practice; typically 30 days minimum). Eviction without court order is unlawful.
- **Agent regulation (Tanzania):** Real estate agents must be registered under the Tanzania Real Estate Agency Act administered via BRELA. Complaints about unregistered agents may be referred to BRELA and police.
- **Required documentation for escalation:** Tenancy agreement / lease / receipt, deposit payment evidence, move-in/out inspection records, written maintenance requests, photos of defects, prior written notice to landlord.

### Escalation Triggers (field values that require immediate escalation)

- `issue_type = illegal_eviction` AND `eviction_method` includes Lock Change or Physical Force — Unlawful eviction; advise police report; refer to Rent Tribunal as emergency; family may need shelter
- `issue_type = illegal_eviction` AND `children_elderly_disabled_affected = Yes` — Priority escalation; vulnerability factor
- `issue_type = habitability_maintenance_failure` AND `maintenance_issue_type` includes Fire Safety — Life safety; immediate notification of local authority and fire department
- `issue_type = habitability_maintenance_failure` AND `maintenance_issue_type` includes Structural Crack AND building is occupied — Structural emergency; recommend professional assessment and potential evacuation
- `issue_type = developer_fraud_off_plan` AND `reservation_fee_paid_tzs > 5000000` AND developer uncontactable — Probable fraud; advise police report and BRELA notification
- `issue_type = double_sale_fraud` — Immediate land registry caveat lodging advised; police report required; refer to property lawyer
- `issue_type = title_dispute_ownership_fraud` AND `police_report_number` is empty — Advise immediate police report before any further payment or legal action
- `issue_type = rent_overcharge` AND `rent_denomination = USD` — Flag potential violation of Tanzania foreign exchange regulations; refer to legal counsel
- `issue_type = illegal_eviction` AND `court_order_exists = No` — Eviction without court order; advise complainant to seek emergency injunction from Rent Tribunal
- `multiple_complaints_same_respondent = Yes` — Pattern of misconduct; flag for regulatory escalation to BRELA (if agent) or police (if fraud pattern)
- `health_impact = Yes` AND `children_elderly_disabled_affected = Yes` — Escalate habitability complaint to local authority health inspectorate

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina la mtoa maoni (hiari) | Optional | ISO 10002:2018: anonymous suggestions permitted; RICS permits anonymous feedback |
| contact_details | Mawasiliano (hiari) | Optional | Required only if submitter wants a response |
| property_address_or_area | Anwani ya mali / eneo | Yes | Routes suggestion to relevant property manager or policy area |
| agent_or_management_company | Wakala / kampuni inayohusika | Recommended | Enables routing to correct management entity |
| suggestion_category | Kategoria ya mapendekezo | Yes | See categories below |
| suggestion_detail | Maelezo ya mapendekezo | Yes | Free text; core substance of the suggestion |
| urgency | Kiwango cha haraka | Yes | Options: Kawaida / Inayohitaji haraka |
| channel_submitted | Njia ya kuwasilisha | Auto | Omnichannel analytics |

### Industry-Specific Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| RS-01 | maintenance_standards | Kuboresha viwango vya matengenezo |
| RS-02 | communication_process | Kuboresha mawasiliano kati ya mwenye nyumba na mpangaji |
| RS-03 | deposit_process | Mchakato bora wa amana |
| RS-04 | lease_fairness | Usawa wa masharti ya mkataba wa kukodisha |
| RS-05 | service_charge_transparency | Uwazi wa ada za huduma |
| RS-06 | security_access_control | Usalama na udhibiti wa upatikanaji |
| RS-07 | green_sustainability | Hatua za mazingira (solar, maji ya mvua) |
| RS-08 | digital_management_tools | Zana za kidijitali za usimamizi wa mali |
| RS-09 | dispute_resolution_process | Mchakato bora wa kutatua migogoro |
| RS-10 | agent_regulation | Udhibiti bora wa mawakala wa mali asiyehamika |
| RS-11 | title_process_improvement | Kuharakisha mchakato wa hati za ardhi |
| RS-12 | community_amenities | Kuboresha vifaa vya jamii ndani ya makazi |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| inquirer_name | Jina la mwulizaji | Recommended | RICS Stage 1: identity verification before disclosing account or property data |
| contact_details | Mawasiliano | Yes | Required to deliver response; RICS CHP: written acknowledgement required |
| property_address_or_area | Anwani ya mali / eneo | Recommended | Contextualizes inquiry for relevant answer |
| inquirer_relationship | Uhusiano wako na mali | Yes | Tenant / Buyer / Owner / Developer / Agent; determines applicable rights information |
| inquiry_type | Aina ya swali | Yes | Routes to correct knowledge base or officer |
| inquiry_detail | Maelezo ya swali | Yes | Free text; core question |
| urgency | Kiwango cha haraka | Yes | Options: Kawaida / Inayohitaji haraka (e.g., eviction imminent) |
| preferred_response_format | Jinsi unavyotaka jibu | Yes | Options: SMS / Simu / WhatsApp / Barua pepe |
| inquiry_reference_number | Nambari ya marejeleo (otomatiki) | Auto | All interactions must be trackable; RICS CHP requires reference numbers |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Swahili | Additional Fields to Collect |
|-------------|---------|------------------------------|
| tenancy_rights | Haki za mpangaji | tenancy_reference_or_lease_number, lease_start_date |
| eviction_process | Mchakato wa kufukuzwa | valid_lease_in_force, eviction_notice_received, court_order_exists |
| deposit_rules | Kanuni za amana | deposit_amount_paid_tzs, move_out_date |
| rent_increase_rules | Kanuni za ongezeko la kodi | current_monthly_rent_tzs, rent_increase_notice_days |
| title_verification | Uthibitishaji wa hati ya ardhi | title_number, property_address_full |
| purchase_process | Mchakato wa kununua mali | property_type, purchase_price_tzs |
| stamp_duty_rates | Kiwango cha ada ya stempu | purchase_price_tzs, property_type |
| land_registry_process | Mchakato wa usajili wa ardhi | title_type, property_address_full |
| agent_registration | Usajili wa wakala wa mali asiyehamika | agent_name, property_address_full |
| mortgage_collateral | Nyumba kama dhamana ya mkopo | title_type, property_value_estimate_tzs |
| rent_tribunal_process | Mchakato wa mahakama ya kodi | issue_type, property_address_full |
| service_charge_rights | Haki za ada za huduma | property_management_company, property_address_full |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina la mtoa pongezi (hiari) | Optional | For acknowledgement; RICS standards support staff recognition via feedback loops |
| contact_details | Mawasiliano (hiari) | Optional | If submitter wants acknowledgement |
| property_address | Anwani ya mali | Yes | Routes compliment to correct property / management company |
| agent_or_management_company | Wakala / kampuni inayohusika | Yes | Identifies entity being commended |
| person_team_commended | Jina la mtu / timu inayopongezwa | Recommended | Enables individual recognition |
| commendation_category | Kategoria ya pongezi | Yes | See categories below |
| commendation_detail | Maelezo ya pongezi | Yes | Free text narrative |
| overall_satisfaction_rating | Kiwango cha ridhaa (1-5) | Yes | RICS CHP Log: "Complainant satisfaction status" is an explicit required field; repurposed for commendation satisfaction tracking |
| date_of_interaction | Tarehe ya mazungumzo / tukio | Recommended | Correlates with personnel and property records |

### Commendation Categories

| Code | Category | Swahili |
|------|----------|---------|
| RA-01 | maintenance_responsiveness | Kujibu haraka maombi ya matengenezo |
| RA-02 | agent_professionalism | Utaalamu wa wakala |
| RA-03 | communication_clarity | Uwazi wa mawasiliano |
| RA-04 | complaint_resolution_speed | Kasi ya kutatua malalamiko |
| RA-05 | deposit_return_fairness | Haki ya kurudisha amana |
| RA-06 | property_condition | Hali nzuri ya mali |
| RA-07 | pricing_transparency | Uwazi wa bei na gharama |
| RA-08 | title_transaction_efficiency | Ufanisi wa muamala wa hati ya ardhi |
| RA-09 | lease_flexibility | Kubadilika kwa masharti ya mkataba |
| RA-10 | emergency_responsiveness | Kuitika kwa haraka wakati wa dharura |

---

## AI Conversation Guidance for This Industry

- **Establish the relationship to the property before any other field.** Ask "Je, wewe ni mpangaji, mnunuzi, mwenye nyumba, au mtu mwingine?" — this single question determines the entire rights framework. A tenant has Rent Tribunal rights; a buyer has conveyancing rights; these are completely different pathways.
- **Collect property address before trying to identify the respondent.** Many complainants know their property address but do not know the formal name of their landlord or management company. Start with the address, then ask "Mwenye nyumba au kampuni ya usimamizi inaitwa nani?" to build out the respondent.
- **For deposit disputes, ask about the move-out inspection immediately.** If no inspection was conducted, this is the most common reason for invalid deductions. Ask "Je, ukaguzi wa nyumba ulifanywa siku mliyoondoka? Je, orodha ya hali ya nyumba ilisainiwa wakati mlipoingia?" — these answers determine the strength of the complaint before any other fact.
- **For eviction complaints, immediately assess whether a court order exists.** Ask "Je, mwenye nyumba alifuata amri ya mahakama, au alifanya hivyo bila idhini ya mahakama?" — eviction without court order is unlawful in Tanzania and triggers urgent Rent Tribunal referral, regardless of other details.
- **Do not ask for RICS registration number or BRELA number directly** — complainants almost never have these. Instead ask "Je, unajua kama wakala huyu amesajiliwa rasmi?" and advise the complainant that Riviwa can check BRELA records.
- **For title fraud, collect financial exposure before procedural details.** Ask "Je, umelipa kiasi gani kwa muuzaji au wakala?" first — the answer determines urgency. Large payments to untraceable parties need immediate police referral, not a standard investigation timeline.
- **For habitability complaints, ask about vulnerability factors early.** "Je, kuna watoto wadogo, wazee, au watu wenye ulemavu wanaoishi kwenye nyumba hiyo?" — this single field escalates a standard maintenance complaint to a priority health and welfare case.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Relationship to property | "Je, wewe ni mpangaji, mnunuzi, mwenye nyumba, au mtu mwingine katika mgogoro huu?" |
| Property address | "Anwani kamili ya mali inayohusika ni nini — mtaa, nambari ya nyumba, na jiji?" |
| Respondent name | "Mwenye nyumba, wakala, au kampuni ya usimamizi inaitwa nani?" |
| Issue type | "Tatizo lako kuu ni nini — amana, kukodisha, hati ya ardhi, matengenezo, au jambo lingine?" |
| Prior notice given | "Je, uliwahi kumwarifu mwenye nyumba au wakala kwa maandishi kuhusu tatizo hili?" |
| Deposit amount | "Ulikabidhi amana ya kiasi gani, na ilikuwa ni miezi mingapi ya kodi?" |
| Move-out inspection | "Ukaguzi wa nyumba ulifanywa wakati wa kuondoka? Je, orodha ya hali ya nyumba ilisainiwa?" |
| Court order for eviction | "Mwenye nyumba alifuata amri ya mahakama, au ulifukuzwa bila idhini ya mahakama?" |
| Health impact | "Je, tatizo hili limeathiri afya ya familia yako au watoto?" |
| Financial loss | "Je, umepoteza pesa ngapi kutokana na tatizo hili — amana, malipo ya awali, au ada ya wakala?" |
| Desired outcome | "Unataka nini kutokea — kupata amana yako, kurekebisha nyumba, kulipwa fidia, au kuchukua hatua za kisheria?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | illegal_eviction AND court_order_exists = No | Urgent: advise complainant to approach Rent Tribunal for emergency injunction; eviction without court order is unlawful |
| issue_type | illegal_eviction AND eviction_method includes Physical Force | Advise police report; create emergency case; refer to Rent Tribunal same day |
| issue_type | deposit_dispute AND deduction_reason_provided = No | Landlord has not provided written deduction breakdown; advise written demand for breakdown; route to Rent Tribunal if unresolved |
| issue_type | developer_fraud_off_plan AND developer uncontactable AND reservation_fee_paid_tzs > 0 | Advise police report and BRELA notification; check developer's BRELA registration status |
| issue_type | double_sale_fraud | Advise immediate caveat registration at land registry; police report mandatory; refer to conveyancing lawyer |
| issue_type | habitability_maintenance_failure AND maintenance_issue_type includes Fire Safety | Life safety: advise immediate notification of local authority fire inspectorate; do not delay for routine investigation |
| issue_type | habitability_maintenance_failure AND health_impact = Yes AND children_elderly_disabled_affected = Yes | Priority escalation to local authority health and housing inspectorate; vulnerability flag |
| multiple_complaints_same_respondent | Yes | Flag for regulatory referral to BRELA or Rent Tribunal; pattern of misconduct indicator |
| issue_type | rent_overcharge AND rent_denomination = USD | Flag potential foreign exchange regulation violation; advise Bank of Tanzania complaint pathway |
| issue_type | title_processing_delay AND delay exceeds 6 months | Advise complainant to write formal inquiry to MLHHSD; escalate to senior land officer |
| issue_type | agent_misconduct AND agent_rics_or_licence_number = None/Unknown | Agent may be unregistered; advise BRELA check; unregistered agents cannot legally charge commission |
| rics_insurer_notified | No (RICS-regulated firm) | RICS CHP Log: insurer notification is an explicit required field; remind RICS-regulated firm of obligation |

---

*Sources: RICS CHP and Complaint Log Template (1st edition), NCREC complaint form, Pennsylvania Real Estate Commission form, LAHD RSO form, California DRE form, EU EIA Directive 2011/92/EU Articles 6 and 11, IFC PS5 GN5 (2012), World Bank ESS10 GN10 (2018), Tanzania Land Act Cap. 113, Tanzania Rent Restriction Act Cap. 479, Tanzania Real Estate Agency Act, MLHHSD title procedures, ISO 10002:2018, IFC GPN (2009)*
