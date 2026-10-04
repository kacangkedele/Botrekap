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
    telebot.types.BotCommand("wd", "Cek Saldo Pemain"),
    telebot.types.BotCommand("bulatkan", "Bulatkan Saldo ke 100"),
    telebot.types.BotCommand("id", "Cek ID Grup"),
    telebot.types.BotCommand("sewa", "Beli Akses Premium Bot"),
    telebot.types.BotCommand("upgrade", "Aktivasi Premium Grup (Admin)"),
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

# Fungsi Auto Fee berdasarkan daftar_fee.txt
def get_auto_fee(amount):
    if amount <= 0: return 0
    if 1 <= amount <= 9: return 1
    if 10 <= amount <= 18: return 2
    if 19 <= amount <= 27: return 3
    if 28 <= amount <= 36: return 4
    if 37 <= amount <= 45: return 5
    if 46 <= amount <= 55: return 6
    if 56 <= amount <= 64: return 7
    if 65 <= amount <= 73: return 8
    if 74 <= amount <= 82: return 9
    if 83 <= amount <= 90: return 10
    if 91 <= amount <= 99: return 11
    if 100 <= amount <= 108: return 12
    if 109 <= amount <= 117: return 13
    if 118 <= amount <= 126: return 14
    if 127 <= amount <= 135: return 15
    if 136 <= amount <= 152: return 16
    if 153 <= amount <= 161: return 17
    if 162 <= amount <= 170: return 18
    if 171 <= amount <= 180: return 19
    if 181 <= amount <= 189: return 20
    if 190 <= amount <= 198: return 21
    if 199 <= amount <= 207: return 22
    if 208 <= amount <= 216: return 23
    if 217 <= amount <= 225: return 24
    if 226 <= amount <= 234: return 25
    if 235 <= amount <= 243: return 26
    if 244 <= amount <= 252: return 27
    if 253 <= amount <= 261: return 28
    if 262 <= amount <= 270: return 30
    if 271 <= amount <= 279: return 31
    if 280 <= amount <= 288: return 32
    if 289 <= amount <= 298: return 33
    if 299 <= amount <= 306: return 34
    if 307 <= amount <= 315: return 35
    if 316 <= amount <= 324: return 36
    if 325 <= amount <= 333: return 37
    if 334 <= amount <= 342: return 38
    if 343 <= amount <= 351: return 39
    if 352 <= amount <= 360: return 40
    if 361 <= amount <= 369: return 41
    if 370 <= amount <= 378: return 42
    if 379 <= amount <= 387: return 43
    if 388 <= amount <= 396: return 44
    if 397 <= amount <= 405: return 45
    if 406 <= amount <= 415: return 46
    if 416 <= amount <= 424: return 47
    if 425 <= amount <= 433: return 48
    if 434 <= amount <= 442: return 49
    if 443 <= amount <= 451: return 50
    if 452 <= amount <= 460: return 51
    if 461 <= amount <= 550: return 60
    if 551 <= amount <= 571: return 65
    if 572 <= amount <= 623: return 67
    if 624 <= amount <= 724: return 68
    if 725 <= amount <= 820: return 69
    if 821 <= amount <= 922: return 70
    if 923 <= amount <= 1000: return 100
    if 1001 <= amount <= 2000: return 240
    if 2001 <= amount <= 3000: return 340
    if 3001 <= amount <= 4000: return 440
    if 4001 <= amount <= 5000: return 500
    
    if amount > 200000: return 20000
    i = amount // 1000
    if amount % 1000 == 0:
        i -= 1
    return (i * 100) + 100

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
    "balances": {}, "browser": None, "device": None,
    "pending_rekap": {}, "premium_groups": {}, 
    "chat_settings": {}, "pending_payment": {},
    "last_win_chat_id": None, "last_win_msg_id": None, "last_win_data": None
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

