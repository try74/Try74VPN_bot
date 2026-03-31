import os, logging, re, threading, time
from flask import Flask
import telebot
from telebot.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8308510677:AAFXv0Q5Er4p-rM30JTrKobgyu4lHBTiXbw"
ADMIN_ID = 6069286437

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

WORKING_KEYS = [] # Твоя база ключей

# ТАРИФЫ
TARIF_PLANS = {
    "1_month": {"title": "1 месяц VPN", "price": 50, "desc": "Доступ на 30 дней"},
    "3_months": {"title": "3 месяца VPN", "price": 120, "desc": "Доступ на 90 дней"},
    "6_months": {"title": "6 месяцев VPN", "price": 200, "desc": "Доступ на 180 дней"},
    "forever": {"title": "VPN Навсегда 🏍", "price": 1000, "desc": "Вечный доступ + огромная помощь автору"},
    "donate_100": {"title": "На шлем — 100 ⭐️", "price": 100, "desc": "Вклад в безопасность!"},
    "donate_500": {"title": "На колесо — 500 ⭐️", "price": 500, "desc": "Рывок к байку!"}
}

# --- КНОПКИ ---
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("🛍 Купить VPN", callback_data="show_tarifs"))
    markup.row(InlineKeyboardButton("🏍 Поддержать мечту", callback_data="show_donates"))
    return markup

# --- КОМАНДЫ АДМИНА ---
@bot.message_handler(commands=['add'])
def add_keys(message):
    if message.from_user.id == ADMIN_ID:
        found = re.findall(r'(vless://[^\s]+|vmess://[^\s]+|trojan://[^\s]+|ss://[^\s]+)', message.text)
        if found:
            WORKING_KEYS.extend(found)
            bot.reply_to(message, f"✅ Добавлено {len(found)} ключей. Всего: {len(WORKING_KEYS)}")
        else:
            bot.reply_to(message, "⚠️ Ссылки не найдены!")

@bot.message_handler(commands=['clear'])
def clear_keys(message):
    if message.from_user.id == ADMIN_ID:
        global WORKING_KEYS
        WORKING_KEYS = []
        bot.reply_to(message, "🗑 База очищена!")

# --- ОБРАБОТКА МЕНЮ ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id, 
        f"Привет! В наличии <b>{len(WORKING_KEYS)}</b> ключей.\nКоплю на байк <b>Kugoo Wish 04</b>! 🏍", 
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
    
    # Если это покупка VPN, а ключей нет
    if "donate" not in plan_key and not WORKING_KEYS:
        bot.answer_callback_query(call.id, "⚠️ Ключи временно закончились!", show_alert=True)
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
        if WORKING_KEYS:
            key = WORKING_KEYS.pop(0)
            bot.reply_to(message, f"✅ Оплата принята!\n\nТвой ключ:\n<code>{key}</code>")
        else:
            bot.reply_to(message, "❌ Ошибка: ключи кончились! Напиши админу.")

# --- ЗАПУСК ---
@app.route('/')
def index():
    return f"Status: Online. Stock: {len(WORKING_KEYS)}"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(skip_pending=True)
        except: time.sleep(5)
