import logging
from collections.abc import Callable
from typing import final

from trading_bot.core.application.database.interfaces.uow import UnitOfWorkProtocol
from trading_bot.core.application.trading.dto.event import EventDTO
from trading_bot.core.application.trading.use_cases.events import ConfirmedUseCase, FilledUseCase, RejectedUseCase, StopLossUseCase, TakeProfitUseCase
from trading_bot.core.domain.value_objects.event import EventType
from trading_bot.core.domain.value_objects.trading import OrderStatus, OrderType

logger = logging.getLogger(__name__)


@final
class EventDispatcherUseCase:
    def __init__(
        self,
        rejected_handler: RejectedUseCase,
        take_profit_handler: TakeProfitUseCase,
        filled_handler: FilledUseCase,
        stop_loss_handler: StopLossUseCase,
        confirmed_handler: ConfirmedUseCase,
        uow_factory: Callable[[], UnitOfWorkProtocol],
    ):
        self._rejected_handler = rejected_handler
        self._take_profit_handler = take_profit_handler
        self._filled_handler = filled_handler
        self._stop_loss_handler = stop_loss_handler
        self._confirmed_handler = confirmed_handler
        self._uow_factory = uow_factory

    async def execute(self, event: EventDTO) -> None:
        # Process only order events (for now)
        if event.event_type != EventType.ORDER or not event.order:
            return
        # 1. If order just ACCEPTED by exchange (Confirmed)
        if event.order.status in (OrderStatus.NEW, OrderStatus.UNTRIGGERED):
            await self._confirmed_handler.handle(event)
            return
        # 2. If order rejected by exchange
        if event.order.status == OrderStatus.REJECTED:
            await self._rejected_handler.handle(event)
            return
        # 3. If order executed (Filled)
        if event.order.status == OrderStatus.FILLED:
            uow = self._uow_factory()
            async with uow:
                db_order = await uow.orders.get_by_id(event.order.id)
                if event.order.order_link_id:
                    db_order = await uow.orders.get_by_link_id(event.order.order_link_id)

                if not db_order:
                    logger.warning(f"⚠️ [{event.account_name}] [{event.order.symbol}] Исполнен ордер, но его нет в БД (ID: {event.order.id}, link: {event.order.order_link_id})")
                    return

                order_type = db_order.order_type
            # Routing based on executed order type
            if order_type == OrderType.TAKE_PROFIT:
                await self._take_profit_handler.handle(event)
            elif order_type == OrderType.STOP_LOSS:
                await self._stop_loss_handler.handle(event)
            else:
                logger.info(f"🚀 [{event.account_name}] [{event.order.symbol}] Исполнен ордер типа {order_type.value} (Перенаправлен в обработчик позиций)")
                await self._filled_handler.handle(event)
