from utils.get_price_and_symbol import get_price_and_symbol

def convert_sol_to_usdc(sol: float) -> float:
    return get_price_and_symbol("So11111111111111111111111111111111111111112")[0] * sol

def convert_usdc_to_sol(usdc: float) -> float:
    return usdc / get_price_and_symbol("So11111111111111111111111111111111111111112")[0]