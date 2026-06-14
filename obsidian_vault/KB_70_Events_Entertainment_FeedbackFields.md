---
tags: [industry-kb, field-standards, feedback-fields, events, entertainment]
---
# Events / Entertainment — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: tukio, event, tamasha, show, concert, onyesho la muziki, festival, karamu, sherehe, wedding, harusi, birthday party, karamu ya kuzaliwa, conference, mkutano, exhibition, maonyesho, trade fair, soko la biashara, graduation party, karamu ya kuhitimu, corporate event, tukio la kampuni, product launch, uzinduzi wa bidhaa, fundraiser, chanzo cha fedha, sports event, tukio la michezo, ticket, tiketi, booking, mapanga, venue, ukumbi, hall, event organizer, mpangaji wa matukio, MC, mwenyeji, DJ, band, bendi, photographer, mpigapicha, videographer, catering, upishi, décor, mapambo, stage, jukwaa, sound system, mfumo wa sauti, lighting, mwanga, alcohol, pombe, security, ulinzi, crowd, umati, ticket refund, kurudisha tiketi, gate, lango, event manager, BASATA, Tanzania Arts Council, COSOTA, Copyright Society of Tanzania, late start, kuanza kuchelewa, gate crash, kuingia bila tiketi

## Why Industry-Specific Fields Matter

Events complaints span ticket fraud (requiring event name, ticket serial number, organizer details), poor event execution (requiring specific deficiency description, time of observation, number affected), venue safety incidents (requiring venue name, incident date/time, injury details), and vendor misconduct (requiring vendor type and service agreement reference). Without events-specific fields, the AI cannot verify whether the organizer is BASATA-licensed (for public performances), generate a police/venue authority safety report, or substantiate a ticketing fraud complaint.

## Source Standards

- Tanzania Arts and Entertainment Act, Cap. 33 — BASATA mandate
- BASATA (Board of Arts and National Culture) licensing requirements
- COSOTA (Copyright Society of Tanzania) Act — performer rights
- Tanzania Police Act — crowd management and public safety
- Fire and Rescue Act — venue fire safety
- Tanzania Food and Drugs Authority (TFDA) — food safety at events
- ISO 20121:2012 — Sustainable event management
- ISO 10002:2018 — complaints handling
- Tanzania Fair Competition Act, Cap. 285 — consumer protection for ticketed events

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL events complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Complaint registration |
| complainant_phone | Nambari ya simu | Yes | Status updates |
| event_name | Jina la tukio | Yes | Core identifier |
| event_date | Tarehe ya tukio | Yes | For timeline and investigation |
| event_venue | Ukumbi / Eneo la tukio | Yes | Venue authority and safety accountability |
| event_organizer_name | Jina la mpangaji wa tukio | Yes | Accountability routing; BASATA license check |
| basata_license_number | Nambari ya leseni ya BASATA (kama inajulikana) | Recommended | For public performance events; BASATA compliance |
| ticket_number | Nambari ya tiketi | Conditional | For ticketed event complaints |
| ticket_category | Aina ya tiketi | Conditional | VIP / Regular / Early bird — for entitlement assessment |
| ticket_price_paid_tzs | Bei ya tiketi iliyolipwa (TZS) | Conditional | For refund and fraud quantification |
| issue_type | Aina ya tatizo | Yes | Complaint taxonomy |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; detailed narrative |
| number_of_people_affected | Idadi ya watu walioathirika | Recommended | Scale of complaint |
| evidence_available | Ushahidi unaopatikana | Recommended | Ticket / Receipt / Photos / Video |
| desired_outcome | Matokeo unayotaka | Yes | Refund / Apology / Compensation / Investigation |

### Conditional Fields (collect based on issue type)

**If issue_type = Ticket Fraud / Event Cancelled:**
Also collect:
- `ticket_purchase_platform` — Jukwaa la kununua tiketi: Online / Gate / Agent / WhatsApp / Social media
- `payment_method` — Njia ya malipo: Mobile money / Bank / Cash
- `payment_reference` — Nambari ya marejeleo ya malipo: For fraud tracing
- `receipt_or_confirmation` — Je, uthibitisho wa malipo ulipokelewa? Yes / No
- `event_cancellation_notice` — Je, taarifa ya kufuta tukio ilitolewa? Yes / No: Advance notice affects refund entitlement

**If issue_type = Venue Safety Incident:**
Also collect:
- `incident_type` — Aina ya tukio: Stampede / Fire / Structural failure / Violence / Crowd crush
- `injuries_sustained` — Majeraha yaliyotokea: Minor / Moderate / Severe / Fatal
- `police_report_filed` — Je, ripoti ya polisi iliwasilishwa? Yes / No
- `venue_capacity_observed` — Je, ukumbi ulikuwa umejaa kupita uwezo? Yes / No
- `fire_exits_available` — Je, njia za kutoroka zilikuwepo? Yes / No

