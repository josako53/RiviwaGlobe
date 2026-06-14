---
tags: [industry-kb, field-standards, feedback-fields, food, consumables, fmcg]
---
# Food & Consumable Products — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: chakula, food, kinywaji, beverage, maji ya kunywa, drinking water, uji, porridge, mkate, bread, biscuit, snack, chips, crisps, confectionery, peremende, chocolate, candy, ice cream, dairy, maziwa, yogurt, mtindi, cheese, jibini, cooking oil, mafuta ya kupikia, sugar, sukari, salt, chumvi, flour, unga, rice, mchele, pasta, noodle, ketchup, sauce, spice, viungo, canned food, chakula cha makopo, tin, instant noodle, ready-to-eat, RTF, juice, soda, soft drink, soda baridi, alcoholic beverage, pombe, beer, bia, wine, spirits, expiry date, tarehe ya kuisha muda, best before, rotten, chakula kilichooza, mold, ukungu, foreign object, kitu kigeni, contamination, uchafu, food poisoning, sumu ya chakula, listeria, salmonella, food safety, usalama wa chakula, TFDA, TBS, Tanzania Bureau of Standards, Tanzania Food and Drug Authority, Codex Alimentarius, halal, label, lebo, packaging, ufungashaji, nutrition label, thamani ya lishe, producer, mtengenezaji, manufacturer, MBS

## Why Industry-Specific Fields Matter

Food and consumable complaints often involve serious public health risks — food poisoning, contamination, counterfeit products, or expired stock. The TFDA Act requires adverse event reporting, and the Tanzania Bureau of Standards requires product certification. A batch number and manufacture/expiry date are critical for potential product recall. Without these fields, the AI cannot generate a TFDA-compliant report or determine whether an incident is isolated or part of a batch-wide safety issue.

## Source Standards

- Tanzania Food, Drugs and Cosmetics Act, Cap. 219 (TFDA)
- TFDA Food Hygiene Regulations 2006
- TFDA Food Labelling Regulations 2006
- Tanzania Bureau of Standards (TBS) Act, Cap. 130
- TBS Compulsory Standards for Food Products
- Codex Alimentarius Commission standards (FAO/WHO) — international food safety reference
- Tanzania Food Safety Authority (TFSA) — emerging regulatory body
- Fair Competition Act, Cap. 285 — misleading food labelling and advertising
- WHO Food Safety Guidelines — 5 keys to safer food
- ISO 22000:2018 — Food safety management systems
- Halal Council of Tanzania — halal certification standards
- East African Community Standardization standards for food products

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL food and consumable complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | TFDA complaint form; enables follow-up |
| complainant_phone | Nambari ya simu | Yes | For status updates and health surveillance |
| product_name | Jina la bidhaa | Yes | Core identifier; required for TFDA report |
| product_brand | Chapa ya bidhaa | Yes | Manufacturer identification; required for recall |
| product_category | Kategoria ya bidhaa | Yes | Food / Beverage / Water / Dairy / Processed / Snacks etc. |
| manufacturer_name | Jina la mtengenezaji | Recommended | TFDA traceability; manufacturer accountability |
| manufacturing_country | Nchi ya uzalishaji | Yes | For imported product complaints; determines customs/TFDA port control |
| batch_number | Nambari ya kundi (batch/lot number) | Yes | CRITICAL for product recall; TFDA pharmacovigilance equivalent for food |
| manufacture_date | Tarehe ya uzalishaji | Recommended | For shelf life calculation |
| expiry_date | Tarehe ya kuisha muda | Yes | For expired product complaints; TFDA enforcement |
| purchase_location | Mahali pa ununuzi | Yes | For traceability and retailer accountability |
| purchase_date | Tarehe ya ununuzi | Yes | Within or after expiry date determination |
| issue_type | Aina ya tatizo | Yes | TFDA complaint taxonomy |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; TFDA requires detailed narrative |
| health_impact | Je, mtu yeyote aliugua? | Yes | Public health surveillance; determines urgency level |
| number_of_people_affected | Idadi ya watu walioathirika | Conditional | Outbreak determination threshold |
| sample_available | Je, sampuli ya bidhaa inapatikana? | Yes | TFDA laboratory testing prerequisite; critical for investigation |

### Conditional Fields (collect based on issue type)

**If issue_type = Food Poisoning / Illness:**
Also collect:
- `symptoms_experienced` — Dalili zilizoonekana: Kichefuchefu / Kutapika / Kuhara / Homa / Maumivu ya tumbo — TFDA illness classification
- `time_from_consumption_to_symptoms_hours` — Muda kutoka kuliwa hadi dalili (masaa): Incubation period helps identify pathogen
- `medical_treatment_sought` — Je, matibabu yalitafutwa? Yes / No: If yes, hospital name and records for TFDA
- `other_people_affected` — Watu wengine walioathirika baada ya kula chakula hicho kile: Outbreak indicator
- `food_storage_conditions` — Hali ya kuhifadhi chakula kabla ya kutumia: For investigation of post-purchase contamination

