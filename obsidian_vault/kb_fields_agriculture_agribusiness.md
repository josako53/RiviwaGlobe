---
tags: [industry-kb, field-standards, feedback-fields]
---
# Agriculture / Agribusiness — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: farm, smallholder farmer, mkulima, seeds, mbegu, fertilizer, mbolea, pesticide, dawa ya wadudu, herbicide, dawa ya magugu, fungicide, crop buyer, aggregator, cooperative, AMCOS, ushirika, irrigation, umwagiliaji, agro-processing, livestock, mifugo, poultry, kuku, fisheries, samaki, extension officer, bwana shamba, afisa kilimo wa kata, crop subsidy, ruzuku ya pembejeo, SAGCOT, TOSCI, TPRI, cash crops, coffee, kahawa, tea, chai, tobacco, tumbaku, cashew, korosho, maize, mahindi, rice, mpunga, sugarcane, miwa, horticulture, mboga, TADB, agri-finance, mkopo wa kilimo, input voucher, hati ya pembejeo, warehouse receipt, hati ya ghala, contract farming, kilimo cha mkataba, crop insurance, bima ya mazao, cooperative fraud, ward agricultural office, dispensary ya kilimo

## Why Industry-Specific Fields Matter

Generic feedback fields cannot distinguish between a counterfeit pesticide complaint (requiring product batch number, TPRI registration check, and potential poisoning escalation), a crop buyer weighing fraud (requiring scale type, transaction reference, and cooperative authority referral), and an agri-loan disbursement failure (requiring TADB loan reference and harvest cycle timing) — all requiring different regulatory bodies (TPRI, TOSCI, TBS, TADB, cooperative registrar) and different evidence. Without agriculture-specific fields, the AI cannot route complaints, trigger mandatory regulatory notifications, or detect systemic input fraud across a community.

## Source Standards

- FAO AFR100 Grievance Redress Mechanism (field requirements for agriculture GRM)
- FAO Ethiopia Complaints and Feedback Response Mechanism (CFRM)
- ETI (Ethical Trading Initiative) Grievance Mechanisms in Agriculture — Synthesis Report
- USDA Farmer Fairness complaint process
- Minnesota Department of Agriculture Pesticide/Fertilizer Complaint Form (field model)
- Oregon ODA Pesticide Complaint form (batch/lot and area affected fields)
- TPRI (Tropical Pesticides Research Institute, Tanzania) — regulatory mandate for pesticide registration and enforcement
- AGRA Kenya Outcome Monitoring Report 2019 (agro-dealer and extension field context)
- Tanzania Official Seed Certification Institute (TOSCI) — seed quality framework
- Tanzania Bureau of Standards (TBS) — fertilizer quality
- TADB (Tanzania Agricultural Development Bank) — agri-finance

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| `complainant_name` | Jina la mkulima / mlalamikaji | Yes | Required for all formal agricultural complaint processes; FAO AFR100: complainant identification for follow-up |
| `complainant_contact` | Mawasiliano (simu / barua pepe) | Yes | Required for FAO, USDA, and MDA forms; needed for update and acknowledgement |
| `complainant_location` | Wilaya / Kata / Kijiji | Yes | FAO AFR100: "location of the incident"; required for geographic analysis and routing to correct ward agricultural office |
| `farm_gps_or_landmark` | GPS / alama ya shamba | Recommended | FAO AFR100 requires location of incident; GPS enables field inspection coordination and multi-complaint heatmap |
| `issue_type` | Aina ya tatizo | Yes | FAO, ETI, USDA all require categorization; determines regulatory body (TPRI for pesticides, TOSCI for seeds, TBS for fertilizers, cooperative registrar for AMCOS fraud) |
| `issue_description` | Maelezo ya tatizo | Yes | FAO AFR100: free narrative of the issue; required by all frameworks as the primary grievance record |
| `crop_or_livestock_type` | Aina ya zao / mifugo iliyoathirika | Yes | FAO and USDA require agricultural commodity identification to classify the complaint and estimate impact |
| `date_of_incident` | Tarehe ya tukio | Yes | FAO AFR100: required for SLA calculation and investigation timeline |
| `supplier_or_agency_name` | Jina la muuzaji / shirika linalohusika | Yes | FAO AFR100: "names of people or organizations involved"; required for regulatory action against supplier |
| `prior_action_taken` | Hatua ulizochukua tayari | Yes | FAO AFR100: "Any actions already taken to address the issue"; avoids re-routing to already-tried channels |
| `desired_outcome` | Matokeo unayotaka | Yes | FAO AFR100 and USDA frameworks require documentation of desired remedy (replacement, refund, investigation, compensation) |
| `evidence_available` | Ushahidi uliopo (picha, mfuko, risiti) | Recommended | FAO AFR100 and MDA complaint form require documentation; photos of crop damage, product packaging, and receipts are critical for TPRI/TOSCI action |

