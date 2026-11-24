"""Бот-визитка на aiogram 3 с формой заявки.

Запуск: двойной клик по run.bat (или `.venv\\Scripts\\python.exe bot.py`).
Все тексты и ссылки лежат в texts.py — их и редактируй.
"""

import asyncio
import html
import logging
import os
import socket
import time
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramUnauthorizedError
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from dotenv import load_dotenv

import texts
import reviews as reviews_store

load_dotenv()


def _owner_id() -> int:
    """ID владельца из .env. 0 — значит, форма заявок выключена."""
    try:
        return int(os.getenv("OWNER_ID", "0").strip() or 0)
    except ValueError:
        return 0


OWNER_ID = _owner_id()
COOLDOWN_SECONDS = 60  # одна заявка в минуту с одного аккаунта

# Порты популярных VPN-клиентов: берём первый, который реально отвечает.
COMMON_PROXIES = [
    "http://127.0.0.1:10809",    # v2rayN, HTTP
    "http://127.0.0.1:10801",    # v2rayTun, HTTP
    "http://127.0.0.1:7890",     # Clash, HTTP
    "socks5://127.0.0.1:10808",  # v2rayN, SOCKS
    "socks5://127.0.0.1:7891",   # Clash, SOCKS
    "http://127.0.0.1:1080",
]
CONNECT_TIMEOUT = 8.0


class NoConnection(Exception):
    """Telegram недоступен ни напрямую, ни через прокси."""


def _port_open(proxy: str) -> bool:
    parsed = urlparse(proxy)
    if not parsed.hostname or not parsed.port:
        return False
    try:
        with socket.create_connection((parsed.hostname, parsed.port), timeout=0.4):
            return True
    except OSError:
        return False


async def _try_proxy(token: str, proxy: str | None):
    session = AiohttpSession(proxy=proxy, timeout=CONNECT_TIMEOUT)
    bot = Bot(
        token=token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        me = await bot.get_me()
        return bot, me
    except TelegramUnauthorizedError:
        await bot.session.close()
        raise
    except Exception:
        await bot.session.close()
        return None


async def build_bot(token: str):
    """Возвращает (бот, рабочий прокси, данные бота)."""
    preferred = os.getenv("PROXY_URL", "").strip()
    candidates: list[str] = []
    for proxy in [preferred, *COMMON_PROXIES]:
        if proxy and proxy not in candidates:
            candidates.append(proxy)

    for proxy in candidates:
        if not _port_open(proxy):
            continue
        result = await _try_proxy(token, proxy)
        if result:
            bot, me = result
            return bot, proxy, me

    result = await _try_proxy(token, None)
    if result:
        bot, me = result
        return bot, None, me

    raise NoConnection

router = Router()


class Form(StatesGroup):
    name = State()
    task = State()
    contact = State()


class ReviewForm(StatesGroup):
    text = State()


FORM_STATES = StateFilter(Form.name, Form.task, Form.contact, ReviewForm.text)
_last_order_at: dict[int, float] = {}
_last_review_at: dict[int, float] = {}
REVIEWS_PER_PAGE = texts.REVIEWS_PER_PAGE
REVIEW_COOLDOWN_SECONDS = 600


# ---------- Клавиатуры ----------

def main_menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"section:{key}")]
        for key, label in texts.MENU
    ]
    rows.append([InlineKeyboardButton(text=texts.ORDER_BUTTON, callback_data="order")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def section_menu(key: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, url=url)]
        for label, url in texts.SECTION_LINKS.get(key, [])
    ]
    rows += [
        [InlineKeyboardButton(text=label, callback_data=data)]
        for label, data in texts.SECTION_BUTTONS.get(key, [])
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts.CANCEL_BUTTON)]],
        resize_keyboard=True,
    )


def rating_keyboard() -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(text=f"{n} ⭐", callback_data=f"review:rate:{n}")
        for n in range(1, 6)
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            row,
            [InlineKeyboardButton(text=texts.REVIEWS_BACK, callback_data="section:reviews")],
        ]
    )


