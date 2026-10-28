# src/database/repository.py
import json
import re
import sqlite3
from typing import List, Optional, Dict, Any
from src.database.db_manager import DatabaseManager
from src.database.models import (
    Admin, Folder, CaseStudy, BoardConfiguration, Board, Scenario, Label, Test, Rule, TestResult
)
from src.security.passwords import hash_password, is_password_hash, verify_password


class Repository:
    def __init__(self):
        self.db = DatabaseManager()

    # --- Administration repository operations ---
    def get_admin_by_name(self, name: str) -> Optional[Admin]:
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Administration WHERE Name = ?", (name,))
            row = cursor.fetchone()
            return Admin.from_row(row)
        finally:
            conn.close()

    def get_admin_by_id(self, admin_id: int) -> Optional[Admin]:
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Administration WHERE Id = ?", (admin_id,))
            return Admin.from_row(cursor.fetchone())
        finally:
            conn.close()

    def create_admin(self, name: str, password: str) -> int:
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Administration (Name, Password) VALUES (?, ?)",
                (name.strip(), hash_password(password)),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def register_admin(self, name: str, password: str) -> tuple[int, int]:
        """Create an administrator and a starter folder/case atomically."""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Administration (Name, Password) VALUES (?, ?)",
                (name.strip(), hash_password(password)),
            )
            admin_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO Folder (AdministrationId, Name) VALUES (?, ?)",
                (admin_id, "Teaching Materials"),
            )
            folder_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO CaseStudy (FolderId, Name) VALUES (?, ?)",
                (folder_id, "My First Case"),
            )
            case_id = cursor.lastrowid
            conn.commit()
            return admin_id, case_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def authenticate_admin(self, name: str, password: str) -> Optional[Admin]:
        """Verify an administrator and upgrade a legacy plaintext password."""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM Administration WHERE Name = ?",
                (name.strip(),),
            )
            row = cursor.fetchone()
            if row is None or not verify_password(password, row["Password"]):
                return None

            stored_password = row["Password"]
            if not is_password_hash(stored_password):
                stored_password = hash_password(password)
                cursor.execute(
                    "UPDATE Administration SET Password = ? WHERE Id = ?",
                    (stored_password, row["Id"]),
                )
                conn.commit()

            return Admin(
                id=row["Id"],
                name=row["Name"],
                password=stored_password,
            )
        finally:
            conn.close()

    def create_student(self, name: str, password: str) -> int:
        normalized_name = name.strip()
        if not normalized_name or not password:
            raise ValueError("Student name and password are required.")
        if len(password) < 8:
            raise ValueError("Student passwords must contain at least 8 characters.")
        conn = self.db.get_connection()
        try:
            cursor = conn.execute(
                "INSERT INTO Student (Name, Password) VALUES (?, ?)",
                (normalized_name, hash_password(password)),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def update_student_password(self, student_id: int, password: str) -> None:
        if len(password) < 8:
            raise ValueError("Student passwords must contain at least 8 characters.")
        conn = self.db.get_connection()
        try:
            with conn:
                cursor = conn.execute(
                    "UPDATE Student SET Password = ? WHERE Id = ?",
                    (hash_password(password), student_id),
                )
                if cursor.rowcount != 1:
                    raise LookupError(f"Student {student_id} was not found.")
        finally:
            conn.close()

    def delete_student_account(self, student_id: int) -> None:
        conn = self.db.get_connection()
        try:
            with conn:
                student = conn.execute(
                    "SELECT Id FROM Student WHERE Id = ?", (student_id,)
                ).fetchone()
                if student is None:
                    raise LookupError(f"Student {student_id} was not found.")
                conn.execute(
                    "DELETE FROM Test_Result WHERE StudentId = ?",
                    (student_id,),
                )
                cursor = conn.execute(
                    "DELETE FROM Student WHERE Id = ?", (student_id,)
                )
                if cursor.rowcount != 1:
                    raise LookupError(f"Student {student_id} was not found.")
        finally:
            conn.close()

    def authenticate_student(self, student_id: int, password: str) -> Optional[dict]:
        conn = self.db.get_connection()
        try:
            row = conn.execute(
                "SELECT Id, Name, Password FROM Student WHERE Id = ?",
                (student_id,),
            ).fetchone()
            if row is None or not verify_password(password, row["Password"]):
                return None

            stored_password = row["Password"]
            if not is_password_hash(stored_password):
                conn.execute(
                    "UPDATE Student SET Password = ? WHERE Id = ?",
                    (hash_password(password), row["Id"]),
                )
                conn.commit()
            return {"id": row["Id"], "name": row["Name"]}
        finally:
            conn.close()

    def get_students(self) -> list[dict]:
        conn = self.db.get_connection()
        try:
            return [
                {"id": row["Id"], "name": row["Name"]}
                for row in conn.execute(
                    "SELECT Id, Name FROM Student ORDER BY Name COLLATE NOCASE, Id"
                )
            ]
        finally:
            conn.close()

    def assign_test_to_student(
        self, admin_id: int, student_id: int, test_id: int
    ) -> None:
        conn = self.db.get_connection()
        try:
            test = conn.execute(
                """
                SELECT Id FROM Test
                WHERE Id = ? AND AdministrationId = ?
                """,
                (test_id, admin_id),
            ).fetchone()
            student = conn.execute(
                "SELECT Id FROM Student WHERE Id = ?", (student_id,)
            ).fetchone()
            if test is None:
                raise LookupError(f"Test {test_id} was not found for this administrator.")
            if student is None:
                raise LookupError(f"Student {student_id} was not found.")
            assignment = conn.execute(
                """
                SELECT CompletedAt FROM Student_Test
                WHERE StudentId = ? AND TestId = ?
                """,
                (student_id, test_id),
            ).fetchone()
            if assignment is not None:
                if assignment["CompletedAt"] is not None:
                    raise ValueError("This student has already completed the test.")
                raise ValueError("This test is already assigned to the student.")
            conn.execute(
                "INSERT INTO Student_Test (StudentId, TestId) VALUES (?, ?)",
                (student_id, test_id),
            )
            conn.commit()
        finally:
            conn.close()

    def get_student_test_assignments(self, admin_id: int) -> list[dict]:
        conn = self.db.get_connection()
        try:
            rows = conn.execute(
                """
                SELECT st.StudentId, s.Name AS StudentName, st.TestId,
                       t.Name AS TestName, st.AssignedAt, st.CompletedAt
                FROM Student_Test st
                JOIN Student s ON s.Id = st.StudentId
                JOIN Test t ON t.Id = st.TestId
                WHERE t.AdministrationId = ?
                ORDER BY s.Name COLLATE NOCASE, t.Name COLLATE NOCASE
                """,
                (admin_id,),
            ).fetchall()
            return [
                {
                    "student_id": row["StudentId"],
                    "student_name": row["StudentName"],
                    "test_id": row["TestId"],
                    "test_name": row["TestName"],
                    "assigned_at": row["AssignedAt"],
                    "completed_at": row["CompletedAt"],
                }
                for row in rows
            ]
        finally:
            conn.close()

    def remove_test_assignment(self, admin_id: int, student_id: int, test_id: int):
        conn = self.db.get_connection()
        try:
            assignment = conn.execute(
                """
                SELECT st.CompletedAt
                FROM Student_Test st
                JOIN Test t ON t.Id = st.TestId
                WHERE st.StudentId = ? AND st.TestId = ?
                  AND t.AdministrationId = ?
                """,
                (student_id, test_id, admin_id),
            ).fetchone()
            if assignment is None:
                raise LookupError("The test assignment was not found.")
            if assignment["CompletedAt"] is not None:
                raise ValueError("A completed test assignment cannot be removed.")
            conn.execute(
                "DELETE FROM Student_Test WHERE StudentId = ? AND TestId = ?",
                (student_id, test_id),
            )
            conn.commit()
        finally:
            conn.close()

    def get_available_tests_for_student(self, student_id: int) -> list[dict]:
        conn = self.db.get_connection()
        try:
            rows = conn.execute(
                """
                SELECT t.Id, t.Name
                FROM Student_Test st
                JOIN Test t ON t.Id = st.TestId
                WHERE st.StudentId = ? AND st.CompletedAt IS NULL
                ORDER BY t.Name COLLATE NOCASE, t.Id
                """,
                (student_id,),
            ).fetchall()
            return [{"id": row["Id"], "name": row["Name"]} for row in rows]
        finally:
            conn.close()

    def get_assigned_test_by_name(
        self, student_id: int, name: str
    ) -> Optional[dict]:
        conn = self.db.get_connection()
        try:
            rows = conn.execute(
                """
                SELECT t.Id, t.AdministrationId
                FROM Student_Test st
                JOIN Test t ON t.Id = st.TestId
                WHERE st.StudentId = ? AND st.CompletedAt IS NULL
                  AND lower(trim(t.Name)) = lower(trim(?))
                """,
                (student_id, name),
            ).fetchall()
        finally:
            conn.close()
        if not rows:
            return None
        if len(rows) > 1:
            raise ValueError(
                "More than one available test has that name; ask the administrator "
                "to make the assigned test names unique."
            )
        return next(
            (
                test
                for test in self.get_tests_by_admin(rows[0]["AdministrationId"])
                if test["id"] == rows[0]["Id"]
            ),
            None,
        )

    def get_administrators(self) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        try:
            rows = conn.execute(
                """
                SELECT Id, Name
                FROM Administration
                ORDER BY Name COLLATE NOCASE
                """
            ).fetchall()
            return [{"id": row["Id"], "name": row["Name"]} for row in rows]
        finally:
            conn.close()

    def get_administrator_asset_counts(self, admin_id: int) -> Dict[str, int]:
        conn = self.db.get_connection()
        try:
            row = conn.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM Folder
                     WHERE AdministrationId = ?) AS folders,
                    (SELECT COUNT(*) FROM CaseStudy c
                     JOIN Folder f ON f.Id = c.FolderId
                     WHERE f.AdministrationId = ?) AS cases,
                    (SELECT COUNT(*) FROM Board b
                     JOIN CaseStudy c ON c.Id = b.CaseId
                     JOIN Folder f ON f.Id = c.FolderId
                     WHERE f.AdministrationId = ?) AS boards,
                    (SELECT COUNT(*) FROM Scenario s
                     JOIN Board b ON b.Id = s.BoardId
                     JOIN CaseStudy c ON c.Id = b.CaseId
                     JOIN Folder f ON f.Id = c.FolderId
                     WHERE f.AdministrationId = ?) AS scenarios,
                    (SELECT COUNT(*) FROM Label l
                     JOIN Scenario s ON s.Id = l.ScenarioId
                     JOIN Board b ON b.Id = s.BoardId
                     JOIN CaseStudy c ON c.Id = b.CaseId
                     JOIN Folder f ON f.Id = c.FolderId
                     WHERE f.AdministrationId = ?) AS labels
                """,
                (admin_id,) * 5,
            ).fetchone()
            return {key: row[key] for key in row.keys()}
        finally:
            conn.close()

    # --- Test construction repository operations ---
    def get_test_assets_by_admin(self, admin_id: int) -> Dict[str, list]:
        """Return the administrator's cases and scenarios for test construction."""
        conn = self.db.get_connection()
        try:
            cases = conn.execute(
                """
                SELECT c.Id, c.Name
                FROM CaseStudy c
                JOIN Folder f ON f.Id = c.FolderId
                WHERE f.AdministrationId = ?
                ORDER BY c.Name COLLATE NOCASE, c.Id
                """,
                (admin_id,),
            ).fetchall()
            scenarios = conn.execute(
                """
                SELECT s.Id, s.Name, s.Contract, b.CaseId, c.Name AS CaseName
                FROM Scenario s
                JOIN Board b ON b.Id = s.BoardId
                JOIN CaseStudy c ON c.Id = b.CaseId
                JOIN Folder f ON f.Id = c.FolderId
                WHERE f.AdministrationId = ?
                ORDER BY c.Name COLLATE NOCASE, b.Id, s.Id
                """,
                (admin_id,),
            ).fetchall()
            return {
                "cases": [
                    {"id": row["Id"], "name": row["Name"]} for row in cases
                ],
                "scenarios": [
                    {
                        "id": row["Id"],
                        "name": row["Name"].strip() or f"Scenario #{row['Id']}",
                        "contract": row["Contract"].strip().upper(),
                        "case_id": row["CaseId"],
                        "case_name": row["CaseName"],
                    }
                    for row in scenarios
                ],
            }
        finally:
            conn.close()

    def get_tests_by_admin(self, admin_id: int) -> list[dict]:
        conn = self.db.get_connection()
        try:
            test_rows = conn.execute(
                """
                SELECT Id, Name FROM Test
                WHERE AdministrationId = ?
                ORDER BY Name COLLATE NOCASE, Id
                """,
                (admin_id,),
            ).fetchall()
            tests = []
            for test_row in test_rows:
                problem_rows = conn.execute(
                    """
                    SELECT ts.Sequence, ts.ScenarioId, r.Id AS RuleId,
                           r.Contracts, r.Rules, s.Name, s.BiddingRoute,
                           s.Information, b.CaseId
                    FROM Test_Scenario ts
                    JOIN Rule r ON r.Id = ts.RuleId
                    JOIN Scenario s ON s.Id = ts.ScenarioId
                    JOIN Board b ON b.Id = s.BoardId
                    WHERE ts.TestId = ?
                    ORDER BY ts.Sequence, ts.Id
                    """,
                    (test_row["Id"],),
                ).fetchall()
                problems_by_sequence = {}
                for row in problem_rows:
                    rule_data = json.loads(row["Rules"])
                    problem = problems_by_sequence.get(row["Sequence"])
                    if problem is None:
                        problem = {
                            "sequence": row["Sequence"],
                            "source_type": "case",
                            "case_id": rule_data.get("case_id") or row["CaseId"],
                            "scenario_ids": [],
                            "scenario_bidding_routes": {},
                            "scenario_information": {},
                            "contracts": [],
                            "results": rule_data.get("results", ["="]),
                            "scores": {},
                            "scenario_scores": {},
                        }
                        problems_by_sequence[row["Sequence"]] = problem
                    problem["scenario_ids"].append(row["ScenarioId"])
                    scenario_rule_scores = rule_data.get("scores", {})
                    problem["scenario_scores"][row["ScenarioId"]] = (
                        scenario_rule_scores
                    )
                    for contract in json.loads(row["Contracts"]):
                        if contract not in problem["contracts"]:
                            problem["contracts"].append(contract)
                        problem["scores"].setdefault(
                            contract,
                            scenario_rule_scores.get(contract, {}),
                        )
                    problem["scenario_bidding_routes"][row["ScenarioId"]] = (
                        row["BiddingRoute"]
                    )
                    problem["scenario_information"][row["ScenarioId"]] = (
                        row["Information"]
                    )
                tests.append(
                    {
                        "id": test_row["Id"],
                        "name": test_row["Name"],
                        "problems": list(problems_by_sequence.values()),
                    }
                )
            return tests
        finally:
            conn.close()

    def get_test_by_name(self, admin_id: int, name: str) -> Optional[dict]:
        target = name.strip().casefold()
        return next(
            (
                test
                for test in self.get_tests_by_admin(admin_id)
                if test["name"].strip().casefold() == target
            ),
            None,
        )

    def get_test_results_by_admin(self, admin_id: int) -> list[dict]:
        conn = self.db.get_connection()
        try:
            rows = conn.execute(
                """
                SELECT tr.Id, tr.TestId, t.Name AS TestName, tr.StudentId,
                       COALESCE(s.Name, tr.ApplicantName) AS StudentName,
                       tr.Contracts, tr.Score, tr.SubmittedAt
                FROM Test_Result tr
                JOIN Test t ON t.Id = tr.TestId
                LEFT JOIN Student s ON s.Id = tr.StudentId
                WHERE t.AdministrationId = ?
                ORDER BY tr.SubmittedAt DESC, tr.Id DESC
                """,
                (admin_id,),
            ).fetchall()
            return [
                {
                    "id": row["Id"],
                    "test_id": row["TestId"],
                    "test_name": row["TestName"],
                    "student_id": row["StudentId"],
                    "student_name": row["StudentName"],
                    "contracts": json.loads(row["Contracts"]),
                    "score": row["Score"],
                    "submitted_at": row["SubmittedAt"],
                }
                for row in rows
            ]
        finally:
            conn.close()

    def get_test_report_data(self, admin_id: int) -> dict:
        conn = self.db.get_connection()
        try:
            administrator = conn.execute(
                "SELECT Name FROM Administration WHERE Id = ?",
                (admin_id,),
            ).fetchone()
            if administrator is None:
                raise LookupError(f"Administrator {admin_id} was not found.")

            scenario_rows = conn.execute(
                """
                SELECT s.Id, s.Name, c.Name AS CaseName,
                       b.Description AS BoardName
                FROM Scenario s
                JOIN Board b ON b.Id = s.BoardId
                JOIN CaseStudy c ON c.Id = b.CaseId
                JOIN Folder f ON f.Id = c.FolderId
                WHERE f.AdministrationId = ?
                """,
                (admin_id,),
            ).fetchall()
            scenarios = {
                row["Id"]: {
                    "id": row["Id"],
                    "name": row["Name"],
                    "case_name": row["CaseName"],
                    "board_name": row["BoardName"],
                }
                for row in scenario_rows
            }
        finally:
            conn.close()

        return {
            "administrator": administrator["Name"],
            "tests": self.get_tests_by_admin(admin_id),
            "results": self.get_test_results_by_admin(admin_id),
            "scenarios": scenarios,
        }

    def get_scenario_id_by_names(
        self, admin_id: int, board_name: str, scenario_name: str
    ) -> Optional[int]:
        conn = self.db.get_connection()
        try:
            row = conn.execute(
                """
                SELECT s.Id
                FROM Scenario s
                JOIN Board b ON b.Id = s.BoardId
                JOIN CaseStudy c ON c.Id = b.CaseId
                JOIN Folder f ON f.Id = c.FolderId
                WHERE f.AdministrationId = ?
                  AND lower(trim(COALESCE(b.Description, ''))) = lower(trim(?))
                  AND lower(trim(s.Name)) = lower(trim(?))
                ORDER BY s.Id
                LIMIT 1
                """,
                (admin_id, board_name, scenario_name),
            ).fetchone()
            return row["Id"] if row else None
        finally:
            conn.close()

    def save_test_result(
        self, test_id: int, student_id: int, scenario_results: list, score: int
    ):
        conn = self.db.get_connection()
        try:
            assignment = conn.execute(
                """
                SELECT CompletedAt FROM Student_Test
                WHERE StudentId = ? AND TestId = ?
                """,
                (student_id, test_id),
            ).fetchone()
            if assignment is None:
                raise LookupError("This test is not assigned to the student.")
            if assignment["CompletedAt"] is not None:
                raise ValueError("This student has already completed the test.")
            student = conn.execute(
                "SELECT Name FROM Student WHERE Id = ?", (student_id,)
            ).fetchone()
            if student is None:
                raise LookupError(f"Student {student_id} was not found.")
            conn.execute(
                """
                INSERT INTO Test_Result (
                    TestId, StudentId, ApplicantName, Contracts, Score
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    test_id,
                    student_id,
                    student["Name"],
                    json.dumps(scenario_results),
                    int(score),
                ),
            )
            updated = conn.execute(
                """
                UPDATE Student_Test
                SET CompletedAt = CURRENT_TIMESTAMP
                WHERE StudentId = ? AND TestId = ? AND CompletedAt IS NULL
                """,
                (student_id, test_id),
            )
            if updated.rowcount != 1:
                raise ValueError("This test assignment is no longer available.")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def duplicate_asset(self, admin_id: int, node_type: str, node_id: int) -> int:
        """Duplicate an owned asset and all descendants in a single transaction."""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()

            def copied_name(name):
                return f"{name} (Copy)"

            def copy_scenario(old_id: int, new_board_id: int) -> int:
                row = cursor.execute(
                    "SELECT * FROM Scenario WHERE Id = ?", (old_id,)
                ).fetchone()
                if row is None:
                    raise LookupError(f"Scenario {old_id} was not found.")
                cursor.execute(
                    """
                    INSERT INTO Scenario (
                        BoardId, Name, Information, BiddingRoute, Declarer, Contract,
                        RiskStatus, IsTargeted, TargetedSequence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_board_id,
                        copied_name(row["Name"]),
                        row["Information"],
                        row["BiddingRoute"],
                        row["Declarer"],
                        row["Contract"],
                        row["RiskStatus"],
                        row["IsTargeted"],
                        row["TargetedSequence"],
                    ),
                )
                new_id = cursor.lastrowid
                cursor.execute(
                    """
                    INSERT INTO Label (ScenarioId, Sequence, Color, Card)
                    SELECT ?, Sequence, Color, Card
                    FROM Label WHERE ScenarioId = ?
                    """,
                    (new_id, old_id),
                )
                return new_id

            def copy_board(old_id: int, new_case_id: int) -> int:
                row = cursor.execute(
                    "SELECT * FROM Board WHERE Id = ?", (old_id,)
                ).fetchone()
                if row is None:
                    raise LookupError(f"Board {old_id} was not found.")
                config = cursor.execute(
                    "SELECT * FROM BoardConfiguration WHERE Id = ?",
                    (row["BoardConfigurationId"],),
                ).fetchone()
                cursor.execute(
                    "INSERT INTO BoardConfiguration (Dealer, Vulnerability) VALUES (?, ?)",
                    (config["Dealer"], config["Vulnerability"]),
                )
                new_config_id = cursor.lastrowid
                cursor.execute(
                    """
                    INSERT INTO Board (
                        CaseId, BoardConfigurationId, SouthHandPbn, WestHandPbn,
                        NorthHandPbn, EastHandPbn, Description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_case_id,
                        new_config_id,
                        row["SouthHandPbn"],
                        row["WestHandPbn"],
                        row["NorthHandPbn"],
                        row["EastHandPbn"],
                        copied_name(row["Description"] or "Board"),
                    ),
                )
                new_board_id = cursor.lastrowid
                for scenario in cursor.execute(
                    "SELECT Id FROM Scenario WHERE BoardId = ?", (old_id,)
                ).fetchall():
                    copy_scenario(scenario["Id"], new_board_id)
                return new_board_id

            def copy_case(old_id: int, new_folder_id: int) -> int:
                row = cursor.execute(
                    "SELECT * FROM CaseStudy WHERE Id = ?", (old_id,)
                ).fetchone()
                cursor.execute(
                    "INSERT INTO CaseStudy (FolderId, Name) VALUES (?, ?)",
                    (new_folder_id, copied_name(row["Name"])),
                )
                new_case_id = cursor.lastrowid
                for board in cursor.execute(
                    "SELECT Id FROM Board WHERE CaseId = ?", (old_id,)
                ).fetchall():
                    copy_board(board["Id"], new_case_id)
                return new_case_id

            def copy_folder(old_id: int, new_parent_id: Optional[int]) -> int:
                row = cursor.execute(
                    "SELECT * FROM Folder WHERE Id = ? AND AdministrationId = ?",
                    (old_id, admin_id),
                ).fetchone()
                if row is None:
                    raise LookupError(f"Folder {old_id} was not found.")
                cursor.execute(
                    """
                    INSERT INTO Folder (AdministrationId, ParentFolderId, Name)
                    VALUES (?, ?, ?)
                    """,
                    (admin_id, new_parent_id, copied_name(row["Name"])),
                )
                new_id = cursor.lastrowid
                for case in cursor.execute(
                    "SELECT Id FROM CaseStudy WHERE FolderId = ?", (old_id,)
                ).fetchall():
                    copy_case(case["Id"], new_id)
                for child in cursor.execute(
                    "SELECT Id FROM Folder WHERE ParentFolderId = ?", (old_id,)
                ).fetchall():
                    copy_folder(child["Id"], new_id)
                return new_id

            if node_type == "folder":
                row = cursor.execute(
                    """
                    SELECT ParentFolderId FROM Folder
                    WHERE Id = ? AND AdministrationId = ?
                    """,
                    (node_id, admin_id),
                ).fetchone()
                if row is None:
                    raise LookupError(f"Folder {node_id} was not found.")
                result_id = copy_folder(node_id, row["ParentFolderId"])
            elif node_type == "case":
                row = cursor.execute(
                    """
                    SELECT c.Id, c.FolderId FROM CaseStudy c
                    JOIN Folder f ON f.Id = c.FolderId
                    WHERE c.Id = ? AND f.AdministrationId = ?
                    """,
                    (node_id, admin_id),
                ).fetchone()
                if row is None:
                    raise LookupError(f"Case {node_id} was not found.")
                result_id = copy_case(node_id, row["FolderId"])
            elif node_type == "board":
                row = cursor.execute(
                    """
                    SELECT b.Id, b.CaseId FROM Board b
                    JOIN CaseStudy c ON c.Id = b.CaseId
                    JOIN Folder f ON f.Id = c.FolderId
                    WHERE b.Id = ? AND f.AdministrationId = ?
                    """,
                    (node_id, admin_id),
                ).fetchone()
                if row is None:
                    raise LookupError(f"Board {node_id} was not found.")
                result_id = copy_board(node_id, row["CaseId"])
            elif node_type == "scenario":
                row = cursor.execute(
                    """
                    SELECT s.Id, s.BoardId FROM Scenario s
                    JOIN Board b ON b.Id = s.BoardId
                    JOIN CaseStudy c ON c.Id = b.CaseId
                    JOIN Folder f ON f.Id = c.FolderId
                    WHERE s.Id = ? AND f.AdministrationId = ?
                    """,
                    (node_id, admin_id),
                ).fetchone()
                if row is None:
                    raise LookupError(f"Scenario {node_id} was not found.")
                result_id = copy_scenario(node_id, row["BoardId"])
            else:
                raise ValueError(f"Cannot duplicate asset type: {node_type}")
            conn.commit()
            return result_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def save_test(
        self,
        admin_id: int,
        name: str,
        problems: list[dict],
        test_id: Optional[int] = None,
    ) -> int:
        """Create or replace a test and its problems atomically."""
        test_name = name.strip()
        if not test_name:
            raise ValueError("A test title is required.")
        if not problems:
            raise ValueError("Add at least one problem to the test.")

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            if test_id is None:
                cursor.execute(
                    "INSERT INTO Test (AdministrationId, Name) VALUES (?, ?)",
                    (admin_id, test_name),
                )
                test_id = cursor.lastrowid
            else:
                cursor.execute(
                    "UPDATE Test SET Name = ? "
                    "WHERE Id = ? AND AdministrationId = ?",
                    (test_name, test_id, admin_id),
                )
                if cursor.rowcount == 0:
                    raise LookupError(f"Test {test_id} was not found.")
                cursor.execute("DELETE FROM Test_Scenario WHERE TestId = ?", (test_id,))
                cursor.execute(
                    """
                    DELETE FROM Rule
                    WHERE Id NOT IN (SELECT RuleId FROM Test_Scenario)
                    """
                )

            for sequence, problem in enumerate(problems, start=1):
                source_type = problem.get("source_type")
                if source_type == "case":
                    case_id = problem.get("case_id")
                    if not case_id:
                        raise ValueError(f"Problem {sequence} needs a case.")
                    owned_case = cursor.execute(
                        """
                        SELECT 1 FROM CaseStudy c
                        JOIN Folder f ON f.Id = c.FolderId
                        WHERE c.Id = ? AND f.AdministrationId = ?
                        """,
                        (case_id, admin_id),
                    ).fetchone()
                    if owned_case is None:
                        raise ValueError(f"Problem {sequence} uses an unavailable case.")
                    scenario_rows = cursor.execute(
                        """
                        SELECT s.Id FROM Scenario s
                        JOIN Board b ON b.Id = s.BoardId
                        WHERE b.CaseId = ? ORDER BY b.Id, s.Id
                        """,
                        (case_id,),
                    ).fetchall()
                    available_scenario_ids = [row["Id"] for row in scenario_rows]
                    available_scenario_id_set = set(available_scenario_ids)
                    scenario_ids = problem.get("scenario_ids")
                    if scenario_ids is None:
                        scenario_ids = available_scenario_ids
                    if (
                        not isinstance(scenario_ids, list)
                        or not scenario_ids
                        or any(
                            not isinstance(scenario_id, int)
                            for scenario_id in scenario_ids
                        )
                        or len(scenario_ids) != len(set(scenario_ids))
                        or any(
                            scenario_id not in available_scenario_id_set
                            for scenario_id in scenario_ids
                        )
                    ):
                        raise ValueError(
                            f"Problem {sequence} must select scenarios from its case."
                        )
                else:
                    raise ValueError(f"Problem {sequence} must use a specific case.")

                selected_rows = cursor.execute(
                    """
                    SELECT s.Id, s.Contract
                    FROM Scenario s
                    JOIN Board b ON b.Id = s.BoardId
                    WHERE b.CaseId = ?
                    """,
                    (case_id,),
                ).fetchall()
                contracts_by_scenario = {
                    row["Id"]: row["Contract"].strip().upper()
                    for row in selected_rows
                }
                selected_contracts = []
                for scenario_id in scenario_ids:
                    contract = contracts_by_scenario.get(scenario_id, "")
                    if not contract:
                        raise ValueError(
                            f"Scenario {scenario_id} has no final contract."
                        )
                    if contract not in selected_contracts:
                        selected_contracts.append(contract)
                if not selected_contracts:
                    raise ValueError(
                        f"Problem {sequence} has no scenarios with final contracts."
                    )

                contracts = [
                    str(value).strip().upper()
                    for value in problem["contracts"]
                ]
                if contracts != selected_contracts:
                    raise ValueError(
                        f"Problem {sequence}'s contracts must match the selected "
                        "scenarios' final contracts."
                    )
                results = [str(value).strip() for value in problem["results"]]
                scores = problem.get("scores", {})
                scenario_scores = problem.get("scenario_scores")
                if not contracts or any(not value for value in contracts):
                    raise ValueError(f"Problem {sequence} needs acceptable contracts.")
                if not results or any(not value for value in results):
                    raise ValueError(f"Problem {sequence} needs acceptable results.")
                if any(
                    result != "="
                    and re.fullmatch(r"[+-](?:[1-9]|1[0-3])", result) is None
                    for result in results
                ):
                    raise ValueError(
                        f"Problem {sequence} has an invalid result stasis."
                    )
                if (
                    len(contracts) != len(set(contracts))
                    or len(results) != len(set(results))
                ):
                    raise ValueError(
                        f"Problem {sequence} has duplicate matrix headings."
                    )
                if (
                    scenario_scores is not None
                    and not isinstance(scenario_scores, dict)
                ):
                    raise ValueError(
                        f"Problem {sequence} has an invalid scoring matrix."
                    )

                normalized_scenario_scores = {}
                try:
                    for scenario_id in scenario_ids:
                        contract = contracts_by_scenario[scenario_id]
                        if scenario_scores is None:
                            scenario_contract_scores = scores
                        else:
                            scenario_contract_scores = scenario_scores.get(
                                scenario_id,
                                scenario_scores.get(str(scenario_id)),
                            )
                            if not isinstance(scenario_contract_scores, dict):
                                raise ValueError
                        normalized_scenario_scores[scenario_id] = {
                            contract: {
                                result: int(
                                    scenario_contract_scores[contract][result]
                                )
                                for result in results
                            }
                        }
                except (KeyError, TypeError, ValueError) as error:
                    raise ValueError(
                        f"Problem {sequence} has an invalid scoring matrix."
                    ) from error

                for scenario_id in scenario_ids:
                    contract = contracts_by_scenario[scenario_id]
                    rule_data = {
                        "source_type": source_type,
                        "case_id": case_id,
                        "results": results,
                        "scores": normalized_scenario_scores[scenario_id],
                    }
                    cursor.execute(
                        "INSERT INTO Rule (Contracts, Rules) VALUES (?, ?)",
                        (json.dumps([contract]), json.dumps(rule_data)),
                    )
                    rule_id = cursor.lastrowid
                    cursor.execute(
                        """
                        INSERT INTO Test_Scenario (TestId, Sequence, ScenarioId, RuleId)
                        VALUES (?, ?, ?, ?)
                        """,
                        (test_id, sequence, scenario_id, rule_id),
                    )
            conn.commit()
            return test_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def delete_test(self, admin_id: int, test_id: int):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM Test WHERE Id = ? AND AdministrationId = ?",
                (test_id, admin_id),
            )
            if cursor.rowcount == 0:
                raise LookupError(f"Test {test_id} was not found.")
            cursor.execute(
                "DELETE FROM Rule WHERE Id NOT IN "
                "(SELECT RuleId FROM Test_Scenario)"
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def move_asset(
        self,
        admin_id: int,
        node_type: str,
        node_id: int,
        target_parent_id: Optional[int],
    ) -> bool:
        """Move an owned asset under a valid parent without changing its ID."""
        conn = self.db.get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()

            if node_type == "folder":
                source = cursor.execute(
                    """
                    SELECT Id, ParentFolderId
                    FROM Folder
                    WHERE Id = ? AND AdministrationId = ?
                    """,
                    (node_id, admin_id),
                ).fetchone()
                if source is None:
                    raise LookupError(f"Folder {node_id} was not found.")
                if target_parent_id is not None:
                    target = cursor.execute(
                        """
                        SELECT Id FROM Folder
                        WHERE Id = ? AND AdministrationId = ?
                        """,
                        (target_parent_id, admin_id),
                    ).fetchone()
                    if target is None:
                        raise LookupError(
                            f"Destination folder {target_parent_id} was not found."
                        )
                    descendant = cursor.execute(
                        """
                        WITH RECURSIVE descendants(Id) AS (
                            SELECT Id FROM Folder WHERE Id = ?
                            UNION
                            SELECT Folder.Id
                            FROM Folder
                            JOIN descendants
                              ON Folder.ParentFolderId = descendants.Id
                        )
                        SELECT 1 FROM descendants WHERE Id = ?
                        """,
                        (node_id, target_parent_id),
                    ).fetchone()
                    if descendant is not None:
                        raise ValueError(
                            "A folder cannot be moved into itself or a descendant."
                        )
                if source["ParentFolderId"] == target_parent_id:
                    conn.rollback()
                    return False
                cursor.execute(
                    """
                    UPDATE Folder SET ParentFolderId = ?
                    WHERE Id = ? AND AdministrationId = ?
                    """,
                    (target_parent_id, node_id, admin_id),
                )

            elif node_type == "case":
                source = cursor.execute(
                    """
                    SELECT CaseStudy.Id, CaseStudy.FolderId
                    FROM CaseStudy
                    JOIN Folder ON Folder.Id = CaseStudy.FolderId
                    WHERE CaseStudy.Id = ? AND Folder.AdministrationId = ?
                    """,
                    (node_id, admin_id),
                ).fetchone()
                if source is None:
                    raise LookupError(f"Case {node_id} was not found.")
                target = cursor.execute(
                    """
                    SELECT Id FROM Folder
                    WHERE Id = ? AND AdministrationId = ?
                    """,
                    (target_parent_id, admin_id),
                ).fetchone()
                if target is None:
                    raise LookupError(
                        f"Destination folder {target_parent_id} was not found."
                    )
                if source["FolderId"] == target_parent_id:
                    conn.rollback()
                    return False
                cursor.execute(
                    "UPDATE CaseStudy SET FolderId = ? WHERE Id = ?",
                    (target_parent_id, node_id),
                )

            elif node_type == "board":
                source = cursor.execute(
                    """
                    SELECT Board.Id, Board.CaseId
                    FROM Board
                    JOIN CaseStudy ON CaseStudy.Id = Board.CaseId
                    JOIN Folder ON Folder.Id = CaseStudy.FolderId
                    WHERE Board.Id = ? AND Folder.AdministrationId = ?
                    """,
                    (node_id, admin_id),
                ).fetchone()
                if source is None:
                    raise LookupError(f"Board {node_id} was not found.")
                target = cursor.execute(
                    """
                    SELECT CaseStudy.Id
                    FROM CaseStudy
                    JOIN Folder ON Folder.Id = CaseStudy.FolderId
                    WHERE CaseStudy.Id = ? AND Folder.AdministrationId = ?
                    """,
                    (target_parent_id, admin_id),
                ).fetchone()
                if target is None:
                    raise LookupError(
                        f"Destination case {target_parent_id} was not found."
                    )
                if source["CaseId"] == target_parent_id:
                    conn.rollback()
                    return False
                cursor.execute(
                    "UPDATE Board SET CaseId = ? WHERE Id = ?",
                    (target_parent_id, node_id),
                )

            elif node_type == "scenario":
                source = cursor.execute(
                    """
                    SELECT Scenario.Id, Scenario.BoardId
                    FROM Scenario
                    JOIN Board ON Board.Id = Scenario.BoardId
                    JOIN CaseStudy ON CaseStudy.Id = Board.CaseId
                    JOIN Folder ON Folder.Id = CaseStudy.FolderId
                    WHERE Scenario.Id = ? AND Folder.AdministrationId = ?
                    """,
                    (node_id, admin_id),
                ).fetchone()
                if source is None:
                    raise LookupError(f"Scenario {node_id} was not found.")
                target = cursor.execute(
                    """
                    SELECT Board.Id
                    FROM Board
                    JOIN CaseStudy ON CaseStudy.Id = Board.CaseId
                    JOIN Folder ON Folder.Id = CaseStudy.FolderId
                    WHERE Board.Id = ? AND Folder.AdministrationId = ?
                    """,
                    (target_parent_id, admin_id),
                ).fetchone()
                if target is None:
                    raise LookupError(
                        f"Destination board {target_parent_id} was not found."
                    )
                if source["BoardId"] == target_parent_id:
                    conn.rollback()
                    return False
                cursor.execute(
                    "UPDATE Scenario SET BoardId = ? WHERE Id = ?",
                    (target_parent_id, node_id),
                )

            else:
                raise ValueError(f"Unsupported asset type: {node_type}")

            if cursor.rowcount != 1:
                raise LookupError(f"{node_type.title()} {node_id} was not found.")
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # --- Folder repository operations ---
    def get_folders_by_admin(self, admin_id: int) -> List[Folder]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Folder WHERE AdministrationId = ?", (admin_id,))
        rows = cursor.fetchall()
        conn.close()
        return [Folder.from_row(row) for row in rows]

    def get_folder_by_id(self, folder_id: int) -> Optional[Folder]:
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Folder WHERE Id = ?", (folder_id,))
            return Folder.from_row(cursor.fetchone())
        finally:
            conn.close()

    def rename_folder(self, folder_id: int, name: str):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE Folder SET Name = ? WHERE Id = ?", (name, folder_id))
            if cursor.rowcount == 0:
                raise LookupError(f"Folder {folder_id} was not found.")
            conn.commit()
        finally:
            conn.close()

    def delete_folder(self, folder_id: int):
        self._delete_by_id("Folder", folder_id)

    def create_folder(self, administration_id: int, parent_folder_id: Optional[int], name: str) -> int:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Folder (AdministrationId, ParentFolderId, Name) VALUES (?, ?, ?)",
            (administration_id, parent_folder_id, name)
        )
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    # --- CaseStudy repository operations ---
    def get_cases_by_folder(self, folder_id: int) -> List[CaseStudy]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM CaseStudy WHERE FolderId = ?", (folder_id,))
        rows = cursor.fetchall()
        conn.close()
        return [CaseStudy.from_row(row) for row in rows]

    def get_case_by_id(self, case_id: int) -> Optional[CaseStudy]:
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM CaseStudy WHERE Id = ?", (case_id,))
            return CaseStudy.from_row(cursor.fetchone())
        finally:
            conn.close()

    def rename_case(self, case_id: int, name: str):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE CaseStudy SET Name = ? WHERE Id = ?", (name, case_id))
            if cursor.rowcount == 0:
                raise LookupError(f"Case {case_id} was not found.")
            conn.commit()
        finally:
            conn.close()

    def delete_case(self, case_id: int):
        self._delete_by_id("CaseStudy", case_id)

    def create_case(self, folder_id: int, name: str) -> int:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO CaseStudy (FolderId, Name) VALUES (?, ?)", (folder_id, name))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    # --- Board and configuration repository operations ---
    def create_board_configuration(self, dealer: str, vulnerability: str) -> int:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO BoardConfiguration (Dealer, Vulnerability) VALUES (?, ?)", (dealer, vulnerability))
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    def create_board(self, case_id: int, config_id: int, south: str, west: str, north: str, east: str, description: Optional[str] = None) -> int:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO Board (CaseId, BoardConfigurationId, SouthHandPbn, WestHandPbn, NorthHandPbn, EastHandPbn, Description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (case_id, config_id, south, west, north, east, description)
        )
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    def save_board(
        self,
        case_id: int,
        hands: Dict[str, str],
        dealer: str,
        vulnerability: str,
        description: Optional[str] = None,
        board_id: Optional[int] = None,
    ) -> int:
        """Create or update a board and its configuration in one transaction."""
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            if board_id is None:
                cursor.execute(
                    "INSERT INTO BoardConfiguration (Dealer, Vulnerability) VALUES (?, ?)",
                    (dealer, vulnerability),
                )
                configuration_id = cursor.lastrowid
                cursor.execute(
                    """INSERT INTO Board (
                        CaseId, BoardConfigurationId, SouthHandPbn, WestHandPbn,
                        NorthHandPbn, EastHandPbn, Description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        case_id,
                        configuration_id,
                        hands["SOUTH"],
                        hands["WEST"],
                        hands["NORTH"],
                        hands["EAST"],
                        description,
                    ),
                )
                board_id = cursor.lastrowid
            else:
                cursor.execute(
                    "SELECT BoardConfigurationId FROM Board WHERE Id = ?",
                    (board_id,),
                )
                board_row = cursor.fetchone()
                if board_row is None:
                    raise LookupError(f"Board {board_id} was not found.")
                old_configuration_id = board_row["BoardConfigurationId"]
                cursor.execute(
                    "SELECT COUNT(*) FROM Board WHERE BoardConfigurationId = ?",
                    (old_configuration_id,),
                )
                configuration_users = cursor.fetchone()[0]
                if configuration_users == 1:
                    configuration_id = old_configuration_id
                    cursor.execute(
                        """UPDATE BoardConfiguration
                           SET Dealer = ?, Vulnerability = ? WHERE Id = ?""",
                        (dealer, vulnerability, configuration_id),
                    )
                else:
                    cursor.execute(
                        "INSERT INTO BoardConfiguration (Dealer, Vulnerability) VALUES (?, ?)",
                        (dealer, vulnerability),
                    )
                    configuration_id = cursor.lastrowid
                cursor.execute(
                    """UPDATE Board
                       SET CaseId = ?, BoardConfigurationId = ?, SouthHandPbn = ?,
                           WestHandPbn = ?, NorthHandPbn = ?, EastHandPbn = ?,
                           Description = ?
                       WHERE Id = ?""",
                    (
                        case_id,
                        configuration_id,
                        hands["SOUTH"],
                        hands["WEST"],
                        hands["NORTH"],
                        hands["EAST"],
                        description,
                        board_id,
                    ),
                )
            conn.commit()
            return board_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def delete_board(self, board_id: int):
        self._delete_by_id("Board", board_id)

    def get_boards_by_case(self, case_id: int) -> List[Board]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Board WHERE CaseId = ?", (case_id,))
        rows = cursor.fetchall()
        conn.close()
        return [Board.from_row(row) for row in rows]

    def get_board_by_id(self, board_id: int) -> Optional[Board]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Board WHERE Id = ?", (board_id,))
        row = cursor.fetchone()
        conn.close()
        return Board.from_row(row)

    def get_board_configuration(self, configuration_id: int) -> Optional[BoardConfiguration]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM BoardConfiguration WHERE Id = ?",
            (configuration_id,),
        )
        row = cursor.fetchone()
        conn.close()
        return BoardConfiguration.from_row(row)

    # --- Scenario repository operations ---
    def create_scenario(
        self,
        board_id: int,
        bidding_route: str,
        declarer: str,
        contract: str,
        risk_status: str,
        is_targeted: int,
        targeted_sequence: Optional[str],
        name: str = "",
        information: Optional[str] = None,
    ) -> int:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO Scenario (
                   BoardId, Name, BiddingRoute, Declarer, Contract, RiskStatus,
                   IsTargeted, TargetedSequence, Information
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                board_id,
                name.strip(),
                bidding_route,
                declarer,
                contract,
                risk_status,
                is_targeted,
                targeted_sequence,
                information,
            ),
        )
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    def get_scenarios_by_board(self, board_id: int) -> List[Scenario]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Scenario WHERE BoardId = ?", (board_id,))
        rows = cursor.fetchall()
        conn.close()
        return [Scenario.from_row(row) for row in rows]

    def get_scenario_by_id(self, scenario_id: int) -> Optional[Scenario]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Scenario WHERE Id = ?", (scenario_id,))
        row = cursor.fetchone()
        conn.close()
        return Scenario.from_row(row)

    def update_scenario(
        self,
        scenario_id: int,
        bidding_route: str,
        declarer: str,
        contract: str,
        risk_status: str,
        is_targeted: int,
        targeted_sequence: Optional[str],
        information: Optional[str] = None,
    ):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE Scenario
                   SET BiddingRoute = ?, Declarer = ?, Contract = ?, RiskStatus = ?,
                       IsTargeted = ?, TargetedSequence = ?, Information = ?
                   WHERE Id = ?""",
                (
                    bidding_route,
                    declarer,
                    contract,
                    risk_status,
                    is_targeted,
                    targeted_sequence,
                    information,
                    scenario_id,
                ),
            )
            if cursor.rowcount == 0:
                raise LookupError(f"Scenario {scenario_id} was not found.")
            conn.commit()
        finally:
            conn.close()

    def rename_scenario(self, scenario_id: int, name: str):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE Scenario SET Name = ? WHERE Id = ?",
                (name.strip(), scenario_id),
            )
            if cursor.rowcount == 0:
                raise LookupError(f"Scenario {scenario_id} was not found.")
            conn.commit()
        finally:
            conn.close()

    def delete_scenario(self, scenario_id: int):
        self._delete_by_id("Scenario", scenario_id)

    # --- Label repository operations ---
    def create_label(self, scenario_id: int, sequence: int, color: str, card: str) -> int:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Label (ScenarioId, Sequence, Color, Card) VALUES (?, ?, ?, ?)",
            (scenario_id, sequence, color, card)
        )
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    def get_labels_by_scenario(self, scenario_id: int) -> List[Label]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Label WHERE ScenarioId = ? ORDER BY Sequence ASC", (scenario_id,))
        rows = cursor.fetchall()
        conn.close()
        return [Label.from_row(row) for row in rows]

    def replace_labels(self, scenario_id: int, labels: list[dict]):
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Label WHERE ScenarioId = ?", (scenario_id,))
            cursor.executemany(
                """INSERT INTO Label (ScenarioId, Sequence, Color, Card)
                   VALUES (?, ?, ?, ?)""",
                [
                    (
                        scenario_id,
                        label["Sequence"],
                        label["Color"],
                        label["Card"],
                    )
                    for label in labels
                ],
            )
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _delete_by_id(self, table: str, row_id: int):
        allowed_tables = {"Folder", "CaseStudy", "Board", "Scenario"}
        if table not in allowed_tables:
            raise ValueError(f"Unsupported table for deletion: {table}")
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table} WHERE Id = ?", (row_id,))
            if cursor.rowcount == 0:
                raise LookupError(f"{table} {row_id} was not found.")
            conn.commit()
        finally:
            conn.close()