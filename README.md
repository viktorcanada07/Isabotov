# 🎲 Istock Bingo Bot

Игровой бот для Telegram на базе **aiogram**.

## 🚀 Запуск на Railway

1. Форкни этот репозиторий.
2. Подключи его в [Railway.app](https://railway.app).
3. В настройках переменных окружения (`Variables`) добавь:
   - `BOT_TOKEN` — токен твоего бота
   - `SUPERUSER_ID` — твой Telegram ID
   - `ALLOWED_CHATS` — список разрешённых чатов (через запятую)
4. Railway сам подтянет зависимости и запустит:
   ```bash
   python bot.py
   ```
5. Готово 🎉 Бот работает 24/7.
