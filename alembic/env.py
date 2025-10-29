from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

# Add project root to path so `src` is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from alembic import context  # type: ignore

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config  # type: ignore

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import the metadata from the application models
from src.db import Base  # noqa: E402

target_metadata = Base.metadata


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///:memory:")


def run_migrations_offline() -> None:
    url = get_database_url()
    context.configure(  # type: ignore
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
    )

    with context.begin_transaction():  # type: ignore
        context.run_migrations()  # type: ignore


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}  # type: ignore
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)  # type: ignore

        with context.begin_transaction():  # type: ignore
            context.run_migrations()  # type: ignore


if context.is_offline_mode():  # type: ignore
    run_migrations_offline()
else:
    run_migrations_online()
