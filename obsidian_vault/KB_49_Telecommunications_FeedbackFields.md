---
tags: [industry-kb, field-standards, feedback-fields, telecommunications]
---
# Telecommunications — Feedback Collection Fields & Standards

> **Note:** A comprehensive telecommunications KB already exists in this vault as `kb_fields_telecommunications.md`. This file (KB_49) serves as the numbered-series entry pointing to the same domain and extends it with additional coverage for Pay TV, fixed broadband, and satellite services.

## Industry Identifiers

Signals the AI uses to detect this industry: Vodacom, Airtel, Tigo, TTCL, Zantel, Halotel, Smile, DSTV, Startimes, Azam TV, Zuku, data bundle, SIM card, USSD, mobile money, M-Pesa, Airtel Money, Tigo Pesa, HaloPesa, recharge, network coverage, call drop, roaming, internet speed, 4G LTE, 5G, TCRA, SIMCARD registration, fiber broadband, token ya mtandao, bundle, airtime, salio, mtandao, simu inakatika, data inaisha, nambari imehamishwa, SIM ilibadilishwa, bili ya simu, decoder, set-top box, satellite dish, Wi-Fi router, modem, MVNO, OTT, DSTV Compact, Azam Extra, Zuku Fiber, TTCL fiber, ISP, internet service provider

## Why Industry-Specific Fields Matter

Telecommunications complaints span mobile (voice/data/SMS/money), Pay TV (decoder/satellite/streaming), and fixed broadband (fiber/DSL) — each with distinct technical evidence requirements. A dropped call complaint needs network location, MSISDN, and frequency data; a DSTV decoder complaint needs decoder serial number and smart card number; a fiber outage complaint needs connection ID and router model. Without telecom-specific fields, the AI cannot route to the correct operator team or generate a TCRA-compliant complaint.

## Source Standards

- ITU-T E.800, E.803, E.805 — QoS measurement standards
- TCRA Electronic and Postal Communications (Consumer Protection) Regulations 2018, GN No. 61
- TCRA Complaints Committee Rules 2018, GN No. 203
- TCRA Personal Data Protection Regulations 2023
- EU EECC Directive 2018/1972 Articles 102–104 (reference)
- ISO 10002:2018 — complaints handling
- GSMA Code of Conduct for Mobile Money Providers, Principle 7

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (ALL telecom sub-sectors)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Required by TCRA GN No. 61 |
| complainant_phone_number | Nambari ya simu ya mlalamikaji | Yes | Primary contact; TCRA uses for updates |
| service_provider_name | Jina la mtoa huduma | Yes | Operator identification; determines TCRA routing |
| service_type | Aina ya huduma | Yes | Mobile Voice / Mobile Data / SMS / Fixed Broadband / Fiber / Pay TV / Mobile Money |
| msisdn_affected | Nambari ya simu iliyoathirika | Conditional | Required for mobile service complaints |
| account_number_or_customer_id | Nambari ya akaunti / ID ya mteja | Recommended | For fixed broadband, Pay TV, and postpaid mobile |
| issue_type | Aina ya tatizo / kategoria | Yes | TCRA accepted categories |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; TCRA form narrative requirement |
| date_issue_first_experienced | Tarehe tatizo lilianza | Yes | Required for QoS duration measurement; TCRA 12-month limitation |
| issue_ongoing | Je tatizo bado linaendelea? | Yes | For duration and severity classification |
| geographic_area_locality | Eneo / Mtaa ulioathirika | Yes | TCRA QoS geographic analysis |
| desired_outcome | Matokeo unayotaka | Yes | Required by Ofcom approved code; ISO 10002:2018 |
| preferred_contact_method | Njia ya mawasiliano | Yes | SMS / Barua pepe / Simu / WhatsApp |
| consent_to_share_data | Ridhaa ya kushiriki data na mdhibiti | Yes | TCRA Personal Data Protection Regulations 2023 |

### Extended Fields for Pay TV / Decoder Complaints

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| decoder_serial_number | Nambari ya msururu wa decoder | Yes | Primary Pay TV identifier; without it, operator cannot access subscription record |
| smart_card_number | Nambari ya kadi ya akili | Yes | Smart card is tied to subscription package; required for channel access disputes |
| subscription_package | Pakiti ya usajili | Yes | Compact / Premium / Family / Extra — determines entitlement |
| channel_missing | Chaneli inayokosekana | Conditional | For missing channel complaints; enables technical verification |
| signal_error_code | Nambari ya hitilafu ya ishara | Recommended | Error codes on screen guide technical investigation |
| installation_date | Tarehe ya ufungaji wa decoder | Recommended | For warranty and installation quality complaints |
| dish_alignment_issue | Je, sahani ya satellite imeelemea? | Conditional | For signal loss complaints; determines if technical visit needed |

