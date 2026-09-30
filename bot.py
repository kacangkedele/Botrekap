import telebot
from telebot import types
import re
import json
import os
import time

# ============== KONFIGURASI ==============
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Ganti dengan token bot Anda
ADMIN_IDS = [123456789]  # Ganti dengan ID Telegram Anda
MIN_MEMBER_PREMIUM = 500
QRIS_PHOTO_PATH = "qris.png"  # Pastikan file qris.png ada di folder yang sama

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# ============== STORAGE ==============
STATE_FILE = "bot_state.json"

data_store = {
    "last_win": None,
    "balances": {},
    "browser": None,
    "device": None,
    "pending_rekap": {},
    "premium_groups": {}, 
    "chat_settings": {},
    "pending_payment": {}, # Menyimpan data user yang sedang dalam proses bayar
}

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                data_store["last_win"] = saved.get("last_win")
                data_store["balances"] = saved.get("balances", {})
                data_store["browser"] = saved.get("browser")
                data_store["device"] = saved.get("device")
                data_store["premium_groups"] = saved.get("premium_groups", {})
                data_store["chat_settings"] = saved.get("chat_settings", {})
                data_store["pending_payment"] = saved.get("pending_payment", {})
        except Exception as e:
            print(f"Error loading state: {e}")

def save_state():
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "last_win": data_store["last_win"],
                "balances": data_store["balances"],
                "browser": data_store["browser"],
                "device": data_store["device"],
                "premium_groups": data_store["premium_groups"],
                "chat_settings": data_store["chat_settings"],
                "pending_payment": data_store["pending_payment"],
            }, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving state: {e}")

load_state()

# ============== PARSER OTOMATIS ==============
def parse_duel_data(text):
    teams = {"KECIL": [], "BESAR": []}
    current_team = None
    for raw_line in text.split('\n'):
        line = raw_line.strip()
        if not line: continue
        
        upper = line.upper()
        if upper.startswith("KECIL:") or upper.startswith("K:"):
            current_team = "KECIL"
            rest = line.split(":", 1)[1].strip()
            if rest: parse_player_line(rest, current_team, teams)
            continue
        elif upper.startswith("BESAR:") or upper.startswith("B:"):
            current_team = "BESAR"
            rest = line.split(":", 1)[1].strip()
            if rest: parse_player_line(rest, current_team, teams)
            continue
            
        if current_team:
            parse_player_line(line, current_team, teams)
    return teams

def parse_player_line(line, team, teams):
    line = line.strip()
    if not line: return
    
    has_result = False
    result = None
    if "//" in line:
        parts = line.split("//", 1)
        left_part = parts[0].strip()
        result_part = parts[1].strip()
        has_result = True
        if result_part:
            try: result = int(result_part.replace(".", "").replace(",", ""))
            except: result = None
    else:
        left_part = line

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

def get_chat_setting(chat_id, key):
    cs = data_store["chat_settings"].get(str(chat_id), {})
    return cs.get(key) or data_store.get(key)

def set_chat_setting(chat_id, key, value):
    cid = str(chat_id)
    if cid not in data_store["chat_settings"]: data_store["chat_settings"][cid] = {}
    data_store["chat_settings"][cid][key] = value
    data_store[key] = value
    save_state()

def fmt_num(n):
    try: return f"{int(n):,}".replace(",", ".")
    except: return str(n)

def parse_amount(s):
    s = str(s).strip().replace(".", "").replace(",", "")
    try: return int(s)
    except: return None

def bulatkan_ke_kelipatan(n, kelipatan=100):
    return int(round(n / kelipatan) * kelipatan)

def try_pin_message(chat_id, message_id):
    try: bot.pin_chat_message(chat_id, message_id, disable_notification=True)
    except: pass

# ============== KEYBOARDS ==============
def winner_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("🏆 KECIL", callback_data="rw_win_KECIL"), types.InlineKeyboardButton("🏆 BESAR", callback_data="rw_win_BESAR"))
    return kb

def score_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("2 - 0", callback_data="rw_score_2-0"), types.InlineKeyboardButton("2 - 1", callback_data="rw_score_2-1"))
    return kb

