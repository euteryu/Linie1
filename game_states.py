# game_states.py
from typing import Optional, TypeVar, Dict, Any
import pygame
import tkinter as tk
from tkinter import filedialog

# --- Relative Imports from Game Logic ---
# Import main Game class and specific classes if needed for type hints
from game_logic.game import Game
from game_logic.player import Player
from game_logic.tile import TileType, PlacedTile
from game_logic.enums import GamePhase, PlayerState, Direction
# Import Command classes if needed for type hints, though usually not
# from game_logic.commands import PlaceTileCommand, ExchangeTileCommand

# --- Constants ---
import constants as C # Use alias

# --- Base Game State ---

class GameState:
    """Abstract base class for different game phases/states."""
    def __init__(self, visualizer):
        self.visualizer = visualizer
        # Ensure game reference is correctly typed if possible
        self.game: Game = visualizer.game # Get game reference

    def handle_event(self, event):
        """Handles Pygame events specific to this state."""
        raise NotImplementedError

    def update(self, dt):
        """Updates state logic over time (e.g., animations)."""
        pass # Not used currently

    def draw(self, screen):
        """Draws the game screen specific to this state."""
        raise NotImplementedError

    # --- Common Event Handling for Buttons ---
    def _handle_common_clicks(self, event) -> bool:
        """
        Handles clicks common to most states: Save, Load, Undo, Redo.
        Returns True if the event was handled, False otherwise.
        """
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False # Only handle left mouse clicks

        mouse_pos = event.pos
        handled = False

        # Check standard buttons
        if self.visualizer.save_button_rect.collidepoint(mouse_pos):
            self.save_game_action()
            handled = True
        elif self.visualizer.load_button_rect.collidepoint(mouse_pos):
            self.load_game_action()
            handled = True
        elif self.visualizer.undo_button_rect.collidepoint(mouse_pos):
            self.undo_action() # New method for undo button click
            handled = True
        elif self.visualizer.redo_button_rect.collidepoint(mouse_pos):
            self.redo_action() # New method for redo button click
            handled = True
        elif self.visualizer.debug_toggle_button_rect.collidepoint(mouse_pos):
            self.toggle_debug_action() # New method for debug toggle
            handled = True

        return handled

    # --- Action Methods Called by Click Handlers ---

    def save_game_action(self):
        """Opens file dialog and calls game save."""
        # (Implementation remains the same, using filedialog)
        if not self.visualizer.tk_root: print("Error: Tkinter needed."); return
        filepath = filedialog.asksaveasfilename( # ... options ...
            title="Save Game", defaultextension=".json",
            filetypes=[("Linie 1 Saves", "*.json"), ("All", "*.*")]
        )
        if filepath:
             if self.game.save_game(filepath): self.set_message("Game Saved.")
             else: self.set_message("Error Saving Game.")
        else: self.set_message("Save Cancelled.")


    def load_game_action(self):
        """Opens file dialog and calls game load."""
        # (Implementation remains the same, using filedialog)
        if not self.visualizer.tk_root: print("Error: Tkinter needed."); return
        filepath = filedialog.askopenfilename( # ... options ...
             title="Load Game",
             filetypes=[("Linie 1 Saves", "*.json"), ("All", "*.*")]
        )
        if filepath:
            # Pass existing tile type definitions to load_game
            loaded_game = Game.load_game(filepath, self.game.tile_types)
            if loaded_game:
                # CRITICAL: Replace game instance in visualizer & current state
                self.visualizer.game = loaded_game
                self.game = loaded_game
                # Let visualizer update state based on loaded game phase/player
                self.visualizer.update_current_state_for_player()
                # Reset any local UI state in the *new* state object if needed
                # (The current state object might be replaced)
                # self.set_message("Game Loaded.") # Message set by new state?
            else: self.set_message("Error Loading Game.")
        else: self.set_message("Load Cancelled.")

    def undo_action(self):
        """Calls the game's undo logic."""
        if self.game.undo_last_action(): self.set_message("Action Undone.")
        else: self.set_message("Nothing to undo.")

    def redo_action(self):
        """Calls the game's redo logic."""
        if self.game.redo_last_action(): self.set_message("Action Redone.")
        else: self.set_message("Nothing to redo.")

    def toggle_debug_action(self):
         """Toggles debug mode and updates messages."""
         self.visualizer.debug_mode = not self.visualizer.debug_mode
         mode_str = "ON" if self.visualizer.debug_mode else "OFF"
         self.set_message(f"Debug Mode {mode_str}")
         # Clear selections when toggling mode
         if hasattr(self, 'selected_tile_index'): self.selected_tile_index = None
         if hasattr(self, 'debug_selected_tile_type'): self.debug_selected_tile_type = None

    # Helper to set message consistently (can be overridden by states)
    def set_message(self, msg: str):
        """Sets the message attribute if it exists."""
        if hasattr(self, 'message'):
            self.message = msg
        else: # Should not happen if states declare message attribute
             print(f"State Warning: Cannot set message '{msg}'")


