"""Слой данных: SQLite + aiosqlite. Все запросы к базе — здесь."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

import config

DB_PATH = Path(__file__).with_name("booking.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    duration INTEGER NOT NULL,
    price INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS barbers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    experience TEXT NOT NULL DEFAULT '',
    rating REAL NOT NULL DEFAULT 5.0,
    extra_fee INTEGER NOT NULL DEFAULT 0,
    user_id INTEGER,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Один Telegram-аккаунт не может быть двумя барберами.
CREATE UNIQUE INDEX IF NOT EXISTS idx_barber_user
    ON barbers(user_id) WHERE user_id IS NOT NULL;

-- Пустой список услуг означает «делает все услуги».
CREATE TABLE IF NOT EXISTS barber_services (
    barber_id INTEGER NOT NULL REFERENCES barbers(id) ON DELETE CASCADE,
    service_id INTEGER NOT NULL REFERENCES services(id),
    PRIMARY KEY (barber_id, service_id)
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    client_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    username TEXT NOT NULL DEFAULT '',
    service_id INTEGER NOT NULL REFERENCES services(id),
    barber_id INTEGER NOT NULL DEFAULT 0,
    barber_fee INTEGER NOT NULL DEFAULT 0,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    reminded_24h INTEGER NOT NULL DEFAULT 0,
    reminded_2h INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(date);
CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id);

CREATE TABLE IF NOT EXISTS days_off (
    date TEXT PRIMARY KEY,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS notify_settings (
    user_id INTEGER PRIMARY KEY,
    new_booking INTEGER NOT NULL DEFAULT 1,
    cancelled INTEGER NOT NULL DEFAULT 1
);
"""


@asynccontextmanager
async def connect():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
    finally:
        await db.close()


async def _columns(db, table: str) -> set[str]:
    cur = await db.execute(f"PRAGMA table_info({table})")
    return {row["name"] for row in await cur.fetchall()}


async def _migrate(db) -> None:
    columns = await _columns(db, "bookings")
    if "barber_id" not in columns:
        await db.execute("ALTER TABLE bookings ADD COLUMN barber_id INTEGER NOT NULL DEFAULT 0")
    if "barber_fee" not in columns:
        await db.execute("ALTER TABLE bookings ADD COLUMN barber_fee INTEGER NOT NULL DEFAULT 0")

    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_bookings_barber ON bookings(barber_id)"
    )

    # Слот занимает конкретный барбер, а не весь салон.
    await db.execute("DROP INDEX IF EXISTS idx_active_slot")
    await db.execute(
        """CREATE UNIQUE INDEX idx_active_slot
           ON bookings(date, time, barber_id) WHERE status = 'active'"""
    )


async def _migrate_staff(db) -> None:
    """Старые сотрудники из admins становятся барберами, доступ не теряется."""
    cur = await db.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'admins'"
    )
    if not await cur.fetchone():
        return
    await db.execute(
        """INSERT OR IGNORE INTO barbers (name, user_id)
           SELECT 'Барбер ' || user_id, user_id FROM admins"""
    )


async def init_db() -> None:
    async with connect() as db:
        await db.executescript(SCHEMA)
        await _migrate(db)
        await _migrate_staff(db)

        cur = await db.execute("SELECT COUNT(*) AS n FROM services")
        row = await cur.fetchone()
        if row["n"] == 0:
            await db.executemany(
                "INSERT INTO services (title, duration, price) VALUES (?, ?, ?)",
                config.DEMO_SERVICES,
            )

        cur = await db.execute("SELECT COUNT(*) AS n FROM barbers")
        row = await cur.fetchone()
        if row["n"] == 0:
            await db.executemany(
                """INSERT INTO barbers (name, experience, rating, extra_fee)
                   VALUES (?, ?, ?, ?)""",
                config.DEMO_BARBERS,
            )
        await db.commit()


# ---------- Услуги ----------

