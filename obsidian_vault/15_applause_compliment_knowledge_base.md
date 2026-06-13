# Riviwa AI — Applause & Compliment Classification Knowledge Base

## 1. Purpose & Usage

This document trains Riviwa AI to **identify and classify** feedback that constitutes an **applause, compliment, or expression of praise** — as opposed to a complaint, suggestion, or inquiry. When a user's feedback primarily contains these signals, the AI should:

1. **Detect** whether the feedback contains compliment or applause signals
2. **Classify** it as `feedback_type: compliment`
3. **Route** it to staff recognition and service quality teams
4. **Respond** with acknowledgement and thanks, and flag for commendation records

---

## 2. Compliment vs. Other Feedback Types

| Signal Pattern | Type | Treatment |
|---|---|---|
| Expresses praise, satisfaction, or gratitude | Compliment | Log for staff recognition; route to quality team |
| Reports dissatisfaction, harm, failure | Complaint / Grievance | Assign SLA, escalate if critical |
| Proposes a change or improvement | Suggestion | Log for product/service team |
| Seeks information or clarification | Inquiry | Route to support team |

**Overlap rule:** Feedback often mixes types — e.g., *"The service was amazing [compliment] — but could you open earlier? [suggestion]"*. Classify by dominant intent. Log embedded signals of other types separately.

**Common ambiguities:**
- *"Surprisingly good for once"* or *"not as bad as usual"* → weak compliment with embedded complaint signal; classify as mixed.
- *"The food was amazing but the wait was terrible"* → note both signals; dominant intent determines primary classification.
- *"You slayed this"* or *"absolutely bussin"* → colloquial compliment; treat equally with formal praise for classification purposes.
- High-emotion language (*"I was moved to tears"*, *"it changed my life"*) = strong compliment signal even without explicit praise words.

---

## 3. Compliment Signal Categories

---

### 3.1 Direct Praise & Commendation

The speaker explicitly praises the quality of work, output, or performance.

well done, excellently done, brilliantly done, perfectly done, expertly done, masterfully done, flawlessly done, good job, great job, excellent job, fantastic job, outstanding job, phenomenal job, exceptional job, good work, great work, excellent work, outstanding work, remarkable work, keep it up, keep up the good work, keep up the excellent work, well done to the team, well done to the staff, well done to all involved, bravo, nailed it, crushed it, knocked it out of the park, spot on, on point, on the money, kudos, gold star, well played, nicely done, beautifully done, sheer perfection, flawless execution, top tier, sterling work, stellar work, home run, ace, ten out of ten, bullseye, dead on, chef's kiss, absolutely right, good stuff, great stuff

---

### 3.2 Gratitude & Thankfulness

The speaker expresses genuine thanks for help, effort, or care received.

thank you, thank you so much, thank you very much, thank you from the bottom of my heart, many thanks, heartfelt thanks, sincere thanks, warmest thanks, endless thanks, profound thanks, much appreciated, deeply appreciated, truly appreciated, sincerely appreciated, deeply grateful, truly grateful, sincerely grateful, forever grateful, eternally grateful, profoundly grateful, I am beyond grateful, I can't thank you enough, words cannot express my gratitude, my gratitude knows no bounds, I owe you a great deal, your help meant everything, your support meant the world, your effort did not go unnoticed, your dedication did not go unnoticed, I noticed and I appreciate it, I see the effort and I appreciate it, I am indebted to you

---

### 3.3 Satisfaction & Delight

The speaker expresses high levels of satisfaction, happiness, or positive emotion about an outcome or interaction.

I am completely satisfied, I am beyond satisfied, very happy with, thrilled with, delighted with, overjoyed with, ecstatic about, elated about, pleased with, extremely pleased with, couldn't be happier, couldn't have asked for better, couldn't ask for more, exceeded my expectations, far exceeded my expectations, surpassed my expectations, blew my expectations out of the water, better than I hoped, better than I imagined, pleasantly surprised, I was genuinely impressed, I was blown away, I was left speechless with joy, left me smiling, made my day, put a smile on my face, made all the difference, brightened my day

