
import sys
import os

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.hand import Hand
from src.core.tiles import tile_to_string, string_to_tile
from src.algorithms.shanten import ShantenCalculator
from src.analysis.efficiency import EfficiencyCalculator
from src.analysis.risk import RiskCalculator
from src.analysis.ev import EVCalculator

def main():
    print("=== Taiwan Mahjong AI Demo ===")
    
    # Example Hand: 16 tiles (Needs 1 to discard)
    # 11123456m 567p 88s E E
    # Let's create a 1-shanten hand or tenpai
    hand_str = "1m 1m 1m 2m 3m 4m 5m 6m 5p 6p 7p 8s 8s 27 27 27" 
    # Using integers for E (27)
    # Parse loop
    tiles = []
    # Manual construction for demo reliability
    # 111m
    tiles.extend([0, 0, 0])
    # 23456m (Partial/Runs)
    tiles.extend([1, 2, 3, 4, 5])
    # 567p
    tiles.extend([13, 14, 15])
    # 88s (Pair)
    tiles.extend([25, 25])
    # EEE (Pung)
    tiles.extend([27, 27, 27])
    # Total 16 tiles.
    
    hand = Hand(tiles)
    print(f"Current Hand: {hand}")
    
    shanten_calc = ShantenCalculator()
    s = shanten_calc.calculate_shanten(hand)
    print(f"Current Shanten: {s}")
    
    print("\n[Analysis] Calculating Efficiency...")
    eff_calc = EfficiencyCalculator(shanten_calc)
    suggestions = eff_calc.get_effective_discards(hand)
    
    print(f"{'Discard':<10} {'Shanten':<10} {'Ukeire (Tiles)':<15} {'Effective Tiles'}")
    print("-" * 60)
    
    for sug in suggestions[:5]: # Top 5
        t_str = tile_to_string(sug['discard'])
        eff_str = ", ".join([tile_to_string(x) for x in sug['ukeire_tiles']])
        print(f"{t_str:<10} {sug['shanten']:<10} {sug['ukeire_count']:<15} {eff_str}")
        
    print("\n[Risk] Checking Danger (Mock)...")
    risk_calc = RiskCalculator()
    # Assume E is discarded by Player 1
    risk_calc.set_discards(1, [27]) # E
    
    top_discard = suggestions[0]['discard']
    danger = risk_calc.calculate_danger(top_discard, 1)
    print(f"Danger of discarding {tile_to_string(top_discard)} against Player 1: {danger}%")

if __name__ == "__main__":
    main()
