---
tags: [industry-kb, field-standards, feedback-fields]
---
# Media / Entertainment — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: TV station, radio station, newspaper, gazeti, online media, habari mtandaoni, journalist, mwandishi wa habari, reporter, editor, mhariri, TBC (Tanzania Broadcasting Corporation), Mwananchi, Nipashe, The Citizen, Jamhuri, Uhuru, ITV Tanzania, Clouds TV, Star TV, Azam TV, Wasafi TV, Channel Ten, Bongo Flava, Bongo Movie, musician, msanii, artiste, record label, lebo ya muziki, streaming, YouTube, TikTok, Instagram, advertising agency, shirika la matangazo, content creator, muundaji wa maudhui, podcast, film production, uzalishaji wa filamu, COSOTA (Copyright Society of Tanzania), TCRA (Tanzania Communications Regulatory Authority), MCT (Media Council of Tanzania), defamation, kashfa, libel, mashtaka ya uongo, fake news, habari za uongo, hate speech, chuki, copyright violation, royalties, maudhui haramu, unyanyasaji mtandaoni, kuchafua jina, DSTV, StarTimes, satellite, decoder, media complaint, malalamiko ya habari

## Why Industry-Specific Fields Matter

Generic feedback fields cannot distinguish between a defamation complaint against a newspaper (requiring article URL, publication date, and MCT escalation pathway), a hate speech complaint against a TV broadcaster (requiring TCRA GN 203 complaints committee process with 30-day operator-first rule), and a copyright royalties dispute with a record label (requiring COSOTA registration details and TCRA content regulations) — all requiring different regulatory bodies (MCT, TCRA, COSOTA), different evidence standards, and different legal bases under Tanzania's Electronic and Postal Communications Act (EPOCA) and the Media Services Act 2016. Without media-specific fields, the AI cannot route complaints accurately or flag content that triggers mandatory TCRA or MCT notification.

## Source Standards

- Media Council of Tanzania (MCT) complaint procedures and Code of Ethics
- TCRA Complaints Committee Rules 2018 (GN No. 203)
- TCRA Electronic and Postal Communications (Online Content) Regulations analysis (MCT 2020)
- MCT Code of Ethics (Scribd — Tanzania ethical journalism standards)
- Tanzania Media Services Act 2016
- Tanzania Electronic and Postal Communications Act (EPOCA) 2010
- PBS Media Law 101: Defamation (reference framework)
- Mondaq: Tanzania's Online Content Regulations (TCRA enforcement analysis)
- COSOTA (Copyright Society of Tanzania) — royalties and copyright framework

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL complaints in this industry)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| `complainant_name` | Jina la mlalamikaji | Yes | MCT complaint procedures require complainant identification for formal complaint registration and written decision |
| `complainant_contact` | Mawasiliano (simu / barua pepe) | Yes | Required by MCT and TCRA GN 203 for follow-up and formal notification of outcome |
| `complainant_role` | Wadhifa wa mlalamikaji | Yes | MCT accepts complaints from: individual directly defamed / organization representative / consumer of media / community group — determines standing and evidence requirements |
| `media_house_or_platform_name` | Jina la chombo cha habari / mtandao | Yes | MCT: complaint must identify the media entity; TCRA GN 203: licensee must be identified for regulatory complaint routing |
| `content_type` | Aina ya maudhui | Yes | MCT accepts: gazeti / redio / televisheni / mtandaoni; TCRA EPOCA covers broadcast, print, online, social media, film — determines which regulatory framework applies |
| `content_identifier` | Kichwa cha makala / mpango / URL / kituo / ukurasa | Yes | MCT: "date when content appeared" and specific content locator required; TCRA: URL or broadcast details needed for investigation |
| `date_of_publication_or_broadcast` | Tarehe ya kuchapishwa / kutangazwa | Yes | MCT: date required; TCRA GN 203: 30-day window for initial complaint to licensee runs from publication/broadcast date |
| `issue_type` | Aina ya tatizo | Yes | MCT Code of Ethics and TCRA EPOCA both require categorization to determine applicable standard, regulatory body, and remedy |
| `issue_description` | Maelezo ya tatizo | Yes | MCT: "description of what was published/broadcast"; TCRA GN 203 requires full narrative for complaint registration |
| `affected_individual_or_group` | Mtu au kundi lililoathirika | Yes | MCT precedent (Christian organization complaints) — identifies who is harmed; required for harm assessment |
| `harm_suffered` | Madhara yaliyopatikana | Yes | Defamation requires reputational harm; hate speech requires community harm; privacy violation requires psychological or safety harm |
| `content_still_accessible` | Je, maudhui bado yanapatikana? | Yes | TCRA online content takedown orders require evidence of ongoing accessibility; urgent takedown pathway if Yes AND content is harmful |
| `complaint_first_raised_with_media_house` | Je, umeshalalamika kwa chombo cha habari moja kwa moja? | Yes | TCRA GN 203 Rule: complainant must first lodge with licensee; licensee must resolve within 12 hours (for broadcast) or reasonable period; failure enables TCRA-CC referral |
| `media_house_response` | Jibu la chombo cha habari (kama lipo) | Conditional | TCRA GN 203: required at regulatory level; complainant must attach media house response or evidence of non-response |
| `date_complaint_lodged_with_media_house` | Tarehe ya malalamiko kwa chombo cha habari | Yes (for TCRA/MCT escalation) | TCRA GN 203: 30-day limitation on escalation to TCRA-CC after lodging with licensee |
| `desired_remedy` | Jibu / hatua unayotaka | Yes | MCT and TCRA provide: retraction / apology / takedown / right of reply / fine / sanction — complainant must state desired remedy |
| `supporting_evidence` | Ushahidi wa kusaidia | Yes | MCT requires: screenshots / recordings / printed copies / links; TCRA: digital evidence must be preserved for online content complaints |

