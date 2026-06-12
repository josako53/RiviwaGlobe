# Riviwa AI — Complaint (Grievance) Classification Knowledge Base

## 1. Purpose & Usage

This document trains Riviwa AI to **identify, classify, and prioritize** feedback that qualifies as a complaint or grievance. When a user submits feedback through any channel (text, voice, SMS, WhatsApp, in-app), the AI must:

1. **Detect** whether the feedback contains complaint signals
2. **Classify** which complaint category or categories apply
3. **Assign urgency** using the four-tier system below
4. **Route** it differently from suggestions, compliments, or neutral feedback

A complaint is any expression of **dissatisfaction, harm, failure, or unmet expectation** directed at a service, product, staff member, process, or organization. Complaints require acknowledgment, assignment, and resolution tracking. They are **not** suggestions (which propose improvement without expressing harm) or compliments (which express satisfaction).

---

## 2. Complaint vs. Other Feedback Types

| Signal Pattern | Type | Treatment |
|---|---|---|
| Dissatisfaction, anger, harm, failure | Complaint / Grievance | Assign SLA, escalate if critical |
| "I wish you had…", "It would be better if…" | Suggestion | Log for product team |
| "Great service", "well done", "thank you" | Compliment | Log for staff recognition |
| Question without negative sentiment | Inquiry | Route to support |
| Report of a safety/legal issue | Complaint (Critical) | Immediate escalation |

---

## 3. Core Complaint Signal Categories

The following categories contain the primary language signals used to detect complaints. Signals apply regardless of subject domain (account, service, product, staff, billing, delivery, application, website, etc.).

---

### 3.1 Explicit Dissatisfaction

Direct negative evaluations of a service, product, or experience.

not satisfied, very dissatisfied, extremely unhappy, not happy with, deeply unhappy, completely unsatisfied, not pleased, far from satisfied, left disappointed, feeling let down, fell short, not what I expected, not up to standard, very disappointed, severely disappointed, utterly disappointed, beyond disappointed, not good enough, nowhere near good enough, absolutely terrible, dreadful experience, horrible experience, awful experience, terrible service, dreadful service, shameful, disgraceful, outrageous, unacceptable, completely unacceptable, absolutely unacceptable, intolerable, inexcusable, embarrassing, humiliating, mortifying, appalling service, shocking service, inadequate service, substandard service, below standard service, insufficient service, poor outcome, badly done, poorly executed, poorly handled, badly managed, completely mismanaged

---

### 3.2 Frustration & Anger

Emotional intensity markers indicating elevated distress.

so frustrated, extremely frustrated, very frustrated, deeply frustrated, beyond frustrated, fed up, totally fed up, had enough, I've had enough, sick and tired, sick of this, tired of this, tired of waiting, annoyed, really annoyed, highly annoyed, irritated, extremely irritated, infuriated, left me furious, makes me angry, made me angry, I am angry, I'm angry about, outraged, I'm outraged, enraged, livid, absolutely livid, at my wit's end, reached my limit, pushed to the limit, lost my patience, my patience has run out, patience is exhausted, done with this, completely done, I give up, giving up on, can't take this anymore, can't deal with this, highly dissatisfied, deeply dissatisfied, completely fed up

---

### 3.3 Negation & Denial

Statements asserting that expected actions were not taken or items/services were not received.

did not work, does not work, doesn't work, won't work, never worked, stopped working, no longer works, failed to work, failed to deliver, failed to respond, did not receive, never received, have not received, yet to receive, did not get, never got, couldn't get, unable to get, didn't show up, never showed up, did not arrive, hasn't arrived, not delivered, not provided, not given, not resolved, not fixed, not addressed, not done, still not done, nothing was done, no action taken, no response, no reply, no follow-up, no one helped, no one called back, no one came, not helped, not assisted, not attended to, not acknowledged, felt ignored, being ignored, completely ignored, totally overlooked, brushed aside, dismissed, my concern was dismissed, my complaint was dismissed

---

### 3.4 Service Failure

Breakdowns in service delivery, including recurring and systemic failures.

poor service, bad service, appalling service, slow service, very slow service, extremely slow, delayed service, long delay, no service, service failure, service breakdown, complete failure, total failure, system failure, technical failure, complete breakdown, repeated failure, consistent failure, kept failing, keeps failing, ongoing issue, recurring problem, same problem again, problem persists, issue not resolved, unresolved issue, still having issues, still experiencing problems, problem continues, problem recurring, neglected, overlooked, no follow-through, not followed up, dropped the ball, mishandled, poorly handled, badly handled, service disruption, service interruption, service unavailable

