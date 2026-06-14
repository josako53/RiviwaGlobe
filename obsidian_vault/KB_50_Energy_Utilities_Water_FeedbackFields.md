---
tags: [industry-kb, field-standards, feedback-fields, energy, utilities, water]
---
# Energy / Utilities / Water — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: TANESCO, DAWASCO, DAWASA, UWASA, EWURA, umeme, electricity, power, nguvu ya umeme, blackout, giza, load shedding, kupotea kwa umeme, meter, mita, prepaid meter, lipa nishati, token ya umeme, unit, bill, ankara ya umeme, transformer, transfoma, power line, cable, wiring, high voltage, voltage fluctuation, maji, water supply, maji ya bomba, water pipe, pampu, pump, burst pipe, bomba lililopasuka, water quality, ubora wa maji, turbid water, maji machafu, DAWASCO, DAWASA, RUWASA, Rural Water, water meter, mita ya maji, water bill, ankara ya maji, sewage, mfumo wa maji taka, solar, jua, generator, jenereta, gas, gesi, LPG, natural gas, TPDC, GASCO, gas leakage, mvujaji wa gesi, renewable energy, nishati mbadala, grid connection, kuunganishwa na gridi, disconnection, kukatwa umeme / maji, reconnection

## Why Industry-Specific Fields Matter

Utilities complaints include power outages (requiring meter number, transformer location, duration), billing disputes (requiring meter reading, token reference, units billed), water quality issues (requiring sample collection data, health impact), and gas leaks (requiring immediate safety escalation). Each has a different EWURA investigation track and different safety protocols. Without utility-specific fields, the AI cannot generate an EWURA-compliant complaint or distinguish between a life-threatening gas leak and a routine billing dispute.

## Source Standards

- Energy and Water Utilities Regulatory Authority (EWURA) Act, Cap. 414
- EWURA Electricity Regulations 2014 (GN No. 96)
- EWURA Water Supply and Sanitation Regulations 2017
- EWURA Customer Service Standards for Electricity Supply 2019
- EWURA Customer Service Standards for Water Supply 2019
- TANESCO Service Charter and Consumer Rights
- Tanzania Standard (TZS) 789 — Drinking Water Quality Standards
- DAWASCO/DAWASA Service Standards
- ISO 10002:2018 — complaints handling
- IEA Energy Access Outlook 2023 (reference for rural electrification standards)

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (ALL utilities sub-sectors)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | EWURA complaint form; enables follow-up |
| complainant_phone | Nambari ya simu | Yes | For status updates and technical visit scheduling |
| utility_type | Aina ya huduma ya matumizi | Yes | Electricity / Water / Gas — determines regulatory team and investigation type |
| utility_provider_name | Jina la mtoa huduma | Yes | TANESCO / DAWASCO / DAWASA / UWASA / RUWASA / GASCO etc. |
| customer_account_number | Nambari ya akaunti ya mteja | Yes | Primary utility account identifier |
| meter_number | Nambari ya mita | Yes | EWURA requires meter number for all billing and supply complaints; enables meter data pull |
| service_address | Anwani ya huduma | Yes | For geographic fault mapping and technical dispatch |
| issue_type | Aina ya tatizo | Yes | EWURA complaint taxonomy |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018 clause 8.2; EWURA requires narrative |
| date_issue_started | Tarehe ya kuanza kwa tatizo | Yes | For outage duration calculation; EWURA SLA monitoring |
| issue_ongoing | Je tatizo bado linaendelea? | Yes | Ongoing vs. resolved; affects urgency |
| previous_complaint_to_provider | Je, umeshalalamika mtoa huduma moja kwa moja? | Yes | EWURA requires prior complaint to provider |
| provider_complaint_reference | Nambari ya rufaa ya mtoa huduma | Conditional | Required for EWURA escalation |
| desired_outcome | Matokeo unayotaka | Yes | Reconnection / Refund / Repair / Investigation / Compensation |
| preferred_contact_method | Njia ya mawasiliano | Yes | SMS / Simu / WhatsApp |

