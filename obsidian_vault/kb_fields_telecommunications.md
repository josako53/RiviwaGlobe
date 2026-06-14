---
tags: [industry-kb, field-standards, feedback-fields]
---
# Telecommunications — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: Vodacom, Airtel, Tigo, TTCL, Zantel, Halotel, Smile, DSTV, Startimes, Azam TV, Zuku, data bundle, SIM card, USSD, mobile money, M-Pesa, Airtel Money, Tigo Pesa, HaloPesa, recharge, network coverage, call drop, roaming, internet speed, 4G LTE, 5G, TCRA, SIMCARD registration, toll-free, call center, IVR, set-top box, decoder, satellite dish, Wi-Fi router, modem, OTT, hotspot, SIM swap, MVNO, fiber broadband, token ya mtandao, bundle, airtime, salio, mtandao, simu inakatika, data inaisha, nambari imehamishwa, SIM ilibadilishwa, bili ya simu

## Why Industry-Specific Fields Matter

Generic feedback fields cannot distinguish between a dropped call complaint (requiring network location and frequency data), a SIM swap fraud (requiring security incident metadata and financial loss), and a billing dispute (requiring account number, MSISDN, and transaction reference) — all of which have different regulatory escalation paths under TCRA rules and require different evidence for the operator and the TCRA-CCC. Without telecom-specific fields, the AI cannot route, prioritize, or generate actionable tickets.

## Source Standards

- ITU-T E.800 (2008) — Definitions of QoS terms (service availability, continuity, accessibility)
- ITU-T E.803 — 88 customer care parameters including throughput, data rate, outage duration, resolution time
- ITU-T E.805 (2019) — Strategies for quality regulatory frameworks; per-service-type and geographic QoS measurement
- TCRA Electronic and Postal Communications (Consumer Protection) Regulations 2018, GN No. 61
- TCRA Complaints Committee Rules 2018, GN No. 203
- TCRA Revised Guideline for Consumer Complaint Handling with ISO Requirements
- TCRA Personal Data Protection (Complaints Settlement Procedures) Regulations 2023
- Ofcom General Condition C4 Annex — Approved Complaints Code of Practice
- EU Directive 2018/1972 (EECC) Articles 102–104 — contract disclosure, speed transparency, complaint handling
- ISO 10002:2018 — Quality management: guidelines for complaints handling (clauses 8.1–8.5)
- ISO/IEC 20000-1:2018 — IT service management (incident vs. complaint distinction)
- GSMA Code of Conduct for Mobile Money Providers, Principle 7 (complaint mechanism)
- Babble / V4VoIP Codes of Practice (Ofcom GC C4 compliant — reference for field completeness)

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Required by TCRA GN No. 61 complaint form and Ofcom GC C4; needed to open formal ticket |
| complainant_phone_number | Nambari ya simu ya mlalamikaji | Yes | Required by TCRA form and Ofcom approved code (V4VoIP/Babble); used for updates and verification |
| complainant_email | Barua pepe ya mlalamikaji | Recommended | Required for written acknowledgement under Ofcom approved code; TCRA-CCC online portal uses email |
| account_number_or_customer_id | Nambari ya akaunti / ID ya mteja | Yes | EU EECC Art. 102(3) mandates account identification; enables operator to pull account history |
| msisdn_affected | Nambari ya simu iliyoathirika | Yes | Primary network identifier; TCRA form requires the specific number affected by the complained issue |
| service_provider_name | Jina la mtoa huduma | Yes | TCRA requires the complaint to name the operator; determines complaint routing |
| service_type | Aina ya huduma | Yes | Required by EU EECC Art. 102 and ITU-T E.805; determines which QoS parameters apply. Options: Voice / Mobile Data / SMS / Fixed Broadband / Fiber / USSD / Mobile Money / Pay TV / IoT |
| contract_tariff_type | Aina ya mkataba / tariff | Yes | Required by EU EECC Art. 102(3); affects which billing rules and protections apply. Options: Prepaid / Postpaid / Business / Consumer |
| issue_type | Aina ya tatizo / kategoria | Yes | TCRA accepted categories drive routing, investigation type, and resolution SLA |
| issue_description | Maelezo ya tatizo | Yes | Required by ISO 10002:2018 clause 8.2 and Ofcom/V4VoIP approved code ("nature of the complaint including relevant details") |
| date_issue_first_experienced | Tarehe tatizo lilianza | Yes | Required for ITU-T QoS duration measurement; TCRA 12-month limitation period runs from this date |
| issue_ongoing | Je tatizo bado linaendelea? | Yes | Needed for duration calculation; ITU-T E.800 service availability metric requires outage duration |
| date_issue_last_experienced | Tarehe ya mwisho tatizo kulionekana | Conditional | Collect if issue_ongoing = No; needed for duration calculation per ITU-T E.803 |
| issue_frequency | Mara ngapi tatizo linatokea | Yes | Classifies service degradation severity per ITU-T E.803 service availability parameters. Options: Mara moja / Mara kwa mara / Kila wakati |
| geographic_area_locality | Eneo / Mtaa ulioathirika | Yes | TCRA QoS reports track complaints by region; enables coverage gap analysis |
| gps_coordinates | Kuratibu za GPS | Recommended | ITU-T E.805 requires geographically relevant QoS measurement; enables heatmap and cell-level fault isolation |
| desired_outcome | Matokeo unayotaka | Yes | Required by Ofcom approved code; ISO 10002:2018 clause 8.3; EWURA awards framework lists remedy types |
| preferred_contact_method | Njia unayopendelea ya mawasiliano | Yes | GSMA Code of Conduct Principle 7 — complainant must be kept informed of status. Options: SMS / Barua pepe / Simu / WhatsApp |
| consent_to_share_data | Ridhaa ya kushiriki data na mdhibiti | Yes | TCRA Personal Data Protection Regulations 2023; required before sharing details with TCRA-CCC |