---

### 3.5 Quality Complaints

Issues with the physical or functional quality of a product or service output.

poor quality, very poor quality, low quality, subpar quality, inferior quality, worst quality, degraded quality, quality has dropped, quality is lacking, defective, broken, damaged, faulty, malfunctioning, not functioning properly, not working properly, product is broken, item arrived broken, arrived damaged, came in bad condition, fell apart, fell apart quickly, broke immediately, broke after one use, stopped working after, disintegrated, worn out quickly, not durable, not built well, poorly made, shoddily made, cheap material, feels cheap, looks cheap, not as described, not as advertised, false advertising, misleading, misrepresented, not what was shown, different from the picture, not matching the description, inaccurate description, counterfeit, fake, cheap knockoff, deficient, below average quality

---

### 3.6 Waiting & Delays

Time-based grievances about excessive waits, missing updates, and missed deadlines.

too long to wait, waited too long, been waiting forever, still waiting, kept waiting, made to wait, wait time is unacceptable, excessive wait, unreasonable wait, ridiculous wait, hours of waiting, days of waiting, weeks of waiting, no update, no status update, no communication, left in the dark, keeping me in the dark, no notification, wasn't notified, not informed, not updated, no ETA given, ETA passed, overdue, long overdue, way past due, past the deadline, missed the deadline, delivery is late, late delivery, shipment is delayed, shipping delay, dispatch delay, took forever, took too long, too slow, unbearably slow, dragging on, going on too long, no end in sight, still not complete, still not finished, not yet resolved, no resolution in sight, delayed indefinitely, extended delay

---

### 3.7 Staff & Treatment

Complaints about the conduct, attitude, or competence of staff, agents, or representatives.

rude staff, very rude, extremely rude, staff was rude, employee was rude, agent was rude, representative was rude, disrespectful, treated disrespectfully, treated rudely, treated poorly, treated badly, treated unfairly, unfair treatment, discriminatory, felt discriminated, made to feel unwelcome, made to feel inferior, belittled, talked down to, condescending, dismissive attitude, unhelpful staff, completely unhelpful, not at all helpful, staff couldn't help, agent couldn't help, they didn't care, no one cared, staff seemed uninterested, didn't seem to care, indifferent, total indifference, ignored my concerns, ignored my complaint, told to call back, told to wait, brushed off, turned away, refused to help, denied help, lied to, was lied to, misled, given false information, given wrong information, misinformed, staff misinformed me, contradicting themselves, rude manager, uncooperative staff, unprofessional staff, incompetent staff, unknowledgeable, bad attitude, lazy, inattentive, uncaring, unsympathetic

---

### 3.8 Billing & Financial

Disputes involving charges, refunds, pricing, and financial errors.

overcharged, incorrectly charged, wrong amount charged, charged too much, charged twice, double charged, duplicate charge, unauthorized charge, unexpected charge, hidden fee, hidden charge, undisclosed fee, charge not disclosed, billing error, billing mistake, invoice is wrong, wrong invoice, incorrect bill, dispute the charge, disputing this charge, requesting a refund, need a refund, want my money back, refund not received, refund was denied, refund rejected, partial refund, no compensation, no reimbursement, no credit, price mismatch, price discrepancy, changed the price, price increase without notice, cancellation not processed, subscription still active, not cancelled, charged after cancellation, still being billed, payment taken wrongly, money deducted wrongly, unauthorized deduction, false billing, hidden fees, extra charges, bait and switch, money down the drain, overpriced, price gouging, extortion, stolen my money, missing refund, trapped in contract, impossible to cancel, auto-renew scam, shortchanged, swindled, taken advantage of, unfair pricing

---

### 3.9 Communication Failures

Breakdowns in responsiveness, clarity, or information delivery.

no response, never responded, failed to respond, slow to respond, took too long to respond, still waiting for a response, no reply, never replied, no acknowledgment, not acknowledged, no confirmation, confirmation not sent, no receipt, no update provided, not kept informed, poor communication, lack of communication, communication breakdown, miscommunication, misunderstood my request, didn't understand my issue, keep repeating myself, had to explain multiple times, transferred multiple times, transferred again, put on hold, left on hold, call disconnected, line was cut, got cut off, no callback, promised a callback, never called back, scheduled callback missed, appointment missed, appointment not honored, email not answered, email ignored, chat not answered, ticket not addressed, support ticket ignored, complaint not logged, complaint not filed, no ticket number, no case reference, slow response, unresponsive, unresponsive team, nobody responded

---

### 3.10 Deception & Trust

Signals involving dishonesty, broken promises, and accountability failures.

