# bot.py
import os
import logging
import telebot
import random
from datetime import datetime
from dotenv import load_dotenv
from models import User, Trading, Coin
import requests
from utils.is_mint_address import is_mint_address
from utils.get_price_and_symbol import get_price_and_symbol
from utils.convert_sol import convert_sol_to_usdc

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize bot
bot = telebot.TeleBot(os.getenv('TELEGRAM_API_KEY'))

trading_tips = [
    "💡 Tip: Consider diversifying your portfolio to manage risk.",
    "💡 Tip: Never invest more than you can afford to lose - even in paper trading!",
    "💡 Tip: Check /pnl regularly to evaluate your trading strategy.",
    "💡 Tip: Use /lock to safeguard profits during volatile periods.",
    "💡 Tip: Research tokens before buying, even in simulator trading."
]

# Command handlers
@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle /start command - introduce the bot and register user"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Register user
    user = User(telegram_id=user_id, username=username, first_name=first_name, last_name=last_name, sol_balance=5, usdc_balance=100)
    user.save()
    
    welcome_text = (
        f"""🚀 Welcome to Solana Meme Trader, {first_name}! 🚀

🌙 Ready to practice moon-shooting without risking real SOL? You're in the right place!

💰 Starting Balance:
   • 5 SOL 🪙
   • 100 USDC 💵

🎮 Quick Commands:
   • /buy - Grab some meme coins 🛒
   • /sell - Take profits (or losses) 📈
   • /list - Browse available tokens 📋
   • /balance - Check your holdings 💼

💎 Join our community: https://t.me/solanasimtraders

Type /help for all commands and tips!"""
    )
    
    bot.send_message(message.chat.id, welcome_text)
    

@bot.message_handler(commands=['list'])
def list_coins(message):
    """List available meme coins for trading"""
    user_id = message.from_user.id
    User.update_last_active(telegram_id=user_id)
    user = User.get_by_telegram_id(user_id)
    coins = user.coins
    
    if len(coins) == 0:
        bot.send_message(message.chat.id, "You don't have any coins available for trading. Use /track to add a token.")
        return
    
    response = "🪙 *Available Meme Coins* 🪙\n\n"
    for coin in coins:
        response += f"*{coin.symbol}* ({coin.amount})\n"
        response += f"Price: {coin.price:.8f} SOL\n\n"
    
    response += f"To buy: /buy [SYMBOL] [usdc_AMOUNT or SOL]\n"
    response += f"Example: \n- `/buy {coin.symbol} 20USDC`\n- /buy {coin.symbol} 0.2SOL\n\nEnsure the currency is either USDC or SOL.\n"
    response += "Use /track to add a new token to your portfolio."
    
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

@bot.message_handler(commands=['track'])
def track_token(message):
    """Track a token by its mint address"""
    user_id = message.from_user.id
    User.update_last_active(telegram_id=user_id)
    
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(
            message.chat.id, 
            "Please use the format: `/track [MINT_ADDRESS]`\n"
            "Example: `/track 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU`",
            parse_mode="Markdown"
        )
        return
    
    mint_address = args[1]
    
    # Get price data from DexScreener
    try:
        symbol = get_price_and_symbol(mint_address)[1]
        coin = Coin(address=mint_address, symbol=symbol, txns=[])
        bot.send_message(
            message.chat.id,
            f"✅ Successfully tracking  {coin.symbol}!\n"
            f"Current price: ${coin.price:.6f})\n\n"
            f"You can now buy this token using: `/buy {coin.symbol} [SOL or USDC]`"
        )
        
    except Exception as e:
        bot.send_message(message.chat.id, f"Error tracking token: {str(e)}")

