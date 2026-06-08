#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# CK SORGUBOT ULTIMATE PRO v9.0 - WEBHOOK EDITION
# @rinexdestek | @cksorgupanel

import os
import sys
import json
import sqlite3
import random
import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from flask import Flask, request, jsonify

# ==================== TOKEN KONTROL ====================
TOKEN = os.environ.get("BOT_TOKEN", "")
if not TOKEN:
    print("❌ HATA: BOT_TOKEN environment variable bulunamadı!")
    sys.exit(1)

ADMIN_IDS = [int(x.strip()) for x in os.environ.get("ADMIN_IDS", "8610336203").split(",")]
REQUIRED_CHANNEL = os.environ.get("REQUIRED_CHANNEL", "@iosstarturkiyee")
CHANNEL_LINK = "https://t.me/cksorgupanel"
SUPPORT_LINK = "https://t.me/rinexdestek"
DB_FILE = "bot_data.db"

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Telegram Bot (PTB v13.15 - webhook uyumlu)
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
from telegram.utils.request import Request

bot = Bot(token=TOKEN)
dispatcher = Dispatcher(bot, None, workers=4, use_context=True)

# ==================== API URL'LER ====================
API_URLS = {
    "tcgsm": {"url": "https://arastir.vip/api/tcgsm.php", "params": {"tc": "{value}"}, "name": "🔍 TC'den GSM", "example": "12345678901"},
    "sulale": {"url": "https://arastir.vip/api/sulale.php", "params": {"tc": "{value}"}, "name": "👨‍👩‍👧‍👦 Sülale", "example": "12345678901"},
    "gsmtc": {"url": "https://arastir.vip/api/gsmtc.php", "params": {"gsm": "{value}"}, "name": "📞 GSM'den TC", "example": "5551234567"},
    "adsoyad": {"url": "https://arastir.vip/api/adsoyad.php", "params": {"adi": "{adi}", "soyadi": "{soyadi}"}, "name": "👤 Ad Soyad", "example": "Mehmet Yılmaz", "multi_param": True},
    "adres": {"url": "https://arastir.vip/api/adres.php", "params": {"tc": "{value}"}, "name": "🏠 Adres", "example": "12345678901"},
    "isyeri": {"url": "https://arastir.vip/api/isyeri.php", "params": {"tc": "{value}"}, "name": "🏢 İş Yeri", "example": "12345678901"},
    "tc": {"url": "https://arastir.vip/api/tc.php", "params": {"tc": "{value}"}, "name": "🆔 TC Sorgu", "example": "12345678901"},
    "operator": {"url": "https://apiservices.alwaysdata.net/apiservices/gncloperator.php", "params": {"numara": "{value}"}, "name": "📡 Operatör", "example": "5315312472"},
    "iban": {"url": "https://rinexibansorguapi.rf.gd/api.php", "params": {"iban": "{value}"}, "name": "🏦 IBAN", "example": "TR280006256953335759003718"},
    "plaka": {"url": "https://rinexplakasorguapi.gt.tc/api/plaka.php", "params": {"endpoint": "ara", "q": "{value}"}, "name": "🚗 Plaka", "example": "34KG4978"},
    "papara_id": {"url": "http://rinexpaparasorguapi.rf.gd/api/papara.php", "params": {"id": "{value}"}, "name": "💰 Papara ID", "example": "1354693996"},
    "papara_isim": {"url": "http://rinexpaparasorguapi.rf.gd/api/papara.php", "params": {"name": "{value}"}, "name": "📛 Papara İsim", "example": "ÖZCAN"},
    "eczane": {"url": "https://eczanedataf3.onrender.com/f3system/api/eczane", "params": {"il": "{value}"}, "name": "💊 Eczane", "example": "İstanbul"},
    "vergi_ad": {"url": "https://serino.onrender.com/vergi", "params": {"ad": "{value}"}, "name": "📑 Vergi (Ad)", "example": "ahmet"},
    "vergi_no": {"url": "https://serino.onrender.com/vergi", "params": {"no": "{value}"}, "name": "📑 Vergi No", "example": "1234567890"}
}

USER_AGENTS = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"]

