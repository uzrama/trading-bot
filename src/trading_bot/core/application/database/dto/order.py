from typing import Literal

import msgspec

from trading_bot.core.application.trading.dto.order import PlacedOrderDTO
from trading_bot.core.domain.value_objects.trading import OrderStatus, OrderType, TradeSide


class OrderDTO(msgspec.Struct, frozen=True, kw_only=True):
    id: str | None
    symbol: str | None
    side: TradeSide | None
    status: OrderStatus | None
    order_type: OrderType
    qty: float | None
    price: float | None
    trigger_price: float | None = None
    trigger_direcation: Literal[0, 1, 2] | None = None
    trigger_by: Literal["LastPrice", "IndexPrice", "MarkPrice"] = "LastPrice"
    reduce_only: bool = False
    close_on_trigger: bool = False
    level: int | None = None
    order_link_id: str | None = None

    account_name: str
    message_id: str | None

    @classmethod
    def from_placed_order(cls, placed: PlacedOrderDTO, account_name: str, message_id: str | None) -> OrderDTO:
        return cls(
            id=placed.id,
            symbol=placed.symbol,
            side=placed.side,
            status=placed.status,
            order_type=placed.order_type,
            qty=placed.qty,
            price=placed.price,
            trigger_price=placed.trigger_price,
            level=placed.level,
            account_name=account_name,
            message_id=message_id,
            order_link_id=placed.order_link_id,
        )
