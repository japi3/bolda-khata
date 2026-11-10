# ਬੋਲਦਾ ਖਾਤਾ · Bolda Khata

**A bahi khata (credit ledger) that you talk to in Punjabi.** A kirana shopkeeper says
*"ਰਮੇਸ਼ ਨੂੰ 500 ਦਾ ਆਟਾ ਉਧਾਰ ਦਿੱਤਾ"* ("gave Ramesh ₹500 of flour on credit"). The entry is
written, the new balance is read back in a Punjabi voice, and an ML model warns the
shopkeeper if that customer is becoming risky. No typing, no English, no app literacy needed.

Built for the Great Indian AI Internship Challenge on **Gnani AI** models:

| Gnani model | Used for |
|---|---|
| **Prisma v3.0** (STT, `pa-IN` / `hi-IN` / `en-IN`) | Punjabi, Hindi, or English/Hinglish speech → text, with the shop's own customer names sent as `keyterms` (in the matching script) and ITN (`format=transcribe`) so "ਡੇਢ ਸੌ", "डेढ़ सौ" or "fifteen hundred" become digits |
| **Timbre v2.5** (TTS) | Every reply spoken back in Punjabi (Mehuli), Hindi (Bhavna) or English (Trupti); payment-reminder voice notes (Zayan / Vikrant / Shlok) |
| **Evon v3.3 30B** (LLM) | Integrated (JSON extraction + grounded answers) and switched on by setting `EVON_BASE_URL`. Needs an 80 GB GPU, so it is not running in this build; the on-device models below do all the understanding |

## What it does

- **Speak entries**: credit (ਉਧਾਰ), payments (ਜਮ੍ਹਾ, incl. "ਪੂਰਾ ਹਿਸਾਬ" = settle all), cash sales, expenses, back-dated ("ਕੱਲ੍ਹ").
- **Ask questions**: "ਰਮੇਸ਼ ਦੇ ਕਿੰਨੇ ਪੈਸੇ ਬਾਕੀ ਨੇ?" (how much does Ramesh owe?), "ਕਿਸ ਕਿਸ ਦੇ ਪੈਸੇ ਬਾਕੀ ਨੇ?" (who still owes money?), "ਇਸ ਹਫ਼ਤੇ ਦੀ ਵਿਕਰੀ?" (this week's sales?)
- **Ask for advice**: "ਕੀ ਬਿੱਟੂ ਨੂੰ ਉਧਾਰ ਦੇਣਾ ਠੀਕ ਹੈ?" ("is it safe to give Bittu credit?") → trust score, the reasons, and a suggested credit limit.
- **Talks back instead of guessing**: asks "ਕਿੰਨੇ ਪੈਸੇ?" ("how much?") when the amount is missing, "ਕਿਹੜਾ ਗੁਰਪ੍ਰੀਤ?" ("which Gurpreet?")
  when two customers share a name, and "ਜਮ੍ਹਾ ਜਾਂ ਉਧਾਰ?" ("received or credit?") when it is unsure of the direction.
  "ਪਿਛਲੀ ਐਂਟਰੀ ਕੱਟ ਦਿਓ" ("delete the last entry") undoes.
- **Reminders**: a Punjabi voice note for each debtor. The tone (gentle or firm) is chosen by the risk model, and it can be shared to WhatsApp.
- **Insights**: total dues, money at risk, collections expected this week, 30-day cash flow, live model metrics.
- **Three languages**: a ਪੰਜਾਬੀ | हिंदी | English switch in the header changes what you speak (Punjabi, Hindi, or
  English/Hinglish such as "Bittu ko 500 udhaar diya"), the screen text, the spoken replies, the risk reasons and
  the reminders. Names work across scripts: say "बिट्टू" in Hindi or "Bittu" in English and it finds the account
  saved as ਬਿੱਟੂ. Devanagari and Gurmukhi sit in parallel Unicode blocks, so names convert letter by letter
  (with fixes for letters that differ). The shop name can be set separately in English and Hindi. In Punjabi mode, English subtitles can be turned on in Settings.
- On desktop, an *under the hood* panel shows every pipeline stage live, with timings.

## Architecture

```
mic ─► 16 kHz WAV (browser, auto-stops on silence)
     ─► Prisma v3.0 STT (pa-IN / hi-IN / en-IN, keyterms = customer names)
     ─► understanding: MuRIL transformer + MEMM ensemble (~25 ms on CPU)   [Evon 30B if configured]
          └─ deterministic code owns amounts, dates, name→account matching, safety questions
     ─► ledger (SQLite, amounts in paise) ─► risk model rescoring
     ─► reply text (Punjabi + Hindi + English) ─► Timbre TTS ─► speaker
```

### ML components

**1. Language understanding: Punjabi, Hindi, English** (`app/nlu/`): two models trained here, ensembled
- **MuRIL joint model** (`transformer.py`): Google's MuRIL (pretrained on 17 Indian languages,
  incl. Punjabi) fine-tuned on this Mac's GPU (MPS) with two heads: an intent classifier on
  `[CLS]` and a BIO tagger on each word's first sub-word (names, items). The word embeddings
  (~150M of 237M parameters) are frozen; ~6 min per training run.
