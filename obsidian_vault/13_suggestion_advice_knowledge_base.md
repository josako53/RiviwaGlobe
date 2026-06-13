# Riviwa AI — Suggestion & Advice Classification Knowledge Base

## 1. Purpose & Usage

This document trains Riviwa AI to **identify and classify** feedback that constitutes a **suggestion, recommendation, or advice** — as opposed to a complaint, grievance, or compliment. When a user's feedback primarily contains these signals, the AI should:

1. **Detect** whether the feedback contains suggestion or advice signals
2. **Classify** it as `feedback_type: suggestion`
3. **Route** it to the appropriate team for review and action (not to a grievance handler)
4. **Respond** with acknowledgement that the idea has been received and logged

---

## 2. Suggestion vs. Other Feedback Types

| Signal Pattern | Type | Treatment |
|---|---|---|
| Proposes a change, improvement, or alternative | Suggestion | Log for product/service team |
| Reports dissatisfaction, harm, failure | Complaint / Grievance | Assign SLA, escalate if critical |
| "Great service", "well done", "thank you" | Compliment | Log for staff recognition |
| Question without negative or improvement intent | Inquiry | Route to support |

**Overlap rule:** Feedback can contain both complaint and suggestion signals — e.g., *"The wait was unacceptable — I suggest you hire more staff."* Classify by the **dominant intent**. If the primary purpose is to propose a solution or change, classify as suggestion. If the primary purpose is to express harm or dissatisfaction, classify as grievance even if a suggestion is embedded.

**Key distinction:** A suggestion is **forward-looking** — the person wants something to be different in the future. A complaint is **backward-looking** — the person is reporting something that went wrong in the past or is wrong now.

---

## 3. Suggestion Signal Categories

---

### 3.1 Direct Suggestion Starters

The speaker explicitly frames their input as a suggestion.

I suggest, I would suggest, I strongly suggest, I humbly suggest, may I suggest, might I suggest, if I may suggest, allow me to suggest, let me suggest, I'd like to suggest, I want to suggest, my suggestion is, one suggestion would be, what I'd suggest is, here is my suggestion

---

### 3.2 Direct Recommendation Starters

The speaker explicitly frames their input as a recommendation.

I recommend, I would recommend, my recommendation is, I highly recommend, I strongly recommend, I wholeheartedly recommend, I'd recommend, I firmly recommend, I recommend that, I recommend trying, I recommend considering, based on experience I recommend, from what I've seen I recommend, as a patient I recommend, as a regular user I recommend, as a professional I recommend

---

### 3.3 Direct Advice Starters

The speaker explicitly frames their input as advice.

my advice is, my advice would be, here is my advice, a word of advice, a piece of advice, I advise, I would advise, I strongly advise, I'd advise, let me give you some advice, I'd like to offer some advice, take my advice, speaking from experience my advice, my professional advice, my honest advice, for what it's worth my advice is, in my humble opinion you should, I offer this advice with good intent

---

### 3.4 Soft Proposal Language

Tentative or hedged suggestions that propose an idea without insisting on it.

it might be worth, it could be worth, it might help to, it could help to, it might make sense to, it could make sense to, it might be a good idea, it would be a good idea, it might be beneficial, it could be beneficial, it would be beneficial, it might be useful, it would be useful, it might be wise to, it would be wise to, it might be prudent, it would be prudent, it might be best to, it would be advisable, a beneficial step would be, a useful step would be, a helpful move would be

---

### 3.5 Conditional Improvement Language

Suggestions framed as conditions — implying that if a specific change is made, things will improve.

if you could, if you would, if you were able to, if it were possible to, if there is a way to, if changes were made, if improvements were made, if this were addressed, if this were fixed, if this were resolved, if this were updated, once this is resolved, once this is fixed, when this is addressed, should you decide to, should you choose to, should the team consider, should management look into, were this to improve, were this to be addressed, were you to consider, given the right changes, assuming this is fixed, provided that changes are made, on the condition that

---

### 3.6 Implicit Desire for Change

Expressions of wishes and hopes that imply a desired improvement without stating it as a direct command.

