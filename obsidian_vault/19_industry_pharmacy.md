---
tags: [industry-kb, feedback-classification, field-standards]
---
# Pharmacy / Pharmaceutical — Feedback Collection Fields & Standards

## Industry Identifiers

pharmacy, chemist, duka la dawa, pharmaceutical, drug store, dispensary pharmacy, hospital pharmacy, retail pharmacy, drug wholesaler, medicine distributor, pharmaceutical manufacturer, herbal medicine, traditional medicine, dawa za asili, prescription drug, OTC medicine, over-the-counter, controlled substance, narcotic, antibiotic, antimalarial, antihypertensive, antiretroviral, ARV, insulin, painkiller, supplement, vitamin, TMDA, TFDA, Tanzania Medicines and Medical Devices Authority, NHIF approved pharmacy, drug shortage, counterfeit medicine, dawa bandia, generic drug, branded medicine, medicine recall, pharmacist, mfamasia, pharmaceutical technician, fundi wa dawa, drug registration, drug license, batch number, nambari ya bachi, expiry date, tarehe ya kuisha, dosage, kipimo, side effects, madhara, drug interaction, mwingiliano wa dawa, dispensary, dawa ghafi, adverse drug reaction, ADR, pharmacovigilance, ufuatiliaji wa madhara, cold chain, MSD, Medical Stores Department, dawa ya agizo, dawa bila agizo

## Why Industry-Specific Fields Matter

Pharmacy feedback sits at the intersection of consumer protection and life-threatening pharmacovigilance — a reported adverse drug reaction without batch number, concomitant medications, and onset timing cannot be processed by TMDA VigiFlow or trigger a product recall, meaning a counterfeit or contaminated drug batch stays on shelves. The WHO CIOMS I framework, ICH E2B(R3) ICSR standard, Tanzania TMDA Yellow Form, and FDA MedWatch all mandate specific technical fields that no generic complaint form captures.

## Source Standards

- FDA MedWatch Form 3500A (mandatory) and 3500B (voluntary) — adverse drug/device event reporting
- WHO CIOMS I Form — international minimum for Individual Case Safety Reports (ICSRs)
- ICH E2B(R3) — electronic ICSR standard; mandatory for WHO VigiBase submission
- WHO VigiFlow — electronic pharmacovigilance platform used by TMDA
- Tanzania TMDA Yellow Form — national paper-based ADR reporting system (operational since 1987)
- Tanzania TMDA VigiFlow — electronic ADR submission system
- ADR Reporting Form v1.2 — regional ADR form with detailed clinical fields
- Naranjo Algorithm — standard causality assessment tool for ADRs
- WHO-UMC Causality Scale — Certain / Probable / Possible / Unlikely / Unclassifiable
- ISO 10002:2018 — Complaint Management System minimum fields
- Tanzania MOHCDGEC National Guide for Complaint, Compliment and Suggestion Management
- Tanzania NHIF Drug Formulary and Essential Medicines List (EML)
- Medical Stores Department (MSD) supply chain standards

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL pharmacy complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complaint_unique_id | Nambari ya malalamiko | Yes | ISO 10002:2018 — tracking, deduplication, TMDA cross-reference |
| date_complaint_received | Tarehe malalamiko yalipokewa | Yes | TMDA 15-day mandatory reporting clock starts here; ISO 10002 SLA |
| time_complaint_received | Wakati malalamiko yalipokewa | Yes | Shift accountability; chain of custody timeline |
| channel_received | Njia ya kupokea | Yes | Walk-in / phone / SMS / online / written — access equity monitoring |
| complainant_full_name | Jina kamili la mlalamikaji | Yes | CIOMS I minimum — identifiable reporter required for ICSR validity |
| complainant_relationship_to_patient | Uhusiano na mgonjwa | Yes | Self / family / carer / health worker — determines consent requirements |
| complainant_phone | Simu ya mlalamikaji | Yes | TMDA Yellow Form follow-up; pharmacovigilance officer callbacks |
| complainant_email | Barua pepe | No | Secondary contact for written TMDA response |
| complainant_professional_qualification | Taaluma ya mlalamikaji | Yes | Doctor / pharmacist / nurse / patient / consumer — determines reporting pathway (mandatory vs. voluntary); credibility weight in causality assessment |
| pharmacy_name | Jina la duka la dawa | Yes | TMDA inspection trigger; chain of custody |
| pharmacy_location | Mahali pa duka la dawa | Yes | TMDA enforcement jurisdiction; consumer geographic access data |
| pharmacy_tmda_license_number | Nambari ya leseni ya TMDA | No | Cross-reference against TMDA registered pharmacy database |
| complaint_category | Aina ya malalamiko | Yes | Determines field set and regulatory reporting pathway |
| remedy_sought | Suluhisho analotaka | Yes | ISO 10002:2018 — guides resolution approach |
| date_acknowledged | Tarehe ya kutoa jibu la awali | Yes | ISO 10002 — acknowledgment SLA; Tanzania Guide |

