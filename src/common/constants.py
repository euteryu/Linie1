# constants.py
# -*- coding: utf-8 -*-
from typing import List, Dict, Tuple, Any
import pygame


# Standard default original Linie 1 # tiles could lead to no more tiles left to play in advanced game states.
# This scale factor could open up opportunities for CIV6 / Monopoly -esque trading systems, where players may
#     purchase extra tile types from bank / other players for certain dynamic (e.g. weather / politcal context
#     driven) costs.
TILE_RUN_OUT_PREVENTION_SCALE_FACTOR = 10


## DEFAULT CONFIG
# --- Grid Dimensions ---
GRID_ROWS: int = 14; GRID_COLS: int = 14
PLAYABLE_ROWS: Tuple[int, int] = (1, 12); PLAYABLE_COLS: Tuple[int, int] = (1, 12)
# --- Game Rules & Data ---
BUILDING_COORDS: Dict[str, Tuple[int, int]] = { 'A': (8, 12), 'B': (11, 9), 'C': (12, 5), 'D': (8, 2), 'E': (5, 1), 'F': (2, 4), 'G': (1, 8), 'H': (4, 11),'I': (6, 9), 'K': (9, 7), 'L': (7, 4), 'M': (4, 6) }
TILE_DEFINITIONS: Dict[str, Dict[str, Any]] = { "Straight": {"connections": [['N', 'S']], "is_swappable": True}, "Curve": {"connections": [['N', 'E']], "is_swappable": True}, "StraightLeftCurve": {"connections": [['N', 'S'], ['S', 'W']], "is_swappable": True}, "StraightRightCurve": {"connections": [['N', 'S'], ['S', 'E']], "is_swappable": True}, "DoubleCurveY": {"connections": [['N', 'W'], ['N', 'E']], "is_swappable": True}, "DiagonalCurve": {"connections": [['S', 'W'], ['N', 'E']], "is_swappable": True}, "Tree_JunctionTop": {"connections": [['E', 'W'], ['W', 'N'], ['N', 'E']], "is_swappable": False}, "Tree_JunctionRight": {"connections": [['E', 'W'], ['N', 'E'], ['S', 'E']], "is_swappable": False}, "Tree_Roundabout": {"connections": [['W', 'N'], ['N', 'E'], ['E', 'S'], ['S', 'W']], "is_swappable": False}, "Tree_Crossroad": {"connections": [['N', 'S'], ['E', 'W']], "is_swappable": False}, "Tree_StraightDiagonal1": {"connections": [['N', 'S'], ['S', 'W'], ['N', 'E']], "is_swappable": False}, "Tree_StraightDiagonal2": {"connections": [['N', 'S'], ['N', 'W'], ['S', 'E']], "is_swappable": False}, }
TILE_COUNTS_BASE: Dict[str, int] = { "Straight": 21 * TILE_RUN_OUT_PREVENTION_SCALE_FACTOR, "Curve": 20 * TILE_RUN_OUT_PREVENTION_SCALE_FACTOR, "StraightLeftCurve": 10 * TILE_RUN_OUT_PREVENTION_SCALE_FACTOR, "StraightRightCurve": 10 * TILE_RUN_OUT_PREVENTION_SCALE_FACTOR, "DoubleCurveY": 10 * TILE_RUN_OUT_PREVENTION_SCALE_FACTOR, "DiagonalCurve": 6 * TILE_RUN_OUT_PREVENTION_SCALE_FACTOR, "Tree_JunctionTop": 6 * TILE_RUN_OUT_PREVENTION_SCALE_FACTOR, "Tree_JunctionRight": 6 * TILE_RUN_OUT_PREVENTION_SCALE_FACTOR, "Tree_Roundabout": 4 * TILE_RUN_OUT_PREVENTION_SCALE_FACTOR, "Tree_Crossroad": 4 * TILE_RUN_OUT_PREVENTION_SCALE_FACTOR, "Tree_StraightDiagonal1": 2 * TILE_RUN_OUT_PREVENTION_SCALE_FACTOR, "Tree_StraightDiagonal2": 2 * TILE_RUN_OUT_PREVENTION_SCALE_FACTOR, }
TILE_COUNTS_5_PLUS_ADD: Dict[str, int] = {"Straight": 15, "Curve": 10,}
STARTING_HAND_TILES: Dict[str, int] = {"Straight": 3, "Curve": 2,}
ROUTE_CARD_VARIANTS: List[Dict[str, Dict[int, List[str]]]] = [ { "1-4": { 1: ['A', 'F'], 2: ['G', 'L'], 3: ['C', 'F'], 4: ['D', 'F'], 5: ['A', 'L'], 6: ['C', 'E'] }, "5-6": { 1: ['A', 'C', 'L'], 2: ['C', 'G', 'K'], 3: ['D', 'H', 'I'], 4: ['C', 'E', 'M'], 5: ['A', 'B', 'M'], 6: ['E', 'I', 'K'] }}, { "1-4": { 1: ['F', 'K'], 2: ['F', 'H'], 3: ['A', 'C'], 4: ['D', 'K'], 5: ['D', 'G'], 6: ['E', 'H'] }, "5-6": { 1: ['B', 'G', 'L'], 2: ['B', 'L', 'M'], 3: ['C', 'I', 'M'], 4: ['A', 'D', 'M'], 5: ['A', 'G', 'K'], 6: ['B', 'F', 'M'] }}, { "1-4": { 1: ['C', 'M'], 2: ['F', 'L'], 3: ['H', 'K'], 4: ['E', 'K'], 5: ['D', 'I'], 6: ['B', 'L'] }, "5-6": { 1: ['C', 'G', 'M'], 2: ['G', 'H', 'L'], 3: ['C', 'D', 'M'], 4: ['A', 'E', 'I'], 5: ['D', 'F', 'I'], 6: ['E', 'K', 'L'] }}, { "1-4": { 1: ['B', 'I'], 2: ['B', 'M'], 3: ['D', 'M'], 4: ['E', 'I'], 5: ['B', 'H'], 6: ['F', 'I'] }, "5-6": { 1: ['C', 'D', 'I'], 2: ['E', 'G', 'I'], 3: ['D', 'H', 'K'], 4: ['H', 'K', 'L'], 5: ['A', 'E', 'L'], 6: ['A', 'B', 'L'] }}, { "1-4": { 1: ['B', 'D'], 2: ['B', 'E'], 3: ['B', 'G'], 4: ['H', 'L'], 5: ['A', 'M'], 6: ['A', 'D'] }, "5-6": { 1: ['F', 'I', 'K'], 2: ['F', 'H', 'K'], 3: ['G', 'M', 'L'], 4: ['E', 'F', 'K'], 5: ['E', 'H', 'K'], 6: ['B', 'F', 'I'] }}, { "1-4": { 1: ['C', 'I'], 2: ['G', 'K'], 3: ['E', 'G'], 4: ['C', 'H'], 5: ['H', 'M'], 6: ['A', 'G'] }, "5-6": { 1: ['F', 'H', 'K'], 2: ['C', 'F', 'I'], 3: ['B', 'H', 'L'], 4: ['D', 'I', 'M'], 5: ['A', 'L', 'M'], 6: ['B', 'F', 'I'] }}, ]
TERMINAL_DATA: Dict[int, Tuple[Tuple[Tuple[int, int], int], Tuple[Tuple[int, int], int]]] = { 1: ( (((6, 0), 90), ((7, 0), 0)), (((2, 13), 180), ((3, 13), 270)) ), 2: ( (((10, 0), 90), ((11, 0), 0)), (((6, 13), 180), ((7, 13), 270)) ), 3: ( (((2, 0), 90), ((3, 0), 0)), (((10, 13), 180), ((11, 13), 270)) ), 4: ( (((0, 6), 90), ((0, 7), 180)), (((13, 10), 0), ((13, 11), 270)) ), 5: ( (((0, 2), 90), ((0, 3), 180)), (((13, 6), 0), ((13, 7), 270)) ), 6: ( (((0, 10), 90), ((0, 11), 180)), (((13, 2), 0), ((13, 3), 270)) ) }
TERMINAL_COORDS: Dict[int, Tuple[Tuple[int,int], Tuple[int,int]]] = { line: (data[0][0][0], data[1][0][0]) for line, data in TERMINAL_DATA.items() }

