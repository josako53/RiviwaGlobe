---
tags: [industry-kb, feedback-classification, field-collection]
---
# Finance / Banking — Feedback Collection Fields & Standards

## Industry Identifiers

bank, commercial bank, microfinance, SACCO, mobile money, M-Pesa, Tigo Pesa, Airtel Money, HaloPesa, stock brokerage, forex bureau, investment, pension fund, NSSF, GEPF, PPF, LAPF, BOT, FSDT, agent banking, loan app, mobile banking, USSD banking, KYC, account opening, ATM, credit card, savings account, fixed deposit, current account, wire transfer, SWIFT, TISS, RTGS, mobile wallet, overdraft, interest rate, collateral, guarantor, credit score, CRB, currency exchange, DSE, Dar es Salaam Stock Exchange, unit trust, MFI, account number, account balance, loan repayment, loan disbursement, debit card, branch, teller, relationship manager, loan officer, transaction, statement, erroneous debit, unauthorized transaction, card blocked, account frozen, float, agent banking operator, CRDB, NMB, NBC, Stanbic, Standard Chartered, Absa, Azania Bank

## Why Industry-Specific Fields Matter

Generic feedback fields cannot capture the transaction references, account types, financial loss amounts, or fraud indicators required by the Bank of Tanzania's Financial Consumer Protection Regulations 2019 (GN No. 884) and Guidelines 2025 — without which complaints cannot be routed to the correct resolution team, reconciled against core banking records, or escalated to BoT within the mandatory 14-day window. A grievance involving an unauthorized ATM debit requires entirely different downstream data from a loan interest dispute or a SWIFT transfer failure.

## Source Standards

- Bank of Tanzania (Financial Consumer Protection) Regulations 2019, GN No. 884 — First Schedule complaint form, Part IX
- Bank of Tanzania Guidelines for Handling Financial Consumer Complaints 2025 (5-year records retention, monthly reporting)
- Bank of Tanzania (Financial Consumer Protection) (Amendment) Regulations 2025
- ISO 10002:2018 — Quality Management, Guidelines for Complaints Handling (unique reference, remedy sought, date of occurrence)
- FCA Handbook DISP 1.9 & 1.10 — Complaints Record Rule and Complaints Reporting Rules (product categories, complaint cause, resolution timeline, upheld/not-upheld, redress)
- FCA DISP Annex 1 — 50 product categories across 5 product groups
- Basel Committee BCBS d383 — Guidance on Core Principles for Financial Inclusion (complaint data as supervisory input)
- PSD2 / EBA-GL-2017-13 — EU Payment Services Directive, EBA Guidelines on Complaints for Alleged PSD2 Infringements (transaction reference, channel, amount, 15-day response window)
- FFIEC BSA/AML Examination Manual — Suspicious Activity Report (SAR) obligations when fraud suspected
- CGAP — Leveraging Complaint Data for Consumer Protection (channel tracking, agent banking fields)
- CFPB (US) product–issue taxonomy (comparative reference for issue classification)
- NIDA (National Identification Authority) — KYC identity verification at complaint intake

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL banking/finance complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complaint_reference_number | Nambari ya Malalamiko | Yes (system-generated) | BoT GN 884 requires unique registration number for every complaint; ISO 10002:2018 unique identifier rule; enables tracking through BoT monthly reporting |
| complainant_full_name | Jina Kamili la Mlalamikaji | Yes | BoT First Schedule section A; ISO 10002:2018; FCA DISP record rule; links complaint to authenticated customer |
| complainant_phone | Nambari ya Simu | Yes | BoT First Schedule (A); ISO 10002:2018; required for callback and SMS updates |
| complainant_email | Barua Pepe | Recommended | FCA DISP; ISO 10002:2018; enables written communication of resolution |
| complainant_address | Anwani ya Mlalamikaji | Yes | BoT First Schedule (A); required for signed resolution declaration (Second Schedule) |
| account_type | Aina ya Akaunti | Yes | FCA DISP Annex 1 product categories; BCBS conduct risk analysis; routes complaint to correct product team |
| account_number_or_customer_id | Nambari ya Akaunti / Kitambulisho | Yes | Links complaint to core banking record; prevents third-party manipulation; BoT; ISO 10002 product identification |
| financial_institution_name | Jina la Benki / Taasisi | Yes | FCA DISP (firm identification); BoT monthly reporting by institution; BCBS supervisory analysis |
| issue_type | Aina ya Tatizo | Yes | FCA DISP Annex 1 (complaint cause — mandatory reporting field); CFPB taxonomy; enables root cause analysis and regulatory reporting |
| complaint_description | Maelezo ya Malalamiko | Yes | ISO 10002:2018; BoT First Schedule section C; FCA DISP narrative requirement |
| date_of_incident | Tarehe ya Tukio | Yes | ISO 10002:2018 (date of occurrence mandatory); PSD2/EBA-GL-2017-13; BoT timeline tracking |
| date_complaint_received | Tarehe ya Kupokea Malalamiko | Yes (system) | ISO 10002:2018; BoT (triggers 14-day resolution clock); FCA DISP (8-week rule starts here) |
| service_channel | Njia ya Huduma | Yes | PSD2/EBA-GL-2017-13 (channel mandatory); BoT digital/analogue tracking; CGAP best practice; identifies whether digital or physical channel failure |
| remedy_sought | Suluhisho Linalohitajika | Yes | ISO 10002:2018 Clause 8.3 — remedy sought must be recorded at intake; sets expectations for resolution |
| financial_loss_amount | Kiasi cha Hasara ya Fedha | Yes (if applicable) | FCA DISP (redress amount tracking); BoT Regulations reference to financial loss from erroneous debits and staff negligence; BCBS conduct risk |
| date_first_raised_with_institution | Tarehe Tatizo Liliporipotiwa Kwanza | Yes | FCA DISP timeline (3-day/8-week thresholds); BoT 14-day resolution window; establishes whether escalation to BoT is now permissible |
| supporting_documents_attached | Nyaraka za Ushahidi | Yes | ISO 10002:2018; BoT First Schedule; affects resolution speed |
| complainant_vulnerability_flag | Mlalamikaji Katika Hali Ngumu | Recommended | FCA 2026 supervisory priority (vulnerable circumstances); BoT consumer protection spirit; triggers priority handling |

