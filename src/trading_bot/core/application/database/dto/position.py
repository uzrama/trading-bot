import msgspec

from trading_bot.core.domain.entities.position import Position
from trading_bot.core.domain.value_objects.take_profit import TakeProfit
from trading_bot.core.domain.value_objects.trading import StopLossState, TradeSide


class PositionDTO(msgspec.Struct, frozen=True, kw_only=True):
    account_name: str
    symbol: str
    side: TradeSide
    entry_price: float
    size: float
    sl_state: StopLossState
    current_sl_order_id: str | None
    highest_tp_hit: int
    is_closed: bool
    is_sl_updated: bool = False

    # Method for Entity -> DTO mapping
    @classmethod
    def from_entity(cls, entity: Position) -> PositionDTO:
        return cls(
            account_name=entity.account_name,
            symbol=entity.symbol,
            side=entity.side,
            entry_price=entity.entry_price,
            size=entity.size,
            sl_state=entity.sl_state,
            current_sl_order_id=entity.current_sl_order_id,
            highest_tp_hit=entity.highest_tp_hit,
            is_closed=entity.is_closed,
            is_sl_updated=entity.is_sl_updated,
        )

    def to_entity(self, take_profits: list[TakeProfit] | None = None) -> Position:
        return Position(
            symbol=self.symbol,
            account_name=self.account_name,
            side=self.side,
            entry_price=self.entry_price,
            size=self.size,
            sl_state=self.sl_state,
            current_sl_order_id=self.current_sl_order_id,
            highest_tp_hit=self.highest_tp_hit,
            is_closed=self.is_closed,
            take_profits=take_profits or [],
            is_sl_updated=self.is_sl_updated,
        )