# ==================== VERİTABANI ====================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, join_date TEXT, total_queries INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0, is_admin INTEGER DEFAULT 0, frozen INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS query_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, query_type TEXT, query_value TEXT, query_time TEXT, result_count INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, platform TEXT, content TEXT, status TEXT DEFAULT 'beklemede', report_time TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    
    for admin_id in ADMIN_IDS:
        c.execute("INSERT OR IGNORE INTO users (user_id, join_date, is_admin) VALUES (?, ?, ?)", (admin_id, datetime.now().isoformat(), 1))
    
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
        c.execute("INSERT INTO users (user_id, join_date) VALUES (?, ?)", (user_id, datetime.now().isoformat()))
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

def get_api_calls():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = 'total_api_calls'")
    r = c.fetchone()
    conn.close()
    return int(r[0]) if r else 0

def increment_api_calls():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE settings SET value = CAST(value AS INTEGER) + 1 WHERE key = 'total_api_calls'")
    conn.commit()
    conn.close()

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
            async with session.get(url, params=params, headers=headers, timeout=20) as resp:
                text = await resp.text()
                increment_api_calls()
                try:
                    return json.loads(text)
                except:
                    return {"sonuc": text[:500] if text else "Boş yanıt"}
    except Exception as e:
        logger.error(f"API hatası: {e}")
        return {"hata": str(e)}

async def execute_query(query_type: str, value: str) -> Tuple[str, int, bool]:
    if query_type not in API_URLS:
        return "❌ Geçersiz sorgu", 0, False
    
    api_info = API_URLS[query_type]
    
    if api_info.get("multi_param"):
        parts = value.split()
        if len(parts) < 2:
            return "❌ Format: Ad Soyad\nÖrnek: Mehmet Yılmaz", 0, False
        params = {"adi": parts[0], "soyadi": " ".join(parts[1:])}
    else:
        params = {}
        for key, template in api_info["params"].items():
            params[key] = template.replace("{value}", value)
    
    data = await api_request(api_info["url"], params)
    
    if data and "hata" not in data:
        result_text = f"📋 **{api_info['name']}**\n━━━━━━━━━━━━━━━━━━━━━━\n🔍 **Aranan:** `{value}`\n⏰ **Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        result_count = 0
        
        if isinstance(data, dict):
            for k, v in data.items():
                if v and str(v) not in ["", "None", "null", "{}", "[]"]:
                    if isinstance(v, dict):
                        result_text += f"📌 **{k.upper()}:**\n"
                        for sk, sv in v.items():
                            if sv and str(sv) not in ["", "None", "null"]:
                                result_text += f"   ▫️ **{sk}:** `{sv}`\n"
                                result_count += 1
                    elif isinstance(v, list):
                        result_text += f"📌 **{k.upper()}:**\n"
                        for i, item in enumerate(v, 1):
                            result_text += f"   {i}. `{item}`\n"
                            result_count += 1
                    else:
                        result_text += f"📌 **{k.upper()}:** `{v}`\n"
                        result_count += 1
        elif isinstance(data, list):
            for i, item in enumerate(data, 1):
                result_text += f"📌 **{i}. KAYIT**\n"
                if isinstance(item, dict):
                    for k, v in item.items():
                        if v and str(v) not in ["", "None", "null"]:
                            result_text += f"   ▫️ **{k}:** `{v}`\n"
                else:
                    result_text += f"   ▫️ `{item}`\n"
                result_text += "\n"
                result_count += 1
        else:
            result_text += f"📄 **SONUÇ:**\n`{str(data)[:500]}`\n"
            result_count = 1
        
        result_text += "\n━━━━━━━━━━━━━━━━━━━━━━\n👑 **Destek:** @rinexdestek | 📢 **Kanal:** @cksorgupanel"
        return result_text, result_count, True
    else:
        hata = data.get("hata", "Bağlantı hatası") if data else "API yanıt vermiyor"
        return f"❌ **HATA:** {hata}", 0, False

# ==================== MENÜLER ====================
def main_menu(is_admin_user=False):
    buttons = [
        [InlineKeyboardButton("🔍 TC'den GSM", callback_data="query_tcgsm")],
        [InlineKeyboardButton("👨‍👩‍👧‍👦 Sülale", callback_data="query_sulale")],
        [InlineKeyboardButton("📞 GSM'den TC", callback_data="query_gsmtc")],
        [InlineKeyboardButton("👤 Ad Soyad", callback_data="query_adsoyad")],
        [InlineKeyboardButton("🏠 Adres", callback_data="query_adres")],
        [InlineKeyboardButton("🏢 İş Yeri", callback_data="query_isyeri")],
        [InlineKeyboardButton("🆔 TC", callback_data="query_tc")],
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
        [InlineKeyboardButton("📢 Kanal", url="https://t.me/cksorgupanel"),
         InlineKeyboardButton("💬 Destek", url="https://t.me/rinexdestek")]
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
        [InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]
    ])

