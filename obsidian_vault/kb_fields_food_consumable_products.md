---
tags: [industry-kb, field-standards, feedback-fields]
---
# Food & Consumable Products — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: food product, packaged food, beverage, snack, bakery, confectionery, bottled water, cooking oil, flour, sugar, dairy, milk, yogurt, juice, soft drink, canned food, cereal, pasta, rice, sauce, baby food, infant formula, energy drink, restaurant, fast food, takeaway, food delivery, catering, halal, expiry date, best before, batch number, lot number, foreign body, food poisoning, contamination, Azam, Bakhresa, Serengeti Breweries, Tanzania Breweries, TBS food, TMDA, chakula, kinywaji, chakula kilichoharibika, sumu ya chakula, tarehe ya kumalizika, nambari ya kundi, maumivu ya tumbo, kichefuchefu, kutapika, kuhara, mzio wa chakula, bidhaa ya kuliwa, mkate, uji, mafuta ya kupikia, mgahawa, chakula cha haraka, mpishi, menu, allergen

## Why Industry-Specific Fields Matter

Food complaints carry a fundamentally different risk profile from all other industries: a single complaint about a foreign object or illness may be the first signal of a product recall affecting thousands of consumers, or a mass foodborne illness outbreak requiring public health authority activation. Without lot/batch number, symptom onset time, and number of persons affected, the AI cannot assess whether this is an isolated quality incident or a regulatory emergency requiring immediate TBS notification and product withdrawal.

## Source Standards

- EU General Food Law Regulation (EC) No 178/2002 — Articles 17, 18, 19 (traceability, unsafe food notification, field requirements)
- FDA CFSAN Adverse Event Reporting System (CAERS) — openFDA food event API schema; Form FDA 3500B (Sections B, C, E)
- USDA FSIS Electronic Consumer Complaint Form (ECCF) — confirmed field structure
- Tanzania Bureau of Standards (TBS) — food safety regulatory authority since 1 July 2019 (successor to TFDA for food); Standards Act No. 2 of 2009; complaints@tbs.go.tz, toll-free 0800110827
- Tanzania Medicines and Medical Devices Authority (TMDA) — handles medicines and medical devices only (not food); relevant for food-medicine boundary cases
- ISO 10002:2018 — Quality management: guidelines for complaints handling (clauses 8.2, Annex C)
- ISO 22000 / HACCP — food safety management system standards (provide issue taxonomy context)
- EU Implementing Regulation (EC) No 931/2011 — additional traceability fields for food of animal origin

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | ISO 10002:2018 clause 8.2 — mandatory for complaint record; FDA 3500B Section E requires reporter identity |
| complainant_phone_number | Nambari ya simu ya mlalamikaji | Yes | Primary contact for follow-up; required by ISO 10002:2018 and FDA 3500B for case tracking |
| complainant_email | Barua pepe ya mlalamikaji | Recommended | For written acknowledgement and documentation sharing |
| product_name | Jina la bidhaa | Yes | All standards (EU 178/2002, FDA CAERS, USDA FSIS, TBS) — mandatory first field; complaint cannot be routed without product identification |
| brand_name | Chapa ya bidhaa | Yes | FDA 3500B Section C — brand name as it appears on label; enables manufacturer routing |
| product_category | Kategoria ya bidhaa | Yes | USDA FSIS ECCF routing question (meat/poultry/egg vs. other food); determines regulatory jurisdiction |
| batch_or_lot_number | Nambari ya kundi / lot | Yes | EU Reg. 178/2002 Art. 18 — MOST CRITICAL food complaint field; the single identifier that enables regulatory traceability and product recall; FDA 3500B Section C; USDA FSIS; TBS |
| expiry_or_best_before_date | Tarehe ya kumalizika / best before | Yes | EU 178/2002 Art. 18, FDA 3500B Section C, TBS — required for recall scope determination and expired-product-sold complaints |
| manufacturing_date | Tarehe ya utengenezaji (kama ipo) | Recommended | EU 178/2002 Art. 18 sector regulations (especially animal products per EC 931/2011) |
| purchase_date | Tarehe ya ununuzi | Yes | All sources — establishes timeline between purchase and reported issue |
| purchase_location | Mahali pa ununuzi (duka, jina, anwani) | Yes | EU 178/2002 Art. 18, FDA CAERS, USDA FSIS ECCF — required to trace supply chain and identify distribution scope |
| manufacturer_name | Jina la mtengenezaji | Yes | EU 178/2002 Art. 18, FDA 3500B Section C — identifies responsible party for product safety |
| issue_type | Aina ya tatizo | Yes | FDA 3500B Section B / USDA FSIS ECCF issue category — determines investigation type, escalation level, and regulatory obligation |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018 clause 8.2 — narrative description required; FDA 3500B free text reaction description |
| evidence_photos_uploaded | Picha za bidhaa na kasoro zilipakiwa | Recommended | FDA 3500B (recommended); GPSR Art. 36; TBS practice — visual evidence critical for foreign body and packaging complaints |
| sample_retained | Je, bidhaa / sampuli imehifadhiwa? | Yes | TBS practice, FDA 3500B Section F — sample enables laboratory testing which is required for regulatory action; if yes, advise customer not to discard |
| tbs_mark_or_registration | Alama ya TBS / nambari ya usajili (kama ipo) | Recommended | TBS — all food products sold in Tanzania must bear TBS mark; absence may constitute regulatory violation |
| desired_resolution | Suluhisho unalotaka | Yes | ISO 10002:2018 Annex C — remedy sought; guides resolution offer |
| reporter_type | Aina ya mtoa taarifa | Yes | FDA 3500B Section E — Consumer / Health professional / Other; determines credibility weighting and referral path |

