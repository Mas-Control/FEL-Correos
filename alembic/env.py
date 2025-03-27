# pylint: disable=E1101, wrong-import-position, wildcard-import, E0401
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from app.config import get_settings
from app.database import Base
from app.main import logger
from app.models.schemas import *  # noqa: F403, F401

from alembic import context

# Load settings
settings = get_settings()

DATABASE_URL = settings.DATABASE_URL
# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set the SQLAlchemy URL dynamically from settings
if DATABASE_URL:
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
else:
    raise ValueError("DATABASE_URL is not set")


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


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
    logger.info("Running migrations offline with URL: %s", url)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        logger.info("Starting offline migration")
        context.run_migrations()
        logger.info("Completed offline migration")


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    logger.info("Configuring online migration engine")
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.QueuePool,
        pool_size=50,
        max_overflow=50,
        pool_timeout=30,
        pool_recycle=600,
        pool_pre_ping=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            logger.info("Starting online migration")
            context.run_migrations()
            logger.info("Completed online migration")


if context.is_offline_mode():
    logger.info("Running in offline mode")
    run_migrations_offline()
else:
    logger.info("Running in online mode")
    run_migrations_online()
