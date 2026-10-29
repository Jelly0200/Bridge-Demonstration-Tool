import hashlib
import json
import os
import struct
import tempfile
import zlib
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.security.passwords import hash_password, is_password_hash, verify_password


_MAGIC = b"BDTPACK\0"
_FORMAT_VERSION = 1
_HEADER = struct.Struct(">8sBIII16s12s")
_SCRYPT_N = 2**15
_SCRYPT_R = 8
_SCRYPT_P = 1
_MAX_PACKAGE_BYTES = 512 * 1024 * 1024
_MAX_PAYLOAD_BYTES = 512 * 1024 * 1024
_MIN_PASSPHRASE_LENGTH = 12

_TABLE_COLUMNS = {
    "Folder": (
        "Id",
        "AdministrationId",
        "ParentFolderId",
        "Name",
    ),
    "CaseStudy": ("Id", "FolderId", "Name"),
    "BoardConfiguration": ("Id", "Dealer", "Vulnerability"),
    "Board": (
        "Id",
        "CaseId",
        "BoardConfigurationId",
        "SouthHandPbn",
        "WestHandPbn",
        "NorthHandPbn",
        "EastHandPbn",
        "Description",
    ),
    "Scenario": (
        "Id",
        "BoardId",
        "Name",
        "Information",
        "BiddingRoute",
        "Declarer",
        "Contract",
        "RiskStatus",
        "IsTargeted",
        "TargetedSequence",
    ),
    "Label": ("Id", "ScenarioId", "Sequence", "Color", "Card"),
    "Test": ("Id", "AdministrationId", "Name"),
    "Rule": ("Id", "Contracts", "Rules"),
    "Test_Scenario": ("Id", "TestId", "Sequence", "ScenarioId", "RuleId"),
    "Student": ("Id", "Name", "Password"),
    "Student_Test": ("StudentId", "TestId", "AssignedAt", "CompletedAt"),
    "Test_Result": (
        "Id",
        "TestId",
        "StudentId",
        "ApplicantName",
        "Contracts",
        "Score",
        "SubmittedAt",
    ),
}


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    if not isinstance(passphrase, str) or not passphrase:
        raise ValueError("An export passphrase is required.")
    if len(passphrase.encode("utf-8")) > 1024:
        raise ValueError("The passphrase is too long.")
    return hashlib.scrypt(
        passphrase.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=32,
        maxmem=64 * 1024 * 1024,
    )


def _fetch_rows(connection, query, parameters=()):
    return [
        dict(row)
        for row in connection.execute(query, parameters).fetchall()
    ]


