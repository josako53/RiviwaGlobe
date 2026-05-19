# Riviwa — KYC Verification: Frontend Implementation Guide
**For:** Frontend developers (React.js / Flutter)  
**Date:** 2026-05-20  
**Base URL (production):** `https://api.riviwa.com`  
**Base URL (dev):** `http://77.237.241.13`  
**Auth service port:** `:8000` (behind Nginx — use base URL only)

---

## What is KYC verification?

KYC (Know Your Customer) is the manual business identity verification track. An org submits official business documents. A Riviwa platform admin reviews them and approves, rejects, or requests more information.

**On approval:** `org.is_kyc_verified = true` → the org's public badge becomes **"Verified Business"** (blue ✓).

KYC is **completely independent** of plan subscription:
- Any org can submit KYC, on any plan, at any point
- Approval does not change features or pricing
- It is purely a trust/credibility signal shown on public profiles, product listings, and QR scan results

---

## Two verification tracks — what each one means

| Track | Field | Set by | Badge |
|-------|-------|--------|-------|
| Payment verification | `is_payment_verified` | Auto — subscription_service sets this the moment a subscription payment succeeds | Green "Active Subscriber" |
| KYC verification | `is_kyc_verified` | Manual — platform admin approves after document review | Blue "Verified Business" |

Both can be true simultaneously. `is_kyc_verified` takes visual priority — the blue badge overrides the green one.

---

## KYC state machine

```
                    ┌─────────────────────────────────────────┐
                    │ org submits documents                   │
                    ▼                                         │
               [ pending ]                                   │
                    │                                         │
                    │  admin opens submission                 │
                    ▼                                         │
           [ under_review ]                                  │
                    │                                         │
          ┌─────────┼──────────┐                             │
          │         │          │                             │
          ▼         ▼          ▼                             │
     [approved] [rejected] [more_info]                       │
          │                    │                             │
          │                    │ org uploads more docs       │
          │                    └────────────────────────────►┘
          │
          ▼
   is_kyc_verified = true
   badge = "Verified Business" (blue)
```

| Status | Meaning | UI action |
|--------|---------|-----------|
| `pending` | Submitted, not yet opened by admin | Show "Submitted — under review" banner |
| `under_review` | Admin has opened it | Show "Under review by Riviwa team" |
| `more_info` | Admin wants additional documents | Show `rejection_reason` message + upload button |
| `approved` | KYC passed — badge is active | Show success state, fetch badge |
| `rejected` | KYC failed — cannot resubmit same docs | Show `rejection_reason` + re-submit button |

---

## Endpoints overview

All endpoints are on `auth_service` behind Nginx. Auth header required on all except the public badge endpoint.

```
Authorization: Bearer <access_token>
```

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/orgs/my/verification` | Own verification status (both tracks + latest submission) |
| `POST` | `/api/v1/orgs/my/kyc/submit` | Create KYC submission (with optional inline documents) |
| `POST` | `/api/v1/orgs/my/kyc/documents/upload` | Upload a document file (multipart) — **use this** |
| `POST` | `/api/v1/orgs/my/kyc/documents` | Add a document by URL to existing submission |
| `DELETE` | `/api/v1/orgs/my/kyc/documents/{doc_id}` | Remove a document from pending/more_info submission |
| `GET` | `/api/v1/orgs/my/kyc` | Full KYC history with documents (last 5 submissions) |
| `GET` | `/api/v1/orgs/{slug}/badge` | **Public** — badge for any org by slug |

---

---

# Step-by-Step Implementation

---

## Step 1 — Check current verification status

**When:** Account settings page, verification dashboard, or any screen where you need to decide what to show.

```
GET /api/v1/orgs/my/verification
Authorization: Bearer <token>
```

**Response — unverified org, no submission yet:**
```json
{
  "org_id":              "org-uuid",
  "slug":                "mnh-hospital",
  "display_name":        "Muhimbili National Hospital",
  "is_payment_verified": true,
  "payment_verified_at": "2026-05-18T20:30:00",
  "is_kyc_verified":     false,
  "kyc_verified_at":     null,
  "kyc_rejection_reason": null,
  "verification_level":  "payment_verified",
  "kyc_submission":      null
}
```

**Response — submission in progress:**
```json
{
  "is_payment_verified": true,
  "is_kyc_verified":     false,
  "verification_level":  "payment_verified",
  "kyc_submission": {
    "id":     "sub-uuid",
    "status": "under_review",
    "submitted_at": "2026-05-19T14:00:00",
    "rejection_reason": null
  }
}
```

**Response — fully verified:**
```json
{
  "is_payment_verified": true,
  "is_kyc_verified":     true,
  "kyc_verified_at":     "2026-05-20T09:15:00",
  "verification_level":  "kyc_verified",
  "kyc_submission": {
    "id":     "sub-uuid",
    "status": "approved"
  }
}
```

`verification_level` values: `"unverified"` → `"payment_verified"` → `"kyc_verified"`

### React.js

```typescript
// hooks/useVerification.ts
import { useQuery } from '@tanstack/react-query';

