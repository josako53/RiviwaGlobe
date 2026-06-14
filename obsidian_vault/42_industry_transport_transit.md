---
tags: [industry-kb, feedback-classification, field-standards]
---
# Transport / Public Transit — Feedback Collection Fields & Standards

## Industry Identifiers

daladala, BRT, UDART, bodaboda, bajaji, boda boda, tuk-tuk, Bolt, Uber, Little, SGR, TAZARA, ferry, MV Bukoba, Zanzibar ferry, JNIA, SUMATRA, LATRA, intercity bus, coach, Dar Express, Kilimanjaro Express, Royal Coach, Scandinavian Express, airport taxi, railway, station, conductor, driver, manifest, fare, ticket, route permit, upcountry bus, Lake Victoria ferry, Mwanza ferry, port transfer, bus terminal, platform, boarding pass, transit, public transport, matatu, basi, nauli, route deviation, overloading, PSV license, route permit, passenger manifest

## Why Industry-Specific Fields Matter

Generic feedback fields miss the regulatory chain that governs transport complaints in Tanzania — LATRA 2024 requires specific vehicle and route identifiers before a complaint can be formally escalated to the authority, and safety-critical incidents (accidents, injuries, overloading) trigger mandatory notification timelines that differ from commercial disputes. Without mode, route, vehicle registration, and incident time, the AI cannot distinguish a fare overcharge requiring mediation from a road accident requiring immediate emergency escalation.

## Source Standards

- Tanzania LATRA Complaint Handling Procedures Rules 2024 (GN No. 16 of 2024) — mandatory complaint fields, 7-day rule, 21-day supplier response window
- Tanzania SUMATRA Complaints and Review Rules 2008 — vehicle and operator identification requirements
- EU Regulation 261/2004 — departure/destination fields, care obligations for delayed passengers
- EU Regulation 1371/2007 — rail passenger delay rights
- ITF Discussion Paper DP2013/16: Measuring and Valuing Convenience and Service Quality — route-level quality dimensions
- NTSB 49 CFR Part 830 — injury classification and mandatory notification thresholds
- NHTSA Vehicle Owner Questionnaire (VOQ) system — incident context, police report fields
- OTIF CIV Uniform Rules (COTIF Appendix A) — rail passenger journey fields
- IATA Consumer Protection Principles — affected passenger count, care obligations
- Athens Convention 2002 (PAL) — maritime passenger luggage liability fields

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| transport_mode | Aina ya usafiri | Yes | Determines which regulator handles the complaint (LATRA for road, SUMATRA for ferries/marine, Tanzania Railways for SGR/TAZARA, TCAA for airport transfers); drives all downstream field logic |
| route_number_or_name | Nambari/jina la njia | Yes | LATRA 2024 requires route-level identification; enables pattern detection across repeated route violations |
| vehicle_registration | Nambari ya usajili wa gari | Yes | LATRA 2024 mandatory; allows regulator to pull vehicle and operator records instantly |
| driver_name_or_badge | Jina/nambari ya dereva | Recommended | LATRA 2024; enables direct disciplinary action against the specific driver rather than just the company |
| incident_date | Tarehe ya tukio | Yes | LATRA 2024; NTSB 49 CFR 830; triggers the 7-day consumer complaint window and 21-day supplier response deadline |
| incident_time | Wakati wa tukio | Yes | Corroborates with vehicle logs, CCTV, and passenger manifests |
| departure_point | Mahali pa kuanzia | Yes | EU 261/2004 Article 3; OTIF CIV; required to verify the passenger was on the route and the operator was operating the route at that time |
| destination_point | Mahali pa kwenda | Yes | Same sources; needed to establish the passenger's contracted journey |
| issue_type | Aina ya tatizo | Yes | Drives the conditional field logic below; determines escalation path |
| incident_description | Maelezo ya tukio | Yes | LATRA 2024; NTSB; provides the narrative record for regulatory referral |
| complainant_full_name | Jina kamili la mlalamikaji | Yes | LATRA 2024 requires named complainant (anonymous complaints accepted only where merit is evident) |
| complainant_phone | Nambari ya simu | Yes | LATRA 2024; required for follow-up and resolution notification |
| complainant_email | Barua pepe | Recommended | LATRA 2024; for formal written responses |
| number_of_passengers_affected | Idadi ya abiria walioathirika | Recommended | EU 261/2004 Articles 9 and 12; IATA; scales the urgency and care obligations |

### Conditional Fields (collect based on issue type)

