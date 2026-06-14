---
tags: [industry-kb, field-standards, feedback-fields, agriculture, agribusiness]
---
# Agriculture / Agribusiness — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: kilimo, agriculture, mkulima, farmer, mazao, crops, harvest, mavuno, seeds, mbegu, fertilizer, mbolea, pesticide, dawa ya wadudu, irrigation, umwagiliaji, agronomy, kilimo bora, contract farming, kilimo cha mkataba, cooperative, ushirika, AMCOS, SACCOS, agricultural marketing, masoko ya kilimo, agro-dealer, muuzaji wa vifaa vya kilimo, extension officer, afisa kilimo, Ministry of Agriculture, Wizara ya Kilimo, MAFC, TOSCI, Tanzania Official Seed Certification Institute, TPRI, Tropical Pesticides Research Institute, land lease, kukodisha ardhi, irrigation scheme, skimu ya umwagiliaji, ASDP, value chain, mnyororo wa thamani, post-harvest, baada ya mavuno, storage, uhifadhi, crop insurance, bima ya mazao, coffee, kahawa, tea, chai, cotton, pamba, rice, mchele, maize, mahindi, cashew, korosho, sisal, katani, sunflower, alizeti, horticulture, mboga mboga, livestock, mifugo, TALIRI, TARI, Tanzania Agriculture Research Institute, extension services, huduma za ugani, input supply, rasilimali za kilimo

## Why Industry-Specific Fields Matter

Agricultural complaints span counterfeit seeds/pesticides (requiring TOSCI certification check), extension service failures (requiring district extension office reference), contract farming disputes (requiring contract reference, offtaker name), irrigation scheme failures (requiring scheme name and LGA authority), and crop insurance claims (requiring policy number and yield assessment). Without agriculture-specific fields, the AI cannot route to TOSCI for seed quality issues, TPRI for pesticide concerns, or the district extension network for agronomy complaints.

## Source Standards

- Tanzania Seeds Act, Cap. 318 — seed certification (TOSCI)
- Plant Protection Act, Cap. 133 — pesticide registration and use (TPRI)
- Agricultural Inputs Act — fertilizer and input quality
- Agricultural Marketing Act, Cap. 384 — cooperative and market regulation
- Tanzania Crop Board regulations — specific crop boards (Coffee Board, Tea Board, Cotton Board, etc.)
- MAFC Extension Service standards
- ASDP (Agricultural Sector Development Programme) guidelines
- ISO 10002:2018 — complaints handling
- FAO Voluntary Guidelines on Responsible Governance of Tenure (VGGT) — land rights
- Codex Alimentarius — food safety for agricultural products
- OECD-FAO Agricultural Outlook — reference standards for commodity pricing

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL agriculture complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Complaint registration |
| complainant_phone | Nambari ya simu | Yes | Status updates |
| complainant_location | Wilaya / Kata / Kijiji | Yes | For district extension office routing and geographic analysis |
| farmer_category | Aina ya mkulima | Yes | Small-scale / Medium / Commercial / Cooperative — shapes rights and routing |
| agribusiness_type | Aina ya shughuli ya kilimo | Yes | Crops / Livestock / Horticulture / Aquaculture — determines advisory body |
| crop_or_product_type | Aina ya zao / bidhaa | Yes | Maize / Coffee / Cotton / Rice / Cashew / Vegetables etc. |
| input_supplier_name | Jina la muuzaji wa vifaa | Conditional | For input quality complaints |
| contract_reference | Nambari ya mkataba | Conditional | For contract farming disputes |
| issue_type | Aina ya tatizo | Yes | Complaint taxonomy |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; detailed narrative |
| season_affected | Msimu ulioathirika | Recommended | Long rains / Short rains / Year-round — for crop cycle context |
| area_affected_hectares | Eneo lililoathirika (hekta) | Conditional | For scale of loss and compensation quantification |
| estimated_loss_tzs | Hasara ya kukadiriwa (TZS) | Conditional | For compensation claim |
| evidence_available | Ushahidi unaopatikana | Recommended | Failed crop samples / Photos / Receipts / Test results |
| desired_outcome | Matokeo unayotaka | Yes | Compensation / Replacement inputs / Investigation / Extension support |

### Conditional Fields (collect based on issue type)

**If issue_type = Counterfeit / Substandard Seeds or Fertilizer:**
Also collect:
- `product_name_and_brand` — Jina la bidhaa na chapa: For TOSCI/TPRI lookup
- `batch_lot_number` — Nambari ya kundi (batch number): Critical for TOSCI traceability
- `tosci_certification_mark` — Je, mbegu zina alama ya TOSCI? Yes / No: Required for certified seeds
- `purchase_date_and_location` — Tarehe na mahali pa ununuzi
- `germination_rate_observed` — Kiwango cha kuota kilichoona (asilimia): Expected vs. actual germination rate
- `samples_available` — Je, sampuli zinapatikana?: TOSCI laboratory testing

