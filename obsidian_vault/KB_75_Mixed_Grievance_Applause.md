# Riviwa AI — Mixed Feedback: Grievance + Applause

## 1. Purpose & Usage

This document trains Riviwa AI to handle feedback that simultaneously contains a **complaint or grievance** AND a **compliment or applause**. This is one of the most common real-world feedback patterns: a person praises one aspect of their experience while criticising another. The AI must:

1. **Detect both signals** — do not let the praise cancel out the complaint or vice versa
2. **Log both types** — create `feedback_type: grievance` AND `feedback_type: applause` as separate records, or use `multiple_issues: true` with `feedback_items` listing both
3. **Acknowledge both** — respond in a way that validates the praise AND takes the complaint seriously
4. **Not let positivity suppress urgency** — if the complaint is urgent, the presence of a compliment does not lower priority

---

## 2. The Core Pattern

The person had a **split experience**: one element was good, another was bad. They are not confused — they are being precise. This is the feedback pattern of a careful, thoughtful person who wants to give credit where it is due while also holding the organisation accountable.

**Linguistic markers that signal this combination:**

- Contrast connectors: *but, however, although, yet, while, on the other hand, at the same time, whereas, even though, despite, in contrast, that said, having said that*
- Sequential praise-then-complaint: *"[X] was wonderful — but [Y] was terrible"*
- Sequential complaint-then-praise: *"[X] was awful, though I must say [Y] was excellent"*
- Attributing each quality to a different person or department: *"The receptionist... but the nurse..."*, *"the food... but the service..."*

---

## 3. Real-World Examples Across Industries

### 3.1 Healthcare / Hospital
> *"I like the receptionist, but the nurse was very rude. I would like to know if this is how you operate every single day."*

- **Applause**: receptionist → kind, welcoming, helpful
- **Grievance**: nurse → rude, disrespectful staff conduct
- **Embedded Inquiry**: "is this how you operate every single day?" → challenge to management

> *"Dr. Kimani was absolutely brilliant — he explained everything clearly and made me feel safe. However, the ward was filthy. There was blood on the bed when I arrived."*

- **Applause**: doctor → excellent diagnosis, communication, empathy
- **Grievance**: ward hygiene → blood on bed, unacceptable cleanliness standards

> *"The surgery went perfectly and the theatre team was outstanding. But I was discharged with no instructions — I did not know what medication to take or when to come back."*

- **Applause**: surgical team, procedure outcome
- **Grievance**: discharge process failure, no post-care communication

---

### 3.2 Restaurant / Food Service
> *"The food was absolutely delicious — the best ugali I have ever had. But the waiter ignored our table for 40 minutes. We had to walk to the counter to order."*

- **Applause**: food quality → excellent
- **Grievance**: service failure → waitstaff unresponsive

> *"I loved the ambiance and the decor is stunning. But I found a hair in my food and when I reported it the manager was dismissive."*

- **Applause**: ambiance, interior design
- **Grievance**: hygiene issue + staff conduct

---

### 3.3 Banking / Financial Services
> *"Your mobile app is excellent — fast, clean, and easy to use. I use it every day. However, I was charged a fee I was never told about when I opened this account. That is not acceptable."*

- **Applause**: mobile banking product
- **Grievance**: undisclosed fee, billing transparency failure

> *"The teller at the Kariakoo branch was patient and very helpful — she even stayed past closing time to help me. But the ATM outside has been broken for three weeks and nobody has fixed it."*

- **Applause**: named staff member, going above and beyond
- **Grievance**: infrastructure failure, unresolved maintenance issue

---

### 3.4 Government / Public Services
> *"The officer at the counter was polite and efficient — I was in and out in 20 minutes. But the parking area outside is completely unusable. There are no markings and it floods when it rains."*

- **Applause**: front-line officer, service speed
- **Grievance**: facilities issue, parking infrastructure

> *"My complaint was handled very professionally and I received a fair resolution. But it took six months to get here. Six months for something that should take two weeks."*

- **Applause**: quality of resolution, professionalism
- **Grievance**: excessive turnaround time, SLA failure

---

### 3.5 Telecommunications
> *"The network coverage in my area has improved massively — no more dropped calls. I'm genuinely impressed. But customer care is still terrible. I called four times last week and nobody could solve my billing problem."*

- **Applause**: network quality improvement
- **Grievance**: customer care failure, unresolved billing issue

---

### 3.6 Education / University
> *"Professor Mwangi is outstanding — the best lecturer I have ever had. He explains complex things simply and always has time for students. However, the library closes at 5pm which makes it impossible for evening students to study."*

- **Applause**: specific staff member, teaching quality
- **Grievance**: facilities policy, operating hours exclusion

> *"The curriculum for this course is very well designed and I am learning a great deal. But the online portal is consistently broken. Assignments submitted there are not showing up and we risk late penalties."*

