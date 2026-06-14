---
tags: [industry-kb, field-standards, feedback-fields, pharmacy, pharmaceutical]
---
# Pharmacy / Pharmaceutical — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: famasi, pharmacy, duka la dawa, pharmacist, mfamasia, dawa, medicine, tablet, capsule, syrup, injection, sindano, ointment, cream, marhamu, prescription, cheti cha dawa, generic drug, brand name, drug brand, TFDA, Tanzania Food and Drug Authority, MSD, Medical Stores Department, drug expiry, dawa iliyokwisha muda, counterfeit medicine, dawa bandia, side effect, madhara ya dawa, dosage, kipimo cha dawa, refill, manufacturer, mtengenezaji wa dawa, drug recall, urejeshaji wa dawa, OTC, over-the-counter, dispensing error, kosa la kutoa dawa, controlled drug, dawa ya kulevya, antibiotic, pain killer, dawa ya maumivu, vitamins, virutubisho, supplement, herbal medicine, dawa ya asili, pharmacovigilance, uangalizi wa usalama wa dawa

## Why Industry-Specific Fields Matter

Pharmacy complaints span regulatory violations (expired/counterfeit drugs), clinical safety incidents (dispensing errors, wrong dosage), and consumer protection issues (overcharging, unlicensed outlets). Each category has a different investigation path: TFDA handles product safety and pharmacovigilance, MOHCDGEC handles dispensing practice, and police handle counterfeit distribution. Without pharmacy-specific fields — drug name, batch number, outlet license number — the AI cannot route the complaint to the correct authority or generate a TFDA-compliant adverse event report.

## Source Standards

- Tanzania Food and Drugs Act, Cap. 219 (TFDA) — licensing, pharmacovigilance, drug quality
- TFDA Good Dispensing Practice Guidelines 2013
- WHO Good Pharmacy Practice (GPP) Standards 2011
- WHO Model List of Essential Medicines, 23rd Edition (2023)
- Tanzania Pharmacy Act, Cap. 32 — pharmacist conduct and licensing
- Tanzania Pharmacy Council regulations on dispensing errors
- MOHCDGEC Standard Treatment Guidelines (STG) 4th Edition 2017
- ISO 10002:2018 — complaints handling
- WHO Guidelines for Medicine Donations (2011) — for NGO/MSD complaints
- ICH E2A/E2B — international pharmacovigilance reporting standards (reference)

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Required for TFDA complaint form; enables follow-up |
| complainant_phone | Nambari ya simu | Yes | For status updates and TFDA investigation coordination |
| pharmacy_outlet_name | Jina la duka la dawa | Yes | Identifies the regulated entity; required for TFDA license verification |
| pharmacy_outlet_location | Mahali pa duka la dawa | Yes | TFDA enforcement is geographic; enables inspection routing |
| pharmacy_license_number | Nambari ya leseni ya duka (kama inajulikana) | Recommended | TFDA can verify license status immediately |
| drug_name_generic | Jina la dawa (jina la kawaida) | Yes | TFDA pharmacovigilance reporting requires generic name; most critical identifier |
| drug_brand_name | Jina la chapa ya dawa | Recommended | Helps identify specific manufacturer; required for TFDA recall investigations |
| drug_batch_number | Nambari ya kundi la uzalishaji | Yes (for product safety) | Critical for batch recall; TFDA requires this for adverse drug reaction (ADR) reports |
| drug_expiry_date | Tarehe ya kuisha muda wa dawa | Conditional | Required for expired drug complaints; TFDA enforcement action basis |
| date_of_purchase_dispensing | Tarehe ya ununuzi / kutoa dawa | Yes | For traceability and limitation period |
| issue_type | Aina ya tatizo | Yes | Drives complaint routing to TFDA, Pharmacy Council, or consumer protection |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018 clause 8.2; TFDA requires incident narrative |
| adverse_effect_experienced | Madhara yaliyosababishwa na dawa | Conditional | TFDA pharmacovigilance; WHO ICH E2A requires this for ADR reports |
| prescription_involved | Je, dawa ilitolewa kwa cheti cha daktari? | Yes | Determines if dispensing without prescription occurred (regulatory violation) |
| desired_outcome | Matokeo unayotaka | Yes | Shapes resolution approach |
| consent_to_report_to_tfda | Ridhaa ya kuripoti kwa TFDA | Yes | Required before submitting pharmacovigilance report on behalf of complainant |

### Conditional Fields (collect based on issue type)

**If issue_type = Dispensing Error (wrong drug, wrong dose, wrong patient):**
Also collect:
- `correct_drug_prescribed` — Dawa iliyoandikwa na daktari: For comparison with what was dispensed
- `drug_received_instead` — Dawa iliyopokelewa badala yake: Core evidence for Pharmacy Council investigation
- `harm_caused_by_error` — Madhara yaliyotokea kwa sababu ya kosa: WHO ICPS harm classification
- `pharmacist_name_or_code` — Jina au nambari ya mfamasia: Tanzania Pharmacy Council requires individual accountability

