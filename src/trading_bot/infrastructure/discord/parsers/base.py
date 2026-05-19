from typing import Protocol

from trading_bot.core.application.signal.dto.signal import SignalDTO


class BaseSignalParser(Protocol):
    def parse(self, source_id: int, message_id: int, text: str) -> SignalDTO | None: ...
