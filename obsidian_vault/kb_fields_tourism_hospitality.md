---
tags: [industry-kb, field-standards, feedback-fields]
---
# Tourism / Hospitality — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: hotel, lodge, safari, tour operator, travel agency, tour guide, national park, game reserve, game drive, beach resort, airline, Zanzibar, Serengeti, Kilimanjaro, Ngorongoro, Tarangire, Ruaha, Selous, Pemba, Mafia Island, TANAPA, NCAA, KINAPA, Tanzania Tourist Board, TTB, TATO, tourist police, visa, Yellow Fever certificate, park fees, bush camp, tented camp, cultural tourism, mountain climbing, diving, snorkelling, dhow cruise, spice tour, accommodation, check-in, check-out, reservation, concierge, front desk, housekeeping, travel insurance, itinerary, transfer, full board, half board, all-inclusive, rack rate, e-visa, tour package, excursion, safari vehicle, game ranger, mpagazi, porter, hoteli, makazi, ziara, mbuga ya wanyama, mwelekezi wa utalii, bwawa la kuogelea

## Why Industry-Specific Fields Matter

Generic feedback fields cannot distinguish between a safari vehicle safety failure (requiring tour operator licence number, TANAPA park permit, and vehicle inspection data), a hotel billing dispute (requiring reservation reference, rack rate, and applied exchange rate), and a food poisoning incident affecting multiple guests (requiring a public health escalation to the district medical officer) — all of which require different evidence, regulatory bodies, and action timelines under Tanzania Tourist Board licensing rules, TANAPA regulations, and the Tanzania Food, Drugs and Cosmetics Act.

## Source Standards

- ABTA (Association of British Travel Agents) Complaint Registration Guidance and Holiday Complaint FAQs
- SetupMyHotel Front Office Guest Complaint Action Form (industry standard form)
- Contend Legal Event and Travel Complaint Guidance (UK Consumer Rights Act 2015 basis)
- Citizens Advice UK: Complaining About Events and Hotels
- UN Tourism (UNWTO) International Code for the Protection of Tourists
- ISO 18513:2021 (Tourism and related services vocabulary — field nomenclature basis)
- Tanzania Tourist Board (TTB) licensing requirements
- TANAPA (Tanzania National Parks Authority) visitor regulations
- Tanzania Food, Drugs and Cosmetics Act (for food poisoning escalation)

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| `complainant_name` | Jina la mlalamikaji | Yes | ABTA requires complainant identification for formal complaint registration; required for follow-up and acknowledgement |
| `complainant_contact` | Mawasiliano ya mlalamikaji (simu / barua pepe) | Yes | Required by ABTA and all formal complaint processes for acknowledgement within 14 days |
| `complainant_nationality` | Taifa la mlalamikaji | Recommended | UNWTO ICPT frames tourist protection by nationality; required for consular notifications and international complaint routing |
| `establishment_name` | Jina la hoteli / lodge / kampuni ya safari | Yes | SetupMyHotel: primary identifier for complaint routing; TTB uses operator name for licence verification |
| `establishment_type` | Aina ya biashara | Yes | Determines regulatory body with jurisdiction and applicable standards. Options: Hoteli / Lodge / Kambi / Operator wa Safari / Wakala wa Utalii / Mgahawa / Mwendeshaji wa Usafiri |
| `booking_reference` | Nambari ya uhifadhi / resevesheni | Yes | ABTA: "Upload your booking invoice"; SetupMyHotel: "Reservation Number"; links complaint to specific contracted service |
| `check_in_date` | Tarehe ya kuingia / kuwasili | Yes | SetupMyHotel: establishes the service period and contractual obligations in force |
| `check_out_date` | Tarehe ya kutoka / kuondoka | Conditional | SetupMyHotel; collect if complaint spans a stay; not applicable for day-tour complaints |
| `visit_date` | Tarehe ya ziara / tukio | Yes | For tours, safaris, day excursions: date when incident occurred |
| `room_number_or_unit` | Nambari ya chumba / kibanda | Conditional | SetupMyHotel: "Room Number/Apartment"; collect if complaint is accommodation-specific |
| `issue_type` | Aina ya tatizo / malalamiko | Yes | ABTA, SetupMyHotel, and Citizens Advice all require issue categorization to route to correct department and determine applicable remedy standard |
| `issue_description` | Maelezo ya tatizo | Yes | SetupMyHotel: "Nature of Complaint"; ABTA: detailed narrative required for formal complaint file |
| `date_and_time_of_incident` | Tarehe na saa ya tukio | Yes | SetupMyHotel: required field; needed for staff shift identification, CCTV retrieval, and correlation with records |
| `location_of_incident` | Mahali pa tukio | Yes | SetupMyHotel: "Location of Incident" — pool, room, restaurant, vehicle, beach, trail, etc. |
| `staff_involved` | Wafanyakazi waliohusika | Recommended | SetupMyHotel: "Staff Involved"; required for staff conduct investigations |
| `witnesses` | Mashahidi (kama wapo) | Recommended | SetupMyHotel: "Witnesses"; corroborates the complaint |
| `tour_operator_licence_number` | Nambari ya leseni ya operator (kama inajulikana) | Recommended | TTB requires licensed operators; licence number enables regulatory verification and enforcement action |
| `desired_outcome` | Matokeo unayotaka | Yes | ABTA and Contend Legal: complainant must state what they want — refund, apology, compensation, replacement service |
| `supporting_evidence` | Ushahidi wa kusaidia (picha, risiti, mawasiliano) | Recommended | ABTA: "Upload correspondences, booking invoice or ATOL certificate"; evidence is required for formal resolution and regulatory escalation |
| `complaint_raised_with_establishment` | Je, umeshalalamika kwa hoteli / operator moja kwa moja? | Yes | ABTA and Contend Legal require complainant to first raise with provider; establishes escalation eligibility |
| `establishment_response` | Jibu la hoteli / operator (kama lipo) | Conditional | Required to assess whether internal resolution was attempted; needed for any TTB or consumer protection escalation |

