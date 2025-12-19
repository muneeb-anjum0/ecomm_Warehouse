# src/common/db_utils.py
"""Database utilities for connecting and executing queries"""

import psycopg2
from psycopg2.extras import execute_values, execute_batch
from contextlib import contextmanager
import logging
from typing import List, Dict, Any, Optional
import os

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Handle Postgres connections and queries"""
    
    def __init__(self, 
                 host: str = None,
                 port: int = 5432,
                 database: str = None,
                 user: str = None,
                 password: str = None):
        """
        Initialize database connection parameters.
        Falls back to environment variables if not provided.
        """
        self.host = host or os.getenv('POSTGRES_HOST', 'postgres')
        self.port = port or int(os.getenv('POSTGRES_PORT', 5432))
        self.database = database or os.getenv('POSTGRES_DB', 'ecommerce_warehouse')
        self.user = user or os.getenv('POSTGRES_USER', 'airflow')
        self.password = password or os.getenv('POSTGRES_PASSWORD', 'airflow')
        self.conn = None

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            yield self.conn
        except psycopg2.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise
        finally:
            if self.conn:
                self.conn.close()

    def execute_query(self, query: str, params: tuple = None) -> List[tuple]:
        """Execute a SELECT query and return results"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    return cur.fetchall()
        except psycopg2.Error as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute INSERT/UPDATE/DELETE query"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    conn.commit()
                    return cur.rowcount
        except psycopg2.Error as e:
            logger.error(f"Update execution failed: {e}")
            raise

    def execute_batch(self, query: str, data: List[tuple], page_size: int = 100) -> int:
        """Execute batch insert/update"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    execute_batch(cur, query, data, page_size=page_size)
                    conn.commit()
                    return cur.rowcount
        except psycopg2.Error as e:
            logger.error(f"Batch execution failed: {e}")
            raise

    def insert_values(self, query: str, values: List[tuple]) -> int:
        """Insert multiple rows using execute_values"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    result = execute_values(cur, query, values)
                    conn.commit()
                    return cur.rowcount
        except psycopg2.Error as e:
            logger.error(f"Insert values failed: {e}")
            raise

    def get_scalar(self, query: str, params: tuple = None) -> Any:
        """Get a single scalar value"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    result = cur.fetchone()
                    return result[0] if result else None
        except psycopg2.Error as e:
            logger.error(f"Scalar query failed: {e}")
            raise

    def table_exists(self, schema: str, table: str) -> bool:
        """Check if a table exists"""
        query = """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = %s
            )
        """
        return self.get_scalar(query, (schema, table))

    def truncate_table(self, schema: str, table: str) -> None:
        """Truncate a table"""
        query = f"TRUNCATE TABLE {schema}.{table} CASCADE"
        self.execute_update(query)
        logger.info(f"Truncated {schema}.{table}")
