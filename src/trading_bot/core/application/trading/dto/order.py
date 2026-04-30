import uuid

import msgspec

from trading_bot.core.domain.value_objects.trading import OrderStatus, OrderType, TradeSide


class PlaceOrderDTO(msgspec.Struct, frozen=True, kw_only=True):
    symbol: str
    side: TradeSide
    order_type: OrderType
    qty: float | None = None
    price: float | None = None
    trigger_price: float | None = None
    trigger_direction: int | None = None
    reduce_only: bool = False
    close_on_trigger: bool = False
    level: int | None = None

    order_link_id: str | None = msgspec.field(default_factory=lambda: str(uuid.uuid4()))


class PlacedOrderDTO(msgspec.Struct, frozen=True, kw_only=True):
    id: str
    symbol: str
    side: TradeSide | None = None
    order_type: OrderType
    status: OrderStatus | None = None
    price: float | None = None
    trigger_price: float | None = None
    trigger_direction: int | None = None
    qty: float | None = None
    level: int | None = None
    reject_reason: str | None = None
    order_link_id: str | None = None
