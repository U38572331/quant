
# Tile Constants
# 0-8: Man (Characters) 1-9
# 9-17: Pin (Dots) 1-9
# 18-26: Sou (Bamboo) 1-9
# 27-30: Winds (East, South, West, North)
# 31-33: Dragons (White, Green, Red)
# 34-41: Flowers/Seasons

TILE_MAN_1 = 0
TILE_MAN_9 = 8
TILE_PIN_1 = 9
TILE_PIN_9 = 17
TILE_SOU_1 = 18
TILE_SOU_9 = 26

TILE_EAST = 27
TILE_SOUTH = 28
TILE_WEST = 29
TILE_NORTH = 30

TILE_WHITE = 31
TILE_GREEN = 32
TILE_RED = 33

# Flowers are usually 0-7 relative to FLOWER_START
TILE_FLOWER_START = 34
TILE_FLOWER_END = 41

TOTAL_TILES_NO_FLOWER = 34
TOTAL_TILES_WITH_FLOWER = 42

def is_man(tile_idx): return TILE_MAN_1 <= tile_idx <= TILE_MAN_9
def is_pin(tile_idx): return TILE_PIN_1 <= tile_idx <= TILE_PIN_9
def is_sou(tile_idx): return TILE_SOU_1 <= tile_idx <= TILE_SOU_9
def is_expert(tile_idx): return TILE_EAST <= tile_idx <= TILE_RED # Honors
def is_flower(tile_idx): return TILE_FLOWER_START <= tile_idx <= TILE_FLOWER_END

def tile_to_string(tile_idx):
    if is_man(tile_idx): return f"{tile_idx - TILE_MAN_1 + 1}m"
    if is_pin(tile_idx): return f"{tile_idx - TILE_PIN_1 + 1}p"
    if is_sou(tile_idx): return f"{tile_idx - TILE_SOU_1 + 1}s"
    if is_expert(tile_idx):
        honors = ["E", "S", "W", "N", "Wh", "G", "R"]
        return honors[tile_idx - TILE_EAST]
    if is_flower(tile_idx):
        return f"F{tile_idx - TILE_FLOWER_START + 1}"
    return "?"

def string_to_tile(s):
    # Simple parser for single tile strings like "1m", "5p", "E"
    # This is a basic implementation
    s = s.lower().strip()
    if s.endswith('m'): return TILE_MAN_1 + int(s[:-1]) - 1
    if s.endswith('p'): return TILE_PIN_1 + int(s[:-1]) - 1
    if s.endswith('s'): return TILE_SOU_1 + int(s[:-1]) - 1
    
    mapping = {
        'e': TILE_EAST, 's': TILE_SOUTH, 'w': TILE_WEST, 'n': TILE_NORTH,
        'wh': TILE_WHITE, 'bai': TILE_WHITE, 
        'g': TILE_GREEN, 'fa': TILE_GREEN,
        'r': TILE_RED, 'chung': TILE_RED
    }
    if s in mapping: return mapping[s]
    # Flowers handling can be added
    return -1
