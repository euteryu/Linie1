# constants.py
# -*- coding: utf-8 -*-
from typing import List, Dict, Tuple, Any

# --- Game Rules & Data ---
GRID_ROWS: int = 12
GRID_COLS: int = 12

BUILDING_COORDS: Dict[str, Tuple[int, int]] = {
    'A': (7, 11), 'B': (10, 8), 'C': (11, 4), 'D': (7, 1), 'E': (4, 0),
    'F': (1, 3),  'G': (0, 7),  'H': (3, 10),'I': (5, 8),  'K': (8, 6),
    'L': (6, 3),  'M': (3, 5),
}

TILE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "Straight":           {"connections": [['N', 'S']], "is_swappable": True},
    "Curve":              {"connections": [['N', 'E']], "is_swappable": True},
    "StraightLeftCurve":  {"connections": [['N', 'S'], ['S', 'W']], "is_swappable": True},
    "StraightRightCurve": {"connections": [['N', 'S'], ['S', 'E']], "is_swappable": True},
    "DoubleCurveY":       {"connections": [['N', 'W'], ['N', 'E']], "is_swappable": True},
    "DiagonalCurve":      {"connections": [['S', 'W'], ['N', 'E']], "is_swappable": True},
    "Tree_JunctionTop":      {"connections": [['E', 'W'], ['W', 'N'], ['N', 'E']], "is_swappable": False},
    "Tree_JunctionRight":    {"connections": [['E', 'W'], ['N', 'E'], ['S', 'E']], "is_swappable": False},
    "Tree_Roundabout":       {"connections": [['W', 'N'], ['N', 'E'], ['E', 'S'], ['S', 'W']], "is_swappable": False},
    "Tree_Crossroad":        {"connections": [['N', 'S'], ['E', 'W']], "is_swappable": False},
    "Tree_StraightDiagonal1":{"connections": [['N', 'S'], ['S', 'W'], ['N', 'E']], "is_swappable": False},
    "Tree_StraightDiagonal2":{"connections": [['N', 'S'], ['N', 'W'], ['S', 'E']], "is_swappable": False},
}

TILE_COUNTS_BASE: Dict[str, int] = {
    "Straight": 21, "Curve": 20, "StraightLeftCurve": 10, "StraightRightCurve": 10,
    "DoubleCurveY": 10, "DiagonalCurve": 6, "Tree_JunctionTop": 6, "Tree_JunctionRight": 6,
    "Tree_Roundabout": 4, "Tree_Crossroad": 4, "Tree_StraightDiagonal1": 2, "Tree_StraightDiagonal2": 2,
}
TILE_COUNTS_5_PLUS_ADD: Dict[str, int] = {"Straight": 15, "Curve": 10,}
STARTING_HAND_TILES: Dict[str, int] = {"Straight": 3, "Curve": 2,}

ROUTE_CARD_VARIANTS: List[Dict[str, Dict[int, List[str]]]] = [
    { "2-4": { 1: ['A', 'F'], 2: ['G', 'L'], 3: ['C', 'F'], 4: ['D', 'F'], 5: ['A', 'L'], 6: ['C', 'E'] }, "5-6": { 1: ['A', 'C', 'L'], 2: ['C', 'G', 'K'], 3: ['D', 'H', 'I'], 4: ['C', 'E', 'M'], 5: ['A', 'B', 'M'], 6: ['E', 'I', 'K'] }},
    { "2-4": { 1: ['F', 'K'], 2: ['F', 'H'], 3: ['A', 'C'], 4: ['D', 'K'], 5: ['D', 'G'], 6: ['E', 'H'] }, "5-6": { 1: ['B', 'G', 'L'], 2: ['B', 'L', 'M'], 3: ['C', 'I', 'M'], 4: ['A', 'D', 'M'], 5: ['A', 'G', 'K'], 6: ['B', 'F', 'M'] }},
    { "2-4": { 1: ['C', 'M'], 2: ['F', 'L'], 3: ['H', 'K'], 4: ['E', 'K'], 5: ['D', 'I'], 6: ['B', 'L'] }, "5-6": { 1: ['C', 'G', 'M'], 2: ['G', 'H', 'L'], 3: ['C', 'D', 'M'], 4: ['A', 'E', 'I'], 5: ['D', 'F', 'I'], 6: ['E', 'K', 'L'] }},
    { "2-4": { 1: ['B', 'I'], 2: ['B', 'M'], 3: ['D', 'M'], 4: ['E', 'I'], 5: ['B', 'H'], 6: ['F', 'I'] }, "5-6": { 1: ['C', 'D', 'I'], 2: ['E', 'G', 'I'], 3: ['D', 'H', 'K'], 4: ['H', 'K', 'L'], 5: ['A', 'E', 'L'], 6: ['A', 'B', 'L'] }},
    { "2-4": { 1: ['B', 'D'], 2: ['B', 'E'], 3: ['B', 'G'], 4: ['H', 'L'], 5: ['A', 'M'], 6: ['A', 'D'] }, "5-6": { 1: ['F', 'I', 'K'], 2: ['F', 'H', 'K'], 3: ['G', 'M', 'L'], 4: ['E', 'F', 'K'], 5: ['E', 'H', 'K'], 6: ['B', 'F', 'I'] }},
    { "2-4": { 1: ['C', 'I'], 2: ['G', 'K'], 3: ['E', 'G'], 4: ['C', 'H'], 5: ['H', 'M'], 6: ['A', 'G'] }, "5-6": { 1: ['F', 'H', 'K'], 2: ['C', 'F', 'I'], 3: ['B', 'H', 'L'], 4: ['D', 'I', 'M'], 5: ['A', 'L', 'M'], 6: ['B', 'F', 'I'] }},
]