- **MEMM model** (`model.py`): per-token maximum-entropy tagger with beam-search Viterbi
  decoding, plus a masked TF-IDF intent classifier with a Punjabi semantic-cue lexicon
  (ਭਰੋਸਾ/ਯਕੀਨ/ਖਤਰਾ, "trust/confidence/danger", share one feature). ~3 ms.
- **Ensemble** (`ensemble.py`): intent = 0.65 × MuRIL + 0.35 × MEMM probabilities; names and items
  from MuRIL. MuRIL finds names far better; the MEMM generalises intent better to new
  phrasings, so together they beat both. The weight was chosen on the dev set.
- **Safety rule**: credit and payment move money in opposite directions, so if the model
  gives the other direction more than 25% probability, the app asks instead of writing.
- **Deterministic layer**: Punjabi number words (ਸਾਢੇ ਤਿੰਨ ਸੌ = 350, ਪੌਣੇ ਦੋ ਸੌ = 175, ਢਾਈ ਹਜ਼ਾਰ = 2500),
  Hindi number words (डेढ़ सौ = 150, साढ़े तीन सौ = 350, ढाई हज़ार = 2500),
  English numbers ("fifteen hundred", "one fifty" = 150, "one hundred and fifty"), quantity vs. price, dates,
  and matching a spoken name to an account by spelling *and* by a script-independent sound key
  (Bittu = Bittoo = बिट्टू = ਬਿੱਟੂ), with ambiguity detection.
- **Training data**: 22.6k synthetic utterances from 531 hand-written templates: 294 Punjabi, 133
  English/Hinglish (`datagen_en.py`) and 104 Hindi (`datagen_hi.py`), with procedurally generated Punjabi names
  (romanised for English, converted to Devanagari for Hindi), plus augmentation: English loanwords in Latin script
  as Prisma writes them ("entry", "Google Pay"), filler words, and dropped function words.

**2. "Did I hear that right?" safeguards** (`app/repeat_detector.py`, `app/audio_quality.py`)

A wrong ledger entry costs real money, so before writing anything the app checks three things and
reads the entry back for a one-tap ✓ (or a spoken "ਹਾਂ") when in doubt:
- **Misheard-audio detector**: logistic regression over a blind SNR estimate of the recording
  (frame-energy percentiles, ignoring digital silence) plus the language model's confidence, margin
  and speaking rate. The threshold minimises 3 × (wrong entries saved) + (correct commands questioned).
  (The ratio was first fixed at 5; after the bilingual retrain, 3 was at least as good in every condition,
  so I switched. That choice was made after seeing cross-validated results.) It only acts on **loud**
  recordings (blind SNR below 12 dB, the same cut-off as the "hold the phone closer" hint), and only in
  Punjabi mode, since it was calibrated on Punjabi recordings. When the background is very loud it also says to hold the phone closer,
  and the recorder warns live ("ਰੌਲਾ ਜ਼ਿਆਦਾ ਹੈ", "it's too noisy") before you speak.
- **Credit vs payment**: asks "ਜਮ੍ਹਾ ਜਾਂ ਉਧਾਰ?" ("received or credit?") if the other direction gets > 25% probability.
- **Several amounts** in one sentence ("600 … ਹੋਰ 150", "600 … 150 more") → asks which one, instead of guessing or adding them.
- **Cut-off start**: a sentence can't begin with ਨੇ / ਨੂੰ / ने / को (they need a name in front) or with a bare verb
  ("paid 500…", "ਆਇਆ ਸੀ…"). That means the first word, usually the name, was lost, so the app says
  "I didn't catch the beginning" and asks which customer, or reads the entry back before writing.