## TEST CONFIG #1: STRAIGHT VERTICAL LINE
# # --- Grid Dimensions ---
# GRID_ROWS: int = 5; GRID_COLS: int = 6
# PLAYABLE_ROWS: Tuple[int, int] = (1, 3); PLAYABLE_COLS: Tuple[int, int] = (1, 4)
# # --- Game Rules & Data ---
# BUILDING_COORDS: Dict[str, Tuple[int, int]] = { 'A': (1, 2), 'B': (3, 2) }
# TILE_DEFINITIONS: Dict[str, Dict[str, Any]] = { "Straight": {"connections": [['N', 'S']], "is_swappable": True}, "Curve": {"connections": [['N', 'E']], "is_swappable": True}, "StraightLeftCurve": {"connections": [['N', 'S'], ['S', 'W']], "is_swappable": True}, "StraightRightCurve": {"connections": [['N', 'S'], ['S', 'E']], "is_swappable": True}, "DoubleCurveY": {"connections": [['N', 'W'], ['N', 'E']], "is_swappable": True}, "DiagonalCurve": {"connections": [['S', 'W'], ['N', 'E']], "is_swappable": True}, "Tree_JunctionTop": {"connections": [['E', 'W'], ['W', 'N'], ['N', 'E']], "is_swappable": False}, "Tree_JunctionRight": {"connections": [['E', 'W'], ['N', 'E'], ['S', 'E']], "is_swappable": False}, "Tree_Roundabout": {"connections": [['W', 'N'], ['N', 'E'], ['E', 'S'], ['S', 'W']], "is_swappable": False}, "Tree_Crossroad": {"connections": [['N', 'S'], ['E', 'W']], "is_swappable": False}, "Tree_StraightDiagonal1": {"connections": [['N', 'S'], ['S', 'W'], ['N', 'E']], "is_swappable": False}, "Tree_StraightDiagonal2": {"connections": [['N', 'S'], ['N', 'W'], ['S', 'E']], "is_swappable": False}, }
# TILE_COUNTS_BASE: Dict[str, int] = { "Straight": 21, "Curve": 20, "StraightLeftCurve": 10, "StraightRightCurve": 10, "DoubleCurveY": 10, "DiagonalCurve": 6, "Tree_JunctionTop": 6, "Tree_JunctionRight": 6, "Tree_Roundabout": 4, "Tree_Crossroad": 4, "Tree_StraightDiagonal1": 2, "Tree_StraightDiagonal2": 2, }
# TILE_COUNTS_5_PLUS_ADD: Dict[str, int] = {"Straight": 15, "Curve": 10,}
# STARTING_HAND_TILES: Dict[str, int] = {"Straight": 3, "Curve": 2,}
# ROUTE_CARD_VARIANTS: List[Dict[str, Dict[int, List[str]]]] = [ 
#     { 
#         "1-4": { 1: ['A', 'B'], 2: ['A', 'B'], }}, 
#     ]
# TERMINAL_DATA: Dict[int, Tuple[Tuple[Tuple[int, int], int], Tuple[Tuple[int, int], int]]] = { 1: ( (((0, 3), 90), ((0, 4), 180)), (((4, 3), 0), ((4, 4), 270)) ), }
# TERMINAL_COORDS: Dict[int, Tuple[Tuple[int,int], Tuple[int,int]]] = { line: (data[0][0][0], data[1][0][0]) for line, data in TERMINAL_DATA.items() }