def _collect_admin_payload(connection, admin_id: int, selection=None) -> dict:
    connection.execute("BEGIN")
    try:
        administrator = connection.execute(
            "SELECT Id, Name FROM Administration WHERE Id = ?",
            (admin_id,),
        ).fetchone()
        if administrator is None:
            raise LookupError(f"Administrator {admin_id} was not found.")

        tables = {
            "Folder": _fetch_rows(
                connection,
                """
                SELECT Id, AdministrationId, ParentFolderId, Name
                FROM Folder WHERE AdministrationId = ? ORDER BY Id
                """,
                (admin_id,),
            ),
            "CaseStudy": _fetch_rows(
                connection,
                """
                SELECT c.Id, c.FolderId, c.Name
                FROM CaseStudy c
                JOIN Folder f ON f.Id = c.FolderId
                WHERE f.AdministrationId = ? ORDER BY c.Id
                """,
                (admin_id,),
            ),
            "BoardConfiguration": _fetch_rows(
                connection,
                """
                SELECT DISTINCT bc.Id, bc.Dealer, bc.Vulnerability
                FROM BoardConfiguration bc
                JOIN Board b ON b.BoardConfigurationId = bc.Id
                JOIN CaseStudy c ON c.Id = b.CaseId
                JOIN Folder f ON f.Id = c.FolderId
                WHERE f.AdministrationId = ? ORDER BY bc.Id
                """,
                (admin_id,),
            ),
            "Board": _fetch_rows(
                connection,
                """
                SELECT b.Id, b.CaseId, b.BoardConfigurationId,
                       b.SouthHandPbn, b.WestHandPbn, b.NorthHandPbn,
                       b.EastHandPbn, b.Description
                FROM Board b
                JOIN CaseStudy c ON c.Id = b.CaseId
                JOIN Folder f ON f.Id = c.FolderId
                WHERE f.AdministrationId = ? ORDER BY b.Id
                """,
                (admin_id,),
            ),
            "Scenario": _fetch_rows(
                connection,
                """
                SELECT s.Id, s.BoardId, s.Name, s.Information, s.BiddingRoute,
                       s.Declarer, s.Contract, s.RiskStatus, s.IsTargeted,
                       s.TargetedSequence
                FROM Scenario s
                JOIN Board b ON b.Id = s.BoardId
                JOIN CaseStudy c ON c.Id = b.CaseId
                JOIN Folder f ON f.Id = c.FolderId
                WHERE f.AdministrationId = ? ORDER BY s.Id
                """,
                (admin_id,),
            ),
            "Label": _fetch_rows(
                connection,
                """
                SELECT l.Id, l.ScenarioId, l.Sequence, l.Color, l.Card
                FROM Label l
                JOIN Scenario s ON s.Id = l.ScenarioId
                JOIN Board b ON b.Id = s.BoardId
                JOIN CaseStudy c ON c.Id = b.CaseId
                JOIN Folder f ON f.Id = c.FolderId
                WHERE f.AdministrationId = ? ORDER BY l.Id
                """,
                (admin_id,),
            ),
            "Test": _fetch_rows(
                connection,
                """
                SELECT Id, AdministrationId, Name
                FROM Test WHERE AdministrationId = ? ORDER BY Id
                """,
                (admin_id,),
            ),
        }

        tables["Rule"] = _fetch_rows(
            connection,
            """
            SELECT DISTINCT r.Id, r.Contracts, r.Rules
            FROM Rule r
            JOIN Test_Scenario ts ON ts.RuleId = r.Id
            JOIN Test t ON t.Id = ts.TestId
            WHERE t.AdministrationId = ? ORDER BY r.Id
            """,
            (admin_id,),
        )
        tables["Test_Scenario"] = _fetch_rows(
            connection,
            """
            SELECT ts.Id, ts.TestId, ts.Sequence, ts.ScenarioId, ts.RuleId
            FROM Test_Scenario ts
            JOIN Test t ON t.Id = ts.TestId
            WHERE t.AdministrationId = ? ORDER BY ts.Id
            """,
            (admin_id,),
        )
        tables["Student"] = []
        tables["Student_Test"] = []
        tables["Test_Result"] = []

        connection.commit()
        payload = {
            "format_version": _FORMAT_VERSION,
            "source_administrator": administrator["Name"],
            "tables": tables,
        }
        return _filter_export_payload(payload, selection)
    except Exception:
        connection.rollback()
        raise


