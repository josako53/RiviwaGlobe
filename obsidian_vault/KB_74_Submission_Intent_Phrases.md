---
tags: [submission-intent, confirm-phrases, conversation-ai, swahili, multilingual]
---
# Feedback Submission Intent — Keywords, Phrases & Real-World Scenarios

## Purpose

This knowledge base helps Riviwa AI correctly identify when a Consumer is expressing intent to SUBMIT their feedback — whether explicitly, implicitly, through frustration, through completion signals, or through code-switching. Misreading submission intent causes either (a) premature submission before the user is ready, or (b) failure to submit when the user is clearly done. Both break trust.

**Rule for AI:** When the conversation is in CONFIRMING stage AND the Consumer's message matches ANY pattern below → set `action=submit`.

---

## 1. DIRECT SUBMISSION COMMANDS (Explicit — Always Submit)

These are unambiguous. The Consumer is directly ordering submission.

### Swahili
| Phrase | Context/Notes |
|--------|--------------|
| Wasilisha | "Submit" — the standard Swahili command |
| Tuma | "Send" — very common; same meaning as submit in this context |
| Ingiza | "Enter/Register" — used when consumer thinks of feedback as "registering" a case |
| Sajili | "Register" — "Sajili malalamiko yangu" = "Register my complaint" |
| Piga chapa | Rare; "Print/Stamp it" — implies formalisation, same intent |
| Peleka | "Send it / Take it" — "Peleka malalamiko yangu" |
| Nitume | "Let me send" or "I want to send" |
| Nipeleke | "Let me take/submit it" |
| Niwasilishe | "Let me submit" / "Have it submitted" |

### English
| Phrase | Context/Notes |
|--------|--------------|
| Submit | Direct |
| Send it | "Send it" after providing details |
| Send this | Same |
| File it | More formal; "file my complaint" |
| Lodge it | "Lodge the complaint" — formal register |
| Register it | "Please register my complaint" |
| Record it | "Please record this" |
| Go ahead | After AI shows summary — "Go ahead" = submit |
| Proceed | "Please proceed" = submit |
| Do it | "Just do it" = impatient submission command |
| Yes, submit | Confirmed + command |
| Please submit | Polite command |
| Submit now | Urgent command |
| Just submit | Frustrated/impatient command |

### Code-Switching (Swahili-English mix — very common in Tanzania/East Africa)
| Phrase | Swahili + English Mix |
|--------|----------------------|
| Ndiyo, please submit | Yes, please submit |
| OK tuma | OK send it |
| Sawa, submit | Fine, submit |
| Yes wasilisha | Yes, submit (English yes + Swahili verb) |
| Submit tu | Just submit (Swahili emphasis "tu") |
| Go ahead tuma | Proceed and send |
| File it tu | Just file it |
| Ndiyo, file hii | Yes, file this |
| OK, proceed wasilisha | OK proceed, submit |
| Record hii tuma | Record this and send |

---

## 2. CONFIRMATION RESPONSES (After AI shows summary — Submit)

These occur in CONFIRMING stage when the AI has displayed the complaint summary and asked "Is this correct? Shall I submit?" The Consumer's response below = submit.

### Affirmative Yes Variants
| Phrase | Language | Notes |
|--------|----------|-------|
| Ndiyo | Swahili | Standard yes |
| Ndio | Swahili | Common spelling variant |
| Naam | Swahili/Arabic | More formal "yes" used by older/Muslim speakers |
| Eh | Swahili (informal) | Colloquial yes — very common in casual speech |
| Ndiyo kabisa | Swahili | "Yes absolutely" |
| Ndiyo, hiyo ni sahihi | Swahili | "Yes, that is correct" |
| Hiyo ni sahihi | Swahili | "That is correct" (without ndiyo) — still submit |
| Sahihi | Swahili | "Correct" as a standalone = yes, correct |
| Kweli | Swahili | "True/Correct" — rare but valid affirmative |
| Nakubaliana | Swahili | "I agree" = confirm |
| Nakubali | Swahili | "I agree/accept" |
| Yes | English | Standard |
| Yeah | English informal | |
| Yep | English informal | |
| Correct | English | "Correct" alone = confirm summary |
| That's right | English | |
| That's correct | English | |
| Exactly | English | |
| Accurate | English | |
| Yes that's it | English | |
| Yes that's correct | English | |
| Yes, go ahead | English | |
| Yes please | English polite | |

