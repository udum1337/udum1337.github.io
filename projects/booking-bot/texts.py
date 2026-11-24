"""Все тексты бота. Меняешь здесь — логику трогать не нужно."""

from __future__ import annotations

import html
from datetime import date

import config

WEEKDAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
MONTHS = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]

CANCEL_BUTTON = "❌ Отмена"
MANUAL_PHONE = "⌨️ Ввести вручную"


def esc(value) -> str:
    return html.escape(str(value or ""))


def format_price(value: int) -> str:
    return f"{value:,}".replace(",", " ") + " ₽"


def format_rating(value: float) -> str:
    return f"{float(value):.1f}"


def format_date(iso: str) -> str:
    day = date.fromisoformat(iso)
    return f"{WEEKDAYS[day.weekday()]}, {day.day} {MONTHS[day.month - 1]}"


def format_date_short(day: date) -> str:
    return f"{WEEKDAYS[day.weekday()]} {day.strftime('%d.%m')}"


# ---------- Клиент ----------

START_TEXT = f"""<b>{config.BUSINESS_NAME}</b>
{config.BUSINESS_TAGLINE}

Записаться можно за минуту: выбираешь услугу, день и время — всё. Или сначала смотришь барберов и записываешься к конкретному.

🕙 Ежедневно с {config.WORK_START} до {config.WORK_END}
📍 {config.ADDRESS}

Что делаем? 👇"""

HELP_TEXT = """Я бот записи. 🙂

/start — главное меню
/admin — панель мастера (только для сотрудников)

Выбирай услугу и время кнопками — я всё оформлю."""

CONTACTS_TEXT = f"""<b>Контакты</b>

📍 {config.ADDRESS}
📞 {config.PHONE}
🕙 Ежедневно с {config.WORK_START} до {config.WORK_END}

<a href="{config.MAP_URL}">Открыть на карте</a>"""

SERVICES_HEADER = "<b>Услуги и цены</b>\n\n"

BARBERS_HEADER = """<b>Наши барберы</b>

Рейтинг, опыт и доплата за выбор мастера. Нажми на имя 👇"""

BARBERS_EMPTY = "Пока не добавили барберов. Записаться можно без выбора мастера."

BARBER_CARD = """<b>{name}</b>
⭐ {rating} · опыт {experience}
💰 Доплата за мастера: {fee}
🛠 {services}"""

BARBER_NO_SERVICES = "Этот мастер пока не принимает записи. Выбери другого или запишись без выбора."

BARBER_GONE = "Этот мастер больше не принимает эту услугу. Выбери другого или запишись без выбора."

BARBER_SERVICES_HEADER = """<b>{name}</b>
⭐ {rating} · опыт {experience}
💰 Доплата за мастера: {fee}

Какую услугу делаем?"""

CHOOSE_DATE = """<b>{service}</b>
{price} · {duration} мин{barber_line}

На какой день записываемся? 👇"""

NO_SLOTS = """На {date} свободного времени нет 😔
Выбери другой день — я покажу."""

CHOOSE_TIME = """<b>{service}</b>
📅 {date}{barber_line}

Свободное время 👇"""

ASK_NAME = "Как тебя зовут? Напиши имя — так мастер будет знать, кого ждать."

ASK_PHONE = """Оставь номер телефона, чтобы мы могли связаться, если что-то изменится.

Можно нажать кнопку ниже или ввести вручную."""

PHONE_MANUAL = "Напиши номер в формате +7 999 123-45-67."

CONFIRM_TITLE = "Проверь запись 👇"
CONFIRM_TEXT = """<b>{service}</b>
📅 {date} в {time}
⏱ {duration} мин
💈 {barber}
💰 {total}{fee_note}

👤 {name}
📞 {phone}

Всё верно?"""

BOOKED_TEXT = """✅ <b>Готово, ты записан!</b>

<b>{service}</b>
📅 {date} в {time}
💈 {barber}
💰 {total}
📍 {address}

Напомним за сутки и за 2 часа. Если планы изменятся — запись можно отменить в «Мои записи»."""

