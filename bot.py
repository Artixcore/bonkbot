import time
import telebot
import requests
import sqlite3
import logging
import random
import string
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv()
TOKEN = "7193109031:AAGnoS9jC6WrQf22yCuiF5DzNH0aFgen4DA"

bot = telebot.TeleBot(TOKEN)
executor = ThreadPoolExecutor(max_workers=10)  # For handling concurrent requests

top_buttons = [
    telebot.types.InlineKeyboardButton(text="Buy 🟢", callback_data="buy"),
    telebot.types.InlineKeyboardButton(text="Sell & Manage 🔴", callback_data="sell"),
]

other_buttons = [
    telebot.types.InlineKeyboardButton(text="Help 💁🏻", callback_data="help"),
    telebot.types.InlineKeyboardButton(text="Wallet 👛", callback_data="wallet"),
    telebot.types.InlineKeyboardButton(text="Alerts 🚨", callback_data="alerts"),
]

other_buttons_2 = [
    telebot.types.InlineKeyboardButton(text="Refer a Friend 🍒", callback_data="refer"),
    telebot.types.InlineKeyboardButton(text="Settings ⚙️", callback_data="settings"),
    telebot.types.InlineKeyboardButton(text="Refresh 🔄", callback_data="refresh"),
]

close_button = [telebot.types.InlineKeyboardButton(text="Close ❎", callback_data="close")] # Single button for the last row

# Create inline keyboard layout
keyboard = telebot.types.InlineKeyboardMarkup() # No row width specified for flexible arrangement

# Add buttons in the desired order, ensuring each row has a maximum of 2 buttons
keyboard.row(top_buttons[0], top_buttons[1]) # 1st row
keyboard.row(other_buttons[0], other_buttons[1], other_buttons[2]) # 2nd row
keyboard.row(other_buttons_2[0], other_buttons_2[1], other_buttons_2[2]) # 3rd row
keyboard.row(close_button[0]) 

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
    c.execute(
        """CREATE TABLE IF NOT EXISTS user_wallets
                 (chat_id TEXT PRIMARY KEY, wallet_address TEXT)"""
    )
    conn.commit()
    conn.close()

def add_user_wallet(chat_id, wallet_address):
    conn = sqlite3.connect("referrals.db")
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO user_wallets (chat_id, wallet_address) VALUES (?, ?)",
        (chat_id, wallet_address),
    )
    conn.commit()
    conn.close()

def get_user_wallet(chat_id):
    conn = sqlite3.connect("referrals.db")
    c = conn.cursor()
    c.execute("SELECT wallet_address FROM user_wallets WHERE chat_id = ?", (chat_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

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
        wallet_address = get_user_wallet(chat_id)
        
        if not wallet_address:
            wallet_address = generate_wallet_address()
            add_user_wallet(chat_id, wallet_address)
        
        sol_balance = get_sol_balance_function(wallet_address)
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
            f"- *Your Wallet Address:* `{wallet_address}`\n"
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

def generate_wallet_address():
    return 'SOL' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=32))

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

    wallet_address = get_user_wallet(chat_id)
    sol_balance = get_sol_balance_function(wallet_address)

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
        telebot.types.InlineKeyboardButton(
            text="Explorer", url=f"https://explorer.solana.com/address/{token_address}"
        ),
        telebot.types.InlineKeyboardButton(
            text="Birdeye", url=f"https://birdeye.so/token/{token_address}"
        ),
        telebot.types.InlineKeyboardButton(
            text="Scan", url=f"https://solscan.io/token/{token_address}"
        ),
        telebot.types.InlineKeyboardButton(
            text="Buy 1.0 SOL", callback_data=f"buy_1_{token_address}"
        ),
        telebot.types.InlineKeyboardButton(
            text="Buy 5.0 SOL", callback_data=f"buy_5_{token_address}"
        ),
        telebot.types.InlineKeyboardButton(
            text="Buy X SOL", callback_data=f"buy_x_{token_address}"
        ),
        telebot.types.InlineKeyboardButton(
            text="Refresh", callback_data=f"refresh_token_{token_address}"
        ),
    ]
    buy_keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
    buy_keyboard.add(*buy_buttons)

    bot.send_message(
        chat_id, token_details_message, reply_markup=buy_keyboard, parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def handle_buy_option(call):
    chat_id = call.message.chat.id
    token_address = call.data.split("_")[-1]
    amount = call.data.split("_")[1]

    bot.send_message(
        chat_id,
        f"Initiating the purchase of {amount} SOL for token {token_address}. Please wait...",
    )
    show_progress(chat_id)

    # Simulate successful purchase
    bot.send_message(
        chat_id, f"Successfully bought {amount} SOL of token {token_address}!"
    )

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

    wallet_address = get_user_wallet(chat_id)
    sol_balance = get_sol_balance_function(wallet_address)

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
        telebot.types.InlineKeyboardButton(
            text="Explorer", url=f"https://explorer.solana.com/address/{token_address}"
        ),
        telebot.types.InlineKeyboardButton(
            text="Birdeye", url=f"https://birdeye.so/token/{token_address}"
        ),
        telebot.types.InlineKeyboardButton(
            text="Scan", url=f"https://solscan.io/token/{token_address}"
        ),
        telebot.types.InlineKeyboardButton(
            text="Buy 1.0 SOL", callback_data=f"buy_1_{token_address}"
        ),
        telebot.types.InlineKeyboardButton(
            text="Buy 5.0 SOL", callback_data=f"buy_5_{token_address}"
        ),
        telebot.types.InlineKeyboardButton(
            text="Buy X SOL", callback_data=f"buy_x_{token_address}"
        ),
        telebot.types.InlineKeyboardButton(
            text="Refresh", callback_data=f"refresh_token_{token_address}"
        ),
    ]
    buy_keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
    buy_keyboard.add(*buy_buttons)

    bot.edit_message_text(
        chat_id=chat_id,
        message_id=call.message.message_id,
        text=token_details_message,
        reply_markup=buy_keyboard,
        parse_mode="Markdown",
    )