### Complaint Category Taxonomy (use for complaint_category field)

- `adverse_drug_reaction` — Physical harm, unexpected reaction, allergy, toxicity after taking a medicine
- `medication_dispensing_error` — Wrong drug, wrong dose, wrong patient, wrong frequency, wrong quantity dispensed
- `drug_quality_counterfeit` — Suspected fake, substandard, deteriorated, or tampered drug
- `drug_expiry_storage` — Expired drug sold, improper storage conditions (cold chain failure, sunlight exposure)
- `drug_shortage_unavailability` — Essential medicine out of stock; ARV/insulin/TB drug gaps
- `pharmacist_staff_conduct` — Rudeness, failure to counsel, dispensing without prescription, privacy breach
- `pricing_nhif_insurance` — Overcharging, NHIF rejection, undisclosed fees, price discrepancy
- `licensing_compliance` — Pharmacy operating without license, selling controlled drugs without prescription, unregistered products

### Conditional Fields — Adverse Drug Reaction (ADR)

*Triggered when complaint_category = adverse_drug_reaction. These fields align with CIOMS I / ICH E2B(R3) / TMDA Yellow Form. The international legal minimum is: identifiable reporter + identifiable patient + one suspect drug + one adverse reaction.*

#### Section A: Patient Information

| Field | Swahili Label | Required? | Framework Source | Why |
|-------|--------------|-----------|-----------------|-----|
| patient_initials | Herufi za kwanza za mgonjwa | Yes | CIOMS I; ICH E2B D; FDA 3500B | Patient privacy — initials not full name; enables deduplication in VigiBase without identifying patient |
| patient_date_of_birth | Tarehe ya kuzaliwa | Yes | CIOMS I; FDA 3500B; TMDA Yellow | Age-related pharmacokinetic differences; pediatric vs. geriatric risk profiles |
| patient_age | Umri wa mgonjwa | Yes | ADR form v1.2; CIOMS I | Complement to date of birth; essential if DOB unknown |
| patient_sex | Jinsia | Yes | All frameworks | Sex-based ADR risk differences — e.g. QT prolongation; hormonal drug interactions |
| patient_weight_kg | Uzito (kg) | No | FDA 3500B; ADR form | Dosing calculation; overdose vs. therapeutic dose assessment |
| patient_race_ethnicity | Kabila / Asili | No | FDA 3500B | Pharmacogenomic differences; enzyme polymorphisms relevant to drug metabolism |
| relevant_medical_history | Historia ya magonjwa ya awali | Yes | CIOMS I; ICH E2B D | Excludes confounders; identifies predisposing conditions; organ dysfunction |
| known_drug_allergies | Mzio wa dawa unaojulikana | Yes | FDA 3500B; ADR form | Cross-reactivity assessment — critical for causality |
| pregnancy_status | Hali ya ujauzito | Yes | FDA 3500B | Teratogenicity and maternal risk classification; mandatory field if patient is female of childbearing age |

#### Section B: Adverse Reaction Details

| Field | Swahili Label | Required? | Framework Source | Why |
|-------|--------------|-----------|-----------------|-----|
| adverse_reaction_description | Maelezo ya mmenyuko mbaya | Yes | All frameworks | Core datum for pharmacovigilance signal detection in WHO VigiBase |
| meddra_term | Neno la MedDRA | Yes (VigiFlow) | ICH E2B(R3) Section E; WHO VigiBase | Enables cross-border aggregation in WHO VigiBase; mandatory for electronic ICSR |
| date_reaction_started | Tarehe ya kuanza mmenyuko | Yes | ADR form v1.2; CIOMS I; FDA 3500B | Time-to-onset calculation; core input for Naranjo causality algorithm |
| time_of_onset_after_drug | Muda uliopita baada ya dawa | Yes | CIOMS I; TMDA Yellow | Naranjo Algorithm Question 2 — hours/days between first dose and onset |
| date_of_recovery | Tarehe ya kupona | No (Required if recovered) | ADR form v1.2 | Duration of adverse event; severity assessment |
| reaction_seriousness | Uzito wa mmenyuko | Yes | FDA 3500A/B; ICH E2B Section E; CIOMS I | Legal definition of serious ADR triggers mandatory reporting timelines |
| patient_outcome | Hali ya mgonjwa | Yes | ADR form v1.2; CIOMS I | Recovered / recovering / not recovered / sequelae / fatal / unknown — signal evaluation |
| laboratory_test_data | Data za vipimo vya maabara | No | ADR form v1.2 Section B; ICH E2B F | Confirmation of organ damage; objective causality evidence |