MY_EMPTY = "У тебя пока нет активных записей. Самое время записаться 👇"
MY_HEADER = "<b>Твои записи</b>\n\n"

CANCELLED = "Запись отменена. Будем рады видеть тебя в другой раз."
CANCELLED_BY_ADMIN = "К сожалению, запись на {date} в {time} отменил мастер. Выбери другое время — будем ждать."

SLOT_TAKEN = "Это время только что заняли 😔 Выбери другое."
ERROR_NAME = "Напиши имя текстом, от 2 до 60 символов."
ERROR_PHONE = "Похоже, это не номер. Напиши в формате +7 999 123-45-67 или отправь контакт кнопкой."
FORM_CANCELLED = "Ок, отменил. Возвращайся, когда будет удобно 🙂"

REMINDER_24H = """🔔 Напоминаем: завтра ты записан в {time}.

<b>{service}</b>
📍 {address}

Если не получится прийти — отмени запись в «Мои записи»."""
REMINDER_2H = """⏰ Через 2 часа ждём тебя в {time}.

<b>{service}</b>
📍 {address}

До встречи!"""

UNKNOWN = "Я понимаю кнопки и команды. Нажми /start — покажу меню."


def services_text(services, extra_fee: int = 0) -> str:
    lines = [SERVICES_HEADER.rstrip()]
    for service in services:
        lines.append(
            f"• <b>{esc(service['title'])}</b> — "
            f"{service['duration']} мин · {format_price(service['price'] + extra_fee)}"
        )
    return "\n".join(lines)


def barber_services_text(services, barber) -> str:
    header = BARBER_SERVICES_HEADER.format(
        name=esc(barber["name"]),
        rating=format_rating(barber["rating"]),
        experience=esc(barber["experience"] or "не указан"),
        fee=format_price(barber["extra_fee"]),
    )
    lines = [header, ""]
    for service in services:
        lines.append(
            f"• <b>{esc(service['title'])}</b> — "
            f"{service['duration']} мин · "
            f"{format_price(service['price'] + barber['extra_fee'])}"
        )
    return "\n".join(lines)


def barber_card(barber, services: list[str]) -> str:
    return BARBER_CARD.format(
        name=esc(barber["name"]),
        rating=format_rating(barber["rating"]),
        experience=esc(barber["experience"] or "не указан"),
        fee=format_price(barber["extra_fee"]),
        services=esc(", ".join(services) if services else "все услуги"),
    )


def booking_short(row) -> str:
    barber = f"\n💈 {esc(row['barber_name'])}" if row["barber_name"] else ""
    return (
        f"📅 <b>{format_date(row['date'])}</b> в {row['time']}\n"
        f"✂️ {esc(row['service_title'])}{barber}"
    )


# ---------- Админ ----------

ADMIN_MENU = """<b>Панель владельца</b>

Записи, барберы, услуги и уведомления."""

ADMIN_MENU_BARBER = """<b>Панель барбера</b>

Здесь только твои записи и настройка уведомлений."""

ADMIN_NO_ACCESS = """Это панель сотрудников. Доступ есть у владельца и барберов.

Твой Telegram ID: <code>{user_id}</code>

Отправь этот номер владельцу бота — он добавит тебя барбером."""

ADMIN_NO_BOOKINGS = "На период «{period}» записей нет."

ADMIN_ADD_TITLE = "Название новой услуги? Например: «Детская стрижка»."
ADMIN_ADD_DURATION = "Сколько длится услуга в минутах? Например: 30 или 60."
ADMIN_ADD_PRICE = "Сколько стоит услуга в рублях? Например: 2000."
ADMIN_ADD_DONE = "Услуга «{title}» добавлена."

ADMIN_SERVICES_HEADER = "<b>Услуги</b>\n\nНажми на услугу, чтобы изменить название, длительность или цену."