felt deceived, I was deceived, deliberately misleading, deliberately misled, false promise, broken promise, promise not kept, didn't honor the agreement, agreement violated, terms violated, not what was agreed, changed the terms, terms changed without notice, not transparent, lack of transparency, hidden information, concealed information, withheld information, not disclosed, not upfront, dishonest, blatantly dishonest, not telling the truth, covering up, cover-up, not taking responsibility, refusing accountability, blame-shifting, passing the buck, no accountability, no one responsible, no ownership, abdicated responsibility, false claims, making false claims, false statements, fabricated, fabricated excuse, making excuses, no genuine response, copy-paste response, automated reply, generic response, scripted answer, canned response, not sincere, insincere apology, lied, deceitful, manipulative, false promises

---

### 3.11 Process & Policy

Complaints about bureaucratic obstacles, policy violations, and technical system failures.

bad policy, unfair policy, unreasonable policy, policy is wrong, policy is flawed, policy makes no sense, inconsistent policy, contradicting policies, contradictory rules, loophole used against me, process is broken, broken process, complicated process, unnecessarily complicated, overly complicated, too many steps, too much bureaucracy, bureaucratic, red tape, excessive paperwork, unnecessary requirements, unreasonable requirements, over-verification, not following their own policy, violated their own policy, not following procedure, improper procedure, no procedure followed, system glitch, website glitch, app not working, app crashed, platform issues, login issues, couldn't log in, account locked, locked out, no access, access denied, account issue, account error, technical problem, technical issue, technical error, bug in the system, system error, outage, service outage, downtime, scheduled maintenance not communicated, unexpected downtime, broken functionality, feature not working, website is down

---

### 3.12 Expectations Unmet

Disappointment and harm from undelivered value.

not as expected, not what I expected, below expectations, did not meet expectations, far below expectations, fell short of expectations, very disappointing, hugely disappointing, utterly disappointing, great disappointment, massive letdown, big letdown, total letdown, waste of money, complete waste, not worth it, not worth the price, not worth the cost, not worth the effort, not worth my time, wasted my time, wasted my money, wasted my effort, cost me money, cost me time, caused inconvenience, great inconvenience, significant inconvenience, major inconvenience, caused problems, created a problem, made things worse, made it worse, compounded the problem, additional stress, unnecessary stress, caused distress, emotional distress, mental anguish, health affected, caused me harm, put me at risk, safety concern, safety issue, health risk, wellbeing affected, quality of life affected

---

### 3.13 Escalation Language

Signals indicating the complainant is formally escalating or threatening consequences.

demanding answers, demand an explanation, I demand a resolution, I insist on, requesting escalation, escalate this matter, speak to a manager, speak to a supervisor, speak to someone senior, need to speak to management, require a senior representative, want to speak to the CEO, going to escalate, will escalate, escalating this complaint, formally complaining, filing a formal complaint, lodging a formal complaint, registering a complaint, submitting a complaint, putting this in writing, putting this on record, going on record, documenting this, keeping evidence, will take this further, taking this further, pursuing this, will not let this go, not dropping this, seeking legal advice, consulting a lawyer, contacting a lawyer, contacting consumer protection, filing with consumer board, reporting to regulator, reporting to authorities, public awareness, warn others, share my experience, leave a review, post a review, write a review, going to the media, going public, going online, legal action, lawsuit, sue, file a complaint, file a claim, submit a grievance, reporting to police, opening a case

---

### 3.14 Emotional Expression

Deep emotional distress signals indicating significant personal impact.

heartbroken, heartbreaking experience, devastated, crushed, feel let down, feeling cheated, feel robbed, feel taken advantage of, exploited, betrayed, feel betrayed, sense of betrayal, loss of trust, no longer trust, trust is broken, trust was destroyed, confidence shattered, faith lost, lost all faith, no confidence anymore, reliability gone, can't rely on, unreliable, can't count on, not dependable, unprofessional, very unprofessional, completely unprofessional, not professional, lacks professionalism, shocking lack of professionalism, I am speechless, words can't describe, unbelievable, I can't believe, beyond belief, honestly disappointed, genuinely upset, deeply upset, deeply troubled, very troubled, concerned about this, alarmed, genuinely alarmed, humiliated, violated, abused, mistreated, disrespected, deeply hurt, betrayed, backstabbed, lied to, manipulated, gaslit

---

### 3.15 Comparative Disappointment

Complaints expressing decline in quality or persistent absence of improvement.

