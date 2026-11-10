"""Held-out test for smart ledger questions. Written BEFORE app/nlu/query.py existed.

Each case: (sentence, lang, expected)
  expected None -> NOT a smart question: the command must be left exactly as before
  expected dict -> the query spec must contain these keys/values:
     type    debtors_over | total | items | not_paid
     op      ">" or "<"               (debtors_over)
     value   rupee threshold          (debtors_over)
     kind    credit | payment | sale | expense   (total)
     window  today | yesterday | day_before | this_week | last_week | this_month | last_month | days | all
     n       number of days when window == "days"
     customer  saved account name (or None for the whole shop)
     days    "not paid for" length in days (not_paid)
"""
from .hard_test import CUSTOMERS  # noqa: F401

CASES = [
    # ---------------- Punjabi
    ("ਪੰਜ ਹਜ਼ਾਰ ਤੋਂ ਵੱਧ ਕਿਸ ਕਿਸ ਵੱਲ ਬਾਕੀ ਹੈ?", "pa", {"type": "debtors_over", "op": ">", "value": 5000}),
    ("ਕਿਹੜੇ ਗਾਹਕਾਂ ਦਾ ਉਧਾਰ 2000 ਤੋਂ ਉੱਪਰ ਹੈ?", "pa", {"type": "debtors_over", "op": ">", "value": 2000}),
    ("500 ਤੋਂ ਘੱਟ ਕਿਸ ਕਿਸ ਦੇ ਪੈਸੇ ਰਹਿੰਦੇ ਨੇ?", "pa", {"type": "debtors_over", "op": "<", "value": 500}),
    ("ਬਿੱਟੂ ਨੇ ਇਸ ਮਹੀਨੇ ਕਿੰਨਾ ਸਮਾਨ ਲਿਆ?", "pa",
     {"type": "total", "kind": "credit", "window": "this_month", "customer": "ਬਿੱਟੂ"}),
    ("ਕੱਲ੍ਹ ਕਿੰਨਾ ਉਧਾਰ ਗਿਆ?", "pa", {"type": "total", "kind": "credit", "window": "yesterday", "customer": None}),
    ("ਮਹੀਨੇ ਤੋਂ ਕਿਸ ਨੇ ਪੈਸੇ ਨਹੀਂ ਦਿੱਤੇ?", "pa", {"type": "not_paid", "days": 30}),
    ("ਪਿੰਕੀ ਨੇ ਇਸ ਹਫ਼ਤੇ ਕਿੰਨੇ ਪੈਸੇ ਜਮ੍ਹਾ ਕਰਵਾਏ?", "pa",
     {"type": "total", "kind": "payment", "window": "this_week", "customer": "ਪਿੰਕੀ"}),
    ("ਪਿਛਲੇ ਹਫ਼ਤੇ ਕਿੰਨੇ ਪੈਸੇ ਵਾਪਸ ਆਏ?", "pa", {"type": "total", "kind": "payment", "window": "last_week", "customer": None}),
    ("ਪਿਛਲੇ ਮਹੀਨੇ ਕਿੰਨਾ ਖਰਚਾ ਹੋਇਆ?", "pa", {"type": "total", "kind": "expense", "window": "last_month", "customer": None}),
    ("ਜਸਵੀਰ ਨੇ ਹੁਣ ਤੱਕ ਕੁੱਲ ਕਿੰਨਾ ਉਧਾਰ ਲਿਆ?", "pa",
     {"type": "total", "kind": "credit", "window": "all", "customer": "ਜਸਵੀਰ"}),
    ("ਮਾਸਟਰ ਜੀ ਨੇ ਇਸ ਮਹੀਨੇ ਕੀ ਕੀ ਲਿਆ?", "pa", {"type": "items", "window": "this_month", "customer": "ਮਾਸਟਰ ਜੀ"}),
    ("ਦੋ ਹਫ਼ਤਿਆਂ ਤੋਂ ਕਿਹੜੇ ਗਾਹਕ ਪੈਸੇ ਦੇਣ ਨਹੀਂ ਆਏ?", "pa", {"type": "not_paid", "days": 14}),
    ("ਪਿਛਲੇ 10 ਦਿਨਾਂ ਵਿੱਚ ਕਿੰਨੀ ਵਿਕਰੀ ਹੋਈ?", "pa", {"type": "total", "kind": "sale", "window": "days", "n": 10, "customer": None}),
    ("ਪਰਸੋਂ ਕਿੰਨਾ ਉਧਾਰ ਦਿੱਤਾ ਸੀ?", "pa", {"type": "total", "kind": "credit", "window": "day_before", "customer": None}),
    ("ਕੁਲਦੀਪ ਨੇ ਪਿਛਲੇ ਮਹੀਨੇ ਕਿੰਨੇ ਪੈਸੇ ਦਿੱਤੇ?", "pa",
     {"type": "total", "kind": "payment", "window": "last_month", "customer": "ਕੁਲਦੀਪ"}),
    ("ਦਸ ਹਜ਼ਾਰ ਤੋਂ ਜ਼ਿਆਦਾ ਉਧਾਰ ਕਿਸ ਦਾ ਹੈ?", "pa", {"type": "debtors_over", "op": ">", "value": 10000}),
    # ---------------- Hindi
    ("पांच हज़ार से ज़्यादा किस किस पर बाकी है?", "hi", {"type": "debtors_over", "op": ">", "value": 5000}),
    ("किन ग्राहकों का उधार 1000 से ऊपर है?", "hi", {"type": "debtors_over", "op": ">", "value": 1000}),
    ("बिट्टू ने इस महीने कितना सामान लिया?", "hi",
     {"type": "total", "kind": "credit", "window": "this_month", "customer": "ਬਿੱਟੂ"}),
    ("कल कितना उधार गया?", "hi", {"type": "total", "kind": "credit", "window": "yesterday", "customer": None}),
    ("एक महीने से किसने पैसे नहीं दिए?", "hi", {"type": "not_paid", "days": 30}),
    ("पिछले हफ़्ते कितनी बिक्री हुई?", "hi", {"type": "total", "kind": "sale", "window": "last_week", "customer": None}),
    ("जसवीर ने क्या क्या लिया इस हफ़्ते?", "hi", {"type": "items", "window": "this_week", "customer": "ਜਸਵੀਰ"}),
    ("सिमरन ने अब तक कितने पैसे जमा किए?", "hi", {"type": "total", "kind": "payment", "window": "all", "customer": "ਸਿਮਰਨ"}),
    ("इस महीने कितना खर्चा हुआ?", "hi", {"type": "total", "kind": "expense", "window": "this_month", "customer": None}),
    ("200 से कम किस किस के पैसे बाकी हैं?", "hi", {"type": "debtors_over", "op": "<", "value": 200}),
    # ---------------- English / Hinglish
    ("Who owes me more than 5000?", "en", {"type": "debtors_over", "op": ">", "value": 5000}),
    ("Which customers have dues above 3000?", "en", {"type": "debtors_over", "op": ">", "value": 3000}),
    ("How much did Bittu buy this month?", "en",
     {"type": "total", "kind": "credit", "window": "this_month", "customer": "ਬਿੱਟੂ"}),
    ("How much credit went out yesterday?", "en", {"type": "total", "kind": "credit", "window": "yesterday", "customer": None}),
    ("Who hasn't paid in a month?", "en", {"type": "not_paid", "days": 30}),
    ("Who has not paid anything for 15 days?", "en", {"type": "not_paid", "days": 15}),
    ("How much did Pinky pay last week?", "en",
     {"type": "total", "kind": "payment", "window": "last_week", "customer": "ਪਿੰਕੀ"}),
    ("What did Kuldeep take this week?", "en", {"type": "items", "window": "this_week", "customer": "ਕੁਲਦੀਪ"}),
    ("How much did we collect in the last 7 days?", "en",
     {"type": "total", "kind": "payment", "window": "days", "n": 7, "customer": None}),
    ("Udhaar 5000 se upar kis kis ka hai?", "en", {"type": "debtors_over", "op": ">", "value": 5000}),
    ("Bittu ne is mahine kitna saman liya?", "en",
     {"type": "total", "kind": "credit", "window": "this_month", "customer": "ਬਿੱਟੂ"}),
    ("Ek mahine se kisne paise nahi diye?", "en", {"type": "not_paid", "days": 30}),
    # ---------------- NOT smart questions: must behave exactly as before
    ("ਰਮੇਸ਼ ਦੇ ਕਿੰਨੇ ਪੈਸੇ ਬਾਕੀ ਨੇ?", "pa", None),
    ("ਕਿਸ ਕਿਸ ਦੇ ਪੈਸੇ ਬਾਕੀ ਨੇ?", "pa", None),
    ("ਇਸ ਹਫ਼ਤੇ ਦੀ ਵਿਕਰੀ ਦੱਸੋ", "pa", None),
    ("ਅੱਜ ਦਾ ਹਿਸਾਬ ਦੱਸੋ", "pa", None),
    ("ਬਿੱਟੂ ਨੂੰ 500 ਉਧਾਰ ਦਿੱਤਾ", "pa", None),
    ("ਕੁਲਦੀਪ ਨੇ 2000 ਜਮ੍ਹਾ ਕਰਵਾਏ", "pa", None),
    ("ਕੱਲ੍ਹ ਪਿੰਕੀ ਨੂੰ 300 ਦਾ ਸਮਾਨ ਦਿੱਤਾ ਸੀ", "pa", None),
    ("ਕੀ ਬਿੱਟੂ ਨੂੰ ਉਧਾਰ ਦੇਣਾ ਠੀਕ ਹੈ?", "pa", None),
    ("बिट्टू पर कितना बाकी है?", "hi", None),
    ("आज की बिक्री बताओ", "hi", None),
    ("Pinky paid 1000 today", "en", None),
    ("How much does Kuldeep owe?", "en", None),
    ("Who owes me money?", "en", None),
    ("Send a reminder to Bittu", "en", None),
]

