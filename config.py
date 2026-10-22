import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
AI_MODEL = os.getenv("AI_MODEL", "claude-sonnet-5-5").strip()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-6.1-sol").strip()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Ixtiyoriy: provayderni qo'lda tanlash (groq / openai / anthropic / demo).
# Bo'sh bo'lsa, kaliti yozilgani avtomatik tanlanadi.
AI_PROVIDER = os.getenv("AI_PROVIDER", "").strip().lower()

# PDF dagi kanal/bot nomi: sarlavhada, pastki qismda va orqadagi xira suv belgida chiqadi.
# .env da BRAND=@sizning_kanalingiz deb o'zgartirasiz.
BRAND = os.getenv("BRAND", "@idcuz").strip() or "@idcuz"

FONTS_DIR = BASE_DIR / "fonts"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Bitta testdagi savollar soni uchun variantlar
COUNT_OPTIONS = [5, 10, 15, 20]

LEVELS = {
    "easy": "Oson",
    "medium": "O'rta",
    "hard": "Qiyin",
    "mixed": "Aralash",
}

KINDS = {
    "test": "Test (A, B, C, D)",
    "written": "Yozma misollar",
}
