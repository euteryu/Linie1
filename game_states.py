# game_states.py
# ... (imports) ...
from typing import Optional, TypeVar, Dict, Any # Keep existing imports
import pygame
import constants as C
import tkinter as tk               # Import tkinter
from tkinter import filedialog     # <--- IMPORT filedialog HERE

# from game_logic import Game, Player, TileType, PlayerState, GamePhase, Direction
from game_logic.game import Game # Import main Game class
from game_logic.player import Player # Import Player if needed directly
from game_logic.tile import PlacedTile, TileType # Import tile classes if needed
from game_logic.enums import GamePhase, PlayerState, Direction # Import enums

class GameState:
    def __init__(self, visualizer): self.visualizer = visualizer; self.game = visualizer.game
    def handle_event(self, event): raise NotImplementedError
    def update(self, dt): pass
    def draw(self, screen): raise NotImplementedError

    # --- Common Save/Load Click Handling ---
    def _handle_common_clicks(self, event):
        """Handles clicks common to most states, like Save/Load buttons."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            if self.visualizer.save_button_rect.collidepoint(mouse_pos):
                self.save_game_action()
                return True # Event handled
            elif self.visualizer.load_button_rect.collidepoint(mouse_pos):
                self.load_game_action()
                return True # Event handled
        return False # Event not handled by common clicks

    # --- Save/Load Action Methods ---
    def save_game_action(self):
        """Opens file dialog and saves the game."""
        if not self.visualizer.tk_root:
             print("Error: Tkinter not available for file dialog.")
             if isinstance(self, LayingTrackState): self.message = "Save failed: Tkinter needed."
             return

        filepath = filedialog.asksaveasfilename(
            title="Save Linie 1 Game State",
            defaultextension=".json",
            filetypes=[("Linie 1 Save Files", "*.json"), ("All Files", "*.*")]
        )
        if filepath: # Check if a file was selected (not cancelled)
            if self.game.save_game(filepath):
                if isinstance(self, LayingTrackState): self.message = f"Game saved to {filepath.split('/')[-1]}"
                elif isinstance(self, DrivingState): self.message = f"Game saved." # Driving state has own message handling
                # Update message in other states if needed
            else:
                if isinstance(self, LayingTrackState): self.message = "Error saving game."
                elif isinstance(self, DrivingState): self.message = "Error saving game."
        else:
            if isinstance(self, LayingTrackState): self.message = "Save cancelled."
            elif isinstance(self, DrivingState): self.message = "Save cancelled."


    def load_game_action(self):
        """Opens file dialog and loads the game."""
        if not self.visualizer.tk_root:
             print("Error: Tkinter not available for file dialog.")
             if isinstance(self, LayingTrackState): self.message = "Load failed: Tkinter needed."
             return

        filepath = filedialog.askopenfilename(
            title="Load Linie 1 Game State",
            filetypes=[("Linie 1 Save Files", "*.json"), ("All Files", "*.*")]
        )
        if filepath:
            loaded_game = Game.load_game(filepath, self.game.tile_types) # Pass existing tile definitions
            if loaded_game:
                # --- Replace game instance in visualizer ---
                self.visualizer.game = loaded_game
                # --- VERY IMPORTANT: Update the game reference in the *current state* object ---
                self.game = loaded_game
                # --- Reset visualizer/state based on loaded game ---
                # self.visualizer.check_game_phase() # Let this switch the GameState object if needed
                # Reset any state-specific UI elements
                if isinstance(self, LayingTrackState):
                    self.message = f"Game loaded from {filepath.split('/')[-1]}"
                    self.selected_tile_index = None
                    self.debug_selected_tile_type = None
                    self.current_orientation = 0
                elif isinstance(self, DrivingState):
                     self.message = f"Game loaded."
                     self.last_roll = None
                # Reset messages/state in other states if needed
                print("Load successful, visualizer game instance updated.")
            else:
                if isinstance(self, LayingTrackState): self.message = "Error loading game."
                elif isinstance(self, DrivingState): self.message = "Error loading game."
        else:
            if isinstance(self, LayingTrackState): self.message = "Load cancelled."
            elif isinstance(self, DrivingState): self.message = "Load cancelled."

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

    def get_selected_tile_for_preview(self) -> Optional[TileType]:
        """Gets the tile type to show in the preview or UI, based on mode."""
        if self.visualizer.debug_mode and self.debug_selected_tile_type:
            # In debug mode, use the tile selected from the palette
            return self.debug_selected_tile_type
        elif not self.visualizer.debug_mode and self.selected_tile_index is not None:
             # In normal mode, use the tile selected from the player's actual hand
             active_player = self.game.get_active_player()
             # Basic check to prevent errors if player object is weird
             if active_player and hasattr(active_player, 'hand'):
                  if 0 <= self.selected_tile_index < len(active_player.hand):
                      return active_player.hand[self.selected_tile_index]
             # else: print("Warning: Could not get valid player/hand for preview.")
        # If no valid selection in the current mode
        return None

    def handle_event(self, event):
        # --- Handle Save/Load/Debug Toggle first ---
        if self._handle_common_clicks(event): return # Handles save/load

        # --- Debug Toggle Specific Logic ---
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
             if self.visualizer.debug_toggle_button_rect.collidepoint(event.pos):
                 self.visualizer.debug_mode = not self.visualizer.debug_mode
                 if self.visualizer.debug_mode:
                      # --- Entering Debug Mode ---
                      # No hand swap needed with palette approach
                      self.message = "Debug Mode ON: Select from palette"
                      self.selected_tile_index = None # Clear hand selection
                 else:
                      # --- Exiting Debug Mode ---
                      self.message = "Debug Mode OFF"
                      self.debug_selected_tile_type = None # Clear palette selection
                 return # Consume event

        # --- Event handling specific to Laying Track state ---
        active_player: Player = self.game.get_active_player()
        # If game loaded into a different state, or player finished, do nothing here
        if active_player.player_state != PlayerState.LAYING_TRACK: return

        # --- Handle Input ---
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            # --- Debug Palette Click Check (ONLY if debug mode is ON) ---
            if self.visualizer.debug_mode:
                 clicked_debug_index = None
                 for index, rect in self.visualizer.debug_tile_rects.items():
                     if rect.collidepoint(mouse_pos):
                         clicked_debug_index = index
                         break
                 if clicked_debug_index is not None:
                     if event.button == 1: # Left click selects from palette
                         # Get TileType corresponding to the clicked index
                         selected_type = self.visualizer.debug_tile_types[clicked_debug_index]
                         self.debug_selected_tile_type = selected_type
                         self.selected_tile_index = None # Ensure normal hand selection is cleared
                         self.current_orientation = 0
                         self.message = f"Debug Select: {self.debug_selected_tile_type.name}"
                         return # Consume event, selected from palette

            # --- Hand Area Click Check (ONLY if debug mode is OFF) ---
            elif not self.visualizer.debug_mode: # Note the 'elif'
                 clicked_hand_index = None
                 for index, rect in self.current_hand_rects.items():
                     if rect.collidepoint(mouse_pos):
                         clicked_hand_index = index
                         break
                 if clicked_hand_index is not None:
                     if event.button == 1: # Left click selects from hand
                         if self.selected_tile_index != clicked_hand_index:
                             self.selected_tile_index = clicked_hand_index
                             self.debug_selected_tile_type = None # Clear debug selection
                             self.current_orientation = 0
                             selected_type = self.get_selected_tile_for_preview() # Use helper
                             self.message = f"Selected: {selected_type.name}" if selected_type else "Error getting selection"
                         return # Consume event, selected from hand

            # --- Board Area Click Check ---
            if C.BOARD_X_OFFSET <= mouse_pos[0] < C.BOARD_X_OFFSET + C.BOARD_DRAW_WIDTH and \
               C.BOARD_Y_OFFSET <= mouse_pos[1] < C.BOARD_Y_OFFSET + C.BOARD_DRAW_HEIGHT:
                grid_col_rel = (mouse_pos[0] - C.BOARD_X_OFFSET) // C.TILE_SIZE
                grid_row_rel = (mouse_pos[1] - C.BOARD_Y_OFFSET) // C.TILE_SIZE
                grid_col_abs = grid_col_rel + C.PLAYABLE_COLS[0]
                grid_row_abs = grid_row_rel + C.PLAYABLE_ROWS[0]

                if event.button == 1: # Left Click on Board (Place/Exchange)
                    # Determine which tile type to use based on mode
                    tile_to_place = self.get_selected_tile_for_preview()

                    if not tile_to_place:
                        self.message = "Select a tile first (from hand or palette)."
                        return

                    if not self.game.board.is_valid_coordinate(grid_row_abs, grid_col_abs):
                        self.message = "Clicked outside valid grid."
                        return

                    target_tile = self.game.board.get_tile(grid_row_abs, grid_col_abs)

                    # --- Logic bifurcation based on Debug Mode ---
                    if self.visualizer.debug_mode:
                        # --- DEBUG PLACE / EXCHANGE ---
                        if target_tile is None: # Try Place
                             if self.game.board.is_playable_coordinate(grid_row_abs, grid_col_abs):
                                 is_valid, msg = self.game.check_placement_validity(tile_to_place, self.current_orientation, grid_row_abs, grid_col_abs)
                                 if is_valid:
                                     placed_tile = PlacedTile(tile_to_place, self.current_orientation)
                                     self.game.board.set_tile(grid_row_abs, grid_col_abs, placed_tile)
                                     self.game._check_and_place_stop_sign(placed_tile, grid_row_abs, grid_col_abs)
                                     self.message = f"DEBUG: Placed {tile_to_place.name}."
                                     # DO NOT change selection or end turn
                                 else: self.message = f"DEBUG: Invalid placement. {msg}"
                             else: self.message = "DEBUG: Cannot place on border."
                        else: # Try Exchange
                            if self.game.board.is_playable_coordinate(grid_row_abs, grid_col_abs):
                                # Simplified Debug Exchange Check (Bypasses hand, complex connection logic)
                                can_exchange = True; msg = ""
                                if target_tile.is_terminal: msg = "Cannot exchange terminal."; can_exchange = False
                                elif not target_tile.tile_type.is_swappable: msg = "Tile not swappable."; can_exchange = False
                                elif target_tile.has_stop_sign: msg = "Cannot exchange tile with stop sign."; can_exchange = False
                                # TODO: Add proper connection validation for debug exchange if needed later

                                if can_exchange:
                                     # Directly perform exchange without action cost
                                     new_placed_tile = PlacedTile(tile_to_place, self.current_orientation)
                                     self.game.board.set_tile(grid_row_abs, grid_col_abs, new_placed_tile)
                                     self.message = f"DEBUG: Exchanged for {tile_to_place.name}."
                                     # DO NOT change selection or end turn
                                else: self.message = f"DEBUG: Invalid exchange. {msg}"
                            else: self.message = "DEBUG: Cannot exchange border."

                    else:
                        # --- NORMAL PLACE / EXCHANGE ---
                        if target_tile is None: # Try Place
                            if self.game.board.is_playable_coordinate(grid_row_abs, grid_col_abs):
                                success = self.game.player_action_place_tile(active_player, tile_to_place, self.current_orientation, grid_row_abs, grid_col_abs)
                                if success:
                                    self.message = f"Placed {tile_to_place.name}."
                                    self.selected_tile_index = None # Clear selection
                                    self.current_orientation = 0
                                    if self.game.actions_taken_this_turn >= C.MAX_PLAYER_ACTIONS: self.end_turn_sequence()
                                else: self.message = "Invalid placement." # Game logic printed details
                            else: self.message = "Cannot place tile here."
                        else: # Try Exchange
                            if self.game.board.is_playable_coordinate(grid_row_abs, grid_col_abs):
                                success = self.game.player_action_exchange_tile(active_player, tile_to_place, self.current_orientation, grid_row_abs, grid_col_abs)
                                if success:
                                     self.message = f"Exchanged for {tile_to_place.name}."
                                     self.selected_tile_index = None # Clear selection
                                     self.current_orientation = 0
                                     if self.game.actions_taken_this_turn >= C.MAX_PLAYER_ACTIONS: self.end_turn_sequence()
                                else: self.message = "Invalid exchange." # Game logic printed details
                            else: self.message = "Cannot exchange terminal/border."

                elif event.button == 3: # Right Click on Board -> Rotate
                    self.current_orientation = (self.current_orientation + 90) % 360
                    selected_type = self.get_selected_tile_for_preview()
                    self.message = f"Orientation: {self.current_orientation}°" + (f" for {selected_type.name}" if selected_type else "")


        elif event.type == pygame.KEYDOWN:
             if event.key == pygame.K_r: # Rotate selected tile
                 self.current_orientation = (self.current_orientation + 90) % 360
                 selected_type = self.get_selected_tile_for_preview()
                 self.message = f"Orientation: {self.current_orientation}°" + (f" for {selected_type.name}" if selected_type else "")
             elif event.key == pygame.K_SPACE: # End turn (ONLY if not in debug mode)
                 if not self.visualizer.debug_mode:
                     if self.game.actions_taken_this_turn >= C.MAX_PLAYER_ACTIONS:
                          self.end_turn_sequence()
                     elif self.game.actions_taken_this_turn > 0:
                          # Allow ending turn early if at least one action taken
                          print(f"Player {active_player.player_id} chose to end turn after {self.game.actions_taken_this_turn} actions.")
                          self.end_turn_sequence()
                     else:
                          self.message = f"Need to take at least 1 action."
                 else:
                      self.message = "End Turn disabled in Debug Mode."

    def end_turn_sequence(self):
        """Ends the current player's turn and resets state."""
        # Call the main game logic end turn function
        self.game.end_player_turn()

        # Reset visual state elements for the next player
        self.message = ""
        self.selected_tile_index = None
        self.debug_selected_tile_type = None
        self.current_orientation = 0

        # Note: The route completion check is now handled within game.end_player_turn
        #       before the next player actually starts their actions.
        #       The visualizer.check_game_phase() call in the main loop
        #       will switch the GameState object if needed based on the
        #       player's state change in handle_route_completion.

    def draw(self, screen):
        self.visualizer.draw_board(screen)

        # Draw Hand OR Debug Panel
        if self.visualizer.debug_mode:
            self.visualizer.draw_debug_panel(screen, self.debug_selected_tile_type)
            self.current_hand_rects = {} # Clear hand rects when not drawn
        else:
            # Need to handle case where player might not exist (e.g., after error/bad load)
            player = self.game.get_active_player()
            if player:
                 self.current_hand_rects = self.visualizer.draw_hand(screen, player)
            else:
                 self.current_hand_rects = {} # No player, no hand

        # Draw UI, passing the correct selected tile type for display
        selected_type_for_ui = self.get_selected_tile_for_preview()
        self.visualizer.draw_ui(screen, self.message, selected_type_for_ui, self.current_orientation)

        # Draw Preview
        self.visualizer.draw_preview(screen, selected_type_for_ui, self.current_orientation)


