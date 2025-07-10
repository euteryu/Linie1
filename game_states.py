# game_states.py

from __future__ import annotations
from typing import Optional, Dict, Any, List, TYPE_CHECKING
import pygame
import tkinter as tk
from tkinter import filedialog
import copy

if TYPE_CHECKING:
    from game_logic.game import Game
    from game_logic.tile import TileType

from game_logic.player import Player, HumanPlayer, AIPlayer
from game_logic.enums import GamePhase, PlayerState, Direction
from game_logic.commands import CombinedActionCommand
import constants as C

class GameState:
    """Abstract base class for different game phases/states."""
    def __init__(self, scene):
        # --- START OF FIX ---
        # The state is owned by a Scene, not a Visualizer.
        self.scene = scene
        self.game: 'Game' = scene.game
        # --- END OF FIX ---
        self.is_transient_state: bool = False

    def handle_event(self, event):
        raise NotImplementedError

    def update(self, dt):
        pass

    def draw(self, screen):
        raise NotImplementedError

    # --- FIX: This method is now obsolete and should be removed. ---
    # The UIManager's ButtonPanel now handles all these clicks directly.
    # def _handle_common_clicks(self, event) -> bool:
    #     ... (REMOVING THE ENTIRE METHOD) ...

    # These action methods are still useful as they are called by ButtonPanel via the current_state
    def save_game_action(self):
        if not self.scene.tk_root:
            self.set_message("Error: Tkinter not available.")
            return
        filepath = filedialog.asksaveasfilename(
            title="Save Game", defaultextension=".json",
            filetypes=[("Linie 1 Saves", "*.json"), ("All", "*.*")]
        )
        if filepath:
             if self.game.save_game(filepath): self.set_message("Game Saved.")
             else: self.set_message("Error Saving Game.")
        else: self.set_message("Save Cancelled.")

    def load_game_action(self):
        """
        Handles the file dialog and game loading process.
        """
        # --- START OF FIX ---
        # We perform a local import here to break the circular dependency at runtime.
        from game_logic.game import Game
        # --- END OF FIX ---

        if not self.scene.tk_root:
            self.set_message("Error: Tkinter not available.")
            return
            
        filepath = filedialog.askopenfilename(
             title="Load Game", filetypes=[("Linie 1 Saves", "*.json"), ("All", "*.*")]
        )
        if filepath:
            # We now correctly call the imported Game class
            loaded_game = Game.load_game(filepath, self.game.tile_types, self.game.mod_manager)
            if loaded_game:
                # Replace the game instance in the visualizer and the current state
                self.scene.game = loaded_game
                self.game = loaded_game
                # Link the newly loaded game back to the visualizer so it can request redraws
                self.game.visualizer = self.scene
                # Update the visualizer's state based on the loaded game's reality
                self.scene.update_current_state_for_player()
                self.set_message("Game Loaded.")
            else: 
                self.set_message("Error Loading Game.")
        else: 
            self.set_message("Load Cancelled.")

    def undo_action(self):
        if hasattr(self, 'staged_moves') and self.staged_moves:
            self.staged_moves = []
            self.set_message("Staging cleared.")
        elif self.game.undo_last_action():
            self.set_message("Action Undone.")
        else:
            self.set_message("Nothing to undo.")

    def redo_action(self):
        if self.game.redo_last_action(): self.set_message("Action Redone.")
        else: self.set_message("Nothing to redo.")

    def toggle_debug_action(self):
         self.scene.debug_mode = not self.scene.debug_mode
         mode_str = "ON" if self.scene.debug_mode else "OFF"
         self.set_message(f"Debug Mode {mode_str}")
         if hasattr(self, 'staged_moves'): self.staged_moves = []

    def toggle_heatmap_action(self):
        self.scene.show_ai_heatmap = not self.scene.show_ai_heatmap
        if self.scene.show_ai_heatmap:
            active_player = self.game.get_active_player()
            if isinstance(active_player, AIPlayer):
                ideal_plan = active_player.strategy._calculate_ideal_route(self.game, active_player)
                self.scene.heatmap_data = active_player.strategy._get_high_value_target_squares(self.game, active_player, ideal_plan)
                self.set_message(f"AI Heatmap ON ({len(self.scene.heatmap_data)} targets)")
            else:
                self.set_message("Heatmap only for AI players.")
                self.scene.heatmap_data = set()
        else:
            self.set_message("AI Heatmap OFF.")
            self.scene.heatmap_data = set()

    def set_message(self, msg: str):
        if hasattr(self, 'message'): self.message = msg
        else: print(f"State Warning: Cannot set message '{msg}'")