**If issue_type = Foreign Object Found:**
Also collect:
- `foreign_object_type` — Aina ya kitu kigeni: Metal / Plastic / Glass / Insect / Hair / Stone / Other
- `object_photos_available` — Je, picha za kitu kigeni zinapatikana?: TFDA requires photographic evidence
- `injury_caused` — Je, kitu kigeni kilisababisha majeraha?: Dental / Mouth / Throat injury changes urgency

**If issue_type = Packaging / Label Problem:**
Also collect:
- `label_issue_type` — Aina ya tatizo la lebo: Missing information / Wrong information / No Swahili translation / No nutrition label / No batch number
- `label_language_compliance` — Je, lebo ina lugha ya Kiswahili?: TFDA requires Swahili labelling for products sold in Tanzania
- `halal_label_issue` — Je, tatizo linahusiana na lebo ya halal?: Halal certification disputes route to Halal Council of Tanzania

**If issue_type = Counterfeit / Substandard:**
Also collect:
- `tbs_certification_mark` — Je, bidhaa ina alama ya TBS / S Mark?: Required for regulated food categories
- `suspected_counterfeit_evidence` — Ushahidi wa tuhuma: Unusual taste / smell / color / packaging inconsistency

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| FD-01 | food_poisoning | Illness following consumption; suspected contamination |
| FD-02 | foreign_object | Physical contaminant found in product |
| FD-03 | expired_product | Product sold or consumed past expiry date |
| FD-04 | poor_quality | Taste, texture, smell, or appearance abnormal but no illness |
| FD-05 | contamination_biological | Mold, bacteria, insects, or rodent contamination |
| FD-06 | contamination_chemical | Unusual chemical smell or appearance; suspected chemical contamination |
| FD-07 | counterfeit_product | Suspected fake brand or substandard imitation |
| FD-08 | labelling_violation | Missing, wrong, or non-compliant labelling |
| FD-09 | misleading_claim | Product claims (e.g., "natural", "organic", "halal") that are false |
| FD-10 | incorrect_weight | Contents less than stated on packaging |
| FD-11 | packaging_defect | Damaged packaging allowing contamination |
| FD-12 | alcohol_content_dispute | Undisclosed alcohol content (especially relevant for non-alcoholic labelled products) |
| FD-13 | halal_certification_dispute | Product labelled halal but suspected not to be |
| FD-14 | water_safety | Bottled or packaged water quality concerns |
| FD-15 | temperature_breach | Evidence of cold chain failure (frozen/chilled product sold thawed) |

### Resolution Standards

- **TFDA:** Food safety complaints acknowledged within 48 hours; investigation within 15 days; serious (illness/outbreak) within 72 hours. TFDA can order product recall.
- **TBS:** Product quality and standards violation complaints; investigation within 30 days.
- **Manufacturer/retailer level:** Standard response within 7 days; replacement or refund within 14 days.
- **Public health outbreak:** If multiple people affected, MOHCDGEC Disease Surveillance Unit must be notified immediately; Tanzania has mandatory outbreak reporting requirements.
- **Required for TFDA escalation:** Product name, brand, batch number, expiry date, purchase location, description of issue, health impact, sample if available.

### Escalation Triggers

- `health_impact = Yes` AND `number_of_people_affected >= 2` — Potential outbreak; immediate MOHCDGEC Disease Surveillance notification AND TFDA food safety alert
- `issue_type = food_poisoning` AND `symptoms = severe` (hospitalization, bloody diarrhea, neurological) — Public health emergency; prioritize TFDA and hospital CDSS reporting
- `issue_type = foreign_object` AND injury caused — TFDA immediate report; medical attention advised
- `issue_type = counterfeit_product` AND widely distributed — TFDA product recall investigation; criminal referral possible
- `issue_type = contamination_chemical` — Immediate TFDA and MOHCDGEC chemical safety unit
- `issue_type = halal_certification_dispute` AND systematic — Halal Council of Tanzania AND TFDA joint investigation

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| product_name | Bidhaa | Recommended | For product-specific routing |
| manufacturer_name | Mtengenezaji | Recommended | For routing to R&D team |
| suggestion_category | Kategoria | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| FDS-01 | taste_quality | Ubora wa ladha |
| FDS-02 | packaging | Ufungashaji bora au rafiki wa mazingira |
| FDS-03 | nutritional_value | Thamani ya lishe |
| FDS-04 | halal_organic | Bidhaa za halal au za asili |
| FDS-05 | pricing | Bei nafuu |
| FDS-06 | labelling | Taarifa bora kwenye lebo |
| FDS-07 | new_flavors | Ladha mpya |
| FDS-08 | local_ingredients | Matumizi ya malighafi za ndani |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina | Recommended | For tracking |
| product_name | Bidhaa | Yes | Core for food queries |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| ingredient_inquiry | Bidhaa ina nini? | product_name, allergen_concern |
| halal_verification | Je, bidhaa hii ni halal? | product_name, product_brand |
| expiry_date | Tarehe ya kuisha muda | product_name, batch_number |
| nutritional_info | Thamani ya lishe ya bidhaa | product_name |
| allergen_info | Je, bidhaa ina allergen (karanga, gluten, maziwa)? | product_name |
| tbs_certification | Je, bidhaa ina cheti cha TBS? | product_name, product_brand |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| product_name | Bidhaa iliyopongezwa | Yes | Product/brand recognition |
| manufacturer_name | Mtengenezaji | Recommended | Routes to marketing/quality team |
| specific_aspect_praised | Kipengele | Yes | Ladha nzuri / Ubora wa ufungashaji / Thamani ya lishe / Bei nzuri |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Brand health tracking |