**Reaction Seriousness Classification** — reaction_seriousness must use these ICH E2B / FDA criteria (any ONE present = serious):
- Death
- Life-threatening event
- Hospitalization (initial or prolonged)
- Disability or permanent damage
- Congenital anomaly or birth defect
- Required medical or surgical intervention to prevent permanent damage

#### Section C: Suspect Drug Information

| Field | Swahili Label | Required? | Framework Source | Why |
|-------|--------------|-----------|-----------------|-----|
| drug_brand_name | Jina la biashara la dawa | Yes | All frameworks | Product identification for the specific product dispensed |
| drug_generic_inn_name | Jina la kimataifa la dawa (INN) | Yes | WHO VigiFlow; CIOMS I; TMDA Yellow | International interoperability; WHO Drug Dictionary coding; recall linkage |
| batch_lot_number | Nambari ya bachi / lot | Yes (recalls) | ADR form v1.2; TMDA Yellow; FDA 3500A | CRITICAL — without batch number a product recall cannot be scoped; TMDA requires for all quality complaints. Ask patient to retain original packaging |
| manufacturer_name | Jina la mzalishaji | Yes | ADR form v1.2; CIOMS I; TMDA Yellow | Manufacturer notification within 15 working days (CIOMS I rule); recall action |
| expiry_date | Tarehe ya kuisha | Yes | ADR form v1.2; TMDA Yellow | Identifies out-of-date product; storage failure investigation |
| dosage_form | Umbo la dawa | Yes | ICH E2B(R3) G; TMDA Yellow | Tablet / capsule / injection / syrup / etc. — route-specific absorption differences |
| dose_taken | Kipimo kilichotumiwa | Yes | All frameworks | Overdose vs. therapeutic dose assessment; dose-response relationship |
| dose_prescribed | Kipimo kilichoagizwa | Yes | ADR form v1.2 | Discrepancy detection: overdose / underdose / transcription error |
| route_of_administration | Njia ya kutumia dawa | Yes | ADR form v1.2; CIOMS I; ICH E2B G | Route-specific ADR risk — IV > oral; inhalation risks |
| dosing_frequency | Mara ngapi kwa siku | Yes | ADR form v1.2 | Accumulation assessment; drug interaction patterns |
| therapy_start_date | Tarehe ya kuanza dawa | Yes | ADR form v1.2; CIOMS I | Onset-to-reaction interval calculation |
| therapy_end_date | Tarehe ya kuacha dawa | Yes | ADR form v1.2 | Dechallenge assessment — did stopping the drug resolve the ADR? |
| indication_for_use | Sababu ya kutumia dawa | Yes | ICH E2B G; CIOMS I | Rules out off-label use as contributing factor; confirms correct indication |
| action_taken_with_drug | Hatua iliyochukuliwa na dawa | Yes | ADR form v1.2 Section C | Withdrawn / dose reduced / no change / N/A / unknown — dechallenge test |
| dechallenge_result | Matokeo ya kusimama dawa | Yes | ADR form v1.2 | Did stopping the drug resolve the reaction? Positive dechallenge strengthens causality to "Probable" |
| rechallenge_result | Matokeo ya kuanza tena dawa | No | ADR form v1.2 | Positive rechallenge = "Certain" causality on WHO-UMC scale — strongest causality proof available |
| storage_conditions | Hali ya uhifadhi wa dawa | Yes | TMDA Yellow Form; quality context | Temperature / light / humidity at pharmacy and at home — degraded drugs cause ADRs; affects recall scope |
| purchase_date | Tarehe ya kununua | Yes | TMDA Yellow | Links to specific dispensing batch and pharmacist on duty |
| where_purchased | Mahali paliponunuliwa | Yes | TMDA Yellow; Tanzania Guide | Chain of custody; counterfeit source tracing; TMDA inspection routing |

#### Section D: Concomitant (Other) Medications

| Field | Swahili Label | Required? | Framework Source | Why |
|-------|--------------|-----------|-----------------|-----|
| all_current_medications | Dawa zote za sasa | Yes | CIOMS I; ICH E2B G; ADR form v1.2 | Drug-drug interaction detection — 20–30% of ADRs caused by interactions; WHO VigiBase interaction signal generation |
| otc_supplements_herbals | Dawa za madukani, virutubisho, dawa za asili | Yes | FDA 3500B Section D | Herb-drug interactions frequently missed — e.g. St. John's Wort and ARVs; dawa za asili interactions |

*For each concomitant medication, collect: name, dose, route, frequency, dates started/stopped, and indication*

#### Section E: Prescriber & Dispensing Information

