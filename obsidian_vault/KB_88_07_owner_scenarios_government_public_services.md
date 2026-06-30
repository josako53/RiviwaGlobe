# Owner Standard Scenarios — Government / Public Services
## Industry 7 of 33 | KB_88 Series

**Source document:** Part of the Riviwa Owner Standard knowledge base (KB_87, KB_88 series)
**Scenarios:** 10 real-world documented cases (expandable over time)
**Sources:** CFPB, UK Financial Ombudsman, FTC, WHO, World Bank, ILO, news reports, call center data
**Index:** See KB_88_index.md for all 33 industries

---

## 7. Government / Public Services

### Scenario 7-1: Automated Welfare Debt Notice Demands Repayment of Money Never Owed (Pattern E)
**Real Basis:** Royal Commission into the Robodebt Scheme, Australia (2023); Federal Court — Amato v Commonwealth (2019); AI Incident Database Incident 57; $1.2 billion class action settlement; Victoria Legal Aid published analysis
**The Problem:** A former Centrelink recipient in Australia receives a certified letter demanding repayment of $4,800 in welfare "overpayments" from three years ago. The letter states the debt was calculated using ATO annual income data and that her next tax refund will be intercepted within 28 days if the debt is not resolved. She has payslips showing her actual fortnightly earnings were consistently below the payment threshold throughout the entire period, but the Centrelink online portal displays no upload function. The automated phone line tells her she must "prove the debt is incorrect."
**What staff/org would do:** Confirm the debt is "in the system" and therefore valid; advise her to lodge a written dispute that will take 12 or more weeks to review; proceed with tax refund interception in the meantime with no pause or hold applied.
**What the Owner does:** Acknowledge the serious financial and emotional distress of receiving an unexpected large debt demand from a government agency; flag this as a well-documented algorithmic averaging error; instruct her to preserve all payslips and income documents immediately; direct her to free legal help.
**Riviwa AI instruction:**
- is_urgent=true (impending tax refund interception within 28 days)
- Opening reply: acknowledge the shock of receiving this demand — this is a known, documented failure of an automated system that wrongly accused hundreds of thousands of Australians; she is not alone and she has strong grounds to fight it
- Direct to: Centrelink formal Review of Decision (lodged online or in person at Services Australia); National Debt Helpline 1800 007 007 (free, specialist community legal centre referral); welfare rights units at community legal centres; Royal Commission compensation claims pathway if still open
- Evidence to collect: All payslips covering the disputed period; bank deposit records; ATO income summaries; every piece of Centrelink correspondence with dates; screenshot of the online portal showing the demand and absence of an upload function
- Feedback category tag: Financial Harm / Automated System Failure / Urgent

---

### Scenario 7-2: Unemployment Fraud Accusation Issued Entirely by Algorithm — Wages Being Garnished (Pattern E)
**Real Basis:** Wisconsin Law Review — "Automated Stategraft: Faulty Programming and Improper Collections in Michigan's Unemployment Insurance Program" (2021); Undark investigative report on Michigan MiDAS (2020); AI Incident Database Incident 373; Ford School of Public Policy MiDAS explainer (2024); $20 million class action settlement
**The Problem:** A laid-off factory worker in Michigan receives a certified letter from the Michigan Unemployment Insurance Agency charging her with intentional misrepresentation of her unemployment claim. The letter demands $14,200 in repayment plus quadruple fraud penalties totaling $56,800. She has already discovered her wages from a new part-time job are being garnished — she found out when her paycheck arrived short. She was never notified before garnishment began and received no opportunity to respond. When she calls the UIA, an automated system confirms her case is "in collection status." A live agent, reached after 35 minutes on hold, tells her: "The determination has been made — you can appeal in writing." She has her original layoff notice and a letter from her former employer confirming the separation.
**What staff/org would do:** Confirm the automated determination is valid; state that appeals take several months and that wage garnishment continues during the appeal period; provide no interim relief.
**What the Owner does:** Treat this as an emergency — active wage garnishment from a determination the system made with no human review is causing immediate financial harm.
**Riviwa AI instruction:**
- is_urgent=true (wages actively being garnished; household income reduced now)
- Opening reply: acknowledge this is alarming — having wages seized over a fraud accusation she did not commit is an emergency, and this automated system was later found to have a 93% error rate in independent analysis; her documentation puts her in a strong position
- Direct to: Michigan UIA appeals process — written appeal to the Michigan Office of Administrative Hearings and Rules (MOAHR); Michigan Legal Aid (michiganlegalhelp.org); ACLU of Michigan; if the class action settlement is still open, class action claims line; Michigan Attorney General Consumer Protection division
- Evidence to collect: Original separation notice from employer; employer letter confirming layoff (not resignation); all UIA correspondence with reference numbers; bank records showing garnishment amounts and dates; pay stubs showing the deductions
- Feedback category tag: Financial Harm / Automated System Failure / Wrongful Garnishment / Urgent

