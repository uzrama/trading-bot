from dataclasses import dataclass

from trading_bot.core.domain.value_objects.trading import OrderType, TradeSide


@dataclass
class Order:
    symbol: str
    side: TradeSide
    order_type: OrderType
    qty: float
    price: float | None = None
    trigger_price: float | None = None
