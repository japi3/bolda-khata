"""Central configuration, read from environment / .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

GNANI_API_KEY = os.getenv("GNANI_API_KEY", "")
GNANI_BASE = os.getenv("GNANI_BASE", "https://api.vachana.ai")

STT_MODEL = os.getenv("STT_MODEL", "prisma-v3.0")
LANG = os.getenv("LANG_CODE", "pa-IN")

TTS_MODEL = os.getenv("TTS_MODEL", "timbre-v2.5")
TTS_VOICE = os.getenv("TTS_VOICE", "Mehuli")          # Punjabi-optimised Timbre v2.5 voice
REMINDER_VOICE = os.getenv("REMINDER_VOICE", "Zayan")  # warm, empathetic Punjabi voice
TTS_VOICE_EN = os.getenv("TTS_VOICE_EN", "Trupti")          # English (en-IN) Timbre v2.5 voice
REMINDER_VOICE_EN = os.getenv("REMINDER_VOICE_EN", "Shlok")
TTS_VOICE_HI = os.getenv("TTS_VOICE_HI", "Bhavna")          # Hindi (hi-IN) Timbre v2.5 voice
REMINDER_VOICE_HI = os.getenv("REMINDER_VOICE_HI", "Vikrant")

# Evon (Gnani's 30B Indic LLM) served behind any OpenAI-compatible endpoint (vLLM / SGLang).
EVON_BASE_URL = os.getenv("EVON_BASE_URL", "")          # e.g. https://<you>--evon-serve.modal.run/v1
EVON_API_KEY = os.getenv("EVON_API_KEY", "not-needed")
EVON_MODEL = os.getenv("EVON_MODEL", "gnani/gnani-evon-v3.3-30B-A3B")
EVON_TIMEOUT = float(os.getenv("EVON_TIMEOUT", "20"))

DATA_DIR = ROOT / "data"
DB_PATH = Path(os.getenv("DB_PATH", DATA_DIR / "khata.db"))
AUDIO_CACHE = DATA_DIR / "audio"
MODEL_DIR = ROOT / "models"

for d in (DATA_DIR, AUDIO_CACHE, MODEL_DIR):
    d.mkdir(parents=True, exist_ok=True)
