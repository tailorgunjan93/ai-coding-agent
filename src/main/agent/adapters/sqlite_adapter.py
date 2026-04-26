"""
SQLite DB Adapter - Concrete implementation using Python's sqlite3.

This adapter implements DBInterface using Python's built-in sqlite3 module,
providing a simple file-based database for local development and testing.
"""

from typing import Any
import sqlite3
import os
from pathlib import Path

from src.main.agent.interfaces.db_interface import (
    DBInterface,
    DBType,
    QueryResult,
    DBConnectionConfig,
    TableSchema,
    MigrationInfo,
)
from src.main.agent.exceptions import QueryError, ConnectionError


class SQLiteAdapter(DBInterface):
    """
    SQLite adapter using Python's sqlite3 module.

    This adapter provides a lightweight, file-based database
    ideal for local development and testing.

    Usage:
        adapter = SQLiteAdapter()
        adapter.connect({"database": "myapp.db"})
        adapter.run_query("SELECT * FROM users")
    """

    def __init__(self):
        """Initialize SQLite adapter."""
        self._conn: sqlite3.Connection | None = None
        self._db_path: str | None = None
        self._in_transaction = False

    def connect(self, config: DBConnectionConfig | None = None) -> None:
        """
        Connect to SQLite database.

        Args:
            config: Optional config with 'database' path.

        Raises:
            ConnectionError: On connection failure.
        """
        config = config or {}
        db_path = config.get("database", ":memory:")

        # Handle relative paths
        if db_path != ":memory:" and not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)

        try:
            self._conn = sqlite3.connect(
                db_path,
                timeout=config.get("timeout", 30.0),
                check_same_thread=False,
            )
            # Enable foreign keys
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._db_path = db_path
        except sqlite3.Error as e:
            raise ConnectionError(f"Failed to connect to SQLite: {e}") from e

    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._conn is not None

    def create_table(self, schema: TableSchema) -> bool:
        """
        Create a table from schema definition.

        Args:
            schema: TableSchema defining the table.

        Returns:
            True if created successfully.

        Raises:
            QueryError: On schema creation failure.
        """
        if not self._conn:
            raise ConnectionError("Not connected to database")

        name = schema["name"]
        columns = schema["columns"]
        primary_key = schema.get("primary_key")
        foreign_keys = schema.get("foreign_keys", [])
        indexes = schema.get("indexes", [])

        # Build column definitions
        col_defs = []
        for col in columns:
            col_str = f"{col['name']} {col['data_type']}"
            if not col.get("nullable", True):
                col_str += " NOT NULL"
            if col.get("autoincrement", False):
                col_str += " AUTOINCREMENT"
            if "default" in col:
                default = col["default"]
                if isinstance(default, str):
                    col_str += f" DEFAULT '{default}'"
                else:
                    col_str += f" DEFAULT {default}"
            col_defs.append(col_str)

        # Primary key
        if primary_key:
            if isinstance(primary_key, str):
                col_defs.append(f"PRIMARY KEY ({primary_key})")
            else:
                col_defs.append(f"PRIMARY KEY ({', '.join(primary_key)})")

        # Foreign keys
        for fk in foreign_keys:
            col = fk["column"]
            ref = fk["references"]
            on_delete = fk.get("on_delete")
            fk_str = f"FOREIGN KEY ({col}) REFERENCES {ref}"
            if on_delete:
                fk_str += f" ON DELETE {on_delete}"
            col_defs.append(fk_str)

        # Build CREATE TABLE statement
        sql = f"CREATE TABLE IF NOT EXISTS {name} (\n    "
        sql += ",\n    ".join(col_defs)
        sql += "\n)"

        try:
            cursor = self._conn.cursor()
            cursor.execute(sql)

            # Create indexes
            for idx in indexes:
                idx_name = idx["name"]
                idx_cols = ", ".join(idx["columns"])
                unique = "UNIQUE " if idx.get("unique") else ""
                cursor.execute(f"CREATE {unique}INDEX IF NOT EXISTS {idx_name} ON {name} ({idx_cols})")

            self._conn.commit()
            return True

        except sqlite3.Error as e:
            self._conn.rollback()
            raise QueryError(f"Failed to create table {name}: {e}") from e

    def drop_table(self, table_name: str) -> bool:
        """Drop a table if it exists."""
        if not self._conn:
            raise ConnectionError("Not connected to database")

        try:
            cursor = self._conn.cursor()
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            self._conn.commit()
            return True
        except sqlite3.Error as e:
            raise QueryError(f"Failed to drop table {table_name}: {e}") from e

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
            QueryResult with rows and metadata.

        Raises:
            QueryError: On query execution failure.
        """
        if not self._conn:
            raise ConnectionError("Not connected to database")

        import time
        start = time.time()

        params = params or {}

        try:
            cursor = self._conn.cursor()

            # Execute query
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Get results
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                # Convert to list of dicts
                rows = [dict(zip(columns, row)) for row in rows]
            else:
                columns = []
                rows = []

            execution_time_ms = (time.time() - start) * 1000

            return QueryResult(
                rows=rows,
                columns=columns,
                row_count=len(rows),
                execution_time_ms=execution_time_ms,
                query=query,
            )

        except sqlite3.Error as e:
            raise QueryError(f"Query failed: {e}", query=query) from e

    def run_migration(self, migration_sql: str) -> MigrationInfo:
        """
        Apply a migration and record it.

        Args:
            migration_sql: SQL migration script.

        Returns:
            MigrationInfo about the applied migration.
        """
        if not self._conn:
            raise ConnectionError("Not connected to database")

        import time
        version = str(int(time.time() * 1000))

        # Create migrations table if not exists
        self.run_query("""
            CREATE TABLE IF NOT EXISTS _migrations (
                version TEXT PRIMARY KEY,
                name TEXT,
                applied_at TEXT,
                rollback_sql TEXT
            )
        """)

        try:
            # Execute migration in transaction
            self.begin_transaction()
            self._conn.executescript(migration_sql)

            # Record migration
            self.run_query(
                "INSERT INTO _migrations (version, applied_at) VALUES (?, ?)",
                {"version": version, "applied_at": time.strftime("%Y-%m-%d %H:%M:%S")}
            )

            self.commit_transaction()

            return MigrationInfo(
                version=version,
                name="migration",
                applied_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                rollback_sql=None,
                status="applied",
            )

        except sqlite3.Error as e:
            self.rollback_transaction()
            return MigrationInfo(
                version=version,
                name="migration",
                applied_at=None,
                rollback_sql=None,
                status="failed",
            )

    def get_migrations(self) -> list[MigrationInfo]:
        """Get all migrations and their status."""
        if not self._conn:
            raise ConnectionError("Not connected to database")

        try:
            # Ensure migrations table exists
            self.run_query("""
                CREATE TABLE IF NOT EXISTS _migrations (
                    version TEXT PRIMARY KEY,
                    name TEXT,
                    applied_at TEXT,
                    rollback_sql TEXT
                )
            """)

            result = self.run_query("SELECT * FROM _migrations ORDER BY version")
            migrations = []
            for row in result["rows"]:
                migrations.append(MigrationInfo(
                    version=row["version"],
                    name=row.get("name", "unknown"),
                    applied_at=row.get("applied_at"),
                    rollback_sql=row.get("rollback_sql"),
                    status="applied" if row.get("applied_at") else "pending",
                ))
            return migrations

        except sqlite3.Error:
            return []

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            self._db_path = None

    def get_db_type(self) -> DBType:
        """Return the database type."""
        return DBType.SQLITE

    def health_check(self) -> dict[str, Any]:
        """Check database health."""
        if not self._conn:
            return {"healthy": False, "error": "Not connected"}

        try:
            self.run_query("SELECT 1")
            return {
                "healthy": True,
                "database": self._db_path,
                "type": "sqlite",
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}

    def get_table_schema(self, table_name: str) -> TableSchema | None:
        """Get schema for an existing table."""
        if not self._conn:
            raise ConnectionError("Not connected to database")

        try:
            # Get table info
            cursor = self._conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = []
            primary_keys = []

            for row in cursor.fetchall():
                col = {
                    "name": row[1],
                    "data_type": row[2],
                    "nullable": not row[3],
                    "default": row[4],
                    "autoincrement": False,
                }
                columns.append(col)
                if row[5]:  # Primary key
                    primary_keys.append(row[1])

            if not columns:
                return None

            # Get foreign keys
            cursor.execute(f"PRAGMA foreign_key_list({table_name})")
            foreign_keys = []
            for row in cursor.fetchall():
                foreign_keys.append({
                    "column": row[3],
                    "references": f"{row[2]}.{row[4]}",
                    "on_delete": row[5] if len(row) > 5 else None,
                })

            # Get indexes
            cursor.execute(f"PRAGMA index_list({table_name})")
            indexes = []
            for row in cursor.fetchall():
                indexes.append({
                    "name": row[1],
                    "columns": [],
                    "unique": bool(row[2]),
                })

            return TableSchema(
                name=table_name,
                columns=columns,
                primary_key=primary_keys[0] if len(primary_keys) == 1 else primary_keys,
                foreign_keys=foreign_keys,
                indexes=indexes,
            )

        except sqlite3.Error:
            return None

    def list_tables(self) -> list[str]:
        """List all tables in the database."""
        if not self._conn:
            raise ConnectionError("Not connected to database")

        try:
            result = self.run_query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
            return [row["name"] for row in result["rows"]]
        except sqlite3.Error:
            return []

    def begin_transaction(self) -> None:
        """Begin a new transaction."""
        if not self._conn:
            raise ConnectionError("Not connected to database")
        if self._in_transaction:
            raise ConnectionError("Already in a transaction")
        self._in_transaction = True

    def commit_transaction(self) -> None:
        """Commit the current transaction."""
        if not self._conn:
            raise ConnectionError("Not connected to database")
        if not self._in_transaction:
            raise ConnectionError("Not in a transaction")
        self._conn.commit()
        self._in_transaction = False

    def rollback_transaction(self) -> None:
        """Rollback the current transaction."""
        if not self._conn:
            raise ConnectionError("Not connected to database")
        if not self._in_transaction:
            raise ConnectionError("Not in a transaction")
        self._conn.rollback()
        self._in_transaction = False
