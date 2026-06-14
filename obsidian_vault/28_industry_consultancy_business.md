---
tags: [industry-kb, feedback-classification, field-standards]
---
# Business Consultancy / Professional Services — Feedback Collection Fields & Standards

## Industry Identifiers

management consulting, business strategy, accounting firm, audit firm, tax consultant, legal advisor, HR consultant, IT consultant, marketing agency, PR firm, research firm, NBAA certified accountant, TRA compliance, BRELA registration, TIN number, due diligence, feasibility study, business valuation, internal audit, statutory audit, transfer pricing, corporate governance, board advisory, CFO advisory, ERP implementation, engagement letter, retainer, management letter, audit report, financial model, business plan, market research, NEMC environmental assessment, OSHA compliance review, forensic accounting, AML compliance, FATCA, payroll services, outsourced CFO, company secretarial, business registration

## Why Industry-Specific Fields Matter

Consultancy complaints require capture of the engagement contract terms, the specific deliverable that failed, and which professional body the consultant is registered with — because the same issue (e.g., wrong financial advice) may fall under NBAA jurisdiction if the advisor is a certified accountant, TRA enforcement if it caused a tax penalty, or general contract law if the firm has no professional licence. Without these fields, it is impossible to route the complaint to the correct regulatory body or assess the magnitude of financial harm.

## Source Standards

- ISO 9001:2015 — Quality Management Systems (Clause 8.2 requirements for products and services; Clause 10.2 nonconformity and corrective action)
- NBAA — National Board of Accountants and Auditors (Tanzania): Professional Standards and Disciplinary Rules
- BRELA — Business Registrations and Licensing Agency (Tanzania): registration compliance standards
- TRA — Tanzania Revenue Authority: tax compliance and advisory standards
- NEMC — National Environment Management Council (Tanzania): EIA standards
- IBA International Principles on Conduct for the Legal Profession (2011) — where legal advisory overlaps
- ACCA / CPA / CIMA Professional Codes of Conduct — international professional standards recognised in Tanzania

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| firm_organisation_name | Jina la kampuni ya ushauri | Yes | Identifies the responsible entity; basis for regulatory look-up (NBAA, BRELA) |
| engagement_type | Aina ya huduma iliyotolewa | Yes | Determines which professional standards and regulatory body apply |
| engagement_reference | Nambari ya mkataba/engagement | Optional | Engagement letter reference; aids dispute resolution on scope and billing |
| lead_consultant_name | Jina la mshauri mkuu | Optional | Needed for conduct complaints (NBAA disciplinary rules) |
| engagement_start_date | Tarehe ya kuanza kazi | Yes | Establishes timeline for breach assessment |
| engagement_end_date_or_current | Tarehe ya kukamilika (au bado inaendelea) | Yes | Determines whether issue is in-progress or post-delivery |
| fee_agreed_tzs | Ada iliyokubaliwa (TZS) | Yes (if financial) | Basis for billing dispute and financial harm assessment |
| fee_invoiced_tzs | Ada iliyotozwa kwenye ankara | Yes (if financial) | Enables comparison against agreed amount |
| issue_type | Aina ya tatizo | Yes | Determines routing: NBAA / TRA / BRELA / NEMC / court / internal |
| specific_deliverable_affected | Kazi/Ripoti iliyoathirika | Yes | Ties complaint to a specific output — report, computation, filing, advice, system |
| financial_loss_caused_tzs | Hasara ya kifedha (TZS) | Yes (if applicable) | Material for regulatory escalation and compensation claims |
| detailed_description | Maelezo ya kina | Yes | ISO 9001 §10.2; basis for investigation |
| desired_outcome | Matokeo yanayotarajiwa | Yes | Enables assessment of remedy options (refund, correction, damages) |
| previous_complaint_to_firm | Je, ulishawasiliana na kampuni? | Yes | Internal resolution requirement under ISO 9001 |
| complainant_name | Jina la mlalamikaji | Yes | Required for all correspondence |
| complainant_contact | Mawasiliano (simu/barua pepe) | Yes | Required for follow-up |
| supporting_documents | Nyaraka za kuthibitisha | Optional | Engagement letter, deliverable, invoice, correspondence, TRA penalty notice |

