---
tags: [industry-kb, field-standards, feedback-fields, logistics, supply-chain]
---
# Logistics / Supply Chain — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: logistics, msururu wa ugavi, supply chain, delivery, uwasilishaji, courier, DHL, FedEx, EMS, Tanzania Post, TanzPost, Posta Tanzania, kila, parcel, package, kifurushi, shipment, mzigo, cargo, freight, sender, mtumaji, recipient, mpokeaji, tracking number, nambari ya ufuatiliaji, waybill, hati ya usafirishaji, customs, forodha, clearance, usafishaji wa forodha, import, uingizaji, export, usafirishaji nje, warehouse, ghala, inventory, hesabu ya bidhaa, last-mile delivery, uwasilishaji wa mwisho, truck, lori, tipper, container, kontena, shipping line, Maersk, MSC, CMA-CGM, TPA, TRL, Tanzania Railways, TAZARA, air cargo, usafirishaji wa hewa, JNIA, Kilimanjaro Airport, KIA, cold chain, mnyororo wa baridi, temperature-controlled, reverse logistics, returns management, 3PL, fourth-party logistics, customs broker, wakala wa forodha, TRA customs, GEPCO, MAZO, RAHA

## Why Industry-Specific Fields Matter

Logistics complaints include lost/damaged parcels (requiring tracking number, declared value, insurance status), delayed deliveries (requiring tracking number, promised delivery date, actual date), customs clearance issues (requiring bill of lading, HS code, TRA customs reference), and temperature-controlled shipment failures (requiring cold chain records, product type). Without logistics-specific fields, the AI cannot generate a claim against the courier's insurance, identify the customs entry point for TRA follow-up, or distinguish between carrier liability and shipper error.

## Source Standards

- Tanzania Postal Corporation Act, Cap. 212 — postal and courier services
- SUMATRA Act, Cap. 413 — freight transport regulation
- Tanzania Customs and Excise Act (TRA) — import/export compliance
- IATA Cargo Handling Manual (CCHM) — air cargo standards (reference)
- UPU Convention and Regulations — Universal Postal Union (international parcels)
- CMR Convention — international road haulage (reference standard)
- IATA Resolution 600a/b — air cargo liability
- ISO 9001:2015 — quality management
- ISO 28000:2022 — Security management systems for supply chains
- ISO 10002:2018 — complaints handling
- Tanzania Bureau of Standards — product certification for imports

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL logistics complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | For claim registration and follow-up |
| complainant_phone | Nambari ya simu | Yes | Status updates |
| complainant_role | Nafasi ya mlalamikaji | Yes | Sender / Recipient / Third party — determines liability and rights |
| courier_or_carrier_name | Jina la kampuni ya usafirishaji / courier | Yes | Routes complaint to correct operator |
| tracking_number | Nambari ya ufuatiliaji | Yes | Single most important identifier; enables immediate shipment trace |
| waybill_or_airway_bill | Nambari ya waybill / AWB | Recommended | For air and sea freight complaints |
| shipment_type | Aina ya usafirishaji | Yes | Parcel / Road freight / Air cargo / Sea cargo / Railway — determines liability regime |
| origin_location | Mahali pa kutoka | Yes | For route and liability analysis |
| destination_location | Mahali pa kwenda | Yes | Last-mile delivery routing |
| declared_value_tzs | Thamani iliyoashiria (TZS) | Yes | Required for loss/damage claims; determines compensation ceiling |
| shipment_contents | Yaliyomo kwenye mzigo | Yes | For damage assessment and customs compliance check |
| insured | Je, mzigo ulikuwa na bima? | Yes | Determines insurance claim path vs. carrier liability claim |
| insurance_reference | Nambari ya bima ya mzigo | Conditional | For insured shipment claims |
| promised_delivery_date | Tarehe ya uwasilishaji iliyoahidiwa | Conditional | For delay complaints |
| issue_type | Aina ya tatizo | Yes | Complaint taxonomy |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; detailed narrative |
| desired_outcome | Matokeo unayotaka | Yes | Compensation / Delivery / Refund / Investigation |

### Conditional Fields (collect based on issue type)

**If issue_type = Lost Parcel / Shipment:**
Also collect:
- `last_tracking_status` — Hali ya mwisho ya ufuatiliaji: "In transit" / "Out for delivery" / "Customs hold" — narrows search area
- `packaging_description` — Maelezo ya ufungashaji: Color, size, labels — for identification at depots
- `claim_notification_date` — Tarehe ya kutoa taarifa ya kupotea: Most carriers require loss notification within 14–30 days