### Conditional Fields (collect based on issue type)

**If issue_type = illness_adverse_reaction OR food_poisoning:**
Also collect:
- `symptoms_description` — Maelezo ya dalili: FDA CAERS (reactions field — coded MedDRA terms; plain language for consumer); required for clinical follow-up and outbreak assessment
- `symptom_onset_date_time` — Tarehe na saa ya kuanza kwa dalili: Foodborne illness best practice — onset timing identifies incubation period which indicates likely pathogen
- `time_between_eating_and_symptoms_hours` — Muda kati ya kula na kuanza dalili (masaa): Critical epidemiological field; different pathogens have characteristic incubation windows (Salmonella 6-48h; Staph aureus 1-6h; norovirus 12-48h)
- `medical_attention_sought` — Je, ulitafuta msaada wa daktari? (Ndiyo / Hapana): FDA CAERS outcomes section
- `hospital_or_clinic_name` — Jina la hospitali / kliniki (kama ipo): FDA CAERS — for clinical follow-up and outbreak investigation
- `hospital_admission_number` — Nambari ya kulazwa hospitalini (kama ipo): FDA CAERS — required if patient was hospitalized
- `outcome_severity` — Kiwango cha madhara: FDA CAERS outcome codes — Kuhusuishwa hospitalini / Dharura / Ulemavu / Hatari ya maisha / Kifo / Nyingine
- `number_of_persons_affected` — Idadi ya watu walioathirika: Foodborne illness best practice — multiple affected persons from same meal/product signals outbreak
- `names_contacts_other_affected` — Majina na mawasiliano ya watu wengine walioathirika (kama ipo): Foodborne illness outbreak investigation; public health contact tracing
- `whether_tbs_notified` — Je, TBS wamearifiwa? (Ndiyo / Hapana): TBS Tanzania requirement for food safety incidents
- `whether_health_authority_notified` — Je, mamlaka ya afya imearifiwa? (Ndiyo / Hapana): EU 178/2002 Art. 19; USDA FSIS ECCF routing question

**If issue_type = foreign_object_found:**
Also collect:
- `foreign_object_description` — Maelezo ya kitu kilichopatikana ndani ya chakula: e.g., kipande cha plastiki, chuma, nywele, kiroboto, jiwe — USDA FSIS and FDA CAERS categorize foreign objects as product problems requiring investigation
- `foreign_object_retained` — Je, kitu kilichopatikana kimehifadhiwa? (Ndiyo / Hapana): TBS and FDA 3500B — sample including foreign body must be retained for laboratory analysis
- `injury_from_foreign_object` — Je, kitu kilisababisha maumivu? (Ndiyo / Hapana): e.g., broken tooth / cut in mouth; determines whether medical and product liability actions are needed

