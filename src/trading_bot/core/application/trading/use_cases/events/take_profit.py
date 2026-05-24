import logging
import uuid
from collections.abc import Callable
from typing import final

from trading_bot.core.application.database.dto import OrderDTO
from trading_bot.core.application.database.dto.position import PositionDTO
from trading_bot.core.application.database.interfaces.uow import UnitOfWorkProtocol
from trading_bot.core.application.trading.dto.event import EventDTO
from trading_bot.core.application.trading.interfaces.config import ConfigProviderProtocol
from trading_bot.core.application.trading.interfaces.exchange import ExchangeRegistryProtocol
from trading_bot.core.domain.value_objects.take_profit import TakeProfit

logger = logging.getLogger(__name__)


@final
class TakeProfitUseCase:
    def __init__(self, exchange_composite: ExchangeRegistryProtocol, uow_factory: Callable[[], UnitOfWorkProtocol], config_provider: ConfigProviderProtocol):
        self._exchange_composite = exchange_composite
        self._uow_factory = uow_factory
        self._config_provider = config_provider

    async def handle(self, event: EventDTO) -> None:
        if not event.order or event.order.price is None or event.order.qty is None:
            return
        logger.info(f"🎯 [{event.account_name}] [{event.order.symbol}] Исполнен Тейк-Профит (ID: {event.order.id})")
        uow = self._uow_factory()
        async with uow:
            tp_order_db = await uow.orders.get_by_id(event.order.id)
            # 1. Fixed argument passing
            position_dto = await uow.positions.get_active_by_symbol(account_name=event.account_name, symbol=event.order.symbol)

        if not position_dto or not tp_order_db or not tp_order_db.message_id or not tp_order_db.level:
            return
        async with uow:
            tps_db = await uow.orders.get_takeprofits_by_signal(account_name=event.account_name, message_id=tp_order_db.message_id)

        tp_vos = [TakeProfit(price=tp.price or tp.trigger_price, level=tp.level) for tp in (tps_db or []) if (tp.price or tp.trigger_price) and tp.level]
        # 2. DTO -> Entity mapping
        position_entity = position_dto.to_entity(take_profits=tp_vos)

        target_sl_state = position_entity.process_take_profit(executed_qty=event.order.qty, tp_level=tp_order_db.level)

        exchange = self._exchange_composite.get_exchange(event.account_name)
        if target_sl_state:
            new_sl_price = position_entity.calculate_sl_price(target_state=target_sl_state)
            if position_entity.current_sl_order_id:
                try:
                    await exchange.cancel_order(event.order.symbol, position_entity.current_sl_order_id)
                except Exception as e:
                    logger.warning(f"⚠️ [{event.account_name}] [{event.order.symbol}] Не удалось отменить старый SL (ID: {position_entity.current_sl_order_id}): {e}")
            try:
                new_sl_link_id = str(uuid.uuid4())
                new_sl_order = await exchange.place_stop_loss_order(symbol=event.order.symbol, side=position_entity.side, stop_price=new_sl_price, link_id=new_sl_link_id)
                async with uow:
                    await uow.orders.upsert(OrderDTO.from_placed_order(new_sl_order, event.account_name, tp_order_db.message_id))
                    await uow.commit()
                position_entity.current_sl_order_id = new_sl_link_id
                logger.info(f"🛡️ [{event.account_name}] [{event.order.symbol}] Стоп-Лосс успешно перенесен на {new_sl_price} ({target_sl_state.value})")
            except Exception as e:
                logger.critical(f"🚨 [{event.account_name}] [{event.order.symbol}] КРИТИЧЕСКАЯ ОШИБКА: Не удалось перенести SL в БУ: {e}")
                logger.critical(f"🚨 [{event.account_name}] [{event.order.symbol}] Выполняется экстренное закрытие позиции по рынку!")

                # 1. Cancel all remaining take profits
                await exchange.cancel_all_orders(event.order.symbol)

                # 2. Close the remaining position with a market order
                try:
                    symbol_info = await exchange.get_symbol_info(event.order.symbol)
                    qty_to_close = position_entity.get_rounded_size(symbol_info.qty_step)

                    if qty_to_close > 0:
                        await exchange.cancel_position(symbol=event.order.symbol, side=position_entity.side, qty=qty_to_close)
                    logger.info(f"✅ [{event.account_name}] [{event.order.symbol}] Позиция экстренно закрыта (Объем: {qty_to_close})")
                except Exception as close_error:
                    # If the error contains code 110017 (position is zero) - it's not fatal!
                    error_str = str(close_error)
                    if "110017" in error_str or "position is zero" in error_str.lower():
                        logger.info(f"✅ [{event.account_name}] [{event.order.symbol}] Позиция уже закрыта на бирже. Аварийное закрытие не требуется")
                    else:
                        logger.critical(f"🚨 [{event.account_name}] [{event.order.symbol}] ФАТАЛЬНО: Не удалось закрыть позицию по рынку: {close_error}")

                # 3. Update entity status
                position_entity.size = 0.0
                position_entity.is_closed = True
                position_entity.current_sl_order_id = None
        if position_entity.size <= 0:
            await exchange.cancel_all_orders(event.order.symbol)
            position_entity.is_closed = True
        # 4. Save updated position
        updated_position_dto = PositionDTO.from_entity(position_entity)
        async with uow:
            # Update position state
            await uow.positions.upsert(updated_position_dto)

            # If position is fully closed, clear all remaining orders for this symbol from DB
            if position_entity.is_closed:
                await uow.orders.delete_by_symbol_and_account(event.account_name, event.order.symbol)
                logger.info(f"🗑️ [{event.account_name}] [{event.order.symbol}] Позиция закрыта. Все ордера удалены из БД")
            await uow.commit()
