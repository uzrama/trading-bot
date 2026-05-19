import logging
import re
from typing import override

from trading_bot.core.application.signal.dto.signal import SignalDTO
from trading_bot.core.domain.value_objects.take_profit import TakeProfit
from trading_bot.core.domain.value_objects.trading import TradeSide

from .base import BaseSignalParser

logger = logging.getLogger(__name__)


class VoyagerParser(BaseSignalParser):
    @override
    def parse(self, source_id: int, message_id: int, text: str) -> SignalDTO | None:
        try:
            # Helper function to clean numbers
            def clean_number(val_str: str) -> float:
                return float(re.sub(r"[,\`\$\s]", "", val_str))

            # 1. Symbol & Side
            # Search for "• INX LONG •" or "• INX SHORT •"
            symbol_match = re.search(r"•\s*([A-Z0-9]+)\s+(LONG|SHORT)\s*•", text, re.IGNORECASE)
            if not symbol_match:
                return None

            raw_symbol = symbol_match.group(1).upper()
            side_str = symbol_match.group(2).upper()
            symbol = f"{raw_symbol}USDT"
            side = TradeSide.SHORT if side_str == "SHORT" else TradeSide.LONG
            # 2. Leverage
            # Search for "Leverage: **10x**"
            leverage_match = re.search(r"Leverage:\s*\**(\d+)x\**", text, re.IGNORECASE)
            leverage = int(leverage_match.group(1)) if leverage_match else None
            # 3. Entry price
            # Search for "Limit @ `$0.009753`" or "CONDITIONAL ENTRY" block
            entry_match = re.search(r"(?:Limit\s*@|ENTRY\**)\s*\n*[`\$]*([0-9.,]+)[`]*", text, re.IGNORECASE)
            entry_price = clean_number(entry_match.group(1)) if entry_match else None
            # 4. Take Profits
            # Search for "TP1: `$0.009832`"
            tp_matches = re.findall(r"TP(\d+):\s*[`\$]*([0-9.,]+)[`]*", text, re.IGNORECASE)
            take_profits = []
            for match in tp_matches:
                level = int(match[0])
                price = clean_number(match[1])
                take_profits.append(TakeProfit(price=price, level=level))
            # 5. Stop Loss
            # Search for "SL: `$0.009384`"
            sl_match = re.search(r"(?:Stop-Loss|SL):\s*[`\$]*([0-9.,]+)[`]*", text, re.IGNORECASE)
            stop_loss = clean_number(sl_match.group(1)) if sl_match else None
            # 6. Status (Active / Closed / Voided)
            is_active = True
            is_awaitable = False

            # Check cancellations and closures (signal voided if unfilled)
            if re.search(r"TRADE\s*CANCELLED|CLOSED|CANCEL|voided", text, re.IGNORECASE):
                is_active = False
            # Check if signal is conditional
            # Strictly search for "CONDITIONAL ENTRY" phrase (ignoring possible asterisks)
            if re.search(r"CONDITIONAL\s+ENTRY", text, re.IGNORECASE):
                is_awaitable = True
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
                is_awaitable=is_awaitable,
                source_name="voyager",
            )
        except Exception as e:
            # logger.error(f"Error parsing Voyager signal: {e}")
            return None
