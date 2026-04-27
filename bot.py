import telebot
from telebot import types
import json
import random
import string
from datetime import datetime
from flask import Flask, request

# ========== CONFIG ==========
BOT_TOKEN = "null"
ADMIN_ID = 1975110056

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ========== MEMORY STORAGE ==========
users_db = {}
withdrawals_db = {}
codes_db = {}
config_db = {
    "signup_bonus": 100,
    "invite_bonus": 50,
    "coin_value": 0.5,
    "min_withdraw": 50,
    "betting_win_rate": 45,
    "coinflip_win_rate": 45,
    "dice_win_rate": 45,
    "checkin_rewards": {
        "Sunday": 5, "Monday": 10, "Tuesday": 15,
        "Wednesday": 20, "Thursday": 30, "Friday": 40, "Saturday": 50
    }
}

# ========== HELPERS ==========
def get_user(uid):
    return users_db.get(str(uid))

def create_user(uid, uname, fname):
    if str(uid) not in users_db:
        users_db[str(uid)] = {
            "user_id": uid,
            "username": uname or "NoUsername",
            "first_name": fname,
            "balance": config_db["signup_bonus"],
            "total_earned": config_db["signup_bonus"],
            "invite_count": 0,
            "last_checkin": None,
            "last_ad": None,
            "ads_watched": 0,
            "games_played": 0,
            "banned": False
        }
        return True
    return False

def update_balance(uid, amount):
    user = get_user(uid)
    if user:
        user["balance"] += amount
        if amount > 0:
            user["total_earned"] += amount

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
    uid = message.from_user.id
    uname = message.from_user.username
    fname = message.from_user.first_name
    
    ref_id = None
    if len(message.text.split()) > 1:
        try:
            ref_id = int(message.text.split()[1].replace("ref", ""))
        except:
            pass
    
    is_new = create_user(uid, uname, fname)
    
    if ref_id and is_new and ref_id != uid:
        update_balance(ref_id, config_db["invite_bonus"])
        ref = get_user(ref_id)
        if ref:
            ref["invite_count"] = ref.get("invite_count", 0) + 1
            try:
                bot.send_message(ref_id, f"🎉 +{config_db['invite_bonus']} coins! {fname} joined!")
            except:
                pass
    
    if uid == ADMIN_ID:
        bot.send_message(message.chat.id, f"🔐 ADMIN PANEL\n\nWelcome {fname}!\nBalance: {get_user(uid)['balance']} coins", reply_markup=admin_keyboard())
    else:
        user = get_user(uid)
        cv = config_db["coin_value"]
        bot.send_message(message.chat.id, f"""╔══════════════════╗
   🎉 WELCOME! 🎉
╚══════════════════╝

👋 {fname}!
💰 Balance: {user['balance']} coins
💵 Value: ₱{user['balance'] * cv / 100}

🎁 Sign-up Bonus: {config_db['signup_bonus']} coins""", reply_markup=main_keyboard())

