# Riviwa AI — Mixed Feedback: Grievance + Inquiry

## 1. Purpose & Usage

This document trains Riviwa AI to handle feedback combining a **complaint** with a **question**. The person is both lodging a problem AND asking for information — often because the problem itself creates questions: *"My package hasn't arrived — where is it?"*, *"I was overcharged — what is your refund policy?"*, *"The nurse was rude — does this hospital have a patient rights officer I can speak to?"*

The AI must:
1. **Acknowledge the complaint** as the primary issue
2. **Record the grievance** with full detail
3. **Attempt to answer the inquiry** if the answer is known from context or org structure
4. **Flag unanswered inquiries** for staff to respond to
5. **Never let the question distract from recording the complaint**

---

## 2. The Core Pattern

The inquiry is almost always triggered by the grievance — it is a request for accountability, clarification, redress, or escalation:
- *What is your policy on this?*
- *Who is responsible for this?*
- *How do I get a refund / compensation / resolution?*
- *Is this normal? Does this happen to everyone?*
- *Who can I speak to about this?*
- *When will this be fixed?*

**Linguistic markers:**
- Question words after or within a complaint: *who, what, when, where, why, how, is this, does this, can I, will you*
- Accountability questions: *"who is responsible", "who do I talk to", "what are you going to do about this"*
- Policy questions: *"what is the procedure", "what is the policy", "am I entitled to", "do I qualify for"*
- Timeline questions: *"how long", "when will", "by when"*

---

## 3. Real-World Examples Across Industries

### 3.1 Healthcare
> *"I like the receptionist, but the nurse was very rude. I would like to know if this is how you operate every single day."*

- **Grievance**: nurse was rude — staff conduct complaint
- **Inquiry**: "is this how you operate every single day?" — challenge to management about systemic conduct

> *"My husband was sent home from the emergency room without proper treatment. He is now in serious pain. Who is the patient rights officer at this hospital and how do I reach them?"*

- **Grievance**: inadequate emergency care, premature discharge
- **Inquiry**: how to access patient rights/advocacy officer

> *"I was given the wrong medication at the pharmacy. I only realised when I got home. What should I do now — should I take the original medication I was given or wait?"*

- **Grievance**: dispensing error at pharmacy
- **Inquiry**: urgent medical guidance on what action to take (note: this requires immediate escalation — `is_urgent: true`)

---

### 3.2 Government / Public Services
> *"My application for a building permit has been pending for eight months with no update. Who is in charge of this, and what is the legal maximum processing time?"*

- **Grievance**: excessive delay, lack of communication
- **Inquiry**: who is accountable + what the legal SLA is

> *"The water supply in our area has been cut off for 11 days. We have not been given any reason or update. When is it coming back and what compensation are we entitled to?"*

- **Grievance**: extended service outage affecting an entire area
- **Inquiry**: restoration timeline + entitlement to compensation

---

### 3.3 Banking / Finance
> *"I was charged 15,000 shillings as a maintenance fee that I never agreed to. I want this reversed. What is the process for disputing a charge?"*

- **Grievance**: unauthorised/unexplained bank charge
- **Inquiry**: dispute/refund process

> *"Someone made three transactions from my account that I did not authorise. I have reported it to the branch but nothing has happened in a week. Who do I escalate this to and is my remaining money safe?"*

- **Grievance**: fraud/unauthorised transactions, no action taken by branch
- **Inquiry**: escalation path + account security status (note: `is_urgent: true`)

---

### 3.4 E-commerce / Online Retail
> *"My order was placed 18 days ago and has not arrived. The tracking link shows nothing. I want a refund — what is your refund policy and how long does it take?"*

- **Grievance**: undelivered order, broken tracking
- **Inquiry**: refund policy and timeline

> *"I received a counterfeit item — the packaging looks fake and the product does not work. Can I get a replacement or full refund, and should I report this to consumer protection?"*

- **Grievance**: counterfeit product received
- **Inquiry**: replacement/refund options + whether to report to regulators

---

### 3.5 Telecommunications
> *"I have been without internet for five days. I work from home and this has cost me clients and income. Who do I contact for compensation and does your service level agreement cover business losses?"*

- **Grievance**: prolonged outage causing financial harm
- **Inquiry**: compensation process + SLA coverage for business losses

---

### 3.6 Transport / Airline / Bus
> *"My luggage was lost on the flight from Nairobi to Dar es Salaam two days ago. I have filed a report but no one has called me back. What is the maximum compensation I am entitled to under airline regulations?"*

- **Grievance**: lost luggage, no follow-up
- **Inquiry**: legal compensation entitlement under aviation regulations

> *"The bus departed 2 hours late and I missed a job interview. This has happened three times on this route. Is there a way to claim compensation and who is the management I can write to?"*

- **Grievance**: repeated delays causing measurable harm
- **Inquiry**: compensation process + management contact

