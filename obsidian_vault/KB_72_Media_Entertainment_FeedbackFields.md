---
tags: [industry-kb, field-standards, feedback-fields, media, entertainment]
---
# Media / Entertainment — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: media, habari, news, gazeti, newspaper, televisheni, television, redio, radio, online media, mtandaoni, blog, podcast, YouTube, social media, mitandao ya kijamii, journalist, mwandishi wa habari, reporter, mwandishi, editor, mhariri, station, kituo cha televisheni, TV station, radio station, kituo cha redio, ITV, TBC, Star TV, Azam TV, Clouds TV, NTV, Channel Ten, Millard Ayo, Radio Uhuru, Radio Free Africa, BBC Swahili, VOA Swahili, Clouds FM, East Africa Radio, TBC FM, content, maudhui, false news, habari za uongo, defamation, kashfa, libel, chongo cha maandishi, slander, kashfa ya maneno, privacy, faragha, broadcast, matangazo, advertisement, tangazo, advertiser, mtangazaji, TCRA, Tanzania Communications Regulatory Authority, MCT, Media Council of Tanzania, COSOTA, copyright, hakimiliki, censorship, ukandamizaji, fake news, habari bandia, hate speech, maneno ya chuki, incitement, uchochezi, content removal, kuondoa maudhui, right of reply, haki ya kujibu, press freedom, uhuru wa habari, rating, tathmini

## Why Industry-Specific Fields Matter

Media complaints span defamation (requiring article/broadcast reference, specific false statement, harm to reputation), copyright infringement (requiring COSOTA registration reference), false news (requiring verifiable factual errors), privacy violations (requiring specific personal information published without consent), and harmful content (requiring content description and broadcast reference). Each requires a different regulatory response: MCT handles press standards complaints, TCRA handles broadcast licensing violations, and police handle criminal defamation. Without media-specific fields, the AI cannot generate an MCT-compliant complaint or separate a copyright dispute from a defamation claim.

## Source Standards

- Tanzania Media Services Act 2016 — media regulation and MCT
- Media Council of Tanzania (MCT) Code of Ethics and Professional Conduct
- TCRA Electronic and Postal Communications Act, Cap. 306 — broadcasting licensing
- COSOTA Act — Copyright Society of Tanzania
- Copyright and Neighbouring Rights Act, Cap. 218
- Tanzania Communications Regulatory Authority Act, Cap. 172
- Penal Code, Cap. 16 — criminal defamation provisions
- Data Protection (Personal Data) Act (emerging) — privacy in media
- Advertising Standards Authority of Tanzania — advertising ethics
- ISO 10002:2018 — complaints handling
- African Charter on Human and Peoples' Rights — press freedom principles
- UNESCO Journalists' Safety Indicators

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL media complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | MCT complaint form; defamation cases require named complainant |
| complainant_phone | Nambari ya simu | Yes | Status updates |
| complainant_email | Barua pepe | Recommended | MCT and TCRA communicate via email |
| media_outlet_name | Jina la chombo cha habari | Yes | Routes to MCT/TCRA licensing check |
| media_type | Aina ya media | Yes | Newspaper / TV / Radio / Online / Social Media |
| journalist_or_author_name | Jina la mwandishi / mhariri | Conditional | For professional conduct complaints |
| publication_broadcast_date | Tarehe ya kuchapishwa / kutangazwa | Yes | For defamation limitation period and investigation |
| content_reference | Kichwa cha habari / Nambari ya kipindi | Yes | Enables MCT/TCRA to retrieve the specific content |
| content_url | Kiungo cha mtandao (kama kipo) | Conditional | For online media; enables direct content access |
| issue_type | Aina ya tatizo | Yes | MCT/TCRA complaint taxonomy |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; specific identification of the offending content |
| specific_false_statement | Taarifa ya uongo mahususi (kama ni defamation) | Conditional | Required for defamation complaints; general dissatisfaction is not actionable |
| harm_caused | Madhara yaliyotokea | Conditional | Reputational / Financial / Psychological — for damages assessment |
| right_of_reply_sought | Je, haki ya kujibu iliombwa? | Recommended | MCT code requires media to provide right of reply before complaint |
| evidence_available | Ushahidi unaopatikana | Yes | Screenshot / Recording / Publication copy |
| desired_outcome | Matokeo unayotaka | Yes | Retraction / Apology / Damages / Content removal / Disciplinary action |

### Conditional Fields (collect based on issue type)

**If issue_type = Defamation (Libel / Slander):**
Also collect:
- `defamatory_statement_verbatim` — Taarifa ya kashfa kwa maneno halisi: MCT requires specific statement, not general description
- `statement_falseness_evidence` — Ushahidi wa uongo wa taarifa: Documentary / Witness / Official record
- `audience_size_estimate` — Ukubwa wa hadhira: National broadcast vs. local; affects damages assessment
- `prior_relationship_with_outlet` — Je, kuna historia ya hapo awali na chombo hiki?: Context for malice assessment
- `criminal_complaint_filed` — Je, malalamiko ya jinai yamewasilishwa?: Penal Code criminal defamation route

