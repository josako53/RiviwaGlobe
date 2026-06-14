---
tags: [industry-kb, field-standards, feedback-fields]
---
# Retail / Consumer Products — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: supermarket, duka, retail chain, wholesale, online marketplace, branded goods, consumer products, general merchandise, clothing store, furniture shop, hardware shop, e-commerce, hypermarket, convenience store, kiosk, Shoprite, Carrefour, Game Store, Pick n Pay, TBS standards mark, barcode, SKU, shelf display, receipt, return policy, warranty card, counterfeit goods, after-sales, loyalty card, shopping cart, point-of-sale, stock clearance, import duty, distributor, reseller, stockist, delivery rider, wrong item delivered, price discrepancy, overcharged, refund, product defect, bidhaa, duka la rejareja, supermarket, kurudisha bidhaa, risiti, bei ya bidhaa, bidhaa bandia, udhamini, uwasilishaji, malipo ya M-Pesa mfanyabiashara

## Why Industry-Specific Fields Matter

Generic feedback fields cannot distinguish a counterfeit goods complaint (requiring batch number, TBS mark verification, and importer details) from a return dispute (requiring purchase date, receipt number, and policy evidence) — both of which have different regulatory paths under Tanzania's Consumer Protection framework and different evidentiary requirements for TBS, TRA, and dispute resolution. Without retail-specific fields, the AI cannot determine whether a complaint triggers a product safety recall, a pricing fraud investigation, or a standard customer service resolution.

## Source Standards

- ISO 10002:2018 — Quality management: guidelines for complaints handling (clauses 8.2, Annex C)
- EU General Product Safety Regulation (GPSR) Regulation (EU) 2023/988 — Articles 9, 20, 35, 36 (product traceability and recall notification fields)
- Better Business Bureau (BBB) Consumer Complaint Form — confirmed field structure
- EU Online Dispute Resolution Regulation (EU) No 524/2013 — Annex (information to be provided); operative until 20 July 2025
- UK Consumer Rights Act 2015 — Which? complaint framework (s.9 satisfactory quality, s.11 as described)
- Tanzania Bureau of Standards (TBS) — consumer product certification mark requirements
- Tanzania Revenue Authority (TRA) — import duty and anti-counterfeit compliance
- East African Community (EAC) standards framework — conformity marks

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Required by ISO 10002:2018 clause 8.2 for complaint record; needed to open formal ticket and issue acknowledgement |
| complainant_phone_number | Nambari ya simu ya mlalamikaji | Yes | Primary contact for resolution updates; needed by BBB form and ISO 10002 preferred correspondence |
| complainant_email | Barua pepe ya mlalamikaji | Recommended | Required for written acknowledgement and document receipt; BBB and EU ODR require electronic address |
| product_name | Jina la bidhaa | Yes | ISO 10002:2018 Annex C and GPSR Art. 9 — complaint cannot be routed or investigated without identifying the product |
| product_brand | Chapa ya bidhaa | Yes | GPSR Art. 9 requires brand/trade name; enables routing to manufacturer vs. retailer |
| product_model_or_sku | Nambari ya mfano / SKU | Yes | GPSR Art. 9 mandates model number on product/packaging; primary identifier for warranty validation and stock tracing |
| batch_or_serial_number | Nambari ya kundi / serial | Recommended | GPSR Art. 9 and Art. 36 — batch/serial enables product recall linkage and unit-level investigation |
| purchase_date | Tarehe ya ununuzi | Yes | ISO 10002:2018 Annex C; Which? / CRA 2015 — statutory 30-day right to reject runs from purchase date; warranty start date |
| store_or_outlet_name | Jina la duka / tawi | Yes | ISO 10002:2018 (organizational unit); BBB form — identifies responsible retailer entity |
| receipt_or_order_number | Nambari ya risiti / agizo | Yes | BBB form and EU ODR Annex — proves transaction existence; links complaint to verifiable purchase record |
| amount_paid_tzs | Kiasi kilicholipwa (TZS) | Yes | BBB form requires monetary value; needed for refund calculation and fraud quantification |
| issue_type | Aina ya tatizo | Yes | ISO 10002:2018 (nature of complaint); determines investigation pathway, escalation trigger, and resolution SLA |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018 clause 8.2 mandatory field — "nature/description of the complaint" |
| date_issue_discovered | Tarehe tatizo liligunduliwa | Yes | CRA 2015 / Which? — statutory rights differ depending on time elapsed since purchase |
| product_returned | Je, bidhaa ilirudishwa? | Yes | BBB and EU ODR — return status determines available remedies (refund vs. replacement vs. repair) |
| warranty_status | Hali ya udhamini | Recommended | Which? (CRA 2015) — determines whether statutory or contractual warranty applies |
| evidence_photos_uploaded | Picha za ushahidi zilipakiwa | Recommended | GPSR Art. 36 and BBB supporting docs — visual evidence critical for product defect and safety claims |
| desired_resolution | Suluhisho unalotaka | Yes | ISO 10002:2018 Annex C, BBB, EU ODR — remedy sought by complainant; guides resolution offer |
| preferred_contact_method | Njia ya mawasiliano unayopendelea | Yes | ISO 10002:2018 — complainant must be kept informed of status. Options: SMS / Barua pepe / Simu / WhatsApp |

