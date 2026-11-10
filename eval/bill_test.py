"""Held-out test for multi-part bills (never used while building app/nlu/bill.py).

Each case: (sentence, lang, total, paid_now, customer)
  total None  -> NOT a bill (a normal single-amount command must be left alone)
  paid_now    -> money received in the same sentence (None if none)
  customer    -> saved account name it should land on, or None for a cash sale
"""
from .hard_test import CUSTOMERS  # noqa: F401

CASES = [
    # ---- Punjabi
    ("ਪਿੰਕੀ ਨੂੰ 3 ਕਿੱਲੋ ਚੌਲ 60 ਰੁਪਏ ਕਿੱਲੋ ਦੇ ਦਿੱਤੇ, ਖਾਤੇ ਵਿੱਚ ਲਿਖੋ", "pa", 180, None, "ਪਿੰਕੀ"),
    ("ਜਸਵੀਰ ਲੈ ਗਿਆ ਦੋ ਲੀਟਰ ਦੁੱਧ 56 ਦਾ ਲੀਟਰ ਤੇ ਇੱਕ ਪੈਕਟ ਬਿਸਕੁਟ 20 ਦਾ, 100 ਦੇ ਗਿਆ", "pa", 132, 100, "ਜਸਵੀਰ"),
    ("ਕੁਲਦੀਪ ਨੇ 700 ਦਾ ਰਾਸ਼ਨ ਲਿਆ, 300 ਨਕਦ ਦਿੱਤੇ, ਬਾਕੀ ਉਧਾਰ", "pa", 700, 300, "ਕੁਲਦੀਪ"),
    ("ਸਿਮਰਨ ਨੂੰ 4 ਦਰਜਨ ਅੰਡੇ 84 ਰੁਪਏ ਦਰਜਨ", "pa", 336, None, "ਸਿਮਰਨ"),
    ("ਦਾਲ 120 ਦੀ, ਚਾਹ ਪੱਤੀ 80 ਦੀ, ਸਾਬਣ 40 ਦਾ, ਸਾਰਾ ਨਕਦ", "pa", 240, None, None),
    ("5 ਪੈਕਟ ਮੈਗੀ 14 ਵਾਲੇ ਵੇਚੇ ਕੈਸ਼", "pa", 70, None, None),
    ("ਮਾਸਟਰ ਜੀ ਨੂੰ ਘਿਓ 550 ਦਾ ਤੇ ਖੰਡ 90 ਦੀ, 1000 ਦੇ ਗਏ", "pa", 640, 1000, "ਮਾਸਟਰ ਜੀ"),
    ("ਬਿੱਟੂ ਨੂੰ 10 ਕਿੱਲੋ ਆਟਾ 35 ਰੁਪਏ ਕਿੱਲੋ ਉਧਾਰ", "pa", 350, None, "ਬਿੱਟੂ"),
    ("ਹਰਪ੍ਰੀਤ ਕੌਰ 2 ਕਿੱਲੋ ਪਿਆਜ਼ 30 ਦੇ ਭਾਅ ਲੈ ਗਈ, ਪੈਸੇ ਬਾਅਦ ਵਿੱਚ", "pa", 60, None, "ਹਰਪ੍ਰੀਤ ਕੌਰ"),
    ("ਰਮੇਸ਼ ਨੇ 400 ਦਾ ਸਮਾਨ ਲਿਆ ਤੇ 400 ਹੀ ਨਕਦ ਦੇ ਗਿਆ", "pa", 400, 400, "ਰਮੇਸ਼ ਕੁਮਾਰ"),
    # ---- Hindi
    ("पिंकी को 3 किलो चीनी 45 रुपये किलो उधार दी", "hi", 135, None, "ਪਿੰਕੀ"),
    ("जसवीर ने 900 का सामान लिया, 500 जमा किए, बाकी खाते में", "hi", 900, 500, "ਜਸਵੀਰ"),
    ("सुखविंदर को 2 लीटर तेल 160 रुपये लीटर और 5 किलो आटा 38 रुपये किलो दिया", "hi", 510, None, "ਸੁਖਵਿੰਦਰ"),
    ("दो दर्जन केले 50 रुपये दर्जन नकद बेचे", "hi", 100, None, None),
    ("कुलदीप चावल 300 का और दाल 150 की ले गया, 200 दे गया", "hi", 450, 200, "ਕੁਲਦੀਪ"),
    ("बिट्टू को 6 पैकेट बिस्कुट 10 वाले दिए", "hi", 60, None, "ਬਿੱਟੂ"),
    ("गुरप्रीत ने 250 का सामान लिया और 500 का नोट दिया", "hi", 250, 500, "ਗੁਰਪ੍ਰੀਤ ਸਿੰਘ"),
    # ---- English / Hinglish
    ("Pinky took 2 kg sugar at 45 per kg and paid 50 cash", "en", 90, 50, "ਪਿੰਕੀ"),
    ("Kuldeep ko 5 kilo atta 40 rupaye kilo diya, 100 nagad liya", "en", 200, 100, "ਕੁਲਦੀਪ"),
    ("Sold 3 packets of biscuits at 10 each and a cold drink for 40, cash", "en", 70, None, None),
    ("Jasvir bought rice for 300 and oil for 180, paid 200", "en", 480, 200, "ਜਸਵੀਰ"),
    ("Simran 4 litre milk 60 rupees litre udhaar", "en", 240, None, "ਸਿਮਰਨ"),
    ("Bittu ne 600 ka saman liya aur 600 cash diye", "en", 600, 600, "ਬਿੱਟੂ"),
    # ---- NOT bills: must behave exactly like before
    ("ਕੁਲਦੀਪ ਨੇ 500 ਦਿੱਤੇ", "pa", None, None, "ਕੁਲਦੀਪ"),
    ("ਬਿੱਟੂ ਨੂੰ 320 ਦਾ ਸਮਾਨ ਉਧਾਰ ਦਿੱਤਾ", "pa", None, None, "ਬਿੱਟੂ"),
    ("ਜਸਵੀਰ ਦੋ ਕਿੱਲੋ ਖੰਡ ਲੈ ਗਿਆ 110 ਰੁਪਏ ਦੀ", "pa", None, None, "ਜਸਵੀਰ"),
    ("600 ਦਾ ਉਧਾਰ ਹੋਰ 150 ਜੋੜ ਦਿਓ", "pa", None, None, None),
    ("बिजली का बिल 1870 भरा", "hi", None, None, None),
    ("Who all owe me more than 5000?", "en", None, None, None),
    ("ਅੱਜ 2 ਕਿੱਲੋ ਖੰਡ ਵਿਕੀ", "pa", None, None, None),
]

