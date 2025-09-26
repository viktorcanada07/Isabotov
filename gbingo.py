import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.exceptions import MessageNotModified, TelegramBadRequest

from config import BOT_TOKEN, ALLOWED_CHATS, SUPERUSER_ID

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

def check_chat(message: types.Message) -> bool:
    return message.chat.id in ALLOWED_CHATS

async def is_admin(message: types.Message) -> bool:
    if not check_chat(message):
        return False
    admins = await bot.get_chat_administrators(message.chat.id)
    return message.from_user.id in [admin.user.id for admin in admins]

@dp.message(Command("gstart"))
async def gstart_command(message: types.Message):
    if not await is_admin(message):
        return
    await message.answer(
        "👋 Привет! Я генератор случайных чисел (Gbingo).\n\n"
        "Команды:\n"
        "🎲 /gbingo N min max — задать параметры и сбросить историю\n"
        "🔢 /gnum X — сгенерировать X строк (от 1 до 5)\n"
        "🔎 /gsrch X — проверить, когда выпало число X\n"
        "Пример:\n"
        "/gbingo 5 1 100\n"
        "/gnum 3\n"
        "/gsrch 42"
    )

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
        if not (1 <= count <= 100):
            await message.answer("⚠️ Количество должно быть от 1 до 100")
            return
        if low < 1 or high > 1000 or low >= high:
            await message.answer("⚠️ Диапазон должен быть от 1 до 1000 и min < max")
            return

        game_state.update({"count": count, "low": low, "high": high,
                           "numbers": [], "history_msg_id": None, "chat_id": message.chat.id})

        await message.answer(
            f"✅ Настройки сохранены!\n"
            f"📌 Количество: {count}\n"
            f"📌 Диапазон: {low} — {high}\n"
            f"📜 История очищена."
        )
        msg = await message.answer("📜 Список выпавших чисел:")
        game_state["history_msg_id"] = msg.message_id
    except ValueError:
        await message.answer("⚠️ Нужно ввести числа!")

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

        # Генерация случайных чисел
        if total_needed > (high - low + 1):
            numbers = [random.randint(low, high) for _ in range(total_needed)]
        else:
            numbers = random.sample(range(low, high + 1), total_needed)

        game_state["numbers"].extend(numbers)

        # новые строки с разделителем
        new_lines = ["; ".join(map(str, numbers[i:i+game_state['count']])) 
                     for i in range(0, len(numbers), game_state["count"])]
        result_new = "\n--------\n".join(new_lines)

        # вся история с разделителем
        all_lines = ["; ".join(map(str, game_state["numbers"][i:i+game_state["count"]])) 
                     for i in range(0, len(game_state["numbers"]), game_state["count"])]
        result_all = "📜 Список выпавших чисел:\n" + "\n--------\n".join(all_lines)

        # обновляем историю
        try:
            await bot.edit_message_text(chat_id=game_state["chat_id"], message_id=game_state["history_msg_id"], text=result_all)
        except (MessageNotModified, TelegramBadRequest):
            msg = await message.answer(result_all)
            game_state["history_msg_id"] = msg.message_id

        await message.answer(f"Открыто {rows} строк:\n\n{result_new}")

    except ValueError:
        await message.answer("⚠️ Нужно ввести число, например: /gnum 3")

@dp.message(Command("gsrch"))
async def gsrch_command(message: types.Message):
    if not await is_admin(message):
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

@dp.message(Command("gstats"))
async def gstats_command(message: types.Message):
    if message.from_user.id != SUPERUSER_ID:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    if not game_state["numbers"]:
        await message.answer("⚠️ История пуста, чисел ещё не было.")
        return

    freq = {}
    for num in game_state["numbers"]:
        freq[num] = freq.get(num, 0) + 1

    sorted_freq = sorted(freq.items(), key=lambda x: int(x[0]))
    text = "📊 Частота выпадения чисел:\n" + "\n".join([f"{num}: {count}" for num, count in sorted_freq])
    await message.answer(text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот выключен.")
                       
