from dataclasses import dataclass
from typing import Literal, List


@dataclass
class Transaction:
    type: Literal["buy", "sell"]
    priceUsd: float
    amount: float

@dataclass
class Coin:
    symbol: str
    address: str
    txns: List[Transaction]
        
        
