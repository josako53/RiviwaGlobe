---
tags: [industry-kb, field-standards, feedback-fields]
---
# Church / Religious Organizations — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: church, kanisa, mosque, msikiti, temple, hekalu, parish, diocese, dayosisi, congregation, mkutano wa ibada, pastor, mchungaji, bishop, askofu, imam, padre, reverend, father, deacon, shemasi, elder, mzee wa kanisa, worship leader, kiongozi wa ibada, sermon, mahubiri, tithe, zaka, offering, sadaka, church fund, mfuko wa kanisa, building fund, mfuko wa ujenzi, fellowship, ushirika, choir, kwaya, Sunday school, shule ya Jumapili, youth ministry, vijana wa kanisa, women's guild, umoja wa wanawake, cell group, kundi la nyumba, prayer meeting, mkutano wa maombi, baptism, ubatizo, wedding kanisani, burial service, mazishi, crusade, uamsho, church camp, kambi ya kanisa, denomination, madhehebu, synod, sinodi, conference ya kanisa, mkutano mkuu, church constitution, katiba ya kanisa, church welfare, ustawi wa kanisa, Pentecostal, Catholic, Anglican, Lutheran, Seventh Day Adventist, Baptist, KKKT, TEC, PAWATA, CHADEMA ya dini, Umoja wa Makanisa Tanzania

## Why Industry-Specific Fields Matter

Generic feedback fields cannot distinguish between financial misconduct by clergy (requiring denomination oversight body notification and potential IRS/regulatory referral), sexual misconduct by a spiritual leader (requiring safeguarding authority notification and victim support protocols), and a doctrinal or governance dispute (requiring denomination-specific dispute resolution channels) — all requiring fundamentally different escalation paths, different oversight bodies, and different sensitivity levels. Without religion-specific fields, the AI cannot route safely, protect complainant confidentiality, or identify mandatory safeguarding reporting triggers.

## Source Standards

- LegalClarity: How to File a Complaint Against a Church (complaint field model)
- Church Society Complaint Form (UK, July 2020) — witness and evidence field structure
- FaithTrust Institute: Responding to Spiritual Leader Misconduct Handbook (2022)
- United Methodist Church (UMC) Complaint Process (chargeable offenses framework)
- Presbyterian Church (U.S.A.) Make a Report Process (presbytery routing model)
- Tanzania Registrar of Societies (registration and accountability framework for religious organizations)
- Tanzania Child Act Cap 13 RE 2019 (mandatory reporting for child safeguarding)
- US State Department 2022 Report on International Religious Freedom: Tanzania (denominational context)
- Tanzania Societies Act (Cap 337) — oversight of registered religious societies

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| `complainant_name` | Jina la mlalamikaji (hiari) | Optional | LegalClarity and Church Society form both allow anonymous submission; do not require name upfront — many complainants fear retaliation or spiritual shaming |
| `anonymous_flag` | Je, unataka kubaki bila jina? | Yes | FaithTrust emphasizes confidentiality protection; UNHCR CFM principle applied; collect upfront before any identifying questions |
| `complainant_relationship_to_organization` | Uhusiano wako na kanisa / dhehebu | Yes | Church Society form: member / visitor / employee / former member / external party — determines standing and complaint pathway |
| `organization_name` | Jina la kanisa / msikiti / shirika la kidini | Yes | LegalClarity: "Organization name and location"; required to route complaint to correct denomination oversight body |
| `branch_or_congregation_name` | Jina la tawi / mkutano maalum | Yes | Presbyterian model: complaint routes to specific presbytery; UMC routes to district superintendent of the specific congregation |
| `denomination_or_faith_tradition` | Madhehebu / Imani | Yes | Determines which oversight body has jurisdiction — UMC District Superintendent, PCUSA Stated Clerk, Catholic Bishop's office, KKKT Synod, Anglican Diocese, etc. |
| `denominational_oversight_body` | Chombo cha juu cha dhehebu / mamlaka ya kidini | Recommended | LegalClarity: identifies the escalation body; UMC uses district superintendent; PCUSA uses stated clerk of presbytery |
| `leader_or_perpetrator_name_and_role` | Jina na wadhifa wa kiongozi / mhusika | Conditional | LegalClarity: "Leadership/staff involved"; FaithTrust: identifies perpetrator's position — Pastor / Bishop / Deacon / Finance Officer / Youth Leader; collect only if complainant is willing to name |
| `issue_type` | Aina ya tatizo | Yes | LegalClarity, FaithTrust, UMC, PCUSA all categorize by issue type to determine appropriate oversight body and complaint procedure |
| `issue_description` | Maelezo ya tatizo | Yes | LegalClarity: "detailed description of events"; Church Society form requires chronological narrative |
| `date_of_incident` | Tarehe (au kipindi) cha tukio | Yes | LegalClarity: "specific dates, times, and locations"; UMC limitation: complaint must be filed within one year of the alleged breach |
| `location_of_incident` | Mahali pa tukio (jengo la kanisa, nyumbani, mtandaoni) | Yes | LegalClarity: location is required for investigation; distinguishes whether incident occurred on church premises |
| `witness_names_and_contacts` | Majina na mawasiliano ya mashahidi | Recommended | Church Society form: witness names required; LegalClarity: "names and contact details of witnesses" |
| `prior_internal_approach` | Je, umeshajaribu kupitia njia za ndani za kanisa? | Yes | LegalClarity: notes internal resolution attempts; FaithTrust: recommends internal first step as standard process; required for escalation eligibility |
| `internal_response_received` | Jibu la ndani lililopo (kama lipo) | Conditional | LegalClarity: "chronological account of what internal channels were attempted"; needed to assess readiness for external escalation |
| `supporting_evidence` | Ushahidi wa kusaidia | Recommended | LegalClarity: "emails, texts, letters, financial records, contracts, internal policies, photographs" |
| `other_authorities_notified` | Je, mamlaka nyingine zimetaarifu? | Recommended | LegalClarity: police / social services / IRS equivalent / EEOC; Tanzania equivalent: police / MoHCDGEC / Registrar of Societies |
| `preferred_anonymity_level` | Kiwango cha siri unachotaka | Yes | FaithTrust emphasizes confidentiality options; identify whether complainant wants name protected even from the denomination body |

