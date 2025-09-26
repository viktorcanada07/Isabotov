import os
import random
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_CHATS = [int(x) for x in os.getenv("ALLOWED_CHATS", "").split(",") if x]
SUPERUSER_ID = int(os.getenv("SUPERUSER_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Состояние игры
game_state = {
    "count": None,
    "low": None,
    "high": None,
    "numbers": [],
    "history_msg_id": None,
    "chat_id": None
}

# Проверка разрешённого чата и отправка "жёсткого" сообщения
async def check_allowed(message: types.Message) -> bool:
    if message.chat.id in ALLOWED_CHATS:
        return True
    else:
        await message.reply("Идите нахуй, вы не заплатили. Пишите моему создателю")
        return False

# Проверка, админ ли пользователь
async def is_admin(message: types.Message) -> bool:
    if not await check_allowed(message):
        return False
    admins = await bot.get_chat_administrators(message.chat.id)
    return message.from_user.id in [admin.user.id for admin in admins]

# Команда /gstart
@dp.message(Command("gstart"))
async def gstart_command(message: types.Message):
    if not await is_admin(message):
        return
    await message.answer(
        "👋 Привет! Я генератор случайных чисел (Gbingo).\n\n"
        "Команды:\n"
        "🎲 /gbingo N min max — задать параметры и сбросить историю\n"
        "🔢 /gnum X — сгенерировать X строк (от 1 до 5)\n"
        "🔎 /gsrch X — проверить, когда выпало число X (для всех)\n\n"
        "Пример:\n"
        "/gbingo 5 1 100\n"
        "/gnum 3\n"
        "/gsrch 42"
    )

# Команда /gbingo
@dp.message(Command("gbingo"))
async def gbingo_command(message: types.Message):
    if not await is_admin(message):
        return
    try:
        parts = message.text.split()
        if len(parts) != 4:
            await message.answer("⚠️ Формат: /gbingo N min max\nПример: /gbingo 5 1 100")
            return
        count, low, high = map(int, parts[1:])
        if not (1 <= count <= 100) or low < 1 or high > 1000 or low >= high:
            await message.answer("⚠️ Некорректные параметры")
            return
        game_state.update({
            "count": count,
            "low": low,
            "high": high,
            "numbers": [],
            "history_msg_id": None,
            "chat_id": message.chat.id
        })
        await message.answer(
            f"✅ Настройки сохранены!\n📌 Количество: {count}\n📌 Диапазон: {low} — {high}\n📜 История очищена."
        )
        msg = await message.answer("📜 Список выпавших чисел:")
        game_state["history_msg_id"] = msg.message_id
    except ValueError:
        await message.answer("⚠️ Нужно ввести числа!")

# Команда /gnum
@dp.message(Command("gnum"))
async def gnum_command(message: types.Message):
    if not await is_admin(message):
        return
    if game_state["count"] is None:
        await message.answer("⚠️ Сначала задай параметры: /gbingo N min max")
        return
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("⚠️ Формат: /gnum X (от 1 до 5)")
            return
        rows = int(parts[1])
        if not (1 <= rows <= 5):
            await message.answer("⚠️ X должно быть от 1 до 5")
            return
        total_needed = rows * game_state["count"]
        low, high = game_state["low"], game_state["high"]
        if total_needed > (high - low + 1):
            numbers = [random.randint(low, high) for _ in range(total_needed)]
        else:
            numbers = random.sample(range(low, high + 1), total_needed)
        game_state["numbers"].extend(numbers)
        new_lines = ["; ".join(map(str, numbers[i:i+game_state['count']])) 
                     for i in range(0, len(numbers), game_state["count"])]
        result_new = "\n--------\n".join(new_lines)
        all_lines = ["; ".join(map(str, game_state["numbers"][i:i+game_state["count"]])) 
                     for i in range(0, len(game_state["numbers"]), game_state["count"])]
        result_all = "📜 Список выпавших чисел:\n" + "\n--------\n".join(all_lines)
        try:
            await bot.edit_message_text(
                chat_id=game_state["chat_id"], 
                message_id=game_state["history_msg_id"], 
                text=result_all
            )
        except TelegramBadRequest:
            msg = await message.answer(result_all)
            game_state["history_msg_id"] = msg.message_id
        await message.answer(f"Открыто {rows} строк:\n\n{result_new}")
    except ValueError:
        await message.answer("⚠️ Нужно ввести число, например: /gnum 3")

# Команда /gsrch — доступна всем
@dp.message(Command("gsrch"))
async def gsrch_command(message: types.Message):
    if not await check_allowed(message):
        return
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("⚠️ Формат: /gsrch X\nПример: /gsrch 42")
            return
        target = int(parts[1])
        positions = []
        for idx, num in enumerate(game_state["numbers"]):
            if num == target:
                line = idx // game_state["count"] + 1
                pos = idx % game_state["count"] + 1
                positions.append((line, pos))
        if positions:
            text = "\n".join([f"Строка {line}, позиция {pos}" for line, pos in positions])
            await message.answer(f"🔎 Число {target} выпало:\n{text}")
        else:
            await message.answer(f"❌ Число {target} ещё не выпадало.")
    except ValueError:
        await message.answer("⚠️ Нужно ввести число!")

# Команда /gstats — только суперпользователь, в ЛС
@dp.message(Command("gstats"))
async def gstats_command(message: types.Message):
    if message.from_user.id != SUPERUSER_ID:
        return
    try:
        await message.delete()
    except:
        pass
    if not game_state["numbers"]:
        await bot.send_message(SUPERUSER_ID, "⚠️ История пуста")
        return
    freq = {}
    for num in game_state["numbers"]:
        freq[num] = freq.get(num, 0) + 1
    sorted_freq = sorted(freq.items(), key=lambda x: int(x[0]))
    text = "📊 Частота выпадения чисел:\n" + "\n".join([f"{num}: {count}" for num, count in sorted_freq])
    await bot.send_message(SUPERUSER_ID, text)

# Обработка webhook
async def handle(request):
    if request.match_info.get('token') == BOT_TOKEN:
        data = await request.json()
        update = types.Update(**data)
        await dp.process_update(update)
        return web.Response()
    return web.Response(status=403)

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL + WEBHOOK_PATH)

async def on_cleanup(app):
    await bot.delete_webhook()

app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle)
app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
