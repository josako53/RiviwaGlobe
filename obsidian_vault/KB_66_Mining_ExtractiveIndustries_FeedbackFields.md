---
tags: [industry-kb, field-standards, feedback-fields, mining, extractive-industries]
---
# Mining / Extractive Industries — Feedback Collection Fields & Standards

## Industry Identifiers

Signals the AI uses to detect this industry: madini, mining, extraction, uchimbaji, gold, dhahabu, diamond, almasi, tanzanite, coal, makaa ya mawe, iron ore, chuma, copper, shaba, nickel, nikel, mineral rights, haki za madini, mining license, leseni ya uchimbaji, MEM, Ministry of Energy and Minerals, STAMICO, TMAA, Tanzania Minerals Audit Agency, TPDC, Tanzania Petroleum Development Corporation, oil, mafuta, gas, gesi, petroleum, artisanal mining, wachimbaji wadogo, small-scale mining, SSM, large-scale mining, LSM, environmental impact, athari ya mazingira, community, jamii, community development agreement, CDA, royalty, mrabaha, CSR, corporate social responsibility, resettlement, uhamishaji, land acquisition, uchukuzi wa ardhi, dust, vumbi la uchimbaji, noise, kelele za uchimbaji, water contamination, uchafuzi wa maji, cyanide, sulfur, lead, NEMC, National Environment Management Council, Barrick, Acacia, Tembo Nickel, STAMICO, TPC, TPDC

## Why Industry-Specific Fields Matter

Mining complaints involve distinct categories with serious regulatory and rights dimensions: environmental contamination (requiring GPS coordinates, substance type, NEMC report), community displacement (requiring original land title, resettlement agreement reference), royalty disputes (TMAA investigation), and ASM (artisanal small-scale mining) conflicts (requiring license details, GPS location). The Mining Act creates specific rights for communities near mining operations. Without mining-specific fields, the AI cannot route to TMAA, NEMC, or the Ministry of Energy and Minerals — or generate a community rights complaint under the Tanzania Mining Act.

## Source Standards

- Tanzania Mining Act, Cap. 123 (as amended 2017/2019)
- Tanzania Mining Regulations 2010 and Mining (Mineral Rights) Regulations 2017
- Tanzania Minerals Audit Agency (TMAA) Act
- Petroleum Act, Cap. 392
- TPDC Act — petroleum development
- National Environment Management Council (NEMC) Act, Cap. 191
- Environmental Management Act, Cap. 191
- Land Act, Cap. 113 — land rights and acquisition
- Land Acquisition Act, Cap. 118 — compulsory acquisition compensation
- ISO 14001:2015 — environmental management systems
- ICMM Mining Principles — industry benchmark for community relations
- Extractive Industries Transparency Initiative (EITI) — Tanzania EITI member
- ISO 10002:2018 — complaints handling
- IFC Performance Standards 1–8 — environmental and social due diligence (for internationally financed projects)

---

## GRIEVANCE / COMPLAINT — Required & Recommended Fields

### Core Fields (collect for ALL mining/extractive complaints)

| Field | Swahili Label | Required? | Why It Enables Better Action |
|-------|--------------|-----------|------------------------------|
| complainant_full_name | Jina kamili la mlalamikaji | Yes | Complaint registration |
| complainant_phone | Nambari ya simu | Yes | Status updates |
| complainant_community | Jina la jamii / kijiji | Yes | Community-level routing; Mining Act community rights |
| mining_company_name | Jina la kampuni ya madini | Yes | MEM/TMAA can look up license holder |
| mining_license_number | Nambari ya leseni ya uchimbaji | Recommended | Enables TMAA and MEM license verification |
| mine_location_name | Jina la eneo la mgodi | Yes | Geographic routing |
| gps_coordinates | Kuratibu za GPS (latitude/longitude) | Recommended | NEMC environmental investigations require precise location |
| issue_type | Aina ya tatizo | Yes | Environmental / Land / CSR / Royalty / Safety etc. |
| issue_description | Maelezo ya tatizo | Yes | ISO 10002:2018; detailed narrative |
| date_of_incident | Tarehe ya tukio au kuanza kwa tatizo | Yes | For investigation timeline |
| people_affected | Idadi ya watu walioathirika | Recommended | Community impact scale |
| evidence_available | Ushahidi unaopatikana | Recommended | Photos / Water samples / Medical records / Video |
| health_impact | Je, athari za kiafya zimetokea? | Yes | For medical and NEMC escalation |
| desired_outcome | Matokeo unayotaka | Yes | Compensation / Environmental remediation / License review / CSR program |

