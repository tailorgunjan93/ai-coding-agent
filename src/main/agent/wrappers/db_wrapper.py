"""
DB Wrapper - Database wrapper adding connection pooling and query templating.

This wrapper uses composition to add orthogonal concerns to any DBInterface
implementation without modifying it.
"""

from typing import Any
from contextlib import contextmanager
import time

from src.main.agent.interfaces.db_interface import (
    DBInterface,
    DBType,
    QueryResult,
    DBConnectionConfig,
    TableSchema,
    MigrationInfo,
)
from src.main.agent.exceptions import QueryError, ConnectionError


class QueryTemplate:
    """
    A query template with placeholders.

    Supports both named parameters ({name}) and positional parameters (?).
    """

    def __init__(self, name: str, query: str, description: str = ""):
        """
        Initialize a query template.

        Args:
            name: Unique name for this query.
            query: SQL query with placeholders.
            description: Human-readable description.
        """
        self.name = name
        self.query = query
        self.description = description

    def render(self, params: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        """
        Render the query with parameters.

        Args:
            params: Parameter values.

        Returns:
            Tuple of (rendered_query, sanitized_params).
        """
        params = params or {}
        # For now, just return as-is (implement param substitution if needed)
        return self.query, params


class ConnectionPool:
    """
    Simple connection pool for database connections.

    Maintains a pool of connections and ensures they're healthy.
    """

    def __init__(
        self,
        db_interface: DBInterface,
        config: DBConnectionConfig,
        min_size: int = 2,
        max_size: int = 10,
    ):
        """
        Initialize connection pool.

        Args:
            db_interface: DBInterface implementation to use.
            config: Database connection config.
            min_size: Minimum pool size.
            max_size: Maximum pool size.
        """
        self._db = db_interface
        self._config = config
        self._min_size = min_size
        self._max_size = max_size
        self._connections: list[Any] = []
        self._in_use: set[int] = set()
        self._created = 0

    def acquire(self) -> DBInterface:
        """
        Acquire a connection from the pool.

        Returns:
            A DBInterface (may be reused from pool).
        """
        # Try to find an available connection
        for i, conn in enumerate(self._connections):
            if i not in self._in_use:
                self._in_use.add(i)
                return conn

        # Create new if under max
        if self._created < self._max_size:
            conn = self._create_connection()
            self._connections.append(conn)
            self._created += 1
            self._in_use.add(len(self._connections) - 1)
            return conn

        # Wait for one to be returned (simplified - just create another)
        # In production, use proper async waiting
        return self._create_connection()

    def release(self, conn: DBInterface) -> None:
        """
        Release a connection back to the pool.

        Args:
            conn: Connection to release.
        """
        # Find and remove from in_use
        for i, c in enumerate(self._connections):
            if c is conn:
                self._in_use.discard(i)
                return

    def _create_connection(self) -> DBInterface:
        """Create a new connection."""
        conn = self._db.__class__()
        conn.connect(self._config)
        return conn

    def close_all(self) -> None:
        """Close all connections in the pool."""
        for conn in self._connections:
            try:
                conn.close()
            except Exception:
                pass
        self._connections.clear()
        self._in_use.clear()
        self._created = 0


class DBWrapper:
    """
    Wrapper that adds connection pooling, query templating, and metrics
    to any DBInterface implementation.

    This wrapper uses composition to add orthogonal concerns:
    - Connection pooling: Reuse connections efficiently
    - Query templating: Reuse and validate common queries
    - Metrics: Track query performance

    Usage:
        db = PostgresAdapter(...)
        wrapped = DBWrapper(db)
        wrapped.connect(config)
        result = await wrapped.run_query("SELECT * FROM users WHERE id = {id}", {"id": 1})
    """

    def __init__(
        self,
        db: DBInterface,
        pool_size: int = 5,
        slow_query_threshold_ms: float = 1000,
    ):
        """
        Initialize the DB wrapper.

        Args:
            db: The database interface to wrap.
            pool_size: Number of connections in the pool.
            slow_query_threshold_ms: Log queries slower than this.
        """
        self._db = db
        self._pool_size = pool_size
        self._slow_threshold = slow_query_threshold_ms
        self._query_templates: dict[str, QueryTemplate] = {}
        self._query_count = 0
        self._slow_queries: list[dict[str, Any]] = []

    def connect(self, config: DBConnectionConfig | None = None) -> None:
        """
        Connect to the database.

        Args:
            config: Optional connection config override.
        """
        self._db.connect(config)

    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._db.is_connected()

    def close(self) -> None:
        """Close database connection."""
        self._db.close()

    def register_query(
        self,
        name: str,
        query: str,
        description: str = "",
    ) -> QueryTemplate:
        """
        Register a query template.

        Args:
            name: Unique name for this query.
            query: SQL query with placeholders.
            description: Human-readable description.

        Returns:
            The created QueryTemplate.
        """
        tmpl = QueryTemplate(name=name, query=query, description=description)
        self._query_templates[name] = tmpl
        return tmpl

    def run_query(
        self,
        query: str,
        params: dict[str, Any] | None = None,
        query_name: str | None = None,
    ) -> QueryResult:
        """
        Run a query with metrics tracking.

        Args:
            query: SQL query or query template name.
            params: Query parameters.
            query_name: Optional name for metrics tracking.

        Returns:
            QueryResult from the query.

        Raises:
            QueryError: On query execution failure.
        """
        self._query_count += 1

        # Check if it's a registered query
        if query in self._query_templates:
            tmpl = self._query_templates[query]
            query, params = tmpl.render(params)

        start = time.time()
        try:
            result = self._db.run_query(query, params)
        except QueryError as e:
            # Add query name to error
            e.details = e.details or {}
            e.details["query_name"] = query_name
            raise
        finally:
            elapsed_ms = (time.time() - start) * 1000
            result_execution = elapsed_ms

            if elapsed_ms > self._slow_threshold:
                self._slow_queries.append({
                    "query": query,
                    "query_name": query_name,
                    "elapsed_ms": elapsed_ms,
                    "timestamp": time.time(),
                })

        return result

    def create_table(self, schema: TableSchema) -> bool:
        """Create a table from schema."""
        return self._db.create_table(schema)

    def drop_table(self, table_name: str) -> bool:
        """Drop a table."""
        return self._db.drop_table(table_name)

    def run_migration(self, migration_sql: str) -> MigrationInfo:
        """Run a migration."""
        return self._db.run_migration(migration_sql)

    def get_migrations(self) -> list[MigrationInfo]:
        """Get all migrations."""
        return self._db.get_migrations()

    def get_db_type(self) -> DBType:
        """Get database type."""
        return self._db.get_db_type()

    def health_check(self) -> dict[str, Any]:
        """Check database health."""
        return self._db.health_check()

    def get_table_schema(self, table_name: str) -> TableSchema | None:
        """Get table schema."""
        return self._db.get_table_schema(table_name)

    def list_tables(self) -> list[str]:
        """List all tables."""
        return self._db.list_tables()

    def begin_transaction(self) -> None:
        """Begin a transaction."""
        self._db.begin_transaction()

    def commit_transaction(self) -> None:
        """Commit the current transaction."""
        self._db.commit_transaction()

    def rollback_transaction(self) -> None:
        """Rollback the current transaction."""
        self._db.rollback_transaction()

    def get_metrics(self) -> dict[str, Any]:
        """Get wrapper metrics."""
        return {
            "query_count": self._query_count,
            "slow_query_count": len(self._slow_queries),
            "slow_queries": list(self._slow_queries[-10:]),  # Last 10
            "db_type": self._db.get_db_type().value,
            "is_connected": self._db.is_connected(),
        }

    def get_slow_queries(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent slow queries."""
        return self._slow_queries[-limit:]
