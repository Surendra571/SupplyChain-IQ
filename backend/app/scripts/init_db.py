"""SupplyChain IQ - Database Initialization CLI Script."""

import sys
import logging
from sqlalchemy import text
from backend.app.core.database import engine, init_db
from backend.app.models.base import Base
import backend.app.models  # ensure all models registered

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_db")


def main():
    logger.info("Initializing SupplyChain IQ database schemas...")
    with engine.connect() as conn:
        # Create segregated schemas if PostgreSQL
        if engine.dialect.name == "postgresql":
            logger.info("Creating 'ground_truth' schema for benchmark segregation...")
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS ground_truth;"))
            conn.commit()
            
    logger.info("Creating operational tables in 'public' schema...")
    init_db(engine)
    logger.info("Database initialized successfully with all tables!")


if __name__ == "__main__":
    main()