class DrivingState(GameState): # Placeholder - TO BE IMPLEMENTED
    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.message = ""
        self.last_roll: Optional[Any] = None # To store the die roll result

    def handle_event(self, event):
        # ... (Handle Save/Load/Debug Toggle first) ...
        if self._handle_common_clicks(event): return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
             if self.visualizer.debug_toggle_button_rect.collidepoint(event.pos):
                 # ... (toggle debug) ...
                 return

        active_player = self.game.get_active_player()
        if active_player.player_state != PlayerState.DRIVING: return

        roll_result: Optional[Any] = None
        action_triggered = False

        # --- Check for Debug Die Click ---
        if self.visualizer.debug_mode and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # ... (logic to check clicks and set roll_result, action_triggered) ...
            mouse_pos = event.pos; clicked_face = None; # ... loop through debug_die_rects ...
            for face, rect in self.visualizer.debug_die_rects.items():
                if rect.collidepoint(mouse_pos): clicked_face = face; break
            if clicked_face is not None: roll_result = clicked_face; self.message = f"DEBUG: Set roll to {roll_result}"; action_triggered = True


        # --- Check for Normal Roll Trigger (Space key) ---
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            if not self.visualizer.debug_mode:
                roll_result = self.game.roll_special_die()
                self.message = f"Rolled {roll_result}"
                action_triggered = True
            # else: Debug mode ON, space does nothing for rolling

        # --- If an action was triggered, execute the move ---
        if action_triggered and roll_result is not None:
            self.last_roll = roll_result

            # --- Determine Target ---
            target_coord: Optional[Tuple[int, int]] = None
            # ... (logic using find_next_feature or trace_track_steps) ...
            if roll_result == C.STOP_SYMBOL: target_coord = self.game.find_next_feature_on_path(active_player)
            elif isinstance(roll_result, int): target_coord = self.game.trace_track_steps(active_player, roll_result)
            else: self.message = "Error: Invalid roll type."; return

            if target_coord:
                # --- Move Streetcar ---
                self.game.move_streetcar(active_player, target_coord) # Position is updated here

                # --- <<<< CHECK WIN CONDITION IMMEDIATELY AFTER MOVING >>>> ---
                if self.game.check_win_condition(active_player):
                    # Win condition met, game phase is now GAME_OVER
                    # The message is set inside check_win_condition or handled by GameOverState
                    # Visualizer state will update on the next frame via update_current_state_for_player
                    print(f"Win detected for Player {active_player.player_id}. State changed.")
                    # IMPORTANT: Do not proceed to end_player_turn if game is over
                else:
                    # --- No Win: End Turn normally ---
                    self.game.actions_taken_this_turn = C.MAX_PLAYER_ACTIONS
                    self.game.end_player_turn()
                    self.message = f"Moved to {target_coord}. Turn ended." # Update message for next frame
            else:
                 self.message = "Error: Could not determine target coordinate."
        # else: No action triggered or invalid roll


    def draw(self, screen):
        self.visualizer.draw_board(screen) # Draw board first
        # --- Draw Streetcars ---
        # (Part of Step 9 - Add basic circle for now)
        for player in self.game.players:
            if player.player_state == PlayerState.DRIVING and player.streetcar_position:
                 r, c = player.streetcar_position
                 if self.visualizer.game.board.is_valid_coordinate(r, c):
                     screen_x = C.BOARD_X_OFFSET + (c - C.PLAYABLE_COLS[0]) * C.TILE_SIZE + C.TILE_SIZE // 2
                     screen_y = C.BOARD_Y_OFFSET + (r - C.PLAYABLE_ROWS[0]) * C.TILE_SIZE + C.TILE_SIZE // 2
                     # Simple circle for now, color based on player ID
                     p_color = C.PLAYER_COLORS[player.player_id % len(C.PLAYER_COLORS)]
                     pygame.draw.circle(screen, p_color, (screen_x, screen_y), C.TILE_SIZE // 3)
                     pygame.draw.circle(screen, C.COLOR_BLACK, (screen_x, screen_y), C.TILE_SIZE // 3, 1)

        # --- Draw UI ---
        active_player = self.game.get_active_player()
        self.visualizer.draw_ui(screen, self.message, None, 0) # Use standard UI draw
        drive_info = f"Player {active_player.player_id} Driving. Roll: {self.last_roll if self.last_roll is not None else '-'}"
        # Corrected usage of the constant:
        self.visualizer.draw_text(screen, drive_info, C.UI_TEXT_X, C.SCREEN_HEIGHT - 60)
        self.visualizer.draw_text(screen, "Press [SPACE] to Roll & Move", C.UI_TEXT_X, C.SCREEN_HEIGHT - 35, size=18)
        roll_display_text = f"Last Roll: {self.last_roll if self.last_roll is not None else '--'}"
        self.visualizer.draw_text(screen, roll_display_text, C.UI_TEXT_X, C.UI_PANEL_Y + 150, size=20) # Adjust Y as needed


class GameOverState(GameState): # Placeholder - Can be improved
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
            print("Game Over. Click or keypress ignored (add restart?).")
            # Potentially add logic here to restart the game

    def draw(self, screen):
        self.visualizer.draw_board(screen) # Draw final board state
        # --- Draw Streetcars in final position ---
        for player in self.game.players:
             if player.streetcar_position: # Draw all streetcars, not just driving ones
                 r, c = player.streetcar_position
                 if self.visualizer.game.board.is_valid_coordinate(r, c):
                     screen_x = C.BOARD_X_OFFSET + (c - C.PLAYABLE_COLS[0]) * C.TILE_SIZE + C.TILE_SIZE // 2
                     screen_y = C.BOARD_Y_OFFSET + (r - C.PLAYABLE_ROWS[0]) * C.TILE_SIZE + C.TILE_SIZE // 2
                     p_color = C.PLAYER_COLORS[player.player_id % len(C.PLAYER_COLORS)]
                     pygame.draw.circle(screen, p_color, (screen_x, screen_y), C.TILE_SIZE // 3)
                     pygame.draw.circle(screen, C.COLOR_BLACK, (screen_x, screen_y), C.TILE_SIZE // 3, 1)

        # --- Draw Winner Text ---
        winner = self.game.winner # Use the winner attribute set in check_win_condition
        win_text = f"GAME OVER! Player {winner.player_id} Wins!" if winner else "GAME OVER! (No winner?)"

        # Draw text centered
        font_to_use = pygame.font.SysFont(None, 40)
        text_surface = font_to_use.render(win_text, True, C.COLOR_STOP)
        text_rect = text_surface.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2))
        # Optional: Add a background rect
        bg_rect = text_rect.inflate(20, 10)
        pygame.draw.rect(screen, C.COLOR_UI_BG, bg_rect, border_radius=5)
        pygame.draw.rect(screen, C.COLOR_BLACK, bg_rect, 2, border_radius=5)
        screen.blit(text_surface, text_rect)