export const useVerification = () =>
  useQuery({
    queryKey: ['verification'],
    queryFn: () => api.get('/api/v1/orgs/my/verification').then(r => r.data),
    staleTime: 60_000,   // re-fetch every 60s while screen is open
  });

// In your component:
const { data: verification } = useVerification();

if (verification?.is_kyc_verified) {
  return <KYCApprovedBanner verifiedAt={verification.kyc_verified_at} />;
}

if (verification?.kyc_submission?.status === 'under_review') {
  return <KYCUnderReviewBanner />;
}

if (verification?.kyc_submission?.status === 'more_info') {
  return <KYCMoreInfoBanner reason={verification.kyc_submission.rejection_reason} />;
}

return <StartKYCPrompt />;
```

### Flutter

```dart
// providers/verification_provider.dart
final verificationProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final r = await dio.get('/api/v1/orgs/my/verification');
  return r.data as Map<String, dynamic>;
});

// In widget:
final verification = ref.watch(verificationProvider);
verification.when(
  data: (v) {
    if (v['is_kyc_verified'] == true) return KYCApprovedWidget();
    final sub = v['kyc_submission'];
    if (sub == null) return StartKYCWidget();
    switch (sub['status']) {
      case 'under_review': return KYCUnderReviewWidget();
      case 'more_info':    return KYCMoreInfoWidget(reason: sub['rejection_reason']);
      case 'rejected':     return KYCRejectedWidget(reason: sub['rejection_reason']);
      default:             return KYCPendingWidget();
    }
  },
  loading: () => CircularProgressIndicator(),
  error: (e, _) => ErrorWidget(e),
);
```

---

## Step 2 — Create a KYC submission

**When:** Org clicks "Start Verification" / "Apply for Verified Business badge".  
**Rule:** A submission must exist before you can upload files. Create it first, then upload.

```
POST /api/v1/orgs/my/kyc/submit
Authorization: Bearer <token>
Content-Type: application/json
```

**Request body:**
```json
{
  "business_type":   "GOVERNMENT",
  "reg_number":      "MNH/MOH/TZ/REG/1956/001",
  "tax_id":          "TIN-100-234-567",
  "notes_for_admin": "State hospital under MoHSW. World Bank tender deadline 30 May 2026.",
  "documents": []
}
```

`documents` can be empty here — upload files using the multipart endpoint in Step 3 instead.

**Response:**
```json
{
  "message": "KYC submission received. Our team will review within 2–3 business days.",
  "submission": {
    "id":             "sub-uuid",
    "status":         "pending",
    "business_type":  "GOVERNMENT",
    "reg_number":     "MNH/MOH/TZ/REG/1956/001",
    "tax_id":         "TIN-100-234-567",
    "notes_for_admin": "State hospital under MoHSW...",
    "rejection_reason": null,
    "submitted_at":   "2026-05-20T10:00:00",
    "documents":      []
  }
}
```

Save `submission.id` — you will use it in the document upload step.

**Important rules:**
- If a `pending` or `more_info` submission already exists, this call **re-opens** it (adds to it) instead of creating a new one
- If a submission is `under_review`, you get `409 SUBMISSION_UNDER_REVIEW` — show "Wait for outcome" message, do not allow re-submit

### React.js

```typescript
const createSubmission = async () => {
  const { submission } = await api.post('/api/v1/orgs/my/kyc/submit', {
    business_type: formData.businessType,
    reg_number:    formData.regNumber,
    tax_id:        formData.taxId,
    notes_for_admin: formData.notes,
    documents: [],
  }).then(r => r.data);

  setSubmissionId(submission.id);
  setStep('upload_documents');   // navigate to upload step
};
```

### Flutter

```dart
Future<String> createSubmission(Map<String, String> form) async {
  final r = await dio.post('/api/v1/orgs/my/kyc/submit', data: {
    'business_type':    form['businessType'],
    'reg_number':       form['regNumber'],
    'tax_id':           form['taxId'],
    'notes_for_admin':  form['notes'],
    'documents':        [],
  });
  return r.data['submission']['id'] as String;
}
```

---

## Step 3 — Upload documents

**When:** Immediately after Step 2, or when admin requests more info (Step 6).  
**Rule:** A submission must already exist. Upload each file separately — one request per file.

```
POST /api/v1/orgs/my/kyc/documents/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Form fields:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `file` | binary | Yes | The document file |
| `document_type` | string | Yes | See table below |