### Conditional Fields (collect based on issue type)

**If issue_type = Deliverable Quality / Negligence:**
- deliverable_type → audit report / feasibility study / financial model / business plan / market research / HR policy / IT audit / valuation / tax computation / due diligence report / other
- scope_agreed_reference → what was agreed in the engagement letter vs. what was delivered
- error_type → factual error / formula error / outdated data / scope mismatch / copied/generic content / wrong methodology
- consequence_of_error → TRA penalty / legal dispute / investor rejection / regulatory non-compliance / business loss / lender rejection

**If issue_type = Billing / Fee Dispute:**
- fee_agreement_type → fixed fee / time-and-materials / retainer / contingency / milestone-based
- invoice_itemisation_provided → whether invoice included breakdown of work (Yes/No)
- disputed_amount_tzs → specific amount disputed
- additional_charges_pre-agreed → whether additional charges were agreed in advance (Yes/No)
- payment_made_tzs → amount actually paid to date

**If issue_type = Regulatory / Compliance Failure:**
- regulation_affected → TRA / BRELA / NBAA / NEMC / OSHA / Companies Act / other
- penalty_or_action_received → fine amount (TZS) / license suspension / legal action / other
- advisor_position_taken → what the consultant advised vs. what the regulation actually requires
- regulator_correspondence → whether complainant has received formal notice from regulator (Yes/No + attach)

**If issue_type = Confidentiality Breach:**
- information_type_disclosed → financial records / personnel data / strategic plans / client lists / trade secrets
- disclosure_recipient → competitor / third party / public / unknown
- evidence_of_breach → how the breach was discovered
- harm_caused → reputational / financial / legal / competitive

**If issue_type = Consultant Conduct:**
- conduct_type → unavailability / misrepresentation of seniority / unprofessional behaviour / undisclosed conflict of interest / unauthorized commitment
- billing_level_vs_delivery → whether partner rates were billed but junior staff delivered (Yes/No)
- conflict_of_interest_disclosed → whether any conflict of interest was disclosed at engagement start (Yes/No)

**If issue_type = Technology / ERP Implementation:**
- system_name → ERP system / software product name
- go_live_status → Live / Not live / Partially live
- budget_agreed_tzs → agreed implementation budget
- budget_actual_tzs → actual spend to date
- data_integrity_issue → whether data migration corrupted or lost records (Yes/No)

### Issue Type Classification

| Code | Issue Type | Regulatory Body | Resolution Target |
|------|-----------|----------------|-------------------|
| CON-GR-01 | Deliverable Quality / Negligence | NBAA / TRA / ISO 9001 | 21 working days |
| CON-GR-02 | Billing / Fee Dispute | Engagement contract / consumer law | 14 working days |
| CON-GR-03 | Regulatory / Compliance Failure | TRA / BRELA / NBAA / NEMC | 14 working days + regulatory referral |
| CON-GR-04 | Timeliness / Delay | ISO 9001 / engagement terms | 14 working days |
| CON-GR-05 | Communication / Responsiveness | ISO 9001 / engagement terms | 7 working days |
| CON-GR-06 | Confidentiality Breach | NBAA Code / data protection / legal | Immediate escalation |
| CON-GR-07 | Consultant Conduct | NBAA disciplinary rules / firm HR | 21 working days |
| CON-GR-08 | ERP / Technology Implementation | Contract / ISO 9001 | 21 working days |
| CON-GR-09 | Financial Fraud / Misappropriation | Police / NBAA / courts | Immediate escalation |

### Resolution Standards for This Industry

