
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from assets.transform import transform_int as tr
from decimal import Decimal
from assets.antispam import antispam, antispam_earning, new_earning
from bot import bot
import time
import sqlite3
import random
import os

from commands.db import conn as conngdb, cursor as cursorgdb
from commands.main import CONFIG as HELLO_CONFIG
from commands.help import CONFIG as HELP_CONFIG
from user import BFGuser

router = Router()

# Редкости как в CS:GO
RARITIES = {
    "Consumer Grade": {"chance": 79.2, "color": "⚪", "multiplier": 1, "price_color": "#B0C3D9"},
    "Industrial Grade": {"chance": 15.98, "color": "🔵", "multiplier": 3, "price_color": "#5E98D9"},
    "Mil-Spec": {"chance": 3.2, "color": "🟣", "multiplier": 10, "price_color": "#4B69FF"},
    "Restricted": {"chance": 0.64, "color": "🟣", "multiplier": 30, "price_color": "#8847FF"},
    "Classified": {"chance": 0.26, "color": "🟠", "multiplier": 80, "price_color": "#D32CE6"},
    "Covert": {"chance": 0.26, "color": "🔴", "multiplier": 200, "price_color": "#EB4B4B"},
    "Extraordinary": {"chance": 0.26, "color": "💎", "multiplier": 1000, "price_color": "#FFD700"},
    "Contraband": {"chance": 0.001, "color": "🟤", "multiplier": 5000, "price_color": "#FF5500"}
}

# Предметы по категориям (реальные скины из CS:GO)
ITEMS = {
    "Пистолеты": {
        "Consumer Grade": ["P250 | Sand Dune", "Glock-18 | Night", "USP-S | Forest Leaves"],
        "Industrial Grade": ["P250 | Muertos", "Glock-18 | Bunsen Burner", "USP-S | Guardian"],
        "Mil-Spec": ["Desert Eagle | Bronze Deco", "R8 Revolver | Reboot", "Five-SeveN | Candy Apple"],
        "Restricted": ["Desert Eagle | Directive", "Glock-18 | Water Elemental", "P250 | Asiimov"],
        "Classified": ["USP-S | Kill Confirmed", "Desert Eagle | Blaze", "Glock-18 | Twilight Galaxy"],
        "Covert": ["Desert Eagle | Printstream", "Glock-18 | Fade", "P250 | Nevermore"],
        "Extraordinary": ["★ Karambit", "★ Butterfly Knife"],
        "Contraband": ["★ M9 Bayonet | Lore"]
    },
    "Штурмовые винтовки": {
        "Consumer Grade": ["AK-47 | Safari Mesh", "M4A4 | Urban DDPAT", "M4A1-S | Boreal Forest"],
        "Industrial Grade": ["AK-47 | Elite Build", "M4A4 | Dragon King", "M4A1-S | Leaded Glass"],
        "Mil-Spec": ["AK-47 | Redline", "M4A4 | Evil Daimyo", "M4A1-S | Hyper Beast"],
        "Restricted": ["AK-47 | Vulcan", "M4A4 | Asiimov", "M4A1-S | Golden Coil"],
        "Classified": ["AK-47 | Fire Serpent", "M4A4 | Howl", "M4A1-S | Chantico's Fire"],
        "Covert": ["AK-47 | Bloodsport", "M4A4 | Poseidon", "M4A1-S | Nightmare"],
        "Extraordinary": ["★ Bayonet", "★ M9 Bayonet"],
        "Contraband": ["★ Karambit | Fade"]
    },
    "Снайперские винтовки": {
        "Consumer Grade": ["AWP | Worm God", "SSG 08 | Abyss", "SCAR-20 | Carbon Fiber"],
        "Industrial Grade": ["AWP | Phobos", "SSG 08 | Mainframe", "SCAR-20 | Powercore"],
        "Mil-Spec": ["AWP | Electric Hive", "SSG 08 | Dragonfire", "SCAR-20 | Bloodsport"],
        "Restricted": ["AWP | Hyper Beast", "SSG 08 | Blood in the Water", "SCAR-20 | Assault"],
        "Classified": ["AWP | Lightning Strike", "SSG 08 | Big Iron", "SCAR-20 | Enforcer"],
        "Covert": ["AWP | Dragon Lore", "AWP | Gungnir", "SSG 08 | Sea Calico"],
        "Extraordinary": ["★ Huntsman Knife", "★ Falchion Knife"],
        "Contraband": ["★ Butterfly Knife | Fade"]
    },
    "Ножи": {
        "Consumer Grade": ["★ Shadow Daggers | Forest DDPAT"],
        "Industrial Grade": ["★ Falchion Knife | Urban Masked"],
        "Mil-Spec": ["★ Gut Knife | Boreal Forest"],
        "Restricted": ["★ Flip Knife | Night"],
        "Classified": ["★ M9 Bayonet | Crimson Web"],
        "Covert": ["★ Karambit | Case Hardened"],
        "Extraordinary": ["★ Butterfly Knife | Fade", "★ Karambit | Doppler"],
        "Contraband": ["★ M9 Bayonet | Lore (Factory New)"]
    },
    "Перчатки": {
        "Classified": ["★ Driver Gloves | King Snake"],
        "Covert": ["★ Sport Gloves | Vice"],
        "Extraordinary": ["★ Specialist Gloves | Emerald Web"],
        "Contraband": ["★ Sport Gloves | Pandora's Box"]
    }
}