**Accepted file types:** PDF, JPEG, PNG, DOCX, DOC, TIFF  
**Max size:** 15 MB per file

**`document_type` values:**

| Value | What to submit |
|-------|---------------|
| `business_license` | Business operating license |
| `certificate_of_incorporation` | BRELA / NGO Board / TRA certificate |
| `tax_clearance` | TRA tax clearance certificate |
| `tax_id` | TIN certificate |
| `directors_national_id` | Director/owner NIDA or passport |
| `utility_bill` | Electricity/water bill (proof of address) |
| `bank_statement` | Bank statement (last 3 months) |
| `memorandum_of_association` | M&A for companies |
| `audited_accounts` | Audited financial statements |
| `other` | Any supplementary document |

**Response:**
```json
{
  "message": "Document 'brela_certificate.pdf' uploaded successfully.",
  "document": {
    "id":            "doc-uuid",
    "document_type": "certificate_of_incorporation",
    "file_url":      "https://minio.riviwa.com/reviwa-kyc/kyc/org-uuid/sub-uuid/certificate_of_incorporation_a3b2.pdf",
    "file_name":     "certificate_of_incorporation_a3b2.pdf",
    "file_size_bytes": 245760,
    "is_verified":   false,
    "uploaded_at":   "2026-05-20T10:05:00"
  },
  "submission_status": "pending"
}
```

Note `submission_status` in the response — if it was `more_info`, uploading a file **automatically resets it to `pending`**. No extra call needed.

### React.js — single file upload

```typescript
const uploadKYCDocument = async (file: File, documentType: string) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('document_type', documentType);

  const { document, submission_status } = await api.post(
    '/api/v1/orgs/my/kyc/documents/upload',
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  ).then(r => r.data);

  return { document, submission_status };
};
```

### React.js — multi-document upload UI

