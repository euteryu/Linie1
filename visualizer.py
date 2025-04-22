# visualizer.py
# -*- coding: utf-8 -*-
import pygame
import sys
import math
from typing import List, Dict, Tuple, Optional, Any
from game_logic import Game, PlacedTile, TileType, GamePhase, Direction, Player
from game_states import GameState, LayingTrackState, DrivingState, GameOverState
import constants as C # Use alias
import copy
from collections import deque

# --- Keep create_tile_surface (Assumed correct from previous step) ---
def create_tile_surface(tile_type: TileType, size: int) -> pygame.Surface:
    surf = pygame.Surface((size, size), pygame.SRCALPHA); surf.fill((0, 0, 0, 0))
    line_width = max(2, int(size * 0.1)); track_color = C.COLOR_TRACK
    half_size_f = size / 2.0; ptN = (int(half_size_f), 0); ptS = (int(half_size_f), size); ptE = (size, int(half_size_f)); ptW = (0, int(half_size_f))
    radius = size // 2; rect_centered_TR = pygame.Rect(int(size/2.0), int(-size/2.0), size, size); rect_centered_TL = pygame.Rect(int(-size/2.0), int(-size/2.0), size, size); rect_centered_BR = pygame.Rect(int(size/2.0), int(size/2.0), size, size); rect_centered_BL = pygame.Rect(int(-size/2.0), int(size/2.0), size, size)
    angle_N = math.pi / 2; angle_W = math.pi; angle_S = 3 * math.pi / 2; angle_E = 0
    temp_size = int(size + line_width * 2.0); temp_surf = pygame.Surface((temp_size, temp_size), pygame.SRCALPHA); temp_surf.fill((0,0,0,0))
    temp_offset_x_f = float(line_width); temp_offset_y_f = float(line_width)
    ptN_temp = (int(size / 2.0 + temp_offset_x_f), int(0 + temp_offset_y_f)); ptS_temp = (int(size / 2.0 + temp_offset_x_f), int(size + temp_offset_y_f)); ptE_temp = (int(size + temp_offset_x_f), int(size / 2.0 + temp_offset_y_f)); ptW_temp = (int(0 + temp_offset_x_f), int(size / 2.0 + temp_offset_y_f))
    rect_centered_TR_temp = pygame.Rect(int(size/2.0 + temp_offset_x_f), int(-size/2.0 + temp_offset_y_f), size, size); rect_centered_TL_temp = pygame.Rect(int(-size/2.0 + temp_offset_x_f), int(-size/2.0 + temp_offset_y_f), size, size); rect_centered_BR_temp = pygame.Rect(int(size/2.0 + temp_offset_x_f), int(size/2.0 + temp_offset_y_f), size, size); rect_centered_BL_temp = pygame.Rect(int(-size/2.0 + temp_offset_x_f), int(size/2.0 + temp_offset_y_f), size, size)
    tile_name = tile_type.name
    if tile_name == "Straight": pygame.draw.line(temp_surf, track_color, ptN_temp, ptS_temp, line_width)
    elif tile_name == "Curve": pygame.draw.arc(temp_surf, track_color, rect_centered_TR_temp, angle_N, angle_E + 2*math.pi, line_width)
    elif tile_name == "StraightLeftCurve": pygame.draw.line(temp_surf, track_color, ptN_temp, ptS_temp, line_width); pygame.draw.arc(temp_surf, track_color, rect_centered_BL_temp, angle_W, angle_S, line_width)
    elif tile_name == "StraightRightCurve": pygame.draw.line(temp_surf, track_color, ptN_temp, ptS_temp, line_width); pygame.draw.arc(temp_surf, track_color, rect_centered_BR_temp, angle_E, angle_S, line_width)
    elif tile_name == "DoubleCurveY": pygame.draw.arc(temp_surf, track_color, rect_centered_TL_temp, angle_N, angle_W, line_width); pygame.draw.arc(temp_surf, track_color, rect_centered_TR_temp, angle_N, angle_E + 2*math.pi, line_width)
    elif tile_name == "DiagonalCurve": pygame.draw.arc(temp_surf, track_color, rect_centered_BL_temp, angle_W, angle_S, line_width); pygame.draw.arc(temp_surf, track_color, rect_centered_TR_temp, angle_N, angle_E + 2*math.pi, line_width)
    elif tile_name == "Tree_JunctionTop": pygame.draw.line(temp_surf, track_color, ptW_temp, ptE_temp, line_width); pygame.draw.arc(temp_surf, track_color, rect_centered_TL_temp, angle_N, angle_W, line_width); pygame.draw.arc(temp_surf, track_color, rect_centered_TR_temp, angle_N, angle_E + 2*math.pi, line_width)
    elif tile_name == "Tree_JunctionRight": pygame.draw.line(temp_surf, track_color, ptW_temp, ptE_temp, line_width); pygame.draw.arc(temp_surf, track_color, rect_centered_TR_temp, angle_N, angle_E + 2*math.pi, line_width); pygame.draw.arc(temp_surf, track_color, rect_centered_BR_temp, angle_E, angle_S, line_width)
    elif tile_name == "Tree_Roundabout": pygame.draw.arc(temp_surf, track_color, rect_centered_TL_temp, angle_N, angle_W, line_width); pygame.draw.arc(temp_surf, track_color, rect_centered_TR_temp, angle_N, angle_E + 2*math.pi, line_width); pygame.draw.arc(temp_surf, track_color, rect_centered_BR_temp, angle_E, angle_S, line_width); pygame.draw.arc(temp_surf, track_color, rect_centered_BL_temp, angle_W, angle_S, line_width)
    elif tile_name == "Tree_Crossroad": pygame.draw.line(temp_surf, track_color, ptN_temp, ptS_temp, line_width); pygame.draw.line(temp_surf, track_color, ptW_temp, ptE_temp, line_width)
    elif tile_name == "Tree_StraightDiagonal1": pygame.draw.line(temp_surf, track_color, ptN_temp, ptS_temp, line_width); pygame.draw.arc(temp_surf, track_color, rect_centered_BL_temp, angle_W, angle_S, line_width); pygame.draw.arc(temp_surf, track_color, rect_centered_TR_temp, angle_N, angle_E + 2*math.pi, line_width)
    elif tile_name == "Tree_StraightDiagonal2": pygame.draw.line(temp_surf, track_color, ptN_temp, ptS_temp, line_width); pygame.draw.arc(temp_surf, track_color, rect_centered_TL_temp, angle_N, angle_W, line_width); pygame.draw.arc(temp_surf, track_color, rect_centered_BR_temp, angle_E, angle_S, line_width)
    else: print(f"FATAL ERROR: Unknown tile type to draw: {tile_name}")
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

        # Main Surfaces
        print("Generating main tile surfaces...");
        self.tile_surfaces = { name: create_tile_surface(ttype, self.TILE_SIZE) for name, ttype in self.game.tile_types.items()}
        self.hand_tile_surfaces = { name: create_tile_surface(ttype, self.HAND_TILE_SIZE) for name, ttype in self.game.tile_types.items()}
        print("Tile surfaces generated.")
        self.current_state: GameState = LayingTrackState(self)

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
            self.check_game_phase()

            # Drawing
            self.screen.fill(C.COLOR_UI_BG)
            self.current_state.draw(self.screen)
            pygame.display.flip()

        pygame.quit()
        sys.exit()

    # --- check_game_phase(), draw_text() remain the same ---
    def check_game_phase(self): # Keep as is
        model_phase = self.game.game_phase
        if model_phase == GamePhase.LAYING_TRACK and not isinstance(self.current_state, LayingTrackState): self.current_state = LayingTrackState(self)
        elif model_phase == GamePhase.DRIVING and not isinstance(self.current_state, DrivingState): self.current_state = DrivingState(self)
        elif model_phase == GamePhase.GAME_OVER and not isinstance(self.current_state, GameOverState): self.current_state = GameOverState(self)
    def draw_text(self, surface, text, x, y, color=C.COLOR_UI_TEXT, size=24): # Keep as is
        try: font_to_use = pygame.font.SysFont(None, size) if size != 24 else self.font; text_surface = font_to_use.render(text, True, color); surface.blit(text_surface, (x, y))
        except Exception as e: print(f"Error rendering text '{text}': {e}")

    # --- draw_board() remains the same (draws terminals as PlacedTiles) ---
    def draw_board(self, screen): # Keep corrected terminal drawing logic
        drawn_terminal_labels = set()
        for r in range(C.GRID_ROWS):
            for c in range(C.GRID_COLS):
                if not (C.PLAYABLE_ROWS[0]-1 <= r <= C.PLAYABLE_ROWS[1]+1 and C.PLAYABLE_COLS[0]-1 <= c <= C.PLAYABLE_COLS[1]+1): continue
                screen_x = C.BOARD_X_OFFSET + (c - C.PLAYABLE_COLS[0]) * self.TILE_SIZE; screen_y = C.BOARD_Y_OFFSET + (r - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE; rect = pygame.Rect(screen_x, screen_y, self.TILE_SIZE, self.TILE_SIZE)
                placed_tile = self.game.board.get_tile(r, c); is_playable = self.game.board.is_playable_coordinate(r, c); is_terminal = placed_tile is not None and placed_tile.is_terminal
                bg_color = C.COLOR_BOARD_BG;
                if is_terminal: bg_color = C.COLOR_TERMINAL_BG
                elif not is_playable: bg_color = tuple(max(0, val - 40) for val in C.COLOR_BOARD_BG)
                pygame.draw.rect(screen, bg_color, rect); pygame.draw.rect(screen, C.COLOR_GRID, rect, 1)
                if placed_tile:
                    tile_surf = self.tile_surfaces.get(placed_tile.tile_type.name)
                    if tile_surf: rotated_surf = pygame.transform.rotate(tile_surf, -placed_tile.orientation); new_rect = rotated_surf.get_rect(center=rect.center); screen.blit(rotated_surf, new_rect.topleft)
                    if placed_tile.has_stop_sign and is_playable: pygame.draw.circle(screen, C.COLOR_STOP, rect.center, self.TILE_SIZE // 4)
                building_id = self.game.board.get_building_at(r, c)
                if building_id and is_playable: b_font = pygame.font.SysFont(None, 20); b_surf = b_font.render(building_id, True, C.COLOR_BUILDING); screen.blit(b_surf, (screen_x + 2, screen_y + 2))
        terminal_font = pygame.font.SysFont(None, int(self.TILE_SIZE * 0.5))
        for line_num, entrances in C.TERMINAL_DATA.items():
             if line_num in drawn_terminal_labels: continue
             entrance_a, entrance_b = entrances; cell1_a_coord = entrance_a[0][0]; cell2_a_coord = entrance_a[1][0]; cell1_b_coord = entrance_b[0][0]; cell2_b_coord = entrance_b[1][0]
             rect1_x1 = C.BOARD_X_OFFSET + (cell1_a_coord[1] - C.PLAYABLE_COLS[0]) * self.TILE_SIZE; rect1_y1 = C.BOARD_Y_OFFSET + (cell1_a_coord[0] - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE; rect2_x1 = C.BOARD_X_OFFSET + (cell2_a_coord[1] - C.PLAYABLE_COLS[0]) * self.TILE_SIZE; rect2_y1 = C.BOARD_Y_OFFSET + (cell2_a_coord[0] - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE; pair1_center_x = (rect1_x1 + rect2_x1 + self.TILE_SIZE) // 2; pair1_center_y = (rect1_y1 + rect2_y1 + self.TILE_SIZE) // 2
             term_surf = terminal_font.render(str(line_num), True, C.COLOR_TERMINAL_TEXT); term_rect1 = term_surf.get_rect(center=(pair1_center_x, pair1_center_y)); bg_rect1 = term_rect1.inflate(6, 4); pygame.draw.rect(screen, C.COLOR_TRACK, bg_rect1, border_radius=3); screen.blit(term_surf, term_rect1)
             rect1_x2 = C.BOARD_X_OFFSET + (cell1_b_coord[1] - C.PLAYABLE_COLS[0]) * self.TILE_SIZE; rect1_y2 = C.BOARD_Y_OFFSET + (cell1_b_coord[0] - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE; rect2_x2 = C.BOARD_X_OFFSET + (cell2_b_coord[1] - C.PLAYABLE_COLS[0]) * self.TILE_SIZE; rect2_y2 = C.BOARD_Y_OFFSET + (cell2_b_coord[0] - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE; pair2_center_x = (rect1_x2 + rect2_x2 + self.TILE_SIZE) // 2; pair2_center_y = (rect1_y2 + rect2_y2 + self.TILE_SIZE) // 2
             term_rect2 = term_surf.get_rect(center=(pair2_center_x, pair2_center_y)); bg_rect2 = term_rect2.inflate(6, 4); pygame.draw.rect(screen, C.COLOR_TRACK, bg_rect2, border_radius=3); screen.blit(term_surf, term_rect2)
             drawn_terminal_labels.add(line_num)

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

    # --- draw_ui needs modification ---
    def draw_ui(self, screen, message, selected_tile_type, orientation):
        """Draws UI elements, conditionally showing debug info or hand info."""
        player = self.game.get_active_player()
        # --- Always Draw Top Info ---
        turn_text = f"Turn {self.game.current_turn} - Player {player.player_id} ({player.player_state.name})"
        self.draw_text(screen, turn_text, C.UI_TEXT_X, C.UI_TURN_INFO_Y)
        action_text = f"Actions: {self.game.actions_taken_this_turn}/{C.MAX_PLAYER_ACTIONS}"
        font_to_use = self.font if self.font else pygame.font.Font(None, 24)
        try:
            action_surf = font_to_use.render(action_text, True, C.COLOR_UI_TEXT)
            action_text_width = action_surf.get_width()
            self.draw_text(screen, action_text, C.UI_PANEL_X + C.UI_PANEL_WIDTH - action_text_width - 15, C.UI_TURN_INFO_Y)
        except Exception as e:
            print(f"Error rendering action text: {e}")
        line_info = "Line: ?"; stops_info = "Stops: ?"
        if player.line_card: term1, term2 = self.game.get_terminal_coords(player.line_card.line_number); term1_str = f"T{player.line_card.line_number}a" if term1 else "?"; term2_str = f"T{player.line_card.line_number}b" if term2 else "?"; line_info = f"Line {player.line_card.line_number} ({term1_str}<->{term2_str})"
        if player.route_card: stops_str = " -> ".join(player.route_card.stops); stops_info = f"Stops: {stops_str}"
        self.draw_text(screen, line_info, C.UI_TEXT_X, C.UI_ROUTE_INFO_Y)
        self.draw_text(screen, stops_info, C.UI_TEXT_X, C.UI_ROUTE_INFO_Y + C.UI_LINE_HEIGHT)

        # --- Draw EITHER Normal UI Bottom OR Debug Panel Title ---
        if isinstance(self.current_state, LayingTrackState):
            if self.debug_mode:
                 # Draw Debug Title where Hand Title would normally be
                 self.draw_text(screen, "DEBUG TILE PALETTE", C.HAND_AREA_X, C.UI_HAND_TITLE_Y)
                 # Draw message and selection below debug panel (adjust Y)
                 debug_panel_end_y = C.DEBUG_PANEL_Y + ((len(self.debug_tile_types) + C.DEBUG_TILES_PER_ROW -1) // C.DEBUG_TILES_PER_ROW) * (C.DEBUG_TILE_SIZE + C.DEBUG_TILE_SPACING)
                 sel_text = "Selected: None";
                 if selected_tile_type: sel_text = f"Selected: {selected_tile_type.name} ({orientation}°)"
                 self.draw_text(screen, sel_text, C.UI_TEXT_X, debug_panel_end_y + 10)
                 self.draw_text(screen, f"Msg: {message}", C.UI_TEXT_X, debug_panel_end_y + 10 + C.UI_LINE_HEIGHT)
                 # Instructions might be less relevant in debug, but draw anyway
                 self.draw_text(screen, "[R] Rotate | [LMB] Place/Select | [Button] Toggle", C.UI_TEXT_X, C.UI_INSTRUCTIONS_Y, size=18)

            else: # Normal Mode UI Bottom
                 self.draw_text(screen, f"Player {player.player_id}'s Hand:", C.HAND_AREA_X, C.UI_HAND_TITLE_Y)
                 sel_text = "Selected: None";
                 if selected_tile_type: sel_text = f"Selected: {selected_tile_type.name} ({orientation}°)"
                 self.draw_text(screen, sel_text, C.UI_TEXT_X, C.UI_SELECTED_TILE_Y)
                 self.draw_text(screen, f"Msg: {message}", C.UI_TEXT_X, C.UI_MESSAGE_Y)
                 self.draw_text(screen, "[RMB/R] Rotate | [LMB] Place/Select | [SPACE] End", C.UI_TEXT_X, C.UI_INSTRUCTIONS_Y, size=18)

        # --- Always Draw Debug Toggle Button ---
        pygame.draw.rect(screen, C.COLOR_GRID, self.debug_toggle_button_rect)
        pygame.draw.rect(screen, C.COLOR_BLACK, self.debug_toggle_button_rect, 1)
        debug_btn_text = "Debug: ON" if self.debug_mode else "Debug: OFF"
        btn_font = pygame.font.SysFont(None, 20)
        btn_surf = btn_font.render(debug_btn_text, True, C.COLOR_WHITE)
        btn_rect = btn_surf.get_rect(center=self.debug_toggle_button_rect.center)
        screen.blit(btn_surf, btn_rect)


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