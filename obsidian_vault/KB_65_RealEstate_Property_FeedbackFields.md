---
tags: [industry-kb, field-standards, feedback-fields, real-estate, property]
---
# Real Estate / Property — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: mali isiyohamishika, real estate, property, nyumba ya kupanga, rental property, kukodisha, landlord, mpangaji, mwenye nyumba, tenant, lease, mkataba wa kukodisha, rent, kodi ya nyumba, deposit, amana ya kukodisha, eviction, kufukuzwa nyumba, notice to vacate, taarifa ya kuacha, property management, usimamizi wa mali, estate agent, dalali wa nyumba, property agent, property valuer, mthamini wa mali, RICS, ATRV (Association of Tanzania Real Estate Valuers), land registry, usajili wa ardhi, title deed, hati ya ardhi, plot number, nambari ya kiwanja, lease agreement, maintenance, matengenezo, repairs, ukarabati, utility bills, bili za huduma, rent increase, kuongeza kodi, illegal eviction, kufukuzwa haramu, security deposit, amana ya usalama, return of deposit, kurudisha amana, property listing, uuzaji wa nyumba, commission, posho ya dalali, escrow, lease renewal, kuhuisha mkataba, commercial property, mali ya biashara, residential property, mali ya makazi

## Why Industry-Specific Fields Matter

Real estate complaints span landlord-tenant disputes (requiring lease agreement reference, deposit amount, eviction notice), property agent fraud (requiring agency license, sale agreement), valuation disputes (requiring valuer registration number), and maintenance failures (requiring specific defect description and prior notice to landlord). Without these fields, the AI cannot route a complaint to the correct authority — Rent Restriction Act for residential tenancy, Land Tribunal for title disputes, or professional body for valuer conduct.

## Source Standards

- Tanzania Rent Restriction Act, Cap. 479 — residential tenancy rights
- Tanzania Land Act, Cap. 113 — property rights and transactions
- Tanzania Land Disputes Courts Act, Cap. 216 — land and property disputes
- Land (Tenant Farmers) Act — tenant farmers rights
- ATRV (Association of Tanzania Real Estate Valuers) professional standards
- RICS (Royal Institution of Chartered Surveyors) — international reference for valuation standards
- Tanzania Fair Competition Act, Cap. 285 — property agent conduct
- ISO 10002:2018 — complaints handling
- Tanzania Law of Contract Act, Cap. 433 — lease contracts

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL real estate/property complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Complaint registration |
| complainant_phone | Nambari ya simu | Yes | Status updates |
| complainant_role | Nafasi ya mlalamikaji | Yes | Tenant / Landlord / Buyer / Seller / Neighbor — shapes rights |
| property_address | Anwani ya mali | Yes | For geographic jurisdiction and property identification |
| plot_number | Nambari ya kiwanja | Recommended | Land Registry identifier; enables title search |
| landlord_or_owner_name | Jina la mwenye nyumba | Conditional | For tenant complaints |
| property_agent_name | Jina la dalali wa nyumba | Conditional | For agent complaints |
| lease_agreement_reference | Nambari ya mkataba wa kukodisha | Conditional | For tenant/landlord disputes |
| rental_amount_tzs | Kodi ya kila mwezi (TZS) | Conditional | For rent dispute quantification |
| deposit_paid_tzs | Amana iliyolipwa (TZS) | Conditional | For deposit disputes |
| tenancy_start_date | Tarehe ya kuanza kukodisha | Conditional | For dispute timeline |
| issue_type | Aina ya tatizo | Yes | Complaint taxonomy |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; detailed narrative |
| notice_given_to_other_party | Je, taarifa ilitolewa kwa upande wa pili? | Recommended | For eviction and deposit disputes |
| desired_outcome | Matokeo unayotaka | Yes | Deposit return / Repairs / Prevent eviction / Agent accountability |

### Conditional Fields (collect based on issue type)

**If issue_type = Illegal Eviction:**
Also collect:
- `eviction_notice_received` — Je, taarifa ya kuacha ilipokelewa? Yes / No
- `notice_period_given_days` — Siku za taarifa zilizotolewa: Rent Restriction Act requires minimum notice
- `reason_for_eviction_stated` — Sababu iliyotolewa ya kufukuzwa
- `court_order_for_eviction` — Je, amri ya mahakama ilitolewa kwa kufukuzwa? Yes / No: Eviction without court order is illegal
- `belongings_seized_or_locked_out` — Je, mali imeshikiliwa au mlango umefungwa?: Illegal lockout; emergency legal relief needed

**If issue_type = Deposit Not Returned:**
Also collect:
- `tenancy_end_date` — Tarehe ya kukamilika kwa ukodishaji
- `deposit_return_deadline_days` — Siku zinazotakiwa kurudisha amana (kawaida siku 14–30)
- `deductions_made_by_landlord` — Makato yaliyofanywa na mwenye nyumba: Amount and reason
- `property_condition_at_handover` — Hali ya nyumba wakati wa kukabidhiwa: For deduction justification
- `handover_inventory_signed` — Je, inventori ya kukabidhia ilisainiwa? Yes / No