### Conditional Fields (collect based on issue type)

**If issue_type = Environmental Contamination:**
Also collect:
- `contamination_type` — Aina ya uchafuzi: Water / Air / Soil / Noise / Vibration / Chemical spill
- `substance_suspected` — Dutu inayoshukiwa: Cyanide / Mercury / Lead / Arsenic / Acid / Dust / Other
- `water_source_affected` — Chanzo cha maji kilichoathirika: River / Well / Borehole / Lake
- `water_used_for` — Maji hutumiwa kwa nini: Drinking / Irrigation / Livestock — for health impact assessment
- `nemc_complaint_filed` — Je, malalamiko yamewahi kuwasilishwa NEMC? Yes / No
- `sample_available` — Je, sampuli ya maji / udongo inapatikana?: NEMC laboratory testing

**If issue_type = Land / Resettlement:**
Also collect:
- `original_plot_number` — Nambari ya kiwanja / ardhi ya asili
- `compensation_agreement_signed` — Je, makubaliano ya fidia yalisainishwa? Yes / No
- `compensation_amount_agreed_tzs` — Kiasi cha fidia kilichokubaliwa (TZS)
- `compensation_received_tzs` — Kiasi cha fidia kilichopokelewa (TZS)
- `resettlement_agreement_reference` — Nambari ya makubaliano ya uhamishaji
- `new_land_provided` — Je, ardhi mpya ilitolewa? Yes / No
- `new_land_quality_comparable` — Je, ardhi mpya ina ubora kama wa ardhi ya asili?

**If issue_type = Royalty / Revenue Dispute:**
Also collect:
- `royalty_agreement_reference` — Nambari ya makubaliano ya mrabaha
- `royalty_period` — Kipindi cha mrabaha kinachobiwabishwa
- `royalty_expected_tzs` — Mrabaha unaotarajiwa (TZS)
- `royalty_received_tzs` — Mrabaha uliopokelewa (TZS)
- `eiti_transparency_concern` — Je, tatizo linahusiana na uwazi wa mapato ya madini?: EITI Tanzania referral

**If issue_type = ASM / Artisanal Mining Conflict:**
Also collect:
- `asm_license_number` — Nambari ya leseni ya mchimbaji mdogo
- `conflict_type` — Aina ya mgongano: Boundary / Competition / Harassment by large company / Water access
- `large_company_involved` — Jina la kampuni kubwa inayohusika (kama ipo)

### Issue Type Classification

| Code | Issue Type | Description |
|------|-----------|-------------|
| MN-01 | water_contamination | Mining activity contaminating water sources |
| MN-02 | air_pollution | Dust, fumes, or chemical emissions affecting community |
| MN-03 | land_rights_violation | Land taken without adequate notice, consent, or compensation |
| MN-04 | resettlement_failure | Inadequate or unfair resettlement |
| MN-05 | noise_vibration | Blasting or machinery noise/vibration affecting community |
| MN-06 | royalty_dispute | Community or government royalty payment dispute |
| MN-07 | csr_failure | Promised CSR activities not delivered |
| MN-08 | asm_conflict | Conflict between artisanal and large-scale miners |
| MN-09 | environmental_damage | Ecosystem destruction; biodiversity loss |
| MN-10 | worker_safety | Mining workplace accident or safety hazard |
| MN-11 | illegal_mining | Unlicensed mining activity |
| MN-12 | community_consultation_failure | Mining company failed to consult affected communities |
| MN-13 | cultural_heritage_damage | Damage to cultural or historical sites |
| MN-14 | gender_impacts | Discriminatory impacts on women in mining communities |

