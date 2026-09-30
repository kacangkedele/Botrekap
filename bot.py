import telebot
from telebot import types
import re
import json
import os
from collections import defaultdict

# ============== KONFIGURASI ==============
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Ganti dengan token bot Anda
ADMIN_IDS = [123456789]  # Ganti dengan ID admin
MIN_MEMBER_PREMIUM = 500

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# ============== STORAGE ==============
STATE_FILE = "bot_state.json"

data_store = {
    "last_win": None,
    "balances": {},
    "browser": None,
    "device": None,
    "pending_rekap": {},
    "premium_groups": set(),
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
                data_store["premium_groups"] = set(saved.get("premium_groups", []))
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
                "premium_groups": list(data_store["premium_groups"]),
                "chat_settings": data_store["chat_settings"],
            }, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving state: {e}")

load_state()

# ============== PARSER BARU ==============
def parse_duel_data(text):
    data = {
        "k_total": 0,
        "b_total": 0,
        "loser_team": None,
        "winner_team": None,
        "loser_nicks": [],
        "winner_nicks": [],
        "base_amount": 0
    }
    
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Cari total KECIL (K: 0 = 0)
        match_k = re.search(r'K\s*:\s*(-?\d+)\s*=\s*(-?\d+)', line, re.IGNORECASE)
        if match_k:
            data["k_total"] = int(match_k.group(1))
            continue
            
        # Cari total BESAR (B: 10000 = 10000)
        match_b = re.search(r'B\s*:\s*(-?\d+)\s*=\s*(-?\d+)', line, re.IGNORECASE)
        if match_b:
            data["b_total"] = int(match_b.group(1))
            continue
            
        # Cari baris detail pemain (K -10000 ALL // ECER)
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
                # Cek apakah bagian setelah // adalah angka (hasil) atau nama pemain
                try:
                    int(w_part.replace(".", "").replace(",", ""))
                    data["winner_nicks"] = []  # Jika angka, berarti itu hasil, bukan nick pemenang
                except:
                    data["winner_nicks"] = [n.strip() for n in w_part.split(',') if n.strip()]
            else:
                data["loser_nicks"] = [n.strip() for n in rest.split(',') if n.strip()]
                data["winner_nicks"] = []
                
    return data

# ============== HELPER ==============
def is_premium(chat_id):
    return chat_id in data_store["premium_groups"]

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
    try:
        return f"{int(n):,}".replace(",", ".")
    except:
        return str(n)

def parse_amount(s):
    s = str(s).strip().replace(".", "").replace(",", "")
    try:
        return int(s)
    except:
        return None

def bulatkan_ke_kelipatan(n, kelipatan=100):
    return int(round(n / kelipatan) * kelipatan)

def try_pin_message(chat_id, message_id):
    try:
        bot.pin_chat_message(chat_id, message_id, disable_notification=True)
    except Exception as e:
        print(f"Pin failed: {e}")

# ============== KEYBOARDS ==============
def winner_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🏆 KECIL", callback_data="rw_win_KECIL"),
        types.InlineKeyboardButton("🏆 BESAR", callback_data="rw_win_BESAR"),
    )
    return kb

def score_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("2 - 0", callback_data="rw_score_2-0"),
        types.InlineKeyboardButton("2 - 1", callback_data="rw_score_2-1"),
    )
    return kb