| Field | Swahili Label | Required? | Framework Source | Why |
|-------|--------------|-----------|-----------------|-----|
| prescribing_clinician_name | Jina la daktari aliyeandika agizo | Yes | ADR form v1.2; TMDA Yellow | Prescriber notification; prescribing pattern analysis; Medical Council |
| prescribing_facility | Kituo cha matibabu | Yes | ADR form v1.2 | Chain of custody; institutional pattern analysis |
| dispensing_pharmacist_name | Jina la mfamasia aliyegawa | Yes | TMDA Yellow; quality complaints | Dispensing error vs. prescribing error differentiation; pharmacist accountability |
| dispensing_facility_name | Jina la duka la dawa | Yes | TMDA Yellow | Chain of custody confirmation |
| prescription_date | Tarehe ya agizo la dawa | Yes | TMDA Yellow | Lag between prescription and dispensing; identifies stale prescriptions |
| previously_reported_to_tmda | Je, tayari imeripotiwa TMDA? | Yes | Tanzania TMDA Yellow Form | Avoids duplicate reports; ensures regulatory reach |
| tmda_reference_number | Nambari ya kumbukumbu ya TMDA | No | TMDA Yellow | Cross-referencing if previously reported |
| causality_assessment | Tathmini ya sababu | No (intake) / Yes (PV officer) | ADR form v1.2; CIOMS I | Naranjo / WHO-UMC scale: Certain / Probable / Possible / Unlikely / Unclassifiable — completed by pharmacovigilance officer, not AI |

### Conditional Fields — Dispensing Error (complaint_category = medication_dispensing_error)

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| error_type | Aina ya kosa | Yes | Wrong drug / wrong dose / wrong patient / wrong quantity / wrong frequency / wrong route / wrong label — NRLS 19-category taxonomy |
| intended_drug | Dawa iliyopaswa kutolewa | Yes | Correct drug for comparison; determines harm potential |
| drug_actually_received | Dawa iliyopokelewa kweli | Yes | Actual dispensed product |
| prescribed_dose | Kipimo kilichoandikwa | Yes | Baseline for dose error calculation |
| dose_actually_dispensed | Kipimo kilichotolewa | Yes | Discrepancy quantification |
| patient_took_wrong_drug | Je, mgonjwa alitumia dawa mbaya? | Yes | Determines whether clinical review is urgently needed |
| clinical_review_needed | Je, hakiki ya kimatibabu inahitajika? | Yes | If patient ingested wrong drug → medical review required immediately |
| prescribing_doctor_notified | Je, daktari amearifiwa? | Yes | Accountability and corrective prescribing |

### Conditional Fields — Drug Quality / Counterfeit (complaint_category = drug_quality_counterfeit)

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| drug_name | Jina la dawa | Yes | Product identification |
| batch_lot_number | Nambari ya bachi | Yes | Recall scoping — non-negotiable; instruct patient to keep packaging |
| manufacturer_name | Jina la mzalishaji | Yes | Manufacturer notification; recall initiation |
| expiry_date | Tarehe ya kuisha | Yes | Batch validation |
| suspected_defect_description | Maelezo ya kasoro inayoshukiwa | Yes | Color / smell / texture / efficacy / packaging anomalies |
| purchase_date | Tarehe ya kununua | Yes | Batch traceability |
| packaging_available | Je, pakiti ipo? | Yes | Evidence for TMDA testing; ask patient to retain product |
| harm_resulted | Je, madhara yalitokea? | Yes | Determines whether ADR fields also apply |
| reported_to_tmda | Je, imeripotiwa TMDA? | Yes | TMDA enforcement trigger |

### Conditional Fields — Drug Shortage (complaint_category = drug_shortage_unavailability)

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| drug_name | Jina la dawa | Yes | Specific product |
| drug_class | Aina ya dawa | Yes | ARV / insulin / TB / oncology / antihypertensive — determines escalation urgency |
| pharmacies_checked | Maduka yaliyoangaliwa | Yes | Scope: individual stock-out vs. regional shortage |
| duration_of_shortage | Muda wa ukosefu | Yes | Weeks / months — systemic vs. temporary |
| patient_health_impact | Athari kwa afya ya mgonjwa | Yes | Treatment gap assessment — ARV gap risks resistance; insulin gap risks DKA |
| nhif_formulary_drug | Je, iko kwenye orodha ya NHIF? | Yes | NHIF formulary drugs must be available at approved pharmacies — violation flag |
| msd_supply_chain_issue | Je, MSD ndiyo tatizo? | No | Medical Stores Department supply chain alert if systemic |

### Resolution Standards for This Industry

