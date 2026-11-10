import { Recorder } from './recorder.js';

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const rs = (n) => (n < 0 ? '-' : '') + '₹' + Math.abs(Math.round(n * 100) / 100).toLocaleString('en-IN');
const KIND = {
  credit: { pa: 'ਉਧਾਰ', en: 'Credit', hi: 'उधार' }, payment: { pa: 'ਜਮ੍ਹਾ', en: 'Paid', hi: 'जमा' },
  sale: { pa: 'ਨਕਦ ਵਿਕਰੀ', en: 'Cash sale', hi: 'नकद बिक्री' }, expense: { pa: 'ਖਰਚਾ', en: 'Expense', hi: 'खर्चा' },
};
const EXAMPLES = [
  ['ਰਮੇਸ਼ ਨੂੰ 500 ਰੁਪਏ ਦਾ ਆਟਾ ਉਧਾਰ ਦਿੱਤਾ', 'Gave Ramesh ₹500 of flour on credit'],
  ['ਗੁਰਪ੍ਰੀਤ ਨੇ ਡੇਢ ਸੌ ਜਮ੍ਹਾ ਕਰਵਾਏ', 'Gurpreet paid ₹150'],
  ['ਕਿਸ ਕਿਸ ਦੇ ਪੈਸੇ ਬਾਕੀ ਨੇ', 'Who still owes money?'],
  ['ਕੀ ਬਿੱਟੂ ਨੂੰ ਉਧਾਰ ਦੇਣਾ ਠੀਕ ਹੈ', 'Is it safe to give Bittu credit?'],
  ['ਅੱਜ ਦਾ ਹਿਸਾਬ ਦੱਸੋ', "Today's summary"],
];

const EXAMPLES_HI = [
  ['रमेश को 500 रुपये का आटा उधार दिया', ''],
  ['गुरप्रीत ने गूगल पे से डेढ़ सौ भेजे', ''],
  ['किस किस के पैसे बाकी हैं?', ''],
  ['क्या बिट्टू को और उधार देना ठीक है?', ''],
  ['आज का हिसाब बताओ', ''],
];
// Hindi for the English UI strings (Hindi mode shows these in place of the English labels)
const HI = {
  '(asks when unsure)': '(शक हो तो पूछता है)', 'All customers': 'सभी ग्राहक', 'Collected': 'पैसे आए', 'Credit': 'उधार',
  'Credit added': 'उधार लिखा', 'Credit given': 'आज उधार', 'Customers': 'ग्राहक', 'Didn’t hear anything': 'कुछ सुनाई नहीं दिया',
  'Entry removed': 'एंट्री हटा दी', 'Expected in 7 days': 'इस हफ़्ते आने की उम्मीद', 'Home': 'घर', 'Insights': 'जानकारी',
  'Language': 'भाषा', 'Last 30 days': 'पिछले 30 दिन', 'Ledger': 'खाता', 'Manual entry': 'हाथ से एंट्री',
  'Microphone permission needed': 'माइक की अनुमति चाहिए', 'Models behind this': 'इसके पीछे के मॉडल',
  'Money at risk (ML)': 'ख़तरे में पैसा (ML)', 'Needs attention': 'ध्यान दीजिए', 'New': 'नया',
  'No customers yet. Speak your first entry.': 'अभी कोई ग्राहक नहीं। माइक दबाकर पहली एंट्री बोलिए।',
  'Nobody risky right now': 'अभी सब ठीक है', 'Nothing saved, say it again': 'नहीं लिखा, फिर से बोलिए',
  'Outstanding': 'कुल बकाया', 'Owner': 'मालिक का नाम', 'Paid': 'जमा', 'Payment added': 'जमा हो गया', 'Phone': 'फ़ोन',
  'Phone saved': 'फ़ोन सेव हुआ', 'Play': 'सुनें', 'Play reminder': 'याद-संदेश सुनें', 'Restore': 'वापस लाएं',
  'Sales today': 'आज बिक्री', 'Save': 'सेव करें', 'Saved': 'सेव हो गया', 'Search customers…': 'ग्राहक खोजें…',
  'See insights': 'जानकारी देखें', 'Send': 'भेजें', 'Settings': 'सेटिंग', 'Shop': 'दुकान', 'Shop name': 'दुकान का नाम',
  'Show English subtitles in Punjabi mode': 'पंजाबी के नीचे अंग्रेज़ी दिखाएं', 'Sorry, something went wrong.': 'माफ़ कीजिए, कुछ गड़बड़ हो गई।',
  'Suggested further credit': 'सुझाई गई और उधार सीमा', 'System': 'सिस्टम', 'Total due': 'कुल बकाया',
  'Trust score (ML)': 'भरोसा स्कोर (ML)', 'Type instead of speaking': 'लिखकर पूछें', 'Under the hood': 'अंदर क्या हुआ',
  'Undo': 'वापस', 'Voice reminder': 'याद-संदेश', 'WhatsApp': 'व्हाट्सएप', 'collected': 'उधार वापसी', 'credit': 'उधार',
  'credit given': 'उधार दिया', 'new': 'नया', "no, I'll repeat": 'नहीं, दोबारा बोलूंगा', 'open': 'खाता', 'received': 'जमा',
  'sales': 'नकद बिक्री', 'yes, save': 'हां, सेव करें', 'Balance due': 'बकाया', 'Advance': 'एडवांस',
  'Bolda Khata · voice ledger': 'बोलता खाता · आवाज़ वाला बही खाता', 'Shop name (English)': 'दुकान का नाम (अंग्रेज़ी)',
  'Shop name (Hindi)': 'दुकान का नाम (हिंदी)',
};

const EXAMPLES_EN = [
  ['Gave Ramesh 500 rupees of flour on credit', ''],
  ['Gurpreet paid 150 on Google Pay', ''],
  ['Who all owe me money?', ''],
  ['Should I give Bittu more credit?', ''],
  ['Bittu ko 300 udhaar diya', 'Hinglish works too'],
];

// ------------------------------------------------------------------ language (Punjabi / English)
let lang = 'pa';
try { lang = localStorage.getItem('lang') || 'pa'; } catch (_) {}
const tr = (pa, en, hi) => (lang === 'en' ? en : lang === 'hi' ? (hi ?? HI[en] ?? en) : pa);
// short label with all forms; applyLang() flips it in place when the language changes
const L = (pa, en, hi) => `<span data-pa="${esc(pa)}" data-en="${esc(en)}"${hi ? ` data-hi="${esc(hi)}"` : ''}>${esc(tr(pa, en, hi))}</span>`;
// an English subtitle span that also knows its Hindi form
const EN = (en, hi, extra = '') => `<span class="en${extra}"${hi ? ` data-hi="${esc(hi)}"` : ''}>${esc(en)}</span>`;
const pick = (o, base = '') => (o ? o[`${base}${lang}`] ?? o[`${base}en`] ?? '' : '');
const GUR = /[\u0A00-\u0A7F]/;

// Every "Punjabi text <span class=en>English</span>" pair: wrap the Punjabi part so CSS can
// show either language. Runs on everything rendered, now or later (MutationObserver).
function wrapPa(root) {
  if (!root.querySelectorAll) return;
  root.querySelectorAll('.en:not([data-w])').forEach((en) => {
    en.dataset.w = '1';
    const parts = [];
    let n = en.previousSibling;
    while (n && (n.nodeType === 3 || (n.nodeType === 1 && ['B', 'BR', 'I', 'STRONG', 'EM'].includes(n.tagName)))) {
      parts.unshift(n); n = n.previousSibling;
    }
    if (!parts.length || !parts.some((x) => GUR.test(x.textContent))) return;
    const w = document.createElement('span');
    w.className = 'pa';
    en.parentNode.insertBefore(w, parts[0]);
    parts.forEach((x) => w.appendChild(x));
    if (!/\s$/.test(w.textContent)) w.appendChild(document.createTextNode(' '));
  });
}
function translate(root) {
  if (!root.querySelectorAll) return;
  root.querySelectorAll('[data-en]').forEach((e) => {
    if (e.dataset.pa == null) e.dataset.pa = e.textContent;
    e.textContent = tr(e.dataset.pa, e.dataset.en, e.dataset.hi);
  });
  root.querySelectorAll('[data-ph-en]').forEach((e) => {
    if (e.dataset.phPa == null) e.dataset.phPa = e.placeholder;
    e.placeholder = tr(e.dataset.phPa, e.dataset.phEn, HI[e.dataset.phEn]);
  });
  // English subtitle spans: in Hindi mode show their Hindi form (data-hi, or the HI table)
  root.querySelectorAll('.en:not(.keep-en)').forEach((e) => {
    if (e.children.length) return;
    if (e.dataset.origEn == null) e.dataset.origEn = e.textContent;
    const h = e.dataset.hi ?? HI[e.dataset.origEn.trim()];
    e.textContent = lang === 'hi' && h ? h : e.dataset.origEn;
  });
}
function applyLang() {
  document.body.classList.toggle('lang-en', lang === 'en');
  document.body.classList.toggle('lang-hi', lang === 'hi');
  document.body.classList.toggle('lang-x', lang !== 'pa');   // any non-Punjabi mode
  document.body.classList.toggle('lang-pa', lang === 'pa');
  document.documentElement.lang = lang;
  $$('.lang-switch button').forEach((b) => b.setAttribute('aria-pressed', b.dataset.lang === lang));
  translate(document);
  renderExamples();
}
function setLang(l) {
  lang = ['en', 'hi'].includes(l) ? l : 'pa';
  try { localStorage.setItem('lang', lang); } catch (_) {}
  pending = null;
  applyLang();
  if (state) refresh();
  if ($('#view-insights').classList.contains('active')) renderInsights();
  if ($('#view-test').classList.contains('active')) openTest();
}
new MutationObserver((muts) => muts.forEach((m) => m.addedNodes.forEach((n) => {
  if (n.nodeType === 1) { wrapPa(n); translate(n); }
}))).observe(document.body, { childList: true, subtree: true });

let state = null;
let pending = null;
let current = null;  // open customer id
const audio = new Audio();

