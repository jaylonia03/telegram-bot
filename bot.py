import telebot
from telebot import types
import json
import os
import random
import string
from datetime import datetime, timedelta
import time

# ========== BOT CONFIG ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8593941443:AAFpZ962tZt0wSuscCGjkUt5o_zVN4N9j30')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '1975110056'))  # Your Telegram ID

bot = telebot.TeleBot(BOT_TOKEN)

# ========== DATA FUNCTIONS (Using Vercel /tmp storage) ==========
DATA_DIR = '/tmp/data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def get_user(user_id):
    users = load_json('users.json')
    return users.get(str(user_id))

def save_user(user_id, data):
    users = load_json('users.json')
    users[str(user_id)] = data
    save_json('users.json', users)

def create_user(user_id, username, first_name):
    if not get_user(user_id):
        config = get_config()
        save_user(user_id, {
            "user_id": user_id,
            "username": username or "NoUsername",
            "first_name": first_name,
            "balance": config.get('signup_bonus', 100),
            "total_earned": config.get('signup_bonus', 100),
            "invite_count": 0,
            "last_checkin": None,
            "last_ad": None,
            "ads_watched": 0,
            "games_played": 0,
            "banned": False,
            "joined": datetime.now().isoformat()
        })
        return True
    return False

def update_balance(user_id, amount):
    user = get_user(user_id)
    if user:
        user['balance'] = user.get('balance', 0) + amount
        user['total_earned'] = user.get('total_earned', 0) + max(0, amount)
        save_user(user_id, user)

def get_config():
    config = load_json('config.json')
    if not config:
        config = {
            "signup_bonus": 100,
            "invite_bonus": 50,
            "coin_value": 0.5,
            "min_withdraw": 50,
            "betting_win_rate": 45,
            "crash_max": 100,
            "coinflip_win_rate": 45,
            "dice_win_rate": 45,
            "checkin_rewards": {
                "Sunday": 5, "Monday": 10, "Tuesday": 15,
                "Wednesday": 20, "Thursday": 30, "Friday": 40, "Saturday": 50
            }
        }
        save_json('config.json', config)
    return config

def save_config(config):
    save_json('config.json', config)

def get_withdrawals():
    return load_json('withdrawals.json')

def save_withdrawal(data):
    withdrawals = load_json('withdrawals.json')
    w_id = str(len(withdrawals) + 1)
    data['id'] = w_id
    data['status'] = 'pending'
    data['date'] = datetime.now().isoformat()
    withdrawals[w_id] = data
    save_json('withdrawals.json', withdrawals)

def get_codes():
    return load_json('codes.json')

def save_code(code, data):
    codes = load_json('codes.json')
    codes[code] = data
    save_json('codes.json', codes)

# ========== KEYBOARDS ==========
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton("💰 Balance"),
        types.KeyboardButton("🎮 Games"),
        types.KeyboardButton("📺 Earn Coins"),
        types.KeyboardButton("👥 Invite"),
        types.KeyboardButton("🏦 Withdraw"),
        types.KeyboardButton("🎟️ Redeem Code"),
        types.KeyboardButton("📊 Stats")
    )
    return markup

def games_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎲 Betting", callback_data="game_bet"),
        types.InlineKeyboardButton("🪙 Flip Coin", callback_data="game_coin"),
        types.InlineKeyboardButton("🎯 Dice Roll", callback_data="game_dice"),
        types.InlineKeyboardButton("◀️ Back", callback_data="back")
    )
    return markup

def earn_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📅 Daily Check-in", callback_data="checkin"),
        types.InlineKeyboardButton("📺 Watch Ad (+5)", callback_data="ad"),
        types.InlineKeyboardButton("◀️ Back", callback_data="back")
    )
    return markup

def admin_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton("📊 Dashboard"),
        types.KeyboardButton("⚙️ Edit Settings"),
        types.KeyboardButton("🏦 Pending WDs"),
        types.KeyboardButton("🎟️ Create Code"),
        types.KeyboardButton("💰 Add Bonus"),
        types.KeyboardButton("👥 User List"),
        types.KeyboardButton("📢 Broadcast"),
        types.KeyboardButton("🔙 User Mode")
    )
    return markup

