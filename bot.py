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
VPN_SOURCE = "https://raw.githubusercontent.com/vfarid/v2ray-share/main/all_configs.txt"

# ТАРИФЫ И ДОНАТЫ
TARIF_PLANS = {
    "1_month": {"title": "1 месяц VPN", "price": 50, "desc": "Доступ на 30 дней"},
    "3_months": {"title": "3 месяца VPN", "price": 120, "desc": "Доступ на 90 дней"},
    "forever": {"title": "VPN Навсегда 🏍", "price": 1000, "desc": "Вечный доступ + огромная помощь автору"},
    "donate_50": {"title": "На бензин — 50 ⭐️", "price": 50, "desc": "Поддержка мечты"},
    "donate_100": {"title": "На шлем — 100 ⭐️", "price": 100, "desc": "Вклад в безопасность!"},
    "donate_500": {"title": "На колесо — 500 ⭐️", "price": 500, "desc": "Рывок к байку!"},
    "donate_1000": {"title": "Меценат — 1000 ⭐️", "price": 1000, "desc": "Ты лучший!"}
}

# --- ЛОГИКА САЙТА И КЛЮЧЕЙ ---
@app.route('/')
def index():
    return f"Status: Alive. Keys: {len(WORKING_KEYS)}"

def update_keys_worker():
    global WORKING_KEYS
    while True:
        try:
            r = requests.get(VPN_SOURCE, timeout=15)
            if r.status_code == 200:
                found = re.findall(r'(vless://[^\s]+|vmess://[^\s]+|trojan://[^\s]+|ss://[^\s]+)', r.text)
                if found:
                    random.shuffle(found)
                    WORKING_KEYS = found[:100]
                    logging.info(f"✅ База обновлена: {len(WORKING_KEYS)}")
        except: pass
        time.sleep(600)

# --- МЕНЮ ---
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🛍 Купить VPN", callback_data="show_tarifs"))
    markup.row(InlineKeyboardButton("🏍 Поддержать мечту", callback_data="show_donates"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет! Коплю на электромотоцикл <b>Kugoo Wish 04</b> 🏍\n\nВыбирай тариф или просто поддержи мою цель!",
        reply_markup=main_menu()
    )

@bot.message_handler(commands=['test_pay'])
def test_payment(message):
    if message.from_user.id == ADMIN_ID:
        if WORKING_KEYS:
            key = WORKING_KEYS.pop(0)
            bot.reply_to(message, f"🛠 ТЕСТОВЫЙ КЛЮЧ:\n<code>{key}</code>")
        else:
            bot.reply_to(message, "⚠️ Ключи еще качаются...")
    else:
        bot.reply_to(message, "❌ Нет прав.")

@bot.callback_query_handler(func=lambda call: call.data == "show_tarifs")
def tarifs(call):
    markup = InlineKeyboardMarkup()
    for k, v in TARIF_PLANS.items():
        if not k.startswith("donate"):
            markup.add(InlineKeyboardButton(f"{v['title']} — {v['price']} ⭐️", callback_data=f"buy_{k}"))
    markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    bot.edit_message_text("Выберите срок подписки:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "show_donates")
def donates(call):
    markup = InlineKeyboardMarkup()
    for k, v in TARIF_PLANS.items():
        if k.startswith("donate"):
            markup.add(InlineKeyboardButton(f"{v['title']}", callback_data=f"buy_{k}"))
    markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    bot.edit_message_text("Сумма поддержки: ❤️", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back")
def back(call):
    bot.edit_message_text("Выберите действие:", call.message.chat.id, call.message.message_id, reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def process_buy(call):
    plan_key = call.data.replace("buy_", "")
    plan = TARIF_PLANS.get(plan_key)
    if plan:
        bot.send_invoice(
            call.message.chat.id, plan['title'], plan['desc'], f"pay_{plan_key}", "", "XTR", 
            [LabeledPrice(label=plan['title'], amount=plan['price'])]
        )

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def payment_done(message):
    payload = message.successful_payment.invoice_payload
    if "donate" in payload:
        bot.reply_to(message, "❤️ Огромное спасибо! Ты приблизил меня к мечте!")
        bot.send_message(ADMIN_ID, f"🎁 ДОНАТ: {message.successful_payment.total_amount} Stars")
        return
    
    if WORKING_KEYS:
        key = WORKING_KEYS.pop(0)
        bot.reply_to(message, f"✅ Оплата принята!\n\n🔑 Твой ключ:\n<code>{key}</code>")
        bot.send_message(ADMIN_ID, f"💰 ПРОДАЖА! +{message.successful_payment.total_amount} Stars")
    else:
        bot.send_message(message.chat.id, "❌ Ключи кончились. Напиши админу!")

# --- ЗАПУСК ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    threading.Thread(target=update_keys_worker, daemon=True).start()
    
    while True:
        try:
            bot.remove_webhook()
            time.sleep(2)
            bot.infinity_polling(skip_pending=True)
        except:
            time.sleep(5)