used to be better, was better before, quality has declined, standards have dropped, has gone downhill, deteriorated, service deteriorated, noticeable decline, significant decline, not the same anymore, things have changed, changed for the worse, not like it used to be, worse than before, much worse, far worse, getting worse, keeps getting worse, no improvement, no sign of improvement, things haven't improved, still the same problem, same issues persist, nothing has changed, no change, no effort to improve, no effort to fix, no effort to resolve, no attempt to address, not taking this seriously, don't seem to care, clearly don't care, put profits first, profit over people, money over customers, treat customers poorly, don't value customers, don't respect customers, customer service is lacking, customer care is absent, customer support is non-existent, support is useless, support team is unhelpful, can't get help, nowhere to turn, left with no options, no recourse offered, no remedy offered, no solution given, no solution provided

---

## 4. Cross-Domain Applicability

All complaint signals in Section 3 apply across all subject domains. When categorizing, note the **subject** alongside the **signal type**:

**Service domains**: account, billing, delivery, service, support, communication, payment, subscription, staff
**Technical domains**: application, mobile app, website, API, platform, system, network, software, hardware
**Product domains**: product, quality, item, order, package
**Operational domains**: security, privacy, compliance, policy, process, legal

*Example*: "The mobile app keeps crashing" → Category: Service Failure + Process & Policy | Domain: Technical / Mobile App

---

## 5. Urgency Tier System

### 5.1 🔴 Critical — Auto-escalate within 60 seconds

**Life & Safety Threats**

life is in danger, my life is at risk, fear for my life, fearing for my safety, someone could die, this could kill someone, could be fatal, life-threatening situation, health is deteriorating fast, patient is critical, patient is deteriorating, serious injury occurred, I am bleeding, severe allergic reaction, anaphylaxis, I cannot breathe, difficulty breathing, chest pain, unconscious, collapsed, seizure, stroke symptoms, heart attack symptoms, not responding, unresponsive, need emergency help, call an ambulance, medical emergency, fire, explosion, gas leak, electrical fault sparking, building is unsafe, structural damage, roof collapsed, flooding inside, flood risk, dangerous environment, violence occurred, physical assault, was attacked, threatened with violence, threat received, death threat, sexual assault, rape, abuse is happening, child is in danger, child at risk, domestic violence, being followed, stalking, armed person, weapon involved

**Legal & Regulatory Breaches**

this is illegal, illegal activity, criminal offense, fraud occurred, I've been defrauded, scammed, financial fraud, identity theft, data breach, personal data leaked, my data was exposed, privacy violation, GDPR violation, data protection breach, unauthorized access to my account, account was hacked, cybercrime, bribery, corruption, extortion, blackmail, coercion, forced to pay, threatened with consequences, regulatory violation, compliance breach, operating without a license, unauthorized practice, court order violated, injunction breached, contract breach with legal consequence, legal action, lawsuit, filing a police report, opening a case, whistleblowing, formal complaint to regulator

---

### 5.2 🟠 High — Escalate within 5 minutes

**Immediate Harm or Severe Loss**

I lost all my money, all my savings are gone, completely wiped out financially, bank account emptied, unauthorized transaction, money stolen, entire stock lost, crop destroyed, livestock died, animals are dying, equipment destroyed, total loss, everything is gone, irreversible damage, permanent damage, irreparable, business is collapsing, about to go bankrupt, cannot pay employees, operations have stopped, factory is shut down, systems are completely down, all services offline, data is lost, data deleted permanently, backup failed, no recovery possible, medication ran out, no medical supply, oxygen finished, blood supply critical, power completely cut off, water completely cut off, road completely blocked, completely stranded, stuck with no help, no food for days, no water access, child has not eaten, elderly patient has no care, vulnerable person unattended, dependent person in danger, disability emergency, abandoned patient

**Healthcare High-Priority**

patient is not breathing, patient collapsed, patient is unconscious, not responding, patient is in critical condition, patient is dying, this could be fatal, life-threatening emergency, patient deteriorating rapidly, condition worsening by the minute, patient is in severe pain, anaphylaxis reaction, patient is bleeding heavily, uncontrolled bleeding, blood pressure dangerously low, oxygen level dropping, patient cannot breathe, chest pain right now, heart attack symptoms, stroke symptoms, seizure occurring, patient fell from bed, wrong medication given right now, overdose occurred, patient given wrong drug, transfusion reaction, wrong blood type given, medical equipment failure on patient, oxygen machine stopped working, patient disconnected from life support, emergency room refusing patient, ambulance refused to come, patient turned away while critical, no bed in ICU, ICU is full, surgery delayed dangerously, no surgeon available, child is critically ill, newborn is in danger, mother in labor with complications, obstetric emergency, maternal hemorrhage

---