def browser_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    options = ["Chrome", "Firefox", "Safari", "Edge", "Opera", "Kiwi"]
    kb.add(*[types.InlineKeyboardButton(b, callback_data=f"rw_browser_{b}") for b in options])
    return kb

def sewa_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("XVIP 1 Hari (Rp 7.000)", callback_data="sewa_1"),
        types.InlineKeyboardButton("XVIP 3 Hari (Rp 20.000)", callback_data="sewa_3"),
        types.InlineKeyboardButton("XVIP Permanen (Rp 50.000)", callback_data="sewa_p"),
        types.InlineKeyboardButton("📊 Cek Status Sewa", callback_data="sewa_cek")
    )
    return kb

# ============== /rekap ==============
@bot.message_handler(commands=['rekap'])
def cmd_rekap(message):
    chat_id = message.chat.id
    user = message.from_user

    if message.chat.type not in ("group", "supergroup"):
        return bot.reply_to(message, "❌ Command ini hanya untuk grup.")

    if not is_premium(chat_id):
        try: member_count = bot.get_chat_member_count(chat_id)
        except: member_count = 0
        if member_count < MIN_MEMBER_PREMIUM:
            return bot.reply_to(message, f"❌ Fitur premium. Butuh minimal {MIN_MEMBER_PREMIUM} member atau beli akses.\nGunakan /sewa untuk membeli premium.")

    if not message.reply_to_message:
        return bot.reply_to(message, "❌ Balas pesan data duel, lalu kirim /rekap [fee]")

    src = message.reply_to_message.text
    if not src:
        return bot.reply_to(message, "❌ Pesan yang dibalas bukan teks data duel.")

    teams = parse_duel_data(src)
    if not teams["KECIL"] and not teams["BESAR"]:
        return bot.reply_to(message, "❌ Gagal parse data duel. Cek format:\nK:\nSIGMA 100\nB:\nFIRMA 50")

    fee = 0.0
    parts = message.text.split()
    if len(parts) > 1:
        try: fee = float(parts[1].replace(",", "."))
        except: return bot.reply_to(message, "❌ Fee tidak valid. Contoh: /rekap 5.5")

    key = f"{chat_id}:{user.id}"
    data_store["pending_rekap"][key] = {
        "teams": teams, "fee": fee, "winner": None, "score": None,
        "browser": None, "device": None, "source_msg_id": message.reply_to_message.message_id,
        "chat_id": chat_id, "user_id": user.id, "username": user.username or user.first_name, "step": "winner",
    }

    summary = render_duel_summary(teams, fee)
    bot.reply_to(message, f"📊 *DATA DUEL DITERIMA*\n\n{summary}\n\n👉 Pilih tim pemenang:", parse_mode="Markdown", reply_markup=winner_keyboard())

def render_duel_summary(teams, fee):
    lines = []
    for t in ("KECIL", "BESAR"):
        if teams[t]:
            lines.append(f"*{t}:*")
            for p in teams[t]:
                tag = " LF" if p["is_lf"] else ""
                r = f" // {p['result']}" if p["result"] is not None else ""
                lines.append(f"  {p['nickname']} {fmt_num(p['modal'])}{tag}{r}")
            lines.append(f"  Total: {fmt_num(sum(p['modal'] for p in teams[t]))}\n")
    lines.append(f"💰 Fee: {fee}%")
    return "\n".join(lines)

# ============== CALLBACK REKAP ==============
@bot.callback_query_handler(func=lambda c: c.data.startswith("rw_win_"))
def cb_winner(call):
    key = f"{call.message.chat.id}:{call.from_user.id}"
    pr = data_store["pending_rekap"].get(key)
    if not pr: return bot.answer_callback_query(call.id, "Sesi tidak ditemukan. Ulangi /rekap")
    pr["winner"] = call.data.split("rw_win_")[1]
    pr["step"] = "score"
    save_state()
    bot.edit_message_text(f"✅ Pemenang: *{pr['winner']}*\n\nPilih skor:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=score_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rw_score_"))
