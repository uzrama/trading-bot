from collections.abc import AsyncGenerator, Callable

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from trading_bot.core.application.database.interfaces.uow import UnitOfWorkProtocol
from trading_bot.infrastructure.database.uow import SQLAlchemyUoW
from trading_bot.main.config.settings import AppSettings


class DatabaseProvider(Provider):
    """
    DI Provider for configuring and providing database-related dependencies,
    including the SQLAlchemy engine, sessions, repositories, and Unit of Work.
    """

    @provide(scope=Scope.APP)
    def get_uow_factory(self, session_maker: async_sessionmaker[AsyncSession]) -> Callable[[], UnitOfWorkProtocol]:
        def factory() -> UnitOfWorkProtocol:
            return SQLAlchemyUoW(session_maker)

        return factory

    @provide(scope=Scope.APP)
    def get_engine(self, settings: AppSettings) -> AsyncEngine:
        return create_async_engine(
            url=settings.postgres.build_url(),
            echo=settings.sqlalchemy.echo,
            echo_pool=settings.sqlalchemy.echo_pool,
            pool_size=settings.sqlalchemy.pool_size,
            max_overflow=settings.sqlalchemy.max_overflow,
        )

    @provide(scope=Scope.APP)
    def get_session_maker(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    @provide(scope=Scope.REQUEST)
    async def get_session(self, session_maker: async_sessionmaker[AsyncSession]) -> AsyncGenerator[AsyncSession]:
        async with session_maker() as session:
            yield session

    @provide(scope=Scope.REQUEST)
    def get_uow(self, session_maker: async_sessionmaker[AsyncSession]) -> UnitOfWorkProtocol:
        return SQLAlchemyUoW(session_maker)
