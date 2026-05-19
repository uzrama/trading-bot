import re
from typing import override

from trading_bot.core.application.signal.dto.signal import SignalDTO
from trading_bot.core.domain.value_objects.take_profit import TakeProfit
from trading_bot.core.domain.value_objects.trading import TradeSide

from .base import BaseSignalParser


class HaseebParser(BaseSignalParser):
    @override
    def parse(self, source_id: int, message_id: int, text: str) -> SignalDTO | None:
        try:
            # 1. Symbol & Side
            symbol_match = re.search(r"\**(LONG|SHORT)\s+SIGNAL\s+-\s+([A-Z0-9]+)/USDT\**", text, re.IGNORECASE)
            if not symbol_match:
                return None
            side_str = symbol_match.group(1).upper()
            raw_symbol = symbol_match.group(2).upper()
            symbol = f"{raw_symbol}USDT"
            side = TradeSide.SHORT if side_str == "SHORT" else TradeSide.LONG

            # 2. Leverage (Added \** to ignore asterisks)
            leverage_match = re.search(r"\**Leverage:\**\s*(?:[a-zA-Z]+\s*)?\**(\d+)x\**", text, re.IGNORECASE)
            leverage = int(leverage_match.group(1)) if leverage_match else None

            # 3. Entry price
            entry_match = re.search(r"\**(?:Entry|Enter on Trigger):\**\s*[`\$]*([0-9.,]+)[`]*", text, re.IGNORECASE)
            entry_price = float(entry_match.group(1)) if entry_match else None

            # 4. Take Profits
            tp_matches = re.findall(r"\**TP(\d+):\**\s*[`\$]*([0-9.,]+)[`]*", text, re.IGNORECASE)
            take_profits = []
            for match in tp_matches:
                level = int(match[0])
                price = float(match[1])
                take_profits.append(TakeProfit(price=price, level=level))

            # 5. Stop Loss
            sl_match = re.search(r"\**(?:Stop-Loss|Stop Loss|SL):\**\s*[`\$]*([0-9.,]+)[`]*", text, re.IGNORECASE)
            stop_loss = float(sl_match.group(1)) if sl_match else None
            # 6. Status (Active / Cancelled)
            is_active = True
            is_awaitable = False

            if re.search(r"TRADE\s*CANCELLED|CLOSED|CANCEL|FINAL PRICE", text, re.IGNORECASE):
                is_active = False

            # 7. Awaitable
            if re.search(r"AWAITING ENTRY|Enter on Trigger", text, re.IGNORECASE):
                is_awaitable = True
            # Validation: return None if key fields (entry or TPs) are missing
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
                is_awaitable=is_awaitable,
                source_name="haseeb",
            )
        except Exception as e:
            # logger.error(f"Error parsing Haseeb signal: {e}")
            return None
