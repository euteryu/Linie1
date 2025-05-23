# visualizer.py
# -*- coding: utf-8 -*-
import pygame
import sys
import math
import tkinter as tk
from tkinter import filedialog
from typing import List, Dict, Tuple, Optional, Any
from collections import deque
import copy # Keep if get_effective_connections needs deepcopy

# --- Game Logic Imports ---
# (Adjust based on final refactoring of game_logic)
from game_logic.game import Game
from game_logic.tile import PlacedTile, TileType
from game_logic.enums import GamePhase, PlayerState, Direction
from game_logic.player import Player

# --- State Machine ---
# Import base class and specific states
from game_states import (GameState, LayingTrackState, DrivingState,
                         GameOverState)

# --- Constants ---
import constants as C # Use alias


# === Helper Function for Drawing Tiles ===

def create_tile_surface(tile_type: TileType, size: int) -> pygame.Surface:
    """ Creates a Pygame Surface using lines and arcs for a tile type. """
    # Use SRALPHA for transparency support if needed later
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    # Make background transparent for easy layering
    surf.fill(C.COLOR_TRANSPARENT)

    line_width = max(2, int(size * C.TRACK_WIDTH_RATIO)) # Use const
    track_color = C.COLOR_TRACK

    # Center points and radii/rects for drawing arcs/lines
    half_size = size // 2
    ptN = (half_size, 0)
    ptS = (half_size, size)
    ptE = (size, half_size)
    ptW = (0, half_size)
    center = (half_size, half_size)

    # Rects for drawing arcs, offset to be centered correctly
    # Top-Right quadrant arc center: (size, 0)
    rect_TR = pygame.Rect(half_size, -half_size, size, size)
    # Top-Left quadrant arc center: (0, 0)
    rect_TL = pygame.Rect(-half_size, -half_size, size, size)
    # Bottom-Right quadrant arc center: (size, size)
    rect_BR = pygame.Rect(half_size, half_size, size, size)
    # Bottom-Left quadrant arc center: (0, size)
    rect_BL = pygame.Rect(-half_size, half_size, size, size)

    # Angles (in radians, Pygame uses degrees for arc start/stop)
    # Pygame angles: 0=East, 90=North, 180=West, 270=South
    angle_N = math.radians(90)
    angle_E = math.radians(0)
    angle_S = math.radians(270)
    angle_W = math.radians(180)

    # --- Simplified Drawing based on Tile Type Name ---
    # This assumes base orientation (0 degrees) as defined in constants
    tile_name = tile_type.name

    # Note: Pygame arc angles go counter-clockwise
    if tile_name == "Straight": # N-S
        pygame.draw.line(surf, track_color, ptN, ptS, line_width)
    elif tile_name == "Curve": # N-E
        pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E,
                        line_width)
    elif tile_name == "StraightLeftCurve": # N-S, S-W
        pygame.draw.line(surf, track_color, ptN, ptS, line_width)
        pygame.draw.arc(surf, track_color, rect_BL, angle_S, angle_W,
                        line_width)
    elif tile_name == "StraightRightCurve": # N-S, S-E
        pygame.draw.line(surf, track_color, ptN, ptS, line_width)
        pygame.draw.arc(surf, track_color, rect_BR, angle_E, angle_S,
                        line_width)
    elif tile_name == "DoubleCurveY": # N-W, N-E ("Y" shape from North)
        pygame.draw.arc(surf, track_color, rect_TL, angle_W, angle_N,
                        line_width)
        pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E,
                        line_width)
    elif tile_name == "DiagonalCurve": # S-W, N-E (Diagonal slash)
        pygame.draw.arc(surf, track_color, rect_BL, angle_S, angle_W,
                        line_width)
        pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E,
                        line_width)
    elif tile_name == "Tree_JunctionTop": # E-W, W-N, N-E (T-junction open South)
        pygame.draw.line(surf, track_color, ptW, ptE, line_width)
        pygame.draw.arc(surf, track_color, rect_TL, angle_W, angle_N,
                        line_width)
        pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E,
                        line_width)
    elif tile_name == "Tree_JunctionRight": # E-W, N-E, S-E (T-junction open West)
        pygame.draw.line(surf, track_color, ptW, ptE, line_width)
        pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E,
                        line_width)
        pygame.draw.arc(surf, track_color, rect_BR, angle_E, angle_S,
                        line_width)
    elif tile_name == "Tree_Roundabout": # W-N, N-E, E-S, S-W (All curves)
        pygame.draw.arc(surf, track_color, rect_TL, angle_W, angle_N,
                        line_width)
        pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E,
                        line_width)
        pygame.draw.arc(surf, track_color, rect_BR, angle_E, angle_S,
                        line_width)
        pygame.draw.arc(surf, track_color, rect_BL, angle_S, angle_W,
                        line_width)
    elif tile_name == "Tree_Crossroad": # N-S, E-W (+)
        pygame.draw.line(surf, track_color, ptN, ptS, line_width)
        pygame.draw.line(surf, track_color, ptW, ptE, line_width)
    elif tile_name == "Tree_StraightDiagonal1": # N-S, S-W, N-E
        pygame.draw.line(surf, track_color, ptN, ptS, line_width)
        pygame.draw.arc(surf, track_color, rect_BL, angle_S, angle_W,
                        line_width)
        pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E,
                        line_width)
    elif tile_name == "Tree_StraightDiagonal2": # N-S, N-W, S-E
        pygame.draw.line(surf, track_color, ptN, ptS, line_width)
        pygame.draw.arc(surf, track_color, rect_TL, angle_W, angle_N,
                        line_width)
        pygame.draw.arc(surf, track_color, rect_BR, angle_E, angle_S,
                        line_width)
    else:
        # Draw a placeholder for unknown types
        print(f"Warning: Unknown tile type to draw: {tile_name}")
        pygame.draw.rect(surf, C.COLOR_GRID, surf.get_rect(), 1)
        pygame.draw.line(surf, C.COLOR_STOP, (0, 0), (size, size), 1)
        pygame.draw.line(surf, C.COLOR_STOP, (0, size), (size, 0), 1)

    return surf