**If issue_type = Accident / Collision or Dangerous Driving:**
- `injury_occurred` — Was anyone injured? [Yes / No] — NTSB 49 CFR Part 830; NHTSA VOQ
- `injury_severity` — [None / Minor / Serious / Fatal] — NTSB Part 830.5 (serious injury triggers 24-hour mandatory notification)
- `injury_description` — Description of injuries sustained — Athens Convention (PAL) 2002 claim elements
- `police_report_filed` — Was a police report filed? [Yes / No] — NHTSA VOQ
- `police_report_number` — Police report reference number — LATRA 2024; NHTSA VOQ
- `police_station_name` — Name and location of police station — LATRA 2024
- `witness_names_contacts` — Witness names and contacts — NTSB witness reporting guidance
- `evidence_photos_video` — Photos or video [file upload] — NHTSA VOQ; LATRA 2024
- `vehicle_speed_estimate` — Estimated speed at time of incident — NHTSA VOQ incident context
- `road_conditions` — Road conditions [Dry / Wet / Murram / Highway / Urban] — NHTSA VOQ

**If issue_type = Overcharging / Fare Dispute:**
- `amount_paid` — Amount actually paid — LATRA 2024
- `correct_fare_known` — Correct fare as displayed or known — LATRA 2024
- `receipt_issued` — Was a receipt issued? [Yes / No] — SUMATRA 2008
- `receipt_photo` — Photo of receipt if issued [file upload]

**If issue_type = Luggage Lost or Damaged:**
- `luggage_description` — Description of luggage/contents — IATA PIR standard; Athens Convention 2002 Article 3
- `luggage_weight_kg` — Approximate weight (kg) — IATA PIR
- `declared_value` — Estimated value of lost/damaged items — Athens Convention; IATA
- `pir_reference` — Property Irregularity Report (PIR) number if issued — IATA PIR system
- `luggage_photos` — Photos of damaged luggage [file upload] — IATA; NHTSA documentation principle

**If issue_type = Late Arrival / Excessive Delay:**
- `scheduled_departure_time` — Scheduled departure time — EU 261/2004; OTIF CIV
- `actual_departure_time` — Actual departure time — EU 261/2004
- `delay_duration_minutes` — Total delay in minutes — EU 1371/2007 (rail: 60+ min triggers compensation)
- `notification_received` — Were passengers notified of the delay? [Yes / No / Only when asked] — ITF service quality standard

**If issue_type = Sexual Harassment / Assault:**
- `perpetrator_role` — [Driver / Conductor / Fellow Passenger / Station Staff / Other]
- `incident_location_detail` — Precise location (seat number, specific area of vehicle)
- `witnesses_present` — Were witnesses present? [Yes / No]
- `reported_to_police` — Was incident reported to police? [Yes / No]
- `police_ob_number` — Police OB (Occurrence Book) number

**If complaint was first filed with the service provider (LATRA 2024 pre-escalation requirement):**
- `complained_to_provider_first` — Did you complain to the service provider first? [Yes / No] — LATRA 2024 requires this before escalating to LATRA
- `date_complained_to_provider` — Date complaint was made to provider — LATRA 2024 (7-day window)
- `provider_response_received` — Provider response received? [Yes / No / No response within 21 days] — LATRA 2024 (21-day supplier response deadline)
- `provider_response_description` — Summary of provider's response — LATRA 2024

### Issue Type Classification

- `OVERCHARGING` — Fare dispute, excess charge, no receipt, price higher than displayed
- `DRIVER_CONDUCT_RECKLESS` — Over-speeding, phone use while driving, reckless overtaking
- `DRIVER_CONDUCT_ABUSE` — Verbal abuse, harassment, refusal to assist disabled passengers
- `ACCIDENT_COLLISION` — Road accident, collision, vehicle rollover
- `ROUTE_DEVIATION` — Dropped passengers before destination, illegal route change
- `NO_SHOW_DEPARTURE_FAILURE` — Bus did not depart, did not show up, cancelled without notice
- `EXCESSIVE_DELAY` — Late departure, late arrival, unexplained stops
- `VEHICLE_BREAKDOWN` — Breakdown during journey, mechanical failure
- `OVERLOADING` — Passenger overcrowding beyond legal capacity
- `VEHICLE_CONDITION` — Faulty brakes, no seatbelts, broken seats, unsanitary conditions
- `LUGGAGE_LOST` — Missing luggage, parcel not delivered
- `LUGGAGE_DAMAGED` — Items damaged during transport
- `SEXUAL_HARASSMENT` — Sexual harassment or assault by transport staff or in vehicle
- `ACCESSIBILITY_FAILURE` — No ramp, no priority seating, refusal to assist person with disability
- `BOOKING_TICKETING` — Booking not honored, system failure, refund refused
- `FARE_SYSTEM_FAILURE` — BRT card not accepted, balance error, card not loading

