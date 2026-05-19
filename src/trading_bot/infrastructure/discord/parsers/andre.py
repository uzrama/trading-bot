import logging
import re
from typing import override

from trading_bot.core.application.signal.dto.signal import SignalDTO
from trading_bot.core.domain.value_objects.take_profit import TakeProfit
from trading_bot.core.domain.value_objects.trading import TradeSide

from .base import BaseSignalParser

logger = logging.getLogger(__name__)


class AndreParser(BaseSignalParser):
    @override
    def parse(self, source_id: int, message_id: int, text: str) -> SignalDTO | None:
        try:
            # Helper function to clean numbers
            def clean_number(val_str: str) -> float:
                # Remove commas, backticks, dollar signs, and spaces
                return float(re.sub(r"[,\`\$\s]", "", val_str))

            # 1. Symbol & Side
            symbol_match = re.search(r"\**([A-Z0-9]+)\**\s+(LONG|SHORT)\s+Signal", text, re.IGNORECASE)
            if not symbol_match:
                return None
            raw_symbol = symbol_match.group(1).upper()
            side_str = symbol_match.group(2).upper()
            symbol = f"{raw_symbol}USDT"
            side = TradeSide.SHORT if side_str == "SHORT" else TradeSide.LONG

            # 2. Leverage
            leverage_match = re.search(r"Leverage:\s*(?:[a-zA-Z]+\s*)?(\d+)x", text, re.IGNORECASE)
            leverage = int(leverage_match.group(1)) if leverage_match else None

            # 3. Entry price
            # Added \** before (?:Entry...) and after colon
            entry_match = re.search(r"\**(?:Entry|Enter on Trigger):\**\s*[`\$]*([0-9.,]+)[`]*", text, re.IGNORECASE)
            entry_price = clean_number(entry_match.group(1)) if entry_match else None

            # 4. Take Profits
            tp_matches = re.findall(r"\**TP(\d+):\**\s*[`\$]*([0-9.,]+)[`]*", text, re.IGNORECASE)
            take_profits = []
            for match in tp_matches:
                level = int(match[0])
                price = clean_number(match[1])
                take_profits.append(TakeProfit(price=price, level=level))

            # 5. Stop Loss
            sl_match = re.search(r"\**(?:Stop-Loss|Stop Loss|SL):\**\s*[`\$]*([0-9.,]+)[`]*", text, re.IGNORECASE)
            stop_loss = clean_number(sl_match.group(1)) if sl_match else None
            # 6. Status (Active / Closed)
            is_active = True
            is_awaitable = False
            # Find cancellation or closure status
            if re.search(r"TRADE\s*CANCELLED|CLOSED|CANCEL", text, re.IGNORECASE):
                is_active = False
            if re.search(r"AWAITING ENTRY|Enter on Trigger", text, re.IGNORECASE) and not re.search(r"✅ Triggered", text, re.IGNORECASE):
                is_awaitable = True
            # Validation
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
                leverage=leverage,  # Will be None, which is fine
                active=is_active,
                is_awaitable=is_awaitable,
                source_name="andre",
            )
        except Exception as e:
            logger.error(f"Error parsing Andre signal: {e}")
            return None
