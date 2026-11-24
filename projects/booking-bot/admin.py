"""Панель записей: владелец видит всё, барбер — только свои записи."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, ReplyKeyboardRemove

import config
import db
import keyboards
import notifications
import texts

router = Router()


class ServiceForm(StatesGroup):
    title = State()
    duration = State()
    price = State()


class ServiceEditForm(StatesGroup):
    title = State()
    duration = State()
    price = State()


class DayOffForm(StatesGroup):
    date = State()


FORM_STATES = StateFilter(
    ServiceForm.title,
    ServiceForm.duration,
    ServiceForm.price,
    ServiceEditForm.title,
    ServiceEditForm.duration,
    ServiceEditForm.price,
    DayOffForm.date,
)


def _now() -> datetime:
    return datetime.now(config.TZ)


def _is_owner(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


async def _barber_for_user(user_id: int):
    return await db.get_barber_by_user(user_id)


async def _is_admin(user_id: int) -> bool:
    return _is_owner(user_id) or await _barber_for_user(user_id) is not None


async def _owner_only(callback: CallbackQuery) -> bool:
    if _is_owner(callback.from_user.id):
        return True
    await callback.answer("Доступно только владельцу", show_alert=True)
    return False


async def _edit(callback: CallbackQuery, text: str, keyboard=None) -> None:
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise


async def _show_bookings(
    callback: CallbackQuery,
    start: date,
    end: date,
    label: str,
    barber_id: int | None = None,
) -> None:
    rows = await db.get_bookings_range(start.isoformat(), end.isoformat(), barber_id)
    if not rows:
        await _edit(callback, texts.ADMIN_NO_BOOKINGS.format(period=label), keyboards.back_admin())
        return

    shown = rows[:30]
    body = f"<b>Записи: {label}</b>\n\n" + "\n\n".join(
        texts.admin_booking_line(row) for row in shown
    )
    if len(rows) > len(shown):
        body += f"\n\n…и ещё {len(rows) - len(shown)}. Полный список — в базе."
    await _edit(callback, body, keyboards.admin_bookings_kb(shown))


def _service_card(service) -> tuple[str, InlineKeyboardMarkup]:
    status = texts.ADMIN_SERVICE_ACTIVE if service["active"] else texts.ADMIN_SERVICE_HIDDEN
    text = texts.ADMIN_SERVICE_CARD.format(
        title=texts.esc(service["title"]),
        duration=service["duration"],
        price=texts.format_price(service["price"]),
        status=status,
    )
    return text, keyboards.admin_service_card_kb(service)


async def _show_days(callback: CallbackQuery) -> None:
    rows = await db.list_days_off(_now().date().isoformat())
    if not rows:
        await _edit(callback, texts.ADMIN_DAYS_EMPTY, keyboards.back_admin())
        return
    await _edit(callback, texts.ADMIN_DAYS_HEADER, keyboards.days_off_kb(rows))


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    if not await _is_admin(message.from_user.id):
        await message.answer(texts.ADMIN_NO_ACCESS.format(user_id=message.from_user.id))
        return
    if await state.get_state():
        await state.clear()
        await message.answer("Ок.", reply_markup=ReplyKeyboardRemove())
    owner = _is_owner(message.from_user.id)
    text = texts.ADMIN_MENU if owner else texts.ADMIN_MENU_BARBER
    await message.answer(text, reply_markup=keyboards.admin_menu_kb(owner))


@router.message(FORM_STATES, F.text == texts.CANCEL_BUTTON)
async def cancel_admin_form(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Ок, отменил.", reply_markup=ReplyKeyboardRemove())
    owner = _is_owner(message.from_user.id)
    text = texts.ADMIN_MENU if owner else texts.ADMIN_MENU_BARBER
    await message.answer(text, reply_markup=keyboards.admin_menu_kb(owner))


# ---------- Записи ----------

@router.callback_query(F.data == "admin:back")
async def admin_back(callback: CallbackQuery) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    owner = _is_owner(callback.from_user.id)
    text = texts.ADMIN_MENU if owner else texts.ADMIN_MENU_BARBER
    await _edit(callback, text, keyboards.admin_menu_kb(owner))
    await callback.answer()


@router.callback_query(F.data == "admin:today")
async def admin_today(callback: CallbackQuery) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    today = _now().date()
    barber = None if _is_owner(callback.from_user.id) else await _barber_for_user(callback.from_user.id)
    await _show_bookings(callback, today, today, "сегодня", barber["id"] if barber else None)
    await callback.answer()


@router.callback_query(F.data == "admin:tomorrow")
async def admin_tomorrow(callback: CallbackQuery) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    tomorrow = _now().date() + timedelta(days=1)
    barber = None if _is_owner(callback.from_user.id) else await _barber_for_user(callback.from_user.id)
    await _show_bookings(
        callback, tomorrow, tomorrow, "завтра", barber["id"] if barber else None
    )
    await callback.answer()


@router.callback_query(F.data == "admin:week")
async def admin_week(callback: CallbackQuery) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    today = _now().date()
    barber = None if _is_owner(callback.from_user.id) else await _barber_for_user(callback.from_user.id)
    await _show_bookings(
        callback,
        today,
        today + timedelta(days=6),
        "ближайшая неделя",
        barber["id"] if barber else None,
    )
    await callback.answer()


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery) -> None:
    if not await _owner_only(callback):
        return

    today = _now().date()
    today_count, today_sum = await db.stats_for_range(today.isoformat(), today.isoformat())
    week_count, week_sum = await db.stats_for_range(
        today.isoformat(), (today + timedelta(days=6)).isoformat()
    )
    await _edit(
        callback,
        texts.ADMIN_STATS.format(
            today_count=today_count,
            today_sum=texts.format_price(today_sum),
            week_count=week_count,
            week_sum=texts.format_price(week_sum),
        ),
        keyboards.back_admin(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admincancel:"))
async def admin_cancel(callback: CallbackQuery) -> None:
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    booking_id = int(callback.data.split(":", 1)[1])
    booking = await db.get_booking(booking_id)
    if not booking or booking["status"] != "active":
        await callback.answer("Запись уже отменена", show_alert=True)
        return

    if not _is_owner(callback.from_user.id):
        barber = await _barber_for_user(callback.from_user.id)
        if not barber or booking["barber_id"] != barber["id"]:
            await callback.answer("Это запись другого барбера", show_alert=True)
            return

    await db.cancel_booking(booking_id)
    await notifications.notify_client_cancelled_by_admin(callback.bot, booking)

    try:
        await callback.message.edit_text(
            "❌ <b>Запись отменена</b>\n\n" + texts.admin_booking_line(booking),
            reply_markup=None,
        )
    except TelegramBadRequest:
        pass
    await callback.answer("Отменено")


# ---------- Услуги ----------

@router.callback_query(F.data == "admin:services")
async def admin_services(callback: CallbackQuery) -> None:
    if not await _owner_only(callback):
        return

    services = await db.get_services(active_only=False)
    if not services:
        await _edit(callback, "Услуг пока нет.", keyboards.admin_services_kb([]))
        await callback.answer()
        return

    await _edit(
        callback,
        texts.ADMIN_SERVICES_HEADER,
        keyboards.admin_services_kb(services),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adminsvc:"))
async def admin_service_card(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _owner_only(callback):
        return

    service_id = int(callback.data.split(":", 1)[1])
    service = await db.get_service(service_id)
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return

    if await state.get_state():
        await state.clear()
    text, keyboard = _service_card(service)
    await _edit(callback, text, keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("svcedit:"))
async def admin_service_edit(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _owner_only(callback):
        return

    try:
        _, raw_id, field = callback.data.split(":")
        service_id = int(raw_id)
    except ValueError:
        await callback.answer("Не понял, что менять", show_alert=True)
        return

    service = await db.get_service(service_id)
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return

    await state.clear()
    await state.update_data(service_id=service_id)

    if field == "title":
        await state.set_state(ServiceEditForm.title)
        prompt = texts.ADMIN_EDIT_TITLE.format(old=texts.esc(service["title"]))
    elif field == "duration":
        await state.set_state(ServiceEditForm.duration)
        prompt = texts.ADMIN_EDIT_DURATION.format(old=service["duration"])
    elif field == "price":
        await state.set_state(ServiceEditForm.price)
        prompt = texts.ADMIN_EDIT_PRICE.format(old=service["price"])
    else:
        await callback.answer("Не понял, что менять", show_alert=True)
        return

    await callback.message.answer(prompt, reply_markup=keyboards.admin_form_kb())
    await callback.answer()


async def _finish_edit(message: Message, state: FSMContext, apply) -> None:
    """Применяет изменение к услуге и показывает обновлённую карточку."""
    data = await state.get_data()
    service = await db.get_service(data.get("service_id", 0))
    if not service:
        await state.clear()
        await message.answer("Услуга не найдена.", reply_markup=ReplyKeyboardRemove())
        await message.answer(texts.ADMIN_MENU, reply_markup=keyboards.admin_menu_kb(True))
        return

    title, duration, price = apply(service)
    await db.update_service(service["id"], title, duration, price)
    await state.clear()

    updated = await db.get_service(service["id"])
    await message.answer(
        texts.ADMIN_EDIT_DONE.format(
            title=texts.esc(updated["title"]),
            duration=updated["duration"],
            price=texts.format_price(updated["price"]),
        ),
        reply_markup=ReplyKeyboardRemove(),
    )
    text, keyboard = _service_card(updated)
    await message.answer(text, reply_markup=keyboard)


@router.message(ServiceEditForm.title)
async def edit_service_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not 2 <= len(title) <= 60:
        await message.answer(texts.ADMIN_ERR_TITLE, reply_markup=keyboards.admin_form_kb())
        return
    await _finish_edit(
        message,
        state,
        lambda service: (title, service["duration"], service["price"]),
    )


@router.message(ServiceEditForm.duration)
async def edit_service_duration(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if not value.isdigit() or not 15 <= int(value) <= 240:
        await message.answer(texts.ADMIN_ERR_DURATION, reply_markup=keyboards.admin_form_kb())
        return
    duration = int(value)
    await _finish_edit(
        message,
        state,
        lambda service: (service["title"], duration, service["price"]),
    )


@router.message(ServiceEditForm.price)
async def edit_service_price(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if not value.isdigit() or not 0 <= int(value) <= 100000:
        await message.answer(texts.ADMIN_ERR_PRICE, reply_markup=keyboards.admin_form_kb())
        return
    price = int(value)
    await _finish_edit(
        message,
        state,
        lambda service: (service["title"], service["duration"], price),
    )


@router.callback_query(F.data.startswith("svctoggle:"))
async def admin_service_toggle(callback: CallbackQuery) -> None:
    if not await _owner_only(callback):
        return

    service_id = int(callback.data.split(":", 1)[1])
    service = await db.get_service(service_id)
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return

    await db.set_service_active(service_id, not service["active"])
    updated = await db.get_service(service_id)

    template = (
        texts.ADMIN_SERVICE_SHOWN_DONE if updated["active"] else texts.ADMIN_SERVICE_HIDDEN_DONE
    )
    text, keyboard = _service_card(updated)
    await _edit(callback, text, keyboard)
    await callback.answer(template.format(title=updated["title"])[:190])


@router.callback_query(F.data == "admin:addservice")
async def admin_add_service(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _owner_only(callback):
        return
    await state.clear()
    await state.set_state(ServiceForm.title)
    await callback.message.answer(texts.ADMIN_ADD_TITLE, reply_markup=keyboards.admin_form_kb())
    await callback.answer()


@router.message(ServiceForm.title)
async def service_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not 2 <= len(title) <= 60:
        await message.answer(texts.ADMIN_ERR_TITLE, reply_markup=keyboards.admin_form_kb())
        return
    await state.update_data(title=title)
    await state.set_state(ServiceForm.duration)
    await message.answer(texts.ADMIN_ADD_DURATION, reply_markup=keyboards.admin_form_kb())


@router.message(ServiceForm.duration)
async def service_duration(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if not value.isdigit() or not 15 <= int(value) <= 240:
        await message.answer(texts.ADMIN_ERR_DURATION, reply_markup=keyboards.admin_form_kb())
        return
    await state.update_data(duration=int(value))
    await state.set_state(ServiceForm.price)
    await message.answer(texts.ADMIN_ADD_PRICE, reply_markup=keyboards.admin_form_kb())


@router.message(ServiceForm.price)
async def service_price(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if not value.isdigit() or not 0 <= int(value) <= 100000:
        await message.answer(texts.ADMIN_ERR_PRICE, reply_markup=keyboards.admin_form_kb())
        return

    data = await state.get_data()
    await db.add_service(data["title"], data["duration"], int(value))
    await state.clear()
    await message.answer(
        texts.ADMIN_ADD_DONE.format(title=texts.esc(data["title"])),
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer(texts.ADMIN_MENU, reply_markup=keyboards.admin_menu_kb(True))


# ---------- Выходные ----------

@router.callback_query(F.data == "admin:dayoff")
async def admin_dayoff(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _owner_only(callback):
        return
    await state.clear()
    await state.set_state(DayOffForm.date)
    await callback.message.answer(texts.ADMIN_DAYOFF_ASK, reply_markup=keyboards.admin_form_kb())
    await callback.answer()


@router.message(DayOffForm.date)
async def dayoff_date(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    try:
        day = date.fromisoformat(value)
    except ValueError:
        await message.answer(texts.ADMIN_DAYOFF_BAD, reply_markup=keyboards.admin_form_kb())
        return
    if day < _now().date():
        await message.answer(texts.ADMIN_DAYOFF_BAD, reply_markup=keyboards.admin_form_kb())
        return

    await db.add_day_off(day.isoformat())
    await state.clear()
    await message.answer(
        texts.ADMIN_DAYOFF_DONE.format(date=texts.format_date(day.isoformat())),
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer(texts.ADMIN_MENU, reply_markup=keyboards.admin_menu_kb(True))


@router.callback_query(F.data == "admin:days")
async def admin_days(callback: CallbackQuery) -> None:
    if not await _owner_only(callback):
        return
    await _show_days(callback)
    await callback.answer()


@router.callback_query(F.data.startswith("undoday:"))
async def admin_undo_day(callback: CallbackQuery) -> None:
    if not await _owner_only(callback):
        return
    iso = callback.data.split(":", 1)[1]
    await db.remove_day_off(iso)
    await _show_days(callback)
    await callback.answer("День снова открыт")
