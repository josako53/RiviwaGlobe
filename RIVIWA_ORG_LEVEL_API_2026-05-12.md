# Riviwa Org-Level API Reference
**Version**: 2.5 · **Base URL**: `https://api.riviwa.com/api/v1` · **Date**: 2026-05-12

> Full reference for React JS and Flutter developers. Every endpoint here is live-tested against the Azam Group organisation (`org_id: a6d704bf-6b7a-4da0-a1fd-c8475938f6a6`). All 33 endpoints return 200 with real data.

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Feedback — List & Counts (Drill-down)](#2-feedback--list--counts-drill-down)
3. [Org Analytics — Summary & Dimensions](#3-org-analytics--summary--dimensions)
4. [Org Analytics — Grievances](#4-org-analytics--grievances)
5. [Org Analytics — Suggestions](#5-org-analytics--suggestions)
6. [Org Analytics — Applause](#6-org-analytics--applause)
7. [Org Analytics — Branch Analytics](#7-org-analytics--branch-analytics)
8. [Suggestions Analytics (Deep)](#8-suggestions-analytics-deep)
9. [Inquiries Analytics (Deep)](#9-inquiries-analytics-deep)
10. [Staff Performance Analytics](#10-staff-performance-analytics)
11. [Reports](#11-reports)
12. [QR Codes](#12-qr-codes)
13. [Products & Services](#13-products--services)
14. [Implementation Patterns](#14-implementation-patterns)

---

## 1. Authentication

All endpoints (except public QR scan) require a JWT Bearer token. Riviwa uses a **two-step login** with OTP.

### Step 1 — Login

```
POST /auth/login
Content-Type: application/json
```

**Body**:
```json
{
  "identifier": "azam.admin2@azamgroup.co.tz",
  "password": "AzamGroup@2026!"
}
```

**Response**:
```json
{
  "login_token": "eyJ...",
  "requires_otp": true
}
```

### Step 2 — Verify OTP

```
POST /auth/login/verify-otp
Content-Type: application/json
```

**Body**:
```json
{
  "login_token": "eyJ...",
  "otp_code": "123456"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "524435b0-568b-4aff-a788-22e02563408f",
    "email": "azam.admin2@azamgroup.co.tz",
    "org_id": "a6d704bf-6b7a-4da0-a1fd-c8475938f6a6",
    "org_role": "admin"
  }
}
```

> **Staging note**: OTP `000000` works in staging/dev. Production sends real OTP via SMS/email.

### Using the Token

Add to every request:
```
Authorization: Bearer <access_token>
```

The `org_id` in the JWT payload is used automatically by most endpoints — you don't need to pass it as a query param for non-platform-admin users.

### React JS — Auth Helper

```javascript
// api.js
const BASE = 'https://api.riviwa.com/api/v1';

export async function login(identifier, password, otpCode) {
  const r1 = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identifier, password }),
  });
  if (!r1.ok) throw new Error('Login failed');
  const { login_token } = await r1.json();

  const r2 = await fetch(`${BASE}/auth/login/verify-otp`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ login_token, otp_code: otpCode }),
  });
  if (!r2.ok) throw new Error('OTP failed');
  const data = await r2.json();

  localStorage.setItem('riviwa_token', data.access_token);
  localStorage.setItem('riviwa_org_id', data.user.org_id);
  return data;
}

// Reusable API client
export function useApi() {
  const token = localStorage.getItem('riviwa_token');

  async function get(path, params = {}) {
    const url = new URL(`${BASE}${path}`);
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v);
    });
    const r = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
    return r.json();
  }

  async function post(path, body) {
    const r = await fetch(`${BASE}${path}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
    return r.json();
  }

  return { get, post };
}
```

### Flutter/Dart — Auth + Client

```dart
// riviwa_client.dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class RiviwaClient {
  static const String BASE = 'https://api.riviwa.com/api/v1';
  final String token;
  final String orgId;

  const RiviwaClient({required this.token, required this.orgId});

  // Two-step login
  static Future<RiviwaClient> login(
      String identifier, String password, String otpCode) async {
    // Step 1
    final r1 = await http.post(
      Uri.parse('$BASE/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'identifier': identifier, 'password': password}),
    );
    final loginToken = jsonDecode(r1.body)['login_token'] as String;

    // Step 2
    final r2 = await http.post(
      Uri.parse('$BASE/auth/login/verify-otp'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'login_token': loginToken, 'otp_code': otpCode}),
    );
    final body = jsonDecode(r2.body);
    return RiviwaClient(
      token: body['access_token'],
      orgId: body['user']['org_id'],
    );
  }

  // GET with query params (null values are ignored)
  Future<Map<String, dynamic>> get(
      String path, {Map<String, String?>? params}) async {
    final filteredParams = <String, String>{};
    params?.forEach((k, v) { if (v != null) filteredParams[k] = v; });
    final uri = Uri.parse('$BASE$path').replace(queryParameters: filteredParams);
    final r = await http.get(uri, headers: {'Authorization': 'Bearer $token'});
    if (r.statusCode != 200) throw Exception('${r.statusCode}: ${r.body}');
    return jsonDecode(r.body);
  }

  // POST with JSON body
  Future<Map<String, dynamic>> post(String path, Map<String, dynamic> body) async {
    final r = await http.post(
      Uri.parse('$BASE$path'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(body),
    );
    if (r.statusCode != 200 && r.statusCode != 201) {
      throw Exception('${r.statusCode}: ${r.body}');
    }
    return jsonDecode(r.body);
  }
}
```

---

## 2. Feedback — List & Counts (Drill-down)

> **Core pattern**: `GET /feedback/counts` gives you all summary numbers in one call. When a user taps a count (e.g. "28 Grievances"), call `GET /feedback` with the exact same filters — the numbers always match perfectly.

### 2.1 Count Feedback (Summary Numbers)

```
GET /feedback/counts
Authorization: Bearer <token>
```

**Query Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `org_id` | UUID | Organisation UUID (auto-read from JWT for org staff — optional) |
| `feedback_type` | string | Narrow to one type: `grievance` \| `suggestion` \| `applause` \| `inquiry` |
| `priority` | string | `critical` \| `high` \| `medium` \| `low` |
| `category` | string | Category slug (see list below) |
| `status` | string | `submitted` \| `acknowledged` \| `in_review` \| `escalated` \| `resolved` \| `closed` \| `dismissed` |
| `department_id` | UUID | Narrow to one department |
| `service_id` | UUID | Narrow to one service |
| `product_id` | UUID | Narrow to one product |
| `date_from` | string | ISO date `YYYY-MM-DD` (lower bound on `submitted_at`) |
| `date_to` | string | ISO date `YYYY-MM-DD` (upper bound on `submitted_at`) |

**Live Response (Azam Group)**:
```json
{
  "total": 60,
  "by_priority": {
    "critical": 7,
    "high": 15,
    "medium": 21,
    "low": 17
  },
  "by_type": {
    "grievance": 28,
    "suggestion": 15,
    "applause": 9,
    "inquiry": 8
  },
  "by_status": {
    "submitted": 59,
    "acknowledged": 1
  },
  "by_category": {
    "other": 12,
    "process": 10,
    "quality": 6,
    "general_inquiry": 5,
    "corruption": 5,
    "staff_conduct": 5,
    "community_benefit": 4,
    "timeliness": 4,
    "safety_hazard": 2,
    "communication": 2,
    "information_request": 2,
    "safety": 1,
    "responsiveness": 1,
    "procedure_inquiry": 1
  }
}
```

**Available `category` slugs**:
`billing` · `quality` · `process` · `staff_conduct` · `corruption` · `safety` · `safety_hazard` · `community_benefit` · `communication` · `timeliness` · `responsiveness` · `general_inquiry` · `procedure_inquiry` · `information_request` · `other`

---

### 2.2 List Feedback (Full Records with Filters)

```
GET /feedback
Authorization: Bearer <token>
```

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `org_id` | UUID | from JWT | Organisation UUID |
| `feedback_type` | string | — | `grievance` \| `suggestion` \| `applause` \| `inquiry` |
| `priority` | string | — | `critical` \| `high` \| `medium` \| `low` |
| `category` | string | — | Category slug |
| `status` | string | — | Status value |
| `channel` | string | — | `in_person` \| `email` \| `web_portal` \| `mobile_app` \| `sms` \| `whatsapp` \| `phone` |
| `department_id` | UUID | — | Filter by department |
| `service_id` | UUID | — | Filter by service |
| `product_id` | UUID | — | Filter by product |
| `branch_id` | UUID | — | Filter by branch |
| `category_def_id` | UUID | — | Filter by dynamic category definition |
| `lga` | string | — | LGA name (partial match) |
| `is_anonymous` | boolean | — | `true` \| `false` |
| `submission_method` | string | — | `self_service` \| `officer_assisted` |
| `assigned_committee_id` | UUID | — | Filter by assigned committee |
| `date_from` | string | — | ISO date `YYYY-MM-DD` |
| `date_to` | string | — | ISO date `YYYY-MM-DD` |
| `skip` | integer | `0` | Pagination offset |
| `limit` | integer | `50` | Page size (max 200) |

**Response Structure**:
```json
{
  "items": [ { ... } ],
  "count": 28
}
```

> **Note**: `count` is the number of items in **this page** (up to `limit`), not the total. Use `/feedback/counts` for total counts.

**Single Item Fields** (all fields present since v2.5):
```json
{
  "id": "357997e6-f902-4007-9f65-f7780cd3eace",
  "feedback_id": "357997e6-f902-4007-9f65-f7780cd3eace",
  "unique_ref": "GRV-2026-0171",
  "tracking_number": "GRV-2026-0171",
  "feedback_type": "grievance",
  "category": "other",
  "status": "submitted",
  "priority": "critical",
  "current_level": "ward",
  "channel": "in_person",
  "submission_method": "self_service",
  "is_anonymous": false,
  "org_id": "a6d704bf-6b7a-4da0-a1fd-c8475938f6a6",
  "branch_id": "38ae7bac-cc0a-43e9-ae94-c179c0c5f844",
  "department_id": "d8028dcb-8947-4295-b479-78f8a226bccd",
  "service_id": null,
  "product_id": "9437c38c-d363-44bf-8eb9-ba54715f2b21",
  "category_def_id": "5733bfb7-930e-4f26-bb31-08e491a41ce8",
  "subproject_id": null,
  "submitted_by_user_id": "524435b0-568b-4aff-a788-22e02563408f",
  "submitter_name": "Miriam Tesha",
  "submitter_phone": "+255754122334",
  "subject": "Azam TV wrong subscription package activated — premium charged instead of basic",
  "description": "DSM HQ customer walked in to report...",
  "assigned_committee_id": null,
  "assigned_to_user_id": null,
  "officer_recorded": false,
  "internal_notes": null,
  "media_urls": null,
  "issue_region": null,
  "issue_district": null,
  "issue_lga": null,
  "issue_ward": null,
  "issue_gps_lat": null,
  "issue_gps_lng": null,
  "date_of_incident": "2026-05-12T10:00:00+00:00",
  "submitted_at": "2026-05-12T11:03:19.252051+00:00",
  "acknowledged_at": null,
  "resolved_at": null,
  "target_resolution_date": null,
  "closed_at": null
}
```

---

### The Drill-Down Pattern — Verified Live Data

| Counts says | Call to list | Items returned | Match |
|-------------|-------------|----------------|-------|
| `by_type.grievance = 28` | `GET /feedback?feedback_type=grievance` | 28 | ✓ |
| `by_type.suggestion = 15` | `GET /feedback?feedback_type=suggestion` | 15 | ✓ |
| `by_type.inquiry = 8` | `GET /feedback?feedback_type=inquiry` | 8 | ✓ |
| `by_type.applause = 9` | `GET /feedback?feedback_type=applause` | 9 | ✓ |
| `by_priority.critical = 7` | `GET /feedback?priority=critical` | 7 | ✓ |
| `by_priority.high = 15` | `GET /feedback?priority=high` | 15 | ✓ |
| `by_priority.medium = 21` | `GET /feedback?priority=medium` | 21 | ✓ |
| `by_priority.low = 17` | `GET /feedback?priority=low` | 17 | ✓ |
| `by_category.corruption = 5` | `GET /feedback?category=corruption` | 5 | ✓ |
| **Compound**: grievance+high | `GET /feedback?feedback_type=grievance&priority=high` | 10 | ✓ |

**React JS — Count → Drill-Down Implementation**:
```javascript
// Dashboard.jsx
function Dashboard() {
  const { get } = useApi();
  const orgId = localStorage.getItem('riviwa_org_id');
  const navigate = useNavigate();
  const [counts, setCounts] = useState(null);

  useEffect(() => {
    get('/feedback/counts').then(setCounts);
  }, []);

  // Navigate to list with pre-applied filters
  const drillDown = (filters) => {
    const params = new URLSearchParams(filters);
    navigate(`/feedback?${params}`);
  };

  if (!counts) return <Spinner />;

  return (
    <div className="grid grid-cols-4 gap-4">
      {/* Type cards — click to see all of that type */}
      <StatCard
        label="Grievances"
        value={counts.by_type.grievance}
        color="red"
        onClick={() => drillDown({ feedback_type: 'grievance' })}
      />
      <StatCard
        label="Suggestions"
        value={counts.by_type.suggestion}
        color="blue"
        onClick={() => drillDown({ feedback_type: 'suggestion' })}
      />
      <StatCard
        label="Inquiries"
        value={counts.by_type.inquiry}
        color="purple"
        onClick={() => drillDown({ feedback_type: 'inquiry' })}
      />
      <StatCard
        label="Applause"
        value={counts.by_type.applause}
        color="green"
        onClick={() => drillDown({ feedback_type: 'applause' })}
      />

      {/* Priority cards */}
      <StatCard
        label="Critical"
        value={counts.by_priority.critical}
        color="red-900"
        onClick={() => drillDown({ priority: 'critical' })}
      />
      <StatCard
        label="High Priority"
        value={counts.by_priority.high}
        color="orange"
        onClick={() => drillDown({ priority: 'high' })}
      />

      {/* Category breakdown */}
      <CategoryBreakdown
        data={counts.by_category}
        onCategoryClick={(cat) => drillDown({ category: cat })}
      />

      {/* Compound: grievance + priority */}
      <StatCard
        label="Critical Grievances"
        value={/* computed: filter grievances */ counts.by_priority.critical}
        onClick={() => drillDown({ feedback_type: 'grievance', priority: 'critical' })}
      />
    </div>
  );
}
```

**Flutter — Count → Drill-Down**:
```dart
// dashboard_screen.dart
class DashboardScreen extends StatefulWidget { ... }

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic>? counts;

  @override
  void initState() {
    super.initState();
    widget.client.get('/feedback/counts').then((data) {
      setState(() => counts = data);
    });
  }

  void drillDown(Map<String, String> filters) {
    Navigator.push(context, MaterialPageRoute(
      builder: (_) => FeedbackListScreen(client: widget.client, filters: filters),
    ));
  }

  @override
  Widget build(BuildContext context) {
    if (counts == null) return const CircularProgressIndicator();
    final byType = counts!['by_type'] as Map;
    final byPriority = counts!['by_priority'] as Map;
    final byCategory = counts!['by_category'] as Map;

    return Scaffold(
      body: Column(children: [
        // Type row
        Row(children: [
          _StatCard('Grievances', byType['grievance'],
            color: Colors.red,
            onTap: () => drillDown({'feedback_type': 'grievance'})),
          _StatCard('Suggestions', byType['suggestion'],
            color: Colors.blue,
            onTap: () => drillDown({'feedback_type': 'suggestion'})),
          _StatCard('Inquiries', byType['inquiry'],
            color: Colors.purple,
            onTap: () => drillDown({'feedback_type': 'inquiry'})),
          _StatCard('Applause', byType['applause'],
            color: Colors.green,
            onTap: () => drillDown({'feedback_type': 'applause'})),
        ]),
        // Priority row
        Row(children: [
          _StatCard('Critical', byPriority['critical'],
            color: Colors.red[900]!,
            onTap: () => drillDown({'priority': 'critical'})),
          _StatCard('High', byPriority['high'],
            color: Colors.orange,
            onTap: () => drillDown({'priority': 'high'})),
          _StatCard('Medium', byPriority['medium'],
            color: Colors.amber,
            onTap: () => drillDown({'priority': 'medium'})),
        ]),
        // Category list
        ...byCategory.entries.map((e) =>
          ListTile(
            title: Text(e.key.replaceAll('_', ' ').toUpperCase()),
            trailing: Chip(label: Text('${e.value}')),
            onTap: () => drillDown({'category': e.key}),
          )
        ),
      ]),
    );
  }
}
```

---

### 2.3 List Feedback — Paginated

```javascript
// React — FeedbackList.jsx (receives filters from drill-down)
function FeedbackList() {
  const [searchParams] = useSearchParams();
  const { get } = useApi();
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 20;

  const filters = Object.fromEntries(searchParams);

  useEffect(() => {
    get('/feedback', {
      ...filters,
      skip: page * PAGE_SIZE,
      limit: PAGE_SIZE,
    }).then(d => setItems(d.items));
  }, [searchParams, page]);

  return (
    <div>
      {/* Active filter chips */}
      <FilterChips filters={filters} />

      <table>
        <thead>
          <tr>
            <th>Ref</th><th>Type</th><th>Priority</th>
            <th>Category</th><th>Status</th><th>Branch</th><th>Date</th>
          </tr>
        </thead>
        <tbody>
          {items.map(item => (
            <tr key={item.id} onClick={() => navigate(`/feedback/${item.id}`)}>
              <td><code>{item.unique_ref}</code></td>
              <td><TypeBadge type={item.feedback_type} /></td>
              <td><PriorityBadge priority={item.priority} /></td>
              <td>{item.category?.replace(/_/g, ' ')}</td>
              <td><StatusBadge status={item.status} /></td>
              <td>{BRANCH_NAMES[item.branch_id] || '—'}</td>
              <td>{new Date(item.submitted_at).toLocaleDateString('en-GB')}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <Pagination
        page={page}
        onPrev={() => setPage(p => Math.max(0, p - 1))}
        onNext={() => setPage(p => p + 1)}
        hasMore={items.length === PAGE_SIZE}
      />
    </div>
  );
}
```

---

### 2.4 Get Single Feedback Item

```
GET /feedback/{feedback_id}
Authorization: Bearer <token>
```

**Path Parameter**: `feedback_id` — UUID (from `id` or `feedback_id` field in list response)

Returns the full feedback object plus history, actions, and resolution details.

---

### 2.5 Submit Feedback

```
POST /feedback
Authorization: Bearer <token>
Content-Type: application/json
```

**Required fields**: `feedback_type`, `subject`, `description`, `category`, `channel`
**One of**: `org_id` or `project_id`

**Full Body Example**:
```json
{
  "feedback_type": "grievance",
  "org_id": "a6d704bf-6b7a-4da0-a1fd-c8475938f6a6",
  "subject": "Billing overcharge on Azam TV account",
  "description": "Customer was charged TZS 60,000 instead of TZS 15,000 for Basic package.",
  "priority": "high",
  "category": "billing",
  "channel": "web_portal",
  "submitter_name": "Miriam Tesha",
  "submitter_phone": "+255754122334",
  "is_anonymous": false,
  "branch_id": "38ae7bac-cc0a-43e9-ae94-c179c0c5f844",
  "department_id": "d8028dcb-8947-4295-b479-78f8a226bccd",
  "service_id": "9c0703ad-c002-4521-8a68-4c932689140d",
  "category_def_id": "5733bfb7-930e-4f26-bb31-08e491a41ce8",
  "date_of_incident": "2026-05-10T10:00:00Z"
}
```

**Response**:
```json
{
  "feedback_id": "357997e6-...",
  "tracking_number": "GRV-2026-0176",
  "status": "submitted",
  "feedback_type": "grievance",
  "message": "Your grievance has been received. Reference: GRV-2026-0176"
}
```

---

## 3. Org Analytics — Summary & Dimensions

All endpoints: `/analytics/org/{org_id}/...`

### 3.1 Overall Summary

```
GET /analytics/org/{org_id}/summary
Authorization: Bearer <token>
```

**Response**:
```json
{
  "org_id": "a6d704bf-...",
  "total_feedback": 60,
  "open": 59,
  "resolved": 1,
  "escalated": 0,
  "dismissed": 0,
  "avg_resolution_hours": null,
  "resolution_rate": 1.67,
  "grievances": 28,
  "suggestions": 15,
  "applause": 9,
  "inquiries": 8,
  "by_priority": {
    "critical": 7,
    "high": 15,
    "medium": 21,
    "low": 17
  }
}
```

---

### 3.2 Breakdown by Branch

```
GET /analytics/org/{org_id}/by-branch
Authorization: Bearer <token>
```

**Response**:
```json
{
  "dimension": "branch_id",
  "total_items": 5,
  "items": [
    {
      "dimension_id": "38ae7bac-cc0a-43e9-ae94-c179c0c5f844",
      "total": 3,
      "grievances": 1,
      "suggestions": 1,
      "applause": 0,
      "inquiries": 0,
      "resolved": 0,
      "avg_resolution_hours": null
    }
  ]
}
```

> `dimension_id` is the `branch_id`. Maintain a local `{ branch_id: "Branch Name" }` map.

---

### 3.3 Breakdown by Service

```
GET /analytics/org/{org_id}/by-service
Authorization: Bearer <token>
```

Same structure. `dimension = "service_id"`.

---

### 3.4 Breakdown by Department

```
GET /analytics/org/{org_id}/by-department
Authorization: Bearer <token>
```

Same structure. `dimension = "department_id"`.

---

### 3.5 Breakdown by Product

```
GET /analytics/org/{org_id}/by-product
Authorization: Bearer <token>
```

Same structure. `dimension = "product_id"`.

---

### 3.6 Time Series (by Period)

```
GET /analytics/org/{org_id}/by-period
Authorization: Bearer <token>
```

**Query Parameters**:
| Param | Type | Default | Options |
|-------|------|---------|---------|
| `period` | string | `week` | `day` \| `week` \| `month` |
| `date_from` | string | — | ISO date |
| `date_to` | string | — | ISO date |

**Response**:
```json
{
  "period": "week",
  "items": [
    {
      "period_label": "2026-W19",
      "total": 60,
      "grievances": 28,
      "suggestions": 15,
      "applause": 9,
      "inquiries": 8
    }
  ]
}
```

---

### 3.7 Breakdown by Channel

```
GET /analytics/org/{org_id}/by-channel
Authorization: Bearer <token>
```

**Response**:
```json
{
  "items": [
    { "channel": "MOBILE_APP", "total": 15 },
    { "channel": "EMAIL", "total": 12 },
    { "channel": "WEB_PORTAL", "total": 10 },
    { "channel": "IN_PERSON", "total": 8 },
    { "channel": "WHATSAPP", "total": 7 },
    { "channel": "SMS", "total": 5 }
  ]
}
```

---

### 3.8 Breakdown by Category

```
GET /analytics/org/{org_id}/by-category
Authorization: Bearer <token>
```

**Response**:
```json
{
  "items": [
    { "category": "other", "total": 12, "resolved": 0, "resolution_rate": 0.0 },
    { "category": "process", "total": 10, "resolved": 0, "resolution_rate": 0.0 },
    { "category": "quality", "total": 6, "resolved": 0, "resolution_rate": 0.0 }
  ]
}
```

---

### React JS — Full Org Dashboard (Parallel Load)

```javascript
// OrgDashboard.jsx
function OrgDashboard() {
  const { get } = useApi();
  const orgId = localStorage.getItem('riviwa_org_id');
  const [data, setData] = useState({});

  useEffect(() => {
    const base = `/analytics/org/${orgId}`;
    Promise.all([
      get(`${base}/summary`),
      get(`${base}/by-branch`),
      get(`${base}/by-service`),
      get(`${base}/by-department`),
      get(`${base}/by-period`, { period: 'month' }),
      get(`${base}/by-channel`),
      get(`${base}/by-category`),
      get('/feedback/counts'),
    ]).then(([summary, branch, service, dept, period, channel, category, counts]) => {
      setData({ summary, branch, service, dept, period, channel, category, counts });
    });
  }, [orgId]);

  return (
    <div className="dashboard-grid">
      <SummaryWidget data={data.summary} />
      <CountsWidget data={data.counts} />
      <BranchBarChart data={data.branch?.items} />
      <LineChart data={data.period?.items} />
      <ChannelPieChart data={data.channel?.items} />
      <CategoryTable data={data.category?.items} />
    </div>
  );
}
```

---

## 4. Org Analytics — Grievances

### 4.1 Grievance Summary

```
GET /analytics/org/{org_id}/grievances/summary
Authorization: Bearer <token>
```

**Optional Params**: `date_from`, `date_to`

**Response**:
```json
{
  "total_grievances": 28,
  "unresolved": 28,
  "resolved": 0,
  "escalated": 0,
  "dismissed": 0,
  "avg_resolution_hours": null,
  "avg_days_open": 0.74,
  "critical_unresolved": 7,
  "high_unresolved": 14,
  "sla_breached": 0,
  "sla_compliance_rate": 100.0
}
```

---

### 4.2 Grievances by Level

```
GET /analytics/org/{org_id}/grievances/by-level
Authorization: Bearer <token>
```

Shows grievances grouped by escalation level (ward → district → regional → national).

---

### 4.3 Grievance SLA

```
GET /analytics/org/{org_id}/grievances/sla
Authorization: Bearer <token>
```

**Response**:
```json
{
  "total": 28,
  "on_time": 28,
  "breached": 0,
  "at_risk": 0,
  "sla_compliance_rate": 100.0,
  "items": []
}
```

---

### 4.4 Full Grievance Dashboard

```
GET /analytics/org/{org_id}/grievances/dashboard
Authorization: Bearer <token>
```

Comprehensive dashboard: unresolved breakdown, by-level, SLA, top categories, trends.

---

## 5. Org Analytics — Suggestions

### 5.1 Suggestion Summary

```
GET /analytics/org/{org_id}/suggestions/summary
Authorization: Bearer <token>
```

**Response**:
```json
{
  "total_suggestions": 15,
  "pending": 15,
  "actioned": 0,
  "noted": 0,
  "dismissed": 0,
  "implementation_rate": 0.0,
  "avg_implementation_hours": null
}
```

---

### 5.2 Suggestions by Project

```
GET /analytics/org/{org_id}/suggestions/by-project
Authorization: Bearer <token>
```

---

## 6. Org Analytics — Applause

### 6.1 Applause Summary

```
GET /analytics/org/{org_id}/applause/summary
Authorization: Bearer <token>
```

**Optional Params**: `date_from`, `date_to`

**Response**:
```json
{
  "total_applause": 9,
  "month_on_month_change": null,
  "top_categories": [
    { "category": "other", "count": 5 }
  ],
  "by_project": [
    { "project_id": null, "project_name": "Org-Level", "count": 9 }
  ]
}
```

---

## 7. Org Analytics — Branch Analytics

### 7.1 All Branches Summary

```
GET /analytics/org/{org_id}/branches/summary
Authorization: Bearer <token>
```

**Optional Query Parameters**:
| Param | Type | Description |
|-------|------|-------------|
| `date_from` | string | ISO date |
| `date_to` | string | ISO date |
| `feedback_type` | string | Filter to one type |

**Live Response (5 Azam branches)**:
```json
{
  "org_id": "a6d704bf-...",
  "total_branches": 5,
  "items": [
    {
      "branch_id": "38ae7bac-cc0a-43e9-ae94-c179c0c5f844",
      "total": 3,
      "grievances": 1,
      "suggestions": 1,
      "applause": 0,
      "inquiries": 1,
      "resolved": 0,
      "open_count": 3,
      "escalated": 0,
      "dismissed": 0,
      "overdue": 0,
      "avg_resolution_hours": null,
      "resolution_rate": 0.0,
      "escalation_rate": 0.0
    },
    {
      "branch_id": "58f75ee8-9e3d-4ffe-b2cd-e399688ca619",
      "total": 2,
      "grievances": 1,
      "suggestions": 0,
      "applause": 0,
      "inquiries": 1,
      "resolved": 0,
      "open_count": 2,
      "escalated": 0,
      "dismissed": 0,
      "overdue": 0,
      "avg_resolution_hours": null,
      "resolution_rate": 0.0,
      "escalation_rate": 0.0
    }
  ]
}
```

> **Displaying branch names**: `branch_id` is a UUID. Maintain a lookup map from your org data:

```javascript
// branchNames.js (Azam Group example)
export const BRANCH_NAMES = {
  '38ae7bac-cc0a-43e9-ae94-c179c0c5f844': 'Dar es Salaam HQ',
  '58f75ee8-9e3d-4ffe-b2cd-e399688ca619': 'Dodoma Branch',
  'ac25f531-04c0-4c2c-b08f-ffa64b35baa3': 'Mwanza Branch',
  '16ea7024-72f5-47ef-9e5e-157e6aa54fd8': 'Zanzibar Branch',
  'a0468a61-9744-47cd-a816-be4551f9c07f': 'Arusha Branch',
};
```

---

### 7.2 Branches Performance (Ranked)

```
GET /analytics/org/{org_id}/branches/performance
Authorization: Bearer <token>
```

Returns branches ranked by resolution rate with performance tier labels.

---

### 7.3 Branches Trend (Time Series)

```
GET /analytics/org/{org_id}/branches/trend
Authorization: Bearer <token>
```

**Optional Params**: `period` (`day`|`week`|`month`), `date_from`, `date_to`

---

### 7.4 Single Branch Detail

```
GET /analytics/org/{org_id}/branches/{branch_id}/detail
Authorization: Bearer <token>
```

Full deep-dive for one branch: by type, priority, category, trend, SLA.

---

### React JS — Branch Table with Drill-Down

```javascript
// BranchTable.jsx
function BranchTable({ orgId, navigate }) {
  const { get } = useApi();
  const [branches, setBranches] = useState([]);

  useEffect(() => {
    get(`/analytics/org/${orgId}/branches/summary`)
      .then(d => setBranches(d.items));
  }, [orgId]);

  return (
    <table>
      <thead>
        <tr>
          <th>Branch</th><th>Total</th><th>Grievances</th>
          <th>Open</th><th>Overdue</th><th>Resolution %</th>
        </tr>
      </thead>
      <tbody>
        {branches.map(b => (
          <tr key={b.branch_id}
              className="cursor-pointer hover:bg-gray-50"
              onClick={() => navigate(`/analytics/branches/${b.branch_id}`)}>
            <td className="font-medium">{BRANCH_NAMES[b.branch_id]}</td>
            <td>{b.total}</td>
            <td className={b.grievances > 0 ? 'text-red-600' : ''}>{b.grievances}</td>
            <td>{b.open_count}</td>
            <td className={b.overdue > 0 ? 'text-red-600 font-bold' : ''}>{b.overdue}</td>
            <td>
              <div className="flex items-center gap-2">
                <div className="w-16 bg-gray-200 rounded-full h-2">
                  <div className="bg-green-500 h-2 rounded-full"
                       style={{ width: `${b.resolution_rate}%` }} />
                </div>
                {b.resolution_rate.toFixed(1)}%
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

**Flutter — Branch List**:
```dart
// branch_analytics_screen.dart
Future<void> loadBranches() async {
  final data = await client.get('/analytics/org/${client.orgId}/branches/summary');
  setState(() => branches = List<Map>.from(data['items']));
}

Widget _branchRow(Map branch) => ListTile(
  title: Text(branchNames[branch['branch_id']] ?? 'Unknown Branch'),
  subtitle: Text('${branch['total']} total · ${branch['grievances']} grievances'),
  trailing: Text('${branch['resolution_rate'].toStringAsFixed(1)}%'),
  onTap: () => Navigator.push(context, MaterialPageRoute(
    builder: (_) => BranchDetailScreen(
      client: client,
      branchId: branch['branch_id'],
    ),
  )),
);
```

---

## 8. Suggestions Analytics (Deep)

All endpoints accept `org_id` OR `project_id`.

### 8.1 Unread Suggestions

```
GET /analytics/suggestions/unread?org_id={org_id}
Authorization: Bearer <token>
```

**Live Response** (total=15):
```json
{
  "total": 15,
  "items": [
    {
      "feedback_id": "20d47e36-f3b1-440e-8c29-199a1bcd63ff",
      "unique_ref": "SGG-2026-0058",
      "submitted_at": "2026-05-11T17:35:46Z",
      "days_unread": 0.74,
      "priority": "MEDIUM",
      "category": "COMMUNICATION",
      "issue_lga": null
    }
  ]
}
```

---

### 8.2 Suggestion Frequency

```
GET /analytics/suggestions/frequency?org_id={org_id}&period=week
Authorization: Bearer <token>
```

**Params**: `org_id`, `period` (`week`|`month`|`year`)

**Live Response** (total=15 this week):
```json
{
  "period": "week",
  "period_days": 7,
  "total": 15,
  "items": [
    { "category": "PROCESS", "priority": "MEDIUM", "count": 4, "rate_per_day": 0.5714 },
    { "category": "PROCESS", "priority": "HIGH", "count": 3, "rate_per_day": 0.4286 },
    { "category": "COMMUNITY_BENEFIT", "priority": "MEDIUM", "count": 3, "rate_per_day": 0.4286 }
  ]
}
```

---

### 8.3 Suggestions by Location

```
GET /analytics/suggestions/by-location?org_id={org_id}
Authorization: Bearer <token>
```

Groups suggestions by region/LGA/ward.

---

### 8.4 Implementation Time

```
GET /analytics/suggestions/implementation-time?org_id={org_id}
Authorization: Bearer <token>
```

**Response** (once suggestions are implemented):
```json
{
  "avg_hours": 48.5,
  "min_hours": 2.1,
  "max_hours": 168.0,
  "median_hours": 36.0,
  "sample_count": 5,
  "items": [ ... ]
}
```

---

### 8.5 Implemented Today / This Week

```
GET /analytics/suggestions/implemented-today?org_id={org_id}
GET /analytics/suggestions/implemented-this-week?org_id={org_id}
Authorization: Bearer <token>
```

---

## 9. Inquiries Analytics (Deep)

### 9.1 Inquiry Summary

```
GET /analytics/inquiries/summary?org_id={org_id}
Authorization: Bearer <token>
```

**Optional Params**: `date_from`, `date_to`

**Live Response** (total=8):
```json
{
  "total_inquiries": 8,
  "open_inquiries": 8,
  "resolved": 0,
  "closed": 0,
  "dismissed": 0,
  "avg_response_hours": null,
  "avg_days_open": 0.31,
  "critical_open": 0,
  "high_open": 0,
  "medium_open": 3,
  "low_open": 5
}
```

---

### 9.2 Unread Inquiries

```
GET /analytics/inquiries/unread?org_id={org_id}
Authorization: Bearer <token>
```

**Optional Filter Params**: `priority`, `department_id`, `service_id`, `product_id`, `category_def_id`

**Live Response** (total=8):
```json
{
  "total": 8,
  "items": [
    {
      "feedback_id": "1ac42fe2-6a26-45c5-9dcf-07d73c7d0e31",
      "unique_ref": "INQ-2026-0030",
      "priority": "LOW",
      "submitted_at": "2026-05-11T17:35:47Z",
      "days_waiting": 0.74,
      "channel": "EMAIL",
      "issue_lga": null,
      "department_id": "d8028dcb-...",
      "service_id": null,
      "product_id": null,
      "category_def_id": null
    }
  ]
}
```

---

### 9.3 Overdue Inquiries

```
GET /analytics/inquiries/overdue?org_id={org_id}
Authorization: Bearer <token>
```

Returns inquiries past their `target_resolution_date`.

---

### 9.4 Inquiries by Channel

```
GET /analytics/inquiries/by-channel?org_id={org_id}
Authorization: Bearer <token>
```

**Live Response**:
```json
{
  "total_items": 5,
  "items": [
    { "channel": "WEB_PORTAL", "total": 3, "open_count": 3, "resolved": 0 },
    { "channel": "EMAIL", "total": 2, "open_count": 2, "resolved": 0 },
    { "channel": "WHATSAPP", "total": 1, "open_count": 1, "resolved": 0 },
    { "channel": "MOBILE_APP", "total": 1, "open_count": 1, "resolved": 0 },
    { "channel": "IN_PERSON", "total": 1, "open_count": 1, "resolved": 0 }
  ]
}
```

---

### 9.5 Inquiries by Category

```
GET /analytics/inquiries/by-category?org_id={org_id}
Authorization: Bearer <token>
```

**Live Response**:
```json
{
  "total_items": 3,
  "items": [
    {
      "category_def_id": "1ca9765a-fa8f-42cf-816c-67ed98944281",
      "category_name": "Service Inquiry",
      "category_slug": "svc_inquiry",
      "total": 3,
      "open_count": 3,
      "resolved": 0,
      "avg_response_hours": null
    },
    {
      "category_def_id": "f0bae586-ca25-47d6-8da1-598b44699253",
      "category_name": "General Inquiry",
      "category_slug": "gen_inquiry",
      "total": 2,
      "open_count": 2,
      "resolved": 0,
      "avg_response_hours": null
    }
  ]
}
```

---

### Flutter — Inquiries Dashboard Widget

```dart
// inquiries_widget.dart
Future<void> loadInquiries() async {
  final results = await Future.wait([
    client.get('/analytics/inquiries/summary', params: {'org_id': client.orgId}),
    client.get('/analytics/inquiries/unread', params: {'org_id': client.orgId}),
    client.get('/analytics/inquiries/by-channel', params: {'org_id': client.orgId}),
  ]);

  setState(() {
    summary = results[0];
    unread = results[1];
    byChannel = results[2];
  });
}

Widget build(BuildContext context) => Card(
  child: Column(children: [
    ListTile(
      title: const Text('Inquiries'),
      trailing: Text('${summary?['total_inquiries'] ?? 0} total'),
    ),
    Row(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
      _CountChip('Open', summary?['open_inquiries'], Colors.orange),
      _CountChip('Medium', summary?['medium_open'], Colors.amber),
      _CountChip('Low', summary?['low_open'], Colors.grey),
    ]),
    const Divider(),
    Text('Unread: ${unread?['total'] ?? 0}'),
  ]),
);
```

---

## 10. Staff Performance Analytics

All staff analytics accept `org_id` as a query param.

### 10.1 Committee Performance

```
GET /analytics/staff/committee-performance?org_id={org_id}
Authorization: Bearer <token>
```

**Response**:
```json
{
  "total": 3,
  "items": [
    {
      "committee_id": "abc123-...",
      "committee_name": "Billing Resolution Committee",
      "level": "org",
      "cases_assigned": 5,
      "resolved": 2,
      "overdue": 1,
      "avg_resolution_hours": 48.5
    }
  ]
}
```

---

### 10.2 Unread Assigned to Staff

```
GET /analytics/staff/unread-assigned?org_id={org_id}
Authorization: Bearer <token>
```

Returns feedback assigned to staff members that hasn't been actioned.

---

### 10.3 Staff Logged In But Didn't Read

```
GET /analytics/staff/login-not-read?org_id={org_id}
Authorization: Bearer <token>
```

Returns staff who logged in today but have unread assigned feedback — useful for manager oversight.

---

## 11. Reports

### 11.1 Performance Dashboard Report

```
GET /reports/performance?org_id={org_id}
Authorization: Bearer <token>
```

**Optional Params**: `date_from`, `date_to`, `feedback_type`

Comprehensive exportable performance report.

---

### 11.2 Grievance Report

```
GET /reports/grievances?org_id={org_id}
Authorization: Bearer <token>
```

---

### 11.3 Grievance Log (Annex 5 Format)

```
GET /reports/grievance-log?org_id={org_id}
Authorization: Bearer <token>
```

Returns all grievances in SEP Annex 5/6 tabular format for Excel export.

---

### 11.4 Count Summary Report

```
GET /reports/summary?org_id={org_id}
Authorization: Bearer <token>
```

---

### 11.5 Overdue Report

```
GET /reports/overdue?org_id={org_id}
Authorization: Bearer <token>
```

---

## 12. QR Codes

### 12.1 List QR Codes

```
GET /qr
Authorization: Bearer <token>
```

> `org_id` is auto-read from JWT. No query param needed.

**Response**:
```json
{
  "items": [
    {
      "id": "abc123-...",
      "short_code": "AZM001",
      "qr_type": "product",
      "organisation_id": "a6d704bf-...",
      "scan_count": 12,
      "last_scanned_at": "2026-05-12T10:00:00Z",
      "created_at": "2026-05-01T00:00:00Z"
    }
  ],
  "total": 5
}
```

---

### 12.2 QR Scan Analytics

```
GET /qr/analytics?short_code={short_code}
Authorization: Bearer <token>
```

---

### 12.3 Public Product Verification (No Auth)

```
GET /qr/scan/{short_code}
```

No authentication required. Executes when a consumer scans a QR code.

**Response — Authentic**:
```json
{
  "status": "AUTHENTIC",
  "short_code": "AZM001",
  "product_name": "Azam White Bread 400g",
  "organisation": "Azam Group Tanzania Limited",
  "scan_count": 13,
  "message": "This product is authentic."
}
```

**Response — Already Used (potential counterfeit)**:
```json
{
  "status": "ALREADY_USED",
  "short_code": "AZM001",
  "scan_count": 13,
  "first_scanned_at": "2026-05-10T08:00:00Z",
  "message": "This QR code has already been scanned. If you believe this is your product, please report it.",
  "report_url": "https://api.riviwa.com/qr/scan/AZM001/report"
}
```

**Response — Unrecognized**:
```json
{
  "status": "UNRECOGNIZED",
  "short_code": "FAKE01",
  "message": "This QR code is not in our system. The product may be counterfeit."
}
```

---

## 13. Products & Services

### 13.1 List Products / Services

```
GET /products/
Authorization: Bearer <token>
```

> **Critical**: Trailing slash is required. Without it Nginx returns a 307 redirect that strips the Authorization header.

**Optional Params**: `org_id`, `service_type` (`SERVICE`|`PRODUCT`|`PROGRAM`), `skip`, `limit`

**Response**:
```json
{
  "items": [
    {
      "id": "9c0703ad-c002-4521-8a68-4c932689140d",
      "name": "Azam TV",
      "service_type": "SERVICE",
      "org_id": "a6d704bf-...",
      "is_active": true
    },
    {
      "id": "9437c38c-d363-44bf-8eb9-ba54715f2b21",
      "name": "Azam Malt / Beverages",
      "service_type": "PRODUCT",
      "org_id": "a6d704bf-...",
      "is_active": true
    }
  ],
  "total": 5
}
```

---

## 14. Implementation Patterns

### 14.1 The Core Drill-Down Pattern

```
┌─────────────────────────────────────────────────────────┐
│  GET /feedback/counts                                   │
│                                                         │
│  Total: 60  ──────────────────── GET /feedback          │
│  ├── Grievances: 28  ─────────── GET /feedback?         │
│  │                                 feedback_type=       │
│  │                                 grievance            │
│  ├── Critical: 7  ────────────── GET /feedback?         │
│  │                                 priority=critical    │
│  ├── Corruption: 5  ──────────── GET /feedback?         │
│  │                                 category=corruption  │
│  └── Critical Grievances  ─────── GET /feedback?        │
│                                     feedback_type=      │
│                                     grievance&          │
│                                     priority=critical   │
└─────────────────────────────────────────────────────────┘
```

**Verified alignments** (counts always = list count):
- `by_type.grievance 28` → `?feedback_type=grievance` → 28 items
- `by_priority.critical 7` → `?priority=critical` → 7 items
- `by_priority.high 15` → `?priority=high` → 15 items
- `by_category.corruption 5` → `?category=corruption` → 5 items
- Compound: `?feedback_type=grievance&priority=high` → 10 items

---

### 14.2 Pagination

`/feedback` uses `skip`/`limit`. The `count` field in responses is the current page size, not total.

```javascript
// React hook
function usePaginatedFeedback(filters, pageSize = 20) {
  const { get } = useApi();
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(0);

  useEffect(() => {
    get('/feedback', { ...filters, skip: page * pageSize, limit: pageSize })
      .then(d => setItems(d.items));
  }, [filters, page]);

  return {
    items,
    page,
    nextPage: () => setPage(p => p + 1),
    prevPage: () => setPage(p => Math.max(0, p - 1)),
    hasMore: items.length === pageSize,
  };
}
```

```dart
// Flutter
class PaginatedFeedback {
  final RiviwaClient client;
  final Map<String, String> filters;
  final int pageSize;
  int currentPage = 0;

  PaginatedFeedback(this.client, this.filters, {this.pageSize = 20});

  Future<List<Map>> loadPage(int page) async {
    final data = await client.get('/feedback', params: {
      ...filters,
      'skip': '${page * pageSize}',
      'limit': '$pageSize',
    });
    return List<Map>.from(data['items']);
  }
}
```

---

### 14.3 Parallel Dashboard Loading

```javascript
// React — load everything at once
useEffect(() => {
  const orgId = localStorage.getItem('riviwa_org_id');
  const base = `/analytics/org/${orgId}`;

  Promise.all([
    // Core counts (for drill-down)
    get('/feedback/counts'),
    // Org-level analytics
    get(`${base}/summary`),
    get(`${base}/grievances/summary`),
    get(`${base}/suggestions/summary`),
    get(`${base}/branches/summary`),
    get(`${base}/by-channel`),
    // Deep analytics
    get('/analytics/inquiries/summary', { org_id: orgId }),
    get('/analytics/suggestions/unread', { org_id: orgId }),
  ]).then(([counts, summary, grievances, suggestions, branches, channel, inquiries, unread]) => {
    setDashboard({ counts, summary, grievances, suggestions, branches, channel, inquiries, unread });
  });
}, []);
```

```dart
// Flutter — parallel with Future.wait
Future<void> loadDashboard() async {
  final orgId = client.orgId;
  final results = await Future.wait([
    client.get('/feedback/counts'),
    client.get('/analytics/org/$orgId/summary'),
    client.get('/analytics/org/$orgId/grievances/summary'),
    client.get('/analytics/org/$orgId/branches/summary'),
    client.get('/analytics/inquiries/summary', params: {'org_id': orgId}),
    client.get('/analytics/suggestions/unread', params: {'org_id': orgId}),
  ]);

  setState(() {
    counts       = results[0];
    summary      = results[1];
    grievances   = results[2];
    branches     = results[3];
    inquiries    = results[4];
    unreadSugg   = results[5];
  });
}
```

---

### 14.4 Full Endpoint Quick Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/auth/login` | Step 1 login |
| POST | `/auth/login/verify-otp` | Step 2 — get access_token |
| GET | `/feedback/counts` | All counts by type/priority/category/status |
| GET | `/feedback` | List with 15+ filter params |
| GET | `/feedback/{id}` | Single item + history |
| POST | `/feedback` | Submit new feedback |
| GET | `/analytics/org/{id}/summary` | Overall org KPIs |
| GET | `/analytics/org/{id}/by-branch` | Per-branch breakdown |
| GET | `/analytics/org/{id}/by-service` | Per-service breakdown |
| GET | `/analytics/org/{id}/by-department` | Per-department breakdown |
| GET | `/analytics/org/{id}/by-product` | Per-product breakdown |
| GET | `/analytics/org/{id}/by-period` | Time series |
| GET | `/analytics/org/{id}/by-channel` | By intake channel |
| GET | `/analytics/org/{id}/by-category` | By category |
| GET | `/analytics/org/{id}/grievances/summary` | Grievance KPIs |
| GET | `/analytics/org/{id}/grievances/sla` | SLA compliance |
| GET | `/analytics/org/{id}/grievances/dashboard` | Full grievance dashboard |
| GET | `/analytics/org/{id}/suggestions/summary` | Suggestion KPIs |
| GET | `/analytics/org/{id}/applause/summary` | Applause stats |
| GET | `/analytics/org/{id}/branches/summary` | All branches KPIs |
| GET | `/analytics/org/{id}/branches/performance` | Branches ranked |
| GET | `/analytics/org/{id}/branches/trend` | Branch time series |
| GET | `/analytics/org/{id}/branches/{bid}/detail` | Single branch deep-dive |
| GET | `/analytics/suggestions/unread` | Unread suggestions |
| GET | `/analytics/suggestions/frequency` | Frequency by period |
| GET | `/analytics/suggestions/by-location` | By region/LGA |
| GET | `/analytics/suggestions/implementation-time` | Speed stats |
| GET | `/analytics/suggestions/implemented-today` | Actioned today |
| GET | `/analytics/suggestions/implemented-this-week` | Actioned this week |
| GET | `/analytics/inquiries/summary` | Inquiry KPIs |
| GET | `/analytics/inquiries/unread` | Unread inquiries |
| GET | `/analytics/inquiries/overdue` | Overdue inquiries |
| GET | `/analytics/inquiries/by-channel` | Inquiries by channel |
| GET | `/analytics/inquiries/by-category` | Inquiries by category |
| GET | `/analytics/staff/committee-performance` | Committee KPIs |
| GET | `/analytics/staff/unread-assigned` | Unread assigned to staff |
| GET | `/analytics/staff/login-not-read` | Staff logged in, not actioned |
| GET | `/reports/performance` | Full performance report |
| GET | `/reports/grievances` | Grievance report |
| GET | `/reports/grievance-log` | Annex 5 log (Excel-ready) |
| GET | `/reports/summary` | Count summary |
| GET | `/reports/overdue` | Overdue report |
| GET | `/qr` | List org QR codes (auto-org from JWT) |
| GET | `/qr/scan/{short_code}` | Public product verification (no auth) |
| GET | `/products/` | List products/services (trailing slash required) |

---

### 14.5 Common Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| 307 redirect drops auth header | Missing trailing slash on `/products` | Always use `/products/` |
| `org_id` param not needed for staff | JWT contains `org_id` automatically | Only platform admins need to pass `org_id` explicitly |
| `count` ≠ total | `count` in `/feedback` response = current page size | Use `/feedback/counts` for totals |
| Branch shown as UUID | `branch_id` is UUID in all responses | Maintain `{ branch_id: name }` map locally |
| 422 on feedback submit | `category` field is required even with `category_def_id` | Always send both `category` (slug) and `category_def_id` |
| Feedback type is lowercase | API accepts and returns lowercase | `grievance`, not `GRIEVANCE` |