### Conditional Fields (collect based on issue type)

**If `issue_type = seed_failure` OR `counterfeit_seeds`:**
Also collect:
- `seed_variety_name` — Jina la aina ya mbegu: TOSCI registration check requires variety name
- `seed_brand` — Chapa ya mbegu: For supplier investigation
- `batch_or_lot_number` — Nambari ya kundi la mbegu: MDA form and TOSCI traceability require batch number for quality investigation
- `purchase_date` — Tarehe ya ununuzi: Required for supplier liability determination
- `purchase_location` — Mahali pa ununuzi (duka / soko): Identifies specific agro-dealer for inspection
- `germination_rate_observed` — Asilimia ya uota iliyoonekana (%): Compare against label claim; MDA field for germination rate discrepancy
- `expected_germination_rate_on_label` — Asilimia ya uota iliyoandikwa kwenye mfuko (%): Benchmark for TOSCI quality standard verification

**If `issue_type = fertilizer_quality_failure` OR `adulterated_fertilizer`:**
Also collect:
- `fertilizer_type` — Aina ya mbolea: NPK / Urea / CAN / DAP / Organic
- `fertilizer_brand` — Chapa ya mbolea: For TBS and supplier action
- `batch_lot_number` — Nambari ya kundi: MDA Minnesota form requires batch number for traceability
- `weight_received_kg` — Uzito uliopokelewa (kg): MDA: bags underweight is a specific complaint category; document actual vs. stated weight
- `stated_weight_on_bag_kg` — Uzito ulioandikwa kwenye mfuko (kg): For TBS Standards Act violation documentation
- `symptoms_observed_on_crop` — Dalili zilizoonekana kwenye mazao: Leaf burn, no response, root damage — for agronomic investigation
- `quantity_purchased` — Kiasi kilichonunuliwa: For loss estimation

**If `issue_type = pesticide_damage` OR `herbicide_crop_damage`:**
Also collect:
- `product_name` — Jina la dawa: Required by MDA Minnesota and Oregon ODA complaint forms
- `registration_number_on_label` — Nambari ya usajili kwenye lebo (kama ipo): TPRI requires all legal pesticides to carry TPRI registration number
- `application_date` — Tarehe ya kunyunyizia: MDA: date of application required
- `application_rate_used` — Kiwango kilichotumika: For compliance check against label instructions
- `area_affected_hectares` — Eneo lililoathirika (hekta): Oregon ODA form includes area affected; required for loss quantification
- `human_or_animal_exposure` — Je, binadamu au mifugo waliathirika? Yes/No: Triggers immediate TPRI and health authority notification if Yes

**If `issue_type = crop_buyer_fraud` OR `weighing_fraud` OR `price_manipulation`:**
Also collect:
- `scale_type_used` — Aina ya mzani uliotumika: Digital / mechanical / spring; determines calibration requirements
- `weight_recorded_by_buyer_kg` — Uzito uliorekodiwa na mnunuzi (kg): For comparison with farmer's independent measurement
- `weight_verified_independently_kg` — Uzito uliohakikiwa kwa kujitegemea (kg): Oregon ODA form model for independent measurement
- `transaction_reference` — Nambari ya muamala / stakabadhi: For financial tracing and cooperative authority referral
- `price_per_kg_agreed` — Bei iliyokubaliwa kwa kilo (TZS): Documented price at contract or meeting level
- `price_per_kg_paid` — Bei iliyolipwa kwa kilo (TZS): Documents price manipulation gap
- `number_of_farmers_affected` — Idadi ya wakulima walioathirika: ETI synthesis notes collective impact; large scale triggers cooperative registrar action

