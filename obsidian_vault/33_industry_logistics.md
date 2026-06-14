---
tags: [industry-kb, feedback-classification, field-standards]
---
# Logistics / Supply Chain & Delivery — Feedback Collection Fields & Standards

## Industry Identifiers

courier, freight forwarder, clearing agent, customs broker, last-mile delivery, cold chain, warehousing, port operations, trucking, cargo airline, consignment, airway bill, bill of lading, container, manifest, TPA (Tanzania Ports Authority), Dar es Salaam Port, TAZARA railway freight, DHL, G4S logistics, Siginon, bodaboda delivery, transit cargo, import clearance, export documentation, 3PL, supply chain, cross-border trade, bonded warehouse, cargo insurance, packing list, commercial invoice, certificate of origin, landlocked transit, dangerous goods, reefer container, cold storage, fleet management, last-mile, dispatch, waybill, SGD, TANCIS, TRA customs, TANROADS, demurrage, LCL, FCL, SSCC, EPCIS, GS1, traceability, tracking number, proof of delivery, freight rate, fuel surcharge

## Why Industry-Specific Fields Matter

Logistics complaints require shipment-level traceability identifiers (tracking number, waybill, SSCC) and financial accountability fields (declared value, claimed amount, invoice) that generic feedback forms do not capture — without these, the company cannot locate the shipment, assess liability, or process an insurance claim. In Tanzania, regulatory complexity adds customs documentation fields (SGD number, HS code, TRA duty calculation) that are unique to this sector and directly determine whether a complaint can be formally pursued with TRA, TPA, or a carrier.

## Source Standards

- GS1 Global Traceability Standard i2 and GS1 EPCIS — SSCC, GTIN, GLN, four-dimension traceability (what/where/when/why)
- ISO 28000:2022 Supply Chain Security Management — security incident categories (tampering, theft, seal integrity, unauthorized access)
- DHL Express Claim Form (US/EN) — standard financial and shipment fields for courier claims
- Standard Freight Claim Form (industry standard, Logistics Plus reference) — declared value, damage description, claimed amount
- OTIF CIM Uniform Rules (COTIF Appendix B) — freight delay liability and documentation
- Tanzania Revenue Authority (TRA) TANCIS system — SGD, HS code, duty calculation
- Tanzania Ports Authority (TPA) — port storage, demurrage, vessel manifest
- ISO 28000 (security incidents, compulsory insurance, seal monitoring)
- East African Community Customs Union (EAC) protocols — cross-border transit documentation

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| tracking_number | Nambari ya ufuatiliaji | Yes | Primary shipment locator; without this the logistics company cannot retrieve the consignment record |
| waybill_number | Nambari ya waybill | Yes | GS1 EPCIS; standard freight claim field; needed for carrier records and court-admissible documentation |
| shipment_date | Tarehe ya kutuma | Yes | GS1 EPCIS "When" dimension; anchors the timeline for delay and liability calculations |
| expected_delivery_date | Tarehe ya kupokea iliyotarajiwa | Yes | Establishes the contracted delivery window; determines whether delay constitutes breach |
| actual_delivery_date | Tarehe halisi ya kupokea (kama ilitolewa) | Conditional | GS1 EPCIS; calculates actual delay duration; required only if goods were received |
| shipper_name_address | Jina na anwani ya mtumaji | Yes | Freight claim standard; GS1 GLN; required to verify the consignment contract |
| consignee_name_address | Jina na anwani ya mpokeaji | Yes | Freight claim standard; GS1 GLN; needed for delivery verification |
| carrier_provider_name | Jina la kampuni ya usafirishaji | Yes | Determines which carrier liability regime applies (road, sea, air, rail) |
| service_type | Aina ya huduma | Yes | Drives conditional field logic; different standards apply to express, standard, freight, cold chain |
| issue_type | Aina ya tatizo | Yes | Core routing decision; determines which conditional fields apply |
| contents_description | Maelezo ya maudhui ya mzigo | Yes | Freight claim standard; needed for carrier liability assessment and customs records |
| number_of_packages | Idadi ya vifurushi | Yes | Freight claim standard; enables partial delivery verification |
| declared_value | Thamani iliyotangazwa | Yes | Freight claim standard: "carrier's maximum liability cannot exceed the declared value"; DHL claim form |
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Required for formal claim processing and regulatory referral |
| complainant_phone | Nambari ya simu | Yes | For follow-up and claim status notification |
| complainant_email | Barua pepe | Recommended | For formal written claim correspondence |

### Conditional Fields (collect based on issue type)

