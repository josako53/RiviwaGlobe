---
tags: [industry-kb, field-standards, feedback-fields]
---
# Energy / Utilities / Water — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: TANESCO, DAWASCO, DAWASA, EWURA, REA, TPDC, prepaid meter, LUKU token, token ya umeme, umeme, load shedding, power outage, blackout, electricity bill, water bill, solar panel, mini-grid, off-grid, biogas, LPG, water pump, borehole, sanitation, water kiosk, transformer, substation, distribution line, feeder line, meter reading, reconnection fee, disconnection notice, voltage fluctuation, maji machafu, maji hayaji, mita ya maji, bili ya maji, gesi, PAYGO solar, REA subsidy, lifeline tariff, saidi, saifi, water kiosk, sewage overflow, piped water, E09 error, LUKU, token ya maji

## Why Industry-Specific Fields Matter

Utility complaints span radically different sub-sectors — a power outage (requiring transformer ID, outage duration, and SAIDI/SAIFI metrics), a water contamination report (requiring WHO-defined quality parameters and potential public health escalation), and a prepaid meter dispute (requiring meter number, token reference, and unit consumption history) — all demand different field sets, different regulatory bodies (TANESCO vs. DAWASCO vs. TPDC), and different urgency levels. Generic fields cannot capture the meter number, vulnerability status, or contamination type needed for EWURA complaint adjudication or field dispatch.

## Source Standards

