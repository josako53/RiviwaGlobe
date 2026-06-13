# Riviwa AI — Inquiry & Question Classification Knowledge Base

## 1. Purpose & Usage

This document trains Riviwa AI to **identify and classify** feedback that constitutes an **inquiry, question, or request for information** — as opposed to a complaint, suggestion, or compliment. When a user's feedback primarily contains these signals, the AI should:

1. **Detect** whether the feedback contains inquiry or question signals
2. **Classify** it as `feedback_type: inquiry`
3. **Route** it to the appropriate support or information team (not a grievance handler)
4. **Respond** with the requested information or direct the user to where they can find it

---

## 2. Inquiry vs. Other Feedback Types

| Signal Pattern | Type | Treatment |
|---|---|---|
| Seeks information, explanation, or clarification | Inquiry | Route to support / information team |
| Reports dissatisfaction, harm, failure | Complaint / Grievance | Assign SLA, escalate if critical |
| Proposes a change or improvement | Suggestion | Log for product/service team |
| Expresses satisfaction | Compliment | Log for staff recognition |

**Overlap rule:** Feedback often mixes types — e.g., *"I'm not happy with the delay [complaint] — when will it be resolved? [inquiry]"*. Classify by dominant intent. If the primary purpose is **seeking information or an answer**, classify as inquiry even if mild dissatisfaction is present.

**Key distinction:** Inquiry feedback expects **an answer or explanation** as the response. Complaint feedback expects **acknowledgement and remedial action**. Suggestion feedback expects **acknowledgement and consideration**.

**Common ambiguities:**
- *"Why don't you improve this?"* = question-form phrasing but dominant intent is a suggestion → classify as suggestion.
- *"Can you please fix this?"* = request without seeking information → classify as complaint/request.
- *"When will this be fixed?"* = seeking a timeline → classify as inquiry (with embedded complaint signal; note both).

---

## 3. Inquiry Signal Categories

---

### 3.1 Direct Question Starters

The speaker explicitly signals they are asking a question or seeking information.

I want to ask, I'd like to ask, I have a question, I have some questions, may I ask, can I ask, I need to ask, I'd like to know, I want to know, I need to know, I'm looking for information, I'm seeking information, I'm seeking clarification, I'm seeking guidance, I need clarification, I need more information, I need further details, I need someone to explain, I need an explanation, could you explain, could you clarify, could you tell me, could you let me know, can you explain, can you clarify, please explain, please clarify, please tell me, please help me understand

---

### 3.2 Uncertainty & Confusion

The speaker signals they do not understand something and need it explained.

I'm not sure, I'm uncertain, I'm unsure, I'm unclear, I'm confused, I'm quite confused, I'm completely confused, I don't understand, I can't understand, I'm having trouble understanding, I'm having difficulty understanding, this doesn't make sense, this isn't clear, this isn't clear to me, something doesn't add up, something is unclear, I'm not following, I can't follow, I'm lost, I feel lost, I'm baffled, I'm puzzled, I'm perplexed, I'm bewildered, I'm at a loss, I don't know what to make of this, I don't know what this means, I don't know how to interpret this

---

### 3.3 Asking for Clarification

The speaker wants a clearer or more detailed explanation of something already said or shown.

what do you mean, what do you mean by, what does that mean, what exactly do you mean, what precisely is meant, can you be more specific, could you be more specific, I need a clearer explanation, I need a more detailed answer, could you elaborate, could you elaborate further, could you expand on that, could you tell me more about, could you shed light on, could you clear this up, what did you mean when you said, when you say that do you mean, are you saying that, do I understand correctly that, am I right in thinking that, am I correct in assuming that, does that mean, is that to say

---

### 3.4 Seeking Information

The speaker expresses curiosity or a desire to learn something they do not yet know.

I would like to know, I am curious about, I am curious whether, I am wondering, I was wondering, I have been wondering, I wonder if, I wonder whether, I wonder what, I wonder why, I wonder how, what can you tell me about, what should I know about, what information do you have, what details can you share, I want to find out, I need to find out, I am trying to find out, I would appreciate any information, I would appreciate any clarity, I would appreciate being informed, I would appreciate an answer

---

### 3.5 WH-Question Forms

Standard question-word patterns across all domains. The presence of these words at the start of a sentence or following a modal verb is a strong inquiry signal.

**what** — what is, what are, what was, what were, what will, what does, what do, what did, what has, what happens, what happened, what exactly is, what exactly are

**when** — when is, when was, when will, when does, when did, when can, when should, when exactly, when is this happening, when will this be done, when can I expect

