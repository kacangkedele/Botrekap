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
MIN_MEMBER_PREMIUM = 10
QRIS_PHOTO_PATH = "qris.png"  # Pastikan file qris.png ada di folder yang sama

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# Fungsi aman untuk membalas pesan agar tidak error 400
def safe_reply(message, text, **kwargs):
    try:
        return bot.reply_to(message, text, **kwargs)
    except:
        try:
            return bot.send_message(message.chat.id, text, **kwargs)
        except Exception as e:
            print(f"Failed to send message: {e}")

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

# ============== PARSER TANGGUH ==============
def parse_duel_data(text):
    teams = {"KECIL": [], "BESAR": []}
    current_team = None
    
    # 1. Cari semua format Array di seluruh teks (contoh: K: [23,20,50] = 93)
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
        
    # 2. Jika tidak ada array, baca format nama pemain (contoh: K: HENDRA 23 P)
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
            
    return teams

def parse_player_line(line, team, teams):
    line = line.strip()
    if not line: return
    
    if "//" in line:
        left_part = line.split("//", 1)[0].strip()
        result_part = line.split("//", 1)[1].strip()
        try: result = int(result_part.replace(".", "").replace(",", "").split()[0])
        except: result = None
    else:
        left_part = line
        result = None

    is_lf = False
    tokens = left_part.split()
    if tokens and tokens[-1].upper() in ("LF", "P"):
        is_lf = True
        tokens = tokens[:-1]

    if len(tokens) < 2: return
    try: modal = int(tokens[-1].replace(".", "").replace(",", ""))
    except: return

    nickname = " ".join(tokens[:-1]).strip()
    if not nickname or re.search(r'\d', nickname): return

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

# ============== /rekap (Tanpa Tombol) & /rekapwin (Dengan Tombol) ==============
@bot.message_handler(commands=['rekapwin', 'rekap', 'win', 'winrekap'])
def cmd_rekap(message):
    chat_id = message.chat.id
    user = message.from_user
    parts = message.text.split()
    if not parts: return
    cmd = parts[0].split('@')[0][1:].lower()

    if message.chat.type not in ("group", "supergroup"):
        return safe_reply(message, "❌ Command ini hanya untuk grup.")

    # Cek apakah user adalah Admin Grup atau Admin Bot
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

    # Cek Premium
    if not is_premium(chat_id):
        try: member_count = bot.get_chat_member_count(chat_id)
        except: member_count = 0
        if member_count < MIN_MEMBER_PREMIUM:
            return safe_reply(message, f"❌ Fitur ini membutuhkan akses premium.\nGunakan /sewa untuk mendapatkan akses premium.")

    if not message.reply_to_message:
        return safe_reply(message, "❌ Balas pesan data duel, lalu kirim /rekapwin [fee]")

    src = message.reply_to_message.text
    if not src:
        return safe_reply(message, "❌ Pesan yang dibalas bukan teks data duel.")

    teams = parse_duel_data(src)
    if not teams["KECIL"] and not teams["BESAR"]:
        return safe_reply(message, "❌ Format K/B tidak lengkap.")

    fee = 0.0
    if len(parts) > 1:
        try: fee = float(parts[1].replace(",", "."))
        except: pass

    summary = render_duel_summary(teams, fee)
    show_buttons = cmd in ['rekapwin', 'win', 'winrekap']
    
    if show_buttons:
        key = f"{chat_id}:{user.id}"
        data_store["pending_rekap"][key] = {
            "teams": teams, "fee": fee, "winner": None, "score": None,
            "browser": None, "device": None, "chat_id": chat_id, "user_id": user.id,
            "username": user.username or user.first_name, "step": "winner",
        }
        save_state()
        safe_reply(message, f"📊 *DATA DUEL DITERIMA*\n\n{summary}\n\n👉 *Pilih tim pemenang:*", parse_mode="Markdown", reply_markup=winner_keyboard())
    else:
        safe_reply(message, f"📊 *DATA DUEL DITERIMA*\n\n{summary}", parse_mode="Markdown")

def render_duel_summary(teams, fee):
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
        lines.append(f"*💰 Saldo Anda seharusnya: {k_total + b_total} B*")
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
        
    if fee > 0:
        lines.append("")
        lines.append(f"*💸 Fee: {fee}%*")
        
    return "\n".join(lines)