**If issue_type = Lost Shipment:**
- `last_known_location` — Last known location of shipment — GS1 EPCIS "Where" dimension (read point and business location)
- `sscc_number` — Serial Shipping Container Code (if applicable) — GS1 Global Traceability Standard i2 (mandatory logistics unit identifier)
- `driver_name_or_id` — Courier or driver name/ID who last handled the shipment
- `delivery_attempted_confirmation` — Was delivery marked as "attempted" in the tracking system? [Yes / No]
- `police_report_filed` — Was a police report filed? [Yes / No] — ISO 28000 (theft incident documentation)
- `police_report_number` — Police report reference number

**If issue_type = Damaged Goods:**
- `packaging_condition_on_receipt` — Packaging condition [Intact / Minor damage / Severely damaged / Opened / Missing] — freight claim standard (inspection requirement for shipments over $500)
- `seal_condition` — Seal condition [Intact / Broken / Missing / Tampered] — ISO 28000:2022 (security monitoring)
- `damage_description` — Detailed description of damage — DHL claim form
- `damage_photos` — Photos of damaged goods [file upload] — DHL claim form; freight claim standard
- `packaging_photos` — Photos of damaged packaging [file upload] — DHL claim form
- `inspection_report` — Carrier-conducted inspection report [file upload] — DHL claim form
- `repair_cost_estimate` — Estimated repair cost — DHL claim form
- `replacement_cost` — Replacement cost if repair is not possible — DHL claim form

**If issue_type = Customs / Documentation Failure:**
- `sgd_number` — Single Goods Declaration (SGD) number — TRA TANCIS system
- `hs_code_declared` — HS code declared by agent — TRA; OTIF CIM Appendix B
- `duty_amount_paid` — Duty amount paid — TRA
- `duty_amount_disputed` — Amount of disputed overcharge or underdeclared penalty — TRA
- `agent_name` — Clearing agent name or company — TRA; EAC Customs Union
- `document_type_in_question` — Which document is the issue? [Bill of Lading / Certificate of Origin / Commercial Invoice / Packing List / SGD / Import Permit / Pre-shipment Inspection Certificate / Other]
- `error_description` — Nature of the documentation error

**If issue_type = Tampered Packaging / Theft Suspected:**
- `seal_number_on_documentation` — Seal number stated on the shipping documents — ISO 28000:2022
- `seal_number_on_delivery` — Seal number found on delivery — ISO 28000 (discrepancy triggers security incident)
- `missing_items_description` — Description of missing items — freight claim standard
- `cargo_value_missing` — Estimated value of missing items — freight claim standard
- `security_incident_report` — Security incident report number if filed with ISO 28000-compliant carrier

**If issue_type = Cold Chain Failure:**
- `required_temperature_range` — Required temperature range (e.g., 2–8°C for pharmaceuticals) — ISO 28000; WHO cold chain standards
- `temperature_on_delivery` — Temperature recorded on delivery (if sensor data available)
- `goods_type` — [Pharmaceuticals / Vaccines / Fresh Produce / Frozen Food / Other]
- `spoilage_confirmed` — Goods confirmed spoiled? [Yes / No / Partial]
- `financial_loss_estimate` — Estimated value of spoiled goods

**All damage/loss claims (financial fields):**
- `amount_claimed` — Total amount claimed — freight claim standard: "total amount claimed must be specified"
- `currency` — Currency (TZS / USD / EUR / KES / Other) — DHL claim form
- `supporting_invoice` — Supporting invoice [file upload] — DHL claim form; freight claim standard
- `insurance_reference` — Insurance claim reference number (if insured) — ISO 28000:2022; industry standard
- `bill_of_lading_number` — Bill of Lading (B/L) number — freight claim standard

### Issue Type Classification

- `LOST_SHIPMENT` — Shipment not received, driver/courier uncontactable, tracking shows no movement
- `DAMAGED_GOODS` — Goods received in damaged condition
- `EXCESSIVE_DELAY` — Delivery beyond contracted or agreed timeline
- `WRONG_ITEM_DELIVERED` — Incorrect goods delivered (GS1 EPCIS "what" dimension mismatch)
- `PARTIAL_DELIVERY` — Only some packages/items received; remainder unaccounted for
- `TAMPERED_PACKAGING` — Seal broken, packaging opened, signs of pilferage
- `THEFT_SUSPECTED` — Goods missing with evidence suggesting theft or pilferage
- `WRONG_DELIVERY_ADDRESS` — Delivered to wrong location
- `CUSTOMS_DELAY` — Goods held at customs beyond standard clearance period
- `DOCUMENTATION_ERROR` — Incorrect HS code, wrong values, missing certificates, SGD errors
- `COLD_CHAIN_FAILURE` — Temperature-sensitive goods spoiled due to refrigeration failure
- `BILLING_DISPUTE` — Invoice differs from quote; undisclosed charges; demurrage dispute
- `STAFF_CONDUCT` — Bribery, rudeness, refusal to assist, misinformation
- `TRACKING_COMMUNICATION_FAILURE` — No updates, system shows incorrect status, no response from company

