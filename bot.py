import telebot

# Replace with your actual Telegram bot token
token = '7193109031:AAGnoS9jC6WrQf22yCuiF5DzNH0aFgen4DA'

bot = telebot.TeleBot(token)

# Define button labels and corresponding callback data
buttons = [
    telebot.types.InlineKeyboardButton(text="Buy", callback_data="buy"),
    telebot.types.InlineKeyboardButton(text="Sell", callback_data="sell"),
    telebot.types.InlineKeyboardButton(text="Manage", callback_data="manage"),
    telebot.types.InlineKeyboardButton(text="Help", callback_data="help"),
    telebot.types.InlineKeyboardButton(text="Refer a Friend", callback_data="refer"),
    telebot.types.InlineKeyboardButton(text="Alerts", callback_data="alerts"),
    telebot.types.InlineKeyboardButton(text="Wallet", callback_data="wallet"),
    telebot.types.InlineKeyboardButton(text="Settings", callback_data="settings"),
    telebot.types.InlineKeyboardButton(text="Refresh", callback_data="refresh"),
]

# Create a 3x3 inline keyboard layout
keyboard = telebot.types.InlineKeyboardMarkup(row_width=3)
keyboard.add(*buttons)

@bot.message_handler(commands=['start'])
def start(message):
  chat_id = message.chat.id
  welcome_message = (
      "*Welcome to OINKbot!*\nHere are your options:\n\n"
      "*Main Menu:*\n"
      "- [Social Media Links](your-link-here)\n"
      "- [Referral Program](your-referral-link-here)\n"
      "- *Your Wallet Address:* \`Click to Copy\`\n"
      "- *Solana Balance & Price Tracker*\n"
      "- *Current SOL Price*: [Price Info](your-price-link-here)\n"
  )
  bot.send_message(chat_id, welcome_message, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
  chat_id = call.message.chat.id
  button_data = call.data

  # Handle button data (e.g., send a message or perform an action)
  if button_data == "buy":
    bot.send_message(chat_id, "Buy Token: \n Buy Tonek from www.www.com")
  elif button_data == "sell":
    bot.send_message(chat_id, "To deposit send SOL to below address:\n dfsdfsdfs5d4s3df1s23d1fs3df1sd3f1sd3f1sd3f1sdfsd \n Send Money")
  elif button_data == "sell":
    bot.send_message(chat_id, "To deposit send SOL to below address:\n dfsdfsdfs5d4s3df1s23d1fs3df1sd3f1sd3f1sd3f1sdfsd \n Send Money")
  elif button_data == "manage":
    bot.send_message(chat_id, "Click Link to Open \n Link")
  elif button_data == "help":
    bot.send_message(chat_id, "Which tokens can I trade? \n Any SPL token that is a Sol pair, on Raydium, Orca, and Jupiter. We pick up raydium pairs instantly, and Jupiter will pick up non sol pairs within around 15 minutes \n")
  elif button_data == "refer":
    bot.send_message(chat_id, "Referrals: Your reflink: \n https://t.me/sol_oink_bot?start=HONS Referrals: 0 Lifetime OINKBot earned: 0.00 OINK ($0.00)")
  elif button_data == "sell":
    bot.send_message(chat_id, "To deposit send SOL to below address:\n dfsdfsdfs5d4s3df1s23d1fs3df1sd3f1sd3f1sd3f1sdfsd \n Send Money")
  # Add more cases for other buttons...
  else:
    bot.send_message(chat_id, "Unknown button clicked!")

  # Answer the callback query to prevent repeated notifications
  bot.answer_callback_query(call.id)

if __name__ == '__main__':
  bot.polling()