### 5.3 🟡 Medium-High — Assign to senior staff, same-day resolution

- Any complaint tagged with **escalation language** (Section 3.13)
- Complaints marked as **repeated** or **recurring** (same user, same issue, multiple submissions)
- Complaints involving **financial loss** without immediate danger
- Complaints from **vulnerable users** (elderly, disabled, children)
- Any complaint containing **3 or more signal categories simultaneously**
- Complaints referencing **regulatory bodies, legal action, or media**

---

### 5.4 🔵 Urgency Language Boosters

These words boost the priority score of any feedback that already contains complaint signals:

**Immediacy**: urgent, immediately, ASAP, right away, right now, time-sensitive, emergency, critical, as soon as possible, without delay, fast-track, within the hour, clock is ticking, expedite

**Severity**: severe, catastrophic, catastrophic failure, blocker, showstopper, mission-critical, production down, fatal error, zero-day, widespread, major incident, total failure, unrecoverable, system down, all hands on deck

**Priority Designations**: top priority, highest priority, P1, P0, Priority 1, Priority 0, Tier 1 escalation, Sev-1, Severity 1, red alert, code red

**Consequence Threats**: legal action, lawsuit, sue, report to regulator, going to the media, going public, regulatory complaint, SLA breach, compliance violation, financial loss, irreversible damage, safety hazard

**Direct Action Phrases**: action required immediately, immediate attention required, needs urgent attention, please respond urgently, urgent attention required, rush order, please prioritize, awaiting immediate response, do not delay, I need this fixed now, this cannot wait

---

## 6. Healthcare / Hospital-Specific Vocabulary

### 6.1 Waiting & Admission Complaints

waited too long in the queue, no bed available, no beds, sent home without treatment, not admitted, admission was delayed, discharge was delayed, kept waiting for hours, hours in the emergency room, never seen by a doctor, waited all day, never attended to, left in the waiting room, waiting room was overcrowded, overcrowded ward, no place to sit, no space in the ward, no triage done, triage was ignored, ignored at reception, reception was unhelpful, reception was rude, made to come back another day, appointment was rescheduled, appointment was cancelled, appointment not honored, came for nothing, wasted my trip, long queue, queue was disorganized, queue was unfair, no queue management, queue jumped, favoritism in the queue, waited past my appointment, late appointment, no explanation for the delay, no update on wait time, given no information, not told anything, left in the dark

### 6.2 Diagnosis & Care Complaints

misdiagnosed, wrong diagnosis, diagnosis was incorrect, condition got worse after treatment, wrong medication given, wrong dosage, overdosed, underdosed, medication was not explained, side effects not disclosed, not monitored after medication, prescription was wrong, prescribing error, wrong test ordered, unnecessary test, test results were lost, test results delayed, test results wrong, lab error, incorrect lab result, no follow-up after diagnosis, not called back with results, results never shared, kept waiting for results, didn't explain my condition, doctor didn't explain, not told what was wrong, diagnosis was unclear, confusing explanation, too technical to understand, doctor was dismissive, doctor ignored my symptoms, my symptoms were overlooked, told it was nothing, minimized my pain, pain was not taken seriously, not referred when needed, referral was denied, referral was delayed, no specialist seen, specialist appointment too long

### 6.3 Staff Conduct Complaints

nurse was rude, nurse was dismissive, nurse ignored me, doctor was rude, doctor was arrogant, doctor didn't listen, staff were unprofessional, staff were careless, staff were negligent, doctor seemed rushed, doctor was in a hurry, no time spent with me, felt rushed out, did not feel cared for, felt like a number, no personal care, no compassion shown, cold attitude, uncaring staff, staff were talking among themselves, staff were on their phones, not attended to properly, no dignity, treated without dignity, my dignity was violated, privacy not respected, curtain not drawn, examined in public, spoken to loudly about my condition, personal information shared, confidentiality breached, patient privacy ignored, spoken to rudely in front of others, disrespected in front of family, humiliated, made to feel unwelcome, made to feel like a burden, discriminatory treatment, felt discriminated against

### 6.4 Facilities & Hygiene Complaints

dirty ward, unhygienic, not clean, blood on the bed, soiled linen, bedsheets not changed, toilet was dirty, bathroom was unusable, no running water, water was unavailable, no soap, no sanitizer, infection risk, got an infection at the hospital, hospital-acquired infection, unhygienic equipment, unsterilized instruments, broken equipment, equipment not available, no equipment, no gloves used, no mask worn, no protective gear, cold ward, ward was too hot, no ventilation, bad smell, foul smell, bad odor, no food provided, food was cold, food was unfit, food was poor quality, no drinkable water, no ambulance available, ambulance was late, no wheelchair, wheelchair not available, stretcher not available, elevator not working, no access for disabled, accessibility issues, not wheelchair friendly, parking was difficult, long walk from parking

