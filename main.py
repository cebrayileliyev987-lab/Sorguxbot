#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# CK SORGUBOT ULTIMATE PRO v7.0 - RENDER FULL EDITION
# @rinexdestek | @cksorgupanel

import os
import sys
import asyncio
import aiohttp
import json
import sqlite3
import random
import ssl
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List

# ==================== TOKEN KONTROL ====================
TOKEN = os.environ.get("BOT_TOKEN", "")
if not TOKEN:
    print("❌ HATA: BOT_TOKEN environment variable bulunamadı!")
    print("Render dashboard'da Environment Variables -> BOT_TOKEN ekleyin")
    sys.exit(1)

ADMIN_IDS = [int(x.strip()) for x in os.environ.get("ADMIN_IDS", "8610336203").split(",")]
REQUIRED_CHANNEL = os.environ.get("REQUIRED_CHANNEL", "@iosstarturkiyee")
CHANNEL_LINK = "https://t.me/cksorgupanel"
SUPPORT_LINK = "https://t.me/rinexdestek"
DB_FILE = "bot_data.db"

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram Import
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember, Bot, InputFile
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ==================== API URL'LER ====================
API_URLS = {
    "tcgsm": {
        "url": "https://arastir.vip/api/tcgsm.php",
        "params": {"tc": "{value}"},
        "name": "🔍 TC'den GSM",
        "example": "12345678901",
        "desc": "TC kimlik numarası ile GSM sorgulama",
        "method": "GET"
    },
    "sulale": {
        "url": "https://arastir.vip/api/sulale.php",
        "params": {"tc": "{value}"},
        "name": "👨‍👩‍👧‍👦 Sülale Sorgu",
        "example": "12345678901",
        "desc": "TC ile aile bireylerini sorgulama",
        "method": "GET"
    },
    "gsmtc": {
        "url": "https://arastir.vip/api/gsmtc.php",
        "params": {"gsm": "{value}"},
        "name": "📞 GSM'den TC",
        "example": "5551234567",
        "desc": "GSM numarası ile TC sorgulama",
        "method": "GET"
    },
    "adsoyad": {
        "url": "https://arastir.vip/api/adsoyad.php",
        "params": {"adi": "{adi}", "soyadi": "{soyadi}"},
        "name": "👤 Ad Soyad Sorgu",
        "example": "Mehmet Yılmaz",
        "multi_param": True,
        "desc": "Ad ve soyad ile kayıt sorgulama",
        "method": "GET"
    },
    "adres": {
        "url": "https://arastir.vip/api/adres.php",
        "params": {"tc": "{value}"},
        "name": "🏠 Adres Sorgu",
        "example": "12345678901",
        "desc": "TC ile adres bilgisi",
        "method": "GET"
    },
    "isyeri": {
        "url": "https://arastir.vip/api/isyeri.php",
        "params": {"tc": "{value}"},
        "name": "🏢 İş Yeri Sorgu",
        "example": "12345678901",
        "desc": "TC ile iş yeri bilgisi",
        "method": "GET"
    },
    "tc": {
        "url": "https://arastir.vip/api/tc.php",
        "params": {"tc": "{value}"},
        "name": "🆔 TC Sorgu",
        "example": "12345678901",
        "desc": "TC kimlik doğrulama",
        "method": "GET"
    },
    "operator": {
        "url": "https://apiservices.alwaysdata.net/apiservices/gncloperator.php",
        "params": {"numara": "{value}"},
        "name": "📡 Operatör Sorgu",
        "example": "5315312472",
        "desc": "GSM operatör bilgisi",
        "method": "GET"
    },
    "iban": {
        "url": "https://rinexibansorguapi.rf.gd/api.php",
        "params": {"iban": "{value}"},
        "name": "🏦 IBAN Sorgu",
        "example": "TR280006256953335759003718",
        "desc": "IBAN ile banka bilgisi",
        "method": "GET"
    },
    "plaka": {
        "url": "https://rinexplakasorguapi.gt.tc/api/plaka.php",
        "params": {"endpoint": "ara", "q": "{value}"},
        "name": "🚗 Plaka Sorgu",
        "example": "34KG4978",
        "desc": "Plaka ile araç bilgisi",
        "method": "GET"
    },
    "papara_id": {
        "url": "http://rinexpaparasorguapi.rf.gd/api/papara.php",
        "params": {"id": "{value}"},
        "name": "💰 Papara ID Sorgu",
        "example": "1354693996",
        "desc": "Papara ID ile hesap",
        "method": "GET"
    },
    "papara_isim": {
        "url": "http://rinexpaparasorguapi.rf.gd/api/papara.php",
        "params": {"name": "{value}"},
        "name": "📛 Papara İsim Sorgu",
        "example": "ÖZCAN",
        "desc": "İsim ile Papara hesabı",
        "method": "GET"
    },
    "eczane": {
        "url": "https://eczanedataf3.onrender.com/f3system/api/eczane",
        "params": {"il": "{value}"},
        "name": "💊 Eczane Sorgu",
        "example": "İstanbul",
        "desc": "İl/ilçe eczane listesi",
        "method": "GET"
    },
    "vergi_ad": {
        "url": "https://serino.onrender.com/vergi",
        "params": {"ad": "{value}"},
        "name": "📑 Vergi (Ad) Sorgu",
        "example": "ahmet",
        "desc": "Ad ile vergi mükellefi",
        "method": "GET"
    },
    "vergi_no": {
        "url": "https://serino.onrender.com/vergi",
        "params": {"no": "{value}"},
        "name": "📑 Vergi No Sorgu",
        "example": "1234567890",
        "desc": "Vergi no ile mükellef",
        "method": "GET"
    }
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
]