**If `issue_type = cooperative_fraud` OR `amcos_mismanagement`:**
Also collect:
- `cooperative_name` — Jina la ushirika / AMCOS
- `cooperative_registration_number` — Nambari ya usajili wa ushirika: Required for cooperative registrar (Ministry of Agriculture) investigation
- `amount_deducted_or_misappropriated_tzs` — Kiasi kilichokatwa / kuchukuliwa bila ruhusa (TZS): For financial investigation
- `dividend_period_affected` — Msimu / kipindi cha mgawanyo ulioathirika
- `general_meeting_held` — Je, mkutano mkuu uliofanyika? Yes/No: Key governance indicator

**If `issue_type = agri_loan_or_subsidy_dispute`:**
Also collect:
- `lender_or_program_name` — Jina la mkopeshaji / programu: TADB / NMB Rural / SACCOS / government subsidy
- `loan_reference_or_application_number` — Nambari ya mkopo / ombi
- `amount_applied_tzs` — Kiasi kilichoombiwa (TZS)
- `amount_disbursed_tzs` — Kiasi kilichotolewa (TZS)
- `disbursement_date` — Tarehe ya kutolewa: For harvest cycle timing analysis
- `crop_cycle_affected` — Mzunguko wa zao ulioathirika: Long rains / short rains / specific season

**If `issue_type = livestock_or_poultry_failure`:**
Also collect:
- `animal_species` — Aina ya mnyama / ndege: Cattle / goat / poultry / fish
- `number_of_animals_affected` — Idadi ya wanyama / ndege waliokufa au kuathirika
- `veterinary_medicine_or_feed_involved` — Dawa ya mifugo / chakula kinachohusika
- `batch_number_of_vet_medicine` — Nambari ya kundi la dawa ya mifugo: TFDA registration check for veterinary medicine
- `vet_officer_notified` — Je, afisa mifugo alitaarifu? Yes/No: Disease outbreak reporting obligation

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| AG-01 | `seed_failure` | Poor germination, wrong variety, expired seeds |
| AG-02 | `counterfeit_seeds` | Fake seeds sold under genuine brand |
| AG-03 | `fertilizer_quality_failure` | Adulterated, underweight, or incorrectly labeled fertilizer |
| AG-04 | `pesticide_crop_damage` | Pesticide/herbicide caused crop damage |
| AG-05 | `counterfeit_agrochemical` | Fake or unregistered pesticide/herbicide/fungicide |
| AG-06 | `extension_officer_misconduct` | Negligence, wrong advice, bribery by extension officer |
| AG-07 | `crop_buyer_fraud` | Weighing fraud, price manipulation, non-payment |
| AG-08 | `cooperative_fraud` | AMCOS mismanagement, embezzlement, unauthorized deductions |
| AG-09 | `irrigation_equipment_failure` | Pump, drip kit, or system failure; defective installation |
| AG-10 | `market_price_manipulation` | Below-floor prices, undisclosed deductions, intermediary fraud |
| AG-11 | `agri_loan_dispute` | Loan denied, wrong rate, disbursement delay, double deduction |
| AG-12 | `crop_insurance_dispute` | Claim denied, assessment disagreement, policy mismatch |
| AG-13 | `subsidy_exclusion` | Wrongful exclusion from government input subsidy program |
| AG-14 | `livestock_poultry_failure` | Disease, counterfeit vet medicine, feed contamination, hatchery failure |
| AG-15 | `land_rights_dispute` | Land access blocked, contract farming rights violated |
| AG-16 | `pesticide_human_exposure` | Farmer or family member exposed to pesticide — health emergency |
| AG-17 | `weather_disaster_response` | Flood/drought damage with inadequate program response |

### Resolution Standards for This Industry