### 6.5 Billing & Insurance Complaints

overcharged, charged for services not received, charged twice, billing error, incorrect bill, unexplained charges, hidden charges, no receipt given, receipt was wrong, not told the cost upfront, price not disclosed, price was too high, unaffordable, insurance not accepted, my insurance was rejected, insurance claim denied, pre-authorization not done, not covered, told I was covered, not reimbursed, slow reimbursement, insurance process took too long, no explanation of charges, no itemized bill, asked for payment before treatment, refused treatment due to money, turned away for non-payment, deposit too high, could not afford the deposit, payment plan denied, financial assistance denied, no waiver offered, bribery expected, bribe was demanded, expected unofficial payment, extortion, forced to pay extra, kickbacks required

### 6.6 Healthcare Emergency Escalation Signals (🔴 Critical)

Code Blue, Code Red, life-threatening, critical condition, unresponsive, not breathing, severe hemorrhage, profuse bleeding, cardiac arrest, chest pain, stroke protocol, anaphylaxis, severe allergic reaction, Triage Level 1, immediate triage, mass casualty incident, oxygen supply failure, biohazard spill, emergency admission, patient deteriorating rapidly, urgent surgery needed, ICU required, medication emergency, ambulance delay critical, emergency case, severe pain, difficulty breathing, unconscious patient, excessive bleeding, delayed treatment risk, imminent risk, patient at risk

---

## 7. Sector-Specific Complaint Vocabulary

### 🌾 Agriculture & Farming

poor yield, rotten crops, pest infestation, blighted, soil degradation, broken tractor, counterfeit seeds, bad fertilizer, defective machinery, late delivery of feed, diseased livestock, expensive replacement parts, low germination rate, spoiled harvest, poor drainage, overgrown, faulty irrigation, weed takeover, pesticide burn, unfair market price, contaminated water, moldy grain, equipment failure, unreliable farmhand, delayed harvest, shortchanged by buyer, inferior feed, malfunctioning silo, rusted tools, broken fencing, sick animals, unseasonal frost damage, drought damage, false claims on chemicals, inadequate yield

**Agriculture Emergency Signals** (🔴/🟠): rapidly spreading disease, immediate quarantine required, imminent freeze, frost warning, mass die-off, complete crop failure, harvest at risk, rotting in the field, toxic runoff, contamination, irrigation failure during drought, total equipment breakdown during harvest window, supply chain emergency, out of feed for livestock

### 📡 Telecom (Internet, Phone, TV)

dropped calls, dead zone, no signal, spotty coverage, slow broadband, throttled speed, hidden roaming fees, data cap, router keeps restarting, unexpected price hike, poor audio quality, static on the line, delayed texts, technician never arrived, unhelpful tech support, auto-renewed without asking, forced bundle, cancellation penalty, disconnected service, arbitrary charges, lagging connection, terrible ping, frequent outages, unannounced maintenance, broken modem, bait and switch plan, impossible to reach an operator, scam calls, unauthorized account changes, misleading coverage map, poor reception

**Telecom Emergency Signals** (🔴/🟠): total blackout, complete network outage, fiber cut, severed line, core routing failure, 911 routing failure, Sev-1 outage, massive data breach, tower down, DDoS attack, under active attack, nationwide impact, critical infrastructure compromised

### 🎉 Events (Conferences, Concerts, Parties)

overcrowded, terrible acoustics, couldn't see the stage, ran out of food, disorganized registration, started late, boring speaker, unprofessional host, dirty restrooms, poor crowd control, too loud, overpriced tickets, VIP was a scam, no parking, freezing venue, boiling hot venue, bad lighting, cancelled last minute, no refunds, misleading agenda, long lines, insufficient seating, audio feedback, broken microphone, poorly planned, uncoordinated staff, scheduling conflicts, lack of security, unsafe crowd, bad visibility, false advertising

**Event Emergency Signals** (🔴): evacuate immediately, evacuation order, active threat, lockdown, crowd crush, stampede risk, structural collapse, fire alarm, active fire, mass medical emergency, complete power failure, security breach, severe weather approaching, headliner cancellation, event terminated

### 📚 Training (Workshops, Corporate, Fitness)