### Conditional Fields (collect based on issue type)

**If `issue_type = financial_misconduct`:**
Also collect:
- `nature_of_financial_misconduct` — Aina ya ubadhilifu wa fedha: Misappropriation / embezzlement / fraudulent fundraising / unauthorized spending
- `amount_misappropriated_tzs` — Kiasi kilichochukuliwa vibaya (TZS): Quantifies financial harm for Tanzania Registrar of Societies and PCCB referral
- `financial_period_affected` — Kipindi cha fedha kilichoathirika (mwaka / msimu): For audit trail
- `church_fund_type` — Aina ya mfuko uliohusika: Tithes / building fund / welfare fund / school fees / general offering
- `audit_conducted` — Je, ukaguzi wa hesabu umefanyika? Yes/No: Establishes whether internal financial controls were applied
- `transaction_records_available` — Je, kuna rekodi za malipo / stakabadhi? Yes/No: Required for financial investigation

**If `issue_type = sexual_misconduct` OR `sexual_abuse_of_minor`:**
Also collect:
- `victim_relationship_to_perpetrator` — Uhusiano wa mwathirika na mkosaji: Congregant / staff member / child in ministry / spouse / counselee
- `victim_age_category` — Kikundi cha umri wa mwathirika: Adult / Minor (chini ya miaka 18): Minor triggers mandatory reporting under Tanzania Child Act Cap 13
- `ongoing_access_flag` — Je, mkosaji bado ana upatikanaji wa wathirika wanaowezekana? Yes/No: Immediate safeguarding concern if Yes
- `previous_complaints_to_denomination` — Je, malalamiko ya awali yalipelekwa kwa dhehebu? Yes/No: Pattern of repeat misconduct escalates severity
- `counseling_support_needed` — Je, mwathirika anahitaji msaada wa kisaikolojia? Yes/No: FaithTrust: support referral is a best practice response step

**If `issue_type = child_safeguarding_failure`:**
Also collect:
- `child_age` — Umri wa mtoto: Mandatory for Child Act classification
- `child_location` — Mahali alipo mtoto sasa: For immediate safety assessment
- `alleged_perpetrator_role` — Wadhifa wa mdaiwa mkosa: Ministry leader / Sunday school teacher / youth worker / parent
- `immediate_danger_flag` — Je, mtoto yuko hatarini sasa hivi? Yes/No: Triggers emergency escalation if Yes

**If `issue_type = financial_misconduct` AND amount > 5,000,000 TZS:**
Also collect:
- `pccb_referral_warranted` — Je, kesi hii inastahili kupelekwa PCCB? Yes/No: Anti-corruption bureau referral threshold
- `registrar_of_societies_notification` — Je, Msajili wa Mashirika atataarifu? Yes/No: Tanzania Societies Act requires religious organizations to maintain financial accountability

