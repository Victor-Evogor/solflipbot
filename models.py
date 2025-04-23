# models.py
from datetime import datetime
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from typing import List, Literal, Tuple
from collections import deque
from utils.convert_sol import convert_usdc_to_sol

from utils.get_price_and_symbol import get_price_and_symbol

# Load environment variables
load_dotenv()

# MongoDB connection
client = MongoClient(os.getenv('MONGODB_URI'))
db = client.memetrader

# Collections
users_collection = db.users
coins_collection = db.coins
transactions_collection = db.transactions
portfolio_collection = db.portfolio


class Txn:
    type: Literal["BUY", "SELL"]
    priceUsd: float
    amount: float
    
    def __init__(self, type: Literal["BUY", "SELL"], priceUsd: float, amount: float):
        self.type = type
        self.priceUsd = priceUsd
        self.amount = amount
    
    
    def json(self):
        return {
            "type": self.type,
            "priceUsd": self.priceUsd,
            "amount": self.amount
        }
class Coin:
    address: str
    symbol: str
    txns: List[Txn]
    amount: str
    
    def __init__(self, address: str, symbol: str, txns: List[Txn]):
        self.address = address
        self.symbol = symbol
        self.txns = txns
    
    def json(self):
        return {
            "address": self.address,
            "symbol": self.symbol,
            "txns": [txn.json() for txn in self.txns],
            "amount": self.amount
        }
        
    @property
    def price(self) -> float:
        return get_price_and_symbol(self.address)[0]
    
    @property
    def pnl(self) -> float:
        buy_queue = deque()  # queue of (amount, price_per_coin)
        total_pnl = 0.0

        for txn in self.txns:
            if txn.type == "BUY":
                price_per_coin = txn.priceUsd / txn.amount
                buy_queue.append((txn.amount, price_per_coin))
            elif txn.type == "SELL":
                remaining = txn.amount
                sell_price_per_coin = txn.priceUsd / txn.amount

                while remaining > 0 and buy_queue:
                    buy_amount, buy_price_per_coin = buy_queue.popleft()
                    matched = min(remaining, buy_amount)

                    pnl = (sell_price_per_coin - buy_price_per_coin) * matched
                    total_pnl += pnl

                    remaining -= matched
                    leftover = buy_amount - matched
                    if leftover > 0:
                        buy_queue.appendleft((leftover, buy_price_per_coin))

        return total_pnl
    
    @property
    def amount(self) -> float:
        total_amount = 0.0
        for txn in self.txns:
            if txn.type == "BUY":
                total_amount += txn.amount
            elif txn.type == "SELL":
                total_amount -= txn.amount
        return total_amount


class User:
    """User model to store user information"""
    
    def __init__(self, telegram_id, username=None, first_name=None, last_name=None, coins: List[Coin]=[], sol_balance=0.0, usdc_balance=0.0):
        self.telegram_id = telegram_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.join_date = datetime.now()
        self.last_active = datetime.now()
        self.coins = coins
        self.sol_balance = sol_balance
        self.usdc_balance = usdc_balance
        
    def save(self):
        user_data = {
            "telegram_id": self.telegram_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "join_date": self.join_date,
            "last_active": self.last_active,
            "coins": [coin.json() for coin in self.coins],
            "sol_balance": self.sol_balance,
            "usdc_balance": self.usdc_balance,
            "pnl": self.pnl
        }
        
        existing_user = users_collection.find_one({"telegram_id": self.telegram_id})
        if existing_user:
            users_collection.update_one(
                {"telegram_id": self.telegram_id},
                {"$set": user_data}
            )
            return existing_user["_id"]
        else:
            user_id = users_collection.insert_one(user_data).inserted_id
            
            return user_id
    
    @classmethod
    def get_by_telegram_id(cls, telegram_id):
        user_data = users_collection.find_one({"telegram_id": telegram_id})
        if not user_data:
            return None
        
        user = cls(
            telegram_id=user_data["telegram_id"],
            username=user_data.get("username"),
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            coins=[Coin(address=coin["address"], symbol=coin["symbol"], txns=[Txn(type=txn["type"],amount=txn["amount"], priceUsd=txn["priceUsd"]) for txn in coin["txns"]]) for coin in user_data.get("coins")],
            sol_balance=user_data.get("sol_balance"),
            usdc_balance=user_data.get("usdc_balance"),
        )
        user.join_date = user_data.get("join_date")
        user.last_active = user_data.get("last_active")
        return user
    
    @classmethod
    def update_last_active(cls, telegram_id):
        users_collection.update_one(
            {"telegram_id": telegram_id},
            {"$set": {"last_active": datetime.now()}}
        )
        
    @property
    def pnl(self) -> float:
        return sum(coin.pnl for coin in self.coins)