## TEST CONFIG #2: TRICK LOOP REDDIT
# # --- Grid Dimensions ---
# GRID_ROWS: int = 10; GRID_COLS: int = 10
# PLAYABLE_ROWS: Tuple[int, int] = (1, 8); PLAYABLE_COLS: Tuple[int, int] = (1, 8)
# # --- Game Rules & Data ---
# BUILDING_COORDS: Dict[str, Tuple[int, int]] = { 'A': (5, 1), 'B': (4, 6), 'C': (6, 8), 'T': (2, 6) }
# TILE_DEFINITIONS: Dict[str, Dict[str, Any]] = { "Straight": {"connections": [['N', 'S']], "is_swappable": True}, "Curve": {"connections": [['N', 'E']], "is_swappable": True}, "StraightLeftCurve": {"connections": [['N', 'S'], ['S', 'W']], "is_swappable": True}, "StraightRightCurve": {"connections": [['N', 'S'], ['S', 'E']], "is_swappable": True}, "DoubleCurveY": {"connections": [['N', 'W'], ['N', 'E']], "is_swappable": True}, "DiagonalCurve": {"connections": [['S', 'W'], ['N', 'E']], "is_swappable": True}, "Tree_JunctionTop": {"connections": [['E', 'W'], ['W', 'N'], ['N', 'E']], "is_swappable": False}, "Tree_JunctionRight": {"connections": [['E', 'W'], ['N', 'E'], ['S', 'E']], "is_swappable": False}, "Tree_Roundabout": {"connections": [['W', 'N'], ['N', 'E'], ['E', 'S'], ['S', 'W']], "is_swappable": False}, "Tree_Crossroad": {"connections": [['N', 'S'], ['E', 'W']], "is_swappable": False}, "Tree_StraightDiagonal1": {"connections": [['N', 'S'], ['S', 'W'], ['N', 'E']], "is_swappable": False}, "Tree_StraightDiagonal2": {"connections": [['N', 'S'], ['N', 'W'], ['S', 'E']], "is_swappable": False}, }
# TILE_COUNTS_BASE: Dict[str, int] = { "Straight": 21, "Curve": 20, "StraightLeftCurve": 10, "StraightRightCurve": 10, "DoubleCurveY": 10, "DiagonalCurve": 6, "Tree_JunctionTop": 6, "Tree_JunctionRight": 6, "Tree_Roundabout": 4, "Tree_Crossroad": 4, "Tree_StraightDiagonal1": 2, "Tree_StraightDiagonal2": 2, }
# TILE_COUNTS_5_PLUS_ADD: Dict[str, int] = {"Straight": 15, "Curve": 10,}
# STARTING_HAND_TILES: Dict[str, int] = {"Straight": 3, "Curve": 2,}
# ROUTE_CARD_VARIANTS: List[Dict[str, Dict[int, List[str]]]] = [ 
#     { 
#         "1-4": { 1: ['A', 'B', 'C'], 2: ['A', 'B', 'C'], }}, 
#     ]
# TERMINAL_DATA: Dict[int, Tuple[Tuple[Tuple[int, int], int], Tuple[Tuple[int, int], int]]] = { 1: ( (((3, 0), 90), ((4, 0), 0)), (((7, 9), 180), ((8, 9), 270)) ), }
# TERMINAL_COORDS: Dict[int, Tuple[Tuple[int,int], Tuple[int,int]]] = { line: (data[0][0][0], data[1][0][0]) for line, data in TERMINAL_DATA.items() }