# --- Laying Track State ---
class LayingTrackState(GameState):
    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.staged_moves: List[Dict[str, Any]] = []
        self.move_in_progress: Optional[Dict[str, Any]] = None
        self.message = "Select a board square or a special hand tile."
        self.current_hand_rects: Dict[int, pygame.Rect] = {}

    def draw(self, screen):
        """
        This state has no special drawing needs. The main visualizer loop
        handles rendering the board, overlays, and UI panels.
        """
        pass

    def _reset_staging(self):
        self.staged_moves = []
        self.move_in_progress = None
        self.message = "Select a board square or a special hand tile."

    def undo_action(self):
        """
        Overrides the base undo action. Prioritizes clearing the staging area
        if it's active.
        """
        # --- NEW, SIMPLER LOGIC ---
        # This now correctly handles resetting the staging area if it's full,
        # or undoing a game action if it's empty.
        if self.staged_moves or self.move_in_progress:
            self._reset_staging() # Clear the local staging
            self.set_message("Staging cleared.")
        else:
            # Fall back to the base class implementation for regular undos
            super().undo_action()

    def handle_event(self, event):
        """Handles user input for the LayingTrackState."""
        active_player = self.game.get_active_player()
        if isinstance(active_player, AIPlayer):
            return

        # --- START OF FIX ---
        # The check for Save/Load/Undo/Redo button clicks is now entirely
        # handled by the UIManager and the ButtonPanel's own handle_event method.
        # This old, broken check that was causing the crash is now removed.
        # We only need to check if we need to reset staging, which is better
        # handled inside the undo_action method itself.
        #
        # The following block is now REMOVED:
        # if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        #     bp = self.scene.ui_manager.components[4] # This was brittle anyway
        #     if bp.save_rect.collidepoint(event.pos) or \
        #        ... (and so on)
        # --- END OF FIX ---

        if active_player.player_state != PlayerState.LAYING_TRACK:
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_mouse_down(event, active_player)
        elif event.type == pygame.KEYDOWN:
            self._handle_key_down(event, active_player)
            self._handle_key_down(event, active_player)

    # --- THE REST OF LayingTrackState REMAINS UNCHANGED ---
    # _handle_mouse_down, _handle_key_down, _validate_all_staged_moves,
    # _commit_staged_moves, and draw methods are correct.
    # I will omit them for conciseness as requested.
    def _handle_mouse_down(self, event, active_player):
        if event.button != 1: return
        mouse_pos = event.pos
        for index, rect in self.current_hand_rects.items():
            if rect.collidepoint(mouse_pos):
                tile_to_use = active_player.hand[index]
                if self.game.mod_manager.on_hand_tile_clicked(self.game, active_player, tile_to_use):
                    return
                if self.move_in_progress and self.move_in_progress.get('coord'):
                    self.scene.sounds.play('click_hand')
                    if any(m['hand_index'] == index for m in self.staged_moves):
                        self.message = "Tile already staged."
                    else:
                        self.move_in_progress['hand_index'] = index
                        self.move_in_progress['tile_type'] = tile_to_use
                        self.move_in_progress['orientation'] = 0
                        self.message = f"Selected tile. [R] Rotate, [S] Stage."
                    self._validate_all_staged_moves()
                else:
                    self.message = "Select a board square before clicking a normal tile."
                return
        if C.BOARD_X_OFFSET <= mouse_pos[0] < C.BOARD_X_OFFSET + C.BOARD_DRAW_WIDTH and \
           C.BOARD_Y_OFFSET <= mouse_pos[1] < C.BOARD_Y_OFFSET + C.BOARD_DRAW_HEIGHT:
            self.scene.sounds.play('click')
            grid_r, grid_c = (mouse_pos[1] - C.BOARD_Y_OFFSET) // C.TILE_SIZE + C.PLAYABLE_ROWS[0], \
                             (mouse_pos[0] - C.BOARD_X_OFFSET) // C.TILE_SIZE + C.PLAYABLE_COLS[0]
            self.move_in_progress = None
            self._validate_all_staged_moves()
            if not self.game.board.is_valid_coordinate(grid_r, grid_c): self.message = "Cannot select outside grid."; return
            if self.game.board.get_building_at(grid_r, grid_c): self.message = "Cannot place on a building."; return
            if any(m['coord'] == (grid_r, grid_c) for m in self.staged_moves): self.message = "Square already staged."; return
            target_tile = self.game.board.get_tile(grid_r, grid_c)
            if target_tile and (target_tile.is_terminal or not target_tile.tile_type.is_swappable): self.message = "Tile is permanent."; return
            self.move_in_progress = {'coord': (grid_r, grid_c)}
            self.message = f"Selected {self.move_in_progress['coord']}. Click a hand tile."
            return

    def _handle_key_down(self, event, active_player):
        """Handles keyboard input for the LayingTrackState."""
        mods = pygame.key.get_mods()
        if event.key == pygame.K_z and (mods & pygame.KMOD_CTRL):
            self.undo_action()
            return
        if event.key == pygame.K_y and (mods & pygame.KMOD_CTRL):
            self.redo_action()
            return
            
        if event.key == pygame.K_r:
            if self.move_in_progress and 'orientation' in self.move_in_progress:
                self.move_in_progress['orientation'] = (self.move_in_progress['orientation'] + 90) % 360
            elif self.staged_moves:
                self.staged_moves[-1]['orientation'] = (self.staged_moves[-1]['orientation'] + 90) % 360
            self._validate_all_staged_moves()
            self.message = "Rotated selection."

        # --- START OF FIX ---
        # Changed K_ESCAPE to K_BACKSPACE for canceling staging
        elif event.key == pygame.K_BACKSPACE:
            if self.move_in_progress:
                self.move_in_progress = None
                self.message = "Selection cleared."
            elif self.staged_moves:
                self.staged_moves = []
                self.message = "All staged moves cleared."
        # --- END OF FIX ---
        
        elif event.key == pygame.K_s:
            # --- FIX: Use a command to stage a move ---
            if self.move_in_progress and 'tile_type' in self.move_in_progress:
                if len(self.staged_moves) + self.game.actions_taken_this_turn >= C.MAX_PLAYER_ACTIONS:
                    self.message = "Cannot stage more moves."
                    return
                # Finalize the move data before creating the command
                self.move_in_progress['action_type'] = 'exchange' if self.game.board.get_tile(*self.move_in_progress['coord']) else 'place'
                command = StageMoveCommand(self.game, self, self.move_in_progress)
                self.game.command_history.execute_command(command)
            else:
                self.message = "Nothing to stage."
                
        elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
            self._commit_staged_moves(active_player)

    def _validate_all_staged_moves(self):
        """
        Checks the validity of all currently staged moves and any move
        that is in progress, updating their 'is_valid' flag.
        """
        player = self.game.get_active_player()
        all_hypothetical_moves = self.staged_moves[:]
        if self.move_in_progress and 'tile_type' in self.move_in_progress:
            all_hypothetical_moves.append(self.move_in_progress)

        for i, move_to_validate in enumerate(all_hypothetical_moves):
            # Create a list of all *other* staged moves to check against.
            other_moves = all_hypothetical_moves[:i] + all_hypothetical_moves[i+1:]
            
            coord_r, coord_c = move_to_validate['coord']
            # Determine if the action is a place or an exchange.
            action = 'exchange' if self.game.board.get_tile(coord_r, coord_c) else 'place'
            
            is_valid = False
            if 'tile_type' in move_to_validate:
                orientation = move_to_validate.get('orientation', 0)
                
                # --- START OF FIX ---
                # Call the validation methods on the rule_engine, not the game object.
                if action == 'place':
                    is_valid, _ = self.game.rule_engine.check_placement_validity(
                        self.game, move_to_validate['tile_type'], orientation, coord_r, coord_c, hypothetical_moves=other_moves
                    )
                else: # action == 'exchange'
                    is_valid, _ = self.game.rule_engine.check_exchange_validity(
                        self.game, player, move_to_validate['tile_type'], orientation, coord_r, coord_c, hypothetical_moves=other_moves
                    )
                # --- END OF FIX ---

            move_to_validate['is_valid'] = is_valid

    def _commit_staged_moves(self, player):
        """Attempts to commit all staged moves as a single atomic command."""
        if self.move_in_progress:
            self.message = "A move is being built. [S] to stage or [ESC] to clear."
            return
        
        if self.staged_moves:
            self._validate_all_staged_moves()
            if all(move.get('is_valid', False) for move in self.staged_moves):
                command = CombinedActionCommand(self.game, player, self.staged_moves)
                if self.game.command_history.execute_command(command):
                    self.scene.sounds.play('commit') # Use self.scene
                    
                    # --- START OF FIX ---
                    # Reset the staging area IMMEDIATELY after a successful commit.
                    # This prevents the highlights from being drawn on the next frame.
                    self._reset_staging()
                    # --- END OF FIX ---

                    if self.game.actions_taken_this_turn >= C.MAX_PLAYER_ACTIONS:
                        if not self.game.confirm_turn():
                             self.message = "Error confirming turn."
                else:
                    self.message = "Commit failed: Action limit would be exceeded."
            else:
                self.message = "Cannot commit: one or more moves are invalid (red)."
                self.scene.sounds.play('error') # Use self.scene
        else:
            # Forfeit logic
            if self.game.confirm_turn():
                self._reset_staging()
            else:
                self.message = "You have possible moves; you must play."
                self.scene.sounds.play('error') # Use self.scene

    def draw(self, screen):
        # We now call draw_board and draw_overlays from the main visualizer loop
        # This draw method is now only for things specific to this state, but since
        # overlays cover that, this method can be empty or simplified.
        # For now, let's keep it as a placeholder to show the flow.
        pass

