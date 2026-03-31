import os, logging, requests, time, re, threading, random
from flask import Flask
import telebot
from telebot.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8308510677:AAFXv0Q5Er4p-rM30JTrKobgyu4lHBTiXbw"
ADMIN_ID = 6069286437

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- ЗАПАСНЫЕ КЛЮЧИ (ВШИТЫЕ) ---
# Если интернет тупит, эти ключи всегда будут в базе
EMERGENCY_KEYS = [
    "vless://7e49753c-4933-4f9e-8c35-c60317e0766a@104.21.57.185:443?path=%2F&security=tls&encryption=none&type=ws#FastVPN_1",
    "ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTo2YmU1YmU1YmU1YmU@172.67.183.185:443#FastVPN_2",
    "trojan://7e49753c-4933-4f9e-8c35-c60317e0766a@cloud.com:443#FastVPN_3"
]

WORKING_KEYS = list(EMERGENCY_KEYS) # Сразу наполняем базу
SOURCES = [
    "https://raw.githubusercontent.com/vfarid/v2ray-share/main/all_configs.txt",
    "https://raw.githubusercontent.com/freev2ray/v2ray-free/master/v2ray"
]

def update_keys_worker():
    global WORKING_KEYS
    while True:
        try:
            for url in SOURCES:
                r = requests.get(url, timeout=15)
                if r.status_code == 200:
                    found = re.findall(r'(vless://[^\s]+|vmess://[^\s]+|trojan://[^\s]+|ss://[^\s]+)', r.text)
                    if found:
                        random.shuffle(found)
                        # Добавляем новые к тем, что уже есть (не заменяя вшитые)
                        WORKING_KEYS = list(set(WORKING_KEYS + found[:100]))
                        logging.info(f"✅ База дополнена. Всего: {len(WORKING_KEYS)}")
                        break
        except: pass
        time.sleep(600)

@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛍 Купить VPN (50 ⭐️)", callback_data="buy_1_month"))
    bot.send_message(message.chat.id, "Бот готов! База ключей обновлена. 🏍", reply_markup=markup)

@bot.message_handler(commands=['test_pay'])
def test_payment(message):
    if message.from_user.id == ADMIN_ID:
        if WORKING_KEYS:
            key = WORKING_KEYS.pop(0)
            bot.reply_to(message, f"🛠 ТЕСТ: <code>{key}</code>\nВ базе еще: {len(WORKING_KEYS)}")
        else:
            bot.reply_to(message, "⚠️ База пуста.")
    else:
        bot.reply_to(message, "❌ Нет прав.")

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