### Resolution Standards for This Industry

- **LATRA 2024**: Consumer must first complain to the service provider within 7 days of the incident. The provider has 21 days to respond. If no satisfactory response, the consumer may escalate to LATRA.
- **SUMATRA 2008**: Marine transport complaints follow SUMATRA's own review process with formal written submission.
- **EU Regulation 1371/2007 (rail)**: For delays exceeding 60 minutes, passengers are entitled to 25% of the ticket price; delays over 120 minutes entitle passengers to 50%. These principles inform SGR/TAZARA complaint handling.
- **Athens Convention (PAL) 2002**: Carrier liability for luggage damage/loss on ferries is up to SDR 2,700 per passenger. Complaints must be submitted in writing.
- **OTIF CIV**: Rail passenger must submit complaint to the carrier within 12 months of the incident.
- **Safety incidents (NTSB principle)**: Accidents involving serious injury must be notified to the relevant authority within 24 hours.

### Escalation Triggers (field values that require immediate escalation)

- `injury_severity` = Serious or Fatal → immediate emergency referral; notify LATRA, Traffic Police, and relevant emergency services
- `issue_type` = ACCIDENT_COLLISION + `injury_occurred` = Yes → escalate within 1 hour; cross-notify SUMATRA or Tanzania Railways as applicable
- Ferry or vessel reported overloaded and about to depart → imminent safety risk; contact Tanzania Harbours Authority (THA)
- `issue_type` = DRIVER_CONDUCT_RECKLESS + vehicle still in motion with passengers → real-time emergency
- `issue_type` = SEXUAL_HARASSMENT → escalate to senior staff immediately; preserve complainant privacy; advise police reporting
- Driver confirmed intoxicated with passengers on board → emergency notification; do not wait for provider response
- Bus/vehicle locks passengers inside and deviates route → LATRA emergency line
- `issue_type` = LUGGAGE_LOST + `declared_value` > TZS 1,000,000 → formal carrier liability claim; Athens Convention thresholds apply for ferry cargo
- Child travelling alone confirmed missing at terminal → immediate referral to police and THA/LATRA as applicable

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| transport_mode_affected | Aina ya usafiri inayoathiriwa | Yes | Ensures suggestion is routed to the correct operator and regulator |
| route_or_service_affected | Njia au huduma inayoathiriwa | Recommended | ITF DP2013/16 recommends route-level service measurement for quality improvement |
| suggestion_category | Aina ya pendekezo | Yes | Categorizes for operator routing and trend analysis |
| suggestion_detail | Maelezo ya pendekezo | Yes | The substantive content |
| perceived_priority | Kipaumbele | Recommended | ITF service quality framework; helps operators triage improvements |
| submitter_contact | Mawasiliano ya mtoa pendekezo | Optional | For follow-up on adoption |

### Industry-Specific Improvement Categories

- `SAFETY_VEHICLE_STANDARDS` — Speed limiters, seatbelts, roadworthiness enforcement, CCTV
- `SCHEDULE_RELIABILITY` — Real-time tracking apps, SMS delay alerts, on-time performance
- `FARE_TRANSPARENCY` — Displayed fares, receipts, M-Pesa payments, no hidden charges
- `DRIVER_CONDUCT_TRAINING` — Safety training, customer service, anti-harassment protocols
- `INFRASTRUCTURE_ROUTES` — New routes, better stops, shelter at terminals, accessible ramps
- `REGULATION_ENFORCEMENT` — LATRA/SUMATRA enforcement, digital permits, public violation reporting
- `ENVIRONMENTAL` — Cleaner vehicles, fuel efficiency standards, emissions
- `ACCESSIBILITY_INCLUSION` — Ramps, priority seating, audio announcements, Swahili-only announcements
- `TECHNOLOGY_DIGITAL` — E-ticketing, apps, USSD booking, BRT card via M-Pesa

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| inquiry_type | Aina ya swali | Yes | Routes the inquiry to the correct information source |
| transport_mode | Aina ya usafiri | Yes | Narrows answer scope immediately |
| route_or_service | Njia au huduma | Recommended | Needed for fare, schedule, and route questions |
| travel_date | Tarehe ya safari | Conditional | Required for booking, schedule, and seat-related inquiries |
| contact_for_response | Mawasiliano ya kujibu | Recommended | Enables callback or SMS response |