- **NBAA**: Complaints against NBAA-registered accountants and auditors are investigated by NBAA's Disciplinary Committee. If a certified accountant is found to have acted in breach of professional standards, sanctions include reprimand, fine, suspension, or deregistration.
- **TRA**: If a tax advisor's error caused a penalty, the firm may be liable for the penalty under the engagement agreement. TRA investigations are independent — the complainant should engage TRA directly for penalty waiver applications.
- **ISO 9001 §10.2**: Firms certified under ISO 9001 must document complaints, investigate root cause, implement corrective action, and communicate outcome in writing within their published resolution timeframe.
- **Engagement Letter**: Most disputes are governed first by the terms of the engagement letter — scope, fee, liability cap, and dispute resolution clause. Collect this document early.
- **BRELA**: If business registration errors caused legal or commercial harm, BRELA has a complaint mechanism for licensed registration agents.

### Escalation Triggers (field values that require immediate escalation)

- `issue_type = CON-GR-06` (Confidentiality Breach) → immediate notification to firm's Data Protection Officer; flag for legal review within 24 hours
- `issue_type = CON-GR-09` (Financial Fraud / Misappropriation of client funds) → refer to Police and NBAA within 24 hours; advise complainant to freeze any ongoing payments
- `issue_type = CON-GR-03` AND `regulation_affected = TRA` AND `penalty_amount > TZS 100,000,000` → urgent escalation; recommend specialist tax litigation advisor
- Audit report signed off with falsified findings → immediate referral to NBAA Disciplinary Committee
- Consultant bribed a government official on behalf of client → refer to PCCB (Prevention and Combating of Corruption Bureau) immediately
- Due diligence failure resulted in client acquiring an entity with undisclosed liabilities now in litigation → flag for legal review
- Misrepresentation in investment memo causing investor losses → flag for securities fraud review

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| firm_organisation_name | Jina la kampuni ya ushauri | Yes | ISO 9001 §10.3 — improvement tied to responsible firm |
| engagement_type | Aina ya huduma | Yes | Improvement must be linked to a specific service area |
| suggestion_category | Aina ya pendekezo | Yes | ISO 9001 §10.3 continual improvement classification |
| suggestion_detail | Maelezo ya pendekezo | Yes | Full description of improvement idea |
| commercial_impact | Athari ya kibiashara | Optional | Helps firm prioritise improvements with client impact evidence |

### Industry-Specific Improvement Categories

