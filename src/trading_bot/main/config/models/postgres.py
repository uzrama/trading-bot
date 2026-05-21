from pydantic import BaseModel, SecretStr
from sqlalchemy import URL


class PostgresConfig(BaseModel):
    host: str
    db: str
    password: SecretStr
    port: int
    user: str

    def build_url(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.user,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            database=self.db,
        )
