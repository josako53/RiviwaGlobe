---
tags: [industry-kb, field-standards, feedback-fields]
---
# Electronics & Technology — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: smartphone, laptop, television, LED TV, fridge, refrigerator, washing machine, air conditioner, printer, router, tablet, earphones, charger, power bank, screen protector, electronics shop, repair technician, warranty card, spare parts, Samsung, Tecno, Infinix, Itel, LG, Sony, Hisense, HP, Dell, Lenovo, power surge, UPS, TANESCO outage, Android, iPhone, software update, motherboard, RAM, screen replacement, IMEI, serial number, firmware, Kariakoo, fundi simu, karabati, simu haitoshi, skrini imevunjika, betri, joto kupita kiasi, haifunguki, data imepotea, overheating, software crash, dead pixels, warranty claim, TCRA, type approval, simu inakatika, laptop haitoshi, TV haikufanya kazi, friji haipoi, AC inafanya kelele

## Why Industry-Specific Fields Matter

Electronics complaints divide into two fundamentally different investigation tracks that require entirely different data: unit-level hardware defects (requiring serial number / IMEI for individual device tracking and warranty validation) and software/firmware anomalies (requiring version numbers and reproducibility data per IEEE 1044-2009). Without the serial number, a warranty claim cannot be validated; without firmware version and reproducibility, a software bug report cannot be escalated to engineering. Generic fields produce unactionable tickets for both tracks.

## Source Standards

- IEEE 1044-2009 — Standard Classification for Software Anomalies (anomaly record attributes, type taxonomy, reproducibility, severity)
- EU General Product Safety Regulation (GPSR) Regulation (EU) 2023/988 — Articles 9, 20, 35, 36 (product traceability, serious risk register, recall notification)
- IEC 62368-1:2023 — Audio/video, IT and communication technology equipment safety (hazard-based taxonomy for electronics issue type vocabulary: electrical, thermal, mechanical energy sources)
- TCRA Electronic and Postal Communications (Consumer Protection) Regulations 2018, GN No. 61 — TCRA Form A (confirmed field structure for telecom devices)
- TCRA Revised Guideline for Consumer Complaint Handling with ISO Requirements (2021)
- Claimlane Electronics Returns & Warranty Claims — industry best practice for structured warranty claim intake
- ISO 10002:2018 — Quality management: guidelines for complaints handling (clauses 8.2, Annex C)
- UK Consumer Rights Act 2015 via Which? — statutory framework for electronics defect rights (s.9 satisfactory quality)

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | ISO 10002:2018 clause 8.2 — mandatory for complaint record; TCRA Form A requires full legal name |
| complainant_phone_number | Nambari ya simu ya mlalamikaji | Yes | Primary contact for updates; TCRA Form A and ISO 10002:2018 require contact details |
| complainant_email | Barua pepe ya mlalamikaji | Recommended | For written documentation and warranty correspondence |
| product_name_and_model | Jina na mfano kamili wa bidhaa | Yes | GPSR Art. 9 — full model designation mandatory; IEEE 1044-2009 "product name and version" attribute; cannot investigate without this |
| product_brand | Chapa ya bidhaa | Yes | GPSR Art. 9 — brand/trade name required; determines manufacturer routing and warranty provider |
| serial_number | Nambari ya serial | Yes | GPSR Art. 9 — THE critical electronics field; unlike food (batch-level), electronics are individually serialized; primary key for warranty validation, stolen device check, and unit-level defect investigation |
| imei_number | Nambari ya IMEI (simu / vifaa vya mtandao) | Yes (mobile devices) | TCRA — IMEI is the regulatory identifier for mobile devices in Tanzania; TCRA Form A; enables network block if stolen; Claimlane industry practice |
| mac_address | Anwani ya MAC (vifaa vya mtandao) | Conditional | Claimlane — required for networking devices (routers, smart TVs, IoT); unit-level identification where IMEI does not apply |
| firmware_or_software_version | Toleo la programu / firmware | Recommended | IEEE 1044-2009 "product version" attribute — mandatory for software anomaly investigation; different firmware versions have different bug profiles |
| purchase_date | Tarehe ya ununuzi | Yes | ISO 10002:2018 Annex C; Claimlane; Which? CRA 2015 — warranty start date; statutory rights depend on time elapsed |
| warranty_expiry_date | Tarehe ya kumalizika kwa udhamini | Recommended | Claimlane; Which? — establishes whether in-warranty or out-of-warranty resolution applies |
| retailer_or_seller_name | Jina la duka / muuzaji | Yes | ISO 10002:2018 (organizational unit); TCRA Form A — identifies who sold the device; determines complaint routing (retailer vs. manufacturer) |
| order_or_receipt_number | Nambari ya agizo / risiti | Yes | BBB form; Claimlane — proof of purchase; links complaint to verifiable transaction record |
| issue_type | Aina ya tatizo | Yes | IEEE 1044-2009 anomaly type taxonomy; TCRA Form A issue categories; determines investigation track (hardware / software / safety / service) |
| issue_description | Maelezo ya tatizo | Yes | IEEE 1044-2009 "description" attribute; ISO 10002:2018 clause 8.2 — narrative description required |
| reproducibility | Je, tatizo linajirudia? | Yes | IEEE 1044-2009 "reproducibility" attribute — critical for software/firmware defect escalation. Options: Kila wakati / Mara kwa mara / Ilitokea mara moja |
| severity_level | Kiwango cha ukali | Yes | IEEE 1044-2009 "severity" attribute. Options: Mbaya sana (haitumiki kabisa) / Kubwa (kazi muhimu imesimama) / Ndogo (inafanya kazi lakini vibaya) / Nzuri (tatizo dogo) |
| safety_risk_present | Je, kuna hatari ya usalama? (Ndiyo / Hapana) | Yes | GPSR Art. 20 — electronics complaints involving serious risk (fire, explosion, electrocution) require a SEPARATE internal register with 5-year retention; this field triggers that routing |
| prior_repair_attempts | Je, bidhaa ilitengenezwa awali? | Recommended | ISO 10002:2018 (prior resolution attempts); Which? CRA 2015 — one failed repair attempt gives consumer stronger rights |
| evidence_photos_or_video_uploaded | Picha / video ya tatizo zilipakiwa | Recommended | GPSR; Claimlane (minimum 2 images: overview + close-up of defect); critical for hardware defect claims |
| data_backed_up | Je, data ilifanyiwa nakala kabla ya tatizo? | Recommended | Consumer electronics best practice — determines data loss scope and liability |
| desired_resolution | Suluhisho unalotaka | Yes | ISO 10002:2018 Annex C; BBB — remedy sought guides resolution offer |
| preferred_contact_method | Njia ya mawasiliano unayopendelea | Yes | Options: SMS / Barua pepe / Simu / WhatsApp |

