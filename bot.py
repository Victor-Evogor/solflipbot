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
        f"🚀 Welcome to Solana Meme Trader, {first_name}! 🚀\n\n"
        "This is your playground to practice meme coin trading on Solana - no real money, no real risks!\n\n"
        "🔹 You start with 5 SOL and 100 USDC (demo tokens)\n"
        "🔹 Buy/sell meme coins and track your performance\n"
        "🔹 Practice your trading without losing real SOL\n\n"
        "Commands:\n"
        "/buy - Buy a specific meme coin using your demo SOL\n"
        "/sell - Sell a percentage of a meme coin you hold\n"
        "/list - See available meme coins for trading\n"
        "/airdrop - Claim a free usdc airdrop (once every 24h)\n"
        "/lock - Convert SOL to usdc for stability\n"
        "/unlock - Convert usdc back to SOL for trading\n"
        "/portfolio - View your current holdings\n"
        "/balance - Check your wallet balance\n"
        "/pnl - See your profit/loss statistics\n"
        "/transactions - View your recent transactions\n\n"
        "Join our telegram group for updates and support: https://t.me/solanasimtraders\n\n"
        
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
    """Buy a meme coin using SOL"""
    user_id = message.from_user.id
    User.update_last_active(telegram_id=user_id)
    
    args = message.text.split()
    if len(args) != 3:
        bot.send_message(
            message.chat.id, 
            "Please use the format: `/buy [Wallet Address] [AMOUNT in SOL or usdc]`\nExample: `/buy 38AzpaUxVEGhFjXxJx86xsb5xxWW1c1DKvqHhPXBpump 0.5SOL\n\nUse the either SOL or usdc as buying currency`",
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
                "Please use a valid wallet address or tracked token(Use the symbol of the token)"
            )
            return 
        
    amount_str: str = args[2]
    if amount_str.lower().endswith("sol") and len(amount_str) > 3:
        try:
            amount = float(amount_str.lower().replace("sol", ""))
        except ValueError:
            bot.send_message(
                message.chat.id,
                "Please enter in a numerical value for the amount of tokens"
            )
            return 
        usdc_amount = convert_sol_to_usdc(amount)
        
    elif amount_str.lower().endswith("usdc") and len(amount_str) > 4:
        try:
            amount = float(amount_str.lower().replace("usdc", ""))
        except ValueError:
            bot.send_message(
                message.chat.id,
                "Please enter in a numerical value for the amount of tokens"
            )
            return 
        usdc_amount = amount
    else:
        bot.send_message(
            message.chat.id,
            "Please specify the amount in either `SOL` or `usdc`.\nExample: `/buy 38AzpaUx... 0.5SOL`",
            parse_mode="Markdown"
        )
        return
    outcome = Trading.buy_coin(telegram_id=user_id, address=address, usdc_amount=usdc_amount)
    if outcome[0]:
        bot.send_message(
            message.chat.id,
            outcome[0]
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
            f"Your balances:\n"
            f"SOL: {user.sol_balance:.4f}\n"
            f"usdc: {user.usdc_balance:.2f}"
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
        response = f"Your current PnL is {total_pnl:.2f}%"
    elif args[0].lower() == "all":
        response = f"*Total PNL*: {total_pnl:.2f}%\n\n"
        response += "*Other PnL*: \n"
        for coin in user.coins:
            response += f"*{coin.symbol}*: {coin.pnl:.2f}%\n"
        
    else:
        response = f"*Total PNL*: {total_pnl:.2f}%\n\n"
        response += "*Other PnL*: \n"
        for symbol in args:
            selected_coins = [coin for coin in user.coins if coin.symbol == symbol]
        for coin in selected_coins:
            response += f"*{coin.symbol}*: {coin.pnl:.2f}%\n"
    
    bot.send_message(message.chat.id, response, parse_mode="Markdown")


@bot.message_handler(commands=['help'])
def help_command(message):
    """Show help message with available commands"""
    user_id = message.from_user.id
    User.update_last_active(telegram_id=user_id)
    
    help_text = (
        "🤖 *Solana Meme Trader Commands* 🤖\n\n"
        "*Trading Commands:*\n"
        "/buy [SYMBOL] [SOL_AMOUNT] - Buy a meme coin\n"
        "/sell [SYMBOL] [PERCENTAGE] - Sell a percentage of your holdings\n"
        "/list - See available meme coins\n\n"
        
        "*Wallet Commands:*\n"
        "/airdrop - Claim free usdc (once every 24h)\n"
        "/lock [SOL_AMOUNT] - Convert SOL to usdc\n"
        "/unlock [usdc_AMOUNT] - Convert usdc to SOL\n\n"
        
        "*Info Commands:*\n"
        "/portfolio - View your coin holdings\n"
        "/balance - Check wallet balances\n"
        "/pnl - See profit/loss statistics\n\n"
        
        "*Other Commands:*\n"
        "/start - Restart the bot\n"
        "/help - Show this help message\n\n"
        
        "📈 Good luck with your paper trading! 📈"
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