**If issue_type = Counterfeit / Substandard Medicine:**
Also collect:
- `physical_description_of_suspicion` — Maelezo ya sababu ya tuhuma: e.g., packaging looks different, smell unusual, no effect
- `manufacturer_name_on_packaging` — Jina la mtengenezaji kwenye bundi: TFDA traceability requirement
- `purchase_receipt_available` — Je, risiti ya ununuzi inapatikana?: Evidence for TFDA enforcement
- `sample_available_for_testing` — Je, sampuli ya dawa inapatikana kwa maabara?: TFDA may request physical sample

**If issue_type = Overcharge / Price Gouging:**
Also collect:
- `price_paid_tzs` — Bei iliyolipwa (TZS)
- `expected_price_tzs` — Bei inayotarajiwa / bei ya MSD (TZS): Tanzania GPSA sets maximum prices for essential medicines
- `receipt_available` — Je, risiti inapatikana?: Evidence for TFDA/consumer protection

**If issue_type = Adverse Drug Reaction (ADR):**
Also collect:
- `time_to_onset_hours` — Muda baada ya kumeza dawa hadi madhara kutokea (masaa): WHO ICH E2A field
- `severity_of_reaction` — Ukali wa madhara: Mild / Moderate / Severe / Life-threatening / Fatal
- `patient_age` — Umri wa mgonjwa: ADR risk varies significantly by age group
- `patient_sex` — Jinsia ya mgonjwa: M / F
- `other_medicines_taken_concurrently` — Dawa nyingine zinazochukuliwa wakati mmoja: Drug interaction assessment
- `medical_treatment_required` — Je, matibabu ya dharura yalihitajika?: Severity classification

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| PH-01 | dispensing_error | Wrong drug, wrong dose, wrong patient, wrong directions |
| PH-02 | counterfeit_medicine | Suspected fake, substandard, or adulterated drug |
| PH-03 | expired_medicine | Medicine sold or dispensed past expiry date |
| PH-04 | adverse_drug_reaction | Unexpected or severe reaction to medicine |
| PH-05 | unlicensed_outlet | Pharmacy operating without TFDA license |
| PH-06 | prescription_violation | Prescription-only drug sold without prescription |
| PH-07 | drug_shortage | Medicine unavailable in pharmacy |
| PH-08 | overcharge | Price above GPSA maximum or misleading pricing |
| PH-09 | storage_violation | Medicines stored incorrectly (heat, light exposure) |
| PH-10 | poor_counseling | No or incorrect advice given on drug use |
| PH-11 | controlled_drug_abuse | Illegal sale or dispensing of controlled substances |
| PH-12 | drug_interaction_not_warned | Patient not warned about dangerous drug interaction |
| PH-13 | packaging_labeling_error | Missing, wrong, or illegible label information |
| PH-14 | staff_conduct | Unprofessional, rude, or discriminatory pharmacy staff |

### Resolution Standards for This Industry

- **Outlet level:** Pharmacy should acknowledge complaint immediately; resolve dispensing and pricing issues within 7 days.
- **TFDA product safety:** TFDA investigates within 30 days; serious/counterfeit drug alerts issued within 72 hours. TFDA can order product recall, seize stock, and revoke license.
- **Pharmacy Council:** Dispensing errors involving harm are investigated by Tanzania Pharmacy Council; pharmacist may face suspension or deregistration.
- **ADR reporting:** Serious ADRs reported to TFDA pharmacovigilance unit within 15 days; fatal reactions within 24 hours.
- **Counterfeit drugs:** TFDA has enforcement authority with police; criminal prosecution possible under TFDA Act Cap. 219.

### Escalation Triggers