### Approval/Proceed Signals
| Phrase | Language | Notes |
|--------|----------|-------|
| Sawa | Swahili | "OK/Fine/Alright" — most common approval word |
| Sawa sawa | Swahili | Emphatic "OK" |
| Vizuri | Swahili | "Good/Well" — approves the summary |
| Nzuri | Swahili | "Good" — approves |
| Endelea | Swahili | "Continue/Proceed" = go ahead and submit |
| Fanya hivyo | Swahili | "Do that" = do it (submit) |
| Fanya | Swahili | "Do it" |
| Ninaomba ufanye | Swahili | "I request you do it" |
| Tafadhali endelea | Swahili | "Please proceed" |
| OK | Universal | |
| Okay | Universal | |
| Alright | English | |
| Fine | English | |
| Sure | English | |
| Of course | English | |
| Please do | English | |
| Please go ahead | English | |
| By all means | English formal | |

### Completion + Approval Combos (very common in real conversations)
| Real-world phrase | Language | What the person means |
|-------------------|----------|----------------------|
| "Ndiyo, hiyo ndiyo yote." | Swahili | Yes, that's all — submit |
| "Ndiyo, hiyo ni yote niliyotaka kusema." | Swahili | Yes, that's everything I wanted to say |
| "Sahihi, tuma sasa." | Swahili | Correct, send now |
| "Sawa, wasilisha basi." | Swahili | OK, submit then |
| "Ndiyo basi." | Swahili | Yes then / yes, that's it |
| "Ndio, tafadhali." | Swahili | Yes please |
| "Yes, that's what happened. Please submit." | English | |
| "That's correct, please go ahead." | English | |
| "Yes, file it as is." | English | |
| "Exactly, please send." | English | |
| "Hiyo ndiyo. Peleka." | Swahili | That's it. Send it. |
| "Vizuri sana. Wasilisha." | Swahili | Very good. Submit. |

---

## 3. COMPLETION SIGNALS (Indicates conversation is done — Submit if in Confirming)

The Consumer signals they have no more to add. If already in CONFIRMING stage, treat as submit.

### "I've said everything" signals
| Phrase | Language | Notes |
|--------|----------|-------|
| "Hiyo ndiyo yote." | Swahili | "That's all" |
| "Hiyo tu." | Swahili | "Just that" |
| "Sina zaidi." | Swahili | "I have nothing more" |
| "Nimesema yote." | Swahili | "I've said everything" |
| "Kila kitu nimesema." | Swahili | "I've said everything" |
| "Hii ndiyo tatizo langu." | Swahili | "This is my problem" — signals completion |
| "Nakushukuru kwa msaada." | Swahili | "Thank you for the help" — usually signals done |
| "Asante, hiyo tu." | Swahili | "Thank you, that's all" |
| "That's all." | English | |
| "That's everything." | English | |
| "That's my complaint." | English | |
| "I have nothing else to add." | English | |
| "That covers it." | English | |
| "That's the whole story." | English | |
| "I'm done." | English | |
| "Done." | English | |

### "Just do it already" (impatient completion)
| Phrase | Language | Emotional tone |
|--------|----------|---------------|
| "Tuma tu basi!" | Swahili | Impatient — "Just send it already!" |
| "Wasilisha tu." | Swahili | "Just submit." |
| "Nimemaliza, tuma." | Swahili | "I'm done, send." |
| "Nimeelezea yote, sasa tuma." | Swahili | "I've explained everything, now send." |
| "Kwa nini unauliza tena? Tuma tu!" | Swahili | "Why are you asking again? Just send!" |
| "Just submit it already!" | English | Impatient |
| "Stop asking — just file it." | English | Frustrated |
| "I've said enough, submit!" | English | Done talking |
| "Submit whatever you have." | English | Accepting partial info |
| "File it as it is." | English | Don't wait for more |