### Conditional Fields (collect based on issue type)

**If issue_type = defective_product OR not_as_described:**
Also collect:
- `defect_description_detailed` — Maelezo ya kina ya kasoro: Specific nature of defect; Which? CRA 2015 s.9 satisfactory quality test requires precise defect description
- `how_defect_manifested` — Jinsi kasoro ilivyojionyesha: e.g., broke on first use / stopped working / wrong color / wrong size — maps to CRA 2015 s.11 (as described) vs. s.9 (quality)
- `tbs_mark_present` — Je, alama ya TBS ipo kwenye bidhaa? (Ndiyo / Hapana / Sijui): TBS mark mandatory on regulated products sold in Tanzania; absence may constitute regulatory violation
- `is_safety_hazard` — Je, bidhaa ni hatari kwa usalama? (Ndiyo / Hapana): GPSR Art. 20 requires manufacturers to maintain an internal register of products posing serious risk; triggers mandatory escalation

**If issue_type = counterfeit_suspected:**
Also collect:
- `why_suspected_counterfeit` — Sababu ya kushuku kuwa ni bandia: Specific observable differences (packaging quality, missing marks, weight, smell)
- `where_purchased` — Mahali pa ununuzi (eneo, mtaa): TRA anti-counterfeit investigations require point-of-sale location
- `import_documentation_seen` — Je, uliona hati za uingizaji bidhaa? (Ndiyo / Hapana): For TRA duty and anti-counterfeit compliance
- `tbs_certificate_number` — Nambari ya cheti cha TBS (kama ipo): TBS diamond mark includes certificate number on compliant products

**If issue_type = price_discrepancy OR overcharged:**
Also collect:
- `shelf_price_shown_tzs` — Bei iliyoandikwa rafu (TZS): Documents the discrepancy between advertised and charged price
- `amount_charged_at_till_tzs` — Bei iliyolipwa kasani (TZS)
- `receipt_uploaded` — Je, risiti imepakiwa? (Ndiyo / Hapana): Receipt is primary evidence for pricing fraud claims
- `payment_method` — Njia ya malipo: M-Pesa / Airtel Money / Cash / Card; for payment tracing if mobile money dispute also exists

**If issue_type = delivery_problem:**
Also collect:
- `order_number` — Nambari ya agizo: Primary tracking identifier for e-commerce delivery complaints
- `expected_delivery_date` — Tarehe ya uwasilishaji iliyotarajiwa
- `actual_delivery_date_or_status` — Tarehe halisi ya uwasilishaji / hali ya sasa
- `delivery_provider` — Mtoa huduma wa uwasilishaji: Determines whether complaint routes to retailer or third-party logistics
- `delivery_damage_description` — Maelezo ya uharibifu wa uwasilishaji: For insurance and carrier claims

**If issue_type = return_refused OR warranty_denied:**
Also collect:
- `days_since_purchase` — Siku zimepita tangu ununuzi: CRA 2015 30-day rejection window is critical; BBB and EU ODR track this
- `return_policy_communicated` — Je, sera ya kurudisha ilielekezwa? (Ndiyo / Hapana / Sijui): Documents whether customer was informed of policy before purchase
- `reason_given_for_refusal` — Sababu waliyotoa ya kukataa: Enables legal/policy assessment of refusal validity
- `prior_repair_attempts` — Je, bidhaa ilitengenezwa awali? (Ndiyo / Hapana): CRA 2015 — after one failed repair, consumer has right to reject

**If is_safety_hazard = Ndiyo (safety risk confirmed):**
Also collect:
- `nature_of_safety_risk` — Aina ya hatari ya usalama: e.g., fire risk / electrical short / toxic material / structural collapse
- `injury_occurred` — Je, kulidhuru mtu? (Ndiyo / Hapana): GPSR Art. 19/20 serious risk register; triggers mandatory regulator notification
- `injury_description` — Maelezo ya maumivu / jeraha: Required for GPSR Art. 20 complaint register and potential litigation
- `product_still_available` — Je, bidhaa bado ipo kwa ajili ya ukaguzi? (Ndiyo / Hapana): Enables product sample collection for TBS testing