### Conditional Fields (collect based on issue type)

**If issue_type = Slow Data / Low Speed / Data Bundle Problem:**
Also collect:
- `speed_test_download_mbps` — Kasi ya kupakua (Mbps): ITU-T E.803 lists throughput as a measured QoS parameter; Ofcom broadband investigations use speed test data as primary evidence
- `speed_test_upload_mbps` — Kasi ya kupakia (Mbps): Same rationale
- `speed_test_tool_used` — Chombo cha kupima kasi: e.g., Ookla / TCRA Net Meter / NDT; TCRA conducts its own QoS benchmarks and references these tools
- `speed_test_timestamp` — Tarehe na saa ya kupima kasi: For correlation with network logs
- `advertised_plan_speed_mbps` — Kasi iliyoahidiwa na mtoa huduma: EU EECC Art. 102(3) requires advertised speed disclosure; Art. 104 requires minimum speed guarantee; this field documents the gap

**If issue_type = Wrong Billing / Unauthorized Charge:**
Also collect:
- `billing_period_affected` — Kipindi cha bili kilichoathirika (mwezi/mwaka)
- `amount_charged_tzs` — Kiasi kilichochukuliwa (TZS)
- `amount_expected_tzs` — Kiasi kilichotarajiwa (TZS)
- `transaction_reference` — Nambari ya marejeleo ya malipo: Required for M-Pesa and mobile money payment disputes
- `bill_copy_upload` — Pakia nakala ya bili / risiti: TCRA requires supporting documentation; ISO 10002:2018 clause 8.2 requires evidence

**If issue_type = SIM Swap Fraud / Unauthorized Port / SIM Cloning:**
Also collect:
- `fraud_incident_date_time` — Tarehe na saa ya tukio la udanganyifu: For police report and TCRA fraud escalation
- `financial_loss_tzs` — Hasara ya fedha (TZS): EWURA/TCRA Committee can order refunds; quantifying loss is required for remedy calculation
- `financial_loss_type` — Aina ya hasara: e.g., Mobile money stolen / Airtime drained / Unauthorized purchase
- `police_report_number` — Nambari ya ripoti ya polisi: Required by TCRA for fraud-based complaint escalation
- `nida_national_id` — Nambari ya Kitambulisho cha Taifa (NIDA): For identity verification in SIM-related fraud cases

