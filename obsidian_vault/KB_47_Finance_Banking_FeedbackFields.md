---
tags: [industry-kb, field-standards, feedback-fields, finance, banking]
---
# Finance / Banking — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: benki, bank, akaunti, account, NMB, CRDB, NBC, Stanbic, Exim Bank, Azania Bank, BOT, Benki Kuu, mkopo, loan, overdraft, faida, interest rate, riba, deposit, amana, withdrawal, kutoa pesa, transfer, kuhamisha pesa, ATM, SWIFT, wire transfer, standing order, direct debit, debit card, credit card, kadi ya benki, PIN, OTP, cheque, hundi, FOREX, foreign exchange, foreign currency, sarafu ya kigeni, loan repayment, malipo ya mkopo, collateral, dhamana, mortgage, rekodi ya mkopo, CRB, credit reference bureau, microfinance, SACCOS, VICOBA, mobile banking, internet banking, USSD banking, account freeze, kufungia akaunti, fraud, udanganyifu, unauthorized transaction, malipo yasiyoidhinishwa, KYC, know your customer, AML, account opening, kufungua akaunti, bank statement, taarifa ya benki

## Why Industry-Specific Fields Matter

Banking complaints span unauthorized transactions (requiring account number, transaction reference, date, amount), loan disputes (requiring loan agreement number, installment schedule, principal outstanding), and KYC/account freeze issues (requiring ID type and national ID number) — each needing different investigation teams and regulatory escalation paths under the Bank of Tanzania (BOT) and Tanzania Financial Intelligence Unit (FIU). Without banking-specific fields, the AI cannot generate a BOT Consumer Protection complaint or route to the correct bank department.

## Source Standards

- Bank of Tanzania Act, Cap. 197 — BOT regulatory authority and consumer protection mandate
- Banking and Financial Institutions Act, Cap. 342 — licensed institution obligations
- BOT Consumer Protection Framework for Banking Services 2019
- BOT Complaints Management Guidelines for Banks 2020
- Tanzania Credit Reference Bureau (TCREBU) Regulations 2012
- Financial Intelligence Unit (FIU) Act, Cap. 423 — suspicious transaction reporting
- Electronic and Postal Communications (Financial Services) Regulations 2020
- ISO 10002:2018 — complaints handling guidelines
- PCI DSS v4.0 — Payment Card Industry Data Security Standard (card fraud reference)
- FATF Recommendations — AML/CFT standards (reference for transaction monitoring)

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | BOT complaint form requires full name; enables bank account lookup |
| complainant_phone | Nambari ya simu | Yes | For complaint status updates and identity verification |
| complainant_email | Barua pepe | Recommended | BOT complaint portal uses email; written acknowledgement |
| bank_name | Jina la benki | Yes | Identifies regulated entity; determines BOT supervision category |
| account_number | Nambari ya akaunti | Yes | Primary banking identifier; required to retrieve transaction history |
| account_type | Aina ya akaunti | Yes | Current / Savings / Loan / Fixed Deposit / Business — determines applicable rules |
| branch_name | Tawi la benki | Recommended | For branch-level investigation and in-person escalation |
| issue_type | Aina ya tatizo | Yes | BOT complaint taxonomy drives routing and SLA |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018 clause 8.2; BOT guidelines require incident narrative |
| date_of_incident | Tarehe ya tukio | Yes | BOT requires date for investigation; fraud cases have time-critical reversal windows |
| amount_affected_tzs | Kiasi kilichoathirika (TZS) | Yes | Required for financial loss quantification and remedy calculation |
| transaction_reference | Nambari ya marejeleo ya muamala | Conditional | Critical for transaction trace; required for all fund transfer or ATM disputes |
| national_id_type | Aina ya kitambulisho | Yes | NIDA / Passport / Driving Licence — for identity verification before account disclosure |
| national_id_number | Nambari ya kitambulisho | Yes | KYC verification; BOT consumer protection requires complainant identity confirmation |
| desired_outcome | Matokeo unayotaka | Yes | ISO 10002:2018 clause 8.3; shapes resolution track |
| previous_complaint_to_bank | Je, umeshalalamika benki moja kwa moja? | Yes | BOT requires customers to first complain to bank; enables determination of escalation eligibility |
| bank_complaint_reference | Nambari ya rufaa ya benki (kama ipo) | Conditional | BOT escalation requires bank complaint reference |

### Conditional Fields (collect based on issue type)

**If issue_type = Unauthorized Transaction / Fraud:**
Also collect:
- `transaction_date_time` — Tarehe na saa ya muamala: Fraud reversal windows are time-critical (24–48 hours)
- `transaction_channel` — Njia ya muamala: ATM / Mobile Banking / Online Banking / Branch / POS — determines investigation path
- `card_number_last_4` — Tarakimu 4 za mwisho za kadi: PCI DSS requires partial card number only; enables card block
- `card_status` — Hali ya kadi: Inatumiwa / Imepotezwa / Iliwekwa wapi — for card fraud classification
- `police_report_number` — Nambari ya ripoti ya polisi: Required for amounts above BOT threshold; FIU reporting prerequisite