# Цены кейсов
CASE_PRICES = {
    "weapon": 1000,      # Обычный кейс с оружием
    "premium": 5000,     # Премиум кейс
    "knife": 25000,      # Кейс с ножами
    "elite": 100000,     # Элитный кейс
    "gloves": 50000      # Кейс с перчатками
}

class CSMarketDB:
    def __init__(self):
        # Используем вашу существующую базу данных users.db
        self.users_conn = sqlite3.connect('users.db')
        self.users_cursor = self.users_conn.cursor()
        
        # Создаем отдельную базу для маркета
        os.makedirs('modules/temp', exist_ok=True)
        market_db_path = 'modules/temp/cs_market.db'
        self.market_conn = sqlite3.connect(market_db_path)
        self.market_cursor = self.market_conn.cursor()
        self.create_market_tables()

    def create_market_tables(self):
        """Создаем таблицы только для маркета (отдельно от основной базы)"""
        # Таблица инвентаря
        self.market_cursor.execute('''
            CREATE TABLE IF NOT EXISTS cs_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_name TEXT,
                rarity TEXT,
                category TEXT,
                price INTEGER,
                float_value REAL DEFAULT 0.0,
                is_stattrak BOOLEAN DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )''')
        
        # Таблица маркета (предметы на продажу)
        self.market_cursor.execute('''
            CREATE TABLE IF NOT EXISTS cs_market (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_id INTEGER,
                item_name TEXT,
                rarity TEXT,
                category TEXT,
                price INTEGER,
                float_value REAL DEFAULT 0.0,
                is_stattrak BOOLEAN DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_id) REFERENCES cs_inventory (id)
            )''')
        
        # Таблица истории транзакций
        self.market_cursor.execute('''
            CREATE TABLE IF NOT EXISTS cs_market_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                buyer_id INTEGER,
                seller_id INTEGER,
                item_name TEXT,
                price INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )''')
        
        # Таблица статистики кейсов
        self.market_cursor.execute('''
            CREATE TABLE IF NOT EXISTS cs_user_stats (
                user_id INTEGER PRIMARY KEY,
                cases_opened INTEGER DEFAULT 0,
                total_spent INTEGER DEFAULT 0,
                total_earned INTEGER DEFAULT 0,
                reputation INTEGER DEFAULT 100
            )''')
        
        self.market_conn.commit()

    # Работа с основной базой данных users
    async def get_user_balance(self, user_id):
        """Получаем баланс пользователя из основной базы"""
        result = self.users_cursor.execute(
            'SELECT balance FROM users WHERE userid = ?', (user_id,)
        ).fetchone()
        return result[0] if result else 0

    async def update_user_balance(self, user_id, amount):
        """Обновляем баланс пользователя в основной базе"""
        current_balance = await self.get_user_balance(user_id)
        new_balance = current_balance + amount
        self.users_cursor.execute(
            'UPDATE users SET balance = ? WHERE userid = ?', 
            (new_balance, user_id)
        )
        self.users_conn.commit()
        return new_balance

    # Работа с маркет-базой
    async def reg_user_stats(self, user_id):
        """Регистрируем пользователя в статистике маркета"""
        ex = self.market_cursor.execute(
            'SELECT user_id FROM cs_user_stats WHERE user_id = ?', (user_id,)
        ).fetchone()
        if not ex:
            self.market_cursor.execute(
                'INSERT INTO cs_user_stats (user_id) VALUES (?)', (user_id,)
            )
            self.market_conn.commit()

    async def get_user_stats(self, user_id):
        """Получаем статистику пользователя"""
        await self.reg_user_stats(user_id)
        return self.market_cursor.execute(
            'SELECT * FROM cs_user_stats WHERE user_id = ?', (user_id,)
        ).fetchone()

    async def add_to_inventory(self, user_id, item_name, rarity, category, price, float_value=0.0, is_stattrak=False):
        """Добавляем предмет в инвентарь"""
        await self.reg_user_stats(user_id)
        self.market_cursor.execute(
            'INSERT INTO cs_inventory (user_id, item_name, rarity, category, price, float_value, is_stattrak) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, item_name, rarity, category, price, float_value, is_stattrak)
        )
        self.market_conn.commit()
        return self.market_cursor.lastrowid

    async def get_inventory(self, user_id):
        """Получаем инвентарь пользователя"""
        await self.reg_user_stats(user_id)
        return self.market_cursor.execute(
            'SELECT * FROM cs_inventory WHERE user_id = ? ORDER BY timestamp DESC', 
            (user_id,)
        ).fetchall()

    async def get_inventory_item(self, user_id, item_id):
        """Получаем конкретный предмет из инвентаря"""
        await self.reg_user_stats(user_id)
        return self.market_cursor.execute(
            'SELECT * FROM cs_inventory WHERE id = ? AND user_id = ?', 
            (item_id, user_id)
        ).fetchone()

    async def remove_from_inventory(self, user_id, item_id):
        """Удаляем предмет из инвентаря"""
        await self.reg_user_stats(user_id)
        self.market_cursor.execute(
            'DELETE FROM cs_inventory WHERE id = ? AND user_id = ?', 
            (item_id, user_id)
        )
        self.market_conn.commit()

    async def add_to_market(self, user_id, item_id, price):
        """Выставляем предмет на маркет"""
        item = await self.get_inventory_item(user_id, item_id)
        if not item:
            return False
        
        self.market_cursor.execute(
            'INSERT INTO cs_market (user_id, item_id, item_name, rarity, category, price, float_value, is_stattrak) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (user_id, item_id, item[2], item[3], item[4], price, item[6], item[7])
        )
        self.market_conn.commit()
        return True

    async def get_market_items(self, category=None, rarity=None, page=0, limit=10):
        """Получаем предметы с маркета"""
        query = 'SELECT * FROM cs_market WHERE 1=1'
        params = []
        
        if category:
            query += ' AND category = ?'
            params.append(category)
        if rarity:
            query += ' AND rarity = ?'
            params.append(rarity)
            
        query += ' ORDER BY price ASC LIMIT ? OFFSET ?'
        params.extend([limit, page * limit])
        
        return self.market_cursor.execute(query, params).fetchall()

    async def get_market_item(self, market_id):
        """Получаем конкретный предмет с маркета"""
        return self.market_cursor.execute(
            'SELECT * FROM cs_market WHERE id = ?', (market_id,)
        ).fetchone()

    async def remove_from_market(self, market_id):
        """Удаляем предмет с маркета"""
        self.market_cursor.execute(
            'DELETE FROM cs_market WHERE id = ?', (market_id,)
        )
        self.market_conn.commit()

    async def buy_from_market(self, buyer_id, market_id):
        """Покупаем предмет с маркета"""
        market_item = await self.get_market_item(market_id)
        if not market_item:
            return False
        
        # Проверяем баланс покупателя
        buyer_balance = await self.get_user_balance(buyer_id)
        if buyer_balance < market_item[6]:
            return False
        
        # Переводим деньги между пользователями
        await self.update_user_balance(buyer_id, -market_item[6])
        await self.update_user_balance(market_item[1], market_item[6])
        
        # Добавляем в инвентарь покупателя
        await self.add_to_inventory(
            buyer_id, market_item[3], market_item[4], market_item[5], 
            market_item[6], market_item[7], market_item[8]
        )
        
        # Удаляем с маркета
        await self.remove_from_market(market_id)
        
        # Удаляем из инвентаря продавца
        await self.remove_from_inventory(market_item[1], market_item[2])
        
        # Записываем в историю
        self.market_cursor.execute(
            'INSERT INTO cs_market_history (buyer_id, seller_id, item_name, price) VALUES (?, ?, ?, ?)',
            (buyer_id, market_item[1], market_item[3], market_item[6])
        )
        
        self.market_conn.commit()
        return True

    async def record_case_opened(self, user_id, spent, earned):
        """Записываем статистику открытия кейса"""
        await self.reg_user_stats(user_id)
        self.market_cursor.execute(
            'UPDATE cs_user_stats SET cases_opened = cases_opened + 1, total_spent = total_spent + ?, total_earned = total_earned + ? WHERE user_id = ?',
            (spent, earned, user_id)
        )
        self.market_conn.commit()