def _filter_export_payload(payload: dict, selection: dict | None) -> dict:
    if selection is None:
        return payload
    if not isinstance(selection, dict) or set(selection) - {
        "folders",
        "cases",
        "boards",
        "tests",
    }:
        raise ValueError("The export selection is invalid.")

    tables = payload["tables"]
    table_names = {
        "folders": "Folder",
        "cases": "CaseStudy",
        "boards": "Board",
        "tests": "Test",
    }
    selected = {}
    for selection_name, table_name in table_names.items():
        ids = selection.get(selection_name, [])
        if not isinstance(ids, (list, tuple, set)):
            raise ValueError("The export selection is invalid.")
        if any(type(row_id) is not int for row_id in ids):
            raise ValueError("The export selection contains an invalid identifier.")
        available_ids = {row["Id"] for row in tables[table_name]}
        selected_ids = set(ids)
        if not selected_ids <= available_ids:
            raise ValueError("The export selection contains an unknown asset.")
        selected[selection_name] = selected_ids
    if not any(selected.values()):
        raise ValueError("Select at least one folder, case, board, or test.")

    folders_by_id = {row["Id"]: row for row in tables["Folder"]}
    cases_by_id = {row["Id"]: row for row in tables["CaseStudy"]}
    boards_by_id = {row["Id"]: row for row in tables["Board"]}
    scenarios_by_id = {row["Id"]: row for row in tables["Scenario"]}
    folder_ids = set(selected["folders"])

    changed = True
    while changed:
        previous_count = len(folder_ids)
        folder_ids.update(
            row["Id"]
            for row in tables["Folder"]
            if row["ParentFolderId"] in folder_ids
        )
        changed = len(folder_ids) != previous_count
    case_ids = {
        row["Id"]
        for row in tables["CaseStudy"]
        if row["FolderId"] in folder_ids
    }
    case_ids.update(selected["cases"])

    board_ids = {
        row["Id"]
        for row in tables["Board"]
        if row["CaseId"] in case_ids
    }
    board_ids.update(selected["boards"])
    case_ids.update(
        boards_by_id[board_id]["CaseId"]
        for board_id in board_ids
    )

    scenario_ids = {
        row["Id"]
        for row in tables["Scenario"]
        if row["BoardId"] in board_ids
    }
    selected_test_scenarios = [
        row
        for row in tables["Test_Scenario"]
        if row["TestId"] in selected["tests"]
    ]
    scenario_ids.update(row["ScenarioId"] for row in selected_test_scenarios)
    for scenario_id in scenario_ids:
        scenario = scenarios_by_id.get(scenario_id)
        if scenario is None:
            raise ValueError("A selected test references an unavailable scenario.")
        board_id = scenario["BoardId"]
        board_ids.add(board_id)
        case_ids.add(boards_by_id[board_id]["CaseId"])

    for case_id in case_ids:
        case = cases_by_id.get(case_id)
        if case is None:
            raise ValueError("A selected board references an unavailable case.")
        folder_id = case["FolderId"]
        while folder_id is not None:
            folder_ids.add(folder_id)
            folder_id = folders_by_id[folder_id]["ParentFolderId"]
    for folder_id in tuple(folder_ids):
        parent_id = folders_by_id[folder_id]["ParentFolderId"]
        while parent_id is not None:
            folder_ids.add(parent_id)
            parent_id = folders_by_id[parent_id]["ParentFolderId"]

    rule_ids = {
        row["RuleId"]
        for row in selected_test_scenarios
    }
    kept_ids = {
        "Folder": folder_ids,
        "CaseStudy": case_ids,
        "Board": board_ids,
        "BoardConfiguration": {
            row["BoardConfigurationId"]
            for row in tables["Board"]
            if row["Id"] in board_ids
        },
        "Scenario": scenario_ids,
        "Label": {
            row["Id"]
            for row in tables["Label"]
            if row["ScenarioId"] in scenario_ids
        },
        "Test": selected["tests"],
        "Rule": rule_ids,
        "Test_Scenario": {
            row["Id"]
            for row in selected_test_scenarios
        },
        "Student": set(),
        "Student_Test": set(),
        "Test_Result": set(),
    }
    for table_name, rows in tables.items():
        rows[:] = (
            [
                row
                for row in rows
                if "Id" in row and row["Id"] in kept_ids[table_name]
            ]
            if table_name != "Student_Test"
            else []
        )
    return payload


