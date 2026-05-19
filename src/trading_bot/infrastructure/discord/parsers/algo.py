import re
from typing import override

from trading_bot.core.application.signal.dto.signal import SignalDTO
from trading_bot.core.domain.value_objects.take_profit import TakeProfit
from trading_bot.core.domain.value_objects.trading import TradeSide

from .base import BaseSignalParser


class AlgoParser(BaseSignalParser):
    @override
    def parse(self, source_id: int, message_id: int, text: str) -> SignalDTO | None:
        try:
            # Symbol
            symbol_match = re.search(r"•\s+([A-Z]+)\s+(SHORT|LONG)\s+•", text)
            if not symbol_match:
                return None
            raw_symbol = symbol_match.group(1)
            # Formatted for Bybit Futures (CCXT) -> 'SYMBOL/USDT:USDT'
            symbol = f"{raw_symbol}USDT"

            # Side
            side_str = symbol_match.group(2)  # 'SHORT'
            side = TradeSide.SHORT if side_str == "SHORT" else TradeSide.LONG

            # Leverage
            leverage_match = re.search(r"Leverage:\s*\*\*(\d+)x\*\*", text)
            leverage = int(leverage_match.group(1)) if leverage_match else None

            # Entry price
            entry_match = re.search(r"ENTRY\**\s*\n\s*`\$([0-9.]+)`", text)
            entry_price = float(entry_match.group(1)) if entry_match else None

            # TPs
            tp_matches = re.findall(r"TP(\d+):\s*`+\$([0-9.]+)`+", text)
            take_profits = []

            for match in tp_matches:
                level = int(match[0])
                price = float(match[1])
                tp = TakeProfit(price=price, level=level)
                take_profits.append(tp)

            # SL
            sl_match = re.search(r"SL:\s*`+\$([0-9.]+)`+", text)
            stop_loss = float(sl_match.group(1)) if sl_match else None

            # Status
            is_active = False
            status_match = re.search(r"STATUS\n\*\*(.*?)\*\*", text, re.IGNORECASE)
            if status_match:
                raw_status = status_match.group(1).upper()
                if "ACTIVE" in raw_status:
                    is_active = True

            # Validation: return None if key fields are missing
            if not entry_price or not take_profits:
                return None

            return SignalDTO(
                source_id=source_id,
                message_id=message_id,
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                take_profits=take_profits,
                stop_loss=stop_loss,
                leverage=leverage,
                active=is_active,
                source_name="algo",
            )
        except Exception:
            return None