# Инициализация базы данных
try:
    db = CSMarketDB()
except Exception as e:
    print(f"Ошибка инициализации базы данных CS Market: {e}")
    db = None

def get_random_item(case_type):
    """Генерация случайного предмета в зависимости от типа кейса"""
    if case_type == "knife":
        categories = ["Ножи"]
    elif case_type == "gloves":
        categories = ["Перчатки"]
    elif case_type == "elite":
        categories = ["Пистолеты", "Штурмовые винтовки", "Снайперские винтовки", "Ножи"]
    else:
        categories = ["Пистолеты", "Штурмовые винтовки", "Снайперские винтовки"]
    
    category = random.choice(categories)
    
    # Выбор редкости на основе шансов CS:GO
    rand = random.random() * 100
    cumulative = 0
    selected_rarity = "Consumer Grade"
    
    for rarity, data in RARITIES.items():
        cumulative += data["chance"]
        if rand <= cumulative:
            selected_rarity = rarity
            break
    
    # Выбор конкретного предмета
    items_in_category = ITEMS[category].get(selected_rarity, [])
    if not items_in_category:
        selected_rarity = "Consumer Grade"
        items_in_category = ITEMS[category]["Consumer Grade"]
    
    item_name = random.choice(items_in_category)
    
    # Расчет цены с учетом float и stattrack
    base_price = CASE_PRICES[case_type]
    price = int(base_price * RARITIES[selected_rarity]["multiplier"])
    
    # Float value (качество скина)
    float_value = round(random.uniform(0.0, 1.0), 4)
    
    # StatTrak шанс (10% для оружия, 100% для ножей)
    is_stattrak = random.random() < 0.1 if category != "Ножи" and category != "Перчатки" else True
    
    if is_stattrak:
        item_name = "StatTrak™ " + item_name
        price = int(price * 1.5)
    
    # Множитель за качество float
    if float_value < 0.07:  # Factory New
        price = int(price * 2.0)
    elif float_value < 0.15:  # Minimal Wear
        price = int(price * 1.5)
    elif float_value < 0.38:  # Field-Tested
        price = int(price * 1.2)
    elif float_value < 0.45:  # Well-Worn
        price = int(price * 1.1)
    # Battle-Scarred - базовая цена
    
    return {
        "name": item_name,
        "rarity": selected_rarity,
        "category": category,
        "price": price,
        "color": RARITIES[selected_rarity]["color"],
        "float_value": float_value,
        "is_stattrak": is_stattrak
    }

