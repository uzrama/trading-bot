import msgspec

from trading_bot.core.domain.value_objects.take_profit import TakeProfit
from trading_bot.core.domain.value_objects.trading import TradeSide


class SignalDTO(msgspec.Struct, frozen=True, kw_only=True):
    source_id: int
    message_id: int
    source_name: str
    symbol: str
    leverage: int | None
    side: TradeSide
    entry_price: float | None = None
    triggered: bool = False
    is_awaitable: bool = False
    active: bool = False
    stop_loss: float | None = None
    take_profits: list[TakeProfit] = []