# ============== CALLBACK REKAP ==============
@bot.callback_query_handler(func=lambda c: c.data.startswith("rw_win_"))
def cb_winner(call):
    key = f"{call.message.chat.id}:{call.from_user.id}"
    pr = data_store["pending_rekap"].get(key)
    if not pr: return bot.answer_callback_query(call.id, "Sesi tidak ditemukan. Ulangi /rekapwin")
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

# ============== HITUNG OTOMATIS (BACA // HASIL) & MULTI-GAME LW ==============
def finalize_rekap(pr, chat_id):
    teams = pr["teams"]
    winner = pr["winner"]
    score = pr["score"]
    fee_pct = pr["fee"]
    
    loser = "BESAR" if winner == "KECIL" else "KECIL"
    
    winner_modal = sum(p["modal"] for p in teams[winner])
    loser_modal = sum(p["modal"] for p in teams[loser])

    multiplier = 2.0 if score == "2-0" else 1.0
    prize_pool = int(loser_modal * multiplier)

    # 1. Hitung pemain yang kalah
    for p in teams[loser]:
        current = data_store["balances"].get(p["nickname"].lower(), 0)
        if p["result"] is not None:
            loss = p["modal"] - p["result"]
            if loss < 0: loss = 0
            new_saldo = current - loss
        else:
            new_saldo = current - p["modal"]
        data_store["balances"][p["nickname"].lower()] = new_saldo

    # 2. Hitung pemain yang menang
    if winner_modal > 0:
        for p in teams[winner]:
            current = data_store["balances"].get(p["nickname"].lower(), 0)
            if p["result"] is not None:
                profit = p["result"] - p["modal"]
                if profit > 0 and fee_pct > 0:
                    profit = int(profit * (1 - fee_pct/100))
                new_saldo = current + profit
            else:
                ratio = p["modal"] / winner_modal
                gross = int(prize_pool * ratio)
                net_winning = int(gross * (1 - fee_pct/100)) if fee_pct > 0 else gross
                new_saldo = current + net_winning
            data_store["balances"][p["nickname"].lower()] = new_saldo

    # Bulatkan semua saldo ke kelipatan 100
    for nick in list(data_store["balances"].keys()):
        data_store["balances"][nick] = bulatkan_ke_kelipatan(data_store["balances"][nick])

    save_state()

    # Cek apakah LW sudah ada di grup ini. Jika ada, tambahkan Game baru. Jika tidak, buat LW baru.
    if data_store.get("last_win_chat_id") != chat_id or not data_store.get("last_win_data"):
        data_store["last_win_chat_id"] = chat_id
        data_store["last_win_data"] = {
            "device": pr['device'],
            "browser": pr['browser'],
            "username": pr['username'],
            "games": []
        }
    else:
        # Update data device/browser/user terbaru
        data_store["last_win_data"]["device"] = pr['device']
        data_store["last_win_data"]["browser"] = pr['browser']
        data_store["last_win_data"]["username"] = pr['username']
        
    # Tambahkan game saat ini ke daftar games di LW
    data_store["last_win_data"]["games"].append({
        "winner": winner[0],
        "score": score,
        "modal": loser_modal
    })
    
    save_state()

    # Render output LW
    output = render_lw_output(data_store["last_win_data"], data_store["balances"])

    # Unpin pesan LW lama jika ada
    old_msg_id = data_store.get("last_win_msg_id")
    if old_msg_id:
        try: bot.unpin_chat_message(chat_id, old_msg_id)
        except: pass

    # Kirim pesan LW baru dan pin pesan tersebut
    bot.send_message(chat_id, "✅ *Rekapwin selesai.*", parse_mode="Markdown")
    sent = bot.send_message(chat_id, output)
    try_pin_message(chat_id, sent.message_id)
    data_store["last_win_msg_id"] = sent.message_id
    save_state()

    # Hapus sesi rekap yang pending
    if f"{chat_id}:{pr['user_id']}" in data_store["pending_rekap"]:
        del data_store["pending_rekap"][f"{chat_id}:{pr['user_id']}"]
    save_state()