**If issue_type = Loan Dispute:**
Also collect:
- `loan_account_number` — Nambari ya akaunti ya mkopo
- `loan_disbursement_date` — Tarehe ya kupokea mkopo
- `loan_amount_original_tzs` — Kiasi cha awali cha mkopo (TZS)
- `outstanding_balance_tzs` — Deni linalobaki (TZS)
- `disputed_charge_type` — Aina ya malipo yanayobishaniwa: Interest / Penalty / Insurance / Processing fee

**If issue_type = CRB / Credit Reference Bureau:**
Also collect:
- `crb_bureau_name` — Jina la CRB: TCREBU / CRB Africa / Creditinfo — determines regulatory jurisdiction
- `negative_listing_date` — Tarehe ya kuorodheshwa vibaya
- `loan_already_paid_off` — Je, mkopo umelipwa? Yes / No
- `crb_clearance_certificate_obtained` — Je, cheti cha usafi wa CRB kimepatikana?: For verification

**If issue_type = Account Freeze / Blocked Account:**
Also collect:
- `reason_given_for_freeze` — Sababu iliyoelezwa na benki: AML / KYC / Court order / Suspected fraud
- `documents_requested_by_bank` — Nyaraka zilizoombwa na benki: Enables complainant to provide required documents

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| BK-01 | unauthorized_transaction | Transaction not initiated by account holder |
| BK-02 | atm_fraud | ATM skimming, card cloning, or ATM malfunction |
| BK-03 | online_banking_fraud | Internet or mobile banking unauthorized access |
| BK-04 | loan_interest_dispute | Wrong interest rate applied, unauthorized charges on loan |
| BK-05 | loan_repayment_dispute | Payment not credited, wrong outstanding balance |
| BK-06 | account_freeze | Account blocked without sufficient notice or reason |
| BK-07 | wrong_transfer | Money sent to wrong account; transfer not received |
| BK-08 | crb_listing | Incorrect or unjust negative CRB listing |
| BK-09 | fees_dispute | Unauthorized or undisclosed bank charges |
| BK-10 | account_opening_refusal | KYC refusal, discriminatory or unjust rejection |
| BK-11 | forex_dispute | Wrong exchange rate applied; unauthorized forex transaction |
| BK-12 | cheque_dishonour | Cheque bounced incorrectly or without sufficient notice |
| BK-13 | delayed_service | Unreasonable delays in account opening, loan processing |
| BK-14 | staff_misconduct | Bribery, fraud, or misconduct by bank employee |
| BK-15 | privacy_breach | Customer data disclosed without consent |
| BK-16 | interest_rate_change | Rate changed without required notice period |
| BK-17 | mobile_money_integration | Error in mobile money to bank transfer |

### Resolution Standards for This Industry

- **Bank level (Tanzania):** BOT Consumer Protection Framework requires acknowledgement within 5 business days and final resolution within 30 business days. Fraud cases must be responded to within 48 hours.
- **BOT escalation:** If bank fails to resolve within 30 days or response is unsatisfactory, complainant may escalate to BOT Consumer Protection Department.
- **BOT resolution timeline:** BOT aims to resolve escalated complaints within 45 business days.
- **Fraud reversal:** Most banks have a 24–48 hour window for unauthorized transaction reversal; critical to report immediately.
- **CRB disputes:** TCREBU must investigate and respond to disputes within 30 days; incorrect listings must be corrected within 5 business days of confirmation.
- **Required for BOT escalation:** Bank name, account number, nature of complaint, bank's response (or evidence of non-response), amount in dispute.

### Escalation Triggers

