import telebot

TOKEN = '7546290209:AAEfSE-qMqwzxogWoFskRfGVcVT-k1o5a6U'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    print(f"Chat ID: {message.chat.id}")
    bot.send_message(message.chat.id, "Your chat ID is " + str(message.chat.id))

bot.polling()