# ============== FITUR SALDO & AUTO UPDATE LW ==============
@bot.message_handler(commands=['resetlw', 'lunas', 'tambah', 'kurangi', 'depo', 'wd', 'bulatkan'])
def cmd_saldo_actions(message):
    try:
        parts = message.text.split()
        if not parts: return
        
        cmd = parts[0].split('@')[0][1:].lower()
        user = message.from_user.username or message.from_user.first_name
        
        if cmd == 'resetlw':
            data_store["balances"] = {}
            data_store["last_win_msg_id"] = None
            data_store["last_win_chat_id"] = None
            data_store["last_win_data"] = None
            # RESET DEVICE DAN BROWSER JUGA AGAR DITANYAKAN ULANG SAAT REKAPWIN
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
            msg_text = "🔁 Pembulatan:\n" + "\n".join(changes) + f"\n\n📟 Oleh: @{user}" if changes else "✅ Semua saldo sudah bulat."
            save_state()
            bot.send_message(message.chat.id, msg_text)
            update_last_win_message()
            return

        if cmd not in ['lunas', 'wd', 'tambah', 'kurangi', 'depo']: return

        if cmd in ['lunas', 'wd'] and len(parts) < 2: 
            return safe_reply(message, f"❌ Format: /{cmd} [username]")
        if cmd in ['tambah', 'kurangi', 'depo'] and len(parts) < 3: 
            return safe_reply(message, f"❌ Format: /{cmd} [username] [jumlah]")

        nick = parts[1].strip().lower()
        amt = 0
        if cmd in ['tambah', 'kurangi', 'depo']:
            try: amt = int(parts[2].replace(".", ""))
            except: return safe_reply(message, "❌ Jumlah tidak valid.")
        
        if cmd == 'lunas':
            if nick not in data_store["balances"]: return safe_reply(message, "❌ Pemain tidak ditemukan.")
            old = data_store["balances"][nick]
            data_store["balances"][nick] = 0
            msg_text = f"✅ Hutang dilunasi.\n👤 {nick}: {fmt_num(old)} → 0\n📟 Oleh: @{user}"
            
        elif cmd in ['tambah', 'depo']:
            old = data_store["balances"].get(nick, 0)
            data_store["balances"][nick] = old + amt
            if cmd == 'depo':
                msg_text = f"✅ Saldo {nick.upper()} berhasil didepo {fmt_num(amt)}."
            else:
                msg_text = f"➕ Saldo ditambah.\n👤 {nick}: {fmt_num(old)} → {fmt_num(data_store['balances'][nick])}\n📟 Oleh: @{user}"
            
        elif cmd == 'kurangi':
            old = data_store["balances"].get(nick, 0)
            data_store["balances"][nick] = old - amt
            msg_text = f"➖ Saldo dikurangi.\n👤 {nick}: {fmt_num(old)} → {fmt_num(data_store['balances'][nick])}\n📟 Oleh: @{user}"
            
        elif cmd == 'wd':
            saldo = data_store["balances"].get(nick, 0)
            msg_text = f"💳 Saldo {nick}: {fmt_num(saldo)}" if saldo > 0 else (f"⚠️ Hutang {nick}: {fmt_num(abs(saldo))}" if saldo < 0 else f"❌ {nick} tidak punya saldo.")
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
        "1️⃣ Perintah Utama:\n"
        "• /rekap - Cek Data Duel (Tanpa Tombol)\n"
        "• /winrekap - Mendapatkan Data Rekap (Dengan Tombol)\n"
        "• /rekapwin [fee] - Rekap duel dengan potongan fee\n"
        "• /win [fee] - Sama seperti /rekapwin\n\n"
        "2️⃣ Format Input Data Duel:\n"
        "```\nK: HENDRA 23 P\nNIP 20\n\nB: ROB 50\n```\nAtau format Array:\n```\nK: [18,200] = 218\n```\n\n"
        "3️⃣ Fitur Saldo:\n"
        "• /resetlw - Reset game (Mereset DEV & ROL juga)\n"
        "• /lunas [user] - Lunasi hutang\n"
        "• /tambah [user] [jumlah]\n"
        "• /kurangi [user] [jumlah]\n"
        "• /depo [user] [jumlah]\n"
        "• /wd [user] - Cek saldo\n"
        "• /bulatkan - Bulatkan ke 100\n\n"
        "4️⃣ Fitur Premium:\n"
        "• /sewa - Beli premium (QRIS)\n"
        "• /upgrade [id] [paket] [hari] - (Admin)\n\n"
        "❗ Bot harus jadi admin untuk pin pesan.",
        parse_mode="Markdown")

if __name__ == "__main__":
    print("🤖 Bot REKAP By Angga Official berjalan...")
    # skip_pending=True agar bot tidak memproses pesan lama saat baru dinyalakan
    bot.infinity_polling(skip_pending=True)
