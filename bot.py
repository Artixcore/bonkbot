from dotenv import load_dotenv
load_dotenv()


import telebot
import requests
import sqlite3
import logging
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
TOKEN = "7193109031:AAGnoS9jC6WrQf22yCuiF5DzNH0aFgen4DA"

bot = telebot.TeleBot(TOKEN)
executor = ThreadPoolExecutor(max_workers=10)  # For handling concurrent requests

# Define button labels and corresponding callback data
buttons = [
    telebot.types.InlineKeyboardButton(text="       Buy🟢       ", callback_data="buy"),
    telebot.types.InlineKeyboardButton(text="Sell & Manage 🔴", callback_data="sell"),
    telebot.types.InlineKeyboardButton(text="Help", callback_data="help"),
    telebot.types.InlineKeyboardButton(text="Refer a Friend", callback_data="refer"),
    telebot.types.InlineKeyboardButton(text="Alerts", callback_data="alerts"),
    telebot.types.InlineKeyboardButton(text="Wallet 👛", callback_data="wallet"),
    telebot.types.InlineKeyboardButton(text="Settings ⚙️", callback_data="settings"),
    telebot.types.InlineKeyboardButton(text="Refresh 🔄", callback_data="refresh"),
    telebot.types.InlineKeyboardButton(text="Close", callback_data="close"),
]