async def get_services(active_only: bool = True) -> list[aiosqlite.Row]:
    query = "SELECT * FROM services"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY id"
    async with connect() as db:
        cur = await db.execute(query)
        return list(await cur.fetchall())


async def get_service(service_id: int):
    async with connect() as db:
        cur = await db.execute("SELECT * FROM services WHERE id = ?", (service_id,))
        return await cur.fetchone()


async def update_service(service_id: int, title: str, duration: int, price: int) -> bool:
    async with connect() as db:
        cur = await db.execute(
            """UPDATE services SET title = ?, duration = ?, price = ?
               WHERE id = ?""",
            (title, duration, price, service_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def set_service_active(service_id: int, active: bool) -> bool:
    async with connect() as db:
        cur = await db.execute(
            "UPDATE services SET active = ? WHERE id = ?",
            (1 if active else 0, service_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def add_service(title: str, duration: int, price: int) -> int:
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO services (title, duration, price) VALUES (?, ?, ?)",
            (title, duration, price),
        )
        await db.commit()
        return cur.lastrowid


# ---------- Барберы ----------

async def list_barbers(active_only: bool = True) -> list[aiosqlite.Row]:
    query = "SELECT * FROM barbers"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY id"
    async with connect() as db:
        cur = await db.execute(query)
        return list(await cur.fetchall())


async def get_barber(barber_id: int):
    async with connect() as db:
        cur = await db.execute("SELECT * FROM barbers WHERE id = ?", (barber_id,))
        return await cur.fetchone()


async def get_barber_by_user(user_id: int):
    async with connect() as db:
        cur = await db.execute("SELECT * FROM barbers WHERE user_id = ?", (user_id,))
        return await cur.fetchone()


async def add_barber(name: str, user_id: int | None = None) -> int:
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO barbers (name, user_id) VALUES (?, ?)",
            (name, user_id),
        )
        await db.commit()
        return cur.lastrowid


BARBER_FIELDS = {"name", "experience", "rating", "extra_fee", "user_id"}


async def update_barber(barber_id: int, field: str, value) -> bool:
    if field not in BARBER_FIELDS:
        raise ValueError(f"Неизвестное поле: {field}")
    async with connect() as db:
        cur = await db.execute(
            f"UPDATE barbers SET {field} = ? WHERE id = ?", (value, barber_id)
        )
        await db.commit()
        return cur.rowcount > 0


async def set_barber_active(barber_id: int, active: bool) -> bool:
    async with connect() as db:
        cur = await db.execute(
            "UPDATE barbers SET active = ? WHERE id = ?",
            (1 if active else 0, barber_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def list_barber_service_ids(barber_id: int) -> set[int]:
    async with connect() as db:
        cur = await db.execute(
            "SELECT service_id FROM barber_services WHERE barber_id = ?", (barber_id,)
        )
        return {row["service_id"] for row in await cur.fetchall()}


async def get_barber_service_titles(barber_id: int) -> list[str]:
    async with connect() as db:
        cur = await db.execute(
            """SELECT s.title FROM barber_services bs
               JOIN services s ON s.id = bs.service_id
               WHERE bs.barber_id = ? ORDER BY s.id""",
            (barber_id,),
        )
        return [row["title"] for row in await cur.fetchall()]


async def toggle_barber_service(barber_id: int, service_id: int) -> bool:
    """Возвращает True, если услуга теперь привязана к барберу."""
    async with connect() as db:
        cur = await db.execute(
            "DELETE FROM barber_services WHERE barber_id = ? AND service_id = ?",
            (barber_id, service_id),
        )
        if cur.rowcount:
            await db.commit()
            return False
        await db.execute(
            "INSERT INTO barber_services (barber_id, service_id) VALUES (?, ?)",
            (barber_id, service_id),
        )
        await db.commit()
        return True


async def barbers_for_service(service_id: int, free_only: bool = False) -> list[aiosqlite.Row]:
    """Активные барберы, которые делают услугу. Пустая привязка = все услуги."""
    query = """SELECT b.* FROM barbers b
               WHERE b.active = 1
                 AND (
                   NOT EXISTS (SELECT 1 FROM barber_services x WHERE x.barber_id = b.id)
                   OR EXISTS (
                     SELECT 1 FROM barber_services x
                     WHERE x.barber_id = b.id AND x.service_id = ?
                   )
                 )"""
    if free_only:
        query += " AND b.extra_fee = 0"
    query += " ORDER BY b.id"
    async with connect() as db:
        cur = await db.execute(query, (service_id,))
        return list(await cur.fetchall())


async def barber_offers_service(barber_id: int, service_id: int) -> bool:
    barbers = await barbers_for_service(service_id)
    return any(row["id"] == barber_id for row in barbers)


def _hhmm_to_minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


async def pick_barber(
    service_id: int,
    date: str,
    time: str,
    duration: int,
    free_only: bool = True,
):
    """Свободный барбер на это время или None."""
    candidates = await barbers_for_service(service_id, free_only=free_only)
    if not candidates:
        return None

    start = _hhmm_to_minutes(time)
    end = start + duration
    busy: set[int] = set()
    for booking in await get_active_bookings_on(date):
        other_start = _hhmm_to_minutes(booking["time"])
        other_end = other_start + booking["duration"]
        if start < other_end and other_start < end:
            busy.add(booking["barber_id"])

    for barber in candidates:
        if barber["id"] not in busy:
            return barber
    return None


# ---------- Записи ----------

_BOOKING_FIELDS = """b.*, s.title AS service_title, s.duration AS duration,
                     s.price AS price, COALESCE(br.name, '') AS barber_name"""
_BOOKING_FROM = """FROM bookings b
                   JOIN services s ON s.id = b.service_id
                   LEFT JOIN barbers br ON br.id = b.barber_id"""


async def create_booking(
    user_id: int,
    client_name: str,
    phone: str,
    username: str,
    service_id: int,
    date: str,
    time: str,
    barber_id: int = 0,
    barber_fee: int = 0,
) -> int:
    async with connect() as db:
        cur = await db.execute(
            """INSERT INTO bookings
               (user_id, client_name, phone, username, service_id, date, time,
                barber_id, barber_fee)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id, client_name, phone, username, service_id, date, time,
                barber_id, barber_fee,
            ),
        )
        await db.commit()
        return cur.lastrowid


async def get_booking(booking_id: int):
    async with connect() as db:
        cur = await db.execute(
            f"SELECT {_BOOKING_FIELDS} {_BOOKING_FROM} WHERE b.id = ?",
            (booking_id,),
        )
        return await cur.fetchone()


async def get_active_bookings_on(date: str) -> list[aiosqlite.Row]:
    async with connect() as db:
        cur = await db.execute(
            f"""SELECT {_BOOKING_FIELDS} {_BOOKING_FROM}
                WHERE b.date = ? AND b.status = 'active'
                ORDER BY b.time""",
            (date,),
        )
        return list(await cur.fetchall())


async def get_user_bookings(user_id: int, today: str) -> list[aiosqlite.Row]:
    async with connect() as db:
        cur = await db.execute(
            f"""SELECT {_BOOKING_FIELDS} {_BOOKING_FROM}
                WHERE b.user_id = ? AND b.status = 'active' AND b.date >= ?
                ORDER BY b.date, b.time""",
            (user_id, today),
        )
        return list(await cur.fetchall())


async def get_bookings_range(
    start: str, end: str, barber_id: int | None = None
) -> list[aiosqlite.Row]:
    query = f"""SELECT {_BOOKING_FIELDS} {_BOOKING_FROM}
                WHERE b.status = 'active' AND b.date BETWEEN ? AND ?"""
    params: list = [start, end]
    if barber_id:
        query += " AND b.barber_id = ?"
        params.append(barber_id)
    query += " ORDER BY b.date, b.time"
    async with connect() as db:
        cur = await db.execute(query, params)
        return list(await cur.fetchall())


async def cancel_booking(booking_id: int) -> bool:
    async with connect() as db:
        cur = await db.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE id = ? AND status = 'active'",
            (booking_id,),
        )
        await db.commit()
        return cur.rowcount > 0


# ---------- Выходные ----------

async def is_day_off(date: str) -> bool:
    async with connect() as db:
        cur = await db.execute("SELECT 1 FROM days_off WHERE date = ?", (date,))
        return await cur.fetchone() is not None


async def add_day_off(date: str, reason: str = "") -> None:
    async with connect() as db:
        await db.execute(
            "INSERT OR REPLACE INTO days_off (date, reason) VALUES (?, ?)",
            (date, reason),
        )
        await db.commit()


async def remove_day_off(date: str) -> None:
    async with connect() as db:
        await db.execute("DELETE FROM days_off WHERE date = ?", (date,))
        await db.commit()


async def list_days_off(today: str) -> list[aiosqlite.Row]:
    async with connect() as db:
        cur = await db.execute(
            "SELECT * FROM days_off WHERE date >= ? ORDER BY date",
            (today,),
        )
        return list(await cur.fetchall())


# ---------- Напоминания и статистика ----------

async def get_reminder_candidates(today: str) -> list[aiosqlite.Row]:
    async with connect() as db:
        cur = await db.execute(
            f"""SELECT {_BOOKING_FIELDS} {_BOOKING_FROM}
                WHERE b.status = 'active' AND b.date >= ?
                  AND (b.reminded_24h = 0 OR b.reminded_2h = 0)
                ORDER BY b.date, b.time""",
            (today,),
        )
        return list(await cur.fetchall())


async def mark_reminded(booking_id: int, field: str) -> None:
    if field not in {"reminded_24h", "reminded_2h"}:
        raise ValueError(f"Неизвестное поле: {field}")
    async with connect() as db:
        await db.execute(f"UPDATE bookings SET {field} = 1 WHERE id = ?", (booking_id,))
        await db.commit()


async def stats_for_range(start: str, end: str) -> tuple[int, int]:
    async with connect() as db:
        cur = await db.execute(
            """SELECT COUNT(*) AS n,
                      COALESCE(SUM(s.price + b.barber_fee), 0) AS total
               FROM bookings b JOIN services s ON s.id = b.service_id
               WHERE b.status = 'active' AND b.date BETWEEN ? AND ?""",
            (start, end),
        )
        row = await cur.fetchone()
        return row["n"], row["total"]


# ---------- Уведомления ----------

async def get_notify_settings(user_id: int) -> tuple[bool, bool]:
    async with connect() as db:
        cur = await db.execute(
            "SELECT new_booking, cancelled FROM notify_settings WHERE user_id = ?",
            (user_id,),
        )
        row = await cur.fetchone()
    if not row:
        return True, True
    return bool(row["new_booking"]), bool(row["cancelled"])


async def set_notify_setting(user_id: int, kind: str, enabled: bool) -> None:
    field = {"new": "new_booking", "cancel": "cancelled"}.get(kind)
    if not field:
        raise ValueError(f"Неизвестный тип уведомлений: {kind}")
    async with connect() as db:
        await db.execute(
            "INSERT OR IGNORE INTO notify_settings (user_id) VALUES (?)", (user_id,)
        )
        await db.execute(
            f"UPDATE notify_settings SET {field} = ? WHERE user_id = ?",
            (1 if enabled else 0, user_id),
        )
        await db.commit()


async def notify_enabled(user_id: int, kind: str) -> bool:
    new_booking, cancelled = await get_notify_settings(user_id)
    return new_booking if kind == "new" else cancelled


async def barber_user_ids_for_service(service_id: int) -> list[int]:
    rows = await barbers_for_service(service_id)
    return [row["user_id"] for row in rows if row["user_id"]]
