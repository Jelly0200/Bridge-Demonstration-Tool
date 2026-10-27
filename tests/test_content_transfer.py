import copy
import os
import tempfile
import unittest

from src.core.content_transfer import ContentTransferService
from src.database.db_manager import DatabaseManager
from src.database.repository import Repository
from src.security.passwords import hash_password


class TestContentTransfer(unittest.TestCase):
    def setUp(self):
        DatabaseManager._instance = None
        self.temp_dir = tempfile.TemporaryDirectory()
        DatabaseManager(os.path.join(self.temp_dir.name, "transfer.db"))
        self.repository = Repository()
        self.service = ContentTransferService(self.repository.db)
        self.source_admin_id = self.repository.create_admin(
            "source_admin",
            "source administrator password",
        )
        self.target_admin_id = self.repository.create_admin(
            "target_admin",
            "target administrator password",
        )
        self.repository.create_folder(
            self.target_admin_id,
            None,
            "Private other-admin folder",
        )

        root_id = self.repository.create_folder(
            self.source_admin_id,
            None,
            "Teaching materials",
        )
        self.child_folder_id = self.repository.create_folder(
            self.source_admin_id,
            root_id,
            "Imported lesson",
        )
        case_id = self.repository.create_case(self.child_folder_id, "Opening")
        board_id = self.repository.save_board(
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
        self.scenario_id = self.repository.create_scenario(
            board_id,
            "1C, P, 1H, P, 4H, P, P, P",
            "SOUTH",
            "4H",
            "NONE",
            0,
            "[]",
            name="Opening lead",
            information="Lead the singleton spade.",
        )
        self.repository.create_label(self.scenario_id, 1, "RED", "SA")
        self.test_id = self.repository.save_test(
            self.source_admin_id,
            "Opening quiz",
            [
                {
                    "source_type": "case",
                    "case_id": case_id,
                    "scenario_ids": [self.scenario_id],
                    "contracts": ["4H"],
                    "results": ["="],
                    "scores": {"4H": {"=": 10}},
                }
            ],
        )
        self.student_id = self.repository.create_student(
            "Transfer student",
            "student password",
        )
        self.repository.assign_test_to_student(
            self.source_admin_id,
            self.student_id,
            self.test_id,
        )
        self.repository.save_test_result(
            self.test_id,
            self.student_id,
            [
                {
                    "problem_number": 1,
                    "scenario_id": self.scenario_id,
                    "contract": "4H",
                    "stasis": "=",
                    "score": 10,
                }
            ],
            10,
        )
        self.package_path = os.path.join(self.temp_dir.name, "workspace.bdtpack")
        self.passphrase = "correct horse battery staple"
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        DatabaseManager._instance = None
        self.temp_dir.cleanup()

    def test_encrypted_package_round_trips_owned_data_and_remaps_ids(self):
        summary = self.service.export_admin_data(
            self.source_admin_id,
            self.package_path,
            self.passphrase,
        )
        self.assertEqual(summary["source_administrator"], "source_admin")
        with open(self.package_path, "rb") as package_file:
            encrypted_package = package_file.read()
        self.assertTrue(encrypted_package.startswith(b"BDTPACK\0"))
        self.assertNotIn(b"source_admin", encrypted_package)
        self.assertNotIn(b"Teaching materials", encrypted_package)

        destination_path = os.path.join(self.temp_dir.name, "destination.db")
        DatabaseManager._instance = None
        DatabaseManager(destination_path)
        destination_repository = Repository()
        destination_admin_id = destination_repository.create_admin(
            "destination_admin",
            "destination password",
        )
        destination_service = ContentTransferService(destination_repository.db)
        payload = destination_service.read_package(
            self.package_path,
            self.passphrase,
        )
        self.assertNotIn("Administration", payload["tables"])
        self.assertEqual(len(payload["tables"]["Folder"]), 2)
        self.assertEqual(len(payload["tables"]["Test_Result"]), 1)
        self.assertNotIn(
            "Private other-admin folder",
            [row["Name"] for row in payload["tables"]["Folder"]],
        )

        imported = destination_service.import_admin_data(
            destination_admin_id,
            payload,
        )
        self.assertEqual(imported["source_administrator"], "source_admin")
        self.assertEqual(
            [
                folder.name
                for folder in destination_repository.get_folders_by_admin(
                    destination_admin_id
                )
            ],
            ["Teaching materials", "Imported lesson"],
        )
        imported_folders = destination_repository.get_folders_by_admin(
            destination_admin_id
        )
        self.assertEqual(imported_folders[0].parent_folder_id, None)
        self.assertEqual(imported_folders[1].parent_folder_id, imported_folders[0].id)
        tests = destination_repository.get_tests_by_admin(destination_admin_id)
        self.assertEqual([test["name"] for test in tests], ["Opening quiz"])
        problem = tests[0]["problems"][0]
        imported_scenario_id = problem["scenario_ids"][0]
        self.assertEqual(
            problem["scenario_information"][imported_scenario_id],
            "Lead the singleton spade.",
        )
        self.assertEqual(
            len(destination_repository.get_test_results_by_admin(destination_admin_id)),
            1,
        )
        self.assertIsNone(
            destination_repository.get_admin_by_name("source_admin")
        )

    def test_wrong_passphrase_and_modified_package_are_rejected(self):
        self.service.export_admin_data(
            self.source_admin_id,
            self.package_path,
            self.passphrase,
        )
        with self.assertRaisesRegex(ValueError, "passphrase is incorrect"):
            self.service.read_package(self.package_path, "wrong passphrase")

        with open(self.package_path, "rb") as package_file:
            corrupted = bytearray(package_file.read())
        corrupted[-1] ^= 1
        corrupt_path = os.path.join(self.temp_dir.name, "corrupt.bdtpack")
        with open(corrupt_path, "wb") as package_file:
            package_file.write(corrupted)
        with self.assertRaisesRegex(ValueError, "passphrase is incorrect"):
            self.service.read_package(corrupt_path, self.passphrase)

    def test_export_requires_a_long_passphrase(self):
        with self.assertRaisesRegex(ValueError, "at least 12 characters"):
            self.service.export_admin_data(
                self.source_admin_id,
                self.package_path,
                "short",
            )
        self.assertFalse(os.path.exists(self.package_path))

    def test_import_conflict_rolls_back_every_insert(self):
        self.service.export_admin_data(
            self.source_admin_id,
            self.package_path,
            self.passphrase,
        )
        payload = copy.deepcopy(
            self.service.read_package(self.package_path, self.passphrase)
        )
        payload["tables"]["Student"][0]["Password"] = hash_password(
            "different student password"
        )
        with self.assertRaisesRegex(ValueError, "different credentials"):
            self.service.import_admin_data(self.target_admin_id, payload)
        self.assertEqual(
            [
                folder.name
                for folder in self.repository.get_folders_by_admin(
                    self.target_admin_id
                )
            ],
            ["Private other-admin folder"],
        )
        self.assertEqual(
            self.repository.get_tests_by_admin(self.target_admin_id),
            [],
        )


if __name__ == "__main__":
    unittest.main()