### Conditional Fields (collect based on issue type)

**If `issue_type = hygiene_or_food_poisoning`:**
Also collect:
- `meal_date_and_time` — Tarehe na saa ya mlo: For correlation with food preparation records
- `food_items_consumed` — Vyakula vilivyoliwa: For food safety investigation
- `medical_treatment_sought` — Je, ulipata matibabu? Yes/No: For public health reporting threshold
- `number_of_people_affected` — Idadi ya watu walioathirika: Public health escalation trigger if >2 guests

**If `issue_type = billing_dispute` OR `overcharging`:**
Also collect:
- `amount_charged_usd_or_tzs` — Kiasi kilichochukuliwa (USD/TZS): For financial remedy calculation
- `amount_expected_usd_or_tzs` — Kiasi kilichotarajiwa: Documents overcharge amount
- `exchange_rate_applied` — Kiwango cha ubadilishaji wa fedha kilichotumika: Common issue in Tanzania; operators must disclose exchange rate per TTB good practice
- `additional_charges_undisclosed` — Ada zisizotangazwa (huduma, kodi, nk): List undisclosed fees applied

**If `issue_type = safety_hazard`:**
Also collect:
- `hazard_type` — Aina ya hatari: Structural / wildlife / water / vehicle / equipment / fire
- `injury_or_harm_occurred` — Je, kulikuwa na jeraha au madhara? Yes/No: Personal injury triggers police and insurance escalation
- `emergency_services_contacted` — Je, huduma za dharura ziliitwa? Yes/No

**If `issue_type = misleading_description` OR `advertising_mismatch`:**
Also collect:
- `advertised_standard` — Ubora ulioahidiwa (kwa mfano, nyota 4, chumba cha bahari): What was advertised
- `actual_standard_received` — Ubora uliokutana nazo: What was actually delivered
- `promotional_material_source` — Chanzo cha matangazo: Website / brochure / booking platform / verbal promise

**If `issue_type = tour_operator_fraud` OR `deposit_not_refunded`:**
Also collect:
- `amount_paid_deposit_usd` — Amana iliyolipwa (USD): For financial fraud quantification
- `operator_contact_attempted` — Je, umejaribu kuwasiliana na operator? Responses received?
- `ttb_licence_verified` — Je, operator ana leseni ya TTB? Yes/No/Unknown: Enables regulatory check