- `issue_type = unauthorized_transaction` AND `amount_affected_tzs > 1,000,000` — Priority fraud alert; immediate bank fraud team notification; advise card block and account freeze
- `issue_type = online_banking_fraud` AND account accessed — Advise immediate password change; escalate to bank cybersecurity team; potential FIU report
- `issue_type = staff_misconduct` AND involves bank employee fraud — Escalate to BOT Supervision Department; potential FIU suspicious transaction report
- `previous_complaint_to_bank = Yes` AND `date > 30 business days ago` — Eligible for BOT Consumer Protection escalation
- `issue_type = crb_listing` AND `loan_already_paid_off = Yes` — Urgent; incorrect CRB listing affects creditworthiness; escalate to TCREBU within 7 days
- `issue_type = account_freeze` AND customer reports inability to access funds for basic needs — Humanitarian urgency; escalate to BOT consumer protection

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous feedback accepted |
| bank_name | Jina la benki | Recommended | For targeted routing |
| service_type | Aina ya huduma | Yes | Determines improvement team |
| suggestion_category | Kategoria ya mapendekezo | Yes | Routes to product/operations/tech team |
| suggestion_detail | Maelezo ya mapendekezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| BKS-01 | digital_banking | Kuboresha benki ya kidijitali / programu |
| BKS-02 | loan_products | Bidhaa mpya za mikopo |
| BKS-03 | fee_reduction | Kupunguza ada za benki |
| BKS-04 | branch_service | Kuboresha huduma za tawi |
| BKS-05 | atm_availability | Upatikanaji zaidi wa ATM |
| BKS-06 | customer_service | Kuboresha huduma kwa wateja |
| BKS-07 | accessibility | Benki kwa walemavu na wazee |
| BKS-08 | sme_products | Bidhaa za benki kwa biashara ndogo |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina la mwulizaji | Recommended | Identity verification before account disclosure |
| account_number | Nambari ya akaunti | Conditional | Required for account-specific queries |
| query_type | Aina ya swali | Yes | Routes inquiry |
| urgency | Haraka | Yes | Standard / Dharura |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| balance_inquiry | Salio la akaunti | account_number |
| loan_eligibility | Ninastahili mkopo? | income_details, employment_status |
| interest_rate | Riba ya mkopo / amana | account_type, loan_type |
| account_statement | Taarifa ya benki | account_number, period |
| forex_rates | Bei za sarafu za kigeni | currency_pair |
| card_block | Kuzuia kadi iliyopotea | card_number_last_4 |
| crb_status | Hali yangu ya CRB | national_id_number |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| staff_name | Jina la mfanyakazi | Recommended | Staff recognition programs |
| branch_or_channel | Tawi / Njia | Yes | Routes to manager |
| specific_aspect_praised | Kipengele kilichotukuka | Yes | Usaidizi wa haraka / Uaminifu / Ujuzi wa bidhaa / Utatuzi wa tatizo |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | BOT Consumer Protection uses CSAT in annual reports |

---

## AI Conversation Guidance for This Industry

- **Never ask for full account number in a chat/SMS channel.** BOT security guidelines require that full account numbers not be transmitted over unsecured channels. Ask "Nambari yako ya akaunti — toa tarakimu 4 za mwisho tu kwa usalama" for identification.
- **For fraud complaints, prioritize speed over completeness.** Say "Kwanza kabla ya kuendelea — kama kadi yako iko nawe, wasiliana na benki mara moja kupiga simu ya kuzuia kadi (card block). Nambari ya dharura ya benki ni...". Collect the fraud details after advising this action.
- **Distinguish between unauthorized transaction and wrong transfer.** An unauthorized transaction is fraud (account compromised); a wrong transfer is a user error. The resolution path and urgency differ significantly.
- **Do not ask for PIN or full card number.** If a user volunteers this information, advise them to keep it private and never share it, even with bank staff.
- **For loan disputes, ask for the loan account number specifically** — it is often different from the savings/current account number and routes to a different team.
- **Validate CRB listing complaints carefully.** Confirm whether the loan was actually paid off and whether a clearance certificate was issued, as this determines whether the dispute is with the bank or TCREBU directly.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Bank name | "Benki gani inayohusika — NMB, CRDB, NBC, au nyingine?" |
| Account number (partial) | "Kwa usalama, toa tarakimu 4 za mwisho za nambari yako ya akaunti" |
| Transaction reference | "Muamala huu una nambari ya marejeleo — inaweza kuonekana kwenye ujumbe wa benki (SMS au email)" |
| Date of incident | "Muamala huu ulifanyika lini hasa — tarehe na saa?" |
| Amount | "Kiasi kilichoathirika ni kiasi gani (TZS)?" |
| Card status | "Kadi yako ya benki — bado uko nayo, au imepotea / ilikuibiwa?" |
| Previous complaint | "Je, umeshalalamika benki moja kwa moja kuhusu tatizo hili? Kama ndiyo, una nambari ya rufaa yao?" |
| Desired outcome | "Unataka nini kutokea — kurudishiwa pesa, kurekebisha rekodi, au kitu kingine?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | unauthorized_transaction AND amount > 0 | Immediate: advise card block / account freeze; create priority fraud ticket; 24-hour response window |
| issue_type | online_banking_fraud | Advise immediate password change and logout all devices; escalate to bank cybersecurity team |
| issue_type | staff_misconduct AND involves bribery or internal fraud | Escalate to BOT Banking Supervision; FIU suspicious transaction report may be required |
| previous_complaint_to_bank | Yes AND unresolved for > 30 business days | Eligible for BOT Consumer Protection escalation; provide BOT contact (+255 22 223 3328 / bot.go.tz) |
| issue_type | crb_listing AND loan_already_paid_off = Yes | Urgent CRB dispute; file with TCREBU within 7 days; advise complainant on TCREBU process |
| amount_affected_tzs | > 5,000,000 | Senior officer review required; BOT threshold for expedited investigation |
| issue_type | forex_dispute | Route to bank treasury/forex desk; check BOT daily exchange rate bulletin for benchmark |
| issue_type | account_freeze AND reason = AML/KYC | Advise customer to provide required KYC documents to the branch; assist with document checklist |

---

*Sources: BOT Act Cap. 197, Banking and Financial Institutions Act Cap. 342, BOT Consumer Protection Framework 2019, BOT Complaints Management Guidelines 2020, Tanzania CRB Regulations 2012, FIU Act Cap. 423, ISO 10002:2018, PCI DSS v4.0*