**If issue_type = Privacy Violation:**
Also collect:
- `private_information_published` — Taarifa ya faragha iliyochapishwa: Name / Photo / Address / Medical / Financial
- `consent_given_for_publication` — Je, idhini ya kuchapisha ilitolewa? Yes / No
- `harm_from_privacy_breach` — Madhara ya uvunjifu wa faragha: Job loss / Family harm / Safety risk / Emotional harm

**If issue_type = Copyright Infringement:**
Also collect:
- `original_work_description` — Maelezo ya kazi ya asili: Article / Photo / Video / Music / Book
- `cosota_registration_number` — Nambari ya usajili wa COSOTA: Strengthens copyright claim
- `infringing_use_description` — Jinsi kazi ilivyotumiwa bila idhini: Published / Broadcast / Used without credit
- `licensing_offered_refused` — Je, leseni iliombwa na kukataliwa? Yes / No

**If issue_type = False/Misleading News:**
Also collect:
- `false_claim_verbatim` — Dai la uongo kwa maneno halisi
- `correct_information` — Taarifa sahihi: What is the true version of events?
- `source_of_correct_information` — Chanzo cha taarifa sahihi: Official record / Expert / Personal knowledge
- `impact_of_false_news` — Athari ya habari za uongo: Public panic / Reputational damage / Business harm

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| ME-01 | defamation_libel | False written/published statements damaging reputation |
| ME-02 | defamation_slander | False broadcast/spoken statements damaging reputation |
| ME-03 | privacy_violation | Personal information published without consent |
| ME-04 | false_news | Factually incorrect reporting causing harm |
| ME-05 | hate_speech | Content inciting hatred against a group |
| ME-06 | copyright_infringement | Work used without permission or credit |
| ME-07 | biased_reporting | Partial, unfair, or politically manipulated reporting |
| ME-08 | misleading_advertising | False or misleading advertisement broadcast/published |
| ME-09 | harmful_content_children | Content inappropriate for children broadcast without watershed |
| ME-10 | right_of_reply_refused | Media refused to publish complainant's response |
| ME-11 | journalist_harassment | Journalist harassed, threatened, or silenced |
| ME-12 | unlicensed_broadcasting | Broadcasting without TCRA license |
| ME-13 | incitement | Content inciting violence or civil unrest |
| ME-14 | obscene_content | Obscene or pornographic content broadcast/published |

### Resolution Standards

- **MCT (Media Council of Tanzania):** Complaints acknowledged within 7 days; mediation offered; formal adjudication within 60 days; remedies include retraction, apology, and right of reply.
- **TCRA (broadcasting):** Licensing violations investigated within 30 days; TCRA can suspend or revoke broadcasting license.
- **Right of reply:** MCT Code requires media to offer right of reply before formal complaint; MCT complainant should demonstrate this was sought.
- **Criminal defamation:** Penal Code Cap. 16; police report; DPP prosecution.
- **COSOTA (copyright):** Civil claim; copyright infringement disputes through courts; COSOTA assists in negotiation.
- **Limitation period:** Civil defamation claims — 12 months from publication; criminal — varies.

### Escalation Triggers

- `issue_type = hate_speech` OR `incitement` — Immediate TCRA + police; potential criminal prosecution; public order concern
- `issue_type = harmful_content_children` AND broadcast in daytime — TCRA immediate complaint; broadcasting license violation
- `issue_type = defamation` AND public official/falsity confirmed — MCT formal complaint + potential criminal defamation referral to police
- `issue_type = journalist_harassment` AND violence/threats — Police report; MCT journalist safety protocol; international press freedom organizations (CPJ, RSF)
- `issue_type = unlicensed_broadcasting` — TCRA enforcement; criminal matter
- `issue_type = false_news` AND caused public panic — TCRA + MCT immediate; potential police referral for public disorder

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted |
| media_outlet | Chombo cha habari | Recommended | For routing |
| media_type | Aina ya media | Yes | Routes to correct team |
| suggestion_category | Kategoria | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| MES-01 | accuracy | Usahihi wa habari |
| MES-02 | balanced_reporting | Taarifa zenye usawa |
| MES-03 | local_content | Maudhui zaidi ya ndani ya nchi |
| MES-04 | children_content | Maudhui bora kwa watoto |
| MES-05 | privacy_protection | Ulinzi bora wa faragha |
| MES-06 | journalist_safety | Usalama wa waandishi wa habari |
| MES-07 | anti_corruption_reporting | Uandishi bora wa habari za ufisadi |
| MES-08 | digital_literacy | Elimu ya kutofautisha habari za uongo |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina | Recommended | For tracking |
| media_outlet | Chombo cha habari | Conditional | For outlet-specific queries |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| mct_complaint_process | Jinsi ya kulalamika dhidi ya chombo cha habari? | media_outlet |
| right_of_reply | Jinsi ya kupata haki ya kujibu katika gazeti? | media_outlet, article_reference |
| copyright_protection | Jinsi ya kulinda kazi yangu dhidi ya wizi | work_type |
| tcra_license_check | Je, kituo hiki kina leseni ya TCRA? | media_outlet_name |
| false_news_reporting | Jinsi ya kuripoti habari za uongo? | platform, content_url |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| journalist_name | Jina la mwandishi | Recommended | Journalist recognition |
| media_outlet | Chombo cha habari | Yes | Routes to editor |
| specific_aspect_praised | Kipengele | Yes | Uandishi sahihi / Ubunifu / Ujasiri / Usawa wa taarifa / Ulinzi wa faragha |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Media quality benchmarking |

