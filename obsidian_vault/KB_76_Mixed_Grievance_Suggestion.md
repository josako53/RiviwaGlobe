# Riviwa AI — Mixed Feedback: Grievance + Suggestion

## 1. Purpose & Usage

This document trains Riviwa AI to handle feedback that contains both a **complaint about something that went wrong** AND a **suggestion for how to fix or improve it**. This is extremely common — people who care enough to complain often also care enough to offer a solution. The AI must:

1. **Record both signals** — the complaint describes harm done; the suggestion describes a desired improvement
2. **Not treat the suggestion as a resolution** — the suggestion does not cancel the grievance; both must be logged
3. **Collect the necessary grievance details** first (what happened, who, when, where), then note the suggestion
4. **Route correctly** — the grievance goes to resolution tracking; the suggestion goes to the improvement/product team

---

## 2. The Core Pattern

The person experienced something bad and is already thinking about how the organisation should fix it. They are solution-oriented. The suggestion embedded in a grievance is often the most actionable feedback an organisation can receive.

**Linguistic markers:**
- Problem + solution structure: *"[X happened] — you should [do Y]"*
- Conditional improvement: *"if you [did Y], this [X problem] wouldn't happen"*
- Direct imperative after complaint: *"fix this", "improve this", "you need to", "you must", "you should"*
- Comparison to better practice: *"other hospitals do it this way", "at [other place] they have [solution]"*

---

## 3. Real-World Examples Across Industries

### 3.1 Healthcare
> *"The waiting room is so crowded and there are never enough chairs. You should install a proper queue management system so people know when it is their turn."*

- **Grievance**: overcrowded waiting area, inadequate seating
- **Suggestion**: implement a queue management system

> *"I received my lab results three weeks after the test — that is far too long. The hospital should send results via SMS or WhatsApp as soon as they are ready."*

- **Grievance**: delayed test results
- **Suggestion**: digital results notification via mobile

> *"There is no clean water in the ward. Patients are thirsty and relatives are buying water from outside. You must install a water dispenser in every ward."*

- **Grievance**: lack of drinking water, basic needs unmet
- **Suggestion**: install water dispensers

---

### 3.2 Government / Public Services
> *"The road between Kigamboni and the ferry is completely broken — it has potholes that damage vehicles. The government should repair it and add speed bumps to prevent accidents."*

- **Grievance**: dangerous road condition causing vehicle damage
- **Suggestion**: road repair + traffic calming measures

> *"Getting a birth certificate here takes four weeks. In Kenya it takes two days online. You should digitize this process and allow applications through a mobile app."*

- **Grievance**: excessive processing time
- **Suggestion**: digital service delivery, mobile app

> *"There is no signage in this office — visitors spend 20 minutes just trying to find the right department. You need clear signs in both Swahili and English at the entrance."*

- **Grievance**: navigation difficulty, poor wayfinding
- **Suggestion**: bilingual signage

---

### 3.3 Banking / Finance
> *"Your ATMs are always out of cash on weekends when people need money most. You should schedule cash refills on Friday evenings and Saturday mornings."*

- **Grievance**: ATM cash availability failure on peak days
- **Suggestion**: scheduled cash refill timing

> *"I had to visit the branch three times to open an account because they kept asking for different documents each time. You should create a complete document checklist and share it upfront."*

- **Grievance**: inefficient process, inconsistent communication
- **Suggestion**: standardised document checklist

---

### 3.4 Education / School / University
> *"The wifi on campus is so slow that we cannot download lecture materials or attend online classes. The institution should upgrade the bandwidth and extend the wifi to the library and hostels."*

- **Grievance**: inadequate internet connectivity
- **Suggestion**: infrastructure upgrade and coverage extension

> *"Lecturers cancel classes without any notice. Students come from far and find an empty room. The university should use the student portal to send cancellation alerts at least an hour in advance."*

- **Grievance**: unannounced class cancellations wasting students' time and money
- **Suggestion**: automated cancellation alerts via student portal

---

### 3.5 Transport / Road / Public Transit
> *"Buses from Dar es Salaam to Dodoma leave without filling the seats then passengers have to wait hours for the next one. They should coordinate departure times and fill each bus before leaving."*

- **Grievance**: wasted waiting time, poor scheduling
- **Suggestion**: coordinated departure system

> *"The bus station has no shelter and when it rains passengers are completely exposed. You should build covered waiting areas."*

- **Grievance**: inadequate facilities, passenger discomfort
- **Suggestion**: covered waiting infrastructure

---

