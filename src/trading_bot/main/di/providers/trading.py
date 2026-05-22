import logging
from collections.abc import AsyncIterable, Callable
from typing import final

from dishka import Provider, Scope, provide

from trading_bot.core.application.database.interfaces.uow import UnitOfWorkProtocol
from trading_bot.core.application.signal.use_cases.execute_signal import ExecuteSignalUseCase
from trading_bot.core.application.signal.use_cases.update_signal import UpdateSignalUseCase
from trading_bot.core.application.trading.interfaces.config import ConfigProviderProtocol
from trading_bot.core.application.trading.interfaces.exchange import ExchangeRegistryProtocol
from trading_bot.core.application.trading.use_cases.dispatcher import EventDispatcherUseCase
from trading_bot.core.application.trading.use_cases.events import ConfirmedUseCase, FilledUseCase, RejectedUseCase, TakeProfitUseCase
from trading_bot.core.application.trading.use_cases.events.stop_loss import StopLossUseCase
from trading_bot.infrastructure.exchanges.bybit import BybitAdapter
from trading_bot.infrastructure.exchanges.composite import CompositeExchangeGateway
from trading_bot.main.config.settings import AppSettings

logger = logging.getLogger(__name__)


@final
class TradingProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_exchange_composite(self, settings: AppSettings) -> AsyncIterable[CompositeExchangeGateway]:
        exchanges = {}
        for account_name, account in settings.accounts.items():
            api_key = account.api_key.get_secret_value()
            secret = account.api_secret.get_secret_value()

            if api_key and secret:
                exchanges[account_name] = BybitAdapter(account_name=account_name, api_key=api_key, api_secret=secret, demo=account.demo)
            else:
                logger.warning(f"⚠️ Bybit account '{account_name}' has empty credentials, skipping")

        if not exchanges:
            raise RuntimeError("❌ No exchange adapters configured. Please provide API keys for at least one exchange account in your .env file.")

        if not exchanges:
            raise RuntimeError("❌ No exchange adapters configured. Please provide API keys for at least one exchange account in your .env file.")
        logger.info(f"📊 Active exchange accounts: {', '.join(exchanges.keys())}")
        composite = CompositeExchangeGateway(exchanges)
        yield composite
        await composite.close()

    # FIX: SCOPE APP
    @provide(scope=Scope.APP)
    def get_execute_signal_use_case(
        self,
        exchange_composite: ExchangeRegistryProtocol,
        uow_factory: Callable[[], UnitOfWorkProtocol],
        config_provider: ConfigProviderProtocol,
    ) -> ExecuteSignalUseCase:
        return ExecuteSignalUseCase(
            exchange_composite=exchange_composite,
            uow_factory=uow_factory,
            config_provider=config_provider,
        )

    @provide(scope=Scope.APP)
    def get_update_signal_use_case(
        self,
        exchange_composite: ExchangeRegistryProtocol,
        uow_factory: Callable[[], UnitOfWorkProtocol],
        config_provider: ConfigProviderProtocol,
    ) -> UpdateSignalUseCase:
        return UpdateSignalUseCase(
            exchange_composite=exchange_composite,
            uow_factory=uow_factory,
            config_provider=config_provider,
        )

    @provide(scope=Scope.APP)
    def get_rejected_use_case(
        self,
        exchange_composite: ExchangeRegistryProtocol,
        uow_factory: Callable[[], UnitOfWorkProtocol],
    ) -> RejectedUseCase:
        return RejectedUseCase(
            exchange_composite=exchange_composite,
            uow_factory=uow_factory,
        )

    @provide(scope=Scope.APP)
    def get_take_profit_use_case(
        self,
        exchange_composite: ExchangeRegistryProtocol,
        uow_factory: Callable[[], UnitOfWorkProtocol],
        config_provider: ConfigProviderProtocol,
    ) -> TakeProfitUseCase:
        return TakeProfitUseCase(
            exchange_composite=exchange_composite,
            uow_factory=uow_factory,
            config_provider=config_provider,
        )

    @provide(scope=Scope.APP)
    def get_filled_use_case(
        self,
        uow_factory: Callable[[], UnitOfWorkProtocol],
    ) -> FilledUseCase:
        return FilledUseCase(
            uow_factory=uow_factory,
        )

    @provide(scope=Scope.APP)
    def get_stop_loss_use_case(
        self,
        exchange_composite: ExchangeRegistryProtocol,
        uow_factory: Callable[[], UnitOfWorkProtocol],
    ) -> StopLossUseCase:
        return StopLossUseCase(
            exchange_composite=exchange_composite,
            uow_factory=uow_factory,
        )

    @provide(scope=Scope.APP)
    def get_confirmed_use_case(self, uow_factory: Callable[[], UnitOfWorkProtocol]) -> ConfirmedUseCase:
        return ConfirmedUseCase(uow_factory=uow_factory)

    @provide(scope=Scope.APP)
    def get_event_dispatcher(
        self,
        rejected_handler: RejectedUseCase,
        take_profit_handler: TakeProfitUseCase,
        filled_handler: FilledUseCase,
        stop_loss_handler: StopLossUseCase,
        confirmed_handler: ConfirmedUseCase,
        uow_factory: Callable[[], UnitOfWorkProtocol],
    ) -> EventDispatcherUseCase:
        return EventDispatcherUseCase(
            rejected_handler=rejected_handler,
            take_profit_handler=take_profit_handler,
            filled_handler=filled_handler,
            stop_loss_handler=stop_loss_handler,
            confirmed_handler=confirmed_handler,
            uow_factory=uow_factory,
        )

    @provide(scope=Scope.APP)
    def get_exchange_registry(self, composite: CompositeExchangeGateway) -> ExchangeRegistryProtocol:
        return composite
