#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# CK SORGUBOT ULTIMATE PRO v6.0 - RENDER EDITION
# @rinexdestek | @cksorgupanel
# Tüm sorgular ücretsizdir! Premium yoktur.

import subprocess
import sys
import importlib.metadata
import asyncio
import aiohttp
import json
import sqlite3
import re
import random
import ssl
import os
import logging
import string
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any, List
from urllib.parse import urlencode, quote

# ==================== PAKET KONTROLÜ ====================
REQUIRED_PACKAGES = [
    "python-telegram-bot>=20.0",
    "aiohttp>=3.8.0",
]

def install_package(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", package])
        return True
    except:
        return False

def check_and_install_packages():
    missing_packages = []
    for package in REQUIRED_PACKAGES:
        package_name = package.split(">=")[0]
        try:
            importlib.metadata.version(package_name)
        except:
            missing_packages.append(package)
    
    if missing_packages:
        print("📦 Paketler yükleniyor...")
        for package in missing_packages:
            install_package(package)
        print("✅ Tamamlandı!\n")

check_and_install_packages()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember, Bot, InputFile
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ==================== KONFIGURASYON ====================
TOKEN = os.environ.get("BOT_TOKEN", "")  # Render'da environment variable olarak ayarla!
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "8610336203").split(",")] if os.environ.get("ADMIN_IDS") else [8610336203]
REQUIRED_CHANNEL = os.environ.get("REQUIRED_CHANNEL", "@iosstarturkiyee")
DB_FILE = "proxyweb.db"
SUPPORT_LINK = "https://t.me/rinexdestek"
CHANNEL_LINK = "https://t.me/cksorgupanel"

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== API'LER (RENDER UYUMLU) ====================
API_URLS = {
    "tcgsm": {
        "url": "https://arastir.vip/api/tcgsm.php",
        "params": {"tc": "{value}"},
        "name": "🔍 TC'den GSM Sorgu",
        "example": "12345678901",
        "desc": "TC kimlik numarası ile kayıtlı GSM numarası sorgulama",
        "method": "GET"
    },
    "sulale": {
        "url": "https://arastir.vip/api/sulale.php",
        "params": {"tc": "{value}"},
        "name": "👨‍👩‍👧‍👦 Sülale Sorgu",
        "example": "12345678901",
        "desc": "TC kimlik numarası ile aile bireylerini sorgulama",
        "method": "GET"
    },
    "gsmtc": {
        "url": "https://arastir.vip/api/gsmtc.php",
        "params": {"gsm": "{value}"},
        "name": "📞 GSM'den TC Sorgu",
        "example": "5551234567",
        "desc": "GSM numarası ile TC kimlik numarası sorgulama",
        "method": "GET"
    },
    "adsoyad": {
        "url": "https://arastir.vip/api/adsoyad.php",
        "params": {"adi": "{adi}", "soyadi": "{soyadi}"},
        "name": "👤 Ad Soyad Sorgu",
        "example": "roket atar",
        "multi_param": True,
        "desc": "Ad ve soyad ile kayıt sorgulama",
        "method": "GET"
    },
    "adsoyad_ilce": {
        "url": "https://arastir.vip/api/adsoyad.php",
        "params": {"adi": "{adi}", "soyadi": "{soyadi}", "il": "{il}", "ilce": "{ilce}"},
        "name": "🌟 Ad Soyad İlçeli Sorgu",
        "example": "Mehmet Yılmaz İstanbul Kadıköy",
        "multi_param": True,
        "desc": "Ad, soyad, il ve ilçe ile detaylı sorgulama",
        "method": "GET"
    },
    "adres": {
        "url": "https://arastir.vip/api/adres.php",
        "params": {"tc": "{value}"},
        "name": "🏠 Adres Sorgu",
        "example": "12345678901",
        "desc": "TC kimlik numarası ile adres bilgisi sorgulama",
        "method": "GET"
    },
    "isyeri": {
        "url": "https://arastir.vip/api/isyeri.php",
        "params": {"tc": "{value}"},
        "name": "🏢 İş Yeri Sorgu",
        "example": "12345678901",
        "desc": "TC ile iş yeri bilgisi sorgulama",
        "method": "GET"
    },
    "tc": {
        "url": "https://arastir.vip/api/tc.php",
        "params": {"tc": "{value}"},
        "name": "🆔 TC Sorgu",
        "example": "12345678901",
        "desc": "TC kimlik numarası doğrulama ve bilgi sorgulama",
        "method": "GET"
    },
    "operator": {
        "url": "https://apiservices.alwaysdata.net/apiservices/gncloperator.php",
        "params": {"numara": "{value}"},
        "name": "📡 Operatör Sorgu",
        "example": "5315312472",
        "desc": "GSM numarasının operatör bilgisi sorgulama",
        "method": "GET"
    },
    "iban": {
        "url": "https://rinexibansorguapi.rf.gd/api.php",
        "params": {"iban": "{value}"},
        "name": "🏦 IBAN Sorgu",
        "example": "TR280006256953335759003718",
        "desc": "IBAN numarası ile banka bilgisi sorgulama",
        "method": "GET"
    },
    "plaka": {
        "url": "https://rinexplakasorguapi.gt.tc/api/plaka.php",
        "params": {"endpoint": "ara", "q": "{value}"},
        "name": "🚗 Plaka Sorgu",
        "example": "34KG4978",
        "desc": "Plaka numarası ile araç bilgisi sorgulama",
        "method": "GET"
    },
    "plaka_ali": {
        "url": "https://rinexplakasorguapi.gt.tc/api/plaka.php",
        "params": {"endpoint": "ara", "q": "{value}"},
        "name": "🔍 Plaka (Alias) Sorgu",
        "example": "ali",
        "desc": "Plaka veya isim ile sorgulama",
        "method": "GET"
    },
    "papara_id": {
        "url": "http://rinexpaparasorguapi.rf.gd/api/papara.php",
        "params": {"id": "{value}"},
        "name": "💰 Papara ID Sorgu",
        "example": "1354693996",
        "desc": "Papara ID ile hesap bilgisi sorgulama",
        "method": "GET"
    },
    "papara_isim": {
        "url": "http://rinexpaparasorguapi.rf.gd/api/papara.php",
        "params": {"name": "{value}"},
        "name": "📛 Papara İsim Sorgu",
        "example": "ÖZCAN",
        "desc": "İsim ile Papara hesabı sorgulama",
        "method": "GET"
    },
    "eczane": {
        "url": "https://eczanedataf3.onrender.com/f3system/api/eczane",
        "params": {"il": "{value}"},
        "name": "💊 Eczane Sorgu",
        "example": "İstanbul",
        "desc": "İl/ilçe bazında eczane listesi sorgulama",
        "method": "GET"
    },
    "vergi_ad": {
        "url": "https://serino.onrender.com/vergi",
        "params": {"ad": "{value}"},
        "name": "📑 Vergi (Ad) Sorgu",
        "example": "ahmet",
        "desc": "Ad ile vergi mükellefi sorgulama",
        "method": "GET"
    },
    "vergi_no": {
        "url": "https://serino.onrender.com/vergi",
        "params": {"no": "{value}"},
        "name": "📑 Vergi No Sorgu",
        "example": "1234567890",
        "desc": "Vergi numarası ile mükellef sorgulama",
        "method": "GET"
    },
    "vergi_ad_soyad": {
        "url": "https://serino.onrender.com/vergi",
        "params": {"ad": "{adi}", "soyad": "{soyadi}"},
        "name": "📑 Vergi Ad Soyad Sorgu",
        "example": "ahmet yılmaz",
        "multi_param": True,
        "desc": "Ad ve soyad ile vergi mükellefi sorgulama",
        "method": "GET"
    }
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# ==================== VERİTABANI ====================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, 
        username TEXT, 
        first_name TEXT, 
        join_date TIMESTAMP, 
        total_queries INTEGER DEFAULT 0, 
        is_banned BOOLEAN DEFAULT 0,
        is_admin BOOLEAN DEFAULT 0,
        frozen BOOLEAN DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS query_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user_id INTEGER, 
        query_type TEXT, 
        query_value TEXT, 
        query_time TIMESTAMP,
        result_count INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, 
        value TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        platform TEXT,
        content TEXT,
        status TEXT DEFAULT 'beklemede',
        report_time TIMESTAMP,
        resolved_time TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS clone_bots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_token TEXT,
        bot_username TEXT,
        owner_id INTEGER,
        created_at TIMESTAMP,
        status TEXT DEFAULT 'active'
    )''')
    
    for admin_id in ADMIN_IDS:
        c.execute("INSERT OR IGNORE INTO users (user_id, join_date, is_admin) VALUES (?, ?, ?)", 
                  (admin_id, datetime.now(), 1))
    
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance', 'false')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('total_api_calls', '0')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bot_start_time', ?)", (datetime.now().isoformat(),))
    
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id, join_date) VALUES (?, ?)", (user_id, datetime.now()))
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
              (user_id, query_type, query_value[:100], datetime.now(), result_count))
    c.execute("UPDATE users SET total_queries = total_queries + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def add_report(user_id, platform, content):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO reports (user_id, platform, content, report_time, status) VALUES (?, ?, ?, ?, ?)",
              (user_id, platform, content, datetime.now(), 'beklemede'))
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
    c.execute("UPDATE reports SET status = ?, resolved_time = ? WHERE id = ?", (status, datetime.now() if status == 'çözüldü' else None, report_id))
    conn.commit()
    conn.close()

# ==================== REKLAM TEMİZLEME (GELİŞMİŞ) ====================
BLOCKED_KEYWORDS = [
    'developer', '_developer', 'version', '_version', 'timestamp', '_timestamp',
    'author', '_author', 'copyright', 'reklam', 'reklam_link', 'ads', 
    'advertisement', 'footer', 'credit', 'api_by', 'owner', 'punisher',
    'arastir', 'alwaysdata', 'ücretli', 'satın al', 'buy', 'price', 'fiyat',
    'message', 'Message', 'MESSAGE', 'error', 'Error', 'hata', 'Hata',
    'success', 'status', 'code', 'response', 'debug', 'test', 'example',
    'donate', 'bağış', 'support', 'destek', 'telegram', 'instagram', 'twitter'
]

def clean_api_response(data: Any, depth: int = 0) -> Any:
    """API yanıtından tüm reklam ve gereksiz bilgileri temizler - DERİN TEMİZLİK"""
    if depth > 10:
        return None
    
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            key_lower = key.lower()
            
            # Engellenen anahtarları atla
            if any(b in key_lower for b in BLOCKED_KEYWORDS):
                continue
            
            # Değer string ise ve reklam içeriyorsa atla
            if isinstance(value, str):
                value_lower = value.lower()
                if any(b in value_lower for b in BLOCKED_KEYWORDS):
                    continue
                if len(value) > 1000 and not any(c.isdigit() for c in value):
                    continue
                if value.startswith("http") and ("reklam" in value_lower or "ads" in value_lower):
                    continue
            
            # İç içe geçmiş verileri temizle
            if isinstance(value, dict):
                cleaned_val = clean_api_response(value, depth + 1)
                if cleaned_val and len(cleaned_val) > 0:
                    cleaned[key] = cleaned_val
            elif isinstance(value, list):
                cleaned_list = []
                for item in value:
                    cleaned_item = clean_api_response(item, depth + 1) if isinstance(item, dict) else item
                    if cleaned_item and cleaned_item not in ["", None, [], {}, "None", "null"]:
                        if isinstance(cleaned_item, str) and len(cleaned_item) > 0:
                            cleaned_list.append(cleaned_item)
                        elif not isinstance(cleaned_item, str):
                            cleaned_list.append(cleaned_item)
                if cleaned_list:
                    cleaned[key] = cleaned_list
            else:
                if value and str(value) not in ["", "None", "null", "0", "false", "False", "[]", "{}"]:
                    cleaned[key] = value
        
        # Boş dict kontrolü
        if len(cleaned) == 0:
            return None
        return cleaned
        
    elif isinstance(data, list):
        cleaned_list = []
        for item in data:
            cleaned_item = clean_api_response(item, depth + 1) if isinstance(item, dict) else item
            if cleaned_item and cleaned_item not in ["", None, [], {}]:
                cleaned_list.append(cleaned_item)
        return cleaned_list if cleaned_list else None
        
    elif isinstance(data, str):
        # String temizliği
        if len(data) > 2000 and not any(c.isdigit() for c in data):
            return None
        if any(b in data.lower() for b in BLOCKED_KEYWORDS):
            return None
        return data if data.strip() else None
        
    return data

def format_result_pretty(data: Any, query_name: str, query_value: str) -> Tuple[str, int]:
    """API verisini çok güzel formatta düzenler - HİÇBİR VERİ KAYBOLMAZ"""
    if not data:
        return "❌ **Sonuç bulunamadı**\n\nLütfen bilgileri kontrol edin.", 0
    
    # Veriyi temizle
    cleaned = clean_api_response(data)
    
    # Boş veri kontrolü
    if not cleaned:
        return "❌ **Sonuç bulunamadı**\n\nLütfen bilgileri kontrol edin.", 0
    
    result = f"📋 **{query_name}**\n━━━━━━━━━━━━━━━━━━━━━━\n"
    result += f"🔍 **Aranan:** `{query_value}`\n"
    result += f"⏰ **Tarih:** {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    result_count = 0
    
    def format_value(val, indent=0):
        nonlocal result_count
        spaces = "  " * indent
        result_text = ""
        
        if isinstance(val, dict):
            for k, v in val.items():
                if v and str(v) not in ["", "None", "null"]:
                    result_text += f"{spaces}📌 **{k.upper()}:**\n"
                    result_text += format_value(v, indent + 1)
                    result_count += 1
        elif isinstance(val, list):
            for i, item in enumerate(val, 1):
                if isinstance(item, dict):
                    result_text += f"{spaces}**{i}. KAYIT:**\n"
                    for k, v in item.items():
                        if v and str(v) not in ["", "None", "null"]:
                            result_text += f"{spaces}  ▫️ **{k.title()}:** `{str(v)[:500]}`\n"
                    result_text += "\n"
                    result_count += 1
                else:
                    item_str = str(item)[:500]
                    if item_str and item_str not in ["", "None", "null"]:
                        result_text += f"{spaces}▫️ `{item_str}`\n"
                        result_count += 1
        else:
            val_str = str(val)[:500]
            if val_str and val_str not in ["", "None", "null"]:
                result_text += f"{spaces}▫️ `{val_str}`\n"
                result_count += 1
        
        return result_text
    
    result += format_value(cleaned)
    
    result += "\n━━━━━━━━━━━━━━━━━━━━━━\n"
    result += f"💳 **API Satın Almak İçin:** @rinexdestek\n"
    result += f"👑 **Destek:** @rinexdestek"
    
    return result, result_count

# ==================== API İSTEK (RENDER UYUMLU) ====================
async def api_request(url: str, params: dict = None, method: str = "GET") -> Optional[Dict]:
    """API isteği gönderir - Render SSL hatası çözüldü, timeout eklendi"""
    try:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
            "Connection": "keep-alive"
        }
        
        # Render'da SSL sorunu yaşamamak için özel connector
        connector = aiohttp.TCPConnector(
            ssl=False,  # SSL doğrulamasını kapat (RF.GD ve Alwaysdata için)
            limit=100,
            ttl_dns_cache=300
        )
        
        timeout = aiohttp.ClientTimeout(total=25, connect=10, sock_read=15)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            if method.upper() == "GET":
                # Parametreleri temizle
                clean_params = {}
                for k, v in params.items():
                    if v and str(v) not in ["", "None"]:
                        clean_params[k] = str(v)
                
                async with session.get(url, params=clean_params, headers=headers) as resp:
                    text = await resp.text()
                    increment_api_calls()
                    
                    # JSON veya metin olarak döndür
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        if text.strip():
                            return {"sonuc": text[:2000]}
                        return None
                        
            else:  # POST
                async with session.post(url, json=params, headers=headers) as resp:
                    text = await resp.text()
                    increment_api_calls()
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        if text.strip():
                            return {"sonuc": text[:2000]}
                        return None
                        
    except asyncio.TimeoutError:
        logger.error(f"Timeout: {url}")
        return {"hata": "Bağlantı zaman aşımı. Lütfen daha sonra tekrar deneyin."}
    except aiohttp.ClientError as e:
        logger.error(f"Client error: {e}")
        return {"hata": f"Bağlantı hatası: {str(e)[:100]}"}
    except Exception as e:
        logger.error(f"API hatası: {e}")
        return {"hata": f"Teknik hata: {str(e)[:100]}"}

async def execute_query(query_type: str, value: str) -> Tuple[str, int, bool]:
    """Sorguyu çalıştırır - TÜM API'LER DESTEKLENİYOR"""
    if query_type not in API_URLS:
        return "❌ **Geçersiz sorgu tipi**", 0, False
    
    api_info = API_URLS[query_type]
    url = api_info["url"]
    params_template = api_info.get("params", {})
    
    # Parametreleri hazırla
    if api_info.get("multi_param"):
        parts = value.replace(';', ' ').split()
        
        if query_type == "adsoyad":
            if len(parts) < 2:
                return "❌ **Geçersiz Ad Soyad**\n\nFormat: `Ad Soyad`\nÖrnek: `roket atar`", 0, False
            params = {"adi": parts[0], "soyadi": " ".join(parts[1:])}
        elif query_type == "adsoyad_ilce":
            if len(parts) < 4:
                return "❌ **Geçersiz format**\n\nFormat: `Ad Soyad İl İlçe`\nÖrnek: `Mehmet Yılmaz İstanbul Kadıköy`", 0, False
            params = {"adi": parts[0], "soyadi": parts[1], "il": parts[2], "ilce": " ".join(parts[3:])}
        elif query_type == "vergi_ad_soyad":
            if len(parts) < 2:
                return "❌ **Geçersiz format**\n\nFormat: `Ad Soyad`\nÖrnek: `ahmet yılmaz`", 0, False
            params = {"ad": parts[0], "soyad": " ".join(parts[1:])}
        else:
            params = {k: value for k in params_template}
    else:
        params = {}
        for key, template in params_template.items():
            # {value} placeholder'ını değiştir
            if "{value}" in template:
                params[key] = template.replace("{value}", value)
            else:
                params[key] = value
    
    # API isteği gönder
    data = await api_request(url, params, api_info.get("method", "GET"))
    
    if data and "hata" not in data:
        result, count = format_result_pretty(data, api_info["name"], value)
        return result, count, True
    else:
        hata_msg = data.get("hata", "Bilinmeyen hata") if data else "API bağlantı hatası"
        return f"❌ **HATA:** {hata_msg}\n\nLütfen daha sonra tekrar deneyin.", 0, False

# ==================== KANAL KONTROLÜ ====================
async def is_member(user_id, context):
    try:
        cm = await context.bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return cm.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except:
        return True

# ==================== MENÜLER ====================
def main_menu(is_admin_user=False):
    buttons = [
        [InlineKeyboardButton("🔍 TC'den GSM", callback_data="query_tcgsm")],
        [InlineKeyboardButton("👨‍👩‍👧‍👦 Sülale", callback_data="query_sulale")],
        [InlineKeyboardButton("📞 GSM'den TC", callback_data="query_gsmtc")],
        [InlineKeyboardButton("👤 Ad Soyad", callback_data="query_adsoyad")],
        [InlineKeyboardButton("🌟 Ad Soyad İlçeli", callback_data="query_adsoyad_ilce")],
        [InlineKeyboardButton("🏠 Adres", callback_data="query_adres")],
        [InlineKeyboardButton("🏢 İş Yeri", callback_data="query_isyeri")],
        [InlineKeyboardButton("🆔 TC Sorgu", callback_data="query_tc")],
        [InlineKeyboardButton("📡 Operatör", callback_data="query_operator")],
        [InlineKeyboardButton("🏦 IBAN", callback_data="query_iban")],
        [InlineKeyboardButton("🚗 Plaka", callback_data="query_plaka")],
        [InlineKeyboardButton("💰 Papara", callback_data="query_papara_id")],
        [InlineKeyboardButton("💊 Eczane", callback_data="query_eczane")],
        [InlineKeyboardButton("📑 Vergi", callback_data="query_vergi_ad")],
        [InlineKeyboardButton("📊 İstatistikler", callback_data="menu_stats")],
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
        [InlineKeyboardButton("🤖 Klon Botlar", callback_data="admin_clones"),
         InlineKeyboardButton("⚠️ İhbarlar", callback_data="admin_reports")],
        [InlineKeyboardButton("🔧 Bakım Modu", callback_data="admin_maintenance"),
         InlineKeyboardButton("👥 Tüm Kullanıcılar", callback_data="admin_users")],
        [InlineKeyboardButton("🔙 Ana Menü", callback_data="main_menu")]
    ])

# ==================== KOMUTLAR ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    if get_maintenance() and not is_admin(user_id):
        return await update.message.reply_text("🔧 **Bot bakım modundadır!**\n\nLütfen daha sonra tekrar deneyin.", parse_mode=ParseMode.MARKDOWN)
    
    if is_banned(user_id):
        return await update.message.reply_text("🚫 **Hesabınız banlanmıştır!**\n\nYetkili ile iletişime geçin: @rinexdestek", parse_mode=ParseMode.MARKDOWN)
    
    if is_frozen(user_id) and not is_admin(user_id):
        return await update.message.reply_text("❄️ **Hesabınız dondurulmuştur!**\n\nYetkili ile iletişime geçin: @rinexdestek", parse_mode=ParseMode.MARKDOWN)
    
    get_user(user_id)
    
    if not await is_member(user_id, context):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Kanala Katıl", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")],
            [InlineKeyboardButton("✅ Katıldım", callback_data="check_join")]
        ])
        return await update.message.reply_text(
            f"🔒 **Kanal Zorunluluğu**\n\nBotu kullanmak için {REQUIRED_CHANNEL} kanalına katılmalısınız!\n\nKatıldıktan sonra 'Katıldım' butonuna basınız.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
        )
    
    await update.message.reply_text(
        f"✨ **Hoşgeldin {user.first_name}!** ✨\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔰 **CK SORGUBOT ULTIMATE PRO v6.0**\n\n"
        f"📌 Aşağıdaki butonlardan sorgu tipini seç:\n"
        f"🎁 **Tüm sorgular ÜCRETSİZDİR!**\n\n"
        f"👑 **Destek:** @rinexdestek\n"
        f"📢 **Kanal:** @cksorgupanel",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu(is_admin(user_id))
    )

async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    user_id = q.from_user.id
    
    user = get_user(user_id)
    api_calls = get_api_calls()
    
    text = (
        f"📊 **İstatistikleriniz**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 **User ID:** `{user_id}`\n"
        f"🔍 **Toplam Sorgu:** `{user[4] if user else 0}`\n"
        f"📅 **Katılım:** `{user[3][:16] if user else '?'}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌍 **Genel İstatistikler**\n"
        f"📡 **Toplam API Çağrısı:** `{api_calls}`\n"
        f"🎁 **Tüm sorgular ÜCRETSİZ!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 **API Satın Almak İçin:** @rinexdestek"
    )
    
    await q.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=result_menu())

async def menu_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    text = (
        f"ℹ️ **Bot Bilgileri**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🤖 **Bot:** CK Sorgu Bot Ultimate\n"
        f"📌 **Sürüm:** 6.0 Pro (Render Edition)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**📱 Sorgu Tipleri:**\n"
        f"• TC'den GSM | Sülale | TC\n"
        f"• GSM'den TC | Operatör\n"
        f"• Ad Soyad | Ad Soyad İlçeli\n"
        f"• Adres | İş Yeri\n"
        f"• IBAN | Plaka\n"
        f"• Papara | Eczane | Vergi\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎁 **Tüm sorgular ÜCRETSİZDİR!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 **Destek:** @rinexdestek\n"
        f"📢 **Kanal:** @cksorgupanel"
    )
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 Destek", url="https://t.me/rinexdestek")],
        [InlineKeyboardButton("📢 Kanal", url="https://t.me/cksorgupanel")],
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
        "⚠️ **Uyarı:**\n"
        "• Token güvenliğinden sen sorumlusun\n"
        "• Klon botun sahibi sensin\n\n"
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
        [InlineKeyboardButton("🌐 Genel İhbar", callback_data="report_general")],
        [InlineKeyboardButton("🔙 İptal", callback_data="main_menu")]
    ])
    
    await q.message.edit_text(
        "⚠️ **İhbar Bildir**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Hangi platformda ihbar yapmak istiyorsunuz?\n\n"
        "İhbar ettiğiniz içerik yetkililer tarafından incelenecektir.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )

# ==================== CALLBACK HANDLER ====================
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = update.effective_user
    user_id = user.id
    data = q.data
    
    if get_maintenance() and not is_admin(user_id) and data not in ["check_join", "main_menu"]:
        await q.message.edit_text("🔧 Bot bakım modundadır!", reply_markup=main_menu(False))
        return
    
    if data == "check_join":
        return await check_join_callback(update, context)
    
    if data == "new_query":
        await q.message.edit_text(
            "🔄 **Yeni Sorgu**\n\nAşağıdaki menüden sorgu tipini seç:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu(is_admin(user_id))
        )
        return
    
    if data == "main_menu":
        await q.message.edit_text(
            "🏠 **Ana Menü**\n\nSorgu tipini seç:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu(is_admin(user_id))
        )
        return
    
    if data == "menu_stats":
        return await menu_stats(update, context)
    
    if data == "menu_info":
        return await menu_info(update, context)
    
    if data == "menu_clone":
        return await menu_clone(update, context)
    
    if data == "menu_report":
        return await menu_report(update, context)
    
    # Sorgu seçimleri
    if data.startswith("query_"):
        query_type = data.replace("query_", "")
        
        if query_type in API_URLS:
            context.user_data["query_type"] = query_type
            context.user_data["await_query"] = True
            
            api_info = API_URLS[query_type]
            await q.message.edit_text(
                f"📝 **{api_info['name']}**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📌 **Açıklama:** {api_info['desc']}\n"
                f"📌 **Örnek:** `{api_info['example']}`\n\n"
                f"💬 **Değeri gönderin:**\n\n"
                f"❌ İptal: `/cancel`\n\n"
                f"💳 **API Satın Almak İçin:** @rinexdestek",
                parse_mode=ParseMode.MARKDOWN
            )
            return
    
    # İhbar platform seçimi
    if data.startswith("report_"):
        platform = data[7:]
        context.user_data["report_platform"] = platform
        context.user_data["await_report"] = True
        await q.message.edit_text(
            f"⚠️ **{platform.upper()} İhbar**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Lütfen ihbar edeceğiniz içeriğin linkini veya kullanıcı adını gönderin:\n\n"
            f"❌ İptal: `/cancel`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # ==================== ADMIN PANELİ ====================
    if not is_admin(user_id):
        return
    
    if data == "admin_panel":
        await q.message.edit_text("👑 **Admin Paneli**\n\nAşağıdaki işlemleri yapabilirsiniz:", parse_mode=ParseMode.MARKDOWN, reply_markup=admin_panel_menu())
        return
    
    if data == "admin_duyuru":
        context.user_data["await_announcement"] = "text"
        await q.message.edit_text("📝 **Duyuru**\n\nGöndermek istediğiniz duyuru metnini yazın:", parse_mode=ParseMode.MARKDOWN)
        return
    
    if data == "admin_stats":
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM query_logs")
        total_queries = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
        banned_users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users WHERE frozen = 1")
        frozen_users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM reports WHERE status = 'beklemede'")
        pending_reports = c.fetchone()[0]
        api_calls = get_api_calls()
        conn.close()
        
        text = (
            f"📊 **Bot İstatistikleri**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 **Toplam Kullanıcı:** `{total_users}`\n"
            f"🔍 **Toplam Sorgu:** `{total_queries}`\n"
            f"📡 **Toplam API Çağrısı:** `{api_calls}`\n"
            f"🚫 **Banlı Kullanıcı:** `{banned_users}`\n"
            f"❄️ **Dondurulan:** `{frozen_users}`\n"
            f"⚠️ **Bekleyen İhbar:** `{pending_reports}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 **Ortalama Sorgu:** `{total_queries/total_users if total_users > 0 else 0:.1f}`"
        )
        await q.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_panel_menu())
        return
    
    if data == "admin_logs":
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT user_id, query_type, query_value, query_time, result_count FROM query_logs ORDER BY id DESC LIMIT 20")
        logs = c.fetchall()
        conn.close()
        
        if not logs:
            text = "📋 **Son Sorgular**\n\nHenüz sorgu yapılmamış."
        else:
            text = "📋 **Son 20 Sorgu**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            for log in logs:
                text += f"👤 **ID:** `{log[0]}`\n📌 **Tip:** {log[1]}\n🔍 **Değer:** `{log[2][:30]}`\n📊 **Sonuç:** {log[4]} kayıt\n⏰ **Zaman:** {log[3][:16]}\n━━━━━━━━━━━━━━━━━━━━━━\n"
        
        await q.message.edit_text(text[:4000], parse_mode=ParseMode.MARKDOWN, reply_markup=admin_panel_menu())
        return
    
    if data == "admin_maintenance":
        current = get_maintenance()
        set_maintenance(not current)
        status = "AÇIK" if not current else "KAPALI"
        await q.message.edit_text(f"🔧 **Bakım Modu {status}**", parse_mode=ParseMode.MARKDOWN, reply_markup=admin_panel_menu())
        return
    
    if data == "admin_ban_menu":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚫 Banla", callback_data="ban_user"),
             InlineKeyboardButton("✅ Ban Kaldır", callback_data="unban_user")],
            [InlineKeyboardButton("📋 Banlı Liste", callback_data="banned_list")],
            [InlineKeyboardButton("🔙 Geri", callback_data="admin_panel")]
        ])
        await q.message.edit_text("🚫 **Ban Yönetimi**\n\nYapmak istediğiniz işlemi seçin:", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        return
    
    if data == "admin_freeze_menu":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("❄️ Dondur", callback_data="freeze_user"),
             InlineKeyboardButton("🔥 Dondurmayı Kaldır", callback_data="unfreeze_user")],
            [InlineKeyboardButton("📋 Dondurulan Liste", callback_data="frozen_list")],
            [InlineKeyboardButton("🔙 Geri", callback_data="admin_panel")]
        ])
        await q.message.edit_text("❄️ **Dondurma Yönetimi**\n\nDondurulan kullanıcılar botu kullanamaz:", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        return
    
    if data == "admin_manage":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 Admin Ekle", callback_data="add_admin"),
             InlineKeyboardButton("👑 Admin Çıkar", callback_data="remove_admin")],
            [InlineKeyboardButton("📋 Admin Liste", callback_data="admin_list")],
            [InlineKeyboardButton("🔙 Geri", callback_data="admin_panel")]
        ])
        await q.message.edit_text("👑 **Admin Yönetimi**\n\nYapmak istediğiniz işlemi seçin:", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        return
    
    if data == "admin_reports":
        reports = get_reports("beklemede")
        if reports:
            text = "⚠️ **Bekleyen İhbarlar**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            for r in reports[:10]:
                text += f"🆔 `{r[0]}` | 👤 `{r[1]}` | 📱 {r[2]}\n📝 {r[3][:50]}...\n━━━━━━━━━━━━━━━━━━━━━━\n"
        else:
            text = "⚠️ **Bekleyen ihbar bulunmuyor.**"
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Çözüldü İşaretle", callback_data="resolve_report")],
            [InlineKeyboardButton("🔙 Geri", callback_data="admin_panel")]
        ])
        await q.message.edit_text(text[:4000], parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
        return
    
    if data == "resolve_report":
        context.user_data["await_resolve"] = True
        await q.message.edit_text(
            "✅ **İhbar Çözüldü İşaretle**\n\nÇözüldü olarak işaretlemek istediğiniz ihbar ID'sini girin:\n\n❌ İptal: `/cancel`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if data == "banned_list":
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE is_banned = 1")
        banned = c.fetchall()
        conn.close()
        text = "🚫 **Banlı Kullanıcılar**\n\n" + "\n".join([f"• `{b[0]}`" for b in banned]) if banned else "Banlı kullanıcı yok."
        await q.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_panel_menu())
        return
    
    if data == "frozen_list":
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE frozen = 1")
        frozen = c.fetchall()
        conn.close()
        text = "❄️ **Dondurulan Kullanıcılar**\n\n" + "\n".join([f"• `{f[0]}`" for f in frozen]) if frozen else "Dondurulan kullanıcı yok."
        await q.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_panel_menu())
        return
    
    if data == "admin_list":
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE is_admin = 1")
        admins = c.fetchall()
        conn.close()
        text = "👑 **Adminler**\n\n" + "\n".join([f"• `{a[0]}`" for a in admins]) if admins else "Admin bulunmuyor."
        await q.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=admin_panel_menu())
        return
    
    if data in ["ban_user", "unban_user", "freeze_user", "unfreeze_user", "add_admin", "remove_admin"]:
        context.user_data["admin_action"] = data
        action_names = {
            "ban_user": "Banla", "unban_user": "Ban Kaldır",
            "freeze_user": "Dondur", "unfreeze_user": "Dondurmayı Kaldır",
            "add_admin": "Admin Ekle", "remove_admin": "Admin Çıkar"
        }
        await q.message.edit_text(
            f"📝 **{action_names[data]}**\n\nKullanıcı ID'sini girin:\n\n❌ İptal: `/cancel`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

# ==================== MESAJ HANDLER ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip() if update.message.text else None
    
    if get_maintenance() and not is_admin(user_id):
        return await update.message.reply_text("🔧 Bot bakım modundadır!")
    
    if is_frozen(user_id) and not is_admin(user_id):
        return await update.message.reply_text("❄️ **Hesabınız dondurulmuştur!**")
    
    # İptal
    if text and text.lower() in ["/cancel", "/iptal"]:
        context.user_data.clear()
        await update.message.reply_text(
            "✅ **İşlem iptal edildi.**\n\nAna menüye dönebilirsiniz.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu(is_admin(user_id))
        )
        return
    
    # Admin işlemleri
    if context.user_data.get("admin_action") and is_admin(user_id):
        action = context.user_data["admin_action"]
        try:
            target_id = int(text)
            
            if action == "ban_user":
                ban_user(target_id)
                await update.message.reply_text(f"✅ **Kullanıcı `{target_id}` banlandı!**", parse_mode=ParseMode.MARKDOWN)
            elif action == "unban_user":
                unban_user(target_id)
                await update.message.reply_text(f"✅ **Kullanıcı `{target_id}` banı kaldırıldı!**", parse_mode=ParseMode.MARKDOWN)
            elif action == "freeze_user":
                freeze_user(target_id)
                await update.message.reply_text(f"❄️ **Kullanıcı `{target_id}` donduruldu!**", parse_mode=ParseMode.MARKDOWN)
            elif action == "unfreeze_user":
                unfreeze_user(target_id)
                await update.message.reply_text(f"🔥 **Kullanıcı `{target_id}` dondurması kaldırıldı!**", parse_mode=ParseMode.MARKDOWN)
            elif action == "add_admin":
                add_admin(target_id)
                await update.message.reply_text(f"✅ **Kullanıcı `{target_id}` admin yapıldı!**", parse_mode=ParseMode.MARKDOWN)
            elif action == "remove_admin":
                remove_admin(target_id)
                await update.message.reply_text(f"✅ **Kullanıcı `{target_id}` adminliği kaldırıldı!**", parse_mode=ParseMode.MARKDOWN)
        except ValueError:
            await update.message.reply_text("❌ **Geçersiz ID!** Lütfen sayısal bir ID girin.", parse_mode=ParseMode.MARKDOWN)
        
        context.user_data.pop("admin_action", None)
        return
    
    # İhbar çözüldü
    if context.user_data.get("await_resolve") and is_admin(user_id):
        try:
            report_id = int(text)
            update_report_status(report_id, 'çözüldü')
            await update.message.reply_text(f"✅ **İhbar ID `{report_id}` çözüldü olarak işaretlendi!**", parse_mode=ParseMode.MARKDOWN)
        except ValueError:
            await update.message.reply_text("❌ **Geçersiz ID!**", parse_mode=ParseMode.MARKDOWN)
        context.user_data.pop("await_resolve", None)
        return
    
    # Bot klonlama
    if context.user_data.get("await_clone"):
        token = text.strip()
        if token and ":" in token and len(token) > 30:
            # Klon botu başlat (basit versiyon)
            try:
                test_bot = Bot(token=token)
                me = await test_bot.get_me()
                
                await update.message.reply_text(
                    f"✅ **Bot başarıyla klonlandı!**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🤖 **Bot kullanıcı adı:** @{me.username}\n"
                    f"👑 **Klon botun sahibi sensin!**\n\n"
                    f"🔗 **Botu hemen dene:** https://t.me/{me.username}\n\n"
                    f"⚠️ Not: Klon bot sadece /start komutuna yanıt verir.",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=main_menu(is_admin(user_id))
                )
            except Exception as e:
                await update.message.reply_text(f"❌ **Klonlama başarısız!**\n\nHata: {str(e)[:100]}", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(
                "❌ **Geçersiz token formatı!**\n\nToken örneği: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`",
                parse_mode=ParseMode.MARKDOWN
            )
        context.user_data.pop("await_clone", None)
        return
    
    # Duyuru
    if context.user_data.get("await_announcement") and is_admin(user_id):
        users = get_all_users()
        
        msg = await update.message.reply_text("📢 **Duyuru gönderiliyor...**", parse_mode=ParseMode.MARKDOWN)
        success, fail = 0, 0
        
        if text:
            for uid in users:
                try:
                    await update.message.bot.send_message(
                        uid,
                        f"📢 **DUYURU**\n━━━━━━━━━━━━━━━━━━━━━━\n\n{text}\n\n━━━━━━━━━━━━━━━━━━━━━━\n👑 @rinexdestek",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    success += 1
                except:
                    fail += 1
                await asyncio.sleep(0.05)
        
        await msg.edit_text(
            f"✅ **Duyuru tamamlandı!**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ **Başarılı:** {success}\n"
            f"❌ **Başarısız:** {fail}",
            reply_markup=admin_panel_menu()
        )
        context.user_data.pop("await_announcement", None)
        return
    
    # İhbar
    if context.user_data.get("await_report"):
        platform = context.user_data.get("report_platform", "bilinmeyen")
        content = text if text else "İçerik belirtilmemiş"
        
        report_id = add_report(user_id, platform, content)
        
        await update.message.reply_text(
            f"✅ **İhbarınız alındı!**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 **İhbar ID:** `{report_id}`\n"
            f"📱 **Platform:** {platform.upper()}\n\n"
            f"Yetkililer en kısa sürede inceleyecektir.\n\n"
            f"📌 **İhbar durumunu sorgula:** `/ihbar {report_id}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=result_menu()
        )
        
        # Adminlere bildirim
        for admin_id in ADMIN_IDS:
            try:
                await update.message.bot.send_message(
                    admin_id,
                    f"⚠️ **Yeni İhbar!**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🆔 **ID:** `{report_id}`\n"
                    f"👤 **Kullanıcı:** `{user_id}`\n"
                    f"📱 **Platform:** {platform}\n"
                    f"📝 **İçerik:** {content[:200]}\n\n"
                    f"📌 `/cozum {report_id}` ile çözüldü işaretleyebilirsiniz.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        
        context.user_data.pop("await_report", None)
        context.user_data.pop("report_platform", None)
        return
    
    # Normal sorgu
    if context.user_data.get("await_query"):
        query_type = context.user_data.get("query_type")
        if not query_type:
            return
        
        value = text
        if not value:
            return
        
        loading = await update.message.reply_text("🔄 **Sorgulanıyor...**\n\nLütfen bekleyin.", parse_mode=ParseMode.MARKDOWN)
        
        result, result_count, success = await execute_query(query_type, value)
        
        await loading.delete()
        
        if success:
            log_query(user_id, API_URLS[query_type]["name"], value, result_count)
            await send_large_message(update, result, result_menu())
        else:
            await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN, reply_markup=result_menu())
        
        context.user_data.pop("await_query", None)
        context.user_data.pop("query_type", None)
        return
    
    # Varsayılan
    await update.message.reply_text(
        "❓ **Geçersiz komut!**\n\nLütfen butonları kullanarak işlem yapın.\n\nAna menü için /start yazabilirsiniz.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu(is_admin(user_id))
    )

async def send_large_message(update, text, reply_markup=None):
    """Büyük mesajları gönderir - HİÇBİR VERİ KESİLMEZ"""
    if len(text) <= 4000:
        try:
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        except:
            await update.message.reply_text(text, reply_markup=reply_markup)
        return
    
    # Büyük veriyi dosya olarak gönder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"sorgu_sonucu_{timestamp}.txt"
    
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(text)
        
        with open(filename, "rb") as f:
            await update.message.reply_document(
                document=InputFile(f, filename=filename),
                caption="📄 **Sorgu Sonucunuz**\n\nVeri boyutu büyük olduğu için dosya olarak gönderildi.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Dosya gönderme hatası: {e}")
        await update.message.reply_text("❌ Sonuç çok büyük ve gönderilemedi.", reply_markup=reply_markup)
    finally:
        if os.path.exists(filename):
            os.remove(filename)

# ==================== KOMUTLAR ====================
async def ihbar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """İhbar durumu sorgulama"""
    if not context.args:
        await update.message.reply_text("❌ **Kullanım:** `/ihbar <ID>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    try:
        report_id = int(context.args[0])
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT platform, content, status, report_time, resolved_time FROM reports WHERE id = ?", (report_id,))
        report = c.fetchone()
        conn.close()
        
        if not report:
            await update.message.reply_text(f"❌ **İhbar ID `{report_id}` bulunamadı!**", parse_mode=ParseMode.MARKDOWN)
            return
        
        platform, content, status, report_time, resolved_time = report
        
        status_emoji = {'beklemede': '⏳', 'incelemede': '🔍', 'çözüldü': '✅', 'reddedildi': '❌'}.get(status, '❓')
        
        text = f"⚠️ **İhbar Durumu**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        text += f"📌 **ID:** `{report_id}`\n"
        text += f"📱 **Platform:** {platform.upper()}\n"
        text += f"📝 **İçerik:** {content[:200]}\n"
        text += f"⏰ **Tarih:** {report_time[:16]}\n"
        text += f"{status_emoji} **Durum:** {status.upper()}\n"
        
        if resolved_time:
            text += f"✅ **Çözülme:** {resolved_time[:16]}\n"
        
        text += f"\n👑 **Destek:** @rinexdestek"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except:
        await update.message.reply_text("❌ **Geçersiz ID!**", parse_mode=ParseMode.MARKDOWN)

async def cozum_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """İhbarı çözüldü olarak işaretler - sadece admin"""
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Bu komut sadece adminler içindir!", parse_mode=ParseMode.MARKDOWN)
    
    if not context.args:
        await update.message.reply_text("❌ **Kullanım:** `/cozum <ID>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    try:
        report_id = int(context.args[0])
        update_report_status(report_id, 'çözüldü')
        await update.message.reply_text(f"✅ **İhbar ID `{report_id}` çözüldü olarak işaretlendi!**", parse_mode=ParseMode.MARKDOWN)
    except:
        await update.message.reply_text("❌ **Geçersiz ID!**", parse_mode=ParseMode.MARKDOWN)

# ==================== ANA FONKSİYON ====================
def main():
    if not TOKEN:
        print("❌ HATA: BOT_TOKEN environment variable ayarlanmamış!")
        print("Render'da Environment Variables -> BOT_TOKEN = bot_tokeni")
        print("ADMIN_IDS = 8610336203 (birden fazla için virgülle ayır)")
        sys.exit(1)
    
    init_db()
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ihbar", ihbar_command))
    app.add_handler(CommandHandler("cozum", cozum_command))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║              CK SORGUBOT ULTIMATE PRO v6.0 - RENDER EDITION                  ║")
    print("║                         @rinexdestek | @cksorgupanel                         ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print(f"\n🔥 Bot Başlatıldı!")
    print(f"👑 Kurucu: @rinexdestek")
    print(f"📞 Destek: @rinexdestek")
    print(f"📢 Zorunlu Kanal: {REQUIRED_CHANNEL}")
    print(f"👑 Adminler: {ADMIN_IDS}")
    print(f"🎁 Tüm sorgular ÜCRETSİZDİR!")
    print(f"📁 Büyük Veri: TXT olarak gönderilecek")
    print(f"⚠️ İhbar Sistemi: AKTIF")
    print(f"🔧 Bakım Modu: {get_maintenance()}")
    print(f"🔢 Toplam Sorgu Tipi: {len(API_URLS)}")
    print("\nBot çalışıyor...\n")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