### Conditional Fields (collect based on issue type)

**If safety_risk_present = Ndiyo:**
Also collect:
- `safety_risk_type` — Aina ya hatari ya usalama: IEC 62368-1 hazard taxonomy — Moto / Mlipuko / Mkondo wa umeme (electrocution) / Joto kupita kiasi (thermal) / Kemikali / Mitambo (mechanical): Each maps to a different IEC 62368-1 energy source category
- `incident_occurred` — Je, tukio la hatari lilitokea? (Moto / Majeraha / Uharibifu wa mali): GPSR Art. 20 serious risk register entry required if incident has already happened
- `injury_description` — Maelezo ya maumivu / jeraha: For medical and product liability; GPSR Art. 36 notification fields
- `product_still_in_use` — Je, bidhaa bado inatumika? (Ndiyo / Hapana): Safety — if still in use, immediate advisory to stop

**If issue_type = software_firmware_bug:**
Also collect:
- `anomaly_type` — Aina ya hitilafu: IEEE 1044-2009 anomaly classification — Hesabu (Computational) / Kiolesura (Interface/timing) / Mantiki (Logic) / Data / Ushughulikiaji data (Data-handling) / Hati (Documentation) / Uthibitisho wa viwango (Standards conformance)
- `steps_to_reproduce` — Hatua za kuifanya ijirudie: IEEE 1044-2009 — reproducibility procedure required for engineering investigation
- `error_message_or_code` — Ujumbe wa hitilafu / msimbo: Specific error text or code; enables direct log correlation
- `os_version` — Toleo la mfumo wa uendeshaji: e.g., Android 14 / iOS 17 / Windows 11; IEEE 1044-2009 environment context; required for software defect routing

