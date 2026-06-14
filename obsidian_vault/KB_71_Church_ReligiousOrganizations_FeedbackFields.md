---
tags: [industry-kb, field-standards, feedback-fields, church, religious-organizations]
---
# Church / Religious Organizations — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: kanisa, church, msikiti, mosque, hekalu, temple, parish, diocese, congregation, mkutano wa ibada, pastor, mchungaji, bishop, askofu, imam, padre, reverend, deacon, shemasi, elder, mzee wa kanisa, worship, ibada, sermon, mahubiri, tithe, zaka, offering, sadaka, fellowship, ushirika, choir, kwaya, Sunday school, shule ya Jumapili, youth ministry, vijana wa kanisa, women's guild, umoja wa wanawake, cell group, kundi la nyumba, prayer meeting, mkutano wa maombi, baptism, ubatizo, wedding ceremony, ndoa ya kanisani, burial service, mazishi, crusade, msafara wa injili, revival meeting, uamsho, church camp, kambi ya kanisa, mission, umishonari, denomination, madhehebu, synod, sinodi, conference, mkutano mkuu, church constitution, katiba ya kanisa, church fund, mfuko wa kanisa, building fund, mfuko wa ujenzi, KKKT, Evangelical Lutheran Church in Tanzania, TEC, Tanzania Episcopal Conference, Assemblies of God, Pentecostal, Seventh-Day Adventist, Catholic Church, National Muslim Council of Tanzania, BAKWATA

## Why Industry-Specific Fields Matter

Religious organization complaints span financial misconduct (requiring specific fund name, amounts, and church committee structure), pastoral misconduct (requiring witness details and church disciplinary process information), service quality feedback (requiring service type and date), and governance disputes (requiring church constitution reference and leadership roles). Without these fields, the AI cannot route the complaint to the correct denominational oversight body or assist in generating a formal complaint to BAKWATA, the relevant diocese, or the denomination's national council.

## Source Standards

- Tanzania Religious Organizations Registration Act, Cap. 39 — registration requirements
- Religious Organizations (Amendment) Act 2019
- NGO Act Cap. 56 (for registered religious organizations with NGO activities)
- Tanzania Anti-Corruption Act (for financial misconduct involving public resources)
- Child Act, Cap. 13 — for child protection in religious settings
- Prevention of Violence Against Women and Children Act 2022 — for sexual misconduct
- PCCB Act, Cap. 329 — for corruption involving religious organization finances
- ISO 10002:2018 — complaints handling
- BAKWATA (National Muslim Council of Tanzania) — Islamic organization standards
- TEC (Tanzania Episcopal Conference) — Catholic church standards
- KKKT (Evangelical Lutheran Church in Tanzania) — disciplinary procedures

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL religious organization complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji (hiari kwa usalama) | Optional | Anonymous accepted; especially for sensitive pastoral complaints |
| complainant_phone | Nambari ya simu (hiari) | Optional | Status updates |
| complainant_membership_status | Hali ya uanachama | Yes | Active member / Former member / Visitor / Community member — shapes standing |
| church_organization_name | Jina la kanisa / taasisi ya dini | Yes | Routes to correct denominational oversight |
| denomination | Madhehebu | Yes | Catholic / Lutheran / Anglican / Pentecostal / Muslim / Adventist / Other — denominational governance differs |
| branch_or_parish | Tawi / Parokia | Recommended | Branch-level accountability |
| leader_in_question | Jina la kiongozi anayehusika | Conditional | For leadership and pastoral complaints |
| leader_position | Cheo cha kiongozi | Conditional | Pastor / Bishop / Elder / Deacon / Imam — determines oversight level |
| issue_type | Aina ya tatizo | Yes | Financial / Pastoral conduct / Service / Governance |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; detailed narrative |
| witnesses_available | Je, mashahidi wanapatikana? | Conditional | For conduct complaints requiring investigation |
| date_of_incident | Tarehe ya tukio | Yes | For investigation timeline |
| internal_complaint_raised | Je, malalamiko yamewahi kuwasilishwa ndani ya kanisa? | Recommended | Denominational oversight requires internal complaint first |
| desired_outcome | Matokeo unayotaka | Yes | Investigation / Financial refund / Leadership accountability / Mediation |

### CRITICAL: Child Protection / Sexual Misconduct Fields

**If any indication of sexual misconduct, child abuse, or exploitation by religious leadership:**
- `incident_type_safeguarding` — Aina ya tukio: Sexual exploitation / Child abuse / Grooming / Financial exploitation of vulnerable
- `victim_age_group` — Kundi la umri: Child under 18 / Adult — mandatory reporting applies for minors
- `immediate_safety_concern` — Je, mhusika yuko salama sasa hivi?
- **Escalate immediately: denominational safeguarding officer + police + DSW (for children)**

### Conditional Fields (collect based on issue type)

