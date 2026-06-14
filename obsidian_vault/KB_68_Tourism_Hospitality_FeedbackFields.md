---
tags: [industry-kb, field-standards, feedback-fields, tourism, hospitality]
---
# Tourism / Hospitality — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: utalii, tourism, hoteli, hotel, lodge, camp, resort, safari, utalii wa wanyamapori, wildlife safari, game reserve, hifadhi ya wanyama, national park, hifadhi ya taifa, TANAPA, Tanzania National Parks, NCAA, Ngorongoro Conservation Area, TAWA, Serengeti, Kilimanjaro, Zanzibar, tour operator, mpangaji wa utalii, guide, mwongozo, tour guide, beach, pwani, diving, kuogelea, snorkeling, accommodation, malazi, bed and breakfast, guesthouse, nyumba ya kulala wageni, booking, mapanga, reservation, check-in, check-out, room service, huduma ya chumba, restaurant, mkahawa, menu, food, chakula, bar, nywele, conference, mkutano, wedding, harusi, spa, pool, bwawa, beach resort, all-inclusive, tariff, tozo, travel agent, wakala wa utalii, visa, travel insurance, bima ya safari, flight, ndege, JNIA, airport transfer, usafiri wa uwanja wa ndege, Tanzania Tourism Board (TTB), TANZANITE, TTB license, Tanzania Association of Tour Operators (TATO), HAT, Hotel Association of Tanzania

## Why Industry-Specific Fields Matter

Tourism complaints span booking fraud (requiring reservation reference, amount paid, travel agent license), hotel quality failures (requiring check-in/out dates, room type, specific deficiencies), safari guide misconduct (requiring park entry receipt, guide license number), and food safety (requiring TFDA concern). TTB licenses tour operators and hotels; TANAPA/NCAA handle park-related complaints. Without tourism-specific fields, the AI cannot verify whether the tour operator is TTB-licensed or generate a TTB consumer complaint that could lead to license suspension.

## Source Standards

- Tanzania Tourism Act, Cap. 261 — tourism regulation and TTB mandate
- Tourism (Tourism Promotion) Regulations 2014 — tour operator licensing
- Tanzania Tourist Board (TTB) Act — consumer protection and operator standards
- Hotel and Hospitality Industry Act — hotel licensing and standards
- Tanzania National Parks Act, Cap. 282 — TANAPA regulations
- Ngorongoro Conservation Area Authority (NCAA) Act
- Tanzania Wildlife Authority (TAWA) — wildlife areas
- Hotel and Tourism Training Institute (HTTI) — hospitality standards
- ISO 10002:2018 — complaints handling
- UNWTO Global Code of Ethics for Tourism — international reference
- TFDA — food safety in hospitality

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL tourism/hospitality complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | TTB complaint form; follow-up |
| complainant_phone | Nambari ya simu | Yes | Status updates |
| complainant_email | Barua pepe | Recommended | Most tourism operators communicate via email |
| complainant_nationality | Uraia wa mlalamikaji | Recommended | Foreign tourists may need embassy assistance |
| service_provider_name | Jina la mtoa huduma (hoteli / tour operator) | Yes | TTB license lookup |
| ttb_license_number | Nambari ya leseni ya TTB (kama inajulikana) | Recommended | Enables immediate compliance check |
| service_type | Aina ya huduma | Yes | Hotel / Safari / Restaurant / Beach Resort / Tour Package / Transfer |
| booking_reference | Nambari ya mapanga / booking | Conditional | For reservation disputes; enables booking lookup |
| stay_dates | Tarehe za kukaa / safari | Yes | For complaint timeline |
| amount_paid_tzs_or_usd | Kiasi kilicholipwa (TZS / USD) | Conditional | For refund and overcharge complaints |
| payment_method | Njia ya malipo | Conditional | Cash / Card / Online — for fraud investigation |
| issue_type | Aina ya tatizo | Yes | TTB complaint taxonomy |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; detailed narrative |
| impact_on_trip | Athari kwa safari / likizo | Recommended | Quantifies the severity of the complaint |
| photos_available | Je, picha zinapatikana? | Recommended | Critical evidence for hotel and safari complaints |
| desired_outcome | Matokeo unayotaka | Yes | Refund / Apology / Service completion / Compensation |

### Conditional Fields (collect based on issue type)

**If issue_type = Booking Fraud / Non-Delivery:**
Also collect:
- `booking_platform` — Jukwaa la mapanga: Direct / Booking.com / Expedia / WhatsApp / Travel agent
- `amount_paid_receipt_available` — Je, risiti ya malipo inapatikana?: For fraud evidence
- `tour_operator_physical_address` — Anwani ya ofisi ya tour operator: For enforcement
- `communication_evidence` — Ushahidi wa mawasiliano: Emails, WhatsApp, website screenshots