### Extended Fields for Fixed Broadband / Fiber Complaints

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| connection_id | Nambari ya muunganisho (connection ID) | Yes | ISP's primary identifier for fixed broadband accounts |
| router_model | Modeli ya router | Recommended | Technical troubleshooting and firmware issues |
| speed_test_download_mbps | Kasi ya kupakua (Mbps) | Yes | ITU-T E.803 QoS measurement; TCRA benchmark |
| speed_test_upload_mbps | Kasi ya kupakia (Mbps) | Yes | ITU-T E.803 |
| advertised_plan_speed_mbps | Kasi iliyoahidiwa (Mbps) | Yes | EU EECC Art. 104 minimum speed obligation reference |
| outage_start_time | Saa ya kuanza kwa kukatika | Yes | For SLA duration calculation |
| outage_duration_hours | Muda wa kukatika (masaa) | Conditional | If outage is over; ITU-T E.800 availability metric |

### Issue Type Classification (Extended)

| Code | Issue Type | Description |
|------|-----------|-------------|
| TC-01 | no_signal_poor_coverage | No signal or weak network in a geographic area |
| TC-02 | slow_data_low_speed | Data speed below acceptable or advertised level |
| TC-03 | wrong_billing | Incorrect charge, overcharge, unauthorized deduction |
| TC-04 | dropped_calls | Calls disconnecting during active conversation |
| TC-05 | sms_not_delivered | SMS messages not reaching recipients |
| TC-06 | sim_swap_fraud | Fraudulent SIM swap to hijack account |
| TC-07 | unauthorized_port | Number ported to another network without consent |
| TC-08 | mobile_money_fraud | Illegal mobile money transfer or account drain |
| TC-09 | data_bundle_expiry | Bundle expired prematurely |
| TC-10 | internet_fiber_outage | Fixed broadband or fiber service down |
| TC-11 | decoder_signal_loss | Pay TV signal lost; decoder error |
| TC-12 | missing_channels | Subscribed channels not available |
| TC-13 | vas_unauthorized_charge | Value-added service charged without consent |
| TC-14 | privacy_violation | Customer data exposed without consent |
| TC-15 | poor_customer_service | Rude or unresponsive customer care |
| TC-16 | line_disconnection | Arbitrary or unexplained service suspension |
| TC-17 | sim_registration_issue | SIM registration blocked, rejected, or failed |
| TC-18 | roaming_charge_dispute | Incorrect or unauthorized roaming fee |
| TC-19 | spam_messages | Unsolicited promotional or fraudulent SMS |
| TC-20 | delayed_service_restoration | Fault reported but not repaired within SLA |

### Resolution Standards

- **Operator level:** TCRA requires operators to acknowledge and resolve complaints within 30 days.
- **TCRA-CCC:** Escalated complaints processed within 60 days. Complainant must provide operator reference number.
- **Fraud (SIM swap/mobile money):** Operator fraud team must respond within 24–48 hours.
- **Fixed broadband SLA:** Most ISP contracts guarantee restoration within 24 hours for service outages; 72 hours for planned maintenance.
- **Limitation period:** 12 months from date of incident.

### Escalation Triggers

