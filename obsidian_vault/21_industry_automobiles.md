---
tags: [industry-kb, feedback-classification, field-standards]
---
# Automobiles / Motor Vehicles — Feedback Collection Fields & Standards

## Industry Identifiers

car dealership, vehicle importer, mitumba car, used vehicle, spare parts, garage, auto repair, fundi gari, bodaboda, boda boda, motorcycle, petrol station, fuel station, driving school, car rental, truck operator, TRA registration, SUMATRA, TANROADS, TLB, logbook, hati ya gari, road worthiness, fitness test, vehicle inspection, import duty, CIF value, Japan auction, Singapore export, engine swap, gearbox, chassis number, number plate, driving license, PSV license, TIRA, vehicle insurance, VIN, odometer, motor vehicle, pickup truck, SUV, minibus, heavy commercial vehicle, engine oil, brake fluid, coolant, alternator, transmission, suspension, tyres, airbag, seatbelt, recall, counterfeit spare parts, EV, electric vehicle, hybrid

## Why Industry-Specific Fields Matter

Automotive complaints span four distinct domains — vehicle defects, dealer/garage conduct, fuel station practices, and regulatory documentation — each with different liable parties and resolution paths. Without the VIN or chassis number, a complaint about a vehicle defect cannot be cross-referenced against NHTSA-style recall databases or TRA registration records. Without mileage, repair history, and the specific defect system, it is impossible to distinguish a latent factory defect (manufacturer liability) from wear-and-tear (owner responsibility) or a botched garage repair (service center liability).

## Source Standards

- NHTSA Vehicle Owner Questionnaire (VOQ) system — VIN, mileage, crash/injury fields, issue type classification, incident context fields
- NHTSA Office of Defects Investigation (ODI) — five major complaint categories (airbags, speed control, fuel system, steering, brakes)
- Consumer Reports automotive reliability survey methodology — 20 trouble area categories, mileage-band tracking, recurrence tracking
- Consumer Reports: How to Write a Car Safety Complaint to NHTSA — supporting documentation guidance
- Tanzania TRA (Tanzania Revenue Authority) — import duty, CIF value, chassis number registration
- Tanzania SUMATRA — vehicle fitness inspection, roadworthiness certificate, PSV licensing
- Tanzania TLB (Tanzania Licensing Board) — driving license exam and registration
- Tanzania TIRA (Tanzania Insurance Regulatory Authority) — vehicle insurance oversight
- ISO 28000:2022 — supply chain security applied to spare parts authenticity and counterfeit parts

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complaint_domain | Eneo la malalamiko | Yes | Determines which liable party and regulatory body apply: [Vehicle Defect / Dealer-Garage Service / Fuel Station / Registration-Documentation / Insurance / Driving School / Car Rental / Bodaboda Platform] |
| vehicle_make | Chapa ya gari | Yes | NHTSA VOQ mandatory; Consumer Reports; identifies manufacturer for recall cross-reference |
| vehicle_model | Mfano wa gari | Yes | NHTSA VOQ mandatory; narrows to the specific model for defect pattern analysis |
| model_year | Mwaka wa gari | Yes | NHTSA VOQ mandatory; Consumer Reports tracks problems by model year |
| vin_or_chassis_number | Nambari ya VIN au chasisi | Yes | NHTSA VOQ: "a unique 17-digit number and letter combination"; without this, no recall cross-reference or TRA registration check is possible; use chassis number for older vehicles common in East Africa |
| current_mileage | Mileage ya sasa (km) | Yes | NHTSA VOQ mandatory; Consumer Reports tracks defect rates by mileage band; determines warranty coverage |
| purchase_type | Aina ya ununuzi | Recommended | [New / Used / Leased / Hire Purchase] — affects warranty rights and dealer liability |
| purchase_date | Tarehe ya ununuzi | Recommended | Establishes warranty period and time elapsed since purchase |
| issue_type | Aina ya tatizo | Yes | Drives conditional field logic; see Issue Type Classification below |
| dealer_or_garage_name | Jina la muuzaji/karakana | Conditional | Required when complaint_domain = Dealer-Garage Service; needed for operator identification and regulatory referral |
| dealer_location | Anwani ya muuzaji/karakana | Conditional | NHTSA VOQ supporting documentation; needed for regulatory referral |
| service_date | Tarehe ya huduma | Conditional | Required when complaint is about garage service; establishes timeline |
| service_order_number | Nambari ya amri ya huduma | Recommended | NHTSA VOQ documentation; key record for dispute and court proceedings |
| incident_description | Maelezo ya tukio | Yes | NHTSA VOQ; Consumer Reports; the substantive narrative record |
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Required for formal complaint processing |
| complainant_phone | Nambari ya simu | Yes | Required for follow-up |
| complainant_email | Barua pepe | Recommended | For formal written responses |