| Category Code | Category Name | Swahili |
|--------------|---------------|---------|
| CON-SG-01 | Deliverable Quality / Depth | Ubora wa kazi inayotolewa |
| CON-SG-02 | Client Communication / Transparency | Mawasiliano na mteja |
| CON-SG-03 | Fee Transparency / Billing Clarity | Uwazi wa ada na ankara |
| CON-SG-04 | Timeline / Project Management | Usimamizi wa muda wa mradi |
| CON-SG-05 | Tanzanian / East African Context | Uhalisi wa Tanzania/Afrika Mashariki |
| CON-SG-06 | Consultant Expertise / Sector Knowledge | Uzoefu wa sekta ya mshauri |
| CON-SG-07 | Regulatory Alignment (TRA/BRELA/NEMC) | Ufuatao wa sheria za Tanzania |
| CON-SG-08 | Technology / Data Systems | Mifumo ya teknolojia |
| CON-SG-09 | SME Accessibility / Pricing | Upatikanaji kwa biashara ndogo |
| CON-SG-10 | Post-Engagement Support | Msaada baada ya kazi kukamilika |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| firm_name | Jina la kampuni ya ushauri | Yes | Routes inquiry to correct firm or body |
| inquiry_type | Aina ya swali | Yes | Determines information source and expected expertise |
| full_name | Jina kamili | Yes | Required for personalised response |
| contact_details | Mawasiliano | Yes | Required for follow-up |
| specific_question | Swali maalum | Yes | ISO 9001 §7.4 — full question text required |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Additional Fields Needed |
|-------------|-------------------------|
| Scope of specific service | engagement_type, company_size, industry_sector |
| Cost / Fee estimate | service_type, scope_description, company_turnover (if audit) |
| Consultant credentials / NBAA registration | consultant_name, service_type |
| TRA requirements / compliance | specific_tax_issue, company_type, transaction_type |
| BRELA registration process | entity_type, business_activity, ownership_structure |
| NEMC / Environmental Assessment | project_type, project_location, project_scale |
| Audit requirement (statutory vs. internal) | company_type, ownership, turnover_range |
| Transfer pricing documentation | parent_company_country, transaction_types, annual_value |
| ERP / IT implementation scope | current_system, target_system, staff_count, industry |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| firm_organisation_name | Jina la kampuni ya ushauri | Yes | ISO 9001 §9.1.2 — satisfaction monitoring must be firm-linked |
| engagement_type | Aina ya huduma | Yes | Positive feedback must be tied to a specific service for staff recognition |
| subject_of_praise | Kinachosifiwa | Yes | Enables firm to recognise and replicate excellent practice |
| named_consultant | Jina la mshauri (kama ipo) | Optional | Individual recognition; encourages excellence |
| description | Maelezo ya uzoefu mzuri | Yes | ISO 9001 §9.1.2 — client satisfaction data |
| business_outcome_achieved | Matokeo ya biashara yaliyofikiwa | Optional | Strengthens understanding of real-world impact |

### Praise Subject Categories

| Code | Subject | Swahili |
|------|---------|---------|
| CON-AP-01 | Deliverable Quality | Ubora wa kazi iliyotolewa |
| CON-AP-02 | Consultant Expertise / Knowledge | Uzoefu na ujuzi wa mshauri |
| CON-AP-03 | Communication / Responsiveness | Mawasiliano na ujibu wa haraka |
| CON-AP-04 | Timeliness / Delivery Speed | Kufanya kazi kwa wakati |
| CON-AP-05 | Integrity / Ethical Conduct | Uadilifu na maadili |
| CON-AP-06 | Regulatory Navigation (TRA/BRELA) | Usimamizi wa masuala ya kisheria/kanuni |
| CON-AP-07 | Value for Money | Thamani ya pesa iliyolipwa |

---

## AI Conversation Guidance for This Industry

- **Start with the engagement type and deliverable, not the problem narrative**: Ask "Ni aina gani ya huduma ya ushauri ulipata — ukaguzi, ushauri wa kodi, ushauri wa biashara, au kitu kingine?" and "Ni kazi gani mahsusi iliyosababisha tatizo hili — ripoti, hesabu, uwakilishi mbele ya TRA, au nyingine?" This narrows the routing decision before any detailed story is collected.
- **Distinguish financial harm amount from disputed fee early**: These are different fields — `financial_loss_caused_tzs` (harm caused by bad advice, e.g., TRA penalty) and `fee_invoiced_tzs` (overbilling dispute). Ask both but separately: "Je, ulipata hasara yoyote ya kifedha kama faini au kupoteza mkataba kwa sababu ya ushauri mbaya?" and separately "Je, kuna tatizo pia na ankara au ada iliyotozwa?"
- **For regulatory failures, ask which body issued the penalty or rejected the filing** — this is more informative than asking "what went wrong." The complainant often does not know the professional standard was breached, but they know "TRA walikataa" or "BRELA ilirudisha nyaraka zetu."
- **For conduct complaints about seniority misrepresentation**, ask: "Katika mkataba au mazungumzo ya awali, walitaja majina ya washauri watakaofanya kazi kwenye mradi huu?" — this establishes whether there was a representation about staffing that was subsequently breached.
- **Do not ask for the engagement letter as the first question** — many SME clients never received a written engagement letter, and asking for it early can make them feel their complaint is invalid. Establish the facts of what was agreed verbally first, then ask about written documentation.