// ------------------------------------------------------------------ api
async function api(path, opts = {}) {
  let r;
  try {
    r = await fetch(path, { headers: opts.body && !(opts.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}, ...opts });
  } catch (_) {
    const err = new Error('network');
    err.code = 'network';
    setReachable(false);
    throw err;
  }
  setReachable(true);
  if (r.status === 401 && path !== '/api/login') { showPin(); throw new Error('PIN required'); }
  if (!r.ok) {
    let msg = r.statusText, code = null;
    try {
      const d = (await r.json()).detail;
      if (d && typeof d === 'object') { msg = d.message || msg; code = d.code || null; } else if (d) msg = d;
    } catch (_) {}
    const err = new Error(msg);
    err.code = code;
    err.status = r.status;
    throw err;
  }
  return r.json();
}
const post = (p, body) => api(p, { method: 'POST', body: body instanceof FormData ? body : JSON.stringify(body) });

// ------------------------------------------------------------------ failures
const FAIL = {
  network: ['ਦੁਕਾਨ ਵਾਲੇ ਕੰਪਿਊਟਰ ਨਾਲ ਸੰਪਰਕ ਨਹੀਂ ਹੋਇਆ। ਕੁਝ ਨਹੀਂ ਲਿਖਿਆ ਗਿਆ।',
    "Couldn't reach the shop computer. Nothing was saved.",
    'दुकान वाले कंप्यूटर से संपर्क नहीं हुआ। कुछ नहीं लिखा गया।'],
  credits: ['Gnani ਦੇ ਕ੍ਰੈਡਿਟ ਖਤਮ ਹੋ ਗਏ ਹਨ, ਆਵਾਜ਼ ਨਹੀਂ ਚੱਲੇਗੀ। ਲਿਖ ਕੇ ਐਂਟਰੀ ਕਰ ਸਕਦੇ ਹੋ।',
    'Gnani credits have run out, so voice is off. You can still type the entry.',
    'Gnani के क्रेडिट ख़त्म हो गए हैं, आवाज़ नहीं चलेगी। लिखकर एंट्री कर सकते हैं।'],
  auth: ['Gnani ਦੀ ਚਾਬੀ (API key) ਕੰਮ ਨਹੀਂ ਕਰ ਰਹੀ। ਲਿਖ ਕੇ ਐਂਟਰੀ ਕਰ ਸਕਦੇ ਹੋ।',
    "The Gnani API key isn't working. You can still type the entry.",
    'Gnani की चाबी (API key) काम नहीं कर रही। लिखकर एंट्री कर सकते हैं।'],
  busy: ['ਆਵਾਜ਼ ਸੇਵਾ ਰੁੱਝੀ ਹੋਈ ਹੈ। ਕੁਝ ਸਕਿੰਟ ਬਾਅਦ ਫਿਰ ਭੇਜੋ।',
    'The voice service is busy. Try again in a few seconds.',
    'आवाज़ सेवा व्यस्त है। कुछ सेकंड बाद फिर भेजिए।'],
  down: ['ਆਵਾਜ਼ ਸੇਵਾ (Gnani) ਇਸ ਵੇਲੇ ਨਹੀਂ ਚੱਲ ਰਹੀ। ਫਿਰ ਭੇਜੋ ਜਾਂ ਲਿਖ ਕੇ ਐਂਟਰੀ ਕਰੋ।',
    "The voice service (Gnani) isn't responding. Retry, or type the entry.",
    'आवाज़ सेवा (Gnani) अभी नहीं चल रही। फिर भेजिए या लिखकर एंट्री कीजिए।'],
  other: ['ਮਾਫ਼ ਕਰਨਾ, ਕੁਝ ਗੜਬੜ ਹੋ ਗਈ। ਕੁਝ ਨਹੀਂ ਲਿਖਿਆ ਗਿਆ।', 'Sorry, something went wrong. Nothing was saved.',
    'माफ़ कीजिए, कुछ गड़बड़ हो गई। कुछ नहीं लिखा गया।'],
};
function failText(e) {
  const [pa, en, hi] = FAIL[e.code] || FAIL.other;
  return tr(pa, en, hi);
}
// An error bubble that keeps what the shopkeeper said: Retry (resend the same recording/text)
// and, when voice can't work, a box to type the entry instead.
function failBubble(e, retry, el) {
  const voiceDead = ['credits', 'auth', 'down', 'busy'].includes(e.code);
  const html = `<div class="say">${esc(failText(e))}</div>
    ${e.code && e.code !== 'network' ? `<span class="en sub-only">${esc(e.message)}</span>` : ''}
    <div class="bot-actions">
      ${retry ? `<button class="icon-btn retry">↻ ${L('ਫਿਰ ਭੇਜੋ', 'Retry', 'फिर भेजें')}</button>` : ''}
    </div>
    ${voiceDead || e.code === 'network' ? `<form class="type-row fail-type">
      <input placeholder="${esc(tr('ਲਿਖ ਕੇ ਐਂਟਰੀ ਕਰੋ…', 'Type the entry…', 'लिखकर एंट्री कीजिए…'))}" autocomplete="off">
      <button class="btn" type="submit">${L('ਭੇਜੋ', 'Send', 'भेजें')}</button></form>` : ''}`;
  if (el) { el.className = 'bubble bot'; el.innerHTML = html; } else el = addBubble('bot', html);
  $('.retry', el)?.addEventListener('click', () => { el.remove(); retry(); });
  const f = $('.fail-type', el);
  if (f) f.onsubmit = (ev) => {
    ev.preventDefault();
    const inp = $('input', f), v = inp.value.trim();
    if (v) { inp.value = ''; sendText(v); }
  };
  el.scrollIntoView({ behavior: 'smooth', block: 'end' });
  return el;
}

// ------------------------------------------------------------------ connection watch
// navigator.onLine only knows about the phone's own network; this also notices when the
// shop computer (the Mac running the app) is asleep or the link is down.
let reachable = true;
function setReachable(ok) {
  const cameBack = ok && !reachable;
  reachable = ok;
  const bar = $('#offlineBar');
  if (bar) {
    const wait = queueCount ? ` · ${queueCount} ${L('ਐਂਟਰੀਆਂ ਫ਼ੋਨ ਵਿੱਚ ਰੱਖੀਆਂ', 'entries saved on this phone', 'एंट्री फ़ोन में रखी')}` : '';
    if (!navigator.onLine) {
      bar.hidden = false;
      bar.innerHTML = 'ਇੰਟਰਨੈੱਟ ਨਹੀਂ · इंटरनेट नहीं · You’re offline' + wait;
    } else if (!ok) {
      bar.hidden = false;
      bar.innerHTML = 'ਦੁਕਾਨ ਵਾਲੇ ਕੰਪਿਊਟਰ ਨਾਲ ਸੰਪਰਕ ਨਹੀਂ · दुकान वाले कंप्यूटर से संपर्क नहीं · Can’t reach the shop computer' + wait;
    } else if (queueCount) {
      bar.hidden = false;
      bar.innerHTML = `🕓 ${queueCount} ${L('ਰੱਖੀਆਂ ਐਂਟਰੀਆਂ ਭੇਜ ਰਹੇ ਹਾਂ…', 'saved entries waiting to send…', 'रखी हुई एंट्री भेज रहे हैं…')}`;
    } else bar.hidden = true;
  }
  if (cameBack) flushQueue();
}
async function pingServer() {
  if (document.hidden) return;
  try { const r = await fetch('/api/auth', { cache: 'no-store' }); setReachable(r.ok || r.status === 401); }
  catch (_) { setReachable(false); }
  if (reachable && queueCount) flushQueue();   // e.g. Gnani was down: the server answered, try the queue again
}

// ------------------------------------------------------------------ offline queue
// When the shop computer, the internet or Gnani can't be reached, the recording (or typed entry) is kept on
// this phone (IndexedDB) and sent by itself, oldest first, once the connection is back. Each entry is written
// with the time it was SPOKEN, so "ਕੱਲ੍ਹ" still means the right day even if it is sent the next morning.
const QUEUEABLE = ['network', 'down', 'busy'];
let queueCount = 0;
let flushing = false;
function qdb() {
  return new Promise((ok, bad) => {
    const r = indexedDB.open('bolda-khata-queue', 1);
    r.onupgradeneeded = () => r.result.createObjectStore('items', { keyPath: 'id', autoIncrement: true });
    r.onsuccess = () => ok(r.result);
    r.onerror = () => bad(r.error);
  });
}
async function qdo(mode, fn) {
  const d = await qdb();
  return new Promise((ok, bad) => {
    const t = d.transaction('items', mode);
    const req = fn(t.objectStore('items'));
    t.oncomplete = () => ok(req.result);
    t.onerror = () => bad(t.error);
  });
}
const qAdd = (item) => qdo('readwrite', (s) => s.add(item));
const qAll = () => qdo('readonly', (s) => s.getAll());
const qDel = (id) => qdo('readwrite', (s) => s.delete(id));
async function updateQueueBadge() {
  try { queueCount = (await qAll()).length; } catch (_) { queueCount = 0; }
  setReachable(reachable);
}
const hhmm = (ms) => new Date(ms).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });

// Keep an entry on the phone. `me` is the shopkeeper's bubble, which becomes a "waiting" bubble.
async function enqueue(item, me) {
  if (item.blob) { item.audio = await item.blob.arrayBuffer(); delete item.blob; }   // iOS stores buffers reliably
  const id = await qAdd(item);
  me.dataset.qid = id;
  me.classList.add('queued');
  const what = item.text ? `${esc(item.text)}<br>` : '🎙 ';
  me.innerHTML = `${what}<span class="muted">🕓 ${esc(tr('ਫ਼ੋਨ ਵਿੱਚ ਰੱਖ ਲਈ, ਸੰਪਰਕ ਹੁੰਦੇ ਹੀ ਆਪੇ ਭੇਜ ਦਿਆਂਗੇ',
    'Saved on this phone. It will send by itself when the connection is back.',
    'फ़ोन में रख ली, संपर्क होते ही अपने आप भेज देंगे'))}</span>
    <button class="icon-btn q-drop">✕ ${L('ਰੱਦ ਕਰੋ', 'Discard', 'रद्द करें')}</button>`;
  $('.q-drop', me).onclick = async () => { await qDel(id); me.remove(); updateQueueBadge(); };
  me.scrollIntoView({ behavior: 'smooth', block: 'end' });
  await updateQueueBadge();
}

