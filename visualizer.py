# visualizer.py
# -*- coding: utf-8 -*-
import pygame
import sys
import math
import tkinter as tk
from tkinter import filedialog
from typing import List, Dict, Tuple, Optional, Any
from collections import deque
import copy

from sound_manager import SoundManager # Import the new class

# --- Game Logic Imports ---
from game_logic.game import Game
from game_logic.tile import PlacedTile, TileType
from game_logic.enums import GamePhase, PlayerState, Direction
from game_logic.player import Player, AIPlayer

# --- State Machine ---
from game_states import (GameState, LayingTrackState, DrivingState,
                         GameOverState)

# --- Constants ---
import constants as C


# === Helper Function for Drawing Tiles ===

def create_tile_surface(tile_type: TileType, size: int) -> pygame.Surface:
    """ Creates a Pygame Surface using lines and arcs for a tile type. """
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill(C.COLOR_TRANSPARENT)
    line_width = max(2, int(size * C.TRACK_WIDTH_RATIO))
    track_color = C.COLOR_TRACK

    half_size = size // 2
    ptN, ptS, ptE, ptW = (half_size, 0), (half_size, size), (size, half_size), (0, half_size)
    rect_TR = pygame.Rect(half_size, -half_size, size, size)
    rect_TL = pygame.Rect(-half_size, -half_size, size, size)
    rect_BR = pygame.Rect(half_size, half_size, size, size)
    rect_BL = pygame.Rect(-half_size, half_size, size, size)

    angle_N, angle_E, angle_S, angle_W = math.radians(90), math.radians(0), math.radians(270), math.radians(180)
    tile_name = tile_type.name

    if tile_name == "Straight": pygame.draw.line(surf, track_color, ptN, ptS, line_width)
    elif tile_name == "Curve": pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E, line_width)
    elif tile_name == "StraightLeftCurve":
        pygame.draw.line(surf, track_color, ptN, ptS, line_width)
        pygame.draw.arc(surf, track_color, rect_BL, angle_S, angle_W, line_width)
    elif tile_name == "StraightRightCurve":
        pygame.draw.line(surf, track_color, ptN, ptS, line_width)
        pygame.draw.arc(surf, track_color, rect_BR, angle_E, angle_S, line_width)
    elif tile_name == "DoubleCurveY":
        pygame.draw.arc(surf, track_color, rect_TL, angle_W, angle_N, line_width)
        pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E, line_width)
    elif tile_name == "DiagonalCurve":
        pygame.draw.arc(surf, track_color, rect_BL, angle_S, angle_W, line_width)
        pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E, line_width)
    elif tile_name == "Tree_JunctionTop":
        pygame.draw.line(surf, track_color, ptW, ptE, line_width)
        pygame.draw.arc(surf, track_color, rect_TL, angle_W, angle_N, line_width)
        pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E, line_width)
    elif tile_name == "Tree_JunctionRight":
        pygame.draw.line(surf, track_color, ptW, ptE, line_width)
        pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E, line_width)
        pygame.draw.arc(surf, track_color, rect_BR, angle_E, angle_S, line_width)
    elif tile_name == "Tree_Roundabout":
        pygame.draw.arc(surf, track_color, rect_TL, angle_W, angle_N, line_width)
        pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E, line_width)
        pygame.draw.arc(surf, track_color, rect_BR, angle_E, angle_S, line_width)
        pygame.draw.arc(surf, track_color, rect_BL, angle_S, angle_W, line_width)
    elif tile_name == "Tree_Crossroad":
        pygame.draw.line(surf, track_color, ptN, ptS, line_width)
        pygame.draw.line(surf, track_color, ptW, ptE, line_width)
    elif tile_name == "Tree_StraightDiagonal1":
        pygame.draw.line(surf, track_color, ptN, ptS, line_width)
        pygame.draw.arc(surf, track_color, rect_BL, angle_S, angle_W, line_width)
        pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E, line_width)
    elif tile_name == "Tree_StraightDiagonal2":
        pygame.draw.line(surf, track_color, ptN, ptS, line_width)
        pygame.draw.arc(surf, track_color, rect_TL, angle_W, angle_N, line_width)
        pygame.draw.arc(surf, track_color, rect_BR, angle_E, angle_S, line_width)
    else:
        print(f"Warning: Unknown tile type to draw: {tile_name}")
        pygame.draw.rect(surf, C.COLOR_GRID, surf.get_rect(), 1)
        pygame.draw.line(surf, C.COLOR_STOP, (0, 0), (size, size), 1)
        pygame.draw.line(surf, C.COLOR_STOP, (0, size), (size, 0), 1)

    return surf