### Issue Type Classification

| Code | Issue Type | Swahili Description |
|------|-----------|---------------------|
| RT-01 | defective_product | Bidhaa yenye kasoro / haikufanya kazi |
| RT-02 | not_as_described | Bidhaa si kama ilivyoelezwa / picha |
| RT-03 | counterfeit_suspected | Bidhaa bandia inashukiwa |
| RT-04 | expired_product_sold | Bidhaa iliyoisha muda iliuzwa |
| RT-05 | price_discrepancy | Tofauti kati ya bei ya rafu na kasani |
| RT-06 | overcharged | Kulipishwa zaidi ya bei halisi |
| RT-07 | wrong_item_delivered | Bidhaa tofauti ilitumwa |
| RT-08 | missing_accessories | Vipande / vifaa vimekosekana kwenye sanduku |
| RT-09 | delivery_problem | Tatizo la uwasilishaji |
| RT-10 | delivery_damage | Bidhaa iliharibiwa wakati wa uwasilishaji |
| RT-11 | return_refused | Kurudisha kulikataliwa |
| RT-12 | warranty_denied | Madai ya udhamini yalikataliwa |
| RT-13 | refund_not_received | Kurudishiwa pesa kulishindwa / kukawia |
| RT-14 | staff_conduct | Tabia mbaya ya mfanyakazi |
| RT-15 | false_advertising | Matangazo ya udanganyifu |
| RT-16 | safety_hazard | Bidhaa ni hatari kwa usalama |
| RT-17 | payment_not_processed | Malipo hayakukamilika (M-Pesa, kadi) |
| RT-18 | stock_unavailability | Bidhaa haipatikani ingawa inaonekana mtandaoni |
| RT-19 | store_environment | Mazingira ya duka (usalama, usafi) |
| RT-20 | import_duty_evasion | Bidhaa iliyoingia bila ushuru / kinyume cha sheria |

### Resolution Standards for This Industry

- **Retailer level (Tanzania):** Consumer Protection Act requires merchants to acknowledge complaints; no statutory maximum resolution period is set nationally, but ISO 10002:2018 recommends 5 working days for acknowledgement and 30 days for resolution.
- **TBS escalation:** Products lacking TBS mark or failing TBS standards should be reported to TBS via complaints@tbs.go.tz or toll-free 0800110827. TBS can order product seizure and market withdrawal.
- **TRA anti-counterfeit escalation:** Counterfeit or duty-evading goods should be reported to TRA Customs at the relevant entry point; TRA can order forfeiture and prosecution.
- **UK CRA 2015 reference standard:** 30-day right to full refund for faulty goods; after 30 days, one repair or replacement attempt before short-term right to reject at reduced price.
- **Required documentation for escalation:** Purchase receipt or bank statement, photos of defective product, TBS mark reference (or absence noted), product batch/serial number, description of defect and communication with retailer.
- **GPSR Art. 20 (EU reference):** Manufacturer internal serious-risk complaint register must be maintained for 5 years; complaints with safety risk trigger mandatory regulator notification.

### Escalation Triggers (field values that require immediate escalation)

- `is_safety_hazard = Ndiyo` AND `injury_occurred = Ndiyo` — Immediate escalation: safety incident report to TBS and relevant health authority within 24 hours; advise customer to preserve product for inspection
- `issue_type = counterfeit_suspected` AND `tbs_mark_present = Hapana` — Escalate to TBS consumer complaints unit and TRA anti-counterfeit division
- `issue_type = expired_product_sold` AND `illness_reported` — Food-adjacent retail: escalate to TBS and local health authority; treat as potential public health issue
- `issue_type = safety_hazard` AND `nature_of_safety_risk` includes fire / electrical / toxic — GPSR Art. 20 serious risk register trigger; notify regulator; initiate product recall inquiry
- `issue_type = payment_not_processed` AND `amount_paid_tzs > 500000` — High-value unresolved payment; escalate to retailer financial officer and, if M-Pesa, to Safaricom merchant dispute team
- `issue_type = store_environment` AND incident description mentions customer injury — Personal injury on premises; escalate to management and legal team; document incident formally
- `issue_type = counterfeit_suspected` AND multiple similar reports from same store — Pattern of trade in counterfeits; escalate to TRA and TBS with aggregate evidence

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina la mtoa maoni (hiari) | Optional | ISO 10002:2018 permits anonymous feedback |
| contact_details | Mawasiliano (hiari) | Optional | For follow-up or acknowledgement if submitter wishes |
| suggestion_category | Kategoria ya mapendekezo | Yes | Routes suggestion to correct team (product / operations / pricing / sustainability) |
| specific_product_or_service | Bidhaa au huduma inayohusika | Recommended | Enables specific team routing and benchmarking |
| suggestion_detail | Maelezo ya mapendekezo | Yes | Core content; ISO 10002:2018 clause 8.4 requires all feedback recorded |
| competitor_benchmark | Ulinganisho na washindani (hiari) | Optional | Provides market context; useful for product sourcing decisions |
| priority_rating | Kipaumbele (kwa mtoa maoni) | Recommended | Juu / Kati / Chini |
| channel_submitted | Njia ya kuwasilisha | Auto | Supports omnichannel analytics |

