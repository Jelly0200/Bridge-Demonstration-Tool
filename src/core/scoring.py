# src/core/scoring.py
from typing import Dict, Any, Tuple


class BridgeScorer:
    @staticmethod
    def calculate_score(contract: str, declarer: str, tricks_taken: int, vulnerability: str,
                        risk_status: str = "NONE") -> int:
        """
        Calculate the duplicate bridge score for a contract.
        :param contract: The contract, such as "4S", "3NT", or "2H".
        :param declarer: The declaring direction, such as "SOUTH" or "NORTH".
        :param tricks_taken: Total tricks won by declarer's side.
        :param vulnerability: The vulnerability ("NONE", "NS", "EW", or "BOTH").
        :param risk_status: The doubling status ("NONE", "DOUBLE", or "REDOUBLE").
        :return: The score from declarer's perspective; positive is made, negative is down.
        """
        if len(contract) < 2:
            raise ValueError(f"Invalid contract format: {contract}")

        level = int(contract[0])
        suit = contract[1:].upper()  # 'S', 'H', 'D', 'C', 'NT'

        # The contract target is six tricks plus the contract level.
        target_tricks = 6 + level
        diff = tricks_taken - target_tricks  # 实际完成情况：>=0 表示做进或超额，<0 表示宕墩

        # Determine whether declarer's side is vulnerable.
        is_vuln = False
        if vulnerability == "BOTH":
            is_vuln = True
        elif vulnerability == "NS" and declarer in ["NORTH", "SOUTH"]:
            is_vuln = True
        elif vulnerability == "EW" and declarer in ["EAST", "WEST"]:
            is_vuln = True

        # --- 1. Penalty for a down contract ---
        if diff < 0:
            down_count = abs(diff)
            score = 0
            if risk_status == "NONE":
                if not is_vuln:
                    score = down_count * 50
                else:
                    score = down_count * 100
            elif risk_status == "DOUBLE":
                if not is_vuln:
                    # 1st: 100, 2nd & 3rd: 200, 4th+: 300
                    scores_list = [100, 200, 200, 300, 300, 300]
                    score = sum(scores_list[min(i, len(scores_list) - 1)] for i in range(down_count))
                else:
                    # 1st: 200, 2nd+: 300
                    scores_list = [200, 300, 300, 300]
                    score = sum(scores_list[min(i, len(scores_list) - 1)] for i in range(down_count))
            elif risk_status == "REDOUBLE":
                score = sum(2 * x for x in [200, 300, 300, 300][:down_count])  # 简化加倍的翻倍
            return -score

        # --- 2. Score for a made contract ---
        trick_score = 0
        # Base points per contract trick.
        if suit in ["C", "D"]:
            base_per_trick = 20
        elif suit in ["H", "S"]:
            base_per_trick = 30
        elif suit == "NT":
            base_per_trick = 30
            trick_score += 10  # 无主第一墩有 10 分加成
        else:
            base_per_trick = 30

        trick_score += level * base_per_trick

        # Apply the double or redouble multiplier.
        multiplier = 1
        insult_bonus = 0
        if risk_status == "DOUBLE":
            multiplier = 2
            insult_bonus = 50
        elif risk_status == "REDOUBLE":
            multiplier = 4
            insult_bonus = 100

        trick_score *= multiplier

        # Bonuses.
        bonus = 0
        is_game = trick_score >= 100

        if not is_game:
            bonus += 50  # 部分分奖分
        else:
            bonus += 300 if not is_vuln else 500  # 成局奖分 (Game bonus)

        # Slam bonuses.
        if level == 6:
            bonus += 500 if not is_vuln else 750
        elif level == 7:
            bonus += 1000 if not is_vuln else 1500

        # Overtrick bonuses.
        overtricks = diff
        if risk_status == "NONE":
            if suit in ["C", "D"]:
                overtrick_val = overtricks * 20
            else:
                overtrick_val = overtricks * 30
            bonus += overtrick_val
        elif risk_status == "DOUBLE":
            per_over = 100 if not is_vuln else 200
            bonus += overtricks * per_over
        elif risk_status == "REDOUBLE":
            per_over = 200 if not is_vuln else 400
            bonus += overtricks * per_over

        total_score = trick_score + bonus + insult_bonus
        return total_score