# Riviwa Feedback Counts & Drill-Down API
**Pattern**: Count → Filter → List · **Verified**: 2026-05-12 · **Base URL**: `https://api.riviwa.com/api/v1`

> This document covers the core drill-down pattern: get summary counts in one call, then fetch the matching records with identical filters. All counts are **verified to be perfectly aligned** with the list — clicking "28 Grievances" returns exactly 28 items.

---

## How the Pattern Works

```
Step 1: One call gives ALL summary numbers
  GET /feedback/counts

  Response: {
    total: 60,
    by_type:     { grievance: 28, suggestion: 15, inquiry: 8, applause: 9 },
    by_priority: { critical: 7, high: 15, medium: 21, low: 17 },
    by_status:   { submitted: 59, acknowledged: 1 },
    by_category: { corruption: 5, quality: 6, process: 10, ... }
  }

Step 2: User taps "28 Grievances" → drill down
  GET /feedback?feedback_type=grievance      → returns exactly 28 items ✓

Step 3: User taps "7 Critical" → drill down
  GET /feedback?priority=critical            → returns exactly 7 items ✓

Step 4: User taps "Corruption (5)" → drill down
  GET /feedback?category=corruption          → returns exactly 5 items ✓

Step 5: Compound — "High Grievances"
  GET /feedback?feedback_type=grievance&priority=high  → returns exactly 10 items ✓
```

---

## GET /feedback/counts

```
GET /feedback/counts
Authorization: Bearer <token>
```

Returns summary totals broken down by 4 dimensions simultaneously.

### Query Parameters

| Param | Type | Purpose |
|-------|------|---------|
| `org_id` | UUID | Organisation (auto from JWT for staff — optional) |
| `feedback_type` | string | Pre-filter before counting |
| `priority` | string | Pre-filter to one priority |
| `category` | string | Pre-filter to one category |
| `status` | string | Pre-filter to one status |
| `department_id` | UUID | Pre-filter to one department |
| `service_id` | UUID | Pre-filter to one service |
| `product_id` | UUID | Pre-filter to one product |
| `date_from` | string | ISO date `YYYY-MM-DD` |
| `date_to` | string | ISO date `YYYY-MM-DD` |

### Full Live Response (Azam Group)

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

### Scoped Count Examples

```bash
# Count only grievances — see breakdown within grievances only
GET /feedback/counts?feedback_type=grievance
# → { total: 28, by_priority: {critical:4, high:10, ...}, by_category: {...} }

# Count only critical items
GET /feedback/counts?priority=critical
# → { total: 7, by_type: {grievance:4, ...}, by_category: {...} }

# Count for a date range
GET /feedback/counts?date_from=2026-05-12&date_to=2026-05-13
# → { total: 39, by_type: {grievance:18, suggestion:10, applause:6, inquiry:5} }

# Count for a specific department
GET /feedback/counts?department_id=d8028dcb-8947-4295-b479-78f8a226bccd
# → { total: 6, ... }
```

---

## GET /feedback (The Drill-Down List)

```
GET /feedback
Authorization: Bearer <token>
```

### All Filter Parameters

| Param | Type | Default | Values |
|-------|------|---------|--------|
| `org_id` | UUID | from JWT | Organisation UUID |
| `feedback_type` | string | — | `grievance` \| `suggestion` \| `applause` \| `inquiry` |
| `priority` | string | — | `critical` \| `high` \| `medium` \| `low` |
| `category` | string | — | see category slugs below |
| `status` | string | — | `submitted` \| `acknowledged` \| `in_review` \| `escalated` \| `resolved` \| `closed` \| `dismissed` |
| `channel` | string | — | `in_person` \| `email` \| `web_portal` \| `mobile_app` \| `sms` \| `whatsapp` \| `phone` |
| `department_id` | UUID | — | Filter by department UUID |
| `service_id` | UUID | — | Filter by service UUID |
| `product_id` | UUID | — | Filter by product UUID |
| `branch_id` | UUID | — | Filter by branch UUID |
| `category_def_id` | UUID | — | Filter by dynamic category definition UUID |
| `lga` | string | — | LGA name (partial match) |
| `is_anonymous` | boolean | — | `true` \| `false` |
| `submission_method` | string | — | `self_service` \| `officer_assisted` |
| `assigned_committee_id` | UUID | — | Filter by assigned committee |
| `date_from` | string | — | ISO date `YYYY-MM-DD` |
| `date_to` | string | — | ISO date `YYYY-MM-DD` |
| `skip` | int | `0` | Pagination offset |
| `limit` | int | `50` | Page size (max 200) |

