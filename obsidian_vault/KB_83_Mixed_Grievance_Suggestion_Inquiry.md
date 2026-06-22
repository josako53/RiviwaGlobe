# Riviwa AI — Mixed Feedback: Grievance + Suggestion + Inquiry

## 1. Purpose & Usage

This document trains Riviwa AI to handle feedback combining a **complaint**, a **suggestion for how to fix it**, and a **question**. The person has experienced something bad, already has an idea for how it should be fixed, and is also asking about accountability, timelines, or whether their idea is feasible.

This combination often comes from people who have thought deeply about their experience — community leaders, professionals, long-time users, or advocates. Their feedback is highly actionable.

The AI must:
1. **Record the grievance** — with full details, SLA
2. **Record the suggestion** — for improvement team
3. **Answer the inquiry** if possible, or flag for staff
4. **Validate all three signals** — none cancels the others

---

## 2. Real-World Examples Across Industries

### 2.1 Healthcare / Hospital

> *"The road inside the hospital campus is completely broken — vehicles damage their tyres just getting to the car park. They should resurface it immediately. Who is responsible for infrastructure maintenance in this hospital — is it the hospital management or the Ministry?"*

- **Grievance**: dangerous road condition inside hospital campus
- **Suggestion**: immediate resurfacing
- **Inquiry**: who is responsible for infrastructure — hospital or Ministry?

> *"There is no signage in this hospital — I spent 20 minutes walking around trying to find the paediatric ward. You should install clear direction signs at every junction. Is there a patient experience officer I can share this with directly?"*

- **Grievance**: absence of wayfinding signage causing patient distress
- **Suggestion**: clear directional signs at junctions
- **Inquiry**: patient experience officer contact

---

### 2.2 Government / Public Services

> *"The road between Kibaha and Chalinze has had a massive pothole for two months causing accidents. The government should repair it and install warning signs immediately. Who do I report this to so it actually gets fixed — is there a road authority hotline?"*

- **Grievance**: dangerous road hazard causing accidents
- **Suggestion**: repair + install warning signage
- **Inquiry**: correct authority to report to (TANROADS/municipal)

> *"The queue management at the National ID office is completely broken. People who arrive at 5am are overtaken by those who arrive at 10am with 'connections.' You should implement a strict number ticket system. Has any audit been done on this office?"*

- **Grievance**: queue manipulation and corruption
- **Suggestion**: strict numbered ticket system
- **Inquiry**: whether the office has been audited

---

### 2.3 Banking / Finance

> *"Your mobile app logs me out every time I switch to another app — it is extremely inconvenient and I lose my transaction mid-way. You should extend the session timeout or allow biometric re-authentication. Is this a known bug that your team is working on?"*

- **Grievance**: excessive session timeouts interrupting transactions
- **Suggestion**: extended timeout or biometric re-auth
- **Inquiry**: whether it is a known issue being addressed

> *"My salary was delayed by two days because your system flagged it as suspicious and froze the transfer. This caused me to miss a bill payment deadline. You need a faster manual override process for legitimate payroll transactions. What compensation do you offer for losses caused by your system errors?"*

- **Grievance**: legitimate payroll frozen, causing financial harm
- **Suggestion**: fast manual override for payroll transactions
- **Inquiry**: compensation for losses caused by system errors

---

### 2.4 Education / University

> *"The online exam portal crashed during the final exam and many students lost their work. The university should invest in a more reliable platform and always provide a manual paper backup option. Have any of the affected students been given an opportunity to resit?"*

- **Grievance**: exam portal failure causing lost work during finals
- **Suggestion**: reliable platform + paper backup protocol
- **Inquiry**: whether affected students have been offered a resit

---

### 2.5 Agriculture / Input Supplier

> *"The extension officers in our ward only visit once a year, which is completely inadequate during planting season. The ministry should hire more officers or allow them to do remote advisory via WhatsApp. Is there a WhatsApp number for the ward agricultural office?"*