# ============== PARSER TANGGUH & ANTI DUPLIKAT ==============
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
            
    # GABUNGKAN NAMA PEMAIN YANG SAMA (Case-Insensitive)
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
            win_lines.append(f"{nick} {fmt_num(saldo)}")
        elif saldo < 0:
            lose_lines.append(f"{nick} -{fmt_num(abs(saldo))}")
            
    output = f"DEV: {lw_data['device']}\nDATE : {date_str}\nTIME : {time_str}\nROL: {lw_data['browser']}\n\nLAST WIN : (@{lw_data['username']})\n"
    
    for i, game in enumerate(lw_data.get('games', [])):
        output += f"GAME {i+1} : {game['winner']} {game['score']} {fmt_num(game['modal'])}\n"
        
    output += f"\nSALDO PEMAIN : ({fmt_num(total_saldo)})\n"
    output += "\n".join(win_lines)
    if lose_lines:
        output += "\n\n" + "\n".join(lose_lines)
    return output

def update_last_win_message():
    chat_id = data_store.get("last_win_chat_id")
    msg_id = data_store.get("last_win_msg_id")
    lw_data = data_store.get("last_win_data")
    
    if not chat_id or not msg_id or not lw_data: return
        
    output = render_lw_output(lw_data, data_store["balances"])
    try:
        bot.edit_message_text(output, chat_id=chat_id, message_id=msg_id)
    except: pass

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