### Resolution Standards for This Industry

- **Freight claim standard**: Claims for damage must be submitted in writing to the carrier within 9 months of delivery (or expected delivery for loss). Carrier has 30 days to acknowledge and 120 days to settle or deny.
- **OTIF CIM (rail freight)**: The carrier is liable for delay from the moment of takeover to delivery. Delay compensation is calculated on the freight charge.
- **TRA TANCIS**: SGD errors by clearing agents can result in penalties to the importer; agents are liable to the client for errors they caused.
- **DHL claim form standard**: Claim submission requires tracking number, proof of value (invoice), photos of damage, and packaging photos.
- **ISO 28000 security incidents**: Organizations must maintain records of security-related incidents (tampering, theft) and report significant breaches to relevant authorities.
- **TPA (port)**: Demurrage begins accruing after free time (typically 5 days) expires. Complaints about unjustified demurrage can be lodged with TPA.

### Escalation Triggers (field values that require immediate escalation)

- `issue_type` = COLD_CHAIN_FAILURE + `goods_type` = Vaccines or Pharmaceuticals → immediate escalation; notify Tanzania Food and Drugs Authority (TFDA) if pharmaceutical; potential public health impact
- `issue_type` = THEFT_SUSPECTED + evidence of seal tampering → ISO 28000 security incident; notify carrier's security team and police within 24 hours
- `amount_claimed` > TZS 50,000,000 → senior management escalation; formal legal referral may apply
- `staff_conduct_type` = Bribery at customs border → report to Tanzania Prevention and Combating of Corruption Bureau (PCCB); do not handle internally only
- `goods_type` = Dangerous goods + `issue_type` = WRONG_DELIVERY_ADDRESS or LOST_SHIPMENT → hazardous materials emergency; notify relevant authority (TAEC for radioactive, TFDA for chemicals)
- `issue_type` = DAMAGED_GOODS + `goods_type` = Medical equipment → escalate immediately; downstream health impact
- Worker injury in warehouse → OSHA Tanzania notification; employer liability
- `issue_type` = LOST_SHIPMENT + driver_confirmed_collected = Yes + driver_now_unreachable = Yes → potential theft; police report required

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| suggestion_category | Aina ya pendekezo | Yes | Routes suggestion to the correct operational team |
| service_area | Eneo la huduma | Recommended | GS1 traceability improvement dimensions; geographic specificity enables action |
| specific_suggestion | Maelezo ya pendekezo | Yes | The substantive content |
| route_or_region | Njia au mkoa (kama husika) | Optional | Enables geographically targeted improvement |
| submitter_contact | Mawasiliano ya mtoa pendekezo | Optional | For follow-up on adoption |

### Industry-Specific Improvement Categories

- `TRACKING_SYSTEM` — Real-time GPS, customer portal, automated SMS milestones, WhatsApp bot
- `PACKAGING_STANDARDS` — Protective packaging, cold chain packaging, hazardous goods labeling
- `DELIVERY_TIME_WINDOWS` — Scheduled delivery windows, same-day options, upcountry reach
- `DOCUMENTATION_ACCURACY` — Digital document management, TRA TANCIS integration, pre-clearance review
- `CUSTOMER_COMMUNICATION` — Proactive delay notifications, single account manager, callback system
- `COLD_CHAIN_OPERATIONS` — Temperature logging equipment, dedicated cold chain team, compliance certificates
- `PRICING_TRANSPARENCY` — All-inclusive quotes, itemized invoices, no post-delivery surcharges
- `STAFF_TRAINING` — Anti-bribery training for border agents, customer service, cargo handling
- `COMPLIANCE_REGULATORY` — Driver licensing, vehicle roadworthiness, cargo insurance as default
- `RETURNS_PROCESS` — Reverse logistics, damaged goods return, refusal to accept process
- `ENVIRONMENTAL` — Fuel-efficient fleet, packaging waste reduction, carbon reporting

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| inquiry_type | Aina ya swali | Yes | Routes the inquiry to the right information source |
| tracking_number | Nambari ya ufuatiliaji | Conditional | Required for tracking status, customs status, and claims status inquiries |
| shipment_date | Tarehe ya kutuma | Conditional | Needed for status and delay inquiries |
| contact_for_response | Mawasiliano ya kujibu | Recommended | Enables callback, SMS, or email response |

