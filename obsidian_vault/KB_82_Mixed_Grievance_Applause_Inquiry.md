# Riviwa AI — Mixed Feedback: Grievance + Applause + Inquiry

## 1. Purpose & Usage

This document trains Riviwa AI to handle feedback containing a **complaint**, a **compliment**, and a **question**. The person praises one element, reports a problem with another, and asks a question — often about how to escalate, what their rights are, or whether the problem is systemic.

This combination is especially common in **healthcare, government, and banking** where a person praises front-line staff but encounters systemic problems, and then asks who is accountable.

The AI must:
1. **Record the grievance** — with full detail, SLA triggered
2. **Record the applause** — for recognition
3. **Answer the inquiry** if possible, or flag for staff response
4. **Not let the praise reduce the seriousness of the complaint**

---

## 2. Real-World Examples Across Industries

### 2.1 Healthcare / Hospital

> *"I like the receptionist, but the nurse was very rude. I would like to know if this is how you operate every single day."*

- **Applause**: receptionist (welcoming, helpful)
- **Grievance**: nurse (rude, dismissive)
- **Inquiry**: is this systemic? Is this the normal standard of conduct?

> *"The ambulance crew were fantastic — they arrived in under 10 minutes and handled everything professionally. But when we got to the emergency room, we waited 3 hours before anyone attended to my husband. Who is the hospital administrator I can file a formal complaint with?"*

- **Applause**: ambulance crew — speed and professionalism
- **Grievance**: emergency room wait time (3 hours, no attention)
- **Inquiry**: who is the hospital administrator / formal complaint channel

> *"Dr. Fatuma is incredibly kind and competent — I always feel safe in her hands. But getting an appointment with her is nearly impossible — always two weeks out. Is there a priority booking option for existing patients?"*

- **Applause**: specific doctor
- **Grievance**: appointment availability problem
- **Inquiry**: whether priority/existing patient booking exists

---

### 2.2 Banking / Finance

> *"The new branch manager, Mr. Osei, is doing an incredible job — the service is faster and the staff are now polite. But last month I was charged fees I never agreed to. I'm told it's 'system-generated' — can you tell me exactly who approved this fee and whether I can waive it?"*

- **Applause**: branch manager
- **Grievance**: unapproved fees
- **Inquiry**: who authorised the fee and whether a waiver is possible

> *"Your customer care agent, Amina, was incredibly patient and professional when I called about my lost card. But the replacement took 21 days. What is the standard processing time supposed to be, and is there a way to expedite in future?"*

- **Applause**: named customer care agent
- **Grievance**: excessively long card replacement time
- **Inquiry**: standard SLA for card replacement + expedite option

---

### 2.3 Government / Public Services

> *"The officer who processed my passport renewal was helpful and professional. But the passport itself was delivered with my name misspelled. Does the office have a correction process and how long does it take?"*

- **Applause**: processing officer
- **Grievance**: error in issued document
- **Inquiry**: correction process and timeline

> *"The community health workers in our area are excellent — they visit regularly and follow up. But the medicines they bring have been out of stock for the past two months. Is there a shortage nationally or is this just our district?"*

- **Applause**: community health workers
- **Grievance**: medicine stockout for two months
- **Inquiry**: whether the shortage is national or local

---

### 2.4 Education / University

> *"My lecturers in the science department are brilliant and always available. But the computer lab has only 20 working machines for 200 students. What is the university's plan to address this? Has it been budgeted for?"*

- **Applause**: science department lecturers
- **Grievance**: severe computer lab resource shortage
- **Inquiry**: whether IT infrastructure improvement has been planned and budgeted

---

### 2.5 Hotel / Hospitality

> *"The chef and the kitchen staff clearly take pride in their work — breakfast was spectacular every morning. But our room was broken into on day two and valuables were taken. We filed a report with your security team. Has the investigation concluded and will we receive any compensation?"*

- **Applause**: kitchen / restaurant team
- **Grievance**: room security breach, theft
- **Inquiry**: status of investigation and compensation entitlement

---

### 2.6 Retail / Supermarket