**If issue_type = Maintenance / Habitability:**
Also collect:
- `maintenance_issue_type` — Aina ya tatizo la matengenezo: Leaking roof / No water / Electrical fault / Sewage / Structural crack / Pest infestation
- `landlord_notified_of_issue` — Je, mwenye nyumba aliarifu tatizo? Yes / No
- `date_notified` — Tarehe ya kutoa taarifa
- `landlord_response` — Jibu la mwenye nyumba: Ignored / Promised but no action / Partial action
- `habitability_impact` — Athari kwa hali ya kuishi: Unsafe / Significant inconvenience / Minor inconvenience

**If issue_type = Property Agent Fraud / Commission Dispute:**
Also collect:
- `commission_rate_agreed` — Asilimia ya posho iliyokubaliwa
- `commission_amount_tzs` — Kiasi cha posho kilicholipwa (TZS)
- `services_rendered` — Huduma zilizotolewa na dalali: Viewing / Negotiation / Documentation / Handover
- `agent_license_number` — Nambari ya leseni ya dalali (kama ipo)
- `deposit_held_by_agent` — Je, amana inashikiliwa na dalali? Yes / No: Security risk

**If issue_type = Valuation Dispute:**
Also collect:
- `valuer_name` — Jina la mthamini
- `atrv_registration_number` — Nambari ya usajili wa ATRV
- `valuation_purpose` — Madhumuni ya tathmini: Bank loan / Taxation / Sale / Insurance
- `valuation_amount_tzs` — Kiasi cha tathmini (TZS)
- `disputed_amount_tzs` — Kiasi kinachobiwabishwa (TZS)
- `independent_valuation_obtained` — Je, tathmini huru imefanywa?

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| RE-01 | illegal_eviction | Eviction without court order or proper notice |
| RE-02 | deposit_not_returned | Security deposit not returned after tenancy ends |
| RE-03 | unlawful_rent_increase | Rent increased above Rent Restriction Act limits |
| RE-04 | maintenance_failure | Landlord fails to maintain property in habitable condition |
| RE-05 | property_agent_fraud | Agent misrepresented property, withheld deposit, or collected double commission |
| RE-06 | title_deed_dispute | Disputed ownership or fraudulent title |
| RE-07 | valuation_dispute | Valuation negligent or manipulated |
| RE-08 | lease_terms_violation | Landlord or tenant breaching specific lease terms |
| RE-09 | noise_disturbance | Noise or nuisance from neighboring property |
| RE-10 | utility_billing_dispute | Landlord charging wrong amounts for utilities |
| RE-11 | discrimination | Landlord refusing to rent on discriminatory basis |
| RE-12 | privacy_invasion | Landlord entering property without notice or consent |
| RE-13 | commercial_lease_dispute | Commercial property lease dispute |
| RE-14 | subletting_dispute | Unauthorized subletting or subletting dispute |
| RE-15 | sale_contract_dispute | Property sale agreement breach or fraud |

### Resolution Standards

- **Tenant/Landlord level:** Rent Restriction Board; parties should negotiate first.
- **Rent Restriction Tribunal:** Complaints regarding controlled residential rent; hearing within 30 days.
- **Land Tribunal:** Title and ownership disputes; District Land and Housing Tribunal → High Court (Land Division).
- **Legal aid:** TANLAP for tenants who cannot afford legal representation.
- **Deposit:** Standard practice is 14–30 days return after tenancy ends; deductions must be itemized.
- **Required for escalation:** Lease agreement, deposit receipts, maintenance request records, eviction notice.

### Escalation Triggers

- `issue_type = illegal_eviction` AND `court_order_for_eviction = No` — Emergency legal aid; illegal eviction; police report if forcible entry
- `issue_type = illegal_eviction` AND `belongings_seized = Yes` — Immediate legal injunction; police; CHRAGG referral
- `issue_type = deposit_not_returned` AND significant amount — Rent Restriction Tribunal or Small Claims Court
- `issue_type = title_deed_dispute` AND fraudulent title suspected — Police + Land Registry + Land Tribunal
- `issue_type = maintenance_failure` AND habitability severely impacted — Rent Restriction Tribunal; local health authority (if unsanitary)
- `deposit_held_by_agent = Yes` AND agent unresponsive — Urgent; police report; FCC consumer protection

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| area_or_district | Eneo au wilaya | Recommended | Geographic routing |
| property_type | Aina ya mali | Yes | Residential / Commercial / Land |
| suggestion_category | Kategoria | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| RES-01 | tenant_rights | Haki bora za wapangaji |
| RES-02 | agent_regulation | Udhibiti wa mawakala wa nyumba |
| RES-03 | maintenance_standards | Viwango vya matengenezo |
| RES-04 | affordable_rentals | Kodi nafuu zaidi |
| RES-05 | digital_listing | Uorodheshaji wa kidijitali wa mali |
| RES-06 | dispute_resolution | Mchakato wa haraka wa kutatua migogoro |
| RES-07 | deposit_protection | Ulinzi wa amana za kukodisha |
| RES-08 | green_properties | Mali rafiki wa mazingira |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina | Recommended | For tracking |
| complainant_role | Nafasi | Yes | Tenant vs. landlord routes differ |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| eviction_rights | Haki zangu ikiwa napewa taarifa ya kuacha | lease_agreement, notice_period |
| deposit_rights | Haki zangu kuhusu amana yangu | deposit_paid_tzs, tenancy_end_date |
| rent_increase_limit | Kodi inaweza kuongezwa kwa kiasi gani? | current_rent, property_type |
| maintenance_obligation | Nani anahusika na matengenezo — mwenye nyumba au mpangaji? | lease_terms |
| title_deed_verification | Jinsi ya kuthibitisha hati ya ardhi | plot_number, location |
| land_tribunal_process | Jinsi ya kupeleka kesi Land Tribunal | case_type |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| agent_or_landlord_name | Jina la dalali / mwenye nyumba | Recommended | Recognition |
| property_address | Anwani ya mali | Recommended | For routing |
| specific_aspect_praised | Kipengele | Yes | Nyumba safi / Haraka ya ukarabati / Uaminifu wa amana / Upendeleo wa mpangaji |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Property management quality |