---

### 3.4 Recognizing Staff & Individuals

The speaker calls out a specific person or team for exceptional performance.

shout out to, a big shout out to, special mention to, special recognition to, I want to commend, I want to recognize, I want to acknowledge, I would like to give credit to, credit goes to, kudos to, hats off to, props to, a round of applause for, standing ovation for, this person deserves recognition, this person deserves a medal, this person went above and beyond, this person made all the difference, this person is an asset, this person is a credit to the organization, this person restored my faith

**Staff quality signals:** the staff were amazing, fantastic, excellent, outstanding, incredibly helpful, genuinely kind, warm and friendly, highly professional, courteous, polite, attentive, caring, compassionate, empathetic, patient, knowledgeable, competent, efficient, dedicated, committed, hardworking

---

### 3.5 Quality & Excellence Recognition

The speaker praises the standard, workmanship, or output quality directly.

excellent quality, exceptional quality, outstanding quality, world-class quality, premium quality, top-notch quality, first-class quality, the quality was impeccable, the quality was flawless, the quality was unmatched, the quality was second to none, the quality exceeded expectations, the quality raised the bar, the quality set a new standard, the quality was industry-leading, the quality was best in class, service quality was excellent, care quality was impeccable, build quality was exceptional, content quality was outstanding, teaching quality was excellent

---

### 3.6 Experience & Feeling Words

The speaker describes how the overall experience felt — emotionally and practically.

**Experience descriptors:** amazing experience, wonderful experience, outstanding experience, memorable experience, unforgettable experience, delightful experience, seamless experience, smooth experience, effortless experience, stress-free experience, hassle-free experience, first-class experience, world-class experience, phenomenal experience, exceptional experience, life-changing experience

**Feeling signals:** I felt valued, I felt appreciated, I felt respected, I felt cared for, I felt heard, I felt listened to, I felt understood, I felt welcomed, I felt at home, I felt comfortable, I felt reassured, I felt safe, I felt in good hands, I felt looked after, I felt supported, I felt empowered, I felt like a priority, I felt like a valued customer, I felt like family, I felt seen, I felt noticed, I felt the warmth, I felt the care, I felt the dedication, I felt the professionalism, I felt the sincerity, I felt the authenticity

---

### 3.7 Recommendation & Endorsement

The speaker actively promotes the service to others or signals they will return.

I would highly recommend, I would strongly recommend, I would not hesitate to recommend, I would recommend without reservation, I would recommend to everyone, I would recommend to family, I would recommend to friends, I have already recommended to others, I have told everyone about this, I have spread the word, I will keep coming back, I will definitely return, I will always come back, I will never go anywhere else, this is my go-to, this is my first choice, this is my preferred provider, five stars, ten out of ten, maximum rating, deserves more than five stars, would give more stars if I could, this deserves the highest rating, every star is well deserved, no rating is high enough

---

### 3.8 Surprise & Delight (Above & Beyond)

The speaker was positively surprised — the service or outcome far exceeded what they expected.

above and beyond, went above and beyond, truly above and beyond, beyond what was required, beyond the call of duty, beyond what was promised, exceeded all expectations, surpassed every expectation, far surpassed expectations, I was blown away, completely blown away, knocked my socks off, floored, I did not expect this level of service, I was not expecting such quality and care, pleasantly caught off guard, the best kind of surprise, a wonderful surprise, surprised me in the best way, could not believe how good, could not believe the quality, I had to share this, I felt compelled to leave a review, I just had to say something

---

### 3.9 Loyalty & Trust Signals

The speaker expresses enduring trust, confidence, and commitment to the provider.

I trust you completely, I have complete confidence, my trust has been earned, you have earned my trust, you have earned my loyalty, you have earned my business, you have my full endorsement, you have proven yourselves, you have demonstrated excellence, you have shown integrity, you have shown consistency and dedication, I will always trust you, I will always choose you, I feel confident choosing you, I feel safe choosing you, my faith has been restored, this rebuilt my trust and confidence, this is why I keep coming back, this is why I recommend you over others, you stand out from the rest, you are head and shoulders above, there is no one I trust more, there is nowhere else I would go, I have renewed faith