def cb_score(call):
    key = f"{call.message.chat.id}:{call.from_user.id}"
    pr = data_store["pending_rekap"].get(key)
    if not pr: return
    pr["score"] = call.data.split("rw_score_")[1]
    chat_id = call.message.chat.id
    browser = get_chat_setting(chat_id, "browser")
    device = get_chat_setting(chat_id, "device")
    
    if browser and device:
        pr["browser"], pr["device"], pr["step"] = browser, device, "done"
        save_state()
        bot.edit_message_text(f"✅ Skor: {pr['score']}\n🌐 Browser: {browser}\n📱 Device: {device}\n\n⏳ Memproses rekap...", chat_id=chat_id, message_id=call.message.message_id)
        finalize_rekap(pr, chat_id, call.message.message_id)
    else:
        pr["step"] = "browser"
        save_state()
        bot.edit_message_text(f"✅ Skor: {pr['score']}\n\n🌐 Pilih browser:", chat_id=chat_id, message_id=call.message.message_id, reply_markup=browser_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rw_browser_"))
def cb_browser(call):
    key = f"{call.message.chat.id}:{call.from_user.id}"
    pr = data_store["pending_rekap"].get(key)
    if not pr: return
    browser = call.data.split("rw_browser_")[1]
    pr["browser"] = browser
    set_chat_setting(call.message.chat.id, "browser", browser)
    device = get_chat_setting(call.message.chat.id, "device")
    
    if device:
        pr["device"], pr["step"] = device, "done"
        save_state()
        bot.edit_message_text(f"🌐 Browser: {browser}\n📱 Device: {device}\n\n⏳ Memproses...", chat_id=call.message.chat.id, message_id=call.message.message_id)
        finalize_rekap(pr, call.message.chat.id, call.message.message_id)
    else:
        pr["step"] = "device"
        save_state()
        bot.edit_message_text(f"🌐 Browser: {browser}\n\n📱 Ketik nama device:", chat_id=call.message.chat.id, message_id=call.message.message_id)

@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'), content_types=['text'])
def catch_device_input(message):
    chat_id = message.chat.id
    key = f"{chat_id}:{message.from_user.id}"
    pr = data_store["pending_rekap"].get(key)
    
    if pr and pr.get("step") == "device":
        device_name = message.text.strip()
        pr["device"] = device_name
        pr["step"] = "done"
        set_chat_setting(chat_id, "device", device_name)
        save_state()
        bot.reply_to(message, f"📱 Device: {device_name}\n\n⏳ Memproses rekap...")
        finalize_rekap(pr, chat_id, message.message_id)
        return

# ============== FINALIZE & HITUNG OTOMATIS ==============
def finalize_rekap(pr, chat_id, edit_msg_id):
    teams = pr["teams"]
    winner = pr["winner"]
    score = pr["score"]
    fee_pct = pr["fee"]
    
    loser = "BESAR" if winner == "KECIL" else "KECIL"
    
    winner_modal = sum(p["modal"] for p in teams[winner])
    loser_modal = sum(p["modal"] for p in teams[loser])
    total_modal = winner_modal + loser_modal

    multiplier = 2.0 if score == "2-0" else 1.0
    prize_pool = int(loser_modal * multiplier)

    saldo_lines_win, saldo_lines_lose = [], []

    if winner_modal > 0:
        for p in teams[winner]:
            ratio = p["modal"] / winner_modal
            gross = int(prize_pool * ratio)
            net_winning = int(gross * (1 - fee_pct/100)) if fee_pct > 0 else gross
            
            current = data_store["balances"].get(p["nickname"].lower(), 0)
            if p["is_lf"]:
                new_saldo = current + net_winning
            else:
                new_saldo = p["modal"] + net_winning
                
            data_store["balances"][p["nickname"].lower()] = new_saldo
            saldo_lines_win.append(f"{p['nickname']} {fmt_num(new_saldo)}")

    for p in teams[loser]:
        current = data_store["balances"].get(p["nickname"].lower(), 0)
        if p["is_lf"]:
            new_saldo = current
        else:
            new_saldo = 0
            
        data_store["balances"][p["nickname"].lower()] = new_saldo
        saldo_lines_lose.append(f"{p['nickname']} -{fmt_num(p['modal'])}")

    for nick in list(data_store["balances"].keys()):
        data_store["balances"][nick] = bulatkan_ke_kelipatan(data_store["balances"][nick])

    total_saldo = sum(v for v in data_store["balances"].values() if v > 0)

    data_store["last_win"] = {"username": pr["username"], "winner": winner, "score": score, "total_modal": total_modal}
    save_state()

    output = render_rekap_output(pr["device"], pr["browser"], pr["username"], winner, score, total_modal, total_saldo, saldo_lines_win, saldo_lines_lose)
    sent = bot.send_message(chat_id, output)
    try_pin_message(chat_id, sent.message_id)
    del data_store["pending_rekap"][f"{chat_id}:{pr['user_id']}"]
    save_state()

def render_rekap_output(device, browser, lw_user, winner, score, total_modal, total_saldo, saldo_win, saldo_lose):
    lines = [f"DEV: {device}", f"ROL: {browser}", "", f"LAST WIN : (@{lw_user})", f"GAME 1 : {winner[0]} {score} {fmt_num(total_modal)}", "", f"SALDO PEMAIN : ({fmt_num(total_saldo)})"]
    lines.extend(saldo_win)
    lines.append("")
    lines.extend(saldo_lose)
    return "\n".join(lines)

# ============== FITUR TAMBAHAN ==============
@bot.message_handler(commands=['resetlw'])
def cmd_resetlw(message):
    data_store["last_win"], data_store["balances"] = None, {}
    save_state()
    bot.reply_to(message, "✅ History direset. Game baru dimulai.")

@bot.message_handler(commands=['lunas', 'tambah', 'kurangi', 'depo', 'wd', 'bulatkan'])
def cmd_saldo_actions(message):
    parts = message.text.split()
    cmd = parts[0][1:].lower()
    chat_id = message.chat.id
    user = message.from_user.username or message.from_user.first_name
    
    if cmd in ['lunas', 'wd'] and len(parts) < 2: return bot.reply_to(message, f"❌ Format: /{cmd} [username]")
    if cmd in ['tambah', 'kurangi', 'depo'] and len(parts) < 3: return bot.reply_to(message, f"❌ Format: /{cmd} [username] [jumlah]")

    nick = parts[1].strip().lower()
    
    if cmd == 'lunas':
        if nick not in data_store["balances"]: return bot.reply_to(message, f"❌ Pemain `{nick}` tidak ditemukan.", parse_mode="Markdown")
        old = data_store["balances"][nick]
        data_store["balances"][nick] = 0
        msg_text = f"✅ Hutang dilunasi.\n👤 {nick}: {fmt_num(old)} → 0\n📟 Oleh: @{user}"
        
    elif cmd in ['tambah', 'depo']:
        amt = parse_amount(parts[2])
        if amt is None: return bot.reply_to(message, "❌ Jumlah tidak valid.")
        old = data_store["balances"].get(nick, 0)
        data_store["balances"][nick] = old + amt
        msg_text = f"{'💰 Deposit' if cmd=='depo' else '➕ Tambah'} berhasil.\n👤 {nick}: {fmt_num(old)} → {fmt_num(data_store['balances'][nick])}\n📟 Oleh: @{user}"
        
    elif cmd == 'kurangi':
        amt = parse_amount(parts[2])
        if amt is None: return bot.reply_to(message, "❌ Jumlah tidak valid.")
        old = data_store["balances"].get(nick, 0)
        data_store["balances"][nick] = old - amt
        msg_text = f"➖ Saldo dikurangi.\n👤 {nick}: {fmt_num(old)} → {fmt_num(data_store['balances'][nick])}\n📟 Oleh: @{user}"
        
    elif cmd == 'bulatkan':
        if not data_store["balances"]: return bot.reply_to(message, "❌ Tidak ada saldo untuk dibulatkan.")
        changes = []
        for n, val in data_store["balances"].items():
            new = bulatkan_ke_kelipatan(val, 100)
            if new != val:
                changes.append(f"👤 {n}: {fmt_num(val)} → {fmt_num(new)}")
                data_store["balances"][n] = new
        msg_text = "🔁 Pembulatan ke kelipatan 100:\n" + "\n".join(changes) + f"\n\n📟 Oleh: @{user}" if changes else "✅ Semua saldo sudah bulat."
        save_state()
        msg = bot.send_message(chat_id, msg_text)
        try_pin_message(chat_id, msg.message_id)
        return
        
    elif cmd == 'wd':
        saldo = data_store["balances"].get(nick, 0)
        msg_text = f"💳 Saldo {nick}: {fmt_num(saldo)}" if saldo > 0 else (f"⚠️ Hutang {nick}: {fmt_num(abs(saldo))}" if saldo < 0 else f"❌ {nick} tidak punya saldo tercatat.")
        bot.reply_to(message, msg_text)
        return

    save_state()
    msg = bot.send_message(chat_id, msg_text)
    try_pin_message(chat_id, msg.message_id)

# ============== /sewa OTOMATIS & /upgrade ==============
@bot.message_handler(commands=['sewa'])
def cmd_sewa(message):
    bot.reply_to(message, "💎 *AKSES PREMIUM*\n\nSilakan pilih paket di bawah ini:", parse_mode="Markdown", reply_markup=sewa_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("sewa_"))
def cb_sewa(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    cid = str(chat_id)
    
    if call.data == "sewa_1":
        days, harga, paket = 1, "7.000", "XVIP 1 Hari"
    elif call.data == "sewa_3":
        days, harga, paket = 3, "20.000", "XVIP 3 Hari"
    elif call.data == "sewa_p":
        days, harga, paket = 0, "50.000", "XVIP Permanen"
    elif call.data == "sewa_cek":
        if cid in data_store["premium_groups"]:
            exp = data_store["premium_groups"][cid]
            if exp == 0:
                text = "📊 Status: *PERMANEN* (Aktif Selamanya)"
            else:
                remaining = int((exp - time.time()) / 86400)
                text = f"📊 Status: *AKTIF*\nSisa masa aktif: {remaining} hari" if remaining > 0 else "📊 Status: *EXPIRED* (Sudah habis)"
        else:
            text = "📊 Status: *BELUM AKTIF*"
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, text, parse_mode="Markdown")
        return
    else:
        return

    # Simpan data sementara user yang ingin bayar
    data_store["pending_payment"][str(user_id)] = {
        "chat_id": chat_id,
        "days": days,
        "harga": harga,
        "paket": paket
    }
    save_state()

    caption = (
        f"📷 *PEMBAYARAN TIER XVIP*\n\n"
        f"📦 Paket: {paket}\n"
        f"💰 Total Bayar: *Rp {harga}*\n\n"
        f"1. Scan QRIS di atas menggunakan e-wallet/m-banking apapun.\n"
        f"2. Pastikan nominal sesuai dengan harga paket.\n"
        f"3. *Kirimkan foto bukti pembayaran KE CHAT INI.*\n"
    )
    
    if os.path.exists(QRIS_PHOTO_PATH):
        with open(QRIS_PHOTO_PATH, 'rb') as photo:
            bot.send_photo(chat_id, photo, caption=caption, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, f"{caption}\n(Maaf, foto QRIS belum diupload.)", parse_mode="Markdown")
    
    bot.answer_callback_query(call.id, "QRIS dikirim! Silakan lakukan pembayaran.")

# Handler untuk menangkap foto bukti pembayaran
@bot.message_handler(content_types=['photo', 'document'])
def handle_payment_proof(message):
    user_id = str(message.from_user.id)
    
    if user_id in data_store["pending_payment"]:
        data = data_store["pending_payment"][user_id]
        group_id = data["chat_id"]
        days = data["days"]
        harga = data["harga"]
        paket = data["paket"]
        username = message.from_user.username or message.from_user.first_name

        notif_text = (
            f"🔔 *PEMBAYARAN BARU MASUK*\n\n"
            f"👤 User: @{username}\n"
            f"🆔 ID: `{group_id}`\n"
            f"📦 Paket: {paket}\n"
            f"💰 Jumlah: *Rp {harga}*\n\n"
            f"Ketik command ini untuk mengaktifkan:\n"
            f"`/upgrade {group_id} XVIP {days}`"
        )

        # Teruskan foto ke Admin
        for admin_id in ADMIN_IDS:
            try:
                if message.photo:
                    file_id = message.photo[-1].file_id
                    bot.send_photo(admin_id, file_id, caption=notif_text, parse_mode="Markdown")
                elif message.document:
                    file_id = message.document.file_id
                    bot.send_document(admin_id, file_id, caption=notif_text, parse_mode="Markdown")
            except Exception as e:
                print(f"Gagal kirim notif ke admin {admin_id}: {e}")

        # Hapus data pending user
        del data_store["pending_payment"][user_id]
        save_state()

        # Balas ke user
        bot.reply_to(message, "✅ *Bukti pembayaran telah dikirim ke admin.*\n\nMohon tunggu verifikasi maksimal 5 menit hingga premium aktif.", parse_mode="Markdown")

@bot.message_handler(commands=['upgrade'])
def cmd_upgrade(message):
    if message.from_user.id not in ADMIN_IDS:
        return bot.reply_to(message, "❌ Hanya admin bot yang bisa menggunakan command ini.")
    
    parts = message.text.split()
    if len(parts) < 4:
        return bot.reply_to(message, "❌ Format: /upgrade [group_id] XVIP [hari]\nContoh: /upgrade -100123456789 XVIP 30\nGunakan 0 untuk permanen.")
    
    try:
        target_group_id = parts[1]
        paket_name = parts[2].upper()
        days = int(parts[3])
    except:
        return bot.reply_to(message, "❌ Format tidak valid.")
    
    cid = target_group_id
    if days == 0:
        data_store["premium_groups"][cid] = 0
        text = "✅ Grup ini sekarang berstatus *PERMANEN*!"
    else:
        current_exp = data_store["premium_groups"].get(cid, time.time())
        if current_exp < time.time(): current_exp = time.time()
        data_store["premium_groups"][cid] = current_exp + (days * 86400)
        text = f"✅ Grup {cid} ({paket_name}) diaktifkan selama *{days} hari*!"
    
    save_state()
    try:
        bot.send_message(int(cid), f"🎉 *Premium {paket_name} Aktif!*\n\nGrup ini telah diaktifkan premium oleh Admin.", parse_mode="Markdown")
    except:
        pass
        
    bot.reply_to(message, text, parse_mode="Markdown")

# ============== /help ==============
@bot.message_handler(commands=['help', 'start'])
def cmd_help(message):
    bot.reply_to(message,
        "📖 *PANDUAN BOT REKAP WIN*\n\n"
        "1️⃣ Format Input Data Duel:\n"
        "```\nK:\nSIGMA 100\nB:\nFIRMA 50\n```\n\n"
        "2️⃣ Perintah Utama:\n"
        "• Balas data duel → /rekap [fee]\n"
        "• Contoh: /rekap 5.5\n\n"
        "3️⃣ Fitur Saldo:\n"
        "• /resetlw - Reset game\n"
        "• /lunas [user] - Lunasi hutang\n"
        "• /tambah [user] [jumlah]\n"
        "• /kurangi [user] [jumlah]\n"
        "• /depo [user] [jumlah]\n"
        "• /wd [user] - Cek saldo\n"
        "• /bulatkan - Bulatkan ke 100\n\n"
        "4️⃣ Fitur Premium:\n"
        "• /sewa - Beli premium (QRIS)\n"
        "• /upgrade [id] [paket] [hari] - (Khusus Admin)\n\n"
        "❗ Bot harus jadi admin untuk pin pesan.",
        parse_mode="Markdown")

if __name__ == "__main__":
    print("🤖 Bot Rekap Win berjalan...")
    bot.infinity_polling()