**If issue_type = mislabeling OR allergen_not_declared:**
Also collect:
- `allergen_type` — Aina ya mzio: Gluten / Karanga (peanuts) / Maziwa (dairy) / Yai (egg) / Samaki / Soya / Njugu / Nyingine — EU 178/2002 Annex II (14 major allergens); FDA Food Allergy Safety Act
- `allergic_reaction_occurred` — Je, mmenyuko wa mzio ulitokea? (Ndiyo / Hapana): Determines severity level and medical/legal escalation need
- `allergic_reaction_severity` — Ukali wa mmenyuko: Upole (ngozi kuwasha) / Wastani (kuvimba) / Anaphylaxis (dharura ya maisha): Anaphylaxis = immediate emergency escalation
- `claimed_certification` — Madai ya cheti kwenye pakiti (Halal / Organic / Vegan): Unverified certification claims on label; routes to relevant certification body

**If issue_type = packaging_defect OR tampered_packaging:**
Also collect:
- `seal_condition` — Hali ya mhuri wa usalama: Intact / Damaged / Missing / Appears tampered: Tamper evidence is a TBS and EU 178/2002 packaging requirement
- `packaging_damage_type` — Aina ya uharibifu wa ufungaji: Crack / Leak / Bloated / Dented (can) / Resealed: Bloated cans specifically indicate possible botulism (Clostridium botulinum gas production) — immediate escalation

**If is_restaurant_or_food_service = Ndiyo:**
Also collect:
- `restaurant_name_location` — Jina na mahali pa mgahawa: Routes complaint to food service entity vs. manufacturer
- `meal_ordered` — Chakula kilichoagizwa: For cross-contamination and preparation investigation
- `date_time_of_meal` — Tarehe na saa ya mlo: Critical for correlating with kitchen shift, batch of ingredients used
- `service_type` — Aina ya huduma: Dine-in / Takeaway / Delivery
- `hygiene_certification_visible` — Je, cheti cha usafi wa mgahawa kilionekana? (Ndiyo / Hapana / Sijui): TBS and municipal health authority require food premises certification

### Issue Type Classification

| Code | Issue Type | Swahili Description |
|------|-----------|---------------------|
| FC-01 | foreign_object_found | Kitu cha kigeni kilipatikana ndani ya chakula |
| FC-02 | bad_taste_odor_appearance | Ladha mbaya / harufu mbaya / rangi isiyo ya kawaida |
| FC-03 | food_poisoning_illness | Sumu ya chakula / kuugua baada ya kula |
| FC-04 | allergic_reaction | Mmenyuko wa mzio (allergen halikutajwa) |
| FC-05 | expired_product_sold | Bidhaa iliyoisha muda iliuzwa |
| FC-06 | mislabeling | Lebo isiyo sahihi / taarifa za uwongo |
| FC-07 | allergen_not_declared | Allergen halikutajwa kwenye lebo |
| FC-08 | packaging_defect | Kasoro ya ufungaji |
| FC-09 | tampered_packaging | Ufungaji ulionekana kubadilishwa |
| FC-10 | underweight_underfilled | Uzito / ujazo mdogo kuliko unaodaiwa |
| FC-11 | false_health_claims | Madai ya afya ya uwongo kwenye pakiti |
| FC-12 | missing_label_information | Taarifa muhimu hazipo kwenye lebo (batch, expiry, origin) |
| FC-13 | counterfeit_food_product | Bidhaa ya chakula bandia inashukiwa |
| FC-14 | restaurant_hygiene | Usafi mbaya wa mgahawa / jiko |
| FC-15 | restaurant_food_quality | Ubora mbaya wa chakula cha mgahawa |
| FC-16 | wrong_order_delivered | Agizo tofauti lilitumwa (delivery) |
| FC-17 | cold_chain_failure | Msururu wa baridi ulipoteza ufanisi (chakula cha baridi kilifikia moto) |
| FC-18 | halal_certification_query | Shaka kuhusu cheti cha halal |

### Resolution Standards for This Industry

