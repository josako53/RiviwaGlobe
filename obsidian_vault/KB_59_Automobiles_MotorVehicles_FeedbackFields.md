---
tags: [industry-kb, field-standards, feedback-fields, automobiles, motor-vehicles]
---
# Automobiles / Motor Vehicles — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: gari, car, vehicle, automobile, motor vehicle, Toyota, Nissan, Mitsubishi, Suzuki, Honda, Hyundai, Kia, Ford, Mercedes, BMW, Volkswagen, Subaru, Isuzu, pickup, truck, lorry, lori, salon car, gari dogo, SUV, 4x4, forklift, motorcycle, pikipiki, baiskeli, bicycle, new car, gari jipya, used car, gari la zamani, dealership, mnunuzi wa gari, showroom, service center, ukarabati, garage, mechanic, fundi wa gari, spare parts, vipande vya kubadilisha, oil change, mabadiliko ya mafuta, brake, breki, engine, injini, transmission, gearbox, suspension, shock absorber, steering, mwongozo, bodywork, mwili wa gari, paint, rangi, warranty, udhamini, dealer, TRA, vehicle registration, usajili wa gari, road tax, kodi ya barabara, insurance, bima ya gari, logbook, hati ya umiliki, recall, urejeshaji, lemon, auto loan, mkopo wa gari, hire purchase, awali

## Why Industry-Specific Fields Matter

Automobile complaints span dealer fraud (odometer tampering, misrepresented condition), manufacturing defects (requiring VIN, production date, defect code), warranty disputes (requiring service history records), and financing disputes (requiring hire purchase agreement number). Without vehicle-specific fields like VIN/chassis number, the AI cannot identify the exact vehicle for recall lookup, warranty verification, or dealer accountability under TRA vehicle registration records.

## Source Standards

- Tanzania Road Traffic Act, Cap. 168 — vehicle registration, roadworthiness
- TRA Vehicle Registration Regulations — vehicle identification requirements
- Tanzania Fair Competition Act, Cap. 285 — dealer and manufacturer consumer protection
- Motor Vehicle Dealers Act (reference from comparable EAC jurisdictions)
- ISO 10002:2018 — complaints handling
- ISO 26262 — Functional Safety for Road Vehicles (reference for defect complaints)
- UNECE WP.29 regulations — vehicle technical requirements (reference)
- Tanzania Hire Purchase Act, Cap. 431 — financing agreements
- BOT consumer protection guidelines — auto loan disputes

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL automobile complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Consumer protection identification |
| complainant_phone | Nambari ya simu | Yes | For status updates |
| vehicle_registration_number | Nambari ya usajili wa gari | Yes | TRA primary identifier; enables ownership verification |
| vehicle_vin_chassis_number | Nambari ya VIN / chassis | Yes | Unique vehicle identifier; required for manufacturer recall lookup |
| vehicle_make | Chapa ya gari (Make) | Yes | Toyota / Nissan / Mitsubishi etc. — manufacturer identification |
| vehicle_model | Modeli ya gari | Yes | For warranty and technical specification lookup |
| vehicle_year | Mwaka wa uzalishaji | Yes | For warranty determination and recall applicability |
| vehicle_color | Rangi ya gari | Recommended | For identification when registration is unclear |
| odometer_reading_km | Usomaji wa mita ya umbali (km) | Recommended | For warranty (kilometer-based) and service history |
| purchase_date | Tarehe ya ununuzi | Yes | For warranty period start date |
| purchase_type | Aina ya ununuzi | Yes | New / Used / Hire Purchase / Lease |
| dealer_or_seller_name | Jina la muuzaji / dealer | Yes | Accountability routing |
| issue_type | Aina ya tatizo | Yes | Complaint taxonomy |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; technical narrative |
| safety_implication | Je, tatizo linaathiri usalama wa udereva? | Yes | Safety-critical defects require immediate manufacturer notification |
| desired_outcome | Matokeo unayotaka | Yes | Repair / Replacement / Refund / Compensation |
| receipt_or_logbook_available | Je, risiti au hati ya umiliki inapatikana? | Yes | Proof of purchase and ownership |

### Conditional Fields (collect based on issue type)

**If issue_type = Manufacturing Defect / Safety Recall:**
Also collect:
- `defect_description_technical` — Maelezo ya kiufundi ya hitilafu: e.g., "breki hazikatii vizuri kwenye kasi > 80km/h"
- `defect_first_noticed_km` — Tatizo lilianza wakati gari lilikuwa na umbali gani (km)?
- `service_history_records` — Je, kumbukumbu za huduma zinapatikana?: Required for warranty and defect investigation
- `manufacturer_recall_number` — Nambari ya urejeshaji wa mtengenezaji (kama inajulikana): For recall-related complaints
- `dealer_service_attempts` — Idadi ya majaribio ya ukarabati kwa tatizo moja: Multiple failed repairs may trigger replacement right

