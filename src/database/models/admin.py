# src/database/models/admin.py
from typing import Optional, Dict, Any

class Admin:
    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        password: str = "",
        expires_at: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.password = password
        self.expires_at = expires_at

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> 'Admin':
        if not row:
            return None
        return cls(
            id=row["Id"],
            name=row["Name"],
            expires_at=row["ExpiresAt"],
            password=row["Password"]
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Id": self.id,
            "Name": self.name,
            "ExpiresAt": self.expires_at,
            "Password": self.password
        }