- **Pesticide/fertilizer quality:** TPRI and TBS are the regulatory bodies; samples must be submitted to TPRI lab for pesticide analysis; TBS handles fertilizer standards. Complaints with product samples can trigger market withdrawal.
- **Seeds:** TOSCI certifies seeds; variety and germination complaints can be investigated by TOSCI inspectors; counterfeit seed complaints can result in criminal prosecution under the Seeds Act.
- **Cooperative fraud:** Cooperative Societies Registrar (under the Ministry of Agriculture) investigates AMCOS mismanagement; district cooperative officers are the first escalation point.
- **Weighing fraud:** Weights and Measures Agency (Tanzania) handles scale calibration and fraudulent weighing complaints.
- **Agri-loans (TADB):** Formal appeals process exists; ombudsman route through Bank of Tanzania for bank-related complaints.
- **Timeline (FAO standard):** Acknowledgement within 5 working days; investigation outcome within 30 days for standard complaints; 60 days for complex cases requiring laboratory analysis.

### Escalation Triggers (field values that require immediate escalation)

- `issue_type = pesticide_human_exposure` — Medical emergency; provide Poison Control Centre and nearest hospital; notify TPRI and district health officer within 24 hours
- `issue_type = counterfeit_agrochemical` OR `counterfeit_seeds` AND multiple farmers affected — Market contamination; escalate to TPRI/TOSCI enforcement unit immediately; flag for market withdrawal
- `issue_type = livestock_poultry_failure` AND `vet_officer_notified = No` AND disease outbreak suspected — Disease reporting obligation; notify district livestock officer within 24 hours
- `issue_type = cooperative_fraud` AND `amount_misappropriated_tzs > 1000000` — Escalate to cooperative registrar and PCCB; create financial fraud priority ticket
- `human_or_animal_exposure = Yes` for any pesticide complaint — Health and safety emergency; escalate to TPRI, district health officer, and (if child) social welfare
- `issue_type = crop_buyer_fraud` AND `number_of_farmers_affected > 20` — Community-scale fraud; escalate to cooperative registrar and district agricultural officer
- `issue_type = agri_loan_dispute` AND farmer reports double deduction from mobile money — Mobile money fraud component; dual-route to TADB/lender AND TCRA/mobile money operator fraud team

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `submitter_name` | Jina la mtoa maoni (hiari) | Optional | Suggestions may be anonymous; do not require identification |
| `contact_details` | Mawasiliano (hiari) | Optional | For follow-up by implementing agency |
| `service_or_program_area` | Huduma / Programu inayohusika | Yes | Routes suggestion to correct department (extension, inputs, market, finance) |
| `crop_or_livestock_focus` | Zao / mifugo inayohusika | Yes | Enables commodity-specific product and program improvement |
| `suggestion_category` | Kategoria ya mapendekezo | Yes | Systematic categorization for program management |
| `suggestion_detail` | Maelezo ya mapendekezo | Yes | Free text; core content |
| `season_or_growing_period` | Msimu / kipindi cha kilimo | Recommended | For time-sensitive suggestions about seasonal program design |
| `geographic_area` | Eneo / Wilaya / Ukanda wa kilimo | Recommended | FAO and AGRA require geographic context for extension program planning |