# ==================== VERİTABANI ====================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        join_date TEXT,
        total_queries INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        is_admin INTEGER DEFAULT 0,
        frozen INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS query_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        query_type TEXT,
        query_value TEXT,
        query_time TEXT,
        result_count INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        platform TEXT,
        content TEXT,
        status TEXT DEFAULT 'beklemede',
        report_time TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    # Admin ekle
    for admin_id in ADMIN_IDS:
        c.execute("INSERT OR IGNORE INTO users (user_id, join_date, is_admin) VALUES (?, ?, ?)",
                  (admin_id, datetime.now().isoformat(), 1))
    
    # Ayarlar
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance', 'false')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('total_api_calls', '0')")
    
    conn.commit()
    conn.close()
    print("✅ Veritabanı hazır")

def get_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id, join_date) VALUES (?, ?)",
                  (user_id, datetime.now().isoformat()))
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()
    conn.close()
    return user

def is_admin(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
    r = c.fetchone()
    conn.close()
    return r and r[0] == 1

def is_banned(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    r = c.fetchone()
    conn.close()
    return r and r[0] == 1

def is_frozen(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT frozen FROM users WHERE user_id = ?", (user_id,))
    r = c.fetchone()
    conn.close()
    return r and r[0] == 1

def get_maintenance():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = 'maintenance'")
    r = c.fetchone()
    conn.close()
    return r and r[0] == 'true'

def set_maintenance(status):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE settings SET value = ? WHERE key = 'maintenance'", ('true' if status else 'false'))
    conn.commit()
    conn.close()

def increment_api_calls():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE settings SET value = CAST(value AS INTEGER) + 1 WHERE key = 'total_api_calls'")
    conn.commit()
    conn.close()

def get_api_calls():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = 'total_api_calls'")
    r = c.fetchone()
    conn.close()
    return int(r[0]) if r else 0

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE is_banned = 0 AND frozen = 0")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def ban_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def freeze_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET frozen = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def unfreeze_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET frozen = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def add_admin(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def remove_admin(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET is_admin = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def log_query(user_id, query_type, query_value, result_count=0):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO query_logs (user_id, query_type, query_value, query_time, result_count) VALUES (?, ?, ?, ?, ?)",
              (user_id, query_type, query_value[:100], datetime.now().isoformat(), result_count))
    c.execute("UPDATE users SET total_queries = total_queries + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def add_report(user_id, platform, content):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO reports (user_id, platform, content, report_time, status) VALUES (?, ?, ?, ?, ?)",
              (user_id, platform, content, datetime.now().isoformat(), 'beklemede'))
    report_id = c.lastrowid
    conn.commit()
    conn.close()
    return report_id

def get_reports(status=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if status:
        c.execute("SELECT id, user_id, platform, content, status, report_time FROM reports WHERE status = ? ORDER BY id DESC", (status,))
    else:
        c.execute("SELECT id, user_id, platform, content, status, report_time FROM reports ORDER BY id DESC")
    reports = c.fetchall()
    conn.close()
    return reports

def update_report_status(report_id, status):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE reports SET status = ? WHERE id = ?", (status, report_id))
    conn.commit()
    conn.close()

# ==================== API İSTEK ====================
async def api_request(url: str, params: dict = None) -> Optional[Dict]:
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS), "Accept": "application/json"}
        connector = aiohttp.TCPConnector(ssl=False)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url, params=params, headers=headers, timeout=25) as resp:
                text = await resp.text()
                increment_api_calls()
                try:
                    return json.loads(text)
                except:
                    return {"sonuc": text[:1000] if text else "Boş yanıt"}
    except Exception as e:
        logger.error(f"API hatası: {e}")
        return {"hata": str(e)}

