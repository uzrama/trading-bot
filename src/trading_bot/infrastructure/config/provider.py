from typing import final, override

from trading_bot.core.application.trading.interfaces.config import AccountConfig, ConfigProviderProtocol, SourceConfig
from trading_bot.main.config.models.discord import Source
from trading_bot.main.config.settings import AppSettings


@final
class AccountConfigAdapter(AccountConfig):
    def __init__(self, account_config: AccountConfig):
        self._config = account_config

    @property
    @override
    def position_size(self) -> float:
        return self._config.position_size


@final
class SourceConfigAdapter(SourceConfig):
    def __init__(self, source_config: Source):
        self._config = source_config

    @property
    @override
    def default_sl(self) -> float:
        return self._config.default_sl

    @property
    @override
    def accounts(self) -> list[str]:
        return [link.account for link in self._config.accounts]

    @override
    def get_tp_distribution(self, num_tps: int) -> list[float]:
        dist = self._config.tp_distributions.get(num_tps, [])
        return [tp.close_size for tp in dist]


@final
class ConfigsProvider(ConfigProviderProtocol):
    def __init__(self, settings: AppSettings):
        self._settings = settings

    @override
    def get_account_config(self, account_name: str) -> AccountConfig:
        config = self._settings.accounts[account_name]
        return AccountConfigAdapter(config)

    @override
    def get_source_config(self, source_id: int) -> SourceConfig:
        source = next(src for src in self._settings.discord.sources if src.channel_id == source_id)
        return SourceConfigAdapter(source)
