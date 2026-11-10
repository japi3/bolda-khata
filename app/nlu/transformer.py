"""Joint intent + slot model on a pretrained Indic transformer (MuRIL by default).

MuRIL (google/muril-base-cased) was pretrained on 17 Indian languages incl. Punjabi,
so it brings real knowledge of Punjabi words the templates never contained.
Architecture: shared encoder -> [CLS] -> intent head; first sub-word of each word ->
BIO slot head (NAME / ITEM). Trained with the sum of both cross-entropies.
Same .analyse() interface as the on-device MEMM model.
"""
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn
from transformers import AutoModel, AutoTokenizer

from .datagen import INTENTS
from .model import TAGS, mask
from .punjabi import normalize, surface_tokens

BASE = "google/muril-base-cased"


class JointModel(nn.Module):
    def __init__(self, base: str = BASE, n_intents=len(INTENTS), n_tags=len(TAGS), dropout=0.1):
        super().__init__()
        self.enc = AutoModel.from_pretrained(base)
        h = self.enc.config.hidden_size
        self.drop = nn.Dropout(dropout)
        self.intent = nn.Linear(h, n_intents)
        self.slot = nn.Linear(h, n_tags)

    def forward(self, input_ids, attention_mask):
        out = self.enc(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        out = self.drop(out)
        return self.intent(out[:, 0]), self.slot(out)


def encode(tok, batch_words: list[list[str]], max_len: int = 64):
    enc = tok(batch_words, is_split_into_words=True, truncation=True, max_length=max_len,
              padding=True, return_tensors="pt")
    first = []  # index of first sub-word for each word (or -1 if truncated)
    for b in range(len(batch_words)):
        wid = enc.word_ids(b)
        pos = {}
        for i, w in enumerate(wid):
            if w is not None and w not in pos:
                pos[w] = i
        first.append([pos.get(w, -1) for w in range(len(batch_words[b]))])
    return enc, first


class TransformerNLU:
    def __init__(self, model: JointModel, tok, device="cpu"):
        self.model, self.tok, self.device = model.eval().to(device), tok, device

    @staticmethod
    def load(path: Path, device: str = "cpu") -> "TransformerNLU":
        path = Path(path)
        meta = json.loads((path / "meta.json").read_text())
        tok = AutoTokenizer.from_pretrained(path / "tokenizer")
        m = JointModel(meta["base"])
        m.load_state_dict(torch.load(path / "joint.pt", map_location="cpu"))
        torch.set_num_threads(4)
        return TransformerNLU(m, tok, device)

    @torch.no_grad()
    def analyse(self, text: str) -> dict:
        toks = normalize(text).split()
        surf = surface_tokens(text)
        if len(surf) != len(toks):
            surf = toks
        if not toks:
            toks = surf = ["."]
        enc, first = encode(self.tok, [toks])
        li, ls = self.model(enc["input_ids"].to(self.device), enc["attention_mask"].to(self.device))
        p_int = torch.softmax(li[0], -1).cpu().numpy()
        p_slot = torch.softmax(ls[0], -1).cpu().numpy()
        tags, confs, prev = [], [], "O"
        for w, f in enumerate(first[0]):
            if f < 0:
                tags.append("O"); confs.append(1.0); prev = "O"; continue
            order = np.argsort(p_slot[f])[::-1]
            for k in order:  # best tag that forms a valid BIO sequence
                t = TAGS[k]
                if t.startswith("I-") and prev[2:] != t[2:]:
                    continue
                break
            tags.append(t); confs.append(float(p_slot[f][k])); prev = t
        spans, cur = {"NAME": [], "ITEM": []}, None
        for w, t in zip(surf, tags):
            if t.startswith("B-"):
                cur = [w]; spans[t[2:]].append(cur)
            elif t.startswith("I-") and cur is not None:
                cur.append(w)
            else:
                cur = None
        order = np.argsort(p_int)[::-1]
        return {
            "tokens": toks, "tags": tags, "masked": mask(toks, tags),
            "intent": INTENTS[order[0]], "confidence": float(p_int[order[0]]),
            "alternatives": [(INTENTS[k], round(float(p_int[k]), 3)) for k in order[1:3]],
            "proba": {INTENTS[k]: float(p_int[k]) for k in range(len(INTENTS))},
            "names": [" ".join(s) for s in spans["NAME"]], "items": [" ".join(s) for s in spans["ITEM"]],
            "tag_confidence": float(np.mean(confs)),
        }
