---
tags: [industry-kb, field-standards, feedback-fields, transport, public-transit]
---
# Transport / Public Transit — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: usafiri, transport, daladala, basi, bus, minibus, coaster, commuter, UDA, Dar Rapid Transit, DART, BRT, bodaboda, pikipiki, tuk-tuk, bajaji, taxi, cab, Uber, Bolt, Little Cab, gari la umma, public transport, dereva, driver, kondakta, conductor, route, njia, fares, nauli, overcrowding, msongamano, accident, ajali, road safety, usalama wa barabarani, SUMATRA, LATRA, TRA, road worthiness, uwezo wa gari, vehicle inspection, ukaguzi wa gari, railway, reli, TAZARA, Tanzania Railways, ferry, kivuko, boti, vessel, port, bandari, TPA, MV Liemba, Mwambao ferry, overloading, kupakia kupita kiasi, night travel, safari ya usiku, road, barabara, matatu, speed, kasi, seatbelt, ukanda wa usalama, police roadblock, kizuizi cha polisi, stand, stendi, bus terminal, terminal ya basi, ticketing, tiketi

## Why Industry-Specific Fields Matter

Transport complaints span accident/safety incidents (requiring vehicle registration, route, SUMATRA/police report), fare overcharging (requiring route code, fare amount), and driver/conductor misconduct (requiring vehicle number, time of incident). Tanzania's SUMATRA (Surface and Marine Transport Regulatory Authority) and LATRA (Land Transport Regulatory Authority) have distinct jurisdictions. Without transport-specific fields, the AI cannot route the complaint to the correct authority, document the vehicle for enforcement action, or generate a SUMATRA-compliant incident report.

## Source Standards

- Tanzania SUMATRA Act, Cap. 413 — surface and marine transport regulation
- LATRA (Land Transport Regulatory Authority) Act 2019
- Tanzania Road Traffic Act, Cap. 168 — road safety and offenses
- TANROADS Act, Cap. 167 — road construction and maintenance
- Tanzania Ports Authority (TPA) Act — maritime transport
- TAZARA Act — railway transport
- Tanzania Police Traffic Department — accident reporting
- ISO 39001:2012 — Road traffic safety management systems
- ISO 10002:2018 — complaints handling
- UNECE Working Party 1 on Road Safety (reference)

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL transport complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | SUMATRA/LATRA complaint form; enables follow-up |
| complainant_phone | Nambari ya simu | Yes | For status updates |
| transport_mode | Aina ya usafiri | Yes | Bus / Daladala / Bodaboda / Taxi / Ferry / Train / BRT — determines regulatory authority |
| vehicle_registration_number | Nambari ya usajili wa gari | Yes | Primary enforcement identifier; SUMATRA can immediately check license status |
| vehicle_route | Njia ya gari | Conditional | Route number/name; enables SUMATRA route compliance check |
| operator_or_company_name | Jina la kampuni ya usafiri | Recommended | For fleet-level accountability |
| driver_name | Jina la dereva | Conditional | For driver-specific complaints |
| conductor_name | Jina la kondakta | Conditional | For conductor misconduct complaints |
| date_of_incident | Tarehe ya tukio | Yes | Required for investigation |
| time_of_incident | Saa ya tukio | Yes | For shift determination and CCTV (if available) |
| location_of_incident | Mahali pa tukio | Yes | Specific street, junction, or area |
| issue_type | Aina ya tatizo | Yes | SUMATRA/LATRA complaint taxonomy |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; detailed narrative |
| passengers_involved | Idadi ya abiria waliohusika | Conditional | For accident and safety complaints |
| desired_outcome | Matokeo unayotaka | Yes | Shapes resolution track |

### Conditional Fields (collect based on issue type)

**If issue_type = Accident / Injury:**
Also collect:
- `injury_type` — Aina ya majeraha: Minor / Moderate / Severe / Fatal — determines urgency and regulatory reporting
- `injured_parties` — Wahusika walioumia: Driver / Conductor / Passengers / Pedestrians / Others
- `police_report_number` — Nambari ya ripoti ya polisi: SUMATRA requires police abstract for accident complaints
- `hospital_treated` — Hospitali iliyotibu: For evidence chain
- `vehicle_road_worthiness_mark` — Je, gari lina hati ya uwezo (sticker ya TRA)?: For compliance check
- `speeding_suspected` — Je, dereva alikuwa akienda kwa kasi ya kupita kiasi?: Road Traffic Act speeding evidence
- `seatbelts_available` — Je, ukanda wa usalama ulikuwepo?: Legal requirement under Road Traffic Act

