from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal

from trading_bot.core.domain.value_objects.take_profit import TakeProfit
from trading_bot.core.domain.value_objects.trading import StopLossState, TradeSide


@dataclass
class Position:
    symbol: str
    account_name: str
    side: TradeSide
    entry_price: float
    size: float

    current_sl_order_id: str | None = None
    take_profits: list[TakeProfit] = field(default_factory=list)

    sl_state: StopLossState = StopLossState.INITIAL
    highest_tp_hit: int = 0

    is_closed: bool = False
    is_sl_updated: bool = False

    def process_take_profit(self, executed_qty: float, tp_level: int) -> StopLossState | None:
        self.size = max(0.0, self.size - executed_qty)

        if self.size <= 0:
            self.is_closed = True
            return None
        self.highest_tp_hit = max(self.highest_tp_hit, tp_level)

        # RULE 1: Reached TP3 (or higher) -> SL moved to TP1
        if self.highest_tp_hit == 3 and self.sl_state in (StopLossState.INITIAL, StopLossState.BREAKEVEN):
            self.sl_state = StopLossState.TRAILED_TP1
            return StopLossState.TRAILED_TP1
        # RULE 2: Reached TP1 (or higher) -> SL moved to Breakeven
        if self.highest_tp_hit == 1 and self.sl_state == StopLossState.INITIAL:
            self.sl_state = StopLossState.BREAKEVEN
            return StopLossState.BREAKEVEN
        return None

    def calculate_sl_price(self, target_state: StopLossState) -> float:
        if target_state == StopLossState.BREAKEVEN:
            # Breakeven is strictly equal to entry price
            return self.entry_price
        elif target_state == StopLossState.TRAILED_TP1:
            # Find TP1 price in our list (level 1)
            tp1_price = next((tp.price for tp in self.take_profits if tp.level == 1), None)
            if not tp1_price:
                # Fallback if TP1 is somehow not found
                return self.calculate_sl_price(StopLossState.BREAKEVEN)
            # Move SL strictly to TP1 price level
            return tp1_price
        # Return Entry by default (fallback option)
        return self.entry_price

    def get_rounded_size(self, qty_step: float) -> float:
        if self.size <= 0:
            return 0.0
        return float((Decimal(str(self.size)) / Decimal(str(qty_step))).quantize(Decimal("1"), rounding=ROUND_DOWN) * Decimal(str(qty_step)))
