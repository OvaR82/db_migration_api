from logging.config import fileConfig
from alembic import context
import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.db import Base, DB_URL
from app import models

config = context.config

if config.config_file_name is not None and config.get_section("loggers"):
    fileConfig(config.config_file_name)

# También escribe la URL en el config para que otros comandos la vean
if DB_URL:
    config.set_main_option("sqlalchemy.url", DB_URL)

target_metadata = Base.metadata

def run_migrations_offline():
    url = DB_URL or config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    from sqlalchemy import engine_from_config, pool
    # Con prefix="" la clave debe ser **url** (no sqlalchemy.url)
    opts = {"url": DB_URL or config.get_main_option("sqlalchemy.url")}
    connectable = engine_from_config(opts, prefix="", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