### Industry-Specific Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| RS-01 | product_range_expansion | Ongeza aina za bidhaa |
| RS-02 | local_product_sourcing | Ongeza bidhaa za Kitanzania |
| RS-03 | pricing_affordability | Punguza bei / ongeza ufahamu wa bei |
| RS-04 | payment_options | Ongeza njia za malipo (M-Pesa, mkopo, installment) |
| RS-05 | store_layout_navigation | Boresha mpangilio wa duka |
| RS-06 | delivery_improvement | Boresha huduma ya uwasilishaji |
| RS-07 | after_sales_service | Boresha huduma ya baada ya mauzo |
| RS-08 | environmental_sustainability | Punguza plastiki / ongeza urafiki wa mazingira |
| RS-09 | digital_experience | Boresha programu / tovuti / ununuzi wa mtandaoni |
| RS-10 | quality_standards | Boresha udhibiti wa ubora / angalia bidhaa bandia |
| RS-11 | accessibility | Upatikanaji kwa watu wenye ulemavu / wazee |
| RS-12 | loyalty_program | Ongeza / boresha programu ya uaminifu |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina la mwulizaji | Recommended | Personalizes response; enables follow-up |
| product_name_or_category | Jina la bidhaa au kategoria | Yes | Routes inquiry to correct product/department knowledge base |
| query_type | Aina ya swali | Yes | Determines answer pathway and team routing |
| order_or_receipt_number | Nambari ya agizo / risiti | Conditional | Required for order-specific queries (tracking, returns status) |
| preferred_response_format | Jinsi unavyotaka jibu | Recommended | SMS / WhatsApp / Simu / Barua pepe |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| product_availability | Upatikanaji wa bidhaa | product_name_or_category, preferred_branch_location |
| product_authenticity | Uthibitisho wa bidhaa (halisi au bandia) | product_name_or_category, where_seen_or_purchased |
| tbs_certification_status | Hali ya cheti cha TBS | product_name, brand_name |
| price_query | Swali la bei | product_name_or_category, preferred_branch_location |
| return_policy_query | Sera ya kurudisha bidhaa | product_category, days_since_purchase |
| warranty_query | Maswali ya udhamini | product_name, purchase_date, model_number |
| delivery_tracking | Kufuatilia uwasilishaji | order_or_receipt_number |
| payment_options | Njia za malipo / mkopo | product_category, estimated_budget_tzs |
| stock_restock_eta | Lini bidhaa itarudi stokuni | product_name_or_category |
| import_documentation | Hati za uingizaji bidhaa | product_name, brand_name |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina la mtoa pongezi (hiari) | Optional | For acknowledgement and recognition schemes |
| store_or_outlet_name | Jina la duka / tawi | Yes | Routes compliment to correct branch management |
| staff_name_recognized | Jina la mfanyakazi anayetambuliwa | Optional | Enables staff recognition and performance records |
| date_of_positive_experience | Tarehe ya uzoefu mzuri | Recommended | Correlates with staff shift records and management review |
| aspect_praised | Kipengele kilichotukuka | Yes | Guides routing: staff / product quality / delivery / after-sales / pricing |
| specific_product_or_service_praised | Bidhaa au huduma iliyopongezwa | Recommended | Product team feedback loop |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Structured satisfaction metric for analytics |
| free_text_commendation | Maneno ya pongezi (hiari) | Optional | Open narrative for nuance not captured by structured fields |

---

## AI Conversation Guidance for This Industry

