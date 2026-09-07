from logging.config import fileConfig

from alembic import context
from geoalchemy2.alembic_helpers import include_object, render_item
from sqlalchemy import engine_from_config, pool

from coolblock_api.db.base import Base
from coolblock_api.db.models import *  # noqa: F401,F403 -- registers every model on Base.metadata for autogenerate
from coolblock_api.settings import get_settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Real DB URL comes from coolblock_api.settings (which reads the repo's
# .env), not a second copy hardcoded in alembic.ini.
config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


# Tables owned by Postgres extensions already installed by
# `infra/postgres/init/001_extensions.sql` (postgis, postgis_topology),
# never part of our own SQLAlchemy metadata. `search_path` here is
# `"$user", public, topology` (topology's own default), which makes
# autogenerate reflect `topology`/`layer` as if they were unqualified
# `public` tables and propose dropping them as "removed" -- a schema-name
# filter alone doesn't catch this, since as far as reflection is
# concerned they aren't schema-qualified. `geoalchemy2.alembic_helpers.
# include_object` (used below) only filters `spatial_ref_sys`; this closes
# the gap for the topology extension's own tables.
_EXTENSION_OWNED_TABLES = frozenset({"topology", "layer"})


def include_name(name: str | None, type_: str, parent_names: dict[str, str]) -> bool:
    if type_ == "table":
        return name not in _EXTENSION_OWNED_TABLES
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=render_item,
        include_object=include_object,
        include_name=include_name,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_item=render_item,
            include_object=include_object,
            include_name=include_name,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
