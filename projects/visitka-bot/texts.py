"""Все тексты и ссылки бота. Меняй здесь, код трогать не нужно.

Разметка: <b>жирный</b>, <i>курсив</i>, <a href="https://...">ссылка</a>.
"""

import html

# Контакт владельца. Замени на свой.
CONTACT = "@your_username"

# ---------- Главный экран ----------

START_TEXT = """Привет! Я <b>Даня</b>, разработчик. 👋
Делаю сайты, ботов и приложения.

Выбирай раздел 👇"""

HELP_TEXT = """Я простой бот-визитка. 🙂

Команды:
/start: главное меню
/help: эта подсказка

А ещё можно нажимать кнопки под сообщением."""

UNKNOWN_TEXT = """Пока я понимаю только кнопки и команды. 🙂
Нажми /start, покажу меню."""

# ---------- Меню ----------
# Первое значение: ключ раздела, второе: текст на кнопке.

MENU = [
    ("about", "👤 Обо мне"),
    ("experience", "📈 Опыт"),
    ("services", "🛠 Чем могу помочь"),
    ("portfolio", "💼 Портфолио"),
    ("reviews", "⭐ Отзывы"),
    ("contacts", "📬 Связаться"),
]

# ---------- Разделы ----------

SECTIONS = {
    "about": """<b>Обо мне</b>

Привет, я Даня, разработчик. Делаю сайты, ботов и приложения: от структуры и прототипа до запуска.

Люблю, когда интерфейс понятен с первого взгляда. Пишу на Python, Swift и JavaScript.""",

    "experience": """<b>Опыт</b>

Начинал с вёрстки: собирал страницы под запуски и личные проекты.

Потом перешёл к приложениям и ботам. Сделал трекер привычек, генератор палитр и погодный виджет. Сейчас развиваю iOS-приложение «Не курю» на SwiftUI и ботов на aiogram.

Умею работать по макету, но не теряюсь, если макета нет: предлагаю структуру и решение сам.""",

    "services": """<b>Чем могу помочь</b>

• Лендинги и сайты-визитки
• Многостраничные сайты и промо-страницы
• Веб-приложения и интерфейсы
• Мобильные приложения на iOS (SwiftUI)
• Вёрстка по макету: Figma → живой сайт
• Адаптив под телефон, планшет и десктоп
• Доработка и ускорение существующих проектов

Если твоей задачи нет в списке, всё равно напиши, разберёмся.""",

    "portfolio": """<b>Портфолио</b>

<b>«Не курю» / I Quit</b>. iOS-приложение для отказа от никотина: стрик, таймлайн восстановления, экономия, достижения и виджеты. SwiftUI, SwiftData, WidgetKit.

<b>Jelly Stack</b>. Браузерная аркада про башню из желе. JavaScript, Phaser 3.

<b>Бот записи</b>. Telegram-бот для барбершопа: услуги, слоты, напоминания и админка. Python, aiogram 3, SQLite.

<b>Сайт с проектами</b>. Страница со ссылками на исходники.

Каждый проект можно открыть и проверить.""",

    "contacts": """<b>Связаться</b>

Напиши в Telegram, отвечу в тот же день.

💬 Telegram: @your_username""",
}

# ---------- Кнопки-ссылки под разделами ----------
# Формат: ключ раздела -> список (текст на кнопке, ссылка).

SECTION_LINKS = {
    "portfolio": [
        ("🐙 «Не курю» на GitHub", "https://github.com/udum1337/i-quit"),
        ("🎮 Jelly Stack", "https://udum1337.github.io/projects/jelly-stack/"),
        ("🗂 Сайт с проектами", "https://udum1337.github.io/"),
    ],
    "contacts": [
        ("💬 Написать в Telegram", "https://t.me/your_username"),
    ],
}

# Кнопки, которые открывают форму или другие экраны.
SECTION_BUTTONS = {
    "services": [("✍️ Оставить заявку", "order")],
    "contacts": [("✍️ Оставить заявку", "order")],
}

# ---------- Форма заявки ----------

ORDER_BUTTON = "✍️ Оставить заявку"