# ========== START ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    config = get_config()
    
    # Referral
    ref_id = None
    if len(message.text.split()) > 1:
        try:
            ref_id = int(message.text.split()[1].replace("ref", ""))
        except:
            pass
    
    is_new = create_user(user_id, username, first_name)
    
    if ref_id and is_new and ref_id != user_id:
        update_balance(ref_id, config.get('invite_bonus', 50))
        ref_user = get_user(ref_id)
        if ref_user:
            ref_user['invite_count'] = ref_user.get('invite_count', 0) + 1
            save_user(ref_id, ref_user)
        try:
            bot.send_message(ref_id, f"🎉 +{config.get('invite_bonus', 50)} coins! {first_name} joined!")
        except:
            pass
    
    if user_id == ADMIN_ID:
        bot.send_message(message.chat.id, 
            f"🔐 *ADMIN PANEL*\nBalance: {get_user(user_id).get('balance', 0)} coins",
            parse_mode="Markdown",
            reply_markup=admin_keyboard())
    else:
        user = get_user(user_id)
        bot.send_message(message.chat.id,
            f"""╔══════════════════╗
   🎉 WELCOME! 🎉
╚══════════════════╝

👋 {first_name}!
💰 Balance: {user.get('balance', 0)} coins
💵 Value: ₱{user.get('balance', 0) * config.get('coin_value', 0.5) / 100}

🎁 Sign-up Bonus: {config.get('signup_bonus', 100)} coins""",
            reply_markup=main_keyboard())

# ========== BALANCE ==========
@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def balance(message):
    user = get_user(message.from_user.id)
    config = get_config()
    if not user:
        bot.reply_to(message, "Please /start first!")
        return
    
    bot.send_message(message.chat.id,
        f"""╔══════════════════╗
      💰 BALANCE
╚══════════════════╝

💎 Coins: {user.get('balance', 0)}
💵 Value: ₱{user.get('balance', 0) * config.get('coin_value', 0.5) / 100}
📊 Rate: 100 coins = ₱{config.get('coin_value', 0.5)}

🎮 Games: {user.get('games_played', 0)}
📺 Ads: {user.get('ads_watched', 0)}
👥 Invites: {user.get('invite_count', 0)}""")

# ========== GAMES ==========
@bot.message_handler(func=lambda m: m.text == "🎮 Games")
def games(message):
    bot.send_message(message.chat.id, "🎮 *SELECT GAME*", parse_mode="Markdown", reply_markup=games_keyboard())

@bot.callback_query_handler(func=lambda c: c.data == "game_bet")
def bet_start(call):
    user = get_user(call.from_user.id)
    if not user or user.get('balance', 0) < 1:
        bot.answer_callback_query(call.id, "No balance!", show_alert=True)
        return
    msg = bot.send_message(call.message.chat.id, "Enter bet amount (1-1000):")
    bot.register_next_step_handler(msg, bet_amount)

def bet_amount(message):
    try:
        amount = int(message.text)
        if amount < 1 or amount > 1000:
            bot.reply_to(message, "1-1000 only!")
            return
        user = get_user(message.from_user.id)
        if user.get('balance', 0) < amount:
            bot.reply_to(message, "Not enough coins!")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔴 Odd", callback_data=f"bet_odd_{amount}"),
            types.InlineKeyboardButton("⚫ Even", callback_data=f"bet_even_{amount}")
        )
        bot.send_message(message.chat.id, f"💎 Bet: {amount}\nChoose:", reply_markup=markup)
    except:
        bot.reply_to(message, "Enter number only!")