- **Start with the product, not the problem.** Ask "Bidhaa gani unayozungumzia — jina la chapa na mfano?" before asking what went wrong. The product identity is the anchor for all subsequent routing decisions and regulatory checks.
- **Ask for the receipt number or order number early, but reassure the customer it is not mandatory.** Say "Kama una risiti au nambari ya agizo, itanisaidia sana — lakini kama huna, tutaendelea bila hiyo." Many customers fear complaints will be rejected without receipts; reassurance keeps them engaged.
- **For defect complaints, ask how long ago the purchase was made.** The 30-day window (CRA 2015 reference / best practice) determines whether the customer has a strong refund claim or whether repair/replacement is the appropriate remedy. Do not ask about this in a legalistic way — simply ask "Ulinunua bidhaa hii lini hasa?" and calculate silently.
- **For safety hazards (fire, electrical, toxic), stop collecting other fields and escalate immediately.** Tell the customer "Hii ni hali ya haraka ya usalama — tafadhali acha kutumia bidhaa hii mara moja" before proceeding to document the incident. Safety first, data collection second.
- **Do not ask for batch numbers or TBS certificate numbers directly unless the complaint involves counterfeit or regulatory issues.** For a simple defect complaint, asking for a batch number feels bureaucratic. Instead ask "Je, kuna nambari yoyote iliyoandikwa kwenye pakiti au chini ya bidhaa?" and let the customer report what they see.
- **For delivery complaints, get the order number before asking about what went wrong.** The order number unlocks all other contextual data (expected date, carrier, contents) and avoids asking the customer to repeat information that is already in the system.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Product name and brand | "Bidhaa gani hasa unayozungumzia — jina la chapa na aina?" |
| Purchase date | "Ulinunua bidhaa hii lini — tarehe au wiki ngapi zilizopita?" |
| Store name | "Ulinunua dukani gani — jina la duka na mahali?" |
| Receipt or order number | "Je, una nambari ya risiti au agizo? Itanisaidia kupata maelezo haraka zaidi." |
| Amount paid | "Ulilipa kiasi gani kwa bidhaa hii?" |
| Nature of defect | "Kasoro au tatizo ni nini hasa — eleza kwa undani kadri uwezavyo." |
| TBS mark | "Je, bidhaa hii ina alama ya TBS (almasi ndogo ya ubora) kwenye pakiti au bidhaa yenyewe?" |
| Safety risk | "Je, bidhaa hii ilisababisha hatari yoyote — moto, mkondo wa umeme, au kuumia?" |
| Return status | "Je, umeshajaribu kurudisha bidhaa hii dukani? Walikuambia nini?" |
| Desired resolution | "Unataka nini kutokea — kurudishiwa pesa, kubadilishiwa bidhaa, au kutengenezwa?" |
| Photo evidence | "Je, unaweza kupiga picha za bidhaa na kasoro yake na kuzituma hapa?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| is_safety_hazard | Ndiyo AND injury_occurred = Ndiyo | Immediate safety escalation; advise customer to stop use; notify TBS and health authority within 24 hours; preserve product for inspection |
| issue_type | counterfeit_suspected AND tbs_mark_present = Hapana | Report to TBS (complaints@tbs.go.tz, 0800110827) and TRA anti-counterfeit; document product details and purchase location |
| issue_type | expired_product_sold | Advise customer to preserve product; report to TBS if illness suspected; request store to check and pull remaining stock |
| days_since_purchase | <= 30 days AND issue_type = defective_product | Advise customer of strong refund right; provide retailer's return policy reference; escalate if retailer refuses |
| days_since_purchase | > 30 days AND issue_type = defective_product | Advise repair or replacement as primary remedy; document warranty status |
| issue_type | refund_not_received AND amount_paid_tzs > 200000 | Escalate to retailer financial officer; set 5-day resolution deadline; flag for follow-up |
| payment_method | M-Pesa AND issue_type = payment_not_processed | Advise customer to check M-Pesa statement; request transaction reference; route to retailer merchant dispute team and Safaricom M-Pesa support |
| issue_type | staff_conduct AND description includes assault or harassment | Immediate escalation to branch manager and HR; document incident with date, time, and staff description |
| tbs_mark_present | Hapana AND product is in regulated category | Flag as potential TBS standards violation; collect full product details for TBS complaint |
| desired_resolution | Kurudishiwa pesa (refund) | Confirm receipt availability; calculate days since purchase; advise on applicable policy; route to returns team |
| issue_type | false_advertising AND multiple complainants | Aggregate reports; escalate to Fair Competition Commission (FCC) Tanzania if pattern confirmed |

---

*Sources: ISO 10002:2018 (clauses 8.2, Annex C), EU GPSR Regulation (EU) 2023/988 (Arts. 9, 20, 35, 36), BBB Consumer Complaint Form, EU ODR Regulation (EU) No 524/2013 (Annex), UK Consumer Rights Act 2015 via Which? complaint framework, Tanzania Bureau of Standards (TBS) consumer complaints mandate, Tanzania Revenue Authority (TRA) anti-counterfeit framework*