### Conditional Fields (collect based on issue type)

**If issue_type = unauthorized_transaction OR suspected_fraud:**
- transaction_reference_number (Nambari ya Muamala) — PSD2/EBA-GL-2017-13 mandatory; FCA DISP; links to core banking audit trail
- transaction_amount (Kiasi cha Muamala) — PSD2/EBA-GL-2017-13; FCA DISP redress tracking
- transaction_date (Tarehe ya Muamala) — PSD2/EBA-GL-2017-13; ISO 10002:2018
- fraud_suspected (Je, Ulaghai Unahisiwa?) — FFIEC BSA/AML SAR obligation trigger; BoT fraudulent activity reference
- police_report_number (Nambari ya Ripoti ya Polisi) — BoT Regulations (police reference for fraudulent activities); FFIEC SAR guidance
- is_card_compromised (Je, Kadi Iliathiriwa?) — FFIEC; FCA DISP card fraud category
- aml_escalation_flag (Inaelekeza kwa Timu ya AML?) — FFIEC BSA/AML; internal compliance routing

**If issue_type = fund_transfer_failure OR wrong_amount:**
- transaction_reference_number (Nambari ya Muamala) — PSD2/EBA-GL-2017-13
- transfer_type (Aina ya Uhamisho: SWIFT / TISS / RTGS / Mobile Money / Agent) — FCA DISP; BoT; routing to correct correspondent team
- beneficiary_name (Jina la Mpokeaji) — PSD2; BoT
- beneficiary_bank (Benki ya Mpokeaji) — PSD2 cross-border; SWIFT routing
- transaction_amount (Kiasi cha Muamala) — PSD2; FCA DISP
- transaction_date (Tarehe ya Muamala) — PSD2; ISO 10002:2018
- exchange_rate_applied (Kiwango cha Ubadilishaji Kilichotumika) — PSD2/EBA (transparency obligation on rates before/after transaction)

**If issue_type = loan_dispute:**
- loan_account_number (Nambari ya Akaunti ya Mkopo) — links to credit file
- loan_type (Aina ya Mkopo: kibinafsi / biashara / SME / nyumba / kilimo / simu) — FCA DISP product category
- disputed_amount (Kiasi Kinachoshindaniwa) — FCA DISP redress; BoT excess charges reference
- crb_impact (Athari kwa CRB: ndiyo / hapana) — BoT (CRB listing disputes are specific BoT remedy pathway); FFIEC credit reporting
- collateral_type (Aina ya Dhamana) — BoT; relevant for collateral release disputes
- is_cro_involved (Je, Meneja wa Mikopo Amehusika?) — internal escalation routing

