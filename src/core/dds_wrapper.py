# src/core/dds_wrapper.py
from typing import Dict, Any, Optional

try:
    import dds3

    DDS_WHEEL_AVAILABLE = True
    DDS_IMPORT_ERROR = None
except ImportError as error:
    dds3 = None
    DDS_WHEEL_AVAILABLE = False
    DDS_IMPORT_ERROR = error


class DdsWrapper:
    def __init__(self):
        """
        Initialize the wrapper using the installed dds3 Python wheel.
        """
        self.available = DDS_WHEEL_AVAILABLE
        if self.available:
            print("[DDS] Successfully loaded the dds3 wheel.")
        else:
            detail = f": {DDS_IMPORT_ERROR}" if DDS_IMPORT_ERROR else ""
            print(
                f"[DDS] Could not import dds3{detail}. "
                "Install a wheel compatible with the active Python version."
            )

    def is_available(self) -> bool:
        """Return whether the dds3 module is available."""
        return self.available

    def calc_dd_table_pbn(self, pbn_deal: str) -> Optional[Dict[str, Any]]:
        """
        Calculate a double-dummy table (CalcDDtable).
        :param pbn_deal: The deal as a PBN string.
        :return: The optimal trick table for each strain and direction.
        """
        if not self.is_available() or dds3 is None:
            raise RuntimeError("The dds3 module is unavailable; double-dummy analysis cannot run.")

        try:
            result = dds3.calc_all_tables_pbn([pbn_deal], mode=-1)
            tables = result.get("tables")
            if not tables:
                raise ValueError("DDS returned no double-dummy table for the deal.")
            return tables[0]
        except Exception as e:
            print(f"[DDS] Double-dummy table calculation failed: {e}")
            return None

    def solve_board_pbn(
        self,
        pbn_deal: str,
        target: int = -1,
        solutions: int = 2,
        mode: int = 0,
        *,
        trump: int = 4,
        first: int = 0,
        current_trick_suit=(0, 0, 0),
        current_trick_rank=(0, 0, 0),
    ) -> Optional[Any]:
        """
        Solve a board for the best card and continuation.
        """
        if not self.is_available() or dds3 is None:
            raise RuntimeError("The dds3 module is unavailable; board solving cannot run.")

        try:
            result = dds3.solve_board_pbn(
                pbn_deal,
                trump=trump,
                first=first,
                current_trick_suit=current_trick_suit,
                current_trick_rank=current_trick_rank,
                target=target,
                solutions=solutions,
                mode=mode,
            )
            return result
        except Exception as e:
            print(f"[DDS] Board solving failed: {e}")
            return None