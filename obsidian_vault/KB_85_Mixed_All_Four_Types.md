# Riviwa AI — Mixed Feedback: All Four Types (Grievance + Applause + Suggestion + Inquiry)

## 1. Purpose & Usage

This document trains Riviwa AI to handle feedback that contains **all four feedback types simultaneously**: a complaint, a compliment, a suggestion, and a question. This is the most complex real-world feedback pattern and represents the feedback of a highly articulate, deeply invested person who has had a nuanced, multi-dimensional experience.

Examples of who gives this type of feedback:
- A patient who experienced excellent nursing care but terrible facilities, has an idea for improvement, and wants to know who is accountable
- A customer who loves the product but had a billing issue, suggests a fix, and asks whether they are entitled to a refund
- A community member who praises an NGO's fieldwork but reports an administrative failure, proposes a system improvement, and asks about reporting channels

The AI must:
1. **Detect all four signals** — do not collapse or miss any
2. **Acknowledge all four explicitly** in the response
3. **Collect grievance details first** — it is the only time-sensitive element
4. **Log applause for recognition**
5. **Log suggestion for improvement team**
6. **Answer inquiry if possible, otherwise flag for staff**
7. **Use `multiple_issues: true` with four `feedback_items`**
8. **Maintain composure** — a long multi-part message is not an emergency unless the grievance signals urgency

---

## 2. Real-World Examples Across Industries

### 2.1 Healthcare / Hospital — The Classic Case

> *"I like the receptionist, she was very welcoming and helpful. But the nurse in ward 3 was extremely rude — she refused to attend to me and told me to 'just sit down.' I think all nurses should go through a mandatory customer care refresher every six months. And I would like to know: does this hospital have a patient rights officer I can speak to about this?"*

- **Applause**: receptionist — welcoming and helpful
- **Grievance**: nurse in ward 3 — refused to attend, spoken to rudely
- **Suggestion**: mandatory 6-monthly customer care refresher for nurses
- **Inquiry**: is there a patient rights officer and how to reach them

> *"Dr. Osei is an absolutely brilliant doctor — one of the best I have encountered. But the hospital pharmacy was out of stock of the medication he prescribed. I had to go to three pharmacies outside the hospital. You should maintain a minimum stock level for commonly prescribed drugs. Is there a way to pre-order before my next appointment so this doesn't happen again?"*

- **Applause**: Dr. Osei — brilliant, exceptional care
- **Grievance**: pharmacy stockout of prescribed medication
- **Suggestion**: minimum stock level policy for common prescriptions
- **Inquiry**: whether pre-ordering medication before appointments is possible

---

### 2.2 Banking / Finance

> *"Your relationship manager, Grace, is outstanding — she has been proactive, transparent, and genuinely helpful every step of the way. But last month I was debited three times for the same standing order. I have raised it twice with the branch and nothing has been done. You need a proper duplicate transaction detection system. And what is your formal escalation process if a branch fails to resolve a complaint within the standard timeframe?"*

- **Applause**: named relationship manager
- **Grievance**: triple debit error, no resolution after two branch visits
- **Suggestion**: automated duplicate transaction detection
- **Inquiry**: formal escalation process beyond branch level

> *"The savings product your bank launched last year is genuinely innovative and I have recommended it to everyone I know. However, I was charged a dormancy fee without any prior warning after only 45 days. You should send a warning SMS at least 14 days before charging dormancy fees. By the way, can this fee be waived given that I am an active customer on all other accounts?"*

- **Applause**: innovative savings product
- **Grievance**: dormancy fee charged without prior warning
- **Suggestion**: 14-day advance warning SMS before dormancy fees
- **Inquiry**: whether fee can be waived for otherwise-active customers

---

### 2.3 Government / Public Services

> *"The new ward executive officer, Madam Leah, has transformed this office — it is clean, organised, and the staff now actually help people. But the water pump serving our village has been broken for three weeks and no one has come to fix it. The council should have a dedicated infrastructure emergency unit that responds within 48 hours. Who do I contact to report a broken community water pump as an emergency?"*