- **ADR reports (serious: harm_level = death or life-threatening)**: Report to TMDA within 7 calendar days (ICH E2B / CIOMS I expedited 7-day rule)
- **ADR reports (serious: hospitalization, disability, congenital anomaly)**: Report to TMDA within 15 working days
- **ADR reports (non-serious)**: Report to TMDA within 90 days
- **Counterfeit / substandard drug**: Immediate TMDA notification; product quarantine at pharmacy; batch number to TMDA product recall unit
- **Dispensing error with patient harm**: Immediate clinical referral; pharmacist to notify prescribing doctor; TMDA notification if harm_level >= 3
- **Drug shortage (ARV/insulin/TB)**: Escalate to MSD and MOHCDGEC within 24 hours; NTLP for TB drugs
- **Pharmacy without license**: Refer to TMDA Inspection and Enforcement Unit
- **Acknowledgment**: Within 3 working days (ISO 10002); TMDA cases have their own regulatory timelines
- **TMDA reporting portal**: VigiFlow electronic system; Yellow Form for paper-based; tmda.go.tz

### Escalation Triggers (field values requiring immediate escalation)

- `complaint_category = adverse_drug_reaction` AND `reaction_seriousness = death` → 7-day TMDA expedited report; preserve batch; clinical investigation
- `complaint_category = adverse_drug_reaction` AND `reaction_seriousness = life_threatening` → 7-day TMDA report; immediate clinical referral
- `complaint_category = adverse_drug_reaction` AND `reaction_seriousness` includes hospitalization, disability, or congenital_anomaly → 15-day TMDA report
- `complaint_category = drug_quality_counterfeit` AND `batch_lot_number` is known → Immediate TMDA product recall unit notification; pharmacy quarantine order
- `drug_class = ARV` AND `duration_of_shortage > 14 days` → MSD + MOHCDGEC emergency alert; HIV treatment interruption risk; drug resistance risk
- `drug_class = insulin` AND patient in active crisis → Medical emergency; drug shortage escalation to MSD simultaneously
- `drug_class = TB_drugs` AND treatment gap confirmed → NTLP (National TB and Leprosy Programme) alert; MDR-TB risk
- `error_type = controlled_drug_dispensed_without_prescription` → TMDA Criminal Investigation Unit + police
- `complaint_category = drug_expiry_storage` AND product type = vaccine → EPI (Expanded Programme on Immunization) emergency; cold chain failure protocol
- `complaint_category = licensing_compliance` AND pharmacy has no TMDA license → TMDA Inspection and Enforcement Unit referral
- `complaint_category = medication_dispensing_error` AND `patient_took_wrong_drug = Yes` → Immediate clinical referral; prescribing doctor notification
- `drug_class = chemotherapy` AND treatment gap confirmed → Oncology department emergency escalation

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| date_submitted | Tarehe iliyowasilishwa | Yes | Tracking; trend analysis |
| channel | Njia | Yes | Walk-in / online / SMS / suggestion box — access equity |
| submitter_name | Jina la mwasilishaji | No | Anonymous submissions accepted — ISO 10002:2018 |
| submitter_contact | Mawasiliano | No | Optional follow-up contact |
| product_service_category | Aina ya bidhaa / huduma | Yes | Dispensing speed / drug availability / labeling / counseling / pricing / staff attitude / opening hours / cold chain / NHIF processing |
| specific_issue | Tatizo mahususi | Yes | Actionability — "labeling" must specify: language / font size / Swahili instructions / allergy warnings |
| frequency_of_issue | Mara ngapi tatizo linatokea | Yes | Systemic vs. one-off; prioritization |
| proposed_improvement | Uboreshaji unaopendekezwa | Yes | Makes suggestion actionable |
| has_medication_safety_implication | Je, ina athari za usalama wa dawa? | Yes | Pharmacy-specific — a suggestion about labeling or storage may have patient safety implications requiring TMDA escalation |
| estimated_patient_impact | Athari inayokadiriwa kwa wagonjwa | No | How many patients affected; severity of impact |
| response_provided | Je, jibu limetolewa? | Yes | ISO 10002 requires acknowledgment |

### Industry-Specific Improvement Categories