def get_float_quality(float_value):
    """Определение качества скина по float value"""
    if float_value < 0.07:
        return "Factory New"
    elif float_value < 0.15:
        return "Minimal Wear"
    elif float_value < 0.38:
        return "Field-Tested"
    elif float_value < 0.45:
        return "Well-Worn"
    else:
        return "Battle-Scarred"

def cases_kb():
    """Клавиатура для выбора кейсов"""
    keyboards = InlineKeyboardMarkup(row_width=2)
    keyboards.add(
        InlineKeyboardButton("🔫 Оружие (1,000$)", callback_data="case_weapon"),
        InlineKeyboardButton("💎 Премиум (5,000$)", callback_data="case_premium"),
        InlineKeyboardButton("🔪 Ножи (25,000$)", callback_data="case_knife"),
        InlineKeyboardButton("🧤 Перчатки (50,000$)", callback_data="case_gloves"),
        InlineKeyboardButton("👑 Элитный (100,000$)", callback_data="case_elite")
    )
    keyboards.add(
        InlineKeyboardButton("🎒 Инвентарь", callback_data="inventory"),
        InlineKeyboardButton("🏪 Маркет", callback_data="market")
    )
    return keyboards

def market_kb():
    """Клавиатура для маркета"""
    keyboards = InlineKeyboardMarkup(row_width=2)
    keyboards.add(
        InlineKeyboardButton("🔫 Оружие", callback_data="market_weapons"),
        InlineKeyboardButton("🔪 Ножи", callback_data="market_knives"),
        InlineKeyboardButton("🧤 Перчатки", callback_data="market_gloves")
    )
    keyboards.add(
        InlineKeyboardButton("📈 Дешевые", callback_data="market_cheap"),
        InlineKeyboardButton("💎 Дорогие", callback_data="market_expensive")
    )
    keyboards.add(InlineKeyboardButton("🎒 Мой инвентарь", callback_data="inventory"))
    return keyboards

