import os
import tempfile
import unittest

from src.core.pbn_parser import PbnParser
from src.core.scoring import BridgeScorer
from src.database.db_manager import DatabaseManager
from src.database.repository import Repository
from src.robot.label_evaluator import LabelEvaluator


class TestBackendUnit(unittest.TestCase):
    def setUp(self):
        DatabaseManager._instance = None
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        db_path = os.path.join(self.temp_dir.name, "bridge_test.db")
        DatabaseManager(db_path)
        self.repo = Repository()

    def tearDown(self):
        DatabaseManager._instance = None

    def test_pbn_hand_round_trip_and_deal_validation(self):
        hands = {
            "NORTH": "AKQJ.T98.765.432",
            "EAST": "432.AKQJ.T98.765",
            "SOUTH": "T98.765.AKQJ.T98",
            "WEST": "765.432.432.AKQJ",
        }
        for pbn in hands.values():
            parsed = PbnParser.parse_hand(pbn)
            self.assertEqual(PbnParser.hand_to_pbn(parsed), pbn)
        self.assertTrue(PbnParser.validate_deal(hands))

    def test_duplicate_bridge_scoring(self):
        made_game_score = BridgeScorer.calculate_score(
            contract="4S",
            declarer="SOUTH",
            tricks_taken=10,
            vulnerability="NONE",
        )
        vulnerable_doubled_down_score = BridgeScorer.calculate_score(
            contract="3NT",
            declarer="SOUTH",
            tricks_taken=8,
            vulnerability="BOTH",
            risk_status="DOUBLE",
        )

        self.assertEqual(made_game_score, 420)
        self.assertEqual(vulnerable_doubled_down_score, -200)

    def test_label_sequence_falls_through_to_next_triggered_rule(self):
        chosen_card = LabelEvaluator.evaluate_card_choice(
            legal_cards=["SA", "SK", "SQ"],
            dds_card_scores={"SK": 8},
            labels=[
                {"Sequence": 1, "Color": "BLUE", "Card": "SQ"},
                {"Sequence": 2, "Color": "RED", "Card": "SA"},
            ],
            play_type="leading",
        )

        self.assertEqual(chosen_card, "SA")

    def test_repository_persists_admin_and_folder(self):
        admin_id = self.repo.create_admin("TournamentDirector", "SecurePass2026")
        admin = self.repo.get_admin_by_name("TournamentDirector")
        if admin is None:
            self.fail("The created administrator could not be loaded.")
        self.assertEqual(admin.id, admin_id)

        folder_id = self.repo.create_folder(admin_id, None, "Teaching Cases")
        folders = self.repo.get_folders_by_admin(admin_id)
        self.assertEqual(len(folders), 1)
        self.assertEqual(folders[0].id, folder_id)
        self.assertEqual(folders[0].name, "Teaching Cases")


if __name__ == "__main__":
    unittest.main()
