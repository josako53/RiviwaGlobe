---
tags: [industry-kb, field-standards, feedback-fields]
---
# Events / Entertainment — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: concert, show, festival, conference, exhibition, trade fair, wedding, ceremony, harusi, party, karamu, gala, seminar, workshop, MICE (Meetings Incentives Conferences Exhibitions), DITF (Dar es Salaam International Trade Fair), venue, ukumbi, banquet hall, stadium, arena, tent, hema, event organizer, promoter, ticket, tiketi, admission, VIP, stage, performance, DJ, MC, master of ceremonies, performer, artist, headline act, sound system, lighting, decoration, catering, buffet, bar, event permit, ruhusa ya tukio, security, ulinzi, event planner, outdoor event, tukio, burudani, tamasha, ngoma, mchezo, sports event, mechi, marathon, tournament, ticketing platform, online ticket, resale ticket, scalper

## Why Industry-Specific Fields Matter

Generic feedback fields cannot distinguish between a concert performer no-show (requiring promoter name, ticket reference, and consumer rights remedy determination), an event safety failure affecting hundreds of attendees (requiring venue authority notification and injury reporting), and a wedding planner contract dispute (requiring service agreement reference and small claims court pathway) — all of which have different legal bases under Tanzania's Consumer Protection Act, OSHA occupational safety regulations for public events, and local government event permit requirements. Without events-specific fields, the AI cannot route complaints, trigger correct escalations, or identify systemic ticketing fraud across a community.

## Source Standards

- ISO 20121:2024 Event Sustainability Management Systems (stakeholder grievance mechanism requirement)
- Citizens Advice UK: Complaining About Events (consumer rights basis)
- Contend Legal: Event Complaint Guidance (UK Consumer Rights Act 2015 — performance/service standard basis)
- ABTA Holiday Complaint guidance (refund and cancellation standards)
- Tanzania Consumer Protection Act 2008 (Cap 395)
- Tanzania Occupational Health and Safety Act 2003 (public safety at events)
- Local Government Authority (LGA) event permit requirements

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| `complainant_name` | Jina la mlalamikaji | Yes | Required by Contend Legal and Citizens Advice for formal complaint registration; needed for refund and acknowledgement |
| `complainant_contact` | Mawasiliano (simu / barua pepe) | Yes | For acknowledgement and follow-up; all consumer rights frameworks require contact for formal complaint processing |
| `event_name` | Jina la tukio | Yes | Contend Legal: "Details of the event (name, date, and venue)"; primary identifier for routing complaint to organizer |
| `event_date` | Tarehe ya tukio | Yes | Contend Legal: required; establishes which contractual obligation was in force and determines refund eligibility window |
| `venue_name_and_location` | Jina na mahali pa ukumbi / eneo la tukio | Yes | Contend Legal and Citizens Advice: venue is separately liable from organizer/promoter for facility failures |
| `event_type` | Aina ya tukio | Yes | Determines applicable standards, permit types, and regulatory bodies. Options: Tamasha la Muziki / Michezo / Mkutano / Maonyesho / Harusi / Karamu ya Biashara / Burudani ya Nje |
| `ticket_reference_or_order_number` | Nambari ya tiketi / agizo | Yes | Contend Legal: "Your booking reference or ticket number"; ABTA equivalent; establishes proof of purchase and entitlement |
| `ticket_price_paid` | Bei ya tiketi iliyolipwa | Yes | UK Consumer Rights Act 2015 basis for refund calculation; required to quantify remedy in any dispute |
| `ticket_seller_name` | Jina la muuzaji wa tiketi | Yes | Citizens Advice distinguishes between ticket seller (e.g., Ticketmaster equivalent) and organizer; each may have separate liability |
| `organizer_or_promoter_name` | Jina la mwandaaji / promoter wa tukio | Yes | Promoter is primarily liable for event cancellation, performer no-show, and misleading advertising |
| `issue_type` | Aina ya tatizo | Yes | Determines regulatory body, remedy calculation, and escalation path; Contend Legal and Citizens Advice categorize by issue type |
| `issue_description` | Maelezo ya tatizo | Yes | Required by all consumer rights frameworks as the primary complaint narrative |
| `date_and_time_of_incident` | Tarehe na saa ya tukio | Yes | For incident-specific complaints (safety, harassment); correlation with staff, security, and CCTV records |
| `number_of_people_affected` | Idadi ya watu walioathirika | Yes | ISO 20121 community impact scope; safety incidents affecting large numbers trigger different escalation paths |
| `desired_outcome` | Matokeo unayotaka | Yes | Contend Legal: "state clearly what you want: refund, compensation, or replacement tickets"; required for resolution framing |
| `prior_complaint_to_organizer` | Je, umeshalalamika kwa mwandaaji / muuzaji moja kwa moja? | Yes | Consumer rights frameworks require complainant to first raise issue with provider; establishes escalation eligibility |
| `organizer_response` | Jibu la mwandaaji / muuzaji (kama lipo) | Conditional | Needed to assess whether internal resolution was attempted before Riviwa escalation |
| `evidence_documentation` | Ushahidi (tiketi, risiti, picha, screenshots, matangazo) | Recommended | Contend Legal: "copies of tickets, receipts, screenshots, photos/videos; promotional materials about performers or advertised facilities" |

