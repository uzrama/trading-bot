import math
from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

from trading_bot.core.domain.value_objects.symbol import SymbolInfo
from trading_bot.core.domain.value_objects.take_profit import TakeProfit
from trading_bot.core.domain.value_objects.trading import TradeSide


@dataclass
class TradeSetup:
    symbol: str
    side: TradeSide
    entry_price: float | None
    stop_loss: float | None
    take_profits: list[TakeProfit]

    def is_valid_for_entry(self, market_price: float) -> bool:
        if not self.stop_loss or not self.take_profits:
            return True
        first_tp = self.take_profits[0].price
        if self.side == TradeSide.LONG:
            return self.stop_loss < market_price < first_tp
        elif self.side == TradeSide.SHORT:
            return first_tp < market_price < self.stop_loss

        return True

    def calculate_qty(self, balance: float, market_price: float, position_size_pct: float, leverage: int, symbol_info: SymbolInfo) -> float:
        margin_qty = balance * position_size_pct
        raw_qty = (margin_qty * leverage) / market_price

        qty = self._rounded(raw_qty, symbol_info.qty_step)
        return qty if qty >= symbol_info.min_order_qty else 0.0

    def calculate_sl_price(self, market_price: float, default_sl_pct: float, tick_size: float) -> float:
        if self.stop_loss:
            sl_price = self.stop_loss
        else:
            sl_multiplier = default_sl_pct
            if self.side == TradeSide.LONG:
                sl_price = market_price * (1 - sl_multiplier)
            else:
                sl_price = market_price * (1 + sl_multiplier)

        return math.floor(sl_price / tick_size) * tick_size

    def calculate_tp_sizes(self, total_qty: float, qty_step: float, distribution_config: list[float]) -> list[tuple[float, float, int]]:
        remaining_qty = total_qty
        num_tps = len(self.take_profits)
        results = []
        for i, tp in enumerate(self.take_profits):
            if i == num_tps - 1:
                qty = 0.0
            else:
                pct = distribution_config[i] if distribution_config else (1.0 / num_tps)
                raw_qty = total_qty * pct
                qty = self._rounded(raw_qty, qty_step)
                remaining_qty -= qty
            results.append((qty, tp.price, i + 1))
        return results

    def _rounded(self, qty: float, step: float) -> float:
        return float((Decimal(str(qty)) / Decimal(str(step))).quantize(Decimal("1"), rounding=ROUND_DOWN) * Decimal(str(step)))