### Common Inquiry Types & Required Data Per Type

- `TRACKING_STATUS` → tracking_number, waybill_number; carrier_provider_name
- `ESTIMATED_DELIVERY` → tracking_number; shipment_date; origin and destination
- `CUSTOMS_CLEARANCE_STATUS` → sgd_number or tracking_number; shipment_date; contents_description
- `CLAIMS_STATUS` → claim_reference_number; tracking_number; date_claim_submitted
- `RATE_QUERY` → service_type; origin; destination; weight_kg; cargo_type
- `DOCUMENTATION_QUERY` → cargo_type; origin country; destination country; specific_document_needed
- `RETURNS_QUERY` → tracking_number; reason_for_return; goods_condition
- `INSURANCE_QUERY` → shipment_type; declared_value; coverage_type_requested
- `WAREHOUSE_QUERY` → location; goods_type; storage_requirements (temperature, security)
- `CUSTOMS_DUTY_QUERY` → hs_code (if known); goods_description; origin country; CIF value estimate

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| carrier_provider_name | Jina la kampuni | Yes | Routes compliment to the correct operator for staff recognition |
| courier_driver_name_or_id | Jina/nambari ya courier au dereva | Recommended | Enables specific staff recognition |
| delivery_date | Tarehe ya uwasilishaji | Yes | Anchors the compliment to a specific service event |
| positive_behavior_category | Aina ya mwenendo mzuri | Recommended | Enables positive performance pattern tracking |
| positive_experience_description | Maelezo ya uzoefu mzuri | Yes | The substantive record for staff recognition |
| tracking_number | Nambari ya ufuatiliaji | Optional | Allows verification and ties compliment to a specific shipment |
| submitter_contact | Mawasiliano ya mtoa sifa | Optional | For acknowledgement |

---

## AI Conversation Guidance for This Industry

- **Start with the tracking or waybill number:** The single most important field. Open with "Let me help you with this — do you have a tracking number or waybill number for the shipment? It's usually on the receipt or the email confirmation you received when the shipment was sent." If the user does not have it, collect shipper name, consignee name, and approximate shipment date as fallback identifiers.
- **Distinguish role before collecting fields:** Ask early "Are you the person who sent the goods, or the person who was supposed to receive them?" Sender and receiver have different information (the sender has the waybill and declared value; the receiver has the delivery condition and packaging photos). This shapes which fields are practical to ask.
- **For damage claims, guide the user to preserve evidence:** Say "Before we continue — if the goods were damaged, please keep the original packaging as it is and take photos of both the packaging and the damaged items. This is required to process a damage claim." Do not let the user dispose of packaging before photos are taken.
- **Customs and documentation issues require agent identification:** If the complaint involves customs delay, wrong duty, or document errors, ask "Do you have a clearing agent who handled this shipment?" Then collect the agent's name and company, the SGD number, and the specific document issue. Without the agent name, the complaint cannot be routed to TRA or referred for PCCB action if bribery is involved.
- **Bribery at the border is a sensitive escalation:** If the user mentions paying "facilitation fees," "extra charges at the border," or a driver paying bribes, acknowledge this without judgment: "Unofficial payments at customs are a serious issue and we can help you report this formally. Do you have any evidence such as receipts, messages, or names?" Route to PCCB referral path.
- **Cold chain complaints are urgent:** If the user mentions vaccines, medicines, or perishable goods that were delayed or temperature-compromised, treat with urgency and ask about the goods type first — this determines whether TFDA notification is needed.

## Swahili Key Phrases for Field Collection

