import os, logging, re, threading, time
from flask import Flask
import telebot
from telebot.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton

# Настройки
BOT_TOKEN = "8308510677:AAFXv0Q5Er4p-rM30JTrKobgyu4lHBTiXbw"
ADMIN_ID = 6069286437

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Пустая база (наполняешь ты сам!)
WORKING_KEYS = []

@app.route('/')
def index():
    return f"Bot is online. Keys in stock: {len(WORKING_KEYS)}"

# Команда для тебя: добавление ключей
@bot.message_handler(commands=['add'])
def add_keys(message):
    if message.from_user.id == ADMIN_ID:
        # Ищем все ссылки в сообщении
        found = re.findall(r'(vless://[^\s]+|vmess://[^\s]+|trojan://[^\s]+|ss://[^\s]+)', message.text)
        if found:
            WORKING_KEYS.extend(found)
            bot.reply_to(message, f"✅ Добавлено {len(found)} ключей.\nВсего в базе: {len(WORKING_KEYS)}")
        else:
            bot.reply_to(message, "⚠️ Ключи не найдены. Пример:\n/add vless://link1 vless://link2")

# Команда для тебя: очистка базы (если ключи сдохли)
@bot.message_handler(commands=['clear'])
def clear_keys(message):
    if message.from_user.id == ADMIN_ID:
        global WORKING_KEYS
        WORKING_KEYS = []
        bot.reply_to(message, "🗑 База полностью очищена!")

@bot.message_handler(commands=['start'])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🛍 Купить VPN (50 ⭐️)", callback_data="buy_vpn"))
    bot.send_message(message.chat.id, f"Привет! В наличии <b>{len(WORKING_KEYS)}</b> проверенных ключей.\nКоплю на байк! 🏍", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "buy_vpn")
def process_buy(call):
    if not WORKING_KEYS:
        bot.answer_callback_query(call.id, "⚠️ Извини, ключи временно закончились. Зайди позже!", show_alert=True)
        return
    bot.send_invoice(call.message.chat.id, "1 месяц VPN", "Доступ на 30 дней", "pay_vpn", "", "XTR", [LabeledPrice(label="VPN", amount=50)])

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def payment_done(message):
    global WORKING_KEYS
    if WORKING_KEYS:
        key = WORKING_KEYS.pop(0) # Отдаем первый ключ и удаляем его из базы
        bot.reply_to(message, f"✅ Оплата принята!\n\nТвой ключ:\n<code>{key}</code>")
        bot.send_message(ADMIN_ID, f"💰 Продажа! Осталось ключей: {len(WORKING_KEYS)}")
    else:
        bot.reply_to(message, "❌ Ошибка: ключи кончились прямо во время оплаты! Напиши @админу за возвратом.")

if __name__ == '__main__':
    # Запуск Flask
    port = int(os.environ.get('PORT', 5000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    # Запуск Поллинга
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(skip_pending=True)
        except:
            time.sleep(5)