async function sendQueued(it) {
  if (it.kind === 'voice') {
    const fd = new FormData();
    fd.append('audio', new Blob([it.audio], { type: 'audio/wav' }), 'speech.wav');
    fd.append('speak', 'false');
    fd.append('lang', it.lang);
    fd.append('recorded_at', String(it.at));
    if (it.pending) fd.append('pending', JSON.stringify(it.pending));
    return post('/api/voice', fd);
  }
  return post('/api/text', { text: it.text, pending: it.pending, speak: false, lang: it.lang, recorded_at: it.at });
}

async function flushQueue() {
  if (flushing || pending) return;   // an open question waits for its answer first
  flushing = true;
  try {
    const items = (await qAll()).sort((a, b) => a.id - b.id);
    for (const it of items) {
      if (pending) break;
      let res;
      try { res = await sendQueued(it); } catch (e) {
        // unreachable, Gnani down/busy/out of credits, or PIN needed: keep it and try again later
        if (QUEUEABLE.includes(e.code) || ['credits', 'auth'].includes(e.code) || e.message === 'PIN required') break;
        // refused for good (e.g. a recording too short): don't block the rest of the queue behind it
        await qDel(it.id);
        const bad = document.querySelector(`.bubble.me[data-qid="${it.id}"]`);
        if (bad) { bad.classList.remove('queued'); $('.q-drop', bad)?.remove(); }
        failBubble(e, null);
        continue;
      }
      await qDel(it.id);
      let me = document.querySelector(`.bubble.me[data-qid="${it.id}"]`);
      if (!me) me = addBubble('me', '');
      me.classList.remove('queued');
      me.innerHTML = `${esc(res.transcript || it.text || '(…)')}<span class="en">🕓 ${esc(tr('ਬੋਲਿਆ', 'said', 'बोला'))} ${hhmm(it.at)}</span>`;
      await afterResult(res);
      await updateQueueBadge();
    }
  } catch (e) {
    console.error(e);
  } finally {
    flushing = false;
    await updateQueueBadge();
  }
}
setInterval(pingServer, 20000);
document.addEventListener('visibilitychange', () => { if (!document.hidden) pingServer(); });