**If issue_type = No Signal / Poor Coverage:**
Also collect:
- `location_type` — Aina ya eneo: Indoor / Outdoor / Rural / Urban / Transit (gari linalohamia); relevant to coverage classification per ITU-T E.800 network performance parameters
- `device_type` — Aina ya simu / kifaa: e.g., Smartphone / Feature phone / Modem / Router; for network compatibility analysis

**If issue_type = Dropped Calls / Voice Quality:**
Also collect:
- `call_frequency_per_day` — Simu zinazoweza kukatika kwa siku: For ITU-T E.803 call setup success rate / drop rate calculation
- `call_duration_before_drop_seconds` — Muda wa simu kabla ya kukatika (sekunde)

**If issue_type = Meter/Token/Prepaid (for mobile money/USSD service):**
Also collect:
- `last_payment_reference` — Nambari ya malipo ya mwisho: For transaction tracing
- `payment_channel_used` — Njia ya malipo iliyotumika: e.g., M-Pesa / Airtel Money / USSD / Agent

### Issue Type Classification

TCRA accepted complaint categories (per TCRA Consumer Protection Regulations 2018 and TCRA-CCC practice):

| Code | Issue Type | Description |
|------|-----------|-------------|
| TC-01 | no_signal_poor_coverage | No signal or weak network in a geographic area |
| TC-02 | slow_data_low_speed | Data speed below acceptable or advertised level |
| TC-03 | wrong_billing | Incorrect charge, overcharge, or unrecognized deduction |
| TC-04 | dropped_calls | Calls disconnecting during active conversation |
| TC-05 | sms_not_delivered | SMS messages not reaching recipients |
| TC-06 | sim_swap_fraud | Fraudulent SIM swap to hijack account |
| TC-07 | unauthorized_port | Number ported to another network without consent |
| TC-08 | spam_messages | Unsolicited promotional or fraudulent SMS |
| TC-09 | line_disconnection | Arbitrary or unexplained line suspension |
| TC-10 | deceptive_advertising | Advertised service does not match delivery |
| TC-11 | privacy_violation | Customer data exposed or shared without consent |
| TC-12 | mobile_money_fraud | Illegal mobile money transfer or account drain |
| TC-13 | vas_unauthorized_charge | Value-added service subscription without consent |
| TC-14 | delayed_service_restoration | Fault reported but not repaired within SLA |
| TC-15 | poor_customer_service | Rude, unresponsive, or unhelpful customer care |
| TC-16 | data_bundle_expiry | Bundle expired prematurely or before advertised validity |
| TC-17 | roaming_charge_dispute | Incorrect or unauthorized roaming fee |
| TC-18 | sim_registration_issue | SIM registration blocked, rejected, or failed |
| TC-19 | decoder_tv_issue | Set-top box, decoder, or Pay TV service problem |
| TC-20 | internet_service_disruption | Fixed broadband or fiber service down |

### Complaint History / Escalation Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| previous_complaint_ref_operator | Nambari ya rufaa ya awali kwa mtoa huduma | Yes (for TCRA escalation) | TCRA requires complainant to have first lodged with operator (30-day rule); operator ticket number is mandatory at regulator level |
| date_complaint_lodged_with_operator | Tarehe ya malalamiko kwa mtoa huduma | Yes (for TCRA escalation) | Required to calculate 30-day operator response window under TCRA Consumer Protection Regulations 2018 |
| operator_response_received | Je, mtoa huduma alijibu? | Yes | Required by TCRA escalation process. Options: Ndiyo / Hapana / Jibu la sehemu |
| operator_response_summary | Muhtasari wa jibu la mtoa huduma | Conditional | Required at TCRA-CCC stage; complainant must attach provider's written reply |
| previous_tcra_reference | Nambari ya rufaa ya TCRA (kama ipo) | Conditional | For repeat complaints or appeals at TCRA-CCC |
| deadlock_letter_received | Je, barua ya msukosuko (deadlock letter) imepokelewa? | Conditional | Ofcom GC C4: providers must issue deadlock letter at 8 weeks (reducing to 6 weeks April 2026); required for ADR access |
| escalate_to_tcra | Peleka kwa TCRA | Conditional | Triggered when operator has not resolved within 30 days or response is unsatisfactory |

