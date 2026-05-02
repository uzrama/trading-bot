from typing import Protocol

from trading_bot.core.application.trading.dto.event import EventDTO


class EventHandlerProtocol(Protocol):
    async def handle(self, event: EventDTO) -> None: ...
