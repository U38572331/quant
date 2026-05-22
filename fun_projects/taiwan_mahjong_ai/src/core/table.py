
import random
from .tiles import TOTAL_TILES_WITH_FLOWER
# Constants
TILES_COUNT = 144 # Standard TW MJ (Includes Flowers usually? Standard is 144: 136 basic + 8 flower)

class Table:
    def __init__(self):
        self.players = []
        self.wall = []
        self.dead_wall = [] # Usually 16 tiles in TW MJ? Or just play until end?
        # TW MJ usually plays until 16 tiles left or until end.
        self.turn = 0 # Index of current player
        self.dealer_idx = 0
        self.round_wind = 0 # 0=East, 1=South...
        
    def init_game(self):
        # Create Wall
        self.wall = self._create_wall()
        self.shuffle_wall()
        
    def _create_wall(self):
        # 4 copies of 0-33 (Suits + Honors)
        tiles = []
        for i in range(34):
            tiles.extend([i] * 4)
        # Flowers (34-41) 1 copy each
        for i in range(34, 42):
            tiles.append(i)
        return tiles

    def shuffle_wall(self):
        random.shuffle(self.wall)
        
    def add_player(self, player):
        player.seat = len(self.players)
        player.table = self
        self.players.append(player)
        
    def deal_initial_hands(self):
        # TW MJ: 16 tiles each.
        for _ in range(16):
            for p in self.players:
                t = self.wall.pop()
                p.draw_tile(t)
        
        # Dealer gets 1 extra (17th) to start
        t = self.wall.pop()
        self.players[self.dealer_idx].draw_tile(t, is_draw=True) # Dealer draws 1st tile effectively
        self.turn = self.dealer_idx

    def get_remaining_count(self):
        return len(self.wall)
    
    def advance_turn(self):
        self.turn = (self.turn + 1) % 4
        
    def draw_tile(self):
        if not self.wall:
            return None # End of game
        return self.wall.pop()