@bot.callback_query_handler(func=lambda call: call.data == "sell")
def handle_sell_button(call):
    chat_id = call.message.chat.id
    show_progress(chat_id)
    # Example of fetching user's positions to simulate management
    wallet_address = get_user_wallet(chat_id)
    positions = get_token_positions(wallet_address)
    positions_message = "Your current positions:\n" + "\n".join(
        [f"{pos['token']}: {pos['amount']} units" for pos in positions]
    )
    sell_buttons = [
        telebot.types.InlineKeyboardButton("Sell 1 unit", callback_data="sell_1"),
        telebot.types.InlineKeyboardButton("Sell 5 units", callback_data="sell_5"),
        telebot.types.InlineKeyboardButton(
            "Manage Holdings", callback_data="manage_holdings"
        ),
    ]
    sell_keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
    sell_keyboard.add(*sell_buttons)
    bot.send_message(chat_id, positions_message, reply_markup=sell_keyboard)

def handle_sell_option(call, units):
    chat_id = call.message.chat.id
    wallet_address = get_user_wallet(chat_id)
    # Simulate a sell operation
    result = sell_token(wallet_address, units)  # This function would need to be implemented
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
    return [{"token": "Token1", "amount": 100}, {"token": "Token2", "amount": 200}]

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
        refer_message = (
            "You don't have a referral link yet. Start using the bot to generate one!"
        )

    bot.send_message(chat_id, refer_message)

@bot.callback_query_handler(func=lambda call: call.data == "wallet")
def handle_wallet_button(call):
    chat_id = call.message.chat.id
    show_progress(chat_id)
    wallet_address = get_user_wallet(chat_id)
    if not wallet_address:
        wallet_address = generate_wallet_address()
        add_user_wallet(chat_id, wallet_address)
    bot.send_message(chat_id, f"Your wallet address is: `{wallet_address}`", parse_mode="Markdown")

def get_token_info(token_address):
    try:
        # CoinGecko API for token information
        api_url = f"https://api.coingecko.com/api/v3/coins/{token_address}"
        response = requests.get(api_url)
        response.raise_for_status()
        token_data = response.json()

        # Extracting relevant information
        token_info = {
            "symbol": token_data["symbol"].upper(),
            "name": token_data["name"],
            "price": token_data["market_data"]["current_price"]["usd"],
            "price_change_5m": token_data["market_data"].get("price_change_percentage_5m", 0),
            "price_change_1h": token_data["market_data"].get("price_change_percentage_1h", 0),
            "price_change_6h": token_data["market_data"].get("price_change_percentage_6h", 0),
            "price_change_24h": token_data["market_data"]["price_change_percentage_24h"],
            "market_cap": token_data["market_data"]["market_cap"]["usd"],
            "price_impact": 0.0,  # Placeholder as price impact calculation is complex
        }
        dexscreener_link = f"https://www.coingecko.com/en/coins/{token_address}"
        return token_info, dexscreener_link
    except requests.RequestException as e:
        logger.error(f"Error fetching token info: {e}")
        return None, None
    except KeyError as e:
        logger.error(f"Key error: {e}")
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

if __name__ == "__main__":
    bot.polling()