---

### 3.10 Admiration & Inspiration

The speaker expresses deep admiration or states that the service/team inspired them.

I admire the dedication, I admire the commitment, I admire the passion, I admire the quality, I admire the attention to detail, I admire the excellence, I am in awe, I am truly in awe, I stand in admiration, this is inspirational, this inspired confidence, this inspired loyalty, this sets the standard, this raises the bar, this is a new benchmark, this is what excellence looks like, this is what great service looks like, this is what dedication looks like, this is the gold standard, this is industry-leading, this is world-class, this is best in class, this deserves formal recognition, others should aspire to this standard, this is a role model for others, this should be taught and shared as an example

---

### 3.11 Positive Outcome Praise

The speaker praises the resolution, delivery, or result of a specific request or issue.

the problem was resolved quickly and efficiently, the issue was handled professionally, it was fixed promptly, it was sorted out efficiently, it was dealt with professionally, everything was resolved, everything went smoothly, everything was seamless, everything was effortless, everything was perfect, exactly what I needed, exactly what was promised, delivered on every promise, kept every promise, honored every commitment, met every expectation, exceeded every expectation, the result was outstanding, the outcome exceeded expectations, the turnaround was impressive, the response was prompt, the response time was excellent, the resolution was quick and professional

---

### 3.12 Value & Worth Expressions

The speaker praises the value received relative to cost or effort.

worth every penny, worth every shilling, worth every cent, worth the investment, absolutely worth it, definitely worth it, without a doubt worth it, the best value, excellent value for money, outstanding value for money, money well spent, best money I ever spent, best decision I ever made, I got more than I paid for, I got more than my money's worth, the price was very fair, the pricing was transparent and honest, no hidden costs, exactly what was quoted, fair and honest billing, I felt I got full value, I felt the price was right, I felt it was a great deal

---

### 3.13 Emotional Impact

The speaker expresses that the experience had a profound emotional effect on them.

it meant the world to me, it meant everything to me, it made all the difference, it changed my experience entirely, it changed how I see you, it restored my faith, it gave me peace of mind, it gave me relief and comfort, I will never forget this, I will always remember the kindness, this touched my heart, this warmed my heart, this moved me, this genuinely moved me, this brought tears to my eyes, I was moved to tears, I was overwhelmed with gratitude and joy, I was deeply touched, I was profoundly touched, I was moved beyond words, words cannot describe how grateful I am, words cannot express my gratitude, no words can do this justice, I felt my heart full, my heart swelled with gratitude

---

### 3.14 Comparative & Superlative

The speaker uses the highest possible comparative language to describe the service or provider.

the best I have ever experienced, the best service I have ever had, the best quality I have ever seen, the best experience of my life, better than anywhere else, better than all the rest, better than industry standard, unlike anything I have experienced before, unlike any other, one of a kind, in a league of its own, stands out from the crowd, head and shoulders above the rest, miles ahead of the competition, second to none, without equal, beyond compare, incomparable, unmatched, unrivaled, unparalleled, unsurpassed, peerless, matchless, the pinnacle of service and quality, the gold standard, the benchmark, the industry leader, the best in class, simply the best, by far the best, clearly the best, without question the best

---

### 3.15 Informal & Colloquial Praise

Casual, social-media, and Gen-Z expressions of praise that carry the same compliment intent as formal language.

awesome, brilliant, incredible, fire, lit, dope, sick, rad, groovy, top tier, nailed it, slayed, serving, ate that and left no crumbs, goated, legendary, an absolute legend, the GOAT, greatest of all time, massive W, huge W, bussin, no cap, straight fire, goes hard, chef's kiss, you rock, you rule, you're the best, knocked my socks off, swept me away, out of this world, from another planet, epic win, home run, grand slam, I loved it, obsessed with it, my favorite, absolute banger, this slaps, pure fire, ten out of ten no notes, main character energy, iconic

