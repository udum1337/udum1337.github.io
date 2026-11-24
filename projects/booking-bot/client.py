"""Клиентский сценарий: услуга → дата → время → имя → телефон → подтверждение."""

from __future__ import annotations

import re
from datetime import date, datetime
from sqlite3 import IntegrityError

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

import config
import db
import keyboards
import notifications
import slots
import texts

router = Router()


class BookingForm(StatesGroup):
    name = State()
    phone = State()


def _now() -> datetime:
    return datetime.now(config.TZ)


async def _edit(callback: CallbackQuery, text: str, keyboard=None) -> None:
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise


async def _barber_from_state(state: FSMContext):
    data = await state.get_data()
    barber_id = data.get("barber_id", 0)
    if not barber_id:
        return None
    barber = await db.get_barber(barber_id)
    return barber if barber and barber["active"] else None


def _barber_line(barber) -> str:
    if not barber:
        return ""
    fee = barber["extra_fee"]
    tail = f" · +{texts.format_price(fee)}" if fee else ""
    return f"\n💈 {texts.esc(barber['name'])}{tail}"


async def _slot_scope(service, barber_id: int, bookings: list):
    """Сколько барберов может вести это время и чьи записи учитывать."""
    if barber_id:
        return 1, [b for b in bookings if b["barber_id"] in (barber_id, 0)]

    all_barbers = await db.barbers_for_service(service["id"])
    if not all_barbers:
        return 1, bookings

    # Без выбора мастера отдаём только барберов без доплаты.
    free = [barber for barber in all_barbers if barber["extra_fee"] == 0]
    if not free:
        return 0, []

    ids = {barber["id"] for barber in free}
    return len(ids), [b for b in bookings if b["barber_id"] in ids]


