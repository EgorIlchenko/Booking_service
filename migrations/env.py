"""Окружение Alembic: async-движок и метаданные домена."""

import asyncio

from alembic import context
from app.config import get_settings
from app.domain.models import Base
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import create_async_engine

target_metadata = Base.metadata


def get_url() -> str:
    """Возвращает строку подключения к БД.

    Returns:
        URL базы данных из настроек приложения.
    """
    return get_settings().database_url


def run_migrations_offline() -> None:
    """Запускает миграции без подключения (рендер SQL)."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Выполняет миграции в рамках соединения.

    Args:
        connection: Синхронное соединение, переданное из async-движка.
    """
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Запускает миграции через async-подключение."""
    engine = create_async_engine(get_url())
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
