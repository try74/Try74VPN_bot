import os, logging, requests, time, socket, re, threading, random, concurrent.futures
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

# Оставил самые быстрые источники
VPN_MIRRORS = [
    "https://raw.githubusercontent.com/vfarid/v2ray-share/main/all_configs.txt",
    "https://raw.githubusercontent.com/freev2ray/v2ray-free/master/v2ray",
    "https://raw.githubusercontent.com/Paw0/Share-V2ray/master/V2ray"
]

TARIF_PLANS = {
    "1_month": {"title": "1 месяц VPN", "price": 50, "desc": "Доступ на 30 дней"},
    "forever": {"title": "VPN Навсегда 🏍", "price": 1000, "desc": "Вечный доступ + помощь автору"},
    "donate_100": {"title": "На шлем — 100 ⭐️", "price": 100, "desc": "Вклад в безопасность!"}
}

def check_vpn_config(config):
    try:
        match = re.search(r'://[^@]+@([^:]+):(\d+)', config)
        if not match: return False
        host, port = match.group(1), int(match.group(2))
        with socket.create_connection((host, port), timeout=1): # Супер-быстрый чек
            return True
    except: return False

def update_keys_worker():
    global WORKING_KEYS
    while True:
        logging.info("🔎 Быстрый поиск ключей...")
        raw_list = []
        for url in VPN_MIRRORS:
            try:
                r = requests.get(url, timeout=3) # Ждем максимум 3 сек
                if r.status_code == 200:
                    found = re.findall(r'(vless://[^\s]+|vmess://[^\s]+|trojan://[^\s]+|ss://[^\s]+)', r.text)
                    raw_list.extend(found)
            except: continue
        
        raw_list = list(set(raw_list))
        random.shuffle(raw_list)

        # Сначала закидываем 5 любых ключей для скорости
        if not WORKING_KEYS and raw_list:
            WORKING_KEYS = raw_list[:5]
            logging.info("⚡️ Быстрый старт: 5 ключей добавлены без проверки")

        # А теперь в фоне проверяем остальные качественно
        temp_keys = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_key = {executor.submit(check_vpn_config, k): k for k in raw_list[:100]}
            for future in concurrent.futures.as_completed(future_to_key):
                if future.result():
                    temp_keys.append(future_to_key[future])
                if len(temp_keys) >= 40: break
        
        WORKING_KEYS = temp_keys
        logging.info(f"✅ База готова: {len(WORKING_KEYS)} проверенных ключей")
        time.sleep(600)

threading.Thread(target=update_keys_worker, daemon=True).start()

@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛍 Купить VPN", callback_data="buy_1_month"))
    bot.send_message(message.chat.id, "Бот готов! Коплю на <b>Kugoo Wish 04</b> 🏍", reply_markup=markup)

@bot.message_handler(commands=['test_pay'])
def test_payment(message):
    if message.from_user.id == ADMIN_ID:
        if WORKING_KEYS:
            key = WORKING_KEYS.pop(0)
            bot.reply_to(message, f"🛠 ТЕСТОВЫЙ КЛЮЧ:\n<code>{key}</code>\n\nВ базе еще: {len(WORKING_KEYS)}")
        else:
            bot.reply_to(message, "⚠️ Ключи еще ищутся, подожди 10 секунд...")
    else:
        bot.reply_to(message, "❌ Нет прав")

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
        bot.reply_to(message, f"✅ Оплата принята!\n🔑 Ключ:\n<code>{key}</code>")
        bot.send_message(ADMIN_ID, "💰 ПРОДАЖА!")
    else:
        bot.send_message(message.chat.id, "❌ Ключи кончились, свяжитесь с админом для возврата.")

@app.route('/')
def index(): return f"Status: Online. Keys: {len(WORKING_KEYS)}"

if __name__ == '__main__':
    try: bot.remove_webhook()
    except: pass
    time.sleep(2)
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))), daemon=True).start()
    bot.infinity_polling(skip_pending=True)
