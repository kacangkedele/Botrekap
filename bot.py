import telebot
from telebot import types
import re
import json
import os
import time
from datetime import datetime, timedelta

# ============== KONFIGURASI ==============
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Ganti dengan token bot Anda
ADMIN_IDS = [123456789]  # Ganti dengan ID Telegram Anda
MIN_MEMBER_PREMIUM = 5
QRIS_PHOTO_PATH = "qris.png"  # Pastikan file qris.png ada di folder yang sama

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# Set Menu Bawaan Telegram
bot.set_my_commands([
    telebot.types.BotCommand("start", "Memulai Bot & Panduan"),
    telebot.types.BotCommand("rekap", "Rekap List (Tanpa Tombol)"),
    telebot.types.BotCommand("win", "Rekap Win Dengan Parameter"),
    telebot.types.BotCommand("winrekap", "Mendapatkan Data Rekap"),
    telebot.types.BotCommand("geser", "Pindahkan Saldo Pemain"),
    telebot.types.BotCommand("resetlw", "Reset History Game"),
    telebot.types.BotCommand("lunas", "Lunasi Hutang Pemain"),
    telebot.types.BotCommand("tambah", "Tambah Saldo Pemain"),
    telebot.types.BotCommand("kurangi", "Kurangi Saldo Pemain"),
    telebot.types.BotCommand("depo", "Deposit Saldo Pemain"),
    telebot.types.BotCommand("del", "Hapus Pemain dari LW"),
    telebot.types.BotCommand("wd", "Cek Saldo Pemain"),
    telebot.types.BotCommand("bulatkan", "Bulatkan Saldo ke 100"),
    telebot.types.BotCommand("id", "Cek ID Grup"),
    telebot.types.BotCommand("sewa", "Beli Akses Premium Bot"),
    telebot.types.BotCommand("upgrade", "Aktivasi Premium Grup (Admin)"),
    telebot.types.BotCommand("antilink", "Aktifkan Anti Link"),
    telebot.types.BotCommand("antiforward", "Aktifkan Anti Forward")
])

# Fungsi aman untuk membalas pesan agar tidak error 400
def safe_reply(message, text, **kwargs):
    try:
        return bot.reply_to(message, text, **kwargs)
    except:
        try:
            return bot.send_message(message.chat.id, text, **kwargs)
        except Exception as e:
            print(f"Failed to send message: {e}")

# Fungsi Auto Fee menggunakan Rumus Matematika
def get_auto_fee(amount):
    if amount <= 0: return 0
    if amount <= 7: return 1
    if amount <= 20: return 2
    return (amount - 1) // 10 + 1

SEWA_PRICES = {
    "1": {"price": 1000, "text": "1 Hari"},
    "3": {"price": 2500, "text": "3 Hari"},
    "7": {"price": 5000, "text": "7 Hari"},
    "14": {"price": 8000, "text": "14 Hari"},
    "30": {"price": 15000, "text": "30 Hari"}
}

# ============== STORAGE ==============
STATE_FILE = "bot_state.json"
data_store = {
    "balances": {}, "browser": None, "device": None, "wd_time": None,
    "pending_rekap": {}, "premium_groups": {}, 
    "chat_settings": {}, "pending_payment": {},
    "last_win_chat_id": None, "last_win_msg_id": None, "last_win_data": None,
    "total_fee": 0
}

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                data_store.update(saved)
        except: pass

def save_state():
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_store, f, indent=2, ensure_ascii=False)
    except: pass

load_state()

# ============== HELPER ==============
def is_premium(chat_id):
    cid = str(chat_id)
    if cid not in data_store["premium_groups"]: return False
    expiry = data_store["premium_groups"][cid]
    if expiry == 0: return True
    if time.time() < expiry: return True
    del data_store["premium_groups"][cid]
    save_state()
    return False

def is_user_admin(chat_id, user_id):
    if user_id in ADMIN_IDS: return True
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

def get_chat_setting(chat_id, key, default=False):
    cid = str(chat_id)
    if cid not in data_store["chat_settings"]:
        data_store["chat_settings"][cid] = {}
    return data_store["chat_settings"][cid].get(key, default)

def set_chat_setting(chat_id, key, value):
    cid = str(chat_id)
    if cid not in data_store["chat_settings"]:
        data_store["chat_settings"][cid] = {}
    data_store["chat_settings"][cid][key] = value
    save_state()

def fmt_num(n):
    try: return f"{int(n):,}".replace(",", ".")
    except: return str(n)

def bulatkan_ke_kelipatan(n, kelipatan=100):
    return int(round(n / kelipatan) * kelipatan)

def try_pin_message(chat_id, message_id):
    try: bot.pin_chat_message(chat_id, message_id, disable_notification=True)
    except: pass

def get_balance_nick(nickname):
    for bal_nick in data_store["balances"].keys():
        if bal_nick.lower() == nickname.lower():
            return bal_nick
    return nickname

