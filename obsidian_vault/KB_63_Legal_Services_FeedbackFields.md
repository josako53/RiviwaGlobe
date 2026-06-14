---
tags: [industry-kb, field-standards, feedback-fields, legal-services]
---
# Legal Services — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: wakili, lawyer, attorney, advocate, mwanasheria, legal services, huduma za kisheria, law firm, kampuni ya sheria, legal advice, ushauri wa kisheria, court, mahakama, case, kesi, litigation, mashtaka, criminal case, kesi ya jinai, civil case, kesi ya madai, family law, sheria ya familia, land dispute, ugomvi wa ardhi, employment law, sheria ya kazi, contract, mkataba, notary, notari, conveyance, uandishi wa hati, power of attorney, hati ya idhini, affidavit, kiapo, legal aid, msaada wa kisheria, TANLAP, Tanganyika Law Society, TLS, Advocates Act, Bar, bar exam, legal fees, ada za kisheria, brief, client, mteja wa kisheria, filing, kuwasilisha mahakamani, court date, tarehe ya kesi, judgment, hukumu, appeal, rufaa, verdict, uamuzi, settlement, makubaliano nje ya mahakama, retainer, mfuko wa mteja

## Why Industry-Specific Fields Matter

Legal service complaints involve unique dimensions: client money held in trust (requiring trust account reference), missed court deadlines (requiring case file number and court date), negligent advice (requiring outcome harm), and professional misconduct (requiring TLS complaint file). Tanzania Advocates Act requires complaints against advocates to go through the Tanganyika Law Society before disciplinary proceedings. Without legal-specific fields, the AI cannot assess whether a complaint is urgent (missed court deadline), a trust account fraud (criminal), or a service quality issue (TLS disciplinary).

## Source Standards

- Tanzania Advocates Act, Cap. 341 — advocate licensing and conduct
- Tanganyika Law Society (TLS) Rules and Code of Professional Conduct
- TLS Disciplinary Committee Rules
- Tanzania Law of Contract Act, Cap. 433
- Tanzania Legal Aid Act, Cap. 432 — legal aid provision
- Tanzania Legal Aid Providers Association (TANLAP)
- ISO 10002:2018 — complaints handling
- IBA International Principles on Conduct for the Legal Profession (reference)
- CCBE Code of Conduct for European Lawyers (reference standard for field design)
- Client Charter for the Judiciary of Tanzania (court-related service standards)

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL legal service complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | TLS complaint form; advocate lookup |
| complainant_phone | Nambari ya simu | Yes | Status updates |
| complainant_email | Barua pepe | Recommended | TLS communicates via email |
| advocate_full_name | Jina kamili la wakili | Yes | TLS can verify registration and disciplinary history |
| law_firm_name | Jina la kampuni ya sheria | Recommended | For firm-level accountability |
| tls_enrollment_number | Nambari ya uandikishaji wa TLS (kama inajulikana) | Recommended | For TLS disciplinary lookup |
| case_type | Aina ya kesi | Yes | Criminal / Civil / Family / Land / Employment / Constitutional — determines court jurisdiction |
| court_name_and_level | Jina la mahakama na ngazi | Conditional | For court-related complaints; enables judiciary referral |
| case_file_number | Nambari ya faili ya kesi | Conditional | Required for missed deadline and negligence complaints |
| engagement_date | Tarehe ya kuanza kushirikiana na wakili | Yes | Timeline for dispute analysis |
| legal_fees_paid_tzs | Ada za kisheria zilizolipwa (TZS) | Yes | For billing disputes and trust fund complaints |
| receipt_or_agreement_available | Je, risiti au mkataba inapatikana? | Yes | Evidence for complaint |
| issue_type | Aina ya tatizo | Yes | TLS complaint taxonomy |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; detailed narrative |
| case_outcome_if_known | Matokeo ya kesi (kama yanajulikana) | Conditional | For negligence and missed deadline complaints |
| desired_outcome | Matokeo unayotaka | Yes | Refund / Compensation / Disciplinary action / Case transfer |

### Conditional Fields (collect based on issue type)

**If issue_type = Trust Fund / Client Money Misappropriation:**
Also collect:
- `amount_in_trust_tzs` — Kiasi kilichowekwa kwenye akaunti ya amana (TZS): Criminal matter; advocate holds client money in trust
- `trust_account_reference` — Nambari ya akaunti ya amana
- `purpose_of_funds` — Madhumuni ya fedha: Court fees / Settlement / Land purchase / Other
- `date_funds_deposited` — Tarehe ya kuweka fedha
- `demand_for_return_made` — Je, uliomba fedha kurudishwa? Yes / No
- **This is potentially criminal — escalate to TLS AND police**