**If issue_type = Financial Misconduct (Tithe, Offering, Building Fund):**
Also collect:
- `fund_name` — Jina la mfuko: Zaka / Mchango wa ujenzi / Mfuko wa kanisa / Sadaka maalum
- `amount_contributed_tzs` — Kiasi kilichochangiwa (TZS)
- `total_fund_amount_tzs` — Jumla ya mfuko (kama inajulikana) (TZS)
- `financial_committee_exists` — Je, kamati ya fedha ya kanisa ipo? Yes / No
- `audited_accounts_available` — Je, hesabu za kanisa zimekaguliwa? Yes / No
- `church_constitution_financial_clause` — Je, katiba ya kanisa ina kifungu cha fedha?
- `other_members_sharing_concern` — Je, wanachama wengine wana wasiwasi huo huo? Yes / No

**If issue_type = Pastoral Misconduct:**
Also collect:
- `misconduct_type` — Aina ya makosa: Sexual / Financial exploitation / Verbal abuse / Favoritism / Doctrinal deception
- `duration_of_misconduct` — Muda wa makosa (kama yanajulikana): Isolated incident vs. ongoing pattern
- `previous_complaints_to_church` — Je, malalamiko yamewahi kuwasilishwa ndani ya kanisa? Yes / No
- `church_response_to_previous_complaints` — Jibu la kanisa kwa malalamiko ya awali

**If issue_type = Governance Dispute:**
Also collect:
- `governance_issue_type` — Aina ya tatizo la utawala: Unconstitutional election / Leadership removal without due process / Constitution violation
- `church_constitution_available` — Je, nakala ya katiba ya kanisa ipo? Yes / No
- `relevant_constitution_clause` — Kifungu cha katiba kinachohusika
- `general_meeting_called` — Je, mkutano mkuu uliombwa? Yes / No

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| CH-01 | financial_misappropriation | Tithe, offerings, or building fund misused by leadership |
| CH-02 | lack_financial_transparency | No financial reports provided to congregation |
| CH-03 | forced_giving | Members pressured or shamed into giving |
| CH-04 | pastoral_sexual_misconduct | Sexual exploitation or harassment by pastor/leader |
| CH-05 | child_abuse | Abuse of children in church settings |
| CH-06 | pastoral_verbal_abuse | Verbal abuse, humiliation, or intimidation by leader |
| CH-07 | favoritism_discrimination | Unfair treatment of members based on wealth, tribe, gender |
| CH-08 | governance_violation | Leadership violating church constitution or by-laws |
| CH-09 | unlawful_exclusion | Member excluded without due process |
| CH-10 | property_dispute | Church property dispute between factions |
| CH-11 | doctrinal_deception | Teachings that cause financial or psychological harm |
| CH-12 | service_quality | Poor worship experience; unqualified teachers; technical issues |
| CH-13 | spiritual_abuse | Manipulation, fear-based control, or spiritual coercion |
| CH-14 | registration_violation | Organization operating without proper registration |

### Resolution Standards

- **Church level:** Internal complaints should be heard by church elders or discipline committee within 30 days.
- **Denominational oversight:** Diocese, synod, or national council should investigate within 60 days.
- **BAKWATA (Islamic):** National Muslim Council handles complaints against mosques and imams; investigation within 60 days.
- **Police (criminal matters):** Sexual misconduct, child abuse, financial fraud — immediate police report.
- **DSW:** Child protection matters; immediate investigation.
- **PCCB:** If church funds involve public money or corruption with government — PCCB referral.
- **NGO Board:** If the organization is registered as an NGO — NGO Board complaint.
- **Required for escalation:** Organization name, denomination, leader's name and position, nature of complaint, date, witnesses.

### Escalation Triggers

- `issue_type = pastoral_sexual_misconduct` OR `child_abuse` — Immediate police + DSW + denominational safeguarding; mandatory reporting for children
- `issue_type = financial_misappropriation` AND significant amount — PCCB referral; denominational audit; police for criminal fraud
- `issue_type = doctrinal_deception` AND financial harm — Consumer protection complaint; PCCB if coercion involved; denominational review
- `issue_type = spiritual_abuse` AND psychological harm pattern — Denominational intervention; referral to mental health support services
- `issue_type = child_abuse` — IMMEDIATE: DSW + police; Child Act mandatory reporting; remove child from danger

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous fully accepted |
| church_name | Jina la kanisa | Recommended | For routing |
| denomination | Madhehebu | Recommended | For denominational routing |
| suggestion_category | Kategoria | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| CHS-01 | financial_transparency | Uwazi wa fedha za kanisa |
| CHS-02 | service_experience | Kuboresha huduma ya ibada |
| CHS-03 | youth_programs | Programu za vijana |
| CHS-04 | community_service | Kujihusisha na jamii |
| CHS-05 | accountability | Uwajibikaji wa viongozi |
| CHS-06 | child_safeguarding | Ulinzi wa watoto chuoni na kanisani |
| CHS-07 | women_inclusion | Ujumuishaji wa wanawake katika uongozi |
| CHS-08 | pastoral_care_quality | Huduma bora ya kichungaji |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina (hiari) | Optional | Anonymous accepted |
| denomination | Madhehebu | Conditional | For denominational queries |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| church_registration | Je, kanisa hili limesajiliwa? | church_name |
| complaint_process | Jinsi ya kulalamika dhidi ya kiongozi wa kanisa? | denomination |
| financial_rights | Haki zangu kuhusu hesabu za kanisa | denomination |
| child_protection_report | Jinsi ya kuripoti unyanyasaji wa mtoto kanisani? | denomination |
| bakwata_process | Mchakato wa BAKWATA wa malalamiko? | — |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| leader_name | Jina la kiongozi | Recommended | Recognition |
| church_name | Jina la kanisa | Yes | Routes to leadership |
| specific_aspect_praised | Kipengele | Yes | Mahubiri ya nguvu / Uwazi wa fedha / Huduma kwa maskini / Programu za vijana / Ujenzi wa jamii |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Congregational satisfaction |