@router.message(F.text.lower() == 'кейсы')
@antispam
async def cases_menu(message: Message, user: BFGuser):
    if not db:
        await message.answer('❌ База данных временно недоступна')
        return
    
    user_balance = await db.get_user_balance(user.user_id)
    user_stats = await db.get_user_stats(user.user_id)
    
    text = f'''🎮 <b>CS2 Case Opening</b>

💰 Ваш баланс: <code>{tr(user_balance)}$</code>
📦 Открыто кейсов: <code>{user_stats[1]}</code>

<b>Доступные кейсы:</b>
🔫 Оружие - 1,000$ (обычные скины)
💎 Премиум - 5,000$ (редкие скины)  
🔪 Ножи - 25,000$ (только ножи)
🧤 Перчатки - 50,000$ (только перчатки)
👑 Элитный - 100,000$ (все категории)

🎯 <b>Особенности:</b>
• Система редкости как в CS:GO
• Float value (качество скина)
• StatTrak™ версии
• Реальный маркет для торговли'''

    await message.answer(text, reply_markup=cases_kb())

@router.callback_query(F.data.startswith('case_'))
@antispam_earning
async def open_case(call: CallbackQuery, user: BFGuser):
    if not db:
        await call.answer('❌ База данных временно недоступна', show_alert=True)
        return
    
    case_type = call.data.split('_')[1]
    price = CASE_PRICES[case_type]
    
    user_balance = await db.get_user_balance(user.user_id)
    
    if user_balance < price:
        await call.answer(f'❌ Недостаточно средств! Нужно {tr(price)}$', show_alert=True)
        return
    
    # Списываем деньги
    await db.update_user_balance(user.user_id, -price)
    
    # Открываем кейс
    item = get_random_item(case_type)
    
    # Добавляем в инвентарь
    item_id = await db.add_to_inventory(
        user.user_id, item["name"], item["rarity"], item["category"], 
        item["price"], item["float_value"], item["is_stattrak"]
    )
    
    # Записываем статистику
    await db.record_case_opened(user.user_id, price, item["price"])
    
    # Анимация открытия
    msg = await call.message.edit_text(f"{user.url}, открываем кейс...\n\n🎁 | ❓")
    
    try:
        for i in range(3):
            await asyncio.sleep(0.5)
            symbols = ["🎁", "✨", "💎"]
            await msg.edit_text(f"{user.url}, открываем кейс...\n\n{symbols[i]} | ❓")
        
        await asyncio.sleep(1)
        
        # Формируем информацию о качестве
        quality = get_float_quality(item["float_value"])
        stattrack_text = " ✅ StatTrak™" if item["is_stattrak"] else ""
        
        result_text = f'''{user.url}, вы открыли кейс!

{item["color"]} <b>{item["name"]}</b>{stattrack_text}
📊 Редкость: <b>{item["rarity"]}</b>
🎯 Категория: <b>{item["category"]}</b>
⭐ Качество: <b>{quality}</b>
🔢 Float: <code>{item["float_value"]}</code>
💰 Стоимость: <code>{tr(item["price"])}$</code>

💵 Предмет добавлен в инвентарь!'''
        
        await msg.edit_text(result_text, reply_markup=cases_kb())
    except Exception as e:
        await call.message.answer(f"{user.url}, произошла ошибка при открытии кейса")