### Common Inquiry Types & Required Data Per Type

- `ROUTE_QUERY` → transport_mode, departure_point, destination_point
- `SCHEDULE_QUERY` → transport_mode, route_or_service, travel_date
- `FARE_QUERY` → transport_mode, route_or_service; travel_date if peak/off-peak rates differ
- `BOOKING_QUERY` → transport_mode, travel_date, number_of_passengers
- `LOST_PROPERTY` → transport_mode, vehicle_registration (if known), date_of_travel, description_of_lost_item; IATA PIR reference if already filed
- `OPERATOR_LICENSING` → vehicle_registration or operator_name; SUMATRA/LATRA licensing status
- `REFUND_QUERY` → ticket_reference, date_of_travel, reason_for_cancellation
- `BRT_CARD_QUERY` → card_number (if available), issue_type (balance error / card lost / not accepted)
- `SAFETY_REGULATION` → topic (helmets / speed limits / roadworthiness); operator or vehicle in question

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| transport_mode | Aina ya usafiri | Yes | Routes compliment to the correct operator for recognition |
| route_or_service | Njia au huduma | Recommended | Enables route-level positive performance tracking (ITF quality measurement) |
| driver_or_staff_name | Jina la dereva/mfanyakazi | Recommended | Enables specific staff recognition and rewards |
| vehicle_registration | Nambari ya gari | Recommended | Corroborates the compliment and identifies the specific vehicle |
| incident_date | Tarehe | Yes | Anchors the compliment to a specific service event |
| positive_behavior_description | Maelezo ya tabia nzuri | Yes | The substantive record for staff recognition and training use |
| positive_behavior_category | Aina ya mwenendo mzuri | Recommended | Enables trend analysis of what is working well |
| submitter_contact | Mawasiliano ya mtoa sifa | Optional | For acknowledgement and verification if needed |

---

## AI Conversation Guidance for This Industry

- **Start with mode, then route:** Open with "Okay, let me help you — which type of transport was this? A daladala, intercity bus, BRT, bodaboda, ferry, or something else?" Mode determines everything else — which regulator, which fields, which resolution path. Do not jump to problem details before establishing mode and route.
- **Collect the vehicle registration conversationally:** Rather than "please provide vehicle registration," ask "Did you happen to see or note down the bus or vehicle number — it's usually on a plate at the front or back of the vehicle? Even a partial number helps." Many passengers in East Africa do note this because they know it matters.
- **Handle injury/safety signals urgently and separately:** If the person mentions an accident, injury, or dangerous driving, shift tone immediately. Ask "Are you and any other passengers safe right now?" before continuing to collect complaint fields. Provide the LATRA emergency line or direct emergency contact if the incident is ongoing.
- **Explain the LATRA 2024 pre-complaint rule naturally:** If the complaint is ready for formal escalation, tell the user: "To formally escalate this to LATRA, we need to know if you already complained to the bus company first — LATRA requires this step. Did you? If yes, when, and what did they say?" This prevents the complaint from being rejected on procedural grounds.
- **Never ask for sexual harassment details bluntly:** If the user signals harassment ("the driver touched me" or "I was assaulted"), respond with empathy first ("I'm very sorry this happened to you"), confirm the person is safe, then ask only what is needed for the record (role of the perpetrator, approximate location, whether they wish to involve police). Do not ask for graphic descriptions.
- **For Swahili-speaking users:** Use the Swahili key phrases below naturally in conversation; do not switch awkwardly between languages.

## Swahili Key Phrases for Field Collection