### Conditional Fields (collect based on issue type)

**If issue_type falls under Safety-Critical (Airbag / Brakes / Speed Control / Steering / Tire):**
- `crash_occurred` — Has this caused a crash? [Yes / No] — NHTSA VOQ mandatory field
- `injury_occurred` — Has this caused an injury? [Yes / No] — NHTSA VOQ mandatory field
- `injury_description` — Description of injuries — NHTSA VOQ
- `airbags_deployed` — Did airbags deploy? [Yes / No / Not applicable] — NHTSA VOQ
- `speed_at_incident` — Speed at time of incident (km/h) — NHTSA VOQ incident context
- `road_conditions` — Road conditions [Highway / Urban road / Murram / Parking lot] — NHTSA VOQ
- `weather_conditions` — Weather conditions [Dry / Wet / Fog / Night] — NHTSA VOQ
- `gear_at_incident` — Gear selection at time of incident (if relevant) — NHTSA VOQ
- `brake_application` — Description of brake application before incident — NHTSA VOQ
- `aftermarket_modifications` — Any aftermarket modifications? [Yes / No / Description] — NHTSA VOQ
- `police_report_filed` — Was a police report filed? [Yes / No]
- `police_report_number` — Police report reference number
- `police_report_upload` — Police report [file upload] — NHTSA VOQ

**If issue_type = Engine / Transmission / Powertrain Defect:**
- `defect_system` — Specific system affected (see Issue Type Classification — Powertrain section)
- `defect_onset_mileage` — Mileage when defect first appeared — Consumer Reports methodology
- `defect_recurrence_count` — Number of previous repair attempts for this same issue — NHTSA VOQ
- `previous_repair_dates` — Dates of previous repair attempts — NHTSA VOQ
- `previous_repairs_under_warranty` — Were previous repairs under warranty? [Yes / No / Partial] — NHTSA VOQ
- `recall_issued` — Was a recall issued for this vehicle for this issue? [Yes / No / Unknown] — NHTSA recall database cross-reference
- `repair_invoices` — Previous repair invoices [file upload] — NHTSA VOQ; Consumer Reports
- `mechanic_assessment` — Independent mechanic's assessment [file upload] — NHTSA VOQ

**If issue_type = Dealer / Garage Service Complaint:**
- `technician_name` — Technician name (if known) — NHTSA VOQ documentation
- `quoted_price` — Price quoted before repair — Consumer Reports: written estimate before work begins
- `final_price_charged` — Final price charged — for billing dispute calculation
- `problem_recurs` — Did the same problem recur after repair? [Yes / No] — Consumer Reports reliability methodology; NHTSA VOQ
- `car_condition_changed` — New problems appeared after service? [Yes / No / Description]
- `service_records_upload` — Service records [file upload] — NHTSA VOQ
- `repair_invoices_upload` — Repair invoices [file upload] — NHTSA VOQ

