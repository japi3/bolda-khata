"""Held-out test for stock tracking. Written BEFORE app/stock.py existed.

PARSE: (sentence, lang, expected)
  expected None -> not a stock command/question: everything must behave as before
  {"type": "stock_left", "item": key}             how much of an item is left
  {"type": "stock_low"}                            what is running low / what to order
  {"type": "stock_all"}                            show the whole stock
  {"type": "stock_set", "items": [(key, qty, unit)]}   counted stock (absolute), units canonical:
        kg (grams converted), l (ml converted), pc (dozens x12, plain counts), pkt, sack, box, crate, btl

SCENARIO: entries said one after another on an empty ledger, then the stock that must result.
"""
PARSE = [
    # ---- how much is left
    ("ਆਟੇ ਦੀਆਂ ਕਿੰਨੀਆਂ ਬੋਰੀਆਂ ਬਚੀਆਂ?", "pa", {"type": "stock_left", "item": "atta"}),
    ("ਖੰਡ ਕਿੰਨੀ ਪਈ ਹੈ?", "pa", {"type": "stock_left", "item": "sugar"}),
    ("ਸਟਾਕ ਵਿੱਚ ਕਿੰਨਾ ਤੇਲ ਹੈ?", "pa", {"type": "stock_left", "item": "oil"}),
    ("चीनी कितनी बची है?", "hi", {"type": "stock_left", "item": "sugar"}),
    ("चावल का स्टॉक कितना है?", "hi", {"type": "stock_left", "item": "rice"}),
    ("How much sugar is left?", "en", {"type": "stock_left", "item": "sugar"}),
    ("How many packets of Maggi do we have?", "en", {"type": "stock_left", "item": "maggi"}),
    ("Atta kitna bacha hai?", "en", {"type": "stock_left", "item": "atta"}),
    # ---- running low
    ("ਕਿਹੜਾ ਮਾਲ ਮੁੱਕਣ ਵਾਲਾ ਹੈ?", "pa", {"type": "stock_low"}),
    ("ਕੀ ਕੀ ਮੰਗਵਾਉਣਾ ਪੈਣਾ?", "pa", {"type": "stock_low"}),
    ("क्या क्या खत्म होने वाला है?", "hi", {"type": "stock_low"}),
    ("What is running low?", "en", {"type": "stock_low"}),
    ("What do I need to reorder?", "en", {"type": "stock_low"}),
    # ---- whole stock
    ("ਸਟਾਕ ਦੱਸੋ", "pa", {"type": "stock_all"}),
    ("पूरा स्टॉक दिखाओ", "hi", {"type": "stock_all"}),
    ("Show me the stock", "en", {"type": "stock_all"}),
    # ---- counted stock
    ("ਆਟੇ ਦਾ ਸਟਾਕ 20 ਬੋਰੀਆਂ ਹੈ", "pa", {"type": "stock_set", "items": [("atta", 20, "sack")]}),
    ("ਸਟਾਕ ਵਿੱਚ 50 ਕਿੱਲੋ ਖੰਡ ਹੈ", "pa", {"type": "stock_set", "items": [("sugar", 50, "kg")]}),
    ("ਸਟਾਕ: ਤੇਲ 12 ਬੋਤਲਾਂ, ਘਿਓ 5 ਕਿੱਲੋ", "pa", {"type": "stock_set", "items": [("oil", 12, "btl"), ("ghee", 5, "kg")]}),
    ("चीनी का स्टॉक 30 किलो है", "hi", {"type": "stock_set", "items": [("sugar", 30, "kg")]}),
    ("स्टॉक में 10 दर्जन अंडे हैं", "hi", {"type": "stock_set", "items": [("eggs", 120, "pc")]}),
    ("Stock of rice is 40 kg", "en", {"type": "stock_set", "items": [("rice", 40, "kg")]}),
    ("We have 24 packets of Maggi in stock", "en", {"type": "stock_set", "items": [("maggi", 24, "pkt")]}),
    # ---- NOT stock: unchanged behaviour
    ("ਬਿੱਟੂ ਨੂੰ 2 ਕਿੱਲੋ ਖੰਡ ਉਧਾਰ ਦਿੱਤੀ, 90 ਰੁਪਏ", "pa", None),
    ("ਥੋਕ ਤੋਂ 10 ਬੋਰੀਆਂ ਆਟਾ 800 ਰੁਪਏ ਬੋਰੀ ਮੰਗਵਾਇਆ", "pa", None),
    ("ਰਮੇਸ਼ ਦੇ ਕਿੰਨੇ ਪੈਸੇ ਬਾਕੀ ਨੇ?", "pa", None),
    ("ਕਿਸ ਕਿਸ ਦੇ ਪੈਸੇ ਬਾਕੀ ਨੇ?", "pa", None),
    ("ਅੱਜ ਦੀ ਵਿਕਰੀ ਦੱਸੋ", "pa", None),
    ("ਬਿੱਟੂ ਨੇ ਇਸ ਮਹੀਨੇ ਕਿੰਨਾ ਸਮਾਨ ਲਿਆ?", "pa", None),
    ("दो दर्जन केले 50 रुपये दर्जन नकद बेचे", "hi", None),
    ("Who owes me more than 5000?", "en", None),
    ("Pinky paid 1000 today", "en", None),
]