// ------------------------------------------------------------------ PIN lock (phone link)
function showPin(msg = '') {
  $('#pinScreen').hidden = false;
  $('#pinMsg').textContent = msg;
  setTimeout(() => $('#pinInput').focus(), 50);
}
$('#pinForm').onsubmit = async (e) => {
  e.preventDefault();
  const r = await fetch('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pin: $('#pinInput').value }) });
  if (r.ok) { $('#pinScreen').hidden = true; $('#pinInput').value = ''; boot(); return; }
  $('#pinInput').value = '';
  showPin(r.status === 429 ? 'Too many tries. Wait 10 minutes.' : 'ਗਲਤ ਪਿੰਨ · गलत पिन · Wrong PIN');
};

// ------------------------------------------------------------------ offline banner
const setOffline = () => setReachable(reachable);
window.addEventListener('online', setOffline);
window.addEventListener('offline', setOffline);
setOffline();

// ------------------------------------------------------------------ audio
// iPhones only allow audio that a tap started. Play a silent clip on the first tap so later
// replies (which arrive after a network round trip) are allowed to play.
const SILENT = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YQAAAAA=';
let audioUnlocked = false;
function unlockAudio() {
  if (audioUnlocked) return;
  audioUnlocked = true;
  try { audio.src = SILENT; audio.play().catch(() => {}); } catch (_) {}
}
document.addEventListener('pointerdown', unlockAudio, { capture: true });

async function speak(text, btn, voice) {
  try {
    const { audio_url } = await post('/api/tts', { text, voice, lang });
    play(audio_url, btn);
    return audio_url;
  } catch (e) {
    console.warn('tts', e);
    if (!speak.warned && e.code !== 'network') {
      speak.warned = true;
      toast(e.code === 'credits'
        ? tr('ਬੋਲ ਕੇ ਜਵਾਬ ਬੰਦ ਹਨ (Gnani ਕ੍ਰੈਡਿਟ ਖਤਮ)। ਐਂਟਰੀਆਂ ਫਿਰ ਵੀ ਲਿਖੀਆਂ ਜਾ ਰਹੀਆਂ ਹਨ।',
             'Spoken replies are off (Gnani credits used up). Entries are still being saved.',
             'बोलकर जवाब बंद हैं (Gnani क्रेडिट ख़त्म)। एंट्री फिर भी लिखी जा रही हैं।')
        : tr('ਬੋਲ ਕੇ ਜਵਾਬ ਇਸ ਵੇਲੇ ਨਹੀਂ ਚੱਲ ਰਹੇ। ਐਂਟਰੀਆਂ ਫਿਰ ਵੀ ਲਿਖੀਆਂ ਜਾ ਰਹੀਆਂ ਹਨ।',
             'Spoken replies are unavailable right now. Entries are still being saved.',
             'बोलकर जवाब अभी नहीं चल रहे। एंट्री फिर भी लिखी जा रही हैं।'));
    }
  }
}
function play(url, btn) {
  if (!url) return;
  $$('.icon-btn.playing').forEach((b) => b.classList.remove('playing'));
  audio.src = url;
  audio.play().catch(() => {});
  if (btn) {
    btn.classList.add('playing');
    audio.onended = () => btn.classList.remove('playing');
  }
}

// ------------------------------------------------------------------ toast
let toastT;
function toast(html, actionLabel, onAction) {
  const t = $('#toast');
  t.innerHTML = `<span>${html}</span>` + (actionLabel ? `<button>${actionLabel}</button>` : '');
  t.hidden = false;
  if (actionLabel) $('button', t).onclick = () => { t.hidden = true; onAction(); };
  clearTimeout(toastT);
  toastT = setTimeout(() => (t.hidden = true), 5000);
}

// ------------------------------------------------------------------ state + home
async function refresh() {
  state = await api('/api/state');
  const st = state.settings;
  $('#shopName').textContent = (lang === 'en' && st.shop_name_en) || (lang === 'hi' && st.shop_name_hi) || st.shop_name || 'ਬੋਲਦਾ ਖਾਤਾ';
  const t = state.today;
  $('#stats').innerHTML = `
    <div class="stat"><div class="k">ਅੱਜ ਵਿਕਰੀ <span class="en">Sales today</span></div><div class="v">${rs(t.sale)}</div></div>
    <div class="stat"><div class="k">ਪੈਸੇ ਆਏ <span class="en">Collected</span></div><div class="v">${rs(t.payment)}</div></div>
    <div class="stat"><div class="k">ਅੱਜ ਉਧਾਰ <span class="en">Credit given</span></div><div class="v">${rs(t.credit)}</div></div>
    <div class="stat due"><div class="k">ਕੁੱਲ ਬਕਾਇਆ <span class="en">Total due</span></div><div class="v">${rs(state.total_outstanding)}</div></div>`;
  renderCustomers();
  renderHealth();
  if (current) openCustomer(current, false);
}

function renderExamples() {
  if (!$('#examples')) return;
  const list = lang === 'en' ? EXAMPLES_EN : lang === 'hi' ? EXAMPLES_HI : EXAMPLES;
  $('#examples').innerHTML = list.map(([main, sub]) =>
    `<button class="ex" data-t="${esc(main)}">${esc(main)}${sub ? `<span class="en${lang === 'pa' ? ' sub-only' : ''}">${esc(sub)}</span>` : ''}</button>`).join('');
  $$('#examples .ex').forEach((b) => (b.onclick = () => sendText(b.dataset.t)));
}

function addBubble(cls, html) {
  $('#welcome')?.remove();
  const d = document.createElement('div');
  d.className = 'bubble ' + cls;
  d.innerHTML = html;
  $('#feed').appendChild(d);
  d.scrollIntoView({ behavior: 'smooth', block: 'end' });
  return d;
}

const PLAY_IC = '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';
const UNDO_IC = '<svg viewBox="0 0 24 24"><path d="M12.5 8c-2.6 0-5 1-6.9 2.6L2 7v9h9l-3.6-3.6A8 8 0 0 1 20.4 16l2.4-.8A10.5 10.5 0 0 0 12.5 8"/></svg>';
const WA_IC = '<svg viewBox="0 0 24 24"><path d="M17.5 14.4c-.3-.1-1.8-.9-2-1s-.5-.1-.7.1-.8 1-1 1.2-.4.2-.6.1a8 8 0 0 1-4-3.5c-.3-.5.3-.5.9-1.6.1-.2 0-.4 0-.5l-.9-2.2c-.2-.6-.5-.5-.7-.5h-.6a1.2 1.2 0 0 0-.8.4 3.5 3.5 0 0 0-1.1 2.6 6 6 0 0 0 1.3 3.2 13.8 13.8 0 0 0 5.3 4.7c2 .9 2.7.9 3.7.8a3.1 3.1 0 0 0 2.1-1.5 2.6 2.6 0 0 0 .2-1.5c-.1-.1-.3-.2-.6-.3M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2"/></svg>';

function entryCard(t) {
  if (!t) return '';
  const k = KIND[t.kind];
  const cname = (lang === 'en' && t.customer_roman) || (lang === 'hi' && t.customer_hi) || t.customer;
  const who = t.customer ? `<span class="who">${esc(cname)}</span>` : `<span class="who">${L(k.pa, k.en)}</span>`;
  const item = t.item ? `<span class="tag">${esc(t.quantity ? t.quantity + ' ' + (t.unit || '') + ' ' : '')}${esc((lang === 'en' && t.item_roman) || (lang === 'hi' && t.item_hi) || t.item)}</span>` : '';
  return `<div class="entry">
    <div class="entry-row">${who}<span class="amt ${t.kind}">${t.kind === 'credit' ? '+' : t.kind === 'payment' ? '−' : ''}${rs(t.amount)}</span></div>
    <div class="entry-row"><span><span class="tag ${t.kind}">${lang === 'pa' ? `${k.pa} · ${k.en}` : k[lang]}</span> ${item}</span>
      <span class="en">${new Date(t.ts * 1000).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}</span></div>
  </div>`;
}

// a multi-part bill: every line, the total, money received now, change and the new balance
function billCard(b, cname) {
  const lines = (b.text?.[lang] || b.text?.en || []).map((t, i) => {
    const label = t.includes(' = ') ? t.slice(0, t.lastIndexOf(' = ')) : t.slice(0, t.lastIndexOf(' ₹')) || t;
    return `<div class="bill-line"><span>${esc(label)}</span><span>${rs(b.lines[i].amount)}</span></div>`;
  }).join('');
  const row = (label, v, cls = '') => `<div class="bill-line ${cls}"><span>${label}</span><span>${v}</span></div>`;
  let h = `<div class="entry bill">${cname ? `<div class="entry-row"><span class="who">${esc(cname)}</span><span class="tag credit">${L('ਬਿੱਲ', 'Bill', 'बिल')}</span></div>` : ''}${lines}`;
  h += row(L('ਕੁੱਲ', 'Total', 'कुल'), rs(b.total), 'bill-total');
  const got = b.paid_in ?? b.paid;
  if (got) h += row(L('ਹੁਣ ਮਿਲੇ', 'Received now', 'अभी मिले'), '−' + rs(got), 'payment');
  if (b.change) h += row(L('ਵਾਪਸ ਦਿਓ', 'Give back', 'वापस दें'), rs(b.change), 'muted');
  if (b.balance !== undefined) {
    h += row(b.balance >= 0 ? L('ਕੁੱਲ ਬਕਾਇਆ', 'Total due', 'कुल बकाया') : L('ਐਡਵਾਂਸ', 'Advance', 'एडवांस'),
      rs(Math.abs(b.balance)), 'bill-total');
  } else if (!b.paid_in && b.paid !== null && b.paid !== undefined && b.due > 0) {
    h += row(L('ਬਾਕੀ', 'Left', 'बाकी'), rs(b.due), 'credit');
  }
  return h + '</div>';
}

// answer to a smart question: one ruled row per customer / entry, tap a customer to open the account
function listCard(r) {
  const rows = r.rows || [];
  if (!rows.length) return '';
  const tap = (x) => x.customer_id && !r.customer_id;
  let h = '<div class="entry list">' + rows.map((x) => `<div class="bill-line${tap(x) ? ' tap' : ''}${x.low ? ' low' : ''}"${tap(x) ? ` data-cid="${x.customer_id}"` : ''}>
      <span>${esc(x.name[lang] || x.name.en)}${x.sub?.[lang] ? ` <span class="muted-sub">${esc(x.sub[lang])}</span>` : ''}</span><span>${x.qty ? esc(x.qty[lang] || x.qty.en) : rs(x.amount)}</span></div>`).join('');
  if (rows.length > 1 && r.total !== undefined) h += `<div class="bill-line bill-total"><span>${L('ਕੁੱਲ', 'Total', 'कुल')}</span><span>${rs(r.total)}</span></div>`;
  return h + '</div>';
}

async function showReply(res, thinkingEl) {
  const r = res.reply;
  const cmd = res.command;
  const say = r[lang] || r.en;
  let html = `<div class="say">${esc(say)}</div>${lang === 'pa' ? `<span class="en">${esc(r.en)}</span>` : ''}`;
  let txn = null;
  if (r.txn_id) {
    txn = (await api('/api/state')).recent.find((t) => t.id === r.txn_id);
    if (r.bill) {
      const cname = txn?.customer && ((lang === 'en' && txn.customer_roman) || (lang === 'hi' && txn.customer_hi) || txn.customer);
      html += billCard(r.bill, cname);
    } else html += entryCard(txn);
  } else if (r.bill) {
    html += billCard(r.bill, null);
  }
  if (r.action === 'show_list' || r.action === 'stock_set') html += listCard(r);
  const rw = r.risk_warning?.reasons?.[0];
  if (rw) html += `<div class="warn">⚠️ ${esc(rw.pa || '')} ${EN(rw.en || '', rw.hi)}</div>`;
  if (r.action === 'choose_customer') {
    html += `<div class="choices">${r.candidates.map((c) => `<button data-id="${c.id}">${esc(c.name)}</button>`).join('')}
      <button data-new="1">+ ਨਵਾਂ <span class="en">new</span></button></div>`;
  }
  if (r.amount_choices) {
    html += `<div class="choices">${r.amount_choices.map((v) => `<button data-amount="${v}">${rs(v)}</button>`).join('')}</div>`;
  }
  if (r.action === 'confirm_heard') {
    html += `<div class="choices"><button data-confirm="1">✓ ਠੀਕ ਹੈ <span class="en">yes, save</span></button>
      <button data-cancel="1">✗ ਦੁਬਾਰਾ ਬੋਲਾਂਗਾ <span class="en">no, I'll repeat</span></button></div>`;
  }
  if (r.action === 'ask_change') {
    html += `<div class="choices"><button data-extra="change">↩ ${L(`${rs(r.extra)} ਵਾਪਸ ਦਿੱਤੇ`, `Gave ${rs(r.extra)} back`, `${rs(r.extra)} वापस दिए`)}</button>
      <button data-extra="advance">＋ ${L('ਐਡਵਾਂਸ ਰੱਖੋ', 'Keep as advance', 'एडवांस रखें')}</button></div>`;
  }
  if (r.action === 'confirm_direction') {
    html += `<div class="choices"><button data-intent="PAYMENT">− ਜਮ੍ਹਾ <span class="en">received</span></button>
      <button data-intent="CREDIT">+ ਉਧਾਰ <span class="en">credit</span></button></div>`;
  }
  html += `<div class="bot-actions"><button class="icon-btn play">${PLAY_IC}${L('ਸੁਣੋ', 'Play', 'सुनें')}</button>`;
  if (r.txn_id) html += `<button class="icon-btn undo">${UNDO_IC}${L('ਵਾਪਸ', 'Undo', 'वापस')}</button>`;
  if (r.stock_move_ids?.length) html += `<button class="icon-btn stock-undo">${UNDO_IC}${L('ਵਾਪਸ', 'Undo', 'वापस')}</button>`;
  if (r.customer_id) html += `<button class="icon-btn open">ਖਾਤਾ <span class="en">open</span></button>`;
  if (r.action === 'show_customers') html += `<button class="icon-btn goto" data-v="customers">${L('ਸਾਰੇ ਗਾਹਕ', 'All customers')}</button>`;
  if (r.action === 'show_insights') html += `<button class="icon-btn goto" data-v="insights">${L('ਸੂਝ ਦੇਖੋ', 'See insights')}</button>`;
  if (cmd?.intent === 'QUERY' || cmd?.intent === 'STOCK') html += `<span class="engine">${L('ਖਾਤੇ ਤੋਂ ਸਿੱਧਾ ਹਿਸਾਬ', 'exact, from the ledger', 'खाते से सीधा हिसाब')}</span>`;
  else if (cmd) html += `<span class="engine">${cmd.engine === 'evon' ? 'Evon' : cmd.engine === 'muril+memm' ? 'MuRIL+MEMM' : 'on-device'} · ${Math.round(cmd.confidence * 100)}%</span>`;
  html += `</div>`;
  (r.reminders || []).forEach((rem) => {
    html += `<div class="entry"><div class="entry-row"><span class="who">${esc(rem.name)}</span><span class="amt credit">${rs(rem.balance)}</span></div>
      <div class="entry-row" style="display:block"><div>${esc(rem[lang] || rem.en)}</div>${lang === 'pa' ? `<span class="en">${esc(rem.en)}</span>` : ''}
      <div class="bot-actions"><button class="icon-btn rem" data-cid="${rem.customer_id}">${PLAY_IC}${L('ਯਾਦ-ਸੁਨੇਹਾ ਸੁਣੋ', 'Play reminder')}</button>
      <button class="icon-btn wa" data-cid="${rem.customer_id}">${WA_IC}${L('ਵਟਸਐਪ', 'WhatsApp')}</button></div></div></div>`;
  });

  const el = thinkingEl || addBubble('bot', '');
  el.className = 'bubble bot';
  el.innerHTML = html;
  el.scrollIntoView({ behavior: 'smooth', block: 'end' });

  const playBtn = $('.play', el);
  playBtn.onclick = () => (res.audio_url ? play(res.audio_url, playBtn) : speak(say, playBtn).then((u) => (res.audio_url = u)));
  if (res.audio_url) play(res.audio_url, playBtn);
  else speak(say, playBtn).then((u) => (res.audio_url = u));

  $('.undo', el)?.addEventListener('click', async (e) => {
    await api(`/api/txns/${r.txn_id}`, { method: 'DELETE' });
    e.currentTarget.disabled = true;
    $('.entry', el)?.style.setProperty('opacity', '.4');
    toast('ਐਂਟਰੀ ਕੱਟ ਦਿੱਤੀ <span class="en">Entry removed</span>', tr('ਮੁੜ ਲਿਆਓ', 'Restore'), async () => {
      await post(`/api/txns/${r.txn_id}/restore`, {}); $('.entry', el)?.style.removeProperty('opacity'); refresh();
    });
    refresh();
  });
  $('.open', el)?.addEventListener('click', () => openCustomer(r.customer_id));
  $$('.list .tap', el).forEach((row) => (row.onclick = () => openCustomer(+row.dataset.cid)));
  $('.stock-undo', el)?.addEventListener('click', async (e) => {
    const btn = e.currentTarget;
    for (const id of r.stock_move_ids) await post(`/api/stock/undo/${id}`, {});
    btn.disabled = true;
    $('.entry', el)?.style.setProperty('opacity', '.4');
    toast(tr('ਸਟਾਕ ਦੀ ਗਿਣਤੀ ਕੱਟ ਦਿੱਤੀ', 'Stock count removed', 'स्टॉक की गिनती हटा दी'), tr('ਮੁੜ ਲਿਆਓ', 'Restore'), async () => {
      for (const id of r.stock_move_ids) await post(`/api/stock/undo/${id}`, { restore: true });
      $('.entry', el)?.style.removeProperty('opacity');
    });
  });
  $$('.goto', el).forEach((b) => (b.onclick = () => switchView(b.dataset.v)));
  $$('.choices button', el).forEach((b) => (b.onclick = async () => {
    let body = { pending: r.pending };
    if (b.dataset.cancel) {
      pending = null;
      $$('.choices button', el).forEach((x) => (x.disabled = true));
      toast('ਨਹੀਂ ਲਿਖਿਆ, ਦੁਬਾਰਾ ਬੋਲੋ <span class="en">Nothing saved, say it again</span>');
      return;
    }
    if (b.dataset.extra) body.extra = b.dataset.extra;
    else if (b.dataset.amount) body.amount = +b.dataset.amount;
    else if (b.dataset.confirm) body.confirm = true;
    else if (b.dataset.intent) body.intent = b.dataset.intent;
    else if (b.dataset.id) body.customer_id = +b.dataset.id;
    else body.new_name = r.pending.customer.name;
    pending = null;
    $$('.choices button', el).forEach((x) => (x.disabled = true));   // one answer only: no double entries
    const think = addBubble('bot thinking', '<span class="dots"><span></span><span></span><span></span></span>');
    const res2 = await post('/api/resolve', { ...body, speak: false, lang });
    await showReply(res2, think);
    refresh();
  }));
  $$('.rem', el).forEach((b) => (b.onclick = () => playReminder(+b.dataset.cid, b)));
  $$('.wa', el).forEach((b) => (b.onclick = () => shareReminder(+b.dataset.cid)));

  pending = ['ask_amount', 'ask_customer', 'choose_customer', 'confirm_direction', 'confirm_heard', 'ask_change'].includes(r.action) ? r.pending : null;
  if (r.txn_id || r.action === 'undone') refresh();
  if (!pending && queueCount && !flushing) flushQueue();   // a question from the queue was answered: carry on
}

// ------------------------------------------------------------------ hood (desktop pipeline view)
function hood(step, status, ms) {
  const li = $(`#pipeline li[data-step="${step}"]`);
  if (!li) return;
  li.classList.remove('run', 'done', 'skip');
  if (status) li.classList.add(status);
  $('em', li).textContent = ms != null ? `${ms} ms` : '';
}
function hoodReset() { ['mic', 'stt', 'nlu', 'evon', 'ledger', 'tts'].forEach((s) => hood(s, null)); }
function hoodDetail(res) {
  const c = res.command;
  if (!c) return;
  const toks = (c.local.tokens || []).map((t, i) => {
    const tag = (c.local.tags || [])[i] || 'O';
    const cls = tag === 'O' ? (/^[\d₹]/.test(t) ? 'NUM' : '') : tag.slice(2);
    return `<span class="tok ${cls}">${esc(t)}</span>`;
  }).join('');
  const alts = (c.local.alternatives || []).map(([k, p]) => `${k} ${Math.round(p * 100)}%`).join(', ');
  $('#hoodDetail').innerHTML = `
    <div><b>Transcript</b> <span class="muted">(${esc(res.transcript_roman || '')})</span></div>
    <div style="font-family:var(--pa);font-size:16px;margin:4px 0 10px">${esc(res.transcript)}</div>
    <div><b>Slot tagger</b> <span class="muted">blue = name, yellow = item, green = number</span></div>
    <div style="margin:4px 0 10px">${toks}</div>
    <div><b>Intent</b>: ${esc(c.local.intent)} ${Math.round(c.local.confidence * 100)}% <span class="muted">(next: ${esc(alts)})</span></div>
    <div><b>Masked input</b>: <span style="font-family:var(--pa)">${esc(c.local.masked)}</span></div>
    ${c.audio_check ? `<div><b>Audio check</b>: est. SNR ${c.audio_check.snr_db} dB, P(misheard) ${Math.round(c.audio_check.p_wrong * 100)}% ${c.audio_check.unsure ? '→ <b>read back &amp; confirm</b>' : '→ ok'}</div>` : ''}
    <div><b>Engine used</b>: ${c.engine === 'evon' ? 'Gnani Evon 30B' : c.engine === 'muril+memm' ? 'MuRIL transformer + MEMM ensemble' : 'on-device MEMM'}${c.evon_error ? ` <span class="muted">(Evon error: ${esc(c.evon_error)})</span>` : ''}</div>
    <pre>${esc(JSON.stringify({ intent: c.intent, customer: c.customer.name, match: c.customer.status, amount: c.amount, item: c.item, qty: c.quantity, day_offset: c.day_offset }, null, 1))}</pre>`;
}

// ------------------------------------------------------------------ voice + text
const rec = new Recorder({
  onLevel: (v) => { $('#ring').style.transform = `scale(${1 + v * 0.35})`; },
  onNoisy: (noisy) => {
    if (!recording) return;
    $('#liveText').textContent = noisy ? tr('ਰੌਲਾ ਜ਼ਿਆਦਾ ਹੈ, ਫ਼ੋਨ ਮੂੰਹ ਦੇ ਨੇੜੇ ਕਰੋ', 'Too noisy, hold the phone closer')
      : tr('ਸੁਣ ਰਿਹਾ ਹਾਂ… ਬੋਲੋ', 'Listening… speak now');
    $('#live').classList.toggle('noisy', noisy);
  },
  onAutoStop: () => stopRec(),
});
let recording = false;

async function startRec() {
  try {
    audio.pause();
    await rec.start();
    recording = true;
    $('#mic').classList.add('rec');
    $('#live').hidden = false;
    $('#liveText').textContent = pending ? tr('ਦੱਸੋ… (ਜਵਾਬ ਉਡੀਕ ਰਿਹਾ)', 'Go ahead… (waiting for your answer)')
      : tr('ਸੁਣ ਰਿਹਾ ਹਾਂ… ਬੋਲੋ', 'Listening… speak now');
    hoodReset(); hood('mic', 'run');
  } catch (e) {
    toast('ਮਾਈਕ ਨਹੀਂ ਚੱਲਿਆ <span class="en">Microphone permission needed</span>');
    console.error(e);
  }
}

async function stopRec() {
  if (!recording) return;
  recording = false;
  $('#mic').classList.remove('rec');
  $('#live').hidden = true;
  const out = await rec.stop();
  if (!out || out.seconds < 0.4 || !out.heardSpeech) {
    hood('mic', null);
    toast('ਕੁਝ ਸੁਣਾਈ ਨਹੀਂ ਦਿੱਤਾ <span class="en">Didn’t hear anything</span>');
    return;
  }
  hood('mic', 'done', Math.round(out.seconds * 1000));
  sendVoice(out.blob, pending);
}

async function sendVoice(blob, pendingAtRecord, at = Date.now()) {
  const fd = new FormData();
  fd.append('audio', blob, 'speech.wav');
  fd.append('speak', 'false');
  fd.append('lang', lang);
  fd.append('recorded_at', String(at));
  if (pendingAtRecord) fd.append('pending', JSON.stringify(pendingAtRecord));
  const me = addBubble('me', '<span class="dots"><span></span><span></span><span></span></span>');
  if (queueCount) {   // older entries are still waiting: keep the order, this one goes behind them
    try { await enqueue({ kind: 'voice', blob, lang, pending: pendingAtRecord || null, at }, me); flushQueue(); return; }
    catch (_) { /* no storage on this phone: send directly */ }
  }
  $('#mic').classList.add('busy');
  hood('stt', 'run');
  try {
    const res = await post('/api/voice', fd);
    const roman = res.transcript_roman && res.transcript_roman !== res.transcript ? `<span class="en">${esc(res.transcript_roman)}</span>` : '';
    me.innerHTML = res.transcript ? `${esc(res.transcript)}${roman}` : '(…)';
    await afterResult(res);
  } catch (e) {
    if (QUEUEABLE.includes(e.code)) {
      try {
        await enqueue({ kind: 'voice', blob, lang, pending: pendingAtRecord || null, at }, me);
        if (pendingAtRecord) pending = null;   // the answer travels with the queued recording
        return;
      } catch (_) { /* no storage: fall back to the retry bubble */ }
    }
    me.innerHTML = `🎙 <span class="muted">${esc(tr('ਆਵਾਜ਼ ਰਿਕਾਰਡ ਹੋਈ, ਭੇਜੀ ਨਹੀਂ ਗਈ', 'Recorded, not sent', 'आवाज़ रिकॉर्ड हुई, भेजी नहीं गई'))}</span>`;
    failBubble(e, () => { me.remove(); sendVoice(blob, pendingAtRecord, at); });
  } finally {
    $('#mic').classList.remove('busy');
  }
}

async function sendText(text, at = Date.now()) {
  if (!text.trim()) return;
  const me = addBubble('me', esc(text));
  hoodReset(); hood('mic', 'skip'); hood('stt', 'skip');
  const p = pending;
  if (queueCount) {   // keep the order behind entries already waiting
    try { await enqueue({ kind: 'text', text, lang, pending: p, at }, me); pending = null; flushQueue(); return; }
    catch (_) { /* no storage: send directly */ }
  }
  const think = addBubble('bot thinking', '<span class="dots"><span></span><span></span><span></span></span>');
  try {
    const res = await post('/api/text', { text, pending: p, speak: false, lang, recorded_at: at });
    await afterResult(res, think);
  } catch (e) {
    if (QUEUEABLE.includes(e.code)) {
      try { think.remove(); await enqueue({ kind: 'text', text, lang, pending: p, at }, me); pending = null; return; }
      catch (_) { /* no storage: retry bubble below */ }
    }
    failBubble(e, () => { me.remove(); sendText(text, at); }, think.isConnected ? think : null);
  }
}

async function afterResult(res, thinkEl) {
  const t = res.timings || {};
  if (t.stt_ms != null) hood('stt', 'done', t.stt_ms);
  if (res.command) {
    hood('nlu', 'done', t.local_nlu_ms != null ? Math.max(1, Math.round(t.local_nlu_ms)) : null);
    hood('evon', res.command.engine === 'evon' ? 'done' : 'skip', res.command.engine === 'evon' ? t.nlu_ms : null);
    hood('ledger', 'done');
    hoodDetail(res);
  }
  hood('tts', 'run');
  const t0 = performance.now();
  await showReply(res, thinkEl);
  const wait = setInterval(() => { if (res.audio_url) { hood('tts', 'done', Math.round(performance.now() - t0)); clearInterval(wait); } }, 100);
  setTimeout(() => clearInterval(wait), 15000);
}

$('#mic').onclick = () => (recording ? stopRec() : startRec());
document.addEventListener('keydown', (e) => {
  if (e.code === 'Space' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName) && !$('#view-test').classList.contains('active')) {
    e.preventDefault(); recording ? stopRec() : startRec();
  }
});
$('#typeForm').onsubmit = (e) => {
  e.preventDefault();
  const v = $('#typeInput').value;
  $('#typeInput').value = '';
  switchView('home');
  sendText(v);
};