**If issue_type = Contract Farming Dispute:**
Also collect:
- `offtaker_company_name` — Jina la kampuni inayonunua mazao
- `contracted_quantity_kg` — Kiasi kilichomkatabiwa (kg)
- `actual_quantity_delivered_kg` — Kiasi kilichowasilishwa (kg)
- `price_agreed_per_kg_tzs` — Bei iliyokubaliwa kwa kilo (TZS)
- `price_paid_per_kg_tzs` — Bei iliyolipwa kwa kilo (TZS)
- `quality_grade_disputed` — Je, daraja la ubora linabishaniwa? Yes / No
- `inputs_provided_by_offtaker` — Vifaa vilivyotolewa na mzabuni: Seeds / Fertilizer / Credit — affects deductions

**If issue_type = Irrigation Scheme Failure:**
Also collect:
- `scheme_name` — Jina la skimu ya umwagiliaji
- `managing_authority` — Mamlaka inayosimamia: LGA / WUA (Water User Association) / Private
- `water_shortage_duration` — Muda wa upungufu wa maji (siku / majuma)
- `crops_affected` — Mazao yaliyoathirika
- `scheme_infrastructure_issue` — Tatizo la miundombinu: Broken pump / Canal blockage / Canal breach / No maintenance

**If issue_type = Extension Service Failure:**
Also collect:
- `extension_officer_name` — Jina la afisa kilimo
- `district_extension_office` — Ofisi ya kilimo ya wilaya
- `service_type_requested` — Huduma iliyoombwa: Soil testing / Pest control advice / Variety selection / Market linkage
- `last_visit_date` — Tarehe ya ziara ya mwisho ya afisa kilimo

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| AG-01 | counterfeit_seeds | Seeds fail to germinate; suspected fake or substandard |
| AG-02 | counterfeit_fertilizer | Fertilizer shows no effect; suspected substandard |
| AG-03 | counterfeit_pesticide | Pesticide fails; suspected fake or ineffective |
| AG-04 | contract_farming_dispute | Offtaker underpays, rejects quality, or doesn't collect |
| AG-05 | irrigation_failure | Irrigation scheme not providing adequate water |
| AG-06 | market_access_failure | Inability to access fair market prices |
| AG-07 | extension_failure | Extension services not provided or poor quality |
| AG-08 | crop_insurance_dispute | Insurance claim rejected or underpaid |
| AG-09 | land_dispute_farming | Land dispute affecting farming operations |
| AG-10 | cooperative_fraud | Cooperative mismanaging member funds |
| AG-11 | storage_facility_failure | Government or cooperative storage failure causing loss |
| AG-12 | input_overcharge | Subsidized inputs overcharged by agro-dealer |
| AG-13 | crop_board_dispute | Crop board pricing, payment, or certification dispute |
| AG-14 | animal_disease | Livestock disease or poor veterinary services |
| AG-15 | environmental_damage | Chemical drift, water contamination from agriculture |

### Resolution Standards

- **Input supplier level:** Replace failed inputs or compensate within 30 days.
- **TOSCI:** Seed quality complaints; inspection within 14 days; market withdrawal if substandard.
- **TPRI:** Pesticide quality; investigation within 30 days.
- **District Agriculture Office (DAO):** Extension service and input complaints; response within 21 days.
- **Specific Crop Boards (Coffee, Tea, Cotton, etc.):** Price and quality disputes; board mediation within 30 days.
- **Contract farming disputes:** MAFC mediation; civil court for significant value claims.
- **Crop insurance:** TIRA framework; insurance-specific timelines (30–60 days for assessment).

### Escalation Triggers

- `issue_type = counterfeit_seeds` AND `area_affected_hectares > 5` — TOSCI emergency investigation; market withdrawal; significant livelihood impact
- `issue_type = pesticide` AND environmental or health damage — TPRI + NEMC + MOHCDGEC immediate; potential criminal matter
- `issue_type = cooperative_fraud` AND significant funds — MAFC cooperative audit; PCCB referral; criminal matter
- `issue_type = irrigation_failure` AND large-scale crop loss — LGA and Ministry of Water escalation; livelihoods at risk
- `issue_type = contract_farming_dispute` AND systemic — MAFC intervention; crop board review
- `issue_type = crop_insurance_dispute` AND TIRA referral — TIRA consumer protection complaint; insurance-specific timeline

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| location | Wilaya / Kata | Recommended | Geographic routing |
| agribusiness_type | Aina ya kilimo | Yes | Routes to correct advisory team |
| suggestion_category | Kategoria | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| AGS-01 | input_quality | Ubora wa mbegu, mbolea, na dawa |
| AGS-02 | extension_services | Huduma bora za ugani |
| AGS-03 | market_linkage | Uhusiano bora na masoko |
| AGS-04 | irrigation | Miundombinu bora ya umwagiliaji |
| AGS-05 | credit_access | Mikopo nafuu kwa wakulima |
| AGS-06 | storage | Ghala bora za uhifadhi wa mazao |
| AGS-07 | digital_agriculture | Teknolojia ya kidijitali kwa kilimo |
| AGS-08 | climate_resilience | Kilimo kinachostahimili mabadiliko ya hali ya hewa |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina | Recommended | For tracking |
| location | Wilaya | Recommended | For location-specific advice |
| crop_type | Aina ya zao | Conditional | For crop-specific queries |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| seed_certification | Je, mbegu hizi zimehakikiwa TOSCI? | seed_name, supplier |
| fertilizer_type | Mbolea gani ifaa kwa zao hili? | crop_type, soil_type |
| pest_identification | Wadudu hawa ni gani? | crop_type, location |
| market_price | Bei ya soko ya [zao] ni ngapi? | crop_type, location |
| extension_contact | Afisa kilimo wa wilaya yangu yuko wapi? | district |
| cooperative_registration | Jinsi ya kusajili ushirika? | location, cooperative_type |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| provider_name | Mtoa huduma | Yes | Routes to management |
| service_type | Aina ya huduma | Yes | For routing |
| specific_aspect_praised | Kipengele | Yes | Mbegu bora / Mbolea nzuri / Ugani bora / Bei ya haki / Mkopo rahisi |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Agribusiness service quality benchmarking |

