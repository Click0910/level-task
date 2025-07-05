from logging.config import fileConfig
import os
from pathlib import Path
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# Cargar .env local
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / "variables.env")

# Importar modelos y Base
from src.api.app.database import Base  # asegúrate de que este sea tu Base declarativa

# Configuración base de Alembic
config = context.config

# 👉 Hardcodea aquí tu URL local para desarrollo
database_url = "postgresql://ticket_user:ticket_pass@localhost:5432/ticket_db"

config.set_main_option("sqlalchemy.url", database_url)

# Logging
if config.config_file_name:
    fileConfig(config.config_file_name)

# Target metadata (para autogenerar)
target_metadata = Base.metadata

# Modo offline
def run_migrations_offline():
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

# Modo online
def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

# Ejecutar
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
