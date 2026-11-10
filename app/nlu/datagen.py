"""Synthetic training data for the on-device Punjabi khata NLU.

Each sample = (tokens, BIO slot tags, intent). Templates are written the way a
Punjabi shopkeeper actually talks (including English loanwords in Gurmukhi,
e.g. ਪੇਮੈਂਟ / ਐਂਟਰੀ / ਰਿਮਾਈਂਡਰ). Names and items are sampled from large pools,
including procedurally generated Punjabi names, so the tagger learns *context*
("X ਨੂੰ ... ਉਧਾਰ") rather than memorising a fixed list.

Placeholders: {N} name, {A} amount, {I} item, {Q} quantity, {D} day word, {E} expense head.
"""
import random

from .punjabi import normalize

INTENTS = ["CREDIT", "PAYMENT", "SALE", "EXPENSE", "BALANCE", "DEBTORS",
           "SUMMARY", "REMIND", "UNDO", "RISK", "OTHER"]

T = {
"CREDIT": [
    "{N} ਨੂੰ ਸਮਾਨ ਦੇ ਦਿੱਤਾ {A} ਦਾ ਬਾਅਦ ਵਿੱਚ ਦੇਊ", "{N} ਦੇ ਖਾਤੇ ਵਿੱਚ {I} {A}",
    "{N} ਨੂੰ {A} ਦਾ {I} ਉਧਾਰ ਦਿੱਤਾ", "{N} ਦੇ ਖਾਤੇ ਵਿੱਚ {A} ਲਿਖ ਦਿਓ", "{N} {Q} {I} ਲੈ ਗਿਆ {A} ਦਾ",
    "{N} ਨੇ {A} ਦਾ ਸਮਾਨ ਉਧਾਰ ਲਿਆ", "{D} {N} ਨੂੰ {A} ਉਧਾਰ", "{N} ਦੇ ਨਾਮ {A} ਚੜ੍ਹਾ ਦਿਓ",
    "{N} ਦੇ ਖਾਤੇ {A} ਪਾ ਦਿਓ", "{I} {A} ਦਾ {N} ਦੇ ਖਾਤੇ ਵਿੱਚ", "{N} ਲਈ {A} ਦਾ {I} ਉਧਾਰ ਲਿਖੋ",
    "{N} {A} ਦਾ ਸਮਾਨ ਲੈ ਗਈ ਪੈਸੇ ਬਾਅਦ ਵਿੱਚ ਦੇਊਗੀ", "{N} ਨੂੰ {Q} {I} ਦਿੱਤਾ {A} ਬਾਕੀ",
    "{N} ਦਾ {A} ਉਧਾਰ ਜੋੜ ਦਿਓ", "ਉਧਾਰ {N} {A}", "{N} ਦੇ ਖਾਤੇ ਵਿੱਚ {A} ਦੀ ਐਂਟਰੀ ਕਰੋ",
    "{N} ਨੂੰ {A} ਦਾ ਸਮਾਨ ਦਿੱਤਾ ਪੈਸੇ ਨਹੀਂ ਦਿੱਤੇ", "{D} {N} {Q} {I} ਲੈ ਕੇ ਗਿਆ {A} ਦਾ ਉਧਾਰ",
    "{N} ਨੇ {I} ਲਿਆ {A} ਖਾਤੇ ਵਿੱਚ ਲਿਖ ਲਓ", "{N} ਨੂੰ {A} ਉਧਾਰ ਦੇ ਦਿੱਤੇ", "{N} ਦੇ ਸਿਰ {A} ਹੋਰ ਚੜ੍ਹ ਗਏ",
    "{N} ਦੇ ਖਾਤੇ ਵਿੱਚ {Q} {I} {A} ਦਾ ਲਿਖੋ", "{N} ਵਾਸਤੇ {A} ਉਧਾਰ ਪਾਓ", "{N} ਨੂੰ {I} ਦਿੱਤਾ ਉਧਾਰ {A}",
    "{N} ਦੀ ਉਧਾਰੀ ਵਿੱਚ {A} ਜੋੜੋ", "{N} ਨੂੰ {A} ਕੈਸ਼ ਉਧਾਰ ਦਿੱਤਾ",
],
"PAYMENT": [
    "{N} ਸਾਰੇ ਪੈਸੇ ਮੋੜ ਗਿਆ", "{N} ਨੇ ਹਿਸਾਬ ਕਰ ਦਿੱਤਾ {A}", "{N} ਨੇ ਖਾਤਾ ਸਾਫ਼ ਕਰ ਦਿੱਤਾ", "{N} ਤੋਂ {A} ਆ ਗਏ",
    "{N} ਨੇ {A} ਦੇ ਦਿੱਤੇ", "{N} {A} ਜਮ੍ਹਾ ਕਰਵਾ ਗਿਆ", "{N} ਤੋਂ {A} ਮਿਲ ਗਏ", "{N} ਨੇ {A} ਵਾਪਸ ਕੀਤੇ",
    "{N} ਦਾ {A} ਆ ਗਿਆ", "{N} ਨੇ {A} ਦੀ ਪੇਮੈਂਟ ਕੀਤੀ", "{N} ਦੇ ਖਾਤੇ ਵਿੱਚੋਂ {A} ਕੱਟ ਦਿਓ",
    "{N} ਨੇ {A} ਗੂਗਲ ਪੇ ਕੀਤੇ", "{N} ਨੇ ਪੂਰਾ ਹਿਸਾਬ ਚੁਕਤਾ ਕਰ ਦਿੱਤਾ", "{D} {N} {A} ਦੇ ਗਈ",
    "{N} ਤੋਂ {A} ਨਕਦ ਲਏ", "{N} ਨੇ {A} ਭੇਜੇ", "ਜਮ੍ਹਾ {N} {A}", "{N} ਨੇ {A} ਫੋਨ ਪੇ ਕਰ ਦਿੱਤੇ",
    "{N} ਸਾਰੇ ਪੈਸੇ ਦੇ ਗਿਆ", "{N} ਦਾ ਸਾਰਾ ਹਿਸਾਬ ਸਾਫ਼ ਹੋ ਗਿਆ", "{N} ਨੇ {A} ਜਮ੍ਹਾ ਕਰਾਏ",
    "{N} ਵੱਲੋਂ {A} ਦੀ ਪੇਮੈਂਟ ਆਈ", "{N} {A} ਮੋੜ ਗਿਆ", "{N} ਨੇ ਉਧਾਰ ਦੇ {A} ਲਾਹ ਦਿੱਤੇ",
    "{N} ਤੋਂ {A} ਵਸੂਲ ਹੋਏ", "{N} ਦੇ {A} ਆਏ ਨੇ ਜਮ੍ਹਾ ਕਰੋ", "{N} ਨੇ {A} ਯੂਪੀਆਈ ਕੀਤੇ",
],
"SALE": [
    "ਗੱਲੇ ਵਿੱਚ {A} ਪਾਏ ਵਿਕਰੀ ਦੇ", "{A} ਨਕਦ ਆਏ ਸਮਾਨ ਵਿਕਿਆ", "ਕਾਊਂਟਰ ਤੇ {A} ਦੀ ਵਿਕਰੀ", "{A} ਦਾ ਮਾਲ ਵੇਚਿਆ", "{Q} {I} ਵੇਚੇ {A} ਦੇ",
    "{A} ਦੀ ਨਕਦ ਵਿਕਰੀ", "{Q} {I} {A} ਦਾ ਨਕਦ ਵੇਚਿਆ", "ਕੈਸ਼ ਵਿੱਚ {A} ਦਾ {I} ਵਿਕਿਆ",
    "{A} ਦਾ ਸਮਾਨ ਨਕਦ ਵੇਚਿਆ", "ਨਕਦ {A}", "{I} ਵੇਚਿਆ {A} ਨਕਦ", "{D} {A} ਦੀ ਵਿਕਰੀ ਹੋਈ",
    "ਗੱਲੇ ਵਿੱਚ {A} ਆਏ", "{Q} {I} ਵਿਕਿਆ {A} ਕੈਸ਼", "ਨਕਦ ਵਿਕਰੀ {A} ਦੀ ਲਿਖੋ", "{A} ਦਾ {I} ਕੈਸ਼ ਵਿੱਚ ਗਿਆ",
    "ਇੱਕ ਗਾਹਕ {A} ਦਾ {I} ਲੈ ਗਿਆ ਨਕਦ", "{A} ਦੀ ਸੇਲ ਲਿਖੋ", "ਵਿਕਰੀ {A} ਨਕਦ {I}", "{A} ਗੱਲੇ ਵਿੱਚ ਪਾਓ ਵਿਕਰੀ ਦੇ",
],
"EXPENSE": [
    "{A} ਦਾ ਖਰਚਾ {E}", "{E} ਦੇ {A} ਦਿੱਤੇ", "{E} {A} ਖਰਚ ਹੋਏ", "ਖਰਚਾ {A} {E}", "{E} ਲਈ {A} ਭਰੇ",
    "{D} {E} ਦਾ {A} ਖਰਚਾ ਹੋਇਆ", "{E} ਵਿੱਚ {A} ਲੱਗ ਗਏ", "{A} {E} ਦੇ ਗਏ", "{E} ਦਾ ਖਰਚਾ {A} ਲਿਖੋ",
    "ਦੁਕਾਨ ਦਾ ਖਰਚਾ {A} {E}", "{E} ਭਰਿਆ {A}",
],
"BALANCE": [
    "{N} ਦੀ ਕਿੰਨੀ ਰਕਮ ਖੜ੍ਹੀ ਹੈ", "{N} ਵੱਲ ਕਿੰਨੇ ਨਿਕਲਦੇ ਨੇ", "{N} ਦਾ ਕਿੰਨਾ ਬਣਦਾ ਹੈ", "{N} ਦਾ ਹਿਸਾਬ ਸੁਣਾਓ", "{N} ਤੋਂ ਕਿੰਨੇ ਲੈਣੇ ਨੇ", "{N} ਦਾ ਬਕਾਇਆ",
    "{N} ਦੇ ਕਿੰਨੇ ਪੈਸੇ ਬਾਕੀ ਨੇ", "{N} ਦਾ ਹਿਸਾਬ ਦੱਸੋ", "{N} ਦਾ ਖਾਤਾ ਦਿਖਾਓ", "{N} ਵੱਲ ਕਿੰਨਾ ਬਕਾਇਆ ਹੈ",
    "{N} ਦਾ ਬੈਲੇਂਸ ਕਿੰਨਾ ਹੈ", "{N} ਨੇ ਕਿੰਨੇ ਦੇਣੇ ਨੇ", "{N} ਦਾ ਕਿੰਨਾ ਉਧਾਰ ਹੈ",
    "{N} ਦੀ ਕਿੰਨੀ ਉਧਾਰੀ ਖੜ੍ਹੀ ਹੈ", "{N} ਦਾ ਖਾਤਾ ਖੋਲ੍ਹੋ", "{N} ਦੇ ਖਾਤੇ ਵਿੱਚ ਕਿੰਨੇ ਨੇ",
    "{N} ਦਾ ਲੇਖਾ ਦੱਸੋ", "ਦੱਸੋ {N} ਦੇ ਕਿੰਨੇ ਪੈਸੇ ਰਹਿੰਦੇ ਨੇ", "{N} ਦੇ ਕਿੰਨੇ ਰਹਿੰਦੇ ਨੇ",
],
"DEBTORS": [
    "ਕਿਨ੍ਹਾਂ ਲੋਕਾਂ ਨੇ ਪੈਸੇ ਦੇਣੇ ਨੇ", "ਉਧਾਰ ਦੀ ਪੂਰੀ ਲਿਸਟ", "ਸਭ ਦੇ ਬਕਾਏ ਸੁਣਾਓ", "ਕਿੰਨੇ ਗਾਹਕਾਂ ਵੱਲ ਪੈਸੇ ਰਹਿੰਦੇ ਨੇ", "ਸਾਰਿਆਂ ਦਾ ਉਧਾਰ ਕਿੰਨਾ ਬਣਦਾ ਹੈ", "ਕੌਣ ਕੌਣ ਪੈਸੇ ਦੇਣ ਵਾਲਾ ਹੈ", "ਸਭ ਤੋਂ ਵੱਡਾ ਬਕਾਇਆ ਕਿਸਦਾ ਹੈ",
    "ਕਿਸ ਕਿਸ ਦੇ ਪੈਸੇ ਬਾਕੀ ਨੇ", "ਕੌਣ ਕੌਣ ਉਧਾਰ ਲੈ ਕੇ ਬੈਠਾ ਹੈ", "ਸਾਰੇ ਬਕਾਏ ਦੱਸੋ",
    "ਸਭ ਤੋਂ ਵੱਧ ਉਧਾਰ ਕਿਸ ਦਾ ਹੈ", "ਉਧਾਰ ਵਾਲਿਆਂ ਦੀ ਲਿਸਟ ਦਿਖਾਓ", "ਬਾਜ਼ਾਰ ਵਿੱਚ ਕਿੰਨਾ ਪੈਸਾ ਫਸਿਆ ਹੈ",
    "ਕੁੱਲ ਕਿੰਨਾ ਉਧਾਰ ਬਾਕੀ ਹੈ", "ਕਿਹਦੇ ਕਿਹਦੇ ਪੈਸੇ ਦੇਣੇ ਰਹਿੰਦੇ ਨੇ", "ਬਾਕੀ ਪੈਸਿਆਂ ਵਾਲੇ ਗਾਹਕ ਦੱਸੋ",
    "ਕੁੱਲ ਬਕਾਇਆ ਕਿੰਨਾ ਹੈ", "ਸਾਰੇ ਖਾਤੇ ਦਿਖਾਓ", "ਕਿੰਨੇ ਲੋਕਾਂ ਦਾ ਉਧਾਰ ਬਾਕੀ ਹੈ",
],
"SUMMARY": [
    "ਅੱਜ ਕੁੱਲ ਕਿੰਨੀ ਕਮਾਈ ਹੋਈ", "ਹਫ਼ਤੇ ਦੀ ਵਿਕਰੀ ਸੁਣਾਓ", "ਅੱਜ ਦਾ ਕੰਮ ਕਿਵੇਂ ਰਿਹਾ", "ਇਸ ਮਹੀਨੇ ਦਾ ਖਰਚਾ ਤੇ ਕਮਾਈ ਦੱਸੋ", "ਅੱਜ ਕਿੰਨਾ ਮਾਲ ਵਿਕਿਆ",
    "ਅੱਜ ਦੀ ਵਿਕਰੀ ਕਿੰਨੀ ਹੋਈ", "ਅੱਜ ਦਾ ਹਿਸਾਬ ਦੱਸੋ", "ਅੱਜ ਕਿੰਨੇ ਪੈਸੇ ਆਏ", "ਇਸ ਹਫ਼ਤੇ ਦੀ ਕਮਾਈ ਕਿੰਨੀ ਹੈ",
    "ਅੱਜ ਦਾ ਟੋਟਲ ਦੱਸੋ", "ਕੱਲ੍ਹ ਕਿੰਨਾ ਖਰਚਾ ਹੋਇਆ", "ਇਸ ਮਹੀਨੇ ਕਿੰਨੀ ਵਿਕਰੀ ਹੋਈ", "ਅੱਜ ਗੱਲੇ ਵਿੱਚ ਕਿੰਨੇ ਨੇ",
    "ਹਫ਼ਤੇ ਦਾ ਹਿਸਾਬ ਕਿਤਾਬ ਦੱਸੋ", "ਅੱਜ ਕਿੰਨਾ ਉਧਾਰ ਗਿਆ ਤੇ ਕਿੰਨਾ ਆਇਆ", "ਮਹੀਨੇ ਦਾ ਮੁਨਾਫ਼ਾ ਕਿੰਨਾ ਹੈ",
    "ਅੱਜ ਦਾ ਲੇਖਾ ਜੋਖਾ", "ਕੱਲ੍ਹ ਦੀ ਵਿਕਰੀ ਦੱਸੋ",
],
"REMIND": [
    "{N} ਨੂੰ ਕਹੋ ਪੈਸੇ ਦੇ ਜਾਵੇ", "{N} ਨੂੰ ਪੈਸਿਆਂ ਬਾਰੇ ਯਾਦ ਕਰਾ ਦਿਓ",
    "{N} ਨੂੰ ਯਾਦ ਕਰਵਾਓ", "{N} ਨੂੰ ਪੈਸਿਆਂ ਦਾ ਰਿਮਾਈਂਡਰ ਭੇਜੋ", "{N} ਨੂੰ ਸੁਨੇਹਾ ਭੇਜ ਦਿਓ ਕਿ ਪੈਸੇ ਦੇ ਜਾਵੇ",
    "{N} ਨੂੰ ਯਾਦ ਦਿਵਾਓ ਕਿ ਉਧਾਰ ਬਾਕੀ ਹੈ", "ਸਾਰਿਆਂ ਨੂੰ ਰਿਮਾਈਂਡਰ ਭੇਜੋ", "{N} ਨੂੰ ਮੈਸੇਜ ਕਰੋ ਪੈਸਿਆਂ ਬਾਰੇ",
    "{N} ਨੂੰ ਤਕਾਜ਼ਾ ਭੇਜੋ", "{N} ਨੂੰ ਬੋਲੋ ਹਿਸਾਬ ਕਰ ਜਾਵੇ", "ਬਕਾਏ ਵਾਲਿਆਂ ਨੂੰ ਯਾਦ ਕਰਵਾਓ",
    "{N} ਲਈ ਵੌਇਸ ਮੈਸੇਜ ਬਣਾਓ", "{N} ਨੂੰ ਵਟਸਐਪ ਤੇ ਯਾਦ ਕਰਵਾ ਦਿਓ",
],
"UNDO": [
    "ਹੁਣੇ ਵਾਲੀ ਐਂਟਰੀ ਗਲਤ ਹੈ", "ਉਹ ਵਾਪਸ ਲੈ ਲਓ",
    "ਪਿਛਲੀ ਐਂਟਰੀ ਕੱਟ ਦਿਓ", "ਗਲਤ ਹੋ ਗਿਆ ਵਾਪਸ ਕਰੋ", "ਆਖਰੀ ਐਂਟਰੀ ਮਿਟਾ ਦਿਓ", "ਉਹ ਰੱਦ ਕਰ ਦਿਓ",
    "ਅਨਡੂ ਕਰੋ", "ਪਿਛਲਾ ਡਿਲੀਟ ਕਰੋ", "ਨਹੀਂ ਨਹੀਂ ਉਹ ਗਲਤ ਸੀ ਹਟਾ ਦਿਓ", "ਪਿਛਲੀ ਗੱਲ ਕੈਂਸਲ ਕਰੋ",
    "ਇਹ ਐਂਟਰੀ ਗਲਤ ਹੈ ਹਟਾਓ", "ਜਿਹੜਾ ਹੁਣੇ ਲਿਖਿਆ ਉਹ ਮਿਟਾਓ",
],
"RISK": [
    "{N} ਤੇ ਯਕੀਨ ਕਰਾਂ ਜਾਂ ਨਹੀਂ", "{N} ਦਾ ਰਿਕਾਰਡ ਕਿਹੋ ਜਿਹਾ ਹੈ", "ਕੀ {N} ਨੂੰ ਹੋਰ ਸਮਾਨ ਦੇ ਦਈਏ", "{N} ਦਾ ਰਿਸਕ ਕਿੰਨਾ ਹੈ", "{N} ਪੈਸੇ ਵੇਲੇ ਸਿਰ ਦਿੰਦਾ ਹੈ", "{N} ਨੂੰ ਉਧਾਰ ਦੇਈਏ ਕਿ ਨਾ", "ਕਿਹੜੇ ਗਾਹਕਾਂ ਤੋਂ ਬਚ ਕੇ ਰਹਾਂ", "{N} ਚੰਗਾ ਗਾਹਕ ਹੈ", "ਕਿਸ ਦਾ ਪੈਸਾ ਡੁੱਬਣ ਦਾ ਖਤਰਾ ਹੈ", "{N} ਦਾ ਇਤਬਾਰ ਹੈ",
    "ਕੀ {N} ਨੂੰ ਉਧਾਰ ਦੇਣਾ ਠੀਕ ਹੈ", "{N} ਤੇ ਭਰੋਸਾ ਕਰ ਸਕਦੇ ਹਾਂ", "{N} ਪੈਸੇ ਮੋੜਦਾ ਹੈ ਕਿ ਨਹੀਂ",
    "{N} ਨੂੰ ਹੋਰ ਉਧਾਰ ਦੇਵਾਂ", "{N} ਦਾ ਭਰੋਸਾ ਸਕੋਰ ਦੱਸੋ", "ਕਿਸ ਨੂੰ ਉਧਾਰ ਨਹੀਂ ਦੇਣਾ ਚਾਹੀਦਾ",
    "ਕਿਹੜੇ ਗਾਹਕ ਖਤਰੇ ਵਾਲੇ ਨੇ", "{N} ਦੇ ਪੈਸੇ ਡੁੱਬ ਤਾਂ ਨਹੀਂ ਜਾਣਗੇ", "{N} ਕਿੰਨਾ ਭਰੋਸੇਮੰਦ ਹੈ",
    "ਕਿਹੜੇ ਗਾਹਕ ਪੈਸੇ ਨਹੀਂ ਮੋੜਦੇ", "{N} ਨੂੰ ਉਧਾਰ ਦੇਣ ਵਿੱਚ ਖਤਰਾ ਤਾਂ ਨਹੀਂ",
],
"OTHER": [
    "ਗਾਹਕ ਵਧਾਉਣ ਦਾ ਤਰੀਕਾ ਦੱਸੋ", "ਅੱਜ ਬਹੁਤ ਗਰਮੀ ਹੈ", "ਕੋਈ ਚੰਗੀ ਗੱਲ ਸੁਣਾਓ", "ਤੁਹਾਡਾ ਨਾਮ ਕੀ ਹੈ",
    "ਸਤ ਸ੍ਰੀ ਅਕਾਲ", "ਤੁਸੀਂ ਕੌਣ ਹੋ", "ਮੌਸਮ ਕਿਹੋ ਜਿਹਾ ਹੈ", "ਦੁਕਾਨ ਦੀ ਵਿਕਰੀ ਕਿਵੇਂ ਵਧਾਈਏ", "ਧੰਨਵਾਦ",
    "ਕੀ ਹਾਲ ਹੈ", "ਮੈਨੂੰ ਇੱਕ ਸਲਾਹ ਚਾਹੀਦੀ ਹੈ", "ਇਹ ਐਪ ਕਿਵੇਂ ਵਰਤਣੀ ਹੈ", "ਦੀਵਾਲੀ ਲਈ ਕਿਹੜਾ ਮਾਲ ਮੰਗਵਾਵਾਂ",
    "ਠੀਕ ਹੈ", "ਹਾਂ ਜੀ", "ਚੱਲੋ ਫਿਰ ਮਿਲਦੇ ਹਾਂ", "ਜੀਐਸਟੀ ਬਾਰੇ ਦੱਸੋ", "ਗਾਹਕ ਘੱਟ ਆ ਰਹੇ ਨੇ ਕੀ ਕਰਾਂ",
],
}

