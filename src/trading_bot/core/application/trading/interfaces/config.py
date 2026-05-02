from typing import Protocol


class AccountConfig(Protocol):
    @property
    def position_size(self) -> float: ...


class SourceConfig(Protocol):
    @property
    def default_sl(self) -> float: ...

    @property
    def accounts(self) -> list[str]: ...

    def get_tp_distribution(self, num_tps: int) -> list[float]: ...


class ConfigProviderProtocol(Protocol):
    def get_account_config(self, account_name: str) -> AccountConfig: ...
    def get_source_config(self, source_id: int) -> SourceConfig: ...