---

## 4. IMPLIED SUBMISSION THROUGH URGENCY

The Consumer doesn't say "submit" but the urgency of the situation implies they want action taken NOW — which means submit and escalate.

| Real-world phrase | Implied meaning | Action |
|------------------|-----------------|--------|
| "Hii ni ya haraka sana, tafadhali msaada!" | Emergency/urgent — submit AND escalate | Submit + is_urgent=true |
| "Mtu anaweza kuumia, tafadhali fanya kitu sasa!" | Safety risk — submit immediately | Submit + is_urgent=true |
| "Mtoto wangu yuko hospitalini, nahitaji hili kushughulikiwa SASA." | Medical emergency context | Submit + is_urgent=true |
| "Tumekuwa tukisubiri miezi mitatu, hatuwezi kuendelea hivi." | Chronic unresolved issue | Submit |
| "Please, this is urgent, I need help right now." | English urgency | Submit + is_urgent=true |
| "This is an emergency situation, please act." | Emergency | Submit + is_urgent=true |
| "We are suffering because of this — please do something." | Human impact | Submit |
| "I cannot wait any longer — this needs to be recorded." | Time pressure | Submit |
| "Naomba sana, hii inaathiri familia yangu." | Family impact, pleading | Submit |

---

## 5. RESPONSES TO SPECIFIC AI QUESTIONS (Q&A Patterns)

These are exact Q&A pairs from real feedback conversations. When the AI asks any of these questions and gets the shown responses, always submit.

### AI asks: "Je, maelezo haya ni sahihi? Niwasilishe?"
(Are these details correct? Shall I submit?)

Valid submit responses:
- "Ndiyo" → SUBMIT
- "Ndio" → SUBMIT
- "Sawa" → SUBMIT
- "Sahihi" → SUBMIT
- "Ndiyo, tuma" → SUBMIT
- "Naam" → SUBMIT
- "Eh, sawa" → SUBMIT (casual Swahili)
- "Yes" → SUBMIT
- "Yes please" → SUBMIT
- "Go ahead" → SUBMIT
- "Proceed" → SUBMIT
- "That's correct" → SUBMIT
- Any combination of the above → SUBMIT

### AI asks: "Je, hii ni yote unayotaka kusema?"
(Is this all you want to say?)

Valid submit responses:
- "Ndiyo, hiyo ndiyo yote" → SUBMIT
- "Ndiyo, wasilisha sasa" → SUBMIT
- "Hiyo tu" → SUBMIT
- "Yes, that's everything" → SUBMIT
- "Ndiyo, nakushukuru" → SUBMIT (thanks = done)
- "Asante" alone → SUBMIT (in this context)

### AI asks: "Niwasilishe malalamiko haya kwa niaba yako?"
(Shall I submit this complaint on your behalf?)

Valid submit responses:
- "Ndiyo, tafadhali" → SUBMIT
- "Tafadhali fanya hivyo" → SUBMIT
- "Nakuomba ufanye hivyo" → SUBMIT
- "Please do" → SUBMIT
- "Yes, please do that" → SUBMIT
- "Fanya" → SUBMIT
- "Sawa" → SUBMIT

### AI asks: "Ungependa niongeze chochote kabla sijawasilisha?"
(Would you like to add anything before I submit?)

Valid "nothing to add, submit" responses:
- "Hapana, hiyo inatosha" → SUBMIT ("No, that's enough")
- "Hakuna kingine" → SUBMIT ("Nothing else")
- "Sina zaidi ya kusema" → SUBMIT ("Nothing more to say")
- "No, that's fine" → SUBMIT
- "No, submit as is" → SUBMIT
- "Nothing else, go ahead" → SUBMIT
- "Tuma tu" → SUBMIT ("Just send")

---

## 6. ANTI-PATTERNS — Do NOT Submit

These look similar to submission signals but are NOT submission intent. The AI must distinguish.