it would be nice if, it would be great if, it would be wonderful if, it would be ideal if, it would be helpful if, it would be perfect if, it would make a difference if, it would go a long way if, it would be appreciated if, it would mean a lot if, I wish there was, I wish you would, I wish this could change, I wish this would improve, I hope to see, I hope this changes, I hope action is taken, I hope you consider, I hope you look into, would love to see, would love it if, would appreciate if, would greatly appreciate, would be grateful if, would be thankful if, would welcome a change, would welcome improvement, it would be a game changer if, it would enhance things if, it would transform things if

---

### 3.7 Have You Considered / Would You Be Open To

Question-form suggestions that invite the organisation to consider an idea — typically polite and non-confrontational.

have you considered, have you thought about, have you looked into, have you explored, have you tried, have you tested, have you reviewed, have you evaluated, have you assessed, would you consider, would you think about, would you be open to, would you be willing to, would you explore, would you look into, could you consider, could you look into, could you explore, couldn't you consider, wouldn't it help to, wouldn't it be worth, wouldn't it make sense to, shouldn't you consider, isn't there a way to, isn't it possible to, isn't it worth trying, isn't it worth exploring

---

### 3.8 Why Not / What If / How About

Rhetorical prompts that propose alternatives or new directions.

why not, why not try, why not consider, why not explore, why not implement, why not add, why not improve, why not offer, why not introduce, what if you, what if you tried, what if you considered, what if you changed, what if a new approach, what if a different method, what about, what about trying, what about considering, what about a different approach, how about, how about trying, how about considering, how about a different approach, how about offering, how about introducing, how about making a change

---

### 3.9 You Should / Ought To / Need To

Direct directive suggestions telling the organisation what action to take. Distinguished from complaints by the presence of a constructive proposed action rather than an expression of harm.

you should, you should try, you should consider, you should ensure, you should prioritize, you should focus on, you should address, you should improve, you should implement, you should provide, you should allow, you ought to, you ought to consider, you ought to ensure, you ought to prioritize, you ought to address, you need to, you need to consider, you need to address, you need to fix, you need to improve, you need to ensure, you need to prioritize, you need to act on this

---

### 3.10 It Would Be Better / More Efficient If

Comparative suggestions that frame the current situation against an improved alternative.

it would be better if, it would be much better if, things would be better if, it would be more efficient if, it would be more effective if, it would be more professional if, it would be more reliable if, it would be more transparent if, it would be more accessible if, it would be more convenient if, it would be easier if, it would be simpler if, it would be faster if, it would be more timely if, it would be less complicated if, it would be less frustrating if, it would work better if, it would perform better if, it would flow better if, it would be more satisfying if, it would be more welcoming if, it would improve greatly if, it would improve significantly if, it would run better if

---

### 3.11 Please / Kindly Requests

Polite requests asking the organisation to take a specific constructive action.

please consider, please look into, please explore, please review, please ensure, please address, please improve, please add, please include, please provide, please allow, please prioritize, please focus on, please take into consideration, please bear in mind, please attend to, kindly consider, kindly look into, kindly ensure, kindly address, kindly improve, kindly include, kindly provide, kindly prioritize, kindly take into consideration, I kindly request, I politely request, I respectfully request, I formally request, I humbly request

---

### 3.12 Future-Oriented Language

Suggestions framed around future interactions — the speaker is not dwelling on the past but proposing what should happen going forward.

going forward, going forward please consider, going forward I suggest, in the future, in future please, in future consider, next time, next time please, next time consider, next time ensure, for future reference, for future improvement, for future customers, for future patients, for future users, for next time, moving forward, moving forward I suggest, from now on, from now on please, from this point forward, in subsequent interactions, in future visits, long term I suggest, strategically I recommend, as a long-term improvement

---

### 3.13 Comparative & Alternative Language

Suggestions that propose a replacement approach, contrasting the current method with a preferred one.

instead of, instead of this you could, instead of the current approach, rather than, rather than this consider, rather than the current method, as an alternative, as an alternative consider, alternatively, alternatively consider, a better approach would be, a better option would be, a better method would be, a more effective way, a more efficient way, a more practical approach, a different approach would be, a fresh approach would be, an improved version would, switching to, changing from this to, moving away from this toward, replacing this with, opting for instead, going with a different approach, pursuing a different strategy, adopting a new approach

---

### 3.14 Improvement & Enhancement Language

General improvement vocabulary — the speaker sees potential for better without necessarily expressing harm.