**If issue_type = Dealer Fraud / Misrepresentation:**
Also collect:
- `advertised_condition` — Hali iliyotangazwa na muuzaji: e.g., "gari jipya", "accident-free", "low mileage"
- `actual_condition` — Hali halisi iliyogunduliwa
- `odometer_suspected_tampering` — Je, mita ya umbali inashukiwa kubadilishwa? Yes / No: Criminal offense under Road Traffic Act
- `independent_inspection_report` — Je, ukaguzi huru wa gari umefanywa?: For evidence
- `documents_provided_at_sale` — Nyaraka zilizotolewa wakati wa mauzo: Logbook / Import duty receipt / Inspection certificate

**If issue_type = Hire Purchase / Auto Loan Dispute:**
Also collect:
- `hp_agreement_number` — Nambari ya mkataba wa hire purchase
- `lender_name` — Jina la mkopeshaji: Bank / Microfinance / Finance company
- `monthly_installment_tzs` — Malipo ya kila mwezi (TZS)
- `installments_paid` — Malipo yaliyofanywa hadi sasa
- `disputed_charge_type` — Aina ya malipo yanayobiwabishwa: Interest / Penalty / Repossession / Early settlement fee
- `repossession_notice_received` — Je, notisi ya kuchukua gari ilitolewa? Yes / No

**If issue_type = Vehicle Service / Repair Complaint:**
Also collect:
- `service_center_name` — Jina la kituo cha huduma / garage
- `repair_type` — Aina ya ukarabati uliofanywa
- `repair_cost_tzs` — Gharama ya ukarabati (TZS)
- `repair_date` — Tarehe ya ukarabati
- `fault_recurring_after_repair` — Je, tatizo limerudia baada ya ukarabati? Yes / No
- `parts_used_genuine` — Je, vipande vilivyotumika ni vya asili (genuine) au vya nakala?

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| AV-01 | manufacturing_defect | Vehicle has inherent defect from factory |
| AV-02 | safety_recall | Manufacturer recall complaint or failure to notify |
| AV-03 | dealer_fraud | Misrepresentation of vehicle condition, odometer, or history |
| AV-04 | warranty_refusal | Manufacturer or dealer refuses valid warranty claim |
| AV-05 | poor_repair_quality | Service center repair inadequate; fault recurs |
| AV-06 | overcharge_service | Overcharged for service, parts, or labor |
| AV-07 | counterfeit_spare_parts | Non-genuine parts sold as original |
| AV-08 | hire_purchase_dispute | Dispute over HP terms, repossession, or charges |
| AV-09 | registration_title_issue | Problems with vehicle registration or title transfer |
| AV-10 | delivery_delay | New vehicle not delivered on promised date |
| AV-11 | import_vehicle_defect | Imported vehicle with undisclosed prior damage |
| AV-12 | unsatisfied_customer | General dissatisfaction with dealer service |
| AV-13 | odometer_tampering | Suspected rollback or tampering with odometer |
| AV-14 | insurance_motor_claim | Motor insurance claim complaint (cross-reference KB_48) |
| AV-15 | lemon_vehicle | Vehicle repeatedly fails; multiple major repairs needed |

### Resolution Standards

- **Dealer level:** Consumer protection standard requires resolution within 30 days; manufacturer complaints within 60 days.
- **Warranty repairs:** Must be completed within reasonable time (typically 14–21 days); "reasonable number of attempts" = 3 for same fault.
- **Lemon law equivalent:** While Tanzania lacks a formal Lemon Law, after 3–4 failed repairs for the same defect, replacement or refund is the standard industry resolution.
- **Hire Purchase:** Tanzania Hire Purchase Act requires proper notice before repossession; default settlement process required.
- **TRA (odometer tampering):** Criminal offense; police report required; TRA can check import history.
- **Manufacturer recall:** Manufacturers must address recalled vehicles free of charge within specified timeframes.

### Escalation Triggers