// ------------------------------------------------------------------ views
function switchView(v) {
  $$('.view').forEach((x) => x.classList.toggle('active', x.id === 'view-' + v));
  $$('#tabs button').forEach((b) => b.classList.toggle('active', b.dataset.view === v));
  if (v === 'insights') renderInsights();
  if (v === 'customers') renderCustomers();
}
$$('#tabs button').forEach((b) => (b.onclick = () => switchView(b.dataset.view)));

function badge(score) {
  if (!score || score.trust == null) return `<span class="badge new">${tr('ਨਵਾਂ', 'New')}</span>`;
  return `<span class="badge ${score.band.key}">${score.trust} · ${esc(tr(score.band.pa, score.band.en, score.band.hi))}</span>`;
}
function ago(ts) {
  if (!ts) return '';
  const d = Math.floor((Date.now() / 1000 - ts) / 86400);
  return d <= 0 ? tr('ਅੱਜ', 'today', 'आज') : d === 1 ? tr('ਕੱਲ੍ਹ', 'yesterday', 'कल') : tr(`${d} ਦਿਨ ਪਹਿਲਾਂ`, `${d} days ago`, `${d} दिन पहले`);
}

function renderCustomers() {
  if (!state) return;
  const q = $('#search').value.trim().toLowerCase();
  const list = state.customers.filter((c) => !q || c.name.toLowerCase().includes(q) || (c.name_roman || '').toLowerCase().includes(q));
  const owed = state.customers.filter((c) => c.balance > 0);
  $('#totalBanner').innerHTML = `<div>ਕੁੱਲ ਬਕਾਇਆ ${EN(`Total due · ${owed.length} customers`, `कुल बकाया · ${owed.length} ग्राहक`)}</div><div class="amt credit" style="font-size:20px">${rs(state.total_outstanding)}</div>`;
  $('#custList').innerHTML = list.length ? list.map((c) => `
    <li class="cust" data-id="${c.id}">
      <div class="avatar">${esc([...c.name][0])}</div>
      <div class="meta"><div class="nm">${esc(c.name)} ${c.name_roman !== c.name ? EN(c.name_roman, c.name_hi) : ''}</div>
        <div class="en sub-meta keep-en">${ago(c.last_ts)}${c.phone ? ' · ' + esc(c.phone) : ''}</div></div>
      <div class="right"><div class="amt ${c.balance > 0 ? 'credit' : 'payment'}">${c.balance === 0 ? '✓' : rs(Math.abs(c.balance))}</div>${badge(c.score)}</div>
    </li>`).join('') : `<li class="empty">ਹਾਲੇ ਕੋਈ ਗਾਹਕ ਨਹੀਂ। ਮਾਈਕ ਦਬਾ ਕੇ ਪਹਿਲੀ ਐਂਟਰੀ ਬੋਲੋ।<br><span class="en">No customers yet. Speak your first entry.</span></li>`;
  $$('#custList .cust').forEach((li) => (li.onclick = () => openCustomer(+li.dataset.id)));
}
$('#search').oninput = renderCustomers;

