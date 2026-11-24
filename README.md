# Сайт с проектами

Статический сайт: https://udum1337.github.io/

Здесь четыре проекта: iOS-приложение «Не курю», бот записи для барбершопа, бот-визитка и браузерная игра Jelly Stack. Сайт собран на HTML и CSS, без сборщика и внешних библиотек.

## Что внутри

- `index.html`: главная страница.
- `style.css`: стили.
- `assets/`: иконки и скриншоты.
- `projects/booking-bot/`: исходники бота записи.
- `projects/visitka-bot/`: исходники бота-визитки.
- `projects/jelly-stack/`: игра.

Исходники «Не курю» лежат отдельно: https://github.com/udum1337/i-quit

## Открыть локально

```
python -m http.server 8000
```

Дальше открыть `http://localhost:8000`.

Можно открыть и просто `index.html`, но тогда ссылки на папки проектов будут работать не так, как на GitHub.

## Проекты

### «Не курю» / I Quit

iOS-приложение для отказа от никотина. SwiftUI, SwiftData, WidgetKit. Есть PWA-версия для браузера.

- Демо: https://udum1337.github.io/i-quit/prototype/
- Код: https://github.com/udum1337/i-quit

### Бот записи для барбершопа

Telegram-бот на Python и aiogram 3. Клиент выбирает услугу и время, мастер получает уведомление, клиенту уходят напоминания.

- Код: `projects/booking-bot/`
- Инструкция: `projects/booking-bot/README.md`

### Бот-визитка

Шаблон Telegram-бота с меню, заявками и отзывами. Python и aiogram 3.

- Код: `projects/visitka-bot/`
- Инструкция: `projects/visitka-bot/README.md`

### Jelly Stack

Браузерная аркада про башню из желе. JavaScript и Phaser 3.

- Играть: https://udum1337.github.io/projects/jelly-stack/
- Код: `projects/jelly-stack/`

## Публикация

GitHub Pages отдаёт сайт из ветки `main`, корень репозитория. После коммита страница обновляется сама.

## Секреты

В репозитории нет токенов, баз и логов. У ботов есть только `.env.example`. Настоящие токены и ID хранятся локально.
