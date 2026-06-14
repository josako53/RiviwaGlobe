---
tags: [industry-kb, field-standards, feedback-fields, electronics, technology]
---
# Electronics & Technology — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: electronics, vifaa vya umeme, smartphone, simu, laptop, kompyuta, computer, tablet, TV, television, runinga, camera, kamera, printer, chapa, scanner, router, modem, smart TV, audio, speaker, spika, headphones, headset, charger, adapter, battery, betri, USB, hard drive, SSD, memory, RAM, processor, operating system, Android, iOS, Windows, software, programu, app, application, gadget, device, kifaa, warranty, udhamini, defective, hitilafu, screen, skrini, display, keyboard, kibodi, mouse, panya, repair, ukarabati, spare parts, vipande vya kubadilisha, TBS, TCRA, CE mark, counterfeit electronics, bidhaa bandia za umeme, overheating, kupasha moto kupita kiasi, explosion, kulipuka, fire, moto, electric shock, umeme wa mshtuko, software bug, virusi, malware, data loss, kupoteza data, warranty claim, madai ya udhamini, after-sales service, huduma baada ya mauzo, technical support, usaidizi wa kiufundi, brand, chapa, Samsung, Tecno, Nokia, Huawei, itel, infinix, Dell, Acer, HP, Xiaomi, Apple

## Why Industry-Specific Fields Matter

Electronics complaints span product safety (explosion, fire, electric shock requiring TCRA/TBS urgent investigation), warranty disputes (requiring purchase date, serial number, service center records), software/cybersecurity issues (requiring device type, OS version), and counterfeit electronics (requiring TBS certification verification). Without electronics-specific fields, the AI cannot differentiate between a design defect requiring manufacturer recall and a user-induced fault outside warranty, or identify a counterfeit device that poses a fire risk.

## Source Standards

- Tanzania Bureau of Standards (TBS) Act, Cap. 130 — electronics product standards
- TCRA Electronic and Postal Communications Act, Cap. 306 — device type approval
- TCRA Device Type Approval Regulations — imported electronics compliance
- Consumer Protection Act (Tanzania Fair Competition Act, Cap. 285)
- EU Directive 2014/35/EU — Low Voltage Directive (reference standard for electronics safety)
- EU WEEE Directive 2012/19/EU — waste electronics (reference for e-waste disposal)
- IEC 62133 — safety requirements for portable sealed rechargeable cells and batteries
- ISO 9001:2015 — quality management (electronics manufacturer QMS)
- ISO 10002:2018 — complaints handling
- IEEE standards (reference for technical specifications)

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL electronics complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Consumer protection and warranty claim identification |
| complainant_phone | Nambari ya simu | Yes | For status updates |
| product_name | Jina la bidhaa / kifaa | Yes | Core identifier |
| product_brand | Chapa ya bidhaa | Yes | Manufacturer identification; warranty determination |
| product_model_number | Nambari ya modeli | Yes | Critical for warranty lookup and technical diagnosis |
| product_serial_number | Nambari ya msururu (serial number) | Yes | Unique device identifier; required for all warranty and safety investigations |
| purchase_date | Tarehe ya ununuzi | Yes | For warranty period determination |
| purchase_location | Mahali pa ununuzi | Yes | For retailer accountability and warranty activation |
| warranty_period | Muda wa udhamini | Recommended | Expressed in months; determines eligibility |
| tcra_type_approval | Je, kifaa kina kibali cha TCRA? | Recommended | TCRA requires type approval for all wireless/electronic devices; absence may indicate counterfeit |
| issue_type | Aina ya tatizo | Yes | Determines urgency, investigation type, and regulatory routing |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; detailed technical narrative |
| safety_incident | Je, tukio la usalama limetokea? (moto, umeme, kulipuka) | Yes | Safety incidents require immediate TCRA/TBS escalation |
| defect_onset | Tatizo lilianza lini baada ya ununuzi? | Yes | Days/weeks/months since purchase; for warranty assessment |
| receipt_available | Je, risiti inapatikana? | Yes | Required for warranty claim and consumer protection |
| desired_outcome | Matokeo unayotaka | Yes | Repair / Replacement / Refund / Investigation |

### Conditional Fields (collect based on issue type)

**If issue_type = Safety Incident (fire, explosion, electric shock):**
Also collect:
- `incident_severity` — Ukali wa tukio: Minor damage / Property damage / Personal injury / Life-threatening
- `injuries_sustained` — Majeraha yaliyotokea: CRITICAL for TBS immediate product safety investigation
- `property_damage_value_tzs` — Thamani ya mali iliyoharibika (TZS): For compensation claim
- `photos_of_incident` — Je, picha za tukio zinapatikana?: TBS and insurance evidence requirement
- `device_condition_at_time_of_incident` — Hali ya kifaa wakati wa tukio: Charging / In use / Idle / Wet

