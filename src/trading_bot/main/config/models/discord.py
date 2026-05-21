from pydantic import BaseModel, SecretStr


class TPDistribution(BaseModel):
    level: int
    close_size: float


class DiscordAccountLink(BaseModel):
    account: str


class Source(BaseModel):
    source_name: str
    enabled: bool
    channel_id: int
    accounts: list[DiscordAccountLink]
    leverage: int
    default_sl: float
    tp_distributions: dict[int, list[TPDistribution]]


class DiscordConfig(BaseModel):
    token: SecretStr
    sources: list[Source]
