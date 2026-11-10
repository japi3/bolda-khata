"""Fine-tune MuRIL for joint intent + slot tagging on the Mac's GPU (MPS).

    python scripts/train_transformer.py --dev     # train on 75% of templates, score unseen 25%
    python scripts/train_transformer.py           # train on everything -> models/muril/

Word embeddings (≈150M of MuRIL's 237M parameters) are frozen: they already know
Punjabi, and freezing them makes training fit in 8 GB and run ~2x faster.
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch  # noqa: E402
from torch import nn  # noqa: E402
from transformers import AutoTokenizer, get_linear_schedule_with_warmup  # noqa: E402

from app import config  # noqa: E402
from app.nlu.datagen import INTENTS, T, generate  # noqa: E402
from app.nlu.model import TAGS  # noqa: E402
from app.nlu.transformer import BASE, JointModel, TransformerNLU, encode  # noqa: E402


def split_templates(seed=1):
    rng = random.Random(seed)
    tr, te = {}, {}
    for intent, temps in T.items():
        idx = list(range(len(temps))); rng.shuffle(idx)
        k = max(1, len(temps) // 4)
        te[intent] = [temps[i] for i in idx[:k]]
        tr[intent] = [temps[i] for i in idx[k:]]
    return tr, te


def train(data, epochs=3, bs=32, lr=4e-5, head_lr=1e-3, device="mps", log_every=50):
    tok = AutoTokenizer.from_pretrained(BASE)
    model = JointModel(BASE).to(device)
    model.enc.embeddings.word_embeddings.weight.requires_grad_(False)
    enc_params = [p for n, p in model.named_parameters() if n.startswith("enc.") and p.requires_grad]
    head_params = list(model.intent.parameters()) + list(model.slot.parameters())
    opt = torch.optim.AdamW([{"params": enc_params, "lr": lr}, {"params": head_params, "lr": head_lr}],
                            weight_decay=0.01)
    steps = epochs * ((len(data) + bs - 1) // bs)
    sched = get_linear_schedule_with_warmup(opt, int(0.06 * steps), steps)
    ce = nn.CrossEntropyLoss(ignore_index=-100)
    ti = {t: i for i, t in enumerate(TAGS)}
    ii = {t: i for i, t in enumerate(INTENTS)}
    model.train()
    step, t0 = 0, time.time()
    for ep in range(epochs):
        random.Random(ep).shuffle(data)
        for b in range(0, len(data), bs):
            batch = data[b:b + bs]
            enc, first = encode(tok, [s["tokens"] for s in batch])
            L = enc["input_ids"].shape[1]
            slot_y = torch.full((len(batch), L), -100, dtype=torch.long)
            for r, s in enumerate(batch):
                for w, f in enumerate(first[r]):
                    if f >= 0:
                        slot_y[r, f] = ti[s["tags"][w]]
            int_y = torch.tensor([ii[s["intent"]] for s in batch])
            li, ls = model(enc["input_ids"].to(device), enc["attention_mask"].to(device))
            loss = ce(li, int_y.to(device)) + ce(ls.reshape(-1, len(TAGS)), slot_y.reshape(-1).to(device))
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step(); opt.zero_grad()
            step += 1
            if step % log_every == 0:
                print(f"  ep {ep + 1} step {step}/{steps} loss {loss.item():.4f} ({time.time() - t0:.0f}s)", flush=True)
    model.eval().to("cpu")
    return model, tok


def save(model, tok, path: Path, extra: dict):
    path.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), path / "joint.pt")
    tok.save_pretrained(path / "tokenizer")
    (path / "meta.json").write_text(json.dumps({"base": BASE, **extra}, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--epochs", type=int, default=3)
    a = ap.parse_args()
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    if a.dev:
        tr, te = split_templates()
        model, tok = train(generate(60, seed=11, templates=tr), epochs=a.epochs, device=dev)
        nlu = TransformerNLU(model, tok)
        from scripts.train_nlu import evaluate
        r = evaluate(nlu, generate(20, seed=99, templates=te))
        print(f"[unseen templates] intent acc={r['intent_accuracy']:.3f} slot F1={r['slot_f1']:.3f}")
        out = config.MODEL_DIR / "muril_dev_report.json"
        out.write_text(json.dumps({k: r[k] for k in ("intent_accuracy", "slot_f1", "n")}, indent=2))
        return
    t0 = time.time()
    model, tok = train(generate(60, seed=7), epochs=a.epochs, device=dev)
    save(model, tok, config.MODEL_DIR / "muril", {"epochs": a.epochs, "train_seconds": round(time.time() - t0)})
    print("saved models/muril", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