def _validate_payload(payload: dict) -> dict:
    if (
        not isinstance(payload, dict)
        or payload.get("format_version") != _FORMAT_VERSION
        or not isinstance(payload.get("source_administrator"), str)
        or not isinstance(payload.get("tables"), dict)
    ):
        raise ValueError("The transfer package has an unsupported or invalid format.")

    tables = payload["tables"]
    if set(tables) != set(_TABLE_COLUMNS):
        raise ValueError("The transfer package does not contain the expected data.")
    destination = payload.get("destination_administrator")
    if destination is not None:
        if (
            not isinstance(destination, dict)
            or set(destination) != {"Name", "Password"}
            or not isinstance(destination["Name"], str)
            or destination["Name"] != destination["Name"].strip()
            or not 3 <= len(destination["Name"]) <= 64
            or not isinstance(destination["Password"], str)
            or not is_password_hash(destination["Password"])
        ):
            raise ValueError("The transfer package has invalid destination account data.")
    for table_name, columns in _TABLE_COLUMNS.items():
        rows = tables[table_name]
        if not isinstance(rows, list):
            raise ValueError(f"Invalid {table_name} data in the transfer package.")
        expected_columns = set(columns)
        primary_key = "Id" if "Id" in expected_columns else None
        seen_ids = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != expected_columns:
                raise ValueError(
                    f"Invalid {table_name} row in the transfer package."
                )
            if primary_key:
                row_id = row[primary_key]
                if type(row_id) is not int or row_id in seen_ids:
                    raise ValueError(
                        f"Invalid {table_name} identifier in the transfer package."
                    )
                seen_ids.add(row_id)
    _validate_folder_tree(tables["Folder"])
    return payload


def _validate_folder_tree(folders: list[dict]):
    parent_by_id = {row["Id"]: row["ParentFolderId"] for row in folders}
    for folder_id, parent_id in parent_by_id.items():
        if parent_id is not None and parent_id not in parent_by_id:
            raise ValueError("A folder references a missing parent folder.")
        if parent_id == folder_id:
            raise ValueError("The transfer package contains a folder cycle.")

    completed = set()
    for folder_id in parent_by_id:
        path = set()
        current = folder_id
        while current is not None and current not in completed:
            if current in path:
                raise ValueError("The transfer package contains a folder cycle.")
            path.add(current)
            current = parent_by_id[current]
        completed.update(path)


def _serialize_payload(payload: dict) -> bytes:
    return zlib.compress(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8"),
        level=9,
    )


def _encrypt_payload(payload: dict, passphrase: str) -> bytes:
    if not isinstance(passphrase, str) or not passphrase:
        raise ValueError("An export passphrase is required.")
    if len(passphrase) < _MIN_PASSPHRASE_LENGTH:
        raise ValueError(
            f"Use an export passphrase with at least "
            f"{_MIN_PASSPHRASE_LENGTH} characters."
        )
    salt = os.urandom(16)
    nonce = os.urandom(12)
    header = _HEADER.pack(
        _MAGIC,
        _FORMAT_VERSION,
        _SCRYPT_N,
        _SCRYPT_R,
        _SCRYPT_P,
        salt,
        nonce,
    )
    ciphertext = AESGCM(_derive_key(passphrase, salt)).encrypt(
        nonce,
        _serialize_payload(payload),
        header,
    )
    package = header + ciphertext
    if len(package) > _MAX_PACKAGE_BYTES:
        raise ValueError("The administrator data is too large to export.")
    return package


