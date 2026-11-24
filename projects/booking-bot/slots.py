"""Расчёт свободных слотов на день."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import config


def hhmm_to_minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def minutes_to_hhmm(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def available_slots(
    day: date,
    duration: int,
    bookings: list,
    now: datetime,
    capacity: int = 1,
) -> list[str]:
    """Свободные старты. capacity — сколько барберов могут работать одновременно."""
    work_start = hhmm_to_minutes(config.WORK_START)
    work_end = hhmm_to_minutes(config.WORK_END)
    step = config.SLOT_STEP

    earliest = 0
    if day == now.date():
        earliest = now.hour * 60 + now.minute + config.MIN_LEAD_MINUTES

    result: list[str] = []
    start = work_start
    while start + duration <= work_end:
        if start < earliest:
            start += step
            continue

        overlapping = 0
        for booking in bookings:
            other_start = hhmm_to_minutes(booking["time"])
            other_end = other_start + booking["duration"]
            if start < other_end and other_start < start + duration:
                overlapping += 1

        if overlapping < max(0, capacity):
            result.append(minutes_to_hhmm(start))
        start += step

    return result


def next_dates(now: datetime, days_off: set[str]) -> list[date]:
    """Ближайшие даты для записи, без выходных."""
    dates: list[date] = []
    for offset in range(config.DAYS_AHEAD):
        day = now.date() + timedelta(days=offset)
        if day.isoformat() in days_off:
            continue
        dates.append(day)
    return dates
