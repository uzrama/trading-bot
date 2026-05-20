from typing import Any, final

from trading_bot.core.domain.exceptions.base import InfrastructureException


@final
class ExchangeAPIException(InfrastructureException):
    """Raised when an error occurs in the Exchange API response."""

    def __init__(self, message: str, code: int | None = None, response: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.response = response


class EntityNotFoundException(InfrastructureException):
    """Raised when an entity is not found in the database/repository."""

    def __init__(self, entity_name: str, entity_id: str):
        super().__init__(f"Entity {entity_name} with ID/key {entity_id} was not found in the database.")


class SignalParsingException(InfrastructureException):
    """Raised when the discord parser fails to parse a signal."""

    pass