- **Applause**: course content quality
- **Grievance**: technical failure in a system students depend on

---

### 3.7 Hotel / Hospitality
> *"The room was immaculate and the view was breathtaking. But the breakfast was cold every single morning and when I complained on day three the staff just shrugged."*

- **Applause**: room quality, cleanliness
- **Grievance**: food service failure + indifferent staff response

> *"The concierge went out of his way to arrange transport and recommend the best local restaurants — absolutely exceptional service. But the pool was closed for the entire duration of our stay with no prior notice."*

- **Applause**: concierge service
- **Grievance**: undisclosed facility closure, no communication

---

### 3.8 Agriculture / Input Supplier
> *"The agronomist who visited our farm was very knowledgeable and gave us excellent advice on soil preparation. But the fertiliser we bought from your shop last month was counterfeit — the seeds barely germinated."*

- **Applause**: extension officer, advisory service
- **Grievance**: counterfeit/defective product

---

### 3.9 Transport / Bus / Ride-hailing
> *"The driver was friendly, drove safely and arrived on time. But the vehicle was in terrible condition — torn seats, no AC, and the window could not close."*

- **Applause**: driver conduct and professionalism
- **Grievance**: vehicle condition and safety concerns

---

### 3.10 Retail / Supermarket
> *"The cashier was so kind and helped me find everything I needed. But the price on the shelf said 4,500 shillings and at the till I was charged 6,200. That is misleading."*

- **Applause**: staff helpfulness
- **Grievance**: price discrepancy, misleading labelling

---

## 4. How Riviwa AI Must Handle This Combination

### Step 1 — Acknowledge both signals explicitly
Do NOT only respond to the complaint. Do NOT only respond to the praise.

**CORRECT:**
> *"Nashukuru kwa sifa uliyompa daktari — hiyo ni muhimu. Lakini pia naona una wasiwasi mkubwa kuhusu muuguzi. Hebu tuandike malalamiko hayo rasmi. Muuguzi huyo alifanya nini hasa?"*
> *(Thank you for the praise you gave the doctor — that is important. But I also see you have a serious concern about the nurse. Let me formally record that complaint. What exactly did the nurse do?)*

**WRONG:**
> *"Asante kwa maoni yako mazuri!"* (only acknowledging the praise and ignoring the complaint)

### Step 2 — Prioritise the complaint for data collection
Praise can be logged quickly. The complaint needs full detail: what happened, who, where, when, how severe.

### Step 3 — Set `multiple_issues: true` and populate `feedback_items`
```json
{
  "multiple_issues": true,
  "feedback_items": [
    {
      "feedback_type": "applause",
      "subject": "Receptionist — excellent service",
      "description": "The receptionist was welcoming and efficient"
    },
    {
      "feedback_type": "grievance",
      "subject": "Nurse — rude conduct",
      "description": "The nurse was dismissive and disrespectful"
    }
  ]
}
```

### Step 4 — Do not let the praise reduce urgency
If the complaint element involves health, safety, financial harm, or discrimination, `is_urgent` must still be set appropriately regardless of the accompanying praise.

---

## 5. AI Conversation Flow — One Question at a Time

**Turn 1 (User):** *"I like the receptionist, but the nurse was very rude."*
**Turn 1 (AI):** Acknowledge both. Focus on the complaint. Ask: *"What did the nurse do or say that was rude?"*

**Turn 2 (User):** *"She refused to attend to me and told me to sit down and wait when I told her my child was in pain."*
**Turn 2 (AI):** Note urgency. Ask: *"Which ward or department was this, and approximately when did this happen?"*

**Turn 3 (User):** *"Paediatric ward, this morning around 10am."*
**Turn 3 (AI):** Sufficient data. Confirm and ask: *"Just to confirm: applause for the receptionist, and a grievance about the nurse in the paediatric ward who refused to attend to your child this morning. Shall I submit both?"*

---

## 6. Swahili Signal Phrases

**Contrast connectors (Swahili):**
lakini (but), hata hivyo (however), ingawa (although), kwa upande mwingine (on the other hand), pamoja na hilo (despite that), licha ya hilo (notwithstanding), wakati huohuo (at the same time), bado (yet/still)

**Mixed feedback patterns (Swahili):**
- *"Ninapenda X, lakini Y ilikuwa mbaya sana"* — I like X, but Y was very bad
- *"X ilikuwa bora, hata hivyo Y..."* — X was good, however Y...
- *"Nashukuru kwa X, lakini nina wasiwasi kuhusu Y"* — I'm grateful for X, but I have a concern about Y
- *"Daktari alifanya kazi nzuri, lakini muuguzi alikuwa mkali sana"* — The doctor did good work, but the nurse was very harsh

---

*Last updated: 2026-06-22 | File: obsidian_vault/KB_75_Mixed_Grievance_Applause.md*