- `dispensing_accuracy` — Barcode scanning, prescription verification systems, double-check protocols
- `patient_counseling` — Mandatory counseling on new prescriptions, allergy history collection before dispensing, Swahili instruction leaflets
- `drug_availability` — Stock forecasting for chronic disease drugs, MSD ordering protocols, generic supplier diversification
- `cold_chain_management` — Fridge temperature monitoring, cold chain alert systems, vaccine storage validation
- `nhif_processing` — Electronic prescription integration, NHIF claims speed, formulary access
- `counterfeit_prevention` — TMDA QR verification displays, batch number scanning, staff training on identifying substandard products
- `patient_privacy` — Separate counseling room, soundproofing at dispensing counter, prescription confidentiality
- `accessibility` — Home delivery for chronic medications, extended hours, rural supply chains
- `drug_information` — Drug interaction check systems, patient medication records, pharmacist prescribing pattern reviews
- `pricing_transparency` — Posted price lists, receipt itemization, generic substitution proactive offers

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| date_received | Tarehe iliyopokelewa | Yes | SLA monitoring |
| channel | Njia | Yes | Response channel matching |
| inquirer_name | Jina la muulizaji | Yes | Identity for response |
| inquirer_relationship_to_patient | Uhusiano na mgonjwa | Yes | Consent check: third-party medication queries require patient consent before sharing clinical information |
| query_type | Aina ya swali | Yes | Routes to correct resource — see taxonomy below |
| drug_name_in_question | Jina la dawa husika | Yes | Clinical context for any medication query |
| specific_question | Swali mahususi | Yes | Actual content of the inquiry |
| urgency_level | Kiwango cha haraka | Yes | Routine / urgent — urgent includes: pregnant patient, pediatric dose, suspected drug interaction, emergency access |
| preferred_response_channel | Njia inayopendelewa ya kujibu | Yes | Accessibility; patient preference |

### Common Inquiry Types & Required Data Per Type

**drug_availability** — Is this medicine in stock?
- Additional fields: `drug_generic_name`, `drug_brand_name`, `dosage_form`, `quantity_needed`
- Note: If unavailable, offer to provide nearest stocked pharmacy or check MSD supply chain

**drug_interaction** — Can I take these two medicines together?
- Additional fields: `all_current_medications` (full list), `medical_conditions`
- Note: Must be routed to registered pharmacist — AI should not provide clinical drug interaction advice; provide pharmacist contact

**dosage_information** — How do I take this medicine?
- Additional fields: `drug_name`, `patient_age`, `patient_weight_kg` (pediatric), `prescribing_doctor_instructions`
- Note: AI provides general information; specific dose adjustments require pharmacist

**side_effects** — What are the effects of this drug?
- Additional fields: `drug_name`, `indication_for_use`
- Note: Distinguish inquiry (information) from complaint (ongoing harm); if patient already experiencing side effects, reclassify as ADR

**prescription_clarification** — Can I get this without a prescription? Is this prescription valid here?
- Additional fields: `drug_name`, `prescription_date`, `prescribing_country` (if foreign)
- Note: Controlled drugs always require valid prescription; AI should not advise bypassing

**nhif_insurance** — Is this pharmacy NHIF-registered? Is this drug on the formulary?
- Additional fields: `nhif_card_number`, `drug_name`, `insurance_provider`

**drug_substitute** — Is there a cheaper generic equivalent?
- Additional fields: `brand_name`, `active_ingredient_name`, `dosage_form`

**expiry_verification** — How do I verify if this drug is expired / authentic?
- Additional fields: `drug_name`, `batch_number`, `expiry_date_visible`
- Action: Provide TMDA verification portal contact / QR scanning instructions

**tmda_regulatory** — How do I report a suspicious pharmacy? Is this drug TMDA-registered?
- Additional fields: `pharmacy_name`, `pharmacy_location`, `drug_name`
- Action: Provide TMDA hotline and VigiFlow reporting instructions

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| date_submitted | Tarehe iliyowasilishwa | Yes | Trend analysis; recognition timeliness |
| channel | Njia | Yes | Access monitoring |
| submitter_name | Jina la mshukuriaji | No | Anonymous compliments are valid |
| staff_member_praised | Jina la mtumishi anayeshukuriwa | Yes | Recognition delivery to specific pharmacist or technician |
| staff_designation | Cheo / Jukumu | Yes | Pharmacist / pharmaceutical technician / dispensary officer / pharmacy attendant |
| pharmacy_branch | Tawi la duka la dawa | Yes | Location-specific performance trending |
| date_of_praised_interaction | Tarehe ya huduma iliyoshukuriwa | Yes | Links to specific dispensing encounter |
| specific_behavior_praised | Tendo mahususi linaloshukuriwa | Yes | "Explained drug interaction clearly" / "caught a prescribing error" / "recommended cheaper generic" / "double-checked allergy before dispensing" — reinforces patient-safe pharmacy behaviors specifically |
| patient_safety_catch | Je, kulikuwa na jambo la usalama lililozuiwa? | No | If pharmacist caught a prescribing error, identified a dangerous interaction, or noticed a counterfeit — this positive near-miss triggers a learning report. The catch becomes a system improvement |
| staff_notified | Je, mtumishi amearifiwa? | Yes | Closes recognition loop; motivation |

---

## AI Conversation Guidance for This Industry