# Create a 3x3 inline keyboard layout with adjusted spacing for the first row
keyboard = telebot.types.InlineKeyboardMarkup(row_width=3)
keyboard.add(*buttons[:3])
keyboard.add(*buttons[3:])

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Database setup
def create_database():
    conn = sqlite3.connect("referrals.db")
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS user_referrals
                 (chat_id TEXT PRIMARY KEY, referral_count INTEGER, discount_text TEXT)"""
    )
    conn.commit()
    conn.close()


def add_user_referral(chat_id, referral_count, discount_text):
    conn = sqlite3.connect("referrals.db")
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO user_referrals (chat_id, referral_count, discount_text) VALUES (?, ?, ?)",
        (chat_id, referral_count, discount_text),
    )
    conn.commit()
    conn.close()


def get_user_referral_status(chat_id):
    conn = sqlite3.connect("referrals.db")
    c = conn.cursor()
    c.execute(
        "SELECT referral_count, discount_text FROM user_referrals WHERE chat_id = ?",
        (chat_id,),
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {"count": row[0], "discounts": row[1]}
    else:
        return {"count": 0, "discounts": "No discounts available"}


# Initialize the database
create_database()


@bot.message_handler(commands=["start"])
def start(message):
    try:
        chat_id = message.chat.id
        sol_price = get_sol_price()
        sol_balance = get_sol_balance_function(chat_id)
        price_info_link = "https://www.coingecko.com/en/coins/solana"

        sol_price_message = (
            f"*Current SOL Price*: ${sol_price} [Price Info]({price_info_link})\n"
            if sol_price is not None
            else "*Current SOL Price*: Failed to retrieve [Price Info]({price_info_link})\n"
        )

        welcome_message = (
            "*Welcome to OINKbot!*\nHere are your options:\n\n"
            "*Main Menu:*\n"
            "- [Social Media Links](your-link-here)\n"
            "- [Referral Program](your-referral-link-here)\n"
            "- *Your Wallet Address:* `Click to Copy`\n"
            "- *Solana Balance & Price Tracker*\n"
            f"{sol_price_message}"
            f"Sol Balance: {sol_balance} SOL\n"
        )
        bot.send_message(
            chat_id, welcome_message, reply_markup=keyboard, parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        bot.send_message(
            chat_id,
            "An error occurred while processing your request. Please try again later.",
        )


@bot.callback_query_handler(func=lambda call: call.data == "buy")
def handle_buy_button(call):
    try:
        chat_id = call.message.chat.id
        bot.send_message(
            chat_id, "Enter the wallet address of the token you want to buy:"
        )
        bot.register_next_step_handler(call.message, handle_token_address)
    except Exception as e:
        logger.error(f"Error in handle_buy_button: {e}")
        bot.send_message(
            call.message.chat.id,
            "An error occurred while processing your request. Please try again later.",
        )


def handle_token_address(message):
    executor.submit(process_token_address, message)


def process_token_address(message):
    try:
        chat_id = message.chat.id
        token_address = message.text
        token_info, dexscreener_link = get_token_info(token_address)

        if token_info is None:
            bot.send_message(
                chat_id, "Failed to retrieve token information. Please try again."
            )
            return

        sol_balance = get_sol_balance_function(chat_id)
        buy_menu_message = f"Sol Balance: {sol_balance} SOL\n"
        buy_menu_message += f"Dexscreener: [Dexscreener]({dexscreener_link})\n"
        buy_menu_message += (
            f"- Birdeye: [Birdeye Link](https://birdeye.com/{token_address})\n"
        )
        buy_menu_message += (
            f"- Rugcheck: [Rugcheck Link](https://rugcheck.io/{token_address})\n"
        )
        buy_menu_message += "Buy Options:\n"
        buy_menu_message += (
            "- Manual Buy: \n  - .5 SOL\n  - 1 SOL\n  - Buy X SOL (coming soon)\n"
        )
        buy_menu_message += "- Limit Order/Target Buy (coming soon)"

        bot.send_message(chat_id, buy_menu_message, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error in handle_token_address: {e}")
        bot.send_message(
            message.chat.id,
            "An error occurred while processing your request. Please try again later.",
        )


@bot.callback_query_handler(func=lambda call: call.data == "sell")
def handle_sell_button(call):
    executor.submit(process_sell_button, call)


def process_sell_button(call):
    try:
        chat_id = call.message.chat.id
        positions = get_token_positions(chat_id)

        sell_menu_message = "Sell & Manage\n\n"
        sell_menu_message += "Token Positions:\n"
        for position in positions:
            sell_menu_message += f"- {position['token']}: {position['amount']} (P&L: {position['pnl']})\n"
        sell_menu_message += "\nOpen Orders:\n"
        sell_menu_message += "Limit Buy Orders:\n"
        # Add logic to list limit buy orders
        sell_menu_message += "Limit Sell Orders:\n"
        # Add logic to list limit sell orders

        sell_buttons = [
            telebot.types.InlineKeyboardButton(
                text="Open Orders", callback_data="open_orders"
            ),
            telebot.types.InlineKeyboardButton(
                text="Change Order", callback_data="change_order"
            ),
            telebot.types.InlineKeyboardButton(
                text="Cancel Order", callback_data="cancel_order"
            ),
            telebot.types.InlineKeyboardButton(
                text="Sell", callback_data="sell_options"
            ),
            telebot.types.InlineKeyboardButton(
                text="Refresh", callback_data="refresh_sell_manage"
            ),
            telebot.types.InlineKeyboardButton(text="Close", callback_data="close"),
        ]
        sell_keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
        sell_keyboard.add(*sell_buttons)

        bot.send_message(chat_id, sell_menu_message, reply_markup=sell_keyboard)
    except Exception as e:
        logger.error(f"Error in handle_sell_button: {e}")
        bot.send_message(
            call.message.chat.id,
            "An error occurred while processing your request. Please try again later.",
        )


@bot.callback_query_handler(func=lambda call: call.data == "refresh_sell_manage")
def handle_refresh_sell_manage(call):
    executor.submit(process_refresh_sell_manage, call)


def process_refresh_sell_manage(call):
    try:
        chat_id = call.message.chat.id
        positions = get_token_positions(chat_id)

        sell_menu_message = "Sell & Manage\n\n"
        sell_menu_message += "Token Positions:\n"
        for position in positions:
            sell_menu_message += f"- {position['token']}: {position['amount']} (P&L: {position['pnl']})\n"
        sell_menu_message += "\nOpen Orders:\n"
        sell_menu_message += "Limit Buy Orders:\n"
        # Add logic to list limit buy orders
        sell_menu_message += "Limit Sell Orders:\n"
        # Add logic to list limit sell orders

        sell_buttons = [
            telebot.types.InlineKeyboardButton(
                text="Open Orders", callback_data="open_orders"
            ),
            telebot.types.InlineKeyboardButton(
                text="Change Order", callback_data="change_order"
            ),
            telebot.types.InlineKeyboardButton(
                text="Cancel Order", callback_data="cancel_order"
            ),
            telebot.types.InlineKeyboardButton(
                text="Sell", callback_data="sell_options"
            ),
            telebot.types.InlineKeyboardButton(
                text="Refresh", callback_data="refresh_sell_manage"
            ),
            telebot.types.InlineKeyboardButton(text="Close", callback_data="close"),
        ]
        sell_keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
        sell_keyboard.add(*sell_buttons)

        current_message = call.message.text
        current_reply_markup = call.message.reply_markup

        if (
            current_message != sell_menu_message
            or current_reply_markup != sell_keyboard
        ):
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=sell_menu_message,
                reply_markup=sell_keyboard,
            )
        else:
            bot.answer_callback_query(
                callback_query_id=call.id,
                text="Nothing to refresh. The content is already up-to-date.",
            )
    except Exception as e:
        logger.error(f"Error in handle_refresh_sell_manage: {e}")
        bot.send_message(
            call.message.chat.id,
            "An error occurred while processing your request. Please try again later.",
        )


@bot.callback_query_handler(func=lambda call: call.data == "refer")
def handle_refer_button(call):
    executor.submit(process_refer_button, call)


def process_refer_button(call):
    try:
        chat_id = call.message.chat.id
        referral_link = get_user_referral_link(chat_id)
        referral_status = get_user_referral_status(chat_id)

        refer_message = (
            "Your Referral Link:\n"
            f"{referral_link}\n\n"
            "Invite 20 friends and have each of them make a trade to receive 5% off Manual/Buy & Sell transaction fees and 10% off limit order transactions.\n\n"
            "Trading bot fees after 20 referrals:\n"
            "- Regular & Manual Buy/Sell Transactions: 0.95%\n"
            "- Limit Orders Buy/Sell Transactions: 1.125%\n\n"
            f"Current Referrals: {referral_status['count']}\n"
            f"Discounts: {referral_status['discounts']}\n"
        )

        bot.send_message(chat_id, refer_message)
    except Exception as e:
        logger.error(f"Error in handle_refer_button: {e}")
        bot.send_message(
            call.message.chat.id,
            "An error occurred while processing your request. Please try again later.",
        )


@bot.callback_query_handler(func=lambda call: call.data == "refresh")
def handle_refresh_button(call):
    executor.submit(process_refresh_button, call)


def process_refresh_button(call):
    try:
        chat_id = call.message.chat.id

        # Fetch updated balances and positions (replace with your logic)
        sol_balance = get_sol_balance_function(chat_id)
        sol_price = get_sol_price()
        price_info_link = "https://www.coingecko.com/en/coins/solana"

        sol_price_message = (
            f"*Current SOL Price*: ${sol_price} [Price Info]({price_info_link})\n"
            if sol_price is not None
            else "*Current SOL Price*: Failed to retrieve [Price Info]({price_info_link})\n"
        )

        # Prepare the refreshed home message
        refresh_message = (
            "*Welcome to OINKbot!*\nHere are your options:\n\n"
            "*Main Menu:*\n"
            "- [Social Media Links](your-link-here)\n"
            "- [Referral Program](your-referral-link-here)\n"
            "- *Your Wallet Address:* `Click to Copy`\n"
            "- *Solana Balance & Price Tracker*\n"
            f"{sol_price_message}"
            f"Sol Balance: {sol_balance} SOL\n"
        )

        # Get the current message content and reply markup
        current_message = call.message.text
        current_reply_markup = call.message.reply_markup

        # Only edit the message if the content or the reply markup has changed
        if current_message != refresh_message or current_reply_markup != keyboard:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=refresh_message,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
        else:
            bot.answer_callback_query(
                callback_query_id=call.id,
                text="Nothing to refresh. The content is already up-to-date.",
            )
    except telebot.apihelper.ApiException as e:
        if (
            e.result.status_code == 400
            and "message is not modified" in e.result.json()["description"]
        ):
            bot.answer_callback_query(
                callback_query_id=call.id,
                text="Nothing to refresh. The content is already up-to-date.",
            )
        else:
            logger.error(f"Error in handle_refresh_button: {e}")
            bot.send_message(
                call.message.chat.id,
                "An error occurred while processing your request. Please try again later.",
            )


@bot.callback_query_handler(func=lambda call: call.data == "close")
def handle_close_button(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        logger.error(f"Failed to delete message: {e}")
        bot.send_message(
            call.message.chat.id,
            "An error occurred while processing your request. Please try again later.",
        )


def get_token_info(token_address):
    try:
        dexscreener_link = f"https://dexscreener.com/token/{token_address}"
        # Example of verifying the link by making a request (optional)
        response = requests.get(dexscreener_link)
        if response.status_code == 200:
            logger.info(f"Dexscreener link for {token_address} is valid.")
            return {"dexscreener_link": dexscreener_link}, dexscreener_link
        else:
            logger.error(f"Dexscreener link for {token_address} is invalid.")
            return None, None
    except Exception as e:
        logger.error(f"Error in get_token_info: {e}")
        return None, None


def get_sol_price():
    api_url = (
        "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
    )
    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        price_data = response.json()
        sol_price = price_data["solana"]["usd"]
        return sol_price
    except requests.RequestException as e:
        logger.error(f"Failed to retrieve SOL price: {e}")
        return None


def get_sol_balance_function(wallet_address):
    # Example using Solana's JSON RPC API
    api_url = "https://api.mainnet-beta.solana.com"
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [wallet_address],
    }
    try:
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        balance_data = response.json()
        return (
            balance_data.get("result", {}).get("value", 0) / 1e9
        )  # Convert lamports to SOL
    except requests.RequestException as e:
        logger.error(f"Failed to retrieve SOL balance: {e}")
        return 0


def get_token_positions(wallet_address):
    # Implement your logic to retrieve token positions
    # Example positions list (replace with actual data)
    return [
        {"token": "TOKEN1", "amount": 100, "pnl": 10},
        {"token": "TOKEN2", "amount": 200, "pnl": -5},
    ]


def get_user_referral_link(chat_id):
    # Implement your logic to retrieve the user's referral link
    # Example: Generate or fetch from database
    return f"https://yourapp.com/referral/{chat_id}"


def get_user_referral_status(chat_id):
    # Implement your logic to retrieve the user's referral status
    # Example: Fetch from database
    return {
        "count": 5,
        "discounts": "5% off Manual/Buy & Sell, 10% off limit order transactions",
    }


if __name__ == "__main__":
    bot.polling()