# ==================== KOMUT HANDLERLERI ====================
def start(update, context):
    user = update.effective_user
    user_id = user.id
    
    if get_maintenance() and not is_admin(user_id):
        update.message.reply_text("🔧 Bot bakım modundadır!")
        return
    
    if is_banned(user_id):
        update.message.reply_text("🚫 Hesabınız banlanmıştır! @rinexdestek")
        return
    
    get_user(user_id)
    
    update.message.reply_text(
        f"✨ **Hoşgeldin {user.first_name}!** ✨\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔰 **CK SORGUBOT v9.0**\n\n📌 Sorgu tipini seç:\n🎁 **Tüm sorgular ÜCRETSİZ!**\n\n👑 @rinexdestek | 📢 @cksorgupanel",
        parse_mode="Markdown",
        reply_markup=main_menu(is_admin(user_id))
    )

def callback_handler(update, context):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    data = query.data
    
    if data == "main_menu":
        query.edit_message_text("🏠 Ana Menü", reply_markup=main_menu(is_admin(user_id)))
        return
    
    if data == "menu_stats":
        user = get_user(user_id)
        api_calls = get_api_calls()
        query.edit_message_text(
            f"📊 **İstatistikleriniz**\n━━━━━━━━━━━━━━━━━━━━━━\n\n👤 ID: `{user_id}`\n🔍 Toplam Sorgu: `{user[4] if user else 0}`\n📡 Toplam API: `{api_calls}`\n🎁 Tüm sorgular ÜCRETSİZ!",
            parse_mode="Markdown", reply_markup=result_menu()
        )
        return
    
    if data == "menu_info":
        query.edit_message_text(
            f"ℹ️ **Bot Bilgileri**\n━━━━━━━━━━━━━━━━━━━━━━\n\n🤖 CK Sorgu Bot v9.0\n📱 15 farklı sorgu tipi\n🎁 Tüm sorgular ÜCRETSİZ!\n\n👑 @rinexdestek | 📢 @cksorgupanel",
            parse_mode="Markdown", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Geri", callback_data="main_menu")]])
        )
        return
    
    if data.startswith("query_"):
        query_type = data.replace("query_", "")
        if query_type in API_URLS:
            context.user_data["query_type"] = query_type
            context.user_data["await_query"] = True
            query.edit_message_text(
                f"📝 **{API_URLS[query_type]['name']}**\n━━━━━━━━━━━━━━━━━━━━━━\n\n📌 Örnek: `{API_URLS[query_type]['example']}`\n\n💬 Değeri gönderin:\n\n❌ İptal: /cancel",
                parse_mode="Markdown"
            )
        return
    
    if data == "menu_clone":
        context.user_data["await_clone"] = True
        query.edit_message_text(
            "🤖 **Bot Klonlama**\n━━━━━━━━━━━━━━━━━━━━━━\n\nBotFather'dan aldığın bot tokenini gönder.\n\nÖrnek: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`\n\n❌ İptal: /cancel",
            parse_mode="Markdown"
        )
        return
    
    if data == "menu_report":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 TikTok", callback_data="report_tiktok"),
             InlineKeyboardButton("📸 Instagram", callback_data="report_instagram")],
            [InlineKeyboardButton("📺 YouTube", callback_data="report_youtube"),
             InlineKeyboardButton("✈️ Telegram", callback_data="report_telegram")],
            [InlineKeyboardButton("🔙 İptal", callback_data="main_menu")]
        ])
        query.edit_message_text("⚠️ **İhbar Bildir**\nHangi platform?", parse_mode="Markdown", reply_markup=kb)
        return
    
    if data.startswith("report_"):
        context.user_data["report_platform"] = data[7:]
        context.user_data["await_report"] = True
        query.edit_message_text(f"⚠️ İçerik linkini veya kullanıcı adını gönder:")
        return
    
    if data == "new_query":
        query.edit_message_text("🔄 Yeni Sorgu", reply_markup=main_menu(is_admin(user_id)))
        return
    
    # Admin panel
    if not is_admin(user_id):
        return
    
    if data == "admin_panel":
        query.edit_message_text("👑 Admin Paneli", reply_markup=admin_panel_menu())
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
        api_calls = get_api_calls()
        conn.close()
        query.edit_message_text(
            f"📊 **İstatistikler**\n━━━━━━━━━━━━━━━━━━━━━━\n\n👥 Kullanıcı: {total_users}\n🔍 Sorgu: {total_queries}\n📡 API: {api_calls}\n🚫 Banlı: {banned}\n❄️ Dondurulan: {frozen}",
            reply_markup=admin_panel_menu()
        )
        return
    
    if data == "admin_logs":
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT user_id, query_type, query_value, query_time FROM query_logs ORDER BY id DESC LIMIT 10")
        logs = c.fetchall()
        conn.close()
        text = "📋 **Son 10 Sorgu**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for log in logs:
            text += f"👤 `{log[0]}` | {log[1]}\n🔍 `{log[2][:20]}`\n⏰ {log[3][:16]}\n━━━━━━━━━━━━━━━━━━━━━━\n"
        query.edit_message_text(text[:4000], parse_mode="Markdown", reply_markup=admin_panel_menu())
        return
    
    if data == "admin_duyuru":
        context.user_data["await_announcement"] = True
        query.edit_message_text("📢 Duyuru metnini yazın:")
        return
    
    if data == "admin_ban_menu":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚫 Banla", callback_data="ban_user"),
             InlineKeyboardButton("✅ Ban Kaldır", callback_data="unban_user")],
            [InlineKeyboardButton("🔙 Geri", callback_data="admin_panel")]
        ])
        query.edit_message_text("🚫 Ban Yönetimi", reply_markup=kb)
        return
    
    if data == "admin_freeze_menu":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("❄️ Dondur", callback_data="freeze_user"),
             InlineKeyboardButton("🔥 Dondurmayı Kaldır", callback_data="unfreeze_user")],
            [InlineKeyboardButton("🔙 Geri", callback_data="admin_panel")]
        ])
        query.edit_message_text("❄️ Dondurma Yönetimi", reply_markup=kb)
        return
    
    if data == "admin_manage":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 Admin Ekle", callback_data="add_admin"),
             InlineKeyboardButton("👑 Admin Çıkar", callback_data="remove_admin")],
            [InlineKeyboardButton("🔙 Geri", callback_data="admin_panel")]
        ])
        query.edit_message_text("👑 Admin Yönetimi", reply_markup=kb)
        return
    
    if data == "admin_reports":
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, user_id, platform, content FROM reports WHERE status = 'beklemede' ORDER BY id DESC LIMIT 10")
        reports = c.fetchall()
        conn.close()
        if reports:
            text = "⚠️ **Bekleyen İhbarlar**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            for r in reports:
                text += f"🆔 `{r[0]}` | 👤 `{r[1]}` | 📱 {r[2]}\n📝 {r[3][:40]}...\n━━━━━━━━━━━━━━━━━━━━━━\n"
        else:
            text = "⚠️ Bekleyen ihbar yok."
        query.edit_message_text(text[:4000], parse_mode="Markdown", reply_markup=admin_panel_menu())
        return
    
    if data == "admin_maintenance":
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = 'maintenance'")
        current = c.fetchone()
        new_value = 'false' if current and current[0] == 'true' else 'true'
        c.execute("UPDATE settings SET value = ? WHERE key = 'maintenance'", (new_value,))
        conn.commit()
        conn.close()
        query.edit_message_text(f"🔧 Bakım modu: {'AÇIK' if new_value == 'true' else 'KAPALI'}", reply_markup=admin_panel_menu())
        return
    
    if data in ["ban_user", "unban_user", "freeze_user", "unfreeze_user", "add_admin", "remove_admin"]:
        context.user_data["admin_action"] = data
        query.edit_message_text("📝 Kullanıcı ID'sini girin:")