**If `issue_type = property_dispute`:**
Also collect:
- `property_description` — Maelezo ya mali inayohusika: Land / building / vehicles / equipment
- `ownership_documentation` — Je, kuna hati za umiliki? Yes/No
- `dispute_nature` — Aina ya mgogoro: Unauthorized sale / lease without consent / encroachment / title transfer fraud

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| CR-01 | `financial_misconduct` | Misappropriation of tithes/offerings, embezzlement, fraudulent fundraising |
| CR-02 | `sexual_misconduct_adult` | Sexual misconduct by clergy/leader against an adult |
| CR-03 | `sexual_abuse_of_minor` | Any sexual conduct involving a minor by clergy or ministry worker |
| CR-04 | `physical_abuse` | Physical assault or corporal punishment by clergy or staff |
| CR-05 | `discrimination` | Race, gender, ethnicity, or disability discrimination within religious community |
| CR-06 | `false_doctrine` | Teaching considered heretical, harmful, or fraudulent spiritual claims |
| CR-07 | `property_dispute` | Unauthorized sale, lease, or misuse of church/mosque property |
| CR-08 | `pastoral_negligence` | Abandonment of pastoral duty, failure to respond to congregation needs |
| CR-09 | `spiritual_abuse` | Coercive control, manipulation of spiritual authority, cult-like behavior |
| CR-10 | `child_safeguarding_failure` | Failure to protect children in ministry from abuse or harm |
| CR-11 | `governance_dispute` | Unconstitutional election, unauthorized leadership change, violation of church constitution |
| CR-12 | `harassment_bullying` | Psychological harassment or bullying by leader or congregation members |
| CR-13 | `communication_failure` | Lack of transparency about church decisions, finances, or programs |
| CR-14 | `fraud_impersonation` | False claims of denominational affiliation, fake ministry credentials |

### Resolution Standards for This Industry

- **Internal (first step):** LegalClarity and FaithTrust recommend approaching church leadership first (if safe to do so); document the response or non-response.
- **Denominational body (second step):** UMC — file with district superintendent who forwards to bishop; PCUSA — file with Stated Clerk of the complainant's presbytery; Anglican/TEC — file with bishop of the diocese; KKKT — file with Synod Council; Catholic — file with diocesan bishop's office.
- **Tanzania Registrar of Societies:** Religious societies registered under Tanzania Societies Act (Cap 337) are accountable to the Registrar for financial misconduct and governance failures; formal complaint can be lodged with the Registrar.
- **PCCB (Prevention and Combating of Corruption Bureau):** For financial misconduct involving public-facing fundraising or misappropriation above significant thresholds.
- **Police:** For criminal matters — sexual assault, physical violence, large-scale financial fraud.
- **Child protection (mandatory):** Tanzania Child Act Cap 13 requires immediate notification of social welfare authorities for any report of child abuse; 24-hour response standard for immediate danger.
- **Timeline:** Denominational processes vary widely; LegalClarity advises documenting all responses and non-responses; no universal statutory timeline applies in Tanzania for internal church dispute resolution.

### Escalation Triggers (field values that require immediate escalation)

- `issue_type = sexual_abuse_of_minor` OR `child_safeguarding_failure` AND `victim_age_category = Minor` — Mandatory report to police and MoHCDGEC Social Welfare within 24 hours; do not delay to collect additional fields; child safety overrides all other considerations
- `issue_type = sexual_abuse_of_minor` AND `ongoing_access_flag = Yes` — Emergency; alleged perpetrator still has access to children; immediate notification to church authority AND police
- `issue_type = sexual_misconduct_adult` AND `previous_complaints_to_denomination = Yes` — Pattern of repeat conduct; escalate to senior denomination leadership and police; document prior complaint history
- `issue_type = spiritual_abuse` AND description includes coercive control or isolation — High-control group indicators; escalate to mental health referral and family notification if person is isolated
- `issue_type = financial_misconduct` AND `amount_misappropriated_tzs > 5000000` — Escalate to PCCB and Tanzania Registrar of Societies; financial fraud at scale
- `issue_type = financial_misconduct` AND involves fraudulent public fundraising — Tanzania FCC and Registrar of Societies referral; consumer protection dimension
- `immediate_danger_flag = Yes` (any issue type) — Emergency priority ticket; provide police number (112) immediately

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `submitter_name` | Jina la mtoa maoni (hiari) | Optional | Many suggestions will be anonymous; do not require identification |
| `organization_or_branch` | Kanisa / Tawi / Dhehebu | Yes | Routes suggestion to correct leadership level |
| `suggestion_category` | Kategoria ya mapendekezo | Yes | Enables systematic routing and thematic analysis |
| `suggestion_detail` | Maelezo ya mapendekezo | Yes | Free text; core content |
| `complainant_relationship_to_organization` | Uhusiano na kanisa | Recommended | Member / visitor / community member — context shapes suggestion weight |

