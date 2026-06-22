# Riviwa AI — Mixed Feedback: Suggestion + Inquiry

## 1. Purpose & Usage

This document trains Riviwa AI to handle feedback combining a **suggestion for improvement** with an **inquiry**. The person has an idea AND a question — often the question is about whether the suggested thing already exists: *"You should have a mobile app — do you have one?"*, *"You should offer home delivery — is that available?"*

This pattern also appears when someone proposes an improvement and simultaneously asks who to direct it to, or asks for more context to refine their suggestion.

The AI must:
1. **Record the suggestion** for the improvement/product team
2. **Answer the inquiry** if the answer is known from org context — the answer may resolve the suggestion entirely (if it already exists) or confirm it is still needed
3. **Not dismiss the suggestion** even if the feature already exists — the person may not have found it, which is itself useful feedback about discoverability
4. **Note the inquiry unanswered** if the AI cannot confirm, for staff follow-up

---

## 2. The Core Pattern

The suggestion and inquiry are often the same idea, framed two ways: a proposal and a check. There is no complaint, no harm, no urgency.

**Linguistic markers:**
- Suggestion + existence check: *"You should have [X] — do you already have that?"*
- Idea + direction question: *"I think you should [X]. Who do I speak to about this?"*
- Proposal + implementation question: *"Why don't you add [X]? How long would something like that take?"*
- Implicit suggestion through question: *"Is there a faster way to do this?" (implies: there should be)*

---

## 3. Real-World Examples Across Industries

### 3.1 Healthcare / Hospital
> *"You should have an online appointment booking system — waiting in line for an hour just to book is unnecessary. Do you already have something like that or is it still only in person?"*

- **Suggestion**: online/digital appointment booking
- **Inquiry**: whether it already exists

> *"It would really help if patients could see their test results online rather than coming back to collect them. Is there a patient portal or mobile app for that?"*

- **Suggestion**: digital results delivery
- **Inquiry**: whether a patient portal exists

---

### 3.2 Government / Public Services
> *"The government should digitize the process for renewing business licences — right now it requires three different offices. Has there been any announcement about when this might go online?"*

- **Suggestion**: digitise business licence renewal
- **Inquiry**: whether it is planned or announced

> *"Municipal services like garbage collection complaints should have a WhatsApp number — it would be much easier than coming to the office. Does the council have an official WhatsApp?"*

- **Suggestion**: WhatsApp complaint channel
- **Inquiry**: whether it already exists

---

### 3.3 Banking / Finance
> *"It would be very helpful to have the ability to open a savings account entirely through the mobile app without visiting a branch. Is that something you plan to offer soon?"*

- **Suggestion**: fully digital account opening
- **Inquiry**: whether it is planned/in development

> *"You should allow customers to set spending limits on their cards through the app for security. Does the current app have any card control features already?"*

- **Suggestion**: card spending controls
- **Inquiry**: existing card control features

---

### 3.4 Education / University
> *"The university should have a dedicated mental health counselling service for students — the academic pressure here is intense. Is there a student counselling centre already?"*

- **Suggestion**: mental health support service
- **Inquiry**: whether counselling already exists on campus

> *"I think a peer mentorship programme between senior and junior students would be very beneficial. Has the student union or faculty considered this?"*

- **Suggestion**: peer mentorship programme
- **Inquiry**: whether it has been considered or piloted

---

### 3.5 Retail / E-commerce
> *"Your website should have a filter for locally manufactured products so we can support Tanzanian businesses. Do you currently have any way to filter by country of origin?"*

- **Suggestion**: local products filter
- **Inquiry**: existing product filter options

> *"You should offer same-day delivery in Dar es Salaam like some of your competitors do. Is that something you're working on?"*

- **Suggestion**: same-day delivery in urban area
- **Inquiry**: whether it is in development

---

### 3.6 Telecommunications
> *"I think you should offer a basic data bundle specifically for children's educational apps — cheap, unlimited, but restricted to learning platforms only. Do you have any parental control or educational-focused plans?"*

- **Suggestion**: educational-only data plan for children
- **Inquiry**: existing parental control or education-tier plans

---

### 3.7 Transport / Ride-hailing
> *"There should be an option to schedule a ride the night before for early morning trips to the airport. Can your app do that already, or is it only on-demand?"*

- **Suggestion**: advance ride scheduling
- **Inquiry**: whether the feature exists in the app

---

### 3.8 Hotel / Hospitality
> *"You should offer a co-working space for guests who work remotely — a dedicated room with fast wifi, desks, and printing. Do you have anything like that currently?"*

- **Suggestion**: co-working/business centre space
- **Inquiry**: whether it already exists

---

### 3.9 NGO / Social Welfare
> *"The organisation should publish monthly impact reports so beneficiaries and donors can see how funds are being used. Is there a transparency report available anywhere online?"*

- **Suggestion**: public impact/transparency reporting
- **Inquiry**: whether reports are already published

---

### 3.10 Agriculture
> *"You should have a mobile app where farmers can report crop diseases and get advice immediately instead of waiting for an agronomist to visit. Is there any digital advisory tool from your agency already?"*

- **Suggestion**: digital pest/disease reporting and advisory app
- **Inquiry**: whether digital tools exist

---

## 4. How Riviwa AI Must Handle This Combination

### Step 1 — Answer the inquiry first if possible
The inquiry may make the suggestion redundant. If the feature already exists, tell the person — and note that discoverability is the real issue.

**CORRECT when feature exists:**
> *"Nzuri sana! Tunayo system ya kuomba miadi online — unaweza kuifanya kupitia tovuti yetu au app. Lakini nimesajili pia pendekezo lako, kwa sababu ukweli kwamba hukujua inaonyesha tunaweza kufanya uwepo wake ujulikane zaidi."*
> *(Great! We do have an online appointment system — you can do it through our website or app. But I've also recorded your suggestion, because the fact that you didn't know about it shows we need to make it more visible.)*

**CORRECT when feature doesn't exist:**
> *"Kwa sasa bado hatujaanzisha mfumo wa miadi online. Nimesajili pendekezo lako na litapelekwa kwa timu ya mipango."*

### Step 2 — Log the suggestion regardless
Even if the feature exists, the suggestion tells the team it needs better marketing or discoverability.

### Step 3 — `multiple_issues: true`
```json
{
  "multiple_issues": true,
  "feedback_items": [
    {
      "feedback_type": "suggestion",
      "subject": "Online appointment booking system",
      "description": "Caller suggests adding digital appointment booking to avoid in-person queues"
    },
    {
      "feedback_type": "inquiry",
      "subject": "Does an online booking system already exist?",
      "description": "Caller asks if online booking is already available"
    }
  ]
}
```

---

## 5. Swahili Signal Phrases

**Suggestion + Inquiry (Swahili):**
- *"Mnafaa kuwa na [X]. Je, tayari mna hiyo?"* — You should have [X]. Do you already have that?
- *"Ingekuwa vizuri kama [X]. Je, hilo lipo tayari?"* — It would be good if [X]. Is that already available?
- *"Nafikiri [X] ingeweza kusaidia. Je, mmewahi fikiria hiyo?"* — I think [X] could help. Have you ever considered it?
- *"[X] ingefanya mambo kuwa rahisi zaidi. Kwa nini hamfanyi [X]?"* — [X] would make things easier. Why don't you do [X]?
- *"Je, mna [X]? Kama la, mnafaa kuanza."* — Do you have [X]? If not, you should start.

---

*Last updated: 2026-06-22 | File: obsidian_vault/KB_80_Mixed_Suggestion_Inquiry.md*