### Conditional Fields (collect based on issue type)

**If `issue_type = defamation` OR `libel`:**
Also collect:
- `false_statement_identified` — Kauli ya uongo iliyochapishwa: Specific false claim made about the complainant; PBS Media Law: defamation requires a specific false statement of fact
- `truth_or_evidence_of_falsity` — Ushahidi kwamba kauli ni ya uongo: Facts contradicting the publication; essential for MCT and legal proceedings
- `publication_distribution` — Usambazaji wa chapisho: National / regional / online reach; determines scope of reputational harm
- `retraction_already_demanded` — Je, ulikwisha omba chombo cha habari kirudishe habari? Yes/No: Prior retraction demand establishes bad faith if refused
- `reputational_damage_description` — Maelezo ya uharibifu wa sifa: Employment loss / business harm / social harm / family impact

**If `issue_type = hate_speech` OR `incitement`:**
Also collect:
- `target_group` — Kundi linaloelekezwa: Ethnic / religious / gender-based / political — determines which anti-hate framework applies
- `language_used` — Lugha iliyotumika: Swahili / English / local language — affects scope of public harm
- `incitement_to_violence_flag` — Je, maudhui yanachochea ukatili? Yes/No: Incitement is a criminal matter under Tanzania Penal Code; triggers police referral alongside TCRA
- `community_harm_scale` — Ukubwa wa madhara kwa jamii: Individual / ward / district / national

**If `issue_type = privacy_violation` OR `unauthorized_image_use`:**
Also collect:
- `information_type_exposed` — Aina ya taarifa zilizofunuliwa: Location / medical / financial / family / sexual / identity
- `consent_given` — Je, uliruhusu kuchapishwa? Yes/No: Without consent = presumptive privacy violation under Tanzania Data Protection framework
- `harm_from_exposure` — Madhara kutokana na kufunuliwa: Physical risk / relationship harm / employment harm / psychological harm

**If `issue_type = copyright_violation` OR `royalties_dispute`:**
Also collect:
- `copyrighted_work_title` — Jina la kazi iliyolindwa: Song / film / article / photograph / program
- `cosota_registration_number` — Nambari ya usajili wa COSOTA (kama ipo): COSOTA registration strengthens copyright enforcement claim
- `how_work_was_used_without_permission` — Jinsi kazi ilivyotumika bila ruhusa: Broadcast / republished / sampled / adapted
- `commercial_benefit_to_media_house` — Je, chombo cha habari kilinufaika kibiashara? Yes/No: Determines remedy calculation

