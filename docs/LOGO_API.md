# Logo & Platform Settings API

Base URL: `https://api.riviwa.com/api/v1`

All file uploads use `multipart/form-data`.  
All other requests use `Content-Type: application/json`.

---

## Organisation Logo

Endpoints for managing the logo of a specific organisation.

### GET `/orgs/{org_id}/logo`

Return the current logo URL for an organisation.

**Auth:** Any authenticated user (Bearer token required)  
**Request body:** None

**Response `200`**
```json
{
  "org_id": "bd877fc4-0439-4e7a-871b-3701b95b3a02",
  "logo_url": "http://minio:9000/riviwa-images/organisations/bd877fc4-.../logo.png"
}
```
> `logo_url` is `null` if no logo has been uploaded yet.

---

### POST `/orgs/{org_id}/logo`

Upload or replace the organisation logo. Re-uploading overwrites the previous file.

**Auth:** `MANAGER` org role or higher  
**Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | Image file. Accepted: JPEG, PNG, WebP, SVG, GIF. Max **5 MB**. |

**Example (curl)**
```bash
curl -X POST https://api.riviwa.com/api/v1/orgs/bd877fc4-0439-4e7a-871b-3701b95b3a02/logo \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/logo.png"
```

**Response `200`**
```json
{
  "org_id": "bd877fc4-0439-4e7a-871b-3701b95b3a02",
  "logo_url": "http://minio:9000/riviwa-images/organisations/bd877fc4-.../logo.png"
}
```

**Errors**
| Status | Reason |
|--------|--------|
| `400` | Unsupported file type or file exceeds 5 MB |
| `403` | Caller does not have MANAGER role or higher |
| `404` | Organisation not found |

---

### DELETE `/orgs/{org_id}/logo`

Remove the organisation logo. The file is deleted from MinIO and `logo_url` is set to `null`.

**Auth:** `MANAGER` org role or higher  
**Request body:** None

**Response `200`**
```json
{
  "org_id": "bd877fc4-0439-4e7a-871b-3701b95b3a02",
  "logo_url": null,
  "message": "Logo removed."
}
```

**Errors**
| Status | Reason |
|--------|--------|
| `403` | MANAGER role required |
| `404` | Organisation not found, or organisation has no logo set |

---

## Platform / System Logo

Endpoints for the platform-wide app logo (shown in emails, login screen, app header).  
Stored in MinIO at `system/00000000-0000-0000-0000-000000000001/logo.{ext}`.

### GET `/system/logo`

Return the current platform logo URL.

**Auth:** **Public — no token required.** The React app calls this on boot.  
**Request body:** None

**Response `200`**
```json
{
  "logo_url": "http://minio:9000/riviwa-images/system/.../logo.png",
  "logo_updated_at": "2026-04-12T19:00:00+00:00",
  "app_name": "Riviwa GRM"
}
```
> `logo_url` is `null` until a super_admin uploads one.

---

### POST `/system/logo`

Upload or replace the platform-wide logo.

**Auth:** `super_admin` platform role  
**Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | Image file. Accepted: JPEG, PNG, WebP, SVG. Max **5 MB**. |

**Example (curl)**
```bash
curl -X POST https://api.riviwa.com/api/v1/system/logo \
  -H "Authorization: Bearer <super_admin_token>" \
  -F "file=@/path/to/platform-logo.png"
```

**Response `200`**
```json
{
  "logo_url": "http://minio:9000/riviwa-images/system/.../logo.png",
  "logo_updated_at": "2026-04-12T19:05:00+00:00",
  "uploaded_by": "24513388-1822-486e-bec4-15c843172a3d"
}
```

**Errors**
| Status | Reason |
|--------|--------|
| `400` | Unsupported file type or file exceeds 5 MB |
| `403` | `super_admin` platform role required |

---

### DELETE `/system/logo`

Remove the platform logo. The app falls back to its bundled default logo.

**Auth:** `super_admin` platform role  
**Request body:** None

**Response `200`**
```json
{
  "logo_url": null,
  "message": "Platform logo removed."
}
```

**Errors**
| Status | Reason |
|--------|--------|
| `403` | `super_admin` role required |
| `404` | No platform logo is currently set |

---

## Platform Favicon

### GET `/system/favicon`

Return the current favicon URL.

**Auth:** **Public — no token required.**  
**Request body:** None

**Response `200`**
```json
{
  "favicon_url": "http://minio:9000/riviwa-images/system/.../favicon.png"
}
```

