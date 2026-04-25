# Organisation Structure and Feedback Routing

## Organisation Hierarchy on Riviwa

```
Organisation (Org)
├── Branches (geographic/functional offices)
│   └── Departments
│       └── Services / Products
└── Projects
    ├── Project Stages
    └── Sub-Projects
```

## When is Feedback Linked to a Project?

Feedback is linked to a **specific project** when the issue is about:
- Active construction or installation work
- A defined infrastructure project with a project ID
- A World Bank-funded or donor-funded programme
- A specific project phase or stage

Examples:
- "The road construction crew blocked my shop entrance" → Project: Msimbazi Road Improvement
- "I haven't received my compensation for the pipeline running through my farm" → Project: Water Supply Pipeline Project

## When is Feedback Org-Level (No Project)?

Feedback does NOT need a project when it's about:
- **Organisation as a whole**: Customer complaints about a bank, telecom, insurance company, hospital
- **Branch-level issues**: "The Mwanza branch of your bank has poor customer service"
- **Department issues**: "Your HR department never responds to job applications"
- **Service/product complaints**: "Your mobile money service has been down for 3 days"
- **Billing/payment issues**: "I was charged twice for the same transaction"
- **Staff conduct**: "The cashier at your Kariakoo branch was rude to me"

In these cases: `project_id = NULL`, `org_id` is set, optionally `branch_id` and `department_id`.

## Routing Logic

The AI and system route feedback based on:

1. **project_id is set** → Routed to project's GRM team
2. **project_id = NULL, branch_id set** → Routed to branch manager/GRM focal
3. **project_id = NULL, department_id set** → Routed to department head
4. **project_id = NULL, only org_id** → Routed to org-level GRM Officer

## Branch vs Department vs Service

**Branch (OrgBranch):**
A geographic or operational sub-office of an organisation.
Examples: "Mbeya Branch", "Dar es Salaam Regional Office", "Northern Zone Office"

**Department (OrgDepartment):**
A functional division within the organisation.
Examples: "Finance Department", "Human Resources", "Customer Care", "Engineering", "Environmental and Social"

**Service (OrgService):**
A specific type of service or product the organisation delivers.
Examples: "Road Maintenance Service", "Water Supply Service", "Mobile Money", "Business Loans"

## Common Industry Contexts

**Banking / Financial Services:**
- Branches: retail bank branches across towns
- Departments: loans, cards, customer care, digital banking
- Common feedback: transaction errors, poor service, account issues, fraud
- No project needed — feedback is about the service

**Telecommunications:**
- Network quality complaints
- Billing disputes
- SIM card issues
- No project needed

**Government / Public Services:**
- Tax authority: assessment disputes, refund delays
- Land authority: title deed delays, boundary disputes
- Immigration: passport delays
- Education: school enrollment, exam results
- Health: hospital services, medicine availability

**Utilities (Water, Electricity):**
- Supply disruption (may or may not be project-related)
- If disruption is caused by a specific project → link to project
- If it's a routine operational issue → org-level, no project

**NGOs / Development Organisations:**
- Programme implementation issues
- Beneficiary complaints
- Often project-specific (per donor programme)
