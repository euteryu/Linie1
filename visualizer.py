# visualizer.py
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import filedialog

import pygame
import sys
import math
from typing import List, Dict, Tuple, Optional, Any
from game_states import GameState, LayingTrackState, DrivingState, GameOverState
import constants as C # Use alias
import copy
from collections import deque

# from game_logic import Game, PlacedTile, TileType, GamePhase, Direction, Player
from game_logic.game import Game # Import main Game class
from game_logic.player import Player # Import Player if needed directly
from game_logic.tile import PlacedTile, TileType # Import tile classes if needed
from game_logic.enums import GamePhase, PlayerState, Direction # Import enums

# Constants import remains the same
import constants as C

def create_tile_surface(tile_type: TileType, size: int) -> pygame.Surface:
    """Creates a Pygame Surface using lines and correctly positioned quadrant arcs."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))

    line_width = max(2, int(size * 0.1))
    track_color = C.COLOR_TRACK

    half_size_f = size / 2.0
    ptN = (int(half_size_f), 0); ptS = (int(half_size_f), size)
    ptE = (size, int(half_size_f)); ptW = (0, int(half_size_f))

    radius = size // 2
    rect_centered_TR = pygame.Rect(int(size/2.0), int(-size/2.0), size, size)
    rect_centered_TL = pygame.Rect(int(-size/2.0), int(-size/2.0), size, size)
    rect_centered_BR = pygame.Rect(int(size/2.0), int(size/2.0), size, size)
    rect_centered_BL = pygame.Rect(int(-size/2.0), int(size/2.0), size, size)

    angle_N = math.pi / 2; angle_W = math.pi; angle_S = 3 * math.pi / 2; angle_E = 0

    temp_size = int(size + line_width * 2.0)
    temp_surf = pygame.Surface((temp_size, temp_size), pygame.SRCALPHA)
    temp_surf.fill((0,0,0,0))
    temp_offset_x_f = float(line_width); temp_offset_y_f = float(line_width)
    ptN_temp = (int(size / 2.0 + temp_offset_x_f), int(0 + temp_offset_y_f)); ptS_temp = (int(size / 2.0 + temp_offset_x_f), int(size + temp_offset_y_f)); ptE_temp = (int(size + temp_offset_x_f), int(size / 2.0 + temp_offset_y_f)); ptW_temp = (int(0 + temp_offset_x_f), int(size / 2.0 + temp_offset_y_f))
    rect_centered_TR_temp = pygame.Rect(int(size/2.0 + temp_offset_x_f), int(-size/2.0 + temp_offset_y_f), size, size); rect_centered_TL_temp = pygame.Rect(int(-size/2.0 + temp_offset_x_f), int(-size/2.0 + temp_offset_y_f), size, size); rect_centered_BR_temp = pygame.Rect(int(size/2.0 + temp_offset_x_f), int(size/2.0 + temp_offset_y_f), size, size); rect_centered_BL_temp = pygame.Rect(int(-size/2.0 + temp_offset_x_f), int(size/2.0 + temp_offset_y_f), size, size)

    tile_name = tile_type.name

    # --- Draw based on Tile Type Name ---
    tile_name = tile_type.name

    if tile_name == "Straight": # N-S
        pygame.draw.line(temp_surf, track_color, ptN_temp, ptS_temp, line_width)
    elif tile_name == "Curve": # N-E
        pygame.draw.arc(temp_surf, track_color, rect_centered_TR_temp, angle_N, angle_E + 2*math.pi, line_width) # OK (pi/2 -> 2pi)
    elif tile_name == "StraightLeftCurve": # N-S, S-W
        pygame.draw.line(temp_surf, track_color, ptN_temp, ptS_temp, line_width)
        # S-W Curve: Centered BL. Start=S(3pi/2), Stop=W(pi+2pi=3pi)
        pygame.draw.arc(temp_surf, track_color, rect_centered_BL_temp, angle_S, angle_W + 2*math.pi, line_width) # << CORRECTED S-W
    elif tile_name == "StraightRightCurve": # N-S, S-E
        pygame.draw.line(temp_surf, track_color, ptN_temp, ptS_temp, line_width)
        pygame.draw.arc(temp_surf, track_color, rect_centered_BR_temp, angle_E, angle_S, line_width) # S-E (Fixed Previously: 0 -> 3pi/2)
    elif tile_name == "DoubleCurveY": # N-W, N-E
        # N-W Curve: Centered TL. Start=W(pi), Stop=N(pi/2+2pi=5pi/2)
        pygame.draw.arc(temp_surf, track_color, rect_centered_TL_temp, angle_W, angle_N + 2*math.pi, line_width) # << CORRECTED N-W
        pygame.draw.arc(temp_surf, track_color, rect_centered_TR_temp, angle_N, angle_E + 2*math.pi, line_width) # N-E
    elif tile_name == "DiagonalCurve": # S-W, N-E
        # S-W Curve: Centered BL. Start=S(3pi/2), Stop=W(pi+2pi=3pi)
        pygame.draw.arc(temp_surf, track_color, rect_centered_BL_temp, angle_S, angle_W + 2*math.pi, line_width) # << CORRECTED S-W
        pygame.draw.arc(temp_surf, track_color, rect_centered_TR_temp, angle_N, angle_E + 2*math.pi, line_width) # N-E
    elif tile_name == "Tree_JunctionTop": # E-W, W-N, N-E
        pygame.draw.line(temp_surf, track_color, ptW_temp, ptE_temp, line_width)
        # N-W Curve (W-N): Centered TL. Start=W(pi), Stop=N(pi/2+2pi=5pi/2)
        pygame.draw.arc(temp_surf, track_color, rect_centered_TL_temp, angle_W, angle_N + 2*math.pi, line_width) # << CORRECTED N-W
        pygame.draw.arc(temp_surf, track_color, rect_centered_TR_temp, angle_N, angle_E + 2*math.pi, line_width) # N-E
    elif tile_name == "Tree_JunctionRight": # E-W, N-E, S-E
        pygame.draw.line(temp_surf, track_color, ptW_temp, ptE_temp, line_width)
        pygame.draw.arc(temp_surf, track_color, rect_centered_TR_temp, angle_N, angle_E + 2*math.pi, line_width) # N-E
        pygame.draw.arc(temp_surf, track_color, rect_centered_BR_temp, angle_E, angle_S, line_width) # S-E (Fixed Previously)
    elif tile_name == "Tree_Roundabout": # W-N, N-E, E-S, S-W
        # N-W Curve: Centered TL. Start=W(pi), Stop=N(pi/2+2pi=5pi/2)
        pygame.draw.arc(temp_surf, track_color, rect_centered_TL_temp, angle_W, angle_N + 2*math.pi, line_width) # << CORRECTED N-W
        pygame.draw.arc(temp_surf, track_color, rect_centered_TR_temp, angle_N, angle_E + 2*math.pi, line_width) # N-E
        pygame.draw.arc(temp_surf, track_color, rect_centered_BR_temp, angle_E, angle_S, line_width) # S-E (Fixed Previously)
        # S-W Curve: Centered BL. Start=S(3pi/2), Stop=W(pi+2pi=3pi)
        pygame.draw.arc(temp_surf, track_color, rect_centered_BL_temp, angle_S, angle_W + 2*math.pi, line_width) # << CORRECTED S-W
    elif tile_name == "Tree_Crossroad": # N-S, E-W
        pygame.draw.line(temp_surf, track_color, ptN_temp, ptS_temp, line_width)
        pygame.draw.line(temp_surf, track_color, ptW_temp, ptE_temp, line_width)
    elif tile_name == "Tree_StraightDiagonal1": # N-S, S-W, N-E
        pygame.draw.line(temp_surf, track_color, ptN_temp, ptS_temp, line_width)
        # S-W Curve: Centered BL. Start=S(3pi/2), Stop=W(pi+2pi=3pi)
        pygame.draw.arc(temp_surf, track_color, rect_centered_BL_temp, angle_S, angle_W + 2*math.pi, line_width) # << CORRECTED S-W
        pygame.draw.arc(temp_surf, track_color, rect_centered_TR_temp, angle_N, angle_E + 2*math.pi, line_width) # N-E
    elif tile_name == "Tree_StraightDiagonal2": # N-S, N-W, S-E
        pygame.draw.line(temp_surf, track_color, ptN_temp, ptS_temp, line_width)
        # N-W Curve: Centered TL. Start=W(pi), Stop=N(pi/2+2pi=5pi/2)
        pygame.draw.arc(temp_surf, track_color, rect_centered_TL_temp, angle_W, angle_N + 2*math.pi, line_width) # << CORRECTED N-W
        pygame.draw.arc(temp_surf, track_color, rect_centered_BR_temp, angle_E, angle_S, line_width) # S-E (Fixed Previously)
    else:
        print(f"FATAL ERROR: Unknown tile type to draw: {tile_name}")

    # --- Blit the center part ---
    blit_rect_on_temp = pygame.Rect(int(temp_offset_x_f), int(temp_offset_y_f), size, size)
    surf.blit(temp_surf, (0, 0), blit_rect_on_temp)

    return surf

# --- Main Visualizer Class ---
class Linie1Visualizer:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
        pygame.display.set_caption("Linie 1"); self.clock = pygame.time.Clock()
        try: self.font = pygame.font.SysFont(None, 24)
        except pygame.error: self.font = pygame.font.Font(None, 24) # Fallback
        self.game = Game(num_players=2)
        self.TILE_SIZE = C.TILE_SIZE; self.HAND_TILE_SIZE = C.HAND_TILE_SIZE

        print("--visualizer.py : WELCOME TO LINIE 1--")

        # Debug Mode Attributes
        self.debug_mode = C.DEBUG_MODE
        # Store TileType objects directly for debug selection
        self.debug_tile_types: List[TileType] = list(self.game.tile_types.values())
        self.debug_tile_surfaces: Dict[str, pygame.Surface] = {
             name: create_tile_surface(ttype, C.DEBUG_TILE_SIZE)
             for name, ttype in self.game.tile_types.items()
        }
        # Store rects for clicking, calculated during draw
        self.debug_tile_rects: Dict[int, pygame.Rect] = {}
        self.debug_toggle_button_rect = pygame.Rect(
            C.DEBUG_BUTTON_X, C.DEBUG_BUTTON_Y,
            C.DEBUG_BUTTON_WIDTH, C.DEBUG_BUTTON_HEIGHT
        )
        # --- Add storage for original hand during debug ---
        self.original_player_hand: Optional[List[TileType]] = None

        # Main Surfaces
        print("")
        print("Generating main tile surfaces...");
        self.tile_surfaces = { name: create_tile_surface(ttype, self.TILE_SIZE) for name, ttype in self.game.tile_types.items()}
        self.hand_tile_surfaces = { name: create_tile_surface(ttype, self.HAND_TILE_SIZE) for name, ttype in self.game.tile_types.items()}
        print("Tile surfaces generated.")
        print("")
        self.current_state: GameState = LayingTrackState(self)

        self.clock = pygame.time.Clock()
        # Initialize Tkinter root ONLY for file dialogs
        try:
            self.tk_root = tk.Tk()
            self.tk_root.withdraw() # Hide the main tkinter window
        except tk.TclError:
             print("Warning: Tkinter not available or display not found. File dialogs disabled.")
             self.tk_root = None

        # UI Button Rects (adjust positions as needed)
        button_width = 100
        button_height = 30
        button_y = C.UI_PANEL_Y + C.UI_PANEL_HEIGHT - button_height - 15
        self.save_button_rect = pygame.Rect(C.UI_PANEL_X + 15, button_y, button_width, button_height)
        self.load_button_rect = pygame.Rect(C.UI_PANEL_X + 15 + button_width + 10, button_y, button_width, button_height)
        self.debug_toggle_button_rect = pygame.Rect( C.DEBUG_BUTTON_X, C.DEBUG_BUTTON_Y, C.DEBUG_BUTTON_WIDTH, C.DEBUG_BUTTON_HEIGHT )

        self.debug_die_surfaces: Dict[Any, pygame.Surface] = self._create_debug_die_surfaces()
        # --- Add print to verify ---
        print(f"Created debug die surfaces for keys: {list(self.debug_die_surfaces.keys())}")
        self.debug_die_rects: Dict[Any, pygame.Rect] = {}

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

    def draw_debug_die_panel(self, screen, selected_face):
        """Draws the clickable die faces for debug mode in driving phase."""
        self.debug_die_rects.clear()
        x = C.DEBUG_DIE_AREA_X
        y = C.DEBUG_DIE_AREA_Y

        self.draw_text(screen, "DEBUG DIE SELECT:", x, y - C.UI_LINE_HEIGHT, size=18)

        # --- Get the faces in the desired order ---
        unique_faces = set(C.DIE_FACES)
        ordered_unique_faces = []
        if C.STOP_SYMBOL in unique_faces: ordered_unique_faces.append(C.STOP_SYMBOL)
        numbers = sorted([f for f in unique_faces if isinstance(f, int)])
        ordered_unique_faces.extend(numbers)
        # --- End get faces ---

        for face in ordered_unique_faces: # Iterate through the ordered list
            face_surf = self.debug_die_surfaces.get(face)
            if face_surf:
                rect = pygame.Rect(x, y, C.DEBUG_DIE_BUTTON_SIZE, C.DEBUG_DIE_BUTTON_SIZE)
                self.debug_die_rects[face] = rect # Store rect by face value
                screen.blit(face_surf, rect.topleft)

                # Optional highlight (can keep or remove)
                # if selected_face == face:
                #    pygame.draw.rect(screen, C.COLOR_SELECTED, rect, 3)

                x += C.DEBUG_DIE_BUTTON_SIZE + C.DEBUG_DIE_SPACING
                # Add logic here for wrapping if needed

    # --- run() method ---
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                # --- Global Debug Toggle Check ---
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1 and self.debug_toggle_button_rect.collidepoint(event.pos):
                        self.debug_mode = not self.debug_mode
                        # Reset selection when toggling mode
                        if isinstance(self.current_state, LayingTrackState):
                            self.current_state.selected_tile_index = None
                            self.current_state.debug_selected_tile_type = None
                            self.current_state.message = f"Debug Mode: {'ON' if self.debug_mode else 'OFF'}"
                        continue # Consume this event

                # Delegate other events
                self.current_state.handle_event(event)

            self.current_state.update(dt)
            self.update_current_state_for_player()

            # Drawing
            self.screen.fill(C.COLOR_UI_BG)
            self.current_state.draw(self.screen)
            pygame.display.flip()

        pygame.quit()
        sys.exit()

    def update_current_state_for_player(self):
        """Sets the self.current_state object based on the ACTIVE player's state."""
        try:
            active_player = self.game.get_active_player()
            player_state = active_player.player_state
            game_phase = self.game.game_phase # Keep track of overall phase too

            # Determine the correct state object type
            target_state_class = None
            if game_phase == GamePhase.GAME_OVER:
                target_state_class = GameOverState
            elif player_state == PlayerState.DRIVING:
                target_state_class = DrivingState
            elif player_state == PlayerState.LAYING_TRACK:
                target_state_class = LayingTrackState
            # Add FINISHED state if needed later
            else:
                # Fallback or error state?
                print(f"Warning: Unknown player state {player_state} for P{active_player.player_id}. Defaulting to LayingTrackState.")
                target_state_class = LayingTrackState # Safer default

            # Switch state object ONLY if the class type is different
            if not isinstance(self.current_state, target_state_class):
                print(f"Visualizer State Changing: {type(self.current_state).__name__} -> {target_state_class.__name__} for Player {active_player.player_id}")
                self.current_state = target_state_class(self)
                # Optional: Call an init method on the new state if needed
                # if hasattr(self.current_state, 'on_enter'): self.current_state.on_enter()

        except (IndexError, AttributeError):
             print("Error: Could not get active player to update visualizer state.")
             # Perhaps default to a safe state or handle error
             if not isinstance(self.current_state, LayingTrackState): # Avoid infinite loops if LayingTrackState fails
                  self.current_state = LayingTrackState(self)

    def draw_text(self, surface, text, x, y, color=C.COLOR_UI_TEXT, size=24): # Keep as is
        try: font_to_use = pygame.font.SysFont(None, size) if size != 24 else self.font; text_surface = font_to_use.render(text, True, color); surface.blit(text_surface, (x, y))
        except Exception as e: print(f"Error rendering text '{text}': {e}")

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

    # --- draw_hand() needs modification for debug mode ---
    def draw_hand(self, screen, player: Player):
        """Draws the player's hand tiles OR the debug panel title."""
        # Only draw hand title if NOT in debug mode
        if not self.debug_mode:
            self.draw_text(screen, f"Player {player.player_id}'s Hand:", C.HAND_AREA_X, C.UI_HAND_TITLE_Y)

        hand_rects = {}
        # Only draw hand tiles if NOT in debug mode
        if not self.debug_mode:
            for i, tile_type in enumerate(player.hand):
                if i >= C.HAND_TILE_COUNT:
                    break
                screen_x = C.HAND_AREA_X
                screen_y = C.HAND_AREA_Y + i * (self.HAND_TILE_SIZE + C.HAND_SPACING)
                rect = pygame.Rect(screen_x, screen_y, self.HAND_TILE_SIZE, self.HAND_TILE_SIZE)
                hand_rects[i] = rect

                pygame.draw.rect(screen, C.COLOR_WHITE, rect)
                hand_surf = self.hand_tile_surfaces.get(tile_type.name)
                if hand_surf:
                    img_rect = hand_surf.get_rect(center=rect.center)
                    screen.blit(hand_surf, img_rect.topleft)
                pygame.draw.rect(screen, C.COLOR_BLACK, rect, 1)

                # Highlight selected hand tile
                if isinstance(self.current_state, LayingTrackState) and self.current_state.selected_tile_index == i:
                    pygame.draw.rect(screen, C.COLOR_SELECTED, rect, 3)
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