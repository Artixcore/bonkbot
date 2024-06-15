import time
import telebot
import requests
import sqlite3
import logging
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv()
TOKEN = "7193109031:AAGnoS9jC6WrQf22yCuiF5DzNH0aFgen4DA"

bot = telebot.TeleBot(TOKEN)
executor = ThreadPoolExecutor(max_workers=10)  # For handling concurrent requests

# Define button labels and corresponding callback data
top_buttons = [
    telebot.types.InlineKeyboardButton(text="Buy🟢", callback_data="buy"),
    telebot.types.InlineKeyboardButton(text="Sell & Manage ", callback_data="sell"),
]

other_buttons = [
    telebot.types.InlineKeyboardButton(text="Help", callback_data="help"),
    telebot.types.InlineKeyboardButton(text="Wallet ", callback_data="wallet"),
    telebot.types.InlineKeyboardButton(text="Alerts", callback_data="alerts"),
]

other_buttons_2 = [
    telebot.types.InlineKeyboardButton(text="Refer a Friend", callback_data="refer"),
    telebot.types.InlineKeyboardButton(text="Settings ⚙️", callback_data="settings"),
    telebot.types.InlineKeyboardButton(text="Refresh ", callback_data="refresh"),
]

close_button = [telebot.types.InlineKeyboardButton(text="Close", callback_data="close")]  # Single button for the last row

# Create inline keyboard layout
keyboard = telebot.types.InlineKeyboardMarkup()  # No row width specified for flexible arrangement

# Add buttons in the desired order, ensuring each row has the specified number of buttons
keyboard.row(*top_buttons)  # Unpack elements of top_buttons list for first row (2 buttons)
keyboard.row(*other_buttons[:2])  # Unpack first 2 elements of other_buttons for second row (2 buttons)
keyboard.row(other_buttons[2])  # Single button for the third row
keyboard.row(*other_buttons_2[:2])  # Unpack first 2 elements of other_buttons_2 for fourth row (2 buttons)
keyboard.row(other_buttons_2[2])  # Single button for the fifth row
keyboard.row(close_button[0])  # Single button for the last row

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

def add_user_token(chat_id, token_address, amount):
    conn = sqlite3.connect("referrals.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO user_tokens (chat_id, token_address, amount) VALUES (?, ?, ?)",
        (chat_id, token_address, amount),
    )
    conn.commit()
    conn.close()

def get_user_tokens(chat_id):
    conn = sqlite3.connect("referrals.db")
    c = conn.cursor()
    c.execute(
        "SELECT token_address, amount FROM user_tokens WHERE chat_id = ?", (chat_id,)
    )
    rows = c.fetchall()
    conn.close()
    return rows

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


def show_progress(chat_id, steps=3, interval=1):
    for i in range(steps):
        time.sleep(interval)
        bot.send_message(chat_id, f"Processing... ({i+1}/{steps})")


@bot.callback_query_handler(func=lambda call: call.data == "buy")
def handle_buy_button(call):
    chat_id = call.message.chat.id
    bot.send_message(chat_id, "Enter the wallet address of the token you want to buy:")
    bot.register_next_step_handler(call.message, handle_token_address)


def handle_token_address(message):
    executor.submit(process_token_address, message)


