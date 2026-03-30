import os
import telebot

# Get the bot token from the environment variable
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Initialize the bot with the token
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Use /help to see the available commands.")

# Handle other commands or messages

# Start polling for new messages
if __name__ == '__main__':
    bot.polling()