### Available `category` Slugs

`billing` · `quality` · `process` · `staff_conduct` · `corruption` · `safety` · `safety_hazard` · `community_benefit` · `communication` · `timeliness` · `responsiveness` · `general_inquiry` · `procedure_inquiry` · `information_request` · `other`

### Response Structure

```json
{
  "items": [
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
      "product_id": null,
      "category_def_id": "5733bfb7-930e-4f26-bb31-08e491a41ce8",
      "subproject_id": null,
      "submitter_name": "Miriam Tesha",
      "submitter_phone": "+255754122334",
      "subject": "Azam TV wrong subscription package activated",
      "description": "DSM HQ customer walked in to report...",
      "officer_recorded": false,
      "internal_notes": null,
      "media_urls": null,
      "issue_region": null,
      "issue_lga": null,
      "date_of_incident": "2026-05-12T10:00:00+00:00",
      "submitted_at": "2026-05-12T11:03:19.252051+00:00",
      "acknowledged_at": null,
      "resolved_at": null,
      "target_resolution_date": null,
      "closed_at": null
    }
  ],
  "count": 1
}
```

> **`count` = items in THIS page** (up to `limit`), NOT the total. Use `/feedback/counts` for totals.

---

## Verified Drill-Down Table (Live Data)

| Counts field | Value | List filter | Items returned |
|-------------|-------|-------------|----------------|
| `by_type.grievance` | 28 | `?feedback_type=grievance` | **28** ✓ |
| `by_type.suggestion` | 15 | `?feedback_type=suggestion` | **15** ✓ |
| `by_type.inquiry` | 8 | `?feedback_type=inquiry` | **8** ✓ |
| `by_type.applause` | 9 | `?feedback_type=applause` | **9** ✓ |
| `by_priority.critical` | 7 | `?priority=critical` | **7** ✓ |
| `by_priority.high` | 15 | `?priority=high` | **15** ✓ |
| `by_priority.medium` | 21 | `?priority=medium` | **21** ✓ |
| `by_priority.low` | 17 | `?priority=low` | **17** ✓ |
| `by_category.corruption` | 5 | `?category=corruption` | **5** ✓ |
| `by_category.quality` | 6 | `?category=quality` | **6** ✓ |
| `by_category.process` | 10 | `?category=process` | **10** ✓ |
| Compound | — | `?feedback_type=grievance&priority=high` | **10** ✓ |

---

## React JS — Complete Implementation

### api/feedback.js

```javascript
const BASE = 'https://api.riviwa.com/api/v1';

function getToken() { return localStorage.getItem('riviwa_token'); }

async function apiGet(path, params = {}) {
  const url = new URL(`${BASE}${path}`);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v));
  });
  const r = await fetch(url, { headers: { Authorization: `Bearer ${getToken()}` } });
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

export const getFeedbackCounts = (filters = {}) =>
  apiGet('/feedback/counts', filters);

export const listFeedback = (filters = {}, skip = 0, limit = 50) =>
  apiGet('/feedback', { ...filters, skip, limit });
```

### hooks/useFeedbackDrillDown.js

```javascript
import { useState, useEffect, useCallback } from 'react';
import { getFeedbackCounts, listFeedback } from '../api/feedback';

export function useFeedbackDrillDown() {
  const orgId = localStorage.getItem('riviwa_org_id');
  const [counts, setCounts] = useState(null);
  const [items, setItems] = useState([]);
  const [activeFilters, setActiveFilters] = useState({});
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 20;

  useEffect(() => {
    getFeedbackCounts().then(setCounts);
  }, []);

  const drillDown = useCallback(async (filters, pageNum = 0) => {
    setActiveFilters(filters);
    setLoading(true);
    const data = await listFeedback(filters, pageNum * PAGE_SIZE, PAGE_SIZE);
    setItems(data.items);
    setPage(pageNum);
    setLoading(false);
  }, []);

  return {
    counts,
    items,
    activeFilters,
    loading,
    page,
    hasMore: items.length === PAGE_SIZE,
    drillDown,
    nextPage: () => drillDown(activeFilters, page + 1),
    prevPage: () => page > 0 && drillDown(activeFilters, page - 1),
  };
}
```

