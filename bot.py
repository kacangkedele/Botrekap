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
QRIS_PHOTO_PATH = "qris.jpg"  # Pastikan file qris.jpg ada di folder yang sama

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
            }, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving state: {e}")

load_state()

# ============== PARSER ==============
def parse_duel_data(text):
    data = {"k_total": 0, "b_total": 0, "loser_team": None, "winner_team": None, "loser_nicks": [], "winner_nicks": [], "base_amount": 0}
    for line in text.split('\n'):
        line = line.strip()
        if not line: continue
        match_k = re.search(r'K\s*:\s*(-?\d+)\s*=\s*(-?\d+)', line, re.IGNORECASE)
        if match_k:
            data["k_total"] = int(match_k.group(1))
            continue
        match_b = re.search(r'B\s*:\s*(-?\d+)\s*=\s*(-?\d+)', line, re.IGNORECASE)
        if match_b:
            data["b_total"] = int(match_b.group(1))
            continue
        match_player = re.match(r'^(K|B)\s+(-?\d+)\s+(.+)', line, re.IGNORECASE)
        if match_player:
            team_char = match_player.group(1).upper()
            data["loser_team"] = "KECIL" if team_char == "K" else "BESAR"
            data["winner_team"] = "BESAR" if data["loser_team"] == "KECIL" else "KECIL"
            data["base_amount"] = abs(int(match_player.group(2)))
            rest = match_player.group(3).strip()
            if "//" in rest:
                l_part, w_part = rest.split("//", 1)
                data["loser_nicks"] = [n.strip() for n in l_part.split(',') if n.strip()]
                try:
                    int(w_part.replace(".", "").replace(",", ""))
                    data["winner_nicks"] = []
                except:
                    data["winner_nicks"] = [n.strip() for n in w_part.split(',') if n.strip()]
            else:
                data["loser_nicks"] = [n.strip() for n in rest.split(',') if n.strip()]
                data["winner_nicks"] = []
    return data

# ============== HELPER ==============
def is_premium(chat_id):
    cid = str(chat_id)
    if cid not in data_store["premium_groups"]:
        return False
    expiry = data_store["premium_groups"][cid]
    if expiry == 0:
        return True
    if time.time() < expiry:
        return True
    else:
        del data_store["premium_groups"][cid]
        save_state()
        return False

def get_chat_setting(chat_id, key):
    cs = data_store["chat_settings"].get(str(chat_id), {})
    return cs.get(key) or data_store.get(key)

def set_chat_setting(chat_id, key, value):
    cid = str(chat_id)
    if cid not in data_store["chat_settings"]:
        data_store["chat_settings"][cid] = {}
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
    except Exception as e: print(f"Pin failed: {e}")

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
        types.InlineKeyboardButton("1 Bulan (Rp 50.000)", callback_data="sewa_1"),
        types.InlineKeyboardButton("3 Bulan (Rp 120.000)", callback_data="sewa_3"),
        types.InlineKeyboardButton("Permanen (Rp 300.000)", callback_data="sewa_p"),
        types.InlineKeyboardButton("📷 Bayar via QRIS", callback_data="sewa_qris"),
        types.InlineKeyboardButton("📊 Cek Status Sewa", callback_data="sewa_cek")
    )
    return kb

def qris_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("QRIS 1 Bulan (50K)", callback_data="qris_1"),
        types.InlineKeyboardButton("QRIS 3 Bulan (120K)", callback_data="qris_3"),
        types.InlineKeyboardButton("QRIS Permanen (300K)", callback_data="qris_p"),
        types.InlineKeyboardButton("⬅️ Kembali", callback_data="sewa_back")
    )
    return kb

# ============== /rekap ==============
@bot.message_handler(commands=['rekap'])
def cmd_rekap(message):
    chat_id = message.chat.id
    user = message.from_user

    if message.chat.type not in ("group", "supergroup"):
        bot.reply_to(message, "❌ Command ini hanya untuk grup.")
        return

    if not is_premium(chat_id):
        try: member_count = bot.get_chat_member_count(chat_id)
        except: member_count = 0
        if member_count < MIN_MEMBER_PREMIUM:
            bot.reply_to(message, f"❌ Fitur premium. Butuh minimal {MIN_MEMBER_PREMIUM} member atau beli akses.\nGunakan /sewa untuk membeli premium.")
            return

    if not message.reply_to_message:
        bot.reply_to(message, "❌ Balas pesan data duel, lalu kirim /rekap [fee]")
        return

    src = message.reply_to_message.text
    if not src:
        bot.reply_to(message, "❌ Pesan yang dibalas bukan teks data duel.")
        return

    parsed = parse_duel_data(src)
    if not parsed["loser_team"] or not parsed["loser_nicks"]:
        bot.reply_to(message, "❌ Gagal parse data duel. Cek format:\n⭐ K: 0 = 0\n⭐ B: 10000 = 10000\nK -10000 ALL // ECER")
        return

    fee = 0.0
    parts = message.text.split()
    if len(parts) > 1:
        try: fee = float(parts[1].replace(",", "."))
        except:
            bot.reply_to(message, "❌ Fee tidak valid. Contoh: /rekap 5.5")
            return

    key = f"{chat_id}:{user.id}"
    data_store["pending_rekap"][key] = {
        "parsed_data": parsed, "fee": fee, "winner": None, "score": None,
        "browser": None, "device": None, "source_msg_id": message.reply_to_message.message_id,
        "chat_id": chat_id, "user_id": user.id, "username": user.username or user.first_name, "step": "winner",
    }

    summary = render_duel_summary(parsed, fee)
    bot.reply_to(message, f"📊 *DATA DUEL DITERIMA*\n\n{summary}\n\n👉 Pilih tim pemenang:", parse_mode="Markdown", reply_markup=winner_keyboard())