**If `issue_type = staff_misconduct` OR `harassment`:**
Also collect:
- `harassment_type` — Aina ya unyanyasaji: Sexual / racial / verbal / physical
- `police_report_filed` — Je, ripoti ya polisi imewasilishwa? Yes/No: Required for criminal matters; tourist police unit referral

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| TH-01 | `hygiene_cleanliness_failure` | Unclean rooms, pests, unhygienic food preparation |
| TH-02 | `food_poisoning_illness` | Foodborne illness attributed to hotel/lodge food |
| TH-03 | `safety_hazard` | Structural, wildlife, vehicle, or equipment safety risk |
| TH-04 | `misleading_description` | Advertised service/standard does not match reality |
| TH-05 | `overcharging_billing_dispute` | Incorrect charges, undisclosed fees, exchange rate fraud |
| TH-06 | `booking_dispute_no_show` | Confirmed booking not honoured; overbooking |
| TH-07 | `cancellation_refund_denied` | Refund withheld after cancellation or service failure |
| TH-08 | `seating_accommodation_mismatch` | Room or seat category different from what was booked |
| TH-09 | `staff_misconduct_harassment` | Rude, discriminatory, or sexually harassing staff |
| TH-10 | `theft_loss_of_property` | Guest property stolen or lost on premises |
| TH-11 | `tour_operator_fraud` | Operator took payment without delivering service; unlicensed operator |
| TH-12 | `wildlife_encounter_mishandled` | Safari incident where operator failed to ensure guest safety near wildlife |
| TH-13 | `accessibility_failure` | Disability access requirement not met |
| TH-14 | `internet_amenity_failure` | Promised facility (wifi, pool, AC) not available |
| TH-15 | `noise_disturbance` | Construction, events, or other disruption affecting stay |
| TH-16 | `food_allergy_ignored` | Documented dietary requirement or allergy not accommodated |
| TH-17 | `transport_failure` | Transfer, vehicle breakdown, or schedule change leaving guest stranded |

### Resolution Standards for This Industry

- **Internal resolution:** ABTA standard — operator must acknowledge within 14 days and provide substantive response within 28 days.
- **TTB escalation (Tanzania):** Complainants can file with Tanzania Tourist Board against licensed operators; TTB can suspend or revoke licences for sustained non-compliance.
- **Food poisoning (public health):** Incidents affecting 3+ guests must be reported to the district medical officer and TFDA (Tanzania Food, Drugs and Cosmetics Act); hotel management has a duty to report.
- **Criminal matters (theft, assault):** Refer to Tanzania Police Tourist Unit; for foreign nationals, embassy/consulate notification may be warranted.
- **TANAPA violations (park incidents):** Escalate to TANAPA or NCAA/KINAPA depending on park; park rangers have authority to investigate in-park incidents.
- **Required documentation:** Booking confirmation, payment receipt, photographic evidence, medical records (if applicable), prior correspondence with operator.

### Escalation Triggers (field values that require immediate escalation)

- `issue_type = safety_hazard` AND `injury_or_harm_occurred = Yes` — Immediate escalation to tourist police unit; advise medical attention; create emergency priority ticket
- `issue_type = food_poisoning_illness` AND `number_of_people_affected >= 3` — Public health emergency; notify district medical officer and TFDA within 24 hours
- `issue_type = tour_operator_fraud` AND `ttb_licence_verified = No` — Unlicensed operator; escalate to TTB enforcement unit immediately
- `issue_type = wildlife_encounter_mishandled` AND `injury_or_harm_occurred = Yes` — TANAPA/NCAA incident report; park authority must be notified
- `issue_type = staff_misconduct_harassment` AND `harassment_type = Sexual` — Escalate to police and tourist police unit; victim safety assessment first
- `issue_type = theft_loss_of_property` AND includes passport or travel documents — Escalate to police AND relevant embassy/consulate; document seizure protocol
- `issue_type = booking_dispute_no_show` AND tourist is stranded with no accommodation — Welfare emergency; immediate re-accommodation assistance required
- `issue_type = transport_failure` AND guest is stranded in remote location — Emergency welfare flag; coordinate with TANAPA/operator for rescue

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `submitter_name` | Jina la mtoa maoni (hiari) | Optional | Suggestions may be anonymous per best practice |
| `establishment_or_operator` | Hoteli / Operator / Mbuga inayohusika | Yes | Routes suggestion to correct entity or regulatory body |
| `suggestion_category` | Kategoria ya mapendekezo | Yes | Enables routing to correct department (operations, safety, sustainability, etc.) |
| `suggestion_detail` | Maelezo ya mapendekezo | Yes | Free text; core content |
| `visit_date` | Tarehe ya ziara | Recommended | Provides context for suggestions about seasonal or operational conditions |
| `establishment_type` | Aina ya biashara inayohusika | Yes | Determines applicable standards and routing |