```typescript
// components/KYCDocumentUploader.tsx
const REQUIRED_DOCS = [
  { type: 'certificate_of_incorporation', label: 'Business Registration Certificate', required: true },
  { type: 'tax_id',                       label: 'TIN Certificate',                  required: true },
  { type: 'directors_national_id',         label: 'Director / Owner National ID',     required: true },
  { type: 'utility_bill',                  label: 'Utility Bill (proof of address)',   required: false },
];

const KYCDocumentUploader = ({ onComplete }) => {
  const [uploads, setUploads] = useState<Record<string, any>>({});
  const [uploading, setUploading] = useState(false);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>, docType: string) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 15 * 1024 * 1024) {
      showError('File must be under 15 MB');
      return;
    }

    setUploading(true);
    try {
      const { document } = await uploadKYCDocument(file, docType);
      setUploads(prev => ({ ...prev, [docType]: document }));
    } catch (err: any) {
      showError(err.response?.data?.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const allRequiredUploaded = REQUIRED_DOCS
    .filter(d => d.required)
    .every(d => uploads[d.type]);

  return (
    <div>
      {REQUIRED_DOCS.map(doc => (
        <div key={doc.type} className="doc-row">
          <label>{doc.label} {doc.required && <span className="required">*</span>}</label>
          {uploads[doc.type] ? (
            <div className="uploaded">
              ✓ {uploads[doc.type].file_name}
              <button onClick={() => deleteDocument(uploads[doc.type].id, doc.type)}>
                Remove
              </button>
            </div>
          ) : (
            <input
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,.docx"
              onChange={(e) => handleFileChange(e, doc.type)}
              disabled={uploading}
            />
          )}
        </div>
      ))}

      <button
        onClick={onComplete}
        disabled={!allRequiredUploaded || uploading}
      >
        Submit for Review
      </button>
    </div>
  );
};
```

### Flutter

```dart
Future<Map<String, dynamic>> uploadKycDocument(
  File file,
  String documentType,
) async {
  final fileName = path.basename(file.path);
  final ext = fileName.split('.').last.toLowerCase();
  final mimeType = {
    'pdf': 'application/pdf',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  }[ext] ?? 'application/octet-stream';

  final formData = FormData.fromMap({
    'document_type': documentType,
    'file': await MultipartFile.fromFile(
      file.path,
      filename: fileName,
      contentType: MediaType.parse(mimeType),
    ),
  });

  final r = await dio.post('/api/v1/orgs/my/kyc/documents/upload', data: formData);
  return r.data as Map<String, dynamic>;
}
```

---

## Step 4 — Remove a document (if needed before review)

**When:** User wants to replace an uploaded file before the submission goes under review.  
**Rule:** Only works on `pending` or `more_info` submissions. Cannot remove from `under_review` or `approved`.

```
DELETE /api/v1/orgs/my/kyc/documents/{doc_id}
Authorization: Bearer <token>
```

**Response:**
```json
{ "message": "Document 'brela_certificate.pdf' removed.", "id": "doc-uuid" }
```

**Error if submission is locked:**
```json
{
  "error":   "SUBMISSION_NOT_EDITABLE",
  "message": "Cannot remove documents — submission is 'under_review'. Only pending or more_info submissions can be edited."
}
```

```typescript
const deleteDocument = async (docId: string, docType: string) => {
  await api.delete(`/api/v1/orgs/my/kyc/documents/${docId}`);
  setUploads(prev => {
    const next = { ...prev };
    delete next[docType];
    return next;
  });
};
```

---

## Step 5 — Poll submission status

**When:** After submitting, show the org their submission progress.

```
GET /api/v1/orgs/my/kyc
Authorization: Bearer <token>
```

**Response:**
```json
{
  "org_id":          "org-uuid",
  "is_kyc_verified": false,
  "kyc_verified_at": null,
  "submissions": [
    {
      "id":       "sub-uuid",
      "status":   "under_review",
      "business_type": "GOVERNMENT",
      "reg_number": "MNH/MOH/TZ/REG/1956/001",
      "rejection_reason": null,
      "submitted_at": "2026-05-20T10:00:00",
      "reviewed_at":  null,
      "documents": [
        {
          "id":            "doc-uuid-1",
          "document_type": "certificate_of_incorporation",
          "file_name":     "brela_cert.pdf",
          "file_url":      "https://...",
          "file_size_bytes": 245760,
          "is_verified":   false,
          "uploaded_at":   "2026-05-20T10:05:00"
        },
        {
          "id":            "doc-uuid-2",
          "document_type": "directors_national_id",
          "file_name":     "director_nida.jpg",
          "file_url":      "https://...",
          "file_size_bytes": 98304,
          "is_verified":   false,
          "uploaded_at":   "2026-05-20T10:06:00"
        }
      ]
    }
  ]
}
```

Returns last 5 submissions so the org can see their history.