---

### POST `/system/favicon`

Upload or replace the platform favicon.

**Auth:** `super_admin` platform role  
**Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | Favicon image. Accepted: PNG, SVG. Recommended size: 32×32px. Max **512 KB**. |

**Example (curl)**
```bash
curl -X POST https://api.riviwa.com/api/v1/system/favicon \
  -H "Authorization: Bearer <super_admin_token>" \
  -F "file=@/path/to/favicon.png"
```

**Response `200`**
```json
{
  "favicon_url": "http://minio:9000/riviwa-images/system/.../favicon.png"
}
```

**Errors**
| Status | Reason |
|--------|--------|
| `400` | Unsupported file type or file exceeds 512 KB |
| `403` | `super_admin` role required |

---

### DELETE `/system/favicon`

Remove the platform favicon.

**Auth:** `super_admin` platform role  
**Request body:** None

**Response `200`**
```json
{
  "favicon_url": null,
  "message": "Platform favicon removed."
}
```

---

## Platform Settings

### GET `/system/settings`

Read all platform settings (branding, contact, colours).

**Auth:** `admin` platform role or higher

**Response `200`**
```json
{
  "app_name": "Riviwa GRM",
  "logo_url": "http://minio:9000/riviwa-images/system/.../logo.png",
  "logo_updated_at": "2026-04-12T19:05:00+00:00",
  "favicon_url": null,
  "support_email": "support@riviwa.com",
  "support_phone": "+255700000000",
  "primary_color": "#185FA5",
  "secondary_color": "#1D9E75",
  "updated_at": "2026-04-12T19:05:00+00:00"
}
```

---

### PATCH `/system/settings`

Update platform settings. All fields are optional — only provided fields are changed.  
Use the dedicated logo/favicon endpoints to change images.

**Auth:** `super_admin` platform role  
**Content-Type:** `application/json`

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `app_name` | string | No | max 128 chars | Platform display name shown in emails and browser title |
| `support_email` | string | No | max 255 chars | Support email shown in notification templates |
| `support_phone` | string | No | max 30 chars | Support phone number |
| `primary_color` | string | No | `#RRGGBB` hex | Primary brand colour |
| `secondary_color` | string | No | `#RRGGBB` hex | Secondary brand colour |

**Request body example**
```json
{
  "app_name": "Riviwa GRM Platform",
  "support_email": "help@riviwa.com",
  "support_phone": "+255700123456",
  "primary_color": "#185FA5",
  "secondary_color": "#1D9E75"
}
```

**Response `200`** — returns the full updated settings object (same shape as GET `/system/settings`)

**Errors**
| Status | Reason |
|--------|--------|
| `400` | No fields provided, or `primary_color`/`secondary_color` not a valid `#RRGGBB` hex |
| `403` | `super_admin` role required |

---

## Access Summary

| Endpoint | Method | Auth |
|----------|--------|------|
| `/orgs/{org_id}/logo` | GET | Any authenticated user |
| `/orgs/{org_id}/logo` | POST | Org `MANAGER` or higher |
| `/orgs/{org_id}/logo` | DELETE | Org `MANAGER` or higher |
| `/system/logo` | GET | **Public** |
| `/system/logo` | POST | Platform `super_admin` |
| `/system/logo` | DELETE | Platform `super_admin` |
| `/system/favicon` | GET | **Public** |
| `/system/favicon` | POST | Platform `super_admin` |
| `/system/favicon` | DELETE | Platform `super_admin` |
| `/system/settings` | GET | Platform `admin` or higher |
| `/system/settings` | PATCH | Platform `super_admin` |

## Accepted File Types

| MIME type | Extension | Max size |
|-----------|-----------|----------|
| `image/jpeg` | `.jpg` | 5 MB (logo), 512 KB (favicon) |
| `image/png` | `.png` | 5 MB (logo), 512 KB (favicon) |
| `image/webp` | `.webp` | 5 MB (logo) |
| `image/svg+xml` | `.svg` | 5 MB (logo), 512 KB (favicon) |
| `image/gif` | `.gif` | 5 MB (logo) |

## MinIO Storage Paths

| Asset | Path in `riviwa-images` bucket |
|-------|-------------------------------|
| Org logo | `organisations/{org_id}/logo.{ext}` |
| Platform logo | `system/00000000-0000-0000-0000-000000000001/logo.{ext}` |
| Platform favicon | `system/00000000-0000-0000-0000-000000000001/favicon.{ext}` |
