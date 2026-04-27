import msgspec


class TakeProfit(msgspec.Struct, frozen=True, kw_only=True):
    price: float
    level: int