---

## AI Conversation Guidance for This Industry

- **Religious organization complaints are sensitive.** Many complainants feel conflicted between their faith and their grievance. Acknowledge this: "Tunakuelewa hali hii inaweza kuwa vigumu kuzungumza — usalama na uadilifu wa jamii yako ndio muhimu zaidi."
- **For child abuse or sexual misconduct, mandatory escalation applies.** Do not allow religious sensitivity to delay reporting child abuse. "Ulinzi wa watoto ni wa kwanza — hii inahitaji kuripotiwa kwa polisi na Idara ya Ustawi wa Jamii, bila kujali hali ya kanisa."
- **For financial misconduct, establish whether financial reports are ever provided.** In many Tanzanian churches, lack of financial transparency is the root of most financial disputes. "Je, kanisa linatoa ripoti ya fedha kwa wanachama? Kama hapana, hiyo ni hatua ya kwanza ya kuomba."
- **For governance disputes, ask about the church constitution.** "Je, kanisa lina katiba iliyoandikwa? Ikiwa ndiyo, sheria hizo zinatoa njia ya kutatua mgongano huu."
- **Respect the belief system while addressing the complaint.** Never make comments that could be seen as disparaging religious beliefs. Focus on the organizational conduct, not the doctrine.
- **For pastoral misconduct, protect the complainant's identity.** Power dynamics in religious settings can create risk of retaliation. "Jina lako litashikiliwa kwa siri kabisa — tutashiriki maelezo tu yanayohitajika kwa uchunguzi."

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Church name | "Kanisa au taasisi ya dini inayohusika inaitwa nini? Madhehebu yake ni gani?" |
| Leader name | "Kiongozi anayehusika anaitwa nini? Na cheo chake ni nani — mchungaji, askofu, imamu?" |
| Fund name | "Mfuko wa fedha unaohusika unaitwa nini — zaka, mfuko wa ujenzi, sadaka maalum?" |
| Amount | "Kiasi kilichochangiwa na wanachama kwa mfuko huu ni kiasi gani kujua?" |
| Witnesses | "Je, wanachama wengine wana wasiwasi kama huo? Unaweza kutaja majina (hiari)?" |
| Internal complaint | "Je, umewahi kuleta tatizo hili kwa wazee wa kanisa au kamati? Jibu lao lilikuwa nini?" |
| Child safety | "Je, watoto wanaohusika wako salama sasa hivi? Hii ndio swali la kwanza la muhimu zaidi" |
| Membership status | "Wewe ni mwanachama wa kanisa hili, mgeni, au mtu wa jamii jirani?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | child_abuse OR pastoral_sexual_misconduct | IMMEDIATE: Police + DSW + denominational safeguarding; mandatory reporting |
| issue_type | financial_misappropriation AND significant | PCCB referral; denominational audit; police for criminal fraud |
| issue_type | spiritual_abuse AND pattern | Denominational intervention; mental health support referral |
| issue_type | registration_violation | Religious Organizations Registrar + NGO Board |
| issue_type | governance_violation AND constitution | Denominational council; constitution enforcement; mediation |
| internal_complaint_raised | Yes AND ignored by church | Denominational oversight body escalation; BAKWATA (Islamic) or diocese/synod (Christian) |
| issue_type | forced_giving AND public shaming | Denominational ethics complaint; community mediation |
| issue_type | property_dispute | Legal referral; potential Land Tribunal if property rights involved |

---

*Sources: Tanzania Religious Organizations Registration Act Cap. 39, Child Act Cap. 13, Prevention of Violence Against Women and Children Act 2022, PCCB Act Cap. 329, NGO Act Cap. 56, ISO 10002:2018, BAKWATA standards, TEC guidelines, KKKT disciplinary procedures*
