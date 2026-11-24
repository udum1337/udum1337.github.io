"""Барберы и настройки уведомлений. Всё это доступно владельцу."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

import config
import db
import keyboards
import texts

router = Router()


class BarberForm(StatesGroup):
    name = State()
    user_id = State()


class BarberEditForm(StatesGroup):
    value = State()


FORM_STATES = StateFilter(BarberForm.name, BarberForm.user_id, BarberEditForm.value)


def _is_owner(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


async def _is_staff(user_id: int) -> bool:
    return _is_owner(user_id) or await db.get_barber_by_user(user_id) is not None


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


async def _barber_card(barber):
    services = await db.get_barber_service_titles(barber["id"])
    user = f"<code>{barber['user_id']}</code>" if barber["user_id"] else "не привязан"
    text = texts.ADMIN_BARBER_CARD.format(
        name=texts.esc(barber["name"]),
        rating=texts.format_rating(barber["rating"]),
        experience=texts.esc(barber["experience"] or "не указан"),
        fee=texts.format_price(barber["extra_fee"]),
        services=texts.esc(", ".join(services) if services else "все услуги"),
        user=user,
        status=texts.ADMIN_BARBER_ACTIVE if barber["active"] else texts.ADMIN_BARBER_HIDDEN,
    )
    return text, keyboards.admin_barber_card_kb(barber)


async def _show_barber(callback: CallbackQuery, barber_id: int) -> None:
    barber = await db.get_barber(barber_id)
    if not barber:
        await callback.answer("Барбер не найден", show_alert=True)
        return
    text, keyboard = await _barber_card(barber)
    await _edit(callback, text, keyboard)


@router.callback_query(F.data == "admin:barbers")
async def admin_barbers(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _owner_only(callback):
        return
    if await state.get_state():
        await state.clear()

    barbers = await db.list_barbers(active_only=False)
    text = texts.ADMIN_BARBERS_HEADER if barbers else texts.ADMIN_BARBERS_EMPTY
    await _edit(callback, text, keyboards.admin_barbers_kb(barbers))
    await callback.answer()


@router.callback_query(F.data.startswith("adminbarber:"))
async def admin_barber_card(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _owner_only(callback):
        return
    if await state.get_state():
        await state.clear()
    barber_id = int(callback.data.split(":", 1)[1])
    await _show_barber(callback, barber_id)
    await callback.answer()


@router.callback_query(F.data == "admin:barberadd")
async def admin_barber_add(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _owner_only(callback):
        return
    await state.clear()
    await state.set_state(BarberForm.name)
    await callback.message.answer(
        texts.ADMIN_BARBER_ADD_NAME, reply_markup=keyboards.admin_form_kb()
    )
    await callback.answer()


@router.message(BarberForm.name)
async def barber_add_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not 2 <= len(name) <= 40:
        await message.answer(texts.ADMIN_BARBER_ERR_NAME, reply_markup=keyboards.admin_form_kb())
        return
    await state.update_data(name=name)
    await state.set_state(BarberForm.user_id)
    await message.answer(texts.ADMIN_BARBER_ADD_ID, reply_markup=keyboards.admin_form_kb())


@router.message(BarberForm.user_id)
async def barber_add_id(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if raw in {"-", "—", "–"}:
        user_id = None
    elif raw.isdigit() and 5 <= len(raw) <= 15:
        user_id = int(raw)
        if await db.get_barber_by_user(user_id):
            await message.answer(
                texts.ADMIN_BARBER_ID_TAKEN, reply_markup=keyboards.admin_form_kb()
            )
            return
    else:
        await message.answer(texts.ADMIN_BARBER_ID_BAD, reply_markup=keyboards.admin_form_kb())
        return

    data = await state.get_data()
    name = data.get("name", "")
    barber_id = await db.add_barber(name, user_id)
    await state.clear()

    note = texts.ADMIN_BARBER_ADDED.format(name=texts.esc(name))
    if user_id:
        try:
            await message.bot.send_message(user_id, texts.ADMIN_BARBER_WELCOME)
        except Exception:
            note = texts.ADMIN_BARBER_ADDED_NO_START.format(name=texts.esc(name))

    await message.answer(note, reply_markup=ReplyKeyboardRemove())
    barber = await db.get_barber(barber_id)
    text, keyboard = await _barber_card(barber)
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("barberedit:"))
async def admin_barber_edit(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _owner_only(callback):
        return

    try:
        _, raw_id, field = callback.data.split(":")
        barber_id = int(raw_id)
    except ValueError:
        await callback.answer("Не понял, что менять", show_alert=True)
        return

    barber = await db.get_barber(barber_id)
    if not barber:
        await callback.answer("Барбер не найден", show_alert=True)
        return

    prompts = {
        "name": texts.ADMIN_BARBER_EDIT_NAME.format(old=texts.esc(barber["name"])),
        "experience": texts.ADMIN_BARBER_EDIT_EXPERIENCE.format(
            old=texts.esc(barber["experience"] or "не указан")
        ),
        "rating": texts.ADMIN_BARBER_EDIT_RATING.format(
            old=texts.format_rating(barber["rating"])
        ),
        "extra_fee": texts.ADMIN_BARBER_EDIT_FEE.format(
            old=barber["extra_fee"]
        ),
        "user_id": texts.ADMIN_BARBER_EDIT_ID.format(
            old=barber["user_id"] or "не привязан"
        ),
    }
    prompt = prompts.get(field)
    if not prompt:
        await callback.answer("Не понял, что менять", show_alert=True)
        return

    await state.clear()
    await state.update_data(barber_id=barber_id, field=field)
    await state.set_state(BarberEditForm.value)
    await callback.message.answer(prompt, reply_markup=keyboards.admin_form_kb())
    await callback.answer()


def _parse_field(field: str, raw: str):
    if field == "name":
        if not 2 <= len(raw) <= 40:
            return None, texts.ADMIN_BARBER_ERR_NAME
        return raw, None

    if field == "experience":
        if raw in {"-", "—", "–"}:
            return "", None
        if not 2 <= len(raw) <= 40:
            return None, texts.ADMIN_BARBER_ERR_EXPERIENCE
        return raw, None

    if field == "rating":
        try:
            value = round(float(raw.replace(",", ".")), 1)
        except ValueError:
            return None, texts.ADMIN_BARBER_ERR_RATING
        if not 0 <= value <= 5:
            return None, texts.ADMIN_BARBER_ERR_RATING
        return value, None

    if field == "extra_fee":
        if not raw.isdigit() or not 0 <= int(raw) <= 50000:
            return None, texts.ADMIN_BARBER_ERR_FEE
        return int(raw), None

    if field == "user_id":
        if raw in {"-", "—", "–"}:
            return None, None
        if not raw.isdigit() or not 5 <= len(raw) <= 15:
            return None, texts.ADMIN_BARBER_ERR_ID
        return int(raw), None

    return None, "Не понял, что менять"


@router.message(BarberEditForm.value)
async def barber_edit_value(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    barber_id = data.get("barber_id", 0)
    field = data.get("field", "")
    barber = await db.get_barber(barber_id)
    if not barber:
        await state.clear()
        await message.answer("Барбер не найден.", reply_markup=ReplyKeyboardRemove())
        return

    raw = (message.text or "").strip()
    value, error = _parse_field(field, raw)
    if error:
        await message.answer(error, reply_markup=keyboards.admin_form_kb())
        return

    if field == "user_id" and value is not None:
        other = await db.get_barber_by_user(value)
        if other and other["id"] != barber["id"]:
            await message.answer(
                texts.ADMIN_BARBER_ID_TAKEN, reply_markup=keyboards.admin_form_kb()
            )
            return

    await db.update_barber(barber_id, field, value)
    await state.clear()

    updated = await db.get_barber(barber_id)
    await message.answer("Сохранил.", reply_markup=ReplyKeyboardRemove())
    text, keyboard = await _barber_card(updated)
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("barbertoggle:"))
async def admin_barber_toggle(callback: CallbackQuery) -> None:
    if not await _owner_only(callback):
        return
    barber_id = int(callback.data.split(":", 1)[1])
    barber = await db.get_barber(barber_id)
    if not barber:
        await callback.answer("Барбер не найден", show_alert=True)
        return

    await db.set_barber_active(barber_id, not barber["active"])
    updated = await db.get_barber(barber_id)
    text, keyboard = await _barber_card(updated)
    await _edit(callback, text, keyboard)
    template = (
        texts.ADMIN_BARBER_SHOWN_DONE if updated["active"] else texts.ADMIN_BARBER_HIDDEN_DONE
    )
    await callback.answer(template.format(name=updated["name"])[:190])


@router.callback_query(F.data.startswith("barberservices:"))
async def admin_barber_services(callback: CallbackQuery) -> None:
    if not await _owner_only(callback):
        return
    barber_id = int(callback.data.split(":", 1)[1])
    barber = await db.get_barber(barber_id)
    if not barber:
        await callback.answer("Барбер не найден", show_alert=True)
        return

    services = await db.get_services()
    if not services:
        await callback.answer("Сначала добавь услуги", show_alert=True)
        return

    selected = await db.list_barber_service_ids(barber_id)
    await _edit(
        callback,
        texts.ADMIN_BARBER_SERVICES_HEADER.format(name=texts.esc(barber["name"])),
        keyboards.admin_barber_services_kb(barber_id, services, selected),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bsvc:"))
async def admin_barber_service_toggle(callback: CallbackQuery) -> None:
    if not await _owner_only(callback):
        return
    try:
        _, raw_barber, raw_service = callback.data.split(":")
        barber_id = int(raw_barber)
        service_id = int(raw_service)
    except ValueError:
        await callback.answer("Не понял", show_alert=True)
        return

    barber = await db.get_barber(barber_id)
    if not barber:
        await callback.answer("Барбер не найден", show_alert=True)
        return

    await db.toggle_barber_service(barber_id, service_id)
    services = await db.get_services()
    selected = await db.list_barber_service_ids(barber_id)
    await _edit(
        callback,
        texts.ADMIN_BARBER_SERVICES_HEADER.format(name=texts.esc(barber["name"])),
        keyboards.admin_barber_services_kb(barber_id, services, selected),
    )
    await callback.answer(texts.ADMIN_BARBER_SERVICES_SAVED)


# ---------- Уведомления ----------

async def _notify_people() -> list[tuple[int, str]]:
    people: list[tuple[int, str]] = []
    seen: set[int] = set()
    for user_id in config.ADMIN_IDS:
        people.append((user_id, f"👑 Владелец {user_id}"))
        seen.add(user_id)
    for barber in await db.list_barbers(active_only=False):
        if barber["user_id"] and barber["user_id"] not in seen:
            people.append(
                (barber["user_id"], f"{barber['name']} · {barber['user_id']}")
            )
            seen.add(barber["user_id"])
    return people


async def _show_notify_person(callback: CallbackQuery, user_id: int) -> bool:
    barber = await db.get_barber_by_user(user_id)
    if user_id in config.ADMIN_IDS:
        name = "владелец"
    elif barber:
        name = barber["name"]
    else:
        return False

    new_on, cancel_on = await db.get_notify_settings(user_id)
    text = texts.ADMIN_NOTIFY_CARD.format(
        name=texts.esc(name),
        new=texts.ADMIN_NOTIFY_ON if new_on else texts.ADMIN_NOTIFY_OFF,
        cancel=texts.ADMIN_NOTIFY_ON if cancel_on else texts.ADMIN_NOTIFY_OFF,
    )
    await _edit(callback, text, keyboards.notify_person_kb(user_id, new_on, cancel_on))
    return True


@router.callback_query(F.data == "admin:notify")
async def admin_notify(callback: CallbackQuery) -> None:
    if not await _is_staff(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    if not _is_owner(callback.from_user.id):
        await _show_notify_person(callback, callback.from_user.id)
        await callback.answer()
        return

    people = await _notify_people()
    if not people:
        await _edit(callback, texts.ADMIN_NOTIFY_EMPTY, keyboards.back_admin())
    else:
        await _edit(callback, texts.ADMIN_NOTIFY_HEADER, keyboards.notify_people_kb(people))
    await callback.answer()


@router.callback_query(F.data.startswith("notif:"))
async def admin_notify_person(callback: CallbackQuery) -> None:
    user_id = int(callback.data.split(":", 1)[1])
    if not _is_owner(callback.from_user.id) and callback.from_user.id != user_id:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await _show_notify_person(callback, user_id)
    await callback.answer()


@router.callback_query(F.data.startswith("notiftoggle:"))
async def admin_notify_toggle(callback: CallbackQuery) -> None:
    try:
        _, raw_id, kind = callback.data.split(":")
        user_id = int(raw_id)
    except ValueError:
        await callback.answer("Не понял", show_alert=True)
        return

    if not _is_owner(callback.from_user.id) and callback.from_user.id != user_id:
        await callback.answer("Нет доступа", show_alert=True)
        return
    if kind not in {"new", "cancel"}:
        await callback.answer("Не понял", show_alert=True)
        return

    enabled = await db.notify_enabled(user_id, kind)
    await db.set_notify_setting(user_id, kind, not enabled)
    await _show_notify_person(callback, user_id)
    await callback.answer("Сохранил")


@router.message(FORM_STATES, F.text == texts.CANCEL_BUTTON)
async def cancel_barber_form(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Ок, отменил.", reply_markup=ReplyKeyboardRemove())
    owner = _is_owner(message.from_user.id)
    text = texts.ADMIN_MENU if owner else texts.ADMIN_MENU_BARBER
    await message.answer(text, reply_markup=keyboards.admin_menu_kb(owner))