---

## AI Conversation Guidance for This Industry

- **Defamation complaints require specificity.** The AI must collect the exact false statement, not just a general description. "Taarifa ya uongo mahususi iliyochapishwa ilikuwa gani hasa — maneno yaliyoandikwa au kusemwa?"
- **Ask about the right of reply first.** MCT requires complainants to have sought a right of reply before filing a formal complaint. "Je, ulimwandikia mhariri na kuomba nafasi ya kujibu habari hiyo? Jibu lao lilikuwa nini?"
- **For online content, get the URL immediately.** Online content can be removed or changed; preserving the URL and a screenshot is critical evidence. "Je, una kiungo cha mtandao (URL) cha maudhui hayo? Na unaweza kupiga screenshot na kuihifadhi?"
- **For copyright complaints, ask about COSOTA registration.** While unregistered works are still protected, COSOTA registration strengthens the claim. "Je, kazi yako imesajiliwa na COSOTA? Kama ndiyo, una nambari ya usajili?"
- **For hate speech or incitement, prioritize TCRA and police escalation.** These are public order matters. "Maudhui ya uchochezi au maneno ya chuki yanastahili taarifa ya haraka kwa TCRA na polisi."
- **Do not assess whether a statement is defamatory.** That is a legal determination. Route the complaint properly and advise the complainant to seek legal counsel. "Tathmini ya kisheria ya kashfa inahitaji mwanasheria — ninaweza kukusaidia kupeleka lalamiko lako kwa MCT au polisi."

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Media outlet | "Chombo cha habari kinachohusika kinaitwa nini — gazeti, kituo cha TV, redio, au tovuti?" |
| Article/broadcast | "Kichwa cha habari au kipindi kinachohusika kinaitwa nini? Na tarehe ya kuchapishwa / kutangazwa?" |
| False statement | "Taarifa ya uongo mahususi iliyochapishwa / kusemwa ilikuwa gani hasa — maneno yenyewe?" |
| Proof of falseness | "Una ushahidi gani unaoonyesha taarifa hiyo ni ya uongo — hati rasmi, mashahidi, au kumbukumbu?" |
| Right of reply | "Je, ulimwandikia mhariri au kutuma ombi la haki ya kujibu? Jibu lao lilikuwa nini?" |
| URL | "Je, maudhui hayo yanapatikana mtandaoni? Kiungo cha mtandao (URL) ni kipi?" |
| Harm caused | "Madhara yaliyotokea kutokana na maudhui hayo ni gani — kiuchumi, kiafya, au kwa sifa yako?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| issue_type | hate_speech OR incitement | Immediate TCRA + police; public order concern; criminal prosecution possible |
| issue_type | harmful_content_children AND daytime broadcast | TCRA complaint; broadcasting license violation |
| issue_type | journalist_harassment AND violence | Police report + MCT journalist safety protocol + international organizations (CPJ, RSF) |
| issue_type | unlicensed_broadcasting | TCRA enforcement; criminal matter under Communications Act |
| issue_type | false_news AND public panic caused | TCRA + MCT immediate; police if public disorder |
| right_of_reply_sought | No | Advise to seek right of reply from media outlet before MCT formal complaint |
| issue_type | copyright_infringement | COSOTA assistance; civil court for damages; cease and desist letter |
| issue_type | defamation AND verified false statement | MCT formal complaint; legal counsel for civil or criminal defamation |

---

*Sources: Tanzania Media Services Act 2016, MCT Code of Ethics, TCRA Act Cap. 172, Copyright and Neighbouring Rights Act Cap. 218, COSOTA Act, Penal Code Cap. 16, ISO 10002:2018, African Charter on Human and Peoples' Rights*
