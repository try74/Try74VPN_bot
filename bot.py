import os
import logging
import requests
import time
from flask import Flask, request, jsonify
import telebot
from telebot.types import LabeledPrice, PreCheckoutQuery

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', '6069286437'))
PRICE_STARS = 35

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

VPN_MIRRORS = [
    "https://github.com/nikita29a/FreeProxyList/raw/refs/heads/main/mirror/1.txt",
    "https://github.com/nikita29a/FreeProxyList/raw/refs/heads/main/mirror/2.txt",
]

def get_vpn_config():
    for url in VPN_MIRRORS:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                lines = r.text.strip().split('\n')
                for line in lines:
                    if line.startswith(('vless://', 'vmess://', 'trojan://')):
                        return line
        except Exception:
            pass
    return None

@bot.message_handler(commands=['start'])
def start_command(message):
    bot.reply_to(
        message,
        f"🤖 <b>VPN Shop</b>\n\n"
        f"💰 Цена: {PRICE_STARS} Stars за рабочий ключ.\n"
        f"/buy — оплатить и получить ключ",
        parse_mode="HTML"
    )

@bot.message_handler(commands=['buy'])
def buy_command(message):
    prices = [LabeledPrice(label="VPN ключ", amount=PRICE_STARS)]
    try:
        bot.send_invoice(
            chat_id=message.chat.id,
            title="VPN ключ",
            description=f"Рабочий VPN-ключ (30 дней)",
            invoice_payload=f"buy_{message.from_user.id}_{int(time.time())}",
            provider_token="",
            currency="XTR",
            prices=prices,
            start_parameter="vpn_key"
        )
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def process_successful_payment(message):
    config = get_vpn_config()
    if not config:
        bot.send_message(ADMIN_ID, "⚠️ Не удалось получить конфиг")
        bot.reply_to(message, "❌ Ошибка получения ключа. Администратор уведомлён.")
        return
    bot.reply_to(
        message,
        f"✅ <b>Оплата прошла!</b>\n\n"
        f"🔑 <b>Ваш ключ:</b>\n"
        f"<code>{config}</code>\n\n"
        f"📱 <b>Как подключиться:</b>\n"
        f"• Android: v2rayNG\n"
        f"• iPhone: Streisand\n\n"
        f"Импортируйте ссылку в приложение.",
        parse_mode="HTML"
    )
    bot.send_message(ADMIN_ID, f"💰 Продажа! {message.from_user.id} купил ключ за {PRICE_STARS} Stars")

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        bot.process_new_updates([update])
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'failed'}), 403

@app.route('/')
def index():
    return "Bot is running"

if __name__ == '__main__':
    bot.remove_webhook()
    webhook_url = os.environ.get('RENDER_EXTERNAL_URL', '') + '/webhook'
    if webhook_url:
        bot.set_webhook(url=webhook_url)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))