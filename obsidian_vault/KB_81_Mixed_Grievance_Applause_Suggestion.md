# Riviwa AI — Mixed Feedback: Grievance + Applause + Suggestion

## 1. Purpose & Usage

This document trains Riviwa AI to handle feedback containing all three of: a **complaint**, a **compliment**, and a **suggestion**. This is the feedback of a highly engaged, thoughtful person. They experienced something bad AND something good in the same interaction, and they have already thought about how to fix the bad part.

This is the pattern of a loyal, articulate consumer who is investing time because they care. The AI must treat every element with respect — none cancels the others.

The AI must:
1. **Record the grievance** — with full details, SLA triggered
2. **Record the applause** — for staff recognition
3. **Record the suggestion** — for the improvement team
4. **Respond with balance** — acknowledge all three; do not let the praise minimise the complaint or the suggestion get lost
5. **Prioritise grievance detail collection** — it is the only time-sensitive element

---

## 2. Real-World Examples Across Industries

### 2.1 Healthcare / Hospital

> *"The manager and security team were absolutely wonderful — professional, calm, and helpful. But the facility itself is in terrible condition. The toilets are filthy, the floors are cracked, and there is paint peeling off the walls. They should allocate a proper maintenance budget and renovate the facility."*

- **Applause**: manager and security team
- **Grievance**: facility condition — hygiene, structural maintenance
- **Suggestion**: maintenance budget allocation and renovation

> *"Nurse Sara is an angel — so caring, so patient with my elderly father. But waiting 4 hours for a doctor to come is completely unacceptable. You should implement a triage system so that serious patients are seen within 30 minutes."*

- **Applause**: named nurse, exceptional care
- **Grievance**: excessive doctor waiting time
- **Suggestion**: formal triage system

> *"Dr. Mwangi diagnosed my condition correctly when two other hospitals had missed it — I am truly grateful. However, when I came for the follow-up the file was lost and I had to explain everything again from scratch. You should digitise patient records so they are never lost."*

- **Applause**: accurate diagnosis, exceptional doctoring
- **Grievance**: lost patient file, failure of records management
- **Suggestion**: digital patient records system

---

### 2.2 Restaurant / Food Service

> *"The chef obviously has real talent — the flavours were incredible. But the restaurant was disgracefully dirty. Tables were sticky, the floor had visible food residue, and the bathroom was unusable. Hire a dedicated cleaning crew or set a proper cleaning schedule."*

- **Applause**: chef talent, food quality
- **Grievance**: hygiene failure across dining area and bathroom
- **Suggestion**: dedicated cleaning staff or schedule

> *"Our waiter, James, was phenomenal — attentive, knowledgeable about the menu, and genuinely warm. But the food took one hour and twenty minutes to arrive. A restaurant of this size should have a kitchen tracker system to prevent such delays."*

- **Applause**: named waiter, excellent front-of-house service
- **Grievance**: extremely long food wait time
- **Suggestion**: kitchen order tracking system

---

### 2.3 Banking / Finance

> *"The new branch manager has transformed this branch — it's clean, organised, and the staff are now professional and respectful. But the queue system is still terrible. Ten tellers but only three working at any time. You should implement a digital queue system that calls customers by number."*

- **Applause**: new branch manager, improved branch culture
- **Grievance**: inefficient queue management despite adequate staffing
- **Suggestion**: digital number-based queue system

---

### 2.4 Government / Public Services

> *"The new county director has made huge changes — offices are cleaner, staff are respectful, and processes are faster. However, the online payment system crashes every time I try to pay fees. Please invest in proper IT infrastructure."*

- **Applause**: new leadership, cultural and process improvement
- **Grievance**: unreliable online payment system
- **Suggestion**: IT infrastructure investment

> *"Officer Hamisi at the permit desk is outstanding — efficient, knowledgeable, never asks for anything unofficial. But the application form itself is 12 pages long for a simple renewal. Simplify it — three pages maximum."*