### components/FeedbackDashboard.jsx

```jsx
import React from 'react';
import { useFeedbackDrillDown } from '../hooks/useFeedbackDrillDown';

const PRIORITY_COLORS = {
  critical: '#7f1d1d',
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#9ca3af',
};

const TYPE_ICONS = {
  grievance: '⚠️',
  suggestion: '💡',
  inquiry: '❓',
  applause: '👏',
};

export function FeedbackDashboard() {
  const { counts, items, activeFilters, loading, page,
          hasMore, drillDown, nextPage, prevPage } = useFeedbackDrillDown();

  if (!counts) return <div>Loading...</div>;

  const isActive = (filters) =>
    JSON.stringify(filters) === JSON.stringify(activeFilters);

  return (
    <div style={{ padding: 24, fontFamily: 'sans-serif', maxWidth: 1200 }}>
      <h1>Feedback Dashboard — Total: {counts.total}</h1>

      {/* ── By Type ── */}
      <section style={{ marginBottom: 24 }}>
        <h3 style={{ color: '#6b7280', textTransform: 'uppercase', fontSize: 12 }}>By Type</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          {Object.entries(counts.by_type).map(([type, count]) => (
            <div
              key={type}
              onClick={() => drillDown({ feedback_type: type })}
              style={{
                cursor: 'pointer',
                padding: 16,
                borderRadius: 8,
                border: isActive({ feedback_type: type }) ? '2px solid #3b82f6' : '1px solid #e5e7eb',
                textAlign: 'center',
                background: isActive({ feedback_type: type }) ? '#eff6ff' : 'white',
              }}
            >
              <div style={{ fontSize: 32 }}>{TYPE_ICONS[type]}</div>
              <div style={{ fontSize: 28, fontWeight: 'bold' }}>{count}</div>
              <div style={{ fontSize: 13, textTransform: 'capitalize' }}>{type}s</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── By Priority ── */}
      <section style={{ marginBottom: 24 }}>
        <h3 style={{ color: '#6b7280', textTransform: 'uppercase', fontSize: 12 }}>By Priority</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          {['critical', 'high', 'medium', 'low'].map(priority => (
            <div
              key={priority}
              onClick={() => drillDown({ priority })}
              style={{
                cursor: 'pointer',
                padding: 16,
                borderRadius: 8,
                border: isActive({ priority }) ? '2px solid #3b82f6' : '1px solid #e5e7eb',
                background: isActive({ priority })
                  ? '#eff6ff'
                  : `${PRIORITY_COLORS[priority]}15`,
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: 28, fontWeight: 'bold',
                            color: PRIORITY_COLORS[priority] }}>
                {counts.by_priority[priority]}
              </div>
              <div style={{ fontSize: 13, textTransform: 'capitalize',
                            color: PRIORITY_COLORS[priority] }}>
                {priority}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── By Category ── */}
      <section style={{ marginBottom: 24 }}>
        <h3 style={{ color: '#6b7280', textTransform: 'uppercase', fontSize: 12 }}>By Category</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
          {Object.entries(counts.by_category)
            .sort((a, b) => b[1] - a[1])
            .filter(([, v]) => v > 0)
            .map(([category, count]) => (
              <div
                key={category}
                onClick={() => drillDown({ category })}
                style={{
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 14px',
                  borderRadius: 6,
                  border: isActive({ category }) ? '2px solid #3b82f6' : '1px solid #e5e7eb',
                  background: isActive({ category }) ? '#eff6ff' : 'white',
                }}
              >
                <span style={{ textTransform: 'capitalize', fontSize: 13 }}>
                  {category.replace(/_/g, ' ')}
                </span>
                <span style={{ fontWeight: 'bold', fontSize: 16,
                               color: count > 5 ? '#ef4444' : '#374151' }}>
                  {count}
                </span>
              </div>
            ))}
        </div>
      </section>

      {/* ── Active Filters ── */}
      {Object.keys(activeFilters).length > 0 && (
        <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe',
                      borderRadius: 8, padding: 12, marginBottom: 16,
                      display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <strong>Showing:</strong>
          {Object.entries(activeFilters).map(([k, v]) => (
            <span key={k} style={{ background: '#dbeafe', padding: '2px 10px',
                                   borderRadius: 12, fontSize: 12 }}>
              {k} = {v}
            </span>
          ))}
          <button onClick={() => { setItems && drillDown({}); }}
                  style={{ marginLeft: 'auto', fontSize: 12, color: '#3b82f6',
                           background: 'none', border: 'none', cursor: 'pointer' }}>
            Clear filters
          </button>
        </div>
      )}

      {/* ── Results Table ── */}
      {items.length > 0 && (
        <section>
          <h3 style={{ color: '#6b7280', textTransform: 'uppercase', fontSize: 12 }}>
            Results ({items.length} items, page {page + 1})
          </h3>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 24, color: '#9ca3af' }}>
              Loading...
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f9fafb', color: '#6b7280' }}>
                  <th style={{ padding: '10px 12px', textAlign: 'left' }}>Ref</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left' }}>Type</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left' }}>Priority</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left' }}>Category</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left' }}>Status</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left' }}>Submitter</th>
                  <th style={{ padding: '10px 12px', textAlign: 'left' }}>Date</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, i) => (
                  <tr key={item.id} style={{
                    borderBottom: '1px solid #f3f4f6',
                    background: i % 2 === 0 ? 'white' : '#fafafa'
                  }}>
                    <td style={{ padding: '10px 12px', fontFamily: 'monospace',
                                 color: '#2563eb', fontSize: 12 }}>
                      {item.unique_ref}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        padding: '2px 8px', borderRadius: 12, fontSize: 11,
                        background: `${PRIORITY_COLORS[item.feedback_type] || '#e5e7eb'}20`,
                      }}>
                        {TYPE_ICONS[item.feedback_type]} {item.feedback_type}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        padding: '2px 8px', borderRadius: 4, fontSize: 11,
                        fontWeight: 'bold',
                        background: `${PRIORITY_COLORS[item.priority]}20`,
                        color: PRIORITY_COLORS[item.priority],
                      }}>
                        {item.priority}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', textTransform: 'capitalize' }}>
                      {item.category?.replace(/_/g, ' ')}
                    </td>
                    <td style={{ padding: '10px 12px', color: '#6b7280' }}>
                      {item.status}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      {item.is_anonymous ? 'Anonymous' : item.submitter_name}
                    </td>
                    <td style={{ padding: '10px 12px', color: '#9ca3af', fontSize: 12 }}>
                      {new Date(item.submitted_at).toLocaleDateString('en-GB')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <div style={{ display: 'flex', justifyContent: 'space-between',
                        alignItems: 'center', marginTop: 12 }}>
            <button onClick={prevPage} disabled={page === 0}
                    style={{ padding: '8px 16px', borderRadius: 6,
                             border: '1px solid #d1d5db', cursor: 'pointer',
                             opacity: page === 0 ? 0.4 : 1 }}>
              ← Previous
            </button>
            <span style={{ color: '#6b7280', fontSize: 13 }}>Page {page + 1}</span>
            <button onClick={nextPage} disabled={!hasMore}
                    style={{ padding: '8px 16px', borderRadius: 6,
                             border: '1px solid #d1d5db', cursor: 'pointer',
                             opacity: !hasMore ? 0.4 : 1 }}>
              Next →
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
```

