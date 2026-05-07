import asyncio
import logging
from collections.abc import Callable
from typing import final

from trading_bot.core.application.database.dto.order import OrderDTO
from trading_bot.core.application.database.interfaces.uow import UnitOfWorkProtocol
from trading_bot.core.application.signal.dto.signal import SignalDTO
from trading_bot.core.application.trading.dto.order import PlaceOrderDTO
from trading_bot.core.application.trading.interfaces.config import ConfigProviderProtocol, SourceConfig
from trading_bot.core.application.trading.interfaces.exchange import ExchangeGatewayProtocol, ExchangeRegistryProtocol
from trading_bot.core.domain.entities.trade_setup import TradeSetup
from trading_bot.core.domain.exceptions.trading import SymbolNotFoundException
from trading_bot.core.domain.value_objects.symbol import SymbolInfo
from trading_bot.core.domain.value_objects.trading import OrderStatus, OrderType

logger = logging.getLogger(__name__)


@final
class ExecuteSignalUseCase:
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
        logger.info(f"📥 [{signal.source_name}] [{signal.symbol}] Received new signal ({signal.side.value})")
        # 1. Get source configuration by channel ID
        try:
            source_config = self._config_provider.get_source_config(signal.source_id)
        except Exception as e:
            logger.error(f"❌ Failed to get source config for {signal.source_name}: {e}")
            return
        # 2. Get list of accounts linked to this source
        target_accounts = source_config.accounts
        if not target_accounts:
            logger.warning(f"⚠️ No accounts configured for source {signal.source_name}. Skipping.")
            return
        # 3. Build tasks for each account
        tasks = []
        for account_name in target_accounts:
            try:
                exchange = self._exchange_composite.get_exchange(account_name)
                tasks.append(self._process_signal_for_exchange(exchange, signal))
            except Exception as e:
                logger.error(f"❌ Failed to initialize account {account_name}: {e}")
        # 4. Execute orders asynchronously on all target accounts
        if tasks:
            await asyncio.gather(*tasks)

    async def _process_signal_for_exchange(self, exchange: ExchangeGatewayProtocol, signal: SignalDTO) -> None:
        if await exchange.get_position(signal.symbol) or await exchange.get_orders(signal.symbol):
            logger.warning(f"⚠️ [{exchange.account_name}] [{signal.symbol}] Позиция/Ордера уже существуют. Игнорируем.")
            return
        uow = self._uow_factory()
        async with uow:
            try:
                market_price, symbol_info, balance = await asyncio.gather(
                    exchange.get_last_price(signal.symbol),
                    exchange.get_symbol_info(signal.symbol),
                    exchange.get_balance(),
                )
            except SymbolNotFoundException as e:
                logger.warning(f"⚠️ [{exchange.account_name}] [{signal.symbol}] Пропускаем сигнал: {e.message}")
                return
            except Exception as e:
                logger.error(f"❌ [{exchange.account_name}] [{signal.symbol}] Ошибка получения рыночных данных: {e}")
                return

            account_config = self._config_provider.get_account_config(exchange.account_name)
            source_config = self._config_provider.get_source_config(signal.source_id)

            trade_setup = TradeSetup(
                symbol=signal.symbol,
                side=signal.side,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profits=signal.take_profits,
            )
            if not trade_setup.is_valid_for_entry(market_price):
                logger.warning(f"⚠️ [{signal.source_name}] [{signal.symbol}] Цена ({market_price}) вне диапазона SL/TP. Вход отменен.")
                return
            qty = trade_setup.calculate_qty(
                balance=balance,
                market_price=market_price,
                position_size_pct=account_config.position_size,
                leverage=5,
                symbol_info=symbol_info,
            )
            if qty <= 0:
                logger.error(f"❌ [{signal.source_name}] [{signal.symbol}] Объем для входа <= 0. Отмена.")
                return
            # 1. Build requests
            entry_req, sl_req, tp_reqs = self._build_order_requests(signal, trade_setup, market_price, qty, symbol_info, source_config)
            all_requests = [entry_req]
            if sl_req:
                all_requests.append(sl_req)
            all_requests.extend(tp_reqs)
            # 2. Pre-save
            for req in all_requests:
                db_dto = OrderDTO(
                    id=req.order_link_id,
                    order_link_id=req.order_link_id,
                    symbol=req.symbol,
                    side=req.side,
                    order_type=req.order_type,
                    status=OrderStatus.CREATED,
                    qty=req.qty,
                    price=req.price,
                    trigger_price=req.trigger_price,
                    level=req.level,
                    account_name=exchange.account_name,
                    message_id=str(signal.message_id),
                )
                await uow.orders.upsert(db_dto)

            await uow.commit()  # Commit pre-save
            # 3. Post requests (ALL OR NOTHING)
            placed_results = await exchange.place_trade_setup(all_requests)
            # If exchange returned fewer orders than requested -> failure (insufficient margin for a TP, limit failure, etc.)
            if len(placed_results) != len(all_requests):
                logger.error(
                    f"🚨 [{signal.source_name}] [{signal.symbol}] Частичный отказ REST API! Принято {len(placed_results)} из {len(all_requests)} ордеров. Экстренная отмена!"
                )
                try:
                    await exchange.cancel_all_orders(signal.symbol)
                except Exception as e:
                    logger.error(f"⚠️ [{exchange.account_name}] Ошибка при отмене ордеров: {e}")
                try:
                    position_info = await exchange.get_position(signal.symbol)
                    if position_info and position_info.size > 0:
                        logger.warning(f"⚠️ [{signal.source_name}] [{signal.symbol}] Позиция уже открыта. Экстренное закрытие по рынку!")
                        await exchange.cancel_position(signal.symbol, position_info.side, position_info.size)
                except Exception as e:
                    logger.critical(f"💀 [{exchange.account_name}] ФАТАЛЬНО: Не удалось проверить/закрыть позицию при сбое сетапа: {e}")
                await uow.orders.delete_by_symbol_and_account(account_name=exchange.account_name, symbol=signal.symbol)
                await uow.commit()
                return
            logger.info(f"✅ [{signal.source_name}] [{signal.symbol}] Сетап успешно размещен ({len(placed_results)} ордеров)")
            await uow.commit()

    def _build_order_requests(
        self,
        signal: SignalDTO,
        trade_setup: TradeSetup,
        market_price: float,
        qty: float,
        symbol_info: SymbolInfo,
        source_config: SourceConfig,
    ) -> tuple[PlaceOrderDTO, PlaceOrderDTO | None, list[PlaceOrderDTO]]:
        entry_price = signal.entry_price if signal.entry_price else market_price
        if signal.is_awaitable and signal.entry_price:
            entry_type = OrderType.CONDITIONAL
        else:
            entry_type = OrderType.LIMIT if signal.entry_price else OrderType.MARKET
        trig_dir = None
        if entry_type == OrderType.CONDITIONAL:
            trig_dir = 1 if market_price < entry_price else 2
        entry_req = PlaceOrderDTO(
            symbol=signal.symbol,
            side=signal.side,
            order_type=entry_type,
            qty=qty,
            price=entry_price if entry_type == OrderType.LIMIT else None,
            trigger_price=entry_price if entry_type == OrderType.CONDITIONAL else None,
            trigger_direction=trig_dir,
        )
        default_sl = source_config.default_sl if source_config else 0.05
        sl_price = trade_setup.calculate_sl_price(market_price, default_sl, symbol_info.tick_size)
        sl_req = (
            PlaceOrderDTO(symbol=signal.symbol, side=signal.side, order_type=OrderType.STOP_LOSS, trigger_price=sl_price, close_on_trigger=True, reduce_only=True)
            if sl_price
            else None
        )

        tp_reqs = []
        if signal.take_profits:
            tp_distribution = source_config.get_tp_distribution(len(signal.take_profits))
            tp_params = trade_setup.calculate_tp_sizes(qty, symbol_info.qty_step, tp_distribution)
            tp_reqs = [
                PlaceOrderDTO(
                    symbol=signal.symbol,
                    side=signal.side,
                    order_type=OrderType.TAKE_PROFIT,
                    qty=tp_qty,
                    trigger_price=tp_price,
                    level=level,
                    close_on_trigger=True,
                    reduce_only=True,
                )
                for tp_qty, tp_price, level in tp_params
            ]
        return entry_req, sl_req, tp_reqs