needs improvement, could be improved, should be improved, has room for improvement, there is scope to improve, there is potential to improve, an area for improvement, could be enhanced, should be enhanced, could be better, should be better, could be updated, needs updating, could be upgraded, needs upgrading, could be refined, needs refining, could be optimized, should be optimized, could be streamlined, needs streamlining, could be simplified, could be modernized, could be strengthened, could be expanded, could be redesigned, could be restructured, could be rethought, an area that needs attention, an area that needs work

---

### 3.15 Positive Framing / Small Change Language

Constructive suggestions presented as easy wins, minor adjustments, or practical next steps — optimistic and solution-focused.

one small change that would help, one thing that would greatly improve, a quick win would be, an easy win would be, a practical improvement would be, a sensible step would be, a smart move would be, a logical next step would be, a simple solution would be, a straightforward improvement, a much-needed improvement, a long-overdue change, something that would go a long way, something worth considering, something worth trying, something worth implementing, something that could transform the experience, something that could elevate the service, something that could build trust, something that could strengthen loyalty, something that would restore confidence, something that would show you care, a positive step would be, a welcome change would be, a good move would be

---

### 3.16 Implied Wishes & Benchmarks

Expressions of unmet expectations that imply what improvement should look like, often referencing other providers or a general standard.

it would have been better, it should have been better, I wish this had been different, I wish this was handled better, I expected better, I had hoped for better, I was hoping for, my expectation was, I had high hopes, I came expecting, I thought there would be, customers deserve better, patients deserve better, users deserve better, the least you could do is, at the very least, a basic expectation would be, a reasonable expectation is, other places do this better, competitors do this better, compared to others you fall short, below industry standard, I've seen it done better elsewhere, I know it can be done better, the benchmark is higher, you can do better than this, I know you can do better, better is achievable, improvement is possible, excellence is achievable, this falls short of what I know is possible, there is a higher standard achievable

---

## 4. Supplementary Signal Vocabulary

Individual keywords that strengthen a suggestion classification when found alongside the phrase patterns above.

### Strong Directive Signals
advocate, counsel, direct, enforce, ensure, exhort, guide, implement, insist, mandate, prescribe, prioritize, require, stress, urge

### Soft / Conditional Signals
arguably, conceivably, consider, contemplate, depending on, explore, feasibly, investigate, optionally, perhaps, possibly, potentially, review, tentatively, weigh

### Value & Quality Signals
advantageous, beneficial, better, constructive, effective, efficient, ideal, improved, optimal, practical, prudent, reliable, sensible, superior, valuable, wise, worthwhile

### Experiential Signals
as far as I can tell, from my experience, from my vantage point, I can attest to, I've found that, if I were you, in my experience, personally speaking

### Idiomatic Signals
bridge the gap, change gears, go the extra mile, iron out, pave the way, raise the bar, take the reins, think outside the box

### Process & Methodological Signals
incrementally, phase by phase, proactively, step-by-step, streamlined, systematically, structured approach, foundational change

### Data & Analytical Signals
analytics indicate, best practices imply, data suggests, evidence points to, findings demonstrate, research proves, studies show, trends indicate

### Comparative / Alternative Signals
alternatively, in contrast, rather than, replacing with, substituting with, transitioning to, upgrading to

### Preventative & Risk-Mitigation Signals
anticipate, handle with care, mitigate, pre-empt, prevent, proceed with caution, take precautions, to avoid, to minimize, to reduce

---

## 5. Disambiguation Notes

- **"I need to…"** (speaker about themselves) is not a suggestion. **"You need to…"** (speaker directing the organisation) is a suggestion.
- **"Please fix this"** alone leans toward a complaint/request. **"Please consider changing the process to…"** is a suggestion.
- **"It was better before"** without proposing a change is a complaint. **"It would be better if you…"** is a suggestion.
- Suggestions are often **polite and constructive** in tone — but harsh phrasing ("you should completely overhaul this") is still a suggestion if it proposes a change rather than expressing harm.
- A speaker who uses **multiple suggestion signals in one message** (e.g., "I suggest… I recommend… it would be better if…") should be classified as suggestion with high confidence even if isolated complaint words appear.
- **Kiswahili equivalents:** *napendekeza* (I suggest), *ningependa kupendekeza* (I'd like to suggest), *ushauri wangu ni* (my advice is), *ingekuwa vizuri kama* (it would be nice if), *unapaswa* (you should), *fikiria* (consider).