# --- Laying Track State ---

class LayingTrackState(GameState):
    """Handles input and drawing when players are placing tiles."""
    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.selected_tile_index: Optional[int] = None
        self.debug_selected_tile_type: Optional[TileType] = None
        self.current_orientation = 0
        self.message = "Select tile and place/exchange."
        # Rects for hand tiles, updated during draw
        self.current_hand_rects: Dict[int, pygame.Rect] = {}

    def get_selected_tile_for_preview(self) -> Optional[TileType]:
        """ Gets the tile type to show in preview/UI based on mode. """
        # (Implementation remains the same)
        if self.visualizer.debug_mode and self.debug_selected_tile_type: return self.debug_selected_tile_type # ... rest ...
        elif not self.visualizer.debug_mode and self.selected_tile_index is not None:
            player = self.game.get_active_player(); # ... null checks ...
            if player and 0 <= self.selected_tile_index < len(player.hand): return player.hand[self.selected_tile_index]
        return None

    def handle_event(self, event):
        # --- Handle Common Buttons ---
        if self._handle_common_clicks(event): return

        # --- State-Specific Handling ---
        try: active_player: Player = self.game.get_active_player()
        except IndexError: return
        if active_player.player_state != PlayerState.LAYING_TRACK: return

        # --- Mouse Input ---
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Add print to see if MOUSE events are overriding KEY events somehow
            # print(f"LayingTrackState MouseDown: {event.button}")
            self._handle_mouse_down(event, active_player)

        # --- Keyboard Input ---
        elif event.type == pygame.KEYDOWN:
            # --- DEBUG PRINT ---
            print(f"LayingTrackState KeyDown: Key={event.key}, Name={pygame.key.name(event.key)}")
            self._handle_key_down(event, active_player)

    def _handle_mouse_down(self, event, active_player):
        """ Handles mouse button down events for LayingTrackState. """
        mouse_pos = event.pos

        # --- Debug Palette Click ---
        if self.visualizer.debug_mode:
            clicked_palette = False
            for index, rect in self.visualizer.debug_tile_rects.items():
                if rect.collidepoint(mouse_pos) and event.button == 1:
                    selected = self.visualizer.debug_tile_types[index]
                    self.debug_selected_tile_type = selected
                    self.selected_tile_index = None
                    self.current_orientation = 0
                    self.message = f"Debug Select: {selected.name}"
                    clicked_palette = True
                    break
            if clicked_palette: return # Consume event

        # --- Hand Click (Normal Mode) ---
        elif not self.visualizer.debug_mode:
            clicked_hand = False
            for index, rect in self.current_hand_rects.items():
                if rect.collidepoint(mouse_pos) and event.button == 1:
                    if self.selected_tile_index != index:
                         self.selected_tile_index = index
                         self.debug_selected_tile_type = None
                         self.current_orientation = 0
                         sel_type = self.get_selected_tile_for_preview()
                         self.message = f"Selected: {sel_type.name}" if sel_type else "Error"
                    clicked_hand = True
                    break
            if clicked_hand: return # Consume event

        # --- Board Click ---
        if C.BOARD_X_OFFSET <= mouse_pos[0] < C.BOARD_X_OFFSET + C.BOARD_DRAW_WIDTH and \
           C.BOARD_Y_OFFSET <= mouse_pos[1] < C.BOARD_Y_OFFSET + C.BOARD_DRAW_HEIGHT:
            grid_col = (mouse_pos[0] - C.BOARD_X_OFFSET) // C.TILE_SIZE + C.PLAYABLE_COLS[0]
            grid_row = (mouse_pos[1] - C.BOARD_Y_OFFSET) // C.TILE_SIZE + C.PLAYABLE_ROWS[0]

            if event.button == 1: # Left Click -> Attempt Action
                self._attempt_board_action(active_player, grid_row, grid_col)
            elif event.button == 3: # Right Click -> Rotate
                self._rotate_selection()


    def _handle_key_down(self, event, active_player):
        """ Handles key down events for LayingTrackState. """
        # --- DEBUG PRINT ---
        # print(f"  _handle_key_down received: {pygame.key.name(event.key)}")

        if event.key == pygame.K_r: # Rotate
            # print("  'R' key detected, calling _rotate_selection...") # DEBUG
            self._rotate_selection()
            # return # Optional: Consume event if needed

        # ... (handle Enter, Ctrl+Z/Y) ...
        mods = pygame.key.get_mods()
        if event.key == pygame.K_z and (mods & pygame.KMOD_CTRL):
             self.undo_action()
        elif event.key == pygame.K_y and (mods & pygame.KMOD_CTRL):
             self.redo_action()
        elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
             if not self.visualizer.debug_mode:
                  self._confirm_turn_action()


    def _rotate_selection(self):
        """ Rotates the current tile selection. """
        self.current_orientation = (self.current_orientation + 90) % 360
        selected_type = self.get_selected_tile_for_preview()
        msg = f"Orientation: {self.current_orientation}°"
        if selected_type: msg += f" for {selected_type.name}"
        self.message = msg

        # --- DEBUG PRINT ---
        print(f"  Rotated preview to {self.current_orientation}. Message: '{self.message}'")

    def _attempt_board_action(self, player, row, col):
        """ Attempts Place or Exchange based on target and mode. """
        tile_to_use = self.get_selected_tile_for_preview()
        if not tile_to_use:
            self.message = "Select a tile first."; return

        if not self.game.board.is_valid_coordinate(row, col):
             self.message = "Clicked outside valid grid."; return

        target_tile = self.game.board.get_tile(row, col)
        success = False
        action_type = ""

        if self.visualizer.debug_mode:
            # --- DEBUG ACTION ---
            # Direct board manipulation, bypass command history for simplicity?
            # OR create debug commands if undo needed. Let's do direct manipulation.
            if target_tile is None: # Try Place
                 if self.game.board.is_playable_coordinate(row, col):
                    valid, msg = self.game.check_placement_validity(
                        tile_to_use, self.current_orientation, row, col)
                    if valid:
                         p_tile = PlacedTile(tile_to_use, self.current_orientation)
                         self.game.board.set_tile(row, col, p_tile)
                         self.game._check_and_place_stop_sign(p_tile, row, col)
                         self.message = f"DEBUG: Placed {tile_to_use.name}."
                    else: self.message = f"DEBUG: Invalid place. {msg}"
                 else: self.message = "DEBUG: Cannot place on border."
            else: # Try Exchange (Simplified)
                if self.game.board.is_playable_coordinate(row, col):
                     valid, msg = self.game.check_exchange_validity(
                         player, tile_to_use, self.current_orientation, row, col)
                     if valid: # Use basic check for now
                         new_p_tile = PlacedTile(tile_to_use, self.current_orientation)
                         self.game.board.set_tile(row, col, new_p_tile)
                         self.message = f"DEBUG: Exchanged for {tile_to_use.name}."
                     else: self.message = f"DEBUG: Invalid Exch. {msg}"
                else: self.message = "DEBUG: Cannot exchange border."

        else:
            # --- NORMAL ACTION (uses Commands) ---
            if target_tile is None: # Attempt PLACE
                if self.game.board.is_playable_coordinate(row, col):
                     success = self.game.attempt_place_tile(
                         player, tile_to_use, self.current_orientation, row, col)
                     action_type = "Place"
                else: self.message = "Cannot place tile here."
            else: # Attempt EXCHANGE
                if self.game.board.is_playable_coordinate(row, col):
                     success = self.game.attempt_exchange_tile(
                         player, tile_to_use, self.current_orientation, row, col)
                     action_type = "Exchange"
                else: self.message = "Cannot exchange terminal/border."

            # Update UI message based on command result
            if action_type:
                if success:
                     acts = self.game.actions_taken_this_turn
                     self.message = f"{action_type} OK ({acts}/{C.MAX_PLAYER_ACTIONS})"
                     self.selected_tile_index = None # Clear selection
                     self.current_orientation = 0
                else:
                     self.message = f"{action_type} Failed."


    def _confirm_turn_action(self):
        """ Attempts to confirm the turn via the game logic. """
        # Check action count before calling confirm
        if self.game.actions_taken_this_turn < C.MAX_PLAYER_ACTIONS:
             # Optional: Allow early end if > 0? For now, require max.
             self.message = f"Need {C.MAX_PLAYER_ACTIONS} actions to confirm."
             return

        if self.game.confirm_turn():
            # Success! Turn advanced. Message will be updated by new state/turn.
            # Reset local UI state for the *next* turn (though state might change)
            self.message = "Turn Confirmed." # Temp message shown briefly
            self.selected_tile_index = None
            self.debug_selected_tile_type = None
            self.current_orientation = 0
        else:
            # Should not happen if action check above is correct, but safety belt.
             self.message = "Cannot confirm turn now."


    def draw(self, screen):
        # Draw board, then Hand OR Debug Panel
        self.visualizer.draw_board(screen)
        if self.visualizer.debug_mode:
            self.visualizer.draw_debug_panel(
                screen, self.debug_selected_tile_type
            )
            self.current_hand_rects = {} # Clear hand rects
        else:
            player = self.game.get_active_player()
            if player:
                 self.current_hand_rects = self.visualizer.draw_hand(
                     screen, player
                 )
            else: self.current_hand_rects = {}

        # Draw UI, including confirm prompt if applicable
        selected_type = self.get_selected_tile_for_preview()
        confirm_prompt = ""
        # Show confirm prompt only if max actions taken and not debug
        if not self.visualizer.debug_mode and \
           self.game.actions_taken_this_turn >= C.MAX_PLAYER_ACTIONS:
             confirm_prompt = " [ENTER] to Confirm Turn."

        self.visualizer.draw_ui(screen, self.message + confirm_prompt,
                               selected_type, self.current_orientation)
        # Draw Preview
        self.visualizer.draw_preview(screen, selected_type,
                                     self.current_orientation)

