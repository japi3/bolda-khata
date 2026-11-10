"""Ensemble of the fine-tuned transformer (MuRIL) and the on-device MEMM model.

Intent: weighted average of both models' probabilities (they make different kinds
of mistakes: MuRIL knows Punjabi vocabulary, the MEMM leans on hand-built cue words).
Slots: transformer's names/items, falling back to the MEMM's when it finds none.
If the transformer weights are missing, it silently degrades to the MEMM alone.
"""
from .. import config
from .model import KhataNLU

W_TRANSFORMER = 0.65   # chosen on the dev set (held-out templates), see models/dev_sweep.json


class EnsembleNLU:
    def __init__(self, memm: KhataNLU, tf=None, w: float = W_TRANSFORMER):
        self.memm, self.tf, self.w = memm, tf, w

    @staticmethod
    def load(w: float = W_TRANSFORMER) -> "EnsembleNLU":
        memm = KhataNLU.load(config.MODEL_DIR / "nlu.joblib")
        tf = None
        if (config.MODEL_DIR / "muril" / "joint.pt").exists():
            from .transformer import TransformerNLU
            tf = TransformerNLU.load(config.MODEL_DIR / "muril")
        return EnsembleNLU(memm, tf, w)

    @property
    def name(self) -> str:
        return "muril+memm" if self.tf else "memm"

    def analyse(self, text: str) -> dict:
        a = self.memm.analyse(text)
        if self.tf is None:
            return a
        b = self.tf.analyse(text)
        p = {k: self.w * b["proba"].get(k, 0.0) + (1 - self.w) * a["proba"].get(k, 0.0) for k in b["proba"]}
        order = sorted(p, key=p.get, reverse=True)
        out = dict(b)
        out.update({
            "intent": order[0], "confidence": p[order[0]],
            "alternatives": [(k, round(p[k], 3)) for k in order[1:3]], "proba": p,
            "names": b["names"] or a["names"], "items": b["items"] or a["items"],
            "members": {"muril": (b["intent"], round(b["confidence"], 3)),
                        "memm": (a["intent"], round(a["confidence"], 3))},
        })
        if not b["names"] and a["names"]:
            out["tags"] = a["tags"]
        return out