### 3.6 Telecommunications
> *"My internet connection drops every evening between 7pm and 9pm when everyone is home. That is unacceptable for a service I pay for monthly. You need to increase server capacity or add more towers in dense residential areas."*

- **Grievance**: systematic evening outage
- **Suggestion**: capacity upgrade, additional infrastructure

---

### 3.7 Retail / Supermarket
> *"The expiry dates on your dairy products are often past or very near to passing when I buy them. You should check expiry dates when stocking shelves and remove products with less than three days remaining."*

- **Grievance**: near-expired or expired products on shelves
- **Suggestion**: expiry date management protocol

---

### 3.8 Agriculture / Input Supplier
> *"The agro-dealer in our village only stocks two types of fertiliser and they run out before the season starts. The company should open more stockists or allow farmers to pre-order online."*

- **Grievance**: inadequate stock availability at point of need
- **Suggestion**: expand distribution network or pre-order system

---

### 3.9 Hotel / Hospitality
> *"The checkout process took 45 minutes — completely unnecessary for a digital age. The hotel should allow guests to check out via the TV in the room or through an app."*

- **Grievance**: excessive checkout wait time
- **Suggestion**: digital self-checkout

---

### 3.10 Social Welfare / NGO
> *"The beneficiary registration process requires people to travel to the district office three times. Many elderly and disabled people cannot do this. You should allow community health workers to register people at their homes."*

- **Grievance**: inaccessible registration process for vulnerable people
- **Suggestion**: mobile/home-based registration through community agents

---

## 4. How Riviwa AI Must Handle This Combination

### Step 1 — Record the grievance in full first
The complaint is time-sensitive and requires resolution tracking. The suggestion is useful but does not need SLA assignment.

**CORRECT approach:**
> *"Naelewa tatizo la maji katika wodi — hiyo ni mbaya sana. Kabla sijaandika pendekezo lako pia, nisaidie: hii ilitokea wodi gani na lini?"*
> *(I understand the water problem in the ward — that is serious. Before I also record your suggestion, help me: which ward was this, and when?)*

### Step 2 — Capture the suggestion as a separate item
After collecting grievance details, explicitly note the suggestion:
> *"Nimesajili malalamiko. Pia nimeandika pendekezo lako la kuweka dispenser ya maji kila wodi. Hilo litapelekwa kwa timu ya uboreshaji wa huduma."*

### Step 3 — Set `multiple_issues: true`
```json
{
  "multiple_issues": true,
  "feedback_items": [
    {
      "feedback_type": "grievance",
      "subject": "No drinking water in ward",
      "description": "Patients in the ward have no access to clean drinking water"
    },
    {
      "feedback_type": "suggestion",
      "subject": "Install water dispensers in every ward",
      "description": "Caller suggests installing water dispensers to solve the problem permanently"
    }
  ]
}
```

---

## 5. AI Conversation Flow

**Turn 1 (User):** *"The road to Kigamboni is completely broken and the government should fix it and add speed bumps."*
**Turn 1 (AI):** *"Naelewa. Sehemu gani hasa ya barabara hiyo ina tatizo kubwa zaidi?"*

**Turn 2 (User):** *"Kutoka kwenye kivuko hadi karibu kilomita mbili. Kuna mashimo makubwa."*
**Turn 2 (AI):** *"Asante. Hii imekuwa tatizo kwa muda gani, na je, imesababisha uharibifu wowote — kwa mfano kwa gari?"*

**Turn 3 (User):** *"Zaidi ya miezi sita. Gari yangu iliharibu tayari mara mbili."*
**Turn 3 (AI):** *"Nimesajili malalamiko kuhusu hali ya barabara na pia pendekezo lako la ukarabati na kuongeza kizuizi cha kasi. Niwasilishe?"*

---

## 6. Swahili Signal Phrases

**Grievance + Suggestion patterns (Swahili):**
- *"[X] ni mbaya sana. Mnafaa [Y]"* — [X] is very bad. You should [Y]
- *"[X] haifanyi kazi. Weka [Y] badala yake"* — [X] doesn't work. Put [Y] instead
- *"Tatizo ni [X]. Suluhisho rahisi ni [Y]"* — The problem is [X]. The easy solution is [Y]
- *"Kama mngeboresha [Y], tatizo hili lingeisha"* — If you improved [Y], this problem would end
- *"Wengine wanafanya [Y] na inafanya kazi vizuri"* — Others do [Y] and it works well

---

*Last updated: 2026-06-22 | File: obsidian_vault/KB_76_Mixed_Grievance_Suggestion.md*