def process_token_address(message):
    chat_id = message.chat.id
    show_progress(chat_id)
    token_address = message.text
    token_info, dexscreener_link = get_token_info(token_address)

    if token_info is None:
        bot.send_message(
            chat_id, "Failed to retrieve token information. Please try again."
        )
        return

    sol_balance = get_sol_balance_function(chat_id)

    token_details_message = (
        f"{token_info['symbol']} | {token_info['name']} | {token_address}\n\n"
        f"Price: ${token_info['price']}\n"
        f"5m: {token_info['price_change_5m']}%, 1h: {token_info['price_change_1h']}%, "
        f"6h: {token_info['price_change_6h']}%, 24h: {token_info['price_change_24h']}%\n"
        f"Market Cap: {token_info['market_cap']}\n\n"
        f"Price Impact (5.0000 SOL): {token_info['price_impact']}%\n\n"
        f"Wallet Balance: {sol_balance} SOL\n"
        "To buy, press one of the buttons below."
    )

    # Define buttons
    buy_buttons = [
        telebot.types.InlineKeyboardButton(text="Cancel", callback_data="cancel_buy"),
        telebot.types.InlineKeyboardButton(text="Explorer", url=f"https://explorer.solana.com/address/{token_address}"),
        telebot.types.InlineKeyboardButton(text="Birdeye", url=f"https://birdeye.so/token/{token_address}"),
        telebot.types.InlineKeyboardButton(text="Scan", url=f"https://solscan.io/token/{token_address}"),
        telebot.types.InlineKeyboardButton(text="Buy 1.0 SOL", callback_data=f"buy_1_{token_address}"),
        telebot.types.InlineKeyboardButton(text="Buy 5.0 SOL", callback_data=f"buy_5_{token_address}"),
        telebot.types.InlineKeyboardButton(text="Buy X SOL", callback_data=f"buy_x_{token_address}"),
        telebot.types.InlineKeyboardButton(text="Refresh", callback_data=f"refresh_token_{token_address}"),
    ]
    buy_keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
    buy_keyboard.add(*buy_buttons)

    bot.send_message(chat_id, token_details_message, reply_markup=buy_keyboard, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def handle_buy_option(call):
    chat_id = call.message.chat.id
    token_address = call.data.split("_")[-1]
    amount = call.data.split("_")[1]

    bot.send_message(chat_id, f"Initiating the purchase of {amount} SOL for token {token_address}. Please wait...")
    show_progress(chat_id)

    # Simulate successful purchase
    bot.send_message(chat_id, f"Successfully bought {amount} SOL of token {token_address}!")


@bot.callback_query_handler(func=lambda call: call.data == "cancel_buy")
def handle_cancel_buy(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        logger.error(f"Failed to delete message: {e}")
        bot.send_message(
            call.message.chat.id,
            "An error occurred while processing your request. Please try again later.",
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("refresh_token_"))
def handle_refresh_token(call):
    chat_id = call.message.chat.id
    token_address = call.data.split("_")[-1]
    show_progress(chat_id)

    token_info, dexscreener_link = get_token_info(token_address)

    if token_info is None:
        bot.send_message(
            chat_id, "Failed to retrieve token information. Please try again."
        )
        return

    sol_balance = get_sol_balance_function(chat_id)

    token_details_message = (
        f"{token_info['symbol']} | {token_info['name']} | {token_address}\n\n"
        f"Price: ${token_info['price']}\n"
        f"5m: {token_info['price_change_5m']}%, 1h: {token_info['price_change_1h']}%, "
        f"6h: {token_info['price_change_6h']}%, 24h: {token_info['price_change_24h']}%\n"
        f"Market Cap: {token_info['market_cap']}\n\n"
        f"Price Impact (5.0000 SOL): {token_info['price_impact']}%\n\n"
        f"Wallet Balance: {sol_balance} SOL\n"
        "To buy, press one of the buttons below."
    )

    # Define buttons
    buy_buttons = [
        telebot.types.InlineKeyboardButton(text="Cancel", callback_data="cancel_buy"),
        telebot.types.InlineKeyboardButton(text="Explorer", url=f"https://explorer.solana.com/address/{token_address}"),
        telebot.types.InlineKeyboardButton(text="Birdeye", url=f"https://birdeye.so/token/{token_address}"),
        telebot.types.InlineKeyboardButton(text="Scan", url=f"https://solscan.io/token/{token_address}"),
        telebot.types.InlineKeyboardButton(text="Buy 1.0 SOL", callback_data=f"buy_1_{token_address}"),
        telebot.types.InlineKeyboardButton(text="Buy 5.0 SOL", callback_data=f"buy_5_{token_address}"),
        telebot.types.InlineKeyboardButton(text="Buy X SOL", callback_data=f"buy_x_{token_address}"),
        telebot.types.InlineKeyboardButton(text="Refresh", callback_data=f"refresh_token_{token_address}"),
    ]
    buy_keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
    buy_keyboard.add(*buy_buttons)

    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=token_details_message,
        reply_markup=buy_keyboard,
        parse_mode="Markdown"
    )


def get_token_info(token_address):
    try:
        # Mock response; replace with actual API call
        token_info = {
            "symbol": "MOSK",
            "name": "Elan Mosk",
            "price": 0.732,
            "price_change_5m": -12.94,
            "price_change_1h": 6.02,
            "price_change_6h": -11.07,
            "price_change_24h": float('nan'),  # Example NaN value
            "market_cap": "$731.60K",
            "price_impact": 3.64,
        }
        dexscreener_link = f"https://dexscreener.com/token/{token_address}"
        return token_info, dexscreener_link
    except Exception as e:
        logger.error(f"Error fetching token info: {e}")
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

def show_progress(chat_id, steps=3, interval=1):
    for i in range(steps):
        time.sleep(interval)
        bot.send_message(chat_id, f"Processing... ({i+1}/{steps})")

@bot.callback_query_handler(func=lambda call: call.data == "sell")
def handle_sell_button(call):
    chat_id = call.message.chat.id
    show_progress(chat_id)
    # Example of fetching user's positions to simulate management
    positions = get_token_positions("user_wallet_address_placeholder")
    positions_message = "Your current positions:\n" + "\n".join([f"{pos['token']}: {pos['amount']} units" for pos in positions])
    sell_buttons = [
        telebot.types.InlineKeyboardButton("Sell 1 unit", callback_data="sell_1"),
        telebot.types.InlineKeyboardButton("Sell 5 units", callback_data="sell_5"),
        telebot.types.InlineKeyboardButton("Manage Holdings", callback_data="manage_holdings")
    ]
    sell_keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
    sell_keyboard.add(*sell_buttons)
    bot.send_message(chat_id, positions_message, reply_markup=sell_keyboard)

def handle_sell_option(call, units):
    chat_id = call.message.chat.id
    # Simulate a sell operation
    result = sell_token("user_wallet_address_placeholder", units)  # This function would need to be implemented
    bot.send_message(chat_id, f"Sold {units} units. {result}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("sell_"))
def handle_sell_actions(call):
    units = int(call.data.split("_")[1])
    handle_sell_option(call, units)

@bot.callback_query_handler(func=lambda call: call.data == "manage_holdings")
def handle_manage_holdings(call):
    chat_id = call.message.chat.id
    show_progress(chat_id)
    # Here you might let users change settings or reallocate holdings
    bot.send_message(chat_id, "Manage your holdings here. Feature under development.")

def sell_token(wallet_address, units):
    # Placeholder function to simulate selling tokens
    return f"Transaction completed for {units} units."

def get_token_positions(wallet_address):
    # Placeholder function to simulate retrieving token positions
    return [
        {"token": "Token1", "amount": 100},
        {"token": "Token2", "amount": 200}
    ]

def get_user_referral_link(chat_id):
    # Retrieve the user's referral link
    conn = sqlite3.connect("referrals.db")
    c = conn.cursor()
    c.execute(
        "SELECT referral_count FROM user_referrals WHERE chat_id = ?",
        (chat_id,),
    )
    row = c.fetchone()
    conn.close()
    if row:
        return f"https://yourapp.com/referral/{chat_id}"
    else:
        return None


@bot.callback_query_handler(func=lambda call: call.data == "refer")
def handle_refer_button(call):
    chat_id = call.message.chat.id
    show_progress(chat_id)

    referral_link = get_user_referral_link(chat_id)
    referral_status = get_user_referral_status(chat_id)

    if referral_link:
        refer_message = (
            "Your Referral Link:\n"
            f"{referral_link}\n\n"
            "Invite friends to earn rewards!\n\n"
            f"Current Referrals: {referral_status['count']}\n"
            f"Discounts: {referral_status['discounts']}\n"
        )
    else:
        refer_message = "You don't have a referral link yet. Start using the bot to generate one!"

    bot.send_message(chat_id, refer_message)


if __name__ == "__main__":
    bot.polling()