**If issue_type = atm_malfunction:**
- atm_id_or_location (Kitambulisho / Mahali pa ATM) — FCA DISP branch identification; BoT; enables technical team dispatch
- transaction_reference_number (Nambari ya Muamala) — FCA DISP; links to switch log
- cash_difference_amount (Tofauti ya Pesa Iliyotolewa) — BoT excess charges / erroneous debits
- card_retained (Je, Kadi Imebakiwa na ATM?) — triggers physical retrieval workflow

**If issue_type = mobile_money_agent_fraud OR agent_banking_fraud:**
- agent_name (Jina la Wakala) — BoT agent banking regulation; FCA firm identification
- agent_code_or_till_number (Nambari ya Wakala / Nambari ya Kisanduku) — BoT; CGAP agent identification
- agent_location (Mahali pa Wakala) — BoT; police referral; enables field investigation
- receipt_number (Nambari ya Risiti) — BoT (receipt is primary evidence in agent banking disputes)

**If issue_type = account_frozen_or_suspended:**
- freeze_notification_received (Je, Uliarifu Kwa Njia Rasmi?) — BoT consumer rights (notice requirement); FCA DISP (customer detriment)
- emergency_access_needed (Je, Unahitaji Fedha kwa Dharura?) — escalation trigger (life-savings/medical emergency)

**If complaint is a repeat / escalation:**
- previous_complaint_reference (Nambari ya Malalamiko ya Awali) — FCA DISP 1.3.3R root cause analysis; BoT escalation tracking
- previous_resolution_outcome (Matokeo ya Awali) — FCA DISP (determines if FSP response was final); BoT (14-day post-response window for BoT escalation)
- days_since_previous_complaint (Siku Tangu Malalamiko ya Awali) — BoT (escalation to BoT permitted after FSP final response + 14 days)

### Issue Type Classification

- `unauthorized_transaction` — Muamala usioidhinishwa / ulaghai
- `wrong_amount_debited_or_credited` — Kiasi kibaya kilichokatwa / kuongezwa
- `account_frozen_or_suspended` — Akaunti iliyozuiwa bila taarifa
- `loan_dispute` — Mgawanyiko wa mkopo (bakaa / riba / ada)
- `fee_or_charge_dispute` — Migogoro ya ada / tozo isiyotangazwa
- `card_issue` — Tatizo la kadi (kuzuiwa / kutolewa / kutofanya kazi mtandaoni)
- `mobile_banking_app_failure` — Kushindwa kwa programu ya benki ya simu
- `atm_malfunction` — Tatizo la ATM (pesa kutotolewa / kadi kubakiwa)
- `fund_transfer_failure` — Uhamisho wa fedha kushindwa au kuchelewa
- `interest_rate_dispute` — Riba iliyotumika vibaya
- `account_opening_or_closure_issue` — Tatizo la kufungua / kufunga akaunti
- `statement_or_data_error` — Kosa la taarifa / rekodi
- `agent_banking_fraud` — Ulaghai wa wakala wa benki
- `mobile_money_agent_dispute` — Mgawanyiko na wakala wa pesa za simu
- `crb_dispute` — Tatizo la CRB (orodha isiyo sahihi)
- `pension_contribution_dispute` — Michango ya NSSF/PPF/GEPF isiyowasilishwa
- `forex_bureau_dispute` — Mgawanyiko wa ubadilishaji wa sarafu
- `investment_dispute` — Mgawanyiko wa uwekezaji (DSE / amana ya muda mfupi)
- `customer_service_failure` — Kushindwa kwa huduma kwa wateja
- `other` — Nyingine (na maelezo ya bure)

### Resolution Standards for This Industry

- **BoT GN 884 / Guidelines 2025**: FSP must acknowledge immediately; resolve within 14 days (maximum — shorter windows for specific issue types per First Schedule, e.g., 6 hours for erroneous debits confirmed by system). Issue signed Complaint Resolution Declaration Form (Second Schedule). Retain records minimum 5 years. Submit monthly reports to BoT within 15 days after month-end.
- **PSD2 / EBA-GL-2017-13**: Payment service providers must respond within 15 business days (35 business days in complex cross-border cases).
- **FCA DISP**: Firm must respond within 3 business days (summary resolution) or send a final response within 8 weeks. Record retention: 3 years (5 years for collective investment schemes).
- **ISO 10002:2018**: Record must include remedy sought, investigation findings, decision, date of decision, compensation offered/paid, and closure date.
- **BoT Escalation Path**: Consumer may escalate to BoT only after FSP final response AND if still dissatisfied, must escalate within 14 days of FSP's final response. BoT requires documented financial loss or material inconvenience. No pending court proceedings.