**If issue_type = Event Quality / Promised vs. Delivered:**
Also collect:
- `artists_promised` — Wasanii / Waigizaji walioahidiwa
- `artists_who_appeared` — Wasanii / Waigizaji walioonekana kweli kweli
- `start_time_promised` — Saa iliyoahidiwa ya kuanza
- `actual_start_time` — Saa ya kuanza kweli kweli
- `specific_quality_issues` — Mapungufu mahususi: Poor sound / No lighting / Wrong MC / Venue too small / No catering

**If issue_type = Vendor / Catering Complaint:**
Also collect:
- `vendor_type` — Aina ya muuzaji: Catering / Photographer / Decorator / DJ / Band
- `service_agreement_reference` — Nambari ya mkataba wa huduma
- `service_fee_paid_tzs` — Ada iliyolipwa kwa muuzaji (TZS)
- `service_quality_issues` — Mapungufu ya huduma: Not attended / Wrong food / Poor photos / No show

**If issue_type = Food Safety at Event:**
Also collect:
- `symptoms` — Dalili: Vomiting / Diarrhea / Allergic reaction
- `dish_consumed` — Chakula kilicholiwa
- `number_affected` — Idadi ya watu walioathirika: Outbreak indicator
- `caterer_name` — Jina la mpishi / kampuni ya upishi

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| EV-01 | ticket_fraud | Fake tickets sold or paid for event that doesn't exist |
| EV-02 | event_cancelled | Event cancelled without adequate refund or notice |
| EV-03 | artist_no_show | Promised headliner or performer didn't appear |
| EV-04 | venue_safety | Safety hazard at event venue |
| EV-05 | crowd_crush_stampede | Overcrowding leading to injuries |
| EV-06 | poor_sound_lighting | Technical quality issues significantly affecting experience |
| EV-07 | significant_delay | Event started hours late without justification |
| EV-08 | food_poisoning | Illness from event catering |
| EV-09 | vendor_no_show | Hired vendor (photographer, caterer, DJ) didn't deliver |
| EV-10 | security_misconduct | Event security aggressive, discriminatory, or abusive |
| EV-11 | overcharge | Charged more than advertised ticket price |
| EV-12 | unlicensed_event | Event held without BASATA or relevant authority license |
| EV-13 | vip_service_failure | VIP ticketholders not receiving promised VIP benefits |
| EV-14 | discrimination | Entry refused on discriminatory grounds |
| EV-15 | theft_at_event | Theft of belongings during event |

### Resolution Standards

- **Organizer level:** Complaints acknowledged within 48 hours; refunds for cancelled events within 14 days.
- **BASATA:** Complaints against unlicensed performances or artist rights violations; investigation within 30 days.
- **Police (safety incidents):** Safety and crowd incidents reported immediately; investigation within 30 days.
- **TFDA (food safety):** Food poisoning at events; investigation within 15 days.
- **Consumer protection (FCC):** Ticket fraud and false advertising; investigation within 60 days.
- **Required for escalation:** Event name, date, organizer name, ticket reference, amount paid, description.

### Escalation Triggers

- `issue_type = venue_safety` AND `injuries_sustained = Severe / Fatal` — Immediate police report; OSHA investigation; venue safety authority
- `issue_type = crowd_crush_stampede` — Major safety emergency; police + fire + OSHA + venue authority; criminal investigation
- `issue_type = food_poisoning` AND `number_affected >= 3` — TFDA outbreak investigation; MOHCDGEC notification
- `issue_type = ticket_fraud` AND large scale — FCC consumer protection + police criminal fraud unit; BASATA if licensed event
- `issue_type = unlicensed_event` — BASATA enforcement; police if safety risk
- `issue_type = vendor_no_show` AND wedding/significant milestone event — High emotional impact; priority settlement; legal referral for breach of contract

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| event_type | Aina ya tukio | Yes | Routes to correct team |
| organizer_name | Mpangaji | Recommended | For routing |
| suggestion_category | Kategoria | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| EVS-01 | safety_standards | Viwango vya usalama katika matukio |
| EVS-02 | sound_quality | Ubora wa sauti |
| EVS-03 | ticketing_transparency | Uwazi wa tiketi na bei |
| EVS-04 | punctuality | Kuanza kwa wakati |
| EVS-05 | catering_quality | Ubora wa chakula na vinywaji |
| EVS-06 | venue_facilities | Vifaa bora vya ukumbi |
| EVS-07 | refund_policy | Sera wazi ya kurudisha pesa |
| EVS-08 | vendor_vetting | Uchunguzi bora wa wasambazaji |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina | Recommended | For tracking |
| event_name | Tukio | Conditional | For event-specific queries |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| ticket_verification | Je, tiketi hii ni halisi? | ticket_number, event_name |
| basata_license_check | Je, tukio hili lina leseni ya BASATA? | event_name, organizer_name |
| refund_process | Jinsi ya kupata kurudishwa pesa tiketi | event_name, ticket_number |
| event_cancellation | Je, tukio hili limefutwa? | event_name, event_date |
| vendor_recommendation | Unaweza kupendekeza mpigapicha / mchoraji? | event_type, location |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| organizer_name | Mpangaji | Yes | Routes to management |
| event_name | Jina la tukio | Yes | Event recognition |
| specific_aspect_praised | Kipengele | Yes | Mipangilio mizuri / Sauti nzuri / Mapambo mazuri / Ulinzi salama / Chakula kitamu |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Event quality benchmarking |
| would_attend_again | Je, ungerudi tena? | Recommended | NPS indicator |

