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
            preference_columns = {
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(AdministratorPreference)"
                )
            }
            if "FontSizePx" not in preference_columns:
                conn.execute(
                    "ALTER TABLE AdministratorPreference "
                    "ADD COLUMN FontSizePx INTEGER NOT NULL DEFAULT 15"
                )
            if "FontColor" not in preference_columns:
                conn.execute(
                    "ALTER TABLE AdministratorPreference "
                    "ADD COLUMN FontColor TEXT NOT NULL DEFAULT '#e2e8f0'"
                )
            if "BackgroundColor" not in preference_columns:
                conn.execute(
                    "ALTER TABLE AdministratorPreference "
                    "ADD COLUMN BackgroundColor TEXT NOT NULL DEFAULT '#0b1120'"
                )
            if "PanelStyles" not in preference_columns:
                conn.execute(
                    "ALTER TABLE AdministratorPreference "
                    "ADD COLUMN PanelStyles JSON NOT NULL DEFAULT '{}'"
                )
            if "CardSuitSymbolSizePx" not in preference_columns:
                conn.execute(
                    "ALTER TABLE AdministratorPreference "
                    "ADD COLUMN CardSuitSymbolSizePx INTEGER NOT NULL DEFAULT 30 "
                    "CHECK(CardSuitSymbolSizePx BETWEEN 10 AND 35)"
                )
            self._migrate_card_suit_symbol_size_constraint(conn)
            admin_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(Administration)")
            }
            if "ExpiresAt" not in admin_columns:
                conn.execute("ALTER TABLE Administration ADD COLUMN ExpiresAt TEXT")
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
    def _migrate_card_suit_symbol_size_constraint(conn: sqlite3.Connection):
        row = conn.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type = 'table' AND name = 'AdministratorPreference'"
        ).fetchone()
        if row is None or row["sql"] is None:
            return
        normalized_sql = "".join(row["sql"].upper().split())
        if "CHECK(CARDSUITSYMBOLSIZEPXBETWEEN10AND35)" in normalized_sql:
            return

        conn.execute(
            """CREATE TABLE AdministratorPreference_new (
                AdministrationId INTEGER PRIMARY KEY,
                CardSizePx INTEGER NOT NULL DEFAULT 50
                    CHECK(CardSizePx BETWEEN 35 AND 50),
                CardSuitSymbolSizePx INTEGER NOT NULL DEFAULT 30
                    CHECK(CardSuitSymbolSizePx BETWEEN 10 AND 35),
                RobotDelayMs INTEGER NOT NULL DEFAULT 1200
                    CHECK(RobotDelayMs BETWEEN 300 AND 3000),
                SoundChoice TEXT NOT NULL DEFAULT 'CLASSIC'
                    CHECK(SoundChoice IN ('OFF', 'CLASSIC')),
                SoundVolumePercent INTEGER NOT NULL DEFAULT 35
                    CHECK(SoundVolumePercent BETWEEN 0 AND 100),
                DdsMatrixHidden INTEGER NOT NULL DEFAULT 0
                    CHECK(DdsMatrixHidden IN (0, 1)),
                DdsDisplayMode TEXT NOT NULL DEFAULT 'TRICKS'
                    CHECK(DdsDisplayMode IN ('TRICKS', 'CONTRACT_OFFSET')),
                ViewMode TEXT NOT NULL DEFAULT 'ANALYSIS'
                    CHECK(ViewMode IN ('ANALYSIS', 'HIDDEN')),
                Perspective TEXT NOT NULL DEFAULT 'SOUTH'
                    CHECK(Perspective IN ('SOUTH', 'WEST', 'NORTH', 'EAST')),
                HumanSeat TEXT NOT NULL DEFAULT 'SOUTH'
                    CHECK(HumanSeat IN ('SOUTH', 'WEST', 'NORTH', 'EAST')),
                LabelJobs JSON NOT NULL DEFAULT '{}',
                FontSizePx INTEGER NOT NULL DEFAULT 15
                    CHECK(FontSizePx BETWEEN 10 AND 24),
                FontColor TEXT NOT NULL DEFAULT '#e2e8f0',
                BackgroundColor TEXT NOT NULL DEFAULT '#0b1120',
                PanelStyles JSON NOT NULL DEFAULT '{}',
                UpdatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (AdministrationId)
                    REFERENCES Administration(Id) ON DELETE CASCADE
            )"""
        )
        conn.execute(
            """INSERT INTO AdministratorPreference_new (
                   AdministrationId, CardSizePx, CardSuitSymbolSizePx,
                   RobotDelayMs, SoundChoice, SoundVolumePercent,
                   DdsMatrixHidden, DdsDisplayMode, ViewMode, Perspective,
                   HumanSeat, LabelJobs, FontSizePx, FontColor,
                   BackgroundColor, PanelStyles, UpdatedAt
               )
               SELECT AdministrationId, CardSizePx,
                   CASE
                       WHEN CardSuitSymbolSizePx < 10 THEN 10
                       WHEN CardSuitSymbolSizePx > 35 THEN 35
                       ELSE CardSuitSymbolSizePx
                   END,
                   RobotDelayMs, SoundChoice, SoundVolumePercent,
                   DdsMatrixHidden, DdsDisplayMode, ViewMode, Perspective,
                   HumanSeat, LabelJobs, FontSizePx, FontColor,
                   BackgroundColor, PanelStyles, UpdatedAt
               FROM AdministratorPreference"""
        )
        conn.execute("DROP TABLE AdministratorPreference")
        conn.execute(
            "ALTER TABLE AdministratorPreference_new "
            "RENAME TO AdministratorPreference"
        )

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