---

### Scenario 7-3: Tax Penalty for On-Time Return — 4 Hours on Hold, Then Disconnected (Pattern B)
**Real Basis:** National Audit Office — "Taxpayers let down by poor HMRC customer service" press release (2024); UHY Hacker Young analysis of HMRC wait time doubling (2024); TaxWatch UK investigation; NAO finding that 72% of HMRC calls in 2023/24 were "failure demand" — calls caused by agency errors
**The Problem:** A self-employed graphic designer in Manchester receives a penalty notice from HMRC for a late Self Assessment return — but her online HMRC account shows the return was marked as submitted with a confirmation timestamp. The online portal provides no mechanism to challenge the penalty; a blue banner reads "Call HMRC to query this." She calls at 9:14am. After 1 hour 52 minutes on hold, the line goes silent and then plays a disconnect tone. She calls again at 2pm. After 2 hours 11 minutes she reaches an agent who tells her: "I can see the note on your account but I can't overturn penalties — you'll need to write to us by post." The agent confirms the penalty is accruing interest daily and the written process takes up to 8 weeks.
**What staff/org would do:** Confirm she must appeal in writing; allow interest to accrue on the penalty during that 8-week period; provide no interim hold on the debt.
**What the Owner does:** Validate the absurdity of a government-caused loop — her return was submitted on time, she has the proof, and the resolution route is clear once she knows it.
**Riviwa AI instruction:**
- is_urgent=false (penalty is accruing interest but no immediate garnishment)
- Opening reply: acknowledge the extreme frustration of spending nearly 4 hours on hold to be told to write a letter — this is one of the most common HMRC failure patterns documented by the National Audit Office; she has clear grounds for a successful appeal
- Direct to: HMRC statutory appeal — Self Assessment Penalty Appeal form SA370 (available on gov.uk); include the submission confirmation timestamp as primary evidence; if HMRC does not respond within 8 weeks, escalate to the Adjudicator's Office (gov.uk/adjudicator-office); LITRG (Low Incomes Tax Reform Group) free helpline for self-employed taxpayers
- Evidence to collect: Screenshot or PDF of the HMRC online account submission confirmation with timestamp; the penalty notice with reference number and charge date; a call log recording both call dates, start times, hold duration, and agent name (if obtained on the second call); any automated confirmation email from HMRC at the time of original submission
- Feedback category tag: Call Center Failure / Bureaucratic Loop / Information Failure

---