ORDER_START = "Отлично! Давай коротко: как тебя зовут?"
ORDER_ASK_TASK = "Приятно познакомиться, {name}! Что нужно сделать? Опиши задачу в паре предложений."
ORDER_ASK_CONTACT = """Как удобнее связаться? Напиши @username, телефон или email.
Если не хочешь оставлять контакт, отправь «-»."""

ORDER_CANCELLED = "Ок, отменил. Если что, я тут. 🙂"
ORDER_BAD_NAME = "Напиши, пожалуйста, имя текстом (до 100 символов)."
ORDER_BAD_TASK = "Опиши задачу текстом, хотя бы пару слов (до 1000 символов)."
ORDER_BAD_CONTACT = "Слишком длинно. Напиши контакт короче (до 200 символов) или «-»."
ORDER_UNAVAILABLE = f"Заявки пока временно недоступны. Напиши напрямую: {CONTACT}"
ORDER_ERROR = f"Не получилось отправить заявку 😔 Напиши напрямую: {CONTACT}"
ORDER_COOLDOWN = "Заявку можно отправить раз в минуту 🙂"
ORDER_DONE = "Спасибо! Заявка улетела владельцу, отвечу в ближайшее время. 🚀"
MENU_AGAIN = "Что дальше? 👇"
CANCEL_BUTTON = "❌ Отмена"

# Сообщение, которое получает владелец бота.
ORDER_SUMMARY = """<b>🔔 Новая заявка с бота</b>

<b>Имя:</b> {name}
<b>Задача:</b> {task}
<b>Связь:</b> {contact}
<b>Telegram:</b> {username} (id <code>{user_id}</code>)"""

# ---------- Отзывы ----------

REVIEWS_HEADER = "<b>⭐ Отзывы</b>"
REVIEWS_EMPTY = "Отзывов пока нет. Стань первым, кто напишет 🙂"
REVIEWS_PER_PAGE = 5

REVIEWS_BUTTON = "✍️ Оставить отзыв"
REVIEWS_MORE = "Показать ещё"
REVIEWS_BACK = "⬅️ Назад"

REVIEWS_ASK_RATING = "Оцени работу от 1 до 5 ⭐"
REVIEWS_ASK_TEXT = """{stars}

Теперь пара слов: что делали, как прошло, что понравилось?
От 10 до 600 символов."""
REVIEWS_BAD_TEXT = "Нужно от 10 до 600 символов. Попробуй ещё раз."
REVIEWS_DONE = """Спасибо за отзыв! 🙌

Он появится после проверки, обычно это быстро."""
REVIEWS_COOLDOWN = "Отзыв можно оставить раз в 10 минут 🙂"
REVIEWS_UNAVAILABLE = f"Отзывы временно недоступны. Напиши напрямую: {CONTACT}"

REVIEWS_OWNER_ONLY = "Это команда владельца бота."
REVIEWS_PENDING_EMPTY = "Отзывов на проверке нет."
REVIEWS_APPROVED = "✅ <b>Опубликован</b>"
REVIEWS_REJECTED = "❌ <b>Отклонён</b>"
REVIEWS_ALREADY_DONE = "Этот отзыв уже обработан."
REVIEWS_NOT_FOUND = "Отзыв не найден."
REVIEWS_PUBLISHED_TO_USER = "Твой отзыв опубликован. Спасибо! 🙌"

REVIEWS_OWNER_NEW = """<b>⭐ Новый отзыв</b>

{block}

👤 {name} · {username} · id <code>{user_id}</code>"""


def stars(rating: int) -> str:
    rating = max(0, min(5, int(rating)))
    return "★" * rating + "☆" * (5 - rating)


def reviews_word(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "отзыв"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return "отзыва"
    return "отзывов"


def reviews_summary(count: int, average: float) -> str:
    return f"Средняя оценка: {average:.1f} ★ · {count} {reviews_word(count)}"


def review_block(review: dict) -> str:
    name = html.escape(review.get("name") or "Гость")
    text = html.escape(review.get("text") or "")
    return f"{stars(review.get('rating', 5))} <b>{name}</b>\n{text}"


def owner_review_text(review: dict) -> str:
    username = f"@{review['username']}" if review.get("username") else "без username"
    return REVIEWS_OWNER_NEW.format(
        block=review_block(review),
        name=html.escape(review.get("name") or "Гость"),
        username=html.escape(username),
        user_id=review.get("user_id", 0),
    )