# === Main Visualizer Class ===

class Linie1Visualizer:
    """
    Manages the Pygame window, main loop, drawing, and input delegation
    based on the current game state.
    """
    def __init__(self, num_players=2):
        pygame.init()
        pygame.font.init() # Explicitly init font module

        self.screen = pygame.display.set_mode(
            (C.SCREEN_WIDTH, C.SCREEN_HEIGHT)
        )
        pygame.display.set_caption("Linie 1")
        self.clock = pygame.time.Clock()

        # Attempt to load preferred font, fallback to default
        try:
            self.font = pygame.font.SysFont(None, C.DEFAULT_FONT_SIZE)
        except Exception as e:
            print(f"SysFont error: {e}. Using default font.")
            self.font = pygame.font.Font(None, C.DEFAULT_FONT_SIZE)

        # Initialize Tkinter root for file dialogs (hidden)
        try:
            self.tk_root = tk.Tk()
            self.tk_root.withdraw()
        except Exception as e:
            print(f"Warning: Tkinter init failed ({e}). File dialogs disabled.")
            self.tk_root = None

        # --- Create Game instance ---
        try:
            self.game = Game(num_players=num_players)
            # Ensure setup runs if game starts in SETUP phase
            if self.game.game_phase == GamePhase.SETUP:
                self.game.setup_game()
        except Exception as e:
             print(f"FATAL: Game initialization failed: {e}")
             traceback.print_exc()
             pygame.quit()
             sys.exit()


        # --- Calculate UI Element Sizes ---
        self.TILE_SIZE = C.TILE_SIZE
        self.HAND_TILE_SIZE = C.HAND_TILE_SIZE

        # --- Debug Mode Attributes ---
        self.debug_mode = C.DEBUG_MODE
        self.debug_tile_types: List[TileType] = list(
            self.game.tile_types.values()
        )
        # Create surfaces for debug palette/die
        self.debug_tile_surfaces = self._create_debug_tile_surfaces()
        self.debug_die_surfaces = self._create_debug_die_surfaces()
        # Rects for clicking, calculated during draw
        self.debug_tile_rects: Dict[int, pygame.Rect] = {}
        self.debug_die_rects: Dict[Any, pygame.Rect] = {}


        # --- Create Tile Surfaces for Drawing ---
        print("Generating main tile surfaces...")
        self.tile_surfaces = {
            name: create_tile_surface(ttype, self.TILE_SIZE)
            for name, ttype in self.game.tile_types.items()
        }
        self.hand_tile_surfaces = {
             name: create_tile_surface(ttype, self.HAND_TILE_SIZE)
             for name, ttype in self.game.tile_types.items()
        }
        print("Tile surfaces generated.")


        # --- UI Button Rectangles ---
        btn_w = C.BUTTON_WIDTH; btn_h = C.BUTTON_HEIGHT; btn_s = C.BUTTON_SPACING
        btn_y = C.UI_PANEL_Y + C.UI_PANEL_HEIGHT - btn_h - C.BUTTON_MARGIN_Y
        btn_x = C.UI_PANEL_X + C.BUTTON_MARGIN_X

        self.save_button_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        btn_x += btn_w + btn_s
        self.load_button_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        btn_x += btn_w + btn_s
        self.undo_button_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        btn_x += btn_w + btn_s
        self.redo_button_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        # Debug toggle might be positioned differently if needed
        self.debug_toggle_button_rect = pygame.Rect(
            C.DEBUG_BUTTON_X, C.DEBUG_BUTTON_Y,
            C.DEBUG_BUTTON_WIDTH, C.DEBUG_BUTTON_HEIGHT
        )

        btn_x += btn_w + btn_s
        self.undo_button_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        btn_x += btn_w + btn_s
        self.redo_button_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        # Confirm button (only drawn when needed by state)
        # Position near bottom center of UI panel?
        confirm_x = C.UI_PANEL_X + (C.UI_PANEL_WIDTH - btn_w) // 2
        confirm_y = btn_y - btn_h - btn_s # Place above other buttons
        self.confirm_button_rect = pygame.Rect(confirm_x, confirm_y, btn_w, btn_h)


        # --- Initial Game State ---
        self.current_state: GameState = LayingTrackState(self) # Start state
        # Ensure correct state is set based on loaded game if applicable
        self.update_current_state_for_player()


    def _create_debug_tile_surfaces(self) -> Dict[str, pygame.Surface]:
        """ Creates surfaces for the debug tile palette. """
        return {
            ttype.name: create_tile_surface(ttype, C.DEBUG_TILE_SIZE)
            for ttype in self.debug_tile_types
        }

    def _create_debug_die_surfaces(self) -> Dict[Any, pygame.Surface]:
        # ... (logic as corrected before to build ordered_unique_faces) ...
        unique_faces = set(C.DIE_FACES); ordered_unique_faces = []; # ... build list ...
        if C.STOP_SYMBOL in unique_faces: ordered_unique_faces.append(C.STOP_SYMBOL)
        numbers = sorted([f for f in unique_faces if isinstance(f, int)]); ordered_unique_faces.extend(numbers)

        surfaces = {}
        size = C.DEBUG_DIE_BUTTON_SIZE
        font_size = int(size * 0.7)
        try:
            font = pygame.font.SysFont(None, font_size)
        except Exception as e: # Catch specific errors if possible
            print(f"SysFont loading error: {e}. Falling back.")
            try:
                 font = pygame.font.Font(None, font_size) # Fallback
            except Exception as e2:
                 print(f"Fallback font loading error: {e2}. Cannot create die surfaces.")
                 return {} # Return empty if font fails completely

        for face in ordered_unique_faces:
             # ... (create surf, fill white, draw border) ...
             surf = pygame.Surface((size, size)); surf.fill(C.COLOR_WHITE); pygame.draw.rect(surf, C.COLOR_BLACK, surf.get_rect(), 1)
             try:
                 text_surf = font.render(str(face), True, C.COLOR_BLACK)
                 text_rect = text_surf.get_rect(center=(size // 2, size // 2))
                 surf.blit(text_surf, text_rect)
                 surfaces[face] = surf
             except Exception as e:
                 print(f"Error rendering/blitting text for die face {face}: {e}")
        return surfaces

    def draw_highlighted_path(self, screen, path_coords: Optional[List[Tuple[int, int]]]):
        """Draws a translucent overlay over tiles in the given path."""
        if not path_coords: return

        highlight_color = (255, 255, 0, 70) # Yellow, semi-transparent

        for i, (r, c) in enumerate(path_coords):
             if not self.game.board.is_valid_coordinate(r, c): continue
             # Calculate screen rect for the tile
             screen_x = C.BOARD_X_OFFSET + (c - C.PLAYABLE_COLS[0]) * self.TILE_SIZE
             screen_y = C.BOARD_Y_OFFSET + (r - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE
             rect = pygame.Rect(screen_x, screen_y, self.TILE_SIZE, self.TILE_SIZE)

             # Create a temporary surface for the highlight
             temp_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
             temp_surf.fill(highlight_color)
             screen.blit(temp_surf, rect.topleft)

             # Optional: Draw arrows indicating direction? More complex.

    def run(self):
        """ Main game loop. """
        running = True
        while running:
            dt = self.clock.tick(C.FPS) / 1000.0 # Use FPS constant
            events = pygame.event.get()

            # Update visualizer state based on active player *before* events
            self.update_current_state_for_player()

            # Handle Events using current state
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                    break # Exit inner loop

                # Let current state handle event (incl. common clicks)
                if self.current_state:
                     self.current_state.handle_event(event)

            if not running: break # Exit outer loop if QUIT received

            # Update current state (for animations etc., if needed)
            if self.current_state:
                 self.current_state.update(dt)

            # Drawing
            self.screen.fill(C.COLOR_UI_BG)
            if self.current_state:
                # Delegate drawing to the current state
                self.current_state.draw(self.screen)
                # Draw highlighted path if applicable (AFTER board, BEFORE streetcars/UI?)
                if isinstance(self.current_state, DrivingState) and self.current_state.current_move_path:
                    self.draw_highlighted_path(self.screen, self.current_state.current_move_path)
                # Draw streetcars (now includes all players) - MOVE THIS CALL?
                # self.draw_streetcars(self.screen) # Maybe call this after board?
            else:
                 # Handle case where state might be None (error?)
                 self.draw_text(self.screen, "Error: Invalid State", 10, 10, C.COLOR_STOP)

            pygame.display.flip()

        # Cleanup
        pygame.quit()
        # Close tkinter root if it exists
        if self.tk_root:
             self.tk_root.destroy()
        sys.exit()


    def update_current_state_for_player(self):
        """ Sets self.current_state based on the active player's state. """
        # (Implementation as provided previously)
        try:
            active_player = self.game.get_active_player(); player_state = active_player.player_state; game_phase = self.game.game_phase; # ... Determine target_state_class ...
            target_state_class = None
            if game_phase == GamePhase.GAME_OVER: target_state_class = GameOverState
            elif player_state == PlayerState.DRIVING: target_state_class = DrivingState
            elif player_state == PlayerState.LAYING_TRACK: target_state_class = LayingTrackState
            else: target_state_class = LayingTrackState # Default
            if not isinstance(self.current_state, target_state_class):
                print(f"State Change: -> {target_state_class.__name__}")
                self.current_state = target_state_class(self)
        except (IndexError, AttributeError) as e: print(f"Error updating state: {e}") # ... error handling ...


    def draw_text(self, surface, text, x, y, color=C.COLOR_UI_TEXT,
                  size=C.DEFAULT_FONT_SIZE):
        """ Helper method to draw text using the default font. """
        try:
            # Use cached font if default size, else create temporary one
            font_to_use = self.font if size == C.DEFAULT_FONT_SIZE else \
                          pygame.font.SysFont(None, size)
            text_surface = font_to_use.render(text, True, color)
            surface.blit(text_surface, (x, y))
        except Exception as e:
            # Fallback if SysFont fails
            try:
                font_to_use = pygame.font.Font(None, size)
                text_surface = font_to_use.render(text, True, color)
                surface.blit(text_surface, (x, y))
            except Exception as e2:
                 print(f"Error rendering text '{text}': {e} / {e2}")


    def draw_board(self, screen):
        # --- Draw Board Background, Grid, Tiles, Buildings, Stop Signs ---
        # (Keep existing logic for drawing the static board elements)
        drawn_terminal_labels = set()
        for r in range(C.GRID_ROWS):
            for c in range(C.GRID_COLS):
                # Limit drawing range slightly for performance maybe?
                # if not (C.PLAYABLE_ROWS[0]-1 <= r <= C.PLAYABLE_ROWS[1]+1 and C.PLAYABLE_COLS[0]-1 <= c <= C.PLAYABLE_COLS[1]+1): continue

                screen_x = C.BOARD_X_OFFSET + (c - C.PLAYABLE_COLS[0]) * self.TILE_SIZE
                screen_y = C.BOARD_Y_OFFSET + (r - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE
                rect = pygame.Rect(screen_x, screen_y, self.TILE_SIZE, self.TILE_SIZE)

                placed_tile = self.game.board.get_tile(r, c)
                is_playable = self.game.board.is_playable_coordinate(r, c)
                is_terminal = placed_tile is not None and hasattr(placed_tile, 'is_terminal') and placed_tile.is_terminal # Safer check

                # Determine Background Color
                bg_color = C.COLOR_BOARD_BG
                if is_terminal:
                    bg_color = C.COLOR_TERMINAL_BG
                elif not is_playable and not (0 <= r < C.GRID_ROWS and 0 <= c < C.GRID_COLS): # Check if truly outside grid bounds
                    bg_color = tuple(max(0, val - 40) for val in C.COLOR_BOARD_BG) # Dim outside area
                elif not is_playable: # Border area inside grid bounds
                     bg_color = C.COLOR_GRID # Use a specific border color maybe?

                pygame.draw.rect(screen, bg_color, rect)
                pygame.draw.rect(screen, C.COLOR_GRID, rect, 1) # Grid line

                # Draw Placed Tile (Tracks)
                if placed_tile:
                    tile_surf = self.tile_surfaces.get(placed_tile.tile_type.name)
                    if tile_surf:
                        rotated_surf = pygame.transform.rotate(tile_surf, -placed_tile.orientation)
                        new_rect = rotated_surf.get_rect(center=rect.center)
                        screen.blit(rotated_surf, new_rect.topleft)

                # Draw Building (Letter over BG)
                building_id = self.game.board.get_building_at(r, c)
                if building_id and is_playable:
                    # ... (keep updated building drawing logic) ...
                    pygame.draw.rect(screen, C.COLOR_BUILDING_BG, rect) # Dark BG
                    font_size = int(self.TILE_SIZE * 0.7); # ... get font ...
                    try: b_font = pygame.font.SysFont(None, font_size)
                    except: b_font = pygame.font.Font(None, font_size)
                    b_surf = b_font.render(building_id, True, C.COLOR_BUILDING_FG); # Light FG
                    b_rect = b_surf.get_rect(center=rect.center); screen.blit(b_surf, b_rect.topleft)
                    pygame.draw.rect(screen, C.COLOR_GRID, rect, 1) # Redraw grid over building

                # Draw Stop Sign (AFTER tile/building)
                if placed_tile and hasattr(placed_tile, 'has_stop_sign') and placed_tile.has_stop_sign and is_playable:
                    # Create a separate surface for the stop sign for alpha blending
                    stop_radius = self.TILE_SIZE // 4
                    # Diameter + 2 for safety margin if drawing border later
                    stop_surface_size = stop_radius * 2 + 2
                    stop_surf = pygame.Surface((stop_surface_size, stop_surface_size), pygame.SRCALPHA)
                    stop_surf.fill((0,0,0,0)) # Fill with transparent background

                    # Draw the circle onto the temporary surface
                    center_pos = stop_surface_size // 2
                    pygame.draw.circle(stop_surf, C.COLOR_STOP, (center_pos, center_pos), stop_radius)
                    # Optional: Draw black border on the temp surface too
                    pygame.draw.circle(stop_surf, C.COLOR_BLACK, (center_pos, center_pos), stop_radius, 1)

                    # Set the overall alpha for the stop sign surface
                    stop_surf.set_alpha(128) # Approx 50% transparent (0=transparent, 255=opaque)

                    # Calculate the top-left position to blit the surface centered in the tile
                    blit_rect = stop_surf.get_rect(center=rect.center)
                    screen.blit(stop_surf, blit_rect.topleft)

        # --- Draw Terminal Labels (AFTER all tiles) ---
        drawn_terminal_labels = set() # Keep track to draw each line number only once per pair
        terminal_font = pygame.font.SysFont(None, int(self.TILE_SIZE * 0.5)) # ...
        for line_num, entrances in C.TERMINAL_DATA.items():
             # Ensure we don't draw labels twice if data is duplicated somehow (unlikely)
             # if line_num in drawn_terminal_labels: continue # Probably not needed

             try: # Add error handling for potentially malformed TERMINAL_DATA
                 # Unpack data for the two entrances (pairs of cells) for this line
                 entrance_a, entrance_b = entrances
                 cell1_a_info, cell2_a_info = entrance_a
                 cell1_b_info, cell2_b_info = entrance_b
                 cell1_a_coord, _ = cell1_a_info # We only need the coord for positioning label
                 cell2_a_coord, _ = cell2_a_info
                 cell1_b_coord, _ = cell1_b_info
                 cell2_b_coord, _ = cell2_b_info

                 # --- Calculate position and draw label for Entrance A ---
                 # Convert grid coords to screen coords for the two cells of entrance A
                 rect1_x1 = C.BOARD_X_OFFSET + (cell1_a_coord[1] - C.PLAYABLE_COLS[0]) * self.TILE_SIZE
                 rect1_y1 = C.BOARD_Y_OFFSET + (cell1_a_coord[0] - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE
                 rect2_x1 = C.BOARD_X_OFFSET + (cell2_a_coord[1] - C.PLAYABLE_COLS[0]) * self.TILE_SIZE
                 rect2_y1 = C.BOARD_Y_OFFSET + (cell2_a_coord[0] - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE
                 # Find the center point between the two cells for placing the label
                 pair1_center_x = (rect1_x1 + rect2_x1 + self.TILE_SIZE) // 2
                 pair1_center_y = (rect1_y1 + rect2_y1 + self.TILE_SIZE) // 2

                 # Render the label text
                 term_surf = terminal_font.render(str(line_num), True, C.COLOR_TERMINAL_TEXT) # Use defined text color
                 term_rect1 = term_surf.get_rect(center=(pair1_center_x, pair1_center_y))
                 # Optional: Draw a background rectangle behind the label for better visibility
                 bg_rect1 = term_rect1.inflate(6, 4) # Add padding
                 pygame.draw.rect(screen, C.COLOR_BLACK, bg_rect1, border_radius=3) # Use a label BG color
                 # Draw the text itself
                 screen.blit(term_surf, term_rect1)

                 # --- Calculate position and draw label for Entrance B ---
                 # Convert grid coords to screen coords for the two cells of entrance B
                 rect1_x2 = C.BOARD_X_OFFSET + (cell1_b_coord[1] - C.PLAYABLE_COLS[0]) * self.TILE_SIZE
                 rect1_y2 = C.BOARD_Y_OFFSET + (cell1_b_coord[0] - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE
                 rect2_x2 = C.BOARD_X_OFFSET + (cell2_b_coord[1] - C.PLAYABLE_COLS[0]) * self.TILE_SIZE
                 rect2_y2 = C.BOARD_Y_OFFSET + (cell2_b_coord[0] - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE
                 # Find the center point between the two cells
                 pair2_center_x = (rect1_x2 + rect2_x2 + self.TILE_SIZE) // 2
                 pair2_center_y = (rect1_y2 + rect2_y2 + self.TILE_SIZE) // 2

                 # Render the label text (can reuse term_surf)
                 term_rect2 = term_surf.get_rect(center=(pair2_center_x, pair2_center_y))
                 # Optional: Draw background
                 bg_rect2 = term_rect2.inflate(6, 4)
                 pygame.draw.rect(screen, C.COLOR_BLACK, bg_rect2, border_radius=3)
                 # Draw the text
                 screen.blit(term_surf, term_rect2)

                 # Mark this line number as drawn (though likely unnecessary)
                 # drawn_terminal_labels.add(line_num)

             except (IndexError, TypeError, ValueError) as e:
                  print(f"Error processing TERMINAL_DATA for Line {line_num}: {e}")
                  # Continue to next line if data is malformed


        # --- <<<< DRAW ALL ACTIVE STREETCARS >>>> ---
        for player in self.game.players:
            if player.player_state == PlayerState.DRIVING and player.streetcar_position:
                 r, c = player.streetcar_position
                 if self.game.board.is_valid_coordinate(r, c):
                     # Calculate center screen coordinates
                     screen_x = C.BOARD_X_OFFSET + (c - C.PLAYABLE_COLS[0]) * self.TILE_SIZE + C.TILE_SIZE // 2
                     screen_y = C.BOARD_Y_OFFSET + (r - C.PLAYABLE_ROWS[0]) * C.TILE_SIZE + C.TILE_SIZE // 2

                     # Create a separate surface for the tram
                     tram_radius = C.TILE_SIZE // 3
                     tram_surface_size = tram_radius * 2 + 2
                     tram_surf = pygame.Surface((tram_surface_size, tram_surface_size), pygame.SRCALPHA)
                     tram_surf.fill((0,0,0,0)) # Transparent background

                     # Draw tram circle onto the temporary surface
                     center_pos = tram_surface_size // 2
                     p_color_index = player.player_id % len(C.PLAYER_COLORS)
                     p_color = C.PLAYER_COLORS[p_color_index]
                     pygame.draw.circle(tram_surf, p_color, (center_pos, center_pos), tram_radius)
                     pygame.draw.circle(tram_surf, C.COLOR_BLACK, (center_pos, center_pos), tram_radius, 1) # Border

                     # Optional: Draw player ID inside the circle on the temp surface
                     id_font_size = int(tram_radius * 1.5)
                     try: id_font = pygame.font.SysFont(None, id_font_size)
                     except: id_font = pygame.font.Font(None, id_font_size) # Fallback
                     id_surf = id_font.render(str(player.player_id), True, C.COLOR_WHITE) # White text
                     id_rect = id_surf.get_rect(center=(center_pos, center_pos))
                     tram_surf.blit(id_surf, id_rect)

                     # Set the overall alpha for the tram surface
                     tram_surf.set_alpha(128) # Slightly less transparent? (Adjust 0-255)

                     # Calculate blit position and draw the tram surface
                     blit_rect = tram_surf.get_rect(center=(screen_x, screen_y))
                     screen.blit(tram_surf, blit_rect.topleft)


    def draw_hand(self, screen, player: Player):
        """ Draws the player's actual hand tiles (Normal Mode). """
        hand_rects = {}
        y_pos = C.HAND_AREA_Y
        for i, tile_type in enumerate(player.hand):
            if i >= C.HAND_TILE_LIMIT: break # Should not happen if logic correct
            x_pos = C.HAND_AREA_X
            rect = pygame.Rect(x_pos, y_pos, self.HAND_TILE_SIZE,
                                self.HAND_TILE_SIZE)
            hand_rects[i] = rect

            pygame.draw.rect(screen, C.COLOR_WHITE, rect) # BG
            hand_surf = self.hand_tile_surfaces.get(tile_type.name)
            if hand_surf:
                img_rect = hand_surf.get_rect(center=rect.center)
                screen.blit(hand_surf, img_rect.topleft)
            pygame.draw.rect(screen, C.COLOR_BLACK, rect, 1) # Border

            # Highlight if selected in GameState
            gs = self.current_state
            if isinstance(gs, LayingTrackState) and \
               not self.debug_mode and gs.selected_tile_index == i:
                 pygame.draw.rect(screen, C.COLOR_SELECTED, rect, 3)

            y_pos += self.HAND_TILE_SIZE + C.HAND_SPACING
        return hand_rects

    def draw_ui(self, screen, message, selected_tile_type,
                orientation):
        """
        Draws all User Interface elements, adapting to the
        current game state and debug mode.
        """
        # --- Get Current Player Info (Safely) ---
        try:
             player = self.game.get_active_player()
             player_id = player.player_id
             player_state_name = player.player_state.name
             player_line_card = player.line_card
             player_route_card = player.route_card
        except (IndexError, AttributeError):
             # Handle cases where player might be invalid
             print("Warning: Could not get valid active player for UI.")
             player_id = "?"
             player_state_name = "Unknown"
             player_line_card = None
             player_route_card = None

        # --- Draw Top Info Panel ---
        # Turn and Player State
        turn_text = (f"Turn {self.game.current_turn} - "
                     f"Player {player_id} ({player_state_name})")
        self.draw_text(screen, turn_text, C.UI_TEXT_X,
                       C.UI_TURN_INFO_Y)

        # Actions Taken (Right-aligned)
        action_text = (f"Actions: {self.game.actions_taken_this_turn}/"
                       f"{C.MAX_PLAYER_ACTIONS}")
        try:
            # Use default font unless specified otherwise
            font_to_use = self.font if self.font else \
                          pygame.font.Font(None, 24)
            action_surf = font_to_use.render(
                action_text, True, C.COLOR_UI_TEXT
            )
            action_text_width = action_surf.get_width()
            action_x = (C.UI_PANEL_X + C.UI_PANEL_WIDTH -
                        action_text_width - 15)
            self.draw_text(screen, action_text, action_x,
                           C.UI_TURN_INFO_Y)
        except Exception as e:
            print(f"Error rendering action text: {e}")

        # Player's Route Info (Line + Stops)
        line_info = "Line: ?"
        stops_info = "Stops: ?"
        if player_line_card:
             # Fetch terminal coordinates for display text
             term1, term2 = self.game.get_terminal_coords(
                 player_line_card.line_number
             )
             term1_str = f"T{player_line_card.line_number}a" if term1 else "?"
             term2_str = f"T{player_line_card.line_number}b" if term2 else "?"
             line_info = (f"Line {player_line_card.line_number} "
                          f"({term1_str}<->{term2_str})")
        if player_route_card:
             stops_str = " -> ".join(player_route_card.stops)
             stops_info = f"Stops: {stops_str}"

        self.draw_text(screen, line_info, C.UI_TEXT_X, C.UI_ROUTE_INFO_Y)
        self.draw_text(screen, stops_info, C.UI_TEXT_X,
                       C.UI_ROUTE_INFO_Y + C.UI_LINE_HEIGHT)


        # --- Draw Middle Section Title (Hand or Debug Palette) ---
        # Only relevant when laying tracks
        if isinstance(self.current_state, LayingTrackState):
            title_y = C.UI_HAND_TITLE_Y
            if self.debug_mode:
                 title_text = "DEBUG TILE PALETTE"
            # Only draw hand title if player is valid & not debug
            elif player_id != "?":
                 title_text = f"Player {player_id}'s Hand:"
            else:
                 title_text = "" # No title if invalid player

            if title_text:
                 self.draw_text(screen, title_text, C.HAND_AREA_X, title_y)

        if self.debug_mode and isinstance(self.current_state, DrivingState):
                self.draw_debug_die_panel(screen, self.current_state.last_roll) # Pass last roll


        # --- Draw Lower Section (Selection, Message, Instructions) ---
        # Calculate start Y pos based on state and mode
        lower_ui_start_y = C.UI_SELECTED_TILE_Y # Default for normal mode
        if isinstance(self.current_state, LayingTrackState):
             if self.debug_mode:
                  # Calculate Y below debug panel
                  num_rows = (
                      (len(self.debug_tile_types) + C.DEBUG_TILES_PER_ROW - 1) //
                       C.DEBUG_TILES_PER_ROW
                  )
                  panel_h = num_rows * (C.DEBUG_TILE_SIZE + C.DEBUG_TILE_SPACING)
                  lower_ui_start_y = C.DEBUG_PANEL_Y + panel_h + 10
        elif isinstance(self.current_state, DrivingState):
             # Driving state message/instructions start lower maybe?
             # Or use standard positions if debug die panel is separate
             lower_ui_start_y = C.UI_MESSAGE_Y # Start with message Y
             if self.debug_mode:
                 # If debug die panel exists, push lower UI further down
                 # This assumes debug die panel is drawn before this section
                 num_die_rows = 1 # Assuming horizontal layout
                 panel_h = num_die_rows * (C.DEBUG_DIE_BUTTON_SIZE + C.DEBUG_DIE_SPACING)
                 lower_ui_start_y = C.DEBUG_DIE_AREA_Y + panel_h + 10


        # Draw Selected Tile Info (if applicable, mainly for LayingTrack)
        if isinstance(self.current_state, LayingTrackState):
            sel_text = "Selected: None"
            if selected_tile_type: # Passed from GameState
                sel_text = (f"Selected: {selected_tile_type.name} "
                            f"({orientation}°)")
            self.draw_text(screen, sel_text, C.UI_TEXT_X, lower_ui_start_y)
            msg_y = lower_ui_start_y + C.UI_LINE_HEIGHT
            instr_y = msg_y + C.UI_LINE_HEIGHT
        else:
             # No "Selected Tile" text in Driving/Game Over
             msg_y = lower_ui_start_y
             instr_y = msg_y + C.UI_LINE_HEIGHT


        # Draw Message (passed in from GameState)
        self.draw_text(screen, f"Msg: {message}", C.UI_TEXT_X, msg_y)

        # Draw Instructions based on State and Mode
        instr_text = ""
        if isinstance(self.current_state, LayingTrackState):
             instr_text = "[RMB/R] Rot | [LMB] Place/Select"
             if not self.debug_mode:
                  instr_text += " | [SPACE] End Turn"
        elif isinstance(self.current_state, DrivingState):
             instr_text = "[SPACE] Roll & Move (Normal)"
             if self.debug_mode:
                 instr_text += " | [Click Die Face]"
        elif isinstance(self.current_state, GameOverState):
             instr_text = "Game Over!"

        # Add debug toggle instruction if not game over
        if not isinstance(self.current_state, GameOverState):
             instr_text += " | [Btn] Debug" if instr_text else "[Btn] Debug"

        self.draw_text(screen, instr_text, C.UI_TEXT_X, instr_y, size=18)


        # --- Always Draw Buttons (Save, Load, Debug Toggle) ---
        btn_text_color = C.COLOR_UI_BUTTON_TEXT
        btn_font_size = 18

        # Save Button
        pygame.draw.rect(screen, C.COLOR_UI_BUTTON_BG, self.save_button_rect)
        pygame.draw.rect(screen, C.COLOR_BLACK, self.save_button_rect, 1)
        self.draw_text(screen, "Save Game", self.save_button_rect.x + 10,
                       self.save_button_rect.y + 7, btn_text_color,
                       size=btn_font_size)

        # Load Button
        pygame.draw.rect(screen, C.COLOR_UI_BUTTON_BG, self.load_button_rect)
        pygame.draw.rect(screen, C.COLOR_BLACK, self.load_button_rect, 1)
        self.draw_text(screen, "Load Game", self.load_button_rect.x + 10,
                       self.load_button_rect.y + 7, btn_text_color,
                       size=btn_font_size)

        # Debug Toggle Button
        debug_btn_bg = C.COLOR_STOP if self.debug_mode else C.COLOR_UI_BUTTON_BG
        pygame.draw.rect(screen, debug_btn_bg, self.debug_toggle_button_rect)
        pygame.draw.rect(screen, C.COLOR_BLACK, self.debug_toggle_button_rect, 1)
        debug_btn_text = "Debug: ON" if self.debug_mode else "Debug: OFF"
        # Adjust font size for smaller button automatically?
        dbg_btn_font_size = 18 if self.debug_toggle_button_rect.width < 80 else 20
        try:
             btn_font = pygame.font.SysFont(None, dbg_btn_font_size)
        except:
             btn_font = pygame.font.Font(None, dbg_btn_font_size) # Fallback
        btn_surf = btn_font.render(debug_btn_text, True, btn_text_color)
        btn_rect = btn_surf.get_rect(center=self.debug_toggle_button_rect.center)
        screen.blit(btn_surf, btn_rect)

        # --- Draw Undo/Redo Buttons ---
        # Grey out if not available?
        undo_color = C.COLOR_UI_BUTTON_TEXT if self.game.command_history.can_undo() else C.COLOR_GRID
        pygame.draw.rect(screen, C.COLOR_UI_BUTTON_BG, self.undo_button_rect)
        pygame.draw.rect(screen, C.COLOR_BLACK, self.undo_button_rect, 1)
        self.draw_text(screen, "Undo(Z)", self.undo_button_rect.x + 10,
                       self.undo_button_rect.y + 7, undo_color, size=18)

        redo_color = C.COLOR_UI_BUTTON_TEXT if self.game.command_history.can_redo() else C.COLOR_GRID
        pygame.draw.rect(screen, C.COLOR_UI_BUTTON_BG, self.redo_button_rect)
        pygame.draw.rect(screen, C.COLOR_BLACK, self.redo_button_rect, 1)
        self.draw_text(screen, "Redo(Y)", self.redo_button_rect.x + 10,
                       self.redo_button_rect.y + 7, redo_color, size=18)

        # # --- Draw Confirm Button ---
        # # (Condition logic remains same - show only when needed)
        # if isinstance(self.current_state, LayingTrackState) and \
        #    not self.debug_mode and \
        #    self.game.actions_taken_this_turn >= C.MAX_PLAYER_ACTIONS:
        #     # ... (draw confirm button) ...


        def draw_debug_die_panel(self, screen, selected_face):
            """Draws the clickable die faces for debug mode in driving phase."""
            # --- Add print to confirm execution ---
            # print("Drawing debug die panel...")
            self.debug_die_rects.clear()
            x = C.DEBUG_DIE_AREA_X
            y = C.DEBUG_DIE_AREA_Y

            # Simple check for visibility
            if x > C.SCREEN_WIDTH or y > C.SCREEN_HEIGHT:
                print(f"Warning: Debug die panel position ({x},{y}) is off-screen.")
                return

            self.draw_text(screen, "DEBUG DIE SELECT:", x, y - C.UI_LINE_HEIGHT, size=18)
            y += 5 # Add small padding below title

            # --- Get the faces in the desired order (same logic as creation) ---
            unique_faces = set(C.DIE_FACES); ordered_unique_faces = [];
            if C.STOP_SYMBOL in unique_faces: ordered_unique_faces.append(C.STOP_SYMBOL)
            numbers = sorted([f for f in unique_faces if isinstance(f, int)]); ordered_unique_faces.extend(numbers)

            for face in ordered_unique_faces:
                face_surf = self.debug_die_surfaces.get(face)
                if face_surf: # Check if surface exists
                    rect = pygame.Rect(x, y, C.DEBUG_DIE_BUTTON_SIZE, C.DEBUG_DIE_BUTTON_SIZE)
                    self.debug_die_rects[face] = rect # Store rect by face value

                    # --- Add print before blitting ---
                    # print(f"  Attempting to draw die face {face} at {rect.topleft}, Surface: {face_surf}")
                    screen.blit(face_surf, rect.topleft)

                    # Optional highlight
                    # if selected_face == face: pygame.draw.rect(screen, C.COLOR_SELECTED, rect, 3)

                    x += C.DEBUG_DIE_BUTTON_SIZE + C.DEBUG_DIE_SPACING
                    # Basic wrapping if goes off edge (adjust condition as needed)
                    if x + C.DEBUG_DIE_BUTTON_SIZE > C.SCREEN_WIDTH - 20:
                        x = C.DEBUG_DIE_AREA_X
                        y += C.DEBUG_DIE_BUTTON_SIZE + C.DEBUG_DIE_SPACING
                else:
                    print(f"Warning: Surface for die face {face} not found.")

    def draw_debug_die_panel(self, screen, selected_face):
            """Draws the clickable die faces for debug mode in driving phase."""
            # --- Add print to confirm execution ---
            # print("Drawing debug die panel...")
            self.debug_die_rects.clear()
            x = C.DEBUG_DIE_AREA_X
            y = C.DEBUG_DIE_AREA_Y

            # Simple check for visibility
            if x > C.SCREEN_WIDTH or y > C.SCREEN_HEIGHT:
                print(f"Warning: Debug die panel position ({x},{y}) is off-screen.")
                return

            self.draw_text(screen, "DEBUG DIE SELECT:", x, y - C.UI_LINE_HEIGHT, size=18)
            y += 5 # Add small padding below title

            # --- Get the faces in the desired order (same logic as creation) ---
            unique_faces = set(C.DIE_FACES); ordered_unique_faces = [];
            if C.STOP_SYMBOL in unique_faces: ordered_unique_faces.append(C.STOP_SYMBOL)
            numbers = sorted([f for f in unique_faces if isinstance(f, int)]); ordered_unique_faces.extend(numbers)

            for face in ordered_unique_faces:
                face_surf = self.debug_die_surfaces.get(face)
                if face_surf: # Check if surface exists
                    rect = pygame.Rect(x, y, C.DEBUG_DIE_BUTTON_SIZE, C.DEBUG_DIE_BUTTON_SIZE)
                    self.debug_die_rects[face] = rect # Store rect by face value

                    # --- Add print before blitting ---
                    # print(f"  Attempting to draw die face {face} at {rect.topleft}, Surface: {face_surf}")
                    screen.blit(face_surf, rect.topleft)

                    # Optional highlight
                    # if selected_face == face: pygame.draw.rect(screen, C.COLOR_SELECTED, rect, 3)

                    x += C.DEBUG_DIE_BUTTON_SIZE + C.DEBUG_DIE_SPACING
                    # Basic wrapping if goes off edge (adjust condition as needed)
                    if x + C.DEBUG_DIE_BUTTON_SIZE > C.SCREEN_WIDTH - 20:
                        x = C.DEBUG_DIE_AREA_X
                        y += C.DEBUG_DIE_BUTTON_SIZE + C.DEBUG_DIE_SPACING
                else:
                    print(f"Warning: Surface for die face {face} not found.")

    def draw_debug_panel(self, screen, selected_debug_tile_type):
        """Draws the panel showing all 12 tile types for selection."""
        # Title is drawn in draw_ui now
        current_col = 0
        current_row = 0
        self.debug_tile_rects.clear() # Clear old rects

        for i, tile_type in enumerate(self.debug_tile_types):
            screen_x = C.DEBUG_PANEL_X + current_col * (C.DEBUG_TILE_SIZE + C.DEBUG_TILE_SPACING)
            screen_y = C.DEBUG_PANEL_Y + current_row * (C.DEBUG_TILE_SIZE + C.DEBUG_TILE_SPACING)
            rect = pygame.Rect(screen_x, screen_y, C.DEBUG_TILE_SIZE, C.DEBUG_TILE_SIZE)
            self.debug_tile_rects[i] = rect # Store rect by original index

            pygame.draw.rect(screen, C.COLOR_WHITE, rect)
            debug_surf = self.debug_tile_surfaces.get(tile_type.name)
            if debug_surf:
                 img_rect = debug_surf.get_rect(center=rect.center)
                 screen.blit(debug_surf, img_rect.topleft)
            pygame.draw.rect(screen, C.COLOR_BLACK, rect, 1)

            # Highlight if selected
            if selected_debug_tile_type == tile_type:
                 pygame.draw.rect(screen, C.COLOR_SELECTED, rect, 3)

            current_col += 1
            if current_col >= C.DEBUG_TILES_PER_ROW:
                current_col = 0
                current_row += 1

    # --- Keep draw_preview ---
    def draw_preview(self, screen, selected_tile, orientation): # Keep as is
         if not isinstance(self.current_state, LayingTrackState) or selected_tile is None: return
         mouse_pos = pygame.mouse.get_pos(); grid_col_rel = (mouse_pos[0] - C.BOARD_X_OFFSET) // self.TILE_SIZE; grid_row_rel = (mouse_pos[1] - C.BOARD_Y_OFFSET) // self.TILE_SIZE
         grid_col = grid_col_rel + C.PLAYABLE_COLS[0]; grid_row = grid_row_rel + C.PLAYABLE_ROWS[0]
         if self.game.board.is_playable_coordinate(grid_row, grid_col):
             screen_x = C.BOARD_X_OFFSET + grid_col_rel * self.TILE_SIZE; screen_y = C.BOARD_Y_OFFSET + grid_row_rel * self.TILE_SIZE; rect = pygame.Rect(screen_x, screen_y, self.TILE_SIZE, self.TILE_SIZE)
             tile_surf = self.tile_surfaces.get(selected_tile.name)
             if tile_surf:
                 rotated_surf = pygame.transform.rotate(tile_surf.copy(), -orientation); rotated_surf.set_alpha(128)
                 new_rect = rotated_surf.get_rect(center=rect.center); screen.blit(rotated_surf, new_rect.topleft)