async def _show_services(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    barber = await _barber_from_state(state)
    if data.get("barber_id") and not barber:
        await state.update_data(barber_id=0)

    services = await db.get_services()
    if barber:
        allowed = await db.list_barber_service_ids(barber["id"])
        if allowed:
            services = [service for service in services if service["id"] in allowed]
        if not services:
            await _edit(callback, texts.BARBER_NO_SERVICES, keyboards.back_menu())
            return
        await _edit(
            callback,
            texts.barber_services_text(services, barber),
            keyboards.services_kb(services, barber["extra_fee"], back="barbers"),
        )
        return

    if not services:
        await _edit(callback, "Пока нет доступных услуг. Загляни чуть позже.", keyboards.back_menu())
        return
    await _edit(callback, texts.services_text(services), keyboards.services_kb(services))


async def _show_dates(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    service = await db.get_service(data.get("service_id", 0))
    if not service:
        await _edit(callback, "Давай начнём заново. Нажми /start.", keyboards.back_menu())
        return

    barber = await _barber_from_state(state)
    if data.get("barber_id") and not barber:
        await state.update_data(barber_id=0)

    now = _now()
    days_off = {row["date"] for row in await db.list_days_off(now.date().isoformat())}
    days = slots.next_dates(now, days_off)
    if not days:
        await _edit(callback, "Пока нет открытых дней для записи. Напиши нам напрямую.", keyboards.back_menu())
        return

    fee = barber["extra_fee"] if barber else 0
    await _edit(
        callback,
        texts.CHOOSE_DATE.format(
            service=texts.esc(service["title"]),
            price=texts.format_price(service["price"] + fee),
            duration=service["duration"],
            barber_line=_barber_line(barber),
        ),
        keyboards.dates_kb(days, back="barbers" if barber else "book"),
    )


# ---------- Команды ----------

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    if await state.get_state():
        await state.clear()
        await message.answer(texts.FORM_CANCELLED, reply_markup=ReplyKeyboardRemove())
    await message.answer(texts.START_TEXT, reply_markup=keyboards.main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(texts.HELP_TEXT, reply_markup=keyboards.main_menu())


@router.message(Command("myid"))
async def cmd_myid(message: Message) -> None:
    await message.answer(f"Твой Telegram ID: <code>{message.from_user.id}</code>")


@router.message(Command("cancel"), StateFilter(BookingForm.name, BookingForm.phone))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.FORM_CANCELLED, reply_markup=ReplyKeyboardRemove())
    await message.answer(texts.START_TEXT, reply_markup=keyboards.main_menu())


@router.message(StateFilter(BookingForm.name, BookingForm.phone), F.text == texts.CANCEL_BUTTON)
async def cancel_button(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.FORM_CANCELLED, reply_markup=ReplyKeyboardRemove())
    await message.answer(texts.START_TEXT, reply_markup=keyboards.main_menu())


# ---------- Навигация ----------

@router.callback_query(F.data == "menu")
async def show_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _edit(callback, texts.START_TEXT, keyboards.main_menu())
    await callback.answer()


@router.callback_query(F.data == "book")
async def start_booking(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _show_services(callback, state)
    await callback.answer()


@router.callback_query(F.data == "services")
async def show_services(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _show_services(callback, state)
    await callback.answer()


@router.callback_query(F.data == "barbers")
async def show_barbers(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    barbers = await db.list_barbers()
    if not barbers:
        await _edit(callback, texts.BARBERS_EMPTY, keyboards.back_menu())
        await callback.answer()
        return
    await _edit(callback, texts.BARBERS_HEADER, keyboards.barbers_kb(barbers))
    await callback.answer()


@router.callback_query(F.data.startswith("barber:"))
async def show_barber(callback: CallbackQuery) -> None:
    barber_id = int(callback.data.split(":", 1)[1])
    barber = await db.get_barber(barber_id)
    if not barber or not barber["active"]:
        await callback.answer("Барбер недоступен", show_alert=True)
        return
    services = await db.get_barber_service_titles(barber_id)
    await _edit(callback, texts.barber_card(barber, services), keyboards.barber_card_kb(barber))
    await callback.answer()


@router.callback_query(F.data.startswith("barberbook:"))
async def book_with_barber(callback: CallbackQuery, state: FSMContext) -> None:
    barber_id = int(callback.data.split(":", 1)[1])
    barber = await db.get_barber(barber_id)
    if not barber or not barber["active"]:
        await callback.answer("Барбер больше не принимает", show_alert=True)
        return
    await state.clear()
    await state.update_data(barber_id=barber_id)
    await _show_services(callback, state)
    await callback.answer()


@router.callback_query(F.data == "contacts")
async def show_contacts(callback: CallbackQuery) -> None:
    await _edit(callback, texts.CONTACTS_TEXT, keyboards.back_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("svc:"))
async def choose_service(callback: CallbackQuery, state: FSMContext) -> None:
    service_id = int(callback.data.split(":", 1)[1])
    service = await db.get_service(service_id)
    if not service or not service["active"]:
        await callback.answer("Услуга недоступна", show_alert=True)
        return

    barber = await _barber_from_state(state)
    if barber and not await db.barber_offers_service(barber["id"], service_id):
        await callback.answer("Этот мастер такую услугу не делает", show_alert=True)
        return

    await state.update_data(service_id=service_id)
    await _show_dates(callback, state)
    await callback.answer()


@router.callback_query(F.data == "backdates")
async def back_to_dates(callback: CallbackQuery, state: FSMContext) -> None:
    await _show_dates(callback, state)
    await callback.answer()


@router.callback_query(F.data.startswith("date:"))
async def choose_date(callback: CallbackQuery, state: FSMContext) -> None:
    iso = callback.data.split(":", 1)[1]
    data = await state.get_data()
    service = await db.get_service(data.get("service_id", 0))
    if not service:
        await callback.answer("Начнём заново", show_alert=True)
        await callback.message.answer(texts.START_TEXT, reply_markup=keyboards.main_menu())
        return

    try:
        day = date.fromisoformat(iso)
    except ValueError:
        await callback.answer("Не понял дату", show_alert=True)
        return

    if await db.is_day_off(iso):
        await callback.answer("Этот день закрыт. Выбери другой.", show_alert=True)
        return

    barber_id = data.get("barber_id", 0)
    barber = await _barber_from_state(state)
    if barber_id and not barber:
        await state.update_data(barber_id=0)
        barber_id = 0

    bookings = await db.get_active_bookings_on(iso)
    capacity, scoped = await _slot_scope(service, barber_id, bookings)
    times = slots.available_slots(day, service["duration"], scoped, _now(), capacity)
    if not times:
        now = _now()
        days_off = {row["date"] for row in await db.list_days_off(now.date().isoformat())}
        await _edit(
            callback,
            texts.NO_SLOTS.format(date=texts.format_date(iso)),
            keyboards.dates_kb(
                slots.next_dates(now, days_off),
                back="barbers" if barber else "book",
            ),
        )
        await callback.answer()
        return

    await state.update_data(date=iso)
    await _edit(
        callback,
        texts.CHOOSE_TIME.format(
            service=texts.esc(service["title"]),
            date=texts.format_date(iso),
            barber_line=_barber_line(barber),
        ),
        keyboards.times_kb(times),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("slot:"))
async def choose_time(callback: CallbackQuery, state: FSMContext) -> None:
    time_str = callback.data.split(":", 1)[1]
    await state.update_data(time=time_str)
    await state.set_state(BookingForm.name)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await callback.message.answer(texts.ASK_NAME, reply_markup=keyboards.name_kb())
    await callback.answer()


# ---------- Форма ----------

@router.message(BookingForm.name)
async def enter_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not 2 <= len(name) <= 60:
        await message.answer(texts.ERROR_NAME, reply_markup=keyboards.name_kb())
        return
    await state.update_data(name=name)
    await state.set_state(BookingForm.phone)
    await message.answer(texts.ASK_PHONE, reply_markup=keyboards.phone_kb())


@router.message(BookingForm.phone)
async def enter_phone(message: Message, state: FSMContext) -> None:
    if message.text == texts.MANUAL_PHONE:
        await message.answer(texts.PHONE_MANUAL, reply_markup=keyboards.phone_kb())
        return

    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = (message.text or "").strip()

    digits = re.sub(r"\D", "", phone)
    if not 10 <= len(digits) <= 15:
        await message.answer(texts.ERROR_PHONE, reply_markup=keyboards.phone_kb())
        return

    await state.update_data(phone=phone)

    data = await state.get_data()
    service = await db.get_service(data.get("service_id", 0))
    if not service:
        await state.clear()
        await message.answer("Сессия истекла. Начнём заново.", reply_markup=ReplyKeyboardRemove())
        await message.answer(texts.START_TEXT, reply_markup=keyboards.main_menu())
        return

    barber = await _barber_from_state(state)
    if data.get("barber_id") and not barber:
        await state.update_data(barber_id=0)

    fee = barber["extra_fee"] if barber else 0
    fee_note = ""
    if fee:
        fee_note = (
            f" (услуга {texts.format_price(service['price'])} + "
            f"доплата {texts.format_price(fee)})"
        )

    await message.answer(texts.CONFIRM_TITLE, reply_markup=ReplyKeyboardRemove())
    await message.answer(
        texts.CONFIRM_TEXT.format(
            service=texts.esc(service["title"]),
            date=texts.format_date(data["date"]),
            time=data["time"],
            duration=service["duration"],
            barber=texts.esc(barber["name"]) if barber else "любой свободный",
            total=texts.format_price(service["price"] + fee),
            fee_note=fee_note,
            name=texts.esc(data["name"]),
            phone=texts.esc(phone),
        ),
        reply_markup=keyboards.confirm_kb(),
    )


@router.callback_query(F.data == "confirm:yes")
async def confirm_booking(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    required = {"service_id", "date", "time", "name", "phone"}
    if not required.issubset(data):
        await state.clear()
        await callback.answer("Сессия истекла, начни заново", show_alert=True)
        await callback.message.answer(texts.START_TEXT, reply_markup=keyboards.main_menu())
        return

    service = await db.get_service(data["service_id"])
    if not service or not service["active"]:
        await state.clear()
        await callback.answer("Услуга больше недоступна", show_alert=True)
        return

    barber_id = data.get("barber_id", 0)
    barber = await db.get_barber(barber_id) if barber_id else None
    if barber_id and (
        not barber
        or not barber["active"]
        or not await db.barber_offers_service(barber_id, service["id"])
    ):
        await state.clear()
        await _edit(callback, texts.BARBER_GONE, keyboards.back_menu())
        await callback.answer()
        return

    # Перепроверяем слот: пока клиент заполнял форму, время могли занять.
    bookings = await db.get_active_bookings_on(data["date"])
    capacity, scoped = await _slot_scope(service, barber_id, bookings)
    free = slots.available_slots(
        date.fromisoformat(data["date"]), service["duration"], scoped, _now(), capacity
    )
    if data["time"] not in free:
        await state.clear()
        await _edit(callback, texts.SLOT_TAKEN, keyboards.back_menu())
        await callback.answer()
        return

    booking_id = None
    assigned = barber
    fee = barber["extra_fee"] if barber else 0
    for _ in range(3):
        if not barber:
            assigned = await db.pick_barber(
                service["id"], data["date"], data["time"], service["duration"],
                free_only=True,
            )
            if not assigned and await db.list_barbers():
                break
            fee = 0

        try:
            booking_id = await db.create_booking(
                user_id=callback.from_user.id,
                client_name=data["name"],
                phone=data["phone"],
                username=callback.from_user.username or "",
                service_id=service["id"],
                date=data["date"],
                time=data["time"],
                barber_id=assigned["id"] if assigned else 0,
                barber_fee=fee,
            )
            break
        except IntegrityError:
            if barber:
                break
            assigned = None

    if not booking_id:
        await state.clear()
        await _edit(callback, texts.SLOT_TAKEN, keyboards.back_menu())
        await callback.answer()
        return

    booking = await db.get_booking(booking_id)
    await notifications.notify_new_booking(callback.bot, booking)
    await state.clear()

    await _edit(
        callback,
        texts.BOOKED_TEXT.format(
            service=texts.esc(service["title"]),
            date=texts.format_date(data["date"]),
            time=data["time"],
            barber=texts.esc(booking["barber_name"]) if booking["barber_name"] else "любой",
            total=texts.format_price(booking["price"] + booking["barber_fee"]),
            address=config.ADDRESS,
        ),
        keyboards.after_booking_kb(),
    )
    await callback.answer("Записал ✅")


@router.callback_query(F.data == "confirm:no")
async def decline_booking(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _edit(callback, texts.FORM_CANCELLED, keyboards.back_menu())
    await callback.answer()


# ---------- Мои записи ----------

@router.callback_query(F.data == "my")
async def my_bookings(callback: CallbackQuery) -> None:
    rows = await db.get_user_bookings(callback.from_user.id, _now().date().isoformat())
    if not rows:
        await _edit(callback, texts.MY_EMPTY, keyboards.main_menu())
        await callback.answer()
        return

    body = texts.MY_HEADER + "\n\n".join(texts.booking_short(row) for row in rows)
    await _edit(callback, body, keyboards.my_bookings_kb(rows))
    await callback.answer()


@router.callback_query(F.data.startswith("mycancel:"))
async def cancel_my_booking(callback: CallbackQuery) -> None:
    booking_id = int(callback.data.split(":", 1)[1])
    booking = await db.get_booking(booking_id)

    if not booking or booking["user_id"] != callback.from_user.id or booking["status"] != "active":
        await callback.answer("Запись не найдена", show_alert=True)
        return

    await db.cancel_booking(booking_id)
    await notifications.notify_cancelled_by_client(callback.bot, booking)
    await _edit(callback, texts.CANCELLED, keyboards.after_booking_kb())
    await callback.answer("Отменено")


# ---------- Всё остальное ----------

@router.message()
async def fallback(message: Message, state: FSMContext) -> None:
    if await state.get_state() == BookingForm.name.state:
        await message.answer(texts.ERROR_NAME, reply_markup=keyboards.name_kb())
        return
    if await state.get_state() == BookingForm.phone.state:
        await message.answer(texts.ERROR_PHONE, reply_markup=keyboards.phone_kb())
        return
    await message.answer(texts.UNKNOWN, reply_markup=keyboards.main_menu())