def browser_keyboard():
    kb = types.InlineKeyboardMarkup(row_width=2)
    options = ["Chrome", "Firefox", "Safari", "Edge", "Opera", "Kiwi"]
    buttons = [types.InlineKeyboardButton(b, callback_data=f"rw_browser_{b}") for b in options]
    kb.add(*buttons)
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
        try:
            member_count = bot.get_chat_member_count(chat_id)
        except:
            member_count = 0
        if member_count < MIN_MEMBER_PREMIUM:
            bot.reply_to(message,
                f"❌ Fitur premium. Butuh minimal {MIN_MEMBER_PREMIUM} member atau beli akses.\n"
                f"Gunakan /sewa untuk membeli premium.")
            return
        else:
            data_store["premium_groups"].add(chat_id)
            save_state()

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
        try:
            fee = float(parts[1].replace(",", "."))
        except:
            bot.reply_to(message, "❌ Fee tidak valid. Contoh: /rekap 5.5")
            return

    key = f"{chat_id}:{user.id}"
    data_store["pending_rekap"][key] = {
        "parsed_data": parsed,
        "fee": fee,
        "winner": None,
        "score": None,
        "browser": None,
        "device": None,
        "source_msg_id": message.reply_to_message.message_id,
        "chat_id": chat_id,
        "user_id": user.id,
        "username": user.username or user.first_name,
        "step": "winner",
    }

    summary = render_duel_summary(parsed, fee)
    bot.reply_to(message,
        f"📊 *DATA DUEL DITERIMA*\n\n{summary}\n\n👉 Pilih tim pemenang:",
        parse_mode="Markdown",
        reply_markup=winner_keyboard())

def render_duel_summary(parsed, fee):
    lines = []
    lines.append(f"K Total: {fmt_num(parsed['k_total'])}")
    lines.append(f"B Total: {fmt_num(parsed['b_total'])}")
    lines.append(f"Base Amount: {fmt_num(parsed['base_amount'])}")
    if parsed['loser_nicks']:
        lines.append(f"Loser: {', '.join(parsed['loser_nicks'])}")
    if parsed['winner_nicks']:
        lines.append(f"Winner: {', '.join(parsed['winner_nicks'])}")
    lines.append(f"💰 Fee: {fee}%")
    return "\n".join(lines)