waste of time, outdated material, boring instructor, irrelevant content, rushed presentation, confusing manual, no practical exercises, broken equipment, unqualified trainer, skipped modules, unengaging, repetitive, copy-pasted slides, audio issues during webinar, no Q&A time, certification delayed, unhelpful feedback, disorganized syllabus, unapproachable coach, poorly structured, lack of application, monotone speaker, insufficient handouts, poorly paced, rushed ending, skipped breaks

**Training Emergency Signals** (🔴/🟠): immediate safety stand-down, mandatory compliance deadline today, certification expired, regulatory breach, critical safety violation, medical emergency, severe liability risk, stop work authority, system lockout due to failed compliance

### 🎓 University & School

unfair grading, useless lectures, unavailable professor, unhelpful advisor, expensive textbooks, terrible dorms, awful cafeteria food, registration system crashed, closed classes, disorganized syllabus, harsh curve, noisy library, hidden campus fees, outdated curriculum, ignored accommodations, unsanitary campus, lost assignment, biased teacher, arbitrary rules, unsupportive administration, poor wifi in dorms, overbooked classes, mandatory useless fees, unkept facilities, lack of resources, unfair policy, unapproachable faculty, slow grading, unresponsive TA, pointless busywork

**Education Emergency Signals** (🔴): campus lockdown, shelter in place, active threat, intruder, missing student, mental health crisis, imminent harm, Title IX emergency, immediate suspension, expulsion hearing, severe bullying or harassment incident, contagious outbreak, hard deadline passed, system-wide exam failure

### 🍽️ Food & Restaurant

cold food, raw meat, overcooked steak, hair in food, rude waiter, ignored by server, took an hour to get water, dirty silverware, sticky table, overpriced menu, tiny portions, tasteless, missing items in takeout, food poisoning, stale bread, wrong order, loud atmosphere, bad ambiance, compulsory gratuity, watered-down drinks, soggy fries, wilted salad, smelly bathroom, unaccommodating to allergies, greasy, burnt edges, unsanitary kitchen, bug on plate, slow service, rushed out, unhelpful host, table not ready

**Food Emergency Signals** (🔴): foodborne illness outbreak, food poisoning, severe allergic reaction, anaphylactic shock, health inspector shutdown, Class 1 Food Recall, kitchen fire, grease fire, critical temperature failure, walk-in freezer completely down, cross-contamination incident, sewage backup, no running water, total POS system crash

### 🚗 Automotive (Car, Dealership, Mechanic)

lemon, overpriced repairs, scratched paint, check engine light returned, sleazy salesman, predatory loan, upselling, unauthorized repair, rattling engine, squeaky brakes, bald tires, false mileage, took all day for oil change, hidden dealership fees, unhonored warranty, bad alignment, stalled on highway, cheap parts used, greasy steering wheel, dirty interior after service, misdiagnosed issue, pressure sales tactics, bait and switch pricing, broken AC, fluid leak, transmission slipping, ignored recall, incomplete repair, damaged during service

**Automotive Emergency Signals** (🔴): immediate stop-drive order, brake failure, engine fire, thermal event, explosive recall, airbag shrapnel, steering locked while driving, total loss, catastrophic accident, stranded in dangerous location, catastrophic transmission failure, high-voltage battery exposure

### 📱 Electronics (Gadgets, Hardware)

dead on arrival, battery drains fast, overheating, cracked screen, unresponsive touch, bloated software, planned obsolescence, frayed cord, stopped charging, distorted speakers, cheap plastic, button stuck, blurry camera, dropped Wi-Fi, constant crashing, bricked after update, voided warranty, incompatible, dead pixels, fragile casing, loud fan noise, screen burn-in, poor resolution, delayed input, laggy interface, false battery life claims, loose ports, snapped hinge, unusable keyboard, inaccurate sensors

**Electronics Emergency Signals** (🔴): battery expanding, swollen battery, catching fire, thermal runaway, electric shock hazard, exposed wiring, zero-day vulnerability, active exploit in the wild, device bricked widespread, mass data wipe, unrecoverable data loss, critical firmware corruption

### 🛒 Online Store (E-commerce)

never arrived, package stolen, tracking not updating, fake reviews, wrong item shipped, difficult returns, restocking fee, scam site, poor packaging, damaged in transit, cheap knockoff, out of stock after ordering, ignored customer service emails, unsecure checkout, spam emails after purchase, counterfeit good, misleading photos, size chart is wrong, refused refund, lost in transit, missing pieces, poor quality materials, unhelpful chatbot, hidden shipping costs, late delivery, incorrect billing address, account locked, deceptive marketing, subscription trap

