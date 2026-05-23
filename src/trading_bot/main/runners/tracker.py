import asyncio
import logging
from typing import final

from trading_bot.core.application.trading.dto.event import EventDTO
from trading_bot.core.application.trading.interfaces.exchange import ExchangeRegistryProtocol
from trading_bot.core.application.trading.use_cases.dispatcher import EventDispatcherUseCase

logger = logging.getLogger(__name__)


@final
class TrackerRunner:
    def __init__(self, exchange_gateway: ExchangeRegistryProtocol, event_dispatcher_use_case: EventDispatcherUseCase):
        self._exchange_gateway = exchange_gateway
        self._event_dispatcher_use_case = event_dispatcher_use_case
        self._is_running = False

    async def run(self):
        self._is_running = True
        logger.info("🔄 PositionTracker: Starting WebSocket listener...")
        while self._is_running:
            try:
                await self._exchange_gateway.listen_user_stream(self._on_ws_update)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ PositionTracker WS error: {e}")
                await asyncio.sleep(5)

    def stop(self):
        self._is_running = False

    async def _on_ws_update(self, event: EventDTO):
        await self._event_dispatcher_use_case.execute(event)
