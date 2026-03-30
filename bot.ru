import os
import logging
import requests
import psycopg2
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import telebot
from telebot.types import LabeledPrice, PreCheckoutQuery

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8308510677:AAFXv0Q5Er4p-rM30JTrKobgyu4lHBTiXbw"
ADMIN_ID = 6069286437
VPN_PRICE_STARS = 35

# ===== ИНИЦИАЛИЗАЦИЯ =====
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ===== ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ =====
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                expires_at TIMESTAMP,
                auto_renew BOOLEAN DEFAULT TRUE,
                referrer_id BIGINT
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                payment_id TEXT PRIMARY KEY,
                user_id BIGINT,
                amount INTEGER,
                created_at TIMESTAMP
            )
        ''')
    conn.commit()
    conn.close()

init_db()

# ===== ФУНКЦИИ БАЗЫ =====
def save_subscription(user_id, username, expires_at, referrer_id=None):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('''
            INSERT INTO users (user_id, username, expires_at, auto_renew, referrer_id)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                expires_at = EXCLUDED.expires_at,
                auto_renew = EXCLUDED.auto_renew,
                referrer_id = EXCLUDED.referrer_id
        ''', (user_id, username, expires_at, True, referrer_id))
    conn.commit()
    conn.close()

def get_subscription(user_id):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('SELECT expires_at, auto_renew, referrer_id FROM users WHERE user_id = %s', (user_id,))
        row = cur.fetchone()
    conn.close()
    if row:
        return {'expires_at': row[0], 'auto_renew': row[1], 'referrer_id': row[2]}
    return None

def save_payment(payment_id, user_id, amount):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('INSERT INTO payments (payment_id, user_id, amount, created_at) VALUES (%s, %s, %s, %s)',
                    (payment_id, user_id, amount, datetime.now()))
    conn.commit()
    conn.close()

def get_referrer(user_id):
    sub = get_subscription(user_id)
    return sub['referrer_id'] if sub else None

def add_referral_bonus(referrer_id, amount_stars):
    if referrer_id:
        bonus = amount_stars * 0.2
        if bonus >= 1:
            try:
                bot.send_message(referrer_id, f"🎉 +{bonus:.0f} Stars за реферала!")
            except:
                pass

# ===== ПОЛУЧЕНИЕ VPN-КОНФИГА =====
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
                    line = line.strip()
                    if line.startswith(('vless://', 'vmess://', 'trojan://')):
                        return line
        except Exception:
            pass
    return None

def get_referral_link(user_id):
    return f"https://t.me/{bot.get_me().username}?start=ref_{user_id}"

# ===== КОМАНДЫ =====
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith('ref_'):
        referrer_id = int(args[1][4:])
        if referrer_id == user_id:
            referrer_id = None

    sub = get_subscription(user_id)
    if sub and sub['expires_at'] and sub['expires_at'] > datetime.now():
        days_left = (sub['expires_at'] - datetime.now()).days
        status_text = f"✅ Активна до {sub['expires_at'].strftime('%d.%m.%Y')} (осталось {days_left} дн.)"
    else:
        status_text = "❌ Нет активной подписки"

    if not sub:
        save_subscription(user_id, username, datetime.now() - timedelta(days=1), referrer_id)
        if referrer_id:
            bot.send_message(referrer_id, f"🎉 Новый реферал: {username}")

    ref_link = get_referral_link(user_id)

    bot.reply_to(
        message,
        f"🤖 <b>VPN Shop Bot</b>\n\n"
        f"Привет, {username}!\n"
        f"{status_text}\n\n"
        f"💰 Цена: {VPN_PRICE_STARS} Stars за 30 дней\n\n"
        f"📌 Команды:\n"
        f"/buy — купить\n"
        f"/status — статус\n"
        f"/ref — рефералка\n"
        f"/cancel — отменить автопродление\n\n"
        f"🔗 Твоя рефералка: {ref_link}\n"
        f"За друга — 20% от его платежа!",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

@bot.message_handler(commands=['buy'])
def buy_command(message):
    price_amount = VPN_PRICE_STARS * 100
    prices = [LabeledPrice(label="VPN подписка (30 дней)", amount=price_amount)]
    try:
        bot.send_invoice(
            chat_id=message.chat.id,
            title="VPN Подписка",
            description=f"Доступ к VPN на 30 дней\nЦена: {VPN_PRICE_STARS} Stars",
            invoice_payload=f"buy_{message.from_user.id}_{int(time.time())}",
            currency="XTR",
            prices=prices,
            start_parameter="vpn_subscription"
        )
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    if pre_checkout_query.currency == "XTR":
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
    else:
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False, error_message="Только Telegram Stars")

@bot.message_handler(content_types=['successful_payment'])
def process_successful_payment(message):
    payment_info = message.successful_payment
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    amount_stars = payment_info.total_amount // 100

    save_payment(payment_info.telegram_payment_charge_id, user_id, amount_stars)

    referrer = get_referrer(user_id)
    if referrer:
        add_referral_bonus(referrer, amount_stars)

    vpn_config = get_vpn_config()
    if not vpn_config:
        bot.send_message(ADMIN_ID, f"⚠️ Нет конфига для {user_id}")
        bot.reply_to(message, "❌ Ошибка получения ключа. Админ уведомлён.")
        return

    expires_at = datetime.now() + timedelta(days=30)
    save_subscription(user_id, username, expires_at, referrer)

    bot.reply_to(
        message,
        f"✅ <b>Оплата прошла!</b>\n\n"
        f"📅 До {expires_at.strftime('%d.%m.%Y')}\n\n"
        f"🔑 <b>Ваш VPN-ключ:</b>\n"
        f"<code>{vpn_config}</code>\n\n"
        f"📱 <b>Как подключиться:</b>\n"
        f"Android: v2rayNG\n"
        f"iPhone: Streisand\n\n"
        f"В приложении: Импорт → Вставить ссылку\n\n"
        f"⚡ Автопродление включено. Отменить: /cancel",
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    bot.send_message(ADMIN_ID, f"💰 Продажа! @{username} купил подписку за {amount_stars} Stars")

@bot.message_handler(commands=['status'])
def status_command(message):
    user_id = message.from_user.id
    sub = get_subscription(user_id)
    if sub and sub['expires_at'] and sub['expires_at'] > datetime.now():
        days_left = (sub['expires_at'] - datetime.now()).days
        renew = "включено" if sub['auto_renew'] else "отключено"
        bot.reply_to(
            message,
            f"✅ Активна до {sub['expires_at'].strftime('%d.%m.%Y')} (осталось {days_left} дн.)\n🔄 Автопродление: {renew}",
            parse_mode="HTML"
        )
    else:
        bot.reply_to(message, f"❌ Нет активной подписки. /buy — {VPN_PRICE_STARS} Stars")

@bot.message_handler(commands=['ref'])
def ref_command(message):
    user_id = message.from_user.id
    ref_link = get_referral_link(user_id)
    bot.reply_to(message, f"🔗 Твоя рефералка:\n{ref_link}\n\n20% от платежей друзей — твои!", disable_web_page_preview=True)

@bot.message_handler(commands=['cancel'])
def cancel_command(message):
    user_id = message.from_user.id
    sub = get_subscription(user_id)
    if not sub or not sub['expires_at'] or sub['expires_at'] < datetime.now():
        bot.reply_to(message, "❌ Нет активной подписки.")
        return
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE users SET auto_renew = FALSE WHERE user_id = %s", (user_id,))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ Автопродление отключено. Подписка активна до {sub['expires_at'].strftime('%d.%m.%Y')}")

@bot.message_handler(commands=['enable_auto'])
def enable_auto_command(message):
    user_id = message.from_user.id
    sub = get_subscription(user_id)
    if not sub or not sub['expires_at'] or sub['expires_at'] < datetime.now():
        bot.reply_to(message, "❌ Нет активной подписки.")
        return
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("UPDATE users SET auto_renew = TRUE WHERE user_id = %s", (user_id,))
    conn.commit()
    conn.close()
    bot.reply_to(message, "✅ Автопродление включено.")

# ===== АДМИН-КОМАНДЫ =====
@bot.message_handler(commands=['stats'])
def stats_command(message):
    if message.from_user.id != ADMIN_ID:
        return
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM users")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM users WHERE expires_at > %s", (datetime.now(),))
        active = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM payments")
        cnt, amt = cur.fetchone()
    conn.close()
    bot.reply_to(
        message,
        f"📊 Статистика\n\n👥 Всего: {total}\n✅ Активных: {active}\n💰 Продаж: {cnt}\n⭐ Stars: {amt}",
        parse_mode="HTML"
    )

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.replace('/broadcast', '').strip()
    if not text:
        bot.reply_to(message, "Укажи текст: /broadcast текст")
        return
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT user_id FROM users")
        users = cur.fetchall()
    conn.close()
    success = 0
    for (uid,) in users:
        try:
            bot.send_message(uid, f"📢 Рассылка\n\n{text}", parse_mode="HTML")
            success += 1
        except:
            pass
    bot.reply_to(message, f"✅ Отправлено {success} пользователям")

# ===== ВЕБХУК =====
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
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