REAL_NAMES = """ਰਮੇਸ਼ ਗੁਰਪ੍ਰੀਤ ਹਰਪ੍ਰੀਤ ਮਨਪ੍ਰੀਤ ਜਸਪ੍ਰੀਤ ਸੁਖਵਿੰਦਰ ਬਲਵਿੰਦਰ ਕੁਲਦੀਪ ਅਮਰਜੀਤ ਪਰਮਜੀਤ
ਜਗਦੀਪ ਹਰਜੀਤ ਗੁਰਮੀਤ ਰਾਜੂ ਸੋਨੂੰ ਪਿੰਕੀ ਬਿੱਟੂ ਮਨਜੀਤ ਸਿਮਰਨ ਨਵਜੋਤ ਰਮਨ ਅਮਨ ਸੰਦੀਪ ਰਾਜਿੰਦਰ
ਸੁਰਿੰਦਰ ਜਸਵੀਰ ਤਰਸੇਮ ਮੋਹਨ ਸੁਨੀਤਾ ਕਮਲਜੀਤ ਬਲਜੀਤ ਹਰਮਨ ਗਗਨ ਲਵਲੀ ਨੀਟੂ ਦੀਪਕ ਵਿੱਕੀ ਮਿੰਟੂ ਗੋਲਡੀ
ਰਾਣੀ ਕਰਮਜੀਤ ਸਤਨਾਮ ਨਿਰਮਲ ਜਸਵੰਤ ਮਹਿੰਦਰ ਗੁਰਨਾਮ ਇਕਬਾਲ ਸਲੀਮ ਯੂਸਫ਼ ਪ੍ਰਕਾਸ਼ ਸ਼ਿੰਦਾ ਕਾਲਾ ਭੋਲਾ
ਜੱਸੀ ਰੂਪ ਹੈਪੀ ਬੌਬੀ ਅਨੀਤਾ ਪੂਜਾ ਨੇਹਾ ਸਰਬਜੀਤ ਹਰਦੀਪ ਦਵਿੰਦਰ""".split()
PREFIX = "ਗੁਰ ਹਰ ਮਨ ਜਸ ਸੁਖ ਬਲ ਕੁਲ ਅਮਰ ਪਰਮ ਜਗ ਨਵ ਰਾਜ ਦਲ ਸਿਮਰ ਪ੍ਰਭ ਤਜ ਕਰਮ ਸਰਬ ਇੰਦਰ ਹਰਮ ਲਖ ਅਰਸ਼".split()
SUFFIX = "ਪ੍ਰੀਤ ਜੀਤ ਵਿੰਦਰ ਦੀਪ ਜੋਤ ਮੀਤ ਵੀਰ ਬੀਰ ਇੰਦਰ ਪਾਲ ਨੀਤ ਨਾਮ ਜਿੰਦਰ ਵੰਤ ਦੇਵ".split()
SURNAMES = "ਸਿੰਘ ਕੌਰ ਸ਼ਰਮਾ ਵਰਮਾ ਗੁਪਤਾ ਅਰੋੜਾ ਗਿੱਲ ਸੰਧੂ ਢਿੱਲੋਂ ਬਰਾੜ ਬਾਜਵਾ ਮਾਨ ਸਿੱਧੂ ਚੀਮਾ".split()
TITLES = ["ਮਾਸਟਰ ਜੀ", "ਡਾਕਟਰ ਸਾਹਿਬ", "ਸਰਪੰਚ ਜੀ", "ਪੰਡਿਤ ਜੀ", "ਬੀਬੀ ਜੀ", "ਚਾਚਾ ਜੀ", "ਤਾਇਆ ਜੀ",
          "ਭਾਬੀ ਜੀ", "ਬਾਬਾ ਜੀ", "ਮਾਸੀ ਜੀ"]

