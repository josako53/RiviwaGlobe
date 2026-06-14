---
tags: [industry-kb, field-standards, feedback-fields, retail, consumer-products]
---
# Retail / Consumer Products — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: duka, shop, store, supermarket, retail outlet, bidhaa za watumiaji, consumer products, product, bidhaa, purchase, ununuzi, receipt, risiti, refund, kurudisha pesa, return, kurudisha bidhaa, exchange, kubadilishana bidhaa, warranty, udhamini, defective, hitilafu, counterfeit, fake, bidhaa bandia, price, bei, overcharge, overpriced, price tag, etiketi ya bei, customer service, huduma ya wateja, cashier, kashe, POS, point of sale, till, shelf, rafu, stock, hisa, out of stock, bidhaa hazipo, delivery, uwasilishaji, online shopping, ununuzi wa mtandao, Jumia, Kilimall, e-commerce, mall, Mlimani City, Quality Centre, Game, Shoprite, Nakumatt, Uchumi, TCRA, TFDA, TBS, Tanzania Bureau of Standards, bar code, expiry date, muda wa kuisha, MBS, weights and measures, vipimo, consumer protection, ulinzi wa watumiaji, Consumer Consultative Council, CCC

## Why Industry-Specific Fields Matter

Retail complaints span product defects (requiring product name, batch, purchase date, receipt), billing errors (requiring POS transaction reference, amount charged vs. amount displayed), counterfeit goods (requiring TFDA/TBS report), and return/refund disputes (requiring store return policy reference). Without retail-specific fields, the AI cannot determine whether the issue is a consumer protection violation under Tanzania's fair trade laws, a TFDA product safety matter, or a TBS standards violation — each requiring a different regulatory escalation.

## Source Standards

- Tanzania Fair Competition Act, Cap. 285 — consumer protection and fair trade
- Fair Competition Commission (FCC) of Tanzania — consumer complaints
- Tanzania Consumer Consultative Council (CCC) Act
- Tanzania Bureau of Standards (TBS) Act, Cap. 130 — product standards and quality marks
- Tanzania Food and Drugs Authority (TFDA) — food, drug, and cosmetic safety
- Weights and Measures Act, Cap. 340 — price accuracy and measurement standards
- TFDA Regulations on Labelling and Packaging 2014
- ISO 10002:2018 — complaints handling
- ISO 9001:2015 — quality management (retail QMS reference)
- UNECE Guidelines for Consumer Protection (revised 2015)

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL retail complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Consumer protection law requires complainant identification |
| complainant_phone | Nambari ya simu | Yes | For status updates |
| store_name | Jina la duka | Yes | Identifies regulated retailer; routes complaint |
| store_location | Mahali pa duka | Yes | Branch identification; geographic consumer protection enforcement |
| product_name | Jina la bidhaa | Yes | Core identifier for product complaints |
| product_brand | Chapa ya bidhaa | Recommended | For manufacturer accountability |
| product_category | Kategoria ya bidhaa | Yes | Electronics / Food / Clothing / Cosmetics / Household — determines regulatory body |
| purchase_date | Tarehe ya ununuzi | Yes | For warranty, return policy, and limitation period |
| purchase_amount_tzs | Kiasi kilicholipwa (TZS) | Yes | For refund calculation and overcharge quantification |
| receipt_available | Je, risiti inapatikana? | Yes | TBS and FCC require proof of purchase for most complaints |
| issue_type | Aina ya tatizo | Yes | FCC consumer complaint taxonomy |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; FCC requires detailed narrative |
| desired_outcome | Matokeo unayotaka | Yes | Refund / Exchange / Repair / Apology / Compensation |
| store_response_already_sought | Je, ulikwenda dukani awali? | Recommended | FCC requires prior attempt at resolution |

### Conditional Fields (collect based on issue type)

**If issue_type = Defective Product:**
Also collect:
- `product_model_number` — Nambari ya modeli ya bidhaa: For warranty verification
- `batch_or_serial_number` — Nambari ya kundi au msururu: For TBS/TFDA product traceability
- `defect_description` — Maelezo ya hitilafu: What specifically is wrong
- `defect_discovered_date` — Tarehe ya kugundua hitilafu: Within or after warranty period
- `photos_of_defect_available` — Je, picha za hitilafu zinapatikana?: Evidence for complaint
- `was_product_used` — Je, bidhaa ilitumika kabla ya hitilafu?: Affects warranty claim validity