### Scenario 7-4: Disability Benefit Denied — Agent Will Not Explain the Assessment Score (Pattern A)
**Real Basis:** Disability Rights UK citing DWP official statistics (2022); ME Association citing The Independent (2022); Citizens Advice PIP guidance; DWP Statistics — PIP and ADP Official Statistics to February 2022; 80,000 decisions overturned at mandatory reconsideration; 43% reversal rate documented
**The Problem:** A 41-year-old woman in Glasgow with fibromyalgia and chronic fatigue syndrome has her Personal Independence Payment claim rejected. The decision letter states only that she "did not score enough points in the daily living component" — it provides no activity-by-activity breakdown and no explanation of how the assessor scored each descriptor. She calls the DWP and asks the agent to explain which activities were assessed and at what level. The agent says: "I'm not able to discuss the assessment outcome over the phone — that has to go through mandatory reconsideration in writing." She explains she is housebound on most days and asks whether she can submit the reconsideration verbally. The agent says no. She asks what the current mandatory reconsideration wait time is. The agent says "a few months."
**What staff/org would do:** Refer her to the mandatory reconsideration written process and end the call, with no further assistance, no explanation of her rights, and no information about the assessment report she is legally entitled to request.
**What the Owner does:** Recognise this is a known systemic failure — nearly half of challenged PIP decisions are reversed before they even reach tribunal — and give her the concrete tools to challenge it.
**Riviwa AI instruction:**
- is_urgent=false (no immediate income loss, but welfare rights require time-sensitive action)
- Opening reply: acknowledge how exhausting and disempowering it is to be denied with no explanation after going through an assessment; confirm that 43% of decisions challenged at mandatory reconsideration are reversed by DWP itself — her instinct to fight this is correct and well-founded
- Direct to: Citizens Advice (free specialist PIP welfare help — citizensadvice.org.uk); Disability Rights UK factsheet on mandatory reconsideration; Scope helpline 0808 800 3333; Welfare Rights Officer at her local council; deadline is 1 month from the decision letter date (extendable for good cause — she should call DWP to request an extension if needed given her health)
- Evidence to collect: Request the Disability Assessor's report in writing from DWP immediately (she is legally entitled to it under the Data Protection Act); keep the original decision letter; document all daily activities and how her conditions affect them using the official PIP descriptor framework; gather letters from her GP, specialist, and any carers
- Feedback category tag: Service Refusal / Rights Violation / Disability / Information Failure

---

### Scenario 7-5: Police Officer Demands Cash Bribe to Clear Passport Verification (Pattern C)
**Real Basis:** LawRato.com documented legal complaint (primary source — complaint text on record); Ministry of External Affairs Rajya Sabha Parliamentary Question No. 1049 on corruption in passport verification in West Bengal; Moneylife — passport applicant files Anti-Corruption Bureau complaint (Bengaluru); Transparency International CPI 2024 (India: 38/100, ranked 96th of 180 countries)
**The Problem:** A 29-year-old software engineer in Bengaluru has submitted his first passport application. His new employer abroad has given him a six-week deadline before the job offer lapses. Three weeks after submitting, the constable assigned to his mandatory police verification visits his apartment. The officer reviews nothing in writing, looks around the flat, and then says: "There are some complications in your file. These things take a long time to clear. If you want it done quickly it's ₹1,200." When the applicant asks what complications, the officer shows him nothing. The applicant is afraid that if he refuses, the officer will submit an adverse verification report, blocking his passport entirely. The Passport Seva Kendra helpline, when called, confirms only that his application is "under police verification" with no estimated date.
**What staff/org would do:** The application remains stuck at "under verification" with no movement; the helpline offers no escalation pathway for misconduct reported over the phone and redirects all complaints to the written Ministry of External Affairs grievance process.
**What the Owner does:** Treat this as urgent given the job offer deadline; acknowledge the vulnerability and fear the applicant is experiencing; provide concrete reporting routes that do not require paying the bribe.
**Riviwa AI instruction:**
- is_urgent=true (job offer expires in approximately three weeks; bribery demand is active)
- Opening reply: acknowledge the fear and pressure he is under — this is an abuse of authority by a public official and he should not pay; this pattern has been documented across multiple Indian cities and there are reporting routes specifically designed for it
- Direct to: Karnataka Anti-Corruption Bureau online complaint portal (acb.karnataka.gov.in) or ACB helpline 1064 — request a trap operation; Passport Seva customer care 1800-258-1800 (document the call date and reference number); MEA Grievance Portal at passportindia.gov.in under the Grievance section; Lokayukta Karnataka for systemic corruption complaints; Bengaluru Police Commissioner's office complaint cell
- Evidence to collect: Note the constable's full name, badge number, date and time of visit, and exact words used; do not pay under any circumstances; if he feels safe doing so, he may record the conversation on his phone (Karnataka follows one-party consent); keep his job offer letter with the deadline date as evidence of urgency; retain all passport application receipts and reference numbers
- Feedback category tag: Corruption / Staff Misconduct / Urgent

---