@bot.callback_query_handler(func=lambda c: c.data.startswith("bet_"))
def bet_result(call):
    user = get_user(call.from_user.id)
    config = get_config()
    parts = call.data.split("_")
    choice = parts[1]
    amount = int(parts[2])
    
    if user.get('balance', 0) < amount:
        bot.answer_callback_query(call.id, "No balance!", show_alert=True)
        return
    
    update_balance(call.from_user.id, -amount)
    user = get_user(call.from_user.id)
    user['games_played'] = user.get('games_played', 0) + 1
    save_user(call.from_user.id, user)
    
    number = random.randint(1, 100)
    is_odd = number % 2 != 0
    win = (is_odd and choice == "odd") or (not is_odd and choice == "even")
    actual_win = random.randint(1, 100) <= config.get('betting_win_rate', 45)
    
    if actual_win and win:
        winnings = amount * 2
        update_balance(call.from_user.id, winnings)
        msg = f"🎲 Number: {number}\n✅ WON {winnings} coins!"
    else:
        msg = f"🎲 Number: {number}\n❌ LOST {amount} coins!"
    
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id)

# ========== FLIP COIN ==========
@bot.callback_query_handler(func=lambda c: c.data == "game_coin")
def coin_start(call):
    user = get_user(call.from_user.id)
    if not user or user.get('balance', 0) < 1:
        bot.answer_callback_query(call.id, "No balance!", show_alert=True)
        return
    msg = bot.send_message(call.message.chat.id, "Enter bet amount (1-200):")
    bot.register_next_step_handler(msg, coin_bet)

def coin_bet(message):
    try:
        amount = int(message.text)
        if amount < 1 or amount > 200:
            bot.reply_to(message, "1-200 only!")
            return
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("👤 Heads", callback_data=f"coin_heads_{amount}"),
            types.InlineKeyboardButton("🪙 Tails", callback_data=f"coin_tails_{amount}")
        )
        bot.send_message(message.chat.id, f"💎 {amount} coins\nChoose:", reply_markup=markup)
    except:
        bot.reply_to(message, "Enter number only!")

@bot.callback_query_handler(func=lambda c: c.data.startswith("coin_"))
def coin_result(call):
    user = get_user(call.from_user.id)
    config = get_config()
    parts = call.data.split("_")
    choice = parts[1]
    amount = int(parts[2])
    
    if user.get('balance', 0) < amount:
        bot.answer_callback_query(call.id, "No balance!", show_alert=True)
        return
    
    update_balance(call.from_user.id, -amount)
    user = get_user(call.from_user.id)
    user['games_played'] = user.get('games_played', 0) + 1
    save_user(call.from_user.id, user)
    
    result = random.choice(["heads", "tails"])
    win = choice == result
    actual_win = random.randint(1, 100) <= config.get('coinflip_win_rate', 45)
    
    if actual_win and win:
        winnings = amount * 2
        update_balance(call.from_user.id, winnings)
        msg = f"🪙 {result.upper()}\n✅ WON {winnings} coins!"
    else:
        msg = f"🪙 {result.upper()}\n❌ LOST {amount} coins!"
    
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id)

# ========== DICE ROLL ==========
@bot.callback_query_handler(func=lambda c: c.data == "game_dice")
def dice_start(call):
    user = get_user(call.from_user.id)
    if not user or user.get('balance', 0) < 5:
        bot.answer_callback_query(call.id, "Need 5 coins!", show_alert=True)
        return
    msg = bot.send_message(call.message.chat.id, "Enter bet (5-300):")
    bot.register_next_step_handler(msg, dice_bet)

def dice_bet(message):
    try:
        amount = int(message.text)
        if amount < 5 or amount > 300:
            bot.reply_to(message, "5-300 only!")
            return
        user = get_user(message.from_user.id)
        if user.get('balance', 0) < amount:
            bot.reply_to(message, "Not enough!")
            return
        
        update_balance(message.from_user.id, -amount)
        user = get_user(message.from_user.id)
        user['games_played'] = user.get('games_played', 0) + 1
        save_user(message.from_user.id, user)
        
        dice = bot.send_dice(message.chat.id, emoji="🎲")
        value = dice.dice.value
        config = get_config()
        
        if value > 3 and random.randint(1, 100) <= config.get('dice_win_rate', 45):
            win = amount * 2
            update_balance(message.from_user.id, win)
            bot.reply_to(message, f"🎯 Dice: {value}\n✅ WON {win} coins!")
        else:
            bot.reply_to(message, f"🎯 Dice: {value}\n❌ LOST {amount} coins!")
    except:
        bot.reply_to(message, "Enter number!")