- **New account**: before creating a customer that doesn't exist yet, it reads back "this opens a new account, is that right?"
  (Real recording: "ਵਿਕਰੀ" (sale) was heard as "Vicky Vicky".)
- **Credit is never a cash sale**: a sentence with ਉਧਾਰ / उधार / udhaar and no cash word can't be booked as a cash sale.
- All of these live in one function (`actions.precheck`) that the app and every evaluation share, so the reports
  measure exactly what the app does.
- Leading silence: the app adds 0.4 s of silence before sending audio, because Prisma tends to drop a first
  word that starts at the very first instant.

**3. Credit-risk model** (`app/ml/`)
- Real kirana khata data is not public, so `simulate.py` generates 9,000 customers from
  interpretable latent traits: reliability, visit rate, ticket size, settlement cycle, partial
  payment, and *financial shocks* (stops paying while still borrowing).
- 13 behavioural features (FIFO-matched age of unpaid credit, repayment speed, on-time rate,
  recency, dues ÷ monthly repayment capacity, credit trend…) are computed **identically** from the live ledger.
- Label: fails to repay ≥ 50% of the dues within the next 45 days.
- Gradient boosting with isotonic calibration, so *trust = 100 × (1 − P(default))* is a real probability.
- Explanations: counterfactual attribution. Each feature is swapped for a typical reliable
  customer's value and the drop in risk is measured; the top drivers become Punjabi reasons.

## Results

### Evaluation protocol
- **Dev set** = sentence templates held out from training (25% per intent). Every modelling
  choice (MuRIL setup, ensemble weight) was made here. See `models/dev_sweep.json`.
- **Hard test set** = `eval/hard_test.py`: 122 hand-written commands that are messier than the
  templates (filler words, Latin-script loanwords, run-on sentences, quantity + price, new names).
  Never used for training or model selection.
- **Voice**: each hard-set command is spoken by Timbre (alternating female/male Punjabi voices),
  optionally mixed with shop noise (background chatter built from other speech clips, plus
  rumble), and transcribed by Prisma. All models are scored on the same cached transcripts.

### Hard test set (122 commands), fully correct = intent + amount + customer all right

| Condition | Prisma char. error | MEMM | MuRIL | **Ensemble (shipped)** |
|---|---|---|---|---|
| Text (perfect transcript) | – | 95.1% | **96.7%** | **96.7%** |
| Voice, clean | 8.2% | 91.8% | **96.7%** | **96.7%** |
| Voice, busy shop (8 dB SNR) | 8.2% | 90.2% | **95.9%** | **95.9%** |
| Voice, chatter as loud as the speaker (0 dB) | 47.5% | 46.7% | 49.2% | **50.8%** |

(Models trained on all three languages. History of the ensemble on this set: Punjabi only 95.9 / 95.1 / 93.4 / 48.4;
+ English 98.4 / 96.7 / 95.1 / 47.5; + Hindi 96.7 / 96.7 / 95.9 / 50.8. So adding languages has not hurt
Punjabi beyond a command or two either way.)

### English / Hinglish hard test set (42 commands, `eval/hard_test_en.py`)

| Condition | MEMM | MuRIL | **Ensemble** |
|---|---|---|---|
| Text | 95.2% | 100% | **100%** |
| Voice (Timbre English voices → Prisma `en-IN`), clean | 95.2% | 100% | **100%** |
| Voice, busy shop (8 dB) | 92.9% | 100% | **100%** |

Before any English training, the ensemble scored 78.6% on this set (text).

### Hindi hard test set (42 commands, `eval/hard_test_hi.py`)

| Condition | MEMM | MuRIL | **Ensemble** |
|---|---|---|---|
| Text | 92.9% | 100% | **100%** |
| Voice (Timbre Hindi voices → Prisma `hi-IN`), clean | 90.5% | 100% | **100%** |
| Voice, busy shop (8 dB) | 90.5% | 100% | **100%** |