**If issue_type = Undisclosed Defect / Odometer Fraud:**
- `odometer_reading_at_sale` — Odometer reading as stated by seller at sale
- `independent_inspection_mileage` — Mileage confirmed by independent mechanic inspection
- `defect_disclosure_made` — Was any defect disclosed before purchase? [Yes / No / Partial]
- `auction_grade_sheet` — Japan/Singapore auction grade sheet [file upload] (for imported vehicles)
- `independent_inspection_report` — Pre-purchase inspection report [file upload]

**If issue_type = Fuel Station Complaint:**
- `fuel_station_name` — Fuel station name and location
- `fuel_type_dispensed` — Fuel type dispensed [Petrol / Diesel / Kerosene / Mixed / Unknown]
- `fuel_quantity_paid_for` — Quantity paid for (litres)
- `quantity_dispute` — Was the full quantity actually dispensed? [Yes / No / Suspected short]
- `pump_reading_photo` — Photo of pump reading [file upload]
- `receipt_issued` — Was a receipt issued? [Yes / No]
- `vehicle_damage_from_fuel` — Did contaminated fuel cause vehicle damage? [Yes / No / Description]
- `price_above_regulated` — Was the price above the government-regulated pump price? [Yes / No]

**If issue_type = Vehicle Insurance Complaint:**
- `insurance_company_name` — Insurance company name — TIRA
- `policy_number` — Insurance policy number — TIRA
- `claim_reference_number` — Insurance claim reference number
- `accident_date` — Date of the accident or incident
- `claim_submission_date` — Date claim was submitted
- `settlement_amount_offered` — Settlement amount offered (if any)
- `settlement_amount_expected` — Settlement amount expected per policy
- `settlement_dispute_reason` — Reason for dispute [Undervaluation / Liability denial / Policy change without notice / Documents disputed / Excessive delay / Other]
- `months_since_claim_filed` — How many months since claim was filed — TIRA: unreasonable delay trigger

**If issue_type = TRA / SUMATRA Registration or Documentation:**
- `registration_reference` — TRA registration reference or TIN
- `chassis_number_mismatch` — Chassis number discrepancy between documents and vehicle? [Yes / No]
- `logbook_status` — Logbook (hati ya gari) transfer status [Pending / Rejected / Delayed / Incorrect data]
- `days_elapsed_since_application` — Number of days since application was submitted
- `official_fee_paid` — Official fee paid (TZS)
- `unofficial_payment_demanded` — Was an unofficial payment demanded? [Yes / No / Amount] — PCCB escalation trigger
- `fitness_certificate_issue` — Roadworthiness certificate issue [Refused unfairly / Overcharged / Officer demanded bribe / Other]

**All vehicle-related complaints (documentation):**
- `defect_photos` — Photos of defect [file upload] — NHTSA VOQ
- `maintenance_records` — Maintenance records [file upload] — NHTSA VOQ

### Issue Type Classification

**Powertrain & Mechanical (aligned with NHTSA ODI + Consumer Reports):**
- `ENGINE_MAJOR` — Engine rebuild, head gasket failure, turbocharger failure, cylinder failure — Consumer Reports "Engine, Major"
- `ENGINE_MINOR` — Belt failure, oil leaks, engine mounts, engine computer — Consumer Reports "Engine, Minor"
- `ENGINE_COOLING` — Radiator, water pump, overheating — Consumer Reports "Engine Cooling"
- `TRANSMISSION_MAJOR` — Rebuild, torque converter failure — Consumer Reports "Transmission, Major"
- `TRANSMISSION_MINOR` — Gear selector, shifting problems, transmission sensors — Consumer Reports "Transmission, Minor"
- `DRIVE_SYSTEM` — Driveshaft, CV joint, differential, 4WD/AWD system — Consumer Reports "Drive System"
- `FUEL_SYSTEM` — Fuel pump, injectors, fuel sensors — Consumer Reports "Fuel System"; NHTSA ODI major category
- `EXHAUST` — Catalytic converter, manifold, exhaust leaks — Consumer Reports "Exhaust"
- `SUSPENSION` — Shocks, struts, ball joints, wheel bearings, steering — Consumer Reports "Suspension"
- `BRAKES` — ABS, calipers, rotors, master cylinder, brake failure — Consumer Reports "Brakes"; NHTSA ODI major category