### Resolution Standards

- **Company GRM (Grievance Redress Mechanism):** IFC PS1 requires companies to have functional GRM; response within 30 days.
- **MEM (Ministry of Energy and Minerals):** License compliance complaints; investigation within 60 days.
- **TMAA:** Revenue and royalty disputes; audit investigation.
- **NEMC:** Environmental contamination; investigation within 30 days; emergency within 72 hours.
- **Land compensation disputes:** Land Tribunal — District → High Court.
- **Community resettlement:** World Bank/IFC OP 4.12 standards for internationally financed projects (compensation at replacement cost, livelihood restoration).
- **Required for escalation:** Mining license number, company name, GPS location, date, description, evidence, health impact documentation.

### Escalation Triggers

- `contamination_type` includes cyanide, mercury, or arsenic — Immediate NEMC emergency response; public health alert; medical assessment
- `health_impact = Yes` AND mining chemicals suspected — MOHCDGEC + NEMC joint investigation; stop order on operations possible
- `issue_type = land_rights_violation` AND forced displacement without compensation — CHRAGG referral; Human Rights Committee; Land Tribunal
- `issue_type = worker_safety` AND fatality — OSHA (Occupational Safety and Health Authority) immediate investigation; MEM notification
- `issue_type = illegal_mining` — MEM enforcement; police referral; TMAA revenue protection
- `issue_type = community_consultation_failure` AND IFC-financed project — IFC Compliance Advisor/Ombudsman (CAO) referral
- `issue_type = csr_failure` AND CDA exists — MEM review of CDA compliance; community development agreement enforcement

---

## SUGGESTION / IMPROVEMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | Anonymous accepted for safety |
| mining_company | Kampuni ya madini | Recommended | For routing |
| community_name | Jina la jamii | Recommended | Community-level routing |
| suggestion_category | Kategoria | Yes | For analysis |
| suggestion_detail | Maelezo | Yes | Core content |

### Improvement Categories

| Code | Category | Swahili |
|------|----------|---------|
| MNS-01 | environmental_management | Usimamizi bora wa mazingira |
| MNS-02 | community_grm | Mfumo bora wa malalamiko ya jamii |
| MNS-03 | csr_delivery | Utekelezaji bora wa CSR |
| MNS-04 | local_employment | Ajira zaidi kwa wenyeji |
| MNS-05 | fair_compensation | Fidia ya haki kwa ardhi na uharibifu |
| MNS-06 | asm_support | Msaada zaidi kwa wachimbaji wadogo |
| MNS-07 | revenue_transparency | Uwazi wa mapato ya madini |
| MNS-08 | mine_closure_planning | Mpango bora wa kufunga mgodi |

---

## INQUIRY / QUESTION — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| caller_name | Jina | Recommended | For tracking |
| community_name | Jamii | Recommended | For community-specific queries |
| query_type | Aina ya swali | Yes | Routes to correct answer |

### Common Inquiry Types

| Inquiry Type | Swahili | Additional Fields |
|-------------|---------|-------------------|
| company_license | Je, kampuni hii ina leseni ya MEM? | company_name |
| royalty_entitlement | Jamii yangu inastahili mrabaha gani? | location, mining_company |
| cda_rights | Makubaliano ya maendeleo ya jamii yana haki gani? | company_name |
| nemc_complaint | Jinsi ya kulalamika kwa NEMC | contamination_type |
| asm_license | Jinsi ya kupata leseni ya uchimbaji mdogo | location |
| eiti_report | Ripoti ya mapato ya madini ya Tanzania ipo wapi? | — |

---

## APPLAUSE / COMPLIMENT — Fields