### Industry-Specific Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| THS-01 | `service_quality` | Ubora wa huduma |
| THS-02 | `safety_and_security` | Usalama wa wageni |
| THS-03 | `sustainability` | Uendelevu na mazingira |
| THS-04 | `accessibility` | Upatikanaji kwa walemavu |
| THS-05 | `pricing_transparency` | Uwazi wa bei na ada |
| THS-06 | `guide_training` | Mafunzo ya mwelekezi |
| THS-07 | `digital_booking` | Teknolojia ya uhifadhi mtandaoni |
| THS-08 | `food_quality` | Ubora wa chakula |
| THS-09 | `responsible_wildlife_tourism` | Utalii wa wanyama wenye uwajibikaji |
| THS-10 | `community_benefit` | Faida kwa jamii ya karibu |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `inquirer_name` | Jina la mwulizaji (hiari) | Optional | Not required for general inquiries |
| `inquiry_type` | Aina ya swali | Yes | Routes to correct knowledge base or referral path |
| `establishment_type_of_interest` | Aina ya biashara inayohusika | Yes | Determines which knowledge base or authority can answer |
| `destination_or_park` | Mahali / mbuga inayohusika | Recommended | For park fee, permit, or activity inquiries — enables accurate fee/regulation data |
| `travel_date` | Tarehe ya safari iliyopangwa | Recommended | For seasonal advice (migration, peak/off-peak, weather) |
| `budget_indication` | Bajeti takriban | Optional | For package or pricing inquiries |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Swahili | Additional Fields Needed |
|-------------|---------|--------------------------|
| `booking_status` | Hali ya resevesheni yangu | `booking_reference`, `establishment_name` |
| `refund_status` | Hali ya marejesho ya pesa | `booking_reference`, `amount_paid`, `cancellation_date` |
| `park_fees` | Ada za kuingia mbuga | `destination_or_park`, `visitor_category` (non-resident/resident/citizen) |
| `visa_requirements` | Mahitaji ya visa | `complainant_nationality`, `destination` |
| `accessibility_requirements` | Mahitaji ya ulemavu | `disability_type`, `establishment_type_of_interest` |
| `tour_operator_licence_check` | Je, operator ana leseni halali? | `establishment_name`, `operator_type` |
| `best_time_to_visit` | Wakati bora wa kutembelea | `destination_or_park`, `interests` |
| `safety_current_conditions` | Hali ya usalama sasa | `destination_or_park` |
| `cancellation_policy` | Sera ya kufuta nafasi | `booking_reference`, `establishment_name` |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `submitter_name` | Jina la mtoa pongezi (hiari) | Optional | For acknowledgement; operator recognition schemes value guest names |
| `establishment_or_staff_recognized` | Hoteli / Operator / Mfanyakazi anayepongezwa | Yes | Routes compliment to correct entity and staff record |
| `role_of_staff_recognized` | Wadhifa wa mfanyakazi (kama anajulikana) | Recommended | Guide / receptionist / chef / manager / porter — for targeted recognition |
| `what_stood_out` | Kilichokuvutia / kilichotukuka | Yes | Specific positive behavior or experience for institutional learning |
| `visit_date` | Tarehe ya ziara | Recommended | For correlation with staff performance records |
| `would_return_or_recommend` | Je, ungerudi au kupendekeza kwa mwingine? | Yes | Net Promoter Signal; valuable for operator and TTB destination promotion data |
| `specific_aspect_praised` | Kipengele maalum kilichopongezwa | Yes | Guides / food / cleanliness / safety / value for money / sustainability |

---

## AI Conversation Guidance for This Industry

