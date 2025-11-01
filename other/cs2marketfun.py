# /modules/skins_market.py

from aiogram import Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from assets.antispam import antispam, antispam_earning, new_earning
from user import BFGuser
import sqlite3
from decimal import Decimal
import random

router = Router()
DB_PATH = "users.db"

# ---------- Настройка кейсов ----------
CASES = [
    {
        "name": "Кейс Победы",
        "cost_balance": 100_000_000,
        "cost_ecoins": 1000,
        "skins": [
            {"name": "AK-47 | Redline", "rarity": "Epic", "price": 300_000_000, "chance": 0.4},
            {"name": "M4A1-S | Hyper Beast", "rarity": "Rare", "price": 200_000_000, "chance": 0.3},
            {"name": "AWP | Dragon Lore", "rarity": "Legendary", "price": 1_000_000_000, "chance": 0.1},
            {"name": "Desert Eagle | Blaze", "rarity": "Common", "price": 50_000_000, "chance": 0.2},
        ]
    },
    {
        "name": "Кейс Легенд",
        "cost_balance": 500_000_000,
        "cost_ecoins": 5000,
        "skins": [
            {"name": "Knife | Fade", "rarity": "Legendary", "price": 1_500_000_000, "chance": 0.05},
            {"name": "AK-47 | Vulcan", "rarity": "Epic", "price": 600_000_000, "chance": 0.3},
            {"name": "M4A4 | Howl", "rarity": "Rare", "price": 350_000_000, "chance": 0.3},
            {"name": "P90 | Death by Kitty", "rarity": "Common", "price": 80_000_000, "chance": 0.35},
        ]
    }
]