### Escalation Triggers (field values requiring immediate action)

- `fraud_suspected = yes` AND `transaction_amount > 0` → Initiate internal SAR process; flag for AML/compliance team; BoT notification if threshold met
- `issue_type = account_frozen_or_suspended` AND `emergency_access_needed = yes` → Priority escalation to branch manager / duty officer within 1 hour
- `issue_type = agent_banking_fraud` AND `agent_uncontactable = yes` → Police referral + BoT agent banking supervision notification
- `issue_type = unauthorized_transaction` AND `card_compromised = yes` → Immediate card block instruction; fraud team notification
- `days_since_previous_complaint >= 14` AND `previous_resolution_outcome = unresolved` → Auto-generate BoT escalation package (First + Second Schedule forms)
- `pension_contribution_dispute = yes` AND `employer_not_remitting = yes` → Escalate to NSSF/PPF/GEPF compliance and labour authority
- `financial_loss_amount > 1000000` (TZS 1 million) → Senior relationship manager review required
- `is_card_compromised = yes` AND `fraud_location_different_from_customer_location = yes` → Emergency card block + fraud investigation unit
- `issue_type = fund_transfer_failure` AND `transfer_type = SWIFT` AND `days_missing > 10` → SWIFT trace request; correspondent bank investigation

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| suggestion_reference_number | Nambari ya Pendekezo | Yes (system) | ISO 10002:2018 unique identifier for all feedback types |
| submitter_name | Jina la Mtoa Pendekezo | Optional | ISO 10002:2018; allow anonymous for honest input |
| submitter_contact | Mawasiliano ya Mtoa Pendekezo | Optional | ISO 10002:2018; for follow-up if implemented |
| service_area | Eneo la Huduma | Yes | FCA DISP product group taxonomy; CFPB product categories; routes to correct product/channel team |
| specific_product_or_feature | Bidhaa / Kipengele Mahususi | Yes | FCA DISP Annex 1 product-level granularity; ISO 10002:2018 |
| suggestion_description | Maelezo ya Pendekezo | Yes | ISO 10002:2018; the substance of the improvement |
| date_submitted | Tarehe ya Kuwasilisha | Yes | ISO 10002:2018 |
| submission_channel | Njia ya Kuwasilisha | Yes | BoT multi-channel; CGAP best practice |

### Industry-Specific Improvement Categories

