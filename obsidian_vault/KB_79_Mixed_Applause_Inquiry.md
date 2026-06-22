# Riviwa AI — Mixed Feedback: Applause + Inquiry

## 1. Purpose & Usage

This document trains Riviwa AI to handle feedback combining **genuine praise** with a **question or request for information**. The person is satisfied — they are not complaining — but they have a question that the positive experience has prompted. Common triggers:
- A good experience makes them want to come back: *"How do I book again?"*
- They want to tell others: *"Do you have other branches?"*
- They want more of the same: *"Do you offer this for businesses too?"*
- They are curious about extending the relationship: *"Do you have a loyalty programme?"*

The AI must:
1. **Log the praise** — route to staff recognition
2. **Attempt to answer the inquiry** from org context if possible
3. **Flag the inquiry** for staff response if the answer is unknown
4. **Maintain a warm, positive tone** throughout — this person is happy

---

## 2. The Core Pattern

The question flows naturally from the positive experience. There is no dissatisfaction, no complaint, no urgency. The person is engaged and wants more information to extend or repeat a good experience.

**Linguistic markers:**
- Praise + question: *"Amazing service! Do you also...?", "I loved it — how do I...?", "Excellent — is there a way to...?"*
- Enthusiasm + inquiry: *"Great experience. By the way, do you...?"*
- Recommendation intent + logistics question: *"I always recommend you. What are your weekend hours?"*

---

## 3. Real-World Examples Across Industries

### 3.1 Healthcare / Clinic
> *"The doctor was very thorough and professional. I felt completely at ease. Do you also offer specialist consultations here or do I need to go elsewhere for that?"*

- **Applause**: doctor thoroughness and patient comfort
- **Inquiry**: whether specialist services are available at the same facility

> *"I have been coming to this clinic for five years and the standard has always been excellent. Do you offer a health package for the whole family at a discounted rate?"*

- **Applause**: long-term satisfaction, consistent quality
- **Inquiry**: family health package pricing

---

### 3.2 Banking / Finance
> *"Your loan application process was incredibly smooth — approved in two days, everything online. By the way, do you offer business loans as well, or only personal?"*

- **Applause**: fast, digital loan process
- **Inquiry**: business loan products

> *"The interest rate I was given on my savings account is really competitive — better than anywhere else I checked. Is there an option to lock in this rate for a longer period?"*

- **Applause**: competitive savings rate
- **Inquiry**: fixed-rate or long-term savings products

---

### 3.3 Restaurant / Food Service
> *"The biryani here is absolutely the best in the city. We drive 40 minutes just to come here. Do you do catering for events and weddings?"*

- **Applause**: food quality, loyalty
- **Inquiry**: catering and event services

> *"Wonderful dinner last night — everything was perfect. What time do you open on Sundays? We'd love to bring family next weekend."*

- **Applause**: dinner experience
- **Inquiry**: Sunday opening hours

---

### 3.4 Government / Public Services
> *"I was impressed by how quickly my business registration was processed — four days! Do you have a similar fast-track option for trademark registration?"*

- **Applause**: efficient business registration
- **Inquiry**: fast-track trademark registration process

> *"The officers here are very helpful and honest — a refreshing change. Are there other services I can access through this same office, like tax clearance or import permits?"*

- **Applause**: officer conduct and integrity
- **Inquiry**: other services available at the same office

---

### 3.5 Education / Training
> *"This was the best professional development course I have attended in years. The facilitator was exceptional and the content was immediately applicable. Do you run an advanced version of this course?"*

- **Applause**: course quality, facilitator excellence, practical content
- **Inquiry**: advanced or follow-up courses available

> *"My children's results improved dramatically after joining your tutoring programme. Thank you so much. At what age do you recommend starting to prepare for national examinations?"*

- **Applause**: tutoring programme impact on results
- **Inquiry**: recommended age/timing for exam preparation

---

### 3.6 Hotel / Hospitality
> *"Perfect weekend getaway — the staff were outstanding, the food was incredible, the pool was clean and peaceful. Do you have a loyalty programme for returning guests?"*

- **Applause**: comprehensive five-star experience
- **Inquiry**: loyalty / repeat guest rewards programme

> *"We had such a wonderful time at your resort. Is it possible to rent the conference room for a corporate retreat?"*

- **Applause**: resort experience
- **Inquiry**: corporate / event facility availability

---

### 3.7 Agriculture / Input Supplier
> *"The hybrid seeds I bought from you last season gave excellent yield — almost double what I was getting before. Do you also sell drip irrigation equipment?"*

- **Applause**: product performance, improved yield
- **Inquiry**: whether drip irrigation is part of the product range

---

### 3.8 Telecommunications
> *"Your home fibre package has been absolutely perfect — consistent speed, no interruptions in six months. Do you offer a small business package with a static IP address?"*

- **Applause**: home fibre reliability and consistency
- **Inquiry**: business-tier internet with static IP

---

### 3.9 Retail / Supermarket
> *"I love this store — well-stocked, clean, and the staff always help me find things. Do you deliver to residential addresses? I sometimes can't make it out in the week."*

- **Applause**: stock availability, cleanliness, staff helpfulness
- **Inquiry**: home delivery option

---

### 3.10 Legal / Professional Services
> *"You handled my property purchase so professionally — everything was transparent and on time. I have a business contract dispute coming up. Is that something your firm handles?"*

- **Applause**: professional, transparent service
- **Inquiry**: whether the firm handles commercial disputes

---

## 4. How Riviwa AI Must Handle This Combination

### Step 1 — Receive the praise warmly
Do not rush past the compliment. The person is happy — mirror that energy.

### Step 2 — Answer the inquiry if possible from org context
If the AI has access to the org's services, branches, hours, or products in the context, answer directly. If not, say: *"Nimesajili swali lako — mtu wa timu atawasiliana nawe na maelezo."*

### Step 3 — Log both
```json
{
  "multiple_issues": true,
  "feedback_items": [
    {
      "feedback_type": "applause",
      "subject": "Excellent biryani — best in the city",
      "description": "Customer praises food quality and drives 40 minutes specifically to visit"
    },
    {
      "feedback_type": "inquiry",
      "subject": "Catering for events and weddings",
      "description": "Customer asking if the restaurant provides catering services for events"
    }
  ]
}
```

### Step 4 — No urgency, warm close
> *"Nimesajili sifa yako na swali lako kuhusu catering. Timu itawasiliana nawe mapema iwezekanavyo na taarifa za bei na upatikanaji. Asante kwa kutuamini!"*

---

## 5. Swahili Signal Phrases

**Applause + Inquiry (Swahili):**
- *"[X ilikuwa] bora sana. Je, mnafanya [Y] pia?"* — [X] was excellent. Do you also do [Y]?
- *"Nimefurahi sana na huduma yenu. Nataka kujua [Y]"* — I was very pleased with your service. I want to know [Y]
- *"Hongera kwa [X]! Mnafungua saa ngapi [siku]?"* — Well done for [X]! What time do you open on [day]?
- *"Ninapendekeza mahali hapa kwa kila mtu. Je, mna tawi [mahali]?"* — I recommend this place to everyone. Do you have a branch [location]?
- *"[X] ilifanya kazi vizuri sana. Mnaweza [Y] pia?"* — [X] worked very well. Can you also [Y]?

---

*Last updated: 2026-06-22 | File: obsidian_vault/KB_79_Mixed_Applause_Inquiry.md*
