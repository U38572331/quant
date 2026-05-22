
import threading
import time
from src.core.table import Table
from src.core.player import HumanPlayer, AIPlayer
from src.core.tiles import tile_to_string, is_flower, is_expert

class GameInterface:
    def __init__(self):
        self.table = None
        self.human_player = None
        self.ai_players = []
        self.game_over = False
        self.lock = threading.Lock()
        self.message = "Initializing..."
        self.last_action_desc = ""
        
        self.reset_game()

    def reset_game(self):
        with self.lock:
            self.table = Table()
            self.human_player = HumanPlayer("You")
            self.ai_players = [
                AIPlayer("Right (AI)"),
                AIPlayer("Top (AI)"),
                AIPlayer("Left (AI)")
            ]
            self.table.add_player(self.human_player)
            for p in self.ai_players:
                self.table.add_player(p)
                
            self.table.init_game()
            self.table.deal_initial_hands()
            self.game_over = False
            self.message = "Game Started. Your Turn."
            # If human is not dealer (0), we need to advance to human turn?
            # Actually Table.turn is dealer_idx initially (0).
            # If our player is 0, it's our turn.
            
            # Start loop to advance to human
            self._advance_to_human()

    def _advance_to_human(self):
        # Keeps playing turns until handled by human or game over
        while not self.game_over:
            current = self.table.players[self.table.turn]
            if current == self.human_player:
                # Needed to draw?
                # Usually deal_initial_hands gives 17 tiles to dealer, so state is "Waiting Discard".
                # If Hand count % 3 == 2 (17, 14, etc), we need to discard.
                # If Hand count % 3 == 1 (16, 13, etc), we need to Draw (unless just started and not dealer?)
                
                # Check tile count
                # 16-tile MJ:
                # Base hand 16. Winner 17.
                # If 17 tiles, we need discard.
                # If 16 tiles, we need Draw.
                
                cnt = len(current.hand.tiles)
                # Flowers are removed? In this engine flowers are in hand but logic must handle.
                # Simplified: standard check.
                
                if cnt % 3 == 2: # 17, 14, 11...
                     self.message = "Your Turn to Discard."
                     return # Wait for input
                else:
                     # Need to draw
                     t = self.table.draw_tile()
                     if t is None:
                         self.game_over = True
                         self.message = "Game Over - Wall Empty"
                         return
                     current.draw_tile(t, is_draw=True)
                     self.last_action_desc = f"You drew {tile_to_string(t)}"
                     self.message = "Your Turn to Discard."
                     return # Wait for input
            
            else:
                # AI Turn
                # Draw
                # Need to check if AI already has 17 (Dealer start)?
                cnt = len(current.hand.tiles)
                if cnt % 3 != 2:
                    t = self.table.draw_tile()
                    if t is None:
                        self.game_over = True
                        return
                    current.draw_tile(t, is_draw=True)
                
                # Discard
                discard = current.decide_discard()
                current.discard_tile(discard)
                self.last_action_desc = f"{current.name} discarded {tile_to_string(discard)}"
                
                # Next
                self.table.advance_turn()
                time.sleep(0.0) # non-blocking

    def handle_discard(self, tile_idx):
        with self.lock:
            if self.game_over: return False
            if self.table.players[self.table.turn] != self.human_player:
                return False
                
            # Verify ownership
            if not self.human_player.discard_tile(tile_idx):
                return False
                
            self.last_action_desc = f"You discarded {tile_to_string(tile_idx)}"
            self.table.advance_turn()
            self._advance_to_human()
            return True

    def get_state_json(self):
        with self.lock:
            # Helper to convert tiles
            def serialize_hand(h):
                return [t for t in sorted(h.tiles)] # Returns ints
            
            def serialize_discards(p):
                return [t for t in p.discards]
                
            state = {
                "turn": self.table.turn,
                "wall_count": self.table.get_remaining_count(),
                "message": self.message,
                "last_action": self.last_action_desc,
                "game_over": self.game_over,
                "me": {
                    "hand": serialize_hand(self.human_player.hand),
                    "seat": self.human_player.seat,
                    "discards": serialize_discards(self.human_player)
                },
                "opponents": []
            }
            
            # Opponents info (masked hand)
            for p in self.table.players:
                if p == self.human_player: continue
                # Relativity: Right, Top, Left
                # If Me=0. Right=1, Top=2, Left=3
                # rel = (p.seat - me.seat) % 4
                rel_idx = (p.seat - self.human_player.seat) % 4
                pos_name = ["", "Right", "Top", "Left"][rel_idx]
                
                state["opponents"].append({
                    "seat": p.seat,
                    "name": p.name,
                    "position": pos_name,
                    "hand_count": len(p.hand.tiles),
                    "discards": serialize_discards(p)
                })
                
            state["opponents"].sort(key=lambda x: ["Right", "Top", "Left"].index(x["position"]))
                
            return state