- `digital_banking_mobile_app` — Programu ya simu ya benki / benki mtandaoni
- `mobile_money_platform` — Mfumo wa pesa za simu (M-Pesa / Airtel Money / Tigo Pesa / HaloPesa)
- `atm_network` — Mtandao wa ATM
- `loan_products_and_process` — Bidhaa za mkopo na mchakato
- `credit_card_services` — Huduma za kadi ya mkopo
- `branch_services_and_hours` — Huduma za tawi na masaa ya kufungua
- `agent_banking_network` — Mtandao wa wakala wa benki
- `customer_service_and_communication` — Huduma kwa wateja na mawasiliano
- `fee_and_tariff_transparency` — Uwazi wa ada na tozo
- `account_opening_and_onboarding` — Mchakato wa kufungua akaunti
- `forex_and_international_transfers` — Ubadilishaji wa sarafu na uhamisho wa kimataifa
- `investment_and_savings_products` — Bidhaa za uwekezaji na akiba
- `pension_services` — Huduma za mstaafu / pensheni

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| inquiry_reference_number | Nambari ya Swali | Yes (system) | ISO 10002:2018 |
| inquirer_name | Jina la Muulizaji | Yes | KYC identity verification; BoT; links to customer record for accurate answer |
| account_identifier | Kitambulisho cha Akaunti | Yes | KYC/identity; BoT; PSD2 (transaction-specific inquiries require account link) |
| account_type | Aina ya Akaunti | Yes | FCA DISP product categories; routes to correct information source |
| inquiry_type | Aina ya Swali | Yes | FCA DISP (distinguishes inquiry from complaint for reporting purposes); CFPB categorisation |
| reference_number | Nambari ya Kumbukumbu | Conditional | PSD2/EBA-GL-2017-13 (transaction ref for payment inquiries); NAIC (claim/loan number) |
| inquiry_description | Maelezo ya Swali | Yes | ISO 10002:2018 |
| date_of_inquiry | Tarehe ya Swali | Yes | ISO 10002:2018 |
| submission_channel | Njia ya Kuwasilisha | Yes | BoT; CGAP |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Additional Required Fields |
|-------------|---------------------------|
| `account_balance` | account_number, account_type |
| `account_statement` | account_number, statement_period_start, statement_period_end |
| `loan_status_and_balance` | loan_account_number, loan_type |
| `transfer_status` | transaction_reference_number, transaction_date, transfer_type |
| `interest_rate_information` | product_type (savings / loan / fixed deposit) |
| `card_status` | card_last_four_digits, card_type |
| `fee_schedule` | product_or_service_type |
| `atm_location` | preferred_area_or_region |
| `account_opening_requirements` | account_type_of_interest, business_or_personal |
| `crb_status_inquiry` | national_id_number (for identity-verified response) |
| `forex_rate` | currency_pair, transaction_direction (buy/sell) |
| `mobile_money_limit` | mobile_money_operator, account_tier |
| `pension_contribution_status` | employer_name, employee_id, nssf_member_number |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| applause_reference_number | Nambari ya Sifa | Yes (system) | ISO 10002:2018 |
| submitter_name | Jina la Mtoa Sifa | Optional | ISO 10002:2018; allow anonymous |
| submitter_contact | Mawasiliano ya Mtoa Sifa | Optional | For verification and internal recognition programs |
| staff_member_commended | Jina la Mtumishi Anayesifiwa | Yes | Standard commendation capture; enables staff recognition and performance tracking |
| branch_or_channel | Tawi / Njia ya Huduma | Yes | FCA DISP (firm and branch identification); links commendation to specific location |
| financial_institution_name | Jina la Benki / Taasisi | Yes | FCA DISP; BoT institutional tracking |
| service_or_transaction_praised | Huduma / Muamala Ulioheshimishwa | Yes | ISO 10002:2018 (product/service identification); FCA Consumer Duty (documenting good outcomes) |
| specific_positive_outcome | Matokeo Mazuri Yaliyoelezwa | Yes | ISO 10002:2018; FCA Consumer Duty evidence requirement |
| date_of_experience | Tarehe ya Uzoefu | Yes | ISO 10002:2018 |
| date_submitted | Tarehe ya Kuwasilisha | Yes | ISO 10002:2018 |

---

## AI Conversation Guidance for This Industry

- **Start with account context, not the complaint detail**: Ask "Unatumia huduma ya nini hasa — akaunti ya benki, pesa za simu, mkopo, au bima?" before going deeper. The account type determines which fields are relevant and which sub-taxonomy to follow. Never start by asking for the account number — establish trust first.
- **Collect transaction reference before narrative on financial loss complaints**: When a customer mentions money missing, a failed transfer, or an unauthorized debit, the single most important field is the transaction reference number. Ask "Je, una nambari ya muamala au SMS iliyotumwa baada ya muamala huo?" early — without it, the complaint cannot be reconciled against banking records.
- **Flag fraud sensitively**: If a customer describes an unauthorized transaction or says someone else used their account, do not immediately say "ulaghai" (fraud) — ask "Je, wewe mwenyewe ulifanya muamala huo?" and "Je, umepata SMS ya muamala ambao hukutarajia?" to establish the facts before labeling. Then ask about police reporting.
- **For loan complaints, always ask about CRB impact**: Many loan complainants do not realize their grievance has damaged their credit record. After capturing the loan details, ask "Je, tatizo hili limeathiri akaunti yako ya CRB?" — this changes the urgency and the remedy pathway.
- **Do NOT ask for PIN, full card number, or password under any circumstances**: The AI must never request these fields. If a customer offers them, politely redirect: "Usishiriki PIN yako au nambari yote ya kadi — hizi zinatosha: nne za mwisho za kadi na tarehe ya muamala."
- **Distinguish mobile money from banking early**: M-Pesa, Airtel Money, Tigo Pesa, and HaloPesa complaints may look like telecom complaints. The signal is money movement. Ask "Je, tatizo liko kwenye pesa zinazobadilika au kwenye simu / data?" to route correctly to this KB.

## Swahili Key Phrases for Field Collection

