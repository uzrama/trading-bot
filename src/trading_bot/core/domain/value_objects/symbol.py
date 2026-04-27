from typing import Any

from msgspec import Struct


class SymbolInfo(Struct, frozen=True, kw_only=True):
    symbol: str
    status: str
    base_coin: str
    quote_coin: str

    tick_size: float
    min_price: float

    qty_step: float
    min_order_qty: float
    max_order_qty: float

    @classmethod
    def from_bybit(cls, data: dict[str, Any]) -> SymbolInfo:
        price_filter = data.get("priceFilter", {})
        lot_filter = data.get("lotSizeFilter", {})

        return cls(
            symbol=data["symbol"],
            status=data["status"],
            base_coin=data["baseCoin"],
            quote_coin=data["quoteCoin"],
            tick_size=float(price_filter.get("tickSize", 0)),
            min_price=float(price_filter.get("minPrice", 0)),
            qty_step=float(lot_filter.get("qtyStep", 0)),
            min_order_qty=float(lot_filter.get("minOrderQty", 0)),
            max_order_qty=float(lot_filter.get("maxOrderQty", 0)),
        )