---

## AI Conversation Guidance for This Industry

- **Food safety complaints are potential public health emergencies.** Before collecting any product details, ask "Je, mtu yeyote aliugua baada ya kutumia bidhaa hii?" If yes, immediately provide emergency health advice and flag for TFDA escalation.
- **Always ask for the batch number.** Even if the customer has discarded the packaging, guide them to check if they can still find it. "Nambari ya kundi (batch number) inaweza kuonekana nyuma ya bidhaa, chini ya bundi, au kwenye kifuniko — je, bado una bundi hilo?"
- **For food poisoning, ask about the time between eating and symptoms.** This is medically important for identifying the pathogen. "Muda ngapi ulipita kati ya kuliwa bidhaa hiyo na dalili kuanza — masaa machache, au siku moja?"
- **Preserve the sample.** Always advise the complainant to keep any remaining product sealed in the refrigerator for possible laboratory testing. "Ikiwa bado una bidhaa iliyobaki, ihifadhi kwenye jokofu bila kufungua — inaweza kuhitajika kwa upimaji wa maabara."
- **For foreign object complaints, ask for photos.** Visual evidence is critical for both TFDA and manufacturer investigations. "Unaweza kupiga picha ya kitu kigeni ulichokikuta kabla ya kuisafisha?"
- **Do not assign blame to the manufacturer vs. retailer prematurely.** Temperature breach, improper storage, and post-purchase contamination can all mimic manufacturing defects.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Product name | "Bidhaa inaitwa nini — na chapa yake ni nani?" |
| Batch number | "Nambari ya kundi (batch number) inaonekana nyuma ya bidhaa au kwenye kifuniko — inasema nini?" |
| Expiry date | "Tarehe ya kuisha muda (best before / expiry date) inasema nini?" |
| Health impact | "Je, wewe au mtu mwingine aliugua baada ya kutumia bidhaa hii? Eleza dalili" |
| Number affected | "Watu wangapi walitumia bidhaa hii na kuathirika?" |
| Symptom timing | "Muda gani ulipita kati ya kuliwa na dalili kuanza?" |
| Sample available | "Je, bado una bidhaa iliyobaki au bundi lake? Ihifadhi kwenye jokofu bila kufungua" |
| Purchase location | "Bidhaa hii ilinunuliwa wapi hasa — jina la duka na mahali?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| health_impact | Yes AND number_affected >= 2 | Immediate TFDA food safety alert + MOHCDGEC Disease Surveillance; potential outbreak |
| issue_type | food_poisoning AND severe symptoms | Emergency: advise hospital attendance; TFDA report within 24 hours |
| issue_type | foreign_object AND injury caused | TFDA immediate report; advise medical attention |
| issue_type | contamination_chemical | TFDA + MOHCDGEC chemical safety; advise stop use immediately |
| issue_type | counterfeit_product AND tbs_mark absent | TBS enforcement + TFDA report; criminal referral |
| issue_type | labelling_violation AND no Swahili | TFDA labelling compliance report; manufacturer notification |
| issue_type | halal_certification_dispute | Halal Council of Tanzania + TFDA joint investigation |
| batch_number | available | Include in TFDA report for potential batch recall; critical field |
| sample_available | Yes | Request sample preservation for laboratory testing; TFDA laboratory will collect |

---

*Sources: TFDA Act Cap. 219, TFDA Food Hygiene Regulations 2006, TFDA Food Labelling Regulations 2006, TBS Act Cap. 130, Codex Alimentarius Commission, WHO Food Safety Guidelines, ISO 22000:2018, Fair Competition Act Cap. 285, Halal Council of Tanzania*