- `issue_type = sim_swap_fraud` AND `financial_loss_tzs > 0` — TCRA fraud unit AND police report within 24 hours
- `issue_type = mobile_money_fraud` AND `financial_loss_tzs > 500,000` — Escalate to TCRA-CCC and MNO fraud team immediately
- `issue_type = unauthorized_port` — Regulatory violation; immediate TCRA escalation
- `issue_type = no_signal_poor_coverage` AND location includes hospital or emergency — Safety-critical; escalate to TCRA NOC unit within 24 hours
- `previous_complaint_ref_operator` provided AND unresolved > 30 days — Eligible for TCRA-CCC escalation

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous feedback accepted |
| service_type_targeted | Huduma inayohusika | Yes | Mobile / Fiber / Pay TV / Mobile Money |
| suggestion_category | Kategoria | Yes | Routes to correct product team |
| suggestion_detail | Maelezo | Yes | Core content |
| geographic_area | Eneo | Recommended | Geographic QoS analysis |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| TC-SG-01 | coverage_expansion | Upanuzi wa mtandao / minara mipya |
| TC-SG-02 | speed_improvement | Kuboresha kasi ya data / fiber |
| TC-SG-03 | pricing_affordability | Bei nafuu zaidi ya bundles / bima |
| TC-SG-04 | rural_connectivity | Muunganiko wa vijijini |
| TC-SG-05 | decoder_channels | Chaneli mpya za Pay TV |
| TC-SG-06 | app_digital_experience | Kuboresha programu ya kidijitali |
| TC-SG-07 | customer_service | Kuboresha huduma ya wateja |
| TC-SG-08 | mobile_money_features | Vipengele vipya vya pesa za simu |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina la mwulizaji | Recommended | Identity verification |
| msisdn_or_account | MSISDN / Nambari ya akaunti | Conditional | For account-specific queries |
| service_type | Aina ya huduma | Yes | Routes to correct knowledge base |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| bundle_availability | Bundles zinazopatikana | service_type, budget |
| balance_check | Kuangalia salio | msisdn_affected |
| coverage_map | Ramani ya mtandao | geographic_area |
| decoder_reactivation | Kuhuisha decoder | decoder_serial_number, smart_card_number |
| fiber_installation | Jinsi ya kupata fiber nyumbani | address, geographic_area |
| port_out_process | Jinsi ya kubadilisha mtandao | msisdn_affected |
| roaming_rates | Bei za roaming | destination_country |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| service_interaction_type | Aina ya huduma | Yes | Kituo cha simu / Fundi / App / Duka |
| staff_name_or_id | Jina au nambari ya mfanyakazi | Optional | Staff recognition |
| specific_aspect_praised | Kipengele kilichotukuka | Yes | Utatuzi wa tatizo / Adabu / Ujuzi / Kasi |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | ITU-T E.800 satisfaction dimension |

---

## AI Conversation Guidance for This Industry

- **Identify the service sub-type first.** Mobile, fiber, and Pay TV are distinct products with different fields. Ask "Tatizo lako linahusiana na simu ya mkononi, intaneti ya nyumbani, au decoder ya TV?"
- **For mobile complaints, get the MSISDN early.** Ask "Nambari gani ya simu inahusika?" and confirm it — complainant may be calling from a different number.
- **For Pay TV, ask for decoder serial and smart card number.** These are printed on the decoder and smart card; without them, customer service cannot access the subscription.
- **For fiber complaints, guide the user through basic troubleshooting** before collecting detailed data: "Je, router yako ina taa ya status? Inaonyesha rangi gani?" — this avoids field visits for simple restarts.
- **For fraud/SIM swap, prioritize safety action.** Immediately advise calling the operator's fraud hotline to block the SIM before collecting remaining fields.
- **For billing disputes, ask for the SMS notification** — all Tanzanian operators send SMS for charges; the SMS contains the transaction reference needed for investigation.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Operator | "Unatumia mtandao gani — Vodacom, Airtel, Tigo, TTCL, Halotel, au Pay TV kama DSTV/Azam?" |
| MSISDN | "Nambari gani ya simu inahusika na tatizo hili?" |
| Decoder serial | "Nambari ya msururu wa decoder (serial number) inaonekana nyuma au chini ya decoder — inasema nini?" |
| Smart card | "Nambari ya kadi ya akili (smart card) inaonekana kwenye kadi ndogo kwenye decoder" |
| Connection ID (fiber) | "Nambari ya muunganisho wa fiber (connection ID) inaonekana kwenye ankara au barua pepe ya ISP yako" |
| Issue start | "Tatizo hili lilianza lini — tarehe na saa ikiwezekana?" |
| Previous complaint ref | "Je, umeshalalamika mtoa huduma moja kwa moja? Kama ndiyo, una nambari ya rufaa yao?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | sim_swap_fraud AND financial loss | Immediate: advise block SIM; create priority ticket; refer to TCRA fraud unit and police |
| issue_type | mobile_money_fraud AND amount > 500,000 | Priority escalation to TCRA-CCC and MNO fraud team; advise police report |
| issue_type | unauthorized_port | Immediate TCRA escalation; regulatory violation |
| issue_type | privacy_violation | Escalate to TCRA under Data Protection Regulations 2023 |
| previous_complaint_ref | provided AND unresolved > 30 days | Eligible for TCRA-CCC escalation; provide TCRA-CCC contact |
| speed_test_download_mbps | < 20% of advertised_plan | Document gap; recommend formal TCRA QoS complaint |
| issue_type | decoder_signal_loss AND dish_alignment_issue = Yes | Schedule technical field visit; not resolvable remotely |

---

*Sources: ITU-T E.800/E.803/E.805, TCRA GN No. 61 (2018), TCRA GN No. 203 (2018), TCRA Personal Data Protection Regulations 2023, ISO 10002:2018, GSMA Code of Conduct Principle 7, EU EECC Directive 2018/1972*
