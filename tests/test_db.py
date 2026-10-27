import os
import sqlite3
import tempfile
import unittest

from src.database.db_manager import DatabaseManager
from src.database.repository import Repository


class TestDatabase(unittest.TestCase):
    def setUp(self):
        DatabaseManager._instance = None
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        db_path = os.path.join(self.temp_dir.name, "bridge_test.db")
        self.db = DatabaseManager(db_path)
        self.connection = self.db.get_connection()

    def tearDown(self):
        self.connection.close()
        DatabaseManager._instance = None

    def test_legacy_label_color_check_is_removed_and_labels_are_preserved(self):
        repository = Repository()
        admin_id = repository.create_admin("color_admin", "secure password")
        folder_id = repository.create_folder(admin_id, None, "Lessons")
        case_id = repository.create_case(folder_id, "Color labels")
        board_id = repository.save_board(
            case_id,
            {
                "SOUTH": "T98.765.AKQJ.T98",
                "WEST": "765.432.432.AKQJ",
                "NORTH": "AKQJ.T98.765.432",
                "EAST": "432.AKQJ.T98.765",
            },
            "SOUTH",
            "NONE",
        )
        scenario_id = repository.create_scenario(
            board_id,
            "",
            "SOUTH",
            "1NT",
            "NONE",
            0,
            "[]",
        )
        repository.create_label(scenario_id, 1, "RED", "SA")

        db_path = self.db.db_path
        self.connection.close()
        legacy_connection = sqlite3.connect(db_path)
        legacy_connection.execute("PRAGMA foreign_keys = OFF")
        legacy_connection.execute("ALTER TABLE Label RENAME TO Label_previous")
        legacy_connection.execute(
            """CREATE TABLE Label (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                ScenarioId INTEGER NOT NULL,
                Sequence INTEGER NOT NULL,
                Color TEXT NOT NULL
                    CHECK(Color IN ('RED', 'YELLOW', 'BLUE', 'GREEN')),
                Card TEXT NOT NULL,
                FOREIGN KEY (ScenarioId)
                    REFERENCES Scenario(Id) ON DELETE CASCADE
            )"""
        )
        legacy_connection.execute(
            """INSERT INTO Label (Id, ScenarioId, Sequence, Color, Card)
               SELECT Id, ScenarioId, Sequence, Color, Card
               FROM Label_previous"""
        )
        legacy_connection.execute("DROP TABLE Label_previous")
        legacy_connection.commit()
        legacy_connection.close()

        DatabaseManager._instance = None
        DatabaseManager(db_path)
        migrated_repository = Repository()
        migrated_repository.create_label(scenario_id, 2, "ORANGE", "SK")
        migrated_repository.create_label(scenario_id, 3, "PURPLE", "SQ")

        labels = migrated_repository.get_labels_by_scenario(scenario_id)
        self.assertEqual(
            [(label.sequence, label.color) for label in labels],
            [(1, "RED"), (2, "ORANGE"), (3, "PURPLE")],
        )
        migrated_connection = DatabaseManager._instance.get_connection()
        table_sql = migrated_connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'Label'"
        ).fetchone()["sql"]
        migrated_connection.close()
        self.assertNotIn("CHECK", table_sql.upper())

    def test_admin_folder_case_and_board_cascade(self):
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO Administration (Name, Password) VALUES (?, ?)",
            ("admin1", "secret"),
        )
        admin_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO Folder (AdministrationId, Name) VALUES (?, ?)",
            (admin_id, "Root Folder"),
        )
        folder_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO CaseStudy (FolderId, Name) VALUES (?, ?)",
            (folder_id, "Opening Leads"),
        )
        case_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO BoardConfiguration (Dealer, Vulnerability) VALUES (?, ?)",
            ("SOUTH", "NONE"),
        )
        configuration_id = cursor.lastrowid
        cursor.execute(
            """INSERT INTO Board (
                CaseId, BoardConfigurationId, SouthHandPbn, WestHandPbn,
                NorthHandPbn, EastHandPbn
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                case_id,
                configuration_id,
                "T98.765.AKQJ.T98",
                "765.432.432.AKQJ",
                "AKQJ.T98.765.432",
                "432.AKQJ.T98.765",
            ),
        )
        board_id = cursor.lastrowid
        self.connection.commit()

        cursor.execute("SELECT Name FROM Folder WHERE Id = ?", (folder_id,))
        self.assertEqual(cursor.fetchone()["Name"], "Root Folder")

        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute(
                "DELETE FROM BoardConfiguration WHERE Id = ?",
                (configuration_id,),
            )

        cursor.execute("DELETE FROM Administration WHERE Id = ?", (admin_id,))
        self.connection.commit()

        for table, row_id in (
            ("Folder", folder_id),
            ("CaseStudy", case_id),
            ("Board", board_id),
        ):
            with self.subTest(table=table):
                cursor.execute(f"SELECT 1 FROM {table} WHERE Id = ?", (row_id,))
                self.assertIsNone(cursor.fetchone())
        cursor.execute(
            "SELECT 1 FROM BoardConfiguration WHERE Id = ?",
            (configuration_id,),
        )
        self.assertIsNotNone(cursor.fetchone())

    def test_schema_enforces_enum_and_foreign_key_constraints(self):
        cursor = self.connection.cursor()
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO BoardConfiguration (Dealer, Vulnerability) VALUES (?, ?)",
                ("INVALID", "NONE"),
            )
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO Folder (AdministrationId, Name) VALUES (?, ?)",
                (9999, "Orphan Folder"),
            )

    def test_existing_scenario_table_is_migrated_with_information_column(self):
        legacy_path = os.path.join(self.temp_dir.name, "legacy_scenario.db")
        legacy = sqlite3.connect(legacy_path)
        legacy.execute(
            """CREATE TABLE Scenario (
                Id INTEGER PRIMARY KEY,
                BoardId INTEGER NOT NULL,
                BiddingRoute TEXT NOT NULL,
                Declarer TEXT NOT NULL,
                Contract TEXT NOT NULL,
                RiskStatus TEXT NOT NULL,
                IsTargeted INTEGER NOT NULL,
                TargetedSequence JSON NULL
            )"""
        )
        legacy.commit()
        legacy.close()

        DatabaseManager._instance = None
        migrated = DatabaseManager(legacy_path).get_connection()
        columns = {
            row["name"] for row in migrated.execute("PRAGMA table_info(Scenario)")
        }
        migrated.close()
        self.assertIn("Information", columns)

    def test_existing_test_result_table_is_migrated_with_student_link(self):
        legacy_path = os.path.join(self.temp_dir.name, "legacy_results.db")
        legacy = sqlite3.connect(legacy_path)
        legacy.execute(
            """CREATE TABLE Test_Result (
                Id INTEGER PRIMARY KEY AUTOINCREMENT,
                TestId INTEGER NOT NULL,
                ApplicantName TEXT NOT NULL,
                Contracts JSON NOT NULL,
                Score INTEGER NOT NULL,
                SubmittedAt DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        legacy.execute(
            """INSERT INTO Test_Result (TestId, ApplicantName, Contracts, Score)
               VALUES (1, 'Legacy student', '[]', 0)"""
        )
        legacy.commit()
        legacy.close()

        DatabaseManager._instance = None
        migrated = DatabaseManager(legacy_path).get_connection()
        columns = {
            row["name"] for row in migrated.execute("PRAGMA table_info(Test_Result)")
        }
        result = migrated.execute(
            "SELECT ApplicantName, StudentId FROM Test_Result"
        ).fetchone()
        migrated.close()
        self.assertIn("StudentId", columns)
        self.assertEqual(result["ApplicantName"], "Legacy student")
        self.assertIsNone(result["StudentId"])

    def test_scenario_information_persists_and_asset_duplication_copies_descendants(self):
        repository = Repository()
        admin_id = repository.create_admin("duplicate_admin", "secure password")
        root_id = repository.create_folder(admin_id, None, "Lessons")
        child_id = repository.create_folder(admin_id, root_id, "Opening")
        case_id = repository.create_case(child_id, "Signals")
        board_id = repository.save_board(
            case_id,
            {
                "SOUTH": "T98.765.AKQJ.T98",
                "WEST": "765.432.432.AKQJ",
                "NORTH": "AKQJ.T98.765.432",
                "EAST": "432.AKQJ.T98.765",
            },
            "SOUTH",
            "NONE",
            description="Board One",
        )
        scenario_id = repository.create_scenario(
            board_id,
            "1NT PASS PASS PASS",
            "SOUTH",
            "1NT",
            "NONE",
            0,
            "[]",
            name="Opening lead",
            information="Lead the king from the sequence.",
        )
        repository.create_label(scenario_id, 1, "RED", "SA")
        repository.update_scenario(
            scenario_id,
            "1NT PASS PASS PASS",
            "SOUTH",
            "1NT",
            "NONE",
            0,
            "[]",
            "Updated scenario notes.",
        )
        self.assertEqual(
            repository.get_scenario_by_id(scenario_id).information,
            "Updated scenario notes.",
        )

        copied_root_id = repository.duplicate_asset(admin_id, "folder", root_id)
        copied_root = repository.get_folder_by_id(copied_root_id)
        self.assertEqual(copied_root.name, "Lessons (Copy)")
        copied_child = repository.get_folders_by_admin(admin_id)
        copied_child = next(
            folder
            for folder in copied_child
            if folder.parent_folder_id == copied_root_id
        )
        copied_case = repository.get_cases_by_folder(copied_child.id)[0]
        copied_board = repository.get_boards_by_case(copied_case.id)[0]
        copied_scenario = repository.get_scenarios_by_board(copied_board.id)[0]

        self.assertEqual(copied_scenario.information, "Updated scenario notes.")
        self.assertEqual(
            [
                (label.sequence, label.color, label.card)
                for label in repository.get_labels_by_scenario(copied_scenario.id)
            ],
            [(1, "RED", "SA")],
        )

    def test_move_asset_reparents_all_asset_types_and_rejects_cycles_or_foreign_targets(self):
        repository = Repository()
        admin_id = repository.create_admin("move_admin", "secure password")
        first_folder_id = repository.create_folder(admin_id, None, "First")
        second_folder_id = repository.create_folder(admin_id, None, "Second")
        child_folder_id = repository.create_folder(
            admin_id,
            first_folder_id,
            "Nested",
        )
        first_case_id = repository.create_case(first_folder_id, "Opening")
        second_case_id = repository.create_case(second_folder_id, "Defense")
        hands = {
            "SOUTH": "T98.765.AKQJ.T98",
            "WEST": "765.432.432.AKQJ",
            "NORTH": "AKQJ.T98.765.432",
            "EAST": "432.AKQJ.T98.765",
        }
        first_board_id = repository.save_board(
            first_case_id,
            hands,
            "SOUTH",
            "NONE",
        )
        second_board_id = repository.save_board(
            second_case_id,
            hands,
            "SOUTH",
            "NONE",
        )
        scenario_id = repository.create_scenario(
            first_board_id,
            "1NT PASS PASS PASS",
            "SOUTH",
            "1NT",
            "NONE",
            0,
            "[]",
        )

        self.assertTrue(
            repository.move_asset(
                admin_id,
                "folder",
                child_folder_id,
                second_folder_id,
            )
        )
        self.assertEqual(
            repository.get_folder_by_id(child_folder_id).parent_folder_id,
            second_folder_id,
        )
        self.assertTrue(
            repository.move_asset(
                admin_id,
                "case",
                first_case_id,
                second_folder_id,
            )
        )
        self.assertEqual(
            repository.get_case_by_id(first_case_id).folder_id,
            second_folder_id,
        )
        self.assertTrue(
            repository.move_asset(
                admin_id,
                "board",
                first_board_id,
                second_case_id,
            )
        )
        self.assertEqual(
            repository.get_board_by_id(first_board_id).case_id,
            second_case_id,
        )
        self.assertTrue(
            repository.move_asset(
                admin_id,
                "scenario",
                scenario_id,
                second_board_id,
            )
        )
        self.assertEqual(
            repository.get_scenario_by_id(scenario_id).board_id,
            second_board_id,
        )

        with self.assertRaisesRegex(ValueError, "descendant"):
            repository.move_asset(
                admin_id,
                "folder",
                second_folder_id,
                child_folder_id,
            )
        self.assertEqual(
            repository.get_folder_by_id(second_folder_id).parent_folder_id,
            None,
        )

        other_admin_id = repository.create_admin("other_move_admin", "secure password")
        foreign_folder_id = repository.create_folder(
            other_admin_id,
            None,
            "Private",
        )
        with self.assertRaisesRegex(LookupError, "Destination folder"):
            repository.move_asset(
                admin_id,
                "case",
                first_case_id,
                foreign_folder_id,
            )
        self.assertEqual(
            repository.get_case_by_id(first_case_id).folder_id,
            second_folder_id,
        )

    def test_repository_loads_board_configuration_scenario_and_labels_by_id(self):
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO Administration (Name, Password) VALUES (?, ?)",
            ("admin", "secret"),
        )
        cursor.execute(
            "INSERT INTO Folder (AdministrationId, Name) VALUES (?, ?)",
            (cursor.lastrowid, "Lessons"),
        )
        folder_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO CaseStudy (FolderId, Name) VALUES (?, ?)",
            (folder_id, "Opening lead"),
        )
        case_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO BoardConfiguration (Dealer, Vulnerability) VALUES (?, ?)",
            ("SOUTH", "NS"),
        )
        configuration_id = cursor.lastrowid
        cursor.execute(
            """INSERT INTO Board (
                CaseId, BoardConfigurationId, SouthHandPbn, WestHandPbn,
                NorthHandPbn, EastHandPbn
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                case_id,
                configuration_id,
                "T98.765.AKQJ.T98",
                "765.432.432.AKQJ",
                "AKQJ.T98.765.432",
                "432.AKQJ.T98.765",
            ),
        )
        board_id = cursor.lastrowid
        cursor.execute(
            """INSERT INTO Scenario (
                BoardId, BiddingRoute, Declarer, Contract, RiskStatus,
                IsTargeted, TargetedSequence
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (board_id, "1NT PASS PASS PASS", "SOUTH", "1NT", "NONE", 0, None),
        )
        scenario_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO Label (ScenarioId, Sequence, Color, Card) VALUES (?, ?, ?, ?)",
            (scenario_id, 1, "RED", "AH"),
        )
        self.connection.commit()

        repository = Repository()
        board = repository.get_board_by_id(board_id)
        configuration = repository.get_board_configuration(configuration_id)
        scenario = repository.get_scenario_by_id(scenario_id)
        labels = repository.get_labels_by_scenario(scenario_id)

        self.assertEqual(board.id, board_id)
        self.assertEqual(board.board_configuration_id, configuration_id)
        self.assertEqual(configuration.dealer, "SOUTH")
        self.assertEqual(configuration.vulnerability, "NS")
        self.assertEqual(scenario.board_id, board_id)
        self.assertEqual(scenario.contract, "1NT")
        self.assertEqual(scenario.name, "")
        repository.rename_scenario(scenario_id, "Opening lead")
        self.assertEqual(
            repository.get_scenario_by_id(scenario_id).name,
            "Opening lead",
        )
        self.assertEqual([(label.sequence, label.card) for label in labels], [(1, "AH")])

    def test_repository_asset_crud_and_cascading_deletes(self):
        repository = Repository()
        admin_id = repository.create_admin("manager", "secure password")
        folder_id = repository.create_folder(admin_id, None, "Original folder")
        case_id = repository.create_case(folder_id, "Original case")
        board_id = repository.save_board(
            case_id,
            {
                "SOUTH": "T98.765.AKQJ.T98",
                "WEST": "765.432.432.AKQJ",
                "NORTH": "AKQJ.T98.765.432",
                "EAST": "432.AKQJ.T98.765",
            },
            "SOUTH",
            "NONE",
        )
        scenario_id = repository.create_scenario(
            board_id,
            "1NT PASS PASS PASS",
            "SOUTH",
            "1NT",
            "NONE",
            0,
            None,
        )
        repository.create_label(scenario_id, 1, "RED", "AH")

        repository.rename_folder(folder_id, "Renamed folder")
        repository.rename_case(case_id, "Renamed case")
        self.assertEqual(repository.get_folder_by_id(folder_id).name, "Renamed folder")
        self.assertEqual(repository.get_case_by_id(case_id).name, "Renamed case")

        repository.delete_scenario(scenario_id)
        self.assertIsNone(repository.get_scenario_by_id(scenario_id))
        self.assertEqual(repository.get_labels_by_scenario(scenario_id), [])
        repository.delete_board(board_id)
        self.assertIsNone(repository.get_board_by_id(board_id))
        repository.delete_case(case_id)
        self.assertIsNone(repository.get_case_by_id(case_id))
        repository.delete_folder(folder_id)
        self.assertIsNone(repository.get_folder_by_id(folder_id))

    def test_updating_a_board_does_not_change_a_shared_configuration(self):
        repository = Repository()
        admin_id = repository.create_admin("manager", "secure password")
        folder_id = repository.create_folder(admin_id, None, "Lessons")
        case_id = repository.create_case(folder_id, "Cases")
        configuration_id = repository.create_board_configuration("SOUTH", "NONE")
        hands = {
            "SOUTH": "T98.765.AKQJ.T98",
            "WEST": "765.432.432.AKQJ",
            "NORTH": "AKQJ.T98.765.432",
            "EAST": "432.AKQJ.T98.765",
        }
        first_board_id = repository.create_board(
            case_id,
            configuration_id,
            hands["SOUTH"],
            hands["WEST"],
            hands["NORTH"],
            hands["EAST"],
        )
        second_board_id = repository.create_board(
            case_id,
            configuration_id,
            hands["SOUTH"],
            hands["WEST"],
            hands["NORTH"],
            hands["EAST"],
        )

        repository.save_board(
            case_id,
            hands,
            "WEST",
            "EW",
            board_id=first_board_id,
        )

        updated_first = repository.get_board_by_id(first_board_id)
        unchanged_second = repository.get_board_by_id(second_board_id)
        updated_configuration = repository.get_board_configuration(
            updated_first.board_configuration_id
        )
        original_configuration = repository.get_board_configuration(
            unchanged_second.board_configuration_id
        )
        self.assertNotEqual(
            updated_first.board_configuration_id,
            unchanged_second.board_configuration_id,
        )
        self.assertEqual(updated_configuration.dealer, "WEST")
        self.assertEqual(original_configuration.dealer, "SOUTH")


if __name__ == "__main__":
    unittest.main()