---

## 4. Supplementary Signal Vocabulary

Individual keywords and short phrases that strengthen a compliment classification when found alongside the phrase patterns above.

### Praise Verbs
applaud, celebrate, commend, compliment, endorse, honor, laud, praise, recognize, salute, tribute to

### Emotion Words
delighted, ecstatic, elated, grateful, happy, joyful, moved, overjoyed, pleased, relieved, satisfied, thankful, thrilled, touched

### Trust & Reliability Signals
consistent, credible, dependable, principled, professional, reliable, reputable, trustworthy, transparent, unwavering

### Approval Signals
accredited, approved, certified, endorsed, recommended, sanctioned, validated

### Core Excellence Adjectives
exceptional, excellent, outstanding, remarkable, impressive, brilliant, superb, fantastic, wonderful, incredible, phenomenal, stellar, top-notch, first-class, world-class, gold-standard, exemplary, commendable, admirable, praiseworthy, laudable, noteworthy, meritorious, magnificent, spectacular, extraordinary, splendid, sublime, glorious, majestic

### Effort & Character Signals
caring, compassionate, dedicated, devoted, diligent, generous, hardworking, honest, humble, kind, patient, principled, selfless, sincere, tireless, thoughtful, warm

### High-Confidence Compliment Triggers
life-changing, moved to tears, heart full, means the world, cannot thank enough, gold standard, above and beyond, beyond compare, best ever, in a league of its own

---

## 5. Sector-Specific Compliment Examples

**Healthcare:** the care I received was exceptional, the nurses were incredibly kind and attentive, I felt safe and in good hands throughout, the diagnosis was spot on, the treatment worked perfectly

**Education:** the teaching quality was outstanding, the instructor explained everything clearly and patiently, the learning experience was engaging and effective, the support from staff was excellent

**Government & GRM:** my complaint was handled professionally and swiftly, I was kept informed throughout the process, the resolution was fair and transparent, the officer was respectful and knowledgeable

**Hospitality:** the food was exquisite, the service was impeccable, the ambiance was perfect, we felt like VIPs, the team went above and beyond to make us feel welcome

**Telecommunications & Technology:** the connection was perfect, the app works flawlessly, customer support was excellent and resolved my issue immediately, the interface is intuitive and seamless

**Agriculture & Environment:** the advice I received was practical and useful, the team understood our needs immediately, the response time was impressive

---

## 6. Disambiguation Notes

- **Mixed compliment + suggestion:** *"Excellent service — could you open earlier?"* → classify as compliment; log the suggestion separately.
- **Backhanded compliments:** *"Surprisingly good for once"* or *"better than I expected given your usual standard"* → weak compliment signal with embedded complaint; classify as mixed; note both.
- **Mixed compliment + complaint:** *"The food was amazing but the wait was terrible"* → note both signals; dominant intent determines primary classification.
- **Formal vs informal language:** colloquial signals (*"you slayed"*, *"bussin"*, *"no cap"*) carry the same compliment intent as formal phrases; treat equally for classification.
- **High-emotion language** (*"moved to tears"*, *"changed my life"*, *"I will never forget this"*) = strong compliment signal even without explicit praise words.
- **Repeated praise = high confidence:** a message containing multiple compliment signals from different categories (e.g., gratitude + staff recognition + endorsement) should be classified as compliment with very high confidence.
- **Kiswahili equivalents:** *hongera* (congratulations / well done), *asante sana* (thank you very much), *nimefurahi sana* (I am very pleased), *huduma bora* (excellent service), *unafanya kazi nzuri sana* (you are doing great work), *nashukuru sana* (I am very grateful), *wewe ni bora* (you are the best), *ulifanya kazi nzuri sana* (you did excellent work), *ninapendeza na huduma hii* (I am delighted with this service), *hii ni bora kabisa* (this is absolutely the best).