@bot.message_handler(commands=['buy'])
def buy_coin(message):
    """Buy a meme coin using SOL or USDC"""
    user_id = message.from_user.id
    User.update_last_active(telegram_id=user_id)
    
    args = message.text.split(" ")
    if len(args) != 3:
        bot.send_message(
            message.chat.id, 
            "Please use the format: `/buy [Wallet Address or Token Symbol] [AMOUNT in SOL or USDC]`\n"
            "Example: `/buy 38AzpaUxVEGhFjXxJx86xsb5xxWW1c1DKvqHhPXBpump 0.5SOL`\n\n"
            "Use either SOL or USDC as the buying currency.",
            parse_mode="Markdown"
        )
        return

    address_or_symbol = args[1]
    amount_str = args[2]
    usdc_amount = None

    # Determine if it's a wallet address or a token symbol
    if is_mint_address(address_or_symbol):
        address = address_or_symbol
        try:
            symbol = get_price_and_symbol(address_or_symbol)[1]
        except Exception:
            bot.send_message(
                message.chat.id,
                "Invalid address. Please provide a valid wallet address or a tracked token symbol."
            )
            return
    else:
        user = User.get_by_telegram_id(user_id)
        token = next((coin for coin in user.coins if coin.symbol.lower() == address_or_symbol.lower()), None)
        if not token:
            bot.send_message(
                message.chat.id,
                "Please provide a valid wallet address or a tracked token symbol."
            )
            return
        address = token.address
        symbol = address_or_symbol.upper()

    # Parse amount
    if amount_str.lower().endswith("sol") and len(amount_str) > 3:
        try:
            amount = float(amount_str[:-3])
            usdc_amount = convert_sol_to_usdc(amount)
        except ValueError:
            bot.send_message(
                message.chat.id,
                "Invalid SOL amount. Please enter a numeric value like `0.5SOL`."
            )
            return

    elif amount_str.lower().endswith("usdc") and len(amount_str) > 4:
        try:
            usdc_amount = float(amount_str[:-4])
        except ValueError:
            bot.send_message(
                message.chat.id,
                "Invalid USDC amount. Please enter a numeric value like `10USDC`."
            )
            return

    else:
        bot.send_message(
            message.chat.id,
            "Please specify the amount with `SOL` or `USDC` suffix (e.g. `1.2SOL` or `15USDC`)."
        )
        return

    # Proceed to buy
    outcome = Trading.buy_coin(telegram_id=user_id, address=address, usdc_amount=usdc_amount)
    if outcome[0]:
        bot.send_message(message.chat.id, outcome[0])
    else:
        bot.send_message(message.chat.id, outcome[1])
        return

    # Show updated balance
    user = User.get_by_telegram_id(user_id)
    bot.send_message(
        message.chat.id,
        f"Your balances:\n"
        f"SOL: {user.sol_balance:.4f}\n"
        f"USDC: {user.usdc_balance:.2f}"
    )
    
    # After successful purchase, add this:
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("View Portfolio", callback_data="view_portfolio"),
        telebot.types.InlineKeyboardButton("Buy More", callback_data=f"buy_more_{symbol}")
    )
    
    bot.send_message(
        message.chat.id,
        f"Want to see your updated portfolio or buy more {symbol}?",
        reply_markup=markup
    )

@bot.message_handler(commands=['sell'])
def sell_coin(message):
    """Sell a percentage of coin holdings"""
    
    user_id = message.from_user.id
    User.update_last_active(telegram_id=user_id)
    
    args = message.text.split()
    if len(args) != 3:
        bot.send_message(
            message.chat.id, 
            "Please use the format: `/sell [Mint Address or MINT SYMBOL] [AMOUNT in SOL or usdc]`\nExample: `/sell 38AzpaUxVEGhFjXxJx86xsb5xxWW1c1DKvqHhPXBpump 100\n\nThis will sell 100% of the currency`",
            parse_mode="Markdown"
        )
        return
    address = args[1]
    if not is_mint_address(args[1]):
        user = User.get_by_telegram_id(user_id)
        address = [coin.address for coin in user.coins if coin.symbol == args[1]][0]
        if not address:
            bot.send_message(
                message.chat.id,
                "Please use a valid mint address or tracked token(Use the symbol of the token)"
            )
            return 
        
    amount_str: str = args[2]
    
    try:
        amount= float(amount_str)
        
    except ValueError:
        bot.send_message(
            message.chat.id,
            "Please enter in a numerical value for the amount of tokens"
        )
        return 
    outcome = Trading.sell_coin(telegram_id=user_id, address=address, percentage=amount)
    if outcome[0]:
        bot.send_message(
            message.chat.id,
            outcome[1]
        )
    else:
        bot.send_message(
            message.chat.id,
            outcome[1]
        )
        return
    
    user = User.get_by_telegram_id(user_id)
    # Show updated balance
    bot.send_message(
            message.chat.id,
            f"Your balance:\n"
            f"SOL: {user.sol_balance:.4f}\n"
            f"usdc: {user.usdc_balance:.2f}"
        )
    

