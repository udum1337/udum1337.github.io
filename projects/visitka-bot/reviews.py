"""Отзывы: хранение в JSON рядом с ботом. Без внешних зависимостей."""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

DATA_PATH = Path(__file__).with_name("reviews.json")
_lock = asyncio.Lock()


def _load() -> dict:
    if not DATA_PATH.exists():
        return {"next_id": 1, "items": []}
    try:
        with DATA_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {"next_id": 1, "items": []}
    data.setdefault("next_id", 1)
    data.setdefault("items", [])
    return data


def _save(data: dict) -> None:
    tmp = DATA_PATH.with_name("reviews.tmp")
    with tmp.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_PATH)


async def add(
    user_id: int,
    name: str,
    username: str,
    rating: int,
    text: str,
) -> dict:
    async with _lock:
        data = _load()
        review = {
            "id": data["next_id"],
            "user_id": user_id,
            "name": name,
            "username": username,
            "rating": max(1, min(5, int(rating))),
            "text": text,
            "status": "pending",
            "created_at": int(time.time()),
        }
        data["next_id"] += 1
        data["items"].append(review)
        _save(data)
        return dict(review)


async def get(review_id: int) -> dict | None:
    async with _lock:
        for review in _load()["items"]:
            if review["id"] == review_id:
                return dict(review)
    return None


async def set_status(review_id: int, status: str) -> bool:
    if status not in {"approved", "rejected"}:
        raise ValueError(f"Неизвестный статус: {status}")
    async with _lock:
        data = _load()
        for review in data["items"]:
            if review["id"] == review_id:
                review["status"] = status
                _save(data)
                return True
    return False


async def approved() -> list[dict]:
    """Опубликованные отзывы, новые сверху."""
    async with _lock:
        items = [r for r in _load()["items"] if r["status"] == "approved"]
    items.sort(key=lambda r: r["created_at"], reverse=True)
    return [dict(r) for r in items]


async def pending() -> list[dict]:
    """Отзывы на проверке, старые сверху."""
    async with _lock:
        items = [r for r in _load()["items"] if r["status"] == "pending"]
    items.sort(key=lambda r: r["created_at"])
    return [dict(r) for r in items]