# ========== EARN COINS ==========
@bot.message_handler(func=lambda m: m.text == "📺 Earn Coins")
def earn(message):
    bot.send_message(message.chat.id, "📺 *EARN COINS*", parse_mode="Markdown", reply_markup=earn_keyboard())

@bot.callback_query_handler(func=lambda c: c.data == "checkin")
def checkin(call):
    user = get_user(call.from_user.id)
    config = get_config()
    today = datetime.now().strftime("%Y-%m-%d")
    
    if user.get('last_checkin') == today:
        bot.answer_callback_query(call.id, "Already checked in!", show_alert=True)
        return
    
    day = datetime.now().strftime("%A")
    reward = config.get('checkin_rewards', {}).get(day, 5)
    
    update_balance(call.from_user.id, reward)
    user['last_checkin'] = today
    save_user(call.from_user.id, user)
    
    bot.answer_callback_query(call.id, f"+{reward} coins!", show_alert=True)
    bot.send_message(call.message.chat.id, f"📅 {day}\n✅ +{reward} coins!")

@bot.callback_query_handler(func=lambda c: c.data == "ad")
def watch_ad(call):
    user = get_user(call.from_user.id)
    
    if user.get('last_ad'):
        last = datetime.fromisoformat(user['last_ad'])
        if (datetime.now() - last).seconds < 1800:
            bot.answer_callback_query(call.id, "Wait 30 mins!", show_alert=True)
            return
    
    # Show ad button
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📺 Watch Ad", url="https://monetag.com"))
    markup.add(types.InlineKeyboardButton("✅ Done Watching", callback_data="ad_done"))
    
    bot.send_message(call.message.chat.id, "📺 Click below to watch:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "ad_done")
def ad_done(call):
    update_balance(call.from_user.id, 5)
    user = get_user(call.from_user.id)
    user['last_ad'] = datetime.now().isoformat()
    user['ads_watched'] = user.get('ads_watched', 0) + 1
    save_user(call.from_user.id, user)
    
    bot.answer_callback_query(call.id, "+5 coins!", show_alert=True)
    bot.edit_message_text("✅ +5 coins!", call.message.chat.id, call.message.message_id)

# ========== INVITE ==========
@bot.message_handler(func=lambda m: m.text == "👥 Invite")
def invite(message):
    bot_info = bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref{message.from_user.id}"
    user = get_user(message.from_user.id)
    config = get_config()
    
    bot.send_message(message.chat.id,
        f"""╔══════════════════╗
    👥 INVITE FRIENDS
╚══════════════════╝

🔗 Your Link:
`{link}`

💰 Bonus: {config.get('invite_bonus', 50)} coins each!
📊 Invites: {user.get('invite_count', 0)}

Share & earn!""",
        parse_mode="Markdown")

# ========== REDEEM CODE ==========
@bot.message_handler(func=lambda m: m.text == "🎟️ Redeem Code")
def redeem_prompt(message):
    msg = bot.reply_to(message, "Enter code:")
    bot.register_next_step_handler(msg, redeem_code)

def redeem_code(message):
    code = message.text.strip().upper()
    codes = get_codes()
    
    if code not in codes:
        bot.reply_to(message, "❌ Invalid code!")
        return
    
    code_data = codes[code]
    if code_data.get('used', False):
        bot.reply_to(message, "❌ Already used!")
        return
    
    if str(message.from_user.id) in code_data.get('used_by', []):
        bot.reply_to(message, "❌ You used this already!")
        return
    
    amount = code_data.get('amount', 0)
    update_balance(message.from_user.id, amount)
    
    if code_data.get('type') == 'single':
        codes[code]['used'] = True
    codes[code]['used_by'] = code_data.get('used_by', []) + [str(message.from_user.id)]
    save_json('codes.json', codes)
    
    bot.reply_to(message, f"✅ +{amount} coins!")

# ========== WITHDRAW ==========
@bot.message_handler(func=lambda m: m.text == "🏦 Withdraw")
def withdraw(message):
    user = get_user(message.from_user.id)
    config = get_config()
    peso = user.get('balance', 0) * config.get('coin_value', 0.5) / 100
    
    if peso < config.get('min_withdraw', 50):
        bot.reply_to(message, f"❌ Min: ₱{config.get('min_withdraw', 50)}\nYou: ₱{peso:.2f}")
        return
    
    msg = bot.send_message(message.chat.id, f"Balance: ₱{peso:.2f}\nEnter amount (₱):")
    bot.register_next_step_handler(msg, process_wd)

def process_wd(message):
    try:
        amount = float(message.text)
        config = get_config()
        user = get_user(message.from_user.id)
        max_wd = user.get('balance', 0) * config.get('coin_value', 0.5) / 100
        
        if amount < config.get('min_withdraw', 50):
            bot.reply_to(message, f"Min ₱{config.get('min_withdraw', 50)}")
            return
        if amount > max_wd:
            bot.reply_to(message, f"Max ₱{max_wd:.2f}")
            return
        
        coins = int(amount / config.get('coin_value', 0.5) * 100)
        update_balance(message.from_user.id, -coins)
        
        msg = bot.send_message(message.chat.id, "Enter GCash/Maya number:")
        bot.register_next_step_handler(msg, save_wd, amount, coins)
    except:
        bot.reply_to(message, "Enter valid amount!")

def save_wd(message, amount, coins):
    number = message.text.strip()
    save_withdrawal({
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "amount_coins": coins,
        "amount_peso": amount,
        "number": number
    })
    bot.reply_to(message, f"✅ Request sent!\n₱{amount}\nWait for approval.")

# ========== STATS ==========
@bot.message_handler(func=lambda m: m.text == "📊 Stats")
def stats(message):
    user = get_user(message.from_user.id)
    config = get_config()
    bot.send_message(message.chat.id,
        f"""╔══════════════════╗
      📊 STATS
╚══════════════════╝

💰 Balance: {user.get('balance', 0)}
💵 Value: ₱{user.get('balance', 0) * config.get('coin_value', 0.5) / 100:.2f}
📈 Earned: {user.get('total_earned', 0)}
🎮 Games: {user.get('games_played', 0)}
📺 Ads: {user.get('ads_watched', 0)}
👥 Invites: {user.get('invite_count', 0)}""")

# ========== ADMIN PANEL ==========
@bot.message_handler(func=lambda m: m.text == "📊 Dashboard" and m.from_user.id == ADMIN_ID)
def admin_dashboard(message):
    users = load_json('users.json')
    wds = get_withdrawals()
    config = get_config()
    pending = sum(1 for w in wds.values() if w.get('status') == 'pending')
    
    total_coins = sum(u.get('balance', 0) for u in users.values())
    
    bot.send_message(message.chat.id,
        f"""📊 *DASHBOARD*

👥 Users: {len(users)}
💰 Total Coins: {total_coins}
💵 Value: ₱{total_coins * config.get('coin_value', 0.5) / 100:.2f}
🏦 Pending WD: {pending}""",
        parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "⚙️ Edit Settings" and m.from_user.id == ADMIN_ID)
def admin_settings(message):
    config = get_config()
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Sign-up Bonus", callback_data="edit_signup"),
        types.InlineKeyboardButton("Invite Bonus", callback_data="edit_invite"),
        types.InlineKeyboardButton("Coin Value", callback_data="edit_coinvalue"),
        types.InlineKeyboardButton("Min Withdraw", callback_data="edit_minwd"),
        types.InlineKeyboardButton("Win Rate %", callback_data="edit_winrate")
    )
    bot.send_message(message.chat.id, f"⚙️ *Current Settings*\nSign-up: {config.get('signup_bonus')}\nInvite: {config.get('invite_bonus')}\nValue: {config.get('coin_value')}\nMin WD: {config.get('min_withdraw')}\nWin Rate: {config.get('betting_win_rate')}%", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_") and c.from_user.id == ADMIN_ID)
def edit_setting(call):
    keys = {"edit_signup": "signup_bonus", "edit_invite": "invite_bonus", "edit_coinvalue": "coin_value", "edit_minwd": "min_withdraw", "edit_winrate": "betting_win_rate"}
    key = keys.get(call.data)
    msg = bot.send_message(call.message.chat.id, f"New value for {key}:")
    bot.register_next_step_handler(msg, update_setting, key)

def update_setting(message, key):
    try:
        value = float(message.text)
        config = get_config()
        config[key] = value
        save_config(config)
        bot.reply_to(message, f"✅ {key} = {value}")
    except:
        bot.reply_to(message, "Invalid!")

@bot.message_handler(func=lambda m: m.text == "🏦 Pending WDs" and m.from_user.id == ADMIN_ID)
def admin_wds(message):
    wds = get_withdrawals()
    pending = {k: v for k, v in wds.items() if v.get('status') == 'pending'}
    
    if not pending:
        bot.reply_to(message, "No pending withdrawals!")
        return
    
    for w_id, w in list(pending.items())[:10]:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Approve", callback_data=f"wd_approve_{w_id}"),
            types.InlineKeyboardButton("❌ Reject", callback_data=f"wd_reject_{w_id}")
        )
        bot.send_message(message.chat.id,
            f"🏦 *WD Request #{w_id}*\nUser: {w.get('username')}\nAmount: ₱{w.get('amount_peso')}\nNumber: {w.get('number')}\nDate: {w.get('date', '')[:10]}",
            parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("wd_") and c.from_user.id == ADMIN_ID)
