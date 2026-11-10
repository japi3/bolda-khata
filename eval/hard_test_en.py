"""Hard held-out ENGLISH / HINGLISH test set (as Prisma en-IN would transcribe it).
Never used for training or model selection. Same format and customers as hard_test.py;
expected customers are the saved (Gurmukhi) account names, which English names must
resolve to across scripts.
"""
from .hard_test import CUSTOMERS  # noqa: F401

CASES = [
    # CREDIT
    ("Okay write it down, Bittu took two kilos of flour and a litre of oil, total 320 rupees.", "CREDIT", 320, "ਬਿੱਟੂ"),
    ("Put 450 on Jasvir's account, he'll pay next week.", "CREDIT", 450, "ਜਸਵੀਰ"),
    ("Master ji took groceries worth 1500 on credit.", "CREDIT", 1500, "ਮਾਸਟਰ ਜੀ"),
    ("Kuldeep ko 600 udhaar diya, likh lo.", "CREDIT", 600, "ਕੁਲਦੀਪ"),
    ("Gurpreet Singh, credit, 275.", "CREDIT", 275, "ਗੁਰਪ੍ਰੀਤ ਸਿੰਘ"),
    ("Add another 150 to Pinky's tab.", "CREDIT", 150, "ਪਿੰਕੀ"),
    ("Sukhwinder ke khate mein gas cylinder ke 1100 daal do.", "CREDIT", 1100, "ਸੁਖਵਿੰਦਰ"),
    ("New customer Lakhvir, gave him 350 on credit.", "CREDIT", 350, "Lakhvir"),
    ("Ramesh took rice for 980, he hasn't paid.", "CREDIT", 980, "ਰਮੇਸ਼ ਕੁਮਾਰ"),
    ("Simran's mother took 5 kg rice for 400, add it to Simran's account.", "CREDIT", 400, "ਸਿਮਰਨ"),
    # PAYMENT
    ("Bittu came and paid 1000.", "PAYMENT", 1000, "ਬਿੱਟੂ"),
    ("Jasvir sent 500 on Google Pay.", "PAYMENT", 500, "ਜਸਵੀਰ"),
    ("Received fifteen hundred from Harpreet Kaur.", "PAYMENT", 1500, "ਹਰਪ੍ਰੀਤ ਕੌਰ"),
    ("Master ji cleared his whole account.", "PAYMENT", None, "ਮਾਸਟਰ ਜੀ"),
    ("Kuldeep finally returned 200.", "PAYMENT", 200, "ਕੁਲਦੀਪ"),
    ("Pinky ne 300 cash de diye.", "PAYMENT", 300, "ਪਿੰਕੀ"),
    ("Got 430 from Gurpreet through UPI.", "PAYMENT", 430, "ਗੁਰਪ੍ਰੀਤ ਸਿੰਘ"),
    ("Sukhwinder deposited 2500, rest next month.", "PAYMENT", 2500, "ਸੁਖਵਿੰਦਰ"),
    ("Ramesh ka payment aa gaya, 700.", "PAYMENT", 700, "ਰਮੇਸ਼ ਕੁਮਾਰ"),
    ("Simran paid back 50 rupees.", "PAYMENT", 50, "ਸਿਮਰਨ"),
    # SALE
    ("A customer bought stuff for 260 and paid cash.", "SALE", 260, None),
    ("Cash sale, three hundred thirty.", "SALE", 330, None),
    ("Sold two dozen eggs for 168, got the money.", "SALE", 168, None),
    ("1200 ka maal becha cash mein.", "SALE", 1200, None),
    # EXPENSE
    ("Paid the electricity bill, 1870.", "EXPENSE", 1870, None),
    ("Gave the helper his salary, 7000.", "EXPENSE", 7000, None),
    ("Shop rent paid, eight thousand.", "EXPENSE", 8000, None),
    ("Spent 650 on fridge repair.", "EXPENSE", 650, None),
    # BALANCE
    ("How much does Bittu owe me?", "BALANCE", None, "ਬਿੱਟੂ"),
    ("What's Kuldeep's balance?", "BALANCE", None, "ਕੁਲਦੀਪ"),
    ("Harpreet ka kitna baaki hai?", "BALANCE", None, "ਹਰਪ੍ਰੀਤ ਕੌਰ"),
    # DEBTORS
    ("Who all still owe me money?", "DEBTORS", None, None),
    ("How much total udhaar is pending?", "DEBTORS", None, None),
    # SUMMARY
    ("How much did I earn today?", "SUMMARY", None, None),
    ("What were the expenses this month?", "SUMMARY", None, None),
    # REMIND
    ("Send Kuldeep a reminder.", "REMIND", None, "ਕੁਲਦੀਪ"),
    ("Bittu ko WhatsApp karo paise ke liye.", "REMIND", None, "ਬਿੱਟੂ"),
    # UNDO
    ("No no, that's wrong, delete it.", "UNDO", None, None),
    # RISK
    ("Bittu wants more credit, should I give it?", "RISK", None, "ਬਿੱਟੂ"),
    ("Can I trust Kuldeep with money?", "RISK", None, "ਕੁਲਦੀਪ"),
    # OTHER
    ("Good morning, how are you?", "OTHER", None, None),
    ("What all can you do?", "OTHER", None, None),
]