- "Usafiri huu ulikuwa wa aina gani — daladala, basi la masafa, BRT, bodaboda, au kivuko?" — What type of transport was this?
- "Njia au nambari ya basi ilikuwa gani?" — What was the bus route or number?
- "Uliona nambari ya usajili wa gari? Hata sehemu ya nambari inaweza kusaidia." — Did you see the vehicle registration number? Even part of the number can help.
- "Tukio hili lilitokea lini — tarehe na takriban saa ngapi?" — When did this happen — date and approximately what time?
- "Ulitoka wapi na ulikuwa unakwenda wapi?" — Where did you depart from and where were you going?
- "Je, mtu yeyote alijeruhiwa katika tukio hili?" — Was anyone injured in this incident?
- "Je, uliwasiliana na kampuni ya basi kuhusu tatizo hili kwanza?" — Did you contact the bus company about this issue first?
- "Ungependa kutoa jina lako na nambari ya simu ili tuweze kukufuatilia?" — Would you like to share your name and phone number so we can follow up with you?
- "Kuna ushahidi wowote — picha, video, au shahidi — unaouhusiana na tukio hili?" — Is there any evidence — photos, video, or witnesses — related to this incident?
- "Ulikuwa umebeba mzigo wowote ambao umepotea au kuharibika?" — Were you carrying any luggage that was lost or damaged?

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| injury_severity | Fatal | Immediate emergency escalation; notify LATRA, police, Tanzania Harbours Authority (marine) or Tanzania Railways (rail) within 1 hour; preserve all complaint data |
| injury_severity | Serious | Escalate within 24 hours per NTSB 49 CFR 830.5 principle; flag for LATRA formal complaint |
| issue_type | SEXUAL_HARASSMENT | Escalate to senior staff immediately; advise police OB filing; offer referral to GBV support; do not share complainant details without consent |
| issue_type | OVERLOADING + ferry or vessel | Contact THA immediately; this is an imminent maritime safety risk |
| issue_type | DRIVER_CONDUCT_RECKLESS + vehicle_in_motion | Treat as live emergency; advise passenger to call 114 (police) or 115 (fire/ambulance) |
| complained_to_provider_first | No | Advise complainant to file with the operator first; provide LATRA escalation guidance for if no response within 21 days |
| provider_response_received | No response within 21 days | Formally eligible for LATRA escalation; initiate referral |
| transport_mode | Ferry / vessel | Route to SUMATRA and THA; apply Athens Convention (PAL) 2002 liability framework for luggage claims |
| transport_mode | SGR or TAZARA | Route to Tanzania Railways Corporation; apply OTIF CIV delay compensation framework |
| delay_duration_minutes | > 60 minutes (rail) | Advise on EU/OTIF compensation principles; document for formal claim |
| luggage_declared_value | > TZS 500,000 | Recommend formal cargo insurance claim; Athens Convention carrier liability applies for sea transport |
| issue_type | BOOKING_TICKETING + receipt_available = Yes | Escalate to operator with receipt evidence; strong case for full refund |

---

## Key Entities & Roles

**Regulatory Bodies:**
LATRA (Land Transport Regulatory Authority) — road transport complaints and route violations since 2023; SUMATRA (Surface and Marine Transport Regulatory Authority) — marine, ferry, and legacy surface transport; UDART (Urban and District Authorities for Road Transport) — BRT operations; Tanzania Harbours Authority (THA) — port and ferry terminal safety; Tanzania Railways Corporation (TRC) — SGR; TAZARA (Tanzania-Zambia Railway Authority); TCAA (Tanzania Civil Aviation Authority) — airport ground transfers

**Operators:**
UDART (BRT), Tanzania Railways (SGR), TAZARA, Azam Marine (Zanzibar ferry), Dar Express, Kilimanjaro Express, Royal Coach, Scandinavian Express, Bolt Tanzania, Uber Tanzania, Little (ride-hailing)

**Key Processes & Documents:**
Route permit, passenger manifest, roadworthiness certificate, PSV licence, Property Irregularity Report (PIR), police OB (Occurrence Book), LATRA complaint reference, BRT prepaid card, electronic ticketing, waybill (for parcels sent by bus)

---

## Disambiguation Notes

- **Transport vs. Logistics/Freight:** Complaints about cargo shipment, parcel delivery, or freight damage belong to the Logistics KB (33). Complaints about passengers, fares, schedules, and personal luggage belong here.
- **Transport vs. Aviation/Airport:** Complaints about flights, boarding, and baggage handling belong to the Aviation KB. Airport ground transportation (taxis, shuttles, JNIA bus) belongs here.
- **Bodaboda personal transport vs. bodaboda parcel delivery:** If the bodaboda carried a person, this is Transport KB. If the bodaboda was carrying a parcel for delivery, that is Logistics KB (33).
- **BRT vs. Daladala:** BRT complaints (cards, gates, UDART-operated buses) escalate to UDART. Daladala route and conduct violations escalate to LATRA.
- **Transport vs. Tourism:** Complaints about a safari vehicle that is primarily about driver/vehicle safety belong here. Complaints about the broader tour package (accommodation, itinerary, guide) belong in Tourism/Hospitality KB (39).