### Resolution Standards for This Industry

- **Operator level (Tanzania):** TCRA requires operators to acknowledge complaints and resolve or provide substantive response within 30 days. If unresolved, customer may escalate to TCRA-CCC.
- **TCRA-CCC level:** TCRA Consumer Complaints Committee must process escalated complaints within 60 days. Customer must attach operator's written response or evidence of non-response.
- **Ofcom standard (reference):** Operators must send written acknowledgement; ADR access available after 8 weeks (6 weeks from April 2026). Deadlock letter required.
- **Required documentation for escalation:** Operator complaint reference number, date of initial complaint, operator response (or evidence of non-response), evidence of financial loss (if any), copy of contract/tariff terms.
- **Limitation period:** 12 months from date of incident under TCRA rules.

### Escalation Triggers (field values that require immediate escalation)

- `issue_type = sim_swap_fraud` AND `financial_loss_tzs > 0` — Report to TCRA fraud unit and advise police report within 24 hours
- `issue_type = mobile_money_fraud` AND `financial_loss_tzs > 500000` — Escalate to TCRA-CCC and relevant MNO fraud team immediately
- `issue_type = unauthorized_port` — Immediate escalation; porting without consent is a TCRA regulatory violation
- `issue_type = privacy_violation` — Escalate to TCRA under TCRA Personal Data Protection Regulations 2023
- `location_type = hospital_or_emergency_zone` AND `issue_type = no_signal_poor_coverage` — Network failure affecting emergency communications; escalate to TCRA NOC unit
- `issue_type = line_disconnection` AND customer reports inability to reach emergency services (112) — Regulatory violation; immediate TCRA referral
- `issue_type = deceptive_advertising` AND multiple complainants report same promotion — Pattern-based TCRA consumer protection escalation
- `issue_type = sim_swap_fraud` OR `mobile_money_fraud` — Always advise customer to immediately call operator fraud hotline AND block SIM

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina la mtoa maoni (hiari) | Optional | ISO 10002:2018 permits anonymous feedback; TCRA portal allows anonymous suggestions |
| contact_details | Mawasiliano (hiari) | Optional | For follow-up if needed |
| service_type_targeted | Huduma inayohusika | Yes | Enables product team routing. Options: Sauti / Data / SMS / Programu / Huduma ya Wateja / Mtandao / Runinga / Nyingine |
| geographic_area | Eneo / Mkoa unaohusika | Recommended | ITU-T E.805 emphasises geographic coverage QoS; enables spatial analysis |
| suggestion_category | Kategoria ya mapendekezo | Yes | Enables routing to correct team |
| suggestion_detail | Maelezo ya mapendekezo | Yes | Free text; core content of the suggestion |
| priority_rating | Kipaumbele | Recommended | ISO 10002:2018 clause 8.4 on priority scoring. Options: Chini / Kati / Juu |
| channel_submitted | Njia ya kuwasilisha | Auto | Supports omnichannel analytics |