- **Applause**: new ward executive officer
- **Grievance**: broken community water pump — 3 weeks without response
- **Suggestion**: 48-hour infrastructure emergency response unit
- **Inquiry**: correct emergency contact for broken water infrastructure

---

### 2.4 Education / University

> *"Professor Mwamba is genuinely exceptional — rigorous, fair, and always available. She is the reason I chose to stay in this programme. But the online submission portal has been broken for three weeks and three of my assignments were marked late because of it. The university should have a backup submission channel — email to the department should always be accepted. Has anyone been penalised for late submissions due to the portal failure, and will those marks be reviewed?"*

- **Applause**: named professor
- **Grievance**: broken portal causing unfair late submission penalties
- **Suggestion**: backup submission channel (email accepted as fallback)
- **Inquiry**: whether late marks due to portal failure will be reviewed

---

### 2.5 Hotel / Hospitality

> *"The restaurant team here is world-class — the head chef clearly has a gift and the waitstaff are warm, attentive, and professional. However, we were placed in a room directly above the generator room and it was unbearably loud all night — completely ruined the sleep. I think the hotel should never place guests in those rooms without disclosing this at check-in. What is the hotel's compensation policy for a disrupted stay, and can we be upgraded for the remaining nights?"*

- **Applause**: restaurant team, chef, and waitstaff
- **Grievance**: noisy room above generator — disrupted sleep, not disclosed at check-in
- **Suggestion**: mandatory disclosure for affected rooms at check-in
- **Inquiry**: compensation policy + room upgrade request

---

### 2.6 Retail / E-commerce

> *"Your app is genuinely excellent — fast, well-designed, and the product range is incredible. But I placed an order 22 days ago that has not arrived. I have contacted support four times and each time I am told it will arrive 'in 2-3 days.' You need a real-time order tracking system that gives accurate updates. And what is my legal entitlement if a product doesn't arrive within the stated delivery window?"*

- **Applause**: app quality, product range
- **Grievance**: 22-day undelivered order, repeated false assurances
- **Suggestion**: real-time tracking with accurate updates
- **Inquiry**: legal entitlement for non-delivery

---

### 2.7 Agriculture / Input Supplier

> *"Your agronomist, John Mwema, is exceptional. He visited our cooperative three times this season and his advice doubled our yield. But the hybrid seeds we ordered in March arrived in June — three months late, after planting season was over. The company must have a pre-season pre-order system with guaranteed delivery windows. And can we be compensated for the season we lost — or at minimum get a discount for next season's order?"*

- **Applause**: named agronomist, quality advisory service
- **Grievance**: seeds delivered 3 months late, after planting season
- **Suggestion**: pre-season pre-order with guaranteed delivery windows
- **Inquiry**: compensation for lost season or discount on next order

---

### 2.8 Telecommunications

> *"Your network engineer, Baraka, was absolutely outstanding — he came on a Sunday morning without being asked and restored our internet within two hours. That level of dedication deserves recognition. However, the outage itself lasted nine days, which caused significant losses for our business. You need a commercial customer priority queue so businesses aren't treated the same as home users. And does our business contract include any SLA penalty clause for outages exceeding 48 hours?"*

- **Applause**: named network engineer
- **Grievance**: 9-day outage causing business losses
- **Suggestion**: separate commercial priority queue for business customers
- **Inquiry**: SLA penalty clause in business contract

---

### 2.9 NGO / Social Welfare

> *"The field officers in Morogoro are doing incredible work — visiting families, collecting data carefully, genuinely caring. But the monthly cash transfers have been delayed for four months. The beneficiaries are suffering. The organisation needs a transparent payment dashboard beneficiaries can check on their phones. I want to know: who is the country director responsible for overseeing payment disbursements, and how do I reach them directly?"*

- **Applause**: field officer team and dedication
- **Grievance**: 4-month payment delay causing hardship for beneficiaries
- **Suggestion**: transparent beneficiary-facing payment dashboard
- **Inquiry**: country director name and contact for direct escalation

---

## 3. How Riviwa AI Must Handle This Combination

### The guiding principle — hold all four, lose none

The most common AI failure with this combination is **focusing on only one signal** — usually the most recent, the most emotional, or the first one. Riviwa AI must track all four throughout the conversation.

