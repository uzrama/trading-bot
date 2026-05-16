import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import final, override

from trading_bot.core.application.trading.dto import EventDTO
from trading_bot.core.application.trading.interfaces.exchange import ExchangeGatewayProtocol, ExchangeRegistryProtocol

logger = logging.getLogger(__name__)


@final
class CompositeExchangeGateway(ExchangeRegistryProtocol):
    def __init__(self, exchanges: dict[str, ExchangeGatewayProtocol]):
        self._exchanges = exchanges

    @override
    def get_exchange(self, name: str) -> ExchangeGatewayProtocol:
        adapter = self._exchanges.get(name)
        if not adapter:
            if not self._exchanges:
                raise RuntimeError("No exchange adapters configured")
            return next(iter(self._exchanges.values()))
        return adapter

    @override
    def get_all_exchanges(self) -> list[ExchangeGatewayProtocol]:
        return list(self._exchanges.values())

    @property
    def name(self) -> str:
        return "composite"

    async def close(self):
        for adapter in self._exchanges.values():
            await adapter.close()

    async def listen_user_stream(self, on_update_callback: Callable[[EventDTO], Awaitable[None]]) -> None:
        if not self._exchanges:
            logger.error("❌ No exchanges configured for WebSocket tracking")
            raise RuntimeError("No exchanges available for WebSocket tracking")

        async def safe_listen(name: str, adapter: ExchangeGatewayProtocol) -> None:
            """Wrapper to handle individual exchange stream errors gracefully."""
            try:
                await adapter.listen_user_stream(on_update_callback)
            except Exception as e:
                logger.error(f"❌ WebSocket stream failed for {name}: {e}")

        tasks = [safe_listen(name, adapter) for name, adapter in self._exchanges.items()]
        await asyncio.gather(*tasks, return_exceptions=True)