- **Manufacturer / food business level (Tanzania):** ISO 10002:2018 recommends acknowledgement within 5 working days; foreign body and illness complaints should receive initial response within 48 hours.
- **TBS escalation (Tanzania):** Food safety complaints — especially foreign bodies, illness, expired products, and suspected contamination — should be reported to TBS (complaints@tbs.go.tz / 0800110827). TBS can order product withdrawal, market seizure, and laboratory testing.
- **TMDA:** Medicines and medical devices only. Food supplements may fall under TMDA or TBS depending on product classification; dietary supplements with therapeutic claims go to TMDA.
- **Municipal health authority:** Restaurant and food premises hygiene complaints go to the relevant local government health authority (Halmashauri ya Jiji / Manispaa).
- **EU 178/2002 Art. 19 standard:** If a food business operator concludes that a food poses a serious risk, they must immediately notify competent authorities and initiate withdrawal/recall. Consumer complaint is the trigger event — the lot number is the operational key.
- **Required documentation for escalation:** Product name, brand, lot/batch number, expiry date, purchase location and date, photos, sample retained status, illness symptoms and onset time (if applicable), number of persons affected.
- **Retention period:** GPSR Art. 20 reference — complaint records involving serious risk must be retained for 5 years.

### Escalation Triggers (field values that require immediate escalation)

- `outcome_severity` includes Hatari ya maisha OR Kifo — Immediate emergency escalation to health authorities and TBS; preserve product; notify manufacturer
- `issue_type = food_poisoning_illness` AND `number_of_persons_affected > 2` — Potential outbreak; activate public health authority alert (municipal health office, Ministry of Health); batch recall investigation
- `issue_type = foreign_object_found` AND `foreign_object_description` includes metal / glass / needle / blade — Product safety emergency; TBS notification; manufacturer must initiate recall assessment
- `packaging_damage_type = Bloated` AND canned product — Suspect botulism; immediate health authority notification; advise consumer not to consume or open product further
- `issue_type = allergen_not_declared` AND `allergic_reaction_severity = Anaphylaxis` — Medical emergency; advise immediate emergency services; report to TBS within 24 hours; manufacturer notification
- `issue_type = food_poisoning_illness` AND `hospital_admission_number` is present (child hospitalized) — Highest priority escalation; TBS notification within 24 hours; mass recall assessment
- `issue_type = tampered_packaging` — Report to TBS; possible criminal tampering; preserve packaging and chain of custody
- `issue_type = counterfeit_food_product` — Report to TBS and TRA; potential public health risk from unregulated production
- `number_of_persons_affected > 10` from a single batch/event — Mass food poisoning; immediate multi-agency escalation (TBS, Ministry of Health, municipal authority)

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina la mtoa maoni (hiari) | Optional | ISO 10002:2018 permits anonymous feedback |
| contact_details | Mawasiliano (hiari) | Optional | For follow-up or acknowledgement |
| suggestion_category | Kategoria ya mapendekezo | Yes | Routes to correct team (product / labeling / packaging / distribution) |
| specific_product_or_brand | Bidhaa au chapa inayohusika | Recommended | Enables specific product team routing |
| suggestion_detail | Maelezo ya mapendekezo | Yes | Core content of the suggestion |
| target_consumer_group | Kundi la walaji wanaohusika | Optional | e.g., watoto / wazee / watu wenye kisukari / walaji wa halal — enables demographic-targeted product development |
| channel_submitted | Njia ya kuwasilisha | Auto | Omnichannel analytics |