def render_lw_output(lw_data, balances):
    months = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    now = datetime.now()
    date_str = f"{now.day} {months[now.month-1]} {now.year}"
    time_str = now.strftime("%H.%M WIB")
    
    total_saldo = sum(v for v in balances.values() if v > 0)
    win_lines, lose_lines = [], []
    for nick, saldo in balances.items():
        if saldo > 0:
            win_lines.append(f"*{nick}* {fmt_num(saldo)}")
        elif saldo < 0:
            lose_lines.append(f"*{nick}* -{fmt_num(abs(saldo))}")
            
    output = f"*📱DEV: {lw_data['device']}*\n"
    output += f"*⌚️WD: {lw_data.get('wd_time', 'Belum diatur')} 🔰*\n"
    output += f"*📝DATE : {date_str}*\n"
    output += f"*⏰️TIME : {time_str}*\n"
    output += f"*🌐ROL: {lw_data['browser']}*\n\n"
    output += f"*LAST WIN : (@{lw_data['username']})*\n"
    
    games = lw_data.get('games', [])
    for i, game in enumerate(games):
        output += f"*GAME {i+1} : {game['winner']} {game['score']} {fmt_num(game['modal'])}*\n"
        
    output += f"\n*💰SALDO PEMAIN : ({fmt_num(total_saldo)})*\n"
    if win_lines:
        output += "\n".join(win_lines)
    else:
        output += "Tidak ada saldo"
        
    output += f"\n\n*🔰SALDO PENGUTANG -🚫*\n"
    if lose_lines:
        output += "\n".join(lose_lines)
    else:
        output += "Tidak ada pengutang"
        
    return output

def update_last_win_message():
    chat_id = data_store.get("last_win_chat_id")
    msg_id = data_store.get("last_win_msg_id")
    lw_data = data_store.get("last_win_data")
    
    if not chat_id or not msg_id or not lw_data: return
        
    output = render_lw_output(lw_data, data_store["balances"])
    try:
        bot.edit_message_text(output, chat_id=chat_id, message_id=msg_id, parse_mode="Markdown")
    except: pass

# ============== PARSER ==============
def parse_duel_data(text):
    teams = {"KECIL": [], "BESAR": []}
    current_team = None
    
    for match in re.finditer(r'\b(K|B)\b[\s:.\-]*\[?([\d\s,]+)\]?\s*=\s*(\d+)', text, re.IGNORECASE):
        team_char = match.group(1).upper()
        team_name = "KECIL" if team_char.startswith("K") else "BESAR"
        total = int(match.group(3))
        if total == 0:
            nums = [int(x.strip()) for x in match.group(2).split(',') if x.strip().isdigit()]
            total = sum(nums)
        teams[team_name].append({"nickname": f"TIM {team_char}", "modal": total, "result": None, "is_lf": False})
        
    if teams["KECIL"] or teams["BESAR"]:
        return teams
        
    for raw_line in text.split('\n'):
        line = raw_line.strip()
        if not line: continue
            
        match_header = re.match(r'^(K|B|KECIL|BESAR)\b[\s:.\-]*(.*)', line, re.IGNORECASE)
        if match_header:
            team_char = match_header.group(1).upper()
            current_team = "KECIL" if team_char.startswith("K") else "BESAR"
            rest = match_header.group(2).strip()
            if rest and not rest.startswith("-"):
                parse_player_line(rest, current_team, teams)
            continue
            
        if current_team:
            parse_player_line(line, current_team, teams)
            
    for team_name in ["KECIL", "BESAR"]:
        merged = {}
        for p in teams[team_name]:
            nick_lower = p["nickname"].lower()
            if nick_lower in merged:
                merged[nick_lower]["modal"] += p["modal"]
                if p["result"] is not None:
                    if merged[nick_lower]["result"] is None: merged[nick_lower]["result"] = 0
                    merged[nick_lower]["result"] += p["result"]
                if p["is_lf"]: merged[nick_lower]["is_lf"] = True
            else:
                p["lower"] = nick_lower
                merged[nick_lower] = p
        
        teams[team_name] = [{
            "nickname": p["nickname"],
            "modal": p["modal"],
            "result": p["result"],
            "is_lf": p["is_lf"]
        } for p in merged.values()]
        
    return teams

def parse_player_line(line, team, teams):
    line = line.strip()
    if not line: return
    
    if "//" in line:
        parts = line.split("//", 1)
        left_part = parts[0].strip()
        right_part = parts[1].strip() if len(parts) > 1 else ""
    else:
        left_part = line
        right_part = ""

    is_lf = False
    
    if right_part:
        right_tokens = right_part.split()
        if right_tokens and right_tokens[-1].upper() in ("LF", "P"):
            is_lf = True
            right_tokens = right_tokens[:-1]
        right_part = " ".join(right_tokens)
        
    if left_part:
        left_tokens = left_part.split()
        if left_tokens and left_tokens[-1].upper() in ("LF", "P"):
            is_lf = True
            left_tokens = left_tokens[:-1]
    else:
        left_tokens = []

    if len(left_tokens) < 2: return
    try: 
        modal = int(left_tokens[-1].replace(".", "").replace(",", ""))
    except: 
        return

    nickname = " ".join(left_tokens[:-1]).strip()
    if not nickname or re.search(r'\d', nickname): return

    result = None
    if right_part:
        try: 
            result = int(right_part.replace(".", "").replace(",", "").split()[0])
        except: 
            result = None

    teams[team].append({"nickname": nickname, "modal": modal, "result": result, "is_lf": is_lf})

# ============== KEYBOARDS ==============
def winner_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("KECIL", callback_data="rw_win_KECIL"), types.InlineKeyboardButton("BESAR", callback_data="rw_win_BESAR"))
    return kb

def score_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("2 - 0", callback_data="rw_score_2-0"), types.InlineKeyboardButton("2 - 1", callback_data="rw_score_2-1"))
    kb.add(types.InlineKeyboardButton("⬅️ Kembali", callback_data="rw_back_score"))
    return kb