# --- Pygame/Visual Layout Constants ---
SCREEN_WIDTH: int = 1366; SCREEN_HEIGHT: int = 800
VISIBLE_GRID_ROWS: int = 12; VISIBLE_GRID_COLS: int = 12
BOARD_AREA_HEIGHT: float = SCREEN_HEIGHT * 0.90; BOARD_AREA_WIDTH: float = BOARD_AREA_HEIGHT
TILE_SIZE: int = int(BOARD_AREA_HEIGHT / VISIBLE_GRID_ROWS)
BOARD_DRAW_WIDTH: int = TILE_SIZE * VISIBLE_GRID_COLS; BOARD_DRAW_HEIGHT: int = TILE_SIZE * VISIBLE_GRID_ROWS
BOARD_X_OFFSET: int = int(SCREEN_WIDTH * 0.04); BOARD_Y_OFFSET: int = (SCREEN_HEIGHT - BOARD_DRAW_HEIGHT) // 2
UI_PANEL_MARGIN_LEFT = 50; UI_PANEL_X: int = BOARD_X_OFFSET + BOARD_DRAW_WIDTH + UI_PANEL_MARGIN_LEFT
UI_PANEL_Y: int = BOARD_Y_OFFSET; UI_PANEL_WIDTH: int = SCREEN_WIDTH - UI_PANEL_X - 20; UI_PANEL_HEIGHT: int = BOARD_DRAW_HEIGHT
HAND_TILE_SIZE: int = int(min(TILE_SIZE * 0.8, UI_PANEL_WIDTH * 0.7)); HAND_SPACING: int = 15; HAND_TILE_COUNT: int = 5
UI_TEXT_X: int = UI_PANEL_X + 15; UI_LINE_HEIGHT: int = 28
UI_TURN_INFO_Y: int = UI_PANEL_Y + 15; UI_ACTION_INFO_Y: int = UI_TURN_INFO_Y
UI_ROUTE_INFO_Y: int = UI_ACTION_INFO_Y + UI_LINE_HEIGHT # Below turn info
# --- Normal Mode UI Positions ---
UI_HAND_TITLE_Y: int = UI_ROUTE_INFO_Y + UI_LINE_HEIGHT * 2
HAND_AREA_X: int = UI_PANEL_X + 15
HAND_AREA_Y: int = UI_HAND_TITLE_Y + UI_LINE_HEIGHT
UI_SELECTED_TILE_Y: int = HAND_AREA_Y + HAND_TILE_COUNT * (HAND_TILE_SIZE + HAND_SPACING) + 20
UI_MESSAGE_Y: int = UI_SELECTED_TILE_Y + UI_LINE_HEIGHT
UI_INSTRUCTIONS_Y: int = UI_MESSAGE_Y + UI_LINE_HEIGHT