### Industry-Specific Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| AGS-01 | `input_quality_traceability` | Ufuatiliaji wa ubora wa pembejeo |
| AGS-02 | `extension_service_delivery` | Uwasilishaji wa huduma za ugani |
| AGS-03 | `market_access` | Upatikanaji wa masoko |
| AGS-04 | `price_transparency` | Uwazi wa bei za mazao |
| AGS-05 | `digital_tools_sms` | Zana za kidijitali / ujumbe mfupi (SMS) |
| AGS-06 | `agri_finance` | Fedha za kilimo / mkopo |
| AGS-07 | `crop_insurance` | Bima ya mazao |
| AGS-08 | `cooperative_governance` | Utawala bora wa ushirika |
| AGS-09 | `irrigation_infrastructure` | Miundombinu ya umwagiliaji |
| AGS-10 | `post_harvest_handling` | Usimamizi wa mazao baada ya kuvuna |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `inquirer_name` | Jina la mwulizaji (hiari) | Optional | Not required for general agricultural inquiries |
| `inquiry_type` | Aina ya swali | Yes | Routes to correct knowledge base |
| `crop_or_livestock_type` | Aina ya zao / mifugo | Recommended | For crop-specific advisory responses |
| `location_or_agroecological_zone` | Wilaya / Ukanda wa hali ya hewa | Recommended | Extension advice is zone-specific; wrong zone advice is a known harm (see ETI report) |
| `season_or_planting_stage` | Msimu / hatua ya ukuaji | Recommended | Pesticide, fertilizer, and irrigation advice is stage-specific |
| `preferred_response_channel` | Njia unayopendelea ya jibu | Yes | SMS / Simu / WhatsApp — critical for rural farmers with basic phones |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Swahili | Additional Fields Needed |
|-------------|---------|--------------------------|
| `input_registration_check` | Je, dawa / mbegu hii imesajiliwa? | `product_name`, `registration_number_on_label` |
| `pesticide_identification` | Dawa hii ni nini na inatumika kwa nini? | `product_name`, `crop_type`, `pest_description` |
| `fertilizer_recommendation` | Mbolea gani inafaa kwa zao langu? | `crop_or_livestock_type`, `soil_type`, `location_or_agroecological_zone` |
| `crop_disease_diagnosis` | Mbona mazao yangu yanaonyesha dalili hizi? | `crop_or_livestock_type`, `symptom_description`, `planting_stage` |
| `market_price_inquiry` | Bei ya sasa ya zao fulani ni ngapi? | `crop_or_livestock_type`, `market_or_location` |
| `cooperative_enrollment` | Jinsi ya kujiunga na ushirika | `location_district`, `crop_or_livestock_type` |
| `subsidy_registration` | Jinsi ya kuomba ruzuku ya pembejeo | `program_name`, `location_district` |
| `loan_requirements` | Mahitaji ya mkopo wa kilimo kutoka TADB | `lender_or_program_name`, `amount_needed`, `crop_or_livestock_type` |
| `tpri_registration_check` | Je, dawa hii iko kwenye orodha ya TPRI? | `product_name`, `registration_number_on_label` |
| `warehouse_receipt_process` | Mfumo wa hati za ghala unafanyaje kazi? | `crop_or_livestock_type`, `location_district` |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `submitter_name` | Jina la mtoa pongezi (hiari) | Optional | For acknowledgement; not required |
| `person_or_program_recognized` | Mtu / programu / bidhaa inayopongezwa | Yes | Routes compliment to staff, supplier, or program management |
| `role_of_person_recognized` | Wadhifa wa mtu anayepongezwa | Recommended | Extension officer / agro-dealer / crop buyer / cooperative official / vet officer |
| `what_went_well` | Kilichofanya vizuri | Yes | Specific behavior or product quality that made a difference |
| `outcome_impact_on_farm` | Matokeo kwa shamba lako | Recommended | Captures program impact data (yield improvement, income increase) — valuable for program M&E |
| `season_or_year` | Msimu / mwaka | Recommended | For correlation with program rollout timing |
| `program_name` | Jina la programu / kampuni | Yes | Links compliment to specific supplier or implementing program |

---

## AI Conversation Guidance for This Industry