### Scenario 7-6: Driving License Revoked for Unpaid Fine — Driver Was Never Told and Loses His Job (Pattern F)
**Real Basis:** ACLU case page — Johnson v. Jessup; ACLU of North Carolina settlement press release (March 2022); Southern Coalition for Social Justice press release; Duke University Wilson Center study documenting racial disparity in suspensions 2013–2017; CBS17 North Carolina reporting; federal court settlement requiring NCDMV to notify 185,000 eligible drivers
**The Problem:** A 36-year-old Black father of three in Durham, North Carolina is pulled over for a broken tail light. The officer tells him his license was suspended more than two years ago for an unpaid $180 traffic fine. He had no idea — he never received any suspension notice at his current address. He is arrested at the scene. The following morning he loses his job: his employer is a delivery company that requires a valid license. He cannot drive to pick up his children from school. To reinstate his license, he must pay $700+ in accumulated fees plus the original fine — money he does not have, particularly now that he is unemployed. When he calls the NCDMV, an automated system confirms his license is suspended and lists the reinstatement fee, but provides no information about hardship hearings or the 2022 federal court settlement.
**What staff/org would do:** Inform him of the reinstatement fees; provide no information about the judicial settlement, the hardship hearing process, or the disproportionate impact of the scheme on Black drivers; make no proactive outreach.
**What the Owner does:** Recognise this as a documented pattern of discriminatory enforcement; ensure he knows his rights under the 2022 federal court settlement and where to get free legal help.
**Riviwa AI instruction:**
- is_urgent=false (immediate crisis of arrest has passed; financial and employment harm is ongoing)
- Opening reply: acknowledge the cascading harm this has caused — losing a job because of a suspension he was never notified of, on a debt that disproportionately targets people in financial hardship, is precisely what a 2022 federal court settlement found to be unjust
- Direct to: Southern Coalition for Social Justice (919-323-3380) — represented plaintiffs in the settlement and can advise on eligibility; ACLU of North Carolina; Legal Aid NC (legalaidnc.org) for free representation in the hardship hearing; North Carolina DMV Failure to Pay Hardship Hearing request; the settlement requires NCDMV to proactively notify 185,000 eligible drivers — he should ask whether he is on that list
- Evidence to collect: The original traffic citation; any DMV correspondence he did receive at any address; arrest record from this incident; employment termination notice; bank statements showing financial hardship; documentation of any prior attempts to check his license status
- Feedback category tag: Discrimination / Rights Violation / Financial Harm / Racial Disparity

---

### Scenario 7-7: Unemployment Benefits Cut Off by Algorithm — Single Mother Has No Income and Rent Is Due (Pattern E)
**Real Basis:** StateScoop — "FTC complaint targets automated public benefit fraud detection" (2021); Time Magazine — "How Government Fraud Detection Algorithms Are Leaving Innocent People Without Benefits" (2021); Center for American Progress analysis of Pondera Fraud Detect deployment; EDD reported 4–8 hour hold times and mass call disconnections at COVID peak (2020–2021)
**The Problem:** A single mother in Fresno, California wakes to find her EDD unemployment deposit has not arrived. Rent is due in four days. She has two children. Her EDD online account shows her claim as "pending review — no payment issued." No letter, no email, no text message has been sent to explain why. She has been receiving payments without issue for four months. She calls the EDD at 8am and the automated system tells her the estimated wait is "over 4 hours." She stays on hold while her children nap. At the 3 hour 17 minute mark, the call drops without connecting her to anyone. She calls again — same automated message. She has never been told what triggered the "pending review" flag.
**What staff/org would do:** The portal continues to show "pending review" indefinitely; no notice is issued; phone lines remain inaccessible with dropped calls; no callback option is offered.
**What the Owner does:** Treat this as a financial emergency — no income, children to feed, rent due in four days — and provide immediate parallel actions.
**Riviwa AI instruction:**
- is_urgent=true (no income, rent due in 4 days, children in the household)
- Opening reply: acknowledge this is a crisis — having payments stopped without any warning or explanation while responsible for children and facing imminent rent arrears is a genuine emergency; this is a known pattern of automated benefit suspension that affected over a million California claimants, the majority of whom were found to be completely legitimate
- Direct to: EDD appeals portal (appeals.edd.ca.gov — she can file online without reaching the call center); California Legal Aid Foundation (lawhelpca.org) for free urgent EDD help; 211 Fresno for emergency rental assistance and food access; CalFresh (food stamps) emergency application; local food banks for immediate food access while the appeal processes
- Evidence to collect: Screenshot of the EDD account showing "pending review" and the date payments stopped; bank records showing the last payment received and the gap; all EDD correspondence; a log of every call attempt with date, time, hold duration, and outcome (dropped call notation)
- Feedback category tag: Automated System Failure / Financial Emergency / Urgent / Vulnerability

