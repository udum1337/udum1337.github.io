"""Уведомления владельцу, ответственному барберу и клиенту."""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import config
import db
import texts


async def _recipients(booking, kind: str) -> list[int]:
    """Владельцы + барбер записи. Без барбера — те, кто делает услугу."""
    ids = list(config.ADMIN_IDS)
    if booking["barber_id"]:
        barber = await db.get_barber(booking["barber_id"])
        if barber and barber["user_id"]:
            ids.append(barber["user_id"])
    else:
        ids.extend(await db.barber_user_ids_for_service(booking["service_id"]))

    recipients: list[int] = []
    for user_id in dict.fromkeys(ids):
        if await db.notify_enabled(user_id, kind):
            recipients.append(user_id)
    return recipients


async def notify_new_booking(bot: Bot, booking) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отменить запись",
                    callback_data=f"admincancel:{booking['id']}",
                )
            ]
        ]
    )
    text = texts.admin_new_booking(booking)
    for user_id in await _recipients(booking, "new"):
        try:
            await bot.send_message(user_id, text, reply_markup=keyboard)
        except Exception:
            logging.exception("Не удалось уведомить %s о новой записи", user_id)


async def notify_cancelled_by_client(bot: Bot, booking) -> None:
    text = texts.admin_cancelled_by_client(booking)
    for user_id in await _recipients(booking, "cancel"):
        try:
            await bot.send_message(user_id, text)
        except Exception:
            logging.exception("Не удалось уведомить %s об отмене", user_id)


async def notify_client_cancelled_by_admin(bot: Bot, booking) -> None:
    text = texts.CANCELLED_BY_ADMIN.format(
        date=texts.format_date(booking["date"]),
        time=booking["time"],
    )
    try:
        await bot.send_message(booking["user_id"], text)
    except Exception:
        logging.exception("Не удалось уведомить клиента %s", booking["user_id"])