- **Start by identifying the issue category (input / market / finance / extension) before asking for product details.** Ask "Tatizo lako linahusiana na pembejeo (mbegu/mbolea/dawa), ununuzi wa mazao, mkopo, au ushauri wa kilimo?" — this single question determines the entire subsequent field set and regulatory routing.
- **For pesticide or fertilizer complaints, always ask about human or animal exposure before anything else.** Say "Je, wewe, mwanakaya, au mifugo wako wameathirika kimwili na dawa au mbolea hii?" — if Yes, provide health emergency guidance immediately and flag for TPRI and health authority notification before completing other fields.
- **Get the batch/lot number before asking for a description of the problem.** Many farmers have the packaging and can read the number; this single field enables TPRI/TOSCI to trace the specific production batch and act on the whole lot. Ask "Una mfuko au chupa ya dawa / mbegu? Kuna nambari yoyote iliyoandikwa pembeni au chini?"
- **For crop buyer or cooperative complaints, quantify the loss in kilograms and shillings.** Ask "Mahali ambapo ulipaswa kupata kilo ngapi / shilingi ngapi, na ulipata kiasi gani?" — this structures the complaint for cooperative registrar and Weights and Measures Agency investigations.
- **Do not ask for TOSCI or TPRI registration numbers from the farmer** — they are unlikely to know them. Instead, ask for the product name and brand, and note whether a registration number appears on the label. The absence of a TPRI number on a pesticide label is itself a violation.
- **For extension officer misconduct (including bribery), assure the farmer of confidentiality.** Many farmers fear losing extension services if they report the officer by name. Say "Unaweza kushiriki jina la ofisa bila wasiwasi — taarifa yako itashughulikiwa kwa siri."

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Issue category | "Tatizo lako linahusiana na mbegu, mbolea, dawa, ununuzi wa mazao, mkopo, au ushauri wa kilimo?" |
| Human/animal exposure | "Je, wewe, familia yako, au mifugo wako wameathirika kimwili na dawa/mbolea hii?" |
| Product name and batch | "Jina la dawa au mbolea ni nini? Una nambari ya kundi (batch/lot) kutoka kwenye mfuko au chupa?" |
| Crop type | "Ni zao gani lililoathirika — mahindi, mpunga, korosho, mboga, au lingine?" |
| Area affected | "Eneo lililoathirika ni kubwa kiasi gani — hekta ngapi au ekari ngapi?" |
| Germination rate | "Kati ya mbegu zote ulizopanda, zingapi zilichipua? Asilimia takriban?" |
| Scale/weighing issue | "Mzani wa mnunuzi ulionyesha kilo ngapi? Ulihakikisha kwa mzani mwingine?" |
| Number of farmers affected | "Je, wakulima wengine katika kijiji chako wamekutana na tatizo hilo hilo?" |
| TPRI registration number | "Kwenye lebo ya dawa, kuna nambari ya usajili wa TPRI iliyoandikwa? Inasoma nini?" |
| Desired outcome | "Unataka nini kitokee — fidia ya hasara, uchunguzi wa bidhaa, au kuona hatua dhidi ya muuzaji?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| `issue_type` | `pesticide_human_exposure` OR `human_or_animal_exposure = Yes` | Medical emergency flag; provide hospital and poison control contacts; notify TPRI and district health officer within 24 hours |
| `issue_type` | `counterfeit_agrochemical` AND `registration_number_on_label = None` | TPRI enforcement referral; product is illegal; advise farmer not to use and to preserve packaging as evidence |
| `issue_type` | `counterfeit_seeds` AND `batch_lot_number` collected | TOSCI enforcement referral; batch can be traced and recalled; flag if multiple farmers report same batch |
| `issue_type` | `cooperative_fraud` AND `amount_misappropriated_tzs > 1000000` | Escalate to cooperative registrar and PCCB; financial fraud priority ticket |
| `issue_type` | `fertilizer_quality_failure` AND `weight_received_kg < stated_weight_on_bag_kg` | Weights and Measures Agency referral; TBS Standards Act violation |
| `issue_type` | `livestock_poultry_failure` AND disease outbreak suspected | District livestock officer notification; disease reporting obligation within 24 hours |
| `number_of_farmers_affected` | > 20 | Community-scale issue; escalate to district agricultural officer; flag for program-level investigation |
| `issue_type` | `crop_buyer_fraud` | Route to Weights and Measures Agency (weighing fraud) and cooperative registrar; document transaction reference |
| `issue_type` | `agri_loan_dispute` AND double deduction from mobile money | Dual-route: lender AND TCRA/mobile money operator fraud team |
| `evidence_available` | Yes AND includes product sample | Advise complainant to preserve sealed sample for laboratory testing; facilitate TPRI/TBS submission |

---

*Sources: FAO AFR100 GRM, FAO Ethiopia CFRM, ETI Grievance Mechanisms in Agriculture Synthesis Report, USDA Farmer Fairness, Minnesota Department of Agriculture Pesticide/Fertilizer Complaint Form, Oregon ODA Pesticide Complaint, TPRI Tanzania, AGRA Kenya Outcome Monitoring 2019, TOSCI, TBS Tanzania, TADB*
