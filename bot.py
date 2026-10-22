"""MatemTest AI — matematikadan test va misollar tuzib beradigan Telegram bot."""
import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, COUNT_OPTIONS, KINDS, LEVELS
from generator import DEMO_MODE, AIError, generate_questions
from pdf_maker import make_pdfs

logging.basicConfig(level=logging.INFO)
router = Router()


class TestFlow(StatesGroup):
    topic = State()
    level = State()
    kind = State()
    count = State()


# ---------- Klaviaturalar ----------
def level_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, label in LEVELS.items():
        kb.button(text=label, callback_data=f"level:{key}")
    kb.adjust(2)
    return kb.as_markup()


def kind_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, label in KINDS.items():
        kb.button(text=label, callback_data=f"kind:{key}")
    kb.adjust(1)
    return kb.as_markup()


def count_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for n in COUNT_OPTIONS:
        kb.button(text=f"{n} ta", callback_data=f"count:{n}")
    kb.adjust(4)
    return kb.as_markup()


def again_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yangi test tuzish", callback_data="again")]
    ])


# ---------- Handlerlar ----------
@router.message(CommandStart())
@router.message(Command("new"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(TestFlow.topic)
    await message.answer(
        "👋 <b>MatemTest AI</b> botiga xush kelibsiz!\n\n"
        "Men matematikadan istalgan mavzu bo'yicha <b>test</b> yoki <b>yozma misollar</b> "
        "tuzib, PDF fayl ko'rinishida (savollar + javoblar) yuboraman.\n\n"
        "📚 Avval <b>mavzuni yozing</b>.\nMasalan: <i>Kasrlar</i>, <i>Kvadrat tenglamalar</i>, "
        "<i>Foizlar</i>, <i>Pifagor teoremasi</i>"
    )


@router.callback_query(F.data == "again")
async def again(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    await state.set_state(TestFlow.topic)
    await call.message.answer("📚 Yangi test uchun <b>mavzuni yozing</b>:")


@router.message(TestFlow.topic, F.text)
async def got_topic(message: Message, state: FSMContext):
    topic = message.text.strip()
    if len(topic) < 2 or len(topic) > 100:
        await message.answer("Iltimos, mavzuni 2–100 belgi oralig'ida yozing.")
        return
    await state.update_data(topic=topic)
    await state.set_state(TestFlow.level)
    await message.answer(f"✅ Mavzu: <b>{topic}</b>\n\n📊 Qiyinlik darajasini tanlang:",
                         reply_markup=level_kb())


@router.callback_query(TestFlow.level, F.data.startswith("level:"))
async def got_level(call: CallbackQuery, state: FSMContext):
    level = call.data.split(":")[1]
    if level not in LEVELS:
        await call.answer()
        return
    await state.update_data(level=level)
    await state.set_state(TestFlow.kind)
    await call.answer()
    await call.message.edit_text(f"✅ Daraja: <b>{LEVELS[level]}</b>\n\n📝 Qaysi turda tuzay?",
                                 reply_markup=kind_kb())


@router.callback_query(TestFlow.kind, F.data.startswith("kind:"))
async def got_kind(call: CallbackQuery, state: FSMContext):
    kind = call.data.split(":")[1]
    if kind not in KINDS:
        await call.answer()
        return
    await state.update_data(kind=kind)
    await state.set_state(TestFlow.count)
    await call.answer()
    await call.message.edit_text(f"✅ Turi: <b>{KINDS[kind]}</b>\n\n🔢 Nechta savol bo'lsin?",
                                 reply_markup=count_kb())


@router.callback_query(TestFlow.count, F.data.startswith("count:"))
async def got_count(call: CallbackQuery, state: FSMContext, bot: Bot):
    count = int(call.data.split(":")[1])
    if count not in COUNT_OPTIONS:
        await call.answer()
        return
    data = await state.get_data()
    await state.clear()
    await call.answer()

    topic, level, kind = data["topic"], data["level"], data["kind"]
    await call.message.edit_text(
        f"⏳ <b>{topic}</b> mavzusida {count} ta {LEVELS[level].lower()} "
        f"{'test' if kind == 'test' else 'misol'} tuzilmoqda...\n"
        "Bu 20–60 soniya vaqt olishi mumkin."
    )
    chat_id = call.message.chat.id
    await bot.send_chat_action(chat_id, ChatAction.UPLOAD_DOCUMENT)

    try:
        questions = await generate_questions(topic, level, kind, count)
        q_pdf, a_pdf, test_id = await asyncio.to_thread(
            make_pdfs, questions, topic, level, kind, call.from_user.id
        )
    except AIError as exc:
        logging.error("AI xatosi: %s", exc.__cause__ or exc)
        await bot.send_message(chat_id, exc.user_message, reply_markup=again_kb())
        return
    except Exception:  # noqa: BLE001
        logging.exception("Test tuzishda xato")
        await bot.send_message(
            chat_id,
            "😔 Kechirasiz, test tuzishda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=again_kb(),
        )
        return

    # Avval savollar, uning tagida javoblar fayli
    await bot.send_document(
        chat_id, FSInputFile(q_pdf),
        caption=f"📄 <b>Savollar</b> — {topic} ({LEVELS[level]})\n🆔 Test ID: <code>{test_id}</code>")
    demo_note = ("\n\n🧪 <i>Demo rejim: API kalit yo'q, shuning uchun savollar mavzuga "
                 "bog'liq emas, oddiy namunaviy misollar.</i>") if DEMO_MODE else ""
    await bot.send_document(chat_id, FSInputFile(a_pdf),
                            caption=f"✅ <b>Javoblar va yechimlar</b>\n🆔 Test ID: <code>{test_id}</code>"
                                    + demo_note,
                            reply_markup=again_kb())

    for p in (q_pdf, a_pdf):
        p.unlink(missing_ok=True)
    try:
        q_pdf.parent.rmdir()  # har bir test uchun alohida vaqtinchalik papka
    except OSError:
        pass


@router.message(TestFlow.topic)
@router.message(TestFlow.level)
@router.message(TestFlow.kind)
@router.message(TestFlow.count)
async def wrong_input(message: Message):
    await message.answer("Iltimos, yuqoridagi tugmalardan birini tanlang yoki /new bosing.")


@router.message()
async def fallback(message: Message, state: FSMContext):
    await message.answer("Boshlash uchun /start ni bosing.")


async def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN topilmadi. .env faylini to'ldiring.")
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