- **Lead with the drug name and the problem, not the form.** Open with "What medicine is this about, and what happened?" The drug name and the problem description are the two most diagnostic pieces of information and should be collected first. Everything else builds from there. Do not ask for patient demographics before you know what drug is involved.

- **Urgency triage is mandatory before detailed collection.** If the patient says they are currently experiencing a reaction (difficulty breathing, swelling, chest pain, loss of consciousness), stop immediately and say: "This sounds like a medical emergency. Please call emergency services or go to the nearest hospital right now. We can complete this report afterward." Pharmacovigilance data collection must never delay emergency care.

- **Batch number is the single most important field in a drug quality complaint — ask for it immediately and ask the patient to keep the packaging.** Say: "Before anything else — do you still have the medicine box or bottle? The batch number printed on it is the most important piece of information for investigating this. Please don't throw it away." Without the batch number, a counterfeit drug recall cannot be executed.

- **Concomitant medications are the most commonly missed required field.** After collecting the suspect drug, always ask: "Are you taking any other medicines at the moment — including over-the-counter medicines, vitamins, supplements, or traditional herbal medicines (dawa za asili)?" Drug-drug interactions cause 20–30% of ADRs, and herb-drug interactions are systematically under-reported in Tanzania.

- **Dechallenge and rechallenge are the causality proof — ask them gently in sequence.** After the reaction is described: "Did you stop taking the medicine? And if so, did the reaction improve after stopping?" (dechallenge). If yes: "Did you try taking the medicine again? And did the reaction come back?" (rechallenge). A positive rechallenge alone upgrades causality to "Certain" and changes the entire weight of the report to TMDA.

- **For drug shortage complaints, quantify the scope before escalating.** Ask: "Have you checked other pharmacies? How many? And how long has this been unavailable?" Individual stock-out vs. regional shortage requires different escalation paths — the former goes to the pharmacy manager; the latter goes to MSD and MOHCDGEC.

- **Compliments about prescription error catches are gold.** If a patient says "the pharmacist noticed my doctor made a mistake," treat this as both a compliment AND a near-miss safety learning report. Ask: "What was the error that was caught?" This data feeds clinical governance and can prevent the same error from reaching the next patient.

## Swahili Key Phrases for Field Collection

| Purpose | Swahili Phrase |
|---------|---------------|
| Opening pharmacy complaint | "Tatizo lako ni kuhusu dawa gani, na kilichotokea ni nini?" |
| Batch number urgency | "Kabla ya chochote — je, bado una pakiti ya dawa? Nambari ya bachi iliyo juu yake ni muhimu sana — tafadhali usitupe" |
| Emergency redirect | "Hali hii inaonekana kama dharura ya kimatibabu. Tafadhali piga simu ya dharura au nenda hospitali sasa hivi — tutakamilisha ripoti hii baadaye" |
| Onset timing | "Mmenyuko huu ulianza baada ya muda gani wa kuanza dawa — masaa mangapi au siku ngapi?" |
| Dechallenge | "Je, uliposimama kutumia dawa, mmenyuko uliisha au ulipungua?" |
| Rechallenge | "Baadaye, je, ulianza tena dawa ile ile? Kama ndiyo — mmenyuko ulirudi?" |
| Concomitant medications | "Je, unanywa dawa nyingine zozote sasa hivi — dawa za madukani, vitamini, virutubisho, au dawa za asili (mitishamba)?" |
| Allergy history | "Je, una mzio wowote unaojulikana wa dawa?" |
| Storage conditions | "Dawa hii ilihifadhiwa wapi — kwenye jokofu, au nje? Na nyumbani ulihifadhia wapi?" |
| Drug shortage scope | "Umekwenda maduka mangapi bila kupata dawa hii? Na imekuwa hivi kwa wiki ngapi?" |
| ADR seriousness | "Je, mmenyuko huu ulisababisha kulazwa hospitalini, ulemavu, au hatari ya maisha?" |
| Counterfeit signs | "Kuna tofauti gani kati ya dawa hii na dawa zako za kawaida — rangi, ladha, harufu, au athari?" |
| Where purchased | "Ulinunua dawa hii wapi — jina la duka na mahali pake?" |
| TMDA reporting | "Hili tayari limeripotiwa TMDA? Kama hapana, tutakusaidia kufanya ripoti ya Yellow Form" |
| Compliment staff name | "Unakumbuka jina la mfamasia au mtumishi huyo — hata jina la kwanza litamsaidia kupokea pongezi" |
| Prescription error catch | "Mfamasia aligundua hitilafu gani kwenye agizo la daktari wako?" |

## Action Recommendations Based on Field Values

