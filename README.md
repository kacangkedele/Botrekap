# Botrekap
I Created a RECAP Bot in TELEGRAM WITH BUTTON TOOLS 
***

```markdown
# 🤖 BOT REKAP By Angga Official

Bot Telegram premium yang dirancang khusus untuk merekapitulasi hasil duel (seperti Domino Higgs), manajemen saldo pemain secara otomatis, sistem sewa grup, dan pembayaran via QRIS. 

Dibuat dengan sistem interaktif tombol (Inline Button) agar mudah digunakan oleh semua member grup.

[![YouTube](https://img.shields.io/badge/YouTube-Angga%20Official-red?style=for-the-badge&logo=youtube)](https://youtube.com/@AnggaOfficial)
[![Telegram](https://img.shields.io/badge/Telegram-Bot%20Rekap-blue?style=for-the-badge&logo=telegram)](https://t.me/YourBotUsername)

---

## 🌟 Fitur Utama

- 📊 **Parsing Data Duel Otomatis:** Mendukung format data duel simbolik (`⭐ K: 0 = 0`, `K -10000 ALL // ECER`).
- 🏆 **Sistem Skor & Fee:** Menghitung pemenang, skor (2-0 / 2-1), dan potongan fee otomatis dari kemenangan.
- 💰 **Manajemen Saldo:** Melunasi hutang, menambah/mengurangi saldo, deposit, dan cek saldo pemain.
- 🔁 **Auto Bulatkan:** Pembulatan saldo otomatis ke kelipatan 100 ratus.
- 📌 **Auto Pin Pesan:** Bot otomatis menyematkan (pin) pesan hasil rekap agar mudah dilihat anggota grup.
- 💎 **Sistem Sewa (Premium):** Grup dengan < 500 member diwajibkan beli akses premium. Dilengkapi dengan menu pembelian dan aktivasi oleh admin.
- 📷 **Pembayaran QRIS:** Bot dapat mengirimkan foto QRIS secara otomatis saat user memilih opsi pembayaran.

---

## 🛠️ Cara Instalasi di Termux (Android)

Bot ini direkomendasikan untuk dijalankan di Termux (Android) atau VPS Linux. Berikut adalah langkah-langkah instalasi di Termux:

**1. Update & Install Dependency**
Buka aplikasi Termux, lalu ketik perintah berikut secara berurutan:
```bash
pkg update && pkg upgrade -y
pkg install python -y
pkg install nano -y
pkg install git -y
```

**2. Install Library Python**
Install library `pyTelegramBotAPI` yang digunakan untuk berkomunikasi dengan API Telegram:
```bash
pip install pyTelegramBotAPI
```

**3. Buat File Bot & Masukkan Kode**
Buat file baru bernama `bot_rekap.py`:
```bash
nano bot_rekap.py
```
*Salin seluruh kode bot ke dalam layar nano tersebut.*

**4. Konfigurasi Bot**
Di dalam kode, cari dan ubah bagian berikut:
```python
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Ganti dengan token dari @BotFather
ADMIN_IDS = [123456789]            # Ganti dengan ID Telegram Anda
```
Simpan file tersebut dengan cara: 
- Tekan `Volume Naik + E` (bersamaan), lalu lepas.
- Ketik huruf `O` (untuk save), tekan `Enter`.
- Ketik huruf `X` (untuk keluar dari nano).

**5. Siapkan Foto QRIS**
Siapkan foto QRIS Anda, lalu ubah nama file-nya menjadi `qris.jpg`. Letakkan file tersebut di folder yang sama persis dengan `bot_rekap.py` di Termux.

**6. Jalankan Bot**
```bash
python bot_rekap.py
```
Jika muncul tulisan `🤖 Bot Rekap Win berjalan...`, berarti bot sudah aktif!

---

## 🚀 Menjalankan Bot di Background (Agar Tetap Hidup)

Agar bot tidak mati saat Termux dikecilkan atau HP tertidur, gunakan `tmux`:

1. Hentikan bot yang sedang berjalan (Tekan `CTRL + C` atau `Volume Bawah + C`).
2. Install tmux:
   ```bash
   pkg install tmux -y
   ```
3. Jalankan sesi baru bernama "bot":
   ```bash
   tmux new -s bot
   ```
4. Jalankan bot di dalam tmux:
   ```bash
   python bot_rekap.py
   ```
5. Keluar dari layar tanpa mematikan bot (Detach): 
   - Tekan `Volume Naik + B`, lalu lepas, lalu tekan tombol `D`.

*Untuk masuk kembali melihat log bot, ketik perintah:* `tmux attach -t bot`

---

## 📖 Panduan Penggunaan

### 1️⃣ Format Input Data Duel
Kirim pesan data duel dengan format berikut:
```text
⭐ K: 0 = 0
⭐ 🔒 B: 10000 = 10000

🐠 K kurang 10000 untuk samakan B

💰 Saldo seharusnya: 10000 K

K -10000 ALL // ECER
```

### 2️⃣ Cara Melakukan Rekap
1. Balas pesan data duel di atas.
2. Ketik `/rekap [fee]` (Contoh: `/rekap 5.5` untuk fee 5.5%).
3. Bot akan memunculkan tombol interaktif. Pilih:
   - Tim Pemenang (KECIL / BESAR)
   - Skor (2-0 / 2-1)
   - Browser (Jika belum diatur)
   - Ketik nama Device (Jika belum diatur)
4. Bot akan mengirim hasil rekap dan otomatis menyematkannya (pin) di grup.

### 3️⃣ Daftar Perintah Bot
| Perintah | Fungsi |
| :--- | :--- |
| `/rekap [fee]` | Merekap data duel (balas pesan data) |
| `/resetlw` | Mereset history dan memulai game baru |
| `/lunas [user]` | Melunasi seluruh hutang pemain |
| `/tambah [user] [jumlah]` | Menambah saldo pemain |
| `/kurangi [user] [jumlah]` | Mengurangi saldo pemain |
| `/depo [user] [jumlah]` | Deposit saldo pemain |
| `/wd [user]` | Mengecek saldo/hutang pemain |
| `/bulatkan` | Membulatkan semua saldo ke kelipatan 100 |
| `/sewa` | Melihat paket premium & pembayaran QRIS |
| `/aktifkan [hari]` | *(Khusus Admin)* Mengaktifkan premium grup |

---

## ⚠️ Catatan Penting
1. **Bot Harus Admin:** Pastikan bot dijadikan admin di grup agar fitur *Pin Pesan* berfungsi.
2. **File State:** Bot akan otomatis membuat file `bot_state.json` untuk menyimpan data saldo dan sewa. Jangan hapus file ini agar data tidak hilang saat bot direstart.
3. **Baterai & RAM:** Sistem Android terkadang mematikan aplikasi Termux di background. Untuk penggunaan 24/7 tanpa henti, disarankan menyewa VPS (Virtual Private Server).

---

## 📲 Connect With Me

Jangan lupa untuk subscribe, like, dan share agar saya semangat mengupdate bot ini!

- 📺 **YouTube:** [Angga Official](https://youtube.com/@bacotamatpro03)
- 📱 **TikTok:** [@AnggaOfficial](https://tiktok.com/@AnggaOfficial)
- 📸 **Instagram:** [@angga](https://instagram.com/angga.official)
- 💬 **Telegram:** [@HanzModeGalau](https://t.me/HanzModeGalau)

*(Silakan ganti link di atas dengan link sosial media Anda yang sebenarnya)*

---
© 2024 Bot Rekap By Angga Official. All Rights Reserved.
```