Before any Hindi training, the ensemble already scored 95.2% (Hindi shares much vocabulary with Punjabi,
and MuRIL was pretrained on Hindi). One fix, adding Hindi "settle the whole account" words (सारा, पूरा, साफ),
came from a mistake seen on this test set, so it is not fully blind. Both 42-command sets are small:
read 100% as "works well", not "perfect".

- Customer identified correctly (8 dB noise, Punjabi): **ensemble 100%**.
- Credit/payment confirmation rule (fixed in advance; measured here, not tuned): with clean
  and 8 dB voice it caught all 3 wrong-direction entries and never fired when the model was right
  (3 questions out of 46 credit/payment commands). At 0 dB, 3 of 40 still got through.
- **Safeguards together** (5-fold cross-validation grouped by sentence, ledger writes only):

  | Condition | Wrong entries saved, no safeguards | Rules only | Detector everywhere | **Detector on loud audio only (shipped)** | Correct commands questioned (shipped) |
  |---|---|---|---|---|---|
  | Clean voice | 2 | 2 | 2 | **2** | 1 of ~68 (was 5) |
  | Busy shop (8 dB) | 3 | 3 | 3 | **3** | 0 of ~67 (was 10) |
  | Very loud (0 dB) | 40 | 31 | 9 | **15** | 22 (was 26) |

  Limiting the detector to loud recordings removes the pointless interruptions in normal and busy-shop
  audio. The cost: 6 more wrong entries get through in very loud noise, where some recordings still
  measure above the 12 dB cut-off.

  With the stronger model, few mistakes are left in clean and busy-shop audio, and those are
  confidently misheard numbers that no detector catches (the spoken read-back and undo cover them). The
  detector's value is in loud noise. (The first, weaker model had 6 / 8 / 40 wrong entries without
  safeguards and 1 / 2 / 6 with them.) Single-signal baselines are in `models/repeat_report.json`.
  Caveat: the detector is trained on Timbre voices and synthetic noise. Real microphones, and the
  browser's own noise suppression, will shift the audio features, so it should be recalibrated with real recordings.
- Before this round of work, the original model scored 89.3% on the hard text set; better
  training data alone took it to 95.1%.
- Dev set (unseen templates): intent accuracy MEMM 93.5%, MuRIL 81.7%, ensemble 94.9%;
  name/item F1 0.936 / 0.967 / 0.961.
- Risk model AUC (held-out simulated customers): **0.831**, against 0.806 for the shopkeeper rule
  "oldest dues first" and 0.825 for logistic regression.

**Honest caveats**
- With 122 commands, one command is worth 0.8 points, so most gaps between the models are within noise.
  The clearest gain from the ensemble is customer identification.
- I wrote both the training templates and the hard test set myself. The test set is messier on
  purpose, but it is not real shopkeeper speech; I also saw the original model's mistakes on it before improving
  the training data (the improvements were general, not copies of test sentences).
- The voices are synthetic (Timbre). Prisma is robust to moderate shop noise (97 of 122 transcripts unchanged
  at 8 dB) but breaks down when chatter is as loud as the speaker. The remaining errors at 8 dB are mostly misheard
  numbers, which no language model can fix; the spoken read-back and one-tap undo cover them.
- The risk model is trained on simulated behaviour, so its absolute numbers need real data before production.

## Real-voice testing

### First real recordings (20, one speaker, quiet room, read from a guide, recorded on a phone)

| | Before ask-back rules | After |
|---|---|---|
| Understood correctly | 11 / 20 | 11 / 20 |
| **Wrong and acted on without asking** | **9** | **3** |
| Misheard, but the app asked back (safe) | 0 | 6 |
| Correct, but asked anyway | 0 | 1 |

Real speech is much harder than the synthetic tests (55% understood vs 95%+). The main cause was the
first word, usually the customer's name, getting lost: the speaker started before the recorder did, or
Prisma dropped a word at the very start. The 3 remaining silent errors are Prisma mishearings with no
warning sign (उधार heard as "धार", 260 heard as 226, 1870 heard as 870). The spoken read-back and undo cover
those. On the synthetic test sets, the new questions add about one extra tap per 20–25 commands, mostly when
opening a new account. A Hindi bug found along the way: "दो" means both "two" and "give" ("चढ़ा दो"); a lone दो
is now read as the verb unless a unit or "rupees" follows.

### How to record

Every number above comes from synthetic voices. To measure the app on **real people**, open
**Settings → Voice testing** (ਆਵਾਜ਼ ਟੈਸਟ):