def browser_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    btns = [types.InlineKeyboardButton(b, callback_data=f"rw_browser_{b}") for b in ["Chrome", "Google", "Safari", "Firefox", "Edge", "Opera"]]
    kb.add(*btns)
    kb.add(types.InlineKeyboardButton("⬅️ Kembali", callback_data="rw_back_browser"))
    return kb

def sewa_main_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("1 Hari (1K)", callback_data="sewa_1"),
        types.InlineKeyboardButton("3 Hari (2.5K)", callback_data="sewa_3"),
        types.InlineKeyboardButton("7 Hari (5K)", callback_data="sewa_7"),
        types.InlineKeyboardButton("14 Hari (8K)", callback_data="sewa_14"),
        types.InlineKeyboardButton("30 Hari (15K)", callback_data="sewa_30"),
        types.InlineKeyboardButton("Cek Status", callback_data="sewa_cek")
    )
    return kb

# ============== /winrekap (Laporan Rekapitulasi) ==============
@bot.message_handler(commands=['winrekap'])
def cmd_winrekap(message):
    lw_data = data_store.get("last_win_data")
    if not lw_data:
        return safe_reply(message, "❌ Belum ada data Last Win yang aktif.")
        
    months = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    now = datetime.now()
    date_str = f"{now.day} {months[now.month-1]} {now.year}"
    
    games = lw_data.get('games', [])
    rincian_bl = [str(game['modal']) for game in games]
    total_games = len(games)
    total_bl = sum(game['modal'] for game in games)
    total_fee = data_store.get("total_fee", 0)
    username = lw_data.get('username', 'None')
    
    output = (
        f"📅 {date_str}\n"
        f"👤 Users: {username}\n"
        f"📊 Rincian BL: [{', '.join(rincian_bl)}]\n"
        f"🎮 Total Game: {total_games} Game\n"
        f"💰 Total BL: {fmt_num(total_bl)}\n"
        f"💵 Total Keuntungan Fee (Belum termasuk pajak aplikasi): {fmt_num(total_fee)}"
    )
    
    safe_reply(message, output)

# ============== /rekap (Tanpa Tombol) & /rekapwin /win (Dengan Tombol) ==============
@bot.message_handler(commands=['rekapwin', 'rekap', 'win'])
def cmd_rekap(message):
    chat_id = message.chat.id
    user = message.from_user
    parts = message.text.split()
    if not parts: return
    cmd = parts[0].split('@')[0][1:].lower()

    if message.chat.type not in ("group", "supergroup"):
        return safe_reply(message, "❌ Command ini hanya untuk grup.")

    if not is_user_admin(chat_id, user.id):
        return safe_reply(message, "❌ Maaf, perintah ini hanya bisa digunakan oleh Admin Grup.")

    if not is_premium(chat_id):
        try: member_count = bot.get_chat_member_count(chat_id)
        except: member_count = 0
        if member_count < MIN_MEMBER_PREMIUM:
            return safe_reply(message, f"❌ Fitur ini membutuhkan akses premium.\nGunakan /sewa untuk mendapatkan akses premium.")

    if not message.reply_to_message:
        return safe_reply(message, "❌ Balas pesan data duel, lalu kirim /win [fee]")

    src = message.reply_to_message.text
    if not src:
        return safe_reply(message, "❌ Pesan yang dibalas bukan teks data duel.")

    teams = parse_duel_data(src)
    if not teams["KECIL"] and not teams["BESAR"]:
        return safe_reply(message, "❌ Format K/B tidak lengkap.")

    fee = 0.0
    auto_fee = False
    
    if cmd in ['win', 'rekapwin']:
        auto_fee = True
    elif len(parts) > 1:
        try: 
            fee = float(parts[1].replace(",", "."))
        except: 
            pass
    else:
        auto_fee = True

    summary = render_duel_summary(teams, fee, auto_fee)
    show_buttons = cmd in ['rekapwin', 'win']
    
    if show_buttons:
        key = f"{chat_id}:{user.id}"
        data_store["pending_rekap"][key] = {
            "teams": teams, "fee": fee, "auto_fee": auto_fee, "winner": None, "score": None,
            "browser": None, "device": None, "wd_time": None,
            "chat_id": chat_id, "user_id": user.id,
            "username": user.username or user.first_name, "step": "winner",
        }
        save_state()
        safe_reply(message, f"📊 *DATA DUEL DITERIMA*\n\n{summary}\n\n👉 *Pilih tim pemenang:*", parse_mode="Markdown", reply_markup=winner_keyboard())
    else:
        safe_reply(message, f"📊 *DATA DUEL DITERIMA*\n\n{summary}", parse_mode="Markdown")