---

### Scenario 7-8: Monthly Benefit Payment Reduced With No Explanation — Agency Refuses to Say Why (Pattern A)
**Real Basis:** Citizens Advice press release — "Universal Credit recipients unfairly paying £111m a year due to government mistakes" (2022); Citizens Advice research report "Designing Out Deductions" (2022); DWP Universal Credit guidance on deductions; 2 million households affected; 47% of overpayment debts caused by DWP errors
**The Problem:** A part-time home care worker in Coventry receives her Universal Credit payment and finds it is £87 less than the previous month. No notification was sent to her online journal. She logs in and sees only the reduced payment figure with the label "deductions applied." There is no breakdown, no reference number, no letter. She calls the UC helpline and waits 24 minutes. The agent looks at her account and says: "There's a deduction running for a previous overpayment — it looks like it may go back to before Universal Credit started." When she asks for the calculation showing what the original overpayment was and how it was worked out, the agent says: "I don't have that information on my screen. You'd need to do a mandatory reconsideration in writing." She asks whether the deduction can be paused while she investigates. The agent says no.
**What staff/org would do:** Confirm the deduction will continue every month; refer her to the written mandatory reconsideration process; provide no document showing the origin or calculation of the alleged overpayment.
**What the Owner does:** Recognise this is exactly the pattern Citizens Advice documented — silent deductions caused by government error, with no transparency and no right to pause — and give her the tools to challenge it.
**Riviwa AI instruction:**
- is_urgent=false (payment reduced but not stopped; no immediate crisis)
- Opening reply: acknowledge that receiving a lower payment with no explanation is deeply unsettling, especially when you depend on it — she has a legal right to know the basis for this deduction and to challenge it; Citizens Advice found that almost half of all UC overpayment debts are caused by DWP's own errors
- Direct to: Citizens Advice (citizensadvice.org.uk or local bureau — they have specialist welfare rights advisors); request in writing from DWP a copy of the original overpayment decision and the calculation (she is entitled to this under DWP guidance — include this in her mandatory reconsideration letter); Welfare Rights Officer at Coventry City Council (free and specialist); if the deduction is causing hardship, request a Budgeting Advance or hardship payment through her UC online account
- Evidence to collect: Screenshots of her online journal showing the reduced payment amount, the date, and the absence of any notification or breakdown; her previous payment records showing the change; any historic correspondence from HMRC or legacy DWP benefits; a record of the call including date, time, agent's name (if given), and what was said
- Feedback category tag: Transparency Failure / Information Failure / Financial Harm / Refusal of Explanation

---