**If `issue_type = misinformation` OR `disinformation`:**
Also collect:
- `source_of_correct_information` — Chanzo cha taarifa sahihi: Government statement / scientific report / official record — required to demonstrate falsity
- `harm_caused_by_false_information` — Madhara ya habari za uongo: Health behavior / public panic / electoral / economic
- `correction_already_published` — Je, urekebisho umechapishwa tayari? Yes/No

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| ME-01 | `defamation_libel` | False statement of fact damaging a person's or organization's reputation |
| ME-02 | `privacy_violation` | Publication of private information or images without consent |
| ME-03 | `hate_speech` | Content that promotes hatred based on ethnicity, religion, gender, or other protected characteristic |
| ME-04 | `misinformation` | Publishing false information presented as factual |
| ME-05 | `disinformation` | Deliberate publication of false information to deceive |
| ME-06 | `copyright_violation` | Use of copyrighted content without permission or payment |
| ME-07 | `royalties_dispute` | Music or content creator not paid royalties due under COSOTA framework |
| ME-08 | `indecent_content` | Sexually explicit or obscene content broadcast or published |
| ME-09 | `blasphemy_religious_offense` | Content disrespectful or offensive to a religious community (TCRA has precedent) |
| ME-10 | `incitement_to_violence` | Content calling for violence against individuals or groups |
| ME-11 | `biased_reporting` | One-sided reporting that violates journalistic balance standards |
| ME-12 | `unauthorized_image_use` | Use of a person's image or identity without consent |
| ME-13 | `advertising_ethics_violation` | False or misleading advertising content |
| ME-14 | `broadcast_quality_failure` | Technical quality failure (signal, subtitle errors, repeated programming) |
| ME-15 | `journalist_misconduct` | Harassment, bribery, or unethical conduct by journalist |

### Resolution Standards for This Industry

- **MCT (Media Council of Tanzania):** MCT accepts complaints from "any institution or member of the public who feels aggrieved by the media." MCT investigates under its Code of Ethics; remedies include required retraction, apology, or right of reply. MCT decisions are published.
- **TCRA Complaints Committee (GN 203):** Complainant must first lodge with the licensee (broadcaster, online platform). Licensee must resolve within 12 hours for broadcast content or a reasonable period for other content. If unresolved or response unsatisfactory, complainant may refer to TCRA-CC within 30 days. TCRA-CC can sanction licensees including suspension and fines.
- **EPOCA Online Content Regulations:** TCRA can order takedown of online content violating EPOCA regulations; content platforms must comply within specified periods.
- **COSOTA:** Copyright royalties disputes are handled by COSOTA under the Copyright and Neighbouring Rights Act (Cap 218); COSOTA can issue licensing compliance orders.
- **Criminal matters (defamation, hate speech, incitement):** Tanzania Penal Code applies; police referral for criminal defamation or incitement to violence.
- **Right of reply:** MCT Code of Ethics entitles individuals defamed by media to a right of reply in the same publication or broadcast; demand for right of reply should be documented.

### Escalation Triggers (field values that require immediate escalation)

- `issue_type = incitement_to_violence` AND `incitement_to_violence_flag = Yes` — Criminal matter; escalate to Tanzania Police AND TCRA simultaneously; do not wait for MCT internal process
- `issue_type = hate_speech` AND `community_harm_scale = National` — High-severity; escalate to TCRA-CC; flag for government regulatory attention
- `issue_type = privacy_violation` AND `harm_from_exposure` includes physical risk — Safety emergency; immediate takedown request to platform AND police notification
- `issue_type = blasphemy_religious_offense` — TCRA has acted on complaints from religious organizations; escalate to TCRA-CC with evidence of content; MCT parallel complaint
- `issue_type = defamation_libel` AND `content_still_accessible = Yes` — Request immediate takedown alongside complaint; preserve evidence (screenshot with timestamp)
- `content_type = Online` AND `content_still_accessible = Yes` AND `issue_type` includes hate speech, incitement, or child-related harm — Emergency TCRA online content takedown referral

---

## SUGGESTION / IMPROVEMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `submitter_name` | Jina la mtoa maoni (hiari) | Optional | Suggestions may be anonymous; do not require identification |
| `media_house_or_platform` | Chombo cha habari / mtandao unaohusika | Yes | Routes suggestion to correct entity or regulatory body |
| `suggestion_category` | Kategoria ya mapendekezo | Yes | Systematic routing and thematic analysis |
| `suggestion_detail` | Maelezo ya mapendekezo | Yes | Free text; core content |
| `content_type_targeted` | Aina ya maudhui inayohusika | Recommended | Broadcast / Online / Print — determines applicable editorial standard |