def reviews_keyboard(page: int, total: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=texts.REVIEWS_BUTTON, callback_data="review:new")]
    ]
    if (page + 1) * REVIEWS_PER_PAGE < total:
        rows.append(
            [
                InlineKeyboardButton(
                    text=texts.REVIEWS_MORE,
                    callback_data=f"reviews:page:{page + 1}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def moderation_keyboard(review_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Опубликовать", callback_data=f"rvok:{review_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить", callback_data=f"rvno:{review_id}"
                ),
            ]
        ]
    )


# ---------- Базовые команды ----------

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    if await state.get_state():
        await state.clear()
        await message.answer(texts.ORDER_CANCELLED, reply_markup=ReplyKeyboardRemove())
    await message.answer(texts.START_TEXT, reply_markup=main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(texts.HELP_TEXT, reply_markup=main_menu())


@router.message(Command("myid"))
async def cmd_myid(message: Message) -> None:
    await message.answer(f"Твой Telegram ID: <code>{message.from_user.id}</code>")


# ---------- Отмена формы ----------

async def _stop_form(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.ORDER_CANCELLED, reply_markup=ReplyKeyboardRemove())
    await message.answer(texts.MENU_AGAIN, reply_markup=main_menu())


@router.message(Command("cancel"), FORM_STATES)
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await _stop_form(message, state)


@router.message(FORM_STATES, F.text == texts.CANCEL_BUTTON)
async def cancel_button(message: Message, state: FSMContext) -> None:
    await _stop_form(message, state)


# ---------- Отзывы ----------

async def _edit_message(callback: CallbackQuery, text: str, keyboard=None) -> None:
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise


async def _show_reviews(callback: CallbackQuery, page: int = 0) -> None:
    items = await reviews_store.approved()
    total = len(items)
    pages = max(1, (total + REVIEWS_PER_PAGE - 1) // REVIEWS_PER_PAGE)
    page = max(0, min(page, pages - 1))
    chunk = items[page * REVIEWS_PER_PAGE : (page + 1) * REVIEWS_PER_PAGE]

    if total:
        average = sum(item["rating"] for item in items) / total
        body = texts.REVIEWS_HEADER + "\n" + texts.reviews_summary(total, average)
        if pages > 1:
            body += f"\nСтраница {page + 1} из {pages}"
        body += "\n\n" + "\n\n".join(texts.review_block(item) for item in chunk)
    else:
        body = texts.REVIEWS_HEADER + "\n\n" + texts.REVIEWS_EMPTY

    await _edit_message(callback, body, reviews_keyboard(page, total))


@router.callback_query(F.data == "section:reviews")
async def show_reviews(callback: CallbackQuery, state: FSMContext) -> None:
    if await state.get_state():
        await state.clear()
    await _show_reviews(callback, 0)
    await callback.answer()


@router.callback_query(F.data.startswith("reviews:page:"))
async def reviews_page(callback: CallbackQuery) -> None:
    try:
        page = int(callback.data.rsplit(":", 1)[1])
    except ValueError:
        page = 0
    await _show_reviews(callback, page)
    await callback.answer()


@router.callback_query(F.data == "review:new")
async def start_review(callback: CallbackQuery, state: FSMContext) -> None:
    if not OWNER_ID:
        await callback.answer(texts.REVIEWS_UNAVAILABLE, show_alert=True)
        return

    now = time.time()
    if now - _last_review_at.get(callback.from_user.id, 0) < REVIEW_COOLDOWN_SECONDS:
        await callback.answer(texts.REVIEWS_COOLDOWN, show_alert=True)
        return

    await state.clear()
    await callback.message.answer(texts.REVIEWS_ASK_RATING, reply_markup=rating_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("review:rate:"))
async def review_rate(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        rating = int(callback.data.rsplit(":", 1)[1])
    except ValueError:
        await callback.answer("Не понял оценку 🙈")
        return
    if not 1 <= rating <= 5:
        await callback.answer("Оценка — от 1 до 5")
        return

    await state.clear()
    await state.update_data(rating=rating)
    await state.set_state(ReviewForm.text)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass

    await callback.message.answer(
        texts.REVIEWS_ASK_TEXT.format(stars=texts.stars(rating)),
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(ReviewForm.text)
async def review_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not 10 <= len(text) <= 600:
        await message.answer(texts.REVIEWS_BAD_TEXT, reply_markup=cancel_keyboard())
        return

    data = await state.get_data()
    review = await reviews_store.add(
        user_id=message.from_user.id,
        name=message.from_user.first_name or "Гость",
        username=message.from_user.username or "",
        rating=int(data.get("rating", 5)),
        text=text,
    )
    _last_review_at[message.from_user.id] = time.time()
    await state.clear()

    try:
        await message.bot.send_message(
            OWNER_ID,
            texts.owner_review_text(review),
            reply_markup=moderation_keyboard(review["id"]),
        )
    except Exception:
        logging.exception("Не удалось отправить отзыв владельцу (OWNER_ID=%s)", OWNER_ID)

    await message.answer(texts.REVIEWS_DONE, reply_markup=ReplyKeyboardRemove())
    await message.answer(texts.MENU_AGAIN, reply_markup=main_menu())


@router.callback_query(F.data.regexp(r"^rv(ok|no):\d+$"))
async def moderate_review(callback: CallbackQuery) -> None:
    if callback.from_user.id != OWNER_ID:
        await callback.answer(texts.REVIEWS_OWNER_ONLY, show_alert=True)
        return

    action, raw_id = callback.data.split(":")
    review = await reviews_store.get(int(raw_id))
    if not review:
        await callback.answer(texts.REVIEWS_NOT_FOUND, show_alert=True)
        return
    if review["status"] != "pending":
        await callback.answer(texts.REVIEWS_ALREADY_DONE, show_alert=True)
        return

    if action == "rvok":
        await reviews_store.set_status(review["id"], "approved")
        title = texts.REVIEWS_APPROVED
        try:
            await callback.bot.send_message(
                review["user_id"], texts.REVIEWS_PUBLISHED_TO_USER
            )
        except Exception:
            logging.info("Не удалось сообщить автору отзыва %s", review["user_id"])
    else:
        await reviews_store.set_status(review["id"], "rejected")
        title = texts.REVIEWS_REJECTED

    await _edit_message(
        callback,
        f"{title}\n\n{texts.review_block(review)}",
        None,
    )
    await callback.answer("Готово")


@router.message(Command("reviews"))
async def cmd_reviews(message: Message) -> None:
    if message.from_user.id != OWNER_ID:
        await message.answer(texts.REVIEWS_OWNER_ONLY)
        return

    items = await reviews_store.pending()
    if not items:
        await message.answer(texts.REVIEWS_PENDING_EMPTY)
        return

    for review in items:
        await message.answer(
            texts.owner_review_text(review),
            reply_markup=moderation_keyboard(review["id"]),
        )


# ---------- Разделы меню ----------

async def _leave_form(callback: CallbackQuery, state: FSMContext) -> None:
    if await state.get_state():
        await state.clear()
        await callback.message.answer(
            texts.ORDER_CANCELLED, reply_markup=ReplyKeyboardRemove()
        )


@router.callback_query(F.data == "menu")
async def show_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await _leave_form(callback, state)
    await callback.message.edit_text(texts.START_TEXT, reply_markup=main_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("section:"))
async def show_section(callback: CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":", 1)[1]
    text = texts.SECTIONS.get(key)
    if text is None:
        await callback.answer("Раздел не найден 🙈")
        return
    await _leave_form(callback, state)
    await callback.message.edit_text(text, reply_markup=section_menu(key))
    await callback.answer()


# ---------- Форма заявки ----------

@router.callback_query(F.data == "order")
async def start_order(callback: CallbackQuery, state: FSMContext) -> None:
    if not OWNER_ID:
        await callback.answer(texts.ORDER_UNAVAILABLE, show_alert=True)
        return

    now = time.time()
    if now - _last_order_at.get(callback.from_user.id, 0) < COOLDOWN_SECONDS:
        await callback.answer(texts.ORDER_COOLDOWN, show_alert=True)
        return

    await state.clear()
    await state.set_state(Form.name)
    await callback.message.answer(texts.ORDER_START, reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(Form.name)
async def form_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not 1 <= len(name) <= 100:
        await message.answer(texts.ORDER_BAD_NAME)
        return

    await state.update_data(name=name)
    await state.set_state(Form.task)
    await message.answer(texts.ORDER_ASK_TASK.format(name=html.escape(name)))


@router.message(Form.task)
async def form_task(message: Message, state: FSMContext) -> None:
    task = (message.text or "").strip()
    if not 3 <= len(task) <= 1000:
        await message.answer(texts.ORDER_BAD_TASK)
        return

    await state.update_data(task=task)
    await state.set_state(Form.contact)
    await message.answer(texts.ORDER_ASK_CONTACT)


@router.message(Form.contact)
async def form_contact(message: Message, state: FSMContext) -> None:
    contact = (message.text or "").strip()
    if len(contact) > 200:
        await message.answer(texts.ORDER_BAD_CONTACT)
        return

    if contact.lower() in {"-", "—", "нет", "пропустить"}:
        contact = "не указал"

    data = await state.get_data()
    username = f"@{message.from_user.username}" if message.from_user.username else "нет"

    summary = texts.ORDER_SUMMARY.format(
        name=html.escape(data.get("name", "")),
        task=html.escape(data.get("task", "")),
        contact=html.escape(contact),
        username=html.escape(username),
        user_id=message.from_user.id,
    )

    try:
        await message.bot.send_message(OWNER_ID, summary)
    except Exception:
        logging.exception("Не удалось отправить заявку владельцу (OWNER_ID=%s)", OWNER_ID)
        await state.clear()
        await message.answer(texts.ORDER_ERROR, reply_markup=ReplyKeyboardRemove())
        return

    _last_order_at[message.from_user.id] = time.time()
    await state.clear()

    logging.info("Новая заявка от %s (%s)", message.from_user.id, data.get("name"))
    await message.answer(texts.ORDER_DONE, reply_markup=ReplyKeyboardRemove())
    await message.answer(texts.MENU_AGAIN, reply_markup=main_menu())


# ---------- Всё остальное ----------

@router.message()
async def fallback(message: Message) -> None:
    """Сюда попадает любой текст, который не команда и не кнопка."""
    await message.answer(texts.UNKNOWN_TEXT, reply_markup=main_menu())


# ---------- Запуск ----------

async def main() -> None:
    token = os.getenv("BOT_TOKEN", "").strip()

    if not token or ":" not in token:
        print("\n[ОШИБКА] В файле .env нет токена.")
        print("Открой .env и вставь токен после BOT_TOKEN= (без кавычек и пробелов).\n")
        return

    try:
        bot, proxy, me = await build_bot(token)
    except TelegramUnauthorizedError:
        print("\n[ОШИБКА] Telegram не принял токен. Проверь его в .env или получи новый у @BotFather.\n")
        return
    except NoConnection:
        print("\n[ОШИБКА] Нет связи с Telegram ни напрямую, ни через прокси.")
        print("Включи VPN и проверь, что он запущен (иконка в трее).")
        print("Бот сам найдёт порт: 10809, 10801, 7890, 10808, 7891, 1080.\n")
        return

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    # Сбрасываем старые апдейты, чтобы бот не отвечал на сообщения, отправленные до запуска.
    await bot.delete_webhook(drop_pending_updates=True)

    print(f"\nБот @{me.username} запущен! Открой его в Telegram и напиши /start.")
    print(f"Подключение: {proxy or 'напрямую, без прокси'}")
    if OWNER_ID:
        print(f"Заявки будут приходить в чат с ID {OWNER_ID}.")
    else:
        print("OWNER_ID не задан — форма заявок выключена.")
        print("Напиши боту /myid, скопируй число в .env: OWNER_ID=...")
    print("Остановить: Ctrl+C в этом окне.\n")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен. До встречи!")