| Phrase | Why NOT submit | What to do instead |
|--------|---------------|-------------------|
| "Ndiyo, ninajua" | Acknowledging AI's statement, not confirming | Continue collecting |
| "Ndiyo, nitarudi hospitalini" | Answering AI's question about their plans | Continue collecting |
| "Sawa, naelewa" | "OK I understand" — acknowledging, not submitting | Continue collecting |
| "OK, asante kwa maelezo" | Thanking AI for information it gave | Continue collecting |
| "Yes, I understand the process" | Acknowledging explanation | Continue collecting |
| "Ndiyo, nilikuwa hospitalini" | Confirming a fact in the story | Continue collecting |
| "Yes, that happened last week" | Confirming timeline detail | Continue collecting |
| "OK so what happens next?" | Asking about process | Explain → Continue |
| "Yes, I want to know more" | Wants more information | Continue explaining |
| "Ndiyo, ninaendelea kusimulia" | "Yes, I'm continuing to tell the story" | Let them continue |

**Key distinguisher:** "Ndiyo" in response to a YES/NO question about a FACT = answering the question, not submitting. "Ndiyo" in response to "Je, niwasilishe?" = SUBMIT.

---

## 7. REAL-WORLD SCENARIO SCRIPTS

### Scenario A: Hospital Complaint — Swahili (East African SMS style)
```
AI:  Malalamiko yako kuhusu Dkt. Kamau, Hospitali ya Muhimbili,
     Idara ya Dharura, tarehe 10 Juni 2026 — je, hii ni sahihi?
     Niwasilishe?

User: sawa tuma

→ ACTION: SUBMIT ✓
```

### Scenario B: Telecoms Complaint — Code-switch
```
AI:  Your complaint about Vodacom data billing issue on July 2nd
     has been recorded. Is this correct? Shall I submit?

User: yes please go ahead

→ ACTION: SUBMIT ✓
```

### Scenario C: Impatient/frustrated consumer
```
AI:  Ningependa kuhakikisha maelezo: maji machafu kutoka kwa
     DAWASCO tangu Aprili...

User: Nimeelezea yote! Tuma tu basi!

→ ACTION: SUBMIT (even mid-confirming) ✓
```

### Scenario D: Elderly speaker, indirect style
```
AI:  Mama, malalamiko yako kuhusu msaada uliopungua kwenye
     zahanati yako yamerekodiwa. Je, nakuwasilishie?

User: Naam, watoto wangu walisema niwasilishe.

→ ACTION: SUBMIT ✓ ("Naam" + context of being told to submit)
```

### Scenario E: NGO beneficiary using local language + Swahili mix
```
AI:  Malalamiko yako kuhusu chakula ambacho hakikufika imebakiwa.
     Niwasilishe kwa ofisi ya NGO?

User: Eh, fanya hivyo tafadhali.

→ ACTION: SUBMIT ✓ ("Eh" = yes, "fanya hivyo" = do that)
```

### Scenario F: Consumer thinks they've already submitted
```
User: Nimekwisha sema, haijatumwa?

→ Means: "I've already said everything — hasn't it been sent?"
→ ACTION: If minimum data present → confirm and ask once → SUBMIT
```

### Scenario G: Consumer adds final detail then signals done
```
User: ...na tukio hili lilitokea saa nne asubuhi. Hiyo ndiyo yote.

→ "Hiyo ndiyo yote" = that's all → if in CONFIRMING → SUBMIT
→ If still COLLECTING, confirm summary first, then submit on next "Ndiyo"
```

### Scenario H: Short emphatic completion (common on WhatsApp)
```
User: 👍

→ Thumbs up emoji after AI summary = approval = SUBMIT ✓

User: ✅

→ Check mark emoji = confirmed = SUBMIT ✓
```

### Scenario I: Professional/formal English speaker
```
AI:  I have recorded your complaint regarding the bank transaction
     dispute at NMB Kariakoo branch, TZS 500,000 deducted on
     12 June 2026. Is this accurate? Shall I proceed?

User: That is accurate. Please proceed.

→ ACTION: SUBMIT ✓
```