**Electrical & Electronics:**
- `ELECTRICAL_SYSTEM` — Alternator, starter, ignition, battery cables — Consumer Reports "Electrical System"
- `ELECTRICAL_ACCESSORIES` — Warning lights, wipers, sensors, lights, horn — Consumer Reports "Electrical Accessories"
- `IN_CAR_ELECTRONICS` — Infotainment, GPS, display screen, phone pairing, backup camera — Consumer Reports "In-Car Electronics"
- `CLIMATE_SYSTEM` — AC, heater, blower motor, refrigerant leak — Consumer Reports "Climate System"

**Safety-Critical (NHTSA ODI top categories):**
- `AIRBAG_DEFECT` — Non-deployment, inadvertent deployment, airbag recall — NHTSA ODI (highest complaint volume category)
- `SEAT_BELT_DEFECT` — Belt failure, retractor defect, buckle failure
- `SPEED_CONTROL` — Unintended acceleration, stuck throttle — NHTSA ODI major category
- `TIRES_WHEELS` — Blowout, tread separation, sidewall failure — NHTSA ODI

**Body & Build:**
- `PAINT_TRIM` — Peeling, premature rust, loose moldings — Consumer Reports "Paint/Trim"
- `NOISE_LEAK` — Squeaks, rattles, wind noise, water ingress — Consumer Reports "Noises/Leaks"
- `BODY_HARDWARE` — Windows, locks, doors, mirrors, sunroof — Consumer Reports "Body Hardware"

**EV-Specific:**
- `ELECTRIC_MOTOR` — Electric motor defect — Consumer Reports "Electric Motor"
- `EV_BATTERY` — Battery defect, range loss, battery degradation — Consumer Reports "EV Battery"
- `EV_CHARGING` — Charging connector, onboard inverter, charging cable — Consumer Reports "EV Charging"

**Commercial & Service:**
- `POOR_REPAIR_RECURRENCE` — Problem recurs after service; same defect persists — Consumer Reports; NHTSA VOQ
- `BILLING_DISPUTE_GARAGE` — Overcharging, undisclosed charges, price change after work
- `WARRANTY_CLAIM_DENIED` — Warranty rejected by dealer or manufacturer
- `COUNTERFEIT_SPARE_PARTS` — Fake or substandard parts installed — ISO 28000 supply chain integrity
- `VEHICLE_DAMAGED_IN_SERVICE` — Vehicle damaged while at garage
- `MISLEADING_SALE` — Undisclosed defect, odometer fraud, accident history concealed
- `FUEL_STATION_SHORT_PUMP` — Fuel quantity short of amount paid
- `FUEL_CONTAMINATION` — Water, wrong fuel type, adulterated fuel dispensed
- `INSURANCE_CLAIM_DISPUTE` — Undervaluation, denial, excessive delay
- `REGISTRATION_DELAY` — TRA/SUMATRA documentation delayed beyond reasonable period
- `OFFICIAL_BRIBERY` — Government officer (TRA/SUMATRA/TLB/Traffic Police) demanded unofficial payment
- `DRIVING_SCHOOL_MISCONDUCT` — Instructor misconduct, payment fraud, training vehicle defect

### Resolution Standards for This Industry

- **NHTSA VOQ (guiding principle)**: Vehicle safety complaints should be filed in writing, including VIN, mileage, description of the defect, crash/injury status, and dealer contact attempts.
- **Consumer Reports methodology**: A defect that requires the same repair more than twice within 12 months is classified as a recurring problem — this is a strong indicator of a latent defect rather than normal wear.
- **Tanzania SUMATRA**: Vehicle fitness complaints (inspector demanding bribe, unjust failure of roadworthiness test) should be escalated to SUMATRA formally with the inspector's name, station, and date.
- **TIRA (Insurance)**: Insurance companies in Tanzania are regulated by TIRA. Unresolved claims or policy disputes can be formally escalated to TIRA if the insurer fails to respond within a reasonable period.
- **TRA**: Vehicle registration disputes, including chassis number mismatches and import duty errors, are handled by TRA's taxpayer services. Duty overpayments require a formal objection filed with TRA within 30 days.
- **Driving school fraud**: TLB (Tanzania Licensing Board) handles complaints about driving schools that collect exam fees but fail to register students.