**If issue_type = Warranty Dispute:**
Also collect:
- `service_center_visited` — Kituo cha huduma kilichotembelewa
- `service_center_response` — Jibu la kituo cha huduma
- `repair_attempt_count` — Idadi ya majaribio ya ukarabati: Multiple failed repairs may trigger replacement right under warranty
- `service_center_job_number` — Nambari ya kazi ya kituo cha huduma: For warranty tracking

**If issue_type = Software / App / Data Issue:**
Also collect:
- `operating_system_version` — Toleo la mfumo wa uendeshaji: e.g., Android 14, iOS 17, Windows 11
- `app_name_and_version` — Jina la programu na toleo lake
- `error_message` — Ujumbe wa hitilafu (error message): For technical diagnosis
- `data_lost` — Je, data ilipotea? Yes / No: Determines compensation scope
- `data_backup_existed` — Je, nakala ya akiba (backup) ilikuwepo?

**If issue_type = Counterfeit Electronics:**
Also collect:
- `tcra_approval_mark` — Je, alama ya kibali cha TCRA ipo? Yes / No: TCRA type approval required
- `tbs_quality_mark` — Je, alama ya ubora ya TBS ipo? Yes / No
- `purchase_channel` — Njia ya ununuzi: Official dealer / Street market / Online / Informal trader
- `counterfeit_evidence` — Ushahidi wa tuhuma: Poor build quality / No safety marks / Suspiciously low price

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| EL-01 | hardware_failure | Device stops working; hardware malfunction |
| EL-02 | display_screen_issue | Cracked screen, dead pixels, display fault |
| EL-03 | battery_issue | Fast drain, swelling, not charging, overheating |
| EL-04 | connectivity_issue | Wi-Fi, Bluetooth, cellular, USB connection failures |
| EL-05 | fire_explosion_shock | Device caught fire, exploded, or gave electric shock (SAFETY) |
| EL-06 | overheating | Excessive heat during normal use |
| EL-07 | software_bug | Operating system or app malfunction |
| EL-08 | data_loss | Loss of data; device wipe; storage failure |
| EL-09 | warranty_refusal | Manufacturer or retailer refuses valid warranty claim |
| EL-10 | poor_build_quality | Product inferior to advertised specifications |
| EL-11 | counterfeit_device | Device suspected to be fake or unauthorized copy |
| EL-12 | repair_poor_quality | Repair service performed poorly; same fault recurs |
| EL-13 | after_sales_unresponsive | Service center unreachable or unhelpful |
| EL-14 | missing_accessories | Accessories missing from original packaging |
| EL-15 | environmental_damage | Product damaged by claimed normal environmental conditions |

### Resolution Standards

- **Manufacturer/retailer warranty:** Most electronics carry 12-month warranty; defects within this period entitle repair, replacement, or refund.
- **Service center:** Repair should be completed within 14–21 days; if same fault recurs after 3 repairs, replacement is standard industry practice.
- **TBS (product safety):** Safety incidents reported to TBS; investigation within 72 hours for fire/explosion; can order product recall.
- **TCRA (counterfeit/uncertified):** TCRA enforcement against uncertified devices; market withdrawal possible.
- **Consumer protection (FCC):** Warranty refusal disputes escalated to FCC; investigation within 60 days.

### Escalation Triggers

- `safety_incident = Yes` AND `issue_type = fire_explosion_shock` — IMMEDIATE TBS product safety report; injuries advise medical attention; police/fire report if applicable
- `issue_type = battery_issue` AND `device_condition = swollen / leaking` — Safety risk; advise stop use immediately; TBS report
- `issue_type = counterfeit_device` AND `tcra_approval_mark = No` — TCRA enforcement complaint; criminal referral possible
- `issue_type = warranty_refusal` AND within warranty period — FCC consumer protection complaint
- `repair_attempt_count >= 3` AND same fault — Entitlement to replacement; escalate to manufacturer headquarters

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| product_brand | Chapa | Recommended | For routing to product team |
| product_category | Kategoria ya bidhaa | Yes | Routes to correct team |
| suggestion_category | Kategoria | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| ELS-01 | battery_life | Maisha mazuri ya betri |
| ELS-02 | durability | Kudumu kwa muda mrefu |
| ELS-03 | repairability | Urahisi wa kukarabati |
| ELS-04 | local_service_centers | Vituo vya huduma vya ndani ya nchi |
| ELS-05 | spare_parts | Upatikanaji wa vipande vya kubadilisha |
| ELS-06 | software_updates | Masasisho ya programu yanayodumu |
| ELS-07 | e_waste | Mpango bora wa taka za kielectroniki |
| ELS-08 | affordability | Bei nafuu zaidi |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina | Recommended | For tracking |
| product_name | Bidhaa | Yes | Core identifier |
| product_model | Modeli | Recommended | For technical queries |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| warranty_check | Je, bidhaa yangu iko chini ya udhamini? | serial_number, purchase_date |
| repair_center_location | Kituo cha ukarabati kiko wapi? | product_brand, location |
| driver_software | Wapi kupakua programu ya kifaa? | product_model |
| tcra_approval_check | Je, kifaa hiki kimeidhinishwa na TCRA? | product_brand, product_model |
| spare_parts | Vipande vya kubadilisha vinapatikana wapi? | product_brand, product_model |
| user_manual | Wapi kupata mwongozo wa kutumia? | product_name, product_model |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| product_name | Bidhaa iliyopongezwa | Yes | Product quality recognition |
| service_center_name | Kituo cha huduma | Conditional | If complimenting service |
| specific_aspect_praised | Kipengele | Yes | Kudumu / Huduma nzuri ya ukarabati / Ubora / Bei nzuri |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Brand NPS tracking |

