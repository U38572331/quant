
from .hand import Hand
from ..analysis.efficiency import EfficiencyCalculator
from ..analysis.risk import RiskCalculator
from ..algorithms.shanten import ShantenCalculator
from .tiles import tile_to_string

class Player:
    def __init__(self, name):
        self.name = name
        self.hand = Hand()
        self.score = 0
        self.seat = -1
        self.table = None
        self.is_ai = False
        self.discards = []
        
    def draw_tile(self, tile, is_draw=False):
        self.hand.add_tile(tile)
        if is_draw:
            # Logic for "Just Drawn" (can calculate Hu here)
            pass
            
    def discard_tile(self, tile):
        if self.hand.remove_tile(tile):
            self.discards.append(tile)
            # Notify table?
            return True
        return False
        
    def decide_discard(self):
        raise NotImplementedError

class AIPlayer(Player):
    def __init__(self, name):
        super().__init__(name)
        self.is_ai = True
        self.shanten_calc = ShantenCalculator()
        self.eff_calc = EfficiencyCalculator(self.shanten_calc)
        self.risk_calc = RiskCalculator()
        
    def decide_discard(self):
        """
        AI Logic:
        1. Calculate Shanten
        2. If Tenpai or close, check Risk?
        3. Use EfficiencyCalculator to get best tile.
        """
        suggestions = self.eff_calc.get_effective_discards(self.hand)
        if not suggestions:
            # Fallback (shouldn't happen unless hand empty)
            return self.hand.tiles[0]
            
        # Strategy: Pick lowest shanten, then max ukeire
        # suggestions are already sorted by (Shanten, -Ukeire)
        best = suggestions[0]['discard']
        
        # Simple logging
        # print(f"[{self.name}] AI Thinking... Best Discard: {tile_to_string(best)} (Shanten: {suggestions[0]['shanten']})")
        
        return best

class HumanPlayer(Player):
    def __init__(self, name):
        super().__init__(name)
        
    def decide_discard(self):
        # In a real GUI, this would wait for event.
        # In CLI, input.
        print(f"\nYour Hand: {self.hand}")
        while True:
            s = input(f"[{self.name}] Enter tile to discard (e.g. 1m, 5p): ")
            from .tiles import string_to_tile
            t = string_to_tile(s)
            if t != -1 and t in self.hand.tiles:
                return t
            print("Invalid tile.")
