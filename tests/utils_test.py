from utils.get_price_of_coin_in_usdt import get_price_and_symbol
from utils.get_mint_address_from_symbol import get_mint_address_from_symbol


class TestUtils:
    def utils():
        assert type(get_price_and_symbol("38AzpaUxVEGhFjXxJx86xsb5xxWW1c1DKvqHhPXBpump")) == float