### Conditional Fields — Electricity Complaints

**If issue_type = Power Outage / Blackout:**
Also collect:
- `outage_start_date_time` — Tarehe na saa ya kuanza giza: EWURA outage SLA begins from this time
- `outage_duration_hours` — Muda wa giza (masaa): For SLA compliance; TANESCO standard is restoration within 4–24 hours
- `outage_area_scope` — Ukubwa wa eneo lililoathiriwa: My house only / Street / Neighbourhood / Transformer area
- `transformer_id_or_name` — Nambari au jina la transfoma: TANESCO can identify fault and dispatch team
- `fault_reported_to_tanesco` — Je, tatizo limeripotiwa TANESCO? (nambari ya simu): Confirms initial report exists

**If issue_type = Billing Dispute / Meter Reading:**
Also collect:
- `bill_amount_tzs` — Kiasi cha ankara (TZS)
- `expected_amount_tzs` — Kiasi kilichotarajiwa (TZS)
- `billing_period` — Kipindi cha ankara (mwezi/mwaka)
- `actual_meter_reading` — Usomaji wa mita uliofanywa mwenyewe
- `token_reference_number` — Nambari ya marejeleo ya token: For prepaid meter disputes (LIPA NISHATI)
- `units_purchased` — Vitengo vilivyonunuliwa
- `units_received_on_meter` — Vitengo vilivyoingizwa kwenye mita

**If issue_type = Voltage Fluctuation / Equipment Damage:**
Also collect:
- `appliances_damaged` — Vifaa vilivyoharibika: List of damaged appliances for compensation claim
- `estimated_damage_value_tzs` — Thamani ya uharibifu (TZS): EWURA compensation framework
- `electrician_report_available` — Je, ripoti ya fundi wa umeme inapatikana?: Evidence for EWURA claim

### Conditional Fields — Water Complaints

**If issue_type = Water Quality (turbid, contaminated, bad smell):**
Also collect:
- `water_quality_issue_type` — Aina ya tatizo la ubora: Rangi (turbid) / Harufu mbaya / Ladha mbaya / Kitu kigeni
- `health_impact_experienced` — Je, watu wameumia baada ya kutumia maji? Yes / No — for public health escalation
- `sample_available` — Je, sampuli ya maji inapatikana kwa upimaji?: TZS 789 testing prerequisite
- `last_date_water_was_clear` — Tarehe ya mwisho maji yalikuwa mazuri: For fault timeline

**If issue_type = Water Shortage / Supply Interruption:**
Also collect:
- `days_without_water` — Siku ngapi bila maji
- `area_affected` — Eneo lililoathiriwa (mtaa / kijiji)
- `alternative_water_source_used` — Chanzo mbadala kilichotumiwa: For vulnerability assessment (hospital / school priority)
- `facility_type` — Aina ya mahali: Hospital / Shule / Nyumba / Biashara — for priority restoration

### Conditional Fields — Gas Complaints

**If issue_type = Gas Leak:**
- `gas_leak_location` — Mahali pa uvujaji wa gesi: Kitchen / Outdoor / Pipeline — SAFETY CRITICAL
- `leak_smell_intensity` — Nguvu ya harufu ya gesi: Light / Moderate / Strong
- `evacuation_done` — Je, watu wameondoka eneo?
- **This is an emergency — immediate escalation protocol applies**

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| EU-01 | power_outage | Planned or unplanned electricity outage |
| EU-02 | voltage_fluctuation | Voltage too high or too low; equipment damage |
| EU-03 | electricity_billing_dispute | Wrong meter reading, overcharge, token issue |
| EU-04 | illegal_connection | Unauthorized electricity connection in area |
| EU-05 | meter_tampering | Suspected meter tampering by another party |
| EU-06 | connection_refusal | New electricity connection application rejected |
| EU-07 | disconnection_dispute | Electricity cut off unjustly or without notice |
| EU-08 | water_shortage | No water supply or interruption |
| EU-09 | water_quality | Contaminated, turbid, or bad-tasting water |
| EU-10 | water_billing_dispute | Wrong water meter reading or overcharge |
| EU-11 | burst_pipe | Water pipe burst or leaking on public infrastructure |
| EU-12 | water_pressure | Water pressure too low for normal use |
| EU-13 | water_connection_refusal | New water connection application rejected |
| EU-14 | sewage_overflow | Sewage system overflow or blockage |
| EU-15 | gas_leak | Gas pipeline or cylinder leakage (EMERGENCY) |
| EU-16 | solar_system_failure | Government or subsidized solar installation failure |
| EU-17 | staff_conduct | Utility company employee misconduct |