- "Je, una nambari ya ufuatiliaji au waybill ya mzigo huu?" — Do you have a tracking or waybill number for this shipment?
- "Ulikuwa mtumaji au mpokeaji wa mzigo huu?" — Were you the sender or the receiver of this shipment?
- "Tarehe ya kutuma ilikuwa lini, na mzigo ulitakiwa kufikia lini?" — What was the sending date, and when was the shipment expected to arrive?
- "Mzigo ulioharibiwa — tafadhali weka ufungaji kama ulivyo na piga picha kabla ya kutupa chochote." — For damaged goods — please keep the packaging as it is and take photos before discarding anything.
- "Nambari ya SGD au uthibitisho wa forodha una nambari gani?" — What is the SGD number or customs clearance reference?
- "Je, ulilipa malipo yoyote yasiyokuwa rasmi katika mpaka?" — Did you pay any unofficial payments at the border?
- "Kampuni gani ya usafirishaji ilishughulikia mzigo huu?" — Which logistics company handled this shipment?
- "Thamani ya bidhaa zilizopotea au kuharibiwa ni kiasi gani?" — What is the value of the goods that were lost or damaged?
- "Je, una picha za bidhaa zilizoharibiwa na ufungaji wake?" — Do you have photos of the damaged goods and packaging?
- "Mzigo ulikuwa na bima?" — Was the shipment insured?

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| goods_type | Vaccines or Pharmaceuticals + issue_type = COLD_CHAIN_FAILURE | Immediate escalation; notify TFDA Tanzania; document temperature data as evidence |
| issue_type | THEFT_SUSPECTED + seal_condition = Tampered | ISO 28000 security incident; file police report; notify carrier's security team within 24 hours |
| staff_conduct_type | Bribery at customs | Refer to PCCB (Prevention and Combating of Corruption Bureau); do not resolve internally |
| amount_claimed | > TZS 50,000,000 | Senior management escalation; formal legal review; ensure all GS1 EPCIS traceability data is preserved |
| goods_type | Dangerous goods + issue_type = LOST_SHIPMENT | Emergency escalation; notify TAEC (if radioactive) or TFDA (if chemical/pharmaceutical) |
| issue_type | DOCUMENTATION_ERROR + cause = Clearing agent | Claim against agent's professional indemnity insurance; file complaint with TRA if duty overpayment confirmed |
| provider_response_received | No response within 30 days | Formal carrier liability claim; freight claim standard 30-day acknowledgement rule |
| issue_type | BILLING_DISPUTE + charge_not_in_original_quote = Yes | Request itemized invoice; compare against freight quote; formal dispute if >15% variance |
| packaging_condition_on_receipt | Severely damaged or Opened | Preserve as evidence; instruct recipient not to use or dispose of goods; initiate damage survey |
| issue_type | DAMAGED_GOODS + goods_type = Medical equipment | Urgent escalation; downstream health implications; TFDA notification if medical devices |

---

## Key Entities & Roles

**Regulatory Bodies:**
Tanzania Revenue Authority (TRA) — customs duty, TANCIS, SGD; Tanzania Ports Authority (TPA) — port operations, demurrage; TANROADS — road transport compliance; Tanzania Atomic Energy Commission (TAEC) — radioactive cargo; TFDA (Tanzania Food and Drugs Authority) — pharmaceutical/food cargo; OSHA Tanzania — workplace safety; PCCB — corruption at border; EAC Customs Union; COMESA; SADC trade protocols

**Industry Participants:**
DHL, G4S Logistics, Siginon, Bolloré, MSC, Maersk, CMA CGM, Ethiopian Airlines Cargo, Dar es Salaam Container Terminal (DCT), TICTS, ICTSI

**Key Documents:**
Bill of Lading (B/L), Airway Bill (AWB), Single Goods Declaration (SGD), packing list, commercial invoice, certificate of origin, import permit, pre-shipment inspection certificate, waybill, Delivery Note, Proof of Delivery (POD), cargo insurance certificate, MSDS (dangerous goods safety data sheet), SSCC label

**Key Infrastructure:**
Dar es Salaam Port, Tanga Port, Mtwara Port, TAZARA railway freight, TANZAM Highway, Namanga border, Holili/Taveta border, Sirari border (Kenya), Kasumulu border (Malawi), Inland Container Depot (ICD), bonded warehouse, cold storage, JNIA and KIA airfreight terminals

---

## Disambiguation Notes

- **Logistics vs. Retail Delivery:** Retail KB (32) covers delivery by a retail brand's own riders. This KB covers specialist freight forwarders, courier companies, clearing agents, and 3PL providers.
- **Logistics vs. Transport/Transit:** Personal luggage or parcel sent via intercity bus and not received → check Transport KB (42) first. Standalone freight consignment via a logistics company → this KB.
- **Bodaboda delivery vs. bodaboda transport:** If the bodaboda was carrying a parcel for a logistics company or e-commerce brand, this is Logistics KB. If the bodaboda was carrying a person, that is Transport KB (42).
- **Logistics vs. Government/Embassy:** Import duty disputes and customs documentation errors are Logistics KB. Visa, work permit, and government document complaints belong in Government/Embassy KB (35 or 36).
- **Logistics vs. Finance/Banking:** Payment disputes about a freight invoice belong here. Payment disputes involving mobile money, bank transfers, or merchant payments belong in Finance/Banking KB (23).