### Industry-Specific Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| CRS-01 | `financial_transparency` | Uwazi wa fedha za kanisa |
| CRS-02 | `safeguarding_child_protection` | Kulinda watoto na watu walio hatarini |
| CRS-03 | `governance_accountability` | Utawala bora na uwajibikaji wa uongozi |
| CRS-04 | `pastoral_care_quality` | Ubora wa huduma ya kichungaji |
| CRS-05 | `community_programs` | Mipango ya huduma kwa jamii |
| CRS-06 | `inclusion_and_belonging` | Ushirikiano na kukubalika kwa wote |
| CRS-07 | `communication_transparency` | Uwazi wa mawasiliano ya uongozi |
| CRS-08 | `youth_ministry` | Huduma ya vijana |
| CRS-09 | `property_management` | Usimamizi wa mali za kanisa |
| CRS-10 | `doctrinal_clarity` | Uwazi wa mafundisho |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `inquirer_name` | Jina la mwulizaji (hiari) | Optional | Not required for general inquiries |
| `inquiry_type` | Aina ya swali | Yes | Routes to correct knowledge base |
| `organization_name` | Kanisa / Dhehebu inayohusika | Recommended | For organization-specific inquiries |
| `preferred_response_channel` | Njia unayopendelea ya jibu | Yes | SMS / Simu / WhatsApp / Ana kwa ana |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Swahili | Additional Fields Needed |
|-------------|---------|--------------------------|
| `membership_process` | Jinsi ya kujiunga na kanisa | `organization_name`, `denomination` |
| `financial_records_request` | Kuomba rekodi za fedha za kanisa | `organization_name`, `financial_period_affected` |
| `doctrine_question` | Swali kuhusu mafundisho | `denomination_or_faith_tradition`, `specific_doctrine_topic` |
| `complaint_process_guidance` | Jinsi ya kuwasilisha malalamiko | `denomination_or_faith_tradition` |
| `referral_to_authority` | Kupelekwa kwa mamlaka ya juu ya dhehebu | `organization_name`, `denomination_oversight_body` |
| `registrar_of_societies_status` | Je, kanisa hili limesajiliwa? | `organization_name` |
| `counseling_referral` | Mahali pa kupata msaada wa kisaikolojia | `location_district`, urgency level |
| `program_information` | Maelezo ya mpango / shughuli maalum | `organization_name` |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `submitter_name` | Jina la mtoa pongezi (hiari) | Optional | For acknowledgement; not required |
| `leader_or_program_recognized` | Kiongozi / Mpango / Huduma inayopongezwa | Yes | Routes compliment to correct leadership for recognition |
| `role_of_person_recognized` | Wadhifa wa mtu anayepongezwa | Recommended | Pastor / Bishop / Deacon / Youth leader / Choir / Women's guild / Program |
| `what_was_impactful` | Kilichokuwa na athari nzuri | Yes | Specific behavior, ministry, or program that made a positive difference |
| `date_or_event_context` | Tarehe / Muktadha (tukio, ibada, nk) | Recommended | For correlation with specific ministry moments |
| `impact_on_life_or_community` | Athari kwa maisha yako / jamii | Recommended | Captures testimony and community impact for ministry reporting |

---

## AI Conversation Guidance for This Industry

