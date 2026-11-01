"""SupplyChain IQ - Pytest Fixtures and Test DB Setup."""

import os
from pathlib import Path
import subprocess
import sys

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest
from sqlalchemy import text
from backend.app.core.database import SessionLocal, engine
from backend.app.models.master_data import SKU
from backend.app.workers.tasks import run_planning_job_sync


@pytest.fixture(scope="session")
def clean_database():
    """Explicitly clean all public tables if requested."""
    with engine.begin() as conn:
        conn.execute(text("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename != 'alembic_version') LOOP
                    EXECUTE 'TRUNCATE TABLE public.' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END $$;
        """))


@pytest.fixture(scope="function")
def db_session():
    """Provide an isolated database session with savepoint rollback."""
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture(scope="session")
def seeded_starter_data():
    """Ensure database has the starter dataset and planning run 1."""
    with SessionLocal() as db:
        cnt = db.query(SKU).count()

    if cnt < 100:
        seed_path = Path("data/generated/starter/sql/seed_data.sql")
        if seed_path.exists():
            env = os.environ.copy()
            env["PGPASSWORD"] = "postgres"
            subprocess.run([
                r"C:\Program Files\PostgreSQL\17\bin\psql.exe",
                "-p", "5433", "-U", "postgres", "-d", "supplychain_iq",
                "-f", str(seed_path)
            ], check=True, stdout=subprocess.DEVNULL, env=env)

        run_planning_job_sync(run_number=1, horizon_weeks=12, persist_db=True)

    return True