| Field | Swahili Label | Required? | Why |
|-------|--------------|-----------|-----|
| submitter_name | Jina (hiari) | Optional | For acknowledgement |
| company_name | Kampuni ya madini | Yes | Routes to community relations |
| community_name | Jamii | Recommended | Community relations |
| specific_aspect_praised | Kipengele | Yes | CSR uliotekelezwa / Mazingira mazuri / Ajira za wenyeji / Mawasiliano mazuri na jamii |
| overall_satisfaction_rating | Kiwango cha ridhaa (1–5) | Yes | Social license to operate benchmarking |

---

## AI Conversation Guidance for This Industry

- **Environmental contamination from mining chemicals is a public health emergency.** If cyanide, mercury, or other toxic substances are suspected in water or soil, immediately escalate: "Uchafuzi wa kemikali za madini ni hatari ya maisha — tutawasiliana na NEMC na MOHCDGEC mara moja."
- **Protect complainant identity for sensitive complaints.** Mining communities often fear retaliation. "Tunaweza kushughulikia malalamiko yako kwa siri — jina lako haligawanyani bila idhini yako."
- **For land disputes, ask about compensation agreements.** Many communities accepted initial compensation without knowing their full rights. "Je, makubaliano ya fidia yalisainishwa? Na fidia hiyo ilikuwa sawa na thamani ya ardhi yako?"
- **Distinguish between CSR failures and regulatory obligations.** Some communities confuse CSR promises with legal rights. "Baadhi ya ahadi za kampuni zinaweza kuwa za hiari — lakini ahadi zilizowekwa kwenye CDA (Community Development Agreement) zina nguvu ya kisheria."
- **For ASM conflicts with large companies, collect GPS coordinates.** Boundary disputes are the most common ASM conflict, and GPS data enables immediate MEM verification.
- **Do not take sides in royalty disputes without data.** TMAA audit is the appropriate resolution path for royalty amount disputes.

## Swahili Key Phrases for Field Collection

| Field to Collect | Swahili Phrase |
|-----------------|----------------|
| Company name | "Kampuni ya madini inayohusika inaitwa nini?" |
| Location | "Mgodi huu uko wapi hasa — wilaya, kata, na kijiji?" |
| GPS | "Kama unaweza, toa kuratibu za GPS za eneo lililathirika" |
| Contamination substance | "Dutu gani inashukiwa kuwa chanzo cha uchafuzi — maji yana rangi gani, harufu gani?" |
| Health impact | "Je, watu wa jamii wameugua baada ya kutumia maji au kugusana na eneo hilo?" |
| Compensation | "Je, fidia ilitolewa kwa ardhi yako — kiasi gani, na ilikuwa sawa?" |
| CDA reference | "Je, kuna makubaliano ya maendeleo ya jamii (CDA) na kampuni? Nambari ya marejeleo?" |
| Evidence | "Je, una ushahidi — picha, sampuli ya maji, rekodi za kiafya?" |

## Action Recommendations Based on Field Values

| Field | Value | Recommended Action |
|-------|-------|--------------------|
| contamination_type | cyanide / mercury / arsenic | Public health emergency; NEMC + MOHCDGEC immediate; stop order on operations |
| health_impact | Yes AND confirmed mining chemicals | NEMC + MOHCDGEC joint investigation; medical assessment for community |
| issue_type | land_rights_violation AND forced displacement | CHRAGG + Human Rights Committee + Land Tribunal |
| issue_type | worker_safety AND fatality | OSHA immediate investigation; MEM notification; company license review |
| issue_type | illegal_mining | MEM enforcement + police; TMAA revenue protection |
| issue_type | csr_failure AND CDA exists | MEM review of CDA compliance; legal action for breach of CDA |
| issue_type | community_consultation_failure AND IFC project | IFC CAO referral; international accountability mechanism |
| eiti_transparency_concern | Yes | EITI Tanzania Secretariat referral; transparency report review |

---

*Sources: Tanzania Mining Act Cap. 123, Mining Regulations 2010/2017, TMAA Act, NEMC Act Cap. 191, Environmental Management Act Cap. 191, Land Acquisition Act Cap. 118, IFC Performance Standards 1–8, ICMM Mining Principles, EITI Standard, ISO 14001:2015, ISO 10002:2018*