**If issue_type = warranty_denied OR warranty_dispute:**
Also collect:
- `warranty_card_available` — Je, kadi ya udhamini ipo? (Ndiyo / Hapana): Many Tanzania retailers deny warranty claims without original card; document this
- `reason_given_for_denial` — Sababu ya kukataa udhamini: e.g., nje ya muda / kuharibika kwa makusudi / serial haitambuliki; enables policy assessment
- `days_since_purchase` — Siku zimepita tangu ununuzi: CRA 2015 / ISO 10002:2018 — rights differ based on time elapsed
- `one_repair_attempt_already_made` — Je, jaribio moja la ukarabati limefanywa? (Ndiyo / Hapana): Which? CRA 2015 — after one failed repair, consumer has right to price reduction or final right to reject

**If issue_type = data_loss:**
Also collect:
- `data_loss_cause` — Sababu ya kupotea kwa data: Ukarabati / Kusasisha programu / Kusimama ghafla / Virusi / Nyingine
- `data_type_lost` — Aina ya data iliyopotea: Picha / Mawasiliano / Nywila / Nyaraka / Hifadhidata ya biashara
- `data_recovery_attempted` — Je, kurejesha data kumejaribiwa? (Ndiyo / Hapana)
- `consent_to_access_data_given` — Je, ulikubaliana na mfanyakazi kushughulika na data yako? (Ndiyo / Hapana): Relevant if data was accessed during repair without permission — privacy and TCRA data protection violation

**If issue_type = stolen_device OR device_identity_fraud:**
Also collect:
- `police_report_number` — Nambari ya ripoti ya polisi: TCRA — required for network block request; police report mandatory for IMEI blacklisting
- `imei_registered_to_another_person` — Je, IMEI imesajiliwa kwa mtu mwingine? (Ndiyo / Hapana / Sijui): Indicates possible stolen or reregistered device
- `tcra_device_check_done` — Je, ukaguzi wa TCRA umefanywa? (Ndiyo / Hapana): TCRA maintains device type approval registry; consumers can verify legitimacy

**If issue_type = repair_shop_misconduct:**
Also collect:
- `repair_shop_name_location` — Jina na mahali pa duka la ukarabati: Enables escalation to shop management or TCRA if licensed repairer
- `parts_replaced_without_consent` — Je, vipande viliwekwa bila ridhaa yako? (Ndiyo / Hapana): Consumer rights violation
- `counterfeit_parts_suspected` — Je, vipande bandia vimewekwa? (Ndiyo / Hapana): Triggers TCRA and TRA anti-counterfeit escalation
- `device_returned_in_worse_condition` — Je, bidhaa ilirudi hali mbaya zaidi? (Ndiyo / Hapana): IEEE 1044-2009 "resolution type" — "not fixed / made worse" scenario

**If issue_type = overheating OR fire_or_smoke_risk:**
Also collect:
- `temperature_before_incident_environment` — Hali ya mazingira wakati wa tatizo: Ndani / Nje / Inachajishwa / Inatumika / Imezimwa: IEC 62368-1 thermal hazard assessment requires environmental context
- `charger_used` — Aina ya charger iliyotumika: Original / Compatible / Isiyojulikana: Non-original chargers are a leading cause of thermal incidents in Tanzania market

### Issue Type Classification