- **Establish anonymity before anything else — and mean it.** Many people bringing religious complaints face real risks of social ostracism, spiritual shaming, or loss of community. Begin every complaint conversation with: "Unaweza kushiriki hili bila kutaja jina lako — chaguo ni lako." Then honor that choice completely — never circle back to ask for a name after anonymity is established.
- **Do not ask for the perpetrator's name as a first question.** Ask about the issue type and general description first. If the complainant is ready to name the person, they will. For sensitive issues (sexual misconduct, financial fraud), the name often comes naturally once trust is established; demanding it early causes abandonment.
- **For child safeguarding signals, pivot immediately to child safety.** If any detail suggests a minor may be at risk, ask "Je, mtoto huyu yuko salama sana hivi sasa?" and provide emergency contacts (police: 112, social welfare) before continuing the complaint form. The Tanzania Child Act imposes mandatory reporting; frame this to the complainant as a way to protect the child, not as adversarial.
- **Distinguish the denomination from the congregation.** The complainant's individual congregation and the broader denomination hierarchy are separate — and the oversight body that can act is usually the denomination, not the local congregation leadership (who may be the subject of the complaint). Ask "Ni dhehebu gani kanisa hili linahusiana nazo — KKKT, TEC, Kikatoliki, Pentecostal, au nyingine?" to identify the correct escalation body.
- **For financial misconduct, ask about the fund type before the amount.** Say "Hii inahusiana na mfuko gani — zaka za kawaida, mfuko wa ujenzi, msaada wa familia, au mwingine?" — the fund type determines what governance rules apply and which financial records should exist.
- **Never minimize spiritual harm or pressure the complainant to reconcile.** Phrases like "Lakini ni kanisa..." or prompts to "forgive and forget" are inappropriate from the AI. The AI's role is to document, route, and escalate — not to provide theological advice or discourage the complaint.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Anonymity | "Je, unataka kubaki bila jina? Unaweza kuendelea bila kutaja jina lako na malalamiko yako yatashughulikiwa kwa usiri." |
| Organization name | "Jina la kanisa / msikiti / shirika hilo ni nini, na liko wapi?" |
| Denomination | "Ni madhehebu gani kanisa hili linahusiana nazo — KKKT, TEC, Kikatoliki, Pentekoste, au nyingine?" |
| Relationship | "Je, wewe ni mwanachama wa kanisa hili, mgeni, mfanyakazi, au una uhusiano mwingine?" |
| Issue type | "Tatizo lako linahusiana na nini hasa — fedha, mwenendo wa kiongozi, kulindwa kwa watoto, umiliki wa mali, au kitu kingine?" |
| Date of incident | "Hili lilitokea lini — ni wakati gani kwa kadri unavyokumbuka?" |
| Internal attempt | "Je, umeshajaribu kuwasiliana na uongozi wa kanisa kuhusu tatizo hili? Walikusema nini au walifanya nini?" |
| Child safety | "Je, mtoto huyu yuko salama sana hivi sasa, au kuna hatari ya haraka?" |
| Evidence | "Je, una barua pepe, ujumbe, stakabadhi za fedha, au nyaraka nyingine zinazohusiana na tatizo hili?" |
| Desired outcome | "Unataka nini kitokee — uchunguzi, mabadiliko ya uongozi, kurejesheewa fedha, au kitu kingine?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| `issue_type` | `sexual_abuse_of_minor` | Mandatory police and MoHCDGEC Social Welfare notification within 24 hours; child safety assessment immediately; do not delay |
| `issue_type` | `child_safeguarding_failure` AND `immediate_danger_flag = Yes` | Emergency escalation; police (112); child protection services; create emergency priority ticket |
| `issue_type` | `sexual_misconduct_adult` AND `ongoing_access_flag = Yes` | Notify senior denomination leadership AND police; prevent continued access to potential victims |
| `issue_type` | `financial_misconduct` AND `amount_misappropriated_tzs > 5000000` | Refer to PCCB and Tanzania Registrar of Societies; financial fraud at scale |
| `issue_type` | `spiritual_abuse` AND description includes isolation or coercive control | Mental health referral; high-control group safeguarding protocol; family notification if appropriate |
| `issue_type` | `governance_dispute` | Route to denomination oversight body (Synod / Presbytery / Diocese / District Superintendent) |
| `prior_internal_approach` | Yes AND `internal_response_received = None` | Advise escalation to denominational body; provide oversight body contact; document non-response |
| `anonymous_flag` | Yes | Never request identifying details; protect anonymity throughout; assign system reference only |
| `issue_type` | `fraud_impersonation` | Verify denomination affiliation with Tanzania Registrar of Societies; advise complainant to avoid financial engagement until verified |
| `other_authorities_notified` | None AND `issue_type` is criminal | Advise police report; for child matters: mandatory even if complainant is reluctant |

---

*Sources: LegalClarity How to File a Complaint Against a Church, Church Society Complaint Form (UK 2020), FaithTrust Institute Responding to Spiritual Leader Misconduct Handbook (2022), United Methodist Church Complaint Process, Presbyterian Church (U.S.A.) Make a Report, Tanzania Registrar of Societies (Societies Act Cap 337), Tanzania Child Act Cap 13 RE 2019, US State Department 2022 Report on International Religious Freedom Tanzania*