function gauge(trust, key) {
  const v = trust ?? 0;
  const col = { good: 'var(--green)', watch: 'var(--amber)', risky: 'var(--danger)', new: 'var(--ink-2)' }[key];
  const C = 2 * Math.PI * 34;
  return `<svg class="gauge" viewBox="0 0 84 84"><circle cx="42" cy="42" r="34" fill="none" stroke="var(--paper-2)" stroke-width="9"/>
    <circle cx="42" cy="42" r="34" fill="none" stroke="${col}" stroke-width="9" stroke-linecap="round" stroke-dasharray="${(C * v) / 100} ${C}" transform="rotate(-90 42 42)"/>
    <text x="42" y="48" text-anchor="middle" font-family="Inter" font-weight="800" font-size="20" fill="var(--ink)">${trust ?? '–'}</text></svg>`;
}

async function openCustomer(id, animate = true) {
  current = id;
  const d = await api(`/api/customers/${id}`);
  const c = d.customer, s = d.score;
  const sheet = $('#sheet');
  sheet.innerHTML = `<div class="grabber"></div>
    <div class="sheet-head"><div class="avatar" style="width:52px;height:52px;font-size:24px">${esc([...c.name][0])}</div>
      <div style="flex:1;min-width:0"><h2>${esc(lang === 'en' ? c.name_roman : lang === 'hi' ? c.name_hi : c.name)}</h2>${lang === 'pa' && c.name_roman !== c.name ? `<div class="en">${esc(c.name_roman)}</div>` : ''}</div>
      <button class="icon-btn" id="closeSheet">✕</button></div>
    <div class="card" style="display:flex;justify-content:space-between;align-items:center">
      <div><div class="muted">${c.balance >= 0 ? 'ਬਕਾਇਆ' : 'ਐਡਵਾਂਸ'} ${EN(c.balance >= 0 ? 'Balance due' : 'Advance')}</div>
        <div class="bal-big ${c.balance > 0 ? 'amt credit' : 'amt payment'}">${rs(Math.abs(c.balance))}</div></div>
      ${c.balance > 0 ? `<button class="btn gold" id="remBtn">🔔 ਯਾਦ-ਸੁਨੇਹਾ<br><span class="en">Voice reminder</span></button>` : ''}
    </div>
    <div class="card"><h3>ਭਰੋਸਾ ਸਕੋਰ <span class="en">Trust score (ML)</span></h3>
      <div class="trust">${gauge(s.trust, s.band.key)}
        <div><div style="font-weight:700;font-size:18px">${esc(s.band.pa)} ${EN(s.band.en, s.band.hi)}</div>
          ${s.suggested_limit != null && s.trust != null ? `<div class="muted" style="font-size:14px">ਸੁਝਾਈ ਹੋਰ ਉਧਾਰ ਹੱਦ <span class="en">Suggested further credit</span>: <b class="num">${rs(s.suggested_limit)}</b></div>` : ''}
          ${s.typical_repay_days ? `<div class="muted" style="font-size:14px">ਆਮ ਤੌਰ ਤੇ <b class="num">${s.typical_repay_days}</b> ਦਿਨਾਂ ਵਿੱਚ ਮੋੜਦਾ ${EN(`usually repays in ${s.typical_repay_days} days`, `आम तौर पर ${s.typical_repay_days} दिन में लौटाता है`)}</div>` : ''}
          ${s.low_data ? `<div class="en">Limited history so far, score will sharpen with use.</div>` : ''}</div></div>
      <ul class="reasons">${(s.reasons || []).map((r) => `<li>${esc(r.pa)} ${EN(r.en, r.hi)}</li>`).join('')}
        ${(s.strengths || []).map((r) => `<li class="plus">${esc(r.pa)} ${EN(r.en, r.hi)}</li>`).join('')}</ul>
    </div>
    <div class="card"><h3>ਹੱਥੀਂ ਐਂਟਰੀ <span class="en">Manual entry</span></h3>
      <form class="manual" id="manualForm"><input id="manAmt" type="number" min="1" step="1" inputmode="numeric" placeholder="${tr('₹ ਰਕਮ', '₹ amount', '₹ रकम')}" required>
        <button class="btn primary" data-k="credit" type="submit">+ ${L('ਉਧਾਰ', 'Credit', 'उधार')}</button><button class="btn green" data-k="payment" type="submit">− ${L('ਜਮ੍ਹਾ', 'Paid', 'जमा')}</button></form>
      <div class="phone-row" style="margin-top:10px"><input id="phoneIn" inputmode="tel" placeholder="ਫ਼ੋਨ ਨੰਬਰ / phone for WhatsApp" value="${esc(c.phone || '')}"><button class="btn" id="phoneSave">${L('ਸੰਭਾਲੋ', 'Save')}</button></div>
    </div>
    <div class="card"><h3>ਖਾਤਾ <span class="en">Ledger</span></h3>
      <ul class="timeline">${d.txns.map((t) => `<li>
        <div><span class="tag ${t.kind}">${esc(tr(KIND[t.kind].pa, KIND[t.kind].en, KIND[t.kind].hi))}</span> ${t.item ? esc((lang === 'en' && t.item_roman) || (lang === 'hi' && t.item_hi) || t.item) : ''}<div class="when">${new Date(t.ts * 1000).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })} · ${t.source}</div></div>
        <div style="text-align:right"><div class="amt ${t.kind}">${t.kind === 'credit' ? '+' : '−'}${rs(t.amount)}</div><div class="after">bal ${rs(t.balance_after)}</div></div></li>`).join('') || '<li class="empty">—</li>'}</ul>
    </div>`;
  $('#sheetBackdrop').hidden = false;
  requestAnimationFrame(() => sheet.classList.add('open'));
  $('#closeSheet').onclick = closeSheet;
  $('#remBtn')?.addEventListener('click', (e) => playReminder(id, e.currentTarget, true));
  let kind = 'credit';
  $$('#manualForm button').forEach((b) => (b.onclick = () => (kind = b.dataset.k)));
  $('#manualForm').onsubmit = async (e) => {
    e.preventDefault();
    await post('/api/txns', { kind, amount: +$('#manAmt').value, customer_id: id });
    toast(kind === 'credit' ? 'ਉਧਾਰ ਲਿਖਿਆ <span class="en">Credit added</span>' : 'ਜਮ੍ਹਾ ਹੋਇਆ <span class="en">Payment added</span>');
    refresh();
  };
  $('#phoneSave').onclick = async () => {
    await api(`/api/customers/${id}`, { method: 'PATCH', body: JSON.stringify({ phone: $('#phoneIn').value }) });
    toast('ਫ਼ੋਨ ਸੰਭਾਲਿਆ <span class="en">Phone saved</span>'); refresh();
  };
}
function closeSheet() {
  current = null;
  $('#sheet').classList.remove('open');
  setTimeout(() => ($('#sheetBackdrop').hidden = true), 250);
}
$('#sheetBackdrop').onclick = closeSheet;