ITEMS = """ਆਟਾ ਚੌਲ ਦਾਲ ਖੰਡ ਚਾਹ ਪੱਤੀ ਤੇਲ ਘਿਓ ਸਾਬਣ ਦੁੱਧ ਲੂਣ ਮਿਰਚ ਹਲਦੀ ਬਿਸਕੁਟ ਮੈਦਾ ਬੇਸਣ ਪਨੀਰ
ਦਹੀਂ ਅੰਡੇ ਸਬਜ਼ੀ ਗੁੜ ਮਸਾਲਾ ਸਰਫ਼ ਨਮਕੀਨ ਮੈਗੀ ਕੋਲਡ ਡਰਿੰਕ ਪਿਆਜ਼ ਆਲੂ ਟਮਾਟਰ ਛੋਲੇ ਰਾਜਮਾਂਹ
ਸੇਵੀਆਂ ਮੂੰਗਫਲੀ ਬਦਾਮ ਕਾਪੀ ਪੈੱਨ ਬੈਟਰੀ ਮਾਚਿਸ ਮੋਮਬੱਤੀ ਸ਼ੈਂਪੂ ਟੁੱਥਪੇਸਟ""".split()
MULTI_ITEMS = ["ਚਾਹ ਪੱਤੀ", "ਸਰ੍ਹੋਂ ਦਾ ਤੇਲ", "ਡਬਲ ਰੋਟੀ", "ਗੈਸ ਸਿਲੰਡਰ", "ਕੋਲਡ ਡਰਿੰਕ", "ਰਿਫਾਇੰਡ ਤੇਲ",
               "ਮੂੰਗੀ ਦੀ ਦਾਲ", "ਬਾਸਮਤੀ ਚੌਲ", "ਦੇਸੀ ਘਿਓ"]