### Resolution Standards

- **EWURA Electricity:** TANESCO must restore supply within 4 hours (urban) to 24 hours (rural) for unplanned outages. Billing disputes resolved within 30 days.
- **EWURA Water:** Water providers must restore supply within 24 hours (urban) and 72 hours (rural). Quality complaints: sampling within 48 hours; results within 7 days.
- **EWURA escalation:** If provider fails to resolve within 30 days, complainant may escalate to EWURA Consumer Affairs Department.
- **EWURA compensation:** EWURA Electricity Regulations 2014 provide for compensation for equipment damage caused by voltage fluctuations if proven.
- **Gas leak:** Emergency response within 30 minutes; GASCO/provider must dispatch immediately.
- **Required for EWURA escalation:** Meter number, account number, provider complaint reference, issue description, dates.

### Escalation Triggers

- `issue_type = gas_leak` AND `leak_smell_intensity = Strong` — EMERGENCY: Immediate GASCO emergency line; evacuate premises; do not use electrical switches
- `issue_type = water_quality` AND `health_impact_experienced = Yes` — Public health emergency; escalate to MOHCDGEC Environmental Health and Ministry of Water immediately
- `issue_type = voltage_fluctuation` AND significant appliance damage — EWURA compensation investigation; request technical inspection report
- `issue_type = power_outage` AND facility is hospital, school, or water pump — Priority restoration; escalate to TANESCO operations center
- `issue_type = illegal_connection` — TANESCO enforcement team; potential safety hazard and revenue loss
- `previous_complaint_to_provider = Yes` AND unresolved > 30 days — Eligible for EWURA Consumer Affairs escalation
- `issue_type = disconnection_dispute` AND disconnection prevents access to essential services (hospital, school) — Regulatory violation; immediate EWURA escalation

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| utility_type | Aina ya huduma | Yes | Electricity / Water / Gas |
| provider_name | Mtoa huduma | Recommended | For targeted routing |
| suggestion_category | Kategoria | Yes | Routes to correct team |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| EUS-01 | rural_electrification | Umeme vijijini |
| EUS-02 | prepaid_meter_expansion | Upanuzi wa mita za malipo ya awali |
| EUS-03 | renewable_energy | Nishati ya jua / upepo katika maeneo ya mbali |
| EUS-04 | water_quality_improvement | Ubora bora wa maji |
| EUS-05 | infrastructure_maintenance | Matengenezo ya miundombinu ya zamani |
| EUS-06 | digital_billing | Ankara na malipo ya kidijitali |
| EUS-07 | response_time | Kuharakisha muda wa kujibu dharura |
| EUS-08 | conservation_education | Elimu ya kuhifadhi maji na nishati |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina la mwulizaji | Recommended | For tracking |
| meter_number | Nambari ya mita | Conditional | For account-specific queries |
| query_type | Aina ya swali | Yes | Routes to correct answer |
| urgency | Haraka | Yes | Standard / Dharura |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| token_balance | Salio la vitengo vya umeme | meter_number |
| bill_explanation | Maelezo ya ankara | account_number, billing_period |
| connection_application | Jinsi ya kuomba muunganisho | address, facility_type |
| outage_schedule | Ratiba ya kupoteza umeme | area, date |
| water_quality_test | Kupima ubora wa maji | address |
| meter_reading_process | Jinsi ya kusoma mita | meter_type |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| staff_name | Jina la mfanyakazi | Recommended | Staff recognition |
| utility_type | Aina ya huduma | Yes | Routes to manager |
| specific_aspect_praised | Kipengele kilichotukuka | Yes | Utatuzi wa haraka / Adabu / Kazi nzuri ya ukarabati |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | EWURA CSAT benchmarking |