---

## AI Conversation Guidance for This Industry

- **For safety incidents (fire, explosion, shock), stop all other data collection and escalate immediately.** "Hii ni dharura ya usalama! Acha kutumia kifaa mara moja. Kama kulikuwa na moto, piga simu ya zimamoto au dharura (+255 117). Tutaripoti tatizo hili kwa TBS mara moja."
- **Get the serial number before anything else.** The serial number is the single most important identifier for electronics complaints. Most devices have it under the battery, in Settings > About, or on the original box. "Nambari ya msururu (serial number) ya kifaa hiki inaonekana wapi — nyuma ya kifaa, kwenye kisanduku, au kwenye mipangilio?"
- **Confirm warranty status before collecting detailed fault description.** If the device is out of warranty, the resolution path changes. "Tarehe ya ununuzi ilikuwa lini? Na muda wa udhamini ni miezi mingapi?"
- **For software issues, ask for the error message verbatim.** Customers often describe what the error says — getting the exact text enables precise technical diagnosis.
- **Distinguish between a hardware fault and a software fault.** A cracked screen is hardware (physical repair); a random restart is potentially software (update or reset). This distinction saves time.
- **For counterfeit concerns, ask about where the device was purchased.** Street markets and informal traders are high-risk; official brand stores and authorized dealers should have TCRA-approved stock.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Product name | "Kifaa hiki kinaitwa nini — modeli yake na chapa yake?" |
| Serial number | "Nambari ya msururu (serial number) inaonekana nyuma ya kifaa, kwenye kisanduku, au Settings > About — inasema nini?" |
| Purchase date | "Kifaa hiki kilinunuliwa tarehe gani?" |
| Defect onset | "Tatizo hili lilianza lini baada ya ununuzi — siku ngapi au wiki ngapi?" |
| Safety incident | "Je, kifaa kililipuka, kuungua, au kutoa umeme wa mshtuko?" |
| TCRA mark | "Je, kifaa hiki kina alama ya kibali cha TCRA au TBS?" |
| Service center | "Je, umekwenda kituo chochote cha ukarabati kuhusu tatizo hili? Walisema nini?" |
| Desired outcome | "Unataka nini — kifaa kikarabatiwe, kibadilishwe na kipya, au upate pesa yako?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| safety_incident | Yes AND fire/explosion/shock | Immediate TBS product safety report; advise stop use; medical attention if injury; potential product recall |
| issue_type | battery_issue AND swollen/leaking | Safety risk; advise stop use and proper disposal; TBS safety report |
| issue_type | counterfeit_device AND tcra_mark absent | TCRA enforcement complaint; advise consumer to return or dispose safely |
| repair_attempt_count | >= 3 AND same fault | Entitlement to replacement; escalate to manufacturer headquarters; FCC complaint if refused |
| issue_type | warranty_refusal AND within warranty period | FCC consumer protection complaint; cite Fair Competition Act Cap. 285 |
| defect_onset | within 7 days of purchase | "Dead on arrival" standard; entitled to immediate replacement without repair |
| data_lost | Yes AND no backup | Document data loss; manufacturer may offer data recovery as part of settlement |
| issue_type | overheating AND charging | Advise use of original charger only; battery inspection; IEC 62133 safety standard reference |

---

*Sources: TBS Act Cap. 130, TCRA Act Cap. 306, TCRA Device Type Approval Regulations, Fair Competition Act Cap. 285, IEC 62133, EU LVD 2014/35/EU, ISO 10002:2018, ISO 9001:2015*