---

## Flutter — Complete Implementation

### screens/feedback_dashboard.dart

```dart
import 'package:flutter/material.dart';

class FeedbackDashboardScreen extends StatefulWidget {
  final RiviwaClient client;
  const FeedbackDashboardScreen({super.key, required this.client});

  @override
  State<FeedbackDashboardScreen> createState() => _State();
}

class _State extends State<FeedbackDashboardScreen> {
  Map<String, dynamic>? counts;
  List<Map<String, dynamic>> items = [];
  Map<String, String> activeFilters = {};
  bool loading = false;
  int page = 0;
  static const int PAGE_SIZE = 20;

  @override
  void initState() {
    super.initState();
    _loadCounts();
  }

  Future<void> _loadCounts() async {
    final data = await widget.client.get('/feedback/counts');
    setState(() => counts = data);
  }

  Future<void> _drillDown(Map<String, String> filters, {int pageNum = 0}) async {
    setState(() { loading = true; activeFilters = filters; page = pageNum; });
    final data = await widget.client.get('/feedback', params: {
      ...filters,
      'skip': '${pageNum * PAGE_SIZE}',
      'limit': '$PAGE_SIZE',
    });
    setState(() {
      items = List<Map<String, dynamic>>.from(data['items']);
      loading = false;
    });
  }

  Color _priorityColor(String p) => switch (p) {
    'critical' => Colors.red[900]!,
    'high' => Colors.red,
    'medium' => Colors.amber[700]!,
    _ => Colors.grey,
  };

  Color _typeColor(String t) => switch (t) {
    'grievance' => Colors.red[400]!,
    'suggestion' => Colors.blue[400]!,
    'inquiry' => Colors.purple[400]!,
    'applause' => Colors.green[400]!,
    _ => Colors.grey,
  };

  @override
  Widget build(BuildContext context) {
    if (counts == null) return const Scaffold(body: Center(child: CircularProgressIndicator()));

    final byType = Map<String, int>.from(counts!['by_type']);
    final byPriority = Map<String, int>.from(counts!['by_priority']);
    final byCategory = Map<String, int>.from(counts!['by_category']);
    final total = counts!['total'] as int;

    return Scaffold(
      appBar: AppBar(
        title: Text('Feedback — Total: $total'),
        actions: [
          if (activeFilters.isNotEmpty)
            TextButton(
              onPressed: () => setState(() { activeFilters = {}; items = []; }),
              child: const Text('Clear', style: TextStyle(color: Colors.white)),
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // ── By Type ──
          const _SectionHeader('BY TYPE'),
          const SizedBox(height: 8),
          Row(
            children: byType.entries.map((e) => Expanded(
              child: _CountCard(
                label: '${e.key}s',
                value: e.value,
                color: _typeColor(e.key),
                active: activeFilters == {'feedback_type': e.key},
                onTap: () => _drillDown({'feedback_type': e.key}),
              ),
            )).toList(),
          ),
          const SizedBox(height: 16),

          // ── By Priority ──
          const _SectionHeader('BY PRIORITY'),
          const SizedBox(height: 8),
          Row(
            children: ['critical', 'high', 'medium', 'low'].map((p) => Expanded(
              child: _CountCard(
                label: p,
                value: byPriority[p] ?? 0,
                color: _priorityColor(p),
                active: activeFilters == {'priority': p},
                onTap: () => _drillDown({'priority': p}),
              ),
            )).toList(),
          ),
          const SizedBox(height: 16),

          // ── By Category ──
          const _SectionHeader('BY CATEGORY'),
          const SizedBox(height: 8),
          ...byCategory.entries
            .where((e) => e.value > 0)
            .toList()
            .sortedBy((e) => -e.value)
            .map((e) => ListTile(
              title: Text(
                e.key.replaceAll('_', ' ').toUpperCase(),
                style: const TextStyle(fontSize: 13),
              ),
              trailing: Chip(
                label: Text(
                  '${e.value}',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: e.value > 5 ? Colors.red : Colors.black87),
                ),
                backgroundColor: e.value > 5 ? Colors.red[50] : Colors.grey[100],
              ),
              selected: activeFilters == {'category': e.key},
              selectedTileColor: Colors.blue[50],
              onTap: () => _drillDown({'category': e.key}),
            )),
          const SizedBox(height: 16),

          // ── Active Filter Badge ──
          if (activeFilters.isNotEmpty) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.blue[50],
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.blue[200]!),
              ),
              child: Wrap(
                spacing: 8,
                runSpacing: 4,
                children: [
                  const Text('Showing: ',
                    style: TextStyle(fontWeight: FontWeight.bold)),
                  ...activeFilters.entries.map((e) => Chip(
                    label: Text('${e.key}: ${e.value}', style: const TextStyle(fontSize: 12)),
                    backgroundColor: Colors.blue[100],
                    padding: EdgeInsets.zero,
                  )),
                ],
              ),
            ),
            const SizedBox(height: 12),
          ],

          // ── Results ──
          if (items.isNotEmpty) ...[
            _SectionHeader('RESULTS (${items.length} on page ${page + 1})'),
            const SizedBox(height: 8),
            if (loading)
              const Center(child: CircularProgressIndicator())
            else
              ...items.map((item) => Card(
                child: ListTile(
                  leading: _PriorityDot(item['priority'] as String, _priorityColor),
                  title: Text(
                    item['unique_ref'] as String,
                    style: const TextStyle(fontFamily: 'monospace', fontSize: 13, color: Colors.blue),
                  ),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item['subject'] as String,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 12),
                      ),
                      Text(
                        '${item['category']} · ${item['channel']}',
                        style: const TextStyle(fontSize: 11, color: Colors.grey),
                      ),
                    ],
                  ),
                  trailing: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: _typeColor(item['feedback_type'] as String).withOpacity(0.15),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          item['feedback_type'] as String,
                          style: TextStyle(
                            fontSize: 10,
                            color: _typeColor(item['feedback_type'] as String),
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        _formatDate(item['submitted_at'] as String),
                        style: const TextStyle(fontSize: 10, color: Colors.grey),
                      ),
                    ],
                  ),
                  isThreeLine: true,
                ),
              )),

            // Pagination
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                TextButton(
                  onPressed: page > 0 ? () => _drillDown(activeFilters, pageNum: page - 1) : null,
                  child: const Text('← Prev'),
                ),
                Text('Page ${page + 1}'),
                TextButton(
                  onPressed: items.length == PAGE_SIZE
                    ? () => _drillDown(activeFilters, pageNum: page + 1)
                    : null,
                  child: const Text('Next →'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  String _formatDate(String iso) {
    final d = DateTime.parse(iso);
    return '${d.day}/${d.month}/${d.year}';
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader(this.title);

  @override
  Widget build(BuildContext context) => Text(
    title,
    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold,
      color: Colors.grey, letterSpacing: 1.5),
  );
}

class _CountCard extends StatelessWidget {
  final String label;
  final int value;
  final Color color;
  final bool active;
  final VoidCallback onTap;

  const _CountCard({
    required this.label, required this.value, required this.color,
    required this.active, required this.onTap,
  });

  @override
  Widget build(BuildContext context) => GestureDetector(
    onTap: onTap,
    child: Container(
      margin: const EdgeInsets.all(4),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: active ? color.withOpacity(0.25) : color.withOpacity(0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: active ? color : color.withOpacity(0.3), width: active ? 2 : 1),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('$value', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: color)),
          Text(label, style: const TextStyle(fontSize: 11), textAlign: TextAlign.center),
        ],
      ),
    ),
  );
}

class _PriorityDot extends StatelessWidget {
  final String priority;
  final Color Function(String) colorFn;
  const _PriorityDot(this.priority, this.colorFn);

  @override
  Widget build(BuildContext context) => CircleAvatar(
    backgroundColor: colorFn(priority).withOpacity(0.2),
    child: Text(priority[0].toUpperCase(),
      style: TextStyle(color: colorFn(priority), fontWeight: FontWeight.bold, fontSize: 14)),
  );
}
```

