import logging
from collections.abc import Callable
from typing import final

from trading_bot.core.application.database.dto.order import OrderDTO
from trading_bot.core.application.database.interfaces.uow import UnitOfWorkProtocol
from trading_bot.core.application.trading.dto.event import EventDTO

logger = logging.getLogger(__name__)


@final
class ConfirmedUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWorkProtocol]):
        self._uow_factory = uow_factory

    async def handle(self, event: EventDTO) -> None:
        if not event.order or not event.order.order_link_id:
            return
        order = event.order

        order_link_id = order.order_link_id
        account_name = event.account_name
        account_name = event.account_name
        uow = self._uow_factory()
        async with uow:
            # 1. Find pre-save by order_link_id
            db_order = await uow.orders.get_by_link_id(order_link_id)
            if not db_order:
                return
            # 2. Update record: delete old by link_id and insert new with exchange ID
            await uow.orders.delete_by_link_id(order_link_id)
            # 3. Form final DTO for saving, passing message_id from old record
            final_order_dto = OrderDTO(
                id=order.id,
                symbol=db_order.symbol,
                side=db_order.side,
                status=order.status,
                order_type=db_order.order_type,
                qty=order.qty or db_order.qty,
                price=order.price or db_order.price,
                trigger_price=order.trigger_price or db_order.trigger_price,
                level=db_order.level,
                account_name=account_name,
                message_id=db_order.message_id,
                order_link_id=db_order.order_link_id,
            )
            await uow.orders.upsert(final_order_dto)
            await uow.commit()
        logger.info(f"✅ [{account_name}] [{order.symbol}] Ордер подтвержден биржей (Тип: {db_order.order_type.value}, ID: {order.id})")
