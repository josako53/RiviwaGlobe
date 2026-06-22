# Riviwa AI — Mixed Feedback: Applause + Suggestion + Inquiry

## 1. Purpose & Usage

This document trains Riviwa AI to handle feedback combining **genuine praise**, a **suggestion for improvement**, and a **question**. There is no complaint here — the person is satisfied and engaged. They want to share what they love, propose something that would make it even better, and get an answer to something they are curious about.

This is the feedback of a highly engaged loyal customer, community member, or advocate. The tone is positive throughout — the suggestion is constructive, the inquiry is curious rather than confrontational.

The AI must:
1. **Log the applause** — for staff/service recognition
2. **Record the suggestion** — for the improvement team
3. **Answer the inquiry** where possible from org context
4. **Maintain a warm, enthusiastic tone** — match the person's positive energy
5. **Not introduce urgency or escalation** — this is entirely positive feedback with a question

---

## 2. Real-World Examples Across Industries

### 2.1 Healthcare / Pharmacy

> *"I love this pharmacy so much — the staff know me by name, the prices are fair, and everything is always in stock. It would be amazing if you added a prescription reminder service via SMS. By the way, do you accept NHIF?"*

- **Applause**: personalised service, pricing, stock availability
- **Suggestion**: SMS prescription reminder service
- **Inquiry**: whether NHIF insurance is accepted

> *"The antenatal services here are outstanding — the midwives are caring and the facility is clean and welcoming. I think adding a breastfeeding support group for new mothers would be very valuable. Do you run any postnatal classes?"*

- **Applause**: antenatal services, midwife quality
- **Suggestion**: breastfeeding support group
- **Inquiry**: whether postnatal classes exist

---

### 2.2 Banking / Finance

> *"Your mobile banking app is the best in the country — intuitive, fast, and I've never had a security issue. I'd love a feature that lets me set savings goals and track progress automatically. Also, do you offer fixed deposit accounts with monthly interest payouts?"*

- **Applause**: app quality, reliability, security
- **Suggestion**: savings goal tracking feature
- **Inquiry**: fixed deposit with monthly interest

> *"Your business account has been excellent — the relationship manager assigned to us is proactive and always available. We'd love a quarterly business health report summarising our transactions. Does your business banking offer any analytics dashboard?"*

- **Applause**: relationship manager quality, proactive service
- **Suggestion**: quarterly business transaction analytics report
- **Inquiry**: whether business analytics dashboard exists

---

### 2.3 Restaurant / Food Service

> *"Absolutely love this place — the food is consistently excellent and the service is warm and personal. I would love a weekly specials WhatsApp broadcast so I know when to come. Do you have a newsletter or any way to stay updated?"*

- **Applause**: food consistency, warm service
- **Suggestion**: weekly specials via WhatsApp
- **Inquiry**: existing newsletter or update channel

> *"The Sunday brunch here is a real highlight of our week. The staff remember our preferences and it feels like family. Could you consider adding a live music component on Sunday afternoons? Also, is the kitchen nut-free? We have a guest with allergies."*

- **Applause**: brunch experience, personalised service
- **Suggestion**: live music on Sunday afternoons
- **Inquiry**: allergen policy (nut-free kitchen)

---

### 2.4 Government / Public Services

> *"The new e-service portal for business registration is a genuine breakthrough — I registered my company in one day from my phone. I think you should add a live chat feature for when you get stuck. Is there a helpdesk number for the portal?"*

- **Applause**: e-registration portal
- **Suggestion**: live chat support within the portal
- **Inquiry**: helpdesk number for technical support

> *"The community policing initiative in our neighbourhood has made a real difference — we feel safer and the officers are accessible. The programme should be extended to all wards. Is there a way for our ward to officially endorse the programme and recommend its expansion?"*

- **Applause**: community policing programme effectiveness
- **Suggestion**: expand to all wards
- **Inquiry**: formal endorsement/expansion process

---

### 2.5 Education / Training

> *"This was the most practical professional training I have ever attended — every module was applicable immediately on the job. I would love a follow-up session six months later to review implementation. Do you have any alumni community or ongoing learning platform?"*