---

## Supported Filter Combinations (Quick Reference)

```
# Single dimension filters (same for counts and list)
?feedback_type=grievance
?feedback_type=suggestion
?feedback_type=inquiry
?feedback_type=applause
?priority=critical
?priority=high
?priority=medium
?priority=low
?category=corruption
?category=quality
?category=process
?category=staff_conduct
?category=billing
?category=safety
?category=community_benefit
?category=timeliness
?category=other
?status=submitted
?status=acknowledged
?status=resolved
?channel=in_person
?channel=email
?channel=mobile_app
?channel=web_portal
?channel=whatsapp
?channel=sms

# UUID-based filters (list only)
?department_id=<uuid>
?service_id=<uuid>
?product_id=<uuid>
?branch_id=<uuid>

# Date range (both counts and list)
?date_from=2026-05-01
?date_to=2026-05-12

# Compound (any combination)
?feedback_type=grievance&priority=critical        → critical grievances
?feedback_type=grievance&priority=high            → high grievances
?feedback_type=suggestion&status=submitted        → unactioned suggestions
?feedback_type=inquiry&status=submitted           → open inquiries
?priority=critical&category=corruption            → critical corruption cases
?feedback_type=grievance&channel=in_person        → in-person grievances
?date_from=2026-05-01&feedback_type=grievance     → grievances this month
```

---

## Key Notes

1. **`org_id` is automatic for staff** — JWT contains `org_id`, no need to pass it as a param (only platform admins need it)

2. **`count` in list response ≠ total** — it's the current page size. Use `/feedback/counts` for totals

3. **Counts and list are always aligned** — if `/feedback/counts?priority=critical` returns 7, then `/feedback?priority=critical` returns 7 items

4. **`by_status` may have missing keys** — only statuses with count > 0 appear in the response

5. **Category keys are slugs** — use them directly as the `category` param (e.g. `by_category.staff_conduct = 5` → `?category=staff_conduct`)
