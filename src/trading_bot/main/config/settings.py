from typing import ClassVar, override

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from trading_bot.main.config.models.account import AccountConfig
from trading_bot.main.config.models.postgres import PostgresConfig
from trading_bot.main.config.models.sqlalchemy import SQLAlchemyConfig

from .models.discord import DiscordConfig


class AppSettings(BaseSettings):
    discord: DiscordConfig = Field(default_factory=DiscordConfig)  # pyright: ignore[reportArgumentType]
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)  # pyright: ignore[reportArgumentType]
    sqlalchemy: SQLAlchemyConfig = Field(default_factory=SQLAlchemyConfig)
    accounts: dict[str, AccountConfig] = Field(default_factory=dict)

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        # yaml_file="configs/config.dev.yaml",
        yaml_file="configs/config.prod.yaml",
        extra="ignore",
    )

    @override
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        yaml_settings = YamlConfigSettingsSource(settings_cls)
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            yaml_settings,
            file_secret_settings,
        )