def render_duel_summary(teams, fee, auto_fee=False):
    k_total = sum(p["modal"] for p in teams["KECIL"])
    b_total = sum(p["modal"] for p in teams["BESAR"])
    
    k_modals = [str(p["modal"]) for p in teams["KECIL"]]
    b_modals = [str(p["modal"]) for p in teams["BESAR"]]
    
    lines = []
    lines.append(f"*🔵 K: [{','.join(k_modals)}] = {k_total}*")
    lines.append("")
    lines.append(f"*🔵 B: [{','.join(b_modals)}] = {b_total}*")
    lines.append("")
    
    if k_total > b_total:
        diff = k_total - b_total
        lines.append(f"*🐠 B masih kekurangan {diff} untuk menyamai K.*")
        lines.append("")
        lines.append(f"*💰 Saldo Anda seharusnya: {k_total + b_total} K*")
        lines.append("")
        lines.append(f"*B -{diff} ALL // ECER*")
    elif b_total > k_total:
        diff = b_total - k_total
        lines.append(f"*🐠 K masih kekurangan {diff} untuk menyamai B.*")
        lines.append("")
        lines.append(f"*💰 Saldo Anda seharusnya: {k_total + b_total} K*")
        lines.append("")
        lines.append(f"*K -{diff} ALL // ECER*")
    else:
        lines.append(f"*💰 Saldo Anda seharusnya: {k_total + b_total} K*")
        lines.append("")
        lines.append("*CEK NAMA + NOMINAL MASING²*")
        lines.append("*KALAU UDAH MAEN BARU*")
        lines.append("*PROTES BRRTI HANGUS*")
        lines.append("")
        lines.append("*(JEMPOL = AMAN)*")
        
    if auto_fee:
        lines.append("")
        lines.append("*💸 Fee: AUTO (Tabel Otomatis)*")
    elif fee > 0:
        lines.append("")
        lines.append(f"*💸 Fee: {fee}%*")
        
    return "\n".join(lines)

# ============== CALLBACK REKAP ==============
@bot.callback_query_handler(func=lambda c: c.data.startswith("rw_win_"))
def cb_winner(call):
    key = f"{call.message.chat.id}:{call.from_user.id}"
    pr = data_store["pending_rekap"].get(key)
    if not pr: return bot.answer_callback_query(call.id, "Sesi tidak ditemukan. Ulangi /win")
    pr["winner"] = call.data.split("rw_win_")[1]
    pr["step"] = "score"
    save_state()
    bot.edit_message_text(f"Tim *{pr['winner'][0]}* menang dengan skor:\nPilih skor:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=score_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rw_score_"))
