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

# НЕСКОЛЬКО ИСТОЧНИКОВ (на случай блокировки одного из них)
SOURCES = [
    "https://raw.githubusercontent.com/vfarid/v2ray-share/main/all_configs.txt",
    "https://raw.githubusercontent.com/freev2ray/v2ray-free/master/v2ray",
    "https://raw.githubusercontent.com/Paw0/Share-V2ray/master/V2ray"
]

# --- ГОРЯЧЕЕ ОБНОВЛЕНИЕ ---
def update_keys_worker():
    global WORKING_KEYS
    while True:
        logging.info("🚀 Пробую обновить ключи из разных источников...")
        found_any = False
        
        for url in SOURCES:
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    found = re.findall(r'(vless://[^\s]+|vmess://[^\s]+|trojan://[^\s]+|ss://[^\s]+)', r.text)
                    if found:
                        random.shuffle(found)
                        WORKING_KEYS = found[:150]
                        logging.info(f"✅ Успех! Найдено {len(WORKING_KEYS)} ключей из {url}")
                        found_any = True
                        break # Если нашли ключи, выходим из цикла источников
            except:
                continue
        
        # Если ничего не нашли, попробуем еще раз через 30 секунд
        # Если нашли — ждем 10 минут до следующего обновления
        time.sleep(30 if not found_any else 600)

# --- МЕНЮ (ТВОЕ ПОЛНОЕ) ---
TARIF_PLANS = {
    "1_month": {"title": "1 месяц VPN", "price": 50, "desc": "Доступ на 30 дней"},
    "forever": {"title": "VPN Навсегда 🏍", "price": 1000, "desc": "Вечный доступ + помощь автору"},
    "donate_100": {"title": "На шлем — 100 ⭐️", "price": 100, "desc": "Вклад в безопасность!"}
}

def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🛍 Купить VPN", callback_data="show_tarifs"))
    markup.row(InlineKeyboardButton("🏍 Поддержать мечту", callback_data="show_donates"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Бот готов! Коплю на <b>Kugoo Wish 04</b> 🏍", reply_markup=main_menu())

@bot.message_handler(commands=['test_pay'])
def test_payment(message):
    if message.from_user.id == ADMIN_ID:
        if WORKING_KEYS:
            key = WORKING_KEYS.pop(0)
            bot.reply_to(message, f"🛠 ТЕСТ: <code>{key}</code>\nВ базе осталось: {len(WORKING_KEYS)}")
        else:
            bot.reply_to(message, "⚠️ База всё еще пуста. Render блокирует запросы к GitHub. Подожди 30 сек.")
    else:
        bot.reply_to(message, "❌ Нет прав.")

# --- ОСТАЛЬНЫЕ ОБРАБОТЧИКИ ---
@bot.callback_query_handler(func=lambda call: call.data == "show_tarifs")
def tarifs(call):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("1 месяц — 50 ⭐️", callback_data="buy_1_month"))
    markup.add(InlineKeyboardButton("Навсегда — 1000 ⭐️", callback_data="buy_forever"))
    markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    bot.edit_message_text("Тарифы:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "show_donates")
def donates(call):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("На шлем — 100 ⭐️", callback_data="buy_donate_100"))
    markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    bot.edit_message_text("Донат: ❤️", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back")
def back(call):
    bot.edit_message_text("Меню:", call.message.chat.id, call.message.message_id, reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def process_buy(call):
    plan_key = call.data.replace("buy_", "")
    plan = TARIF_PLANS.get(plan_key) or {"title": "Донат", "price": 100, "desc": "Поддержка"}
    bot.send_invoice(call.message.chat.id, plan['title'], plan['desc'], f"pay_{plan_key}", "", "XTR", [LabeledPrice(label=plan['title'], amount=plan['price'])])

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def payment_done(message):
    if WORKING_KEYS:
        key = WORKING_KEYS.pop(0)
        bot.reply_to(message, f"✅ Оплата принята!\nКлюч: <code>{key}</code>")
    else:
        bot.reply_to(message, "❌ Ошибка! Ключи кончились. Напиши админу!")

# --- ЗАПУСК ---
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
        except:
            time.sleep(5)
