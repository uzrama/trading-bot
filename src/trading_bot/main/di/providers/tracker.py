from typing import final

from dishka import Provider, Scope, provide

from trading_bot.core.application.trading.interfaces.exchange import ExchangeRegistryProtocol
from trading_bot.core.application.trading.use_cases.dispatcher import EventDispatcherUseCase
from trading_bot.main.runners.tracker import TrackerRunner


@final
class TrackerProvider(Provider):
    @provide(scope=Scope.APP)
    def get_tracker_runner(self, exchange_gateway: ExchangeRegistryProtocol, event_dispatcher_use_case: EventDispatcherUseCase) -> TrackerRunner:
        return TrackerRunner(exchange_gateway=exchange_gateway, event_dispatcher_use_case=event_dispatcher_use_case)