| If Field | Equals | Recommended Action |
|----------|--------|-------------------|
| reaction_seriousness | death or life_threatening | 7-day TMDA expedited report; preserve batch; immediate clinical investigation |
| reaction_seriousness | hospitalization, disability, or congenital_anomaly | 15-day TMDA mandatory report via VigiFlow or Yellow Form |
| complaint_category | drug_quality_counterfeit AND batch_lot_number known | TMDA product recall unit notification immediately; request pharmacy to quarantine remaining stock |
| complaint_category | drug_quality_counterfeit AND batch_lot_number unknown | Instruct patient to retrieve packaging; note pharmacy and purchase date for TMDA inspection |
| drug_class | ARV AND duration_of_shortage > 14 days | MSD + MOHCDGEC emergency alert; HIV programme officer notification; drug resistance risk |
| drug_class | insulin AND patient_health_impact = active_crisis | Medical emergency parallel track; MSD shortage alert simultaneously |
| drug_class | TB_drugs AND treatment gap confirmed | NTLP (National TB and Leprosy Programme) immediate alert; MDR-TB prevention priority |
| error_type | controlled_drug_dispensed_without_prescription | TMDA Criminal Investigation Unit; police referral |
| complaint_category | drug_expiry_storage AND product_type = vaccine | EPI emergency; cold chain failure protocol; MOHCDGEC notification |
| complaint_category | licensing_compliance AND no_tmda_license | TMDA Inspection and Enforcement Unit referral; pharmacy ID and location |
| patient_took_wrong_drug | Yes | Immediate clinical referral; prescribing doctor notification; poison control if overdose risk |
| dechallenge_result | positive (reaction resolved when drug stopped) | Causality upgraded to Probable; strengthens TMDA report |
| rechallenge_result | positive (reaction returned when restarted) | Causality = Certain (WHO-UMC); strongest possible TMDA signal report |
| patient_safety_catch | Yes (compliment — prescribing error caught) | Convert to near-miss learning report; share at pharmacy governance meeting; recognize staff formally |
| has_medication_safety_implication | Yes (suggestion) | Route to pharmacy director and QIT; not just store manager |
| query_type | drug_interaction | Route to registered pharmacist; AI must not provide drug interaction clinical advice |
| query_type | side_effects AND patient experiencing them now | Reclassify as ADR complaint; begin ADR field collection |
| drug_class | chemotherapy AND treatment gap | Oncology department emergency escalation; MOHCDGEC supply chain alert |
| previously_reported_to_tmda | No AND reaction_seriousness is serious | Generate TMDA report immediately; 7-day or 15-day clock starts at date_complaint_received |

---

## Key Entities & Roles (Tanzania Context)

**Staff Titles:** Pharmacist (Mfamasia / Daktari wa Dawa), Pharmaceutical Technician (Fundi wa Dawa), Dispensary Officer, Pharmacy Attendant, Drug Store Manager, Medical Sales Representative (MSR), Drug Inspector (TMDA), Traditional Medicine Practitioner (Mganga wa Jadi)

**Drug Categories:** Prescription-Only Medicine (POM / Dawa ya Agizo), Over-the-Counter (OTC / Dawa bila Agizo), Controlled Drug / Narcotic, Generic Medicine, Branded / Originator Medicine, Biological / Biosimilar, Herbal / Traditional Medicine (Dawa za Asili), Supplement / Vitamin, Medical Device / Supply

**Common Drug Names (Tanzania):** Coartem (artemether-lumefantrine — malaria), Doxycycline, Amoxicillin, Metformin, Amlodipine, Atenolol, Humulin (insulin), Efavirenz / Tenofovir / Lamivudine (ARV), Tramadol, Diclofenac, Paracetamol, Ibuprofen, ORS, Zinc (childhood diarrhea), Folic Acid, Ferrous Sulfate, Albendazole, Fluconazole, Metronidazole, Co-trimoxazole, TB drugs (RHZE), Depo-Provera, Microgynon, Artemisinin-based Combination Therapy (ACT)

**Regulatory & Government Bodies:** TMDA (Tanzania Medicines and Medical Devices Authority), MOHCDGEC, Medical Stores Department (MSD), NHIF, Tanzania Pharmacy Board (within TMDA), NTLP (National TB and Leprosy Programme), EPI (Expanded Programme on Immunization), WHO-UMC (Uppsala Monitoring Centre)

**Key Processes:** Drug Registration (Usajili wa Dawa), Prescription Verification, Dispensing (Ugawaji wa Dawa), Cold Chain Management, Drug Recall (Urejeshaji wa Dawa), Pharmacovigilance (Ufuatiliaji wa Madhara ya Dawa), ADR Reporting, VigiFlow, TMDA Yellow Form, NHIF Drug Formulary, Essential Medicines List (EML), Naranjo Algorithm, WHO-UMC Causality Scale, ICH E2B(R3) ICSR, CIOMS I Form