- `issue_type = manufacturing_defect` AND `safety_implication = Yes` — Immediate manufacturer safety team notification; potential safety recall
- `issue_type = odometer_tampering` — Criminal offense; police report AND TRA referral; FCC consumer fraud complaint
- `issue_type = dealer_fraud` AND misrepresentation of significant nature — FCC consumer protection complaint
- `issue_type = hire_purchase_dispute` AND repossession_notice_received = No — Illegal repossession; legal aid referral; BOT consumer protection
- `dealer_service_attempts >= 3` AND same defect — Entitlement to replacement; escalate to manufacturer headquarters
- `issue_type = counterfeit_spare_parts` AND safety-critical parts (brake, steering) — TBS enforcement; criminal referral; SUMATRA safety concern

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| vehicle_make | Chapa ya gari | Recommended | For routing |
| dealer_name | Muuzaji | Recommended | For dealer-specific routing |
| suggestion_category | Kategoria | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| AVS-01 | genuine_parts_availability | Upatikanaji wa vipande halisi |
| AVS-02 | service_quality | Ubora wa huduma ya gari |
| AVS-03 | transparent_pricing | Bei wazi za ukarabati na vipande |
| AVS-04 | certified_mechanics | Mafundi waliohitimu |
| AVS-05 | local_assembly | Ubunifu wa magari nchini |
| AVS-06 | electric_vehicles | Magari ya umeme |
| AVS-07 | financing_accessibility | Mikopo ya gari inayopatikana zaidi |
| AVS-08 | after_sales_service | Kuboresha huduma baada ya mauzo |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina | Recommended | For tracking |
| vehicle_make | Chapa | Conditional | For vehicle-specific queries |
| vehicle_model | Modeli | Conditional | For technical queries |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| warranty_check | Je, gari langu liko chini ya udhamini? | vin_number, purchase_date |
| recall_check | Je, gari langu limerejeshwa? | vin_number, vehicle_make |
| service_schedule | Ratiba ya huduma ya gari | vehicle_model, odometer |
| spare_parts_price | Bei ya kipande fulani | vehicle_make, vehicle_model |
| registration_process | Jinsi ya kusajili gari | vehicle_type |
| hp_balance | Deni linalobaki la hire purchase | hp_agreement_number |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| dealer_or_service_center | Muuzaji / Kituo cha huduma | Yes | Routes to management |
| staff_name | Jina la mfanyakazi | Recommended | Staff recognition |
| specific_aspect_praised | Kipengele | Yes | Huduma ya haraka / Uaminifu / Ujuzi wa kiufundi / Ubora wa ukarabati |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Dealer performance benchmarking |

---

## AI Conversation Guidance for This Industry

- **Get the VIN/chassis number early.** This is the universal vehicle identifier that enables recall lookup, import history verification, and warranty claims. It is typically found on the dashboard (visible through windscreen), door jamb, or in the engine bay. "Nambari ya VIN au chassis inaonekana kwenye dashibodi ndani ya gari, kwenye mlango, au injinini — ni nambari na herufi 17 kwa magari mengi."
- **For safety-related defects, assess urgency immediately.** Ask "Je, tatizo hili linaathiri breki, usukani, au mfumo mwingine wa usalama?" — if yes, advise not to drive the vehicle until inspected.
- **For dealer fraud complaints, ask about the inspection before purchase.** "Je, gari hili lilichunguzwa na fundi wa kujitegemea kabla ya kununua?" — most fraud complaints involve skipped pre-purchase inspections.
- **For hire purchase disputes, establish the agreement terms first.** "Mkataba wa hire purchase una masharti gani — malipo ya kila mwezi ni kiasi gani, na muda ni miaka mingapi?"
- **Do not make technical diagnoses.** Describe observed symptoms clearly: "Eleza tatizo unavyoona — sauti gani, moshi gani, tatizo linatokea lini (wakati wa kufungua gari, wakati wa mwendo, wakati wa kusimama)?"
- **For odometer tampering, treat as a serious matter.** This is a criminal offense in Tanzania. "Kama mita ya umbali inashukiwa kubadilishwa, hii ni suala la jinai — tunashauri kuwasiliana na polisi na TRA."

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Vehicle registration | "Nambari ya usajili wa gari (sahani) ni ipi?" |
| VIN / chassis | "Nambari ya VIN au chassis inaonekana kwenye dashibodi, mlango, au injini — ni nambari na herufi" |
| Vehicle make/model | "Gari ni ya chapa gani na modeli gani — mwaka wa uzalishaji?" |
| Purchase date | "Gari hili lilinunuliwa tarehe gani?" |
| Dealer name | "Muuzaji au dealer wanaitwa nini?" |
| Safety implication | "Je, tatizo hili linaathiri usalama wa udereva — breki, usukani, au mfumo mwingine?" |
| Service attempts | "Umejaribu kukarabati tatizo hili mara ngapi? Walisema nini kila wakati?" |
| Odometer reading | "Mita ya umbali ya gari inaonyesha kilomita ngapi sasa hivi?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| safety_implication | Yes AND defect affects brakes/steering | Advise stop driving immediately; manufacturer safety recall notification |
| issue_type | odometer_tampering | Police report + TRA import history check + FCC fraud complaint |
| issue_type | dealer_fraud AND misrepresentation | FCC consumer protection complaint; potential criminal fraud |
| dealer_service_attempts | >= 3 AND same defect | Entitlement to replacement; escalate to manufacturer; FCC complaint if refused |
| issue_type | counterfeit_spare_parts AND safety-critical | TBS enforcement; police report; SUMATRA safety concern |
| issue_type | hire_purchase_dispute AND illegal repossession | Legal aid referral; BOT consumer protection; Hire Purchase Act s.15 rights |
| issue_type | manufacturing_defect AND recall applicable | Manufacturer recall center referral; repair must be free of charge |
| purchase_type | Used AND hidden damage discovered | FCC misrepresentation complaint; independent inspection evidence |

---

*Sources: Tanzania Road Traffic Act Cap. 168, TRA Vehicle Registration Regulations, Fair Competition Act Cap. 285, Tanzania Hire Purchase Act Cap. 431, ISO 10002:2018, ISO 26262, UNECE WP.29, BOT Consumer Protection Guidelines*
