import asyncio
import random
import time
from decimal import Decimal

from aiogram import F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from assets.antispam import antispam, antispam_earning, new_earning
from assets.transform import transform_int as tr
from bot import bot, dp
from commands.db import conn, cursor, url_name
from commands.help import CONFIG
from user import BFGuser, BFGconst

CONFIG['help_game'] += '\n   🔘 Кн [ставка]'


games = []
waiting = {}


def creat_start_kb() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤯 Принять вызов", callback_data="tictactoe-start")]
    ])
    return keyboard


async def update_balance(user_id: int, amount: int | str, operation="subtract") -> None:
    balance = cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)).fetchone()[0]
    
    if operation == 'add':
        new_balance = Decimal(str(balance)) + Decimal(str(amount))
    else:
        new_balance = Decimal(str(balance)) - Decimal(str(amount))
    
    new_balance = "{:.0f}".format(new_balance)
    cursor.execute('UPDATE users SET balance = ? WHERE user_id = ?', (str(new_balance), user_id))
    cursor.execute('UPDATE users SET games = games + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    

class Game:
    def __init__(self, chat_id, user_id, summ, message_id):
        self.chat_id = chat_id
        self.user_id = user_id
        self.chips = {}
        self.r_id = 0
        self.move = random.choice(['cross', 'zero'])
        self.message_id = message_id
        self.summ = summ
        self.board = [['  ' for _ in range(3)] for _ in range(3)]
        self.last_time = time.time()
    
    def start(self):
        self.last_time = time.time()
        players = [self.user_id, self.r_id]
        random.shuffle(players)
        self.chips['cross'] = players[0]
        self.chips['zero'] = players[1]
    
    def get_user_chips(self, user_id):
        if self.chips.get('cross') == user_id:
            return 'cross'
        return 'zero'
        
    def make_move(self, x, y, user_id):
        if self.board[x][y] != '  ':
            return "not empty"
        
        marker = self.get_user_chips(user_id)
        marker = '❌' if marker == 'cross' else '⭕️'
        
        self.last_time = time.time()
        self.board[x][y] = marker
        
        self.move = 'zero' if self.move == 'cross' else 'cross'
    
    def check_winner(self):
        win_combinations = [
            # горизонтали
            [(0, 0), (0, 1), (0, 2)],
            [(1, 0), (1, 1), (1, 2)],
            [(2, 0), (2, 1), (2, 2)],
            # вертикали
            [(0, 0), (1, 0), (2, 0)],
            [(0, 1), (1, 1), (2, 1)],
            [(0, 2), (1, 2), (2, 2)],
            # диагонали
            [(0, 0), (1, 1), (2, 2)],
            [(0, 2), (1, 1), (2, 0)]
        ]
        
        for combo in win_combinations:
            symbols = [self.board[x][y] for x, y in combo]
            if symbols[0] != '  ' and symbols[0] == symbols[1] == symbols[2]:
                return symbols[0]
        
        if all(self.board[i][j] != '  ' for i in range(3) for j in range(3)):
            return 'draw'
        
        return None
    
    def get_kb(self):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for i in range(3):
            row = []
            for j in range(3):
                row.append(InlineKeyboardButton(text=self.board[i][j], callback_data=f"TicTacToe_{i}_{j}"))
            keyboard.inline_keyboard.append(row)
        return keyboard

    async def pay_money(self, user_id, summ):
        await update_balance(user_id, summ, operation='add')

        
def find_waiting(chat_id, message_id):
    for game in waiting.keys():
        if game.chat_id == chat_id and game.message_id == message_id:
            return game
    return None


def find_game_by_mid(chat_id, message_id):
    for game in games:
        if game.chat_id == chat_id and game.message_id == message_id:
            return game
    return None


def find_game_by_userid(user_id):
    for game in games:
        if game.user_id == user_id or game.r_id == user_id:
            return game
    return None


@dp.message(F.text.lower().startswith('кн'))
@antispam
async def start(message: Message, user: BFGuser):
    win, lose = BFGconst.emj()
    
    if message.chat.type != 'supergroup':
        return
    
    if find_game_by_userid(user.user_id):
        await message.answer(f'{user.url}, у вас уже есть активная игра {lose}')
        return
        
    try:
        if message.text.lower().split()[1] in ['все', 'всё']:
            summ = int(user.balance)
        else:
            summ = message.text.split()[1].replace('е', 'e')
            summ = int(float(summ))
    except:
        await message.answer(f'{user.url}, вы не ввели ставку для игры 🫤')
        return
    
    if summ < 10:
        await message.answer(f'{user.url}, минимальная ставка - 10$ {lose}')
        return
    
    if summ > int(user.balance):
        await message.answer(f'{user.url}, у вас недостаточно денег {lose}')
        return
    
    msg = await message.answer(f"❌⭕️ {user.url} хочет сыграть в крестики-нолики\n💰 Ставка: {tr(summ)}$\n⏳ <i>Ожидаю противника в течении 3х минут</i>", reply_markup=creat_start_kb())
    game = Game(msg.chat.id, user.user_id, summ, msg.message_id)
    await new_earning(msg)
    await update_balance(user.user_id, summ, operation='subtract')
    waiting[game] = int(time.time()) + 180
    

@dp.callback_query(F.data == "tictactoe-start")
@antispam_earning
async def start_game_kb(call: CallbackQuery, user: BFGuser):
    game = find_waiting(call.message.chat.id, call.message.message_id)
    
    if not game or user.user_id == game.user_id:
        return
    
    if int(user.balance) < game.summ:
        await call.answer('❌ У вас недостаточно денег.', show_alert=True)
        return
    
    games.append(game)
    waiting.pop(game)
    
    game.r_id = user.user_id
    game.start()
    
    cross = await url_name(game.chips['cross'])
    zero = await url_name(game.chips['zero'])
    
    crossp, zerop = ('ᅠ ', '👉') if game.move == 'zero' else ('👉', 'ᅠ ')
    
    text = f'''<b>Игра крестики-нолики</b>
💰 Ставка: {tr(game.summ)}$

{crossp}❌ {cross}
{zerop}⭕️ {zero}'''
    
    await call.message.edit_text(text, reply_markup=game.get_kb())
    await update_balance(user.user_id, game.summ, operation='subtract')


@dp.callback_query(F.data.startswith("TicTacToe_"))
@antispam_earning
async def game_kb(call: CallbackQuery, user: BFGuser):
    game = find_game_by_mid(call.message.chat.id, call.message.message_id)
    
    if not game:
        return
    
    if game.r_id != user.user_id and game.user_id != user.user_id:
        await call.answer('💩 Вы не можете нажать на эту кнопку.', show_alert=True)
        return
    
    if game.get_user_chips(user.user_id) != game.move:
        await call.answer('❌ Не ваш ход.', show_alert=True)
        return
    
    x = int(call.data.split('_')[1])
    y = int(call.data.split('_')[2])
    result = game.make_move(x, y, user.user_id)
    
    if result == 'not empty':
        await call.answer('❌ Эта клетка уже занята.', show_alert=True)
        return
    
    cross = await url_name(game.chips['cross'])
    zero = await url_name(game.chips['zero'])
    
    crossp, zerop = ('ᅠ ', '👉') if game.move == 'zero' else ('👉', 'ᅠ ')
    
    text = f'''<b>Игра крестики-нолики</b>
💰 Ставка: {tr(game.summ)}$

{crossp}❌ {cross}
{zerop}⭕️ {zero}'''
    
    await call.message.edit_text(text, reply_markup=game.get_kb())
    
    result = game.check_winner()
    if result:
        if result == 'draw':
            await call.message.answer(f'🥸 У вас ничья!\n<i>Деньги возвращены.</i>', reply_to_message_id=game.message_id)
            await update_balance(game.user_id, game.summ, operation='add')
            await update_balance(game.r_id, game.summ, operation='add')
        else:
            move = 'zero' if result == '⭕️' else 'cross'
            win = game.chips[move]
            win_name = await url_name(win)
            await call.message.answer(f'🎊 {win_name} поздравляем с победой!\n<i>💰 Приз: {tr(game.summ*2)}$</i>', reply_to_message_id=game.message_id)
            await update_balance(win, (game.summ*2), operation='add')
        
        games.remove(game)


async def check_waiting():
    while True:
        for game, gtime in list(waiting.items()):
            if int(time.time()) > gtime:
                waiting.pop(game)
                chat_id = game.chat_id
                message_id = game.message_id
                try:
                    await bot.send_message(chat_id, f'❌ Не удалось найти противника.', reply_to_message_id=message_id)
                    await game.pay_money(game.user_id, game.summ)
                except:
                    pass
        await asyncio.sleep(30)
        
        
async def check_game():
    while True:
        for game in games:
            if int(time.time()) > int(game.last_time+60):
                games.remove(game)
                chat_id = game.chat_id
                message_id = game.message_id
                try:
                    win = 'zero' if game.move == 'cross' else 'cross'
                    win = game.chips[win]
                    win_name = await url_name(win)
                    await update_balance(win, (game.summ * 2), operation='add')
                    txt = f'⚠️ <b>От противника давно не было активности</b>\n{win_name} поздравляем с победой!\n<i>💰 Приз: {tr(game.summ*2)}$</i>'
                    await bot.send_message(chat_id, txt, reply_to_message_id=message_id)
                except:
                    pass
        await asyncio.sleep(30)


async def start_background_tasks():
    asyncio.create_task(check_waiting())
    asyncio.create_task(check_game())

def register_handlers(dp):
    asyncio.create_task(start_background_tasks())

asyncio.create_task(start_background_tasks())

MODULE_DESCRIPTION = {
    'name': '❌⭕️ Крестики-нолики',
    'description': 'Новая игра "крестики-нолики" против других игроков (на деньги)'
}
