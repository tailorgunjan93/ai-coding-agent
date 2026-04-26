"""
DB Interface - Abstract contract for database operations.

This interface defines the contract that all database providers must implement,
enabling interchangeable database backends (SQLite, PostgreSQL, MySQL, MongoDB).
"""

from abc import ABC, abstractmethod
from typing import Any, TypedDict
from enum import Enum


class DBType(Enum):
    """Supported database types."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    SQLSERVER = "sqlserver"


class TableSchema(TypedDict):
    """Schema definition for table creation."""
    name: str
    columns: list["ColumnDefinition"]
    primary_key: str | list[str]
    foreign_keys: list["ForeignKeyDefinition"]
    indexes: list["IndexDefinition"]


class ColumnDefinition(TypedDict):
    """Column definition within a table schema."""
    name: str
    data_type: str
    nullable: bool
    default: Any | None
    autoincrement: bool


class ForeignKeyDefinition(TypedDict):
    """Foreign key constraint definition."""
    column: str
    references: str  # "table.column"
    on_delete: str | None  # CASCADE, SET NULL, etc.


class IndexDefinition(TypedDict):
    """Index definition."""
    name: str
    columns: list[str]
    unique: bool


class QueryResult(TypedDict):
    """Result from a database query execution."""
    rows: list[dict[str, Any]]
    columns: list[str]
    row_count: int
    execution_time_ms: float
    query: str | None  # For debugging


class DBConnectionConfig(TypedDict):
    """Configuration for database connection."""
    host: str | None
    port: int | None
    database: str
    user: str | None
    password: str | None
    connection_string: str | None  # Alternative to individual params
    timeout: int | None
    ssl: bool | None


class MigrationInfo(TypedDict):
    """Information about a database migration."""
    version: str
    name: str
    applied_at: str | None
    rollback_sql: str | None
    status: str  # "applied", "pending", "failed"


class DBInterface(ABC):
    """
    Abstract base for database operations.

    This interface ensures all database implementations provide a consistent contract
    for connection management, query execution, and schema operations.

    Implementations should handle connection pooling internally.
    """

    @abstractmethod
    def connect(self, config: DBConnectionConfig | None = None) -> None:
        """
        Establish database connection.

        Args:
            config: Optional connection configuration. Uses default if None.

        Raises:
            ConnectionError: On connection failure.
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if database connection is active.

        Returns:
            True if connected, False otherwise.
        """
        pass

    @abstractmethod
    def create_table(self, schema: TableSchema) -> bool:
        """
        Create a table from schema definition.

        Args:
            schema: TableSchema defining the table structure.

        Returns:
            True if created successfully.

        Raises:
            QueryError: On schema creation failure.
        """
        pass

    @abstractmethod
    def drop_table(self, table_name: str) -> bool:
        """
        Drop a table if it exists.

        Args:
            table_name: Name of the table to drop.

        Returns:
            True if dropped successfully.

        Raises:
            QueryError: On table drop failure.
        """
        pass

    @abstractmethod
    def run_query(
        self,
        query: str,
        params: dict[str, Any] | None = None
    ) -> QueryResult:
        """
        Execute a query and return results.

        Args:
            query: SQL query string (or MongoDB equivalent).
            params: Optional query parameters for parameterized queries.

        Returns:
            QueryResult with rows and metadata.

        Raises:
            QueryError: On query execution failure.
        """
        pass

    @abstractmethod
    def run_migration(self, migration_sql: str) -> MigrationInfo:
        """
        Apply a migration and record it.

        Args:
            migration_sql: SQL migration script.

        Returns:
            MigrationInfo about the applied migration.

        Raises:
            QueryError: On migration failure.
        """
        pass

    @abstractmethod
    def get_migrations(self) -> list[MigrationInfo]:
        """
        Get all migrations and their status.

        Returns:
            List of MigrationInfo sorted by version.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Close database connection and cleanup resources.
        """
        pass

    @abstractmethod
    def get_db_type(self) -> DBType:
        """
        Return the database type.

        Returns:
            DBType enum value identifying the database.
        """
        pass

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """
        Check database health and connectivity.

        Returns:
            Dict with health status, latency_ms, and other metrics.
        """
        pass

    @abstractmethod
    def get_table_schema(self, table_name: str) -> TableSchema | None:
        """
        Retrieve schema for an existing table.

        Args:
            table_name: Name of the table.

        Returns:
            TableSchema if table exists, None otherwise.
        """
        pass

    @abstractmethod
    def list_tables(self) -> list[str]:
        """
        List all tables in the database.

        Returns:
            List of table names.
        """
        pass

    @abstractmethod
    def begin_transaction(self) -> None:
        """
        Begin a new database transaction.

        Raises:
            ConnectionError: If already in a transaction or not connected.
        """
        pass

    @abstractmethod
    def commit_transaction(self) -> None:
        """
        Commit the current transaction.

        Raises:
            ConnectionError: If not in a transaction.
        """
        pass

    @abstractmethod
    def rollback_transaction(self) -> None:
        """
        Rollback the current transaction.

        Raises:
            ConnectionError: If not in a transaction.
        """
        pass
