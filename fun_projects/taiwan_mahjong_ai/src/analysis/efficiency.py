
from ..core.tiles import TOTAL_TILES_NO_FLOWER

class EfficiencyCalculator:
    def __init__(self, shanten_calculator):
        self.st = shanten_calculator

    def get_effective_discards(self, hand):
        """
        Returns a list of calculated metrics for each unique tile in hand.
        List of dicts:
        [{
            'discard_tile': int,
            'shanten_after': int,
            'effective_tiles': int (count of unique tiles that improve hand),
            'effective_count': int (total physical tiles remaining)
        }]
        """
        results = []
        # Get unique tiles to discard
        unique_tiles = sorted(list(set(hand.tiles)))
        
        # Current shanten
        current_shanten = self.st.calculate_shanten(hand)
        
        for t in unique_tiles:
            # 1. Try discard
            hand.remove_tile(t)
            
            # 2. Check all possible draws
            # Improvement if new_shanten < current_shanten
            # Wait, standard Ukeire logic:
            # If we are strictly checking improvement:
            # We look for tiles 'x' where calculate_shanten(hand + x) < current_shanten??
            # Or calculate_shanten(hand_after_discard + x) < calculate_shanten(hand_after_discard)?
            
            # definition: "Effective tiles to breadth"
            # We want to know: "If I discard T, how many tiles X make my hand move forward?"
            # Usually strict definition: Shanten decreases compared to "Discards T + Draw X".
            
            temp_shanten = self.st.calculate_shanten(hand)
            
            effective_list = []
            effective_total = 0
            
            for x in range(TOTAL_TILES_NO_FLOWER):
                # Assume we draw x
                hand.add_tile(x)
                if self.st.calculate_shanten(hand) < current_shanten:
                    # This is an effective tile
                    # Count remaining visible? (For basic, assume 4)
                    count_in_hand = hand.tiles.count(x)
                    rem = 4 - count_in_hand # And minus visible/discarded
                    effective_list.append(x)
                    effective_total += max(0, rem)
                hand.remove_tile(x)
            
            results.append({
                'discard': t,
                'shanten': temp_shanten,
                'ukeire_count': effective_total,
                'ukeire_tiles': effective_list
            })
            
            # Restore
            hand.add_tile(t)
            
        # Sort results: Lower shanten first, then Higher ukeire_count
        results.sort(key=lambda x: (x['shanten'], -x['ukeire_count']))
        return results