---

## AI Conversation Guidance for This Industry

- **Identify utility type first.** Electricity, water, and gas complaints have completely different fields, safety profiles, and regulatory bodies. "Tatizo lako linahusiana na umeme, maji, au gesi?"
- **For gas leak complaints, escalate IMMEDIATELY.** Do not continue collecting fields. Say "Hii ni dharura ya usalama! Toka nje ya nyumba mara moja, usiwashe taa au vifaa vya umeme, na piga simu GASCO / fire brigade (+255...)."
- **For power outages, ask for the transformer location.** TANESCO dispatches by transformer area. "Je, unajua namba au mahali pa transfoma ya karibu?"
- **For billing disputes with prepaid meters, ask for the token number.** The LIPA NISHATI token SMS contains the reference needed to verify units purchased vs. loaded. "Ujumbe wa token ya umeme — toa nambari ya marejeleo iliyoandikwa."
- **For water quality complaints, assess health impact before collecting technical data.** If anyone has fallen ill from drinking the water, that is a public health emergency requiring immediate escalation.
- **Collect meter number before account number** — in Tanzania, meter numbers are more reliably remembered by customers than account numbers, and are sufficient to pull the account record.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Utility type | "Tatizo lako ni la umeme, maji, au gesi?" |
| Provider | "Mtoa huduma ni nani — TANESCO, DAWASCO, DAWASA, au mwingine?" |
| Meter number | "Nambari ya mita yako inaonekana kwenye mita mwenyewe au kwenye ankara — inasema nini?" |
| Outage duration | "Umeme / maji kumekatika tangu lini hasa? Na bado inaendelea?" |
| Area affected | "Nyumba yako tu inaathirika, au mtaa wote?" |
| Token reference | "Nambari ya marejeleo ya token ya umeme inaonekana kwenye ujumbe wa SMS uliokuja baada ya kununua" |
| Damage assessment | "Je, vifaa vyovyote vya umeme viliharibika? Vifaa vipi na thamani yake ni kiasi gani?" |
| Water health | "Je, mtu yeyote aliugua baada ya kunywa maji hayo?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | gas_leak | EMERGENCY: Immediate GASCO alert; do not delay for data collection; evacuate guidance first |
| issue_type | water_quality AND health_impact = Yes | Public health emergency; notify MOHCDGEC Environmental Health AND Ministry of Water immediately |
| issue_type | voltage_fluctuation AND appliances damaged | EWURA compensation track; schedule TANESCO technical inspection; advise electrician report |
| facility_type | hospital OR water_pump AND issue_type = power_outage | Priority restoration request; escalate to TANESCO operations center |
| issue_type | illegal_connection | TANESCO enforcement referral; safety and revenue risk |
| previous_complaint_to_provider | Yes AND unresolved > 30 days | EWURA Consumer Affairs escalation; provide EWURA contact (ewura.go.tz) |
| issue_type | electricity_billing_dispute AND token_units_shortfall | Verify via LIPA NISHATI system; if discrepancy confirmed, refund/credit units |
| issue_type | water_shortage AND days_without_water > 3 | Priority restoration; facility type determines urgency (hospital = immediate) |

---

*Sources: EWURA Act Cap. 414, EWURA Electricity Regulations 2014, EWURA Water Regulations 2017, TANESCO Service Charter, TZS 789 Drinking Water Quality Standards, DAWASCO/DAWASA Service Standards, ISO 10002:2018*