### Conditional Fields (collect based on issue type)

**If `issue_type = cancellation_refund_denied` OR `event_postponed`:**
Also collect:
- `cancellation_or_postponement_notice_date` — Tarehe ya taarifa ya kufutwa / kuahirishwa: Contend Legal; adequate notice period is a consumer rights factor
- `original_event_date` — Tarehe ya awali ya tukio: For calculating notice period
- `new_event_date` — Tarehe mpya (kama tukio liliahirishwa): For determining whether rescheduled event is acceptable
- `refund_requested_date` — Tarehe ya kuomba marejesho: For limitation period and organizer response timeline
- `refund_amount_expected` — Kiasi cha marejesho kinachostahiliwa (TZS): For remedy calculation

**If `issue_type = safety_hazard` OR `overcrowding`:**
Also collect:
- `hazard_type` — Aina ya hatari: Structural / overcrowding / fire / electrical / crowd crush / security failure
- `injury_or_harm_occurred` — Je, kulikuwa na jeraha au madhara? Yes/No: Personal injury triggers police and event authority escalation
- `emergency_services_contacted` — Je, huduma za dharura ziliitwa? Yes/No
- `estimated_attendance` — Idadi ya wahudhuria (takriban): Overcrowding determination requires attendance vs. venue capacity
- `venue_stated_capacity` — Uwezo wa ukumbi uliodaiwa: For capacity violation determination

**If `issue_type = performer_no_show` OR `misrepresentation`:**
Also collect:
- `advertised_performer_or_program` — Msanii / mpango uliodaiwa katika matangazo: What was advertised
- `actual_performer_or_program` — Msanii / mpango halisi uliofanyika: What actually happened
- `notice_of_change_given` — Je, taarifa ya mabadiliko ilitolewa? Yes/No: Last-minute substitution without notice is a consumer rights violation
- `promotional_material_available` — Je, una matangazo ya awali (poster, flyer, screenshot)? Yes/No: Key evidence for misrepresentation claim

**If `issue_type = harassment` BY staff or other attendees:**
Also collect:
- `harassment_type` — Aina ya unyanyasaji: Sexual / physical / verbal / racial
- `perpetrator_role` — Wadhifa wa mkosaji: Security / staff / other attendee / unknown
- `police_report_filed` — Je, ripoti ya polisi imewasilishwa? Yes/No

**If `issue_type = fake_or_invalid_ticket`:**
Also collect:
- `purchase_channel` — Njia ya ununuzi: Official website / authorized agent / social media / reseller / street vendor
- `amount_paid` — Kiasi kilicholipwa (TZS): For fraud quantification
- `seller_contact_details` — Mawasiliano ya muuzaji (kama yapo): For police fraud referral