**If issue_type = Damaged Goods:**
Also collect:
- `damage_type` — Aina ya uharibifu: Physical damage / Moisture / Contamination / Breakage / Missing items
- `damage_discovered_at` — Uharibifu uligundulika wapi: At collection / On delivery / After delivery
- `photos_of_damage_available` — Je, picha za uharibifu zinapatikana?: Required for all damage claims
- `original_packaging_intact` — Je, ufungashaji wa asili ulikuwa sawa?: For liability determination (carrier vs. packing)
- `original_invoice_available` — Je, ankara ya asili ya bidhaa inapatikana?: For declared value verification

**If issue_type = Customs Clearance Issue:**
Also collect:
- `bill_of_lading_number` — Nambari ya hati ya mzigo wa bahari (B/L)
- `hs_code` — Msimbo wa HS wa bidhaa: For TRA customs classification disputes
- `customs_entry_number` — Nambari ya ingizo la forodha (TRA)
- `duty_charged_tzs` — Ada ya forodha iliyotozwa (TZS)
- `duty_expected_tzs` — Ada ya forodha inayotarajiwa (TZS)
- `goods_held_at_port` — Je, bidhaa zimeshikiliwa bandarini? Yes / No
- `customs_broker_name` — Jina la wakala wa forodha aliyetumika

**If issue_type = Temperature / Cold Chain Failure:**
Also collect:
- `required_temperature_celsius` — Joto linaloohitajika (°C)
- `temperature_at_delivery_celsius` — Joto la wakati wa uwasilishaji (°C)
- `cold_chain_log_available` — Je, kumbukumbu za mnyororo wa baridi zinapatikana?: Required for pharmaceutical/food cold chain claims
- `product_compromised` — Je, bidhaa imeathirika (dawa, chakula, kielelezo cha maabara)?: Public health implications

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| LG-01 | lost_parcel | Shipment cannot be located; presumed lost |
| LG-02 | damaged_goods | Goods received in damaged condition |
| LG-03 | delivery_delay | Delivery significantly later than promised |
| LG-04 | wrong_delivery | Goods delivered to wrong address or wrong recipient |
| LG-05 | missing_items | Partial delivery; items missing from consignment |
| LG-06 | customs_delay | Clearance unreasonably delayed by carrier/customs broker |
| LG-07 | customs_overcharge | Incorrect duty or tax applied at customs |
| LG-08 | cold_chain_failure | Temperature-sensitive goods not kept within required range |
| LG-09 | theft_pilferage | Suspected theft from shipment |
| LG-10 | documentation_error | Wrong documents provided; shipment rejected at destination |
| LG-11 | tracking_failure | Tracking system not updating; no visibility of shipment |
| LG-12 | claim_refusal | Carrier refuses to pay valid loss/damage claim |
| LG-13 | warehouse_damage | Goods damaged while in warehouse storage |
| LG-14 | carrier_misconduct | Rude, unresponsive, or dishonest carrier staff |
| LG-15 | demurrage_dispute | Excessive or incorrect demurrage/storage charges |

### Resolution Standards

- **Domestic courier (Tanzania):** Carriers should acknowledge claims within 5 business days; resolve within 30 days.
- **International courier (DHL/FedEx):** IATA and UPU conventions; claims typically resolved within 30–60 days; international arbitration for large claims.
- **Customs disputes (TRA):** TRA objection period is 30 days from assessment; Tax Appeals Board for unresolved disputes.
- **Insurance claims:** Cargo insurance claims typically 30–90 days depending on investigation scope.
- **Loss declaration:** Most carriers require formal loss notification within 14 days of expected delivery; damage within 7 days of delivery.
- **Liability limits:** Domestic road freight under Tanzania law; international air cargo under IATA Resolution; sea freight under Hague-Visby Rules.

### Escalation Triggers