**If issue_type = Counterfeit / Substandard Product:**
Also collect:
- `suspected_counterfeit_evidence` — Ushahidi wa tuhuma ya ulaghai: Packaging, label, color, smell, no TBS mark
- `tbs_mark_present` — Je, alama ya TBS ipo kwenye bidhaa?: Tanzania Bureau of Standards mark required on regulated products
- `country_of_origin_on_label` — Nchi ya asili iliyoandikwa kwenye lebo: For TFDA/TBS enforcement

**If issue_type = Price Dispute / Overcharge:**
Also collect:
- `price_displayed_tzs` — Bei iliyoonyeshwa kwenye bidhaa / rafu (TZS)
- `price_charged_tzs` — Bei iliyotozwa (TZS)
- `price_discrepancy_tzs` — Tofauti ya bei (TZS): Weights and Measures Act requires price as displayed
- `price_tag_photo_available` — Je, picha ya lebo ya bei inapatikana?: Critical evidence

**If issue_type = Return / Refund Refused:**
Also collect:
- `days_since_purchase` — Siku tangu ununuzi: Determines if within standard return window
- `store_return_policy_known` — Je, sera ya kurudisha bidhaa ya duka inajulikana?: For reference
- `product_condition` — Hali ya bidhaa: Sealed / Opened / Used / Damaged
- `reason_given_for_refusal` — Sababu ya kukataa kurudisha pesa

**If issue_type = Online Shopping Dispute:**
Also collect:
- `platform_name` — Jina la jukwaa la mtandao: Jumia / Kilimall / WhatsApp shop / Facebook shop
- `order_number` — Nambari ya agizo
- `delivery_date_promised` — Tarehe ya uwasilishaji iliyoahidiwa
- `delivery_date_actual` — Tarehe ya uwasilishaji halisi (au bado haujafika)
- `product_received_vs_ordered` — Bidhaa iliyopokelewa vs. iliyoagizwa: For wrong item complaints

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| RT-01 | defective_product | Product not functioning as expected; manufacturing defect |
| RT-02 | counterfeit_product | Suspected fake or substandard product |
| RT-03 | price_overcharge | Charged more than displayed price |
| RT-04 | refund_refused | Store refuses valid refund or exchange |
| RT-05 | expired_product | Product sold past expiry date |
| RT-06 | wrong_product | Received different product than ordered/selected |
| RT-07 | misleading_advertising | Product does not match advertisement |
| RT-08 | poor_customer_service | Rude, unhelpful, or discriminatory staff |
| RT-09 | warranty_dispute | Warranty claim refused or improperly handled |
| RT-10 | online_delivery_failure | Online order not delivered or significantly delayed |
| RT-11 | incorrect_weight_measure | Product weight or quantity less than labeled |
| RT-12 | unsafe_product | Product poses physical safety risk |
| RT-13 | hidden_charges | Undisclosed fees added at checkout |
| RT-14 | data_misuse | Customer data used without consent |
| RT-15 | loyalty_points_dispute | Loyalty points not credited or wrongly deducted |

### Resolution Standards

- **Store level:** Standard retail practice requires resolution attempt within 7 days; most consumer protection frameworks require exchange/refund within 30 days for defective products.
- **FCC (Fair Competition Commission):** Receives consumer complaints; investigation within 60 days. FCC can order refunds and impose penalties.
- **TBS (Tanzania Bureau of Standards):** Product quality and safety investigations; can order product recall.
- **TFDA:** Food, cosmetics, and drug-related product complaints; investigation within 30 days; serious safety issues within 72 hours.
- **Online platforms:** Most platforms (Jumia, Kilimall) have internal dispute resolution; escalation to platform then FCC.
- **Weights and Measures:** Inspector can verify pricing and measurement complaints on-site.

### Escalation Triggers