**If `issue_type = accessibility_failure`:**
Also collect:
- `disability_type` — Aina ya ulemavu: Mobility / visual / hearing / cognitive
- `accommodation_requested_in_advance` — Je, ulihitaji msaada maalum kabla ya tukio? Yes/No
- `accommodation_denied_or_failed` — Msaada ulikataliwa au haukufanya kazi vizuri: Description

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| EV-01 | `safety_hazard` | Structural failure, overcrowding, fire risk, crowd crush |
| EV-02 | `misrepresentation` | Performer replaced without notice; facilities not as advertised |
| EV-03 | `cancellation_refund_denied` | Event cancelled but refund withheld |
| EV-04 | `postponement_inadequate_notice` | Event postponed without adequate notice to ticket holders |
| EV-05 | `overcrowding_capacity_violation` | Venue exceeded stated or permitted capacity |
| EV-06 | `harassment_by_staff` | Abuse, aggression, or misconduct by event security or staff |
| EV-07 | `harassment_by_attendees` | Assault, sexual harassment, or aggression by other attendees |
| EV-08 | `poor_facilities` | Inadequate toilets, lighting, sound, seating, or disability access |
| EV-09 | `performer_no_show` | Headliner or main act did not appear |
| EV-10 | `security_failure` | Inadequate security leading to theft, assault, or crowd disorder |
| EV-11 | `fake_invalid_ticket` | Ticket purchased in good faith was fake or duplicate |
| EV-12 | `seating_mismatch` | Seat category received different from seat purchased |
| EV-13 | `accessibility_failure` | Disability access requirement not met despite prior arrangement |
| EV-14 | `admission_refusal` | Valid ticket holder refused entry without justification |
| EV-15 | `food_beverage_failure` | Food poisoning, mislabeled allergens, or service below contracted standard |
| EV-16 | `catering_or_decoration_contract_dispute` | Wedding/event planner did not deliver contracted services |
| EV-17 | `noise_environmental_complaint` | Event caused unreasonable noise or disturbance to surrounding community |

### Resolution Standards for This Industry

- **Consumer rights (Tanzania Consumer Protection Act 2008):** Consumers have the right to a refund or replacement if a service is not rendered as contracted; event cancellations without adequate alternatives entitle the consumer to a full refund.
- **ISO 20121:2024 requirement:** Event organizations must establish a grievance mechanism enabling community feedback and post-event complaint resolution; organizer must document and respond to all community complaints.
- **Safety incidents (OSHA 2003):** Workplace injuries at events must be reported to OSHA Tanzania; organizers holding public permits are liable for crowd safety.
- **LGA event permits:** Local government authorities issue event permits; safety violations (overcrowding, unlicensed events) can be reported to the issuing LGA.
- **Fake tickets / fraud:** Escalate to Tanzania Police Fraud Unit (CIFT — Cybercrime Investigation and Forensic Techniques); advise complainant to preserve all digital evidence.
- **Refund timeline standard (Contend Legal basis):** Organizers should process refunds within 14 days of cancellation; failure to refund within 30 days enables consumer protection complaint.

### Escalation Triggers (field values that require immediate escalation)

- `issue_type = safety_hazard` AND `injury_or_harm_occurred = Yes` — Emergency; escalate to police and OSHA; create priority medical emergency ticket
- `issue_type = overcrowding_capacity_violation` AND `estimated_attendance` significantly exceeds `venue_stated_capacity` — Public safety risk; notify LGA permit authority and police; do not wait for organizer response
- `issue_type = harassment_by_staff` OR `harassment_by_attendees` AND `harassment_type = Sexual` — Escalate to police; victim safety first; do not pressure victim to interact with organizer
- `issue_type = fake_invalid_ticket` AND `amount_paid > 500000 TZS` — Financial fraud; escalate to Tanzania Police CIFT unit; preserve digital evidence
- `issue_type = food_beverage_failure` AND multiple attendees report same illness — Public health emergency; notify district medical officer and TFDA
- `issue_type = cancellation_refund_denied` AND `ticket_price_paid × number_of_people_affected > 5000000 TZS` — Large-scale consumer fraud; escalate to Fair Competition Commission (FCC) Tanzania

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `submitter_name` | Jina la mtoa maoni (hiari) | Optional | ISO 20121 community grievance mechanism permits anonymous suggestions |
| `event_or_venue_name` | Jina la tukio / ukumbi | Yes | Routes suggestion to correct organizer or venue management |
| `suggestion_category` | Kategoria ya mapendekezo | Yes | Systematic routing and analysis |
| `suggestion_detail` | Maelezo ya mapendekezo | Yes | Free text; core content |
| `event_type` | Aina ya tukio | Yes | Determines applicable standards for the suggestion |
| `event_date` | Tarehe ya tukio | Recommended | Provides context for time-specific operational suggestions |