### Escalation Triggers (field values that require immediate escalation)

- `crash_occurred` = Yes + `injury_occurred` = Yes → immediate safety escalation; advise police report; NHTSA VOQ principle (life-threatening defect)
- `issue_type` = AIRBAG_DEFECT + `crash_occurred` = Yes → urgent safety defect report; cross-check recall database; escalate to manufacturer and relevant regulator
- `issue_type` = FUEL_CONTAMINATION + `vehicle_damage_from_fuel` = Yes → escalate to fuel station operator and Energy and Water Utilities Regulatory Authority (EWURA) for pump quality investigation
- `issue_type` = MISLEADING_SALE + `chassis_number_mismatch` = Yes → potential stolen vehicle; escalate to Tanzania Police (CID Motor Vehicle Section); cross-check Interpol stolen vehicle register
- `official_bribery` trigger (any domain): TRA/SUMATRA/TLB/Traffic Police demanded unofficial payment → PCCB referral; do not resolve internally
- `issue_type` = DRIVING_SCHOOL_MISCONDUCT + sub-type = Sexual Harassment → immediate escalation; advise police OB filing; preserve complainant privacy
- `issue_type` = VEHICLE_DAMAGED_IN_SERVICE + garage now uncontactable + days > 90 → consumer protection escalation
- `insurance_claim_dispute` + `months_since_claim_filed` > 6 + `injury_in_accident` = Yes → TIRA formal complaint; life/health impact
- `issue_type` = COUNTERFEIT_SPARE_PARTS + evidence of supply chain fraud → ISO 28000 security referral; TFDA if pharmaceutical-grade lubricants involved; Tanzania Bureau of Standards (TBS) referral

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| suggestion_category | Aina ya pendekezo | Yes | Routes suggestion to the correct domain (dealer / garage / regulator / fuel station) |
| vehicle_make_model | Chapa na mfano wa gari (kama husika) | Conditional | Required if suggestion is product-specific |
| specific_suggestion | Maelezo ya pendekezo | Yes | Substantive content |
| submitter_contact | Mawasiliano ya mtoa pendekezo | Optional | For follow-up |

### Industry-Specific Improvement Categories

- `DEALER_SERVICE_IMPROVEMENT` — Pre-purchase inspection transparency, auction reports, logbook speed, buy-back guarantees
- `GARAGE_REPAIR_QUALITY` — Written estimates, diagnostic tools, genuine parts guarantee, service history logging
- `SPARE_PARTS_AVAILABILITY` — Online catalog, stock availability, counterfeit prevention, parts certification
- `FUEL_STATION_STANDARDS` — Pump labeling (petrol vs. diesel), auto receipts, calibration certificates, digital displays
- `REGISTRATION_EFFICIENCY` — TRA/SUMATRA digital processing, chassis number online verification, reduced wait times
- `VEHICLE_SAFETY_RECALL` — Better recall communication, TRA-linked VIN alerts, multi-channel recall notices
- `WARRANTY_POLICY` — Extended warranty options, warranty honoring enforcement, spare parts warranty
- `EV_INFRASTRUCTURE` — Charging stations, battery service centers, EV registration guidance
- `INSURANCE_POLICY` — Faster claims, TIRA-standard settlement timelines, fairer assessment
- `DRIVING_SCHOOL_STANDARDS` — Mandatory instructor certification, training vehicle roadworthiness, TLB exam transparency
- `BODABODA_PLATFORM` — Helmet enforcement, rider licensing checks, pricing transparency, safety ratings

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| inquiry_type | Aina ya swali | Yes | Routes the inquiry to the right domain |
| vehicle_make_model | Chapa na mfano wa gari | Conditional | Required for vehicle-specific questions |
| vin_or_chassis_number | Nambari ya VIN au chasisi | Conditional | Required for recall checks, registration status, insurance status |
| contact_for_response | Mawasiliano ya kujibu | Recommended | For callback or SMS response |