---

### 3.7 Education / University
> *"My exam results were different from what was announced in class — I scored 74% but my transcript shows 54%. I have raised this with the lecturer and got no response. Who do I appeal to and what is the deadline for grade appeals?"*

- **Grievance**: incorrect exam results, no response from lecturer
- **Inquiry**: formal appeal process and deadline

---

### 3.8 Insurance
> *"I submitted my car insurance claim two months ago with all documents and nothing has happened. I have followed up six times. Is there a regulatory body I can report this to if the company does not respond?"*

- **Grievance**: claim processing delay, unresponsive insurer
- **Inquiry**: regulatory escalation path (e.g., Tanzania Insurance Regulatory Authority)

---

### 3.9 Real Estate / Property
> *"My landlord has not repaired the broken water heater for two months despite multiple requests. Am I allowed to deduct the repair cost from my rent under Tanzanian law?"*

- **Grievance**: maintenance failure by landlord
- **Inquiry**: legal rights of tenant regarding maintenance deductions

---

### 3.10 NGO / Social Welfare
> *"I was removed from the beneficiary list without explanation. I have been receiving assistance for two years and suddenly it stopped. Who reviews these decisions and how do I appeal?"*

- **Grievance**: unexplained removal from benefits
- **Inquiry**: decision review and appeal process

---

## 4. How Riviwa AI Must Handle This Combination

### Step 1 — Prioritise recording the grievance
The complaint requires resolution tracking. The inquiry needs to be noted but should not delay capturing the grievance details.

### Step 2 — Answer the inquiry if possible from context
If the org has provided standard information (e.g., "contact the Patient Rights Officer at ext. 204"), provide it. If not, flag it: *"I have noted your question — staff will respond to that specifically when they review your case."*

### Step 3 — Never let the question replace the complaint record
This is the critical error to avoid: AI that only answers the question and forgets to log the complaint.

**WRONG:**
> User: *"I was overcharged — what is the refund process?"*
> AI: *"Refunds take 5-7 business days and you can apply at the branch."*
> *(The overcharge complaint was never recorded.)*

**CORRECT:**
> AI: *"Nimesajili malalamiko yako kuhusu malipo ya ziada. Pia nimeandika swali lako kuhusu mchakato wa kurudisha pesa — timu itajibu hiyo pia. Kwanza, naomba nikusaidie na malalamiko: ulitozwa kiasi gani zaidi ya ulichotarajiwa?"*

### Step 4 — `multiple_issues: true` for separate log
```json
{
  "multiple_issues": true,
  "feedback_items": [
    {
      "feedback_type": "grievance",
      "subject": "Overcharged — undisclosed fee",
      "description": "Customer was charged 15,000 TZS maintenance fee not agreed to at account opening"
    },
    {
      "feedback_type": "inquiry",
      "subject": "What is the charge dispute process?",
      "description": "Customer asks for the formal process to dispute and reverse the charge"
    }
  ]
}
```

---

## 5. AI Conversation Flow

**Turn 1 (User):** *"My package has not arrived in 18 days and I want a refund. How long does a refund take?"*
**Turn 1 (AI):** *"Naelewa — muda huo ni mrefu sana. Nimesajili tatizo hili. Refund kwa kawaida inachukua siku 5-7 za kazi baada ya kuidhinishwa. Lakini kwanza — je, una namba ya order yako ili niweze kuisajili kwa usahihi?"*

**Turn 2 (User):** *"Ndiyo — ORD-2026-08847"*
**Turn 2 (AI):** *"Asante. Na ulichonunua kilikuwa nini — ili malalamiko iwe wazi?"*

**Turn 3 (User):** *"Simu ya Samsung, nililipia 280,000 shillings."*
**Turn 3 (AI):** *"Nimesajili malalamiko: simu haikufika baada ya siku 18, na swali lako kuhusu muda wa refund. Je, niwasilishe?"*

---

## 6. Swahili Signal Phrases

**Grievance + Inquiry patterns (Swahili):**
- *"[Tatizo]. Nataka kujua [swali]"* — [Problem]. I want to know [question]
- *"[X ilikuwa mbaya]. Je, hii ndiyo kawaida yenu?"* — [X was bad]. Is this your normal way of operating?
- *"[Tatizo]. Niwasiliane na nani?"* — [Problem]. Who do I contact?
- *"[X halifanyika]. Lini itafanyika?"* — [X didn't happen]. When will it happen?
- *"[Nimedhulumiwa]. Nina haki ya nini?"* — [I was wronged]. What am I entitled to?
- *"[Tatizo]. Mchakato wa malalamiko ni upi?"* — [Problem]. What is the complaint process?

---

*Last updated: 2026-06-22 | File: obsidian_vault/KB_77_Mixed_Grievance_Inquiry.md*