@router.callback_query(F.data == 'inventory')
@antispam_earning
async def show_inventory(call: CallbackQuery, user: BFGuser):
    if not db:
        await call.answer('❌ База данных временно недоступна', show_alert=True)
        return
    
    inventory = await db.get_inventory(user.user_id)
    
    if not inventory:
        await call.message.answer(f'{user.url}, ваш инвентарь пуст!', reply_markup=cases_kb())
        return
    
    text = f"🎒 <b>Инвентарь {user.name}</b>\n\n"
    total_value = 0
    
    for item in inventory[:8]:  # Показываем первые 8 предметов
        item_id, user_id, item_name, rarity, category, price, float_value, is_stattrak, timestamp = item
        quality = get_float_quality(float_value)
        stattrack_text = " ✅ StatTrak™" if is_stattrak else ""
        
        text += f"{RARITIES[rarity]['color']} <b>{item_name}</b>{stattrack_text}\n"
        text += f"   📊 {rarity} | 🎯 {category}\n"
        text += f"   ⭐ {quality} | 🔢 {float_value}\n"
        text += f"   💰 {tr(price)}$ | ID: {item_id}\n"
        text += f"   🏪 <code>продать {item_id} [цена]</code>\n\n"
        total_value += price
    
    text += f"💰 <b>Общая стоимость:</b> <code>{tr(total_value)}$</code>"
    
    if len(inventory) > 8:
        text += f"\n\n📁 ... и еще {len(inventory) - 8} предметов"
    
    await call.message.answer(text, reply_markup=cases_kb())

@router.message(F.text.lower().startswith('продать '))
@antispam
async def sell_item(message: Message, user: BFGuser):
    if not db:
        await message.answer('❌ База данных временно недоступна')
        return
    
    try:
        parts = message.text.split()
        item_id = int(parts[1])
        price = int(parts[2])
    except:
        await message.answer('❌ Неверный формат. Используйте: <code>продать [ID] [цена]</code>')
        return
    
    # Проверяем наличие предмета
    item = await db.get_inventory_item(user.user_id, item_id)
    if not item:
        await message.answer('❌ Предмет не найден в вашем инвентаре')
        return
    
    # Проверяем цену (минимум 100$)
    if price < 100:
        await message.answer('❌ Минимальная цена продажи: 100$')
        return
    
    # Добавляем на маркет
    success = await db.add_to_market(user.user_id, item_id, price)
    
    if success:
        await message.answer(f'✅ {user.url}, предмет выставлен на маркет!\n\n'
                           f'{RARITIES[item[3]]["color"]} <b>{item[2]}</b>\n'
                           f'💰 Цена: <code>{tr(price)}$</code>\n\n'
                           f'Для просмотра маркета: <code>маркет</code>')
    else:
        await message.answer('❌ Ошибка при выставлении предмета на маркет')

@router.message(F.text.lower() == 'маркет')
@router.callback_query(F.data == 'market')
@antispam
async def market_menu(message: Message, user: BFGuser):
    if not db:
        await message.answer('❌ База данных временно недоступна')
        return
    
    text = '''🏪 <b>CS2 Market</b>

Здесь вы можете покупать и продавать скины:

• 🔫 Оружие - все типы оружия
• 🔪 Ножи - только ножи  
• 🧤 Перчатки - только перчатки
• 📈 Дешевые - самые доступные предложения
• 💎 Дорогие - премиум предметы

Для продажи предмета из инвентаря:
<code>продать [ID] [цена]</code>'''
    
    if isinstance(message, CallbackQuery):
        await message.message.answer(text, reply_markup=market_kb())
    else:
        await message.answer(text, reply_markup=market_kb())

