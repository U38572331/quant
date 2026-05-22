from .tiles import string_to_tile, tile_to_string

class Hand:
    def __init__(self, tiles=None):
        # List of tile indices (integers)
        self.tiles = []
        # List of melds (tuples or objects representing Chi/Pon/Kan)
        self.melds = [] 
        # Flowers are usually kept separate in game logic as they are bonus tiles
        self.flowers = []
        
        if tiles:
            if isinstance(tiles, list):
                self.tiles = sorted(tiles)
            elif isinstance(tiles, str):
                self.parse_hand_string(tiles)
    
    def add_tile(self, tile_idx):
        self.tiles.append(tile_idx)
        self.tiles.sort()
        
    def remove_tile(self, tile_idx):
        if tile_idx in self.tiles:
            self.tiles.remove(tile_idx)
            return True
        return False
        
    def parse_hand_string(self, hand_str):
        """
        Parses a string like "123m456p789s11z"
        This is a simplified parser requiring specific format.
        """
        # A more robust parser would iterate and track type.
        # Implementation placeholder
        pass

    def __str__(self):
        return "".join([tile_to_string(t) for t in self.tiles])

    def count_tiles(self):
        counts = {}
        for t in self.tiles:
            counts[t] = counts.get(t, 0) + 1
        return counts