# --- Simple Terminal Definitions (Example - NEEDS ACTUAL BOARD LAYOUT) ---
# Map: Line Number -> Tuple[ Tuple[StartCoord], Tuple[EndCoord] ]
TERMINAL_COORDS: Dict[int, Tuple[Tuple[int,int], Tuple[int,int]]] = {
    1: ((0, 11), (11, 11)), # Line 1: Top-Right to Bottom-Right (Example)
    2: ((0, 8), (11, 8)),   # Line 2: Example
    3: ((0, 4), (11, 4)),   # Line 3: Example
    4: ((0, 0), (11, 0)),   # Line 4: Top-Left to Bottom-Left (Example)
    5: ((4, 0), (4, 11)),   # Line 5: Left-Mid to Right-Mid (Example)
    6: ((8, 0), (8, 11)),   # Line 6: Example
}


# --- Pygame/Visual Layout Constants ---
SCREEN_WIDTH: int = 1200
SCREEN_HEIGHT: int = 800

# Board Area Calculations
BOARD_AREA_HEIGHT: float = SCREEN_HEIGHT * 0.95
BOARD_AREA_WIDTH: float = BOARD_AREA_HEIGHT # Keep it square
TILE_SIZE: int = int(BOARD_AREA_HEIGHT / GRID_ROWS) # Use GRID_ROWS from above

BOARD_WIDTH: int = TILE_SIZE * GRID_COLS
BOARD_HEIGHT: int = TILE_SIZE * GRID_ROWS

BOARD_X_OFFSET: int = 20
BOARD_Y_OFFSET: int = (SCREEN_HEIGHT - BOARD_HEIGHT) // 2

# UI Panel Area
UI_PANEL_X: int = BOARD_X_OFFSET + BOARD_WIDTH + 20
UI_PANEL_Y: int = BOARD_Y_OFFSET
UI_PANEL_WIDTH: int = SCREEN_WIDTH - UI_PANEL_X - 20
UI_PANEL_HEIGHT: int = BOARD_HEIGHT # Match board height for alignment

# Hand Area
HAND_AREA_X: int = UI_PANEL_X + 10
HAND_AREA_Y: int = UI_PANEL_Y + 50
HAND_TILE_SIZE: int = int(min(TILE_SIZE * 0.9, UI_PANEL_WIDTH * 0.7))
HAND_SPACING: int = 15
HAND_TILE_COUNT: int = 5 # Max tiles shown in hand display

# UI Text Positions (Add spacing)
UI_TEXT_X: int = UI_PANEL_X + 10
UI_LINE_HEIGHT: int = 25 # Vertical space between UI text lines
UI_TURN_INFO_Y: int = UI_PANEL_Y + 10
UI_ACTION_INFO_Y: int = UI_TURN_INFO_Y # Keep on same line for now? Or next line:
# UI_ACTION_INFO_Y: int = UI_TURN_INFO_Y + UI_LINE_HEIGHT
UI_ROUTE_INFO_Y: int = UI_ACTION_INFO_Y + UI_LINE_HEIGHT # Add space for Route Info
UI_HAND_TITLE_Y: int = UI_ROUTE_INFO_Y + UI_LINE_HEIGHT * 2 # Add more space before hand
HAND_AREA_Y: int = UI_HAND_TITLE_Y + UI_LINE_HEIGHT # Hand starts below its title

UI_SELECTED_TILE_Y: int = HAND_AREA_Y + HAND_TILE_COUNT * (HAND_TILE_SIZE + HAND_SPACING) + 20
UI_MESSAGE_Y: int = UI_SELECTED_TILE_Y + UI_LINE_HEIGHT
UI_INSTRUCTIONS_Y: int = UI_MESSAGE_Y + UI_LINE_HEIGHT

# Colors (Tuple[int, int, int] or Tuple[int, int, int, int])
COLOR_WHITE: Tuple[int, int, int] = (255, 255, 255)
COLOR_BLACK: Tuple[int, int, int] = (0, 0, 0)
COLOR_GRID: Tuple[int, int, int] = (100, 100, 100)
COLOR_BOARD_BG: Tuple[int, int, int] = (180, 180, 180)
COLOR_TRACK: Tuple[int, int, int] = (50, 50, 50)
COLOR_STOP: Tuple[int, int, int] = (255, 0, 0)
COLOR_BUILDING: Tuple[int, int, int] = (0, 100, 0)
COLOR_HIGHLIGHT: Tuple[int, int, int, int] = (255, 255, 0, 150) # Preview
COLOR_SELECTED: Tuple[int, int, int] = (0, 150, 255) # Hand selection
COLOR_UI_BG: Tuple[int, int, int] = (200, 200, 220)
COLOR_UI_TEXT: Tuple[int, int, int] = (10, 10, 50)

# Other constants if needed
MAX_PLAYER_ACTIONS: int = 2