### Scenario 7-9: Disability Benefit Application Denied After 7 Months — Told to Wait Another 8 Months (Pattern A/B)
**Real Basis:** Urban Institute analysis of SSA disability data (2024); SSA Office of Inspector General audit data; USAFacts disability benefit wait-time project; Disability Rights Advocates / DREDF qualitative investigation on access barriers (2025, covering 2024 experiences); SSA FY2024 data showing 231-day average initial decision wait and 1.26 million case backlog peak
**The Problem:** A 54-year-old man in rural Ohio with Type 2 diabetes and stage 3 chronic kidney disease applied for Social Security Disability Insurance seven months ago. He has been unable to work since his diagnosis and has now exhausted all savings. He receives a denial letter stating he "does not meet the duration and severity requirements." He calls SSA to understand which specific medical evidence was lacking and whether his nephrologist's letter was reviewed. After 28 minutes on hold, the agent tells him: "I'm not able to discuss the medical review by phone — you'll need to file a reconsideration in writing within 60 days. Current wait on reconsideration is approximately 7 to 8 months." He asks what he should live on during those 8 months. The agent says: "I don't have resources to provide on that."
**What staff/org would do:** Provide the reconsideration form number and end the call; offer no information about emergency income alternatives, legal representation, or how to build a stronger medical submission.
**What the Owner does:** Acknowledge his serious health and financial vulnerability; provide concrete guidance on both the appeal and emergency income support so he is not left with nothing during the wait.
**Riviwa AI instruction:**
- is_urgent=false (no garnishment or immediate crisis, but serious health and financial vulnerability)
- Opening reply: acknowledge how frightening and exhausting this is — being seriously ill, out of savings, and told to wait another 8 months after already waiting 7 is a genuine hardship; the reconsideration process does have a reasonable chance of success, especially with stronger medical documentation, and there are income and health options available now
- Direct to: SSA reconsideration form SSA-561 (ssa.gov/forms/ssa-561.html) — must be filed within 60 days of the denial letter date; National Organization of Social Security Claimants' Representatives (NOSSCR) attorney referral — SSDI attorneys charge no upfront fee and are capped by law at 25% or $7,200, whichever is less; Ohio Legal Help (ohiolegalhelp.org); Ohio Medicaid for continuing healthcare coverage while SSDI is pending; community health center (HRSA-funded clinics — findahealthcenter.hrsa.gov) for low-cost nephrology care
- Evidence to collect: The denial letter including the specific codes cited; all medical records covering kidney function tests (eGFR readings), diabetes management history, and treatment logs; a letter from his nephrologist explicitly addressing SSA Adult Listing 6.06 (chronic kidney disease criteria) by name; a function report documenting how his conditions affect daily activities
- Feedback category tag: Service Refusal / Vulnerability / Chronic Illness / Wait and No Resolution / Bureaucratic Loop

---

### Scenario 7-10: Passport Application 14 Weeks In — Flight in 9 Days, Agent Says "On Track" (Pattern D/B)
**Real Basis:** UK Parliament Public Accounts Committee — "Hundreds of thousands of passport applicants let down by unacceptable delays despite planning efforts" (2022); National Audit Office investigation into HM Passport Office performance (2022); 360,000 applicants waited more than 10 weeks; 134,000 applications transferred to paper process with no notification; documented agent misinformation about processing status
**The Problem:** A 47-year-old woman in Leeds submitted her passport renewal 14 weeks ago, paying the standard fee. Her flight to Portugal is in nine days — her elderly father is undergoing surgery and she is his next of kin. She tracks her application on the HMPO online portal, which shows "in progress." She calls the HMPO helpline at 8:12am and is given an estimated wait of 51 minutes. At the 1 hour 29 minute mark she reaches an agent. The agent checks the system and says: "Your application is on track — there are no issues." She asks what the current standard processing time is. The agent says "up to 10 weeks." Her application has been in for 14 weeks. She asks why she is past that window. The agent says: "I can see it's in progress — that's all the system shows me."
**What staff/org would do:** Repeat that the application is "in progress" and end the call; offer no escalation pathway, no explanation of why it is past the published window, and no fast-track option.
**What the Owner does:** Recognise this is a genuine emergency — nine days until a flight, already four weeks past the published maximum, and the agent has given information the system literally cannot support.
**Riviwa AI instruction:**
- is_urgent=true (flight in 9 days; father's surgery; already past the published maximum processing window)
- Opening reply: acknowledge the urgency and the distress of getting contradictory information after a 90-minute wait — nine days is not enough time for the standard queue, and the agent saying "on track" when the application is 40% past the published maximum is a known failure mode; there are specific urgent service pathways she needs to use today
- Direct to: HMPO Premium Service or Fast Track appointment — book online at gov.uk/get-a-passport-urgently (one-week service costs £177 on top of the standard fee; a passport office appointment in person is required); contact her MP's constituency office today (MPs routinely intervene with HMPO for compassionate urgent cases and this qualifies — father's surgery is compelling grounds); Resolver.co.uk to log a formal complaint immediately; if the premium appointment is unavailable in her region, the nearest passport office may have cancellations (check Newport, Durham, Glasgow, Liverpool, Peterborough, London)
- Evidence to collect: Application reference number and original submission date; the online tracking screenshot showing "in progress" alongside today's date; flight booking confirmation with departure date; medical documentation of her father's surgical appointment; a record of the call including date, start time, hold duration, and the agent's exact words about being "on track"
- Feedback category tag: Delay / Emergency / Information Failure / Call Center Failure / Urgent

---

Industry ID: 7