# --- Driving State ---
class DrivingState(GameState):
    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.message = "Roll die or select debug roll."
        self.last_roll: Optional[Any] = None

    def handle_event(self, event):
        # The common clicks (Save, Load, etc.) are already handled by the UIManager now.
        try:
            active_player = self.game.get_active_player()
            if active_player.player_state != PlayerState.DRIVING: return
        except IndexError: return

        roll_result: Optional[Any] = None
        if self.scene.debug_mode and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for face, rect in self.scene.debug_die_rects.items():
                if rect.collidepoint(event.pos):
                    self.scene.sounds.play('dice_roll')
                    roll_result = face; break
        elif not self.scene.debug_mode and event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self.scene.sounds.play('dice_roll')
            # --- START OF FIX ---
            roll_result = self.game.deck_manager.roll_special_die()
            # --- END OF FIX ---
        
        if roll_result is not None:
            self.last_roll = roll_result
            self.message = f"Rolled {roll_result}..."
            if not self.game.attempt_driving_move(active_player, roll_result):
                self.scene.sounds.play('error')
                self.message = "Driving move failed to execute."
            else:
                self.scene.sounds.play('train_move')

    def draw(self, screen):
        """
        Draws elements specific ONLY to the driving state, which are now handled
        by the UI panels (like debug die). This can be empty.
        """
        pass


# --- Game Over State ---
class GameOverState(GameState):
    def __init__(self, visualizer):
        super().__init__(visualizer)
        winner = self.game.winner
        self.message = f"GAME OVER! Player {winner.player_id} Wins!" if winner else "GAME OVER! DRAW!"

    def handle_event(self, event):
        # No special event handling, common clicks are handled by UI manager
        pass

    def draw(self, screen):
        # ... (implementation is correct)
        from rendering_utils import get_font
        # Draw a big "Game Over" message in the center of the screen
        font = get_font(50)
        text_surface = font.render(self.message, True, C.COLOR_STOP)
        text_rect = text_surface.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2))
        
        bg_rect = text_rect.inflate(40, 20)
        pygame.draw.rect(screen, C.COLOR_UI_BG, bg_rect, border_radius=10)
        pygame.draw.rect(screen, C.COLOR_BLACK, bg_rect, 3, border_radius=10)
        
        screen.blit(text_surface, text_rect)