EXPENSES = ["ਬਿਜਲੀ ਦਾ ਬਿੱਲ", "ਦੁਕਾਨ ਦਾ ਕਿਰਾਇਆ", "ਚਾਹ ਪਾਣੀ", "ਮਾਲ ਦੀ ਖਰੀਦ", "ਮੁੰਡੇ ਦੀ ਤਨਖਾਹ",
            "ਭਾੜਾ", "ਕਿਰਾਇਆ", "ਥੋਕ ਵਾਲੇ", "ਰਿਪੇਅਰ", "ਪੈਟਰੋਲ", "ਸਫ਼ਾਈ", "ਬਿਜਲੀ"]
DAYS = ["ਅੱਜ", "ਕੱਲ੍ਹ", "ਪਰਸੋਂ", "ਹੁਣੇ", "ਸਵੇਰੇ", "ਸ਼ਾਮ ਨੂੰ"]
UNITS = ["ਕਿੱਲੋ", "ਲੀਟਰ", "ਪੈਕਟ", "ਦਰਜਨ", "ਬੋਰੀ", "ਡੱਬੇ", "ਬੋਤਲਾਂ"]
SMALL_NUM_WORDS = ["ਇੱਕ", "ਦੋ", "ਤਿੰਨ", "ਚਾਰ", "ਪੰਜ", "ਦਸ", "ਅੱਧਾ", "ਡੇਢ", "ਢਾਈ"]
AMOUNT_WORDS = ["ਪੰਜ ਸੌ", "ਡੇਢ ਸੌ", "ਢਾਈ ਸੌ", "ਦੋ ਹਜ਼ਾਰ", "ਸਾਢੇ ਤਿੰਨ ਸੌ", "ਇੱਕ ਹਜ਼ਾਰ ਦੋ ਸੌ", "ਸੌ",
                "ਤਿੰਨ ਸੌ", "ਪੰਜਾਹ", "ਵੀਹ", "ਸੱਤ ਸੌ", "ਹਜ਼ਾਰ", "ਢਾਈ ਹਜ਼ਾਰ", "ਚਾਰ ਸੌ ਪੰਜਾਹ"]


