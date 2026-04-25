# Project Types, Sectors, and Common Contexts

## Sectors

Projects in Riviwa are classified by sector. The sector determines what kind of feedback categories are most relevant.

**Transport / Roads (TARURA, TANROADS)**
- Road rehabilitation and construction
- Bridge construction and repair
- Rural roads upgrading
- Urban road improvement
- Highway projects
- Keywords: road, bridge, highway, tarmac, gravel road, drainage, culvert, corridor, rehabilitation, upgrading, pavement, bitumen, construction

**Water and Sanitation (DAWASA, DAWASCO, Water Utilities)**
- Water supply pipeline installation
- Treatment plant construction
- Borehole drilling
- Sanitation facilities
- Sewerage systems
- Keywords: water, pipeline, borehole, supply, treatment, sanitation, sewage, tap, reservoir

**Energy (TANESCO)**
- Rural electrification
- Grid extension
- Solar projects
- Substation construction
- Keywords: electricity, power, grid, solar, electrification, substation, transformer

**Health**
- Hospital construction
- Health centre renovation
- Medical equipment supply
- Keywords: hospital, clinic, health centre, dispensary, maternity, pharmacy

**Education**
- School construction
- Classroom renovation
- Library, laboratory construction
- Keywords: school, classroom, university, college, library, education

**Agriculture and Irrigation**
- Irrigation scheme construction
- Dams and water storage
- Farm input supply
- Keywords: farm, irrigation, dam, agriculture, crops, planting, harvest

**Urban Development**
- Slum upgrading
- Urban infrastructure
- Markets, public spaces
- Keywords: urban, market, housing, slum, development, upgrading

**Environment**
- Forest conservation
- Environmental restoration
- Flood control
- Keywords: environment, forest, flood, erosion, conservation, basin, river

## Common Project Names and Contexts in Tanzania

**Msimbazi River Corridor Road Improvement Project**
- Location: Dar es Salaam, Ilala and Ubungo districts
- Sector: Transport / Urban Development
- Description: Road improvement along the Msimbazi River corridor including drainage, bridges, and pedestrian paths
- Affected areas: Gerezani, Kariakoo, Jangwani, Msimbazi, Ilala, Ubungo wards
- LGAs: Ilala, Ubungo
- Funding: World Bank

**Kigoma GRC (Grievance Redress Committee)**
- Location: Kigoma Region
- Sector: Transport / Rural Roads
- Description: Rural road rehabilitation in Kigoma region

**RISE Project (Road Infrastructure for Socio-Economic Development)**
- Sector: Transport
- Description: Road construction and rehabilitation for economic development

**TACTICS (Tanzania Transport for Climate-resilient Infrastructure)**
- Sector: Transport / Climate Resilience
- Description: Climate-resilient road infrastructure programme

**Safari Tour Project**
- Sector: Tourism
- Description: Tourism infrastructure development project

## Org-Level Feedback (No Project)

Some feedback is not about a specific project but about the organisation itself:
- Customer service complaints for a bank, telecom, or utility company
- Feedback about a specific department or branch
- Feedback about a type of service (e.g. "your mobile money service is slow")
- HR or employment complaints
- Regulatory compliance issues

In these cases, `project_id` is NULL and the feedback is associated directly with the organisation, and optionally with a branch, department, or service.

## Identifying the Right Project

The AI uses these signals to identify which project feedback belongs to:
1. **Location**: region, LGA (district), ward — matched against project's primary_lga and region
2. **Keywords**: road, water, construction, bridge etc. — matched against project sector/category
3. **Description**: semantic similarity to project name, description, objectives
4. **Organisation**: org_id narrows to that org's projects only
5. **Time context**: active projects preferred over completed ones