# --- Driving State ---

class DrivingState(GameState):
    """Handles input and drawing when players are driving trams."""
    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.message = "Roll die or select debug roll."
        self.last_roll: Optional[Any] = None
        self.current_move_path: Optional[List[Tuple[int, int]]] = None # Store path taken this move

    def handle_event(self, event):
        # --- Handle Save/Load/Debug Toggle first ---
        if self._handle_common_clicks(event): return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
             if self.visualizer.debug_toggle_button_rect.collidepoint(event.pos):
                 self.visualizer.debug_mode = not self.visualizer.debug_mode
                 self.message = f"Debug Mode {'ON' if self.visualizer.debug_mode else 'OFF'}"
                 return

        active_player = self.game.get_active_player()
        if active_player.player_state != PlayerState.DRIVING: return

        roll_result: Optional[Any] = None
        action_triggered = False # Reset per event check

        # --- Check for Debug Die Click ---
        if self.visualizer.debug_mode and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos; clicked_face = None
            for face, rect in self.visualizer.debug_die_rects.items():
                if rect.collidepoint(mouse_pos):
                    # --- DEBUG PRINT ---
                    print(f"*** DBG: Debug die click detected! Face: {face}, Rect: {rect}")
                    clicked_face = face; break
            if clicked_face is not None:
                roll_result = clicked_face
                self.message = f"DEBUG: Set roll to {roll_result}"
                action_triggered = True


        # --- Check for Normal Roll Trigger (Space key) ---
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            if not self.visualizer.debug_mode:
                # --- DEBUG PRINT ---
                print("*** DBG: Space pressed for normal roll.")
                roll_result = self.game.roll_special_die()
                self.message = f"Rolled {roll_result}"
                action_triggered = True
            else:
                self.message = "DEBUG: Press die face or disable debug."


        # --- If an action was triggered, execute the move ---
        if action_triggered:
            # --- DEBUG PRINT ---
            print(f"*** DBG: Action triggered. Roll result: {roll_result}")
            if roll_result is not None:
                self.last_roll = roll_result # Store for display

                # --- Determine Target ---
                target_coord: Optional[Tuple[int, int]] = None
                # --- DEBUG PRINT ---
                print("*** DBG: Calculating target coordinate...")
                if roll_result == C.STOP_SYMBOL:
                     target_coord = self.game.find_next_feature_on_path(active_player)
                     # --- DEBUG PRINT ---
                     print(f"*** DBG: Target (H): {target_coord}")
                elif isinstance(roll_result, int):
                     target_coord = self.game.trace_track_steps(active_player, roll_result)
                     # --- DEBUG PRINT ---
                     print(f"*** DBG: Target ({roll_result}): {target_coord}")
                else:
                     print(f"Error: Invalid roll result type {roll_result}")
                     self.message = "Error: Invalid roll type."; return # Exit if roll invalid

                if target_coord:
                     # --- DEBUG PRINT ---
                     print(f"*** DBG: Moving streetcar to {target_coord}...")
                     self.game.move_streetcar(active_player, target_coord) # Position updated here

                     # --- Check Win Condition ---
                     # --- DEBUG PRINT ---
                     print("*** DBG: Checking win condition...")
                     if self.game.check_win_condition(active_player):
                         self.message = f"Player {active_player.player_id} WINS!"
                         # --- DEBUG PRINT ---
                         print(f"*** DBG: Win detected for P{active_player.player_id}. Turn should not advance.")
                         # DO NOT CALL END TURN HERE
                     else:
                         # --- No Win: End Turn normally ---
                         # --- DEBUG PRINT ---
                         print(f"*** DBG: No win detected for P{active_player.player_id}. Ending turn...")
                         self.game.actions_taken_this_turn = C.MAX_PLAYER_ACTIONS
                         self.game.end_player_turn() # Proceeds to next player
                         self.message = f"Moved to {target_coord}. Turn ended."
                         # --- DEBUG PRINT ---
                         print("*** DBG: end_player_turn called.")
                else:
                     self.message = "Error: Could not determine target coordinate."
                     # --- DEBUG PRINT ---
                     print("*** DBG: Error: Target coordinate calculation failed.")
            else:
                 self.message = "Error: Action triggered but no valid roll result."
                 # --- DEBUG PRINT ---
                 print("*** DBG: Error: Action triggered but roll_result was None.")
        # else: No action triggered this frame (e.g., just mouse movement)

    # draw method is likely empty, but visualizer needs access to current_move_path
    def draw(self, screen):
        # Board/Streetcars drawn by visualizer.draw_board
        self.visualizer.draw_board(screen)

        # Draw UI - Driving state doesn't have 'selected tile'
        self.visualizer.draw_ui(screen, self.message, None, 0)

        # Draw last roll info separately if needed (optional)
        roll_info_y = C.DEBUG_DIE_AREA_Y - 30 # Position near debug die
        roll_display = f"Last Roll: {self.last_roll if self.last_roll is not None else '--'}"
        self.visualizer.draw_text(screen, roll_display, C.UI_TEXT_X,
                                  roll_info_y, size=20)