def render_duel_summary(parsed, fee):
    lines = [
        f"K Total: {fmt_num(parsed['k_total'])}",
        f"B Total: {fmt_num(parsed['b_total'])}",
        f"Base Amount: {fmt_num(parsed['base_amount'])}"
    ]
    if parsed['loser_nicks']: lines.append(f"Loser: {', '.join(parsed['loser_nicks'])}")
    if parsed['winner_nicks']: lines.append(f"Winner: {', '.join(parsed['winner_nicks'])}")
    lines.append(f"💰 Fee: {fee}%")
    return "\n".join(lines)

# ============== CALLBACK REKAP ==============
@bot.callback_query_handler(func=lambda c: c.data.startswith("rw_win_"))
def cb_winner(call):
    key = f"{call.message.chat.id}:{call.from_user.id}"
    pr = data_store["pending_rekap"].get(key)
    if not pr:
        bot.answer_callback_query(call.id, "Sesi tidak ditemukan. Ulangi /rekap")
        return
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

# ============== FINALIZE & HITUNG ==============
def finalize_rekap(pr, chat_id, edit_msg_id):
    parsed = pr["parsed_data"]
    winner = pr["winner"]
    score = pr["score"]
    fee_pct = pr["fee"]
    
    loser_team = "BESAR" if winner == "KECIL" else "KECIL"
    base_amount = parsed["base_amount"] if parsed["base_amount"] > 0 else abs(parsed["k_total"] - parsed["b_total"])
    multiplier = 2.0 if score == "2-0" else 1.0
    prize_pool = int(base_amount * multiplier)

    saldo_lines_win, saldo_lines_lose = [], []

    if parsed["loser_team"] == loser_team:
        loser_nicks, winner_nicks = parsed["loser_nicks"], parsed["winner_nicks"]
    else:
        loser_nicks, winner_nicks = parsed["winner_nicks"], parsed["loser_nicks"]

    for nick in loser_nicks:
        current = data_store["balances"].get(nick.lower(), 0)
        data_store["balances"][nick.lower()] = current - prize_pool
        saldo_lines_lose.append(f"{nick} -{fmt_num(prize_pool)}")

    for nick in winner_nicks:
        current = data_store["balances"].get(nick.lower(), 0)
        net_winning = int(prize_pool * (1 - fee_pct/100)) if fee_pct > 0 else prize_pool
        data_store["balances"][nick.lower()] = current + net_winning
        saldo_lines_win.append(f"{nick} {fmt_num(net_winning)}")

    for nick in list(data_store["balances"].keys()):
        data_store["balances"][nick] = bulatkan_ke_kelipatan(data_store["balances"][nick])

    total_saldo = sum(v for v in data_store["balances"].values() if v > 0)
    total_modal = parsed["k_total"] + parsed["b_total"]

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
    
    if cmd in ['lunas', 'wd'] and len(parts) < 2:
        return bot.reply_to(message, f"❌ Format: /{cmd} [username]")
    if cmd in ['tambah', 'kurangi', 'depo'] and len(parts) < 3:
        return bot.reply_to(message, f"❌ Format: /{cmd} [username] [jumlah]")

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

# ============== /sewa & AKTIVASI ==============
@bot.message_handler(commands=['sewa'])
def cmd_sewa(message):
    bot.reply_to(message, "💎 *AKSES PREMIUM*\n\nPilih paket di bawah ini untuk melihat cara pembayaran:", parse_mode="Markdown", reply_markup=sewa_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("sewa_"))