### Common Inquiry Types & Required Data Per Type

- `RECALL_CHECK` → vin_or_chassis_number; vehicle_make, vehicle_model, model_year; NHTSA recall database cross-reference
- `SERVICE_BOOKING` → dealer_or_garage_name; vehicle_make_model; service_type; preferred_date
- `SPARE_PARTS_AVAILABILITY` → vehicle_make_model; model_year; part_description
- `WARRANTY_QUERY` → vehicle_make_model; model_year; purchase_date; vin_or_chassis_number; issue_description
- `IMPORT_DUTY_QUERY` → vehicle_make_model; model_year; origin_country; estimated_cif_value — TRA CIF value basis
- `LOGBOOK_TRANSFER_QUERY` → application_reference; days_elapsed; purchase_date
- `PSV_LICENSE_QUERY` → vehicle_type; current_registration_status; application_date
- `INSURANCE_QUERY` → vehicle_make_model; vehicle_year; coverage_type_requested; estimated_vehicle_value
- `CHASSIS_VERIFICATION` → chassis_number; vehicle_make_model — TRA and Tanzania Police Motor Vehicle Section
- `DRIVING_LICENSE_QUERY` → license_class_required; current_license_status; TLB_exam_status
- `ROADWORTHINESS_QUERY` → vehicle_registration; last_certificate_date; inspection_center

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| complaint_domain | Eneo la sifa | Yes | Routes compliment to the correct operator for staff recognition |
| dealer_or_garage_name | Jina la muuzaji/karakana | Yes | Enables specific business recognition |
| technician_name | Jina la fundi (kama anajulikana) | Recommended | Enables specific staff recognition |
| service_date | Tarehe ya huduma | Yes | Anchors the compliment to a specific service event |
| vehicle_make_model | Chapa na mfano wa gari | Recommended | Corroborates the service context |
| positive_experience_category | Aina ya uzoefu mzuri | Recommended | Enables positive performance pattern tracking |
| positive_experience_description | Maelezo ya uzoefu mzuri | Yes | The substantive record for staff recognition |
| submitter_contact | Mawasiliano ya mtoa sifa | Optional | For acknowledgement |

---

## AI Conversation Guidance for This Industry

- **Establish the domain first, not the defect:** Open with "Is this about a vehicle defect or mechanical issue, a garage or repair experience, a fuel station, vehicle registration or insurance, or something else?" The domain (vehicle defect vs. dealer conduct vs. fuel station vs. documentation) determines the entire field set. Jumping to defect details before knowing the domain wastes collection effort.
- **For mechanical complaints, collect the VIN/chassis number conversationally:** Say "To help track this properly — do you have the vehicle's VIN or chassis number? It's usually on a metal plate inside the driver's door frame or on the dashboard near the windshield. In Tanzania, it's also on the TRA logbook." Many users in East Africa know the chassis number because it's on the logbook (hati ya gari).
- **Safety-critical signals require an immediate clarifying question:** If the user mentions a crash, brake failure, airbag problem, or unintended acceleration, ask "Was anyone injured in connection with this problem?" before continuing. Injury changes the urgency, the regulatory path, and the documentation required.
- **Bribery at TRA/SUMATRA/TLB is common and should be handled carefully:** If the user mentions paying unofficial fees at a government office, do not normalize it. Acknowledge: "What you are describing sounds like an unofficial payment that you were not legally required to make. Would you like us to help you report this formally?" Route to PCCB.
- **Insurance complaints need the policy number and claim reference early:** Without these, no follow-up with the insurance company or TIRA is possible. Ask "Do you have your insurance policy number and the reference number for the claim you filed?" These are usually in the claim acknowledgement letter or SMS the insurer sent.
- **For fuel station short-pump complaints, guide evidence collection:** Say "Did you take a photo of the pump screen showing the amount dispensed? And do you have a receipt? Both are very useful for this type of complaint." Short-pump fraud is a regulatory matter for EWURA; evidence is essential.
- **For driving school sexual harassment:** Follow the same sensitivity protocol as transport harassment — empathy first, safety check, minimal field collection, immediate senior escalation, police OB referral.

