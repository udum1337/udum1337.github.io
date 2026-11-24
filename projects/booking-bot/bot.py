"""Точка входа: запуск бота записи с автопоиском прокси."""

from __future__ import annotations

import asyncio
import logging
import os
import socket
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramConflictError, TelegramUnauthorizedError
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

import config
import db
import reminders
from admin import router as admin_router
from barbers import router as barbers_router
from client import router as client_router

load_dotenv()

# Порты популярных VPN-клиентов. Бот берёт первый, который реально отвечает.
COMMON_PROXIES = [
    "http://127.0.0.1:10809",   # v2rayN, HTTP
    "http://127.0.0.1:10801",   # v2rayTun, HTTP
    "http://127.0.0.1:7890",    # Clash, HTTP
    "socks5://127.0.0.1:10808", # v2rayN, SOCKS
    "socks5://127.0.0.1:7891",  # Clash, SOCKS
    "http://127.0.0.1:1080",    # общий HTTP
]

TIMEOUT = 8.0


class NoConnection(Exception):
    """Не удалось достучаться до Telegram ни через один прокси."""


def _port_open(proxy: str) -> bool:
    parsed = urlparse(proxy)
    if not parsed.hostname or not parsed.port:
        return False
    try:
        with socket.create_connection((parsed.hostname, parsed.port), timeout=0.4):
            return True
    except OSError:
        return False


def _new_bot(token: str, proxy: str | None) -> Bot:
    session = AiohttpSession(proxy=proxy, timeout=TIMEOUT)
    return Bot(
        token=token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


async def _try(token: str, proxy: str | None):
    """Пробует подключиться через прокси. Возвращает (bot, me) или None."""
    bot = _new_bot(token, proxy)
    try:
        me = await bot.get_me()
        return bot, me
    except TelegramUnauthorizedError:
        await bot.session.close()
        raise
    except Exception:
        await bot.session.close()
        return None


async def build_bot(token: str) -> tuple[Bot, str | None, object]:
    """Возвращает бота, рабочий прокси и данные бота."""
    preferred = os.getenv("PROXY_URL", "").strip()
    candidates: list[str] = []
    for proxy in [preferred, *COMMON_PROXIES]:
        if proxy and proxy not in candidates:
            candidates.append(proxy)

    for proxy in candidates:
        if not _port_open(proxy):
            continue
        result = await _try(token, proxy)
        if result:
            bot, me = result
            return bot, proxy, me

    # Последняя попытка — напрямую (если VPN не нужен или уже системный).
    result = await _try(token, None)
    if result:
        bot, me = result
        return bot, None, me

    raise NoConnection


async def _watchdog(holder: dict, dp: Dispatcher, interval: float = 20.0) -> None:
    """Следит за связью. Если VPN сменил порт — перезапускает поллинг."""
    fails = 0
    while True:
        await asyncio.sleep(interval)
        try:
            await holder["bot"].get_me()
            fails = 0
        except Exception:
            fails += 1
            if fails >= 2:
                print("\nСвязь с Telegram потеряна — ищу рабочий прокси…")
                await dp.stop_polling()
                return


async def main() -> None:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token or ":" not in token:
        print("\n[ОШИБКА] В файле .env нет токена.")
        print("Открой .env и вставь токен после BOT_TOKEN=.\n")
        return

    try:
        bot, proxy, me = await build_bot(token)
    except TelegramUnauthorizedError:
        print("\n[ОШИБКА] Telegram не принял токен. Проверь .env или получи новый у @BotFather.\n")
        return
    except NoConnection:
        print("\n[ОШИБКА] Нет связи с Telegram ни напрямую, ни через прокси.")
        print("Включи VPN и проверь, что он запущен (иконка в трее).")
        print("Бот сам найдёт порт: 10809, 10801, 7890, 10808, 7891, 1080.\n")
        return

    await db.init_db()

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_routers(admin_router, barbers_router, client_router)

    await bot.delete_webhook(drop_pending_updates=True)

    where = proxy or "напрямую, без прокси"
    print(f"\nБот @{me.username} запущен — {config.BUSINESS_NAME}.")
    print(f"Подключение: {where}")
    if proxy and proxy != os.getenv("PROXY_URL", "").strip():
        print(f"(порт определён автоматически, .env менять не нужно)")
    if config.ADMIN_IDS:
        print(f"Админка: /admin. Уведомления придут в чат(ы) {config.ADMIN_IDS}.")
    else:
        print("[ВНИМАНИЕ] ADMIN_IDS не задан: админка и уведомления выключены.")
        print("Впиши свой ID в .env: ADMIN_IDS=123456789")
    print("Остановить: Ctrl+C в этом окне.\n")

    holder = {"bot": bot}
    reminder_task = asyncio.create_task(reminders.reminder_loop(lambda: holder["bot"]))

    try:
        while True:
            watchdog = asyncio.create_task(_watchdog(holder, dp))
            try:
                await dp.start_polling(holder["bot"])
            except TelegramConflictError:
                print("\n[ОШИБКА] Этот бот уже запущен в другом окне. Закрой лишний процесс.\n")
                break
            except TelegramUnauthorizedError:
                print("\n[ОШИБКА] Telegram не принял токен. Проверь .env.\n")
                break
            except Exception:
                logging.exception("Поллинг остановился")
            finally:
                watchdog.cancel()

            print("Переподключаюсь…")
            await holder["bot"].session.close()
            try:
                new_bot, proxy, me = await build_bot(token)
            except TelegramUnauthorizedError:
                print("[ОШИБКА] Telegram не принял токен. Проверь .env.\n")
                break
            except NoConnection:
                print("[ОШИБКА] Связи нет. Включи VPN и запусти бота снова.\n")
                break

            holder["bot"] = new_bot
            print(f"Снова на связи: {proxy or 'напрямую'} (@{me.username})\n")
            await new_bot.delete_webhook(drop_pending_updates=True)
    finally:
        reminder_task.cancel()
        await holder["bot"].session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен. До встречи!")