# Entries in order on an empty ledger -> stock afterwards: {item: {unit: qty}}
SCENARIO = [
    "ਥੋਕ ਤੋਂ 10 ਬੋਰੀਆਂ ਆਟਾ 800 ਰੁਪਏ ਬੋਰੀ ਮੰਗਵਾਇਆ",           # atta +10 sack
    "ਖੰਡ ਦਾ ਸਟਾਕ 50 ਕਿੱਲੋ ਹੈ",                              # sugar = 50 kg
    "ਪਿੰਕੀ ਨੂੰ 3 ਕਿੱਲੋ ਖੰਡ 45 ਰੁਪਏ ਕਿੱਲੋ ਉਧਾਰ",               # sugar -3 kg (credit bill)
    "2 ਕਿੱਲੋ ਖੰਡ 90 ਰੁਪਏ ਦੀ ਨਕਦ ਵੇਚੀ",                       # sugar -2 kg (cash sale)
    "ਬਿੱਟੂ 2 ਬੋਰੀਆਂ ਆਟਾ 850 ਰੁਪਏ ਬੋਰੀ ਲੈ ਗਿਆ",                # atta -2 sack (credit bill)
    "bought 24 packets of maggi from the wholesaler at 12 each",   # maggi +24 pkt
    "Sold 5 packets of Maggi at 14 each, cash",                  # maggi -5 pkt
    "ਪਿਛਲੀ ਐਂਟਰੀ ਕੱਟ ਦਿਓ",                                    # undo the Maggi sale: maggi back to 24
    "ਸਿਮਰਨ ਨੂੰ ਅੱਧਾ ਕਿੱਲੋ ਚਾਹ ਪੱਤੀ 300 ਦੀ ਉਧਾਰ",               # tea never stocked: not tracked
]
SCENARIO_STOCK = {"atta": {"sack": 8}, "sugar": {"kg": 45}, "maggi": {"pkt": 24}}

# Second blind set: written after app/stock.py was built, different wording, scored once.
PARSE_BLIND2 = [
    ("ਘਿਓ ਕਿੰਨਾ ਰਹਿ ਗਿਆ?", "pa", {"type": "stock_left", "item": "ghee"}),
    ("ਮੈਗੀ ਦੇ ਕਿੰਨੇ ਪੈਕਟ ਪਏ ਨੇ?", "pa", {"type": "stock_left", "item": "maggi"}),
    ("ਕਿਹੜੀਆਂ ਚੀਜ਼ਾਂ ਖਤਮ ਹੋਣ ਵਾਲੀਆਂ ਨੇ?", "pa", {"type": "stock_low"}),
    ("ਦੁਕਾਨ ਦਾ ਸਟਾਕ ਕਿੰਨਾ ਹੈ?", "pa", {"type": "stock_all"}),
    ("ਸਟਾਕ ਵਿੱਚ 500 ਗ੍ਰਾਮ ਹਲਦੀ ਹੈ", "pa", {"type": "stock_set", "items": [("haldi", 0.5, "kg")]}),
    ("अंडे कितने बचे हैं?", "hi", {"type": "stock_left", "item": "eggs"}),
    ("कौन सा सामान मंगवाना है?", "hi", {"type": "stock_low"}),
    ("स्टॉक: आटा 15 बोरी, चावल 60 किलो", "hi", {"type": "stock_set", "items": [("atta", 15, "sack"), ("rice", 60, "kg")]}),
    ("How much oil is in stock?", "en", {"type": "stock_left", "item": "oil"}),
    ("Which items are finishing?", "en", {"type": "stock_low"}),
    ("Stock count: 3 dozen eggs", "en", {"type": "stock_set", "items": [("eggs", 36, "pc")]}),
    ("Chini ka stock kitna hai?", "en", {"type": "stock_left", "item": "sugar"}),
    # not stock
    ("ਪਿੰਕੀ ਨੇ ਇਸ ਹਫ਼ਤੇ ਕਿੰਨੀ ਖੰਡ ਲਈ?", "pa", None),
    ("ਹਫ਼ਤੇ ਵਿੱਚ ਕਿੰਨਾ ਮਾਲ ਵਿਕਿਆ?", "pa", None),
    ("कितने ग्राहकों का पैसा बाकी है?", "hi", None),
    ("Sold 2 kg sugar for 90 cash", "en", None),
]

SCENARIO2 = [
    "ਸਟਾਕ: ਘਿਓ 10 ਕਿੱਲੋ, ਅੰਡੇ 5 ਦਰਜਨ",          # ghee = 10 kg, eggs = 60 pc
    "ਪਿੰਕੀ ਨੂੰ 2 ਦਰਜਨ ਅੰਡੇ 84 ਰੁਪਏ ਦਰਜਨ ਉਧਾਰ",     # eggs -24 -> 36
    "ਕੁਲਦੀਪ ਨੂੰ 8 ਕਿੱਲੋ ਘਿਓ 550 ਰੁਪਏ ਕਿੱਲੋ ਉਧਾਰ",   # ghee -8 -> 2 kg: running low (<= 20% of 10)
    "ਸਟਾਕ ਵਿੱਚ 40 ਕਿੱਲੋ ਚੌਲ ਹਨ",                  # rice = 40 kg
    "ਪਿਛਲੀ ਐਂਟਰੀ ਕੱਟ ਦਿਓ",                        # undo the rice count
    "500 ਗ੍ਰਾਮ ਘਿਓ 280 ਰੁਪਏ ਦਾ ਨਕਦ ਵੇਚਿਆ",          # ghee -0.5 -> 1.5 kg
]
SCENARIO2_STOCK = {"ghee": {"kg": 1.5}, "eggs": {"pc": 36}}
SCENARIO2_LOW = ["ghee"]