## Swahili Key Phrases for Field Collection

| Field Being Collected | Swahili Phrase to Use |
|----------------------|----------------------|
| firm_organisation_name | "Ni kampuni gani ya ushauri unaozungumzia?" |
| engagement_type | "Walikusaidia na aina gani ya kazi — ukaguzi, kodi, usajili, ERP, au nyingine?" |
| specific_deliverable_affected | "Ni ripoti au kazi gani mahsusi ambayo haikuwa ya kiwango?" |
| financial_loss_caused_tzs | "Je, tatizo hili lilisababisha hasara ya kifedha? Ni kiasi gani?" |
| fee_agreed_tzs | "Ada iliyokubaliwa mwanzoni ilikuwa ngapi?" |
| fee_invoiced_tzs | "Walitoza kiasi gani kwenye ankara yao ya mwisho?" |
| desired_outcome | "Unataka nini kifanyike — kurejesha pesa, kusahihisha makosa, au kitu kingine?" |
| previous_complaint_to_firm | "Je, umeshazungumza na kampuni hiyo kuhusu tatizo hili? Walisema nini?" |
| regulation_affected | "Je, mlikuwa na tatizo na TRA, BRELA, au shirika lingine la serikali kwa sababu ya ushauri huu?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | CON-GR-06 (Confidentiality Breach) | Immediate escalation to human reviewer; advise complainant to seek legal counsel |
| issue_type | CON-GR-09 (Financial Fraud) | Refer to Police and NBAA within 24 hours; advise complainant to stop further payments |
| financial_loss_caused_tzs | > TZS 100,000,000 | Flag for urgent senior review; recommend legal representation |
| regulation_affected | TRA AND penalty_received = Yes | Advise complainant to file penalty waiver with TRA; recommend specialist tax advisor |
| lead_consultant_nbaa_registered | Yes | Route conduct complaint to NBAA Disciplinary Committee; provide NBAA contact |
| lead_consultant_nbaa_registered | No / Unknown | Advise complainant to check NBAA register; if unregistered, flag as potential fraud |
| invoice_itemisation_provided | No | Flag as potential billing malpractice; advise complainant to request full itemised invoice |
| conflict_of_interest_disclosed | No | Flag as breach of NBAA Code / IBA Principles; escalate if material harm caused |
| issue_type | CON-GR-03 AND regulation_affected = NEMC | Refer to NEMC for investigation; advise on EIA requirements |
| data_integrity_issue | Yes (ERP migration) | Flag as urgent; advise immediate system freeze and data recovery assessment |

---

## Key Entities & Roles

**Regulatory Bodies:** TRA (Tanzania Revenue Authority), NBAA (National Board of Accountants and Auditors), BRELA (Business Registrations and Licensing Agency), NEMC (National Environment Management Council), OSHA Tanzania, CAG (Controller and Auditor General), PCCB (Prevention and Combating of Corruption Bureau)
**Job Titles:** Managing Partner, Senior Partner, Engagement Manager, Senior Consultant, Associate Consultant, Tax Manager, Audit Manager, IT Consultant, HR Consultant, Research Analyst, Legal Advisor, CFO Advisory Specialist, Due Diligence Analyst
**Documents & Deliverables:** Engagement Letter, Management Letter, Audit Report, Feasibility Study, Business Plan, Financial Model, Due Diligence Report, Tax Computation, Transfer Pricing Documentation, Board Paper, Strategic Roadmap, HR Policy Manual, IT Audit Report, Business Valuation Report, EIA Report
**Certifications:** NBAA CPA, CFA, ACCA, CIMA, CISA, ISO 9001

---

## Kiswahili / Swahili Equivalents