## Swahili Key Phrases for Field Collection

- "Tatizo hili linahusu nini hasa — kasoro ya gari, huduma ya karakana, kituo cha mafuta, usajili wa TRA, bima, au kitu kingine?" — Is this about a vehicle defect, garage service, fuel station, TRA registration, insurance, or something else?
- "Gari ni chapa gani, mfano gani, na mwaka gani?" — What is the vehicle make, model, and year?
- "Una nambari ya VIN au chasisi? Kawaida iko kwenye lango la dereva au kwenye hati ya gari (logbook)." — Do you have the VIN or chassis number? It's usually on the driver's door or in the logbook.
- "Tatizo lilianza lini, na gari ilikuwa na mileage ngapi wakati huo?" — When did the problem start, and what was the mileage at that time?
- "Je, gari imewahi kupelekwa karakanani kwa tatizo hili kabla? Mara ngapi?" — Has the vehicle been taken to a garage for this problem before? How many times?
- "Je, kumekuwa na ajali au mtu amejeruhiwa kwa sababu ya tatizo hili?" — Has there been an accident or has anyone been injured because of this problem?
- "Je, una ankara ya huduma au hati nyingine za matengenezo?" — Do you have the service invoice or other repair documents?
- "Kampuni ya bima inaitwa nini, na una nambari ya polisi ya madai yako?" — What is the insurance company's name, and do you have your claims reference number?
- "Je, umewahi kulipa ada yoyote isiyo rasmi katika ofisi ya TRA au SUMATRA?" — Did you pay any unofficial fee at the TRA or SUMATRA office?
- "Tatizo hili linaathiri usalama wa gari — kama breki, mfumo wa kasi, au mifuko ya hewa?" — Does this problem affect vehicle safety — such as brakes, speed control, or airbags?

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| crash_occurred | Yes + injury_occurred = Yes | Immediate safety escalation; advise police OB filing; preserve all evidence; NHTSA VOQ principle — life-threatening defect |
| issue_type | AIRBAG_DEFECT or SPEED_CONTROL | Cross-check manufacturer recall database; escalate to manufacturer's Tanzania representative; advise SUMATRA notification |
| issue_type | FUEL_CONTAMINATION + vehicle_damage = Yes | Report to EWURA (Energy and Water Utilities Regulatory Authority) for pump quality investigation; document fuel station details |
| issue_type | MISLEADING_SALE + chassis_number_mismatch = Yes | Escalate to Tanzania Police (CID Motor Vehicle Section); do not advise consumer to continue using vehicle |
| official_bribery | Any value indicating unofficial payment | PCCB referral; capture officer name, station, date, amount, and any witnesses |
| issue_type | DRIVING_SCHOOL_MISCONDUCT + sub_type = Sexual Harassment | Immediate senior escalation; police OB referral; preserve complainant privacy; do not share details without consent |
| issue_type | INSURANCE_CLAIM_DISPUTE + months_since_claim_filed > 6 | TIRA formal complaint; attach policy number and claim reference; escalate with documented settlement delay |
| issue_type | COUNTERFEIT_SPARE_PARTS + evidence of batch supply | ISO 28000 security referral; TBS (Tanzania Bureau of Standards) notification; TFDA if lubricants/fluids involved |
| issue_type | WARRANTY_CLAIM_DENIED + defect within warranty period | Formal written demand to dealer; Consumer Reports escalation principle: two failed repairs of same issue within 12 months = latent defect |
| recall_issued | Yes + defect_matches_recall = Yes | Advise consumer this is a known defect covered by recall; dealer must repair free of charge; escalate if dealer refuses |
| registration_delay + days_elapsed > 60 | TRA | Formal TRA taxpayer services complaint; track application reference; escalate to SUMATRA if fitness certificate involved |
| fuel_station_price_above_regulated | Yes | Report to EWURA (energy regulator for fuel pricing); capture station name, location, price displayed, date |
| issue_type | POOR_REPAIR_RECURRENCE + defect_recurrence_count > 2 | Classify as latent defect (Consumer Reports methodology); escalate to manufacturer or importer; advise independent mechanic assessment |

