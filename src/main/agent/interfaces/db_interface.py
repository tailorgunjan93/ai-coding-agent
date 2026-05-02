"""
DB Interface - Abstract contract for database operations.

Defines the types and ABC that all database adapters must implement.
Supports SQLite, PostgreSQL, MySQL, MongoDB.
"""

from abc import ABC, abstractmethod
from typing import Any, TypedDict, NotRequired
from enum import Enum


class DBType(Enum):
    """Supported database types."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"


class QueryResult(TypedDict):
    """Result from a database query execution."""
    rows: list[dict[str, Any]]
    columns: list[str]
    row_count: int
    execution_time_ms: float


class DBConnectionConfig(TypedDict, total=False):
    """Database connection configuration."""
    host: str
    port: int
    database: str
    user: str
    password: str
    options: dict[str, Any]


class DBInterface(ABC):
    """
    Abstract base for database operations.

    Adapters (SQLite, PostgreSQL, etc.) must implement this interface
    to be used by the DB node and DB wrapper.
    """

    @abstractmethod
    def connect(self, config: DBConnectionConfig | None = None) -> None:
        """Establish database connection."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close database connection."""
        pass

    @abstractmethod
    def create_table(self, schema: str, table_name: str) -> bool:
        """
        Create a table from schema definition.

        Args:
            schema: SQL CREATE TABLE statement or schema dict.
            table_name: Name of the table.

        Returns:
            True if table created successfully.
        """
        pass

    @abstractmethod
    def run_query(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> QueryResult:
        """
        Execute a query and return results.

        Args:
            query: SQL query string.
            params: Optional query parameters.

        Returns:
            QueryResult with rows, columns, and metadata.
        """
        pass

    @abstractmethod
    def get_db_type(self) -> DBType:
        """Return the database type."""
        pass

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """
        Check database health and connectivity.

        Returns:
            Dict with 'healthy' bool and diagnostic info.
        """
        pass

    @abstractmethod
    def list_tables(self) -> list[str]:
        """Return list of table names in the database."""
        pass

    @abstractmethod
    def get_table_schema(self, table_name: str) -> dict[str, Any]:
        """
        Get schema definition for a table.

        Args:
            table_name: Name of the table.

        Returns:
            Dict with column names, types, and constraints.
        """
        pass