**If issue_type = Hotel Quality / Room Condition:**
Also collect:
- `room_type_booked` — Aina ya chumba kilichopangwa: Standard / Deluxe / Suite / Sea view / Family
- `room_type_received` — Aina ya chumba kilichopokelewa
- `specific_deficiencies` — Mapungufu mahususi: Dirty / Broken AC / No hot water / Noise / Insects / Wrong view / Unsafe
- `complaint_raised_with_hotel` — Je, malalamiko yaliwasilishwa hotelini wakati wa kukaa? Yes / No
- `hotel_response_to_complaint` — Jibu la hoteli: Action taken / Offered alternative / Ignored

**If issue_type = Safari / Wildlife Guide Complaint:**
Also collect:
- `park_name` — Jina la hifadhi: Serengeti / Ngorongoro / Kilimanjaro / Ruaha / Selous / Zanzibar
- `guide_name` — Jina la mwongozo
- `guide_license_number` — Nambari ya leseni ya mwongozo: TAWA / TANAPA guides must be licensed
- `park_entry_receipt` — Nambari ya risiti ya kuingia hifadhini: For TANAPA verification
- `wildlife_promise_vs_reality` — Utalii wa wanyama: Wanyama walioahidiwa vs. kuonekana kweli
- `equipment_condition` — Hali ya vifaa vya safari: Vehicle, binoculars, camping gear

**If issue_type = Food Safety / Quality:**
Also collect:
- `dish_name` — Jina la chakula kilichohusika
- `illness_symptoms` — Dalili za ugonjwa: Vomiting / Diarrhea / Fever / Allergic reaction
- `number_affected` — Idadi ya watu walioathirika
- `medical_treatment_sought` — Je, matibabu yalitafutwa? Yes / No

**If issue_type = Overcharge / Hidden Fees:**
Also collect:
- `quoted_price_tzs_or_usd` — Bei iliyonukuliwa mwanzo
- `final_price_charged` — Bei ya mwisho iliyotozwa
- `itemized_receipt_available` — Je, ankara yenye maelezo ya kila malipo inapatikana?
- `hidden_charges_type` — Aina ya malipo ya ziada: Resort fee / City tax / Service charge / Park fee / Fuel surcharge

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| TH-01 | booking_fraud | Payment made but no service delivered; fraudulent operator |
| TH-02 | hotel_quality_mismatch | Hotel significantly below advertised or booked standard |
| TH-03 | overcharge_hidden_fees | Charged more than quoted; undisclosed fees |
| TH-04 | refund_refused | Hotel or tour operator refuses valid refund |
| TH-05 | safari_guide_misconduct | Guide rude, incompetent, or failed to show promised wildlife |
| TH-06 | food_poisoning | Illness from hotel/restaurant food |
| TH-07 | safety_hazard | Physical safety risk at hotel, boat, or safari vehicle |
| TH-08 | sexual_harassment | Sexual harassment by hotel staff or guide |
| TH-09 | theft | Theft of belongings from room or vehicle |
| TH-10 | discrimination | Differential treatment based on nationality or race |
| TH-11 | cancellation_dispute | Hotel or tour operator refusing cancellation refund |
| TH-12 | unlicensed_operator | Tour operator operating without TTB license |
| TH-13 | poor_customer_service | Rude, unresponsive, or unhelpful staff |
| TH-14 | transport_failure | Airport transfer or in-country transport not provided |
| TH-15 | park_entry_overcharge | Charged incorrect park entry fees |

### Resolution Standards

- **Hotel/Operator level:** Acknowledge within 24 hours; resolve within 14 days.
- **TTB:** TTB receives consumer complaints; investigation within 30 days; can suspend or revoke licenses.
- **TANAPA/NCAA:** Park-related complaints; investigation within 30 days; guide licenses can be revoked.
- **TAWA:** Wildlife area complaints.
- **TFDA (food safety):** Food poisoning reports; investigation within 15 days.
- **Required for TTB complaint:** Operator name, TTB license number, service type, dates, booking reference, description.

### Escalation Triggers

