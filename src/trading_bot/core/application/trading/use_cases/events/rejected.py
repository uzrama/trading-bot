import logging
from collections.abc import Callable
from typing import final

from trading_bot.core.application.database.interfaces.uow import UnitOfWorkProtocol
from trading_bot.core.application.trading.dto.event import EventDTO
from trading_bot.core.application.trading.interfaces.exchange import ExchangeRegistryProtocol

logger = logging.getLogger(__name__)


@final
class RejectedUseCase:
    def __init__(self, exchange_composite: ExchangeRegistryProtocol, uow_factory: Callable[[], UnitOfWorkProtocol]):
        self._exchange_composite = exchange_composite
        self._uow_factory = uow_factory

    async def handle(self, event: EventDTO) -> None:
        if not event.order:
            return

        order = event.order
        account_name = event.account_name

        try:
            exchange = self._exchange_composite.get_exchange(account_name)
            reason = f" Причина: {order.reject_reason}" if order.reject_reason else ""
            logger.warning(f"🚨 [{account_name}] [{order.symbol}] Ордер отклонен биржей (ID: {order.id}).{reason}")

            await exchange.cancel_all_orders(order.symbol)
            logger.info(f"🗑️ [{account_name}] [{order.symbol}] Отменены все активные ордера из-за ошибки")

            uow = self._uow_factory()
            async with uow:
                await uow.orders.delete_by_symbol_and_account(symbol=order.symbol, account_name=account_name)
                await uow.commit()

            logger.info(f"✅ [{account_name}] [{order.symbol}] База данных очищена от ордеров")
        except Exception as e:
            logger.error(f"❌ [{account_name}] [{order.symbol}] Ошибка при очистке ордеров: {e}")
