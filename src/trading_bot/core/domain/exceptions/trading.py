from typing import final

from trading_bot.core.domain.exceptions.base import DomainException


@final
class SymbolNotFoundException(DomainException):
    """Raised when the requested symbol is not listed on the exchange."""

    def __init__(self, symbol: str, exchange_name: str):
        self.symbol = symbol
        self.exchange_name = exchange_name
        super().__init__(f"Symbol {symbol} is not found on exchange {exchange_name}.")