### Malalamiko (Complaints)
- "Ripoti mliyotuletea haikuwa na ubora wa kutosha"
- "Mshauri wenu hakuwa na uzoefu wa kutosha katika sekta yetu"
- "Tulisubiri wiki tatu kupata ripoti iliyochelewa bila sababu"
- "Ankara yenu haikuonyesha kazi zilizofanywa kwa undani"
- "Kazi hiyo haikufanywa vizuri na TRA wanatutoza faini sasa"
- "Tuliombwa kulipa zaidi ya bei iliyokubaliwa kwenye mkataba"
- "Mshauri wenu alishiriki taarifa zetu za siri na watu wengine"

### Mapendekezo (Suggestions)
- "Ingekuwa vizuri kupewa ripoti ya maendeleo kila wiki"
- "Mnapaswa kutupatia mshauri mwenye uzoefu katika sekta ya Tanzania"
- "Pendekeza bei za uwazi zaidi kabla ya kuanza kazi"
- "Ingekuwa bora kusoma mazingira ya Tanzania kabla ya kutoa ushauri"

### Maswali (Inquiries)
- "Je, mshauri wenu ana usajili wa NBAA?"
- "Gharama za ukaguzi wa kisheria ni ngapi kwa kampuni ndogo?"
- "Je, mnaweza kusaidia na usajili wa BRELA na TIN pamoja?"
- "Je, mnaweza kutuwakilisha mbele ya TRA?"

### Pongezi (Compliments)
- "Mshauri wenu alifanya kazi bora sana — asante sana"
- "Ripoti ya mkakati ilikuwa kamili na ya kina sana"
- "Timu yenu ilifanya kazi kwa weledi na uaminifu mkubwa"
- "Kazi mliyofanya imetusaidia kuepuka matatizo makubwa ya TRA"

---

## Industry-Specific Escalation Triggers

1. Consultant shared confidential client financial data with a third party — immediate investigation required
2. Audit report signed off with falsified or misrepresented findings — refer to NBAA Disciplinary Committee
3. Tax advice caused TRA penalty assessment exceeding TZS 100 million — urgent remediation
4. Due diligence failure resulted in client acquiring a company with undisclosed liabilities now in litigation
5. NBAA-certified accountant signed a report they did not prepare — professional ethics violation
6. Client funds held in escrow by the firm are unaccounted for — potential financial fraud; refer to Police
7. Consultant bribed a government official on behalf of the client — refer to PCCB immediately
8. Data breach exposed sensitive client financial or personnel records
9. Misrepresentation in investment memo has caused investors to lose funds — securities fraud risk
10. Regulatory filing missed and client faces legal action due to advisor's failure
11. Consultant made unauthorized commitments on behalf of client in negotiations
12. Conflict of interest: firm advising both parties in a transaction without disclosure

---

## Disambiguation Notes

- **Consultancy vs. Financial Services**: Both involve financial advice, but consultancy focuses on deliverables, reports, and advisory quality rather than investment returns or loan products. "Engagement," "scope," "deliverable," "strategy" → Consultancy.
- **Consultancy vs. Training**: Training feedback focuses on learning outcomes, trainers, curricula. "Course," "facilitator," "exam," "certificate" → Training, not Consultancy.
- **Consultancy vs. Legal Services**: Legal advisor feedback may come through a consultancy firm — escalate signals around court cases, contracts, and litigation to Legal Services.
- **Tax Consulting vs. General Accounting**: Tax-specific complaints reference TRA, VAT returns, transfer pricing, penalties. General accounting complaints reference balance sheets, reconciliations. Both fall under this industry but require different routing.
- **IT Consulting vs. Technology/SaaS**: IT consulting feedback is about advisory and ERP implementation by consultants. Technology product feedback is about software the company uses directly. Distinguish by whether a "consultant" or "firm" is mentioned versus a "platform" or "system."
- **Company Secretarial vs. Legal Services**: Company registration and secretarial services belong here when provided by a non-legal business advisory firm; classify under Legal Services only when provided by an advocate or law firm.
