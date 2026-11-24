"""Клавиатуры. Тексты кнопок — здесь, чтобы не искать по коду."""

from __future__ import annotations

from datetime import date

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

import texts


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Записаться", callback_data="book")],
            [InlineKeyboardButton(text="💈 Барберы", callback_data="barbers")],
            [InlineKeyboardButton(text="🗓 Мои записи", callback_data="my")],
            [InlineKeyboardButton(text="✂️ Услуги и цены", callback_data="services")],
            [InlineKeyboardButton(text="📍 Контакты", callback_data="contacts")],
        ]
    )


def back_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")]]
    )


def services_kb(services, extra_fee: int = 0, back: str = "menu") -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=(
                    f"{service['title']} · "
                    f"{texts.format_price(service['price'] + extra_fee)}"
                ),
                callback_data=f"svc:{service['id']}",
            )
        ]
        for service in services
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ В меню" if back == "menu" else "⬅️ К барберам",
                callback_data=back,
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def barbers_kb(barbers) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{barber['name']} · ⭐ {texts.format_rating(barber['rating'])}",
                callback_data=f"barber:{barber['id']}",
            )
        ]
        for barber in barbers
    ]
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def barber_card_kb(barber) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"📅 Записаться к {barber['name'].split()[0]}",
                    callback_data=f"barberbook:{barber['id']}",
                )
            ],
            [InlineKeyboardButton(text="⬅️ К барберам", callback_data="barbers")],
        ]
    )


def dates_kb(days: list[date], back: str = "book") -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(days), 2):
        rows.append(
            [
                InlineKeyboardButton(
                    text=texts.format_date_short(day),
                    callback_data=f"date:{day.isoformat()}",
                )
                for day in days[i : i + 2]
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ К услугам" if back == "book" else "⬅️ К барберам",
                callback_data=back,
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def times_kb(times: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(times), 3):
        rows.append(
            [InlineKeyboardButton(text=t, callback_data=f"slot:{t}") for t in times[i : i + 3]]
        )
    rows.append([InlineKeyboardButton(text="⬅️ К датам", callback_data="backdates")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm:yes"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="confirm:no"),
            ]
        ]
    )


def after_booking_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗓 Мои записи", callback_data="my")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")],
        ]
    )


def my_bookings_kb(rows) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"❌ {texts.format_date_short(date.fromisoformat(row['date']))} "
                f"{row['time']} · {row['service_title']}",
                callback_data=f"mycancel:{row['id']}",
            )
        ]
        for row in rows
    ]
    keyboard.append([InlineKeyboardButton(text="📅 Записаться", callback_data="book")])
    keyboard.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер", request_contact=True)],
            [KeyboardButton(text=texts.MANUAL_PHONE)],
            [KeyboardButton(text=texts.CANCEL_BUTTON)],
        ],
        resize_keyboard=True,
    )


def name_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts.CANCEL_BUTTON)]],
        resize_keyboard=True,
    )


# ---------- Админ ----------

def admin_menu_kb(is_owner: bool = True) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="📋 Сегодня", callback_data="admin:today"),
            InlineKeyboardButton(text="📅 Завтра", callback_data="admin:tomorrow"),
        ],
        [InlineKeyboardButton(text="🗓 Ближайшая неделя", callback_data="admin:week")],
    ]
    if is_owner:
        rows += [
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
            [InlineKeyboardButton(text="💈 Барберы", callback_data="admin:barbers")],
        ]
    rows.append(
        [InlineKeyboardButton(text="🔔 Уведомления", callback_data="admin:notify")]
    )
    if is_owner:
        rows += [
            [
                InlineKeyboardButton(text="✂️ Услуги", callback_data="admin:services"),
                InlineKeyboardButton(text="➕ Добавить", callback_data="admin:addservice"),
            ],
            [
                InlineKeyboardButton(text="🚫 Закрыть день", callback_data="admin:dayoff"),
                InlineKeyboardButton(text="📆 Выходные", callback_data="admin:days"),
            ],
        ]
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_services_kb(services) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"✏️ {service['title']}" + ("" if service["active"] else " · скрыта"),
                callback_data=f"adminsvc:{service['id']}",
            )
        ]
        for service in services
    ]
    rows.append(
        [
            InlineKeyboardButton(text="➕ Добавить услугу", callback_data="admin:addservice"),
        ]
    )
    rows.append([InlineKeyboardButton(text="⬅️ В админку", callback_data="admin:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_service_card_kb(service) -> InlineKeyboardMarkup:
    service_id = service["id"]
    toggle_text = "🙈 Скрыть от клиентов" if service["active"] else "👁 Показать клиентам"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Название", callback_data=f"svcedit:{service_id}:title"
                ),
                InlineKeyboardButton(
                    text="⏱ Длительность", callback_data=f"svcedit:{service_id}:duration"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💰 Цена", callback_data=f"svcedit:{service_id}:price"
                )
            ],
            [
                InlineKeyboardButton(
                    text=toggle_text, callback_data=f"svctoggle:{service_id}"
                )
            ],
            [InlineKeyboardButton(text="⬅️ К услугам", callback_data="admin:services")],
        ]
    )