### Industry-Specific Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| EVS-01 | `safety_crowd_management` | Usalama wa umma na usimamizi wa umati |
| EVS-02 | `accessibility_disability` | Upatikanaji kwa walemavu |
| EVS-03 | `facilities_quality` | Ubora wa miundombinu (vyoo, mwanga, sauti) |
| EVS-04 | `sustainability_waste` | Uendelevu na usimamizi wa taka |
| EVS-05 | `ticketing_transparency` | Uwazi wa mauzo ya tiketi |
| EVS-06 | `community_impact` | Athari kwa jamii inayozunguka tukio |
| EVS-07 | `catering_and_food_quality` | Ubora wa chakula na huduma ya chakula |
| EVS-08 | `communication_to_attendees` | Mawasiliano na wahudhuria (kabla, wakati, baada) |
| EVS-09 | `security_standards` | Viwango vya ulinzi |
| EVS-10 | `pricing_fairness` | Haki ya bei ya tiketi na huduma |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `inquirer_name` | Jina la mwulizaji (hiari) | Optional | Not required for general inquiries |
| `inquiry_type` | Aina ya swali | Yes | Routes to correct answer path or referral |
| `event_name_and_date` | Jina na tarehe ya tukio | Conditional | Required for event-specific inquiries |
| `ticket_reference` | Nambari ya tiketi (kama ipo) | Conditional | For ticket-specific inquiries (status, validity, refund) |
| `preferred_response_channel` | Njia unayopendelea ya jibu | Yes | SMS / Simu / WhatsApp / Barua pepe |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Swahili | Additional Fields Needed |
|-------------|---------|--------------------------|
| `ticket_status` | Hali ya tiketi yangu | `ticket_reference_or_order_number`, `event_name` |
| `refund_status` | Hali ya marejesho ya pesa yangu | `ticket_reference`, `refund_requested_date` |
| `accessibility_arrangements` | Mipango ya msaada kwa walemavu | `disability_type`, `event_name_and_date` |
| `program_schedule` | Ratiba ya tukio | `event_name_and_date` |
| `venue_directions` | Jinsi ya kufika eneo la tukio | `venue_name_and_location` |
| `ticket_validity_check` | Je, tiketi yangu ni ya kweli? | `ticket_reference`, `event_name`, `purchase_channel` |
| `event_permit_status` | Je, tukio hili lina ruhusa ya serikali? | `event_name`, `venue_name_and_location`, `event_date` |
| `cancellation_policy` | Sera ya kufuta tiketi | `event_name`, `ticket_price_paid` |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `submitter_name` | Jina la mtoa pongezi (hiari) | Optional | For acknowledgement; not required |
| `event_or_organizer_recognized` | Tukio / Mwandaaji / Mfanyakazi anayepongezwa | Yes | Routes compliment to organizer or staff recognition |
| `specific_staff_or_team` | Mfanyakazi / Timu maalum (kama inajulikana) | Optional | For targeted staff recognition |
| `what_was_exceptional` | Kilichokuwa bora / cha kipekee | Yes | Specific positive element; routes to relevant team |
| `event_date` | Tarehe ya tukio | Recommended | For correlation with operational records |
| `would_attend_again` | Je, ungerudi kwenye tukio lingine la mwandaaji huyu? | Yes | Attendee loyalty signal; valuable for organizer marketing data |
| `specific_aspect_praised` | Kipengele maalum kilichopongezwa | Yes | Organisation / Safety / Sound and lighting / Catering / Performer / Facilities / Value for money |

---

## AI Conversation Guidance for This Industry