> *"The cashiers at this branch are always polite and efficient — really a great team. But I bought chicken last Saturday that was already off when I opened it at home — it was within the sell-by date on the label. What is your procedure for returning food products and getting a refund?"*

- **Applause**: cashier team
- **Grievance**: defective food product (spoiled within sell-by date)
- **Inquiry**: food return and refund procedure

---

### 2.7 Transport / Airline

> *"The flight crew were exceptional — friendly, professional, and handled a turbulent flight with complete calm. But my connecting flight was cancelled with no notice and no assistance provided at the airport. What compensation am I entitled to under aviation regulations for a cancelled connection?"*

- **Applause**: flight crew conduct
- **Grievance**: flight cancellation, no ground support provided
- **Inquiry**: passenger compensation entitlement under aviation law

---

### 2.8 Telecommunications

> *"Your technical support agent was very thorough and resolved the issue in one visit. But I have been without internet for 11 days while waiting for that visit. Do I get a credit on my bill for the days of service I didn't receive?"*

- **Applause**: technical support agent
- **Grievance**: 11-day outage before technician arrived
- **Inquiry**: whether bill credit/pro-rata refund applies for downtime

---

## 3. How Riviwa AI Must Handle This Combination

### Priority: Grievance first, inquiry close

**CORRECT turn-by-turn approach:**

**Turn 1 (User):** *"I like the receptionist, but the nurse was very rude. I would like to know if this is how you operate every single day."*

**Turn 1 (AI):** Acknowledge both. Note the question. Focus complaint data collection first.
> *"Nashukuru kwa sifa ya receptionist — hiyo ni muhimu. Lakini malalamiko kuhusu muuguzi ni jambo zito. Naandika hilo rasmi. Muuguzi huyo alifanya au kusema nini hasa?"*

**Turn 2 (User):** *"Alikataa kunisaidia na kunisemea ukali mbele ya watu wote."*

**Turn 2 (AI):** Record description. Get location/time.
> *"Hiyo ni ya kuudhi sana. Hii ilitokea wapi — ni wodi gani au sehemu gani ya hospitali, na ilikuwa saa ngapi?"*

**Turn 3 (User):** *"Wodi ya wazazi, asubuhi ya leo."*

**Turn 3 (AI):** Now address the inquiry.
> *"Nimesajili malalamiko yako. Kuhusu swali lako — hospitali inafuata viwango vya huduma na tabia ya wafanyakazi. Matibabu ya aina hii si ya kawaida inayokubalika. Menejimenti watapitia na kuchukua hatua. Je, niwasilishe malalamiko na sifa zote mbili?"*

### `multiple_issues: true`
```json
{
  "multiple_issues": true,
  "feedback_items": [
    {
      "feedback_type": "applause",
      "subject": "Receptionist — welcoming and helpful",
      "description": "Patient praises receptionist conduct"
    },
    {
      "feedback_type": "grievance",
      "subject": "Nurse in maternity ward — rude and dismissive",
      "description": "Nurse refused to help patient and spoke harshly in front of others"
    },
    {
      "feedback_type": "inquiry",
      "subject": "Is this the standard of conduct at the hospital?",
      "description": "Patient asking whether rude staff conduct is systemic or isolated"
    }
  ]
}
```

---

## 4. Swahili Signal Phrases

**G+A+I patterns (Swahili):**
- *"[X] alifanya kazi nzuri, lakini [Y] alikuwa mbaya. Je, hii ndiyo kawaida yenu?"*
  *[X] did well, but [Y] was bad. Is this your normal standard?*
- *"Ninaipongeza [X]. Hata hivyo [tatizo]. Nataka kujua [swali]."*
  *I commend [X]. However [problem]. I want to know [question].*
- *"[X] ni wa kupongezwa. Lakini [tatizo] halikubaliki. Ninaweza kuwasiliana na nani kuhusu hilo?"*
  *[X] deserves praise. But [problem] is unacceptable. Who can I contact about that?*

---

*Last updated: 2026-06-22 | File: obsidian_vault/KB_82_Mixed_Grievance_Applause_Inquiry.md*