ADMIN_SERVICE_CARD = """<b>{title}</b>
{duration} мин · {price}
{status}

Что меняем?"""
ADMIN_SERVICE_ACTIVE = "👁 Показывается клиентам"
ADMIN_SERVICE_HIDDEN = "🙈 Скрыта от клиентов"

ADMIN_EDIT_TITLE = "Новое название услуги. Сейчас: «{old}»."
ADMIN_EDIT_DURATION = "Новая длительность в минутах. Сейчас: {old}."
ADMIN_EDIT_PRICE = "Новая цена в рублях. Сейчас: {old}."
ADMIN_EDIT_DONE = "Сохранил: <b>{title}</b> — {duration} мин · {price}."
ADMIN_SERVICE_HIDDEN_DONE = "Услуга «{title}» скрыта — клиенты её больше не увидят. Старые записи остались."
ADMIN_SERVICE_SHOWN_DONE = "Услуга «{title}» снова показывается клиентам."

ADMIN_ERR_TITLE = "Название — от 2 до 60 символов. Попробуй ещё раз."
ADMIN_ERR_DURATION = "Нужно число от 15 до 240 минут. Например: 60."
ADMIN_ERR_PRICE = "Нужна цена числом от 0 до 100 000. Например: 2500."

ADMIN_BARBERS_HEADER = """<b>Барберы</b>

Нажми на барбера, чтобы изменить имя, опыт, рейтинг, доплату или услуги. Telegram ID открывает доступ к панели и уведомлениям."""

ADMIN_BARBERS_EMPTY = "Барберов пока нет. Добавь первого — и клиенты смогут выбирать мастера."

ADMIN_BARBER_CARD = """<b>{name}</b>
⭐ {rating} · опыт {experience}
💰 Доплата за мастера: {fee}
🛠 Услуги: {services}
👤 Telegram: {user}
{status}"""

ADMIN_BARBER_ACTIVE = "👁 Принимает записи"
ADMIN_BARBER_HIDDEN = "🙈 Скрыт от клиентов"

ADMIN_BARBER_ADD_NAME = "Как зовут барбера? Напиши имя и фамилию."
ADMIN_BARBER_ADD_ID = """Пришли Telegram ID барбера.

Он узнает его в боте командой /myid. Если барбер пока не в Telegram, отправь «-» — привяжешь позже."""
ADMIN_BARBER_ID_BAD = "Нужен числовой ID, например 123456789. Или отправь «-», чтобы пропустить."
ADMIN_BARBER_ID_TAKEN = "Этот ID уже привязан к другому барберу."
ADMIN_BARBER_ADDED = "Барбер добавлен: <b>{name}</b>. Настрой услуги и доплату."
ADMIN_BARBER_ADDED_NO_START = """Барбер добавлен: <b>{name}</b>.

Написать ему не удалось — похоже, он ещё не открывал бота. Попроси нажать /start и отправить /admin."""
ADMIN_BARBER_WELCOME = """Вас добавили барбером в бот записи.

Отправьте /admin — там ваши записи. Новые записи будут приходить сюда же."""

ADMIN_BARBER_EDIT_NAME = "Новое имя. Сейчас: «{old}»."
ADMIN_BARBER_EDIT_EXPERIENCE = "Новый опыт. Сейчас: «{old}». Например: «6 лет»."
ADMIN_BARBER_EDIT_RATING = "Новый рейтинг от 0 до 5. Сейчас: {old}. Например: 4.9."
ADMIN_BARBER_EDIT_FEE = "Доплата за выбор мастера в рублях. Сейчас: {old}. Например: 300."
ADMIN_BARBER_EDIT_ID = """Новый Telegram ID. Сейчас: {old}.

Отправь «-», чтобы отвязать аккаунт и закрыть доступ."""

ADMIN_BARBER_ERR_NAME = "Имя — от 2 до 40 символов."
ADMIN_BARBER_ERR_EXPERIENCE = "Опыт — от 2 до 40 символов. Например: «6 лет»."
ADMIN_BARBER_ERR_RATING = "Нужно число от 0 до 5. Например: 4.9."
ADMIN_BARBER_ERR_FEE = "Нужна сумма от 0 до 50 000 рублей. Например: 300."
ADMIN_BARBER_ERR_ID = "Нужен числовой ID или «-», чтобы отвязать аккаунт."