def message_handler(update, context):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if text and text.lower() == "/cancel":
        context.user_data.clear()
        update.message.reply_text("✅ İptal edildi.", reply_markup=main_menu(is_admin(user_id)))
        return
    
    # Admin işlemleri
    if context.user_data.get("admin_action") and is_admin(user_id):
        action = context.user_data["admin_action"]
        try:
            target_id = int(text)
            if action == "ban_user":
                ban_user(target_id)
                update.message.reply_text(f"✅ Kullanıcı `{target_id}` banlandı!")
            elif action == "unban_user":
                unban_user(target_id)
                update.message.reply_text(f"✅ Kullanıcı `{target_id}` banı kaldırıldı!")
            elif action == "freeze_user":
                freeze_user(target_id)
                update.message.reply_text(f"❄️ Kullanıcı `{target_id}` donduruldu!")
            elif action == "unfreeze_user":
                unfreeze_user(target_id)
                update.message.reply_text(f"🔥 Kullanıcı `{target_id}` dondurması kaldırıldı!")
            elif action == "add_admin":
                add_admin(target_id)
                update.message.reply_text(f"✅ Kullanıcı `{target_id}` admin yapıldı!")
            elif action == "remove_admin":
                remove_admin(target_id)
                update.message.reply_text(f"✅ Kullanıcı `{target_id}` adminliği kaldırıldı!")
        except:
            update.message.reply_text("❌ Geçersiz ID!")
        context.user_data.pop("admin_action", None)
        return
    
    # Duyuru
    if context.user_data.get("await_announcement") and is_admin(user_id):
        users = get_all_users()
        success, fail = 0, 0
        for uid in users:
            try:
                bot.send_message(uid, f"📢 **DUYURU**\n\n{text}\n\n👑 @rinexdestek", parse_mode="Markdown")
                success += 1
            except:
                fail += 1
        update.message.reply_text(f"✅ Duyuru gönderildi!\n✅ Başarılı: {success}\n❌ Başarısız: {fail}")
        context.user_data.pop("await_announcement", None)
        return
    
    # Klonlama
    if context.user_data.get("await_clone"):
        token = text.strip()
        if token and ":" in token and len(token) > 30:
            try:
                test_bot = Bot(token=token)
                me = test_bot.get_me()
                update.message.reply_text(f"✅ **Bot klonlandı!**\n\n🤖 @{me.username}\n\n🔗 https://t.me/{me.username}")
            except Exception as e:
                update.message.reply_text(f"❌ Klonlama başarısız!\nHata: {str(e)[:100]}")
        else:
            update.message.reply_text("❌ Geçersiz token formatı!")
        context.user_data.pop("await_clone", None)
        return
    
    # İhbar
    if context.user_data.get("await_report"):
        platform = context.user_data.get("report_platform", "bilinmeyen")
        report_id = add_report(user_id, platform, text)
        update.message.reply_text(f"✅ İhbarınız alındı!\n🆔 ID: `{report_id}`", parse_mode="Markdown")
        context.user_data.pop("await_report", None)
        context.user_data.pop("report_platform", None)
        return
    
    # Sorgu
    if context.user_data.get("await_query"):
        query_type = context.user_data.get("query_type")
        if query_type and text:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result, count, success = loop.run_until_complete(execute_query(query_type, text))
            loop.close()
            
            if success:
                log_query(user_id, query_type, text, count)
                update.message.reply_text(result, parse_mode="Markdown", reply_markup=result_menu())
            else:
                update.message.reply_text(result, parse_mode="Markdown", reply_markup=result_menu())
        context.user_data.pop("await_query", None)
        context.user_data.pop("query_type", None)
        return
    
    update.message.reply_text("❓ Geçersiz komut! /start", reply_markup=main_menu(is_admin(user_id)))

