"""AI yordamida matematik test va misollar tuzish."""
import json
import logging
import re

import random
from fractions import Fraction

from config import (
    AI_MODEL,
    AI_PROVIDER,
    ANTHROPIC_API_KEY,
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
    LEVELS,
    OPENAI_API_KEY,
    OPENAI_MODEL,
)

# Provayder: AI_PROVIDER berilgan bo'lsa shu, aks holda kaliti yozilgani (Groq -> OpenAI -> Claude).
# Kalit umuman yo'q bo'lsa — demo rejim: savollarni bot o'zi tuzadi (AI siz).
_KEYS = {"groq": GROQ_API_KEY, "openai": OPENAI_API_KEY, "anthropic": ANTHROPIC_API_KEY}
if AI_PROVIDER in _KEYS and _KEYS[AI_PROVIDER]:
    PROVIDER = AI_PROVIDER
elif AI_PROVIDER == "demo":
    PROVIDER = "demo"
else:
    PROVIDER = next((name for name, key in _KEYS.items() if key), "demo")

DEMO_MODE = PROVIDER == "demo"

_client = None
log = logging.getLogger(__name__)


class AIError(Exception):
    """Foydalanuvchiga ko'rsatiladigan tushunarli AI xatosi (qayta urinish foydasiz)."""

    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


def _classify_error(exc: Exception) -> AIError | None:
    """Qayta urinish foydasiz bo'lgan xatolarni aniqlaydi (kredit, kalit, limit...)."""
    if isinstance(exc, ImportError):
        pkg = "anthropic" if PROVIDER == "anthropic" else "openai"
        return AIError(f"⚙️ Kutubxona o'rnatilmagan. Terminalda <code>pip install {pkg}</code> "
                       "ni ishga tushiring va botni qayta yoqing.")
    s = str(exc).lower()
    if any(k in s for k in ("insufficient_quota", "credit_balance", "no credits", "billing")):
        return AIError("💳 AI hisobida kredit tugagan. Hisobni to'ldiring yoki boshqa AI "
                       "provayderiga o'ting, keyin qayta urinib ko'ring.")
    if any(k in s for k in ("invalid_api_key", "incorrect api key", "authentication",
                            "unauthorized", "error code: 401")):
        return AIError("🔑 AI kaliti noto'g'ri yoki eskirgan. <code>.env</code> dagi kalitni "
                       "tekshiring.")
    if any(k in s for k in ("model_not_found", "does not exist", "error code: 404")):
        return AIError("🤖 AI model nomi noto'g'ri yoki sizga ochiq emas. "
                       "<code>.env</code> dagi model nomini tekshiring.")
    if any(k in s for k in ("rate_limit", "rate limit", "error code: 429", "too many requests")):
        return AIError("⏱ AI so'rovlar limitiga yetdi. Bir daqiqa kutib, yoki kamroq savol "
                       "tanlab qayta urinib ko'ring.")
    return None


def _get_client():
    """Tanlangan provayder uchun klientni birinchi chaqiruvda yaratadi."""
    global _client
    if _client is None:
        if PROVIDER in ("openai", "groq"):
            from openai import AsyncOpenAI  # faqat kerak bo'lganda import qilinadi
            if PROVIDER == "groq":  # Groq OpenAI bilan bir xil protokolda ishlaydi
                _client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
            else:
                _client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        else:
            from anthropic import AsyncAnthropic
            _client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _client


