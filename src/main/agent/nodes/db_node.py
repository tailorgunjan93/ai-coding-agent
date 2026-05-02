"""
DB Node - Generates database schema and migration commands.

Produces SQL schema definitions and migration commands
based on generated code artifacts.
"""

from typing import Any
import re
import logging

from src.main.agent.nodes.base_node import BaseNode
from src.main.agent.interfaces.db_interface import DBInterface
from src.main.agent.models.agent_state import AgentState

logger = logging.getLogger(__name__)


class DBNode(BaseNode):
    """
    Node responsible for database operation command generation.

    Generates:
    - SQL schema from Pydantic/SQLAlchemy models in code
    - Migration commands (alembic, django, raw SQL)
    - Database setup commands

    Dependencies:
        - model (needs generated code with DB models)
    """

    def __init__(
        self,
        db_wrapper: DBInterface | None = None,
        migrations_dir: str = "./migrations",
        max_retries: int = 3,
    ):
        super().__init__(max_retries=max_retries, timeout_seconds=120)
        self._db = db_wrapper
        self._migrations_dir = migrations_dir

    @property
    def node_name(self) -> str:
        return "db"

    @property
    def description(self) -> str:
        return "Generates database schema and migration commands"

    def get_required_dependencies(self) -> list[str]:
        return ["model"]

    async def run(self, state: AgentState) -> AgentState:
        """
        Generate database schema and migration commands.

        Steps:
        1. Scan generated code for model definitions
        2. Extract field types and relationships
        3. Generate SQL CREATE TABLE statements
        4. Produce migration commands
        """
        artifacts = state.get("artifacts", [])
        code_files = [a for a in artifacts if a.get("type") == "file" and a.get("category") != "test"]

        if not code_files:
            state["db_config"] = {
                "status": "skipped",
                "reason": "No code files to analyze",
                "commands": [],
            }
            return state

        # Scan for model definitions
        models_found = []
        for artifact in code_files:
            content = artifact.get("content", "")
            models = self._extract_models(content, artifact.get("path", ""))
            models_found.extend(models)

        if not models_found:
            state["db_config"] = {
                "status": "skipped",
                "reason": "No database models found in generated code",
                "commands": [],
            }
            return state

        # Generate SQL schema
        sql_schema = self._generate_sql(models_found)

        # Add schema as artifact
        state["artifacts"].append({
            "type": "file",
            "path": f"{self._migrations_dir}/001_initial_schema.sql",
            "content": sql_schema,
            "created_at": state.get("updated_at", ""),
            "category": "migration",
        })

        # Generate commands
        commands = [
            {
                "tool": "sqlite",
                "command": f"sqlite3 app.db < {self._migrations_dir}/001_initial_schema.sql",
                "description": "Apply schema to SQLite database",
            },
            {
                "tool": "alembic",
                "command": "alembic init migrations && alembic revision --autogenerate -m 'initial'",
                "description": "Initialize Alembic migrations (if using SQLAlchemy)",
            },
            {
                "tool": "verify",
                "command": "sqlite3 app.db '.tables'",
                "description": "Verify tables were created",
            },
        ]

        state["db_config"] = {
            "status": "generated",
            "models_found": len(models_found),
            "schema_file": f"{self._migrations_dir}/001_initial_schema.sql",
            "commands": commands,
        }

        logger.info(f"Generated SQL schema for {len(models_found)} models")
        return state

    def _extract_models(self, code: str, file_path: str) -> list[dict[str, Any]]:
        """Extract model definitions from Python code."""
        models = []

        # Look for Pydantic BaseModel or SQLAlchemy DeclarativeBase classes
        class_pattern = r"class\s+(\w+)\s*\(\s*(BaseModel|Base|DeclarativeBase|db\.Model)\s*\):"
        field_pattern = r"(\w+)\s*[:=]\s*(.*?)(?:\n|$)"

        for match in re.finditer(class_pattern, code):
            class_name = match.group(1)
            parent = match.group(2)

            # Find the class body (simple heuristic: lines after class until next class/EOF)
            start = match.end()
            end = len(code)
            next_class = re.search(r"\nclass\s+", code[start:])
            if next_class:
                end = start + next_class.start()

            class_body = code[start:end]

            # Extract fields
            fields = []
            for field_match in re.finditer(r"(\w+)\s*:\s*(str|int|float|bool|datetime|Optional|list|dict)", class_body, re.IGNORECASE):
                fields.append({
                    "name": field_match.group(1),
                    "type": field_match.group(2),
                })

            if fields:
                models.append({
                    "name": class_name,
                    "parent": parent,
                    "fields": fields,
                    "file": file_path,
                })

        return models

    def _generate_sql(self, models: list[dict[str, Any]]) -> str:
        """Generate SQL CREATE TABLE statements from model definitions."""
        type_map = {
            "str": "TEXT",
            "int": "INTEGER",
            "float": "REAL",
            "bool": "INTEGER",  # SQLite boolean
            "datetime": "TIMESTAMP",
            "list": "TEXT",  # JSON serialized
            "dict": "TEXT",  # JSON serialized
            "optional": "TEXT",
        }

        sql_parts = [
            "-- Auto-generated schema by AI Coding Agent",
            "-- Run: sqlite3 app.db < this_file.sql\n",
        ]

        for model in models:
            table_name = self._to_snake_case(model["name"])
            columns = ["    id INTEGER PRIMARY KEY AUTOINCREMENT"]

            for field in model["fields"]:
                if field["name"] == "id":
                    continue
                sql_type = type_map.get(field["type"].lower(), "TEXT")
                columns.append(f"    {field['name']} {sql_type}")

            columns.append("    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            columns.append("    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

            sql_parts.append(
                f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
                + ",\n".join(columns)
                + "\n);\n"
            )

        return "\n".join(sql_parts)

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert CamelCase to snake_case."""
        result = re.sub(r"([A-Z])", r"_\1", name).lower().lstrip("_")
        return result