**where** — where is, where are, where was, where will, where can, where should, where do I, where exactly, where can I find, where should I go

**who** — who is, who are, who was, who will, who can, who should, who handles, who is responsible, who is in charge, who do I contact, who do I speak to

**why** — why is, why are, why was, why were, why did, why does, why would, why should, why can't, why hasn't, why won't

**how** — how is, how are, how was, how will, how does, how do, how can, how should, how would, how exactly, how long, how much, how many, how often, how soon, how quickly, how far

---

### 3.6 Expressing Doubt & Disbelief

The speaker questions whether information they have received is accurate, correct, or truthful — primarily seeking verification rather than expressing harm.

I doubt this is correct, I doubt this is accurate, I doubt this is what was agreed, I'm questioning whether, I question the accuracy of, I question the validity of, this doesn't seem right, this doesn't look right, this doesn't sound right, something seems off, something seems wrong, I find it hard to believe, I am skeptical, I am not convinced, I'm doubtful, I have doubts, I have reservations, I'm not fully sure, I'm not one hundred percent sure, I'm on the fence about this

---

### 3.7 Process & Procedure Questions

The speaker wants to understand how something works, what steps to take, or how to complete an action.

how does this work, how does this process work, how does this procedure work, what is the process, what is the procedure, what are the steps, what do I need to do, what steps do I need to take, what is the next step, what is the first step, what comes next, what do I do next, how do I proceed, how do I get started, how do I apply, how do I register, how do I sign up, how do I access, how do I submit, how do I file, how do I report, how do I claim, how do I appeal, how do I dispute, how do I escalate, how do I get a refund, how do I cancel, how do I track, how do I verify

---

### 3.8 Status & Update Questions

The speaker wants to know the current state of a request, case, order, or complaint.

what is the status, what is the current status, what is the latest update, what is happening, what is going on, what stage is this at, where does my case stand, where does my request stand, where does my complaint stand, has this been received, has this been processed, has this been reviewed, has this been resolved, has anything been done, has any progress been made, is there any update, is there any progress, is there any development, is there any response, is there any resolution, is anyone looking at this, is anyone handling this, is this being reviewed, is this being looked at, is this being acted on

---

### 3.9 Eligibility & Entitlement

The speaker wants to know whether they qualify for a service, benefit, or action.

am I eligible, am I eligible for, am I entitled to, am I qualified for, am I allowed to, am I permitted to, am I supposed to, do I qualify, do I qualify for, do I meet the requirements, do I meet the criteria, do I have the right to, can I apply for, can I receive, can I access, can I claim, will I be eligible, will I qualify, will I receive, who is eligible, who qualifies, who can apply, who can benefit, what are the requirements, what are the criteria, what are the conditions, what documents are needed, what proof is required, what do I need to qualify, is there a minimum requirement, is there an age requirement

---

### 3.10 Confirmation & Verification

The speaker wants to confirm or verify information they have received or assumed.

is this correct, is this right, is this accurate, is this confirmed, is this valid, is this still correct, is this still applicable, is this still in effect, can you confirm, can you confirm this, can you verify, can you check, can you double-check, please confirm, please verify, I need confirmation, I need to confirm, I want to confirm, I want to verify, I want to make sure, I want to be certain, I need to be sure, just to confirm, just to clarify, just to double-check, just checking, just making sure, I wanted to confirm, I was just making sure, I was just checking

---

### 3.11 Time & Availability

The speaker wants to know when something will happen, how long it will take, or whether something is currently accessible.

when will this be available, when will this be ready, when will this be completed, when will this be delivered, when will this be resolved, when will I receive, when will I hear back, when will I get a response, when will I be contacted, when can I expect, when should I expect, when is the deadline, when is the closing date, when does this expire, when does this start, when does this open, how long will this take, how long will I have to wait, how long does it take, how soon can I, how quickly will, how fast is, is this available now, is this currently available, is there an appointment available, is there a slot available, is there a booking available, is there capacity

---

### 3.12 Cost & Payment

The speaker wants information about pricing, charges, coverage, or financial terms.

how much does this cost, how much will this cost, how much am I being charged, how much do I need to pay, what is the cost, what is the price, what is the fee, what is the charge, what is the total, what is the balance, what is included, what is not covered, are there any fees, are there any hidden fees, are there any additional charges, are there any penalties, is there a cancellation fee, is there a late payment fee, is there a service charge, is there a delivery fee, is there a processing fee, is this free, is this included in the price, is this covered by my plan, is this covered by insurance, is this refundable, will I be charged, will I be charged extra, will there be additional charges

---

### 3.13 Options & Alternatives

The speaker wants to understand what choices are available to them.

