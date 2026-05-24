import logging
from collections.abc import Callable
from typing import final

from trading_bot.core.application.database.dto import PositionDTO
from trading_bot.core.application.database.interfaces.uow import UnitOfWorkProtocol
from trading_bot.core.application.trading.dto.event import EventDTO
from trading_bot.core.domain.entities.position import Position
from trading_bot.core.domain.value_objects.take_profit import TakeProfit
from trading_bot.core.domain.value_objects.trading import TradeSide

logger = logging.getLogger(__name__)


@final
class FilledUseCase:
    def __init__(self, uow_factory: Callable[[], UnitOfWorkProtocol]):
        self._uow_factory = uow_factory

    async def handle(self, event: EventDTO) -> None:
        if not event.order or event.order.price is None or event.order.qty is None:
            return
        order = event.order
        account_name = event.account_name
        entry_order_db = None
        logger.info(f"🚀 [{account_name}] [{order.symbol}] Исполнен входной ордер (ID: {order.id}). Цена входа: {order.price}")
        uow = self._uow_factory()
        async with uow:
            # 1. Retrieve the executed entry order from our DB
            if event.order.order_link_id:
                entry_order_db = await uow.orders.get_by_link_id(event.order.order_link_id)
            else:
                entry_order_db = await uow.orders.get_by_id(event.order.id)
            if not entry_order_db or not entry_order_db.message_id:
                logger.warning(
                    f"⚠️ [{account_name}] [{order.symbol}] Входной ордер не найден в БД или не имеет message_id (ID: {order.id}, link: {order.order_link_id}). Позиция не создана."
                )
                return

            # 2. Find SL and TP belonging to the SAME signal (message_id)
            sl_order_db = await uow.orders.get_stop_loss_by_signal(account_name=event.account_name, message_id=entry_order_db.message_id)
            sl_order_id = sl_order_db.order_link_id if sl_order_db else None
            # 3. Find attached Take Profits
            tps_db = await uow.orders.get_takeprofits_by_signal(account_name=event.account_name, message_id=entry_order_db.message_id)
            # Map DTOs from DB to Value Objects for Domain
            tp_vos = [TakeProfit(price=tp.price or tp.trigger_price, level=tp.level) for tp in (tps_db or []) if (tp.price or tp.trigger_price) and tp.level]
            # 4. Create a new Position entity
            actual_entry_price = order.price or order.trigger_price or 0
            new_position = Position(
                symbol=order.symbol,
                account_name=account_name,
                side=order.side or TradeSide.LONG,
                entry_price=actual_entry_price,
                size=order.qty or 0,
                current_sl_order_id=sl_order_id,
                take_profits=tp_vos,
            )
            position_dto = PositionDTO.from_entity(new_position)
            # 5. Save to DB
            await uow.positions.upsert(position_dto)
            # 6. DELETE executed entry order to avoid cluttering DB
            if entry_order_db.id:
                await uow.orders.delete_by_id(entry_order_db.id)
            await uow.commit()

            logger.info(f"✅ [{account_name}] [{order.symbol}] Позиция успешно создана в базе")