### Conversation flow

**Turn 1 (User):** Gives all four signals in one message.

**Turn 1 (AI):** Acknowledge all four briefly. Pivot to grievance detail collection.
> *"Nimesikia mambo manne muhimu katika ujumbe wako: sifa kwa daktari, malalamiko kuhusu dawa kukosekana, pendekezo la akiba ya dawa, na swali la pre-order. Nimeyaandika yote. Hebu tuanzie na malalamiko — kwa sababu yanachukua muda wa ufumbuzi. Ni dawa gani hasa zilizokosekana?"*

**Turn 2–3:** Collect grievance detail (what, who, when, impact).

**Turn 4 (AI):** Note the applause, suggestion, and inquiry explicitly before confirming.
> *"Vizuri. Hapa kuna muhtasari wa mambo manne:
> 1. Sifa: Dkt. Osei — bora sana
> 2. Malalamiko: Dawa 'X' haikuwepo, nilipotuma mitaa mitatu
> 3. Pendekezo: Weka akiba ya chini ya dawa zinazopendekeza mara nyingi
> 4. Swali: Pre-order kabla ya miadi inawezekana?
> Je, niwasilishe yote manne?"*

### `multiple_issues: true` with four items
```json
{
  "multiple_issues": true,
  "feedback_items": [
    {
      "feedback_type": "applause",
      "subject": "Dr. Osei — exceptional diagnostic skills",
      "description": "Patient praises doctor's expertise and care"
    },
    {
      "feedback_type": "grievance",
      "subject": "Pharmacy stockout — prescribed medication unavailable",
      "description": "Patient had to visit 3 external pharmacies after prescription could not be filled"
    },
    {
      "feedback_type": "suggestion",
      "subject": "Maintain minimum stock of commonly prescribed drugs",
      "description": "Patient suggests setting a minimum stock level policy for frequently prescribed medications"
    },
    {
      "feedback_type": "inquiry",
      "subject": "Can medication be pre-ordered before appointment?",
      "description": "Patient asks if pre-ordering is possible to prevent future stockouts"
    }
  ]
}
```

---

## 4. Complete Combination Matrix Reference

| # | Types | Example Pattern |
|---|---|---|
| 1 | G only | "The nurse was rude." |
| 2 | A only | "The doctor was excellent." |
| 3 | S only | "You should add more seats." |
| 4 | I only | "What time do you open?" |
| 5 | G+A | "I like the receptionist but the nurse was rude." |
| 6 | G+S | "The road is broken — fix it and add speed bumps." |
| 7 | G+I | "I was overcharged. What is the refund process?" |
| 8 | A+S | "Great food! You should add a vegetarian menu." |
| 9 | A+I | "Amazing service! Do you deliver?" |
| 10 | S+I | "You should have an app — do you already?" |
| 11 | G+A+S | "Great manager, terrible facility. Please renovate." |
| 12 | G+A+I | "Staff kind but 3hr wait. Is there a faster option?" |
| 13 | G+S+I | "Road broken. Fix it. Who is responsible?" |
| 14 | A+S+I | "Love this bank! Add savings goals. Do you have them?" |
| 15 | G+A+S+I | "I like the receptionist, but the nurse was rude. Nurses need training. Is there a patient rights officer?" |

---

## 5. Swahili Signal Phrases for All-Four Pattern

**Detection phrases:**
- *"[Sifa]. Lakini [tatizo]. Wafaa [suluhisho]. Na ninataka kujua [swali]."*
  *[Praise]. But [problem]. They should [solution]. And I want to know [question].*
- *"Napongeza [X]. Hata hivyo, [Y ilikuwa mbaya]. Pendekezo langu ni [Z]. Je, [swali]?"*
  *I commend [X]. However, [Y was bad]. My suggestion is [Z]. Is/Does [question]?*
- *"[X] ni bora. [Y] ni tatizo. Wangeweza [Z]. Naomba kujua [swali]."*
  *[X] is excellent. [Y] is a problem. They could [Z]. I'd like to know [question].*

---

*Last updated: 2026-06-22 | File: obsidian_vault/KB_85_Mixed_All_Four_Types.md*
