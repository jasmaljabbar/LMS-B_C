# alembic/env.py
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# --- ADD THESE IMPORTS ---
import sys
import os
# Adjust path if your project structure is different
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import Base # Import your Base from where it's defined
from backend import models       # Import your models module to register tables
# --- END ADDED IMPORTS ---

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# --- SET THIS VARIABLE ---
# target_metadata = None # Original line might be None or commented out
target_metadata = Base.metadata # Assign your Base's metadata here
# --- END SET VARIABLE ---

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# ... (rest of the file, including run_migrations_offline) ...

def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # --- ENSURE target_metadata IS SET HERE TOO ---
    # This block might already exist, just ensure target_metadata uses your Base.metadata
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata # Make sure it uses your Base.metadata
            # ... other options like compare_type=True might be here
        )

        with context.begin_transaction():
            context.run_migrations()
    # --- END ENSURE ---

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
