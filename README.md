# MatemTest AI — Telegram bot

Matematikadan istalgan mavzu bo'yicha **test** yoki **yozma misollar** tuzib,
PDF ko'rinishida yuboradigan bot.

## Bot qanday ishlaydi
1. `/start` — bot mavzuni so'raydi (masalan: *Kasrlar*).
2. Qiyinlik darajasi: **Oson / O'rta / Qiyin / Aralash**.
3. Turi: **Test (A, B, C, D)** yoki **Yozma misollar**.
4. Savollar soni: 5 / 10 / 15 / 20.
5. Bot ikkita PDF yuboradi: avval **savollar**, uning tagida **javoblar va yechimlar**.

## PDF dizayni
- Ikki ustunli A4, o'rtada ajratuvchi chiziq, ko'k sarlavha.
- Har testga o'zining **Test ID** si beriladi (masalan `#T_D4J`): tepada, sarlavha tagida
  va fayl nomida (`Savollar_D4J.pdf`, `Javoblar_D4J.pdf`). Telegramda ham yoziladi.
- Sahifa orqasida diagonal xira suv belgi (`©kanal`), pastda `@kanal • Sahifa N`.
- Kanal/bot nomini `.env` dagi `BRAND=@sizning_kanalingiz` bilan o'zgartirasiz.
- Javoblar faylida tepada javoblar kaliti jadvali, pastda yechimlar.

## O'rnatish
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

`.env.example` faylini `.env` deb nusxalang va to'ldiring:
```
BOT_TOKEN=...          # @BotFather dan
ANTHROPIC_API_KEY=...  # console.anthropic.com dan
```

## AI tanlash
`.env` da qaysi kalit yozilgan bo'lsa, bot shuni ishlatadi (ustuvorlik shu tartibda):
1. `GROQ_API_KEY` — **Groq** (model: `GROQ_MODEL`, `pip install openai`)
2. `OPENAI_API_KEY` — **OpenAI** (model: `OPENAI_MODEL`, `pip install openai`)
3. `ANTHROPIC_API_KEY` — **Claude** (model: `AI_MODEL`, `pip install anthropic`)
4. hammasi bo'sh — **demo rejim**

Boshqasini majburan tanlash uchun `AI_PROVIDER=openai` kabi yozing.

AI xatolarida (kredit tugagan, kalit noto'g'ri, limit) bot foydalanuvchiga tushunarli
xabar yozadi, sababi esa bot oynasida ko'rinadi.

## Demo rejim (API kalitsiz tez sinash)
Ikkala kalitni ham **bo'sh** qoldiring. Bot AI siz ishlaydi va oddiy namunaviy misollar
(arifmetika, kasrlar, tenglama, foiz) tuzadi. Ular mavzuga bog'liq emas, faqat bot va
PDF lar ishlashini tekshirish uchun. `openai`/`anthropic` kutubxonalari ham shart emas.

## Ishga tushirish
```bash
python bot.py
```

## Fayllar
| Fayl | Vazifasi |
|---|---|
| `bot.py` | Telegram bot (menyu, tugmalar, fayl yuborish) |
| `generator.py` | AI orqali savollar tuzish va tekshirish |
| `pdf_maker.py` | Savollar va javoblar PDF fayllarini yasash |
| `config.py` | Sozlamalar |
| `fonts/` | PDF uchun shriftlar (o', g', ², √ belgilari uchun) |