# ============== CALLBACK HANDLERS ==============
@bot.callback_query_handler(func=lambda c: c.data.startswith("rw_win_"))
def cb_winner(call):
    key = f"{call.message.chat.id}:{call.from_user.id}"
    pr = data_store["pending_rekap"].get(key)
    if not pr:
        bot.answer_callback_query(call.id, "Sesi tidak ditemukan. Ulangi /rekap")
        return
    winner = call.data.split("rw_win_")[1]
    pr["winner"] = winner
    pr["step"] = "score"
    save_state()
    bot.edit_message_text(
        f"✅ Pemenang: *{winner}*\n\nPilih skor:",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="Markdown",
        reply_markup=score_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rw_score_"))
def cb_score(call):
    key = f"{call.message.chat.id}:{call.from_user.id}"
    pr = data_store["pending_rekap"].get(key)
    if not pr:
        bot.answer_callback_query(call.id, "Sesi tidak ditemukan")
        return
    score = call.data.split("rw_score_")[1]
    pr["score"] = score
    save_state()
    chat_id = call.message.chat.id
    browser = get_chat_setting(chat_id, "browser")
    device = get_chat_setting(chat_id, "device")
    if browser and device:
        pr["browser"] = browser
        pr["device"] = device
        pr["step"] = "done"
        save_state()
        bot.edit_message_text(
            f"✅ Skor: {score}\n🌐 Browser: {browser}\n📱 Device: {device}\n\n⏳ Memproses rekap...",
            chat_id=chat_id,
            message_id=call.message.message_id)
        finalize_rekap(pr, chat_id, call.message.message_id)
    else:
        pr["step"] = "browser"
        save_state()
        bot.edit_message_text(
            f"✅ Skor: {score}\n\n🌐 Pilih browser:",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=browser_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("rw_browser_"))
def cb_browser(call):
    key = f"{call.message.chat.id}:{call.from_user.id}"
    pr = data_store["pending_rekap"].get(key)
    if not pr:
        bot.answer_callback_query(call.id, "Sesi tidak ditemukan")
        return
    browser = call.data.split("rw_browser_")[1]
    pr["browser"] = browser
    set_chat_setting(call.message.chat.id, "browser", browser)
    device = get_chat_setting(call.message.chat.id, "device")
    if device:
        pr["device"] = device
        pr["step"] = "done"
        save_state()
        bot.edit_message_text(
            f"🌐 Browser: {browser}\n📱 Device: {device}\n\n⏳ Memproses...",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id)
        finalize_rekap(pr, call.message.chat.id, call.message.message_id)
    else:
        pr["step"] = "device"
        save_state()
        bot.edit_message_text(
            f"🌐 Browser: {browser}\n\n📱 Ketik nama device:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id)

@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'), content_types=['text'])
def catch_device_input(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    key = f"{chat_id}:{user_id}"
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
    
    # Deteksi auto data duel
    if re.search(r'K\s*:\s*(-?\d+)\s*=\s*(-?\d+)', message.text, re.IGNORECASE) or \
       re.search(r'B\s*:\s*(-?\d+)\s*=\s*(-?\d+)', message.text, re.IGNORECASE):
        bot.reply_to(message,
            "✅ Data duel terdeteksi. Balas pesan ini dengan `/rekap [fee]` untuk memproses.",
            parse_mode="Markdown")

# ============== HITUNG HASIL ==============
def finalize_rekap(pr, chat_id, edit_msg_id):
    parsed = pr["parsed_data"]
    winner = pr["winner"]
    score = pr["score"]
    fee_pct = pr["fee"]
    browser = pr["browser"]
    device = pr["device"]

    loser_team = "BESAR" if winner == "KECIL" else "KECIL"
    
    base_amount = parsed["base_amount"]
    if base_amount == 0:
        base_amount = abs(parsed["k_total"] - parsed["b_total"])
        
    multiplier = 2.0 if score == "2-0" else 1.0
    prize_pool = int(base_amount * multiplier)

    changes = {}
    saldo_lines_win = []
    saldo_lines_lose = []

    # Tentukan siapa kalah dan menang berdasarkan input
    if parsed["loser_team"] == loser_team:
        loser_nicks = parsed["loser_nicks"]
        winner_nicks = parsed["winner_nicks"]
    else:
        loser_nicks = parsed["winner_nicks"]
        winner_nicks = parsed["loser_nicks"]

    # Apply balances untuk yang kalah
    for nick in loser_nicks:
        current = data_store["balances"].get(nick.lower(), 0)
        new_saldo = current - prize_pool
        data_store["balances"][nick.lower()] = new_saldo
        saldo_lines_lose.append(f"{nick} -{fmt_num(prize_pool)}")

    # Apply balances untuk yang menang
    for nick in winner_nicks:
        current = data_store["balances"].get(nick.lower(), 0)
        net_winning = prize_pool
        if fee_pct > 0:
            net_winning = int(prize_pool * (1 - fee_pct/100))
        new_saldo = current + net_winning
        data_store["balances"][nick.lower()] = new_saldo
        saldo_lines_win.append(f"{nick} {fmt_num(net_winning)}")

    # Bulatkan semua ke 100
    for nick in list(data_store["balances"].keys()):
        data_store["balances"][nick] = bulatkan_ke_kelipatan(data_store["balances"][nick])

    total_saldo = sum(v for v in data_store["balances"].values() if v > 0)
    total_modal = parsed["k_total"] + parsed["b_total"]

    lw_user = pr.get("username", "Unknown")
    data_store["last_win"] = {
        "username": lw_user,
        "winner": winner,
        "score": score,
        "total_modal": total_modal,
    }
    save_state()

    output = render_rekap_output(
        device=device,
        browser=browser,
        lw_user=lw_user,
        winner=winner,
        score=score,
        total_modal=total_modal,
        total_saldo=total_saldo,
        saldo_lines_win=saldo_lines_win,
        saldo_lines_lose=saldo_lines_lose,
    )

    sent = bot.send_message(chat_id, output)
    try_pin_message(chat_id, sent.message_id)

    del data_store["pending_rekap"][f"{chat_id}:{pr['user_id']}"]
    save_state()

def render_rekap_output(device, browser, lw_user, winner, score, total_modal, total_saldo, saldo_lines_win, saldo_lines_lose):
    lines = []
    lines.append(f"DEV: {device}")
    lines.append(f"ROL: {browser}")
    lines.append("")
    lines.append(f"LAST WIN : (@{lw_user})")
    lines.append(f"GAME 1 : {winner[0]} {score} {fmt_num(total_modal)}")
    lines.append("")
    lines.append(f"SALDO PEMAIN : ({fmt_num(total_saldo)})")
    for s in saldo_lines_win:
        lines.append(s)
    lines.append("")
    for s in saldo_lines_lose:
        lines.append(s)
    return "\n".join(lines)

# ============== /resetlw ==============
@bot.message_handler(commands=['resetlw'])
def cmd_resetlw(message):
    chat_id = message.chat.id
    data_store["last_win"] = None
    data_store["balances"] = {}
    save_state()
    bot.reply_to(message, "✅ History direset. Game baru dimulai.")

# ============== /lunas ==============
@bot.message_handler(commands=['lunas'])
def cmd_lunas(message):
    chat_id = message.chat.id
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ Format: /lunas [username]")
        return
    nick = parts[1].strip().lower()
    if nick not in data_store["balances"]:
        bot.reply_to(message, f"❌ Pemain `{nick}` tidak ditemukan.", parse_mode="Markdown")
        return
    old = data_store["balances"][nick]
    data_store["balances"][nick] = 0
    save_state()
    user = message.from_user.username or message.from_user.first_name
    msg = bot.send_message(chat_id,
        f"✅ Hutang dilunasi.\n👤 {nick}: {fmt_num(old)} → 0\n📟 Oleh: @{user}")
    try_pin_message(chat_id, msg.message_id)

# ============== /tambah ==============
@bot.message_handler(commands=['tambah'])
def cmd_tambah(message):
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "❌ Format: /tambah [username] [jumlah]")
        return
    nick = parts[1].strip().lower()
    amt = parse_amount(parts[2])
    if amt is None:
        bot.reply_to(message, "❌ Jumlah tidak valid.")
        return
    old = data_store["balances"].get(nick, 0)
    data_store["balances"][nick] = old + amt
    save_state()
    user = message.from_user.username or message.from_user.first_name
    msg = bot.send_message(message.chat.id,
        f"➕ Saldo ditambah.\n👤 {nick}: {fmt_num(old)} → {fmt_num(data_store['balances'][nick])}\n📟 Oleh: @{user}")
    try_pin_message(message.chat.id, msg.message_id)

# ============== /kurangi ==============
@bot.message_handler(commands=['kurangi'])
def cmd_kurangi(message):
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "❌ Format: /kurangi [username] [jumlah]")
        return
    nick = parts[1].strip().lower()
    amt = parse_amount(parts[2])
    if amt is None:
        bot.reply_to(message, "❌ Jumlah tidak valid.")
        return
    old = data_store["balances"].get(nick, 0)
    data_store["balances"][nick] = old - amt
    save_state()
    user = message.from_user.username or message.from_user.first_name
    msg = bot.send_message(message.chat.id,
        f"➖ Saldo dikurangi.\n👤 {nick}: {fmt_num(old)} → {fmt_num(data_store['balances'][nick])}\n📟 Oleh: @{user}")
    try_pin_message(message.chat.id, msg.message_id)

# ============== /depo ==============
@bot.message_handler(commands=['depo'])
def cmd_depo(message):
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "❌ Format: /depo [username] [jumlah]")
        return
    nick = parts[1].strip().lower()
    amt = parse_amount(parts[2])
    if amt is None:
        bot.reply_to(message, "❌ Jumlah tidak valid.")
        return
    old = data_store["balances"].get(nick, 0)
    data_store["balances"][nick] = old + amt
    save_state()
    user = message.from_user.username or message.from_user.first_name
    msg = bot.send_message(message.chat.id,
        f"💰 Deposit berhasil.\n👤 {nick}: {fmt_num(old)} → {fmt_num(data_store['balances'][nick])}\n📟 Oleh: @{user}")
    try_pin_message(message.chat.id, msg.message_id)