def handle_wd(call):
    parts = call.data.split("_")
    action = parts[1]
    w_id = parts[2]
    wds = get_withdrawals()
    
    if w_id in wds:
        wds[w_id]['status'] = 'approved' if action == 'approve' else 'rejected'
        save_json('withdrawals.json', wds)
        
        if action == 'reject':
            update_balance(wds[w_id]['user_id'], wds[w_id]['amount_coins'])
        
        bot.edit_message_text(f"{'✅ Approved' if action == 'approve' else '❌ Rejected'} #{w_id}",
            call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == "🎟️ Create Code" and m.from_user.id == ADMIN_ID)
def create_code(message):
    msg = bot.send_message(message.chat.id, "Format: AMOUNT-TYPE\nExample: 100-single\nType: single/multi")
    bot.register_next_step_handler(msg, make_code)

def make_code(message):
    try:
        parts = message.text.split("-")
        amount = int(parts[0])
        c_type = parts[1] if len(parts) > 1 else "single"
        
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        save_code(code, {"amount": amount, "type": c_type, "used": False, "used_by": [], "created": datetime.now().isoformat()})
        
        bot.reply_to(message, f"✅ Code: `{code}`\nAmount: {amount}\nType: {c_type}", parse_mode="Markdown")
    except:
        bot.reply_to(message, "Invalid format!")