### Industry-Specific Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| MES-01 | `editorial_accuracy` | Usahihi wa habari na ukweli |
| MES-02 | `content_diversity` | Utofauti wa maudhui na sauti |
| MES-03 | `language_quality` | Ubora wa lugha (Kiswahili / Kiingereza) |
| MES-04 | `online_safety` | Usalama wa maudhui mtandaoni |
| MES-05 | `advertising_ethics` | Maadili ya matangazo |
| MES-06 | `accessibility` | Upatikanaji (manukuu, lugha ya ishara) |
| MES-07 | `local_content` | Maudhui ya ndani na utamaduni |
| MES-08 | `journalist_training` | Mafunzo ya waandishi wa habari |
| MES-09 | `copyright_compliance` | Kuzingatia sheria ya hakimiliki |
| MES-10 | `technical_quality` | Ubora wa kiufundi (mawimbi, sauti, picha) |

---

## INQUIRY / QUESTION — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `inquirer_name` | Jina la mwulizaji (hiari) | Optional | Not required for general inquiries |
| `inquiry_type` | Aina ya swali | Yes | Routes to correct knowledge base or referral pathway |
| `media_entity_of_interest` | Chombo cha habari kinachohusika | Recommended | For entity-specific inquiries |
| `content_reference` | Marejeleo ya maudhui (kama ipo) | Conditional | For content-specific inquiries (correction, right of reply) |
| `preferred_response_channel` | Njia unayopendelea ya jibu | Yes | SMS / Simu / WhatsApp / Barua pepe |

### Common Inquiry Types & Required Data Per Type

| Inquiry Type | Swahili | Additional Fields Needed |
|-------------|---------|--------------------------|
| `correction_request` | Ombi la urekebisho wa habari | `media_house_or_platform_name`, `content_identifier`, `false_statement_identified` |
| `right_of_reply` | Haki ya kujibu habari iliyonichafua | `media_house_or_platform_name`, `date_of_publication_or_broadcast`, `complainant_name` |
| `tcra_licence_verification` | Je, kituo hiki kina leseni ya TCRA? | `media_house_or_platform_name`, `content_type` |
| `copyright_query` | Swali kuhusu hakimiliki ya kazi yangu | `copyrighted_work_title`, `media_house_or_platform_name` |
| `cosota_registration` | Jinsi ya kusajili kazi yangu kwa COSOTA | `content_type`, `complainant_role` |
| `mct_complaint_process` | Jinsi ya kuwasilisha malalamiko MCT | `media_house_or_platform_name`, `issue_type` |
| `takedown_request` | Jinsi ya kuomba maudhui yaondolewe | `content_identifier`, `issue_type`, `content_still_accessible` |

---

## APPLAUSE / COMPLIMENT — Fields

### Core Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| `submitter_name` | Jina la mtoa pongezi (hiari) | Optional | For acknowledgement; not required |
| `media_house_journalist_program_recognized` | Chombo cha habari / Mwandishi / Mpango unaopongezwa | Yes | Routes compliment to correct entity, journalist, or editorial team |
| `what_was_exemplary` | Kilichokuwa bora / cha mfano | Yes | Specific journalism quality, accuracy, courage, or community impact |
| `date_of_publication_or_broadcast` | Tarehe ya makala / kipindi kilichopongezwa | Recommended | For correlation with editorial records and recognition |
| `impact_of_content` | Athari ya maudhui hayo | Recommended | Captures public interest journalism impact for MCT recognition and media awards data |
| `content_identifier` | Kichwa / URL / Kipindi kilichopongezwa | Recommended | Enables the media house to identify the specific piece or journalist for recognition |

---

## AI Conversation Guidance for This Industry