**Status → UI mapping:**

| `status` | What to show |
|---------|-------------|
| `pending` | "Submitted — our team will review within 2–3 business days" |
| `under_review` | "Under review by Riviwa team" (no action needed) |
| `more_info` | Show `rejection_reason` text + "Upload additional documents" button |
| `approved` | "KYC Verified ✓" — fetch badge |
| `rejected` | Show `rejection_reason` + "Start new submission" button |

### React.js — status page

```typescript
const KYCStatusPage = () => {
  const { data, refetch } = useQuery({
    queryKey: ['kyc-status'],
    queryFn: () => api.get('/api/v1/orgs/my/kyc').then(r => r.data),
    refetchInterval: 30_000,  // auto-refresh every 30s
  });

  const latest = data?.submissions?.[0];

  if (!latest) return <StartKYCButton />;

  if (data.is_kyc_verified) {
    return (
      <div className="verified">
        <span className="badge blue">✓ Verified Business</span>
        <p>Verified on {format(new Date(data.kyc_verified_at), 'dd MMM yyyy')}</p>
      </div>
    );
  }

  switch (latest.status) {
    case 'pending':
      return <StatusBanner
        icon="⏳"
        title="Submission received"
        body="Our team will review your documents within 2–3 business days."
      />;

    case 'under_review':
      return <StatusBanner
        icon="🔍"
        title="Under review"
        body="Your documents are being reviewed by the Riviwa team."
      />;

    case 'more_info':
      return (
        <div>
          <StatusBanner
            icon="📋"
            title="Additional documents required"
            body={latest.rejection_reason}
            variant="warning"
          />
          <KYCDocumentUploader onComplete={() => refetch()} />
        </div>
      );

    case 'rejected':
      return (
        <div>
          <StatusBanner
            icon="✗"
            title="Verification rejected"
            body={latest.rejection_reason}
            variant="error"
          />
          <button onClick={() => setStep('submit_new')}>
            Start New Submission
          </button>
        </div>
      );

    default:
      return null;
  }
};
```

---

## Step 6 — Handle the "more_info" loop

**When:** `submission.status === "more_info"` — admin has asked for additional documents.  
`rejection_reason` contains the admin's specific request.

The flow is:
1. Show the `rejection_reason` text prominently
2. Show the list of already-uploaded documents (so org knows what they have)
3. Provide an upload button for the additional document(s)
4. When the org uploads, `submission_status` in the response automatically becomes `pending`
5. Poll/refresh the status — it will go back to `under_review` when admin reopens it

```typescript
// components/KYCMoreInfoHandler.tsx
const KYCMoreInfoHandler = ({ submission, onRefetch }) => {
  return (
    <div className="more-info-panel">
      <h3>Additional Documents Required</h3>
      <div className="admin-request">
        <p className="label">Requested by Riviwa team:</p>
        <p className="message">{submission.rejection_reason}</p>
      </div>

      <h4>Documents already uploaded:</h4>
      <ul>
        {submission.documents.map(doc => (
          <li key={doc.id}>
            ✓ {doc.document_type.replace(/_/g, ' ')} — {doc.file_name}
          </li>
        ))}
      </ul>

      <h4>Upload additional document:</h4>
      <select onChange={e => setDocType(e.target.value)}>
        <option value="utility_bill">Utility Bill</option>
        <option value="bank_statement">Bank Statement</option>
        <option value="audited_accounts">Audited Accounts</option>
        <option value="other">Other</option>
      </select>
      <input
        type="file"
        accept=".pdf,.jpg,.jpeg,.png,.docx"
        onChange={async (e) => {
          const file = e.target.files?.[0];
          if (!file) return;
          const result = await uploadKYCDocument(file, docType);
          // submission_status in response will be "pending" now
          onRefetch();   // refresh status page
          showToast('Document uploaded — submission resubmitted for review');
        }}
      />
    </div>
  );
};
```

---

## Step 7 — Display the public verification badge

**When:** Org profile page, product listings, QR scan result, search results.  
**No auth required** — this is a public endpoint.

