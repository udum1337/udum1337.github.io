"""Фоновые напоминания клиентам за 24 часа и за 2 часа."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time, timedelta

from aiogram import Bot

import config
import db
import texts


async def _send(bot: Bot, booking, template: str, fields: tuple[str, ...]) -> None:
    message = template.format(
        service=texts.esc(booking["service_title"]),
        time=booking["time"],
        address=config.ADDRESS,
    )
    try:
        await bot.send_message(booking["user_id"], message)
    except Exception:
        logging.warning("Не смог отправить напоминание клиенту %s", booking["user_id"])

    for field in fields:
        await db.mark_reminded(booking["id"], field)


async def tick(bot: Bot) -> None:
    now = datetime.now(config.TZ)
    bookings = await db.get_reminder_candidates(now.date().isoformat())

    for booking in bookings:
        appointment = datetime.combine(
            date.fromisoformat(booking["date"]),
            time.fromisoformat(booking["time"]),
            tzinfo=config.TZ,
        )
        delta = appointment - now
        if delta.total_seconds() <= 0:
            continue

        if not booking["reminded_2h"] and delta <= timedelta(hours=2):
            # За 2 часа: 24-часовое напоминание уже не нужно.
            await _send(bot, booking, texts.REMINDER_2H, ("reminded_2h", "reminded_24h"))
        elif not booking["reminded_24h"] and delta <= timedelta(hours=24):
            await _send(bot, booking, texts.REMINDER_24H, ("reminded_24h",))


async def reminder_loop(bot_provider) -> None:
    """bot_provider — бот или функция, возвращающая актуального бота."""
    while True:
        bot = bot_provider() if callable(bot_provider) else bot_provider
        try:
            await tick(bot)
        except asyncio.CancelledError:
            raise
        except Exception:
            logging.exception("Ошибка в цикле напоминаний")
        await asyncio.sleep(60)
