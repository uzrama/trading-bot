from dishka import Provider, Scope, provide

from trading_bot.core.application.trading.interfaces.config import ConfigProviderProtocol
from trading_bot.infrastructure.config.provider import ConfigsProvider
from trading_bot.main.config.settings import AppSettings


class SettingsProvide(Provider):
    @provide(scope=Scope.APP)
    def get_settings(self) -> AppSettings:
        return AppSettings()

    @provide(scope=Scope.APP)
    def get_config(self, settings: AppSettings) -> ConfigProviderProtocol:
        return ConfigsProvider(settings)
