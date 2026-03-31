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

WORKING_KEYS = []

# Оставил 1 самый надежный и быстрый источник, чтобы не тупило
VPN_SOURCE = "https://raw.githubusercontent.com/vfarid/v2ray-share/main/all_configs.txt"

TARIF_PLANS = {
    "1_month": {"title": "1 месяц VPN", "price": 50, "desc": "Доступ на 30 дней"},
    "forever": {"title": "VPN Навсегда 🏍", "price": 1000, "desc": "Вечный доступ + помощь автору"},
    "donate_100": {"title": "На шлем — 100 ⭐️", "price": 100, "desc": "Вклад в безопасность!"}
}

def update_keys_worker():
    global WORKING_KEYS
    while True:
        logging.info("🚀 Загрузка ключей...")
        try:
            r = requests.get(VPN_SOURCE, timeout=10)
            if r.status_code == 200:
                # Ищем все протоколы
                found = re.findall(r'(vless://[^\s]+|vmess://[^\s]+|trojan://[^\s]+|ss://[^\s]+)', r.text)
                if found:
                    random.shuffle(found)
                    WORKING_KEYS = found[:100] # Берем первые 100 штук
                    logging.info(f"✅ База наполнена: {len(WORKING_KEYS)} шт.")
        except Exception as e:
            logging.error(f"Ошибка загрузки: {e}")
        
        time.sleep(600) # Обновляем раз в 10 минут

# Запускаем сборщик сразу
threading.Thread(target=update_keys_worker, daemon=True).start()

@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛍 Купить VPN (50 ⭐️)", callback_data="buy_1_month"))
    bot.send_message(message.chat.id, "Бот готов! Коплю на <b>Kugoo Wish 04</b> 🏍", reply_markup=markup)

@bot.message_handler(commands=['test_pay'])
def test_payment(message):
    if message.from_user.id == ADMIN_ID:
        if WORKING_KEYS:
            key = WORKING_KEYS.pop(0)
            bot.reply_to(message, f"🛠 ТЕСТОВЫЙ КЛЮЧ:\n<code>{key}</code>\n\nОсталось: {len(WORKING_KEYS)}")
        else:
            bot.reply_to(message, "⚠️ База пуста. Подожди 10 секунд и попробуй снова.")
    else:
        bot.reply_to(message, "❌ Нет прав.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def process_buy(call):
    plan_key = call.data.replace("buy_", "")
    plan = TARIF_PLANS.get(plan_key)
    if plan:
        bot.send_invoice(call.message.chat.id, plan['title'], plan['desc'], f"pay_{plan_key}", "", "XTR", [LabeledPrice(label=plan['title'], amount=plan['price'])])

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def payment_done(message):
    if WORKING_KEYS:
        key = WORKING_KEYS.pop(0)
        bot.reply_to(message, f"✅ Оплата принята!\n\n🔑 Ключ:\n<code>{key}</code>")
        bot.send_message(ADMIN_ID, "💰 ПРОДАЖА!")
    else:
        bot.send_message(message.chat.id, "❌ Ключи кончились. Напиши админу!")

@app.route('/')
def index():
    return f"Alive. Keys: {len(WORKING_KEYS)}"

if __name__ == '__main__':
    try: bot.remove_webhook()
    except: pass
    # Запуск Flask
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))), daemon=True).start()
    # Запуск бота
    bot.infinity_polling(skip_pending=True)