def cb_score(call):
    key = f"{call.message.chat.id}:{call.from_user.id}"
    pr = data_store["pending_rekap"].get(key)
    if not pr: return
    pr["score"] = call.data.split("rw_score_")[1]
    chat_id = call.message.chat.id
    browser = data_store.get("browser")
    device = data_store.get("device")
    wd_time = data_store.get("wd_time")
    
    if browser and device and wd_time:
        pr["browser"], pr["device"], pr["wd_time"], pr["step"] = browser, device, wd_time, "done"
        save_state()
        bot.edit_message_text(f"✅ Skor: {pr['score']}\n🌐 Browser: {browser}\n📱 Device: {device}\n⌚️ WD: {wd_time}\n\n⏳ Memproses...", chat_id=chat_id, message_id=call.message.message_id)
        finalize_rekap(pr, chat_id)
    else:
        if not browser:
            pr["step"] = "browser"
            save_state()
            bot.edit_message_text("Pilih browser yang digunakan:", chat_id=chat_id, message_id=call.message.message_id, reply_markup=browser_keyboard())
        elif not device:
            pr["step"] = "device"
            save_state()
            bot.edit_message_text(f"✅ Skor: {pr['score']}\n🌐 Browser: {browser}\n\n📱 Masukkan nama device (contoh: IPHONE 14):", chat_id=chat_id, message_id=call.message.message_id)
        elif not wd_time:
            pr["step"] = "wd_time"
            save_state()
            bot.edit_message_text(f"✅ Skor: {pr['score']}\n🌐 Browser: {browser}\n📱 Device: {device}\n\n⌚️ Masukkan waktu WD (contoh: 22.00 WIB):", chat_id=chat_id, message_id=call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rw_browser_"))
def cb_browser(call):
    key = f"{call.message.chat.id}:{call.from_user.id}"
    pr = data_store["pending_rekap"].get(key)
    if not pr: return
    browser = call.data.split("rw_browser_")[1]
    pr["browser"] = browser
    data_store["browser"] = browser
    save_state()
    
    device = data_store.get("device")
    wd_time = data_store.get("wd_time")
    
    if device and wd_time:
        pr["device"], pr["wd_time"], pr["step"] = device, wd_time, "done"
        save_state()
        bot.edit_message_text(f"✅ Skor: {pr['score']}\n🌐 Browser: {browser}\n📱 Device: {device}\n⌚️ WD: {wd_time}\n\n⏳ Memproses...", chat_id=call.message.chat.id, message_id=call.message.message_id)
        finalize_rekap(pr, call.message.chat.id)
    elif not device:
        pr["step"] = "device"
        save_state()
        bot.edit_message_text(f"✅ Skor: {pr['score']}\n🌐 Browser: {browser}\n\n📱 Masukkan nama device (contoh: IPHONE 14):", chat_id=call.message.chat.id, message_id=call.message.message_id)
    elif not wd_time:
        pr["step"] = "wd_time"
        save_state()
        bot.edit_message_text(f"✅ Skor: {pr['score']}\n🌐 Browser: {browser}\n📱 Device: {device}\n\n⌚️ Masukkan waktu WD (contoh: 22.00 WIB):", chat_id=call.message.chat.id, message_id=call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "rw_back_score")
def cb_back_score(call):
    key = f"{call.message.chat.id}:{call.from_user.id}"
    pr = data_store["pending_rekap"].get(key)
    if not pr: return
    pr["step"] = "winner"
    save_state()
    bot.edit_message_text("👉 *Pilih tim pemenang:*", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=winner_keyboard())

@bot.callback_query_handler(func=lambda c: c.data == "rw_back_browser")
def cb_back_browser(call):
    key = f"{call.message.chat.id}:{call.from_user.id}"
    pr = data_store["pending_rekap"].get(key)
    if not pr: return
    pr["step"] = "score"
    save_state()
    bot.edit_message_text(f"Tim *{pr['winner'][0]}* menang dengan skor:\nPilih skor:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=score_keyboard())

# ============== HITUNG OTOMATIS ==============
def finalize_rekap(pr, chat_id):
    teams = pr["teams"]
    winner = pr["winner"]
    score = pr["score"]
    fee_pct = pr["fee"]
    auto_fee = pr.get("auto_fee", False)
    
    loser = "BESAR" if winner == "KECIL" else "KECIL"
    
    winner_modal = sum(p["modal"] for p in teams[winner])
    loser_modal = sum(p["modal"] for p in teams[loser])
    
    total_fee_this_game = 0

    for team_name in [winner, loser]:
        for p in teams[team_name]:
            nick_target = get_balance_nick(p["nickname"])
            current = data_store["balances"].get(nick_target, 0)
            fee_dipotong = 0
            
            if p["is_lf"]:
                p_mult = 1.0
            else:
                p_mult = 2.0
            
            if p["result"] is not None:
                total_masuk = p["result"]
            else:
                if team_name == winner:
                    share = int(loser_modal * p_mult * (p["modal"] / winner_modal)) if winner_modal > 0 else 0
                    total_masuk = p["modal"] + share
                else:
                    total_masuk = 0
                    
            if total_masuk > 0:
                if auto_fee:
                    fee_dipotong = get_auto_fee(total_masuk)
                    net_masuk = total_masuk - fee_dipotong
                elif fee_pct > 0:
                    fee_dipotong = int(total_masuk * (fee_pct/100))
                    net_masuk = int(total_masuk * (1 - fee_pct/100))
                else:
                    net_masuk = total_masuk
            else:
                net_masuk = 0
                
            total_fee_this_game += fee_dipotong
            net = net_masuk - p["modal"]
            data_store["balances"][nick_target] = current + net

    data_store["total_fee"] = data_store.get("total_fee", 0) + total_fee_this_game
    
    # LOGIKA PENYIMPANAN LW YANG DIPERBAIKI
    lw_data = data_store.get("last_win_data")
    
    if not lw_data or data_store.get("last_win_chat_id") != chat_id:
        # Buat data LW baru jika tidak ada atau chat id berbeda
        lw_data = {
            "device": pr['device'],
            "browser": pr['browser'],
            "wd_time": pr.get('wd_time'),
            "username": pr['username'],
            "games": []
        }
        data_store["last_win_data"] = lw_data
        data_store["last_win_chat_id"] = chat_id
    else:
        # Update data device/browser/wd_time/username jika sudah ada
        lw_data["device"] = pr['device']
        lw_data["browser"] = pr['browser']
        lw_data["wd_time"] = pr.get('wd_time')
        lw_data["username"] = pr['username']
        
    # Tambahkan game saat ini ke daftar games
    lw_data["games"].append({
        "winner": winner[0],
        "score": score,
        "modal": loser_modal
    })
    
    save_state()

    output = render_lw_output(lw_data, data_store["balances"])

    total_games = len(lw_data['games'])
    bot.send_message(chat_id, f"✅ *Rekapwin selesai. Total Game: {total_games}*", parse_mode="Markdown")
    sent = bot.send_message(chat_id, output, parse_mode="Markdown")
    try_pin_message(chat_id, sent.message_id)
    data_store["last_win_msg_id"] = sent.message_id
    save_state()

    if f"{chat_id}:{pr['user_id']}" in data_store["pending_rekap"]:
        del data_store["pending_rekap"][f"{chat_id}:{pr['user_id']}"]
    save_state()

# ============== FITUR TAMBAHAN ==============
@bot.message_handler(commands=['id'])
def cmd_id(message):
    chat_id = message.chat.id
    safe_reply(message, f"🆔 ID Grup ini adalah: `{chat_id}`", parse_mode="Markdown")

@bot.message_handler(commands=['resetlw', 'geser', 'del', 'lunas', 'tambah', 'kurangi', 'depo', 'wd', 'bulatkan'])
def cmd_saldo_actions(message):
    try:
        chat_id = message.chat.id
        user = message.from_user
        
        if not is_user_admin(chat_id, user.id):
            return safe_reply(message, "⚠️Hanya Admin Group yang bisa menggunakan Perintah ini🚫")

        parts = message.text.split()
        if not parts: return
        cmd = parts[0].split('@')[0][1:].lower()
        
        if cmd == 'geser':
            if len(parts) < 4:
                return safe_reply(message, "❌ Format: /geser [dari_user] [jumlah] [ke_user]")
            
            from_nick_input = parts[1].strip()
            try:
                amt = int(parts[2].replace(".", ""))
            except:
                return safe_reply(message, "❌ Jumlah tidak valid.")
            to_nick_input = parts[3].strip()
            
            from_nick = get_balance_nick(from_nick_input)
            to_nick = get_balance_nick(to_nick_input)
            
            if from_nick not in data_store["balances"]:
                return safe_reply(message, f"❌ Pemain {from_nick_input} tidak ditemukan.")
                
            if data_store["balances"][from_nick] < amt:
                return safe_reply(message, f"❌ Saldo {from_nick} tidak cukup. Saldo saat ini: {fmt_num(data_store['balances'][from_nick])}")
                
            data_store["balances"][from_nick] -= amt
            if to_nick not in data_store["balances"]:
                data_store["balances"][to_nick] = 0
            data_store["balances"][to_nick] += amt
            
            save_state()
            update_last_win_message()
            return safe_reply(message, f"✅ Berhasil memindahkan saldo {fmt_num(amt)} dari {from_nick} ke {to_nick}.")
            
        if cmd == 'del':
            if len(parts) < 2:
                return safe_reply(message, "❌ Format: /del [username]")
            
            nick_input = parts[1].strip()
            nick_target = get_balance_nick(nick_input)
            
            if nick_target not in data_store["balances"]:
                return safe_reply(message, "❌ Pemain tidak ditemukan.")
                
            del data_store["balances"][nick_target]
            save_state()
            update_last_win_message()
            return safe_reply(message, f"🗑️ Pemain {nick_target} berhasil dihapus dari daftar saldo LW.")
            
        if cmd == 'resetlw':
            data_store["balances"] = {}
            data_store["last_win_msg_id"] = None
            data_store["last_win_chat_id"] = None
            data_store["last_win_data"] = None
            data_store["device"] = None
            data_store["browser"] = None
            data_store["wd_time"] = None
            data_store["total_fee"] = 0
            save_state()
            return safe_reply(message, "✅ History direset. Dev, ROL, WD & Total Fee akan diperbarui saat rekapwin berikutnya.")
            
        if cmd == 'bulatkan':
            if not data_store["balances"]: return safe_reply(message, "❌ Tidak ada saldo.")
            changes = []
            for n, val in data_store["balances"].items():
                new = bulatkan_ke_kelipatan(val, 100)
                if new != val:
                    changes.append(f"👤 {n}: {fmt_num(val)} → {fmt_num(new)}")
                    data_store["balances"][n] = new
            msg_text = "🔁 Pembulatan:\n" + "\n".join(changes) + f"\n\n📟 Oleh: @{user.username or user.first_name}" if changes else "✅ Semua saldo sudah bulat."
            save_state()
            bot.send_message(message.chat.id, msg_text)
            update_last_win_message()
            return

        if cmd not in ['lunas', 'wd', 'tambah', 'kurangi', 'depo']: return

        if cmd in ['lunas', 'wd'] and len(parts) < 2: 
            return safe_reply(message, f"❌ Format: /{cmd} [username]")
        if cmd in ['tambah', 'kurangi', 'depo'] and len(parts) < 3: 
            return safe_reply(message, f"❌ Format: /{cmd} [username] [jumlah]")

        nick_input = parts[1].strip()
        nick_target = get_balance_nick(nick_input)
        
        amt = 0
        if cmd in ['tambah', 'kurangi', 'depo']:
            try: amt = int(parts[2].replace(".", ""))
            except: return safe_reply(message, "❌ Jumlah tidak valid.")
        
        if cmd == 'lunas':
            if nick_target not in data_store["balances"]: return safe_reply(message, "❌ Pemain tidak ditemukan.")
            old = data_store["balances"][nick_target]
            data_store["balances"][nick_target] = 0
            msg_text = f"✅ Hutang dilunasi.\n👤 {nick_target}: {fmt_num(old)} → 0\n📟 Oleh: @{user.username or user.first_name}"
            
        elif cmd in ['tambah', 'depo']:
            if nick_target not in data_store["balances"]:
                nick_target = nick_input 
            old = data_store["balances"].get(nick_target, 0)
            data_store["balances"][nick_target] = old + amt
            if cmd == 'depo':
                msg_text = f"✅ Saldo {nick_target.upper()} berhasil didepo {fmt_num(amt)}."
            else:
                msg_text = f"➕ Saldo ditambah.\n👤 {nick_target}: {fmt_num(old)} → {fmt_num(data_store['balances'][nick_target])}\n📟 Oleh: @{user.username or user.first_name}"
            
        elif cmd == 'kurangi':
            if nick_target not in data_store["balances"]: return safe_reply(message, "❌ Pemain tidak ditemukan.")
            old = data_store["balances"][nick_target]
            data_store["balances"][nick_target] = old - amt
            msg_text = f"➖ Saldo dikurangi.\n👤 {nick_target}: {fmt_num(old)} → {fmt_num(data_store['balances'][nick_target])}\n📟 Oleh: @{user.username or user.first_name}"
            
        elif cmd == 'wd':
            if nick_target not in data_store["balances"]: return safe_reply(message, "❌ Pemain tidak ditemukan.")
            saldo = data_store["balances"].get(nick_target, 0)
            msg_text = f"💳 Saldo {nick_target}: {fmt_num(saldo)}" if saldo > 0 else (f"⚠️ Hutang {nick_target}: {fmt_num(abs(saldo))}" if saldo < 0 else f"❌ {nick_target} tidak punya saldo.")
            return safe_reply(message, msg_text)

        save_state()
        bot.send_message(message.chat.id, msg_text)
        update_last_win_message()
    except Exception as e:
        print(f"Error di saldo actions: {e}")

# ============== FITUR ANTI LINK & FORWARD ==============
@bot.message_handler(commands=['antilink'])
def cmd_antilink(message):
    chat_id = message.chat.id
    if not is_user_admin(chat_id, message.from_user.id):
        return safe_reply(message, "⚠️Hanya Admin Group yang bisa menggunakan Perintah ini🚫")
    
    current = get_chat_setting(chat_id, "antilink", False)
    set_chat_setting(chat_id, "antilink", not current)
    status = "AKTIF ✅" if not current else "NONAKTIF ❌"
    safe_reply(message, f"🛡️ Anti-Link sekarang *{status}*.", parse_mode="Markdown")

@bot.message_handler(commands=['antiforward'])
def cmd_antiforward(message):
    chat_id = message.chat.id
    if not is_user_admin(chat_id, message.from_user.id):
        return safe_reply(message, "⚠️Hanya Admin Group yang bisa menggunakan Perintah ini🚫")
    
    current = get_chat_setting(chat_id, "antiforward", False)
    set_chat_setting(chat_id, "antiforward", not current)
    status = "AKTIF ✅" if not current else "NONAKTIF ❌"
    safe_reply(message, f"🛡️ Anti-Forward sekarang *{status}*.", parse_mode="Markdown")

# ============== FITUR SEWA ==============
@bot.message_handler(commands=['sewa'])
def cmd_sewa(message):
    text = (
        "👑 *SEWA BOT REKAPWIN*\n\n"
        "Untuk menggunakan bot tanpa batas, silakan sewa bot.\n\n"
        "📋 *Daftar Harga:*\n"
        "• 1 Hari : Rp 1.000\n• 3 Hari : Rp 2.500\n• 7 Hari : Rp 5.000\n• 14 Hari : Rp 8.000\n• 30 Hari : Rp 15.000\n\n"
        "Silakan pilih durasi sewa di bawah ini:"
    )
    safe_reply(message, text, parse_mode="Markdown", reply_markup=sewa_main_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("sewa_"))
def cb_sewa(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    cid = str(chat_id)
    
    if call.data == "sewa_cek":
        if cid in data_store["premium_groups"]:
            exp = data_store["premium_groups"][cid]
            if exp == 0: text = "📊 Status: *PERMANEN*"
            else:
                remaining = int((exp - time.time()) / 86400)
                text = f"📊 Status: *AKTIF*\nSisa masa aktif: {remaining} hari" if remaining > 0 else "📊 Status: *EXPIRED*"
        else:
            text = "📊 Status: *BELUM AKTIF*"
        bot.answer_callback_query(call.id)
        return bot.send_message(chat_id, text, parse_mode="Markdown")

    days_str = call.data.split("_")[1]
    if days_str not in SEWA_PRICES: return
    
    data = SEWA_PRICES[days_str]
    days = int(days_str)
    price = data["price"]
    
    admin_fee = int(price * 0.027)
    total = price + admin_fee
    
    data_store["pending_payment"][str(user_id)] = {
        "chat_id": chat_id, "days": days, "price": total, "text": data["text"]
    }
    save_state()

    deadline_str = (datetime.now() + timedelta(minutes=5)).strftime("%H:%M")
    
    caption = (
        f"🧾 *INVOICE PEMBAYARAN*\n\n"
        f"📦 Service: Sewa Rekapwin {data['text']}\n"
        f"💰 Price: Rp {fmt_num(price)}\n"
        f"⚙️ Biaya Admin: Rp {fmt_num(admin_fee)}\n"
        f"💵 Total: *Rp {fmt_num(total)}*\n\n"
        f"Silakan scan QRIS di atas.\n\n"
        f"⏳ Batas Waktu: {deadline_str} WIB\n"
        f"❗ Status: *Menunggu konfirmasi transfer*"
    )
    
    if os.path.exists(QRIS_PHOTO_PATH):
        with open(QRIS_PHOTO_PATH, 'rb') as photo:
            bot.send_photo(chat_id, photo, caption=caption, parse_mode="Markdown", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ Saya Sudah Transfer", callback_data="conf_transfer")))
    else:
        bot.send_message(chat_id, f"{caption}\n\n(Maaf, foto QRIS belum diupload.)", parse_mode="Markdown")
    
    bot.answer_callback_query(call.id, f"Invoice {data['text']} dibuat!")

@bot.callback_query_handler(func=lambda c: c.data == "conf_transfer")
def cb_conf_transfer(call):
    bot.answer_callback_query(call.id, "Pembayaran belum terdeteksi!")
    bot.send_message(call.message.chat.id, "⚠️ *Pembayaran belum terdeteksi.*\n\nJika sudah transfer, kirim *foto bukti pembayaran* ke chat ini.", parse_mode="Markdown")

@bot.message_handler(commands=['upgrade'])
def cmd_upgrade(message):
    if not is_user_admin(message.chat.id, message.from_user.id): return
    parts = message.text.split()
    if len(parts) < 4: return safe_reply(message, "❌ Format: /upgrade [group_id] XVIP [hari]")
    
    try:
        cid = parts[1]
        days = int(parts[3])
    except: return safe_reply(message, "❌ Format tidak valid.")
    
    if days == 0:
        data_store["premium_groups"][cid] = 0
        text = "✅ Grup ini PERMANEN!"
    else:
        exp = data_store["premium_groups"].get(cid, time.time())
        if exp < time.time(): exp = time.time()
        data_store["premium_groups"][cid] = exp + (days * 86400)
        text = f"✅ Grup diaktifkan selama *{days} hari*!"
    
    save_state()
    try: bot.send_message(int(cid), f"🎉 *Premium Aktif!* Grup ini telah diaktifkan.", parse_mode="Markdown")
    except: pass
    safe_reply(message, text, parse_mode="Markdown")

# ============== PANDUAN ==============
@bot.message_handler(commands=['help', 'start', 'panduan'])
def cmd_help(message):
    safe_reply(message,
        "📖 *PANDUAN BOT REKAP WIN By Angga Official*\n\n"
        "1️⃣ Perintah Utama Rekap:\n"
        "• /rekap - Cek Data Duel (Tanpa Tombol)\n"
        "• /win - Rekap Win Dengan Parameter Auto Fee (Dengan Tombol)\n"
        "• /win [fee] - Rekap duel dengan potongan fee manual (contoh: /win 5.5)\n"
        "• /winrekap - Mendapatkan Data Rekapitulasi Total\n\n"
        "2️⃣ Fitur Saldo & LW:\n"
        "• /resetlw - Reset History & Saldo Game (Mereset DEV, ROL, WD & Fee)\n"
        "• /geser [dari] [jumlah] [ke] - Pindahkan saldo antar pemain\n"
        "• /del [user] - Hapus data pemain dari LW\n"
        "• /lunas [user] - Lunasi hutang pemain\n"
        "• /tambah [user] [jumlah] - Tambah saldo pemain\n"
        "• /kurangi [user] [jumlah] - Kurangi saldo pemain\n"
        "• /depo [user] [jumlah] - Deposit saldo pemain\n"
        "• /wd [user] - Cek saldo pemain\n"
        "• /bulatkan - Bulatkan semua saldo ke kelipatan 100\n\n"
        "3️⃣ Fitur Premium:\n"
        "• /id - Cek ID Grup (Untuk aktivasi premium)\n"
        "• /sewa - Beli akses premium (QRIS)\n"
        "• /upgrade [id_grup] XVIP [hari] - Aktivasi premium (Khusus Admin Bot)\n\n"
        "4️⃣ Fitur Keamanan Grup:\n"
        "• /antilink - Aktifkan/Nonaktifkan Anti Link\n"
        "• /antiforward - Aktifkan/Nonaktifkan Anti Forward\n\n"
        "❗ *Bot harus menjadi Admin Grup untuk bisa menyematkan (pin) pesan LW.*\n"
        "❗ *Perintah Rekap, Saldo, & Keamanan hanya bisa digunakan oleh Admin Grup.*",
        parse_mode="Markdown")

# ============== HANDLER UTAMA (Anti Link, Anti Forward, Input Text/Foto) ==============
@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'forward'])
def handle_all_messages(message):
    chat_id = message.chat.id
    user = message.from_user
    
    if message.chat.type not in ("group", "supergroup"):
        return
        
    # Abaikan jika pesan adalah command (sudah ditangani handler di atas)
    if message.text and message.text.startswith('/'):
        return
        
    admin = is_user_admin(chat_id, user.id)
    
    # 1. Cek Anti-Forward
    if not admin and get_chat_setting(chat_id, "antiforward", False):
        if message.forward_from or message.forward_from_chat or message.forward_sender_name:
            try: bot.delete_message(chat_id, message.message_id)
            except: pass
            return

    # 2. Cek Anti-Link
    if not admin and message.text and get_chat_setting(chat_id, "antilink", False):
        link_pattern = re.compile(r'((https?://|www\.|t\.me/|telegram\.me/|wa\.me/|whatsapp\.com/)[^\s]+)', re.IGNORECASE)
        if link_pattern.search(message.text):
            try: bot.delete_message(chat_id, message.message_id)
            except: pass
            return
            
    # 3. Tangkap Foto Bukti Pembayaran
    if message.photo:
        user_id = str(user.id)
        if user_id in data_store["pending_payment"]:
            data = data_store["pending_payment"][user_id]
            username = user.username or user.first_name
            notif_text = (f"🔔 *PEMBAYARAN BARU MASUK*\n\n👤 User: @{username}\n🆔 ID: `{data['chat_id']}`\n📦 Paket: {data['text']}\n💰 Jumlah: *Rp {fmt_num(data['price'])}*\n\nKetik command ini:\n`/upgrade {data['chat_id']} XVIP {data['days']}`")
            for admin_id in ADMIN_IDS:
                try: bot.send_photo(admin_id, message.photo[-1].file_id, caption=notif_text, parse_mode="Markdown")
                except: pass
            del data_store["pending_payment"][user_id]
            save_state()
            safe_reply(message, "✅ *Bukti pembayaran telah dikirim ke admin.*\n\nMohon tunggu verifikasi.", parse_mode="Markdown")
            return
            
    # 4. Tangkap Input Device / WD Time
    if message.text:
        key = f"{chat_id}:{user.id}"
        pr = data_store["pending_rekap"].get(key)
        
        if pr and pr.get("step") == "device":
            device_name = message.text.strip()
            pr["device"] = device_name
            data_store["device"] = device_name
            save_state()
            wd_time = data_store.get("wd_time")
            if wd_time:
                pr["wd_time"] = wd_time
                pr["step"] = "done"
                save_state()
                safe_reply(message, f"📱 Device: {device_name}\n⌚️ WD: {wd_time}\n\n⏳ Memproses rekap...")
                finalize_rekap(pr, chat_id)
            else:
                pr["step"] = "wd_time"
                save_state()
                safe_reply(message, f"📱 Device: {device_name}\n\n⌚️ Masukkan waktu WD (contoh: 22.00 WIB):")
            return
            
        if pr and pr.get("step") == "wd_time":
            wd_time_val = message.text.strip()
            pr["wd_time"] = wd_time_val
            data_store["wd_time"] = wd_time_val
            pr["step"] = "done"
            save_state()
            safe_reply(message, f"⌚️ WD: {wd_time_val}\n\n⏳ Memproses rekap...")
            finalize_rekap(pr, chat_id)
            return

if __name__ == "__main__":
    print("🤖 Bot REKAP By Angga Official sedang berjalan...")
    bot.infinity_polling(skip_pending=True)
