import logging
from collections.abc import Callable
from typing import final

from trading_bot.core.application.database.dto.position import PositionDTO
from trading_bot.core.application.database.interfaces.uow import UnitOfWorkProtocol
from trading_bot.core.application.trading.dto.event import EventDTO
from trading_bot.core.application.trading.interfaces.exchange import ExchangeRegistryProtocol

logger = logging.getLogger(__name__)


@final
class StopLossUseCase:
    def __init__(self, exchange_composite: ExchangeRegistryProtocol, uow_factory: Callable[[], UnitOfWorkProtocol]):
        self._exchange_composite = exchange_composite
        self._uow_factory = uow_factory

    async def handle(self, event: EventDTO) -> None:
        if not event.order:
            return
        logger.info(f"🛑 [{event.account_name}] [{event.order.symbol}] Сработал Стоп-Лосс (ID: {event.order.id})")
        exchange = self._exchange_composite.get_exchange(event.account_name)
        uow = self._uow_factory()
        # 1. Infrastructure: Cancel all remaining Take Profits on the exchange
        try:
            await exchange.cancel_all_orders(event.order.symbol)
            logger.info(f"🗑️ [{event.account_name}] [{event.order.symbol}] Отменены все оставшиеся Тейк-Профиты")
        except Exception as e:
            logger.error(f"❌ [{event.account_name}] [{event.order.symbol}] Ошибка при отмене ордеров: {e}")
        # 2. Update DB (close position)
        async with uow:
            position_dto = await uow.positions.get_active_by_symbol(account_name=event.account_name, symbol=event.order.symbol)
            if position_dto:
                position_entity = position_dto.to_entity()

                position_entity.size = 0.0
                position_entity.is_closed = True
                position_entity.current_sl_order_id = None

                updated_dto = PositionDTO.from_entity(position_entity)
                await uow.positions.upsert(updated_dto)
                logger.info(f"✅ [{event.account_name}] [{event.order.symbol}] Позиция закрыта в БД")
            else:
                logger.warning(f"⚠️ [{event.account_name}] [{event.order.symbol}] Активная позиция не найдена в БД при срабатывании СЛ")
            # --- DB CLEANUP ---
            # Delete triggered SL and all pending TPs for this symbol at once!
            await uow.orders.delete_by_symbol_and_account(account_name=event.account_name, symbol=event.order.symbol)
            logger.info(f"🗑️ [{event.account_name}] [{event.order.symbol}] Все ордера удалены из БД")
            await uow.commit()