- **Grievance**: insufficient extension officer visits
- **Suggestion**: increase officer frequency or WhatsApp advisory
- **Inquiry**: whether a WhatsApp channel exists for the ward agricultural office

---

### 2.6 Transport / Road Authority

> *"The street lights on Uhuru Street have been out for six weeks making the road dangerous at night — three muggings have occurred near my home. The council should restore the lights immediately and increase police patrols. Is there an emergency reporting number for street lighting faults?"*

- **Grievance**: extended street light outage causing safety risk
- **Suggestion**: immediate restoration + increased police patrols
- **Inquiry**: emergency reporting channel for street light faults

---

### 2.7 Telecommunications

> *"My business premises have had no internet for five days and your technician appointment has been rescheduled three times. I'm losing money every day. You should have a guaranteed commercial SLA with penalties for breach. Does your business contract include any penalty clause I can invoke?"*

- **Grievance**: repeated technician no-shows, 5-day outage causing business loss
- **Suggestion**: guaranteed commercial SLA with breach penalties
- **Inquiry**: whether their current contract includes penalty clauses

---

### 2.8 NGO / Social Welfare

> *"Beneficiaries in our village have not received their monthly stipend for three months with no explanation. The organisation should send SMS updates when payments are delayed and give a reason. Who is the regional coordinator responsible for our area?"*

- **Grievance**: three months of unpaid stipends, no communication
- **Suggestion**: SMS payment status notifications with explanations
- **Inquiry**: regional coordinator contact

---

## 3. How Riviwa AI Must Handle This Combination

### Step 1 — Confirm the grievance details first
The complaint is time-sensitive. Get: what happened, where, when, impact.

### Step 2 — Note the suggestion concisely
*"Nimesajili pia pendekezo lako la [X] — litapelekwa kwa timu ya mipango."*

### Step 3 — Answer the inquiry or flag it
If the org structure includes the answer (e.g., a patient experience officer, a hotline), provide it. If not:
*"Swali lako kuhusu [Y] limesajiliwa — mtu wa timu atawasiliana nawe na maelezo."*

### `multiple_issues: true`
```json
{
  "multiple_issues": true,
  "feedback_items": [
    {
      "feedback_type": "grievance",
      "subject": "Street lights out on Uhuru Street for 6 weeks — safety risk",
      "description": "Six-week street light outage causing muggings near caller's home"
    },
    {
      "feedback_type": "suggestion",
      "subject": "Restore lights immediately and increase police patrols",
      "description": "Caller suggests emergency light restoration and more police presence as solution"
    },
    {
      "feedback_type": "inquiry",
      "subject": "Emergency reporting number for street light faults",
      "description": "Caller asking for the correct channel to report infrastructure faults urgently"
    }
  ]
}
```

---

## 4. Swahili Signal Phrases

**G+S+I patterns (Swahili):**
- *"[Tatizo]. Wafaa [suluhisho]. Na ninataka kujua [swali]."*
  *[Problem]. They should [solution]. And I want to know [question].*
- *"[X] haifanyi kazi vizuri. Badilisheni [Y]. Je, [swali]?"*
  *[X] doesn't work well. Change it to [Y]. Is [question]?*
- *"Tatizo kubwa ni [X]. Suluhisho rahisi ni [Y]. Nani anaweza kusaidia na hilo?"*
  *The big problem is [X]. The easy solution is [Y]. Who can help with that?*
- *"[X] imesababisha [madhara]. Mnafaa [Y] kuzuia hili. Je, kuna [mchakato/mtu/nambari] wa kuwasiliana?"*
  *[X] has caused [harm]. You should [Y] to prevent this. Is there a [process/person/number] to contact?*

---

*Last updated: 2026-06-22 | File: obsidian_vault/KB_83_Mixed_Grievance_Suggestion_Inquiry.md*