# --- Debug Mode UI Positions ---
DEBUG_MODE = False # Default to off
DEBUG_PANEL_TITLE_Y: int = UI_ROUTE_INFO_Y + UI_LINE_HEIGHT * 2 # Same Y as hand title
DEBUG_PANEL_X: int = UI_PANEL_X + 15
DEBUG_PANEL_Y: int = DEBUG_PANEL_TITLE_Y + UI_LINE_HEIGHT # Debug tiles start below title
DEBUG_TILE_SIZE: int = TILE_SIZE // 2
DEBUG_TILE_SPACING: int = 5
DEBUG_TILES_PER_ROW: int = 4
DEBUG_BUTTON_WIDTH: int = 150; DEBUG_BUTTON_HEIGHT: int = 30
DEBUG_BUTTON_X: int = UI_PANEL_X + (UI_PANEL_WIDTH - DEBUG_BUTTON_WIDTH) // 2 # Center button
DEBUG_BUTTON_Y: int = UI_PANEL_Y + UI_PANEL_HEIGHT - DEBUG_BUTTON_HEIGHT - 97 # Bottom of panel


# --- Colors ---
COLOR_WHITE: Tuple[int, int, int] = (255, 255, 255)
COLOR_BLACK: Tuple[int, int, int] = (0, 0, 0)
COLOR_GRID: Tuple[int, int, int] = (100, 100, 100)
COLOR_BOARD_BG: Tuple[int, int, int] = (180, 180, 180)
COLOR_TRACK: Tuple[int, int, int] = (50, 250, 50)
COLOR_STOP: Tuple[int, int, int] = (255, 0, 0)
COLOR_BUILDING_BG: Tuple[int, int, int] = (0, 80, 0)  # Dark Green for background
COLOR_BUILDING_FG: Tuple[int, int, int] = (144, 238, 144) # Light Green for letter (like lightgreen)
COLOR_HIGHLIGHT: Tuple[int, int, int, int] = (255, 255, 0, 150)
COLOR_SELECTED: Tuple[int, int, int] = (90, 150, 255)
COLOR_UI_BG: Tuple[int, int, int] = (200, 200, 220)
COLOR_UI_TEXT: Tuple[int, int, int] = (10, 10, 50)
COLOR_TERMINAL_BG: Tuple[int, int, int] = (160, 160, 190)
COLOR_TERMINAL_TEXT: Tuple[int, int, int] = COLOR_WHITE