@bot.message_handler(commands=['airdrop'])
def airdrop(message):
    """Claim a free usdc airdrop"""
    user_id = message.from_user.id
    User.update_last_active(telegram_id=user_id)
    
    args = message.text.split()
    if len(args) != 2:
        bot.send_message(
            message.chat.id, 
            "Please use the format: `/airdrop [AMOUNT]`\nExample: `/airdrop 50`",
            parse_mode="Markdown"
        )
        return
    
    try:
        usdc_amount = float(args[1])
        if usdc_amount <= 0:
            bot.send_message(message.chat.id, "Amount must be greater than 0")
            return
    except ValueError:
        bot.send_message(message.chat.id, "Invalid amount. Please enter a valid number.")
        return
    
    outcome = Trading.airdrop_usdc(usdc_amount=usdc_amount, telegram_id=user_id)
    bot.send_message(message.chat.id, outcome[1])
    

@bot.message_handler(commands=['lock'])
def lock_sol(message):
    """Convert SOL to usdc"""
    user_id = message.from_user.id
    User.update_last_active(telegram_id=user_id)
    
    args = message.text.split()
    if len(args) != 2:
        bot.send_message(
            message.chat.id, 
            "Please use the format: `/lock [SOL_AMOUNT]`\nExample: `/lock 1.5`",
            parse_mode="Markdown"
        )
        return
    
    try:
        sol_amount = float(args[1])
        if sol_amount <= 0:
            bot.send_message(message.chat.id, "Amount must be greater than 0")
            return
    except ValueError:
        bot.send_message(message.chat.id, "Invalid amount. Please enter a valid number.")
        return
    
    
    # Process lock (convert SOL to usdc)
    success, message_text = Trading.lock_sol(telegram_id=user_id, sol_amount=sol_amount)
    if not success:
        bot.send_message(message.chat.id, message_text)
        return
        
    user = User.get_by_telegram_id(user_id)
    # Show updated balance
    bot.send_message(
            message.chat.id,
            f"Updated balances:\n"
            f"SOL: {user.sol_balance:.4f}\n"
            f"usdc: {user.usdc_balance:.2f}"
        )

@bot.message_handler(commands=['unlock'])
def unlock_usdc(message):
    """Convert usdc back to SOL"""
    user_id = message.from_user.id
    User.update_last_active(telegram_id=user_id)
    
    args = message.text.split()
    if len(args) != 2:
        bot.send_message(
            message.chat.id, 
            "Please use the format: `/unlock [USDC_AMOUNT]`\nExample: `/unlock 230`",
            parse_mode="Markdown"
        )
        return
    
    try:
        usdc_amount = float(args[1])
        if usdc_amount <= 0:
            bot.send_message(message.chat.id, "Amount must be greater than 0")
            return
    except ValueError:
        bot.send_message(message.chat.id, "Invalid amount. Please enter a valid number.")
        return
    
    
    # Process lock (convert SOL to usdc)
    success, message_text = Trading.unlock_usdc(telegram_id=user_id, usdc_amount=usdc_amount)
    if not success:
        bot.send_message(message.chat.id, message_text)
        return
        
    user = User.get_by_telegram_id(user_id)
    # Show updated balance
    bot.send_message(
            message.chat.id,
            f"Updated balances:\n"
            f"SOL: {user.sol_balance:.4f}\n"
            f"usdc: {user.usdc_balance:.2f}"
        )
    bot.send_message(message.chat.id, random.choice(trading_tips))

@bot.message_handler(commands=['balance'])
def show_balance(message):
    """Show user's wallet balance"""
    user_id = message.from_user.id
    User.update_last_active(telegram_id=user_id)
    
    user = User.get_by_telegram_id(telegram_id=user_id)
    sol_balance = user.sol_balance
    usdc_balance = user.usdc_balance
    coins_balance = [{"symbol": coin.symbol, "amount": coin.amount} for coin in user.coins]

    response_lines = [
        "*💼 Wallet Balances:*",
        f"- 🪙 *SOL:* {sol_balance:.4f}",
        f"- 💵 *USDC:* {usdc_balance:.2f}"
    ]

    if coins_balance:
        response_lines.append("\n*📦 Other Tokens:*")
        for coin in coins_balance:
            response_lines.append(f"- {coin['symbol']}: {coin['amount']:.4f}")

    response = "\n".join(response_lines)
    
    bot.send_message(message.chat.id, response, parse_mode="Markdown")
    
    