### Industry-Specific Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| FS-01 | product_recipe_improvement | Boresha ladha / muundo wa bidhaa |
| FS-02 | nutritional_improvement | Boresha lishe (punguza sukari, chumvi, mafuta) |
| FS-03 | packaging_improvement | Boresha ufungaji (ukubwa, urahisi, mazingira) |
| FS-04 | labeling_improvement | Boresha lebo (lugha ya Kiswahili, allergens, tarehe) |
| FS-05 | halal_kosher_certification | Ombi la cheti cha halal / kosher |
| FS-06 | allergen_free_version | Ombi la bidhaa bila allergen |
| FS-07 | local_sourcing | Tumia malighafi za ndani / za Tanzania |
| FS-08 | distribution_expansion | Peleka bidhaa mikoa / maeneo ya vijijini |
| FS-09 | price_affordability | Punguza bei / ongeza ukubwa wa pakiti ndogo |
| FS-10 | environmental_sustainability | Punguza plastiki / ongeza ufungaji unaoweza kurejeshwa |
| FS-11 | restaurant_menu_improvement | Boresha menyu (chaguo, lishe, ubunifu) |
| FS-12 | traceability_transparency | Ongeza QR code / taarifa za asili ya chakula |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina la mwulizaji | Recommended | Personalizes response; enables follow-up |
| product_name_or_category | Jina la bidhaa au kategoria | Yes | Routes inquiry to correct product knowledge base |
| query_type | Aina ya swali | Yes | Determines answer pathway |
| preferred_response_format | Jinsi unavyotaka jibu | Recommended | SMS / WhatsApp / Simu / Barua pepe |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| ingredient_query | Swali la viungo / viambajengo | product_name, specific_concern (allergen, additive, origin) |
| allergen_status | Je, bidhaa ina allergen fulani? | product_name, allergen_type_of_concern |
| halal_certification | Uthibitisho wa halal | product_name, brand_name |
| expiry_interpretation | Maana ya tarehe ya bidhaa | product_name, date_shown_on_pack |
| storage_guidance | Jinsi ya kuhifadhi bidhaa | product_name, storage_condition_question |
| recall_status | Je, bidhaa hii inaombwa kurudishwa? | product_name, batch_or_lot_number |
| complaint_reporting_process | Jinsi ya kutoa taarifa ya tatizo | product_name, issue_type_overview |
| tbs_registration_status | Je, bidhaa hii imesajiliwa TBS? | product_name, brand_name |
| country_of_origin | Nchi ya utengenezaji | product_name, brand_name |
| restaurant_hygiene_certification | Je, mgahawa una cheti cha afya? | restaurant_name_location |
| catering_inquiry | Ombi la huduma ya chakula / catering | event_type, number_of_guests, date_required |
| nutritional_information | Taarifa za lishe | product_name, specific_nutrient_question |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina la mtoa pongezi (hiari) | Optional | For acknowledgement and recognition |
| product_or_restaurant_name | Jina la bidhaa au mgahawa | Yes | Routes compliment to correct brand/product team or restaurant management |
| specific_product_or_dish_praised | Bidhaa au sahani iliyopongezwa | Yes | Product team feedback loop; identifies high-performing products |
| aspect_praised | Kipengele kilichotukuka | Yes | Options: Ladha / Ubora / Ufungaji / Thamani / Usafi / Huduma / Uwasilishaji |
| staff_name_recognized | Jina la mfanyakazi anayetambuliwa (mgahawa) | Optional | For staff recognition schemes in food service |
| date_of_positive_experience | Tarehe ya uzoefu mzuri | Recommended | Correlates with production batch or kitchen shift |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Structured satisfaction metric |
| free_text_commendation | Maneno ya pongezi (hiari) | Optional | Open narrative for nuance |

---

## AI Conversation Guidance for This Industry