---

## AI Conversation Guidance for This Industry

- **For safety incidents at events, prioritize physical safety.** "Je, kuna majeraha au hatari ya haraka? Kama ndiyo, piga simu ya polisi (+255 117) au ambulance mara moja."
- **For ticket fraud, get the payment reference immediately.** Mobile money transactions can be traced and reversed within hours if reported quickly. "Ulilipa kwa njia ya pesa ya simu? Nambari ya marejeleo ya malipo ni muhimu sana — inaweza kusaidia kufuatilia na kuzuia fedha."
- **For vendor no-shows at weddings or special events, acknowledge the emotional impact.** "Tunakuelewa hali hii ni ya kiuchungu sana — tutahakikisha malalamiko yako yanaenda mbele haraka iwezekanavyo."
- **Distinguish between refund complaints and safety complaints.** Refund complaints are consumer protection matters; safety incidents require police and authority involvement regardless of the refund outcome.
- **For food poisoning at events, collect a list of what was consumed.** "Chakula kilicholiwa katika tukio hicho kilikuwa nini hasa? Orodha ya vyakula itasaidia TFDA kufanya uchunguzi."
- **For BASATA license questions, provide the BASATA contact.** "BASATA inaweza kuthibitisha kama tukio au msanii ana leseni — unaweza wasiliana nao kwa..."

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Event name | "Tukio hili linaitwa nini? Na lilipangwa na nani?" |
| Ticket number | "Nambari ya tiketi inaonekana kwenye tiketi yako — je, inasema nini?" |
| Payment reference | "Ulipolipa tiketi au huduma hii, nambari ya marejeleo ya malipo ilikuwa nini?" |
| Artist promised | "Wasanii au waigizaji waliohidi kutoa onyesho walikuwa akina nani?" |
| Start time | "Tukio liliahidiwa kuanza saa ngapi? Na lilianza saa ngapi kweli kweli?" |
| Safety incident | "Je, kulikuwa na majeraha yoyote? Na watu wangapi waliathirika?" |
| Food poisoning | "Chakula kilicholiwa kilikuwa nini? Na dalili za ugonjwa zilianza lini baada ya kula?" |
| Desired outcome | "Unataka nini — kurudishiwa pesa, fidia, au hatua dhidi ya mpangaji?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | crowd_crush_stampede | Major safety emergency; police + fire + OSHA + venue authority; criminal investigation |
| issue_type | venue_safety AND injuries severe/fatal | Immediate police; OSHA investigation; venue safety authority; medical care |
| issue_type | food_poisoning AND number_affected >= 3 | TFDA outbreak investigation; MOHCDGEC; caterer food safety inspection |
| issue_type | ticket_fraud AND large scale | FCC + police criminal fraud; BASATA if licensed event; mobile money reverse |
| issue_type | event_cancelled AND refund_refused | FCC consumer protection; legal referral for breach of contract |
| issue_type | vendor_no_show AND wedding | High impact; priority settlement; contract breach legal referral |
| issue_type | unlicensed_event | BASATA enforcement; police if safety risk |
| issue_type | security_misconduct AND assault | Police report; criminal matter; venue management |

---

*Sources: Tanzania Arts and Entertainment Act Cap. 33, BASATA regulations, COSOTA Act, Fire and Rescue Act, TFDA Act Cap. 219, Fair Competition Act Cap. 285, ISO 20121:2012, ISO 10002:2018*