**If issue_type = Missed Court Deadline / Negligence:**
Also collect:
- `court_date_missed` — Tarehe ya kesi iliyokosekana
- `consequence_of_missed_date` — Matokeo ya kukosa tarehe: Case dismissed / Default judgment / Limitation expired
- `advocate_explanation_given` — Maelezo ya wakili kuhusu kukosekana
- `case_dismissal_reference` — Nambari ya uamuzi wa kufuta kesi (kama ipo)
- `limitation_period_expired` — Je, muda wa kuwasilisha kesi umekwisha? Yes / No

**If issue_type = Abandonment / Non-Communication:**
Also collect:
- `last_communication_date` — Tarehe ya mawasiliano ya mwisho
- `documents_held_by_advocate` — Nyaraka zinazoshikiliwa na wakili: Client files must be returned
- `attempts_to_contact_made` — Majaribio ya kuwasiliana: Calls, visits, letters
- `urgent_court_date_pending` — Je, tarehe ya kesi ya haraka ipo? Yes / No

**If issue_type = Billing Dispute:**
Also collect:
- `fee_agreement_type` — Aina ya makubaliano ya ada: Fixed fee / Hourly rate / Contingency / Retainer
- `hourly_rate_agreed` — Ada ya kila saa iliyokubaliwa (TZS kama ya masaa)
- `hours_billed` — Masaa yaliyotozwa
- `itemized_bill_provided` — Je, ankara yenye maelezo ya kila kazi ilitolewa? Yes / No: TLS code requires itemized billing on request

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| LS-01 | trust_fund_misappropriation | Client money in trust misused or stolen |
| LS-02 | missed_court_deadline | Case dismissed or judgment entered due to advocate failure |
| LS-03 | professional_negligence | Wrong legal advice caused measurable harm |
| LS-04 | abandonment | Advocate abandoned client without notice or file return |
| LS-05 | billing_overcharge | Fees exceed agreed amount without authorization |
| LS-06 | conflict_of_interest | Advocate representing opposing party or has undisclosed interest |
| LS-07 | non_communication | Consistent failure to update client or respond |
| LS-08 | false_representation | Advocate misrepresented case status or outcome |
| LS-09 | unlicensed_practice | Person providing legal advice without TLS enrollment |
| LS-10 | document_withholding | Advocate refuses to return client documents |
| LS-11 | breach_of_confidentiality | Client information disclosed without consent |
| LS-12 | court_misconduct | Advocate behaved unprofessionally before court |
| LS-13 | poor_service_quality | Cases mishandled; poor preparation; inadequate representation |

### Resolution Standards

- **Advocate/firm level:** Complaints should be acknowledged within 3 days; billing disputes resolved within 21 days.
- **TLS Disciplinary Committee:** Complaint acknowledged within 14 days; investigation within 90 days; serious cases may take longer.
- **TLS sanctions:** Reprimand / Suspension / Disbarment depending on severity.
- **Trust fund misappropriation:** Criminal prosecution under Advocates Act; TLS Compensation Fund provides limited redress.
- **Negligence claims:** Civil lawsuit for professional negligence; advocates should carry professional indemnity insurance.
- **Document return:** TLS rules require prompt return of client files on request or on termination; advocates can retain documents for unpaid fees only in limited circumstances.
- **Legal aid:** TANLAP provides free legal assistance for qualifying complainants who cannot afford private advocates.

### Escalation Triggers

- `issue_type = trust_fund_misappropriation` AND advocate refusing to return funds — IMMEDIATE TLS disciplinary complaint + police report; criminal embezzlement; urgent
- `issue_type = missed_court_deadline` AND `case_dismissed OR limitation_expired` — Urgent TLS disciplinary complaint; potential negligence claim; malpractice insurance
- `issue_type = unlicensed_practice` — Immediate TLS referral; criminal matter under Advocates Act
- `issue_type = abandonment` AND `urgent_court_date_pending = Yes` — Emergency: advise client to appear in person to request adjournment; TLS emergency referral
- `issue_type = conflict_of_interest` AND current case — TLS disciplinary complaint; client may seek court order to remove advocate
- `legal_fees_paid_tzs > 10,000,000` AND disputed — Legal counsel; TLS fee dispute arbitration

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| firm_name | Kampuni ya sheria | Recommended | For routing |
| service_type | Aina ya huduma | Yes | Routes to correct team |
| suggestion_category | Kategoria | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| LSS-01 | communication | Mawasiliano bora na wateja |
| LSS-02 | transparency_fees | Uwazi wa ada za kisheria |
| LSS-03 | legal_aid_access | Ufikiaji bora wa msaada wa kisheria |
| LSS-04 | digital_services | Huduma za kisheria za kidijitali |
| LSS-05 | tls_accountability | Uwajibikaji bora wa TLS |
| LSS-06 | pro_bono | Kazi za bure kwa maskini |
| LSS-07 | swahili_services | Huduma za kisheria kwa Kiswahili |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina | Recommended | For tracking |
| case_type | Aina ya kesi | Conditional | For case-specific queries |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| tls_verification | Je, wakili huyu ana leseni ya TLS? | advocate_name |
| legal_aid | Ninaweza kupata msaada wa kisheria bure? | income_level, case_type |
| fees_standard | Ada za kawaida za wakili ni kiasi gani? | case_type |
| complaint_process | Jinsi ya kulalamika dhidi ya wakili? | advocate_name |
| document_retrieval | Jinsi ya kupata nyaraka zangu kutoka kwa wakili? | advocate_name |
| limitation_period | Muda wa kuwasilisha kesi wangu ni muda gani? | case_type, incident_date |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| advocate_name | Jina la wakili | Recommended | Individual recognition |
| firm_name | Kampuni ya sheria | Yes | Routes to management |
| specific_aspect_praised | Kipengele | Yes | Ujuzi wa hali ya juu / Uwazi / Ushindi wa kesi / Mawasiliano mazuri |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Legal service quality benchmarking |