# === Main Visualizer Class ===

class Linie1Visualizer:
    def __init__(self, player_types: List[str], difficulty: str):
        """
        Initializes the visualizer and the game engine.
        :param player_types: A list defining players, e.g., ['human', 'ai', 'ai']
        :param difficulty: The game's difficulty setting, e.g., 'king' or 'normal'
        """
        self.sounds = SoundManager()
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
        pygame.display.set_caption("Linie 1")
        self.clock = pygame.time.Clock()

        try:
            self.font = pygame.font.SysFont(None, C.DEFAULT_FONT_SIZE)
        except Exception as e:
            print(f"SysFont error: {e}. Using default font.")
            self.font = pygame.font.Font(None, C.DEFAULT_FONT_SIZE)

        try:
            self.tk_root = tk.Tk()
            self.tk_root.withdraw()
        except Exception as e:
            print(f"Warning: Tkinter init failed ({e}). File dialogs disabled.")
            self.tk_root = None

        try:
            self.game = Game(player_types=player_types, difficulty=difficulty)
            # Give the game a reference back to the visualizer for forced redraws.
            self.game.visualizer = self
        except Exception as e:
            print(f"FATAL: Game initialization failed: {e}")
            import traceback
            traceback.print_exc()
            pygame.quit()
            sys.exit()

        # --- The rest of the __init__ method is unchanged ---
        self.TILE_SIZE = C.TILE_SIZE
        self.HAND_TILE_SIZE = C.HAND_TILE_SIZE
        self.debug_mode = C.DEBUG_MODE
        self.debug_tile_types: List[TileType] = list(self.game.tile_types.values())
        self.debug_tile_surfaces = self._create_debug_tile_surfaces()
        self.debug_die_surfaces = self._create_debug_die_surfaces()
        self.debug_tile_rects: Dict[int, pygame.Rect] = {}
        self.debug_die_rects: Dict[Any, pygame.Rect] = {}

        print("Generating main tile surfaces...")
        self.tile_surfaces = {name: create_tile_surface(ttype, self.TILE_SIZE) for name, ttype in self.game.tile_types.items()}
        self.hand_tile_surfaces = {name: create_tile_surface(ttype, self.HAND_TILE_SIZE) for name, ttype in self.game.tile_types.items()}
        print("Tile surfaces generated.")

        btn_w, btn_h, btn_s = C.BUTTON_WIDTH, C.BUTTON_HEIGHT, C.BUTTON_SPACING
        btn_y = C.UI_PANEL_Y + C.UI_PANEL_HEIGHT - btn_h - C.BUTTON_MARGIN_Y
        btn_x = C.UI_PANEL_X + C.BUTTON_MARGIN_X
        self.save_button_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        btn_x += btn_w + btn_s
        self.load_button_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        btn_x += btn_w + btn_s
        self.undo_button_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        btn_x += btn_w + btn_s
        self.redo_button_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        self.debug_toggle_button_rect = pygame.Rect(C.DEBUG_BUTTON_X, C.DEBUG_BUTTON_Y, C.DEBUG_BUTTON_WIDTH, C.DEBUG_BUTTON_HEIGHT)

        self.current_state: GameState = LayingTrackState(self)
        self.update_current_state_for_player()

        self.sounds.load_sounds()
        self.sounds.play_music('main_theme')

        self.show_ai_heatmap = False
        self.heatmap_data: Set[Tuple[int, int]] = set() # To store squares to highlight
        # --- NEW Heatmap Toggle Button ---
        btn_w, btn_h, btn_s = C.BUTTON_WIDTH, C.BUTTON_HEIGHT, C.BUTTON_SPACING
        # Place it below the other buttons
        heatmap_btn_y = self.redo_button_rect.y - btn_h - btn_s 
        heatmap_btn_x = self.save_button_rect.x
        self.heatmap_button_rect = pygame.Rect(heatmap_btn_x, heatmap_btn_y, btn_w * 2 + btn_s, btn_h)

    def draw_ai_heatmap(self, screen):
        """Draws a visual highlight over the squares the AI is considering."""
        if not self.show_ai_heatmap or not self.heatmap_data:
            return

        highlight_color = (0, 255, 255, 90) # Cyan, semi-transparent
        border_color = (0, 200, 200)

        for r, c in self.heatmap_data:
            if not self.game.board.is_valid_coordinate(r, c): continue
            
            screen_x = C.BOARD_X_OFFSET + (c - C.PLAYABLE_COLS[0]) * self.TILE_SIZE
            screen_y = C.BOARD_Y_OFFSET + (r - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE
            rect = pygame.Rect(screen_x, screen_y, self.TILE_SIZE, self.TILE_SIZE)
            
            temp_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
            temp_surf.fill(highlight_color)
            screen.blit(temp_surf, rect.topleft)
            pygame.draw.rect(screen, border_color, rect, 2)


    def _create_debug_tile_surfaces(self) -> Dict[str, pygame.Surface]:
        return {ttype.name: create_tile_surface(ttype, C.DEBUG_TILE_SIZE) for ttype in self.debug_tile_types}

    def _create_debug_die_surfaces(self) -> Dict[Any, pygame.Surface]:
        unique_faces = set(C.DIE_FACES)
        ordered_unique_faces = []
        if C.STOP_SYMBOL in unique_faces: ordered_unique_faces.append(C.STOP_SYMBOL)
        numbers = sorted([f for f in unique_faces if isinstance(f, int)])
        ordered_unique_faces.extend(numbers)
        surfaces = {}
        size = C.DEBUG_DIE_BUTTON_SIZE
        font_size = int(size * 0.7)
        try: font = pygame.font.SysFont(None, font_size)
        except: font = pygame.font.Font(None, font_size)
        for face in ordered_unique_faces:
             surf = pygame.Surface((size, size))
             surf.fill(C.COLOR_WHITE)
             pygame.draw.rect(surf, C.COLOR_BLACK, surf.get_rect(), 1)
             try:
                 text_surf = font.render(str(face), True, C.COLOR_BLACK)
                 text_rect = text_surf.get_rect(center=(size // 2, size // 2))
                 surf.blit(text_surf, text_rect)
                 surfaces[face] = surf
             except Exception as e:
                 print(f"Error rendering/blitting text for die face {face}: {e}")
        return surfaces

    def run(self):
        """ Main game loop. """
        running = True
        
        if isinstance(self.game.get_active_player(), AIPlayer):
             pygame.event.post(pygame.event.Event(C.START_NEXT_TURN_EVENT))
        
        while running:
            dt = self.clock.tick(C.FPS) / 1000.0
            events = pygame.event.get()

            

            self.update_current_state_for_player()

            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                    break

                # --- THIS IS THE FIX ---
                # Handle our custom game flow event
                if event.type == C.START_NEXT_TURN_EVENT:
                    active_player = self.game.get_active_player()
                    # The turn handler now needs access to the visualizer to force redraws
                    active_player.handle_turn_logic(self.game, self, self.sounds)
                    continue
                # --- END OF FIX ---

                if self.current_state:
                     self.current_state.handle_event(event)

            if not running: break

            # Main drawing loop - this still runs every frame for smooth animation and human input
            self.screen.fill(C.COLOR_UI_BG)
            if self.current_state:
                self.current_state.draw(self.screen)
                self.draw_ai_heatmap(self.screen)
            else:
                 self.draw_text(self.screen, "Error: Invalid State", 10, 10, C.COLOR_STOP)
            pygame.display.flip()

        pygame.quit()
        if self.tk_root: self.tk_root.destroy()
        sys.exit()

    def update_current_state_for_player(self):
        try:
            active_player = self.game.get_active_player()
            player_state = active_player.player_state
            game_phase = self.game.game_phase
            target_state_class = None
            if game_phase == GamePhase.GAME_OVER: target_state_class = GameOverState
            elif player_state == PlayerState.DRIVING: target_state_class = DrivingState
            else: target_state_class = LayingTrackState
            if not isinstance(self.current_state, target_state_class):
                print(f"State Change: -> {target_state_class.__name__}")
                self.current_state = target_state_class(self)
        except (IndexError, AttributeError) as e:
            print(f"Error updating state: {e}")

    def draw_text(self, surface, text, x, y, color=C.COLOR_UI_TEXT, size=C.DEFAULT_FONT_SIZE):
        try:
            font_to_use = self.font if size == C.DEFAULT_FONT_SIZE else pygame.font.SysFont(None, size)
            text_surface = font_to_use.render(text, True, color)
            surface.blit(text_surface, (x, y))
        except Exception:
            try:
                font_to_use = pygame.font.Font(None, size)
                text_surface = font_to_use.render(text, True, color)
                surface.blit(text_surface, (x, y))
            except Exception as e2:
                 print(f"Error rendering text '{text}': {e2}")

    def draw_board(self, screen):
        for r in range(C.GRID_ROWS):
            for c in range(C.GRID_COLS):
                screen_x = C.BOARD_X_OFFSET + (c - C.PLAYABLE_COLS[0]) * self.TILE_SIZE
                screen_y = C.BOARD_Y_OFFSET + (r - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE
                rect = pygame.Rect(screen_x, screen_y, self.TILE_SIZE, self.TILE_SIZE)
                placed_tile = self.game.board.get_tile(r, c)
                is_playable = self.game.board.is_playable_coordinate(r, c)
                is_terminal = placed_tile is not None and placed_tile.is_terminal
                bg_color = C.COLOR_TERMINAL_BG if is_terminal else C.COLOR_BOARD_BG if is_playable else C.COLOR_GRID
                pygame.draw.rect(screen, bg_color, rect)
                pygame.draw.rect(screen, C.COLOR_GRID, rect, 1)

                if placed_tile:
                    tile_surf = self.tile_surfaces.get(placed_tile.tile_type.name)
                    if tile_surf:
                        rotated_surf = pygame.transform.rotate(tile_surf, -placed_tile.orientation)
                        screen.blit(rotated_surf, rotated_surf.get_rect(center=rect.center))

                building_id = self.game.board.get_building_at(r, c)
                if building_id and is_playable:
                    pygame.draw.rect(screen, C.COLOR_BUILDING_BG, rect)
                    try: b_font = pygame.font.SysFont(None, int(self.TILE_SIZE * 0.7))
                    except: b_font = pygame.font.Font(None, int(self.TILE_SIZE * 0.7))
                    b_surf = b_font.render(building_id, True, C.COLOR_BUILDING_FG)
                    screen.blit(b_surf, b_surf.get_rect(center=rect.center))
                    pygame.draw.rect(screen, C.COLOR_GRID, rect, 1)

                if placed_tile and placed_tile.has_stop_sign and is_playable:
                    stop_radius = self.TILE_SIZE // 4
                    stop_surf = pygame.Surface((stop_radius * 2, stop_radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(stop_surf, C.COLOR_STOP + (128,), (stop_radius, stop_radius), stop_radius)
                    pygame.draw.circle(stop_surf, C.COLOR_BLACK + (128,), (stop_radius, stop_radius), stop_radius, 1)
                    screen.blit(stop_surf, stop_surf.get_rect(center=rect.center))

        terminal_font = pygame.font.SysFont(None, int(self.TILE_SIZE * 0.5))
        for line_num, entrances in C.TERMINAL_DATA.items():
             try:
                 for entrance_pair in entrances:
                     cell1_coord, cell2_coord = entrance_pair[0][0], entrance_pair[1][0]
                     rect1_x = C.BOARD_X_OFFSET + (cell1_coord[1] - C.PLAYABLE_COLS[0]) * self.TILE_SIZE
                     rect1_y = C.BOARD_Y_OFFSET + (cell1_coord[0] - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE
                     rect2_x = C.BOARD_X_OFFSET + (cell2_coord[1] - C.PLAYABLE_COLS[0]) * self.TILE_SIZE
                     rect2_y = C.BOARD_Y_OFFSET + (cell2_coord[0] - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE
                     center_x = (rect1_x + rect2_x + self.TILE_SIZE) // 2
                     center_y = (rect1_y + rect2_y + self.TILE_SIZE) // 2
                     term_surf = terminal_font.render(str(line_num), True, C.COLOR_TERMINAL_TEXT)
                     term_rect = term_surf.get_rect(center=(center_x, center_y))
                     bg_rect = term_rect.inflate(6, 4)
                     pygame.draw.rect(screen, C.COLOR_BLACK, bg_rect, border_radius=3)
                     screen.blit(term_surf, term_rect)
             except (IndexError, TypeError, ValueError) as e:
                  print(f"Error processing TERMINAL_DATA for Line {line_num}: {e}")

        for player in self.game.players:
            if player.player_state == PlayerState.DRIVING and player.streetcar_position:
                 r, c = player.streetcar_position
                 if self.game.board.is_valid_coordinate(r, c):
                     screen_x = C.BOARD_X_OFFSET + (c - C.PLAYABLE_COLS[0]) * self.TILE_SIZE + C.TILE_SIZE // 2
                     screen_y = C.BOARD_Y_OFFSET + (r - C.PLAYABLE_ROWS[0]) * C.TILE_SIZE + C.TILE_SIZE // 2
                     tram_radius = C.TILE_SIZE // 3
                     p_color = C.PLAYER_COLORS[player.player_id % len(C.PLAYER_COLORS)]
                     pygame.draw.circle(screen, p_color, (screen_x, screen_y), tram_radius)
                     pygame.draw.circle(screen, C.COLOR_BLACK, (screen_x, screen_y), tram_radius, 1)
                     try: id_font = pygame.font.SysFont(None, int(tram_radius * 1.5))
                     except: id_font = pygame.font.Font(None, int(tram_radius * 1.5))
                     id_surf = id_font.render(str(player.player_id), True, C.COLOR_WHITE)
                     screen.blit(id_surf, id_surf.get_rect(center=(screen_x, screen_y)))

    def draw_staged_moves(self, screen, staged_moves: List[Dict]):
        """Renders translucent previews of staged moves on the board with validity indicators."""
        for move in staged_moves:
            r, c = move['coord']
            screen_x = C.BOARD_X_OFFSET + (c - C.PLAYABLE_COLS[0]) * self.TILE_SIZE
            screen_y = C.BOARD_Y_OFFSET + (r - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE
            rect = pygame.Rect(screen_x, screen_y, self.TILE_SIZE, self.TILE_SIZE)

            tile_surf = self.tile_surfaces.get(move['tile_type'].name)
            if tile_surf:
                rotated_surf = pygame.transform.rotate(tile_surf.copy(), -move['orientation'])
                rotated_surf.set_alpha(150)
                screen.blit(rotated_surf, rotated_surf.get_rect(center=rect.center))

            highlight_color = (0, 255, 0, 100) if move['is_valid'] else (255, 0, 0, 100)
            highlight_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
            highlight_surface.fill(highlight_color)
            screen.blit(highlight_surface, rect.topleft)

    def draw_live_preview(self, screen, move_in_progress: Dict):
        """Draws the tile being actively configured before it's staged."""
        if not move_in_progress or 'tile_type' not in move_in_progress:
            return
        
        r, c = move_in_progress['coord']
        tile_type = move_in_progress['tile_type']
        orientation = move_in_progress.get('orientation', 0)
        is_valid = move_in_progress.get('is_valid', False)

        screen_x = C.BOARD_X_OFFSET + (c - C.PLAYABLE_COLS[0]) * self.TILE_SIZE
        screen_y = C.BOARD_Y_OFFSET + (r - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE
        rect = pygame.Rect(screen_x, screen_y, self.TILE_SIZE, self.TILE_SIZE)
        
        # Draw the tile preview
        tile_surf = self.tile_surfaces.get(tile_type.name)
        if tile_surf:
            rotated_surf = pygame.transform.rotate(tile_surf.copy(), -orientation)
            rotated_surf.set_alpha(150) # Translucent
            screen.blit(rotated_surf, rotated_surf.get_rect(center=rect.center))
        
        # Draw the red/green validity indicator
        highlight_color = (0, 255, 0, 100) if is_valid else (255, 0, 0, 100)
        highlight_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        highlight_surface.fill(highlight_color)
        screen.blit(highlight_surface, rect.topleft)

    def draw_hand(self, screen, player: Player, staged_moves: List[Dict], selected_hand_index: Optional[int]):
        """Draws the player's hand, highlighting staged AND currently selected tiles."""
        hand_rects = {}
        staged_hand_indices = {move['hand_index'] for move in staged_moves} # Use a set for faster lookups
        
        y_pos = C.HAND_AREA_Y
        for i, tile_type in enumerate(player.hand):
            if i >= C.HAND_TILE_LIMIT: break
            rect = pygame.Rect(C.HAND_AREA_X, y_pos, self.HAND_TILE_SIZE, self.HAND_TILE_SIZE)
            hand_rects[i] = rect

            pygame.draw.rect(screen, C.COLOR_WHITE, rect)
            hand_surf = self.hand_tile_surfaces.get(tile_type.name)
            if hand_surf:
                screen.blit(hand_surf, rect.topleft)
            pygame.draw.rect(screen, C.COLOR_BLACK, rect, 1)

            # Highlight if the tile is either staged or currently being selected
            if i in staged_hand_indices:
                 # A more subtle color for already-staged tiles
                 pygame.draw.rect(screen, (100, 100, 100), rect, 3) 
            elif i == selected_hand_index:
                 # The bright selection color for the tile being actively considered
                 pygame.draw.rect(screen, C.COLOR_SELECTED, rect, 3)

            y_pos += self.HAND_TILE_SIZE + C.HAND_SPACING
        return hand_rects

    def draw_ui(self, screen, message: str, instructions: str = ""):
        """Draws all User Interface elements, adapting to the current game state and debug mode."""
        try:
            player = self.game.get_active_player()
            player_id, player_state_name = player.player_id, player.player_state.name
            player_line_card, player_route_card = player.line_card, player.route_card
        except (IndexError, AttributeError):
            player_id, player_state_name, player_line_card, player_route_card = "?", "Unknown", None, None

        # --- Draw Top Info Panel ---
        turn_text = f"Turn {self.game.current_turn} - Player {player_id} ({player_state_name})"
        self.draw_text(screen, turn_text, C.UI_TEXT_X, C.UI_TURN_INFO_Y)
        action_text = f"Actions: {self.game.actions_taken_this_turn}/{C.MAX_PLAYER_ACTIONS}"
        try:
            font = self.font or pygame.font.Font(None, 24)
            action_surf = font.render(action_text, True, C.COLOR_UI_TEXT)
            action_x = C.UI_PANEL_X + C.UI_PANEL_WIDTH - action_surf.get_width() - 15
            screen.blit(action_surf, (action_x, C.UI_TURN_INFO_Y))
        except Exception as e: print(f"Error rendering action text: {e}")

        line_info, stops_info = "Line: ?", "Stops: ?"
        if player_line_card:
            line_info = f"Line {player_line_card.line_number}"
        if player_route_card: stops_info = f"Stops: {' -> '.join(player_route_card.stops)}"
        self.draw_text(screen, line_info, C.UI_TEXT_X, C.UI_ROUTE_INFO_Y)
        self.draw_text(screen, stops_info, C.UI_TEXT_X, C.UI_ROUTE_INFO_Y + C.UI_LINE_HEIGHT)

        # --- Draw Middle Section Title ---
        if isinstance(self.current_state, LayingTrackState):
            title_text = "DEBUG TILE PALETTE" if self.debug_mode else f"Player {player_id}'s Hand:" if player_id != "?" else ""
            if title_text: self.draw_text(screen, title_text, C.HAND_AREA_X, C.UI_HAND_TITLE_Y)

        if self.debug_mode and isinstance(self.current_state, DrivingState):
            self.draw_debug_die_panel(screen, self.current_state.last_roll)

        # --- Draw Lower Section (Message and Instructions) ---
        lower_ui_start_y = C.UI_MESSAGE_Y
        if isinstance(self.current_state, LayingTrackState):
            # Position below hand or debug panel
            if self.debug_mode:
                num_rows = (len(self.debug_tile_types) + C.DEBUG_TILES_PER_ROW - 1) // C.DEBUG_TILES_PER_ROW
                lower_ui_start_y = C.DEBUG_PANEL_Y + num_rows * (C.DEBUG_TILE_SIZE + C.DEBUG_TILE_SPACING) + 10
            else:
                lower_ui_start_y = C.UI_SELECTED_TILE_Y # Default position below hand
        elif isinstance(self.current_state, DrivingState):
            if self.debug_mode:
                lower_ui_start_y = C.DEBUG_DIE_AREA_Y + C.DEBUG_DIE_BUTTON_SIZE + C.DEBUG_DIE_SPACING + 10

        msg_y = lower_ui_start_y
        instr_y = msg_y + C.UI_LINE_HEIGHT

        self.draw_text(screen, f"Msg: {message}", C.UI_TEXT_X, msg_y)

        # Use the passed-in instructions text
        final_instr = instructions
        if not final_instr: # Fallback for other game states
            if isinstance(self.current_state, DrivingState): final_instr = "[SPACE] Roll | [Click Die]"
            elif isinstance(self.current_state, GameOverState): final_instr = "Game Over!"
        
        if not isinstance(self.current_state, GameOverState):
            final_instr += " | [Btn] Debug"
        
        self.draw_text(screen, final_instr, C.UI_TEXT_X, instr_y, size=18)

        # --- Draw Buttons ---
        # (This section is unchanged and correct)
        btn_text_color, btn_font_size = C.COLOR_UI_BUTTON_TEXT, 18
        for rect, text in [(self.save_button_rect, "Save Game"), (self.load_button_rect, "Load Game")]:
            pygame.draw.rect(screen, C.COLOR_UI_BUTTON_BG, rect)
            pygame.draw.rect(screen, C.COLOR_BLACK, rect, 1)
            self.draw_text(screen, text, rect.x + 10, rect.y + 7, btn_text_color, size=btn_font_size)
        
        undo_color = C.COLOR_UI_BUTTON_TEXT if self.game.command_history.can_undo() else C.COLOR_GRID
        pygame.draw.rect(screen, C.COLOR_UI_BUTTON_BG, self.undo_button_rect)
        pygame.draw.rect(screen, C.COLOR_BLACK, self.undo_button_rect, 1)
        self.draw_text(screen, "Undo(Z)", self.undo_button_rect.x + 10, self.undo_button_rect.y + 7, undo_color, size=btn_font_size)
        
        redo_color = C.COLOR_UI_BUTTON_TEXT if self.game.command_history.can_redo() else C.COLOR_GRID
        pygame.draw.rect(screen, C.COLOR_UI_BUTTON_BG, self.redo_button_rect)
        pygame.draw.rect(screen, C.COLOR_BLACK, self.redo_button_rect, 1)
        self.draw_text(screen, "Redo(Y)", self.redo_button_rect.x + 10, self.redo_button_rect.y + 7, redo_color, size=btn_font_size)


        heatmap_btn_bg = C.COLOR_HIGHLIGHT if self.show_ai_heatmap else C.COLOR_UI_BUTTON_BG
        pygame.draw.rect(screen, heatmap_btn_bg, self.heatmap_button_rect)
        pygame.draw.rect(screen, C.COLOR_BLACK, self.heatmap_button_rect, 1)
        
        heatmap_btn_text = "Heatmap: ON" if self.show_ai_heatmap else "Heatmap: OFF"
        try:
             btn_font = pygame.font.SysFont(None, 18)
        except:
             btn_font = pygame.font.Font(None, 18) # Fallback
        btn_surf = btn_font.render(heatmap_btn_text, True, C.COLOR_UI_BUTTON_TEXT)
        btn_rect = btn_surf.get_rect(center=self.heatmap_button_rect.center)
        screen.blit(btn_surf, btn_rect)


        debug_btn_bg = C.COLOR_STOP if self.debug_mode else C.COLOR_UI_BUTTON_BG
        pygame.draw.rect(screen, debug_btn_bg, self.debug_toggle_button_rect)
        pygame.draw.rect(screen, C.COLOR_BLACK, self.debug_toggle_button_rect, 1)
        debug_btn_text = "Debug: ON" if self.debug_mode else "Debug: OFF"
        try: btn_font = pygame.font.SysFont(None, 20)
        except: btn_font = pygame.font.Font(None, 20)
        btn_surf = btn_font.render(debug_btn_text, True, btn_text_color)
        screen.blit(btn_surf, btn_surf.get_rect(center=self.debug_toggle_button_rect.center))

    def draw_debug_die_panel(self, screen, selected_face):
        self.debug_die_rects.clear()
        x, y = C.DEBUG_DIE_AREA_X, C.DEBUG_DIE_AREA_Y
        self.draw_text(screen, "DEBUG DIE SELECT:", x, y - C.UI_LINE_HEIGHT, size=18)
        y += 5
        unique_faces = set(C.DIE_FACES); ordered_unique_faces = []
        if C.STOP_SYMBOL in unique_faces: ordered_unique_faces.append(C.STOP_SYMBOL)
        numbers = sorted([f for f in unique_faces if isinstance(f, int)]); ordered_unique_faces.extend(numbers)

        for face in ordered_unique_faces:
            face_surf = self.debug_die_surfaces.get(face)
            if face_surf:
                rect = pygame.Rect(x, y, C.DEBUG_DIE_BUTTON_SIZE, C.DEBUG_DIE_BUTTON_SIZE)
                self.debug_die_rects[face] = rect
                screen.blit(face_surf, rect.topleft)
                if selected_face == face: pygame.draw.rect(screen, C.COLOR_SELECTED, rect, 3)
                x += C.DEBUG_DIE_BUTTON_SIZE + C.DEBUG_DIE_SPACING
                if x + C.DEBUG_DIE_BUTTON_SIZE > C.SCREEN_WIDTH - 20:
                    x = C.DEBUG_DIE_AREA_X
                    y += C.DEBUG_DIE_BUTTON_SIZE + C.DEBUG_DIE_SPACING

    def draw_debug_panel(self, screen, selected_debug_tile_type):
        self.debug_tile_rects.clear()
        current_col, current_row = 0, 0
        for i, tile_type in enumerate(self.debug_tile_types):
            rect = pygame.Rect(
                C.DEBUG_PANEL_X + current_col * (C.DEBUG_TILE_SIZE + C.DEBUG_TILE_SPACING),
                C.DEBUG_PANEL_Y + current_row * (C.DEBUG_TILE_SIZE + C.DEBUG_TILE_SPACING),
                C.DEBUG_TILE_SIZE, C.DEBUG_TILE_SIZE
            )
            self.debug_tile_rects[i] = rect
            pygame.draw.rect(screen, C.COLOR_WHITE, rect)
            debug_surf = self.debug_tile_surfaces.get(tile_type.name)
            if debug_surf:
                 screen.blit(debug_surf, debug_surf.get_rect(center=rect.center))
            pygame.draw.rect(screen, C.COLOR_BLACK, rect, 1)
            if selected_debug_tile_type == tile_type:
                 pygame.draw.rect(screen, C.COLOR_SELECTED, rect, 3)
            current_col = (current_col + 1) % C.DEBUG_TILES_PER_ROW
            if current_col == 0: current_row += 1

    def draw_selected_coord_highlight(self, screen, coord: Optional[Tuple[int, int]]):
        """Draws a translucent orange overlay on the selected board square."""
        if not coord:
            return

        r, c = coord
        if not self.game.board.is_playable_coordinate(r, c):
            return

        screen_x = C.BOARD_X_OFFSET + (c - C.PLAYABLE_COLS[0]) * self.TILE_SIZE
        screen_y = C.BOARD_Y_OFFSET + (r - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE
        rect = pygame.Rect(screen_x, screen_y, self.TILE_SIZE, self.TILE_SIZE)

        # Create a temporary surface for the highlight
        highlight_color = (255, 165, 0, 100) # Orange, semi-transparent
        temp_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        temp_surf.fill(highlight_color)
        screen.blit(temp_surf, rect.topleft)

        # Optional: Draw a thicker border for more emphasis
        pygame.draw.rect(screen, (255, 165, 0), rect, 2)

    def force_redraw(self, message: str = "Processing..."):
        """Forces an immediate, one-off redraw of the entire screen."""
        self.screen.fill(C.COLOR_UI_BG)
        # We need to call the current state's draw method to draw the board, etc.
        if self.current_state:
            # We can temporarily override the state's message for the redraw
            original_message = self.current_state.message
            self.current_state.message = message
            self.current_state.draw(self.screen)
            self.current_state.message = original_message
        pygame.display.flip()