def synth_name(rng: random.Random) -> list[str]:
    r = rng.random()
    if r < 0.40:
        base = [rng.choice(REAL_NAMES)]
    elif r < 0.75:
        base = [rng.choice(PREFIX) + rng.choice(SUFFIX)]
    elif r < 0.85:
        return rng.choice(TITLES).split()
    else:
        base = [rng.choice(REAL_NAMES + [p + s for p in PREFIX[:6] for s in SUFFIX[:6]])]
    if rng.random() < 0.25:
        base.append(rng.choice(SURNAMES))
    if rng.random() < 0.15:
        base.append("ਜੀ")
    return base


def synth_amount(rng: random.Random) -> list[str]:
    if rng.random() < 0.75:
        n = rng.choice([rng.randint(1, 50) * 10, rng.randint(1, 40) * 50, rng.randint(1, 20) * 500,
                        rng.randint(10, 9999)])
        form = rng.random()
        if form < 0.45:
            return [str(n), "ਰੁਪਏ"]
        if form < 0.55:
            return ["₹", str(n)]
        return [str(n)]
    w = rng.choice(AMOUNT_WORDS).split()
    return w + (["ਰੁਪਏ"] if rng.random() < 0.5 else [])


def synth_qty(rng: random.Random) -> list[str]:
    n = str(rng.randint(1, 10)) if rng.random() < 0.6 else rng.choice(SMALL_NUM_WORDS)
    return [n, rng.choice(UNITS)]


