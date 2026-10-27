# src/database/db_manager.py
import sqlite3
import os
from typing import Optional


class DatabaseManager:
    _instance: Optional['DatabaseManager'] = None

    def __new__(cls, db_path: str = "bridge_tool.db"):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.db_path = db_path
            cls._instance._initialize_database()
        return cls._instance

    def __init__(self, db_path: str = "bridge_tool.db"):
        # Initialize the singleton only once.
        pass

    def get_connection(self) -> sqlite3.Connection:
        """Open a SQLite connection with foreign-key enforcement enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Allow query results to be accessed by column name.
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _initialize_database(self):
        """Initialize the database schema from the project-root schema.sql file."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.abspath(os.path.join(current_dir, "../../schema.sql"))

        if not os.path.exists(schema_path):
            print(f"[Database warning] schema.sql was not found: {schema_path}")
            return

        conn = self.get_connection()
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_script = f.read()
            conn.executescript(schema_script)
            self._migrate_label_color_constraint(conn)
            scenario_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(Scenario)")
            }
            if "Name" not in scenario_columns:
                conn.execute(
                    "ALTER TABLE Scenario ADD COLUMN Name TEXT NOT NULL DEFAULT ''"
                )
            if "Information" not in scenario_columns:
                conn.execute("ALTER TABLE Scenario ADD COLUMN Information TEXT NULL")
            result_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(Test_Result)")
            }
            if "StudentId" not in result_columns:
                conn.execute(
                    "ALTER TABLE Test_Result ADD COLUMN StudentId "
                    "INTEGER NULL REFERENCES Student(Id) ON DELETE RESTRICT"
                )
            conn.commit()
            print(f"[Database] Initialized successfully at {os.path.abspath(self.db_path)}")
        except Exception as e:
            print(f"[Database error] Schema initialization failed: {e}")
            conn.rollback()
        finally:
            conn.close()

    @staticmethod
    def _migrate_label_color_constraint(conn: sqlite3.Connection):
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'Label'"
        ).fetchone()
        if row is None or row["sql"] is None:
            return
        normalized_sql = "".join(row["sql"].upper().split())
        if "CHECK(COLORIN(" not in normalized_sql:
            return

        conn.execute(
            """CREATE TABLE Label_new (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                ScenarioId INTEGER NOT NULL,
                Sequence INTEGER NOT NULL,
                Color TEXT NOT NULL,
                Card TEXT NOT NULL,
                FOREIGN KEY (ScenarioId) REFERENCES Scenario(Id) ON DELETE CASCADE
            )"""
        )
        conn.execute(
            """INSERT INTO Label_new (Id, ScenarioId, Sequence, Color, Card)
               SELECT Id, ScenarioId, Sequence, Color, Card FROM Label"""
        )
        conn.execute("DROP TABLE Label")
        conn.execute("ALTER TABLE Label_new RENAME TO Label")