# --- Game Over State ---

class GameOverState(GameState):
    """Displays the game over message and winner."""
    def __init__(self, visualizer):
        super().__init__(visualizer)
        winner = self.game.winner
        self.message = f"GAME OVER! Player {winner.player_id} Wins!" if winner else "GAME OVER!"

    def handle_event(self, event):
        # Allow Save/Load/Debug Toggle even on game over screen
        if self._handle_common_clicks(event): return

        # Any other click/key does nothing (or could trigger restart?)
        if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
            print("Game Over. Input ignored.")

    def draw(self, screen):
        # Draw final board state
        self.visualizer.draw_board(screen)
        # Draw standard UI panel (buttons etc.)
        self.visualizer.draw_ui(screen, self.message, None, 0)

        # --- Draw Winner Text Centered ---
        try:
             font_to_use = pygame.font.SysFont(None, 40)
        except: font_to_use = pygame.font.Font(None, 40)
        text_surface = font_to_use.render(self.message, True, C.COLOR_STOP)
        text_rect = text_surface.get_rect(
            center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2)
        )
        # Optional: Background rect
        bg_rect = text_rect.inflate(20, 10)
        pygame.draw.rect(screen, C.COLOR_UI_BG, bg_rect, border_radius=5)
        pygame.draw.rect(screen, C.COLOR_BLACK, bg_rect, 2, border_radius=5)
        screen.blit(text_surface, text_rect)