def admin_form_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts.CANCEL_BUTTON)]],
        resize_keyboard=True,
    )


def admin_barbers_kb(barbers) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{barber['name']}" + ("" if barber["active"] else " · скрыт"),
                callback_data=f"adminbarber:{barber['id']}",
            )
        ]
        for barber in barbers
    ]
    rows.append(
        [InlineKeyboardButton(text="➕ Добавить барбера", callback_data="admin:barberadd")]
    )
    rows.append([InlineKeyboardButton(text="⬅️ В админку", callback_data="admin:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_barber_card_kb(barber) -> InlineKeyboardMarkup:
    barber_id = barber["id"]
    toggle = "🙈 Скрыть от клиентов" if barber["active"] else "👁 Показать клиентам"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Имя", callback_data=f"barberedit:{barber_id}:name"),
                InlineKeyboardButton(text="🎓 Опыт", callback_data=f"barberedit:{barber_id}:experience"),
            ],
            [
                InlineKeyboardButton(text="⭐ Рейтинг", callback_data=f"barberedit:{barber_id}:rating"),
                InlineKeyboardButton(text="💰 Доплата", callback_data=f"barberedit:{barber_id}:extra_fee"),
            ],
            [
                InlineKeyboardButton(
                    text="👤 Telegram ID", callback_data=f"barberedit:{barber_id}:user_id"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛠 Услуги", callback_data=f"barberservices:{barber_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=toggle, callback_data=f"barbertoggle:{barber_id}"
                )
            ],
            [InlineKeyboardButton(text="⬅️ К барберам", callback_data="admin:barbers")],
        ]
    )


def admin_barber_services_kb(barber_id: int, services, selected: set[int]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=("✅ " if service["id"] in selected else "⬜ ") + service["title"],
                callback_data=f"bsvc:{barber_id}:{service['id']}",
            )
        ]
        for service in services
    ]
    rows.append(
        [InlineKeyboardButton(text="⬅️ К барберу", callback_data=f"adminbarber:{barber_id}")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def notify_people_kb(people) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"notif:{user_id}")]
        for user_id, label in people
    ]
    rows.append([InlineKeyboardButton(text="⬅️ В админку", callback_data="admin:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def notify_person_kb(user_id: int, new_on: bool, cancel_on: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=("✅ " if new_on else "❌ ") + "Новые записи",
                    callback_data=f"notiftoggle:{user_id}:new",
                )
            ],
            [
                InlineKeyboardButton(
                    text=("✅ " if cancel_on else "❌ ") + "Отмены",
                    callback_data=f"notiftoggle:{user_id}:cancel",
                )
            ],
            [InlineKeyboardButton(text="⬅️ К уведомлениям", callback_data="admin:notify")],
        ]
    )


def back_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ В админку", callback_data="admin:back")]]
    )


def admin_bookings_kb(rows) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"❌ {row['time']} · {row['client_name'][:14]}",
                callback_data=f"admincancel:{row['id']}",
            )
        ]
        for row in rows
    ]
    keyboard.append([InlineKeyboardButton(text="⬅️ В админку", callback_data="admin:back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def days_off_kb(rows) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"📆 {row['date']}",
                callback_data=f"undoday:{row['date']}",
            )
        ]
        for row in rows
    ]
    keyboard.append([InlineKeyboardButton(text="⬅️ В админку", callback_data="admin:back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
