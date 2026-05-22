
import sys
import os
import time

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.table import Table
from src.core.player import HumanPlayer, AIPlayer
from src.core.tiles import tile_to_string

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    print("=== Taiwan Mahjong Game (AI Edition) ===")
    
    table = Table()
    
    # Setup Players
    # P0: Human
    p0 = HumanPlayer("You")
    # P1-3: AI
    p1 = AIPlayer("AI-Right")
    p2 = AIPlayer("AI-Top")
    p3 = AIPlayer("AI-Left")
    
    table.add_player(p0)
    table.add_player(p1)
    table.add_player(p2)
    table.add_player(p3)
    
    print("Initializing Game... Shuffling Wall...")
    table.init_game()
    table.deal_initial_hands()
    
    # Game Loop
    game_over = False
    
    while not game_over and table.get_remaining_count() > 16: # Rule: End when 16 tiles left
        current_player = table.players[table.turn]
        
        # Display Info (If Human Turn or just update)
        if current_player == p0:
            print(f"\n--- Turn: {current_player.name} ---")
            print(f"Tiles Left: {table.get_remaining_count()}")
            # Show discards of others?
            print(f"AI Discards: {[tile_to_string(d) for d in p1.discards[-6:]]} ...")
            
            # Draw
            t = table.draw_tile()
            if t is None:
                game_over = True
                break
                
            print(f"DRAW: {tile_to_string(t)}")
            current_player.draw_tile(t, is_draw=True)
            
            # Action (Discard)
            discard = current_player.decide_discard()
            print(f"Discarding: {tile_to_string(discard)}")
            current_player.discard_tile(discard)
            
        else:
            # AI Turn
            # print(f"--- Turn: {current_player.name} ---")
            t = table.draw_tile()
            if t is None:
                game_over = True
                break
            current_player.draw_tile(t, is_draw=True)
            
            # AI Thinking
            # time.sleep(0.1) # Simulate think
            discard = current_player.decide_discard()
            print(f"[{current_player.name}] Draws ? -> Discards {tile_to_string(discard)}")
            current_player.discard_tile(discard)

        # Post Discard Logic (Check Ron/Pong)
        # TODO: Implement Interruption logic here
        
        # Next Turn
        table.advance_turn()

    print("\nGame Over! Wall exhausted.")

if __name__ == "__main__":
    main()