async def execute_query(query_type: str, value: str) -> Tuple[str, int, bool]:
    if query_type not in API_URLS:
        return "❌ Geçersiz sorgu tipi", 0, False
    
    api_info = API_URLS[query_type]
    
    # Parametreleri hazırla
    if api_info.get("multi_param"):
        parts = value.split()
        if query_type == "adsoyad":
            if len(parts) < 2:
                return "❌ Format: Ad Soyad\nÖrnek: Mehmet Yılmaz", 0, False
            params = {"adi": parts[0], "soyadi": " ".join(parts[1:])}
        else:
            params = {k: value for k in api_info["params"]}
    else:
        params = {}
        for key, template in api_info["params"].items():
            params[key] = template.replace("{value}", value)
    
    data = await api_request(api_info["url"], params)
    
    if data and "hata" not in data:
        # Sonucu formatla
        result_text = f"📋 **{api_info['name']}**\n━━━━━━━━━━━━━━━━━━━━━━\n"
        result_text += f"🔍 **Aranan:** `{value}`\n"
        result_text += f"⏰ **Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
        result_text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        result_count = 0
        
        if isinstance(data, dict):
            for k, v in data.items():
                if v and str(v) not in ["", "None", "null", "{}", "[]"]:
                    if isinstance(v, dict):
                        result_text += f"<blockquote expandable>📌 **{k.upper()}**\n"
                        for sk, sv in v.items():
                            if sv and str(sv) not in ["", "None", "null"]:
                                result_text += f"   ▫️ **{sk}:** `{sv}`\n"
                                result_count += 1
                        result_text += "</blockquote>\n"
                    elif isinstance(v, list):
                        result_text += f"<blockquote expandable>📌 **{k.upper()}**\n"
                        for i, item in enumerate(v, 1):
                            result_text += f"   {i}. `{item}`\n"
                            result_count += 1
                        result_text += "</blockquote>\n"
                    else:
                        result_text += f"<blockquote expandable>📌 **{k.upper()}**\n   ▫️ `{v}`</blockquote>\n"
                        result_count += 1
        elif isinstance(data, list):
            for i, item in enumerate(data, 1):
                result_text += f"<blockquote expandable>📌 **{i}. KAYIT**\n"
                if isinstance(item, dict):
                    for k, v in item.items():
                        if v and str(v) not in ["", "None", "null"]:
                            result_text += f"   ▫️ **{k}:** `{v}`\n"
                else:
                    result_text += f"   ▫️ `{item}`\n"
                result_text += "</blockquote>\n"
                result_count += 1
        else:
            result_text += f"<blockquote expandable>📄 **SONUÇ**\n`{str(data)[:500]}`</blockquote>\n"
            result_count = 1
        
        result_text += "\n━━━━━━━━━━━━━━━━━━━━━━\n"
        result_text += f"💳 **API Satın Al:** @rinexdestek\n"
        result_text += f"👑 **Destek:** @rinexdestek | 📢 **Kanal:** @cksorgupanel"
        
        return result_text, result_count, True
    else:
        hata = data.get("hata", "Bağlantı hatası") if data else "API yanıt vermiyor"
        return f"❌ **HATA:** {hata}\n\nLütfen daha sonra tekrar deneyin.", 0, False

# ==================== KANAL KONTROLÜ ====================
async def is_member(user_id, context):
    try:
        cm = await context.bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return cm.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except:
        return True