ADMIN_BARBER_SERVICES_HEADER = """<b>Услуги: {name}</b>

Отметь, что делает барбер. Если не выбрано ничего — он делает все услуги."""
ADMIN_BARBER_SERVICES_SAVED = "Сохранил."

ADMIN_BARBER_HIDDEN_DONE = "Барбер «{name}» скрыт. Новые записи к нему не принимаются."
ADMIN_BARBER_SHOWN_DONE = "Барбер «{name}» снова принимает записи."

ADMIN_NOTIFY_HEADER = """<b>Уведомления</b>

Новая запись приходит владельцу и барберу, который её ведёт. Остальные барберы не получают ничего.

Нажми на человека, чтобы включить или выключить уведомления."""

ADMIN_NOTIFY_EMPTY = "Пока некого настраивать: добавь барберов с Telegram ID."

ADMIN_NOTIFY_CARD = """<b>Уведомления: {name}</b>

Новые записи: {new}
Отмены: {cancel}"""

ADMIN_NOTIFY_ON = "включены"
ADMIN_NOTIFY_OFF = "выключены"

ADMIN_DAYOFF_ASK = "Какой день закрываем? Пришли дату в формате 2026-11-25."
ADMIN_DAYOFF_DONE = "День {date} закрыт для записи."
ADMIN_DAYOFF_BAD = "Не понял дату. Нужен формат 2026-11-25, и день не должен быть в прошлом."
ADMIN_DAYS_EMPTY = "Закрытых дней нет."
ADMIN_DAYS_HEADER = "<b>Закрытые дни</b>\n\nНажми на день, чтобы снова открыть его."

ADMIN_STATS = """<b>Статистика</b>

Сегодня: {today_count} записей · {today_sum}
Ближайшие 7 дней: {week_count} записей · {week_sum}"""

ADMIN_NEW_BOOKING = """🆕 <b>Новая запись</b>

<b>{service}</b>
📅 {date} в {time} ({duration} мин)
💈 {barber}
💰 {total}{fee_note}

👤 {name}
📞 {phone}
🔗 {username}"""

ADMIN_CANCELLED_BY_CLIENT = """❌ <b>Клиент отменил запись</b>

<b>{service}</b>
📅 {date} в {time}
💈 {barber}

👤 {name}
📞 {phone}"""


def admin_booking_line(row) -> str:
    barber = f"\n💈 {esc(row['barber_name'])}" if row["barber_name"] else ""
    return (
        f"<b>{row['time']}</b> — {esc(row['service_title'])}{barber}\n"
        f"{esc(row['client_name'])}, {esc(row['phone'])}"
    )


def admin_new_booking(row) -> str:
    username = f"@{esc(row['username'])}" if row["username"] else "—"
    total = row["price"] + row["barber_fee"]
    fee_note = ""
    if row["barber_fee"]:
        fee_note = (
            f" (услуга {format_price(row['price'])} + "
            f"доплата {format_price(row['barber_fee'])})"
        )
    return ADMIN_NEW_BOOKING.format(
        service=esc(row["service_title"]),
        date=format_date(row["date"]),
        time=row["time"],
        duration=row["duration"],
        barber=esc(row["barber_name"]) if row["barber_name"] else "любой",
        total=format_price(total),
        fee_note=fee_note,
        name=esc(row["client_name"]),
        phone=esc(row["phone"]),
        username=username,
    )


def admin_cancelled_by_client(row) -> str:
    return ADMIN_CANCELLED_BY_CLIENT.format(
        service=esc(row["service_title"]),
        date=format_date(row["date"]),
        time=row["time"],
        barber=esc(row["barber_name"]) if row["barber_name"] else "любой",
        name=esc(row["client_name"]),
        phone=esc(row["phone"]),
    )
