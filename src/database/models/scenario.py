# src/database/models/scenario.py
from typing import Optional, Dict, Any


class Scenario:
    def __init__(
        self,
        id: Optional[int] = None,
        board_id: int = 0,
        bidding_route: str = "",
        declarer: str = "SOUTH",
        contract: str = "",
        risk_status: str = "NONE",
        is_targeted: int = 0,
        targeted_sequence: Optional[str] = None,
        name: str = "",
        information: Optional[str] = None,
    ):
        self.id = id
        self.board_id = board_id
        self.name = name
        self.information = information
        self.bidding_route = bidding_route
        self.declarer = declarer
        self.contract = contract
        self.risk_status = risk_status
        self.is_targeted = is_targeted
        self.targeted_sequence = targeted_sequence

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> 'Scenario':
        if not row:
            return None
        return cls(
            id=row["Id"],
            board_id=row["BoardId"],
            name=row["Name"],
            bidding_route=row["BiddingRoute"],
            declarer=row["Declarer"],
            contract=row["Contract"],
            risk_status=row["RiskStatus"],
            is_targeted=row["IsTargeted"],
            targeted_sequence=row["TargetedSequence"],
            information=(
                row["Information"] if "Information" in row.keys() else None
            ),
        )


class Label:
    def __init__(
        self,
        id: Optional[int] = None,
        scenario_id: int = 0,
        sequence: int = 0,
        color: str = "RED",
        card: str = "",
    ):
        self.id = id
        self.scenario_id = scenario_id
        self.sequence = sequence
        self.color = color
        self.card = card

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> 'Label':
        if not row:
            return None
        return cls(
            id=row["Id"],
            scenario_id=row["ScenarioId"],
            sequence=row["Sequence"],
            color=row["Color"],
            card=row["Card"],
        )