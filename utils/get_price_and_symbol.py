import requests
from typing import Tuple

def get_price_and_symbol(address: str) -> Tuple[float, str]:
    """
    Get the price of a coin in USDT using the Dex Screener API.
    
    Args:
        address (str): The mint address of the coin.
        
    Returns:
        float: The price of the coin in USDT.
    """
    # Check if the address is valid
    if not (address.isalnum() and len(address) == 44 or address == "So11111111111111111111111111111111111111112"):
        return 0.0
    
    # Check with Dex Screener API
    response = requests.get(
        f"https://api.dexscreener.com/token-pairs/v1/solana/{address}",
        headers={"Accept": "*/*"},
    )
    
    if response.status_code != 200:
        raise "Error fetching data from Dex Screener API"
    
    data = response.json()
    
    if not data: 
        return 0.0
    
    
    
    if not data[0]:
        return 0.0
    
    price = data[0]["priceUsd"]
    symbol = data[0]["baseToken"]["symbol"]
    
    return float(price), symbol
    