# ==================== HANDLER KAYITLARI ====================
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CallbackQueryHandler(callback_handler))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))

# ==================== WEBHOOK ====================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"Webhook hatası: {e}")
        return jsonify({"ok": False}), 500

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "Bot is running!", "version": "9.0"})

def set_webhook():
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "")
    if not render_url:
        print("❌ RENDER_EXTERNAL_URL bulunamadı!")
        return False
    
    webhook_url = f"{render_url}/{TOKEN}"
    result = bot.set_webhook(webhook_url)
    if result:
        print(f"✅ Webhook ayarlandı: {webhook_url}")
        return True
    else:
        print("❌ Webhook ayarlanamadı!")
        return False

# ==================== ANA FONKSİYON ====================
if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║          CK SORGUBOT ULTIMATE PRO v9.0 - WEBHOOK             ║")
    print("║              @rinexdestek | @cksorgupanel                    ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    init_db()
    
    port = int(os.environ.get("PORT", 8080))
    
    # Webhook ayarla
    set_webhook()
    
    print(f"\n🔥 Bot Başlatıldı! (Webhook Mode)")
    print(f"👑 Adminler: {ADMIN_IDS}")
    print(f"🔢 Toplam Sorgu Tipi: {len(API_URLS)}")
    print(f"🎁 Tüm sorgular ÜCRETSİZ!")
    print(f"\n✅ Bot çalışıyor... Port: {port}\n")
    
    app.run(host="0.0.0.0", port=port)