- `issue_type = counterfeit_medicine` — Immediate TFDA report; advise patient not to take remaining stock; preserve evidence
- `issue_type = adverse_drug_reaction` AND `severity_of_reaction = Severe / Life-threatening / Fatal` — Emergency TFDA pharmacovigilance report within 24 hours
- `issue_type = dispensing_error` AND `harm_caused_by_error` is significant — Escalate to Tanzania Pharmacy Council within 48 hours
- `issue_type = controlled_drug_abuse` — Report to TFDA Drug Control Unit and police; criminal matter
- `issue_type = unlicensed_outlet` — TFDA enforcement immediate; unlicensed pharmacy operation is a criminal offense under Cap. 219
- `issue_type = expired_medicine` AND batch distributed widely — TFDA may initiate public recall

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous feedback accepted |
| pharmacy_outlet | Duka la dawa linalohusika | Recommended | For targeted improvement |
| suggestion_category | Kategoria ya mapendekezo | Yes | Routes to correct team |
| suggestion_detail | Maelezo ya mapendekezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| PS-01 | drug_availability | Upatikanaji wa dawa mbalimbali |
| PS-02 | pricing_transparency | Uwazi wa bei |
| PS-03 | counseling_quality | Ubora wa ushauri wa mfamasia |
| PS-04 | opening_hours | Masaa ya kufungua |
| PS-05 | digital_prescription | Dawa kwa cheti cha kidijitali |
| PS-06 | home_delivery | Uwasilishaji wa dawa nyumbani |
| PS-07 | waiting_time | Kupunguza muda wa kusubiri |
| PS-08 | storage_conditions | Hali bora za kuhifadhi dawa |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina la mwulizaji | Recommended | For tracking |
| query_type | Aina ya swali | Yes | Routes to correct answer |
| drug_name | Jina la dawa inayoulizwa | Conditional | For drug-specific queries |
| urgency | Haraka | Yes | Standard / Dharura |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| drug_availability | Dawa inapatikana? | drug_name_generic, outlet_location |
| drug_price | Bei ya dawa? | drug_name_generic |
| drug_interaction | Je, dawa hizi zinaweza kuchanganywa? | drug_names_list |
| dosage_guidance | Kipimo sahihi cha dawa | drug_name_generic, patient_age |
| storage_advice | Jinsi ya kuhifadhi dawa | drug_name_generic |
| tfda_license_verification | Je, duka hili lina leseni? | pharmacy_outlet_name |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| pharmacist_name | Jina la mfamasia aliyepongezwa | Recommended | Staff recognition |
| outlet_name | Duka la dawa | Yes | Routes to manager |
| specific_aspect_praised | Kipengele kilichotukuka | Yes | Ushauri mzuri / Haraka / Uzoefu / Ukweli wa bei |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | WHO GPP standard; patient satisfaction |

---

## AI Conversation Guidance for This Industry

- **Ask for the drug name immediately.** The medicine name is the single most important identifier. Ask "Dawa inayohusika inaitwa nini?" early — this determines whether the issue is clinical (ADR) or regulatory (counterfeit/expired).
- **Request the batch number for product safety complaints.** Say "Kama una bundi la dawa mbele yako, tafadhali angalia nambari ya kundi (batch number) nyuma ya bundi" — this is critical for TFDA traceability.
- **Do not provide medical advice.** If asked "ni salama kuendelea kumeza dawa hii?", redirect: "Hilo ni swali la kimatibabu — tafadhali wasiliana na daktari wako au mfamasia haraka iwezekanavyo."
- **For ADR complaints, assess severity immediately.** If the patient describes severe symptoms (difficulty breathing, loss of consciousness, severe rash), advise them to go to the nearest emergency room immediately before completing the form.
- **Distinguish between a drug reaction and a drug quality complaint.** A reaction that matches known side effects is an ADR; a reaction with no therapeutic effect plus unusual appearance is a suspected counterfeit. Guide the conversation accordingly.
- **Confirm prescription status.** Ask "Je, dawa hii iliandikwa na daktari?" — dispensing prescription-only drugs without a prescription is a regulatory violation that must be escalated separately.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Drug name | "Dawa inayohusika inaitwa nini? (jina la kawaida au la chapa)" |
| Batch number | "Tafadhali angalia nambari ya kundi (batch number) kwenye bundi la dawa" |
| Expiry date | "Tarehe ya kuisha muda inaonekana kwenye bundi — inasema nini?" |
| Outlet name | "Dawa hii ilinunuliwa au kutolewa wapi — jina la duka la dawa?" |
| Adverse effect | "Baada ya kumeza dawa hii, nini kilitokea? Eleza madhara uliyoyapata" |
| Severity | "Madhara hayo ni makali kiasi gani — ni madogo, ya kati, au ya hatari?" |
| Prescription | "Je, dawa hii iliandikwa na daktari wako, au ulinunua bila cheti?" |
| Sample available | "Je, bado una dawa iliyobaki au bundi lake ambalo linaweza kutumwa kwa maabara?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | counterfeit_medicine | Immediate TFDA report; advise patient to stop taking; preserve sample; TFDA alert within 72 hours |
| severity_of_reaction | Life-threatening OR Fatal | Emergency TFDA pharmacovigilance report within 24 hours; advise immediate hospital attendance |
| issue_type | dispensing_error AND harm_caused | Escalate to Tanzania Pharmacy Council within 48 hours; hospital referral if patient unwell |
| issue_type | unlicensed_outlet | Report to TFDA enforcement unit; criminal referral under Cap. 219 |
| issue_type | controlled_drug_abuse | Report to TFDA Drug Control Unit AND Tanzania Police; criminal matter |
| issue_type | expired_medicine | TFDA inspection request; advise outlet to remove stock; check if batch distributed to other outlets |
| price_paid_tzs | significantly exceeds GPSA maximum | Flag for TFDA/GPSA consumer protection action; provide complainant with GPSA price list reference |
| prescription_involved | No AND prescription-only drug | Report to Tanzania Pharmacy Council; regulatory violation |

---

*Sources: TFDA Act Cap. 219, TFDA Good Dispensing Practice Guidelines 2013, WHO GPP Standards 2011, Tanzania Pharmacy Act Cap. 32, MOHCDGEC STG 4th Edition 2017, WHO ICH E2A/E2B, ISO 10002:2018*