### Industry-Specific Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| SG-01 | coverage_expansion | Upanuzi wa mtandao / minara mipya |
| SG-02 | speed_improvement | Kuboresha kasi ya data |
| SG-03 | billing_transparency | Uwazi wa bili na malipo |
| SG-04 | new_bundle_feature | Aina mpya ya bundle au huduma |
| SG-05 | accessibility | Upatikanaji kwa wazee / walemavu |
| SG-06 | pricing_affordability | Bei nafuu zaidi |
| SG-07 | app_digital_experience | Kuboresha programu au huduma ya kidijitali |
| SG-08 | customer_service_quality | Kuboresha huduma ya wateja |
| SG-09 | rural_connectivity | Muunganiko wa vijijini |
| SG-10 | pay_tv_content | Maudhui ya runinga / chaneli mpya |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina la mwulizaji | Recommended | Identity verification before disclosing account data per Ofcom GC C4 |
| account_number_or_msisdn | Nambari ya akaunti / MSISDN | Conditional | Required to pull account-specific data; EU EECC Art. 102(3) mandates account identification |
| service_type | Aina ya huduma inayohusika | Yes | Determines which team or knowledge base to consult |
| query_type | Aina ya swali | Yes | Routes inquiry to correct answer path |
| billing_period_of_interest | Kipindi cha bili kinachohusika | Conditional | Collect if query is about bill or usage history |
| preferred_response_format | Jinsi unavyotaka jibu | Yes | Options: SMS / Barua pepe / Simu / Mazungumzo; ISO 10002:2018 and GSMA Principle 7 require accessible communication |
| urgency | Kiwango cha haraka | Recommended | Standard / Dharura |
| inquiry_reference_number | Nambari ya marejeleo (otomatiki) | Auto | Ofcom GC C4 and operator codes require all interactions trackable by reference number |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| balance_check | Kuangalia salio | msisdn_affected |
| bundle_availability | Bundles zinazopatikana | service_type, budget_tzs (optional) |
| data_usage_history | Historia ya matumizi ya data | msisdn_affected, billing_period_of_interest |
| contract_terms | Masharti ya mkataba | account_number_or_msisdn, contract_tariff_type |
| coverage_map | Ramani ya mtandao | geographic_area |
| port_out_process | Jinsi ya kubadilisha mtandao | msisdn_affected |
| roaming_rates | Bei za roaming | destination_country, service_type |
| sim_swap_process | Jinsi ya kubadilisha SIM | msisdn_affected, account_number_or_msisdn |
| billing_explanation | Maelezo ya bili | account_number_or_msisdn, billing_period_of_interest |
| unsubscribe_vas | Kufuta huduma za malipo | msisdn_affected |
| data_safety | Usalama wa data yangu | account_number_or_msisdn |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina la mtoa pongezi (hiari) | Optional | For acknowledgement or recognition schemes |
| service_interaction_type | Aina ya huduma iliyopongezwa | Yes | Routes compliment to correct team. Options: Kituo cha simu / Fundi wa uwanja / Programu / Duka / Kujihudumia |
| staff_name_or_id | Jina au nambari ya mfanyakazi | Optional | GSMA Principle 7 on consumer feedback loops supports staff recognition |
| date_of_interaction | Tarehe ya mazungumzo / huduma | Recommended | For correlation with staff performance records |
| channel_of_interaction | Njia ya mawasiliano | Yes | Simu / Gumzo la maandishi / Barua pepe / Ana kwa ana / SMS |
| specific_aspect_praised | Kipengele kilichotukuka | Yes | Utatuzi wa tatizo / Adabu / Ujuzi wa kiufundi / Usahihi wa bili / Ubora wa mtandao |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | ITU-T E.800 defines QoS partly in terms of degree of satisfaction; structured satisfaction capture |
| free_text_commendation | Maneno ya pongezi (hiari) | Optional | Open narrative; captures nuance not covered by structured fields |

---

## AI Conversation Guidance for This Industry