- **Applause**: specific officer
- **Grievance**: bureaucratic form design causing friction
- **Suggestion**: simplified application form

---

### 2.5 Education / University

> *"The lecturers in this department are world-class. I could not ask for better teaching. But the library is almost useless — half the books are from the 1990s and the online database subscription has expired. The university needs to update the library resources urgently."*

- **Applause**: lecturers / teaching quality
- **Grievance**: outdated library resources
- **Suggestion**: library resource update and database subscription renewal

---

### 2.6 Hotel / Hospitality

> *"The front desk team and the restaurant staff were wonderful — so welcoming and genuinely eager to help. But the room we were given had a broken air conditioner, a leaking tap, and no hot water. A hotel of this standard should have a pre-check system before assigning rooms to guests."*

- **Applause**: front desk and restaurant staff
- **Grievance**: room maintenance failures — AC, plumbing, hot water
- **Suggestion**: pre-arrival room inspection protocol

---

### 2.7 Transport / Bus Company

> *"The driver was very professional — courteous, drove safely, and departed on time. But the bus itself was in shocking condition. Torn seats, broken windows, no working AC. The company should retire old buses and replace them. At minimum, conduct monthly maintenance inspections."*

- **Applause**: driver conduct and professionalism
- **Grievance**: poor vehicle condition
- **Suggestion**: fleet renewal or mandatory maintenance inspections

---

### 2.8 Telecommunications

> *"Your technical support team is excellent — they walked me through every step and resolved the issue within an hour. But the fact that I had to call three times because the problem kept returning shows the first resolution was not permanent. You should implement a follow-up call 48 hours after every technical resolution to confirm it is holding."*

- **Applause**: technical support team quality
- **Grievance**: recurring technical issue — incomplete resolution
- **Suggestion**: 48-hour post-resolution follow-up protocol

---

## 3. How Riviwa AI Must Handle This Combination

### Priority order for data collection
1. **Grievance** — collect details (what happened, who, where, when, severity)
2. **Applause** — note who is being praised and why
3. **Suggestion** — note the proposed improvement

### Response approach — acknowledge all three explicitly
**CORRECT:**
> *"Nashukuru kwa sifa ulizompa daktari na pendekezo lako la mfumo wa kuhifadhi rekodi. Na malalamiko kuhusu faili iliyopotea — hiyo ni tatizo zito. Niambie: hii ilitokea lini na ni faili ya nani hasa?"*

**WRONG:**
> *"Nashukuru kwa maoni yako mazuri!"* (only acknowledging the praise, ignoring everything else)

### `multiple_issues: true` with three items
```json
{
  "multiple_issues": true,
  "feedback_items": [
    {
      "feedback_type": "applause",
      "subject": "Dr. Mwangi — accurate diagnosis after two other hospitals failed",
      "description": "Patient expresses deep gratitude for correct diagnosis"
    },
    {
      "feedback_type": "grievance",
      "subject": "Patient file lost at follow-up visit",
      "description": "Patient had to re-explain full medical history because file was missing"
    },
    {
      "feedback_type": "suggestion",
      "subject": "Digitise patient records",
      "description": "Patient suggests electronic records to prevent loss and duplication"
    }
  ]
}
```

---

## 4. Swahili Signal Phrases

**G+A+S patterns (Swahili):**
- *"[Person/X] alifanya kazi nzuri, lakini [tatizo]. Wafaa [suluhisho]."*
  *[Person/X] did good work, but [problem]. They should [solution].*
- *"Ninashukuru [X], hata hivyo [tatizo] ni tatizo kubwa. Ninapendekeza [Y]."*
  *I appreciate [X], however [problem] is a serious issue. I suggest [Y].*
- *"Timu [X] wanastahili sifa. Lakini jengo/mfumo/huduma [Y] ni mbaya. Waboreshe [Z]."*
  *The [X] team deserves praise. But the [Y] is bad. They should improve [Z].*

---

*Last updated: 2026-06-22 | File: obsidian_vault/KB_81_Mixed_Grievance_Applause_Suggestion.md*
