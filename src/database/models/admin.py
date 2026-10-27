# src/database/models/admin.py
from typing import Optional, Dict, Any

class Admin:
    def __init__(self, id: Optional[int] = None, name: str = "", password: str = ""):
        self.id = id
        self.name = name
        self.password = password

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> 'Admin':
        if not row:
            return None
        return cls(
            id=row["Id"],
            name=row["Name"],
            password=row["Password"]
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Id": self.id,
            "Name": self.name,
            "Password": self.password
        }