- `issue_type = theft_pilferage` AND significant value — Immediate police report AND carrier security team; potential criminal investigation
- `issue_type = cold_chain_failure` AND pharmaceutical / vaccine / food — TFDA and MOHCDGEC notification if medicines or vaccines compromised
- `issue_type = customs_overcharge` AND systematic pattern — TRA Commissioner referral; Tax Appeals Board
- `declared_value_tzs > 5,000,000` AND loss or damage — Senior claims officer review; legal counsel may be needed
- `issue_type = documentation_error` AND goods held at port with accruing demurrage — Urgent; delays are costly; escalate to customs broker and carrier immediately
- `claim_refusal = Yes` AND valid claim within carrier liability — Legal referral; SUMATRA complaint for licensed carriers

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| carrier_name | Kampuni ya usafirishaji | Recommended | For routing |
| suggestion_category | Kategoria | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| LGS-01 | tracking_visibility | Ufuatiliaji wa wakati halisi |
| LGS-02 | packaging_standards | Viwango bora vya ufungashaji |
| LGS-03 | cold_chain | Mnyororo wa baridi bora |
| LGS-04 | last_mile_delivery | Uwasilishaji bora wa mwisho |
| LGS-05 | claims_process | Mchakato wa madai haraka zaidi |
| LGS-06 | customs_integration | Ushirikiano bora na forodha |
| LGS-07 | rural_delivery | Uwasilishaji maeneo ya vijijini |
| LGS-08 | digital_documentation | Nyaraka za kidijitali |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina | Recommended | For tracking |
| tracking_number | Nambari ya ufuatiliaji | Conditional | For shipment-specific queries |
| carrier_name | Kampuni | Conditional | For carrier-specific queries |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| shipment_status | Wapi mzigo wangu sasa hivi? | tracking_number |
| customs_requirements | Mahitaji ya forodha kwa bidhaa hizi | shipment_contents, hs_code |
| delivery_timeline | Mzigo utafika lini? | origin, destination, shipment_type |
| claim_process | Jinsi ya kudai fidia ya mzigo | carrier_name |
| rates | Bei ya kusafirisha | origin, destination, weight |
| restricted_items | Bidhaa ambazo haziruhusiwi kusafirishwa | destination_country |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| carrier_name | Kampuni | Yes | Routes to manager |
| staff_name | Jina la mfanyakazi | Recommended | Staff recognition |
| specific_aspect_praised | Kipengele | Yes | Uwasilishaji wa haraka / Utunzaji wa bidhaa / Ufuatiliaji mzuri / Huduma nzuri |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Carrier KPI tracking |

---

## AI Conversation Guidance for This Industry

- **Always ask for the tracking number first.** It is the single most actionable piece of information. "Nambari ya ufuatiliaji (tracking number) ya mzigo wako ni ipi? Inaweza kuonekana kwenye risiti ya kutuma au ujumbe wa kuthibitisha."
- **Determine sender vs. recipient role immediately.** The rights and obligations differ; sender holds the contract but recipient often has the delivery interest. "Je, wewe ndiye uliyetuma mzigo, au ndiye unaopaswa kupokea?"
- **For damage claims, ask about packaging condition.** If packaging is intact and goods are damaged, this is typically carrier liability. If packaging is damaged, it helps establish at what point damage occurred. "Je, ufungashaji wa nje ulikuwa sawa au uliathirika wakati wa kupokea?"
- **For customs complaints, distinguish between TRA (government) and the customs broker.** Many delays are broker errors, not TRA errors. "Je, tatizo linahusiana na TRA moja kwa moja, au ni wakala wa forodha aliyefanya kosa?"
- **For cold chain failures, assess health/safety immediately.** If medicines or vaccines are involved, this is a potential public health issue requiring TFDA notification. "Bidhaa zinazohusika ni za aina gani — dawa, chakula, kielelezo cha maabara, au kitu kingine?"
- **Advise on claim notification deadlines.** Many customers lose valid claims because they don't know about the notification window. "Kwa mzigo uliopotea au kuharibika, taarifa inapaswa kutolewa ndani ya siku 7–14 — ni muhimu kufanya hivi haraka."

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Tracking number | "Nambari ya ufuatiliaji ya mzigo huu ni ipi?" |
| Role | "Je, wewe ni mtumaji wa mzigo au mpokeaji?" |
| Carrier name | "Kampuni ya usafirishaji inaitwa nini?" |
| Declared value | "Thamani ya bidhaa zilizotumwa ilikuwa kiasi gani?" |
| Insurance | "Je, mzigo ulikuwa na bima? Ikiwa ndiyo, bima ya kampuni gani?" |
| Damage photos | "Je, una picha za uharibifu wa bidhaa au ufungashaji? Zitatusaidia sana" |
| Last tracking status | "Nambari ya ufuatiliaji inaonyesha nini hivi karibuni? Hali ya mwisho iliyoonekana ilikuwa nini?" |
| Customs entry | "Je, una nambari ya ingizo la forodha (customs entry number) au hati ya mzigo (B/L)?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | theft_pilferage | Police report AND carrier security team; criminal investigation; preserve evidence |
| issue_type | cold_chain_failure AND medicines/vaccines | TFDA notification; MOHCDGEC if vaccines; stop distribution of compromised goods |
| declared_value_tzs | > 5,000,000 | Senior claims officer; legal counsel review; insurance claim parallel track |
| issue_type | customs_overcharge | TRA objection within 30 days; Tax Appeals Board if unresolved |
| issue_type | claim_refusal AND within liability | Legal referral; SUMATRA complaint for licensed domestic carriers |
| damage_discovered_at | On delivery AND packaging intact | Carrier liability; document with delivery agent signature; photos critical |
| claim_notification_date | approaching or past carrier deadline | Urgent; advise immediate formal notification in writing even if late; preserve rights |

---

*Sources: Tanzania Postal Corporation Act Cap. 212, SUMATRA Act Cap. 413, TRA Customs Act, UPU Convention, IATA Resolution 600a/b, CMR Convention, ISO 28000:2022, ISO 10002:2018*
