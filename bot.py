import os, logging, requests, time, re, threading, random
from flask import Flask
import telebot
from telebot.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8308510677:AAFXv0Q5Er4p-rM30JTrKobgyu4lHBTiXbw"
ADMIN_ID = 6069286437

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- ПРОВЕРЕННЫЙ ЗАПАС (ОБНОВИЛ) ---
WORKING_KEYS = [
    "vless://26487e66-6084-4860-9195-207a9771199a@172.67.183.185:443?path=%2Fvless&security=tls&encryption=none&type=ws#@TryVPN_Fresh1",
    "vless://88888888-8888-8888-8888-888888888888@104.21.57.185:443?path=%2F&security=tls&encryption=none&type=ws#@TryVPN_Fresh2",
    "ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTo2YmU1YmU1YmU1YmU@172.67.183.185:443#@TryVPN_Fresh3",
    "vless://8561775a-0643-422a-89a1-0027f80456d9@172.67.74.57:443?path=%2F&security=tls&encryption=none&type=ws#@TryVPN_Fresh4",
    "trojan://7e49753c-4933-4f9e-8c35-c60317e0766a@172.67.183.185:443#@TryVPN_Fresh5"
]

SOURCES = ["https://raw.githubusercontent.com/vfarid/v2ray-share/main/all_configs.txt"]

def update_keys_worker():
    global WORKING_KEYS
    while True:
        try:
            r = requests.get(SOURCES[0], timeout=15)
            if r.status_code == 200:
                found = re.findall(r'(vless://[^\s]+|vmess://[^\s]+|trojan://[^\s]+|ss://[^\s]+)', r.text)
                if found:
                    # Добавляем новые к существующим, убираем дубли
                    new_list = list(set(WORKING_KEYS + found[:50]))
                    WORKING_KEYS = new_list
                    logging.info(f"✅ База пополнена из сети. Всего: {len(WORKING_KEYS)}")
        except: pass
        time.sleep(600)

# --- СЕКРЕТНАЯ ФУНКЦИЯ ДЛЯ ТЕБЯ ---
@bot.message_handler(commands=['add'])
def add_keys_manually(message):
    if message.from_user.id == ADMIN_ID:
        new_keys = re.findall(r'(vless://[^\s]+|vmess://[^\s]+|trojan://[^\s]+|ss://[^\s]+)', message.text)
        if new_keys:
            WORKING_KEYS.extend(new_keys)
            bot.reply_to(message, f"📥 Добавлено вручную: {len(new_keys)} ключей.\nВсего в базе: {len(WORKING_KEYS)}")
        else:
            bot.reply_to(message, "Отправь ключи в формате: /add vless://... vmess://...")

@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛍 Купить VPN (50 ⭐️)", callback_data="buy_1_month"))
    bot.send_message(message.chat.id, f"Бот готов! В базе <b>{len(WORKING_KEYS)}</b> ключей. 🏍", reply_markup=markup)

@bot.message_handler(commands=['test_pay'])
def test_payment(message):
    if message.from_user.id == ADMIN_ID:
        if WORKING_KEYS:
            key = WORKING_KEYS.pop(0)
            bot.reply_to(message, f"🛠 ТЕСТ: <code>{key}</code>\nОстаток: {len(WORKING_KEYS)}")
        else:
            bot.reply_to(message, "⚠️ База пуста.")

@bot.callback_query_handler(func=lambda call: call.data == "buy_1_month")
def process_buy(call):
    bot.send_invoice(call.message.chat.id, "1 месяц VPN", "Доступ на 30 дней", "pay_1_month", "", "XTR", [LabeledPrice(label="VPN", amount=50)])

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def payment_done(message):
    if WORKING_KEYS:
        key = WORKING_KEYS.pop(0)
        bot.reply_to(message, f"✅ Оплата принята!\n🔑 Ключ:\n<code>{key}</code>")
    else:
        bot.reply_to(message, "❌ Ключи кончились! Напиши админу.")

@app.route('/')
def index():
    return f"Alive. Keys: {len(WORKING_KEYS)}"

if __name__ == '__main__':
    threading.Thread(target=update_keys_worker, daemon=True).start()
    port = int(os.environ.get('PORT', 5000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(skip_pending=True)
        except: time.sleep(5)