---

## AI Conversation Guidance for This Industry

- **For illegal eviction, treat as urgent.** "Kufukuzwa nyumba bila amri ya mahakama ni haramu Tanzania — unahitaji msaada wa kisheria haraka. Piga simu TANLAP au wakili leo."
- **For deposit disputes, ask for the inventory report.** "Je, kulikuwa na inventori (orodha ya vitu) iliyosainishwa wakati wa kuingia na wakati wa kuacha nyumba? Hiyo inaathiri sana haki ya makato."
- **For maintenance complaints, ask whether the landlord was notified.** Under most lease agreements, the landlord must be given written notice before the tenant can take remedial action. "Je, ulimwandikia au kumpigia simu mwenye nyumba kuhusu tatizo hili? Lini, na jibu lake lilikuwa nini?"
- **For title deed disputes, direct immediately to Land Tribunal.** Title disputes are legal matters requiring court determination. "Ugomvi wa hati ya ardhi unahitaji Land Tribunal — siwezi kusaidia kufanya uamuzi huo, lakini naweza kukusaidia kupeleka malalamiko yako."
- **For property agent fraud, ask about the deposit held by agent.** If the agent holds the deposit and is unresponsive, this is an emergency — money is at risk. "Je, amana ya TZS [kiasi] inashikiliwa na dalali mwenyewe au mwenye nyumba? Kama iko kwa dalali na hajaweza kuwasiliana, hii ni hali ya dharura."
- **Do not assess whether rent is fair.** The Rent Restriction Act has specific provisions; reference to the Act or Tribunal is the correct response.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Complainant role | "Wewe ni mpangaji, mwenye nyumba, mnunuzi, au dalali?" |
| Property address | "Anwani kamili ya nyumba au mali inayohusika ni ipi?" |
| Plot number | "Nambari ya kiwanja (plot number) inaweza kuonekana kwenye hati ya ardhi au ankara ya kodi" |
| Lease reference | "Mkataba wa kukodisha una nambari ya marejeleo — je, una nambari hiyo?" |
| Deposit amount | "Amana iliyolipwa ilikuwa kiasi gani? Na ililipwa kwa nani?" |
| Eviction notice | "Je, taarifa ya kuacha ilipewa kwa maandishi? Tarehe ya taarifa ilikuwa lini, na siku ngapi zilitolewa?" |
| Court order | "Je, mwenye nyumba ana amri ya mahakama ya kukufukuza? Kama hapana, hii inaweza kuwa haramu" |
| Maintenance notice | "Ulimwandikia au kumwambia mwenye nyumba kuhusu tatizo la matengenezo? Lini?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | illegal_eviction AND no_court_order | Emergency legal aid; TANLAP referral; police if forcible entry; CHRAGG referral |
| belongings_seized | Yes AND no court order | Immediate legal injunction; police; document as criminal conduct |
| issue_type | title_deed_dispute AND fraudulent | Police + Land Registry + Land Tribunal; criminal referral for fraud |
| deposit_held_by_agent | Yes AND agent unresponsive | Police report; FCC consumer protection; consider it at-risk until recovered |
| issue_type | maintenance_failure AND habitability severe | Rent Restriction Tribunal; local health authority if sanitation concern |
| issue_type = unlawful_rent_increase | above Rent Restriction Act limits | Rent Restriction Tribunal complaint |
| issue_type | discrimination | CHRAGG complaint; Fair Competition Act consumer protection |
| issue_type | property_agent_fraud | FCC complaint; police if fraud; ATRV professional conduct if registered |

---

*Sources: Tanzania Rent Restriction Act Cap. 479, Land Act Cap. 113, Land Disputes Courts Act Cap. 216, Tanzania Law of Contract Act Cap. 433, Fair Competition Act Cap. 285, ATRV Professional Standards, RICS Standards (reference), ISO 10002:2018*
