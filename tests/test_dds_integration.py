import hashlib
import importlib
import importlib.machinery
import sys
import tempfile
import unittest
from enum import IntEnum
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

from src.core.dds_wrapper import DdsProviderUnavailable, DdsWrapper


class TestDdsWrapper(unittest.TestCase):
    def test_default_provider_is_off_and_does_not_import_optional_modules(self):
        with patch.object(importlib, "import_module") as import_module:
            solver = DdsWrapper()

        self.assertEqual(solver.provider, "none")
        self.assertFalse(solver.is_available())
        import_module.assert_not_called()
        with self.assertRaisesRegex(RuntimeError, "No DDS source is selected"):
            solver.calc_dd_table_pbn("N:...")
        with self.assertRaisesRegex(RuntimeError, "No DDS source is selected"):
            solver.solve_board_pbn("N:...")

    def test_unavailable_provider_does_not_replace_current_provider(self):
        solver = DdsWrapper()
        with (
            patch(
                "src.core.dds_wrapper.DdsWrapper._load_scanned_dds",
                side_effect=ModuleNotFoundError("missing"),
            ),
            self.assertRaisesRegex(DdsProviderUnavailable, "dds3"),
        ):
            solver.set_provider("dds3")

        self.assertEqual(solver.provider, "none")
        self.assertFalse(solver.is_available())

    def test_scanned_provider_requires_a_built_native_extension(self):
        solver = DdsWrapper()
        with (
            patch.object(
                DdsWrapper,
                "_find_scanned_dds_extension",
                return_value=None,
            ),
            self.assertRaisesRegex(DdsProviderUnavailable, "scanned"),
        ):
            solver.set_provider("scanned")

        self.assertEqual(solver.provider, "none")

    def test_registered_provider_loads_from_the_registered_folder(self):
        fake_dds = ModuleType("dds3")
        with tempfile.TemporaryDirectory() as folder, patch.object(
                DdsWrapper,
                "_load_scanned_dds",
                return_value=fake_dds,
        ) as load_scanned:
            solver = DdsWrapper("dds3", folder)

        self.assertEqual(solver.provider, "dds3")
        self.assertIs(solver._backend, fake_dds)
        load_scanned.assert_called_once_with(Path(folder).resolve())

    def test_scanned_provider_detects_extension_in_selected_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            package = root / "python" / "dds3"
            bazel_package = root / "bazel-bin" / "python" / "dds3"
            package.mkdir(parents=True)
            bazel_package.mkdir(parents=True)
            (package / "__init__.py").write_text("", encoding="utf-8")
            suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
            (bazel_package / f"_dds3{suffix}").touch()

            self.assertTrue(
                DdsWrapper.is_provider_installed("scanned", folder)
            )

    def test_scanned_provider_accepts_a_selected_bazel_package_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            extension_folder = (
                    Path(folder) / "bazel-bin" / "python" / "dds3"
            )
            extension_folder.mkdir(parents=True)
            suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
            extension_path = extension_folder / f"_dds3{suffix}"
            extension_path.touch()

            self.assertEqual(
                DdsWrapper._find_scanned_dds_extension(extension_folder),
                extension_path.resolve(),
            )

    def test_scanned_provider_does_not_search_above_the_selected_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            selected_folder = root / "selected"
            selected_folder.mkdir()
            parent_package = root / "python" / "dds3"
            parent_package.mkdir(parents=True)
            suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
            (parent_package / f"_dds3{suffix}").touch()

            self.assertIsNone(
                DdsWrapper._find_scanned_dds_extension(selected_folder)
            )

    def test_scanned_provider_finds_extensions_in_venv_site_packages(self):
        relative_packages = (
            Path("Lib") / "site-packages" / "dds3",
            Path("lib")
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
            / "site-packages"
            / "dds3",
        )
        suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
        for relative_package in relative_packages:
            with self.subTest(relative_package=relative_package):
                with tempfile.TemporaryDirectory() as folder:
                    package = (
                            Path(folder) / ".venv" / relative_package
                    )
                    package.mkdir(parents=True)
                    extension_path = package / f"_dds3{suffix}"
                    extension_path.touch()

                    self.assertEqual(
                        DdsWrapper._find_scanned_dds_extension(folder),
                        extension_path.resolve(),
                    )

    def test_scanned_loader_imports_the_selected_native_extension(self):
        extension_path = Path("/tmp/dds3/_dds3.pyd")
        fake_module = ModuleType("_dds3")
        fake_loader = Mock()
        fake_spec = SimpleNamespace(loader=fake_loader)
        module_suffix = hashlib.sha256(
            str(extension_path.resolve()).encode("utf-8")
        ).hexdigest()[:16]
        module_name = (
            f"_bridge_demonstration_scanned_dds3_{module_suffix}"
        )
        self.addCleanup(
            sys.modules.pop,
            f"{module_name}._dds3",
            None,
        )
        self.addCleanup(
            sys.modules.pop,
            module_name,
            None,
        )
        with (
            patch.object(
                DdsWrapper,
                "_find_scanned_dds_extension",
                return_value=extension_path,
            ),
            patch(
                "importlib.util.spec_from_file_location",
                return_value=fake_spec,
            ) as spec_from_file,
            patch(
                "importlib.util.module_from_spec",
                return_value=fake_module,
            ) as module_from_spec,
        ):
            loaded = DdsWrapper._load_scanned_dds(Path("/tmp/dds3"))
            loaded_again = DdsWrapper._load_scanned_dds(Path("/tmp/dds3"))

        self.assertIs(loaded, fake_module)
        self.assertIs(loaded_again, loaded)
        self.assertTrue(spec_from_file.call_args.args[0].endswith("._dds3"))
        self.assertEqual(spec_from_file.call_args.args[1], extension_path)
        spec_from_file.assert_called_once()
        module_from_spec.assert_called_once()
        fake_loader.exec_module.assert_called_once_with(fake_module)

    def test_scanned_provider_uses_dds3_backend(self):
        table_result = {"res_table": [[7, 8, 9, 10]] * 5}
        fake_dds = ModuleType("scanned_dds3")
        fake_dds.calc_all_tables_pbn = Mock(
            return_value={
                "no_of_boards": 1,
                "tables": [table_result],
                "par_results": [],
            }
        )
        fake_dds.solve_board_pbn = Mock(return_value=SimpleNamespace())

        solver = DdsWrapper()
        with (
            patch.object(
                DdsWrapper,
                "_load_scanned_dds",
                return_value=fake_dds,
            ) as load_scanned,
        ):
            solver.set_provider("scanned")
            self.assertEqual(solver.calc_dd_table_pbn("N:deal"), table_result)

        load_scanned.assert_called_once_with(solver.source_folder)
        fake_dds.calc_all_tables_pbn.assert_called_once_with(["N:deal"], mode=-1)

    def test_dds3_provider_is_loaded_only_when_selected_and_receives_calls(self):
        table_result = {"res_table": [[7, 8, 9, 10]] * 5}
        board_result = SimpleNamespace(cards=["SA", "SK"])
        fake_dds = ModuleType("dds3")
        fake_dds.calc_all_tables_pbn = Mock(
            return_value={
                "no_of_boards": 1,
                "tables": [table_result],
                "par_results": [],
            }
        )
        fake_dds.solve_board_pbn = Mock(return_value=board_result)

        solver = DdsWrapper()
        with patch(
                "src.core.dds_wrapper.DdsWrapper._load_scanned_dds",
                return_value=fake_dds,
        ) as load_scanned:
            solver.set_provider("dds3")
            self.assertEqual(solver.calc_dd_table_pbn("N:deal"), table_result)
            self.assertIs(solver.solve_board_pbn("N:deal"), board_result)

        load_scanned.assert_called_once_with(solver.source_folder)
        fake_dds.calc_all_tables_pbn.assert_called_once_with(
            ["N:deal"],
            mode=-1,
        )
        fake_dds.solve_board_pbn.assert_called_once_with(
            "N:deal",
            trump=4,
            first=0,
            current_trick_suit=(0, 0, 0),
            current_trick_rank=(0, 0, 0),
            target=-1,
            solutions=2,
            mode=0,
        )

    def test_endplay_provider_normalizes_table_and_solver_results(self):
        class Denom(IntEnum):
            spades = 0
            hearts = 1
            diamonds = 2
            clubs = 3
            nt = 4

        class Player(IntEnum):
            north = 0
            east = 1
            south = 2
            west = 3

        class SolveMode(IntEnum):
            Default = 0
            OptimalOne = 1
            OptimalAll = 2

        class Deal:
            def __init__(self, pbn, *, first=Player.north, trump=Denom.nt):
                self.pbn = pbn
                self.first = first
                self.trump = trump
                self.played = []

            def play(self, card, *, from_hand=True):
                self.played.append((card, from_hand))

        class FakeTable:
            def __getitem__(self, item):
                denom, player = item
                return int(denom) * 10 + int(player)

        solved = [
            (
                SimpleNamespace(suit=0, rank=SimpleNamespace(abbr="A")),
                7,
            ),
            (
                SimpleNamespace(suit=1, rank=SimpleNamespace(abbr="K")),
                6,
            ),
        ]
        table_module = ModuleType("endplay.dds")
        table_module.calc_dd_table = Mock(return_value=FakeTable())
        table_module.solve_board = Mock(return_value=solved)
        solve_module = ModuleType("endplay.dds.solve")
        solve_module.SolveMode = SolveMode
        types_module = ModuleType("endplay.types")
        types_module.Deal = Deal
        types_module.Denom = Denom
        types_module.Player = Player
        modules = {
            "endplay.dds": table_module,
            "endplay.dds.solve": solve_module,
            "endplay.types": types_module,
        }
        solver = DdsWrapper()

        with patch.object(
                importlib,
                "import_module",
                side_effect=modules.__getitem__,
        ) as import_module:
            solver.set_provider("endplay")
            table = solver.calc_dd_table_pbn("N:deal")
            result = solver.solve_board_pbn(
                "N:deal",
                solutions=2,
                trump=4,
                first=3,
                current_trick_suit=(0, 1, 0),
                current_trick_rank=(14, 13, 0),
            )

        self.assertEqual(import_module.call_count, 3)
        self.assertEqual(
            table["res_table"],
            [
                [0, 1, 2, 3],
                [10, 11, 12, 13],
                [20, 21, 22, 23],
                [30, 31, 32, 33],
                [40, 41, 42, 43],
            ],
        )
        self.assertEqual(result, {
            "cards": 2,
            "suit": [0, 1],
            "rank": [14, 13],
            "score": [7, 6],
        })
        deal = table_module.solve_board.call_args.args[0]
        self.assertEqual(deal.first, Player.west)
        self.assertEqual(deal.trump, Denom.nt)
        self.assertEqual(deal.played, [("SA", False), ("HK", False)])
        table_module.solve_board.assert_called_once_with(
            deal,
            mode=SolveMode.OptimalAll,
            target=-1,
        )

        solver.solve_board_pbn("N:deal", solutions=3)
        self.assertEqual(
            table_module.solve_board.call_args.kwargs["mode"],
            SolveMode.Default,
        )

    def test_solver_errors_return_none(self):
        fake_dds = ModuleType("dds3")
        fake_dds.calc_all_tables_pbn = Mock(side_effect=ValueError("bad deal"))
        fake_dds.solve_board_pbn = Mock(side_effect=ValueError("bad deal"))

        with patch(
                "src.core.dds_wrapper.DdsWrapper._load_scanned_dds",
                return_value=fake_dds,
        ):
            solver = DdsWrapper("dds3")
            self.assertIsNone(solver.calc_dd_table_pbn("N:bad"))
            self.assertIsNone(solver.solve_board_pbn("N:bad"))


if __name__ == "__main__":
    unittest.main()