- **Account type**: "Unatumia aina gani ya akaunti — akaunti ya akiba, akaunti ya sasa, mkopo, au pesa za simu?"
- **Transaction reference**: "Je, una nambari ya muamala au nambari ya rejista? Kawaida inaonekana kwenye SMS ya benki."
- **Date of incident**: "Tukio hili lilitokea lini hasa — tarehe na wakati unaoweza kukumbuka?"
- **Financial loss amount**: "Ni kiasi gani cha pesa ambacho unahisi unapotezwa — toa nambari halisi ikiwa unaweza."
- **Fraud flag**: "Je, unaamini mtu mwingine alitumia akaunti yako bila ruhusa yako?"
- **Police report**: "Je, umewasiliana na polisi kuhusu hali hii? Una nambari ya OB (Occurrence Book)?"
- **Remedy sought**: "Ungependa tatizo hili lisuluhishwe vipi hasa — unataka fedha zako zirudishwe, au unahitaji kitu kingine?"
- **Branch/channel**: "Tatizo hili lilitokea wapi hasa — tawi, ATM, programu ya simu, au kupitia wakala?"
- **Agent details**: "Jina la wakala na mahali alipokuwepo — au nambari ya kisanduku chake ikiwa unakumbuka?"
- **Previous complaint**: "Je, umeshawahi kuripoti tatizo hili kwa benki moja kwa moja? Kama ndiyo, ulipata jibu gani?"

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|-------------------|
| `fraud_suspected` | yes | Flag for internal AML/fraud team; advise customer to change PIN immediately; request police OB if not done |
| `issue_type` | unauthorized_transaction | Request transaction reference, date, amount; trigger card block workflow if card-based |
| `emergency_access_needed` | yes (frozen account) | Escalate to duty branch manager within 1 hour; BoT complaint if unresolved in 6 hours |
| `days_since_previous_complaint` | ≥14 with unresolved status | Auto-generate BoT escalation packet; inform customer of right to escalate |
| `crb_impact` | yes | Flag for credit compliance team; CRB dispute letter template activation |
| `agent_uncontactable` | yes | Advise police report; flag for agent banking supervision team and BoT |
| `transfer_type` | SWIFT AND days_missing ≥ 10 | Escalate to correspondent banking team for SWIFT trace (MT199/MT299) |
| `pension_contribution_dispute` AND `employer_not_remitting` | yes | Escalate to NSSF/PPF/GEPF compliance; advise customer on Ministry of Labour referral |
| `financial_loss_amount` | ≥ TZS 1,000,000 | Senior manager review; priority resolution track; BoT report threshold check |
| `complainant_vulnerability_flag` | yes | Assign dedicated case handler; priority queue; follow FCA/BoT vulnerable person guidelines |
| `receipt_number` present (agent banking dispute) | any | Escalate to agent banking operations team with receipt scan for reconciliation |
| `previous_resolution_outcome` | upheld_partially AND dissatisfied | Offer BoT escalation information and Second Schedule Declaration form guidance |

---

## Complaint / Grievance Signals — Finance / Banking (Examples)

### Account Management & Access
- I have been locked out of my mobile banking app and the reset process has not worked for three days
- My ATM card was blocked without any notification and I cannot access my money
- I deposited cash at the branch and it still has not reflected in my account after 48 hours
- My salary was credited to the wrong account due to a bank error and I cannot access it
- The bank deducted a monthly maintenance fee from my account but the fee amount changed without notice
- My account was frozen by the bank and no one has explained why or given me a timeline for resolution
- I received an SMS saying a transaction was made on my account but I did not authorize it — possible fraud