- EWURA Consumer Complaints Settlement Procedure Rules, GN No. 10 of 2013
- EWURA Act Cap 414, Section 34 — complaint handling mandate
- TANESCO Customer Service Charter 2025
- DAWASA Complaint/Feedback Form (dawasa.go.tz/complaints) — live form fields: name, email, phone, area/location, service type, nearest office, message
- WHO Guidelines for Drinking-Water Quality, 4th edition (NCBI Bookshelf NBK579461, NBK579449) — aesthetic and health-based parameters: colour, turbidity, taste, odour; surveillance framework distinguishing health-based from aesthetic complaints
- ISO 10002:2018 — Quality management: guidelines for complaints handling (clauses 8.1–8.5)
- NARUC — Utility Compensation for Service Interruptions (US best practice; financial impact quantification)
- ITU-T E.800 equivalents for energy utilities: SAIDI (System Average Interruption Duration Index) and SAIFI (System Average Interruption Frequency Index) — both require outage duration and number of customers affected
- TCRA Personal Data Protection Regulations 2023 (analogous data consent requirement applies to EWURA-regulated entities)
- California CPUC Medical Baseline / Michigan Critical Care / Puget Sound Energy Life Support (reference for medical vulnerability priority classification — no direct Tanzania equivalent, but EWURA's "specific performance" awards imply critical-need prioritisation)
- Water Supply and Sanitation Act 2019 (Tanzania)
- Electricity Act 2008 (Tanzania)
- Tanzania Energy Policy 2015
- Environmental Management Act 2004 (NEMC jurisdiction over water quality)

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Required by EWURA GN No. 10/2013 prescribed form (First Schedule); DAWASA complaint form requires name |
| complainant_phone_number | Nambari ya simu ya mlalamikaji | Yes | EWURA prescribed form; DAWASA form collects "Namba ya Simu"; used for field team coordination and status updates |
| complainant_email | Barua pepe ya mlalamikaji | Recommended | EWURA online portal and DAWASA form collect "Barua pepe"; required for written acknowledgement |
| complainant_physical_address | Anwani ya makazi ya mlalamikaji | Yes | EWURA requires supply address for fault geolocation and field dispatch |
| supply_address | Anwani ya mahali pa huduma | Yes | EWURA form requires this; may differ from complainant's mailing address; used for meter lookup and field dispatch |
| gps_coordinates | Kuratibu za GPS za mahali pa huduma | Recommended | EWURA-CCC online feedback form uses location data; critical for TANESCO fault dispatch and DAWASA pipeline mapping |
| account_number | Nambari ya akaunti | Yes | Required by EWURA: complaint must identify the account; TANESCO Customer Service Charter references customer account numbers |
| meter_number | Nambari ya mita | Yes | Critical identifier for all metered services; required for meter reading disputes, billing errors, and token issues; EWURA complaint categories specifically reference meter number |
| service_type | Aina ya huduma | Yes | EWURA regulates five sectors; determines complaint routing. Options: Umeme / Maji ya bomba / Maji taka (Sewerage) / Gesi asilia / Petroli |
| service_provider_name | Jina la mtoa huduma | Yes | EWURA Act Cap 414 s.34 requires complaint to name the "supplier of regulated goods or services." Options: TANESCO / DAWASCO / DAWASA / TPDC / Kampuni ya Gesi / REA / Nyingine |
| customer_category | Kategoria ya mteja | Yes | Affects tariff application and complaint priority under EWURA tariff orders. Options: Makazi / Biashara / Viwanda / Kilimo / Taasisi ya umma |
| issue_type | Aina ya tatizo / kategoria | Yes | EWURA accepted categories determine routing, investigation type, and applicable SLA |
| issue_description | Maelezo ya tatizo | Yes | Required by EWURA prescribed form ("material facts or act complained"); ISO 10002:2018 clause 8.2 |
| date_issue_began | Tarehe tatizo lilianza | Yes | Required for EWURA limitation period calculation (12 months general; 24 months poor quality of service; 7 days off-spec petroleum) |
| issue_ongoing | Je tatizo bado linaendelea? | Yes | For duration calculation; TANESCO SLA commits to 24-hour restoration for unplanned outages — duration tracking verifies compliance |
| date_issue_resolved | Tarehe tatizo lilitatuliwa (kama limetatuliwa) | Conditional | Collect if issue_ongoing = No; required for outage duration calculation and SLA verification |
| issue_frequency | Mara ngapi tatizo linatokea | Yes | SAIFI (System Average Interruption Frequency Index) requires frequency data. Options: Mara moja / Mara kwa mara / Kila wakati |
| outage_duration_hours | Muda wa kupoteza huduma (masaa) | Yes | SAIDI (System Average Interruption Duration Index) requires this; also determines compensation eligibility per NARUC framework |
| area_ward_district_region | Eneo / Kata / Wilaya / Mkoa | Yes | EWURA reports complaints by region; needed for routing to correct regional office and field team |
| number_of_households_affected | Idadi ya kaya zilizoathirika | Recommended | Required for SAIFI calculation; determines priority level — widespread outages escalate faster |
| desired_outcome | Matokeo unayotaka | Yes | EWURA awards framework lists specific remedy types: refund / kulipwa fidia / kuunganishwa tena / ukarabati wa haraka. Required by ISO 10002:2018 clause 8.3 |
| preferred_contact_method | Njia unayopendelea ya mawasiliano | Yes | For field team coordination and status updates. Options: SMS / Barua pepe / Simu / WhatsApp / Ana kwa ana |
| consent_to_share_data | Ridhaa ya kushiriki data na EWURA | Yes | TCRA Personal Data Protection Regulations 2023 (analogous); EWURA complaint data shared with service providers during mediation |

### Conditional Fields (collect based on issue type)

**If issue_type = Billing Error / Meter Reading Dispute:**
Also collect:
- `billing_period_affected` — Kipindi cha bili kilichoathirika: Month and year
- `amount_billed_tzs` — Kiasi kilichotozwa kwenye bili (TZS)
- `amount_expected_tzs` — Kiasi kilichotarajiwa kulingana na matumizi halisi (TZS)
- `payment_receipt_reference` — Nambari ya risiti ya malipo: Required if customer has paid but account still shows outstanding balance
- `bill_copy_upload` — Pakia nakala ya bili: Required for EWURA complaint documentation
- `meter_type` — Aina ya mita: Prepaid (LUKU token) / Postpaid / Smart meter; affects which billing rules apply

**If issue_type = Prepaid Meter / Token Problem (Electricity):**
Also collect:
- `meter_type` — Aina ya mita: Must confirm prepaid/LUKU
- `last_token_reference` — Nambari ya token ya mwisho iliyonunuliwa: 20-digit LUKU token number; required for token verification with TANESCO
- `token_purchase_channel` — Njia ya kununua token: M-Pesa / USSD / Wakala / Benki; for transaction tracing
- `token_purchase_amount_tzs` — Kiasi kilicholipwa kwa token (TZS)
- `meter_error_code` — Msimbo wa hitilafu wa mita: e.g., E09, REJECT, TAMPERED; TANESCO uses specific error codes for diagnosis
- `units_before_issue` — Vitengo vilivyokuwepo kabla ya tatizo: For overconsumption analysis

**If issue_type = Water Quality / Contamination:**
Also collect:
- `water_quality_description` — Maelezo ya ubora wa maji: WHO Guidelines (4th edition) define aesthetic parameters. Options: Rangi ya kahawia/njano/nyeusi / Harufu mbaya / Mafuta / Uchanganyiko (turbidity) / Ladha mbaya
- `suspected_contamination_type` — Aina ya uchafu inayoshukiwa: WHO surveillance framework distinguishes health-based from aesthetic complaints. Options: Kemikali / Kibiolojia (viumbe) / Aesthetic tu
- `illness_reported` — Je, watu wamepata ugonjwa? Ndiyo / Hapana; if Yes → immediate public health escalation
- `number_of_people_affected_by_illness` — Idadi ya watu waliougua
- `water_source_type` — Aina ya chanzo cha maji: Bomba la mtandao / Borehole / Tanker / Kiosk; determines routing to DAWASA vs. regional water authority
- `last_normal_water_date` — Tarehe ya mwisho maji yalikuwa sawa

**If issue_type = Power Outage / No Electricity:**
Also collect:
- `transformer_feeder_reference` — Nambari ya transformer / feeder: Enables TANESCO fault isolation and field dispatch
- `apparent_cause` — Sababu inayoonekana: Hali ya hewa / Matengenezo yaliyopangwa / Hitilafu ya vifaa / Uunganishaji haramu wa jirani / Haijulikani; TANESCO Customer Service Charter requires communicating outage cause
- `planned_maintenance_notified` — Je, uliarifiwa kuhusu matengenezo yaliyopangwa? Ndiyo / Hapana; unplanned outages without notice are an EWURA SLA violation
- `appliances_damaged` — Je, vifaa vimeharibiwa na mabadiliko ya umeme? Ndiyo / Hapana; for compensation claim

**If issue_type = Voltage Fluctuation / Power Surge:**
Also collect:
- `voltage_reading` — Usomaji wa voltage kwenye chanzo: TANESCO service standards define acceptable voltage range (±10% of nominal); this documents the deviation
- `appliances_damaged_list` — Orodha ya vifaa vilivyoharibiwa
- `estimated_damage_value_tzs` — Thamani ya hasara (TZS): Required for EWURA compensation award calculation

**If service_type = Gas / Petroleum:**
Also collect:
- `product_type` — Aina ya bidhaa: LPG / Gesi asilia / Petroli / Mafuta ya taa
- `batch_reference` — Nambari ya kundi / batch: For off-specification petroleum; EWURA 7-day limitation period applies for off-spec fuel complaints
- `supplier_outlet_name` — Jina la kituo / duka la mwuzaji

### Vulnerability / Priority Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| medical_equipment_dependency | Je, kuna vifaa vya matibabu vinavyotegemea umeme? | Yes (electricity complaints) | Life support / critical care customers require priority restoration; analogous to California CPUC Medical Baseline classification; EWURA "specific performance" awards imply critical-need priority |
| medical_equipment_type | Aina ya kifaa cha matibabu | Conditional | Collect if medical_equipment_dependency = Ndiyo. e.g., Mashine ya kupumua / Jokofu la dawa / Dialysis |
| vulnerable_household_member | Je, kuna mzee, mlemavu, mgonjwa, au mtoto mdogo nyumbani? | Recommended | Relevant to disconnection protections and restoration priority |
| business_critical_dependency | Je, tatizo hili linaathiri hospitali, shule, au kituo cha umuhimu? | Yes | Hospitals, schools, and water pumping stations have priority restoration entitlement; affects EWURA complaint priority classification |

### Financial Impact Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| estimated_financial_loss_tzs | Hasara ya fedha inayokadiriwa (TZS) | Recommended | Required for EWURA remedy calculation; EWURA Act sets minimum fine of TZS 3 million; claims above minimum must be substantiated |
| financial_loss_type | Aina ya hasara ya fedha | Conditional | Chakula kilichooza / Vifaa vilivyoharibiwa / Mapato ya biashara yaliyopotea / Gharama za dawa / Gharama za chanzo mbadala cha maji/umeme |
| financial_loss_evidence_upload | Pakia ushahidi wa hasara (picha / risiti / kadirio la ukarabati) | Conditional | Required at EWURA Committee hearing stage; Duke Energy analogy — repair estimates and receipts required for damage claims |

### Complaint History / Escalation Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| previous_fault_ref_provider | Nambari ya rufaa ya awali kwa mtoa huduma | Yes (for EWURA escalation) | EWURA requires complainant to have first approached the service provider; TANESCO issues fault reference numbers |
| date_reported_to_provider | Tarehe ya kuripoti kwa mtoa huduma | Yes (for EWURA escalation) | EWURA Rules GN No. 10/2013 require supplier given 14 days to reconsider before mediation can begin |
| provider_response_received | Je, mtoa huduma alijibu? | Yes | Required for EWURA escalation assessment. Options: Ndiyo / Hapana / Jibu la sehemu |
| provider_response_summary | Muhtasari wa jibu la mtoa huduma | Conditional | Required at EWURA mediation stage |
| previous_ewura_reference | Nambari ya rufaa ya EWURA (kama ipo) | Conditional | For repeat or related complaints at EWURA-CCC |

### Issue Type Classification

EWURA accepted complaint categories:

**Electricity (TANESCO):**

| Code | Issue Type | Swahili Description |
|------|-----------|---------------------|
| EU-E01 | power_outage | Kupoteza umeme / Giza |
| EU-E02 | voltage_fluctuation | Mabadiliko ya umeme / Voltage pungufu au kubwa |
| EU-E03 | meter_reading_dispute | Utata wa usomaji wa mita |
| EU-E04 | billing_error | Hitilafu ya bili |
| EU-E05 | delayed_connection | Kuchelewa kuunganishwa na umeme |
| EU-E06 | transformer_fault | Hitilafu ya transformer |
| EU-E07 | illegal_connection_neighbour | Muunganisho haramu wa jirani |
| EU-E08 | electrical_fire_or_damage | Moto wa umeme / Uharibifu wa umeme |
| EU-E09 | compensation_dispute | Kutolipwa fidia stahiki |
| EU-E10 | disconnection_dispute | Tatizo la kukata umeme |
| EU-E11 | tariff_dispute | Tatizo la kiwango cha bei |
| EU-E12 | prepaid_token_problem | Tatizo la token ya prepaid / LUKU |
| EU-E13 | safety_hazard_electrical | Hatari ya usalama wa umeme (waya, nguzo, mita) |

**Water / Sewerage (DAWASCO / DAWASA / Regional Authorities):**

| Code | Issue Type | Swahili Description |
|------|-----------|---------------------|
| EU-W01 | no_water_supply | Kutokuwa na maji kabisa |
| EU-W02 | low_water_pressure | Shinikizo la maji pungufu |
| EU-W03 | water_discoloration | Rangi mbaya ya maji |
| EU-W04 | water_contamination | Uchafu wa maji / Maji si salama |
| EU-W05 | pipe_leakage | Bomba lililopasuka / kuvuja |
| EU-W06 | meter_reading_dispute_water | Utata wa usomaji wa mita ya maji |
| EU-W07 | water_billing_error | Hitilafu ya bili ya maji |
| EU-W08 | sewage_overflow | Kufurika kwa maji taka |
| EU-W09 | delayed_water_connection | Kuchelewa kuunganishwa na maji |
| EU-W10 | illegal_water_connection | Muunganisho haramu wa maji |

**Gas / Petroleum:**

| Code | Issue Type | Swahili Description |
|------|-----------|---------------------|
| EU-G01 | off_spec_fuel | Mafuta yasiyokuwa ya kiwango (off-specification) |
| EU-G02 | gas_pricing_dispute | Tatizo la bei ya gesi |
| EU-G03 | gas_supply_interruption | Usumbufu wa ugavi wa gesi |
| EU-G04 | gas_safety_hazard | Hatari ya usalama wa gesi (uvujaji) |

### Resolution Standards for This Industry

- **Provider level (14 days):** EWURA Rules GN No. 10/2013 require the service provider to be given 14 days to reconsider the complaint before EWURA mediation begins. Complainant must have first approached the provider.
- **EWURA Mediation:** 60-day mediation window. EWURA-CCC can award refunds, compensation, and specific performance (reconnection, repair, etc.).
- **TANESCO SLA:** Customer Service Charter 2025 commits to restoring power within 24 hours for unplanned outages. Planned outages must be communicated in advance.
- **EWURA minimum award:** TZS 3 million minimum fine for upheld complaints; financial claims above minimum require substantiated evidence.
- **Documentation required for EWURA escalation:** Provider complaint reference, date of initial report to provider, provider response or evidence of non-response, meter number, account number, bill copy (for billing disputes), financial loss evidence (for compensation claims).
- **Limitation periods:** 12 months general; 24 months for poor quality of service; 7 days for off-specification petroleum. Runs from date of incident.
- **NEMC referral:** Water contamination events with confirmed illness or environmental damage should be referred to NEMC (National Environment Management Council) in parallel.

### Escalation Triggers (field values that require immediate escalation)

- `issue_type = safety_hazard_electrical` (any variant: live wire, sparking transformer, burning meter box) — Immediate dispatch to TANESCO emergency line (0800 110 059); notify fire service if active fire
- `issue_type = gas_safety_hazard` AND `suspected_contamination_type = gas_leak` — Immediate: advise evacuate premises, do not use switches, call TPDC emergency and fire service; do not delay for data collection
- `issue_type = water_contamination` AND `illness_reported = Ndiyo` — Public health emergency; escalate to DAWASA/regional water authority AND NEMC AND Ministry of Health simultaneously; collect `number_of_people_affected_by_illness`
- `medical_equipment_dependency = Ndiyo` AND `issue_type = power_outage` AND `outage_duration_hours > 4` — Priority life support escalation; immediate TANESCO emergency referral
- `business_critical_dependency = hospitali` AND `outage_duration_hours > 4` — Hospital power outage; escalate to TANESCO NOC and regional EWURA office within 2 hours
- `issue_type = electrical_fire_or_damage` OR `appliances_damaged = Ndiyo` — Document financial loss; initiate EWURA compensation claim process
- `issue_type = illegal_connection_neighbour` — Report to TANESCO anti-theft unit; collect evidence if available
- `issue_type = disconnection_dispute` AND `medical_equipment_dependency = Ndiyo` — Utility has no right to disconnect life support customer without medical review; immediate EWURA escalation
- `issue_type = off_spec_fuel` — EWURA 7-day limitation period applies; escalate immediately; collect batch reference
- `provider_response_received = Hapana` AND `date_reported_to_provider > 14 days ago` — Customer qualifies for EWURA mediation; provide EWURA-CCC contact (+255 26 296 0099 / ewuraccc.go.tz)

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina la mtoa maoni (hiari) | Optional | ISO 10002:2018 permits anonymous feedback |
| contact_details | Mawasiliano (hiari) | Optional | For follow-up |
| service_type_targeted | Huduma inayohusika | Yes | EWURA regulates five sectors; routing depends on service type |
| suggestion_category | Kategoria ya mapendekezo | Yes | Routes suggestion to correct department or regulator |
| geographic_area | Eneo / Mkoa unaohusika | Recommended | EWURA regional complaint data informs infrastructure investment priorities |
| suggestion_detail | Maelezo ya mapendekezo | Yes | Free text; core content |
| priority_urgency | Kiwango cha haraka | Recommended | Options: Juu / Kati / Chini |
| estimated_beneficiaries | Idadi ya kaya / biashara zinazoweza kufaidika | Optional | Supports EWURA cost-benefit analysis for licensing decisions |
| channel_submitted | Njia ya kuwasilisha | Auto | Omnichannel analytics |

### Industry-Specific Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| SU-01 | infrastructure_upgrade | Kuboresha miundombinu ya usambazaji (cables, bomba, transformer) |
| SU-02 | smart_metering | Utekelezaji wa mita za kisasa (smart meters) |
| SU-03 | billing_system | Kuboresha mfumo wa bili na malipo |
| SU-04 | customer_communication | Taarifa za mapema za usumbufu / matengenezo |
| SU-05 | new_connection_process | Kuboresha mchakato wa kuomba muunganisho mpya |
| SU-06 | prepaid_token_access | Njia zaidi za kununua token (USSD, wakala, benki) |
| SU-07 | renewable_energy_expansion | Kupanua nishati mbadala (solar, mini-grid, biogas) |
| SU-08 | rural_electrification | Kupeleka umeme vijiji (REA) |
| SU-09 | water_quality_testing | Uchunguzi wa mara kwa mara wa ubora wa maji |
| SU-10 | environmental_sustainability | Mazingira na uhifadhi (greywater, solar water heaters) |
| SU-11 | tariff_policy | Ushauri wa sera ya bei (lifeline tariff, ruzuku) |
| SU-12 | self_service_digital | Huduma za kidijitali (portal, app, USSD) |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina la mwulizaji | Recommended | For account-specific inquiries |
| account_number | Nambari ya akaunti | Conditional | Required to retrieve billing or consumption data |
| meter_number | Nambari ya mita | Conditional | Required for meter-related inquiries |
| service_type | Aina ya huduma | Yes | Electricity / Water / Gas — determines correct answer path and contact |
| query_type | Aina ya swali | Yes | Routes inquiry to correct information source |
| billing_period_of_interest | Kipindi cha bili kinachohusika | Conditional | For billing or consumption inquiries |
| geographic_area | Eneo | Conditional | For outage status, coverage, or new connection inquiries |
| preferred_response_format | Jinsi unavyotaka jibu | Yes | Options: SMS / Barua pepe / Simu / Ana kwa ana; DAWASA: 181 or +255 22 2760006; EWURA-CCC: +255 26 296 0099 |
| inquiry_reference_number | Nambari ya marejeleo (otomatiki) | Auto | ISO 10002:2018 and EWURA-CCC best practice require all interactions tracked by reference number |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| token_loading_help | Jinsi ya kupakia token ya LUKU | meter_number, meter_error_code (if showing) |
| meter_error_code_meaning | Maana ya msimbo wa hitilafu wa mita | meter_error_code, meter_type |
| bill_explanation | Maelezo ya bili | account_number, billing_period_of_interest |
| consumption_history | Historia ya matumizi | account_number, meter_number, billing_period_of_interest |
| outage_status | Hali ya usumbufu wa umeme/maji | geographic_area, service_type |
| planned_maintenance_schedule | Ratiba ya matengenezo yaliyopangwa | geographic_area, service_type |
| new_connection_process | Jinsi ya kuomba muunganisho mpya | service_type, geographic_area, customer_category |
| tariff_rates | Viwango vya bei | service_type, customer_category |
| payment_plan | Mpango wa kulipa deni | account_number, estimated_financial_loss_tzs |
| disconnection_notice_query | Swali kuhusu notisi ya kukata | account_number, meter_number |
| refund_status | Hali ya kurudishiwa pesa | account_number, previous_fault_ref_provider |
| water_safety | Je maji ya bomba ni salama? | geographic_area, water_source_type |
| solar_subsidy | Ruzuku ya solar kupitia REA | geographic_area, customer_category |
| fault_reporting | Jinsi ya kuripoti hitilafu | service_type, geographic_area |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina la mtoa pongezi (hiari) | Optional | For recognition and acknowledgement |
| service_type_commended | Aina ya huduma iliyopongezwa | Yes | Electricity / Water / Gas; routes compliment to correct team |
| staff_team_or_contractor | Jina au timu iliyopongezwa | Optional | For internal staff recognition; specific to TANESCO/DAWASA teams or solar contractors |
| interaction_type | Aina ya mwingiliano | Yes | Ukarabati wa hitilafu / Muunganisho mpya / Urekebisha wa bili / Huduma ya wateja / Mwitikio wa dharura |
| date_of_interaction | Tarehe ya tukio | Recommended | For correlation with staff and dispatch records |
| specific_aspect_praised | Kipengele kilichotukuka | Yes | Kasi ya mwitikio / Adabu / Ubora wa kiufundi / Usahihi wa bili / Mawasiliano wakati wa usumbufu |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | EWURA monitors consumer satisfaction as part of its regulatory performance framework; ITU-T E.800 equivalent includes user satisfaction as QoS dimension |
| free_text_commendation | Maneno ya pongezi (hiari) | Optional | Open narrative for nuance |
| channel_of_interaction | Njia ya mawasiliano | Yes | Simu / Ana kwa ana / App / USSD / Wakala |

---

## AI Conversation Guidance for This Industry

- **Identify the utility type before anything else.** Ask "Tatizo lako linahusu umeme, maji, au gesi?" as the very first question. This determines which regulatory body (TANESCO/EWURA vs. DAWASA/EWURA vs. TPDC), which fields to collect, and which escalation path applies. Mixing electricity and water fields creates confusion.
- **Get the meter number early — it is the single most important identifier.** Unlike telecom where the MSISDN is the anchor, in utilities the meter number unlocks account history, billing records, and field dispatch. Ask "Una nambari ya mita yako? Inaweza kupatikana kwenye mita yenyewe au kwenye bili yako."
- **For prepaid token problems, ask for the 20-digit token number immediately.** Customers often have it in an SMS; this single piece of data allows TANESCO to verify whether the token was issued, whether it matches the meter, and whether it has been used. Ask "Una nambari ya token uliyonunua? Ni nambari ndefu ya tarakimu 20."
- **For water quality complaints, ask about illness before asking about aesthetics.** If anyone has been sick, this is a public health emergency requiring escalation before the conversation ends. Ask "Je, kuna mtu nyumbani aliyeugua baada ya kunywa maji haya?" before asking about colour or smell.
- **For power outages, ask about medical equipment and hospitals before collecting outage details.** A customer with a dialysis machine or oxygen concentrator at home during an outage is a life safety case — ask "Je, kuna mtu nyumbani anayetumia mashine ya matibabu inayohitaji umeme?" within the first two questions.
- **Do not ask for GPS coordinates directly — ask for the street address and nearest landmark instead.** Most customers cannot share GPS coordinates but can describe their location. The AI should convert this to a geographic area field. For technical teams, the address plus meter number is sufficient for dispatch.
- **For billing disputes, ask the customer what they expected to pay versus what they were billed.** This frames the inquiry productively and immediately surfaces the disputed amount without requiring the customer to understand tariff structures. Then ask for the billing period and the payment receipt reference.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Service type | "Tatizo lako linahusu umeme, maji ya bomba, au gesi?" |
| Provider name | "Unatumia huduma ya TANESCO, DAWASCO, DAWASA, au mtoa huduma mwingine?" |
| Account / meter number | "Una nambari ya mita yako? Inaweza kuwa kwenye mita yenyewe au kwenye bili yako ya zamani." |
| Issue type (electricity) | "Tatizo lako ni nini hasa — giza (power outage), mabadiliko ya voltage, tatizo la token, bili potofu, au kingine?" |
| Issue type (water) | "Tatizo lako ni nini — hakuna maji, shinikizo la chini, rangi mbaya ya maji, au bili potofu?" |
| Date issue started | "Tatizo hili lilianza lini — ni masaa, siku, au wiki ngapi zilizopita?" |
| Outage duration | "Umekuwa bila huduma kwa muda gani — masaa mangapi au siku ngapi?" |
| Token number | "Una nambari ya token uliyonunua? Ni tarakimu 20 — inaweza kuwa kwenye ujumbe wa SMS au risiti yako." |
| Medical equipment | "Je, kuna mtu nyumbani anayetumia mashine ya matibabu inayohitaji umeme — kama mashine ya kupumua au jokofu la dawa?" |
| Illness from water | "Je, kuna mtu aliyeugua baada ya kutumia maji haya? Ugonjwa gani?" |
| Financial loss | "Je, umepata hasara yoyote ya fedha — kama chakula kilichoharibika, vifaa vilivyoharibiwa, au gharama nyingine? Kiasi gani?" |
| Previous complaint ref | "Je, umeshawahi ripoti tatizo hili kwa TANESCO au DAWASA moja kwa moja? Kama ndiyo, una nambari ya rufaa yao?" |
| Desired outcome | "Unataka nini kutokea — kurekebisha haraka, kulipwa fidia, kurudishiwa pesa, au kitu kingine?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | safety_hazard_electrical (any: live wire, sparking transformer, burning meter) | Immediate: provide TANESCO emergency line (0800 110 059); advise customer not to approach; create priority safety ticket; notify EWURA regional office |
| issue_type | gas_safety_hazard | Immediate: advise evacuate, do not use switches, call fire service and TPDC; this takes priority over all data collection |
| issue_type | water_contamination AND illness_reported = Ndiyo | Public health emergency: escalate to DAWASA, NEMC, and Ministry of Health simultaneously; provide EWURA-CCC contact; create urgent ticket |
| medical_equipment_dependency | Ndiyo AND outage_duration_hours > 4 | Life support priority: escalate to TANESCO emergency immediately; document for EWURA priority complaint |
| business_critical_dependency | Hospitali AND outage_duration_hours > 4 | Critical infrastructure: escalate to TANESCO NOC and regional EWURA office within 2 hours |
| issue_type | prepaid_token_problem AND last_token_reference collected | Route token number to TANESCO verification system; advise customer on token troubleshooting steps while verification is pending |
| issue_type | billing_error AND amount_billed_tzs > 3x amount_expected_tzs | Flag as suspected meter fault or estimated billing anomaly; escalate to EWURA mediation track; document for SAIDI/SAIFI reporting |
| provider_response_received | Hapana AND date_reported_to_provider > 14 days ago | Customer qualifies for EWURA mediation; provide EWURA-CCC contact (+255 26 296 0099); advise to prepare: meter number, account number, previous complaint reference, and bill copy |
| issue_type | disconnection_dispute AND medical_equipment_dependency = Ndiyo | Immediate EWURA escalation — utility cannot disconnect life support customers without medical review; provide EWURA-CCC contact |
| issue_type | off_spec_fuel | Urgent: EWURA 7-day limitation period applies from date of purchase; collect batch reference immediately; escalate to EWURA-CCC |
| issue_type | illegal_connection_neighbour | Route to TANESCO anti-theft unit; advise customer to document evidence (photo if safe) |
| estimated_financial_loss_tzs | > 0 | Advise customer to collect receipts, photos, and repair estimates for EWURA compensation claim; note EWURA minimum award is TZS 3 million |
| issue_type | power_outage AND outage_duration_hours > 24 | TANESCO SLA breach (Customer Service Charter 2025 commits to 24-hour restoration for unplanned outages); escalate to EWURA as SLA violation |
| water_quality_description | Rangi ya kahawia / nyeusi / harufu mbaya | Advise customer not to drink; provide temporary alternatives if possible; escalate to DAWASA water quality team; create urgent ticket |
| customer_category | Biashara / Viwanda AND outage_duration_hours > 8 | Prioritize for commercial loss compensation documentation; route to EWURA commercial complaint track |

---

*Sources: EWURA GN No. 10/2013, EWURA Act Cap 414 s.34, TANESCO Customer Service Charter 2025, DAWASA complaint form (dawasa.go.tz/complaints), WHO GDWQ 4th edition (NCBI NBK579461, NBK579449), ISO 10002:2018, NARUC Utility Compensation guidelines, Water Supply and Sanitation Act 2019, Electricity Act 2008 (Tanzania), Environmental Management Act 2004, REA rural electrification framework*