- Pick a mode. **Say it your way** shows only the situation ("Bittu took ₹320 of goods on credit") and
  the speaker uses their own words: the honest test. **Read this** shows the exact sentence.
- Tag where you are (quiet / busy / very noisy) and who is speaking (name or initials).
- Tap the mic and speak. The app transcribes with Prisma, interprets the command exactly as it would
  for real, and shows ✓ or ✗ with what it heard. **Nothing is written to the ledger.**
- The language switch picks the language (Punjabi, Hindi, English). Prompts come from the hard test sets,
  in random order. Any recording can be deleted from the result line.

Recordings stay on this computer (`data/real/`, excluded from git) and each one costs one Gnani STT call.
**Get consent** from anyone you record.

A good session: 3–5 people, about 20 commands each, mostly "say it your way", some in a quiet room and some
with real background noise (a busy shop, a TV, a market). Then:

```bash
.venv/bin/python scripts/eval_real.py --errors
```

It re-scores every recording with the current models (no API calls), broken down by language, noise
level, mode and speaker. It lists every misunderstood command and how many wrong entries the safeguards
would have let through. The overall figure also appears on the Insights screen. Once there are ~100 real
recordings, the misheard-audio detector should be recalibrated on them, and the mistakes can feed new
training phrasings.

## Run it

```bash
cd bahi-khata
python3 -m venv .venv
.venv/bin/pip install fastapi "uvicorn[standard]" python-multipart httpx scikit-learn numpy python-dotenv joblib torch transformers
echo "GNANI_API_KEY=<your key>" > .env
.venv/bin/python scripts/train_nlu.py                               # MEMM, ~10 s
HF_HUB_DISABLE_XET=1 .venv/bin/python scripts/train_transformer.py  # MuRIL, ~6 min on an M-series Mac (downloads ~900 MB once)
.venv/bin/python scripts/train_risk.py                              # risk model, ~4 s
.venv/bin/python scripts/seed_demo.py --reset                       # optional 90-day demo shop
HF_HUB_DISABLE_XET=1 .venv/bin/uvicorn app.main:app --port 8000
```
Open http://localhost:8000, tap the mic (or press Space) and speak Punjabi. The app works
without the MuRIL weights too; it falls back to the MEMM alone.

### On your phone

A phone's microphone only works over HTTPS, so the app is reached through a free Cloudflare quick
tunnel (no account, no card). Your Mac stays the server and must be on and online while you use it.

```bash
brew install cloudflared                 # once
.venv/bin/python scripts/phone.py        # starts the app + link, prints a QR code
```

1. Scan the QR code with the phone camera, or open the `https://….trycloudflare.com` link.
2. Enter the **PIN** (`APP_PIN` in `.env`; change it there and restart). Wrong PINs are rate-limited
   (5 per 10 minutes per device), and a correct PIN keeps the phone signed in for 30 days.
3. Allow the microphone.
4. Install it: Android Chrome → menu ⋮ → **Install app**; iPhone Safari → Share → **Add to Home Screen**.

The link is different every time and stops when you press Ctrl+C. The script refuses to run without
a PIN, because anyone with the link reaches the login screen. The app is installable (manifest,
icons, service worker), opens without a connection (showing an offline banner), and unlocks audio
on the first tap so iPhones play the spoken replies.

Re-run the evaluations:
```bash
.venv/bin/python scripts/dev_sweep.py                  # model selection on the dev set (~25 min)
.venv/bin/python scripts/eval_voice.py --transcribe    # speak + noise + Prisma (Gnani API calls)
.venv/bin/python scripts/final_report.py               # Punjabi hard-set table -> models/nlu_comparison.json
.venv/bin/python scripts/eval_voice_en.py [--lang hi] --transcribe   # English (or Hindi) voice test (Gnani API calls)
.venv/bin/python scripts/eval_voice_en.py [--lang hi] --model ensemble  # score it
```

**Evon (optional)**: `deploy/evon_modal.py` serves Evon through vLLM on a Modal H100. Modal requires a payment method for any GPU,
so this build does not use it. Point `EVON_BASE_URL` / `EVON_API_KEY` at any OpenAI-compatible
Evon server and the app uses it automatically, falling back to the on-device models if Evon is slow or down.