# --- Game Rules ---
MAX_PLAYER_ACTIONS: int = 2; HAND_TILE_LIMIT: int = 5


COLOR_P0: Tuple[int, int, int] = (200, 0, 0)    # Red
COLOR_P1: Tuple[int, int, int] = (0, 0, 200)    # Blue
COLOR_P2: Tuple[int, int, int] = (0, 150, 0)    # Green
COLOR_P3: Tuple[int, int, int] = (200, 200, 0)  # Yellow
COLOR_P4: Tuple[int, int, int] = (150, 0, 150)  # Purple
COLOR_P5: Tuple[int, int, int] = (0, 150, 150)  # Cyan
PLAYER_COLORS: List[Tuple[int, int, int]] = [COLOR_P0, COLOR_P1, COLOR_P2, COLOR_P3, COLOR_P4, COLOR_P5]

STOP_SYMBOL = 'H' # Define the symbol used for the 'Stop' face of the die
DIE_FACES: Tuple[Any, ...] = (1, 2, 3, 4, STOP_SYMBOL, STOP_SYMBOL)

COLOR_UI_BUTTON_BG: Tuple[int, int, int] = (180, 180, 180) # Light grey
COLOR_UI_BUTTON_TEXT: Tuple[int, int, int] = COLOR_BLACK

# --- Add constants for Debug Die UI ---
DEBUG_DIE_BUTTON_SIZE: int = 40
DEBUG_DIE_SPACING: int = 10
DEBUG_DIE_AREA_X: int = UI_PANEL_X + 15
DEBUG_DIE_AREA_Y: int = UI_PANEL_Y + 250 # Adjust Y position as needed 

COLOR_TRANSPARENT = (0, 0, 0, 0)
TRACK_WIDTH_RATIO = 0.1 # Adjust for desired track thickness
DEFAULT_FONT_SIZE = 24
FPS = 60
BUTTON_WIDTH = 80 # Adjusted size maybe
BUTTON_HEIGHT = 25
BUTTON_SPACING = 8
BUTTON_MARGIN_X = 10
BUTTON_MARGIN_Y = 10
COLOR_CONFIRM_BG = (100, 200, 100) # Light green maybe

# AI takes 1 ms per move instead of near-instant 2 moves shown on screen
AI_MOVE_DELAY_MS = 1
AI_ACTION_TIMER_EVENT = pygame.USEREVENT + 1
START_NEXT_TURN_EVENT = pygame.USEREVENT + 2 # NEW: For triggering the next turn

# --- AI Difficulty Constants ---
# The higher the number, the more likely an KING AI is to draw a Tree tile.
# A value of 10 means a Tree tile is 10 times more likely than a non-Tree tile.
KING_AI_TREE_TILE_BIAS = 10

# Control search space in ai_strategy.py
# Number of possible single moves = 5 squares * 5 tiles at-hand * 4 orientations = 100
# Number of pairs of moves to check = 100C2 = 4950 pairs of moves
MAX_TARGETS_FOR_COMBO_SEARCH  = 5