async def _call_ai(prompt: str) -> str:
    """AI ga so'rov yuboradi va matnli javobni qaytaradi."""
    client = _get_client()
    if PROVIDER in ("openai", "groq"):
        resp = await client.responses.create(
            model=GROQ_MODEL if PROVIDER == "groq" else OPENAI_MODEL,
            instructions=SYSTEM_PROMPT,
            input=prompt,
            # Groq bepul tarifida daqiqalik token limiti kichik, shuning uchun kamroq
            max_output_tokens=6000 if PROVIDER == "groq" else 16000,
        )
        return resp.output_text
    resp = await client.messages.create(
        model=AI_MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")

LEVEL_HINTS = {
    "easy": "Barcha savollar OSON bo'lsin: mavzuning asosiy qoidalari va qisqa hisoblashlar.",
    "medium": "Barcha savollar O'RTA qiyinlikda bo'lsin: bir necha qadamli hisoblashlar.",
    "hard": "Barcha savollar QIYIN bo'lsin: murakkab, fikrlashni talab qiladigan, olimpiada darajasiga yaqin.",
    "mixed": "Savollar ARALASH bo'lsin: taxminan uchdan bir qismi oson, uchdan bir qismi o'rta, "
             "uchdan bir qismi qiyin. Oddiydan murakkabga qarab tartiblang.",
}

SYSTEM_PROMPT = (
    "Sen tajribali matematika o'qituvchisan. O'zbek tilida (lotin yozuvida) test va "
    "misollar tuzasan. Javoblar ANIQ va TO'G'RI bo'lishi shart: har bir savolni o'zing "
    "qadam-baqadam yechib, javobni tekshirib chiq. Matematik ifodalarni oddiy matn "
    "ko'rinishida, Unicode belgilar bilan yoz (masalan: x², √16, ½, 3/4, π, ≤, ≥, ≠, ×, ÷). "
    "LaTeX ishlatma. Faqat so'ralgan formatda javob ber, kirish yoki yakuniy izoh yozma."
)


def _build_prompt(topic: str, level: str, kind: str, count: int) -> str:
    # JSON o'rniga oddiy matnli format: modellar uni deyarli buzmaydi (tirnoq, vergul xatosi yo'q)
    if kind == "test":
        fmt = (
            "Q: savol matni\n"
            "A) birinchi variant\n"
            "B) ikkinchi variant\n"
            "C) uchinchi variant\n"
            "D) to'rtinchi variant\n"
            "ANS: to'g'ri variant harfi (A, B, C yoki D)\n"
            "SOL: qisqa yechim\n"
            "=====\n"
            "(keyingi savol ham xuddi shunday, har savoldan keyin ===== qatori)"
        )
        extra = (
            "Har bir savolda 4 ta variant (A, B, C, D) bo'lsin, faqat bittasi to'g'ri. "
            "To'g'ri javob harflari turlicha taqsimlansin (hammasi bir xil harf bo'lmasin). "
            "Noto'g'ri variantlar ishonarli bo'lsin."
        )
    else:
        fmt = (
            "Q: misol matni\n"
            "ANS: yakuniy javob\n"
            "SOL: qisqa yechim bosqichlari\n"
            "=====\n"
            "(keyingi misol ham xuddi shunday, har misoldan keyin ===== qatori)"
        )
        extra = (
            "Yozma ishlash uchun misollar va masalalar tuz (hisoblash, soddalashtirish, "
            "tenglama yechish, matnli masala). Javob qisqa va aniq bo'lsin."
        )

    return (
        f"Mavzu: {topic}\n"
        f"Qiyinlik: {LEVELS[level]}. {LEVEL_HINTS[level]}\n"
        f"Savollar soni: aynan {count} ta.\n"
        f"{extra}\n"
        "Savollar bir-birini takrorlamasin. Har bir maydon (Q, ANS, SOL, variantlar) "
        "bitta qatorda bo'lsin. Raqamlash, markdown (**, #) va qo'shimcha izoh qo'shma.\n\n"
        f"Javobni FAQAT mana shu formatda qaytar:\n{fmt}"
    )


def _parse_blocks(text: str, kind: str) -> dict:
    """Matnli formatni ({"questions": [...]}) ko'rinishiga o'giradi."""
    text = text.replace("**", "").replace("`", "")
    field_re = re.compile(
        r"^\s*(?:(Q)\d*\s*[:.]|([ABCD])\s*[).:]|(ANS)\s*[:=]|(SOL)\s*[:=])\s*(.*)$", re.I)

    items = []
    for block in re.split(r"^\s*={3,}\s*$", text, flags=re.M):
        cur_key = None
        fields: dict[str, str] = {}
        for line in block.splitlines():
            m = field_re.match(line)
            if m:
                letter = m.group(2)
                key = ("q" if m.group(1) else letter.upper() if letter
                       else "ans" if m.group(3) else "sol")
                fields[key] = m.group(5).strip()
                cur_key = key
            elif cur_key and line.strip():
                fields[cur_key] += " " + line.strip()  # qator uzilgan bo'lsa davom ettiramiz
        if "q" not in fields or "ans" not in fields:
            continue
        item = {"question": fields["q"], "answer": fields["ans"],
                "solution": fields.get("sol", "")}
        if kind == "test":
            item["options"] = {k: fields.get(k, "") for k in "ABCD"}
        items.append(item)

    if not items:
        raise ValueError("AI javobida savollar topilmadi")
    return {"questions": items}


def _extract_json(text: str) -> dict:
    text = text.strip()
    # ```json ... ``` o'ramini olib tashlash
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("AI javobida JSON topilmadi")
    return json.loads(text[start:end + 1])


def validate(data: dict, kind: str) -> list[dict]:
    """JSON ni tekshiradi va tozalangan savollar ro'yxatini qaytaradi."""
    items = data.get("questions")
    if not isinstance(items, list) or not items:
        raise ValueError("Savollar ro'yxati bo'sh")

    cleaned = []
    for item in items:
        q = str(item.get("question", "")).strip()
        ans = str(item.get("answer", "")).strip()
        sol = str(item.get("solution", "")).strip()
        if not q or not ans:
            continue
        entry = {"question": q, "answer": ans, "solution": sol}
        if kind == "test":
            opts = item.get("options") or {}
            options = {k: str(opts.get(k, "")).strip() for k in "ABCD"}
            letter = ans.upper()[:1]
            if not all(options.values()) or letter not in options:
                continue
            entry["options"] = options
            entry["answer"] = letter
        cleaned.append(entry)

    if not cleaned:
        raise ValueError("Yaroqli savol qolmadi")
    return cleaned


# ---------------- Demo rejim (API kalitsiz) ----------------
def _fmt(fr: Fraction) -> str:
    return str(fr.numerator) if fr.denominator == 1 else f"{fr.numerator}/{fr.denominator}"


def _demo_one(level: str) -> tuple[str, str, list[str], str]:
    """Bitta savol: (matn, to'g'ri javob, noto'g'ri variantlar, yechim)."""
    if level == "mixed":
        level = random.choice(["easy", "medium", "hard"])
    hi = {"easy": 10, "medium": 30, "hard": 90}[level]
    kind = random.choice(["add", "mul", "frac", "eq", "pct"] if level != "easy"
                         else ["add", "mul", "frac"])

    if kind == "add":
        a, b, c = (random.randint(2, hi) for _ in range(3))
        ans = a + b * c
        return (f"Hisoblang: {a} + {b} × {c}", str(ans),
                [str(ans + d) for d in (-c, b, 10)], f"{b} × {c} = {b * c}; {a} + {b * c} = {ans}")
    if kind == "mul":
        a, b = random.randint(2, hi), random.randint(2, max(3, hi // 2))
        ans = a * b
        return (f"Hisoblang: {a} × {b}", str(ans),
                [str(ans + d) for d in (-a, b, 10)], f"{a} × {b} = {ans}")
    if kind == "frac":
        d1, d2 = random.randint(2, 6), random.randint(2, 9)
        f1, f2 = Fraction(random.randint(1, d1 - 1 or 1), d1), Fraction(random.randint(1, d2), d2)
        ans = f1 + f2
        wrong = [Fraction(f1.numerator + f2.numerator, f1.denominator + f2.denominator),
                 ans + Fraction(1, 2), abs(f1 - f2) + 1]
        return (f"Hisoblang: {_fmt(f1)} + {_fmt(f2)}", _fmt(ans), [_fmt(w) for w in wrong],
                f"Umumiy maxrajga keltiramiz: {_fmt(f1)} + {_fmt(f2)} = {_fmt(ans)}")
    if kind == "eq":
        x, a, b = random.randint(2, hi // 2 + 2), random.randint(2, 9), random.randint(1, hi)
        return (f"Tenglamani yeching: {a}x + {b} = {a * x + b}", str(x),
                [str(x + d) for d in (1, -1, a)], f"{a}x = {a * x + b} − {b} = {a * x}; x = {x}")
    p = random.choice([10, 20, 25, 50])
    n = random.choice([40, 60, 80, 120, 200])
    ans = n * p // 100
    return (f"{n} sonining {p}% ini toping.", str(ans),
            [str(ans + d) for d in (5, -5, 10)], f"{n} × {p} / 100 = {ans}")


def demo_questions(topic: str, level: str, kind: str, count: int) -> list[dict]:
    out, seen = [], set()
    attempts = 0
    while len(out) < count and attempts < count * 50:
        attempts += 1
        text, ans, wrong, sol = _demo_one(level)
        if text in seen:
            continue
        seen.add(text)
        entry = {"question": text, "answer": ans, "solution": sol}
        if kind == "test":
            variants = [ans] + [w for w in dict.fromkeys(wrong) if w != ans]
            while len(variants) < 4:
                variants.append(str(random.randint(1, 999)))
            variants = variants[:4]
            random.shuffle(variants)
            entry["options"] = dict(zip("ABCD", variants))
            entry["answer"] = "ABCD"[variants.index(ans)]
        out.append(entry)
    return out


async def generate_questions(topic: str, level: str, kind: str, count: int) -> list[dict]:
    """AI dan savollar oladi (kalit bo'lmasa demo rejim). Xato bo'lsa qayta urinadi."""
    if DEMO_MODE:
        return demo_questions(topic, level, kind, count)

    prompt = _build_prompt(topic, level, kind, count)
    last_error: Exception | None = None

    for _ in range(3):
        try:
            text = await _call_ai(prompt)
            try:
                return validate(_parse_blocks(text, kind), kind)
            except ValueError:
                # model baribir JSON qaytargan bo'lsa, shuni ham o'qib ko'ramiz
                try:
                    return validate(_extract_json(text), kind)
                except ValueError:
                    log.warning("AI javobi o'qilmadi. Boshi: %r", text[:400])
                    raise
        except Exception as exc:  # noqa: BLE001
            fatal = _classify_error(exc)
            if fatal:  # kredit/kalit/limit xatosida qayta urinish foydasiz
                raise fatal from exc
            last_error = exc

    raise RuntimeError(f"Savollar tuzib bo'lmadi: {last_error}")
