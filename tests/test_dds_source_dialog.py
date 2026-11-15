import importlib.machinery
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication, QLabel, QPushButton

from src.core.dds_wrapper import DdsProviderUnavailable
from src.ui.dialogs.dds_source_dialog import DdsSourceDialog
from src.ui.main_window import MainWindow


class TestDdsSourceDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_dialog_lists_all_sources_and_defaults_to_none(self):
        with patch(
            "src.ui.dialogs.dds_source_dialog.DdsWrapper.is_provider_installed",
            return_value=False,
        ):
            dialog = DdsSourceDialog()

        self.addCleanup(dialog.close)
        self.assertEqual(dialog.selected_provider(), "none")
        self.assertEqual(
            set(dialog.provider_buttons),
            {"none", "dds3", "scanned", "endplay"},
        )
        endplay_status = dialog.findChild(
            QLabel,
            "provider_status_endplay",
        )
        self.assertEqual(endplay_status.text(), "Not installed")
        self.assertTrue(dialog.provider_buttons["dds3"].isEnabled())
        self.assertTrue(dialog.provider_cards["none"].property("selected"))

    def test_registered_dds_option_is_always_enabled(self):
        dialog = DdsSourceDialog()
        self.addCleanup(dialog.close)

        self.assertTrue(dialog.provider_buttons["dds3"].isEnabled())

    def test_registered_dds_is_uninstalled_without_a_database_record(self):
        dialog = DdsSourceDialog()
        self.addCleanup(dialog.close)

        status = dialog.findChild(QLabel, "provider_status_dds3")
        self.assertEqual(status.text(), "Not installed")
        self.assertEqual(
            status.toolTip(),
            "No DDS source folder is registered.",
        )

    def test_registered_dds_status_uses_the_registered_folder(self):
        registered_folder = Path("/registered/dds")
        scan_folder = Path("/project/dds")
        with patch(
            "src.ui.dialogs.dds_source_dialog.DdsWrapper.is_provider_installed",
            return_value=False,
        ) as is_installed:
            dialog = DdsSourceDialog(
                source_folder=str(scan_folder),
                registered_source_folder=str(registered_folder),
            )
        self.addCleanup(dialog.close)

        is_installed.assert_any_call(
            "dds3",
            str(registered_folder),
        )
        self.assertEqual(
            dialog.findChild(QLabel, "provider_status_dds3").toolTip(),
            str(registered_folder),
        )
        self.assertEqual(
            dialog.dds_source_folder_input.text(),
            str(scan_folder),
        )

    def test_user_can_select_each_optional_provider(self):
        dialog = DdsSourceDialog()
        self.addCleanup(dialog.close)

        dialog.provider_buttons["dds3"].setChecked(True)
        self.assertEqual(dialog.selected_provider(), "dds3")
        dialog.provider_buttons["scanned"].setChecked(True)
        self.assertEqual(dialog.selected_provider(), "scanned")
        dialog.provider_buttons["endplay"].setChecked(True)
        self.assertEqual(dialog.selected_provider(), "endplay")
        dialog.provider_buttons["none"].setChecked(True)
        self.assertEqual(dialog.selected_provider(), "none")

    def test_scanned_source_folder_can_be_browsed_and_updates_status(self):
        dialog = DdsSourceDialog()
        self.addCleanup(dialog.close)

        with tempfile.TemporaryDirectory() as folder, patch(
            "src.ui.dialogs.dds_source_dialog.QFileDialog.getExistingDirectory",
            return_value=folder,
        ) as choose_folder:
            package = Path(folder) / "python" / "dds3"
            bazel_package = Path(folder) / "bazel-bin" / "python" / "dds3"
            package.mkdir(parents=True)
            bazel_package.mkdir(parents=True)
            (package / "__init__.py").write_text("", encoding="utf-8")
            suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
            (bazel_package / f"_dds3{suffix}").touch()
            dialog.findChild(
                QPushButton,
                "browseDdsSourceFolder",
            ).click()

        self.assertEqual(
            dialog.selected_source_folder(),
            str(Path(folder).resolve()),
        )
        self.assertEqual(
            dialog.findChild(QLabel, "provider_status_scanned").text(),
            "Installed",
        )
        choose_folder.assert_called_once()

    def test_schema_does_not_pre_register_a_dds_folder(self):
        schema_path = Path(__file__).resolve().parents[1] / "schema.sql"
        with schema_path.open(encoding="utf-8") as schema_file:
            schema = schema_file.read()
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)

        connection.executescript(schema)
        row = connection.execute(
            "SELECT SettingValue FROM ApplicationSetting "
            "WHERE SettingKey = 'DDS_SOURCE_FOLDER'"
        ).fetchone()

        self.assertIsNone(row)

    def test_source_options_follow_the_interface_language(self):
        window = MainWindow()
        self.addCleanup(window.close)
        with patch(
            "src.ui.dialogs.dds_source_dialog.DdsWrapper.is_provider_installed",
            return_value=False,
        ):
            dialog = window._prepare_dialog(DdsSourceDialog())
        self.addCleanup(dialog.close)

        window.set_language("zh")

        self.assertEqual(dialog.windowTitle(), "DDS 来源")
        self.assertEqual(
            dialog.provider_buttons["none"].text(),
            "A. 不使用 DDS",
        )
        self.assertEqual(
            dialog.provider_buttons["scanned"].text(),
            "C. 扫描 DDS 源码目录",
        )
        self.assertEqual(
            dialog.findChild(QLabel, "ddsSourceFolderLabel").text(),
            "DDS 源码目录",
        )
        self.assertEqual(
            dialog.findChild(QPushButton, "browseDdsSourceFolder").text(),
            "浏览...",
        )
        self.assertEqual(
            dialog.findChild(QLabel, "provider_status_endplay").text(),
            "未安装",
        )

    def test_tool_menu_action_opens_the_source_window(self):
        with patch("src.ui.main_window.QSettings") as settings_class:
            settings_class.return_value.value.return_value = "none"
            window = MainWindow()
        self.addCleanup(window.close)

        with patch(
            "src.ui.main_window.exec_and_delete",
            return_value=False,
        ) as execute_dialog:
            window.action_dds_source.trigger()

        dialog = execute_dialog.call_args.args[0]
        self.assertIsInstance(dialog, DdsSourceDialog)
        self.assertIn(window.action_dds_source, window.tool_menu.actions())

    def test_registered_provider_uses_the_database_folder(self):
        with patch("src.ui.main_window.QSettings") as settings_class:
            settings_class.return_value.value.return_value = "none"
            window = MainWindow()
        self.addCleanup(window.close)
        with tempfile.TemporaryDirectory() as folder:
            registered_folder = Path(folder).resolve()
            window.repo.get_application_setting = lambda _key: str(
                registered_folder
            )

            def choose_registered_source(dialog):
                dialog.provider_buttons["dds3"].setChecked(True)
                return True

            with (
                patch(
                    "src.ui.main_window.exec_and_delete",
                    side_effect=choose_registered_source,
                ),
                patch.object(
                    window.table_view,
                    "set_dds_provider",
                ) as set_provider,
                patch(
                    "src.ui.dialogs.dds_source_dialog.DdsWrapper.is_provider_installed",
                    return_value=False,
                ),
            ):
                window.open_dds_source_dialog()

            set_provider.assert_called_once_with(
                "dds3",
                source_folder=str(registered_folder),
            )

    def test_registered_provider_requires_a_database_folder(self):
        with patch("src.ui.main_window.QSettings") as settings_class:
            settings_class.return_value.value.return_value = "none"
            window = MainWindow()
        self.addCleanup(window.close)
        window.repo.get_application_setting = lambda _key: None

        def choose_registered_source(dialog):
            dialog.provider_buttons["dds3"].setChecked(True)
            self.assertEqual(
                dialog.findChild(QLabel, "provider_status_dds3").text(),
                "Not installed",
            )
            return True

        with (
            patch(
                "src.ui.main_window.exec_and_delete",
                side_effect=choose_registered_source,
            ),
            patch.object(
                window.table_view,
                "set_dds_provider",
            ) as set_provider,
            patch("src.ui.main_window.show_message") as show_message,
        ):
            window.open_dds_source_dialog()

        set_provider.assert_not_called()
        show_message.assert_called_once()

    def test_confirmed_source_is_applied_and_saved(self):
        with patch("src.ui.main_window.QSettings") as settings_class:
            settings_class.return_value.value.return_value = "none"
            window = MainWindow()
        self.addCleanup(window.close)

        def choose_endplay(dialog):
            dialog.provider_buttons["endplay"].setChecked(True)
            return True

        with (
            patch(
                "src.ui.main_window.exec_and_delete",
                side_effect=choose_endplay,
            ),
            patch.object(window.table_view, "set_dds_provider") as set_provider,
        ):
            window.open_dds_source_dialog()

        set_provider.assert_called_once_with(
            "endplay",
            source_folder=window._get_registered_dds_source_folder(),
        )
        window.dds_source_settings.setValue.assert_called_once_with(
            "DDS/source",
            "endplay",
        )

    def test_scanned_folder_is_saved_and_passed_to_provider(self):
        with patch("src.ui.main_window.QSettings") as settings_class:
            settings_class.return_value.value.return_value = "none"
            window = MainWindow()
        self.addCleanup(window.close)

        with tempfile.TemporaryDirectory() as folder:
            normalized_folder = str(Path(folder).resolve())
            call_order = []

            def choose_scanned_source(dialog):
                dialog.provider_buttons["scanned"].setChecked(True)
                dialog.dds_source_folder_input.setText(folder)
                return True

            with (
                patch("src.ui.main_window.QSettings") as settings_class,
                patch(
                    "src.ui.main_window.exec_and_delete",
                    side_effect=choose_scanned_source,
                ),
                patch.object(
                    window.table_view,
                    "set_dds_provider",
                    side_effect=lambda *_args, **_kwargs: call_order.append(
                        "load"
                    ),
                ) as set_provider,
                patch.object(
                    window.repo,
                    "save_application_setting",
                    side_effect=lambda *_args, **_kwargs: call_order.append(
                        "save"
                    ),
                ) as save_setting,
            ):
                window.open_dds_source_dialog()

        save_setting.assert_called_once_with(
            "DDS_SOURCE_FOLDER",
            normalized_folder,
        )
        set_provider.assert_called_once_with(
            "scanned",
            source_folder=normalized_folder,
        )
        self.assertEqual(call_order, ["load", "save"])

    def test_unloadable_scanned_folder_is_not_registered(self):
        with patch("src.ui.main_window.QSettings") as settings_class:
            settings_class.return_value.value.return_value = "none"
            window = MainWindow()
        self.addCleanup(window.close)

        with tempfile.TemporaryDirectory() as folder:
            def choose_scanned_source(dialog):
                dialog.provider_buttons["scanned"].setChecked(True)
                dialog.dds_source_folder_input.setText(folder)
                return True

            with (
                patch(
                    "src.ui.main_window.exec_and_delete",
                    side_effect=choose_scanned_source,
                ),
                patch.object(
                    window.table_view,
                    "set_dds_provider",
                    side_effect=DdsProviderUnavailable("load failed"),
                ),
                patch.object(
                    window.repo,
                    "save_application_setting",
                ) as save_setting,
                patch("src.ui.main_window.show_message"),
            ):
                window.open_dds_source_dialog()

        save_setting.assert_not_called()

if __name__ == "__main__":
    unittest.main()