**If issue_type = Overcharging / Fare Dispute:**
Also collect:
- `official_route_fare_tzs` — Nauli rasmi ya njia (TZS): SUMATRA sets approved fares per route
- `fare_charged_tzs` — Nauli iliyotozwa (TZS)
- `fare_overcharge_tzs` — Kiasi cha ziada kilichotozwa (TZS)
- `receipt_or_ticket_available` — Je, tiketi au risiti inapatikana?: Evidence for SUMATRA fare complaint

**If issue_type = Overloading:**
Also collect:
- `number_of_passengers_observed` — Idadi ya abiria walioonekana: For comparison against vehicle capacity
- `vehicle_licensed_capacity` — Uwezo wa kisheria wa gari: For SUMATRA overloading prosecution
- `standing_passengers` — Je, abiria walisimama ndani ya gari? Yes / No

**If issue_type = Driver/Conductor Misconduct:**
Also collect:
- `misconduct_type` — Aina ya makosa: Verbal abuse / Physical assault / Refusing to stop / Refusing ticket / Theft / Sexual harassment
- `witnesses_present` — Mashahidi waliopo
- `any_physical_injury` — Je, alikuwepo majeraha yoyote ya kimwili?

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| TR-01 | accident_injury | Road accident causing injury or death |
| TR-02 | overcharging | Fare charged above approved SUMATRA rate |
| TR-03 | overloading | Vehicle carrying passengers beyond licensed capacity |
| TR-04 | speeding | Driver exceeding speed limits |
| TR-05 | driver_misconduct | Verbal abuse, aggressive driving, reckless behavior |
| TR-06 | conductor_misconduct | Overcharging, verbal abuse, refusing change |
| TR-07 | no_seatbelts | No functioning seatbelts in passenger vehicle |
| TR-08 | night_travel_unsafe | Unsafe night travel without lights or drunk driver |
| TR-09 | unroadworthy_vehicle | Mechanically unsafe vehicle in service |
| TR-10 | route_deviation | Driver deviating from licensed route |
| TR-11 | refusing_to_board | Driver/conductor refusing passengers at stops |
| TR-12 | vehicle_condition | Poor hygiene, broken seats, no ventilation |
| TR-13 | taxi_fraud | Meter tampering, wrong route, overcharging |
| TR-14 | ferry_safety | Overcrowded or unsafe ferry/boat crossing |
| TR-15 | railway_complaint | TAZARA service quality, safety, or delay |
| TR-16 | bodaboda_misconduct | Motorcycle taxi recklessness or overcharging |
| TR-17 | disability_access | Failure to accommodate passengers with disabilities |

### Resolution Standards

- **SUMATRA:** Complaints acknowledged within 5 working days; resolved within 30 days. Serious safety violations within 72 hours.
- **LATRA:** Land transport regulation; similar timelines to SUMATRA.
- **Police Traffic Department:** Accident reports and traffic offense complaints; investigation within 30 days.
- **Driver/vehicle license suspension:** SUMATRA can suspend operating licenses pending investigation.
- **TPA (ferry):** Maritime incident reports within 24 hours; investigation by Marine Accident Investigation Unit.
- **Required for escalation:** Vehicle registration number, route, date/time, description, police report number (for accidents).

### Escalation Triggers

- `issue_type = accident_injury` AND `injury_type = Severe / Fatal` — Immediate SUMATRA accident report + police notification; potential prosecution
- `issue_type = overloading` AND ferry/boat — Maritime safety emergency; TPA and SUMATRA immediate action; capsizing risk
- `issue_type = no_seatbelts` AND school children transport — Road Traffic Act violation; immediate SUMATRA enforcement
- `issue_type = conductor_misconduct` AND `misconduct_type = Sexual harassment` — Escalate to employer + SUMATRA + police (criminal matter)
- `vehicle_road_worthiness = expired/absent` AND accident — Criminal negligence; SUMATRA and DPP referral
- `issue_type = ferry_safety` AND significant overloading — Maritime emergency protocol; TPA immediate intervention

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| transport_mode | Aina ya usafiri | Yes | Routes to correct authority |
| route_or_area | Njia au eneo | Recommended | Geographic routing |
| suggestion_category | Kategoria | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| TRS-01 | road_safety | Usalama zaidi wa barabarani |
| TRS-02 | fare_regulation | Nauli zilizo wazi na zinazothibitishwa |
| TRS-03 | vehicle_condition | Magari bora ya usafiri wa umma |
| TRS-04 | driver_training | Mafunzo ya madereva |
| TRS-05 | disability_access | Usafiri unaofikiwa na walemavu |
| TRS-06 | route_coverage | Njia mpya za usafiri |
| TRS-07 | digital_ticketing | Tiketi za kidijitali |
| TRS-08 | infrastructure | Stendi bora na vituo vya abiria |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina | Recommended | For tracking |
| transport_mode | Aina ya usafiri | Yes | Routes to correct authority |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| fare_information | Nauli rasmi ya njia hii ni ngapi? | route, transport_mode |
| route_information | Gari linapita wapi? | route, origin, destination |
| operator_license | Je, kampuni hii ina leseni ya SUMATRA? | operator_name |
| report_accident_process | Jinsi ya kuripoti ajali | vehicle_registration |
| BRT_route | Njia za DART/BRT | origin, destination |
| bodaboda_registration | Je, bodaboda hii imesajiliwa? | vehicle_registration |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| driver_name | Jina la dereva | Recommended | Driver recognition |
| vehicle_registration | Nambari ya gari | Yes | Routes to operator/fleet manager |
| route | Njia | Recommended | Routes to route manager |
| specific_aspect_praised | Kipengele | Yes | Udereva salama / Ukarimu / Usafi wa gari / Muda wa kufika |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Transport service quality benchmarking |