---

## AI Conversation Guidance for This Industry

- **Identify the crop and input type first.** "Zao gani linahusika? Na ni tatizo la mbegu, mbolea, dawa, mkataba, au kitu kingine?" — this determines the regulatory body (TOSCI for seeds, TPRI for pesticides, crop board for pricing).
- **For failed seeds, ask about the germination rate.** "Mbegu hizi ziliota kwa asilimia ngapi unaokadiriwa? Na uliamini zitaota kwa asilimia ngapi?" — the gap quantifies the failure.
- **Always ask about the batch/lot number for input complaints.** "Nambari ya kundi (batch/lot number) ya mbegu au mbolea inaonekana kwenye mfuko — je, unaweza kuisoma?" — critical for TOSCI/TPRI traceability.
- **For contract farming disputes, get the signed contract.** "Je, mkataba wa kilimo uliandikwa na kusainiwa na pande zote mbili? Bei iliyokubaliwa ilikuwa ngapi kwa kilo?"
- **Acknowledge the livelihood impact.** Farming is not just an economic activity; for many Tanzanians it is their only income source. "Tunakuelewa hali hii ina athari kubwa kwa maisha yako — tutahakikisha tatizo lako linashughulikiwa haraka iwezekanavyo."
- **For market price complaints, provide crop board reference.** Coffee, cotton, tea, and cashew prices are set by their respective boards — the AI should reference these rather than expressing an opinion on price fairness.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Crop type | "Zao gani linahusika — mahindi, mchele, kahawa, pamba, korosho, au nyingine?" |
| Input type | "Tatizo ni la mbegu, mbolea, dawa ya wadudu, au kitu kingine?" |
| Batch number | "Nambari ya kundi kwenye mfuko wa mbegu / mbolea / dawa inaonekana wapi? Inasema nini?" |
| Germination rate | "Mbegu hizi ziliota — asilimia ngapi ya mbegu iliyopandwa iliota?" |
| Area affected | "Eneo lililoathirika ni hekta ngapi? Na hasara ya kukadiriwa ni kiasi gani?" |
| Contract reference | "Mkataba wa kilimo cha mkataba una nambari ya marejeleo — je, una nambari hiyo?" |
| Price dispute | "Bei iliyokubaliwa kwenye mkataba ilikuwa kiasi gani kwa kilo? Na ulilipwa kiasi gani?" |
| Evidence | "Je, una sampuli za mbegu / mazao yaliyoshindwa, picha, au risiti za ununuzi?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | counterfeit_seeds AND area > 5 hectares | TOSCI emergency investigation; market withdrawal; livelihood support alert |
| issue_type | counterfeit_pesticide AND health/environmental damage | TPRI + NEMC + MOHCDGEC immediate; criminal referral |
| issue_type | cooperative_fraud | MAFC cooperative audit + PCCB criminal referral |
| issue_type | contract_farming_dispute AND systemic | MAFC mediation + relevant crop board review |
| issue_type | irrigation_failure AND large-scale loss | LGA + Ministry of Water escalation; livelihoods at risk |
| issue_type | crop_insurance_dispute | TIRA consumer protection complaint; insurance claim review |
| tosci_certification | No certification mark AND seed failed | TOSCI enforcement; market withdrawal; compensation from supplier |
| estimated_loss_tzs | significant AND verifiable | Legal aid referral for compensation claim; crop board mediation |

---

*Sources: Tanzania Seeds Act Cap. 318, Plant Protection Act Cap. 133, Agricultural Marketing Act Cap. 384, TOSCI regulations, TPRI Act, TIRA Act Cap. 394, MAFC extension guidelines, ISO 10002:2018, FAO VGGT, Codex Alimentarius*