- **Prioritize illness safety above all other data collection.** If the customer says they got sick, immediately ask "Je, uko salama sasa hivi? Je, unahitaji msaada wa daktari?" and only after confirming safety proceed to collect evidence fields. A consumer in medical distress must be referred to emergency services before you collect batch numbers.
- **Ask for the batch/lot number by referencing the packaging in plain language.** Do not say "batch number" or "lot number" as those are technical terms most consumers do not know. Instead say: "Kwenye pakiti ya bidhaa, kawaida kuna nambari ndogo iliyochapishwa — mara nyingi karibu na tarehe ya kumalizika. Je, unaweza kuniambia nambari hiyo?" Frame it as a simple observation task, not a technical requirement.
- **Ask how many people ate the same food before asking about symptoms.** This is the fastest way to assess outbreak risk. If the answer is more than one person and multiple are ill, immediately flag as a potential outbreak and advise TBS notification.
- **For restaurant complaints about illness, always ask about the time between eating and first symptoms.** This field (onset time) is the most clinically valuable data point and most consumers can answer it. A lag of under 6 hours suggests Staph aureus or chemical contamination; over 24 hours suggests Salmonella or Campylobacter. This context shapes escalation urgency.
- **Do not ask customers to open or further disturb a suspect product.** If a bloated can, broken seal, or contaminated product is being described, advise the customer to set it aside without opening it further and that it may need to be collected for testing. Preserving the sample is more valuable than satisfying curiosity.
- **For halal or allergen inquiries, confirm the exact concern before answering.** "Ina halal" and "ina cheti cha halal" are different questions — the first is about ingredients, the second about formal certification. Clarify which the customer needs before providing information.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Product name and brand | "Bidhaa gani hasa unayozungumzia — jina lake na chapa yake?" |
| Batch / lot number | "Kwenye pakiti, karibu na tarehe ya kumalizika, kuna nambari ndogo. Je, unaweza kuniambia inasema nini?" |
| Expiry date | "Tarehe ya kumalizika iliyoandikwa kwenye bidhaa ni ipi?" |
| Purchase location | "Ulinunua bidhaa hii wapi hasa — jina la duka na mahali?" |
| Purchase date | "Ulinunua bidhaa hii lini?" |
| Symptom description | "Ulianza kuhisi nini hasa — eleza dalili zako kwa undani." |
| Symptom onset time | "Ulikula chakula / ukatumia bidhaa hiyo saa ngapi, na dalili zilianza saa ngapi?" |
| Number of persons affected | "Je, mtu mwingine yeyote alikula chakula hicho hicho? Wameathirika pia?" |
| Sample retained | "Je, bado una bidhaa hiyo au sehemu yake — pakiti, kitu kilichopatikana, au kilichobaki? Tafadhali usitupe — kinaweza kuhitajika kwa uchunguzi." |
| TBS mark | "Je, kwenye pakiti ya bidhaa kuna alama ya almasi ndogo inayoonyesha 'TBS' — je, ipo?" |
| Medical attention | "Je, umekwenda kwa daktari au hospitalini kwa sababu ya tatizo hili?" |
| Desired resolution | "Unataka nini kutokea — kurudishiwa pesa, kubadilishiwa bidhaa, au hatua nyingine?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| outcome_severity | Hatari ya maisha OR Kifo | Immediate emergency escalation; notify TBS within 24 hours; contact manufacturer; advise family to call emergency services if not already done |
| number_of_persons_affected | > 2 AND issue_type = food_poisoning_illness | Treat as potential outbreak; activate municipal health authority and TBS notification; request batch number urgently |
| foreign_object_description | Metal OR glass OR needle OR blade | Product safety emergency; TBS notification required; advise consumer to retain sample; initiate manufacturer contact for recall assessment |
| packaging_damage_type | Bloated AND product is canned | Suspect botulism; advise consumer not to open or consume; immediate TBS and health authority notification |
| allergen_type present AND allergic_reaction_severity | Anaphylaxis | Medical emergency — direct to emergency services immediately; report to TBS within 24 hours; document as serious adverse event |
| issue_type | expired_product_sold AND purchase_location confirmed | Document store name and batch; report to TBS for market inspection; advise consumer on refund rights |
| sample_retained | Ndiyo | Advise consumer to keep in original packaging, in a secure location; TBS or manufacturer may request collection |
| sample_retained | Hapana AND foreign_object_found | Advise consumer to photograph any remnants; still file report — photos are secondary evidence |
| issue_type | halal_certification_query AND claimed_certification appears unverified | Route to BAKWATA or relevant halal certification authority for verification; do not confirm or deny without checking |
| tbs_mark_or_registration | Hapana AND product is in TBS-regulated category | Flag as potential TBS standards violation; report to TBS with full product details |
| issue_type | food_poisoning_illness AND whether_tbs_notified = Hapana | Advise consumer to contact TBS: complaints@tbs.go.tz / 0800110827; create internal escalation record |
| number_of_persons_affected | > 10 from single batch or event | Multi-agency escalation: TBS + Ministry of Health + municipal health authority; treat as mass food poisoning event |

---

*Sources: EU General Food Law Regulation (EC) No 178/2002 (Arts. 17–19), FDA CFSAN CAERS / Form FDA 3500B, USDA FSIS Electronic Consumer Complaint Form, Tanzania Bureau of Standards (TBS) food safety mandate (Finance Act No. 8 of 2019), Tanzania Medicines and Medical Devices Authority (TMDA), ISO 10002:2018 (clauses 8.2, Annex C), ISO 22000 / HACCP framework, EU Implementing Regulation (EC) No 931/2011*