- **Start with the service, not the problem.** Ask "Unatumia mtandao gani — Vodacom, Airtel, Tigo, TTCL?" before asking what went wrong. Knowing the operator first helps the AI understand the right regulatory framework (TCRA applies to all, but procedures differ slightly by operator).
- **Get the MSISDN early and confirm it.** The affected phone number is the single most important identifier in a telecom complaint. Ask "Nambari gani ya simu inahusika?" early in the conversation and repeat it back for confirmation before proceeding.
- **For billing disputes, ask for the amount and period before asking for a receipt.** Say "Ilikatwa kiasi gani, na lini?" before asking them to upload documentation — many customers cannot upload immediately and will drop off.
- **Do not ask for national ID (NIDA) unless the issue is SIM swap fraud or SIM registration.** For general network or billing complaints, NIDA is not needed and asking for it feels intrusive and may cause the customer to abandon the conversation.
- **For fraud/SIM swap complaints, prioritize urgency over completeness.** Immediately tell the customer to call the operator's fraud hotline to block the SIM, then collect remaining fields. Do not delay this safety step to gather more data.
- **Distinguish between the complainant's number and the number they are complaining about.** A customer calling from a different number to complain about their affected SIM is common; always ask "Je, unawasiliana kutoka kwa nambari iliyoathirika?" to confirm which number to investigate.
- **For speed complaints, guide the customer through a speed test before collecting the result.** Say "Unaweza kufanya mtihani wa kasi sasa hivi kwa kutumia Ookla au TCRA Net Meter?" and then ask for the result, rather than asking for a number they may not have.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Operator name | "Unatumia mtandao gani — Vodacom, Airtel, Tigo, TTCL, Halotel au mwingine?" |
| MSISDN affected | "Nambari gani ya simu inahusika na tatizo hili?" |
| Issue type | "Tatizo lako ni nini hasa — mtandao, data, bili, SIM, au huduma ya wateja?" |
| Date issue started | "Tatizo hili lilianza lini — ni siku ngapi au wiki ngapi zilizopita?" |
| Location | "Tatizo hili linatokea wapi hasa — nyumbani, kazini, au mahali pengine?" |
| Previous complaint ref | "Je, umeshawahi ripoti tatizo hili kwa mtoa huduma moja kwa moja? Kama ndiyo, una nambari ya rufaa yao?" |
| Financial loss | "Je, umepoteza pesa yoyote kutokana na tatizo hili? Kiasi gani?" |
| Desired outcome | "Unataka nini kutokea baada ya malalamiko yako kushughulikiwa — kurudishiwa pesa, kurekebisha tatizo, au kitu kingine?" |
| Speed test result | "Unaweza kufanya mtihani wa kasi ya data na kunieleza matokeo — kasi ya kupakua (download) na kupakia (upload)?" |
| Contact preference | "Ungependa tupate habari yako vipi — SMS, simu, au WhatsApp?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | sim_swap_fraud | Immediately advise customer to call operator fraud hotline; create priority ticket; flag for TCRA fraud unit referral |
| issue_type | mobile_money_fraud AND financial_loss_tzs > 100000 | Priority ticket; advise police report; escalate to TCRA-CCC and MNO fraud team |
| issue_type | unauthorized_port | Immediate TCRA escalation — porting without consent is a regulatory violation |
| issue_type | privacy_violation | Escalate to TCRA under TCRA Personal Data Protection Regulations 2023; log incident with reference number |
| operator_response_received | Hapana AND date_complaint_lodged_with_operator > 30 days ago | Advise customer they qualify for TCRA-CCC escalation; provide TCRA-CCC contact (+255 22 xxx / tcra-ccc.go.tz) |
| operator_response_received | Hapana AND date_complaint_lodged_with_operator < 30 days ago | Advise customer to wait for operator's 30-day window to expire; set reminder |
| speed_test_download_mbps | < 20% of advertised_plan_speed_mbps | Document gap; cite EU EECC Art. 104 minimum speed obligation (reference standard); recommend formal complaint to TCRA QoS unit |
| issue_type | no_signal_poor_coverage AND location_type includes hospital or emergency | Flag as safety-critical; escalate to TCRA NOC unit within 24 hours |
| issue_type | vas_unauthorized_charge | Advise customer to dial *100# or use operator app to list and cancel all active VAS subscriptions; document all unauthorized charges for refund claim |
| desired_outcome | Refund | Confirm financial amount; request bill or transaction upload; route to billing dispute resolution track |
| issue_type | dropped_calls AND issue_frequency = Kila wakati | Create quality-of-service ticket; flag for TCRA QoS monitoring data cross-reference |
| service_type | Mobile Money AND issue_type = wrong_billing | Dual-route: telecom billing team AND mobile money compliance team |

---

*Sources: ITU-T E.800/E.803/E.805, TCRA GN No. 61 (2018), TCRA GN No. 203 (2018), TCRA Personal Data Protection Regulations 2023, Ofcom GC C4, EU EECC Directive 2018/1972 Arts. 102–104, ISO 10002:2018, GSMA Code of Conduct Principle 7, Babble/V4VoIP Codes of Practice (Ofcom-approved)*