---

## Key Entities & Roles

**Regulatory Bodies:**
TRA (Tanzania Revenue Authority) — import duty, CIF value, chassis registration; SUMATRA (Surface and Marine Transport Regulatory Authority) — vehicle fitness, PSV licensing; TANROADS (Tanzania National Roads Agency) — road standards and heavy vehicles; TLB (Tanzania Licensing Board) — driving license examination; TIRA (Tanzania Insurance Regulatory Authority) — vehicle insurance oversight; EWURA (Energy and Water Utilities Regulatory Authority) — fuel quality and pricing; TBS (Tanzania Bureau of Standards) — spare parts and consumer goods standards; PCCB (Prevention and Combating of Corruption Bureau) — bribery by government officers; Tanzania Police (CID Motor Vehicle Section) — stolen vehicles, chassis fraud

**Common Vehicle Brands in Tanzania:**
Toyota (Hilux, Land Cruiser, Corolla, Vitz, RAV4, Prado), Nissan (NP300, X-Trail, Navara, Patrol), Mitsubishi (Pajero, L200, Outlander), Isuzu (trucks, D-Max), Subaru (Forester, Outback), Mercedes-Benz, BMW, Honda, Mazda, Suzuki

**Key Processes & Documents:**
Logbook (hati ya gari / V5) transfer; TRA import duty calculation (CIF value); SUMATRA fitness inspection certificate; chassis number verification; Japan/Singapore auction grade sheet (Grade 3, 3.5, 4, 4.5, 5); PSV licence; driving licence (Class B, C, D, E); TLB exam registration; insurance certificate of cover; pre-purchase inspection (PPI) report; service order / repair invoice; police OB (Occurrence Book) number

---

## Disambiguation Notes

- **Automobiles vs. Transport/Logistics:** If the complaint is about cargo not being delivered or freight charges, use Logistics KB (33). If it is about a truck breakdown, bodaboda passenger ride safety, or fuel quality for a vehicle, stay in this KB.
- **Automobiles vs. Insurance (General):** Vehicle insurance complaints sit firmly in this KB. Non-vehicle insurance (health, life, property) belongs in Finance/Banking KB (23).
- **Automobiles vs. Government Services:** TRA and SUMATRA processes are touchpoints in the vehicle ownership journey — complaints about corruption or systemic failure at these bodies should dual-route: document in this KB, but escalate to Government Services KB (36) or PCCB for the regulatory dimension.
- **Bodaboda personal transport vs. bodaboda platform:** Bodaboda rider conduct (safety, harassment, fare) during a personal ride belongs in Transport KB (42). Complaints about the bodaboda platform (app, payment, rider management) belong here or in a Technology KB if platform-focused.
- **Fuel Stations vs. Utilities:** Fuel quality and short-pump disputes belong here. Complaints about electricity supply to a fuel station belong in Energy/Utilities KB (40). Fuel price cap violations may dual-route: here for the consumer experience, Government KB (36) for the regulatory breach.
- **Automobiles vs. Products/Retail:** Spare parts purchased from a retail shop and found to be counterfeit — if the retail experience is the complaint (wrong item sold, return refused), use Products/Retail KB (32). If the counterfeit part caused vehicle damage, use this KB.
