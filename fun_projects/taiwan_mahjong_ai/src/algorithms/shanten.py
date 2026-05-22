
import copy

class ShantenCalculator:
    def __init__(self):
        pass

    def calculate_shanten(self, hand):
        """
        Calculates Shanten for 16-tile Mahjong (Target: 5 Sets + 1 Pair).
        Returns the minimum number of tiles required to reach Tenpai.
        """
        counts = [0] * 34 
        hand_counts = hand.count_tiles()
        for t, c in hand_counts.items():
            if t < 34:
                counts[t] = c

        min_shanten = 8 
        
        # Case A: Assume we have a pair (Try each feasible pair)
        for i in range(34):
            if counts[i] >= 2:
                counts[i] -= 2
                groups, partials = self._search(counts, 5) # Need 5 groups
                # Constrain partials
                if partials > (5 - groups): partials = (5 - groups)
                s = (5 - groups) * 2 - partials - 1
                min_shanten = min(min_shanten, s)
                counts[i] += 2
        
        # Case B: No pair assumption (Standard headless)
        groups, partials = self._search(counts, 5)
        if partials > (5 - groups): partials = (5 - groups)
        
        # Formula for headless: 
        # (Needed sets * 2) - partials + 1 (need pair) ??
        # Or: 8 - 2*groups - partials
        # Let's standardize:
        # Tenpai usually implies 0 shanten.
        # If we have 5 groups, 0 pair, we need 1 tile (pair). s=0.
        # (5-5)*2 - 0 = 0. Correct.
        # If we have 4 groups, 1 partial, 0 pair. 
        # We need 1 tile to finish partial -> 5 groups. Still need pair? 
        s_no_pair = (5 - groups) * 2 - partials
        # Usually headless penalty is handled by checking "if we have free terminals" etc.
        # For simplicity in this v1:
        min_shanten = min(min_shanten, s_no_pair)
        
        return min_shanten

    def _search(self, counts, max_groups):
        return self._dfs(counts, 0, 0, max_groups)

    def _dfs(self, counts, idx, g, max_g):
        # Base cases
        while idx < 34 and counts[idx] == 0:
            idx += 1
        if idx >= 34:
            # Leaf: count partials in remaining
            return g, self._count_partials_greedy(counts)

        # Pruning
        if g >= max_g:
            return g, 0

        best_g, best_p = g, 0
        
        # Try skipping this tile (don't use for Group)
        # We will try to match groups starting from next tile
        # IMPORTANT: If we skip, we treat this tile as "unused for groups".
        # It might be used for Pair or Partial later.
        # Since we are in DFS for Groups, we just move `idx` but DON'T decrement count?
        # No, must move idx. 
        # But if count > 0, we can't just ignore it if we iterate tiles.
        # Actually our loop `while idx < 34` skips zeros.
        # So we are at a tile that exists.
        
        # Branch 1: Skip (Don't use `counts[idx]` for a starting set)
        # We temporarily pretend we don't use the first of these tiles for a set.
        # But we might use later copies? No, standard logic is "Use or Drop".
        # We recurse on idx+1? If we still have counts[idx], it will be picked up by count_partials later.
        g_skip, p_skip = self._dfs(counts, idx + 1, g, max_g)
        best_g, best_p = g_skip, p_skip

        # Branch 2: Pung (AAA)
        if counts[idx] >= 3:
            counts[idx] -= 3
            res_g, res_p = self._dfs(counts, idx, g + 1, max_g)
            if (res_g * 10 + res_p) > (best_g * 10 + best_p): # Prioritize groups
                best_g, best_p = res_g, res_p
            counts[idx] += 3

        # Branch 3: Chow (ABC)
        if idx < 27:
            # Check suit boundaries
            is_valid_chow = False
            # Man: 0-6, Pin: 9-15, Sou: 18-24 can start a chow
            if 0 <= idx <= 6: is_valid_chow = True
            elif 9 <= idx <= 15: is_valid_chow = True
            elif 18 <= idx <= 24: is_valid_chow = True
            
            if is_valid_chow and counts[idx+1] > 0 and counts[idx+2] > 0:
                counts[idx] -= 1
                counts[idx+1] -= 1
                counts[idx+2] -= 1
                res_g, res_p = self._dfs(counts, idx, g + 1, max_g) 
                # Note: verify idx still has tiles? 
                # dfs restarts check at idx.
                if (res_g * 10 + res_p) > (best_g * 10 + best_p):
                    best_g, best_p = res_g, res_p
                counts[idx] += 1
                counts[idx+1] += 1
                counts[idx+2] += 1
                
        return best_g, best_p

    def _count_partials_greedy(self, counts):
        # Count pairs (AA) and tatsu (AB, AC) in remaining tiles
        p = 0
        tmp = list(counts) # Copy
        
        # 1. Pairs
        for i in range(34):
            if tmp[i] >= 2:
                tmp[i] -= 2
                p += 1
        
        # 2. Side/Kanchan
        for i in range(27): # Suits only
             if i % 9 < 8: # AB
                while tmp[i] > 0 and tmp[i+1] > 0:
                    tmp[i] -= 1
                    tmp[i+1] -= 1
                    p += 1
             if i % 9 < 7: # AC
                while tmp[i] > 0 and tmp[i+2] > 0:
                    tmp[i] -= 1
                    tmp[i+2] -= 1
                    p += 1

        return p