@bot.message_handler(commands=['pnl'])
def show_pnl(message):
    """Show user's profit and loss statistics"""
    user_id = message.from_user.id
    User.update_last_active(telegram_id=user_id)
    user = User.get_by_telegram_id(telegram_id=user_id)
    total_pnl = user.pnl
    
    args = message.text.split()[1:]
    
    if len(args) == 0:
        response = f"Your current PnL is {total_pnl:.5f}%"
    elif args[0].lower() == "all":
        response = f"*Total PNL*: {total_pnl:.5f}%\n\n"
        response += "*Other PnL*: \n"
        for coin in user.coins:
            response += f"*{coin.symbol}*: {coin.pnl:.5f}%\n"
        
    else:
        response = f"*Total PNL*: {total_pnl:.5f}%\n\n"
        response += "*Other PnL*: \n"
        for symbol in args:
            selected_coins = [coin for coin in user.coins if coin.symbol == symbol]
        for coin in selected_coins:
            response += f"*{coin.symbol}*: {coin.pnl:.5f}%\n"
    
    bot.send_message(message.chat.id, response, parse_mode="Markdown")
    bot.send_message(message.chat.id, random.choice(trading_tips))


@bot.message_handler(commands=['help'])
def help_command(message):
    """Show detailed help message with available commands"""
    user_id = message.from_user.id
    User.update_last_active(telegram_id=user_id)
    
    help_text = (
    "🚀 *SOLANA MEME TRADER BOT* 🚀\n\n"
    "Welcome to your paper trading playground! Here's how to use the bot:\n\n"
    
    "📊 *TRADING COMMANDS* 📊\n"
    "/buy [SYMBOL/ADDRESS] [AMOUNT+CURRENCY] - Buy tokens\n"
    "  Examples: `/buy BONK 10USDC` or `/buy BONK 0.5SOL`\n\n"
    
    "/sell [SYMBOL/ADDRESS] [PERCENTAGE] - Sell your holdings\n"
    "  Example: `/sell BONK 50` (sells 50% of your BONK)\n\n"
    
    "/list - View all your trackable tokens\n\n"
    
    "/track [ADDRESS] - Add a new token to your watchlist\n"
    "  Example: `/track 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU`\n\n"
    
    "💰 *WALLET COMMANDS* 💰\n"
    "/airdrop [AMOUNT] - Get free demo USDC\n"
    "  Example: `/airdrop 50`\n\n"
    
    "/lock [AMOUNT] - Convert SOL to stable USDC\n"
    "  Example: `/lock 1.5`\n\n"
    
    "/unlock [AMOUNT] - Convert USDC back to SOL\n"
    "  Example: `/unlock 25`\n\n"
    
    "📈 *PORTFOLIO COMMANDS* 📈\n"
    "/balance - View your wallet balances\n\n"
    
    "/portfolio - See your complete holdings\n\n"
    
    "/pnl - Check your profit/loss metrics\n"
    "  Options: `/pnl all` or `/pnl [SYMBOL]`\n\n"
    
    "💡 *PRO TIPS* 💡\n"
    "• Start with small trades to learn the platform\n"
    "• Track your favorite tokens with `/track`\n"
    "• Lock profits in USDC during volatile periods\n"
    "• Compare strategies by tracking your PnL\n\n"
    
    "🤔 Need more help? Join our community: https://t.me/solanasimtraders"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

# Handle all other messages
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    """Echo all other messages and suggest using /help"""
    bot.send_message(
        message.chat.id, 
        "I don't understand that command. Try /help to see available commands."
    )

# Import for timedelta
from datetime import timedelta

# Main function to start the bot
def main():
    """Main function to start the bot"""
    logger.info("Starting Solana Meme Trader Bot...")
    # Start the bot
    bot.polling(none_stop=True)

if __name__ == "__main__":
    main()