| Code | Issue Type | Swahili Description |
|------|-----------|---------------------|
| ET-01 | device_wont_power_on | Kifaa haikiwashi / DOA (Dead on Arrival) |
| ET-02 | battery_failure | Tatizo la betri / inaisha haraka |
| ET-03 | screen_defect | Kasoro ya skrini (dead pixels, crack ya ndani, giza) |
| ET-04 | software_firmware_bug | Hitilafu ya programu / firmware (crash, freeze, restart) |
| ET-05 | connectivity_failure | Tatizo la muunganiko (Wi-Fi, Bluetooth, 4G, HDMI) |
| ET-06 | overheating | Joto kupita kiasi wakati wa kutumika / kuchaji |
| ET-07 | data_loss | Data imepotea (picha, faili, mawasiliano) |
| ET-08 | short_circuit_electrical | Mzunguko mfupi wa umeme / kasoro ya kimweme |
| ET-09 | fire_smoke_burn_risk | Hatari ya moto / moshi / kuchomwa |
| ET-10 | physical_mechanical_defect | Kasoro ya kimwili / mitambo (sehemu iliyovunjika, hinge) |
| ET-11 | charging_failure | Haichajiwi / chajio polepole kupita kawaida |
| ET-12 | audio_video_defect | Tatizo la sauti au picha |
| ET-13 | accessory_missing_incompatible | Kifaa kingine kimekosekana au kisichofanya kazi |
| ET-14 | warranty_denied | Madai ya udhamini yalikataliwa |
| ET-15 | warranty_repair_delay | Ukarabati wa udhamini unakawia |
| ET-16 | repair_shop_misconduct | Tabia mbaya ya duka la ukarabati |
| ET-17 | counterfeit_parts_installed | Vipande bandia viliwekwa wakati wa ukarabati |
| ET-18 | stolen_device | Kifaa kilichoibiwa / identity fraud |
| ET-19 | data_accessed_without_consent | Data ilifikiriwa bila ruhusa wakati wa ukarabati |
| ET-20 | power_surge_damage | Uharibifu wa mzigo wa umeme (TANESCO) |
| ET-21 | cosmetic_defect | Kasoro ya nje tu (mikwaruzo, rangi) |
| ET-22 | price_billing_dispute | Tofauti ya bei / malipo |

### Resolution Standards for This Industry

- **Retailer / seller level (Tanzania):** ISO 10002:2018 recommends acknowledgement within 5 working days; hardware defect complaints should receive initial technical assessment within 14 days. 24-hour DOA exchanges are industry best practice.
- **Warranty claims:** Manufacturer warranty documentation must specify repair timeline; industry standard (Claimlane reference) is 7–14 working days for warranty repair. Replacement unit should be provided if repair exceeds 30 days.
- **TCRA escalation (Tanzania telecom devices):** TCRA regulates type approval of communications equipment. Devices without TCRA type approval can be blocked. Consumer complaints about TCRA-regulated devices should first go to the operator/seller; if unresolved within 30 days, TCRA-CCC accepts escalation.
- **GPSR Art. 20 serious risk register:** Electronics complaints involving safety risk (fire, explosion, electrocution) must be recorded in a separate internal register maintained for 5 years. This is distinct from standard quality complaints.
- **TCRA device type approval:** All mobile and communications devices sold in Tanzania must hold TCRA type approval. A complaint about a device lacking approval routes to TCRA directly.
- **Required documentation for escalation:** Purchase receipt with serial number, photos of defect, warranty card (where available), description of defect and steps to reproduce, prior repair attempt documentation (if applicable), police report (if theft-related).

### Escalation Triggers (field values that require immediate escalation)