```
GET /api/v1/orgs/{slug}/badge
```

**Response:**
```json
{
  "org_id":              "org-uuid",
  "slug":                "mnh-hospital",
  "display_name":        "Muhimbili National Hospital",
  "logo_url":            "https://...",
  "is_payment_verified": true,
  "is_kyc_verified":     true,
  "kyc_verified_at":     "2026-05-20T09:15:00",
  "verification_level":  "kyc_verified",
  "badge": {
    "show_payment_badge": true,
    "show_kyc_badge":     true,
    "label": "Verified Business",
    "color": "blue"
  }
}
```

`verification_level` values:
- `"unverified"` — no badge
- `"payment_verified"` — green badge ("Active Subscriber")
- `"kyc_verified"` — blue badge ("Verified Business") ← KYC takes priority

### React.js — VerificationBadge component

```typescript
// components/VerificationBadge.tsx
interface BadgeProps {
  slug: string;
  size?: 'sm' | 'md' | 'lg';
}

const VerificationBadge = ({ slug, size = 'md' }: BadgeProps) => {
  const { data } = useQuery({
    queryKey: ['badge', slug],
    queryFn: () => api.get(`/api/v1/orgs/${slug}/badge`).then(r => r.data.badge),
    staleTime: 5 * 60_000,  // cache for 5 minutes — badges rarely change
  });

  if (!data?.label) return null;

  return (
    <span
      className={`badge badge-${data.color} badge-${size}`}
      title={data.color === 'blue'
        ? 'Business identity verified by Riviwa'
        : 'Active Riviwa subscriber'
      }
    >
      ✓ {data.label}
    </span>
  );
};

// CSS reference:
// .badge-blue  { background: #1d4ed8; color: white; }
// .badge-green { background: #16a34a; color: white; }
```

### Flutter

```dart
// widgets/verification_badge.dart
class VerificationBadge extends StatelessWidget {
  final String slug;
  const VerificationBadge({required this.slug});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Map<String, dynamic>>(
      future: dio.get('/api/v1/orgs/$slug/badge')
          .then((r) => (r.data['badge'] as Map<String, dynamic>)),
      builder: (ctx, snap) {
        if (!snap.hasData || snap.data!['label'] == null) return SizedBox.shrink();
        final badge = snap.data!;
        final isBlue = badge['color'] == 'blue';
        return Container(
          padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: isBlue ? Color(0xFF1d4ed8) : Color(0xFF16a34a),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.verified, color: Colors.white, size: 14),
              SizedBox(width: 4),
              Text(
                badge['label'] as String,
                style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600),
              ),
            ],
          ),
        );
      },
    );
  }
}
```

---

---

# Complete KYC flow diagram

```
org clicks "Apply for Verified Business badge"
    │
    ▼
GET /orgs/my/verification
    │
    ├── is_kyc_verified=true ─────── show "Already Verified" → done
    │
    ├── kyc_submission.status=under_review ──── show "Under Review" → wait
    │
    └── no submission / pending / rejected ─────────────────────────┐
                                                                    │
                                                                    ▼
                                          Step 1 — Fill submission form
                                          POST /orgs/my/kyc/submit
                                          → { submission.id }
                                                                    │
                                                                    ▼
                                          Step 2 — Upload documents one by one
                                          POST /orgs/my/kyc/documents/upload
                                          (file + document_type) × N files
                                          → each returns doc record
                                                                    │
                                                     (optional: remove wrong file)
                                          DELETE /orgs/my/kyc/documents/{doc_id}
                                                                    │
                                                                    ▼
                                          Step 3 — Poll status
                                          GET /orgs/my/kyc
                                                                    │
                              ┌───────────────┬────────────────┬───┴───────────────┐
                              │               │                │                   │
                              ▼               ▼                ▼                   ▼
                           pending       under_review       more_info           rejected
                           "submitted"   "under review"     admin wants          show reason
                           wait 2-3 days  wait               more docs            re-submit
                                                              │
                                                              ▼
                                          Upload additional docs
                                          POST /orgs/my/kyc/documents/upload
                                          → submission auto-reverts to "pending"
                                          → loops back to polling
                                                                    │
                                                             approved
                                                                    │
                                                                    ▼
                                          GET /orgs/{slug}/badge
                                          → badge.label = "Verified Business"
                                          → badge.color = "blue"
                                          → show badge everywhere
```