def _decrypt_package(package_path: str | os.PathLike, passphrase: str) -> dict:
    path = Path(package_path)
    try:
        package_size = path.stat().st_size
    except OSError:
        raise
    if package_size > _MAX_PACKAGE_BYTES or package_size < _HEADER.size + 16:
        raise ValueError("The selected file is not a valid transfer package.")
    package = path.read_bytes()
    header = package[: _HEADER.size]
    try:
        magic, version, n, r, p, salt, nonce = _HEADER.unpack(header)
    except struct.error as error:
        raise ValueError("The selected file is not a valid transfer package.") from error
    if magic != _MAGIC or version != _FORMAT_VERSION:
        raise ValueError("The transfer package version is not supported.")
    if (n, r, p) != (_SCRYPT_N, _SCRYPT_R, _SCRYPT_P):
        raise ValueError("The transfer package uses unsupported security settings.")
    ciphertext = package[_HEADER.size :]
    try:
        compressed = AESGCM(_derive_key(passphrase, salt)).decrypt(
            nonce,
            ciphertext,
            header,
        )
    except InvalidTag:
        raise ValueError(
            "The passphrase is incorrect or the transfer package was damaged."
        ) from None
    decompressor = zlib.decompressobj()
    try:
        serialized = decompressor.decompress(
            compressed,
            _MAX_PAYLOAD_BYTES + 1,
        )
        if len(serialized) > _MAX_PAYLOAD_BYTES or decompressor.unconsumed_tail:
            raise ValueError("The transfer package expands beyond the allowed size.")
        if not decompressor.eof or decompressor.unused_data:
            raise ValueError("The transfer package payload is incomplete or invalid.")
        serialized += decompressor.flush()
    except zlib.error as error:
        raise ValueError("The transfer package payload is invalid.") from error
    if len(serialized) > _MAX_PAYLOAD_BYTES:
        raise ValueError("The transfer package expands beyond the allowed size.")
    try:
        payload = json.loads(serialized.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("The transfer package contains invalid data.") from error
    return _validate_payload(payload)


def _student_credentials_match(source_password: str, existing_password: str) -> bool:
    if source_password == existing_password:
        return True
    if not is_password_hash(source_password):
        return verify_password(source_password, existing_password)
    if not is_password_hash(existing_password):
        return verify_password(existing_password, source_password)
    return False


def _require_mapping(mapping: dict, source_id, relationship: str) -> int:
    if source_id not in mapping:
        raise ValueError(
            f"The transfer package contains a missing {relationship} reference."
        )
    return mapping[source_id]


def _insert_row(connection, table_name: str, row: dict, overrides=None) -> int:
    values = {key: value for key, value in row.items() if key != "Id"}
    if overrides:
        values.update(overrides)
    columns = tuple(values)
    placeholders = ", ".join("?" for _ in columns)
    cursor = connection.execute(
        f"INSERT INTO {table_name} ({', '.join(columns)}) "
        f"VALUES ({placeholders})",
        tuple(values[column] for column in columns),
    )
    return cursor.lastrowid


class ContentTransferService:
    """Export and restore one administrator's workspace as an encrypted file."""

    def __init__(self, database_manager):
        self.database_manager = database_manager

    def list_export_assets(self, admin_id: int) -> list[dict]:
        connection = self.database_manager.get_connection()
        try:
            folders = _fetch_rows(
                connection,
                """
                SELECT Id, ParentFolderId, Name FROM Folder
                WHERE AdministrationId = ? ORDER BY Name, Id
                """,
                (admin_id,),
            )
            cases = _fetch_rows(
                connection,
                """
                SELECT c.Id, c.FolderId, c.Name, f.Name AS FolderName
                FROM CaseStudy c
                JOIN Folder f ON f.Id = c.FolderId
                WHERE f.AdministrationId = ? ORDER BY f.Name, c.Name, c.Id
                """,
                (admin_id,),
            )
            boards = _fetch_rows(
                connection,
                """
                SELECT b.Id, b.CaseId, COALESCE(b.Description, '') AS Name,
                       c.Name AS CaseName, f.Name AS FolderName
                FROM Board b
                JOIN CaseStudy c ON c.Id = b.CaseId
                JOIN Folder f ON f.Id = c.FolderId
                WHERE f.AdministrationId = ?
                ORDER BY f.Name, c.Name, b.Id
                """,
                (admin_id,),
            )
            tests = _fetch_rows(
                connection,
                """
                SELECT Id, Name FROM Test
                WHERE AdministrationId = ? ORDER BY Name, Id
                """,
                (admin_id,),
            )
        finally:
            connection.close()

        assets = [
            {
                "type": "folder",
                "id": row["Id"],
                "parent_id": row["ParentFolderId"],
                "name": row["Name"],
            }
            for row in folders
        ]
        assets.extend(
            {
                "type": "case",
                "id": row["Id"],
                "folder_id": row["FolderId"],
                "name": f'{row["FolderName"]} / {row["Name"]}',
            }
            for row in cases
        )
        for row in boards:
            board_name = row["Name"] or f'Board #{row["Id"]}'
            assets.append(
                {
                    "type": "board",
                    "id": row["Id"],
                    "case_id": row["CaseId"],
                    "name": (
                        f'{row["FolderName"]} / {row["CaseName"]} / '
                        f"{board_name}"
                    ),
                }
            )
        assets.extend(
            {"type": "test", "id": row["Id"], "name": row["Name"]}
            for row in tests
        )
        return assets

    def export_admin_data(
        self,
        admin_id: int,
        package_path: str | os.PathLike,
        passphrase: str,
        selection: dict | None = None,
        destination_account: dict | None = None,
    ) -> dict:
        connection = self.database_manager.get_connection()
        try:
            payload = _collect_admin_payload(connection, admin_id, selection)
        finally:
            connection.close()
        if destination_account is not None:
            if not isinstance(destination_account, dict):
                raise ValueError("The destination administrator account is invalid.")
            name = destination_account.get("name")
            password = destination_account.get("password")
            if (
                not isinstance(name, str)
                or not 3 <= len(name.strip()) <= 64
                or not isinstance(password, str)
                or len(password) < 8
            ):
                raise ValueError(
                    "Enter a destination administrator name and a password "
                    "with at least 8 characters."
                )
            payload["destination_administrator"] = {
                "Name": name.strip(),
                "Password": hash_password(password),
            }
        package = _encrypt_payload(_validate_payload(payload), passphrase)
        target = Path(package_path)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{target.name}.",
                suffix=".tmp",
                dir=target.parent,
                delete=False,
            ) as output:
                temporary_path = Path(output.name)
                output.write(package)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary_path, target)
        except OSError:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise
        return _payload_summary(payload)

    def read_package(
        self,
        package_path: str | os.PathLike,
        passphrase: str,
    ) -> dict:
        return _decrypt_package(package_path, passphrase)

    def import_admin_data(self, admin_id: int | None, payload: dict) -> dict:
        payload = _validate_payload(payload)
        tables = payload["tables"]
        connection = self.database_manager.get_connection()
        mappings = {
            "Folder": {},
            "CaseStudy": {},
            "BoardConfiguration": {},
            "Board": {},
            "Scenario": {},
            "Label": {},
            "Test": {},
            "Rule": {},
            "Test_Scenario": {},
            "Student": {},
        }
        try:
            connection.execute("BEGIN IMMEDIATE")
            if admin_id is None:
                destination = payload.get("destination_administrator")
                if destination is None:
                    raise ValueError(
                        "This package does not include a destination administrator."
                    )
                cursor = connection.execute(
                    "INSERT INTO Administration (Name, Password) VALUES (?, ?)",
                    (destination["Name"], destination["Password"]),
                )
                admin_id = cursor.lastrowid
            elif connection.execute(
                "SELECT 1 FROM Administration WHERE Id = ?",
                (admin_id,),
            ).fetchone() is None:
                raise LookupError(f"Administrator {admin_id} was not found.")

            for row in tables["Folder"]:
                mappings["Folder"][row["Id"]] = _insert_row(
                    connection,
                    "Folder",
                    row,
                    {
                        "AdministrationId": admin_id,
                        "ParentFolderId": None,
                    },
                )
            for row in tables["Folder"]:
                parent_id = row["ParentFolderId"]
                mapped_parent_id = (
                    _require_mapping(mappings["Folder"], parent_id, "parent folder")
                    if parent_id is not None
                    else None
                )
                connection.execute(
                    "UPDATE Folder SET ParentFolderId = ? WHERE Id = ?",
                    (mapped_parent_id, mappings["Folder"][row["Id"]]),
                )

            for row in tables["CaseStudy"]:
                mappings["CaseStudy"][row["Id"]] = _insert_row(
                    connection,
                    "CaseStudy",
                    row,
                    {
                        "FolderId": _require_mapping(
                            mappings["Folder"],
                            row["FolderId"],
                            "case folder",
                        )
                    },
                )
            for row in tables["BoardConfiguration"]:
                mappings["BoardConfiguration"][row["Id"]] = _insert_row(
                    connection,
                    "BoardConfiguration",
                    row,
                )
            for row in tables["Board"]:
                mappings["Board"][row["Id"]] = _insert_row(
                    connection,
                    "Board",
                    row,
                    {
                        "CaseId": _require_mapping(
                            mappings["CaseStudy"],
                            row["CaseId"],
                            "board case",
                        ),
                        "BoardConfigurationId": _require_mapping(
                            mappings["BoardConfiguration"],
                            row["BoardConfigurationId"],
                            "board configuration",
                        ),
                    },
                )
            for row in tables["Scenario"]:
                mappings["Scenario"][row["Id"]] = _insert_row(
                    connection,
                    "Scenario",
                    row,
                    {
                        "BoardId": _require_mapping(
                            mappings["Board"],
                            row["BoardId"],
                            "scenario board",
                        )
                    },
                )
            for row in tables["Label"]:
                mappings["Label"][row["Id"]] = _insert_row(
                    connection,
                    "Label",
                    row,
                    {
                        "ScenarioId": _require_mapping(
                            mappings["Scenario"],
                            row["ScenarioId"],
                            "label scenario",
                        )
                    },
                )
            for row in tables["Test"]:
                mappings["Test"][row["Id"]] = _insert_row(
                    connection,
                    "Test",
                    row,
                    {"AdministrationId": admin_id},
                )
            for row in tables["Rule"]:
                mappings["Rule"][row["Id"]] = _insert_row(
                    connection,
                    "Rule",
                    row,
                )
            for row in tables["Test_Scenario"]:
                mappings["Test_Scenario"][row["Id"]] = _insert_row(
                    connection,
                    "Test_Scenario",
                    row,
                    {
                        "TestId": _require_mapping(
                            mappings["Test"],
                            row["TestId"],
                            "test scenario test",
                        ),
                        "ScenarioId": _require_mapping(
                            mappings["Scenario"],
                            row["ScenarioId"],
                            "test scenario",
                        ),
                        "RuleId": _require_mapping(
                            mappings["Rule"],
                            row["RuleId"],
                            "test scenario rule",
                        ),
                    },
                )

            for row in tables["Student"]:
                existing = connection.execute(
                    "SELECT Id, Password FROM Student WHERE Name = ?",
                    (row["Name"],),
                ).fetchone()
                if existing is not None:
                    if not _student_credentials_match(
                        row["Password"],
                        existing["Password"],
                    ):
                        raise ValueError(
                            f"A student named {row['Name']!r} already exists "
                            "with different credentials."
                        )
                    mappings["Student"][row["Id"]] = existing["Id"]
                else:
                    password = row["Password"]
                    if not is_password_hash(password):
                        password = hash_password(password)
                    mappings["Student"][row["Id"]] = _insert_row(
                        connection,
                        "Student",
                        row,
                        {"Password": password},
                    )

            for row in tables["Student_Test"]:
                connection.execute(
                    """
                    INSERT INTO Student_Test (
                        StudentId, TestId, AssignedAt, CompletedAt
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        _require_mapping(
                            mappings["Student"],
                            row["StudentId"],
                            "assigned student",
                        ),
                        _require_mapping(
                            mappings["Test"],
                            row["TestId"],
                            "assigned test",
                        ),
                        row["AssignedAt"],
                        row["CompletedAt"],
                    ),
                )
            for row in tables["Test_Result"]:
                source_student_id = row["StudentId"]
                student_id = (
                    _require_mapping(
                        mappings["Student"],
                        source_student_id,
                        "result student",
                    )
                    if source_student_id is not None
                    else None
                )
                _insert_row(
                    connection,
                    "Test_Result",
                    row,
                    {
                        "TestId": _require_mapping(
                            mappings["Test"],
                            row["TestId"],
                            "result test",
                        ),
                        "StudentId": student_id,
                    },
                )

            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise ValueError("The imported data violates database relationships.")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        summary = _payload_summary(payload)
        summary["destination_administrator_id"] = admin_id
        return summary


def _payload_summary(payload: dict) -> dict:
    tables = payload["tables"]
    summary = {
        "source_administrator": payload["source_administrator"],
        "counts": {
            table_name: len(rows)
            for table_name, rows in tables.items()
        },
    }
    destination = payload.get("destination_administrator")
    if destination is not None:
        summary["destination_administrator"] = destination["Name"]
    return summary