- `safety_risk_type` includes Moto OR Mlipuko OR Mkondo wa umeme AND `incident_occurred = Ndiyo` — GPSR Art. 20 serious risk register entry; notify TBS within 24 hours; advise consumer to stop use; preserve device for inspection; notify manufacturer
- `issue_type = fire_smoke_burn_risk` — Immediate consumer safety advisory: stop use; isolate device; do not charge overnight; GPSR Art. 20 escalation; TCRA notification if communications device
- `issue_type = stolen_device` AND `police_report_number` present — TCRA IMEI blacklist request; advise consumer to contact network operator to block SIM and IMEI
- `issue_type = data_accessed_without_consent` — Privacy violation; advise consumer to change all account passwords immediately; log under TCRA Personal Data Protection Regulations 2023
- `issue_type = counterfeit_parts_installed` — Escalate to TRA anti-counterfeit unit and TCRA; document repair shop details
- `outcome_severity = Mbaya sana` AND `safety_risk_present = Ndiyo` — Dual escalation: product safety (TBS/TCRA) and consumer compensation track
- `issue_type = power_surge_damage` AND amount_paid_tzs > 1000000 — High-value loss; advise consumer on TANESCO surge damage compensation process and insurance claim pathway
- `issue_type = warranty_denied` AND `days_since_purchase <= 30` — Strong statutory rights position; provide consumer with legal basis; escalate to manufacturer if retailer is non-responsive
- `imei_registered_to_another_person = Ndiyo` — Possible stolen device resale; escalate to TCRA and advise consumer to report to police

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina la mtoa maoni (hiari) | Optional | ISO 10002:2018 permits anonymous feedback |
| contact_details | Mawasiliano (hiari) | Optional | For follow-up |
| suggestion_category | Kategoria ya mapendekezo | Yes | Routes to correct team (product / repair / pricing / customer experience) |
| specific_product_or_service | Bidhaa au huduma inayohusika | Recommended | Specific routing and benchmarking |
| suggestion_detail | Maelezo ya mapendekezo | Yes | Core content |
| os_or_platform_context | Mfumo wa uendeshaji / jukwaa (kama inafaa) | Optional | e.g., Android 14, Windows 11 — for software feature suggestions |
| channel_submitted | Njia ya kuwasilisha | Auto | Omnichannel analytics |

### Industry-Specific Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| ES-01 | product_range_expansion | Ongeza aina za bidhaa / mifano mipya |
| ES-02 | local_power_compatibility | Bidhaa zinazofaa na hali ya umeme Tanzania (230V, mzigo wa umeme) |
| ES-03 | solar_compatibility | Bidhaa zinazofanya kazi na nishati ya jua |
| ES-04 | repair_service_improvement | Boresha huduma ya ukarabati (muda, ubora, uwazi wa bei) |
| ES-05 | warranty_policy_improvement | Boresha sera ya udhamini |
| ES-06 | software_feature_request | Ombi la kipengele kipya cha programu |
| ES-07 | ui_ux_improvement | Boresha muundo wa programu / kiolesura |
| ES-08 | accessory_availability | Ongeza upatikanaji wa vifaa vya ziada (genuine) |
| ES-09 | pricing_affordability | Punguza bei / ongeza chaguzi za mkopo |
| ES-10 | technical_support_improvement | Boresha msaada wa kiufundi / mafunzo ya wafanyakazi |
| ES-11 | digital_experience | Boresha mchakato wa ununuzi wa mtandaoni / programu |
| ES-12 | upcountry_service_access | Ongeza vituo vya huduma nje ya Dar es Salaam |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina la mwulizaji | Recommended | Personalizes response |
| product_name_or_category | Jina la bidhaa au kategoria | Yes | Routes inquiry to correct product knowledge base or technical team |
| query_type | Aina ya swali | Yes | Determines answer pathway |
| serial_number_or_imei | Nambari ya serial / IMEI (kama inafaa) | Conditional | Required for account-specific queries (warranty status check, stolen device check) |
| preferred_response_format | Jinsi unavyotaka jibu | Recommended | SMS / WhatsApp / Simu / Barua pepe |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| product_availability | Je, bidhaa hii ipo stokuni? | product_name_or_category, preferred_branch_location |
| product_comparison | Linganisha bidhaa mbili | product_a_name, product_b_name, use_case |
| warranty_status_check | Angalia hali ya udhamini | serial_number_or_imei, purchase_date |
| warranty_coverage_query | Udhamini unajumuisha nini? | product_name_or_category, specific_concern |
| repair_cost_estimate | Bei ya ukarabati | issue_type, product_name_and_model |
| repair_center_location | Wapi kituo cha ukarabati? | product_brand, customer_location |
| driver_firmware_download | Kupakua dereva / firmware | product_name_and_model, os_version |
| compatibility_query | Je, bidhaa hii inafanya kazi na X? | product_name, other_device_or_os |
| power_compatibility | Je, inafanya kazi na umeme wa Tanzania (230V)? | product_name_and_model |
| tcra_type_approval_status | Je, bidhaa hii ina idhini ya TCRA? | product_name_and_model, imei_number |
| imei_check | Angalia usajili wa IMEI | imei_number |
| payment_options | Chaguzi za malipo / mkopo | product_name_and_model, estimated_budget_tzs |
| trade_in_valuation | Thamani ya kubadilisha simu ya zamani | current_device_model, condition |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina la mtoa pongezi (hiari) | Optional | For acknowledgement and staff recognition |
| store_or_service_name | Jina la duka / kituo cha huduma | Yes | Routes compliment to correct branch or service management |
| staff_name_or_description | Jina / maelezo ya mfanyakazi | Optional | Staff recognition schemes; performance records |
| date_of_interaction | Tarehe ya mazungumzo / huduma | Recommended | Correlates with staff shift and service records |
| interaction_type | Aina ya mazungumzo / huduma | Yes | Options: Ununuzi / Ukarabati / Udhamini / Msaada wa kiufundi / Uwasilishaji / Mtandaoni |
| specific_product_or_service_praised | Bidhaa au huduma iliyopongezwa | Yes | Product team and service quality feedback loop |
| aspect_praised | Kipengele kilichotukuka | Yes | Options: Utendaji wa bidhaa / Ubora wa ukarabati / Maarifa ya mfanyakazi / Wakati wa kujibu / Uwazi / Uaminifu / Bei nzuri |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Structured satisfaction metric |
| free_text_commendation | Maneno ya pongezi (hiari) | Optional | Open narrative |