const reminders = {};
async function playReminder(cid, btn, offerShare = false) {
  btn?.classList.add('playing');
  try {
    const key = cid + ':' + lang;
    const rem = reminders[key] || (reminders[key] = await post(`/api/reminders/${cid}?lang=${lang}`, {}));
    play(rem.audio_url, btn);
    if (offerShare) toast(`${esc(rem.tone === 'firm' ? 'ਪੱਕਾ ਸੁਨੇਹਾ' : 'ਨਰਮ ਸੁਨੇਹਾ')} ${EN(`${rem.tone} tone, chosen by risk score`, rem.tone === 'firm' ? 'सख़्त लहजा, रिस्क स्कोर से चुना' : 'नरम लहजा, रिस्क स्कोर से चुना')}`, tr('ਵਟਸਐਪ', 'WhatsApp'), () => shareReminder(cid));
  } catch (e) { btn?.classList.remove('playing'); toast(esc(e.message)); }
}
async function shareReminder(cid) {
  const key = cid + ':' + lang;
  const rem = reminders[key] || (reminders[key] = await post(`/api/reminders/${cid}?lang=${lang}`, {}));
  try {
    const blob = await (await fetch(rem.audio_url)).blob();
    const file = new File([blob], `reminder-${cid}.wav`, { type: 'audio/wav' });
    if (navigator.canShare?.({ files: [file] })) {
      await navigator.share({ files: [file], text: rem[lang] || rem.en });
      return;
    }
  } catch (_) {}
  window.open(rem.whatsapp_url, '_blank', 'noopener');
}