def synth_item(rng: random.Random) -> list[str]:
    return (rng.choice(MULTI_ITEMS) if rng.random() < 0.25 else rng.choice(ITEMS)).split()


def expand(template: str, rng: random.Random) -> tuple[list[str], list[str]]:
    if template.startswith("EN:"):
        from .datagen_en import expand_en
        return expand_en(template, rng)
    if template.startswith("HI:"):
        from .datagen_hi import expand_hi
        return expand_hi(template, rng)
    toks, tags = [], []
    name = None
    for part in template.split():
        if part == "{N}":
            name = name or synth_name(rng)          # same person if mentioned twice
            seg, lab = name, "NAME"
        elif part == "{I}":
            seg, lab = synth_item(rng), "ITEM"
        elif part == "{E}":
            seg, lab = rng.choice(EXPENSES).split(), "ITEM"
        elif part == "{A}":
            seg, lab = synth_amount(rng), None
        elif part == "{Q}":
            seg, lab = synth_qty(rng), None
        elif part == "{D}":
            seg, lab = ([rng.choice(DAYS)] if rng.random() < 0.7 else []), None
        else:
            seg, lab = [part], None
        for k, w in enumerate(seg):
            for sub in normalize(w).split():
                toks.append(sub)
                tags.append("O" if lab is None else ("B-" if k == 0 else "I-") + lab)
    return toks, tags


