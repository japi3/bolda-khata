"""Model selection on the DEV set (held-out templates) only — the hard test set is not used here.

Trains several MuRIL configurations + the MEMM on 75% of templates, then scores
each alone and in ensembles on the unseen 25%. Writes models/dev_sweep.json.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch  # noqa: E402

from app import config  # noqa: E402
from app.nlu.datagen import generate  # noqa: E402
from app.nlu.ensemble import EnsembleNLU  # noqa: E402
from app.nlu.model import KhataNLU  # noqa: E402
from app.nlu.transformer import TransformerNLU  # noqa: E402
from scripts.train_nlu import evaluate  # noqa: E402
import scripts.train_transformer as tt  # noqa: E402

CONFIGS = {
    "ep3": dict(epochs=3, freeze=0),
    "ep1": dict(epochs=1, freeze=0),
    "ep2_freeze6": dict(epochs=2, freeze=6),
    "ep3_freeze9": dict(epochs=3, freeze=9),
}


def train_cfg(data, epochs, freeze):
    orig = tt.JointModel.__init__

    def patched(self, *a, **k):
        orig(self, *a, **k)
        for layer in self.enc.encoder.layer[:freeze]:
            for p in layer.parameters():
                p.requires_grad_(False)
    tt.JointModel.__init__ = patched
    try:
        return tt.train(list(data), epochs=epochs, device="mps" if torch.backends.mps.is_available() else "cpu",
                        log_every=10_000)
    finally:
        tt.JointModel.__init__ = orig


def main():
    tr, te = tt.split_templates()
    train_data = generate(60, seed=11, templates=tr)
    dev = generate(20, seed=99, templates=te)
    memm = KhataNLU().fit(train_data)
    results = {"memm": {k: evaluate(memm, dev)[k] for k in ("intent_accuracy", "slot_f1")}}
    print("memm", results["memm"], flush=True)
    for name, cfg in CONFIGS.items():
        t0 = time.time()
        model, tok = train_cfg(train_data, **cfg)
        tf = TransformerNLU(model, tok)
        r = {k: evaluate(tf, dev)[k] for k in ("intent_accuracy", "slot_f1")}
        r["train_s"] = round(time.time() - t0)
        for w in (0.2, 0.35, 0.5, 0.65):
            e = evaluate(EnsembleNLU(memm, tf, w), dev)
            r[f"ens_w{w}"] = {k: e[k] for k in ("intent_accuracy", "slot_f1")}
        results[name] = r
        tt.save(model, tok, config.MODEL_DIR / "dev" / name, cfg)
        print(name, json.dumps(r), flush=True)
        (config.MODEL_DIR / "dev_sweep.json").write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