# ============== /wd ==============
@bot.message_handler(commands=['wd'])
def cmd_wd(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ Format: /wd [username]")
        return
    nick = parts[1].strip().lower()
    saldo = data_store["balances"].get(nick, 0)
    if saldo > 0:
        reply = f"💳 Saldo {nick}: {fmt_num(saldo)}"
    elif saldo < 0:
        reply = f"⚠️ Hutang {nick}: {fmt_num(abs(saldo))}"
    else:
        reply = f"❌ {nick} tidak punya saldo tercatat."
    bot.reply_to(message, reply)

# ============== /bulatkan ==============
@bot.message_handler(commands=['bulatkan'])
def cmd_bulatkan(message):
    if not data_store["balances"]:
        bot.reply_to(message, "❌ Tidak ada saldo untuk dibulatkan.")
        return
    changes = []
    for nick, val in data_store["balances"].items():
        new = bulatkan_ke_kelipatan(val, 100)
        if new != val:
            changes.append(f"👤 {nick}: {fmt_num(val)} → {fmt_num(new)}")
            data_store["balances"][nick] = new
    save_state()
    user = message.from_user.username or message.from_user.first_name
    if changes:
        text = "🔁 Pembulatan ke kelipatan 100:\n" + "\n".join(changes) + f"\n\n📟 Oleh: @{user}"
    else:
        text = "✅ Semua saldo sudah bulat."
    msg = bot.send_message(message.chat.id, text)
    try_pin_message(message.chat.id, msg.message_id)

# ============== /sewa ==============
@bot.message_handler(commands=['sewa'])
def cmd_sewa(message):
    bot.reply_to(message,
        "💎 *AKSES PREMIUM*\n\n"
        "• Grup dengan ≥ 500 member: GRATIS (otomatis)\n"
        "• Beli akses premium:\n"
        "  - 1 Bulan: Rp 50.000\n"
        "  - 3 Bulan: Rp 120.000\n"
        "  - Permanen: Rp 300.000\n\n"
        "Hubungi admin: @admin_username",
        parse_mode="Markdown")

# ============== /help ==============
@bot.message_handler(commands=['help', 'start'])
def cmd_help(message):
    bot.reply_to(message,
        "📖 *PANDUAN BOT REKAP WIN*\n\n"
        "1️⃣ Format Input Data Duel:\n"
        "```\n⭐ K: 0 = 0\n⭐ 🔒 B: 10000 = 10000\nK -10000 ALL // ECER\n```\n\n"
        "2️⃣ Penjelasan Format:\n"
        "• Header: K/B: [total] = [hasil]\n"
        "• Format: [K/B] [jumlah] [nick_kalah] // [nick_menang]\n"
        "• Jika tanpa pemenang: [K/B] [jumlah] [nick] // [hasil]\n\n"
        "3️⃣ Perintah:\n"
        "• Balas data duel → /rekap [fee]\n"
        "• Contoh: /rekap 5.5\n\n"
        "4️⃣ Fitur Tambahan:\n"
        "• /resetlw - Reset game\n"
        "• /lunas [user] - Lunasi hutang\n"
        "• /tambah [user] [jumlah] - Tambah saldo\n"
        "• /kurangi [user] [jumlah] - Kurangi saldo\n"
        "• /depo [user] [jumlah] - Deposit\n"
        "• /wd [user] - Cek saldo\n"
        "• /bulatkan - Bulatkan ke 100\n"
        "• /sewa - Beli premium\n\n"
        "❗ Bot harus jadi admin untuk pin pesan.",
        parse_mode="Markdown")

# ============== MAIN ==============
if __name__ == "__main__":
    print("🤖 Bot Rekap Win berjalan...")
    bot.infinity_polling()https://www.instagram.com/p/Ddf7atyj_Xc/?stkn=ZmJjcmk4YTVlaTIx
