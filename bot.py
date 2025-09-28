import os
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_CHATS = [int(x) for x in os.getenv("ALLOWED_CHATS", "").split(",") if x]
SUPERUSER_ID = int(os.getenv("SUPERUSER_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# состояние игры
game_state = {
    "count": None,
    "low": None,
    "high": None,
    "numbers": [],
    "history_msg_id": None,
    "chat_id": None,
    "forced_numbers": [],   # список до 5 чисел
    "forbidden_numbers": set()  # числа, которые не должны выпадать
}

# проверка чата
async def check_allowed(message: types.Message) -> bool:
    if message.chat.id in ALLOWED_CHATS:
        return True
    else:
        await message.reply("Идите нахуй, вы не заплатили. Пишите моему создателю")
        return False

# проверка админа
async def is_admin(message: types.Message) -> bool:
    if not await check_allowed(message):
        return False
    admins = await bot.get_chat_administrators(message.chat.id)
    return message.from_user.id in [admin.user.id for admin in admins]

# --- инструкция
@dp.message(Command("bingo"))
async def bingo_command(message: types.Message):
    if not await is_admin(message):
        return
    await message.answer(
        "👋 Вас приветствует игровой бот IstockChat.

"
        "Команды:
"
        "🎲 /bset N min max — задать параметры и сбросить историю
"
        "🔢 /line X — сгенерировать X лайнов (от 1 до 5)
"
        "🔎 /num X — проверить, когда выпало число X (для всех)

"
        "Пример:
"
        "/bset 5 1 100
"
        "/line 3
"
        "/num 42"
    )

# --- /bset
@dp.message(Command("bset"))
async def bset_command(message: types.Message):
    if not await is_admin(message):
        return
    try:
        parts = message.text.split()
        if len(parts) != 4:
            await message.answer("⚠️ Формат: /bset N min max\nПример: /bset 5 1 100")
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
            "chat_id": message.chat.id,
            "forced_numbers": [],
            "forbidden_numbers": set()
        })
        await message.answer(
            f"✅ Настройки сохранены!\n📌 Количество: {count}\n📌 Диапазон: {low} — {high}\n📜 История очищена."
        )
        msg = await message.answer("📜 Список выпавших чисел:")
        game_state["history_msg_id"] = msg.message_id
        await bot.pin_chat_message(message.chat.id, msg.message_id, disable_notification=True)
    except ValueError:
        await message.answer("⚠️ Нужно ввести числа!")

# --- /line
@dp.message(Command("line"))
async def line_command(message: types.Message):
    if not await is_admin(message):
        return
    if game_state["count"] is None:
        await message.answer("⚠️ Сначала задай параметры: /bset N min max")
        return
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("⚠️ Формат: /line X (от 1 до 5)")
            return
        rows = int(parts[1])
        if not (1 <= rows <= 5):
            await message.answer("⚠️ X должно быть от 1 до 5")
            return

        total_needed = rows * game_state["count"]
        low, high = game_state["low"], game_state["high"]

        # базовые числа
        numbers = []
        while len(numbers) < total_needed:
            num = random.randint(low, high)
            if num not in game_state["forbidden_numbers"]:
                numbers.append(num)

        # вставляем до 5 форсированных чисел
        if game_state["forced_numbers"]:
            for num in game_state["forced_numbers"][:5]:
                pos = random.randint(0, len(numbers)-1)
                numbers[pos] = num
            game_state["forced_numbers"] = []

        game_state["numbers"].extend(numbers)

        # новые строки
        new_lines = [
            "; ".join(map(str, numbers[i:i+game_state['count']]))
            for i in range(0, len(numbers), game_state["count"])
        ]
        result_new = "\n--------\n".join(new_lines)

        # вся история
        all_lines = [
            "; ".join(map(str, game_state["numbers"][i:i+game_state["count"]]))
            for i in range(0, len(game_state["numbers"]), game_state["count"])
        ]
        result_all = "📜 Список выпавших чисел:\n" + "\n--------\n".join(all_lines)

        # обновляем историю
        try:
            await bot.edit_message_text(
                chat_id=game_state["chat_id"],
                message_id=game_state["history_msg_id"],
                text=result_all
            )
        except:
            msg = await message.answer(result_all)
            game_state["history_msg_id"] = msg.message_id

        await message.answer(f"Открыто лайнов {rows}:\n\n{result_new}")

    except ValueError:
        await message.answer("⚠️ Нужно ввести число, например: /line 3")

# --- /num
@dp.message(Command("num"))
async def num_command(message: types.Message):
    if not await check_allowed(message):
        return
    try:
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("⚠️ Формат: /num X\nПример: /num 42")
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

# --- скрытая /force (до 5 чисел)
@dp.message(Command("force"))
async def force_command(message: types.Message):
    if message.chat.type != "private":
        return
    if message.from_user.id != SUPERUSER_ID:
        return
    try:
        parts = message.text.split()[1:]
        nums = [int(x) for x in parts]
        if not (1 <= len(nums) <= 5):
            await message.answer("⚠️ Можно указать от 1 до 5 чисел")
            return
        game_state["forced_numbers"] = nums
        await message.answer(f"✅ Числа {', '.join(map(str, nums))} будут вставлены в следующую генерацию.")
    except ValueError:
        await message.answer("⚠️ Нужно ввести числа!")

# --- скрытая /forbid (блокировка чисел)
@dp.message(Command("forbid"))
async def forbid_command(message: types.Message):
    if message.chat.type != "private":
        return
    if message.from_user.id != SUPERUSER_ID:
        return
    try:
        parts = message.text.split()[1:]
        nums = [int(x) for x in parts]
        if not nums:
            await message.answer("⚠️ Формат: /forbid X Y Z")
            return
        game_state["forbidden_numbers"].update(nums)
        await message.answer(f"🚫 Числа {', '.join(map(str, nums))} не будут выпадать.")
    except ValueError:
        await message.answer("⚠️ Нужно ввести числа!")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Бот работает")
    await dp.start_polling(bot)

if __name__ == "__main__":
    keep_alive()
    asyncio.run(main())