# ------------------------------------------------------------------ v2: more phrasings
# Written from general Punjabi shop-talk patterns (context clauses, relatives paying on
# someone's behalf, Hindi-tinged forms, future/modal questions, polite requests).
T2 = {
"CREDIT": [
    "{N} ਆਇਆ ਸੀ {Q} {I} ਲੈ ਗਿਆ {A} ਉਧਾਰ", "{N} ਦੇ ਘਰੋਂ ਕੋਈ {A} ਦਾ ਸਮਾਨ ਲੈ ਗਿਆ {N} ਦੇ ਖਾਤੇ ਵਿੱਚ",
    "{N} ਨੂੰ {A} ਦੀਏ ਉਧਾਰ", "{N} ਨੇ {A} ਦਾ {I} ਲੀਆ ਪੈਸੇ ਨਹੀਂ ਦੀਏ", "{N} ਦਾ ਖਾਤਾ {A} ਉਧਾਰ",
    "{N} {I} ਲੈ ਗਈ {A} ਦਾ ਲਿਖ ਦੇਣਾ", "{D} {N} ਨੂੰ {A} ਦਾ ਮਾਲ ਦਿੱਤਾ ਸੀ ਉਹ ਚੜ੍ਹਾਉਣਾ ਰਹਿ ਗਿਆ",
    "{N} ਦੇ ਨਾਮ ਤੇ {A} ਲਿਖੋ", "{N} ਨੂੰ {A} ਦਾ ਰਾਸ਼ਨ ਦਿੱਤਾ ਉਧਾਰ ਤੇ", "{N} ਦੇ ਖਾਤੇ {A} ਹੋਰ ਜੋੜੋ ਜੀ",
    "{N} ਲਈ {Q} {I} ਤੇ {I} ਕੁੱਲ {A} ਉਧਾਰ", "{N} ਨੇ ਉਧਾਰ ਤੇ {I} ਲਿਆ {A} ਦਾ",
],
"PAYMENT": [
    "{N} ਆਇਆ ਸੀ {A} ਦੇ ਗਿਆ", "{N} ਦਾ ਮੁੰਡਾ {A} ਦੇ ਗਿਆ {N} ਦੇ ਖਾਤੇ ਦੇ", "{N} ਨੇ {A} ਦੀਏ ਹੈਂ",
    "{N} ਵੱਲੋਂ {A} ਆਏ", "{N} ਦੇ {A} ਮਿਲ ਗਏ ਖਾਤੇ ਵਿੱਚੋਂ ਘਟਾ ਦਿਓ", "{N} ਨੇ ਕੁਝ ਪੈਸੇ ਦਿੱਤੇ {A}",
    "{N} ਨੇ {A} ਪੇਟੀਐਮ ਕੀਤੇ", "{N} ਤੋਂ {A} ਨਕਦ ਮਿਲੇ", "{N} ਦਾ {A} ਦਾ ਭੁਗਤਾਨ ਆ ਗਿਆ",
    "{N} ਨੇ ਸਾਰੇ ਪੈਸੇ ਮੋੜ ਦਿੱਤੇ", "{N} ਦਾ ਖਾਤਾ ਪੂਰਾ ਹੋ ਗਿਆ ਸਾਰਾ ਦੇ ਗਿਆ", "{N} ਨੇ ਅਦਾਇਗੀ ਕੀਤੀ {A}",
],
"SALE": [
    "ਇੱਕ ਬੰਦਾ {A} ਦਾ {I} ਲੈ ਗਿਆ ਪੈਸੇ ਦੇ ਕੇ", "{A} ਦਾ ਸਮਾਨ ਵਿਕਿਆ ਪੈਸੇ ਹੱਥ ਵਿੱਚ ਆਏ",
    "ਗਾਹਕ ਨੇ {Q} {I} ਲਿਆ {A} ਨਕਦ ਦਿੱਤੇ", "{D} ਨਕਦ ਵਿੱਚ {A} ਦੀ ਵਿਕਰੀ ਹੋਈ", "{A} ਕੈਸ਼ ਆਇਆ ਵਿਕਰੀ ਦਾ",
    "{I} ਵੇਚਿਆ {A} ਦਾ ਨਕਦੀ", "ਬਿਨਾਂ ਉਧਾਰ {A} ਦੀ ਵਿਕਰੀ", "ਕਿਸੇ ਨੇ {A} ਦਾ {I} ਖਰੀਦਿਆ ਨਕਦ",
],
"EXPENSE": [
    "{E} ਤੇ {A} ਲੱਗੇ", "{E} ਦੇ {A} ਖਰਚੇ", "{A} {E} ਵਿੱਚ ਗਏ", "{E} ਲਈ {A} ਦੇ ਦਿੱਤੇ",
    "{E} ਖਰੀਦਿਆ {A} ਦਾ ਦੁਕਾਨ ਵਾਸਤੇ", "ਦੁਕਾਨ ਲਈ {E} ਲਿਆ {A}", "{D} {E} ਭਰਿਆ {A}",
    "{E} ਦਾ {A} ਦੇਣਾ ਪਿਆ",
],
"BALANCE": [
    "{N} ਦਾ ਕਿੰਨਾ ਬਣਦਾ ਹੈ ਹੁਣ ਤੱਕ", "{N} ਦੇ ਕੋਈ ਪੈਸੇ ਰਹਿੰਦੇ ਨੇ", "{N} ਦਾ ਖਾਤਾ ਕਿੰਨੇ ਤੇ ਹੈ",
    "{N} ਵੱਲ ਕੀ ਬਾਕੀ ਹੈ", "{N} ਦੀ ਉਧਾਰੀ ਕਿੰਨੀ ਹੋ ਗਈ", "ਜ਼ਰਾ {N} ਦਾ ਹਿਸਾਬ ਦੇਖੋ",
    "{N} ਨੇ ਕਿੰਨੇ ਦੇਣੇ ਬਾਕੀ ਨੇ", "{N} ਦਾ ਬਕਾਇਆ ਕਿੰਨਾ ਹੈ ਦੱਸੋ",
],
"DEBTORS": [
    "ਕਿੰਨਾ ਪੈਸਾ ਬਾਹਰ ਗਿਆ ਹੋਇਆ ਹੈ", "ਮੇਰਾ ਕਿੰਨਾ ਉਧਾਰ ਲੋਕਾਂ ਵੱਲ ਹੈ", "ਕਿਹਦੇ ਕਿਹਦੇ ਵੱਲ ਪੈਸੇ ਨੇ",
    "ਸਾਰੇ ਉਧਾਰ ਵਾਲੇ ਗਾਹਕ ਦਿਖਾਓ", "ਕੁੱਲ ਕਿੰਨੇ ਪੈਸੇ ਲੈਣੇ ਨੇ ਸਾਰਿਆਂ ਤੋਂ", "ਪੈਸੇ ਦੇਣ ਵਾਲਿਆਂ ਦੀ ਸੂਚੀ",
    "ਕਿੰਨੇ ਲੋਕ ਉਧਾਰ ਤੇ ਨੇ", "ਸਾਰਿਆਂ ਦੇ ਖਾਤਿਆਂ ਦਾ ਜੋੜ ਦੱਸੋ",
],
"SUMMARY": [
    "ਅੱਜ ਦਾ ਕਾਰੋਬਾਰ ਕਿੰਨਾ ਹੋਇਆ", "ਇਸ ਹਫ਼ਤੇ ਕਿੰਨਾ ਖਰਚਾ ਹੋਇਆ", "ਮਹੀਨੇ ਦੀ ਕੁੱਲ ਵਿਕਰੀ ਦੱਸੋ",
    "ਅੱਜ ਕਿੰਨਾ ਨਕਦ ਆਇਆ", "ਕੱਲ੍ਹ ਕਿੰਨੀ ਕਮਾਈ ਹੋਈ ਸੀ", "ਇਸ ਮਹੀਨੇ ਫ਼ਾਇਦਾ ਕਿੰਨਾ ਰਿਹਾ",
    "ਅੱਜ ਕਿੰਨਾ ਉਧਾਰ ਗਿਆ", "ਹਫ਼ਤੇ ਦੀ ਰਿਪੋਰਟ ਦਿਓ",
],
"REMIND": [
    "{N} ਨੂੰ ਪੈਸਿਆਂ ਦਾ ਸੁਨੇਹਾ ਲਾ ਦਿਓ", "{N} ਨੂੰ ਫੋਨ ਕਰਕੇ ਯਾਦ ਕਰਾਓ", "{N} ਨੂੰ ਬੋਲੋ ਪੈਸੇ ਭੇਜ ਦੇਵੇ",
    "ਸਾਰੇ ਬਕਾਏ ਵਾਲਿਆਂ ਨੂੰ ਸੁਨੇਹਾ ਭੇਜੋ", "{N} ਨੂੰ ਪੈਸਿਆਂ ਲਈ ਮੈਸੇਜ ਭੇਜ ਦਿਓ", "{N} ਨੂੰ ਨਰਮੀ ਨਾਲ ਯਾਦ ਕਰਾਓ",
    "ਜਿਹੜੇ ਪੈਸੇ ਨਹੀਂ ਦੇ ਰਹੇ ਉਹਨਾਂ ਨੂੰ ਯਾਦ ਕਰਾਓ",
],
"UNDO": [
    "ਰੁਕੋ ਇਹ ਗਲਤ ਹੈ", "ਉਹ ਨਾ ਲਿਖੋ ਹਟਾ ਦਿਓ", "ਆਖਰੀ ਵਾਲੀ ਮਿਟਾਓ", "ਗਲਤੀ ਹੋ ਗਈ ਪਿਛਲਾ ਹਟਾਓ",
    "ਜੋ ਹੁਣੇ ਲਿਖਿਆ ਕੈਂਸਲ ਕਰੋ",
],
"RISK": [
    "{N} ਹੋਰ ਉਧਾਰ ਮੰਗ ਰਿਹਾ ਹੈ ਦੇਵਾਂ", "{N} ਦੇ ਪੈਸੇ ਮੁੜਨਗੇ", "{N} ਪੈਸਿਆਂ ਦਾ ਪੱਕਾ ਹੈ",
    "{N} ਨੂੰ {A} ਦਾ ਉਧਾਰ ਦੇਣਾ ਠੀਕ ਰਹੂ", "ਕਿਹੜੇ ਗਾਹਕਾਂ ਨੂੰ ਉਧਾਰ ਬੰਦ ਕਰਾਂ", "{N} ਤੇ ਭਰੋਸਾ ਹੈ ਕਿ ਨਹੀਂ",
    "ਕਿਸ ਦੇ ਪੈਸੇ ਫਸਣ ਦਾ ਖਤਰਾ ਹੈ",
],
"OTHER": [
    "ਤੁਸੀਂ ਮੇਰੀ ਕੀ ਮਦਦ ਕਰ ਸਕਦੇ ਹੋ", "ਅੱਜ ਬੜੀ ਠੰਡ ਹੈ", "ਹੈਲੋ ਹੈਲੋ", "ਨਮਸਤੇ ਜੀ", "ਮੇਰੀ ਦੁਕਾਨ ਕਿਵੇਂ ਚੱਲ ਰਹੀ ਹੈ",
    "ਚੰਗਾ ਜੀ ਧੰਨਵਾਦ", "ਕੋਈ ਗੱਲ ਨਹੀਂ",
],
}
for _k, _v in T2.items():
    T[_k] = T[_k] + _v

