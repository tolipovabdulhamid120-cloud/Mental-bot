import asyncio
import random
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# ================== SOZLAMALAR ==================
TOKEN = "8733167513:AAGrrlP_cpLODhyManCGBnegG5Yv8lMM4c0"
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================== BAZA ==================
def init_db():
    conn = sqlite3.connect("abakus.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            level INTEGER DEFAULT 1,
            score INTEGER DEFAULT 0,
            stars INTEGER DEFAULT 0,
            correct INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id, name):
    conn = sqlite3.connect("abakus.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cur.fetchone()
    if not user:
        cur.execute("INSERT INTO users (user_id, name) VALUES (?, ?)", (user_id, name))
        conn.commit()
        user = (user_id, name, 1, 0, 0, 0, 0)
    conn.close()
    return user

def update_user(user_id, **kwargs):
    conn = sqlite3.connect("abakus.db")
    cur = conn.cursor()
    for key, value in kwargs.items():
        cur.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()

def get_top_users(limit=10):
    conn = sqlite3.connect("abakus.db")
    cur = conn.cursor()
    cur.execute("SELECT name, score, stars FROM users ORDER BY score DESC LIMIT ?", (limit,))
    result = cur.fetchall()
    conn.close()
    return result

# ================== DARAJALAR ==================
LEVELS = {
    1: {"name": "1-daraja (Qo‘shish)", "ops": ["+"], "min": 1, "max": 10},
    2: {"name": "2-daraja (Qo‘shish + Ayirish)", "ops": ["+", "-"], "min": 1, "max": 20},
    3: {"name": "3-daraja (Ko‘paytirish 1)", "ops": ["*"], "min": 2, "max": 5},
    4: {"name": "4-daraja (Ko‘paytirish 2)", "ops": ["*"], "min": 2, "max": 9},
    5: {"name": "5-daraja (Aralash)", "ops": ["+", "-", "*"], "min": 2, "max": 12},
    6: {"name": "6-daraja (Tezkor)", "ops": ["+", "-", "*"], "min": 3, "max": 15},
}

# ================== HOLATLAR ==================
class Game(StatesGroup):
    waiting_answer = State()

# ================== YORDAMCHI FUNKSIYALAR ==================
def generate_example(level: int):
    conf = LEVELS[level]
    op = random.choice(conf["ops"])
    a = random.randint(conf["min"], conf["max"])
    b = random.randint(conf["min"], conf["max"])

    if op == "-":
        if a < b:
            a, b = b, a
        answer = a - b
        text = f"{a} − {b} = ?"
    elif op == "*":
        answer = a * b
        text = f"{a} × {b} = ?"
    else:
        answer = a + b
        text = f"{a} + {b} = ?"

    return text, answer

def main_keyboard():
    kb = [
        [KeyboardButton(text="▶️ Boshlash")],
        [KeyboardButton(text="📊 Mening natijam"), KeyboardButton(text="🏆 Reyting")],
        [KeyboardButton(text="📚 Darajani tanlash"), KeyboardButton(text="ℹ️ Yordam")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def level_keyboard():
    kb = []
    for i in range(1, 7):
        kb.append([KeyboardButton(text=f"{i}-daraja")])
    kb.append([KeyboardButton(text="🔙 Orqaga")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# ================== HANDLERLAR ==================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = get_user(message.from_user.id, message.from_user.first_name)
    text = (
        f"Salom, {message.from_user.first_name}! 👋\n\n"
        f"Men — <b>Sehrli Abakus</b> botiman!\n"
        f"Mental arifmetikani o‘ynab o‘rganamiz 🧮\n\n"
        f"Siz hozir <b>{LEVELS[user[2]]['name']}</b> dasiz.\n"
        f"Ballaringiz: <b>{user[3]}</b> | Yulduzchalar: <b>{user[4]}⭐</b>\n\n"
        f"Tayyormisiz?"
    )
    await message.answer(text, reply_markup=main_keyboard(), parse_mode="HTML")

@dp.message(F.text == "▶️ Boshlash")
async def start_game(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id, message.from_user.first_name)
    level = user[2]
    example, answer = generate_example(level)

    await state.set_state(Game.waiting_answer)
    await state.update_data(correct_answer=answer, level=level)

    await message.answer(
        f"🧮 <b>{LEVELS[level]['name']}</b>\n\n"
        f"<b>{example}</b>\n\n"
        f"Javobni yozing:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(Game.waiting_answer)
async def check_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    correct = data["correct_answer"]
    level = data["level"]

    try:
        user_answer = int(message.text.strip())
    except:
        await message.answer("Iltimos, faqat raqam yozing 🙂")
        return

    user = get_user(message.from_user.id, message.from_user.first_name)
    score = user[3]
    stars = user[4]
    correct_count = user[5]
    total = user[6] + 1

    if user_answer == correct:
        score += 10
        correct_count += 1
        stars += 1
        text = (
            f"✅ <b>To‘g‘ri!</b> Ajoyib! 🎉\n"
            f"+10 ball\n"
            f"Yulduzcha: ⭐\n\n"
            f"Jami ball: <b>{score}</b>"
        )
    else:
        text = (
            f"❌ Noto‘g‘ri.\n"
            f"To‘g‘ri javob: <b>{correct}</b>\n\n"
            f"Hechqisi yo‘q, yana urinib ko‘ring! 💪"
        )

    update_user(
        message.from_user.id,
        score=score,
        stars=stars,
        correct=correct_count,
        total=total
    )

    await state.clear()
    await message.answer(text, parse_mode="HTML", reply_markup=main_keyboard())

@dp.message(F.text == "📊 Mening natijam")
async def my_stats(message: types.Message):
    user = get_user(message.from_user.id, message.from_user.first_name)
    text = (
        f"📊 <b>Sizning natijangiz</b>\n\n"
        f"Ism: {user[1]}\n"
        f"Daraja: {LEVELS[user[2]]['name']}\n"
        f"Ball: <b>{user[3]}</b>\n"
        f"Yulduzchalar: <b>{user[4]}⭐</b>\n"
        f"To‘g‘ri javoblar: {user[5]} / {user[6]}"
    )
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "🏆 Reyting")
async def show_rating(message: types.Message):
    top = get_top_users()
    if not top:
        await message.answer("Hali hech kim o‘ynamagan.")
        return

    text = "🏆 <b>Eng yaxshi 10 talaba</b>\n\n"
    for i, (name, score, stars) in enumerate(top, 1):
        text += f"{i}. {name} — {score} ball | {stars}⭐\n"

    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "📚 Darajani tanlash")
async def choose_level(message: types.Message):
    await message.answer("Qaysi darajani tanlaysiz?", reply_markup=level_keyboard())

@dp.message(F.text.regexp(r"^[1-6]-daraja$"))
async def set_level(message: types.Message):
    level = int(message.text[0])
    update_user(message.from_user.id, level=level)
    await message.answer(
        f"✅ Siz {LEVELS[level]['name']} ga o‘tdingiz!",
        reply_markup=main_keyboard()
    )

@dp.message(F.text == "🔙 Orqaga")
async def back(message: types.Message):
    await message.answer("Asosiy menyu:", reply_markup=main_keyboard())

@dp.message(F.text == "ℹ️ Yordam")
async def help_cmd(message: types.Message):
    text = (
        "ℹ️ <b>Yordam</b>\n\n"
        "▶️ Boshlash — misol ishlash\n"
        "📊 Mening natijam — ballaringiz\n"
        "🏆 Reyting — eng yaxshilar\n"
        "📚 Darajani tanlash — qiyinlikni o‘zgartirish\n\n"
        "Har to‘g‘ri javob uchun +10 ball va 1 yulduzcha olasiz!"
    )
    await message.answer(text, parse_mode="HTML")

# ================== ISHGA TUSHIRISH ==================
async def main():
    init_db()
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