- `issue_type = unsafe_product` AND safety risk to consumers — Immediate TFDA or TBS product recall investigation
- `issue_type = counterfeit_product` AND tbs_mark_present = No — TBS enforcement complaint; potential criminal matter
- `issue_type = expired_product` AND food or medicine — TFDA immediate investigation
- `price_charged_tzs` significantly exceeds `price_displayed_tzs` AND systematic pattern — FCC price fixing investigation
- `issue_type = misleading_advertising` AND widespread — FCC Consumer Protection Unit; Tanzania Advertising Standards

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| store_name | Duka | Recommended | For routing |
| product_category | Kategoria ya bidhaa | Yes | Routes to buyer/category team |
| suggestion_category | Kategoria ya mapendekezo | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| RTS-01 | product_quality | Ubora bora wa bidhaa |
| RTS-02 | pricing_transparency | Uwazi wa bei |
| RTS-03 | return_policy | Sera ya kurudisha bidhaa ifupishe |
| RTS-04 | stock_availability | Bidhaa ziwe na uhakika wa upatikanaji |
| RTS-05 | staff_training | Mafunzo ya wafanyakazi |
| RTS-06 | loyalty_program | Mfumo bora wa tuzo za wateja |
| RTS-07 | online_shopping | Kuboresha ununuzi wa mtandao |
| RTS-08 | store_layout | Mpangilio bora wa duka |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina | Recommended | For tracking |
| store_name | Duka | Conditional | For store-specific queries |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| product_availability | Je, bidhaa X inapatikana? | product_name, store_location |
| price_check | Bei ya bidhaa hii ni ngapi? | product_name |
| return_policy | Sera ya kurudisha bidhaa ni ipi? | store_name, purchase_date |
| warranty_terms | Masharti ya udhamini | product_name, product_brand |
| tbs_mark_verification | Je, bidhaa hii ina alama ya TBS? | product_name, product_brand |
| online_order_status | Hali ya agizo langu la mtandao | order_number |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| staff_name | Jina la mfanyakazi | Recommended | Staff recognition |
| store_name | Duka | Yes | Routes to manager |
| specific_aspect_praised | Kipengele | Yes | Msaada / Ubora wa bidhaa / Bei nzuri / Haraka ya huduma |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | NPS / CSAT benchmarking |

---

## AI Conversation Guidance for This Industry

- **Get the store name and purchase date first.** These two fields determine whether the complaint is within the return window and which branch to route to. "Bidhaa hii ilinunuliwa dukani gani, na tarehe ya ununuzi ilikuwa lini?"
- **Ask about the receipt early.** The receipt is the foundation of most retail complaints. "Je, una risiti ya ununuzi? Bila risiti, mchakato wa kurudisha pesa au kubadilishana unaweza kuwa mgumu."
- **For food or cosmetics, ask about expiry date and batch number.** These trigger TFDA reporting requirements. "Tarehe ya kuisha muda inaonekana wapi kwenye bidhaa? Na nambari ya kundi (batch number)?"
- **For counterfeit complaints, ask about the TBS mark.** "Je, bidhaa hii ina alama ya TBS (Tanzania Bureau of Standards)? Alama hiyo ni muhimu kwa bidhaa nyingi zinazouzwa Tanzania."
- **For online shopping disputes, get the order number immediately.** Platforms can trace the entire delivery chain with an order number. "Agizo lako lina nambari ya marejeleo (order number) — inaweza kuonekana kwenye barua pepe ya uthibitisho."
- **Do not make legal determinations about warranty coverage.** Say "Masharti ya udhamini yanaamuliwa na muuzaji au mtengenezaji — tutapeleka tatizo lako kwao kwa ufumbuzi."

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Store name | "Duka au muuzaji anaitwa nini — na iko wapi?" |
| Product name | "Bidhaa inaitwa nini, na ni aina gani?" |
| Purchase date | "Ununuzi huu ulifanyika tarehe gani?" |
| Receipt | "Je, una risiti ya ununuzi? Risiti inasaidia sana katika mchakato wa kurudisha au kulipwa" |
| Defect description | "Tatizo au hitilafu ni nini hasa — eleza kwa undani" |
| Price displayed | "Bei iliyoandikwa kwenye bidhaa au rafu ilikuwa kiasi gani?" |
| Price charged | "Ulilipa kiasi gani halisi?" |
| TBS mark | "Je, bidhaa ina alama ya TBS au muhuri mwingine wa ubora?" |
| Desired outcome | "Unataka nini — kurudishiwa pesa, kubadilishana bidhaa, ukarabati, au kitu kingine?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | unsafe_product | Immediate TFDA or TBS product safety report; advise consumer to stop using product |
| issue_type | counterfeit_product AND tbs_mark = No | TBS enforcement complaint; criminal referral possible under TBS Act |
| issue_type | expired_product AND food or medicine | TFDA immediate report; store inspection request |
| price_charged vs price_displayed | significant discrepancy | Weights and Measures complaint; FCC consumer protection referral |
| issue_type | refund_refused AND within 30 days of purchase | Cite FCC Consumer Protection guidelines; recommend FCC complaint |
| issue_type | online_delivery_failure AND platform is Jumia/Kilimall | Platform dispute resolution first; then FCC escalation |
| product_category | Food / Medicine / Cosmetics | TFDA is the primary regulatory body; route accordingly |
| issue_type | misleading_advertising AND widespread | FCC Consumer Protection Unit + Tanzania Advertising Standards body |

---

*Sources: Tanzania Fair Competition Act Cap. 285, FCC Tanzania, TBS Act Cap. 130, TFDA Regulations, Weights and Measures Act Cap. 340, Consumer Consultative Council Act, ISO 10002:2018*