### Mobile Money Issues (M-Pesa / Tigo Pesa / Airtel Money / HaloPesa)
- I sent TZS 200,000 to the wrong number and the recipient is not cooperating — the platform should have a recall mechanism
- My M-Pesa withdrawal at the agent was unsuccessful but the money was deducted from my wallet
- The Airtel Money agent gave me less cash than the amount I withdrew — short-changing is happening regularly
- HaloPesa reversed a transaction I completed days ago without explanation — my money is now missing
- The mobile money USSD (*150*00#) has not been working for two days — I cannot access my funds
- I was charged twice for a single M-Pesa payment to a business
- A person posing as a mobile money agent took my money and disappeared — I was not in a licensed booth

### Loans & Credit
- I repaid my loan in full but the CRB listing has not been cleared after four months
- The loan app deducted repayments from my mobile money account before the due date without my consent
- The interest rate on my loan is higher than what was stated in the loan agreement I signed
- The mobile loan app approved me for TZS 50,000 but charged me an upfront processing fee of TZS 10,000 — this was not disclosed
- After loan repayment, my collateral has not been released for three months despite multiple follow-ups

### ATM & Card Services
- The ATM dispensed less money than it deducted from my account — the receipt shows the full amount was debited
- The ATM swallowed my card and the bank says they cannot retrieve it for five days
- My debit card was compromised — someone used it for a transaction in Nairobi while I was in Dar es Salaam

### Transfers & Payments
- I made an international transfer (SWIFT) five working days ago and the beneficiary still has not received the funds
- I was charged a transfer fee that was higher than the published tariff on your website
- The bank processed a duplicate payment for a single instruction — two payments went out instead of one

### Agent Banking
- The bank agent collected my deposit but it was never reflected in my account — the agent is uncontactable now
- The agent's system was "offline" and they wrote a manual receipt — the amount still has not posted after one week
- The bank agent charged me a fee higher than the official agent banking tariff

---

## Suggestion / Advice Signals — Finance / Banking (Examples)

- Please introduce a transaction reversal feature on mobile money — one wrong digit ruins everything
- The mobile banking app should support face recognition or fingerprint login — PIN entry is slow
- Please make your USSD banking service work without an internet connection — it times out frequently
- A spending analytics feature in the app showing monthly category breakdown would be very useful
- Please design loan repayment schedules aligned to income cycles — weekly earners cannot make monthly repayments
- A credit score transparency tool showing me my BoT CRB score and how to improve it would empower customers
- Please extend branch operating hours to include Saturday afternoon — working people cannot visit during the week
- A virtual queue system (take a number, wait anywhere) would reduce the frustration of long queues at branches
- More ATMs in peri-urban areas would reduce the burden on agents who frequently run out of float

---

## Inquiry / Question Signals — Finance / Banking (Examples)

- What documents do I need to open a current account for my small business?
- What is the current interest rate for a personal loan?
- What collateral does the bank accept for a TZS 10 million business loan?
- How do I reverse an M-Pesa transaction sent to the wrong number?
- What is the maximum amount I can send through HaloPesa in one transaction?
- How do I update my mobile money registration to my new national ID number?
- At what age am I eligible to claim my NSSF pension benefits?
- What is today's buying and selling rate for USD at your forex bureau?
- How do I buy shares listed on the Dar es Salaam Stock Exchange (DSE)?

---

## Compliment / Applause Signals — Finance / Banking (Examples)

- The mobile banking app is very easy to use and I can do everything without going to the branch — excellent design
- The loan was approved and disbursed within four days — the fastest I have ever experienced from any bank
- The customer service team called me back within one hour of my complaint — I did not expect that level of responsiveness
- Your branch staff assisted an elderly customer with her withdrawal even though she was not in the queue — very compassionate
- My NSSF retirement benefit process was clear and the officer guided me through each step patiently
- The agent banking point near my home is always stocked with float and the agent is helpful — saves me a long journey to the branch

---

## Key Entities & Roles

**Regulatory Bodies**
- BOT (Bank of Tanzania) — banking oversight, mobile money regulation, financial consumer protection
- FSDT (Financial Sector Deepening Trust) — financial inclusion
- CRB (Credit Reference Bureau Tanzania) — credit reporting
- NSSF (National Social Security Fund), PPF (Public Service Pensions Fund), GEPF, LAPF
- NHIF (National Health Insurance Fund)
- DSE (Dar es Salaam Stock Exchange), CMSA (Capital Markets and Securities Authority)
- NIDA (National Identification Authority) — KYC

**Major Banks in Tanzania**
- CRDB Bank, NMB Bank, NBC (National Bank of Commerce), Stanbic Bank, Standard Chartered, Absa Bank Tanzania, Azania Bank, Mkombozi Commercial Bank, Akiba Commercial Bank, I&M Bank Tanzania

**Mobile Money Operators**
- M-Pesa (Vodacom Tanzania), Tigo Pesa (MIC Tanzania), Airtel Money (Airtel Tanzania), HaloPesa (Halotel)

---

## Kiswahili / Swahili Equivalents

**Malalamiko (Complaints)**
- Pesa zangu hazikuonekana akaunti yangu baada ya siku mbili za kuweka benki — kuna tatizo
- Nilituma pesa kwa nambari isiyo sahihi kupitia M-Pesa — tafadhali nisaidie kuirejesha
- Wakala wa benki alichukua amana yangu lakini pesa hazikuonekana akaunti yangu hadi leo
- ATM ilipiga kadi yangu na benki inasema itachukua siku tano kuirudisha — hii si sawa
- Mkopo wangu umelipwa lakini CRB bado inanionyesha kama mdaiwa — hii inanidhuru
- Riba ya mkopo wangu imebadilika bila taarifa — bei ya awali tuliyokubaliana ilikuwa tofauti
- Mfumo wa USSD haujakuwa ukifanya kazi kwa siku mbili — siwezi kupata pesa zangu
- Mwajiri wangu anakato NSSF kila mwezi lakini michango haionekani kwenye taarifa yangu

**Mapendekezo (Suggestions)**
- Ingekuwa vizuri kama programu ya simu ya benki ingeweza kusaidia kurejesha pesa zilizotumwa kwa makosa
- Tafadhali ongeza saa za kufungua matawi — watu wanaofanya kazi siwezi kwenda wakati wa saa za ofisi
- Matumizi ya lugha ya Kiswahili katika programu ya simu itasaidia wateja wengi zaidi
- Toleo la muda mfupi la mkopo kwa wafanyabiashara wadogo wenye kipato cha wiki lingehitajika sana

**Maswali (Inquiries)**
- Ninahitaji hati gani kufungua akaunti ya biashara?
- Riba ya mkopo wa kibinafsi kwa sasa ni asilimia ngapi?
- Ninawezaje kujua kama mwajiri wangu anarejesha michango ya NSSF kwa wakati?
- Kiwango cha juu cha kutuma fedha kwa M-Pesa kwa siku moja ni kiasi gani?
- Ninawezaje kubadilisha nambari ya simu kwenye akaunti yangu ya benki?

**Sifa / Shukrani (Compliments)**
- Programu ya simu ya benki yenu ni rahisi sana kutumia — naweza kufanya kila kitu bila kwenda tawi
- Mkopo wangu uliidhinishwa na kutolewa ndani ya siku nne — haraka kuliko nilivyotarajia
- Wakala wa benki karibu na nyumbani kwangu ana fedha za kutosha daima — ananisaidia sana
- Timu ya huduma ya wateja ilipigia simu ndani ya saa moja ya malalamiko yangu — nimefurahi sana

---

## Industry-Specific Escalation Triggers

1. Customer reports unauthorized transactions — suspected account takeover or card skimming fraud
2. Mobile money agent collected customer cash and is uncontactable — suspected fraudulent agent
3. Customer's pension contributions (NSSF/PPF/GEPF) deducted by employer but never remitted over multiple years
4. Account frozen with life-saving funds (medical emergency, school fees deadline) and no emergency access provided
5. Confirmed identity theft — KYC details used to open accounts or take loans without customer knowledge
6. Forex bureau confirmed to be distributing counterfeit currency notes
7. Loan app making unauthorized deductions beyond agreed repayment amount — illegal over-collection
8. Bank teller or employee suspected of internal fraud — unauthorized access to customer accounts
9. Loan recovery agent using threats, physical intimidation, or harassment to collect debt
10. SWIFT transfer carrying business-critical funds missing for more than 10 working days with no trace
11. Multiple customers reporting the same agent operator collecting deposits never posted — pattern of agent fraud
12. Pension fund or SACCO suspected of misappropriating member savings — systemic financial misconduct

---

## Disambiguation Notes

- **Finance/Banking vs. Mobile Telecom**: Mobile money (M-Pesa, Airtel Money, Tigo Pesa, HaloPesa) complaints about transaction failures, wrong amounts, or agent conduct belong to finance/banking KB even though they operate on telecom networks. If the complaint is about voice call or data service on the same telecom network, route to telecoms KB. The discriminating signal is whether money movement is involved.
- **Finance vs. Government Services**: NSSF, GEPF, PPF, and NHIF are government-backed funds. Complaints about contribution records, benefit delays, or policy administration belong in finance/banking KB. Complaints about the government institution itself as an employer or regulator belong to government services KB.
- **Insurance vs. Healthcare**: NHIF complaints about premium deductions, coverage claims, or rejected treatment reimbursements stay in finance/banking KB. Complaints about the quality of medical treatment received at a hospital — even if NHIF-covered — belong to healthcare KB.
- **Banking vs. Real Estate**: Home mortgage products sit in finance/banking KB when the complaint is about loan terms, disbursement, or repayment. If the complaint shifts to the property itself (developer delays, title deed issues, construction defects), route to real estate KB.
- **Agent Banking vs. Agent Telecom**: An agent banking operator working under a bank's network who collects deposits belongs to finance KB. An agent working as a mobile money distributor (float dealer) also belongs to finance KB. An agent selling SIM cards or data bundles belongs to telecoms KB.
