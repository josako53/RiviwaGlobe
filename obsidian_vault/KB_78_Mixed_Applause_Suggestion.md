# Riviwa AI — Mixed Feedback: Applause + Suggestion

## 1. Purpose & Usage

This document trains Riviwa AI to handle feedback that combines **genuine praise** with a **constructive suggestion for improvement**. This is the feedback of a loyal, engaged person — they love the service or product enough to recommend it AND care enough to suggest how it could be even better.

This combination is valuable for product and service teams because:
- The praise confirms what is working (do not change it)
- The suggestion identifies an unmet need from someone who is already satisfied
- The person is not angry — they are invested

The AI must:
1. **Record both signals** — praise to staff recognition; suggestion to improvement queue
2. **Respond with warmth** that validates both the satisfaction and the idea
3. **Ask for more detail on the suggestion** to make it actionable
4. **Not treat the suggestion as a complaint** — there is no harm done here

---

## 2. The Core Pattern

The person's overall experience was positive. The suggestion is forward-looking: *"I love [X] — you should also add [Y]."* There is no grievance, no harm, no urgency. The tone is supportive and collaborative.

**Linguistic markers:**
- Positive emotion + improvement proposal: *"love this, but you could...", "excellent — maybe also add...", "great service! Have you considered...?"*
- Endorsement + gap identification: *"I always recommend you — the one thing missing is..."*
- High satisfaction + incremental idea: *"perfect in every way — the only improvement would be..."*

---

## 3. Real-World Examples Across Industries

### 3.1 Healthcare / Pharmacy
> *"I love this pharmacy. The staff are always friendly and the prices are fair. You should also add a home delivery service for elderly patients who cannot travel."*

- **Applause**: staff friendliness, fair pricing
- **Suggestion**: home delivery for elderly / mobility-limited patients

> *"The antenatal clinic here is excellent — organised, clean, and the midwives are caring and professional. It would be wonderful if you could add an evening session for working mothers."*

- **Applause**: organised service, excellent midwife conduct
- **Suggestion**: evening clinic hours to accommodate working women

---

### 3.2 Banking / Finance
> *"Your mobile banking app is the best I have used — fast, secure, and very easy to understand. I would love it if you could add a feature to split bills with friends, like how some apps abroad do it."*

- **Applause**: app quality, speed, security, UX
- **Suggestion**: bill-splitting feature

> *"The tellers at this branch are always professional and never make me feel rushed. One improvement: could you add a dedicated counter for senior citizens so they don't have to stand in the long queue?"*

- **Applause**: staff professionalism
- **Suggestion**: priority counter for elderly customers

---

### 3.3 Restaurant / Food Service
> *"Absolutely delicious food and the service was impeccable. I would love to see a vegetarian menu option — many of my friends avoid meat but love everything else you do."*

- **Applause**: food quality, service excellence
- **Suggestion**: vegetarian menu

> *"The atmosphere here is perfect for a date night. The only thing I'd suggest is adding a QR code menu so we don't have to wait for the waiter to bring the physical menu."*

- **Applause**: ambiance
- **Suggestion**: digital QR code menu

---

### 3.4 Government / Public Services
> *"The new e-government portal is a massive improvement. I renewed my driving licence in 20 minutes from home — incredible. The only thing I'd add is a WhatsApp notification when the physical card is ready for collection."*

- **Applause**: new digital service, speed and convenience
- **Suggestion**: WhatsApp status notification for physical documents

> *"The staff at this immigration office are the most professional and helpful I have ever encountered in a government office. I would suggest adding more parking spaces — the area outside is always full."*

- **Applause**: staff professionalism
- **Suggestion**: additional parking facilities

---

### 3.5 Education / University
> *"Professor Aisha is genuinely one of the best lecturers I have encountered. Engaging, knowledgeable, and patient. I think the university should record her lectures and make them available to students who miss class — they would be a great resource."*

- **Applause**: specific lecturer
- **Suggestion**: lecture recording and on-demand access

> *"The student mentorship programme is excellent and has helped me so much. I think it would be even better if you could match mentors and mentees based on their career goals rather than just their department."*

- **Applause**: mentorship programme
- **Suggestion**: improved matching algorithm/criteria

---

### 3.6 Hotel / Hospitality
> *"Stayed three nights and everything was perfect — the room, the food, the pool, the staff. I genuinely have no complaints. One idea: offer a bicycle hire service so guests can explore the town without needing a taxi."*

- **Applause**: comprehensive excellence across all touchpoints
- **Suggestion**: bicycle hire facility for guests

