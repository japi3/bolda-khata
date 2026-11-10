# ਬੋਲਦਾ ਖਾਤਾ · Bolda Khata: the bahi khata that listens and talks back

**Solution pitch · Great Indian AI Internship Challenge (Gnani AI)**

### The problem
India's kirana shops run on *udhaar* (credit), written in a paper **bahi khata**. Entries are slow to write, easy to lose and hard to total. Collecting dues is awkward, and the shopkeeper finds out a customer is risky only after the money is gone. Ledger apps exist, but they expect typing in English and form-filling, which doesn't suit a busy counter or a shopkeeper who thinks in Punjabi.

### Our solution
A **voice-first ledger**. The shopkeeper just speaks: *"ਬਿੱਟੂ ਨੂੰ ਤਿੰਨ ਸੌ ਦਾ ਸਮਾਨ ਉਧਾਰ ਦਿੱਤਾ"* ("gave Bittu ₹300 of goods on credit"). The entry is written, and the new balance is spoken back. It works in **Punjabi, Hindi and English/Hinglish**, on any phone, as an installable web app.

- **Whole bills in one sentence:** quantity × rate, several items, cash paid now, and "give change or keep as advance?"
- **Ask the ledger:** "who hasn't paid in a month?", "who owes more than ₹5,000?", "how much credit went out yesterday?"
- **Credit-risk ML:** a trust score per customer with plain reasons and a safe credit limit. It warns while you're giving credit.
- **Voice reminders:** a polite Punjabi/Hindi/English voice note, ready for WhatsApp.
- **Stock:** sales and restocking keep stock up to date, with "running low" alerts.
- **Built for real shops:** it asks instead of guessing, and one tap undoes a mistake. With no signal, entries wait on the phone and send themselves later. It is PIN-locked for use on a phone.

### How it uses Gnani
**Prisma v3.0** turns speech into text, given the shop's own customer names as keyterms. **Timbre v2.5** speaks every reply and reminder. **Evon 30B** is integrated and switches on when a GPU is available. Between them, a fine-tuned **MuRIL + MEMM** model understands the sentence. Deterministic code owns the money: amounts, dates, bills and name matching.

### Results (honest numbers, details in README)
- **Hard test set (122 Punjabi commands):** 96.7% fully correct, and 95.9% in a noisy shop. Hindi and English score 100% on 42 commands each.
- **20 real recordings of my own voice:** 3 were written wrong without asking (all numbers Prisma misheard). The rest were right, or the app asked first.
- **Smart questions:** 16/16 answers right. **Bills and stock:** blind first runs are reported alongside the fixed scores.
- **Risk model AUC:** 0.831, against 0.806 for the shopkeeper's rule "oldest dues first".

### Impact and next steps
It saves time at the counter, cuts lost credit, and leads to earlier, polite collection. No literacy or English needed. Next: field trials with real shops and voices, running Evon on a GPU, and UPI payment links in reminders.

**Code:** github.com/japi3/bolda-khata (MIT) · **Demo video:** *[add your link]*