@bot.message_handler(func=lambda m: m.text == "💰 Add Bonus" and m.from_user.id == ADMIN_ID)
def add_bonus_prompt(message):
    msg = bot.send_message(message.chat.id, "Format: USER_ID-AMOUNT\nExample: 123456-100")
    bot.register_next_step_handler(msg, add_bonus)

def add_bonus(message):
    try:
        parts = message.text.split("-")
        uid = int(parts[0])
        amount = int(parts[1])
        update_balance(uid, amount)
        try:
            bot.send_message(uid, f"🎁 Admin added {amount} coins!")
        except:
            pass
        bot.reply_to(message, f"✅ +{amount} to {uid}")
    except:
        bot.reply_to(message, "Invalid!")

@bot.message_handler(func=lambda m: m.text == "🔙 User Mode" and m.from_user.id == ADMIN_ID)
def user_mode(message):
    bot.send_message(message.chat.id, "Switched to user mode", reply_markup=main_keyboard())

@bot.callback_query_handler(func=lambda c: c.data == "back")
def go_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Main menu:", reply_markup=main_keyboard())

# ========== WEBHOOK FOR VERCEL ==========
from flask import Flask, request
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Bad Request', 403

# For local testing
if __name__ == '__main__':
    print("Starting bot...")
    bot.polling(none_stop=True)
