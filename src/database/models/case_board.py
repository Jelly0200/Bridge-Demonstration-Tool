# src/database/models/case_board.py
from typing import Optional, Dict, Any

class CaseStudy:
    def __init__(self, id: Optional[int] = None, folder_id: int = 0, name: str = ""):
        self.id = id
        self.folder_id = folder_id
        self.name = name

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> 'CaseStudy':
        if not row:
            return None
        return cls(id=row["Id"], folder_id=row["FolderId"], name=row["Name"])


class BoardConfiguration:
    def __init__(self, id: Optional[int] = None, dealer: str = "SOUTH", vulnerability: str = "NONE"):
        self.id = id
        self.dealer = dealer
        self.vulnerability = vulnerability

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> 'BoardConfiguration':
        if not row:
            return None
        return cls(id=row["Id"], dealer=row["Dealer"], vulnerability=row["Vulnerability"])


class Board:
    def __init__(self, id: Optional[int] = None, case_id: int = 0, board_configuration_id: int = 0,
                 south_hand_pbn: str = "", west_hand_pbn: str = "", north_hand_pbn: str = "",
                 east_hand_pbn: str = "", description: Optional[str] = None):
        self.id = id
        self.case_id = case_id
        self.board_configuration_id = board_configuration_id
        self.south_hand_pbn = south_hand_pbn
        self.west_hand_pbn = west_hand_pbn
        self.north_hand_pbn = north_hand_pbn
        self.east_hand_pbn = east_hand_pbn
        self.description = description

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> 'Board':
        if not row:
            return None
        return cls(
            id=row["Id"],
            case_id=row["CaseId"],
            board_configuration_id=row["BoardConfigurationId"],
            south_hand_pbn=row["SouthHandPbn"],
            west_hand_pbn=row["WestHandPbn"],
            north_hand_pbn=row["NorthHandPbn"],
            east_hand_pbn=row["EastHandPbn"],
            description=row["Description"]
        )