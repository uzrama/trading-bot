from pydantic import BaseModel, SecretStr


class AccountConfig(BaseModel):
    exchange: str
    demo: bool
    position_size: float
    timeout_seconds: int
    api_key: SecretStr
    api_secret: SecretStr
