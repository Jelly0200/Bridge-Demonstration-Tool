# src/database/models/test_model.py
from typing import Optional, Dict, Any

class Test:
    def __init__(self, id: Optional[int] = None, administration_id: int = 0, name: str = ""):
        self.id = id
        self.administration_id = administration_id
        self.name = name

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> 'Test':
        if not row:
            return None
        return cls(id=row["Id"], administration_id=row["AdministrationId"], name=row["Name"])


class Rule:
    def __init__(self, id: Optional[int] = None, contracts: str = "{}", rules: str = "{}"):
        self.id = id
        self.contracts = contracts
        self.rules = rules

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> 'Rule':
        if not row:
            return None
        return cls(id=row["Id"], contracts=row["Contracts"], rules=row["Rules"])


class TestResult:
    def __init__(
        self,
        id: Optional[int] = None,
        test_id: int = 0,
        applicant_name: str = "",
        contracts: str = "{}",
        score: int = 0,
        submitted_at: Optional[str] = None,
        student_id: Optional[int] = None,
    ):
        self.id = id
        self.test_id = test_id
        self.student_id = student_id
        self.applicant_name = applicant_name
        self.contracts = contracts
        self.score = score
        self.submitted_at = submitted_at

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> 'TestResult':
        if not row:
            return None
        return cls(
            id=row["Id"],
            test_id=row["TestId"],
            student_id=row["StudentId"] if "StudentId" in row.keys() else None,
            applicant_name=row["ApplicantName"],
            contracts=row["Contracts"],
            score=row["Score"],
            submitted_at=row["SubmittedAt"]
        )