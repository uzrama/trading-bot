import asyncio
import logging
import uuid
from collections.abc import Callable
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import final

from trading_bot.core.application.database.dto import OrderDTO, PositionDTO
from trading_bot.core.application.database.interfaces.uow import UnitOfWorkProtocol
from trading_bot.core.application.signal.dto.signal import SignalDTO
from trading_bot.core.application.trading.interfaces.config import ConfigProviderProtocol
from trading_bot.core.application.trading.interfaces.exchange import ExchangeGatewayProtocol, ExchangeRegistryProtocol
from trading_bot.core.domain.value_objects.trading import StopLossState

logger = logging.getLogger(__name__)


@final
class UpdateSignalUseCase:
    def __init__(
        self,
        exchange_composite: ExchangeRegistryProtocol,
        uow_factory: Callable[[], UnitOfWorkProtocol],
        config_provider: ConfigProviderProtocol,
    ):
        self._exchange_composite = exchange_composite
        self._uow_factory = uow_factory
        self._config_provider = config_provider

    async def execute(self, signal: SignalDTO) -> None:
        if not signal.stop_loss:
            return  # Nothing to update, SL still not present

        logger.debug(f"🔄 [{signal.source_name}] [{signal.symbol}] Received signal update")

        try:
            source_config = self._config_provider.get_source_config(signal.source_id)
        except Exception as e:
            logger.error(f"❌ Failed to get source config for {signal.source_name}: {e}")
            return

        target_accounts = source_config.accounts
        if not target_accounts:
            logger.warning(f"⚠️ No accounts configured for source {signal.source_name}. Skipping update.")
            return

        tasks = []
        for account_name in target_accounts:
            try:
                exchange = self._exchange_composite.get_exchange(account_name)
                tasks.append(self._process_update_for_exchange(exchange, signal))
            except Exception as e:
                logger.error(f"❌ Failed to initialize account {account_name} for update: {e}")

        if tasks:
            await asyncio.gather(*tasks)

    async def _process_update_for_exchange(self, exchange: ExchangeGatewayProtocol, signal: SignalDTO) -> None:
        uow = self._uow_factory()
        async with uow:
            position_dto = await uow.positions.get_active_by_symbol(account_name=exchange.account_name, symbol=signal.symbol)

            if not position_dto or not position_dto.current_sl_order_id:
                return
            # --- 1. PROTECT AGAINST BREAKEVEN OVERWRITE ---
            if position_dto.sl_state != StopLossState.INITIAL:
                logger.debug(f"⚠️ [{exchange.account_name}] [{signal.symbol}] СЛ уже перенесен в {position_dto.sl_state.value}. Игнорируем обновление из Discord.")
                return
            # --- 2. PROTECT AGAINST REPEATED UPDATE ---
            if position_dto.is_sl_updated:
                logger.debug(f"⚠️ [{exchange.account_name}] [{signal.symbol}] СЛ уже был обновлен по сигналу ранее. Игнорируем повторное обновление.")
                return
            # Retrieve old SL from DB
            old_sl_db = await uow.orders.get_by_link_id(position_dto.current_sl_order_id)
            # (Or get_by_id, depending on what is stored in position)
            if not old_sl_db or old_sl_db.trigger_price is None:
                return
            # Calculate new price with rounding
            symbol_info = await exchange.get_symbol_info(signal.symbol)
            sl_dec = Decimal(str(signal.stop_loss))
            tick_dec = Decimal(str(symbol_info.tick_size))
            if signal.side.value == "Buy":
                # Round up (safer for long)
                new_sl_price = float((sl_dec / tick_dec).quantize(Decimal("1"), rounding=ROUND_CEILING) * tick_dec)
            else:
                # Round down (safer for short)
                new_sl_price = float((sl_dec / tick_dec).quantize(Decimal("1"), rounding=ROUND_FLOOR) * tick_dec)
            # If provider price differs from our default SL - move it!
            if abs(old_sl_db.trigger_price - new_sl_price) > symbol_info.tick_size:
                logger.info(f"🛡️ [{exchange.account_name}] [{signal.symbol}] Обновление СЛ: {old_sl_db.trigger_price} -> {new_sl_price}")

                # 1. Cancel old
                try:
                    await exchange.cancel_order_by_link_id(signal.symbol, position_dto.current_sl_order_id)
                except Exception as e:
                    logger.warning(f"⚠️ [{exchange.account_name}] [{signal.symbol}] Не удалось отменить старый СЛ (ID: {position_dto.current_sl_order_id}): {e}")
                # 2. Place new
                new_sl_link_id = str(uuid.uuid4())
                new_sl_placed = await exchange.place_stop_loss_order(symbol=signal.symbol, side=signal.side, stop_price=new_sl_price, link_id=new_sl_link_id)

                # 3. Update DB (delete old, write new)
                await uow.orders.delete_by_link_id(position_dto.current_sl_order_id)
                await uow.orders.upsert(OrderDTO.from_placed_order(new_sl_placed, exchange.account_name, str(signal.message_id)))

                # 4. Update position
                position_entity = position_dto.to_entity()
                position_entity.current_sl_order_id = new_sl_link_id  # Save new ID

                position_entity.is_sl_updated = True

                await uow.positions.upsert(PositionDTO.from_entity(position_entity))
                await uow.commit()