// ------------------------------------------------------------------ insights
function chart(daily) {
  const W = 440, H = 170, P = 26, n = daily.length;
  const max = Math.max(100, ...daily.map((d) => Math.max(d.sale + d.payment, d.credit)));
  const bw = (W - P - 6) / n;
  const y = (v) => H - 18 - (v / max) * (H - 30);
  let bars = '';
  daily.forEach((d, i) => {
    const x = P + i * bw;
    const hs = (d.sale / max) * (H - 30), hp = (d.payment / max) * (H - 30);
    bars += `<rect x="${x + 1}" y="${H - 18 - hs}" width="${bw * 0.62}" height="${hs}" fill="var(--green)" rx="1.5"><title>${d.date} sales ${rs(d.sale)}</title></rect>`;
    bars += `<rect x="${x + 1}" y="${H - 18 - hs - hp}" width="${bw * 0.62}" height="${hp}" fill="#7fbf95" rx="1.5"><title>${d.date} collected ${rs(d.payment)}</title></rect>`;
  });
  const line = daily.map((d, i) => `${P + i * bw + bw * 0.31},${y(d.credit)}`).join(' ');
  const labels = [0, Math.floor(n / 2), n - 1].map((i, k) => `<text x="${k === 2 ? W - 2 : P + i * bw}" y="${H - 4}" font-size="10" fill="var(--ink-2)" font-family="Inter" text-anchor="${k === 2 ? 'end' : 'start'}">${daily[i].date.slice(5)}</text>`).join('');
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="30 day cash flow">
    <line x1="${P}" x2="${W}" y1="${H - 18}" y2="${H - 18}" stroke="var(--line)"/>
    <text x="0" y="12" font-size="10" fill="var(--ink-2)" font-family="Inter">${rs(max)}</text>
    ${bars}<polyline points="${line}" fill="none" stroke="var(--danger)" stroke-width="2" stroke-linejoin="round"/>${labels}</svg>`;
}

async function renderInsights() {
  const el = $('#insights');
  el.innerHTML = '<div class="empty"><span class="dots"><span></span><span></span><span></span></span></div>';
  const [d, st] = await Promise.all([api('/api/insights'), api('/api/stock').catch(() => ({ items: [] }))]);
  const stockCard = `<div class="card"><h3>ਸਟਾਕ <span class="en">Stock</span></h3>
      ${st.items.length ? `<div class="entry list" style="margin-top:0">${st.items.map((x) => `<div class="bill-line${x.low ? ' low' : ''}">
        <span>${esc(x.name[lang] || x.name.en)}${x.low ? ` <span class="muted-sub">${esc(x.sub[lang] || x.sub.en)}</span>` : ''}</span><span>${esc(x.qty[lang] || x.qty.en)}</span></div>`).join('')}</div>`
        : `<p class="muted">${esc(tr('ਹਾਲੇ ਕੋਈ ਸਟਾਕ ਨਹੀਂ। ਬੋਲੋ: “ਆਟੇ ਦਾ ਸਟਾਕ 20 ਬੋਰੀਆਂ ਹੈ”। ਥੋਕ ਤੋਂ ਆਇਆ ਮਾਲ ਆਪੇ ਜੁੜਦਾ ਹੈ।',
          'No stock yet. Say: “stock of flour is 20 sacks”. Goods bought from the wholesaler are added by themselves.',
          'अभी कोई स्टॉक नहीं। बोलिए: “आटे का स्टॉक 20 बोरियां है”। थोक से आया माल अपने आप जुड़ता है।'))}</p>`}</div>`;
  const risky = d.customers.filter((c) => c.balance > 0 && c.score.band?.key === 'risky');
  const watch = d.customers.filter((c) => c.balance > 0 && c.score.band?.key === 'watch');
  const m = d.models || {};
  const rr = m.risk_report?.test, nc = m.nlu_comparison;
  const pct = (x) => (x == null ? '–' : Math.round(x * 1000) / 10 + '%');
  el.innerHTML = `
    <div class="kpis">
      <div class="kpi"><div class="k">ਕੁੱਲ ਬਕਾਇਆ <span class="en">Outstanding</span></div><div class="v">${rs(d.total_outstanding)}</div></div>
      <div class="kpi"><div class="k">ਇਸ ਹਫ਼ਤੇ ਆਉਣ ਦੀ ਉਮੀਦ <span class="en">Expected in 7 days</span></div><div class="v" style="color:var(--green)">${rs(d.expected_collections_7d)}</div></div>
      <div class="kpi wide"><div class="k">ਖਤਰੇ ਵਿੱਚ ਪੈਸਾ <span class="en">Money at risk (ML)</span></div>
        <div class="v" style="color:var(--danger)">${rs(d.at_risk)} ${EN(`${Math.round(d.at_risk_share * 100)}% of dues`, `बकाये का ${Math.round(d.at_risk_share * 100)}%`)}</div>
        <div class="bar"><i style="width:${Math.round(d.at_risk_share * 100)}%"></i></div></div>
    </div>
    <div class="card chart"><h3>30 ਦਿਨ <span class="en">Last 30 days</span></h3>${chart(d.daily)}
      <div class="legend"><span><i style="background:var(--green)"></i>ਨਕਦ ਵਿਕਰੀ <span class="en">sales</span></span>
      <span><i style="background:#7fbf95"></i>ਉਧਾਰ ਵਾਪਸੀ <span class="en">collected</span></span>
      <span><i style="background:var(--danger)"></i>ਉਧਾਰ ਦਿੱਤਾ <span class="en">credit given</span></span></div></div>
    <div class="card"><h3>ਧਿਆਨ ਦਿਓ <span class="en">Needs attention</span></h3>
      <ul class="cust-list" style="box-shadow:none">${[...risky, ...watch].slice(0, 8).map((c) => `
        <li class="cust" data-id="${c.id}"><div class="avatar">${esc([...c.name][0])}</div>
          <div class="meta"><div class="nm">${esc(c.name)} ${c.name_roman !== c.name ? EN(c.name_roman, c.name_hi) : ''}</div>
          ${EN(c.score.reasons?.[0]?.en || '', c.score.reasons?.[0]?.hi, ' sub-meta')}</div>
          <div class="right"><div class="amt credit">${rs(c.balance)}</div>${badge(c.score)}</div></li>`).join('') || '<li class="empty">ਸਭ ਠੀਕ ਹੈ 👍 <span class="en">Nobody risky right now</span></li>'}</ul></div>
    ${stockCard}
    <div class="card"><h3>ਮਾਡਲ <span class="en">Models behind this</span></h3><div class="model-grid">
      ${rr ? `<div class="metric"><span>Credit-risk model (gradient boosting) AUC</span><b>${rr.gradient_boosting.auc}</b></div>
        <div class="metric"><span class="muted">vs shopkeeper rule "oldest dues"</span><b>${rr.rule_oldest_dues.auc}</b></div>` : ''}
      ${m.real_report?.n ? (() => { const g = m.real_report.groups.all, n = g.n;
        return `<div class="metric"><span><b>Real voices</b> (${n} recordings): understood correctly</span><b>${pct((g.understood ?? g.correct) / n)}</b></div>
        <div class="metric"><span class="muted">…acted right / asked back first / wrong without asking</span><b>${g.correct ?? 0} / ${(g.asked_needed ?? 0) + (g.asked_unneeded ?? 0)} / ${g.wrong_silent ?? 0}</b></div>`; })() : ''}
      ${nc ? `<div class="metric"><span>Language model in use</span><b>MuRIL transformer + MEMM</b></div>
        <div class="metric"><span>Hard test (${nc.n} messy commands), text</span><b>${pct(nc.conditions.text?.ensemble.fully_correct)}</b></div>
        <div class="metric"><span>…spoken by Timbre → Prisma, clean</span><b>${pct(nc.conditions.clean?.ensemble.fully_correct)}</b></div>
        <div class="metric"><span>…in a noisy shop (8 dB)</span><b>${pct(nc.conditions.noisy?.ensemble.fully_correct)}</b></div>
        ${nc.conditions.loud ? `<div class="metric"><span>…with chatter as loud as the voice (0 dB)</span><b>${pct(nc.conditions.loud.ensemble.fully_correct)}</b></div>` : ''}
        <div class="metric"><span>Customer identified correctly (noisy)</span><b>${pct(nc.conditions.noisy?.ensemble.customer_acc)}</b></div>
        <div class="metric"><span>Credit/payment mix-ups saved (noisy)</span><b>${nc.direction_check?.noisy?.wrong_direction_saved ?? '–'} <span class="en">(asks when unsure)</span></b></div>` : ''}
      ${m.repeat_report?.all_safeguards ? (() => { const a = m.repeat_report.all_safeguards_loud_only || m.repeat_report.all_safeguards; const row = (k, label) =>
        `<div class="metric"><span>Wrong entries saved without asking, ${label}</span><b>${a[k].wrong_writes_saved} / ${a[k].wrong_writes_without_detector}</b></div>`;
        return row('noisy', 'busy shop') + row('loud', 'very loud') +
          `<div class="metric"><span class="muted">"Did I hear that right?" detector (loud audio only), cross-validated</span><b>${a.noisy.correct_but_asked_to_repeat} taps / ${a.noisy.writes} in busy shop</b></div>`; })() : ''}
      <div class="metric"><span>Speech</span><b>Gnani Prisma v3.0 · Timbre</b></div>
      <div class="metric"><span>Language model</span><b>${state?.health?.evon ? 'Gnani Evon 30B ✓' : 'Evon: not connected'}</b></div>
    </div></div>`;
  $$('#insights .cust').forEach((li) => (li.onclick = () => openCustomer(+li.dataset.id)));
}

// ------------------------------------------------------------------ settings
async function loadSettings() {
  const s = await api('/api/settings');
  const f = $('#settingsForm');
  for (const [k, v] of Object.entries(s)) if (f.elements[k]) f.elements[k].value = v;
  f.onsubmit = async (e) => {
    e.preventDefault();
    await api('/api/settings', { method: 'PUT', body: JSON.stringify(Object.fromEntries(new FormData(f))) });
    toast('ਸੰਭਾਲਿਆ ਗਿਆ <span class="en">Saved</span>'); refresh();
  };
}
function renderHealth() {
  const h = state.health;
  $('#healthCard').innerHTML = `<h3>ਸਿਸਟਮ <span class="en">System</span></h3><div class="health">
    <div class="${h.gnani_key ? 'ok' : 'off'}">● Gnani API key ${h.gnani_key ? 'connected' : 'missing'}</div>
    <div class="ok">● STT: ${esc(h.stt_model)} (${{ en: 'en-IN', hi: 'hi-IN', pa: 'pa-IN' }[lang]})</div>
    <div class="ok">● TTS: ${esc(h.tts_model)} · ${{ en: 'Trupti (English)', hi: 'Bhavna (Hindi)', pa: esc(h.tts_voice) }[lang]}</div>
    <div class="${h.evon ? 'ok' : 'off'}">● Evon: ${h.evon ? esc(h.evon_model) : 'not connected (on-device NLU in use)'}</div></div>`;
}

// ------------------------------------------------------------------ boot
// ------------------------------------------------------------------ real-voice testing
const test = { prompts: [], order: [], pos: 0, mode: 'free', env: 'quiet', recording: false, last: null };
const testRec = new Recorder({ onLevel: () => {}, onAutoStop: () => testStop(), maxSeconds: 28, silenceMs: 1500 });

async function openTest() {
  const d = await api(`/api/collect/prompts?lang=${lang}`);
  test.prompts = d.prompts;
  // shuffled order so every session covers different cases
  test.order = [...test.prompts.keys()].sort(() => Math.random() - 0.5);
  test.pos = 0;
  try { $('#testSpeaker').value = localStorage.getItem('testSpeaker') || ''; } catch (_) {}
  switchView('test');
  renderTestStats(d.stats);
  showPrompt();
}
function renderTestStats(st) {
  if (!st) return;
  const l = st.by.lang?.[lang];
  $('#testStats').innerHTML = `${tr('ਕੁੱਲ ਰਿਕਾਰਡਿੰਗਾਂ', 'Recordings', 'कुल रिकॉर्डिंग')}: <b>${st.n}</b>` +
    (st.n ? ` · ${tr('ਸਹੀ', 'correct', 'सही')} ${Math.round((st.correct / st.n) * 100)}%` : '') +
    (l ? `<br>${lang}: ${l.correct}/${l.n}` : '');
}
function showPrompt() {
  const p = test.prompts[test.order[test.pos]];
  $('#testCount').textContent = `${test.pos + 1} / ${test.prompts.length}`;
  $('#testPrompt').textContent = test.mode === 'read' ? p.text : p.situation;
  $('#testHint').textContent = test.mode === 'read'
    ? tr('ਇਹ ਵਾਕ ਜਿਵੇਂ ਲਿਖਿਆ ਹੈ ਉਵੇਂ ਪੜ੍ਹੋ', 'Read the sentence as written', 'यह वाक्य जैसा लिखा है वैसा पढ़िए')
    : tr('ਇਹ ਗੱਲ ਆਪਣੇ ਸ਼ਬਦਾਂ ਵਿੱਚ ਐਪ ਨੂੰ ਕਹੋ', 'Tell the app this in your own words', 'यह बात अपने शब्दों में ऐप को बोलिए');
  $('#testResult').innerHTML = '';
  test.last = null;
}
async function testStart() {
  try {
    audio.pause();
    await testRec.start();
    test.recording = true;
    $('#testMic').classList.add('rec');
    $('#testResult').innerHTML = `<span class="muted">${tr('ਸੁਣ ਰਿਹਾ ਹਾਂ…', 'Listening…', 'सुन रहा हूं…')}</span>`;
  } catch (e) { toast('ਮਾਈਕ ਨਹੀਂ ਚੱਲਿਆ <span class="en">Microphone permission needed</span>'); }
}
async function testStop() {
  if (!test.recording) return;
  test.recording = false;
  $('#testMic').classList.remove('rec');
  const out = await testRec.stop();
  if (!out || out.seconds < 0.4 || !out.heardSpeech) {
    $('#testResult').innerHTML = `<span class="muted">${tr('ਕੁਝ ਸੁਣਾਈ ਨਹੀਂ ਦਿੱਤਾ, ਫਿਰ ਬੋਲੋ', 'Didn’t hear anything, try again', 'कुछ सुनाई नहीं दिया, फिर बोलिए')}</span>`;
    return;
  }
  const p = test.prompts[test.order[test.pos]];
  const speaker = $('#testSpeaker').value.trim();
  try { localStorage.setItem('testSpeaker', speaker); } catch (_) {}
  const fd = new FormData();
  fd.append('audio', out.blob, 'speech.wav');
  fd.append('lang', lang); fd.append('case', p.case); fd.append('mode', test.mode);
  fd.append('env', test.env); fd.append('speaker', speaker);
  $('#testMic').classList.add('busy');
  $('#testResult').innerHTML = '<span class="dots"><span></span><span></span><span></span></span>';
  try {
    const r = await post('/api/collect', fd);
    test.last = r.id;
    const res = r.result, exp = r.expected;
    const ok = res.correct;
    const bits = [];
    if (!res.ok_intent) bits.push(`intent: ${res.intent} ≠ ${exp.intent}`);
    if (res.ok_intent && !res.ok_amount) bits.push(`amount: ${res.amount ?? '–'} ≠ ${exp.amount ?? 'settle all'}`);
    if (!res.ok_customer) bits.push(`customer: ${res.customer ?? '–'} ≠ ${exp.customer}`);
    $('#testResult').innerHTML = `<div class="verdict ${ok ? 'ok' : 'bad'}">${ok ? '✓ ' + tr('ਸਹੀ ਸਮਝਿਆ', 'Understood correctly', 'सही समझा')
        : '✗ ' + tr('ਗਲਤ ਸਮਝਿਆ', 'Misunderstood', 'गलत समझा')}</div>
      <div class="heard">${esc(r.transcript || '(…)')}</div>
      <div class="detail">${esc(bits.join(' · ') || `${res.intent}${res.amount ? ' · ₹' + res.amount : ''}${res.customer ? ' · ' + res.customer : ''}`)}
        · SNR ${r.audio?.snr_db ?? '–'} dB · <a href="#" id="testDel">${tr('ਇਹ ਰਿਕਾਰਡਿੰਗ ਮਿਟਾਓ', 'delete this recording', 'यह रिकॉर्डिंग हटाएं')}</a></div>`;
    $('#testDel').onclick = async (e) => {
      e.preventDefault();
      const d = await api(`/api/collect/${test.last}`, { method: 'DELETE' });
      renderTestStats(d.stats);
      $('#testResult').innerHTML = `<span class="muted">${tr('ਮਿਟਾ ਦਿੱਤੀ', 'Deleted', 'हटा दी')}</span>`;
    };
    renderTestStats(r.stats);
  } catch (e) {
    $('#testResult').innerHTML = `<span class="muted">${esc(e.message)}</span>`;
  } finally {
    $('#testMic').classList.remove('busy');
  }
}
function testNext() {
  test.pos = (test.pos + 1) % test.prompts.length;
  showPrompt();
}
$('#openTest').onclick = openTest;
$('#closeTest').onclick = () => switchView('settings');
$('#testMic').onclick = () => (test.recording ? testStop() : testStart());
$('#testNext').onclick = testNext;
$('#testSkip').onclick = testNext;
$$('#testMode button').forEach((b) => (b.onclick = () => {
  test.mode = b.dataset.mode;
  $$('#testMode button').forEach((x) => x.setAttribute('aria-pressed', x === b));
  if (test.prompts.length) showPrompt();
}));
$$('#testEnv button').forEach((b) => (b.onclick = () => {
  test.env = b.dataset.env;
  $$('#testEnv button').forEach((x) => x.setAttribute('aria-pressed', x === b));
}));

function setSubs(on) {
  document.body.classList.toggle('no-en', !on);
  $('#subToggle').checked = on;
  try { localStorage.setItem('en', on ? '1' : '0'); } catch (_) {}
}
$('#subToggle').onchange = (e) => setSubs(e.target.checked);
let enPref = '1';
try { enPref = localStorage.getItem('en') ?? '1'; } catch (_) {}
setSubs(enPref === '1');
$$('.lang-switch button').forEach((b) => (b.onclick = () => setLang(b.dataset.lang)));

async function boot() {
  try {
    const st = await (await fetch('/api/auth')).json();
    if (st.pin_required && !st.ok) { showPin(); return; }
  } catch (_) {}
  refresh();
  loadSettings();
  await updateQueueBadge();   // entries kept from an earlier visit go out now
  if (queueCount) flushQueue();
}
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
wrapPa(document);
applyLang();
boot();
