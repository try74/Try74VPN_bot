import os
import logging
import requests
import time
import socket
import re
import threading
import random
import concurrent.futures
from flask import Flask, jsonify
import telebot
from telebot.types import LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8308510677:AAFXv0Q5Er4p-rM30JTrKobgyu4lHBTiXbw"
ADMIN_ID = 6069286437

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

WORKING_KEYS = []

# ИСТОЧНИКИ
VPN_MIRRORS = [
    "https://raw.githubusercontent.com/freev2ray/v2ray-free/master/v2ray",
    "https://raw.githubusercontent.com/vfarid/v2ray-share/main/all_configs.txt",
    "https://raw.githubusercontent.com/Paw0/Share-V2ray/master/V2ray",
    "https://raw.githubusercontent.com/ovpns/sub/master/vless",
    "https://raw.githubusercontent.com/erfantkerfan/free-v2ray-config/main/configs.txt"
]

TARIF_PLANS = {
    "1_month": {"title": "1 месяц VPN", "price": 50, "desc": "Доступ на 30 дней"},
    "3_months": {"title": "3 месяца VPN", "price": 120, "desc": "Доступ на 90 дней"},
    "6_months": {"title": "6 месяцев VPN", "price": 200, "desc": "Доступ на 180 дней"},
    "1_year": {"title": "1 год VPN", "price": 350, "desc": "Доступ на 365 дней"},
    "forever": {"title": "VPN Навсегда 🏍", "price": 1000, "desc": "Вечный доступ + помощь автору"},
    "donate_50": {"title": "На бензин — 50 ⭐️", "price": 50, "desc": "Поддержка мечты"},
    "donate_100": {"title": "На шлем — 100 ⭐️", "price": 100, "desc": "Вклад в безопасность!"},
    "donate_500": {"title": "На колесо — 500 ⭐️", "price": 500, "desc": "Рывок к покупке байка!"},
    "donate_1000": {"title": "Меценат — 1000 ⭐️", "price": 1000, "desc": "Ты лучший!"}
}

# --- ЛОГИКА ПРОВЕРКИ ---
def extract_host_port(link):
    match = re.search(r'://[^@]+@([^:]+):(\d+)', link)
    if match: return match.group(1), int(match.group(2))
    return None, None

def check_vpn_config(config):
    host, port = extract_host_port(config)
    if not host or not port: return False
    try:
        with socket.create_connection((host, port), timeout=2) as sock:
            return True
    except: return False

def update_keys_worker():
    global WORKING_KEYS
    while True:
        logging.info("🚀 Обновление базы ключей...")
        all_raw_configs = []
        for url in VPN_MIRRORS:
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    found = re.findall(r'(vless://[^\s]+|vmess://[^\s]+|trojan://[^\s]+|ss://[^\s]+)', r.text)
                    all_raw_configs.extend(found)
            except: pass
        
        all_raw_configs = list(set(all_raw_configs))
        random.shuffle(all_raw_configs)
        
        temp_keys = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            future_to_key = {executor.submit(check_vpn_config, k): k for k in all_raw_configs[:150]}
            for future in concurrent.futures.as_completed(future_to_key):
                key = future_to_key[future]
                try:
                    if future.result():
                        temp_keys.append(key)
                    if len(temp_keys) >= 60: break
                except: pass
        
        WORKING_KEYS = temp_keys
        logging.info(f"✨ База обновлена: {len(WORKING_KEYS)} ключей.")
        time.sleep(300)

threading.Thread(target=update_keys_worker, daemon=True).start()

# --- ОБРАБОТКА КОМАНД ---
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🛍 Купить VPN", callback_data="show_tarifs"))
    markup.row(InlineKeyboardButton("🏍 Поддержать мечту", callback_data="show_donates"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет! Коплю на электромотоцикл <b>Kugoo Wish 04</b> 🏍\n\nЗдесь можно купить VPN или задонатить.",
        reply_markup=main_menu()
    )

@bot.message_handler(commands=['test_pay'])
def test_payment(message):
    if message.from_user.id == ADMIN_ID:
        if not WORKING_KEYS:
            bot.reply_to(message, "⚠️ Ищу ключи, попробуй через 10 секунд...")
            return
        key = WORKING_KEYS.pop(0)
        bot.reply_to(message, f"🛠 <b>ТЕСТОВЫЙ КЛЮЧ:</b>\n\n<code>{key}</code>\n\nОсталось: {len(WORKING_KEYS)}")
    else:
        bot.reply_to(message, "❌ Нет прав.")

@bot.callback_query_handler(func=lambda call: call.data == "show_tarifs")
def tarifs(call):
    markup = InlineKeyboardMarkup()
    for k, v in TARIF_PLANS.items():
        if not k.startswith("donate"):
            markup.add(InlineKeyboardButton(f"{v['title']} — {v['price']} ⭐️", callback_data=f"buy_{k}"))
    markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    bot.edit_message_text("Выберите тариф:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "show_donates")
def donates(call):
    markup = InlineKeyboardMarkup()
    for k, v in TARIF_PLANS.items():
        if k.startswith("donate"):
            markup.add(InlineKeyboardButton(v['title'], callback_data=f"buy_{k}"))
    markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    bot.edit_message_text("Сумма поддержки: ❤️", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back")
def back(call):
    bot.edit_message_text("Выберите действие:", call.message.chat.id, call.message.message_id, reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def process_buy(call):
    plan_key = call.data.split("_", 1)[1]
    plan = TARIF_PLANS.get(plan_key)
    if plan:
        bot.send_invoice(
            call.message.chat.id,
            plan['title'], plan['desc'], f"pay_{plan_key}", "", "XTR",
            [LabeledPrice(label=plan['title'], amount=plan['price'])],
            start_parameter="vpn"
        )

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def payment_done(message):
    payload = message.successful_payment.invoice_payload
    if "donate" in payload:
        bot.reply_to(message, "❤️ Спасибо за поддержку!")
        bot.send_message(ADMIN_ID, f"🎁 ДОНАТ: {message.successful_payment.total_amount} Stars")
        return
    if not WORKING_KEYS:
        bot.refund_star_payment(message.from_user.id, message.successful_payment.telegram_payment_charge_id)
        bot.send_message(message.chat.id, "❌ Ключи кончились. Сделан возврат средств!")
        return
    key = WORKING_KEYS.pop(0)
    bot.reply_to(message, f"✅ Оплата принята!\n\n🔑 Ключ:\n<code>{key}</code>")
    bot.send_message(ADMIN_ID, f"💰 ПРОДАЖА! +{message.successful_payment.total_amount} Stars")

# --- ЗАПУСК ---
@app.route('/')
def index():
    return f"Bot is running. Keys: {len(WORKING_KEYS)}"

if __name__ == '__main__':
    # Принудительно чистим вебхук перед стартом
    try:
        bot.remove_webhook()
    except:
        pass
    
    time.sleep(5) # Защита от ошибки 409
    
    def run_web():
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    
    threading.Thread(target=run_web, daemon=True).start()
    
    print("Бот запускается...")
    # Бесконечный цикл перезапуска при конфликтах
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=60)
        except Exception as e:
            logging.error(f"Ошибка Polling: {e}")
            time.sleep(10)