# Second blind set: written after the rule fixes above and scored once, with no changes made after.
CASES_BLIND2 = [
    ("ਗੁਰਪ੍ਰੀਤ ਨੂੰ ਡੇਢ ਕਿੱਲੋ ਪਨੀਰ 400 ਰੁਪਏ ਕਿੱਲੋ ਉਧਾਰ", "pa", 600, None, "ਗੁਰਪ੍ਰੀਤ ਸਿੰਘ"),
    ("ਸੁਖਵਿੰਦਰ ਨੇ ਗੈਸ ਸਿਲੰਡਰ 1100 ਦਾ ਲਿਆ ਤੇ 600 ਗੂਗਲ ਪੇ ਕੀਤੇ", "pa", 1100, 600, "ਸੁਖਵਿੰਦਰ"),
    ("ਤਿੰਨ ਕਿੱਲੋ ਆਲੂ 25 ਦਾ ਕਿੱਲੋ ਤੇ ਦੋ ਕਿੱਲੋ ਟਮਾਟਰ 40 ਦਾ ਕਿੱਲੋ, ਨਕਦ", "pa", 155, None, None),
    ("ਪਿੰਕੀ 250 ਦਾ ਸਮਾਨ ਲੈ ਗਈ, 100 ਦੇ ਗਈ", "pa", 250, 100, "ਪਿੰਕੀ"),
    ("हरप्रीत कौर को 2 पैकेट दूध 33 वाले और ब्रेड 45 की दी", "hi", 111, None, "ਹਰਪ੍ਰੀਤ ਕੌਰ"),
    ("रमेश ने 1200 का सामान लिया, 1000 नकद दिए", "hi", 1200, 1000, "ਰਮੇਸ਼ ਕੁਮਾਰ"),
    ("आठ अंडे 7 रुपये वाले नकद बेचे", "hi", 56, None, None),
    ("Master ji took 3 kg dal at 120 per kg on credit", "en", 360, None, "ਮਾਸਟਰ ਜੀ"),
    ("Kuldeep bought soap for 40 and shampoo for 120, gave 200", "en", 160, 200, "ਕੁਲਦੀਪ"),
    ("Simran ko 2 kilo chawal 70 rupaye kilo diya, paise baad mein", "en", 140, None, "ਸਿਮਰਨ"),
    ("ਹਰਪ੍ਰੀਤ ਨੇ 300 ਦਿੱਤੇ", "pa", None, None, "ਹਰਪ੍ਰੀਤ ਕੌਰ"),
    ("बिट्टू को 450 का सामान उधार दिया", "hi", None, None, "ਬਿੱਟੂ"),
]
