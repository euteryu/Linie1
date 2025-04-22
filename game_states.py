# game_states.py
# ... (imports) ...
from typing import Optional, TypeVar
import pygame
from game_logic import Game, Player, TileType, PlayerState, GamePhase, Direction
import constants as C

class GameState: # Keep as is
    def __init__(self, visualizer): self.visualizer = visualizer; self.game = visualizer.game
    def handle_event(self, event): raise NotImplementedError
    def update(self, dt): pass
    def draw(self, screen): raise NotImplementedError

class LayingTrackState(GameState):
    # ... (__init__, get_selected_tile_type) ...
    def __init__(self, visualizer): # Keep as is
        super().__init__(visualizer); self.selected_tile_index: Optional[int] = None; self.debug_selected_tile_type: Optional[TileType] = None
        self.current_orientation = 0; self.message = ""; self.current_hand_rects: Dict[int, pygame.Rect] = {}; self.current_debug_rects: Dict[int, pygame.Rect] = {}
    def get_selected_tile_type(self) -> Optional[TileType]: # Keep as is
        if self.visualizer.debug_mode and self.debug_selected_tile_type: return self.debug_selected_tile_type
        elif not self.visualizer.debug_mode and self.selected_tile_index is not None:
             active_player = self.game.get_active_player();
             if 0 <= self.selected_tile_index < len(active_player.hand): return active_player.hand[self.selected_tile_index]
        return None

    def handle_event(self, event):
        active_player: Player = self.game.get_active_player()
        if active_player.player_state != PlayerState.LAYING_TRACK: return

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            # --- Debug Panel Click Check ---
            if self.visualizer.debug_mode:
                 # ... (keep debug panel click logic as before) ...
                 clicked_debug_index = None
                 for index, rect in self.visualizer.debug_tile_rects.items():
                     if rect.collidepoint(mouse_pos): clicked_debug_index = index; break
                 if clicked_debug_index is not None:
                     if event.button == 1: self.debug_selected_tile_type = self.visualizer.debug_tile_types[clicked_debug_index]; self.selected_tile_index = None; self.current_orientation = 0; self.message = f"Debug Select: {self.debug_selected_tile_type.name}"; return

            # --- Hand Area Click Check ---
            if not self.visualizer.debug_mode:
                 # ... (keep hand click logic as before) ...
                 clicked_hand_index = None
                 for index, rect in self.current_hand_rects.items():
                     if rect.collidepoint(mouse_pos): clicked_hand_index = index; break
                 if clicked_hand_index is not None:
                     if event.button == 1:
                         if self.selected_tile_index != clicked_hand_index: self.selected_tile_index = clicked_hand_index; self.debug_selected_tile_type = None; self.current_orientation = 0; selected_type = self.get_selected_tile_type(); self.message = f"Selected: {selected_type.name}" if selected_type else "Error"
                         return

            # --- Board Area Click Check ---
            if C.BOARD_X_OFFSET <= mouse_pos[0] < C.BOARD_X_OFFSET + C.BOARD_DRAW_WIDTH and \
               C.BOARD_Y_OFFSET <= mouse_pos[1] < C.BOARD_Y_OFFSET + C.BOARD_DRAW_HEIGHT:
                grid_col_rel = (mouse_pos[0] - C.BOARD_X_OFFSET) // C.TILE_SIZE
                grid_row_rel = (mouse_pos[1] - C.BOARD_Y_OFFSET) // C.TILE_SIZE
                grid_col_abs = grid_col_rel + C.PLAYABLE_COLS[0]
                grid_row_abs = grid_row_rel + C.PLAYABLE_ROWS[0]

                if event.button == 1: # Left Click on Board
                    selected_type = self.get_selected_tile_type()
                    if not selected_type:
                        self.message = "Select a tile first."; return # Exit if no tile selected

                    if not self.game.board.is_valid_coordinate(grid_row_abs, grid_col_abs):
                        self.message = "Clicked outside valid grid."; return # Clicked border maybe

                    # *** DIFFERENTIATE ACTION BASED ON TARGET SQUARE ***
                    target_tile = self.game.board.get_tile(grid_row_abs, grid_col_abs)

                    if target_tile is None:
                        # --- Attempt PLACE action ---
                        if self.game.board.is_playable_coordinate(grid_row_abs, grid_col_abs): # Can only place on playable squares
                             success = self.game.player_action_place_tile(
                                 active_player, selected_type, self.current_orientation, grid_row_abs, grid_col_abs
                             )
                             if success:
                                 self.message = f"Placed {selected_type.name}."
                                 # Reset selection based on mode
                                 if self.visualizer.debug_mode: self.debug_selected_tile_type = None
                                 else: self.selected_tile_index = None
                                 self.current_orientation = 0
                                 if self.game.actions_taken_this_turn >= C.MAX_PLAYER_ACTIONS:
                                     self.end_turn_sequence()
                             else:
                                 self.message = "Invalid placement." # Logic printed details
                        else:
                             self.message = "Cannot place tile here."

                    else: # Target square IS occupied
                         # --- Attempt EXCHANGE action ---
                         # Can only exchange on playable squares
                         if self.game.board.is_playable_coordinate(grid_row_abs, grid_col_abs):
                              success = self.game.player_action_exchange_tile(
                                   active_player, selected_type, self.current_orientation, grid_row_abs, grid_col_abs
                              )
                              if success:
                                   self.message = f"Exchanged for {selected_type.name}."
                                   # Reset selection based on mode
                                   if self.visualizer.debug_mode: self.debug_selected_tile_type = None
                                   else: self.selected_tile_index = None
                                   self.current_orientation = 0
                                   if self.game.actions_taken_this_turn >= C.MAX_PLAYER_ACTIONS:
                                       self.end_turn_sequence()
                              else:
                                   self.message = "Invalid exchange." # Logic printed details
                         else:
                              self.message = "Cannot exchange terminal/border."


                elif event.button == 3: # Right Click on Board -> Rotate
                    self.current_orientation = (self.current_orientation + 90) % 360
                    self.message = f"Orientation: {self.current_orientation} deg"

        # ... (Keep KEYDOWN handling) ...
        elif event.type == pygame.KEYDOWN:
             if event.key == pygame.K_r: self.current_orientation = (self.current_orientation + 90) % 360; self.message = f"Orientation: {self.current_orientation} deg"
             elif event.key == pygame.K_SPACE:
                 if not self.visualizer.debug_mode:
                     if self.game.actions_taken_this_turn >= C.MAX_PLAYER_ACTIONS: self.end_turn_sequence()
                     else: self.message = f"Need {C.MAX_PLAYER_ACTIONS - self.game.actions_taken_this_turn} more actions."
                 else: self.message = "End Turn disabled in Debug."

    # ... (keep end_turn_sequence, draw, get_selected_tile_type) ...
    def end_turn_sequence(self): # Keep as is
         self.game.end_player_turn(); self.message = ""; self.selected_tile_index = None; self.debug_selected_tile_type = None; self.current_orientation = 0
         new_player = self.game.get_active_player()
         if new_player.player_state == PlayerState.LAYING_TRACK:
             if self.game.check_player_route_completion(new_player): self.game.handle_route_completion(new_player)
    def draw(self, screen): # Keep as is
        self.visualizer.draw_board(screen)
        if self.visualizer.debug_mode: self.visualizer.draw_debug_panel(screen, self.debug_selected_tile_type); self.current_hand_rects = {}
        else: self.current_hand_rects = self.visualizer.draw_hand(screen, self.game.get_active_player())
        selected_type = self.get_selected_tile_type(); self.visualizer.draw_ui(screen, self.message, selected_type, self.current_orientation)
        self.visualizer.draw_preview(screen, selected_type, self.current_orientation)


# --- Keep Placeholder States (DrivingState, GameOverState) ---
class DrivingState(GameState): # Placeholder
    def handle_event(self, event): print("Driving State: Event handling not implemented.")
    def draw(self, screen): self.visualizer.draw_board(screen); self.visualizer.draw_text(screen, "DRIVING PHASE", 10, self.visualizer.SCREEN_HEIGHT - 30)
class GameOverState(GameState): # Placeholder
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN: print("Game Over.")
    def draw(self, screen):
        self.visualizer.draw_board(screen); winner_id = self.game.first_player_to_finish_route
        win_text = f"GAME OVER! Player {winner_id} Wins!" if winner_id is not None else "GAME OVER!"
        self.visualizer.draw_text(screen, win_text, C.SCREEN_WIDTH // 2 - 150, C.SCREEN_HEIGHT // 2, size=40)