# ==================== KLON BOT ====================
async def clone_bot(token: str, owner_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Ana botun tüm özelliklerine sahip klon bot oluştur"""
    try:
        test_bot = Bot(token=token)
        me = await test_bot.get_me()
        
        # Klon botu başlat (basit polling ile)
        async def run_clone():
            try:
                clone_app = Application.builder().token(token).build()
                
                async def clone_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
                    user = update.effective_user
                    await update.message.reply_text(
                        f"✨ **Hoşgeldin {user.first_name}!** ✨\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"🔰 **CK SORGUBOT KLON**\n\n"
                        f"📌 **Bu bot ana botun tam kopyasıdır!**\n"
                        f"🎁 **Tüm sorgular ÜCRETSİZDİR!**\n\n"
                        f"👑 **Ana Bot:** @ckfreesorgubot\n"
                        f"💬 **Destek:** @rinexdestek\n"
                        f"📢 **Kanal:** @cksorgupanel",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=main_menu(False)
                    )
                
                async def clone_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
                    q = update.callback_query
                    await q.answer()
                    data = q.data
                    
                    if data == "main_menu":
                        await q.message.edit_text(
                            "🏠 **Ana Menü**",
                            reply_markup=main_menu(False)
                        )
                    elif data.startswith("query_"):
                        query_type = data.replace("query_", "")
                        if query_type in API_URLS:
                            ctx.user_data["query_type"] = query_type
                            ctx.user_data["await_query"] = True
                            await q.message.edit_text(
                                f"📝 **{API_URLS[query_type]['name']}**\n\n"
                                f"📌 **Örnek:** `{API_URLS[query_type]['example']}`\n\n"
                                f"💬 **Değeri gönderin:**",
                                parse_mode=ParseMode.MARKDOWN
                            )
                    elif data == "new_query":
                        await q.message.edit_text(
                            "🔄 **Yeni Sorgu**",
                            reply_markup=main_menu(False)
                        )
                
                async def clone_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
                    user_id = update.effective_user.id
                    text = update.message.text.strip() if update.message.text else None
                    
                    if ctx.user_data.get("await_query"):
                        query_type = ctx.user_data.get("query_type")
                        if query_type and text:
                            loading = await update.message.reply_text("🔄 **Sorgulanıyor...**")
                            result, count, success = await execute_query(query_type, text)
                            await loading.delete()
                            await update.message.reply_text(result, parse_mode=ParseMode.HTML, reply_markup=result_menu())
                        ctx.user_data.pop("await_query", None)
                        ctx.user_data.pop("query_type", None)
                
                clone_app.add_handler(CommandHandler("start", clone_start))
                clone_app.add_handler(CallbackQueryHandler(clone_callback))
                clone_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, clone_message))
                
                await clone_app.initialize()
                await clone_app.start()
                await clone_app.updater.start_polling()
                
                # Botu canlı tut
                while True:
                    await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Klon bot hatası: {e}")
        
        asyncio.create_task(run_clone())
        return {"success": True, "username": me.username}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ==================== MENÜLER ====================
def main_menu(is_admin_user=False):
    buttons = [
        [InlineKeyboardButton("🔍 TC'den GSM", callback_data="query_tcgsm")],
        [InlineKeyboardButton("👨‍👩‍👧‍👦 Sülale", callback_data="query_sulale")],
        [InlineKeyboardButton("📞 GSM'den TC", callback_data="query_gsmtc")],
        [InlineKeyboardButton("👤 Ad Soyad", callback_data="query_adsoyad")],
        [InlineKeyboardButton("🏠 Adres", callback_data="query_adres")],
        [InlineKeyboardButton("🏢 İş Yeri", callback_data="query_isyeri")],
        [InlineKeyboardButton("🆔 TC Sorgu", callback_data="query_tc")],
        [InlineKeyboardButton("📡 Operatör", callback_data="query_operator")],
        [InlineKeyboardButton("🏦 IBAN", callback_data="query_iban")],
        [InlineKeyboardButton("🚗 Plaka", callback_data="query_plaka")],
        [InlineKeyboardButton("💰 Papara", callback_data="query_papara_id")],
        [InlineKeyboardButton("💊 Eczane", callback_data="query_eczane")],
        [InlineKeyboardButton("📑 Vergi", callback_data="query_vergi_ad")],
        [InlineKeyboardButton("📊 İstatistik", callback_data="menu_stats")],
        [InlineKeyboardButton("ℹ️ Bilgi", callback_data="menu_info")],
        [InlineKeyboardButton("⚠️ İhbar", callback_data="menu_report")],
        [InlineKeyboardButton("🤖 Bot Klonla", callback_data="menu_clone")],
        [InlineKeyboardButton("📢 Kanal", url=CHANNEL_LINK),
         InlineKeyboardButton("💬 Destek", url=SUPPORT_LINK)]
    ]
    
    if is_admin_user:
        buttons.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(buttons)

def result_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Yeni Sorgu", callback_data="new_query")],
        [InlineKeyboardButton("🏠 Ana Menü", callback_data="main_menu")]
    ])

def admin_panel_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 İstatistikler", callback_data="admin_stats"),
         InlineKeyboardButton("📋 Son Sorgular", callback_data="admin_logs")],
        [InlineKeyboardButton("📢 Duyuru", callback_data="admin_duyuru"),
         InlineKeyboardButton("🚫 Ban Yönetimi", callback_data="admin_ban_menu")],
        [InlineKeyboardButton("❄️ Dondurma", callback_data="admin_freeze_menu"),
         InlineKeyboardButton("👑 Admin Yönetimi", callback_data="admin_manage")],
        [InlineKeyboardButton("⚠️ İhbarlar", callback_data="admin_reports"),
         InlineKeyboardButton("🔧 Bakım Modu", callback_data="admin_maintenance")],
        [InlineKeyboardButton("👥 Tüm Kullanıcılar", callback_data="admin_users")],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]
    ])

# ==================== KOMUTLAR ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    if get_maintenance() and not is_admin(user_id):
        return await update.message.reply_text("🔧 **Bot bakım modundadır!**\n\nLütfen daha sonra tekrar deneyin.", parse_mode=ParseMode.MARKDOWN)
    
    if is_banned(user_id):
        return await update.message.reply_text("🚫 **Hesabınız banlanmıştır!**\n\nYetkili: @rinexdestek", parse_mode=ParseMode.MARKDOWN)
    
    if is_frozen(user_id) and not is_admin(user_id):
        return await update.message.reply_text("❄️ **Hesabınız dondurulmuştur!**\n\nYetkili: @rinexdestek", parse_mode=ParseMode.MARKDOWN)
    
    get_user(user_id)
    
    if not await is_member(user_id, context):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Kanala Katıl", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")],
            [InlineKeyboardButton("✅ Katıldım", callback_data="check_join")]
        ])
        return await update.message.reply_text(
            f"🔒 **Kanal Zorunluluğu**\n\nBotu kullanmak için {REQUIRED_CHANNEL} kanalına katılmalısınız!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
        )
    
    await update.message.reply_text(
        f"✨ **Hoşgeldin {user.first_name}!** ✨\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔰 **CK SORGUBOT ULTIMATE PRO v7.0**\n\n"
        f"📌 Aşağıdaki butonlardan sorgu tipini seç:\n"
        f"🎁 **Tüm sorgular ÜCRETSİZDİR!**\n\n"
        f"👑 **Destek:** @rinexdestek\n"
        f"📢 **Kanal:** @cksorgupanel",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu(is_admin(user_id))
    )

async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = update.effective_user
    
    if await is_member(user.id, context):
        await q.message.delete()
        await q.message.reply_text(
            "✅ **Hoşgeldin!**\nArtık botu kullanabilirsin.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu(is_admin(user.id))
        )
    else:
        await q.answer("❌ Hala kanala katılmadınız!", show_alert=True)

async def menu_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = get_user(q.from_user.id)
    api_calls = get_api_calls()
    
    text = (
        f"📊 **İstatistikleriniz**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 **ID:** `{q.from_user.id}`\n"
        f"🔍 **Toplam Sorgu:** `{user[4] if user else 0}`\n"
        f"📅 **Katılım:** `{user[3][:16] if user else '?'}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌍 **Genel**\n"
        f"📡 **Toplam API:** `{api_calls}`\n"
        f"🎁 **Tüm sorgular ÜCRETSİZ!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 **API Satın Al:** @rinexdestek"
    )
    await q.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=result_menu())

async def menu_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    text = (
        f"ℹ️ **Bot Bilgileri**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🤖 **Bot:** CK Sorgu Bot Ultimate\n"
        f"📌 **Sürüm:** 7.0 Pro (Render)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**📱 Sorgu Tipleri (14):**\n"
        f"• TC'den GSM | Sülale | TC\n"
        f"• GSM'den TC | Operatör\n"
        f"• Ad Soyad | Adres | İş Yeri\n"
        f"• IBAN | Plaka | Papara\n"
        f"• Eczane | Vergi\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎁 **Tüm sorgular ÜCRETSİZDİR!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 **Destek:** @rinexdestek\n"
        f"📢 **Kanal:** @cksorgupanel"
    )
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 Destek", url=SUPPORT_LINK)],
        [InlineKeyboardButton("📢 Kanal", url=CHANNEL_LINK)],
        [InlineKeyboardButton("🔙 Geri", callback_data="main_menu")]
    ])
    await q.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)

async def menu_clone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["await_clone"] = True
    await q.message.edit_text(
        "🤖 **Bot Klonlama**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "BotFather'dan aldığın **bot tokenini** gönder.\n\n"
        "**Token örneği:**\n`1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`\n\n"
        "⚠️ **Not:** Klon bot ana botun tüm özelliklerine sahip olur!\n\n"
        "❌ İptal: `/cancel`",
        parse_mode=ParseMode.MARKDOWN
    )

async def menu_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 TikTok", callback_data="report_tiktok"),
         InlineKeyboardButton("📸 Instagram", callback_data="report_instagram")],
        [InlineKeyboardButton("📺 YouTube", callback_data="report_youtube"),
         InlineKeyboardButton("✈️ Telegram", callback_data="report_telegram")],
        [InlineKeyboardButton("🌐 Diğer", callback_data="report_other")],
        [InlineKeyboardButton("🔙 İptal", callback_data="main_menu")]
    ])
    await q.message.edit_text(
        "⚠️ **İhbar Bildir**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Hangi platformda ihbar yapmak istiyorsunuz?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )

# ==================== CALLBACK HANDLER ====================
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    data = q.data
    
    if get_maintenance() and not is_admin(user_id) and data not in ["check_join", "main_menu"]:
        await q.message.edit_text("🔧 Bakım modu!", reply_markup=main_menu(False))
        return
    
    if data == "check_join":
        return await check_join(update, context)
    
    if data == "new_query":
        await q.message.edit_text("🔄 **Yeni Sorgu**", reply_markup=main_menu(is_admin(user_id)))
        return
    
    if data == "main_menu":
        await q.message.edit_text("🏠 **Ana Menü**", reply_markup=main_menu(is_admin(user_id)))
        return
    
    if data == "menu_stats":
        return await menu_stats(update, context)
    
    if data == "menu_info":
        return await menu_info(update, context)
    
    if data == "menu_clone":
        return await menu_clone(update, context)
    
    if data == "menu_report":
        return await menu_report(update, context)
    
    if data.startswith("query_"):
        query_type = data.replace("query_", "")
        if query_type in API_URLS:
            context.user_data["query_type"] = query_type
            context.user_data["await_query"] = True
            api_info = API_URLS[query_type]
            await q.message.edit_text(
                f"📝 **{api_info['name']}**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📌 **Örnek:** `{api_info['example']}`\n\n"
                f"💬 **Değeri gönderin:**\n\n"
                f"❌ İptal: `/cancel`",
                parse_mode=ParseMode.MARKDOWN
            )
        return
    
    if data.startswith("report_"):
        platform = data[7:]
        context.user_data["report_platform"] = platform
        context.user_data["await_report"] = True
        await q.message.edit_text(
            f"⚠️ **{platform.upper()} İhbar**\n\nİçerik linkini veya kullanıcı adını gönder:",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # ==================== ADMIN ====================
    if not is_admin(user_id):
        return
    
    if data == "admin_panel":
        await q.message.edit_text("👑 **Admin Paneli**", reply_markup=admin_panel_menu())
        return
    
    if data == "admin_duyuru":
        context.user_data["await_announcement"] = True
        await q.message.edit_text("📢 **Duyuru**\n\nDuyuru metnini yazın:", parse_mode=ParseMode.MARKDOWN)
        return
    
    if data == "admin_stats":
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM query_logs")
        total_queries = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
        banned = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users WHERE frozen = 1")
        frozen = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM reports WHERE status = 'beklemede'")
        pending = c.fetchone()[0]
        api_calls = get_api_calls()
        conn.close()
        
        text = f"📊 **İstatistikler**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        text += f"👥 Kullanıcı: {total_users}\n"
        text += f"🔍 Toplam Sorgu: {total_queries}\n"
        text += f"📡 API Çağrısı: {api_calls}\n"
        text += f"🚫 Banlı: {banned}\n"
        text += f"❄️ Dondurulan: {frozen}\n"
        text += f"⚠️ Bekleyen İhbar: {pending}"
        await q.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_panel_menu())
        return
    
    if data == "admin_logs":
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT user_id, query_type, query_value, query_time, result_count FROM query_logs ORDER BY id DESC LIMIT 10")
        logs = c.fetchall()
        conn.close()
        
        text = "📋 **Son 10 Sorgu**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for log in logs:
            text += f"👤 `{log[0]}` | {log[1]}\n🔍 `{log[2][:20]}` | 📊 {log[4]}\n⏰ {log[3][:16]}\n━━━━━━━━━━━━━━━━━━━━━━\n"
        await q.message.edit_text(text[:4000], parse_mode=ParseMode.MARKDOWN, reply_markup=admin_panel_menu())
        return
    
    if data == "admin_ban_menu":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚫 Banla", callback_data="ban_user"),
             InlineKeyboardButton("✅ Ban Kaldır", callback_data="unban_user")],
            [InlineKeyboardButton("📋 Banlı Liste", callback_data="banned_list")],
            [InlineKeyboardButton("🔙 Geri", callback_data="admin_panel")]
        ])
        await q.message.edit_text("🚫 **Ban Yönetimi**", reply_markup=kb)
        return
    
    if data == "admin_freeze_menu":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("❄️ Dondur", callback_data="freeze_user"),
             InlineKeyboardButton("🔥 Dondurmayı Kaldır", callback_data="unfreeze_user")],
            [InlineKeyboardButton("📋 Dondurulan Liste", callback_data="frozen_list")],
            [InlineKeyboardButton("🔙 Geri", callback_data="admin_panel")]
        ])
        await q.message.edit_text("❄️ **Dondurma Yönetimi**", reply_markup=kb)
        return
    
    if data == "admin_manage":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 Admin Ekle", callback_data="add_admin"),
             InlineKeyboardButton("👑 Admin Çıkar", callback_data="remove_admin")],
            [InlineKeyboardButton("📋 Admin Liste", callback_data="admin_list")],
            [InlineKeyboardButton("🔙 Geri", callback_data="admin_panel")]
        ])
        await q.message.edit_text("👑 **Admin Yönetimi**", reply_markup=kb)
        return
    
    if data == "admin_reports":
        reports = get_reports("beklemede")
        if reports:
            text = "⚠️ **Bekleyen İhbarlar**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            for r in reports[:10]:
                text += f"🆔 `{r[0]}` | 👤 `{r[1]}` | 📱 {r[2]}\n📝 {r[3][:40]}...\n━━━━━━━━━━━━━━━━━━━━━━\n"
        else:
            text = "⚠️ Bekleyen ihbar yok."
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Çözüldü İşaretle", callback_data="resolve_report")],
            [InlineKeyboardButton("🔙 Geri", callback_data="admin_panel")]
        ])
        await q.message.edit_text(text[:4000], reply_markup=kb)
        return
    
    if data == "admin_maintenance":
        current = get_maintenance()
        set_maintenance(not current)
        await q.message.edit_text(f"🔧 Bakım modu: {'AÇIK' if not current else 'KAPALI'}", reply_markup=admin_panel_menu())
        return
    
    if data == "admin_users":
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT user_id, total_queries FROM users ORDER BY total_queries DESC LIMIT 20")
        users = c.fetchall()
        conn.close()
        
        text = "👥 **En Aktif 20 Kullanıcı**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for u in users:
            text += f"👤 `{u[0]}` | 🔍 {u[1]} sorgu\n"
        await q.message.edit_text(text[:4000], parse_mode=ParseMode.MARKDOWN, reply_markup=admin_panel_menu())
        return
    
    if data == "banned_list":
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE is_banned = 1")
        banned = c.fetchall()
        conn.close()
        text = "🚫 **Banlılar**\n\n" + "\n".join([f"• `{b[0]}`" for b in banned]) if banned else "Banlı yok"
        await q.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_panel_menu())
        return
    
    if data == "frozen_list":
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE frozen = 1")
        frozen = c.fetchall()
        conn.close()
        text = "❄️ **Dondurulanlar**\n\n" + "\n".join([f"• `{f[0]}`" for f in frozen]) if frozen else "Dondurulan yok"
        await q.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_panel_menu())
        return
    
    if data == "admin_list":
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE is_admin = 1")
        admins = c.fetchall()
        conn.close()
        text = "👑 **Adminler**\n\n" + "\n".join([f"• `{a[0]}`" for a in admins])
        await q.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_panel_menu())
        return
    
    if data == "resolve_report":
        context.user_data["await_resolve"] = True
        await q.message.edit_text("✅ **İhbar ID'sini girin:**")
        return
    
    if data in ["ban_user", "unban_user", "freeze_user", "unfreeze_user", "add_admin", "remove_admin"]:
        context.user_data["admin_action"] = data
        await q.message.edit_text(f"📝 **Kullanıcı ID'sini girin:**")

# ==================== MESAJ HANDLER ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else None
    
    if get_maintenance() and not is_admin(user_id):
        return await update.message.reply_text("🔧 Bakım modu!")
    
    if is_frozen(user_id) and not is_admin(user_id):
        return await update.message.reply_text("❄️ Hesabınız donduruldu!")
    
    if text and text.lower() == "/cancel":
        context.user_data.clear()
        await update.message.reply_text("✅ İptal edildi.", reply_markup=main_menu(is_admin(user_id)))
        return
    
    # Admin işlemleri
    if context.user_data.get("admin_action") and is_admin(user_id):
        action = context.user_data["admin_action"]
        try:
            target_id = int(text)
            if action == "ban_user":
                ban_user(target_id)
                await update.message.reply_text(f"✅ Kullanıcı `{target_id}` banlandı!")
            elif action == "unban_user":
                unban_user(target_id)
                await update.message.reply_text(f"✅ Kullanıcı `{target_id}` banı kaldırıldı!")
            elif action == "freeze_user":
                freeze_user(target_id)
                await update.message.reply_text(f"❄️ Kullanıcı `{target_id}` donduruldu!")
            elif action == "unfreeze_user":
                unfreeze_user(target_id)
                await update.message.reply_text(f"🔥 Kullanıcı `{target_id}` dondurması kaldırıldı!")
            elif action == "add_admin":
                add_admin(target_id)
                await update.message.reply_text(f"✅ Kullanıcı `{target_id}` admin yapıldı!")
            elif action == "remove_admin":
                remove_admin(target_id)
                await update.message.reply_text(f"✅ Kullanıcı `{target_id}` adminliği kaldırıldı!")
        except ValueError:
            await update.message.reply_text("❌ Geçersiz ID!")
        context.user_data.pop("admin_action", None)
        return
    
    # İhbar çözme
    if context.user_data.get("await_resolve") and is_admin(user_id):
        try:
            report_id = int(text)
            update_report_status(report_id, 'çözüldü')
            await update.message.reply_text(f"✅ İhbar `{report_id}` çözüldü!")
        except:
            await update.message.reply_text("❌ Geçersiz ID!")
        context.user_data.pop("await_resolve", None)
        return
    
    # Duyuru
    if context.user_data.get("await_announcement") and is_admin(user_id):
        users = get_all_users()
        success, fail = 0, 0
        for uid in users:
            try:
                await update.message.bot.send_message(uid, f"📢 **DUYURU**\n\n{text}\n\n👑 @rinexdestek", parse_mode=ParseMode.MARKDOWN)
                success += 1
            except:
                fail += 1
            await asyncio.sleep(0.05)
        await update.message.reply_text(f"✅ Duyuru gönderildi!\n✅ Başarılı: {success}\n❌ Başarısız: {fail}")
        context.user_data.pop("await_announcement", None)
        return
    
    # Bot klonlama
    if context.user_data.get("await_clone"):
        token = text.strip()
        if token and ":" in token and len(token) > 30:
            result = await clone_bot(token, user_id, context)
            if result["success"]:
                await update.message.reply_text(
                    f"✅ **Bot klonlandı!**\n\n🤖 @{result['username']}\n\n"
                    f"⚠️ Klon bot ana botun tüm özelliklerine sahiptir!",
                    reply_markup=main_menu(is_admin(user_id))
                )
            else:
                await update.message.reply_text(f"❌ Klonlama başarısız!\nHata: {result.get('error')}")
        else:
            await update.message.reply_text("❌ Geçersiz token formatı!")
        context.user_data.pop("await_clone", None)
        return
    
    # İhbar
    if context.user_data.get("await_report"):
        platform = context.user_data.get("report_platform", "bilinmeyen")
        content = text if text else "İçerik yok"
        report_id = add_report(user_id, platform, content)
        await update.message.reply_text(f"✅ İhbarınız alındı!\n🆔 ID: `{report_id}`", parse_mode=ParseMode.MARKDOWN)
        context.user_data.pop("await_report", None)
        context.user_data.pop("report_platform", None)
        return
    
    # Normal sorgu
    if context.user_data.get("await_query"):
        query_type = context.user_data.get("query_type")
        if query_type and text:
            loading = await update.message.reply_text("🔄 **Sorgulanıyor...**")
            result, count, success = await execute_query(query_type, text)
            await loading.delete()
            
            if success:
                log_query(user_id, query_type, text, count)
                await update.message.reply_text(result, parse_mode=ParseMode.HTML, reply_markup=result_menu())
            else:
                await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN, reply_markup=result_menu())
        context.user_data.pop("await_query", None)
        context.user_data.pop("query_type", None)
        return
    
    await update.message.reply_text("❓ Geçersiz komut! /start", reply_markup=main_menu(is_admin(user_id)))

# ==================== ANA FONKSİYON ====================
def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║          CK SORGUBOT ULTIMATE PRO v7.0 - RENDER              ║")
    print("║              @rinexdestek | @cksorgupanel                    ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    init_db()
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print(f"\n🔥 Bot Başlatıldı!")
    print(f"👑 Adminler: {ADMIN_IDS}")
    print(f"📢 Zorunlu Kanal: {REQUIRED_CHANNEL}")
    print(f"🔢 Toplam Sorgu Tipi: {len(API_URLS)}")
    print(f"🎁 Tüm sorgular ÜCRETSİZ!")
    print(f"\n✅ Bot çalışıyor...\n")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
