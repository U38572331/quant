
class RiskCalculator:
    def __init__(self):
        self.discards = {} # Player -> List of discards
        pass

    def set_discards(self, player_idx, tiles):
        self.discards[player_idx] = tiles

    def calculate_danger(self, tile, target_player):
        """
        Returns danger score (0-100) or Probability.
        Rule-based:
        1. Genbutsu (Same tile in discard): 0%
        2. Suji (Stripes) logic: Lower risk
        3. Push/Fold judgement: If tile is Live (seen=0), high risk.
        """
        # Genbutsu Check
        if target_player in self.discards:
            if tile in self.discards[target_player]:
                return 0 # Safe
        
        # Default risk
        # Simple heuristic: Honors are safer if visible count is high?
        # For prototype, return simplified danger.
        return 50 # Unknown
