import os
import logging
import requests
import time
import socket
import re
import threading
from flask import Flask, request, jsonify
import telebot
from telebot.types import LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton

# ===== НАСТРОЙКИ =====
# Твой токен возвращен на место, как ты и просил
BOT_TOKEN = "8308510677:AAFXv0Q5Er4p-rM30JTrKobgyu4lHBTiXbw"
ADMIN_ID = 6069286437

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Хранилище проверенных ключей в оперативной памяти
WORKING_KEYS = []
VPN_MIRRORS = [
    "https://github.com/nikita29a/FreeProxyList/raw/refs/heads/main/mirror/1.txt",
    "https://github.com/nikita29a/FreeProxyList/raw/refs/heads/main/mirror/2.txt",
]

# СЛОВАРЬ ТАРИФОВ И ДОНАТОВ
TARIF_PLANS = {
    "1_month": {"title": "1 месяц VPN", "price": 50, "desc": "Доступ на 30 дней"},
    "3_months": {"title": "3 месяца VPN", "price": 120, "desc": "Доступ на 90 дней"},
    "6_months": {"title": "6 месяцев VPN", "price": 200, "desc": "Доступ на 180 дней"},
    "1_year": {"title": "1 год VPN", "price": 350, "desc": "Доступ на 365 дней"},
    "forever": {"title": "VPN Навсегда 🏍", "price": 1000, "desc": "Вечный доступ + огромная помощь автору"},
    # Донаты (разные суммы для выбора)
    "donate_50": {"title": "На бензин — 50 ⭐️", "price": 50, "desc": "Небольшая поддержка мечты"},
    "donate_100": {"title": "На шлем — 100 ⭐️", "price": 100, "desc": "Вклад в безопасность!"},
    "donate_500": {"title": "На колесо — 500 ⭐️", "price": 500, "desc": "Серьезный рывок к покупке байка!"},
    "donate_1000": {"title": "Меценат — 1000 ⭐️", "price": 1000, "desc": "Ты лучший! Твой вклад поможет купить Wish 04."}
}

def extract_host_port(link):
    match = re.search(r'vless://[^@]+@([^:]+):(\d+)', link)
    if match: return match.group(1), int(match.group(2))
    return None, None

def check_vpn_config(config):
    host, port = extract_host_port(config)
    if not host or not port: return False
    try:
        with socket.create_connection((host, port), timeout=3) as sock:
            return True
    except: return False

def update_keys_worker():
    """Фоновый процесс: проверяет ключи раз в 10 минут."""
    global WORKING_KEYS
    while True:
        logging.info("Обновление базы ключей...")
        temp_keys = []
        for url in VPN_MIRRORS:
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    lines = r.text.strip().split('\n')
                    for line in lines[:50]:
                        line = line.strip()
                        if line.startswith('vless://') and check_vpn_config(line):
                            temp_keys.append(line)
                            if len(temp_keys) >= 15: break
            except: pass
        WORKING_KEYS = temp_keys
        logging.info(f"База обновлена. Готовых ключей: {len(WORKING_KEYS)}")
        time.sleep(600)

# Запуск фонового потока проверки ключей
threading.Thread(target=update_keys_worker, daemon=True).start()

def main_menu_markup():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🛍 Купить VPN (Тарифы)", callback_data="show_tarifs"))
    markup.row(InlineKeyboardButton("🏍 Поддержать мечту (Донат)", callback_data="show_donates"))
    return markup

@bot.message_handler(commands=['start'])
def start_command(message):
    bot.send_message(
        message.chat.id,
        "Привет! Я коплю на электромотоцикл <b>Kugoo Wish 04</b> 🏍\n\n"
        "Здесь можно купить быстрый VPN или просто поддержать мой путь к мечте.\n"
        "<i>Все ключи проверяются автоматически перед выдачей.</i>",
        reply_markup=main_menu_markup()
    )

@bot.callback_query_handler(func=lambda call: call.data == "show_tarifs")
def show_tarifs(call):
    markup = InlineKeyboardMarkup()
    for key, val in TARIF_PLANS.items():
        if not key.startswith("donate_"):
            markup.add(InlineKeyboardButton(f"{val['title']} — {val['price']} ⭐️", callback_data=f"buy_{key}"))
    markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main"))
    bot.edit_message_text("Выберите тариф VPN:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "show_donates")
def show_donates(call):
    markup = InlineKeyboardMarkup()
    for key, val in TARIF_PLANS.items():
        if key.startswith("donate_"):
            markup.add(InlineKeyboardButton(val['title'], callback_data=f"buy_{key}"))
    markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main"))
    bot.edit_message_text("Сколько хочешь закинуть в копилку на байк? ❤️", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def back_to_main(call):
    bot.edit_message_text("Выберите действие:", call.message.chat.id, call.message.message_id, reply_markup=main_menu_markup())

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def process_buy(call):
    plan_key = call.data.split("_", 1)[1]
    plan = TARIF_PLANS.get(plan_key)
    if plan:
        try:
            bot.send_invoice(
                chat_id=call.message.chat.id,
                title=plan['title'],
                description=plan['desc'],
                invoice_payload=f"pay_{plan_key}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label=plan['title'], amount=plan['price'])],
                start_parameter="vpn_shop"
            )
        except Exception as e:
            bot.answer_callback_query(call.id, f"Ошибка: {e}")

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    payload = message.successful_payment.invoice_payload
    
    # 1. Если это ДОНАТ
    if "donate" in payload:
        bot.reply_to(message, "❤️ Огромное спасибо! Твой донат уже в копилке на Kugoo Wish 04. Это очень ценно!")
        bot.send_message(ADMIN_ID, f"🎁 ДОНАТ: {message.successful_payment.total_amount} Stars от {message.from_user.id}")
        return

    # 2. Если покупка VPN
    if not WORKING_KEYS:
        try:
            # Автоматический возврат средств, если ключа нет в базе
            bot.refund_star_payment(message.from_user.id, message.successful_payment.telegram_payment_charge_id)
            bot.send_message(message.chat.id, "❌ Извините, рабочие ключи закончились. Stars возвращены на ваш баланс автоматически.")
            bot.send_message(ADMIN_ID, "⚠️ Платёж возвращён: база пуста!")
        except: pass
        return

    # Берем один ключ и удаляем его из списка (чтобы не выдать дважды)
    config = WORKING_KEYS.pop(0)
    bot.reply_to(
        message,
        f"✅ <b>Оплата принята!</b>\n\n🔑 <b>Ваш ключ:</b>\n<code>{config}</code>\n\n"
        "Импортируйте его в v2rayNG или Streisand. Приятного пользования! 🏍"
    )
    bot.send_message(ADMIN_ID, f"💰 ПРОДАЖА! +{message.successful_payment.total_amount} Stars в копилку!")

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        bot.process_new_updates([update])
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'failed'}), 403

@app.route('/')
def index():
    return f"Bot is live. Ready keys: {len(WORKING_KEYS)}"

if __name__ == '__main__':
    bot.remove_webhook()
    time.sleep(1)
    # Пытаемся взять URL из настроек Render для вебхука
    webhook_url = os.environ.get('RENDER_EXTERNAL_URL', '') + '/webhook'
    if webhook_url and "onrender.com" in webhook_url: 
        bot.set_webhook(url=webhook_url)
    
    # Запуск сервера
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