---

---

# Error reference

| HTTP | Error code | When | What to show |
|------|-----------|------|-------------|
| `401` | `UNAUTHORISED` | Token missing / expired | Redirect to login |
| `400` | `NO_ORG` | Token has no `org_id` | Prompt to switch org |
| `404` | `NO_ACTIVE_SUBMISSION` | Tried to upload before creating submission | Call `POST /orgs/my/kyc/submit` first |
| `404` | `NOT_FOUND` | Document or org not found | Generic error |
| `409` | `SUBMISSION_UNDER_REVIEW` | Tried to create submission while one is under review | "Your submission is being reviewed. Please wait." |
| `409` | `SUBMISSION_NOT_EDITABLE` | Tried to delete doc on locked submission | "Documents cannot be removed after review starts." |
| `422` | `UPLOAD_ERROR` | Wrong file type or over 15 MB | "Accepted: PDF, JPEG, PNG, DOCX — max 15 MB" |
| `422` | `VALIDATION_ERROR` | Missing required field | Show field error |

### Handle 409 SUBMISSION_UNDER_REVIEW

```typescript
api.interceptors.response.use(null, (error) => {
  if (error.response?.status === 409) {
    const { error: code, submission_id } = error.response.data;
    if (code === 'SUBMISSION_UNDER_REVIEW') {
      showModal({
        title: 'Submission under review',
        body: 'Your KYC documents are currently being reviewed by the Riviwa team. We will notify you of the outcome within 2–3 business days.',
        action: { label: 'View status', href: '/account/verification' },
      });
      return;
    }
  }
  return Promise.reject(error);
});
```

### Handle UPLOAD_ERROR

```typescript
if (error.response?.data?.error === 'UPLOAD_ERROR') {
  showError(
    error.response.data.message ||
    'Upload failed. Accepted formats: PDF, JPEG, PNG, DOCX. Max size: 15 MB.'
  );
}
```

---

---

# Implementation checklist

```
Setup
□ Add Authorization header to all kyc requests
□ Confirm org_id is in the JWT (login → switch-org if needed)

Step 1 — Check status on page load
□ GET /orgs/my/verification on account/verification page
□ Branch UI by verification_level and kyc_submission.status

Step 2 — Start submission
□ Build form: business_type, reg_number, tax_id, notes_for_admin
□ POST /orgs/my/kyc/submit → save submission.id
□ Handle 409 SUBMISSION_UNDER_REVIEW → show "wait" message

Step 3 — Upload documents
□ Build document picker per type (required: cert_of_inc, tax_id, directors_nid)
□ Validate file type client-side (PDF/JPEG/PNG/DOCX) and size (< 15MB)
□ POST /orgs/my/kyc/documents/upload (multipart) for each file
□ Show upload progress + uploaded file name on success
□ Allow DELETE /orgs/my/kyc/documents/{id} to replace wrong file

Step 4 — Show status
□ GET /orgs/my/kyc — auto-refresh every 30s
□ pending:      "Submitted, under review"
□ under_review: "Being reviewed"
□ more_info:    show rejection_reason + new upload UI
□ rejected:     show rejection_reason + re-submit button
□ approved:     show success + fetch badge

Step 5 — more_info loop
□ Show admin's request text (rejection_reason)
□ Show already-uploaded documents list
□ Upload new file → submission auto-reverts to pending
□ Refresh status → loops back to pending/under_review

Step 6 — Badge display
□ GET /orgs/{slug}/badge — no auth, cache 5 min
□ blue  badge → "Verified Business" (is_kyc_verified=true)
□ green badge → "Active Subscriber" (is_payment_verified=true)
□ no badge    → no label, hide component
□ Show badge on: org profile, product listings, QR scan results, search results
```