# ========== BALANCE ==========
@bot.message_handler(func=lambda m: m.text == "💰 Balance")
def balance(message):
    user = get_user(message.from_user.id)
    if not user:
        bot.reply_to(message, "Please /start first!")
        return
    cv = config_db["coin_value"]
    bot.send_message(message.chat.id, f"""╔══════════════════╗
      💰 BALANCE
╚══════════════════╝

💎 Coins: {user['balance']}
💵 Value: ₱{user['balance'] * cv / 100}
📊 Rate: 100 coins = ₱{cv}

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
    if not user or user['balance'] < 1:
        bot.answer_callback_query(call.id, "No balance!", show_alert=True)
        return
    msg = bot.send_message(call.message.chat.id, "Enter bet (1-1000):")
    bot.register_next_step_handler(msg, bet_amt)

def bet_amt(message):
    try:
        amt = int(message.text)
        if amt < 1 or amt > 1000:
            bot.reply_to(message, "1-1000 only!")
            return
        if get_user(message.from_user.id)['balance'] < amt:
            bot.reply_to(message, "Not enough!")
            return
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔴 Odd", callback_data=f"bet_odd_{amt}"),
            types.InlineKeyboardButton("⚫ Even", callback_data=f"bet_even_{amt}")
        )
        bot.send_message(message.chat.id, f"💎 {amt} coins\nChoose:", reply_markup=markup)
    except:
        bot.reply_to(message, "Invalid number!")

@bot.callback_query_handler(func=lambda c: c.data.startswith("bet_"))
def bet_res(call):
    user = get_user(call.from_user.id)
    parts = call.data.split("_")
    choice = parts[1]
    amt = int(parts[2])
    
    if user['balance'] < amt:
        bot.answer_callback_query(call.id, "No balance!", show_alert=True)
        return
    
    update_balance(call.from_user.id, -amt)
    user['games_played'] += 1
    
    num = random.randint(1, 100)
    is_odd = num % 2 != 0
    win = (is_odd and choice == "odd") or (not is_odd and choice == "even")
    actual = random.randint(1, 100) <= config_db["betting_win_rate"]
    
    if actual and win:
        winnings = amt * 2
        update_balance(call.from_user.id, winnings)
        msg = f"🎲 Number: {num}\n✅ WON {winnings} coins!"
    else:
        msg = f"🎲 Number: {num}\n❌ LOST {amt} coins!"
    
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id)

# ========== FLIP COIN ==========
@bot.callback_query_handler(func=lambda c: c.data == "game_coin")
def coin_start(call):
    user = get_user(call.from_user.id)
    if not user or user['balance'] < 1:
        bot.answer_callback_query(call.id, "No balance!", show_alert=True)
        return
    msg = bot.send_message(call.message.chat.id, "Enter bet (1-200):")
    bot.register_next_step_handler(msg, coin_amt)

def coin_amt(message):
    try:
        amt = int(message.text)
        if amt < 1 or amt > 200:
            bot.reply_to(message, "1-200 only!")
            return
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("👤 Heads", callback_data=f"coin_heads_{amt}"),
            types.InlineKeyboardButton("🪙 Tails", callback_data=f"coin_tails_{amt}")
        )
        bot.send_message(message.chat.id, f"💎 {amt} coins\nChoose:", reply_markup=markup)
    except:
        bot.reply_to(message, "Invalid number!")

@bot.callback_query_handler(func=lambda c: c.data.startswith("coin_"))
def coin_res(call):
    user = get_user(call.from_user.id)
    parts = call.data.split("_")
    choice = parts[1]
    amt = int(parts[2])
    
    if user['balance'] < amt:
        bot.answer_callback_query(call.id, "No balance!", show_alert=True)
        return
    
    update_balance(call.from_user.id, -amt)
    user['games_played'] += 1
    
    result = random.choice(["heads", "tails"])
    win = choice == result
    actual = random.randint(1, 100) <= config_db["coinflip_win_rate"]
    
    if actual and win:
        winnings = amt * 2
        update_balance(call.from_user.id, winnings)
        msg = f"🪙 {result.upper()}\n✅ WON {winnings} coins!"
    else:
        msg = f"🪙 {result.upper()}\n❌ LOST {amt} coins!"
    
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id)

# ========== DICE ==========
@bot.callback_query_handler(func=lambda c: c.data == "game_dice")
def dice_start(call):
    user = get_user(call.from_user.id)
    if not user or user['balance'] < 5:
        bot.answer_callback_query(call.id, "Need 5 coins!", show_alert=True)
        return
    msg = bot.send_message(call.message.chat.id, "Enter bet (5-300):")
    bot.register_next_step_handler(msg, dice_amt)

def dice_amt(message):
    try:
        amt = int(message.text)
        if amt < 5 or amt > 300:
            bot.reply_to(message, "5-300 only!")
            return
        if get_user(message.from_user.id)['balance'] < amt:
            bot.reply_to(message, "Not enough!")
            return
        
        update_balance(message.from_user.id, -amt)
        user = get_user(message.from_user.id)
        user['games_played'] += 1
        
        dice = bot.send_dice(message.chat.id, emoji="🎲")
        val = dice.dice.value
        
        if val > 3 and random.randint(1, 100) <= config_db["dice_win_rate"]:
            win = amt * 2
            update_balance(message.from_user.id, win)
            bot.reply_to(message, f"🎯 Dice: {val}\n✅ WON {win} coins!")
        else:
            bot.reply_to(message, f"🎯 Dice: {val}\n❌ LOST {amt} coins!")
    except:
        bot.reply_to(message, "Invalid number!")

# ========== EARN ==========
@bot.message_handler(func=lambda m: m.text == "📺 Earn Coins")
def earn(message):
    bot.send_message(message.chat.id, "📺 *EARN*", parse_mode="Markdown", reply_markup=earn_keyboard())

@bot.callback_query_handler(func=lambda c: c.data == "checkin")
def checkin(call):
    user = get_user(call.from_user.id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    if user.get('last_checkin') == today:
        bot.answer_callback_query(call.id, "Already checked in!", show_alert=True)
        return
    
    day = datetime.now().strftime("%A")
    reward = config_db["checkin_rewards"].get(day, 5)
    
    update_balance(call.from_user.id, reward)
    user['last_checkin'] = today
    
    bot.answer_callback_query(call.id, f"+{reward} coins!", show_alert=True)
    bot.send_message(call.message.chat.id, f"📅 {day}\n✅ +{reward} coins!")

@bot.callback_query_handler(func=lambda c: c.data == "ad")
def ad(call):
    user = get_user(call.from_user.id)
    
    if user.get('last_ad'):
        try:
            if (datetime.now() - datetime.fromisoformat(user['last_ad'])).seconds < 1800:
                bot.answer_callback_query(call.id, "Wait 30 mins!", show_alert=True)
                return
        except:
            pass
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📺 Watch", url="https://tithes101botads.blogspot.com/"))
    markup.add(types.InlineKeyboardButton("✅ Done", callback_data="ad_done"))
    bot.send_message(call.message.chat.id, "Watch ad to earn 5 coins:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "ad_done")
def ad_done(call):
    update_balance(call.from_user.id, 5)
    user = get_user(call.from_user.id)
    user['last_ad'] = datetime.now().isoformat()
    user['ads_watched'] += 1
    bot.answer_callback_query(call.id, "+5 coins!", show_alert=True)
    bot.edit_message_text("✅ +5 coins!", call.message.chat.id, call.message.message_id)

# ========== INVITE ==========
@bot.message_handler(func=lambda m: m.text == "👥 Invite")
def invite(message):
    info = bot.get_me()
    link = f"https://t.me/{info.username}?start=ref{message.from_user.id}"
    user = get_user(message.from_user.id)
    bot.send_message(message.chat.id, f"""╔══════════════════╗
    👥 INVITE
╚══════════════════╝

🔗 `{link}`
💰 Bonus: {config_db['invite_bonus']} coins
📊 Invites: {user.get('invite_count', 0)}""", parse_mode="Markdown")

# ========== REDEEM ==========
@bot.message_handler(func=lambda m: m.text == "🎟️ Redeem Code")
def redeem_prompt(message):
    msg = bot.reply_to(message, "Enter code:")
    bot.register_next_step_handler(msg, redeem)

def redeem(message):
    code = message.text.strip().upper()
    if code not in codes_db:
        bot.reply_to(message, "❌ Invalid!")
        return
    if codes_db[code].get('used'):
        bot.reply_to(message, "❌ Used!")
        return
    if str(message.from_user.id) in codes_db[code].get('used_by', []):
        bot.reply_to(message, "❌ Already used!")
        return
    
    update_balance(message.from_user.id, codes_db[code]['amount'])
    if codes_db[code].get('type') == 'single':
        codes_db[code]['used'] = True
    codes_db[code]['used_by'] = codes_db[code].get('used_by', []) + [str(message.from_user.id)]
    bot.reply_to(message, f"✅ +{codes_db[code]['amount']} coins!")

# ========== WITHDRAW ==========
@bot.message_handler(func=lambda m: m.text == "🏦 Withdraw")
def withdraw(message):
    user = get_user(message.from_user.id)
    cv = config_db["coin_value"]
    min_wd = config_db["min_withdraw"]
    peso = user['balance'] * cv / 100
    
    if peso < min_wd:
        bot.reply_to(message, f"❌ Min: ₱{min_wd}\nYou: ₱{peso:.2f}")
        return
    msg = bot.send_message(message.chat.id, f"Balance: ₱{peso:.2f}\nEnter amount:")
    bot.register_next_step_handler(msg, wd_amt)

def wd_amt(message):
    try:
        amt = float(message.text)
        cv = config_db["coin_value"]
        user = get_user(message.from_user.id)
        max_wd = user['balance'] * cv / 100
        
        if amt < config_db["min_withdraw"]:
            bot.reply_to(message, f"Min ₱{config_db['min_withdraw']}")
            return
        if amt > max_wd:
            bot.reply_to(message, f"Max ₱{max_wd:.2f}")
            return
        
        coins = int(amt / cv * 100)
        update_balance(message.from_user.id, -coins)
        
        msg = bot.send_message(message.chat.id, "Enter GCash/Maya number:")
        bot.register_next_step_handler(msg, save_wd, amt, coins)
    except:
        bot.reply_to(message, "Invalid!")

def save_wd(message, amt, coins):
    num = message.text.strip()
    w_id = str(int(datetime.now().timestamp()))
    withdrawals_db[w_id] = {
        "id": w_id,
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "amount_peso": amt,
        "amount_coins": coins,
        "number": num,
        "status": "pending"
    }
    bot.reply_to(message, f"✅ Request sent!\n₱{amt}\nWait for approval.")

# ========== STATS ==========
@bot.message_handler(func=lambda m: m.text == "📊 Stats")
def stats(message):
    user = get_user(message.from_user.id)
    cv = config_db["coin_value"]
    bot.send_message(message.chat.id, f"""╔══════════════════╗
      📊 STATS
╚══════════════════╝

💰 Balance: {user['balance']}
💵 Value: ₱{user['balance'] * cv / 100}
📈 Earned: {user['total_earned']}
🎮 Games: {user.get('games_played', 0)}
📺 Ads: {user.get('ads_watched', 0)}
👥 Invites: {user.get('invite_count', 0)}""")

# ========== ADMIN ==========
@bot.message_handler(func=lambda m: m.text == "📊 Dashboard" and m.from_user.id == ADMIN_ID)
def dash(message):
    total = sum(u['balance'] for u in users_db.values())
    pending = sum(1 for w in withdrawals_db.values() if w['status'] == 'pending')
    cv = config_db["coin_value"]
    bot.send_message(message.chat.id, f"""📊 DASHBOARD
👥 Users: {len(users_db)}
💰 Coins: {total}
💵 Value: ₱{total * cv / 100}
🏦 Pending: {pending}""")

@bot.message_handler(func=lambda m: m.text == "⚙️ Edit Settings" and m.from_user.id == ADMIN_ID)
def settings(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Sign-up", callback_data="ed_signup"),
        types.InlineKeyboardButton("Invite", callback_data="ed_invite"),
        types.InlineKeyboardButton("Coin Value", callback_data="ed_cv"),
        types.InlineKeyboardButton("Min WD", callback_data="ed_minwd"),
        types.InlineKeyboardButton("Win Rate", callback_data="ed_wr")
    )
    bot.send_message(message.chat.id, f"Sign-up: {config_db['signup_bonus']}\nInvite: {config_db['invite_bonus']}\nValue: {config_db['coin_value']}\nMin WD: {config_db['min_withdraw']}\nWin: {config_db['betting_win_rate']}%", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ed_") and c.from_user.id == ADMIN_ID)
def edit(call):
    keys = {"ed_signup": "signup_bonus", "ed_invite": "invite_bonus", "ed_cv": "coin_value", "ed_minwd": "min_withdraw", "ed_wr": "betting_win_rate"}
    key = keys[call.data]
    msg = bot.send_message(call.message.chat.id, f"New value for {key}:")
    bot.register_next_step_handler(msg, update, key)

def update(message, key):
    try:
        config_db[key] = float(message.text)
        bot.reply_to(message, f"✅ {key} = {config_db[key]}")
    except:
        bot.reply_to(message, "Invalid!")

@bot.message_handler(func=lambda m: m.text == "🏦 Pending WDs" and m.from_user.id == ADMIN_ID)
def wds(message):
    pending = {k: v for k, v in withdrawals_db.items() if v['status'] == 'pending'}
    if not pending:
        bot.reply_to(message, "No pending!")
        return
    for w_id, w in list(pending.items())[:5]:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Approve", callback_data=f"wda_{w_id}"),
            types.InlineKeyboardButton("❌ Reject", callback_data=f"wdr_{w_id}")
        )
        bot.send_message(message.chat.id, f"ID: {w_id}\nUser: {w['username']}\n₱{w['amount_peso']}\n{w['number']}", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("wd") and c.from_user.id == ADMIN_ID)
def handle_wd(call):
    w_id = call.data.split("_")[1]
    if call.data.startswith("wda_"):
        withdrawals_db[w_id]['status'] = 'approved'
        bot.edit_message_text(f"✅ Approved #{w_id}", call.message.chat.id, call.message.message_id)
    else:
        withdrawals_db[w_id]['status'] = 'rejected'
        update_balance(withdrawals_db[w_id]['user_id'], withdrawals_db[w_id]['amount_coins'])
        bot.edit_message_text(f"❌ Rejected #{w_id}", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: m.text == "🎟️ Create Code" and m.from_user.id == ADMIN_ID)
def create_code(message):
    msg = bot.send_message(message.chat.id, "Format: AMOUNT-TYPE\nExample: 100-single")
    bot.register_next_step_handler(msg, make_code)

def make_code(message):
    try:
        parts = message.text.split("-")
        amt = int(parts[0])
        ctype = parts[1] if len(parts) > 1 else "single"
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        codes_db[code] = {"amount": amt, "type": ctype, "used": False, "used_by": []}
        bot.reply_to(message, f"✅ Code: `{code}`\nAmount: {amt}\nType: {ctype}", parse_mode="Markdown")
    except:
        bot.reply_to(message, "Invalid!")

@bot.message_handler(func=lambda m: m.text == "💰 Add Bonus" and m.from_user.id == ADMIN_ID)
def bonus_prompt(message):
    msg = bot.send_message(message.chat.id, "Format: USER_ID-AMOUNT")
    bot.register_next_step_handler(msg, bonus)

def bonus(message):
    try:
        parts = message.text.split("-")
        uid = int(parts[0])
        amt = int(parts[1])
        update_balance(uid, amt)
        bot.reply_to(message, f"✅ +{amt} to {uid}")
    except:
        bot.reply_to(message, "Invalid!")

@bot.message_handler(func=lambda m: m.text == "👥 User List" and m.from_user.id == ADMIN_ID)
def users_list(message):
    sorted_users = sorted(users_db.items(), key=lambda x: x[1]['balance'], reverse=True)[:20]
    text = "👥 TOP 20\n\n"
    for i, (uid, u) in enumerate(sorted_users, 1):
        text += f"{i}. {u['first_name']} - {u['balance']} coins\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast" and m.from_user.id == ADMIN_ID)
def bc_prompt(message):
    msg = bot.send_message(message.chat.id, "Enter message:")
    bot.register_next_step_handler(msg, bc)

def bc(message):
    count = 0
    for uid in users_db:
        try:
            bot.send_message(int(uid), f"📢 {message.text}")
            count += 1
        except:
            pass
    bot.reply_to(message, f"✅ Sent to {count} users!")

@bot.message_handler(func=lambda m: m.text == "🔙 User Mode" and m.from_user.id == ADMIN_ID)
def user_mode(message):
    bot.send_message(message.chat.id, "User Mode", reply_markup=main_keyboard())

@bot.callback_query_handler(func=lambda c: c.data == "back")
def back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Main Menu:", reply_markup=main_keyboard())

# ========== VERCEL WEBHOOK ==========
@app.route('/')
def home():
    return "Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Bad Request', 403