# ---------- Создание таблиц, если их нет ----------
def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skins_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            skin_name TEXT,
            rarity TEXT,
            price REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skins_market (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            skin_id INTEGER,
            skin_name TEXT,
            price REAL,
            currency TEXT
        )
    """)
    conn.commit()
    conn.close()

create_tables()

# ---------- Магазин кейсов ----------
@router.message(F.text == "Магазин кейсов")
@antispam
async def show_cases(message: Message, user: BFGuser):
    text = "🎁 Доступные кейсы:\n"
    keyboard = InlineKeyboardMarkup()
    for i, case in enumerate(CASES):
        text += f"{case['name']} - {case['cost_balance']}💰 или {case['cost_ecoins']}🤑\n"
        keyboard.add(
            InlineKeyboardButton(f"Открыть {case['name']}", callback_data=f"open_case|{i}|{user.user_id}")
        )
    msg = await message.answer(text, reply_markup=keyboard)
    await new_earning(msg)

# ---------- Открытие кейса ----------
@router.callback_query(F.data.startswith("open_case"))
@antispam_earning
async def open_case(call: CallbackQuery, user: BFGuser):
    _, case_index, user_id = call.data.split("|")
    case_index = int(case_index)
    case = CASES[case_index]

    # Проверка средств
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, ecoins FROM users WHERE user_id = ?", (user.user_id,))
    balance, ecoins = map(Decimal, cursor.fetchone())

    if balance >= case['cost_balance']:
        new_balance = balance - case['cost_balance']
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (f"{new_balance:.0f}", user.user_id))
    elif ecoins >= case['cost_ecoins']:
        new_ecoins = ecoins - case['cost_ecoins']
        cursor.execute("UPDATE users SET ecoins = ? WHERE user_id = ?", (new_ecoins, user.user_id))
    else:
        await call.message.answer("Недостаточно средств для открытия кейса!")
        conn.close()
        return

    # Рандомное выпадение скина
    skin = random.choices(
        population=[s for s in case['skins']],
        weights=[s['chance'] for s in case['skins']],
        k=1
    )[0]

    cursor.execute(
        "INSERT INTO skins_inventory (user_id, skin_name, rarity, price) VALUES (?, ?, ?, ?)",
        (user.user_id, skin['name'], skin['rarity'], skin['price'])
    )
    conn.commit()
    conn.close()

    await call.message.answer(f"🎉 Вы открыли {case['name']} и получили скин: {skin['name']} ({skin['rarity']}) стоимостью {skin['price']}💰!")

# ---------- Инвентарь ----------
@router.message(F.text == "Мой инвентарь")
@antispam
async def show_inventory(message: Message, user: BFGuser):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, skin_name, rarity, price FROM skins_inventory WHERE user_id = ?", (user.user_id,))
    skins = cursor.fetchall()
    conn.close()

    if not skins:
        await message.answer("Ваш инвентарь пуст 😢")
        return

    text = "Ваш инвентарь:\n"
    keyboard = InlineKeyboardMarkup()
    for skin in skins:
        skin_id, name, rarity, price = skin
        text += f"{name} ({rarity}) - {price}💰\n"
        keyboard.add(
            InlineKeyboardButton(f"Продать {name}", callback_data=f"sell_skin|{skin_id}|{user.user_id}")
        )
    msg = await message.answer(text, reply_markup=keyboard)
    await new_earning(msg)

# ---------- Продажа скина на маркет ----------
@router.callback_query(F.data.startswith("sell_skin"))
@antispam_earning
async def sell_skin(call: CallbackQuery, user: BFGuser):
    _, skin_id, user_id = call.data.split("|")
    skin_id = int(skin_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT skin_name, price FROM skins_inventory WHERE id = ? AND user_id = ?", (skin_id, user.user_id))
    skin = cursor.fetchone()
    if not skin:
        await call.message.answer("Ошибка! Скин не найден.")
        conn.close()
        return

    skin_name, price = skin
    cursor.execute(
        "INSERT INTO skins_market (seller_id, skin_id, skin_name, price, currency) VALUES (?, ?, ?, ?, ?)",
        (user.user_id, skin_id, skin_name, price, "balance")
    )
    cursor.execute("DELETE FROM skins_inventory WHERE id = ?", (skin_id,))
    conn.commit()
    conn.close()
    await call.message.answer(f"Вы выставили {skin_name} на маркет за {price}💰!")

# ---------- Просмотр маркета ----------
@router.message(F.text == "Маркет")
@antispam
async def show_market(message: Message, user: BFGuser):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, seller_id, skin_name, price FROM skins_market WHERE seller_id != ?", (user.user_id,))
    skins = cursor.fetchall()
    conn.close()

    if not skins:
        await message.answer("Маркет пуст 😢")
        return

    text = "Скины на продаже:\n"
    keyboard = InlineKeyboardMarkup()
    for s in skins:
        market_id, seller_id, name, price = s
        text += f"{name} - {price}💰\n"
        keyboard.add(
            InlineKeyboardButton(f"Купить {name}", callback_data=f"buy_skin|{market_id}|{user.user_id}")
        )
    msg = await message.answer(text, reply_markup=keyboard)
    await new_earning(msg)

# ---------- Покупка скина ----------
@router.callback_query(F.data.startswith("buy_skin"))
@antispam_earning
async def buy_skin(call: CallbackQuery, user: BFGuser):
    _, market_id, buyer_id = call.data.split("|")
    market_id = int(market_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT seller_id, skin_id, skin_name, price FROM skins_market WHERE id = ?", (market_id,))
    data = cursor.fetchone()
    if not data:
        await call.message.answer("Ошибка! Скин уже куплен.")
        conn.close()
        return

    seller_id, skin_id, skin_name, price = data
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user.user_id,))
    balance = Decimal(str(cursor.fetchone()[0]))
    if balance < price:
        await call.message.answer("Недостаточно денег для покупки!")
        conn.close()
        return

    # Списание с покупателя и зачисление продавцу
    new_balance = balance - price
    cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (f"{new_balance:.0f}", user.user_id))
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (seller_id,))
    seller_balance = Decimal(str(cursor.fetchone()[0]))
    cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (f"{seller_balance + price:.0f}", seller_id))

    # Передача скина покупателю
    cursor.execute(
        "INSERT INTO skins_inventory (user_id, skin_name, rarity, price) VALUES (?, ?, ?, ?)",
        (user.user_id, skin_name, "unknown", price)
    )
    cursor.execute("DELETE FROM skins_market WHERE id = ?", (market_id,))
    conn.commit()
    conn.close()

    await call.message.answer(f"Вы купили {skin_name} за {price}💰!")

# ---------- Регистрация роутера ----------
def register_handlers(dp):
    dp.include_router(router)

MODULE_DESCRIPTION = {
    'name': '🎮 Расширенные кейсы и маркет скинов',
    'description': 'Кейсы с редкостью, инвентарь и маркет для продажи/покупки скинов между игроками'
}
