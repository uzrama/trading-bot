from types import TracebackType
from typing import Protocol

from trading_bot.core.application.database.interfaces.repositories.postitions import PositionRepositoryProtocol

from .repositories import OrderRepositoryProtocol


class UnitOfWorkProtocol(Protocol):
    orders: OrderRepositoryProtocol
    positions: PositionRepositoryProtocol

    async def __aenter__(self) -> UnitOfWorkProtocol: ...

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