> *"The breakfast buffet is phenomenal — the best I've had in Tanzania. Could you consider adding a made-to-order omelette station? That would make it absolutely perfect."*

- **Applause**: buffet quality
- **Suggestion**: live cooking station addition

---

### 3.7 Telecommunications
> *"Your fibre internet service has been rock-solid for eight months — no downtime, excellent speed. I would love a family plan option that covers multiple devices at a better rate than buying individual packages."*

- **Applause**: network reliability, uptime
- **Suggestion**: family/multi-device pricing plan

---

### 3.8 Retail / Supermarket
> *"I love shopping here — good variety, clean, and the prices are competitive. My only suggestion is to introduce a loyalty points system so regular customers like me get some benefit for our consistent shopping."*

- **Applause**: variety, cleanliness, pricing
- **Suggestion**: loyalty rewards programme

> *"The self-checkout machines you installed are a great idea and save so much time. Could you also add them near the entrance for customers buying fewer than five items?"*

- **Applause**: self-checkout innovation
- **Suggestion**: express self-checkout near entrance for small purchases

---

### 3.9 NGO / Social Welfare
> *"The school feeding programme your organisation runs is changing lives in our community. The children are more focused and attendance has improved. I think extending it to Saturday school sessions would help even more families."*

- **Applause**: programme impact, community benefit
- **Suggestion**: extend to weekend sessions

---

### 3.10 Transport / Ride-hailing
> *"I use your service every day and it is reliable and affordable. The drivers are always polite and on time. My suggestion: add a 'quiet ride' option for passengers who prefer no conversation — some of us use the commute to prepare for meetings."*

- **Applause**: reliability, affordability, driver conduct
- **Suggestion**: quiet ride preference option

---

## 4. How Riviwa AI Must Handle This Combination

### Step 1 — Respond with warmth, not urgency
This is positive feedback with a constructive idea. No SLA. No escalation. The tone should match the energy — cheerful and appreciative.

**CORRECT:**
> *"Nashukuru sana kwa maneno hayo mazuri — hiyo inamaanisha mengi kwa timu yetu. Na pendekezo lako la delivery kwa wazee ni wazo zuri sana. Unaweza kunieleza zaidi — je, ungependa wasilishe dawa, au pia vitu kama vipimo na ushauri wa daktari?"*
> *(Thank you so much for those kind words — that means a lot to our team. And your suggestion about delivery for the elderly is a very good idea. Can you tell me more — would you want medication delivered, or also things like tests and medical consultations?)*

### Step 2 — Make the suggestion actionable
Ask one clarifying question to make the suggestion specific enough for the product/service team to act on.

### Step 3 — Log both
```json
{
  "multiple_issues": true,
  "feedback_items": [
    {
      "feedback_type": "applause",
      "subject": "Excellent pharmacy service — friendly staff and fair prices",
      "description": "Customer praises staff friendliness and competitive pricing"
    },
    {
      "feedback_type": "suggestion",
      "subject": "Home delivery for elderly patients",
      "description": "Customer suggests adding delivery service for elderly or mobility-limited patients"
    }
  ]
}
```

---

## 5. AI Conversation Flow

**Turn 1 (User):** *"Your mobile app is amazing — best banking app I have used. You should add a bill-splitting feature though."*
**Turn 1 (AI):** *"Nashukuru sana! Tunafurahi kusikia hivyo. Pendekezo lako la bill-splitting ni zuri — unafikiria liwe kwa vikundi vya marafiki, familia, au wote?"*

**Turn 2 (User):** *"Mainly friends — like when we go to a restaurant together."*
**Turn 2 (AI):** *"Vizuri sana. Nimesajili sifa yako ya app na pendekezo la bill-splitting kwa vikundi vya marafiki katika migahawa na matukio. Timu ya bidhaa itaona hilo. Je, niwasilishe?"*

---

## 6. Swahili Signal Phrases

**Applause + Suggestion (Swahili):**
- *"[X] ni bora sana. Mngekuwa na [Y] pia, ingekuwa kamili"* — [X] is very good. If you also had [Y] it would be perfect
- *"Napenda sana [X]. Wazo langu: ongezeni [Y]"* — I really love [X]. My idea: add [Y]
- *"[X] imefanya kazi nzuri sana. Pendekezo langu ni [Y]"* — [X] has worked very well. My suggestion is [Y]
- *"Ninaipendekeza huduma hii kwa kila mtu. Kitu kimoja tu ningeomba: [Y]"* — I recommend this service to everyone. The one thing I'd ask for: [Y]

---

*Last updated: 2026-06-22 | File: obsidian_vault/KB_78_Mixed_Applause_Suggestion.md*