- **Establish the ticket reference before asking about the problem.** The ticket or order number is the single most important field — it proves attendance entitlement and unlocks the contract between the attendee and the organizer. Ask "Una nambari ya tiketi au nambari ya agizo lako?" early and confirm it before exploring the complaint.
- **Distinguish between the ticket seller and the event organizer.** In Tanzania, tickets may be sold through a third-party platform (social media pages, agents, WhatsApp) while a different promoter runs the event. Ask "Ulinunua tiketi kutoka wapi — moja kwa moja kutoka kwa mwandaaji, au kupitia muuzaji mwingine?" — this determines who is liable for the refund.
- **For safety complaints, prioritize the person's current status before collecting event details.** Ask "Je, uko salama sasa hivi? Je, ulipata jeraha lolote?" before asking for the event name or ticket number. Provide police emergency number (112) immediately if there is a safety emergency.
- **For cancelled event refund complaints, collect the timeline precisely.** Ask "Tukio lilifutwa lini? Ulitaarifiwa lini? Na ulipata jibu lolote baada ya kuomba marejesho?" — the notice period and the time since refund was requested are legally determinative under consumer rights frameworks.
- **For fake ticket complaints, do not ask the victim to confront the seller.** Instead, say "Usijaribu kuwasiliana na muuzaji tena — tumia ushahidi ulio nao (screenshots, nambari ya tiketi ya bandia) kuripoti kwa polisi na kwa mwandaaji wa tukio la kweli."
- **For harassment or assault complaints, create a safe space first.** Say "Ninakusikia na hii ni jambo zito. Je, uko salama sasa hivi?" before collecting details. Never ask a harassment victim to describe the incident repeatedly or in unnecessary detail.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Event name | "Jina la tukio hili ni nini — tamasha, mkutano, harusi, au aina nyingine?" |
| Ticket reference | "Una nambari ya tiketi au nambari ya agizo lako? Inaweza kuwa kwenye SMS, barua pepe, au tiketi ya karatasi." |
| Ticket seller vs organizer | "Ulinunua tiketi kutoka wapi — moja kwa moja kutoka kwa mwandaaji, au kupitia mtu mwingine au mtandao?" |
| Number of people affected | "Je, wewe peke yako uliathirika, au watu wengine pia waliokuwepo nawe?" |
| Safety check | "Je, uko salama sasa hivi? Je, ulipata jeraha lolote au mtu yeyote aliumia?" |
| Notice of cancellation | "Ulipata taarifa ya kufutwa / kuahirishwa kwa tukio lini? Na uliomba marejesho lini?" |
| Prior complaint | "Je, umeshalalamika kwa mwandaaji au muuzaji wa tiketi moja kwa moja? Walikusema nini au wamefanya nini?" |
| Desired outcome | "Unataka nini kitokee — tiketi ya mbadala, kurejeshewe pesa, au fidia ya aina nyingine?" |
| Would attend again | "Licha ya tatizo hili, ungekuwa tayari kuhudhuria tukio jingine la mwandaaji huyu hapo baadaye?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| `issue_type` | `safety_hazard` AND `injury_or_harm_occurred = Yes` | Emergency priority ticket; provide police (112) and OSHA Tanzania contacts; advise medical documentation |
| `issue_type` | `overcrowding_capacity_violation` | Notify LGA permit authority; flag for public safety review; create community safety ticket |
| `issue_type` | `harassment_by_staff` OR `harassment_by_attendees` AND `harassment_type = Sexual` | Police escalation; victim safety first; do not route through organizer |
| `issue_type` | `fake_invalid_ticket` | Advise preserve all evidence; refer to Tanzania Police CIFT; provide organizer contact for official ticket verification |
| `issue_type` | `performer_no_show` AND `notice_of_change_given = No` | Consumer Protection Act complaint; document advertising vs. actual delivery gap; calculate full refund entitlement |
| `issue_type` | `cancellation_refund_denied` AND `refund_requested_date` > 30 days ago | Escalate to Fair Competition Commission Tanzania; consumer protection complaint pathway |
| `issue_type` | `food_beverage_failure` AND `number_of_people_affected >= 3` | Public health emergency; notify district medical officer and TFDA |
| `prior_complaint_to_organizer` | Yes AND no response AND `event_date` > 14 days ago | Advise FCC Tanzania escalation; organizer has exceeded reasonable response window |
| `ticket_price_paid` | > 200000 TZS AND `issue_type = fake_invalid_ticket` | High-value fraud flag; police CIFT referral AND FCC notification |
| `issue_type` | `accessibility_failure` AND `accommodation_requested_in_advance = Yes` | Priority complaint; reference Tanzania Persons with Disabilities Act 2010 |

---

*Sources: ISO 20121:2024 Event Sustainability Management Systems, Citizens Advice UK (Complaining About Events), Contend Legal Event Complaint Guidance, UK Consumer Rights Act 2015 (performance service standards), ABTA complaint standards, Tanzania Consumer Protection Act 2008, Tanzania Occupational Health and Safety Act 2003, Local Government Authority event permit requirements*
