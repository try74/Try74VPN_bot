import os
import logging
import re
import threading
import time
import socket
import base64
import requests
from urllib.parse import urlparse
from flask import Flask
import telebot
from telebot.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton

# ===== НАСТРОЙКИ =====
# Не забудь использовать переменные окружения в будущем!
BOT_TOKEN = "ТВОЙ_ТОКЕН"
ADMIN_ID = 6069286437

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

WORKING_KEYS = [] # База живых ключей

# Источники бесплатных ключей (GitHub репозитории с саб-ссылками)
SOURCES = [
    "https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/Eternity",
    "https://raw.githubusercontent.com/pawdroid/Free-servers/main/sub",
    "https://raw.githubusercontent.com/freefq/free/master/v2"
]

# ТАРИФЫ
TARIF_PLANS = {
    "1_month": {"title": "1 месяц VPN", "price": 50, "desc": "Доступ на 30 дней"},
    "3_months": {"title": "3 месяца VPN", "price": 120, "desc": "Доступ на 90 дней"},
    "6_months": {"title": "6 месяцев VPN", "price": 200, "desc": "Доступ на 180 дней"},
    "forever": {"title": "VPN Навсегда 🏍", "price": 1000, "desc": "Вечный доступ + огромная помощь автору"},
    "donate_100": {"title": "На шлем — 100 ⭐️", "price": 100, "desc": "Вклад в безопасность!"},
    "donate_500": {"title": "На колесо — 500 ⭐️", "price": 500, "desc": "Рывок к байку!"}
}

# --- ФУНКЦИЯ ПРОВЕРКИ КЛЮЧА ---
def is_key_alive(key_str):
    try:
        parsed = urlparse(key_str)
        netloc = parsed.netloc
        host_port = netloc.split('@')[-1] if '@' in netloc else netloc
        
        if ':' in host_port:
            host, port = host_port.split(':')
            port = int(port.split('?')[0])
        else:
            host = host_port
            port = 443
            
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0) # Таймаут 2 секунды для быстрого отсева
        result = sock.connect_ex((host, port))
        sock.close()
        
        return result == 0
    except:
        return False

# --- АВТОМАТИЧЕСКИЙ ПАРСЕР ---
def auto_parser():
    global WORKING_KEYS
    while True:
        logging.info("Начинаю парсинг свежих ключей...")
        raw_keys = []
        
        for url in SOURCES:
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    text = resp.text
                    
                    # Часто ключи закодированы в Base64. Проверяем и декодируем.
                    if '://' not in text[:50]:
                        try:
                            # Добавляем выравнивание для правильного декодирования
                            missing_padding = len(text) % 4
                            if missing_padding:
                                text += '=' * (4 - missing_padding)
                            text = base64.b64decode(text).decode('utf-8', errors='ignore')
                        except Exception as e:
                            logging.error(f"Ошибка Base64: {e}")
                            
                    # Ищем все ссылки в тексте
                    found = re.findall(r'(vless://[^\s]+|vmess://[^\s]+|trojan://[^\s]+|ss://[^\s]+)', text)
                    raw_keys.extend(found)
            except Exception as e:
                logging.error(f"Ошибка загрузки из {url}: {e}")
        
        # Убираем дубликаты
        raw_keys = list(set(raw_keys))
        logging.info(f"Собрано {len(raw_keys)} сырых ключей. Начинаю проверку...")
        
        valid_keys = []
        # Проверяем ключи. Чтобы не вешать систему на весь день, собираем 30-50 рабочих и останавливаемся
        for key in raw_keys:
            if is_key_alive(key):
                valid_keys.append(key)
                if len(valid_keys) >= 30: # Ограничение, чтобы проверка не шла часами
                    break
                    
        WORKING_KEYS = valid_keys
        logging.info(f"Парсинг окончен! В базе {len(WORKING_KEYS)} рабочих ключей.")
        
        # Спим 3 часа до следующего обновления
        time.sleep(10800)

# --- КНОПКИ ---
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🛍 Купить VPN", callback_data="show_tarifs"))
    markup.row(InlineKeyboardButton("🏍 Поддержать мечту", callback_data="show_donates"))
    return markup

# --- КОМАНДЫ АДМИНА ---
@bot.message_handler(commands=['status'])
def admin_status(message):
    if message.from_user.id == ADMIN_ID:
        bot.reply_to(message, f"🟢 В базе сейчас рабочих ключей: {len(WORKING_KEYS)}")

# --- ОБРАБОТКА МЕНЮ ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id, 
        f"Привет! В наличии <b>{len(WORKING_KEYS)}</b> проверенных ключей.\nКоплю на байк <b>Kugoo Wish 04</b>! 🏍", 
        reply_markup=main_menu()
    )

@bot.callback_query_handler(func=lambda call: call.data == "show_tarifs")
def tarifs(call):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("1 месяц — 50 ⭐️", callback_data="buy_1_month"))
    markup.add(InlineKeyboardButton("3 месяца — 120 ⭐️", callback_data="buy_3_months"))
    markup.add(InlineKeyboardButton("6 месяцев — 200 ⭐️", callback_data="buy_6_months"))
    markup.add(InlineKeyboardButton("Навсегда — 1000 ⭐️", callback_data="buy_forever"))
    markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    bot.edit_message_text("Выберите срок подписки:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "show_donates")
def donates(call):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("На шлем (100 ⭐️)", callback_data="buy_donate_100"))
    markup.add(InlineKeyboardButton("На колесо (500 ⭐️)", callback_data="buy_donate_500"))
    markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    bot.edit_message_text("Спасибо за поддержку! ❤️", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back")
def back(call):
    bot.edit_message_text("Выберите действие:", call.message.chat.id, call.message.message_id, reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def process_buy(call):
    plan_key = call.data.replace("buy_", "")
    plan = TARIF_PLANS.get(plan_key)
    if not plan: return
    
    if "donate" not in plan_key and not WORKING_KEYS:
        bot.answer_callback_query(call.id, "⚠️ Бот ищет новые ключи. Зайди через пару минут!", show_alert=True)
        return

    bot.send_invoice(call.message.chat.id, plan['title'], plan['desc'], f"pay_{plan_key}", "", "XTR", [LabeledPrice(label=plan['title'], amount=plan['price'])])

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def payment_done(message):
    payload = message.successful_payment.invoice_payload
    if "donate" in payload:
        bot.reply_to(message, "❤️ Огромное спасибо за поддержку мечты!")
    else:
        key_found = None
        while WORKING_KEYS:
            potential_key = WORKING_KEYS.pop(0)
            if is_key_alive(potential_key):
                key_found = potential_key
                break
        
        if key_found:
            bot.reply_to(message, f"✅ Оплата принята!\n\nТвой рабочий ключ:\n<code>{key_found}</code>")
        else:
            bot.reply_to(message, "❌ Ошибка: В процессе выдачи живые ключи кончились! Твои Звёзды сохранены. Напиши админу.")

# --- ЗАПУСК ---
@app.route('/')
def index():
    return f"Status: Online. Stock: {len(WORKING_KEYS)}"

if __name__ == '__main__':
    # Запускаем парсер в отдельном потоке
    threading.Thread(target=auto_parser, daemon=True).start()
    
    port = int(os.environ.get('PORT', 5000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            time.sleep(5)