@router.callback_query(F.data.startswith('market_'))
@antispam_earning
async def show_market(call: CallbackQuery, user: BFGuser):
    if not db:
        await call.answer('❌ База данных временно недоступна', show_alert=True)
        return
    
    market_type = call.data.split('_')[1]
    
    if market_type == "weapons":
        items = await db.get_market_items(category="Пистолеты")
        items.extend(await db.get_market_items(category="Штурмовые винтовки"))
        items.extend(await db.get_market_items(category="Снайперские винтовки"))
        title = "🔫 Оружие"
    elif market_type == "knives":
        items = await db.get_market_items(category="Ножи")
        title = "🔪 Ножи"
    elif market_type == "gloves":
        items = await db.get_market_items(category="Перчатки")
        title = "🧤 Перчатки"
    elif market_type == "cheap":
        items = await db.get_market_items()
        items = sorted(items, key=lambda x: x[6])[:10]  # 10 самых дешевых
        title = "📈 Дешевые"
    elif market_type == "expensive":
        items = await db.get_market_items()
        items = sorted(items, key=lambda x: x[6], reverse=True)[:10]  # 10 самых дорогих
        title = "💎 Дорогие"
    else:
        items = await db.get_market_items()
        title = "🏪 Весь маркет"
    
    if not items:
        await call.message.answer(f'📭 На маркете нет предметов в категории "{title}"')
        return
    
    text = f'🏪 <b>{title}</b>\n\n'
    
    for item in items[:8]:
        market_id, user_id, item_id, item_name, rarity, category, price, float_value, is_stattrak, timestamp = item
        quality = get_float_quality(float_value)
        stattrack_text = " ✅ StatTrak™" if is_stattrak else ""
        
        text += f"{RARITIES[rarity]['color']} <b>{item_name}</b>{stattrack_text}\n"
        text += f"   📊 {rarity} | 🎯 {category}\n"
        text += f"   ⭐ {quality} | 🔢 {float_value}\n"
        text += f"   💰 <code>{tr(price)}$</code> | ID: {market_id}\n"
        text += f"   🛒 <code>купить {market_id}</code>\n\n"
    
    if len(items) > 8:
        text += f"📁 ... и еще {len(items) - 8} предложений"
    
    await call.message.answer(text, reply_markup=market_kb())

@router.message(F.text.lower().startswith('купить '))
@antispam
async def buy_item(message: Message, user: BFGuser):
    if not db:
        await message.answer('❌ База данных временно недоступна')
        return
    
    try:
        market_id = int(message.text.split()[1])
    except:
        await message.answer('❌ Неверный формат. Используйте: <code>купить [ID]</code>')
        return
    
    # Покупаем предмет
    success = await db.buy_from_market(user.user_id, market_id)
    
    if success:
        await message.answer(f'✅ {user.url}, вы успешно купили предмет с маркета!')
    else:
        await message.answer('❌ Не удалось купить предмет. Возможно, его уже купили или у вас недостаточно средств.')

@router.message(F.text.lower() == 'топ кейсы')
@antispam
async def top_cases(message: Message, user: BFGuser):
    if not db:
        await message.answer('❌ База данных временно недоступна')
        return
    
    # Получаем топ игроков по количеству открытых кейсов
    top_players = db.market_cursor.execute(
        'SELECT user_id, cases_opened, total_earned FROM cs_user_stats ORDER BY cases_opened DESC LIMIT 10'
    ).fetchall()
    
    text = "🏆 <b>Топ игроков по открытым кейсам</b>\n\n"
    
    for i, player in enumerate(top_players, 1):
        user_id, cases_opened, total_earned = player
        try:
            user_name = (await bot.get_chat(user_id)).first_name
        except:
            user_name = f"Игрок {user_id}"
        
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🔸"
        text += f"{medal} {user_name}\n"
        text += f"   📦 Кейсов: <code>{cases_opened}</code>\n"
        text += f"   💰 Заработано: <code>{tr(total_earned)}$</code>\n\n"
    
    await message.answer(text)

def register_handlers(dp):
    dp.include_router(router)

MODULE_DESCRIPTION = {
    'name': '🎮 CS2 Market',
    'description': '''Реалистичная система кейсов и маркета в стиле CS2:
- Открытие кейсов с реальными шансами CS:GO
- Система редкости и качества скинов
- StatTrak™ версии предметов
- Полноценный маркет для торговли
- Float value (качество скинов)

Команды:
• Кейсы - открытие кейсов
• Маркет - торговля предметами
• Продать [ID] [цена] - выставить на продажу
• Купить [ID] - купить с маркета
• Топ кейсы - таблица лидеров'''
}