- **Applause**: practical, immediately applicable training
- **Suggestion**: six-month follow-up implementation review session
- **Inquiry**: alumni community or ongoing learning resource

> *"The robotics club at this school has transformed my son's interest in learning — he talks about it every evening. The school should invest in expanding the programme to lower primary grades. Do you accept donations of equipment from parents?"*

- **Applause**: robotics club impact on student engagement
- **Suggestion**: expand to lower primary grades
- **Inquiry**: whether equipment donations are accepted

---

### 2.6 Hotel / Hospitality

> *"This hotel is our family's favourite — we have stayed five times and every visit is perfect. I would suggest adding an airport shuttle service as a package add-on. Do you currently arrange transport from the airport?"*

- **Applause**: consistent excellence over multiple visits
- **Suggestion**: airport shuttle package
- **Inquiry**: current airport transfer arrangements

---

### 2.7 Agriculture / Input Supplier

> *"Your hybrid maize seeds gave me the best harvest I have had in 10 years — I am recommending them to everyone in my village. You should create a farmer-to-farmer referral reward so we get something for recommending you. Do you have any farmer loyalty programme?"*

- **Applause**: product performance, harvest results
- **Suggestion**: referral/ambassador reward programme
- **Inquiry**: whether a farmer loyalty programme exists

---

### 2.8 NGO / Social Welfare

> *"The women's cooperative programme your organisation runs has genuinely changed lives in our community. Women who had nothing now have income and confidence. The programme should be replicated in the coastal regions. Does your organisation accept proposals from community leaders for programme expansion?"*

- **Applause**: cooperative programme impact
- **Suggestion**: replicate in coastal regions
- **Inquiry**: process for communities to propose expansion

---

## 3. How Riviwa AI Must Handle This Combination

### Tone — positive, warm, engaged
No urgency. No SLA. This is a good conversation. Mirror the person's enthusiasm.

### Step 1 — Receive praise with genuine warmth
> *"Asante sana kwa maneno hayo mazuri — tunafurahi kusikia hivyo na tutashirikisha timu yetu."*

### Step 2 — Record suggestion with a clarifying question
> *"Pendekezo lako la vikumbusho vya dawa kwa SMS ni wazo zuri. Ungependa vikumbusho hivyo vitumwe siku ngapi kabla ya kukwisha dawa?"*

### Step 3 — Answer the inquiry if possible
> *"Kuhusu NHIF — ndiyo, tunakubali NHIF. Kadi yako ya NHIF inahitajika wakati wa kuja."*

If answer is unknown: *"Swali lako kuhusu NHIF limesajiliwa — timu itakujibu mapema."*

### `multiple_issues: true`
```json
{
  "multiple_issues": true,
  "feedback_items": [
    {
      "feedback_type": "applause",
      "subject": "Pharmacy — personalised service, fair pricing, always in stock",
      "description": "Long-time customer praises staff who know them by name and consistent stock"
    },
    {
      "feedback_type": "suggestion",
      "subject": "SMS prescription reminder service",
      "description": "Customer suggests automated SMS reminders when prescriptions are due for renewal"
    },
    {
      "feedback_type": "inquiry",
      "subject": "Does the pharmacy accept NHIF?",
      "description": "Customer asks about NHIF insurance acceptance"
    }
  ]
}
```

---

## 4. Swahili Signal Phrases

**A+S+I patterns (Swahili):**
- *"Napenda sana [X]. Mngeweza pia [Y]? Je, mna [Z]?"*
  *I really love [X]. Could you also [Y]? Do you have [Z]?*
- *"[X] imefanya kazi vizuri sana. Pendekezo langu ni [Y]. Na ningependa kujua [swali]."*
  *[X] has worked very well. My suggestion is [Y]. And I'd like to know [question].*
- *"Ninaipendekeza [huduma hii] kwa kila mtu. Ingekuwa bora zaidi kama [Y]. Mnafungua [siku/saa]?"*
  *I recommend [this service] to everyone. It would be even better if [Y]. Do you open on [day/hour]?*

---

*Last updated: 2026-06-22 | File: obsidian_vault/KB_84_Mixed_Applause_Suggestion_Inquiry.md*
