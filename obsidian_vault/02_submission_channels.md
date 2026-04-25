# Submission Channels

Riviwa accepts feedback through multiple channels to ensure accessibility for all community members.

## 1. Web Portal (Consumer Portal)

The web portal is the primary self-service channel for literate users with internet access.

- URL: riviwa.com/my/feedback (consumer portal)
- Requires account registration/login
- Supports all feedback types
- File and photo attachments supported
- Provides real-time tracking and status updates
- Available in Swahili and English

## 2. WhatsApp

WhatsApp is the most accessible channel for most Tanzanians with smartphones.

- The AI chatbot guides users through the submission process in natural language
- Supports Swahili and English
- Users provide: feedback type, description, location, contact details
- The AI auto-identifies the relevant project from the description
- Final confirmation before submission
- Tracking number sent back via WhatsApp
- SMS fallback if WhatsApp is unavailable

**How to start:** Message the Riviwa WhatsApp number and say "Ninataka kutoa malalamiko" (I want to submit a grievance) or simply describe the issue.

## 3. SMS

For basic phones without smartphones.

- Short structured SMS format
- Keyword-based: GRM, LALAMIKO, PENDEKEZO
- AI processes and routes the SMS
- Confirmation SMS sent with tracking number

## 4. Mobile App (MOBILE_APP)

Riviwa mobile application for Android and iOS.

- Full feature parity with web portal
- GPS location auto-capture
- Photo/video attachment
- Offline drafting capability
- Push notifications for status updates

## 5. Staff / Officer Entry (STAFF_ENTRY)

GRM Officers can submit feedback on behalf of community members who appear in person or call.

- Full control over all fields
- Can set priority, backdate, assign directly
- Useful for walk-in submissions, phone calls, suggestion boxes
- Officer's identity recorded in the audit trail

## 6. AI Chatbot (CHATBOT)

Structured conversational interface deployed as a widget or standalone.

- Multi-turn conversation to gather complete feedback details
- Auto-classification of feedback type and project
- Collects: description, location, contact information
- Submits with high confidence after extracting all required fields

## 7. Partner API / Integration (API, PARTNER_API)

Third-party applications (banks, mobile apps, service portals) can submit feedback on behalf of their users via the Riviwa Integration Service.

- OAuth2 / API Key authentication
- Org-scoped — submissions bound to the partner's organisation
- Context sessions for pre-filling user data
- Webhook notifications for status updates

## 8. Voice Notes (VOICE)

Oral feedback recorded via phone or web interface.

- Speech-to-text transcription (Whisper/Google STT)
- Supports Swahili and other local languages
- Audio file stored in MinIO
- Transcript used for AI classification

## Channel Codes in the System

| Channel | Code |
|---|---|
| Web Portal | WEB_PORTAL |
| WhatsApp | WHATSAPP |
| SMS | SMS |
| Mobile App | MOBILE_APP |
| Staff Entry | STAFF_ENTRY |
| AI Chatbot | CHATBOT |
| API / Integration | API / PARTNER_API |
| Mini App | MINI_APP |
| Voice | VOICE |
| Community Meeting | COMMUNITY_MEETING |
| Suggestion Box | SUGGESTION_BOX |
| Email | EMAIL |
| Phone | PHONE |
