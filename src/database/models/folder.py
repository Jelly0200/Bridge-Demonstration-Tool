# src/database/models/folder.py
from typing import Optional, Dict, Any

class Folder:
    def __init__(self, id: Optional[int] = None, administration_id: int = 0, parent_folder_id: Optional[int] = None, name: str = ""):
        self.id = id
        self.administration_id = administration_id
        self.parent_folder_id = parent_folder_id
        self.name = name

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> 'Folder':
        if not row:
            return None
        return cls(
            id=row["Id"],
            administration_id=row["AdministrationId"],
            parent_folder_id=row["ParentFolderId"],
            name=row["Name"]
        )