def cb_sewa(call):
    cid = str(call.message.chat.id)
    
    if call.data == "sewa_1":
        text = "Anda memilih paket *1 Bulan (Rp 50.000)*.\n\nSilakan transfer ke:\nDana/Ovo: 085xxx\n\nAtau gunakan /sewa lalu pilih *Bayar via QRIS*.\n\nSetelah transfer, kirim bukti ke admin lalu admin akan mengetik `/aktifkan 30` di grup ini."
    elif call.data == "sewa_3":
        text = "Anda memilih paket *3 Bulan (Rp 120.000)*.\n\nSilakan transfer ke:\nDana/Ovo: 085xxx\n\nAtau gunakan /sewa lalu pilih *Bayar via QRIS*.\n\nSetelah transfer, kirim bukti ke admin lalu admin akan mengetik `/aktifkan 90` di grup ini."
    elif call.data == "sewa_p":
        text = "Anda memilih paket *Permanen (Rp 300.000)*.\n\nSilakan transfer ke:\nDana/Ovo: 085xxx\n\nAtau gunakan /sewa lalu pilih *Bayar via QRIS*.\n\nSetelah transfer, kirim bukti ke admin lalu admin akan mengetik `/aktifkan 0` di grup ini."
    elif call.data == "sewa_qris":
        text = "📷 *Pembayaran via QRIS*\n\nSilakan pilih paket di bawah ini. Bot akan mengirimkan gambar QRIS untuk kamu scan."
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=qris_keyboard())
        return
    elif call.data == "sewa_back":
        text = "💎 *AKSES PREMIUM*\n\nPilih paket di bawah ini untuk melihat cara pembayaran:"
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=sewa_keyboard())
        return
    elif call.data == "sewa_cek":
        if cid in data_store["premium_groups"]:
            exp = data_store["premium_groups"][cid]
            if exp == 0:
                text = "📊 Status: *PERMANEN* (Aktif Selamanya)"
            else:
                remaining = int((exp - time.time()) / 86400)
                if remaining > 0:
                    text = f"📊 Status: *AKTIF*\nSisa masa aktif: {remaining} hari"
                else:
                    text = "📊 Status: *EXPIRED* (Sudah habis)"
        else:
            text = "📊 Status: *BELUM AKTIF*"
    
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("qris_"))
def cb_qris(call):
    paket = call.data.split("qris_")[1]
    
    if paket == "1":
        harga = "50.000"
        hari = "1 Bulan"
    elif paket == "3":
        harga = "120.000"
        hari = "3 Bulan"
    elif paket == "p":
        harga = "300.000"
        hari = "Permanen"
        
    caption = (
        f"📷 *QRIS PEMBAYARAN*\n\n"
        f"Paket: {hari}\n"
        f"Total Bayar: *Rp {harga}*\n\n"
        f"1. Scan QRIS di atas menggunakan e-wallet/m-banking apapun.\n"
        f"2. Pastikan nominal sesuai dengan harga paket.\n"
        f"3. Setelah bayar, kirim bukti transfer ke admin.\n"
        f"4. Admin akan mengetik `/aktifkan [hari]` di grup ini untuk mengaktifkan premium."
    )
    
    if os.path.exists(QRIS_PHOTO_PATH):
        with open(QRIS_PHOTO_PATH, 'rb') as photo:
            bot.send_photo(call.message.chat.id, photo, caption=caption, parse_mode="Markdown")
    else:
        bot.send_message(call.message.chat.id, f"{caption}\n\n(Maaf, foto QRIS belum diupload oleh admin. Silakan hubungi admin langsung.)", parse_mode="Markdown")
        
    bot.answer_callback_query(call.id, "QRIS dikirim!")

@bot.message_handler(commands=['aktifkan'])
def cmd_aktifkan(message):
    if message.from_user.id not in ADMIN_IDS:
        return bot.reply_to(message, "❌ Hanya admin bot yang bisa mengaktifkan sewa.")
    
    if message.chat.type not in ("group", "supergroup"):
        return bot.reply_to(message, "❌ Gunakan command ini di dalam grup yang ingin diaktifkan.")
    
    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(message, "❌ Format: /aktifkan [jumlah_hari]\nContoh: /aktifkan 30\nGunakan 0 untuk permanen.")
    
    try:
        days = int(parts[1])
    except:
        return bot.reply_to(message, "❌ Jumlah hari harus berupa angka.")
    
    cid = str(message.chat.id)
    if days == 0:
        data_store["premium_groups"][cid] = 0
        text = "✅ Grup ini sekarang berstatus *PERMANEN*!"
    else:
        current_exp = data_store["premium_groups"].get(cid, time.time())
        if current_exp < time.time(): current_exp = time.time()
        data_store["premium_groups"][cid] = current_exp + (days * 86400)
        text = f"✅ Grup ini diaktifkan selama *{days} hari*!"
    
    save_state()
    bot.reply_to(message, text, parse_mode="Markdown")

# ============== /help ==============
@bot.message_handler(commands=['help', 'start'])
def cmd_help(message):
    bot.reply_to(message,
        "📖 *PANDUAN BOT REKAP WIN*\n\n"
        "1️⃣ Format Input Data Duel:\n"
        "```\n⭐ K: 0 = 0\n⭐ 🔒 B: 10000 = 10000\nK -10000 ALL // ECER\n```\n\n"
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
        "• /sewa - Beli premium (Dana/Ovo/QRIS)\n"
        "• /aktifkan [hari] - (Khusus Admin)\n\n"
        "❗ Bot harus jadi admin untuk pin pesan.",
        parse_mode="Markdown")

if __name__ == "__main__":
    print("🤖 Bot Rekap Win berjalan...")
    bot.infinity_polling()
