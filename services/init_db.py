#!/usr/bin/env python3
"""
Database initialization script for the Agent Platform.

This script initializes the SQLite database by creating all tables.
It can be run from the command line to set up a fresh database.

Usage:
    python -m services.init_db                # Initialize database
    python -m services.init_db --force        # Drop and recreate database
    python -m services.init_db --verbose      # Show detailed output
    python -m services.init_db --force --verbose  # Both options
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect, text

from services.database import engine, Base, SessionLocal, init_db, drop_all

# Constants
DATABASE_PATH = "data/agent_platform.db"


# Configure logging
def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        verbose: If True, set logging level to DEBUG; otherwise INFO

    Returns:
        Configured logger instance
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


logger = logging.getLogger(__name__)


def ensure_data_directory() -> Path:
    """
    Ensure the data directory exists.

    Returns:
        Path to the data directory

    Raises:
        OSError: If directory creation fails
    """
    data_dir = Path("data")
    try:
        data_dir.mkdir(exist_ok=True)
        logger.debug(f"Data directory ensured: {data_dir.absolute()}")
        return data_dir
    except OSError as e:
        logger.error(f"Failed to create data directory: {e}")
        raise


def database_exists() -> bool:
    """
    Check if the database file exists.

    Returns:
        True if database file exists, False otherwise
    """
    db_path = Path(DATABASE_PATH)
    exists = db_path.exists()
    logger.debug(f"Database exists check: {exists}")
    return exists


def get_table_names() -> list:
    """
    Get list of table names in the database.

    Returns:
        List of table names
    """
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    logger.debug(f"Found {len(tables)} tables: {tables}")
    return tables


def drop_all_tables() -> None:
    """
    Drop all database tables.

    WARNING: This will delete all data irreversibly.
    """
    logger.warning("Dropping all database tables...")
    try:
        drop_all()
        logger.info("All tables dropped successfully")
    except Exception as e:
        logger.error(f"Failed to drop tables: {e}")
        raise


def initialize_database() -> None:
    """
    Initialize the database by creating all tables.

    Uses SQLAlchemy's create_all which is idempotent (safe to run multiple times).
    """
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def health_check() -> dict:
    """
    Perform a health check on the database.

    Returns:
        Dictionary with health check results:
        - database_exists: bool
        - tables_created: bool
        - table_count: int
        - can_query: bool
        - status: str ('healthy', 'unhealthy')
    """
    health = {
        "database_exists": False,
        "tables_created": False,
        "table_count": 0,
        "can_query": False,
        "status": "unhealthy"
    }

    try:
        # Check database file exists
        health["database_exists"] = database_exists()

        # Check tables are created
        tables = get_table_names()
        health["table_count"] = len(tables)
        health["tables_created"] = len(tables) > 0

        # Test basic query
        db = SessionLocal()
        try:
            # Try a simple query
            db.execute(text("SELECT 1"))
            health["can_query"] = True
        finally:
            db.close()

        # Overall status
        if all([health["database_exists"], health["tables_created"], health["can_query"]]):
            health["status"] = "healthy"

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        health["error"] = str(e)

    return health


def display_health_check(health: dict, verbose: bool = False) -> None:
    """
    Display health check results.

    Args:
        health: Health check dictionary
        verbose: If True, show detailed output
    """
    logger.info("Database Health Check Results:")
    logger.info(f"  Status: {health['status'].upper()}")
    logger.info(f"  Database exists: {health['database_exists']}")
    logger.info(f"  Tables created: {health['tables_created']}")
    logger.info(f"  Table count: {health['table_count']}")
    logger.info(f"  Can query: {health['can_query']}")

    if verbose and health['table_count'] > 0:
        tables = get_table_names()
        logger.info(f"  Tables: {', '.join(tables)}")

    if 'error' in health:
        logger.error(f"  Error: {health['error']}")


def display_created_tables() -> None:
    """
    Display list of created tables.
    """
    tables = get_table_names()
    logger.info(f"Created {len(tables)} table(s):")
    for table_name in tables:
        logger.info(f"  - {table_name}")


def main() -> None:
    """
    Main initialization function with CLI argument parsing.
    """
    parser = argparse.ArgumentParser(
        description="Initialize the Agent Platform SQLite database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m services.init_db                 # Initialize database
  python -m services.init_db --force         # Drop and recreate database
  python -m services.init_db --verbose       # Show detailed output
  python -m services.init_db --force --verbose  # Both options
        """
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Drop all existing tables and recreate the database (WARNING: deletes all data)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output with detailed logging'
    )

    args = parser.parse_args()

    # Set up logging
    logger = setup_logging(verbose=args.verbose)

    # Print header
    logger.info("=" * 70)
    logger.info("Agent Platform Database Initialization")
    logger.info("=" * 70)
    logger.debug(f"Started at: {datetime.now().isoformat()}")

    try:
        # Ensure data directory exists
        data_dir = ensure_data_directory()
        logger.info(f"Data directory: {data_dir.absolute()}")

        # Check if database already exists
        db_exists = database_exists()

        if db_exists and not args.force:
            logger.info("Database file already exists")
            tables = get_table_names()
            if tables:
                logger.info(f"Existing tables found: {', '.join(tables)}")
                logger.info("Creating any missing tables (safe to continue)...")
            else:
                logger.info("No existing tables found, creating new tables...")
        elif db_exists and args.force:
            logger.warning("--force flag specified: Dropping all existing tables!")
            logger.warning("This will delete all data irreversibly!")
            drop_all_tables()
            logger.info("Proceeding to create fresh tables...")
        else:
            logger.info("Creating new database")

        # Initialize database
        initialize_database()

        # Display created tables
        display_created_tables()

        # Perform health check
        logger.info("")
        health = health_check()
        display_health_check(health, verbose=args.verbose)

        # Final success message
        db_path = Path(DATABASE_PATH)
        logger.info("")
        logger.info("=" * 70)
        if health['status'] == 'healthy':
            logger.info("✓ Database initialized successfully!")
            logger.info(f"  Location: {db_path.absolute()}")
            logger.info(f"  Tables: {health['table_count']}")
            logger.info(f"  Status: {health['status'].upper()}")
        else:
            logger.error("✗ Database initialization completed with errors")
            logger.error(f"  Status: {health['status']}")
        logger.info("=" * 70)

        # Exit with appropriate code
        sys.exit(0 if health['status'] == 'healthy' else 1)

    except KeyboardInterrupt:
        logger.warning("\nInitialization cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n✗ Error during initialization: {e}")
        logger.debug("Exception details:", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