---

## AI Conversation Guidance for This Industry

- **Always get the vehicle registration number first.** It is the single most actionable piece of information — SUMATRA/LATRA can immediately check operator license, route compliance, and accident history. "Nambari ya usajili wa gari inaonekana mbele au nyuma ya gari — ni nambari na herufi. Je, uliitazama?"
- **For accident complaints, ask about police immediately.** Under Tanzania Road Traffic Act, all accidents must be reported to police. "Je, ajali hii iliripotiwa polisi? Kama ndiyo, una nambari ya ripoti ya polisi?"
- **For overcharging, confirm the official route fare.** SUMATRA publishes approved fares; if the customer doesn't know it, the AI should confirm they were charged more than they expected, and SUMATRA can verify the official rate. "Nauli rasmi ya njia hii inaweza kuthibitishwa na SUMATRA — ulilipwa kiasi gani?"
- **For overloading on ferries, treat as an emergency.** Overloaded ferries in Tanzania have caused tragedies. "Boti inayobeba abiria zaidi ya uwezo ni hatari ya maisha — tafadhali jaribu kushuka kama inawezekana, au piga simu ya dharura (+255 117)."
- **Do not ask for gender or personal details of misconduct victims** beyond what they volunteer — especially for sexual harassment incidents. Allow the complainant to share at their own comfort level.
- **For bodaboda complaints, ask for any identifying marks.** Registration plates are often unreadable on bodabodas; ask for color, time, and location to enable some investigation.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Vehicle registration | "Nambari ya usajili wa gari (sahani ya mbele au nyuma) ni ipi? Au uliweza kuisoma?" |
| Route | "Gari hili lilikuwa linakwenda njia gani — njia namba ngapi au kutoka wapi hadi wapi?" |
| Date and time | "Tukio hili lilitokea tarehe gani na saa ngapi?" |
| Location | "Tukio hili lilitokea wapi hasa — barabara gani, nusukani gani, au karibu na nini?" |
| Police report | "Je, ajali hii iliripotiwa polisi? Kama ndiyo, nambari ya ripoti ya polisi ni ipi?" |
| Official fare | "Uliamini nauli rasmi ya njia hii ni kiasi gani? Ulitozwa kiasi gani?" |
| Injuries | "Je, wewe au mtu mwingine aliumia? Majeraha yalipata matibabu?" |
| Vehicle capacity | "Ulidhani gari lilikuwa na abiria wangapi zaidi ya uwezo wake?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | accident_injury AND severe/fatal | Immediate SUMATRA accident report + police; potential prosecution; confirm medical care |
| issue_type | ferry_safety AND significant overloading | Maritime emergency; TPA immediate intervention; coastguard if at sea |
| issue_type | conductor_misconduct AND sexual harassment | Employer + SUMATRA + police (criminal matter); victim support services |
| vehicle_road_worthiness | expired or absent AND accident | Criminal negligence referral; SUMATRA enforcement; DPP notification |
| issue_type | overloading AND school children | Road Traffic Act violation; immediate SUMATRA enforcement; school authority notification |
| issue_type | no_seatbelts AND long-distance bus | Road Traffic Act s.53; SUMATRA inspection order |
| issue_type | overcharging AND systematic pattern | SUMATRA fare audit; multiple complaints = route enforcement action |
| issue_type | speeding AND accident | Police Traffic Department + SUMATRA; driving license suspension |

---

*Sources: SUMATRA Act Cap. 413, LATRA Act 2019, Tanzania Road Traffic Act Cap. 168, TANROADS Act Cap. 167, TPA Act, ISO 39001:2012, ISO 10002:2018*
