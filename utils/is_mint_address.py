import requests

def is_mint_address(address: str) -> bool:
    if not (address.isalnum()  and len(address) == 44):
        return False
    
    # check with dexscreenr api
    response = requests.get(
    f"https://api.dexscreener.com/token-pairs/v1/solana/{address}",
    headers={"Accept":"*/*"},
    )

    
    if not response.status_code == 200:
        return False
     
    data = response.json()
     
    if len(data) == 0:
        return False
    
    if data[0]["baseToken"]["address"] != address:
        return False
    return True