# trading.py - Trading logic for the bot
class Trading:
    """Class to handle all trading operations"""
    
    @staticmethod
    def buy_coin(telegram_id, address, usdc_amount):
        """Buy a meme coin with SOL"""
        user = User.get_by_telegram_id(telegram_id)
        sol_amount = convert_usdc_to_sol(usdc_amount)
        if sol_amount > user.sol_balance:
            return False, "Insufficient balance SOL balance"
        token_price, symbol = get_price_and_symbol(address)
        amount = usdc_amount / token_price
        coin = next((coin for coin in user.coins if coin.address == address), None)
        if coin :
            coin.txns.append(Txn(type="BUY", amount=amount, priceUsd=token_price))
        else:
            user.coins.append(Coin(address=address, symbol=symbol, txns=[Txn(type="BUY", amount=amount, priceUsd=token_price)]))
        user.sol_balance -= sol_amount
        user.save()
        return f"Bought {amount}{symbol} for {usdc_amount}USDC", None
        
    
    @staticmethod
    def sell_coin(telegram_id, address, percentage):
        """Sell a percentage of coin holdings"""
        if percentage <= 0 or percentage > 100:
            return False, "Percentage must be between 1 and 100"
        token_price, _ = get_price_and_symbol(address)
        user= User.get_by_telegram_id(telegram_id)
        coin = next((coin for coin in user.coins if coin.address == address), None)
        if coin:
            selling_price = coin.amount * (percentage / 100) * coin.price
            coin.txns.append(Txn(type="SELL", amount=coin.amount * (percentage / 100), priceUsd=token_price))
            user.sol_balance -= convert_usdc_to_sol(selling_price)
            user.save()
            return True, f"Sold {percentage}% of {coin.symbol} at {token_price:.4f} usdc"
        else:
            raise f"No coin found for address {address}"
    
    @staticmethod
    def lock_sol(telegram_id, sol_amount):
        """Convert SOL to usdc"""
        sol_to_usdc_rate = get_price_and_symbol("So11111111111111111111111111111111111111112")[0]
        user = User.get_by_telegram_id(telegram_id=telegram_id)
        if sol_amount > user.sol_balance:
            return False, "Insufficient SOL balance"
        # Calculate usdc amount (1 SOL = 20 usdc in this example)
        usdc_amount = sol_amount * sol_to_usdc_rate
        user.sol_balance -= sol_amount
        user.usdc_balance += usdc_amount
        user.save()
        
        return True, f"Converted {sol_amount:.4f} SOL to {usdc_amount:.2f} usdc"
    
    @staticmethod
    def unlock_usdc(telegram_id, usdc_amount):
        """Convert usdc back to SOL"""
        sol_to_usdc_rate = get_price_and_symbol("So11111111111111111111111111111111111111112")[0]
        user = User.get_by_telegram_id(telegram_id=telegram_id)
        if usdc_amount > user.usdc_balance:
            return False, "Insufficient usdc balance"
        sol_amount = usdc_amount / sol_to_usdc_rate
        user.usdc_balance -= usdc_amount
        user.sol_balance += sol_amount
        user.save()
        
        return True, f"Converted {usdc_amount:.2f} usdc to {sol_amount:.4f} SOL"
    
    @staticmethod
    def airdrop_usdc(telegram_id, usdc_amount=50.0):
        """Claim free usdc airdrop"""
        user = User.get_by_telegram_id(telegram_id=telegram_id)
        user.usdc_balance += usdc_amount
        user.save()
        
        return True, f"Airdropped {usdc_amount:.2f} usdc to your wallet!"
    
    @staticmethod
    def get_portfolio_value(telegram_id) -> Tuple[float, float]:
        """Calculate total portfolio value in SOL"""
        user = User.get_by_telegram_id(telegram_id=telegram_id)
        value_of_coins = sum([get_price_and_symbol(coin.address)[0] * coin.amount for coin in user.coins])
        value_of_sol = get_price_and_symbol("So11111111111111111111111111111111111111112")[0] * user.sol_balance
        return user.usdc_balance + value_of_coins + value_of_sol, user.pnl
    
    