- **Identify the content type and media channel first.** Ask "Hii inahusu gazeti, redio, televisheni, au maudhui ya mtandaoni?" before asking about the problem — the regulatory pathway (MCT for journalism ethics, TCRA for broadcast and online, COSOTA for copyright) depends entirely on the medium.
- **Get the content reference (URL, article title, broadcast date/program name) before asking for the complainant's description.** Without a specific content reference, neither MCT nor TCRA can investigate. Say "Una kiungo (URL) cha maudhui hayo, au unaweza kunieleza jina la makala, kipindi cha redio, au mpango wa TV?" — if the content has been taken down, ask if they preserved a screenshot.
- **For defamation and privacy complaints, establish whether the content is still accessible.** Ask "Je, maudhui hayo bado yanaonekana mtandaoni au kwenye chombo cha habari?" — if Yes, a takedown request may need to run in parallel with the complaint; if No, collect evidence that existed (screenshots, cached copies).
- **Always ask whether the complainant has already contacted the media house.** TCRA GN 203 requires the complainant to first raise the issue with the licensee before the TCRA-CC can accept the complaint. Ask "Je, umeshalalamika moja kwa moja kwa gazeti / kituo hicho? Walikusema nini au walifanya nini?" — this determines whether TCRA-CC escalation is available.
- **For copyright and royalties complaints, ask about COSOTA registration.** Say "Je, kazi yako imesajiliwa kwa COSOTA? Una nambari ya usajili?" — registered works have stronger protection and COSOTA can act more readily; unregistered works still have copyright but the complaint route may differ.
- **For hate speech or incitement complaints, collect the target group explicitly.** Ask "Maudhui haya yalilenga nani hasa — kikabila, kidini, kwa jinsia, au kikundi kingine?" — this is essential for determining which anti-hate framework applies and whether the matter has a criminal dimension.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Media channel type | "Hii inahusu gazeti, redio, televisheni, au maudhui ya mtandaoni / mitandao ya kijamii?" |
| Media house name | "Jina la chombo cha habari au mtandao unaohusika ni nini?" |
| Content identifier | "Una kiungo (URL) cha maudhui hayo? Au unaweza kunipa jina la makala / kipindi, na tarehe iliyochapishwa / kutangazwa?" |
| Issue type | "Tatizo lako ni nini hasa — kashfa ya uongo, uvamizi wa faragha, chuki, habari za uongo, au kitu kingine?" |
| Content accessible | "Je, maudhui hayo bado yanaonekana mtandaoni au kwenye kituo? Au yameshafutwa?" |
| Prior complaint | "Je, umeshalalamika moja kwa moja kwa chombo cha habari hicho? Walikusema nini au walifanya nini?" |
| Date lodged | "Ulishalalamika lini kwa chombo cha habari? Tarehe gani?" |
| Evidence preservation | "Una ushahidi wowote — picha ya skrini, kurekodi, nakala ya gazeti, au kiungo ambacho bado kinafanya kazi?" |
| Target group (hate speech) | "Maudhui haya yalilenga nani hasa — ni kikabila, kidini, kwa jinsia, au kikundi kingine?" |
| Desired remedy | "Unataka nini kitokee — kuomba msamaha hadharani, kuondoa maudhui, haki ya kujibu, au hatua za kisheria?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| `issue_type` | `incitement_to_violence` AND `incitement_to_violence_flag = Yes` | Immediate escalation to Tanzania Police AND TCRA-CC; preserve evidence; criminal referral alongside regulatory complaint |
| `issue_type` | `hate_speech` AND `community_harm_scale = National` | TCRA-CC escalation; MCT parallel complaint; flag for government regulatory awareness |
| `content_still_accessible` | Yes AND `issue_type` includes hate speech, incitement, or privacy violation | Immediate TCRA online content takedown referral; advise complainant to preserve screenshot with timestamp |
| `issue_type` | `blasphemy_religious_offense` | TCRA-CC complaint (TCRA has precedent for acting on this category); MCT parallel complaint; collect community harm evidence |
| `complaint_first_raised_with_media_house` | Yes AND `media_house_response = None` AND `date_complaint_lodged` > 12 hours for broadcast or > 30 days | Advise TCRA-CC escalation eligibility; provide TCRA-CC complaint submission link (+255 22 xxx / tcra.go.tz) |
| `complaint_first_raised_with_media_house` | No | Advise complainant to first contact media house directly; provide guidance on what to say; explain that TCRA/MCT require this first step |
| `issue_type` | `copyright_violation` AND `cosota_registration_number` provided | COSOTA enforcement referral; licensing compliance order pathway available |
| `issue_type` | `defamation_libel` AND `retraction_already_demanded = Yes` AND no retraction published | MCT complaint; document bad faith; calculate reputational harm for potential civil claim |
| `issue_type` | `privacy_violation` AND `harm_from_exposure` includes physical risk | Safety emergency; immediate takedown request AND police notification |
| `complainant_role` | Individual directly defamed AND `issue_type = defamation_libel` | Right of reply demand letter to media house; MCT complaint; preserve evidence for potential civil defamation action |

---

*Sources: Media Council of Tanzania (MCT) complaint procedures and Code of Ethics, TCRA Complaints Committee Rules 2018 (GN No. 203), TCRA Electronic and Postal Communications (Online Content) Regulations analysis (MCT 2020), Tanzania Media Services Act 2016, Tanzania Electronic and Postal Communications Act (EPOCA) 2010, PBS Media Law 101 Defamation, Mondaq Tanzania Online Content Regulations analysis, COSOTA Copyright Society of Tanzania*