# English / Hinglish templates (see datagen_en.py), same intents
from .datagen_en import T_EN  # noqa: E402
from .datagen_hi import T_HI  # noqa: E402
for _k, _v in T_EN.items():
    T[_k] = T[_k] + _v + T_HI[_k]

# Prisma writes many English loanwords in Latin script ("entry", "Google Pay", "cash").
LOANWORDS = {
    "ਐਂਟਰੀ": ["entry"], "ਪੇਮੈਂਟ": ["payment"], "ਕੈਸ਼": ["cash"], "ਟੋਟਲ": ["total"], "ਬੈਲੇਂਸ": ["balance"],
    "ਰਿਮਾਈਂਡਰ": ["reminder"], "ਡਿਲੀਟ": ["delete"], "ਕੈਂਸਲ": ["cancel"], "ਅਨਡੂ": ["undo"],
    "ਯੂਪੀਆਈ": ["upi"], "ਲਿਸਟ": ["list"], "ਸਕੋਰ": ["score"], "ਰਿਸਕ": ["risk"], "ਮੈਸੇਜ": ["message"],
    "ਵਟਸਐਪ": ["whatsapp"], "ਸੇਲ": ["sale"], "ਰਿਪੇਅਰ": ["repair"], "ਪੈਟਰੋਲ": ["petrol"], "ਬਿੱਲ": ["bill"],
    "ਵੌਇਸ": ["voice"], "ਰਿਪੋਰਟ": ["report"], "ਪੇਟੀਐਮ": ["paytm"], "ਹੈਲੋ": ["hello"],
}
LOAN_PHRASES = {("ਗੂਗਲ", "ਪੇ"): ["google", "pay"], ("ਫੋਨ", "ਪੇ"): ["phonepe"], ("ਕੋਲਡ", "ਡਰਿੰਕ"): ["cold", "drink"]}
_LOAN_N = {normalize(k): v for k, v in LOANWORDS.items()}
_PHRASE_N = {tuple(normalize(w) for w in k): v for k, v in LOAN_PHRASES.items()}
FILLERS_PRE = ["ਹਾਂ ਜੀ", "ਓ ਭਾਈ", "ਸੁਣੋ", "ਅੱਛਾ", "ਚਲੋ", "ਜ਼ਰਾ", "ਲਿਖੋ", "ਹਾਂ", "ਦੇਖੋ ਜੀ", "ਅੱਛਾ ਸੁਣੋ"]
FILLERS_POST = ["ਜੀ", "ਹੈ ਜੀ", "ਠੀਕ ਹੈ", "ਹਾਂ", "ਬੱਸ"]


def augment(toks: list[str], tags: list[str], rng: random.Random):
    """Realistic surface variation on top of the templates."""
    toks, tags = list(toks), list(tags)
    if rng.random() < 0.35:   # Latin-script loanwords
        out_t, out_g, i = [], [], 0
        while i < len(toks):
            pair = tuple(toks[i:i + 2])
            if len(pair) == 2 and pair in _PHRASE_N and tags[i] == "O" and rng.random() < 0.8:
                rep = _PHRASE_N[pair]; out_t += rep; out_g += ["O"] * len(rep); i += 2; continue
            if toks[i] in _LOAN_N and rng.random() < 0.8:
                rep = _LOAN_N[toks[i]]
                out_t += rep; out_g += [tags[i]] + [tags[i].replace("B-", "I-")] * (len(rep) - 1); i += 1; continue
            out_t.append(toks[i]); out_g.append(tags[i]); i += 1
        toks, tags = out_t, out_g
    if rng.random() < 0.25:   # filler words at the start / end
        f = normalize(rng.choice(FILLERS_PRE)).split()
        toks, tags = f + toks, ["O"] * len(f) + tags
    if rng.random() < 0.12:
        f = normalize(rng.choice(FILLERS_POST)).split()
        toks, tags = toks + f, tags + ["O"] * len(f)
    if rng.random() < 0.06 and len(toks) > 4:   # ASR drops a short function word
        i = rng.randrange(len(toks))
        if tags[i] == "O" and len(toks[i]) <= 3:
            del toks[i]; del tags[i]
    return toks, tags


def generate(n_per_template: int = 60, seed: int = 7, templates: dict | None = None, aug: bool = True):
    rng = random.Random(seed)
    data = []
    for intent, temps in (templates or T).items():
        for ti, tmpl in enumerate(temps):
            reps = n_per_template if "{" in tmpl else max(8, n_per_template // 6)
            for _ in range(reps):
                toks, tags = expand(tmpl, rng)
                if aug:
                    if tmpl.startswith("EN:"):
                        from .datagen_en import augment_en
                        toks, tags = augment_en(toks, tags, rng)
                    elif tmpl.startswith("HI:"):
                        from .datagen_hi import augment_hi
                        toks, tags = augment_hi(toks, tags, rng)
                    else:
                        toks, tags = augment(toks, tags, rng)
                data.append({"tokens": toks, "tags": tags, "intent": intent, "template": f"{intent}:{ti}"})
    rng.shuffle(data)
    return data