---

## AI Conversation Guidance for This Industry

- **Get the serial number first, but frame it as a "label hunt."** Most customers do not know where their serial number is. Instead of asking "nambari yako ya serial ni nini?" guide them: "Kwenye simu, nenda Mipangilio → Kuhusu Simu → Taarifa za Simu, utaona nambari ya serial huko. Au angalia kwenye sanduku la bidhaa." For laptops: "Angalia mwisho wa laptop au ndani ya betri." Make it a joint treasure hunt, not a bureaucratic demand.
- **Ask about safety risk before asking about any other detail.** If the customer mentions moto, moshi, mkondo wa umeme, or joto kupita kiasi, immediately confirm: "Je, bidhaa hiyo bado inatumika sasa hivi? Kama inachajishwa, tafadhali iondoe kutoka kwa umeme mara moja." Safety advisory takes priority over data collection; GPSR Art. 20 serious-risk escalation is non-negotiable.
- **For software bugs, collect reproducibility before collecting severity.** Ask "Je, tatizo hili linatokea kila wakati ukijaribu, au linatokea mara kwa mara tu?" This is the IEEE 1044-2009 reproducibility field and is the single most operationally useful data point for an engineering bug report. A bug that happens every time is a different priority from one that happened once.
- **Do not conflate IMEI and serial number — they are different.** IMEI applies to communications devices (phones, modems, routers) and is the regulatory identifier for TCRA. Serial number applies to all electronics. For phones, collect IMEI; for laptops and appliances, collect serial number. For networking devices, MAC address may be more relevant than IMEI.
- **For warranty denial complaints, ask how long ago the customer purchased the device before asking about the warranty card.** If it has been less than 30 days, the consumer has strong statutory rights regardless of whether they have the warranty card. Frame this positively: "Kwa sababu ulinunua bidhaa hii hivi karibuni, una haki ya kisheria ya kuhitaji ukarabati au ubadilishaji, hata bila kadi ya udhamini."
- **For TANESCO power surge damage, collect the date and time of the surge and whether a UPS or surge protector was in use.** This information determines whether TANESCO liability or product liability (if the UPS failed) applies and routes the complaint accordingly. Also advise the customer to file a TANESCO damage claim.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Product name and model | "Bidhaa gani hasa unayozungumzia — jina la chapa na mfano kamili?" |
| Serial number (phone) | "Nenda Mipangilio → Kuhusu Simu → Taarifa za Simu. Utaona nambari ya serial. Je, unaweza kuniambia inasema nini?" |
| Serial number (laptop) | "Angalia mwisho wa laptop au kwenye stika ndogo chini ya laptop — utaona nambari ya serial." |
| IMEI (mobile device) | "Piga *#06# kwenye simu yako — nambari ya IMEI itaonekana mara moja kwenye skrini." |
| Purchase date | "Ulinunua bidhaa hii lini hasa — tarehe au wiki ngapi zilizopita?" |
| Warranty status | "Je, bidhaa hii iko ndani ya muda wa udhamini — ni miaka mingapi udhamini unaendelea?" |
| Issue description | "Eleza tatizo kwa undani — linianza lini, linatokea lini, na linajitokeza vipi?" |
| Reproducibility | "Je, tatizo hili linatokea kila wakati unajaribu, au linatokea mara kwa mara tu?" |
| Safety risk | "Je, bidhaa hii imeshika moto, ikatoa moshi, au ilikupa mshtuko wa umeme wakati wowote?" |
| Data backup status | "Je, ulikuwa umefanya nakala ya data yako (picha, mawasiliano) kabla tatizo hili kutokea?" |
| Prior repair | "Je, bidhaa hii ilitengenezwa awali — kwa udhamini au duka la ukarabati?" |
| Desired resolution | "Unataka nini kutokea — ukarabati wa bure, ubadilishaji wa bidhaa, au kurudishiwa pesa?" |
| TCRA check | "Je, umewahi kuangalia kama bidhaa hii ina idhini ya TCRA? Unaweza kutuma *#06# na kuangalia IMEI kwenye tovuti ya TCRA." |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| safety_risk_type | Moto OR Mlipuko OR Mkondo wa umeme | Immediate: advise stop use; isolate device; do not charge; GPSR Art. 20 escalation; TBS and TCRA notification within 24 hours; preserve device for inspection |
| issue_type | fire_smoke_burn_risk | Consumer safety advisory first; create urgent ticket; notify manufacturer; log in serious risk register |
| issue_type | stolen_device AND police_report_number present | Request TCRA IMEI blacklist; advise consumer to contact network operator for SIM block; do not restore or factory reset device before police documentation |
| issue_type | data_accessed_without_consent | Advise immediate password changes (email, banking apps, social media); log under TCRA Personal Data Protection Regulations 2023; escalate to repair shop management |
| issue_type | counterfeit_parts_installed | Document repair shop details; escalate to TRA anti-counterfeit and TCRA; advise consumer on right to original parts under warranty |
| days_since_purchase | <= 30 AND issue_type = defective_product | Advise consumer of strong refund/replacement right; provide legal basis; escalate to retailer if denied |
| days_since_purchase | > 30 AND issue_type = defective_product | Advise warranty repair as primary remedy; document any prior repair attempts |
| one_repair_attempt_already_made | Ndiyo AND issue_type = defective_product | Consumer eligible for price reduction or final right to reject; escalate to retailer management |
| issue_type | power_surge_damage | Advise TANESCO damage claim filing; collect date and time of surge; check if UPS was in use; route to retailer if UPS itself failed |
| imei_registered_to_another_person | Ndiyo | Flag as possible stolen device; do not assist in unlocking; advise consumer to report to police and TCRA |
| warranty_card_available | Hapana AND days_since_purchase <= 12 months | Most manufacturer warranties are serial-number-based; advise consumer that card may not be strictly required if serial number can be verified in manufacturer database |
| reproducibility | Kila wakati AND severity_level = Mbaya sana | Escalate to manufacturer engineering team with full IEEE 1044-2009 anomaly record; create priority defect ticket |
| firmware_or_software_version | outdated version identified | Advise firmware update first before escalating hardware complaint; provide update instructions in Swahili |
| issue_type | warranty_repair_delay AND days_waiting > 30 | Escalate to manufacturer regional support; advise consumer on right to replacement unit if repair exceeds reasonable period |

---

*Sources: IEEE 1044-2009 (Standard Classification for Software Anomalies — anomaly record attributes, type taxonomy), EU GPSR Regulation (EU) 2023/988 (Arts. 9, 20, 35, 36), IEC 62368-1:2023 (hazard taxonomy for electronics safety classification), TCRA Electronic and Postal Communications (Consumer Protection) Regulations 2018 GN No. 61, TCRA Form A, TCRA Revised Guideline for Consumer Complaint Handling (ISO-aligned, 2021), Claimlane Electronics Returns & Warranty Claims industry practice, ISO 10002:2018 (clauses 8.2, Annex C), UK Consumer Rights Act 2015 via Which? complaint framework*
