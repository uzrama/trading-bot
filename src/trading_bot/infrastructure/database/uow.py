import traceback
from types import TracebackType
from typing import final, override

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from trading_bot.core.application.database.interfaces.uow import UnitOfWorkProtocol
from trading_bot.infrastructure.database.repositories.position import SQLAlchemyPositionRepository

from .repositories import SQLAlchemyOrderRepository


@final
class SQLAlchemyUoW(UnitOfWorkProtocol):
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self._session_maker = session_maker
        self._session: AsyncSession | None = None
        self._session_ctx = None

    @override
    async def __aenter__(self) -> SQLAlchemyUoW:
        self._session_ctx = self._session_maker()
        self._session = await self._session_ctx.__aenter__()
        self.orders = SQLAlchemyOrderRepository(self._session)
        self.positions = SQLAlchemyPositionRepository(self._session)

        return self

    @override
    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
        if exc_val:
            print("ERROR:", exc_val)
            print("".join(traceback.format_tb(exc_tb)))
            print(f"Exception type: {exc_type}")
        if self._session_ctx:
            try:
                if exc_type is not None and self._session:
                    await self._session.rollback()
            finally:
                await self._session_ctx.__aexit__(exc_type, exc_val, exc_tb)
                self._session = None
                self._session_ctx = None

    @override
    async def commit(self):
        if self._session is None:
            raise RuntimeError("Session is not initialized. Call __aenter__ first.")
        await self._session.commit()

    @override
    async def rollback(self):
        if self._session is None:
            raise RuntimeError("Session is not initialized. Call __aenter__ first.")
        await self._session.rollback()
