from models import User


def get_mint_address_from_symbol(telegram_id, mint_symbol):
    user, user_data = User.get_by_telegram_id(telegram_id)
    if not user:
        raise Exception(f"No user found with telegram id {telegram_id}")
    
    tracked_tokens = user_data["tracked_tokens"]
    address = [token["symbol"] for token in tracked_tokens if token["symbol"] == mint_symbol][0]
    return address