what are my options, what options are available, what choices do I have, what alternatives are there, is there another option, is there another way, is there a different approach, can I switch, can I change, can I upgrade, can I choose, what happens if I choose, what is the difference between, how does this compare, how does this differ from, which is better, which is best, which would you recommend, which should I choose, which option is right for me, which is more suitable, which is more affordable, is it worth it, is it worth the cost, is it worth switching, is it the right choice, is it the best option

---

### 3.14 Seeking Guidance & Direction

The speaker does not know what to do or who to contact and is asking for direction.

what should I do, what should I do now, what should I do next, what is the best course of action, what is the right thing to do, what would you recommend, what would you advise, what do I do next, where do I start, where should I begin, where can I get help, where can I find help, who should I contact, who should I speak to, who should I ask, who can help me, who can advise me, who is the right person, who is the right contact, who handles this, who is responsible for this, who is my point of contact, I'm not sure what to do, I don't know what to do, I'm not sure where to start, I don't know how to proceed, I'm not sure how to handle this

---

### 3.15 Follow-up & Unanswered Questions

The speaker has already asked and not received a response — primarily seeking the information they were owed, not expressing anger as the primary intent.

I asked before but, I asked previously but, I already asked about this, I have asked multiple times, I have asked repeatedly, my question was not answered, my question was not addressed, my question was ignored, I never received an answer, I never got a response, nobody answered my question, no one got back to me, no one followed up, still waiting for an answer, still waiting for a response, still waiting for clarification, still waiting to hear back, I keep asking but, I've been following up on this, I've been waiting for an answer, I've been unable to get an answer, I can't get a straight answer, nobody can tell me, nobody seems to know, can someone please answer, can someone please explain, can someone please clarify, does anyone know, does anyone have an answer

---

## 4. Supplementary Signal Vocabulary

Individual keywords that strengthen an inquiry classification when found alongside the phrase patterns above.

### Core Question Words
what, why, when, where, who, whom, whose, which, how, whether, can, could, would, should, will, may, might, is, are, was, were, does, do, did, has, have, had

### Information Seeking
clarify, describe, elaborate, educate, explain, guide, inform, provide details, share, tell me

### Uncertainty Markers
baffled, confused, curious, doubtful, lost, perplexed, puzzled, questioning, skeptical, uncertain, unclear, unsure, wondering

### Investigation Intent
analyze, assess, determine, discover, evaluate, examine, explore, identify, investigate, look into, research, review, understand, uncover, validate, verify

### Assistance Seeking
advise me, assist, guide me, help me, point me in the right direction, show me, support, teach me, walk me through

### Decision-Making
best option, compare, comparison, pros and cons, recommended, right choice, suitable, which is better, which should I, worth it

### Status Seeking
confirmation, development, outcome, progress, reply, resolution, response, status, update

---

## 5. Sector-Specific Inquiry Examples

**Healthcare:** is this normal, should I see a doctor, what are the symptoms of, am I supposed to take this, what does this diagnosis mean, is this covered by my insurance

**Agriculture & Environment:** why are my crops failing, what should I use for, how do I improve yield, when should I plant, what fertilizer is recommended, why are my livestock sick

**Telecommunications:** why is my network slow, how do I activate this service, what package is best for me, why was I charged this amount, how do I transfer my number

**Government & GRM:** what are my rights in this case, who is responsible for this decision, what is the process for appealing, what are the criteria for compensation, when will I be compensated

**Education:** how do I apply, what are the admission requirements, when are applications open, am I eligible for a scholarship, what are the fees

**Finance & Payments:** when will my refund be processed, why was I charged twice, how do I dispute this charge, what is the outstanding balance, is there a payment plan available

---

## 6. Disambiguation Notes

- **Repeated inquiries with frustration** (*"I've asked five times and nobody answers"*) contain both inquiry and complaint signals. If the dominant intent is still to **get the information**, classify as inquiry and note embedded complaint.
- **"Why don't you do X?"** uses a question form but proposes a change → classify as suggestion.
- **"Can you please fix this?"** is a request for action, not information → classify as complaint/request.
- **Confirmation requests** (*"just to confirm, my appointment is at 3pm?"*) are inquiries even when they seem declarative.
- **Kiswahili equivalents:** *ninataka kujua* (I want to know), *naweza kuuliza* (can I ask), *sijui* (I don't know), *sifahamu* (I don't understand), *nini* (what), *lini* (when), *wapi* (where), *nani* (who), *kwa nini* (why), *jinsi gani* / *vipi* (how), *naomba ufafanuzi* (I request clarification), *natafuta taarifa* (I'm looking for information).