- **Identify the establishment type before asking about the problem.** Ask "Unazungumzia hoteli, lodge, kampuni ya safari, au kitu kingine?" first — a safari operator complaint and a hotel billing complaint require completely different fields, regulatory bodies, and evidence standards.
- **Get the booking reference early and treat it as the anchor.** Say "Una nambari ya uhifadhi au risiti ya malipo yako?" — this single field unlocks the entire contractual record and avoids disputes about what was promised versus delivered.
- **For food or health complaints, ask immediately how many people were affected.** "Je, wewe peke yako uliugua, au watu wengine pia waliohudhuria mlo huo waliathirika?" — if the number is 3 or more, a public health escalation is needed alongside the complaint, and the AI should flag this.
- **For safety or assault complaints, prioritize the person's physical safety before collecting fields.** If there is any indication of physical harm, confirm: "Je, uko salama sasa hivi? Je, unahitaji msaada wa haraka wa matibabu au polisi?" Provide emergency contacts (police: 112, tourist police unit) before completing the complaint form.
- **Do not ask for the TTB licence number directly** — most tourists do not know it. Instead, ask for the operator's full name and whether they received a written contract or booking confirmation, which enables TTB to verify the licence independently.
- **For safari complaints, ask about the vehicle separately from the guide.** Vehicle safety (condition, capacity, roof hatch) and guide competence are investigated by different parties (TANAPA vs. the tour operator); separating them produces clearer, more actionable complaints.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Establishment name | "Jina la hoteli, lodge, au kampuni ya safari ni nini?" |
| Booking reference | "Una nambari ya uhifadhi, nambari ya resevesheni, au risiti ya malipo yako?" |
| Issue type | "Tatizo lako ni nini hasa — uchafu, usalama, bei, mwelekezi, au kitu kingine?" |
| Date of incident | "Hili lilitokea lini — tarehe na saa ngapi kama unajua?" |
| Location of incident | "Tukio hili lilitokea wapi hasa — chumbani, bwawani, garilini, au mahali pengine?" |
| Number affected | "Je, wewe peke yako uliathirika, au watu wengine pia?" |
| Prior complaint to establishment | "Je, ulishalalamika kwa meneja wa hoteli au operator moja kwa moja? Walikusema nini?" |
| Evidence available | "Una picha, stakabadhi, au mawasiliano yoyote (barua pepe, ujumbe) kuhusu tatizo hili?" |
| Desired outcome | "Unataka nini kitokee — kurejeshewe pesa, ombi la msamaha, fidia, au kitu kingine?" |
| Would recommend | "Kwa ujumla, ungependekeza hoteli / ziara hii kwa rafiki yako baada ya uzoefu huu?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| `issue_type` | `food_poisoning_illness` AND `number_of_people_affected >= 3` | Public health emergency ticket; notify district medical officer and TFDA; advise complainant to seek medical documentation |
| `issue_type` | `safety_hazard` AND `injury_or_harm_occurred = Yes` | Emergency priority ticket; provide tourist police number; advise medical attention; notify TANAPA if in-park incident |
| `issue_type` | `tour_operator_fraud` AND `ttb_licence_verified = No` | Escalate to TTB enforcement; advise complainant this is an unlicensed operator complaint; provide TTB complaint contact |
| `issue_type` | `wildlife_encounter_mishandled` AND injury occurred | TANAPA/NCAA/KINAPA incident report required; create high-priority ticket with park authority referral |
| `issue_type` | `staff_misconduct_harassment` AND `harassment_type = Sexual` | Police and tourist police unit escalation; victim safety check first; provide crisis support reference |
| `issue_type` | `theft_loss_of_property` AND includes passport/documents | Escalate to police AND embassy/consulate; document seizure emergency protocol |
| `complaint_raised_with_establishment` | Yes AND `establishment_response` = unsatisfactory OR no response | Advise TTB escalation; provide TTB complaint submission link and contacts |
| `desired_outcome` | Refund AND `booking_reference` confirmed | Route to financial remedy track; confirm refund eligibility under cancellation policy; document amount for claim |
| `establishment_type` | Tour operator AND `booking_reference` exists | Verify against TTB licensed operator database; flag if licence cannot be verified |
| `issue_type` | `accessibility_failure` | Route to establishment accessibility compliance desk; reference UNWTO tourist rights framework |

---

*Sources: ABTA Complaint Registration Guidance and Holiday Complaint FAQs, SetupMyHotel Front Office Guest Complaint Action Form, Contend Legal Event and Travel Complaint Guidance, Citizens Advice UK (Events and Hotels), UNWTO International Code for the Protection of Tourists, ISO 18513:2021, Tanzania Tourist Board licensing requirements, TANAPA visitor regulations, Tanzania Food Drugs and Cosmetics Act*