### Scenario J: Consumer changes mind mid-confirmation (DO NOT SUBMIT)
```
AI:  Malalamiko yako yamerekodiwa. Je, niwasilishe?

User: Ngoja kidogo — nataka kuongeza kitu.

→ "Ngoja kidogo" = "Wait a moment" → DO NOT SUBMIT
→ Return to COLLECTING, let them add more
```

---

## 8. EMOJI SIGNALS (WhatsApp/Messaging context)

In WhatsApp conversations, emojis carry submission meaning:

| Emoji | Meaning in context | Action |
|-------|-------------------|--------|
| 👍 | Approval/agree | SUBMIT if in CONFIRMING |
| ✅ | Confirmed/checked | SUBMIT if in CONFIRMING |
| 🙏 | Please do it / thank you | SUBMIT if in CONFIRMING |
| ✔️ | Tick = correct | SUBMIT if in CONFIRMING |
| 👌 | OK/perfect | SUBMIT if in CONFIRMING |
| 😊 after summary | Approves summary | SUBMIT if in CONFIRMING |
| ❌ | No/wrong | Do NOT submit — ask what's wrong |
| 🚫 | No | Do NOT submit |
| ✏️ | Edit/change something | Do NOT submit — ask what to change |

---

## 9. SUBMISSION REFUSAL SIGNALS (Critical — Do NOT Submit)

If Consumer says any of these after AI summary → do NOT submit, ask what's wrong.

| Phrase | Language | Action |
|--------|----------|--------|
| "Hapana" | Swahili | No — ask what's wrong |
| "Sivyo" | Swahili | "That's not right" |
| "Hiyo si sahihi" | Swahili | "That is not correct" |
| "Subiri" | Swahili | "Wait" |
| "Ngoja" | Swahili | "Wait/Hold on" |
| "Ngoja kidogo" | Swahili | "Wait a moment" |
| "No" | English | Do not submit |
| "Not yet" | English | Still not ready |
| "Wait" | English | Pause |
| "That's wrong" | English | Incorrect — re-collect |
| "That's not what I said" | English | Misunderstood — re-collect |
| "You got it wrong" | English | Error — re-collect |
| "Nimesema tofauti" | Swahili | "I said something different" |
| "Hiyo si nilichosema" | Swahili | "That's not what I said" |
| "Badilisha" | Swahili | "Change it" |
| "Rekebisha" | Swahili | "Correct it" |

---

## 10. REGIONAL & DIALECT VARIATIONS

### Coastal Swahili (Dar es Salaam, Mombasa, Zanzibar)
| Standard | Coastal variant | Meaning |
|----------|----------------|---------|
| Ndiyo | Eeeh / Ey | Yes (coastal affirmative) |
| Sawa | Poa / Freshi | OK/Fine |
| Tuma | Peleka | Send/Submit |
| Nakubali | Niamini | I agree |

### Upcountry Tanzania (Dodoma, Mwanza, Arusha area)
| Phrase | Meaning |
|--------|---------|
| "Ndiyo, basi" | Yes, then (= OK submit) |
| "Ah, sawa" | Ah OK |
| "Ndiyo, pamoja" | Yes, together/proceed |

### Uganda/Kenya adjacent (used by cross-border workers)
| Phrase | Origin | Meaning |
|--------|--------|---------|
| "Sawa, proceed" | KE code-switch | OK proceed |
| "Ei, do it" | UG/KE informal | Yes, do it |
| "Wewe tuma" | East Africa | You send it |

---

## AI Behaviour Summary

When in **CONFIRMING** stage and Consumer's message matches ANY pattern in sections 1–5 and 8: → set `action=submit`

When in **COLLECTING** stage and Consumer's message contains an EXPLICIT command from section 1 (wasilisha/tuma/submit/file it/send it): → treat as submission request even without full confirmation step, provided minimum data is present (feedback_type + description non-empty)

When message matches section 6 (anti-patterns) or section 9 (refusal): → do NOT submit, continue or re-collect

When message contains emoji from section 8 in CONFIRMING stage: → set `action=submit`