---

## AI Conversation Guidance for This Industry

- **Trust fund misappropriation is a criminal emergency.** If a client reports that their money held in trust is missing, treat this as urgent: "Pesa zilizoshikiliwa na wakili kwa niaba yako ni suala la jinai kama zimechukuliwa bila idhini — unahitaji kuwasiliana na TLS na polisi leo."
- **For missed court deadlines with case dismissal, advise urgency.** "Kama kesi yako imefutwa kwa sababu ya wakili kukosa tarehe, unaweza kuwa na dai la uzembe wa kimatibabu (professional negligence) — unahitaji mshauri mwingine haraka iwezekanavyo."
- **Always verify TLS enrollment.** TANLAP and TLS maintain public registers. "Tunaweza kuthibitisha kama [jina la wakili] amesajiliwa TLS — hii ni kinga ya msingi kwa wateja."
- **For abandonment with pending court dates, prioritize court date.** "Tarehe ya kesi yako ni lini? Kama ni hivi karibuni, unapaswa kwenda mahakamani mwenyewe na kuomba muda zaidi (adjournment) huku ukitafuta wakili mwingine."
- **Do not advise on legal strategy.** Say "Ushauri wa kisheria unaohusu kesi yako unahitaji wakili mwingine — siwezi kutoa ushauri huo. Ninaweza kukusaidia kupeleka lalamiko lako kwa TLS."
- **For billing disputes, ask about the fee agreement type.** Fixed fee vs. hourly rate vs. contingency have very different dispute resolution approaches.
- **Refer to TANLAP for clients who cannot afford another lawyer.** "TANLAP (Tanzania Legal Aid Providers Association) inaweza kukusaidia kupata mshauri bure au wa bei nafuu — nambari yao ni..."

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Advocate name | "Jina kamili la wakili anayehusika ni nani?" |
| TLS number | "Je, unajua nambari ya uandikishaji wa TLS ya wakili huyu?" |
| Case file number | "Kesi yako ina nambari ya faili kwenye mahakama — je, una nambari hiyo?" |
| Fees paid | "Ada za kisheria zilizolipwa jumla ni kiasi gani? Una risiti au makubaliano ya maandishi?" |
| Trust funds | "Ulipiga pesa mahali pa wakili kwa madhumuni gani? Kiasi kilikuwa kiasi gani?" |
| Missed deadline | "Tarehe ya kesi iliyokosekana ilikuwa lini? Na matokeo ya kukosa hiyo tarehe yalikuwa gani?" |
| Court date | "Je, una tarehe ya kesi ijayo inayokaribia — ni tarehe gani?" |
| Document status | "Je, wakili ana nyaraka gani zako? Na amekwisha kuomba kurudishwa zipi?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | trust_fund_misappropriation | IMMEDIATE: TLS disciplinary complaint + police report; criminal embezzlement |
| issue_type | missed_court_deadline AND case dismissed | Urgent TLS complaint; professional negligence assessment; malpractice insurance claim |
| issue_type | unlicensed_practice | TLS immediate enforcement; criminal referral under Advocates Act |
| issue_type | abandonment AND urgent_court_date = Yes | Emergency: advise appear in court personally; TLS emergency referral; TANLAP for replacement |
| issue_type | conflict_of_interest | TLS disciplinary complaint; may seek court order to remove advocate |
| legal_fees_paid_tzs | > 10,000,000 AND disputed | TLS fee arbitration; legal counsel for resolution |
| document_withholding | Yes | TLS rules require return; formal TLS demand letter; legal injunction if necessary |
| issue_type | non_communication AND urgent case | Certified demand letter + TLS complaint; pursue adjournment in court |

---

*Sources: Tanzania Advocates Act Cap. 341, TLS Code of Professional Conduct, TLS Disciplinary Committee Rules, Tanzania Law of Contract Act Cap. 433, Tanzania Legal Aid Act Cap. 432, ISO 10002:2018, IBA International Principles*