# ============== /rekap (Tanpa Tombol) & /rekapwin /win (Dengan Tombol) ==============
@bot.message_handler(commands=['rekapwin', 'rekap', 'win', 'winrekap'])
def cmd_rekap(message):
    chat_id = message.chat.id
    user = message.from_user
    parts = message.text.split()
    if not parts: return
    cmd = parts[0].split('@')[0][1:].lower()

    if message.chat.type not in ("group", "supergroup"):
        return safe_reply(message, "❌ Command ini hanya untuk grup.")

    is_user_admin = False
    if user.id in ADMIN_IDS:
        is_user_admin = True
    else:
        try:
            chat_member = bot.get_chat_member(chat_id, user.id)
            if chat_member.status in ['administrator', 'creator']:
                is_user_admin = True
        except: pass

    if not is_user_admin:
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
    
    if cmd == 'win':
        auto_fee = True
    elif len(parts) > 1:
        try: 
            fee = float(parts[1].replace(",", "."))
        except: 
            pass
    else:
        auto_fee = True

    summary = render_duel_summary(teams, fee, auto_fee)
    show_buttons = cmd in ['rekapwin', 'win', 'winrekap']
    
    if show_buttons:
        key = f"{chat_id}:{user.id}"
        data_store["pending_rekap"][key] = {
            "teams": teams, "fee": fee, "auto_fee": auto_fee, "winner": None, "score": None,
            "browser": None, "device": None, "chat_id": chat_id, "user_id": user.id,
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
    
    if browser and device:
        pr["browser"], pr["device"], pr["step"] = browser, device, "done"
        save_state()
        bot.edit_message_text(f"✅ Skor: {pr['score']}\n🌐 Browser: {browser}\n📱 Device: {device}\n\n⏳ Memproses...", chat_id=chat_id, message_id=call.message.message_id)
        finalize_rekap(pr, chat_id)
    else:
        pr["step"] = "browser"
        save_state()
        bot.edit_message_text("Pilih browser yang digunakan:", chat_id=chat_id, message_id=call.message.message_id, reply_markup=browser_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rw_browser_"))
def cb_browser(call):
    key = f"{call.message.chat.id}:{call.from_user.id}"
    pr = data_store["pending_rekap"].get(key)
    if not pr: return
    browser = call.data.split("rw_browser_")[1]
    pr["browser"] = browser
    data_store["browser"] = browser
    save_state()
    
    if data_store.get("device"):
        pr["device"], pr["step"] = data_store["device"], "done"
        save_state()
        bot.edit_message_text(f"✅ Skor: {pr['score']}\n🌐 Browser: {browser}\n📱 Device: {pr['device']}\n\n⏳ Memproses...", chat_id=call.message.chat.id, message_id=call.message.message_id)
        finalize_rekap(pr, call.message.chat.id)
    else:
        pr["step"] = "device"
        save_state()
        bot.edit_message_text(f"✅ Skor: {pr['score']}\n🌐 Browser: {browser}\n\n📱 Masukkan nama device (contoh: IPHONE 14):", chat_id=call.message.chat.id, message_id=call.message.message_id)

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

@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'), content_types=['text'])
def catch_device_input(message):
    chat_id = message.chat.id
    key = f"{chat_id}:{message.from_user.id}"
    pr = data_store["pending_rekap"].get(key)
    
    if pr and pr.get("step") == "device":
        device_name = message.text.strip()
        pr["device"] = device_name
        data_store["device"] = device_name
        pr["step"] = "done"
        save_state()
        safe_reply(message, f"📱 Device: {device_name}\n\n⏳ Memproses rekap...")
        finalize_rekap(pr, chat_id)
        return

# ============== HITUNG OTOMATIS (Fee Disembunyikan & Dikirim ke PM Admin) ==============
def finalize_rekap(pr, chat_id):
    teams = pr["teams"]
    winner = pr["winner"]
    score = pr["score"]
    fee_pct = pr["fee"]
    auto_fee = pr.get("auto_fee", False)
    
    loser = "BESAR" if winner == "KECIL" else "KECIL"
    
    winner_modal = sum(p["modal"] for p in teams[winner])
    loser_modal = sum(p["modal"] for p in teams[loser])
    
    multiplier = 1.0
    fee_logs = []

    for team_name in [winner, loser]:
        for p in teams[team_name]:
            nick_target = get_balance_nick(p["nickname"])
            current = data_store["balances"].get(nick_target, 0)
            fee_dipotong = 0
            
            if p["result"] is not None:
                hasil = p["result"]
                
                if hasil > 0:
                    if auto_fee:
                        fee_dipotong = get_auto_fee(hasil)
                        hasil -= fee_dipotong
                    elif fee_pct > 0:
                        fee_dipotong = int(hasil * (fee_pct/100))
                        hasil = int(hasil * (1 - fee_pct/100))
                        
                # Saldo langsung diisi dengan Hasil Bersih (Hasil - Fee)
                net = hasil
                
                # Catat untuk laporan PM Admin
                if fee_dipotong > 0:
                    fee_logs.append(f"👤 {nick_target}\n   Hasil: {fmt_num(p['result'])} - Fee: {fmt_num(fee_dipotong)} = {fmt_num(hasil)}")
            else:
                if team_name == winner:
                    share = int(loser_modal * multiplier * (p["modal"] / winner_modal)) if winner_modal > 0 else 0
                    net = share
                else: 
                    penalty = int(p["modal"] * multiplier)
                    net = -penalty
                    
            data_store["balances"][nick_target] = current + net

    save_state()

    # Kirim Database Fee ke Chat Pribadi Admin (PM)
    if fee_logs:
        log_text = f"📊 *DATABASE FEE OTOMATIS*\n\nGame: {winner[0]} {score}\n\n" + "\n".join(fee_logs)
        for admin_id in ADMIN_IDS:
            try: bot.send_message(admin_id, log_text, parse_mode="Markdown")
            except: pass

    if data_store.get("last_win_chat_id") != chat_id or not data_store.get("last_win_data"):
        data_store["last_win_chat_id"] = chat_id
        data_store["last_win_data"] = {
            "device": pr['device'],
            "browser": pr['browser'],
            "username": pr['username'],
            "games": []
        }
    else:
        data_store["last_win_data"]["device"] = pr['device']
        data_store["last_win_data"]["browser"] = pr['browser']
        data_store["last_win_data"]["username"] = pr['username']
        
    data_store["last_win_data"]["games"].append({
        "winner": winner[0],
        "score": score,
        "modal": loser_modal
    })
    
    save_state()

    output = render_lw_output(data_store["last_win_data"], data_store["balances"])

    bot.send_message(chat_id, "✅ *Rekapwin selesai.*", parse_mode="Markdown")
    sent = bot.send_message(chat_id, output)
    try_pin_message(chat_id, sent.message_id)
    data_store["last_win_msg_id"] = sent.message_id
    save_state()

    if f"{chat_id}:{pr['user_id']}" in data_store["pending_rekap"]:
        del data_store["pending_rekap"][f"{chat_id}:{pr['user_id']}"]
    save_state()

# ============== FITUR /id (Cek ID Grup) ==============
@bot.message_handler(commands=['id'])
def cmd_id(message):
    chat_id = message.chat.id
    safe_reply(message, f"🆔 ID Grup ini adalah: `{chat_id}`", parse_mode="Markdown")

# ============== FITUR SALDO, GESER (TRANSFER), & AUTO UPDATE LW (KHUSUS ADMIN) ==============
@bot.message_handler(commands=['resetlw', 'geser', 'lunas', 'tambah', 'kurangi', 'depo', 'wd', 'bulatkan'])
def cmd_saldo_actions(message):
    try:
        chat_id = message.chat.id
        user = message.from_user
        
        is_user_admin = False
        if user.id in ADMIN_IDS:
            is_user_admin = True
        else:
            try:
                chat_member = bot.get_chat_member(chat_id, user.id)
                if chat_member.status in ['administrator', 'creator']:
                    is_user_admin = True
            except: pass

        parts = message.text.split()
        if not parts: return
        cmd = parts[0].split('@')[0][1:].lower()
        
        restricted_cmds = ['geser', 'lunas', 'kurangi', 'depo', 'wd', 'bulatkan']
        
        if cmd in restricted_cmds and not is_user_admin:
            return safe_reply(message, "⚠️Hanya Admin Group yang bisa menggunakan Perintah ini🚫")
            
        # FITUR /geser (Transfer Saldo)
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
                
            # Lakukan Transfer
            data_store["balances"][from_nick] -= amt
            if to_nick not in data_store["balances"]:
                data_store["balances"][to_nick] = 0
            data_store["balances"][to_nick] += amt
            
            save_state()
            update_last_win_message()
            return safe_reply(message, f"✅ Berhasil memindahkan saldo {fmt_num(amt)} dari {from_nick} ke {to_nick}.")
            
        if cmd == 'resetlw':
            data_store["balances"] = {}
            data_store["last_win_msg_id"] = None
            data_store["last_win_chat_id"] = None
            data_store["last_win_data"] = None
            data_store["device"] = None
            data_store["browser"] = None
            save_state()
            return safe_reply(message, "✅ History direset. Dev & ROL akan diperbarui saat rekapwin berikutnya.")
            
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

@bot.message_handler(content_types=['photo'])
def handle_payment_proof(message):
    try:
        user_id = str(message.from_user.id)
        if user_id in data_store["pending_payment"]:
            if not message.photo: return
            data = data_store["pending_payment"][user_id]
            username = message.from_user.username or message.from_user.first_name

            notif_text = (f"🔔 *PEMBAYARAN BARU MASUK*\n\n👤 User: @{username}\n🆔 ID: `{data['chat_id']}`\n📦 Paket: {data['text']}\n💰 Jumlah: *Rp {fmt_num(data['price'])}*\n\nKetik command ini:\n`/upgrade {data['chat_id']} XVIP {data['days']}`")

            for admin_id in ADMIN_IDS:
                try: bot.send_photo(admin_id, message.photo[-1].file_id, caption=notif_text, parse_mode="Markdown")
                except: pass

            del data_store["pending_payment"][user_id]
            save_state()
            safe_reply(message, "✅ *Bukti pembayaran telah dikirim ke admin.*\n\nMohon tunggu verifikasi.", parse_mode="Markdown")
    except Exception as e:
        print(f"Error handle photo: {e}")

@bot.message_handler(commands=['upgrade'])
def cmd_upgrade(message):
    if message.from_user.id not in ADMIN_IDS: return
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

@bot.message_handler(commands=['help', 'start', 'panduan'])
def cmd_help(message):
    safe_reply(message,
        "📖 *PANDUAN BOT REKAP WIN By Angga Official*\n\n"
        "1️⃣ Perintah Utama Rekap:\n"
        "• /rekap - Cek Data Duel (Tanpa Tombol)\n"
        "• /win - Rekap Win Dengan Parameter Auto Fee (Dengan Tombol)\n"
        "• /win [fee] - Rekap duel dengan potongan fee manual (contoh: /win 5.5)\n"
        "• /winrekap - Mendapatkan Data Rekap\n\n"
        "2️⃣ Fitur Saldo & LW:\n"
        "• /resetlw - Reset History & Saldo Game (Mereset DEV & ROL juga)\n"
        "• /geser [dari] [jumlah] [ke] - Pindahkan saldo antar pemain\n"
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
        "❗ *Bot harus menjadi Admin Grup untuk bisa menyematkan (pin) pesan LW.*\n"
        "❗ *Perintah Rekap & Saldo hanya bisa digunakan oleh Admin Grup.*",
        parse_mode="Markdown")

if __name__ == "__main__":
    print("🤖 Bot berjalan...")
    bot.infinity_polling(skip_pending=True)