# Second blind set: written after query.py was built, phrased differently on purpose, scored once.
CASES_BLIND2 = [
    ("ਕਿਨ੍ਹਾਂ ਗਾਹਕਾਂ ਵੱਲ ਤਿੰਨ ਹਜ਼ਾਰ ਤੋਂ ਜ਼ਿਆਦਾ ਖੜ੍ਹੇ ਨੇ?", "pa", {"type": "debtors_over", "op": ">", "value": 3000}),
    ("ਸਿਮਰਨ ਨੇ ਪਿਛਲੇ ਹਫ਼ਤੇ ਕੀ ਕੀ ਸਮਾਨ ਲਿਆ?", "pa", {"type": "items", "window": "last_week", "customer": "ਸਿਮਰਨ"}),
    ("ਅੱਜ ਕਿੰਨਾ ਖਰਚਾ ਹੋਇਆ ਦੁਕਾਨ ਦਾ?", "pa", {"type": "total", "kind": "expense", "window": "today", "customer": None}),
    ("ਤਿੰਨ ਹਫ਼ਤਿਆਂ ਤੋਂ ਕੌਣ ਕੌਣ ਪੈਸੇ ਨਹੀਂ ਦੇ ਕੇ ਗਿਆ?", "pa", {"type": "not_paid", "days": 21}),
    ("ਗੁਰਪ੍ਰੀਤ ਨੇ ਇਸ ਮਹੀਨੇ ਕਿੰਨੇ ਪੈਸੇ ਭਰੇ?", "pa",
     {"type": "total", "kind": "payment", "window": "this_month", "customer": "ਗੁਰਪ੍ਰੀਤ ਸਿੰਘ"}),
    ("ਪਿਛਲੇ ਤੀਹ ਦਿਨਾਂ ਵਿੱਚ ਕਿੰਨਾ ਉਧਾਰ ਗਿਆ?", "pa", {"type": "total", "kind": "credit", "window": "days", "n": 30, "customer": None}),
    ("सुखविंदर ने पिछले महीने कितना उधार लिया?", "hi",
     {"type": "total", "kind": "credit", "window": "last_month", "customer": "ਸੁਖਵਿੰਦਰ"}),
    ("किस किस ने दो हफ़्ते से कुछ नहीं दिया?", "hi", {"type": "not_paid", "days": 14}),
    ("आज कितने पैसे वापस आए?", "hi", {"type": "total", "kind": "payment", "window": "today", "customer": None}),
    ("कौन से ग्राहक 10000 से ऊपर के कर्ज़दार हैं?", "hi", {"type": "debtors_over", "op": ">", "value": 10000}),
    ("How much did I sell yesterday?", "en", {"type": "total", "kind": "sale", "window": "yesterday", "customer": None}),
    ("Which customers owe less than 1000?", "en", {"type": "debtors_over", "op": "<", "value": 1000}),
    ("How much has Jasvir paid so far?", "en", {"type": "total", "kind": "payment", "window": "all", "customer": "ਜਸਵੀਰ"}),
    ("Who hasn't paid for two weeks?", "en", {"type": "not_paid", "days": 14}),
    ("Kal kitni bikri hui?", "en", {"type": "total", "kind": "sale", "window": "yesterday", "customer": None}),
    ("Master ji ne is hafte kya kya liya?", "en", {"type": "items", "window": "this_week", "customer": "ਮਾਸਟਰ ਜੀ"}),
    # not smart questions
    ("ਸਿਮਰਨ ਵੱਲ ਕਿੰਨੇ ਪੈਸੇ ਨੇ?", "pa", None),
    ("ਅੱਜ 3000 ਦੀ ਵਿਕਰੀ ਹੋਈ", "pa", None),
    ("ਕਿਸ ਦਾ ਉਧਾਰ ਸਭ ਤੋਂ ਵੱਧ ਹੈ?", "pa", None),
    ("किसने सबसे ज़्यादा उधार लिया हुआ है?", "hi", None),
    ("Gurpreet gave 700, write it", "en", None),
    ("Who is the riskiest customer?", "en", None),
]