- `issue_type = booking_fraud` AND `ttb_license_number not found` — Immediate TTB enforcement; criminal referral for fraud
- `issue_type = food_poisoning` AND `number_affected >= 2` — TFDA outbreak investigation; MOHCDGEC notification
- `issue_type = sexual_harassment` AND by staff — Hotel management + TTB + police (criminal matter)
- `issue_type = safety_hazard` AND physical injury — Medical care priority; TTB safety investigation; TANAPA if park incident
- `issue_type = theft` AND hotel room — Police report; hotel security; insurance claim
- `issue_type = unlicensed_operator` — TTB enforcement; criminal referral; consumer advisory to avoid operator

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| provider_name | Mtoa huduma | Recommended | For routing |
| service_type | Aina ya huduma | Yes | Routes to correct team |
| suggestion_category | Kategoria | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| THS-01 | service_quality | Ubora wa huduma |
| THS-02 | staff_training | Mafunzo ya wafanyakazi |
| THS-03 | price_transparency | Uwazi wa bei |
| THS-04 | digital_booking | Mapanga ya kidijitali |
| THS-05 | sustainable_tourism | Utalii endelevu |
| THS-06 | local_culture | Ujumuishaji wa utamaduni wa Tanzania |
| THS-07 | safety_standards | Viwango vya usalama |
| THS-08 | community_benefit | Faida kwa jamii za jirani |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina | Recommended | For tracking |
| service_type | Aina ya huduma | Yes | Routes to correct answer |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| operator_license | Je, tour operator huu ana leseni ya TTB? | operator_name |
| park_fees | Ada za kuingia hifadhi ni kiasi gani? | park_name, nationality |
| booking_cancellation | Sera ya kufuta mapanga ni ipi? | provider_name, booking_reference |
| visa_for_tourism | Ninajua visa ya Tanzania kwa utalii | nationality |
| safari_planning | Ninawezaje kupanga safari ya Serengeti? | travel_dates, budget |
| halal_food | Je, hoteli hii ina chakula cha halal? | hotel_name |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| staff_name | Jina la mfanyakazi | Recommended | Staff recognition |
| provider_name | Mtoa huduma | Yes | Routes to management |
| service_type | Aina ya huduma | Yes | For routing |
| specific_aspect_praised | Kipengele | Yes | Karibisho / Usafi / Chakula bora / Safari nzuri / Mwongozo bora |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | TTB CSAT; tourism quality benchmarking |
| would_recommend | Je, ungependekeza kwa wengine? | Recommended | NPS indicator |

---

## AI Conversation Guidance for This Industry

- **For booking fraud, confirm TTB license status immediately.** "Tunaweza kuthibitisha kama tour operator au hoteli hii ina leseni ya TTB (Tanzania Tourist Board). Jina la kampuni ni nani?"
- **For hotel quality complaints, ask whether the complaint was raised during the stay.** Many hotels cannot remedy complaints made only after checkout. "Je, ulimwambia meneja wa hoteli kuhusu tatizo hili wakati bado ukiwa hotelini?"
- **For safari complaints, guide license verification is critical.** "Je, mwongozo ana nambari ya leseni? Au ni tour operator gani aliomtoa mwongozo huyu?"
- **For food poisoning, collect medical evidence.** If tourists seek medical attention, doctor's report is the strongest evidence. "Je, ulikwenda hospitali au kliniki? Daktari alithibitisha kuhusiana na chakula?"
- **For foreign tourist complaints, consider embassy assistance.** "Kama una ugumu mkubwa hapa Tanzania, ubalozi wa nchi yako unaweza pia kusaidia — unatoka nchi gani?"
- **For overcharge complaints with foreign currency, confirm the currency.** Tanzania tourism is typically priced in USD; confusion between TZS and USD pricing is common. "Nukuu ya awali ilikuwa katika sarafu gani — USD, EUR, au TZS?"

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Provider name | "Hoteli, lodge, au kampuni ya utalii inaitwa nini?" |
| TTB license | "Je, kampuni hii ina leseni ya TTB? Nambari ya leseni inaweza kuonekana kwenye makubaliano au tovuti" |
| Booking reference | "Mapanga yako yana nambari ya marejeleo (booking reference) — je, una nambari hiyo?" |
| Stay dates | "Tarehe ya kuingia na kutoka zilikuwa lini?" |
| Room type | "Uliomba chumba cha aina gani, na ulipewa chumba gani?" |
| Hotel response | "Je, ulilalamika hotelini wakati wa kukaa? Walisema au walifanya nini?" |
| Safari guide | "Mwongozo wa safari anaitwa nini, na ana nambari ya leseni?" |
| Park name | "Safari ilikuwa kwenye hifadhi gani — Serengeti, Ngorongoro, au nyingine?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | booking_fraud AND unlicensed_operator | Immediate TTB enforcement; criminal referral; consumer advisory |
| issue_type | food_poisoning AND number_affected >= 2 | TFDA outbreak report; MOHCDGEC notification; hotel food safety inspection |
| issue_type | sexual_harassment AND staff | Hotel management + TTB complaint + police; criminal matter |
| issue_type | safety_hazard AND injury | Medical care first; TTB + TANAPA/NCAA investigation if park |
| issue_type | theft AND hotel room | Police report + hotel security; travel insurance claim |
| issue_type | overcharge AND hidden_fees systematic | TTB consumer protection; advertise consumer advisory |
| ttb_license_number | not found in TTB register | Unlicensed operator; TTB enforcement; consumer warning |
| issue_type | park_entry_overcharge | TANAPA/NCAA complaint; correct fee verification from TTB |

---

*Sources: Tanzania Tourism Act Cap. 261, TTB Act, Tourism Regulations 2014, TANAPA Act Cap. 282, NCAA Act, TAWA regulations, TFDA Act Cap. 219, UNWTO Global Code of Ethics, ISO 10002:2018*