**E-commerce Emergency Signals** (🔴/🟠): checkout down, payment gateway offline, mass fraud attack, stolen credit card testing, site crashed during major sale, database wiped, corrupted customer data, API rate limit exceeded, missing funds, failed payouts, inventory wiped out due to overselling glitch, domain hijacked, SSL certificate expired, catastrophic fulfillment failure

---

## 8. General Complaint Vocabulary Patterns

These additional signals appear across all feedback types and reinforce complaint classification when detected alongside primary signals.

**Direct Negative Evaluations**: awful, terrible, horrible, worst, bad, abysmal, dreadful, horrendous, atrocious, pathetic, deplorable, useless, garbage, trash, junk, flawed, imperfect, inadequate, deficient, subpar, zero stars, one star, do not recommend, avoid, stay away, never again, regret, nightmare, joke, absurd, waste, ruined, failing, lamentable, wretched, miserable, poor showing, bad look, complete nonsense, utter rubbish, epic fail, total fail, abysmal failure, worser than expected, hot mess, trainwreck, dumpster fire

**Idiomatic Complaint Expressions**: what a joke, absolute disgrace, complete waste of time, highway robbery, daylight robbery, left a bad taste in my mouth, dropped the ball, not what I signed up for, load of crap, not worth a dime, wouldn't recommend to my worst enemy, run away, steer clear, avoid like the plague, save your money, save yourself the headache, don't bother, do not buy, buyer beware, running in circles, hitting a brick wall, talking to a wall, pulling teeth, jumping through hoops, red tape, wild goose chase, left high and dry, swept under the rug, gave me the runaround, cold shoulder, slap in the face, kick in the teeth, adding insult to injury, last straw, breaking point, enough is enough, I've had it, completely out of line, cannot believe it, makes no sense, royal screw up

**General Technical Complaint Signals**: glitch, bug, crashing, frozen screen, unresponsive, lag, high ping, disconnect, server down, maintenance, offline, error code, fatal error, rebooting, looping, dead pixel, won't charge, battery drain, overheating, buffering, won't load, slow download, failed upload, sync error, corrupted file, lost data, missing save, malware, spyware, virus, hacked account, compromised password, phished, no signal, dropped call, static, poor audio, page not found, gateway timeout, database error, throttling, capped speed, forced update, broken update, behind paywall, un-cancellable, useless bot, no human agent

**Emotional State Signals (Intensifiers)**: furious, enraged, livid, seething, aggravated, exasperated, distressed, anxious, overwhelmed, disgusted, repulsed, sickened, appalled, horrified, dismayed, depressed, heartbroken, miserable, cynical, bitter, resentful, suspicious, distrustful, wary, skeptical, helpless, powerless, desperate, hopeless, exhausted, burnt out, at my wits end, impatient, restless, agitated, intimidated, bullied, harassed, stalked, threatened, violated, abused, mistreated, unappreciated, disrespected, insulted, offended, hurt, deeply hurt

---

## 9. AI Classification & Routing Rules

### Detection Rule
A feedback submission should be classified as a **complaint** if it contains **one or more signals** from Sections 3, 6, 7, or 8, OR if the overall sentiment is clearly negative and directed at a specific service, product, staff member, or process.

### Urgency Scoring
- Contains **any 🔴 Critical signal** → immediate escalation, do not wait for confirmation
- Contains **any 🟠 High signal** → escalate within 5 minutes
- Contains **escalation language** (Section 3.13) + **2+ other signal categories** → treat as 🟠 High
- Contains **🔵 Urgency booster words** alongside complaint signals → increase priority tier by one level
- Contains **only mild signals** (e.g., "not satisfied", "a bit slow") → 🟡 Medium

### Multi-Category Signals
When a complaint contains signals from **3 or more categories**, it should be flagged as:
- **Complex complaint** — requires senior staff
- **Pattern complaint** — cross-reference for recurring issues from same user or organisation

### Special Treatment
- **Escalation language** (Section 3.13) always triggers a manager notification, regardless of other tier
- **Healthcare/hospital complaints** with life & safety signals → 🔴 regardless of language softness
- **Financial harm complaints** (charged wrongly, unauthorized deduction, refund denied) + urgency booster → 🟠 minimum
- **Discrimination complaints** (treated unfairly, discriminatory, felt discriminated) → flag separately for compliance review

### Distinction from Suggestions
A complaint says something went **wrong or caused harm**. A suggestion says something **could be better**. Phrases like "I wish", "it would be nice if", "maybe you could", "have you considered" — without accompanying negative sentiment — should be classified as suggestions, not complaints.

---

*Last updated: 2026-06-12 | Maintained in: obsidian_vault/12_complaint_knowledge_base.md | Auto-indexed by ObsidianRAGService on startup*
