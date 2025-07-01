# game_states.py
from typing import Optional, Dict, Any, List
import pygame
import tkinter as tk
from tkinter import filedialog
import copy

# --- Relative Imports from Game Logic ---
from game_logic.game import Game
from game_logic.player import Player, HumanPlayer, AIPlayer
from game_logic.tile import TileType, PlacedTile
from game_logic.enums import GamePhase, PlayerState, Direction
from game_logic.commands import CombinedActionCommand # Make sure to create this new command

# --- Constants ---
import constants as C

# --- Base Game State ---

class GameState:
    """Abstract base class for different game phases/states."""
    def __init__(self, visualizer):
        self.visualizer = visualizer
        self.game: Game = visualizer.game

    def handle_event(self, event):
        raise NotImplementedError

    def update(self, dt):
        pass

    def draw(self, screen):
        raise NotImplementedError

    def _handle_common_clicks(self, event) -> bool:
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False

        mouse_pos = event.pos
        handled = False
        if self.visualizer.save_button_rect.collidepoint(mouse_pos):
            self.save_game_action()
            handled = True
        elif self.visualizer.load_button_rect.collidepoint(mouse_pos):
            self.load_game_action()
            handled = True
        elif self.visualizer.undo_button_rect.collidepoint(mouse_pos):
            self.undo_action()
            handled = True
        elif self.visualizer.redo_button_rect.collidepoint(mouse_pos):
            self.redo_action()
            handled = True
        elif self.visualizer.debug_toggle_button_rect.collidepoint(mouse_pos):
            self.toggle_debug_action()
            handled = True
        return handled

    def save_game_action(self):
        if not self.visualizer.tk_root: print("Error: Tkinter needed."); return
        filepath = filedialog.asksaveasfilename(
            title="Save Game", defaultextension=".json",
            filetypes=[("Linie 1 Saves", "*.json"), ("All", "*.*")]
        )
        if filepath:
             if self.game.save_game(filepath): self.set_message("Game Saved.")
             else: self.set_message("Error Saving Game.")
        else: self.set_message("Save Cancelled.")

    def load_game_action(self):
        if not self.visualizer.tk_root: print("Error: Tkinter needed."); return
        filepath = filedialog.askopenfilename(
             title="Load Game", filetypes=[("Linie 1 Saves", "*.json"), ("All", "*.*")]
        )
        if filepath:
            loaded_game = Game.load_game(filepath, self.game.tile_types)
            if loaded_game:
                self.visualizer.game = loaded_game
                self.game = loaded_game
                self.visualizer.update_current_state_for_player()
            else: self.set_message("Error Loading Game.")
        else: self.set_message("Load Cancelled.")

    def undo_action(self):
        # In the new flow, undo should clear staged moves first.
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
         self.visualizer.debug_mode = not self.visualizer.debug_mode
         mode_str = "ON" if self.visualizer.debug_mode else "OFF"
         self.set_message(f"Debug Mode {mode_str}")
         if hasattr(self, 'staged_moves'): self.staged_moves = []

    def set_message(self, msg: str):
        if hasattr(self, 'message'): self.message = msg
        else: print(f"State Warning: Cannot set message '{msg}'")

# --- Laying Track State ---

class LayingTrackState(GameState):
    """Handles input and drawing for the staging user flow."""
    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.staged_moves: List[Dict[str, Any]] = []
        self.move_in_progress: Optional[Dict[str, Any]] = None
        self.message = "Select an interactable board square."
        self.current_hand_rects: Dict[int, pygame.Rect] = {}
        # The is_committing flag is REMOVED.

    def _reset_staging(self):
        """Helper to clear all staging attributes."""
        self.staged_moves = []
        self.move_in_progress = None
        self.message = "Select an interactable board square."

    def handle_event(self, event):
        active_player: Player = self.game.get_active_player()
        if isinstance(active_player, AIPlayer):
            self.message = f"Waiting for AI Player {active_player.player_id}..."; return

        if self._handle_common_clicks(event):
             if self.staged_moves or self.move_in_progress: self._reset_staging()
             return

        if active_player.player_state != PlayerState.LAYING_TRACK: return

        if event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_mouse_down(event, active_player)
        elif event.type == pygame.KEYDOWN:
            self._handle_key_down(event, active_player)

    def _handle_mouse_down(self, event, active_player):
        # This method's logic is correct and does not need to change.
        mouse_pos = event.pos
        if (C.BOARD_X_OFFSET <= mouse_pos[0] < C.BOARD_X_OFFSET + C.BOARD_DRAW_WIDTH and
            C.BOARD_Y_OFFSET <= mouse_pos[1] < C.BOARD_Y_OFFSET + C.BOARD_DRAW_HEIGHT):
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
        if self.move_in_progress and self.move_in_progress.get('coord'):
            for index, rect in self.current_hand_rects.items():
                if rect.collidepoint(mouse_pos) and event.button == 1:
                    if any(m['hand_index'] == index for m in self.staged_moves): self.message = "Tile already staged."; return
                    if self.move_in_progress.get('hand_index') == index: self.move_in_progress.pop('hand_index', None); self.move_in_progress.pop('tile_type', None); self.message = f"Deselected hand tile."
                    else: self.move_in_progress['hand_index'] = index; self.move_in_progress['tile_type'] = active_player.hand[index]; self.move_in_progress['orientation'] = 0; self.message = f"Selected hand tile. [R] Rotate, [S] Stage."
                    self._validate_all_staged_moves(); return

    def _handle_key_down(self, event, active_player):
        # This method's logic is correct and does not need to change.
        mods = pygame.key.get_mods()
        if event.key == pygame.K_z and (mods & pygame.KMOD_CTRL): self.undo_action(); return
        if event.key == pygame.K_y and (mods & pygame.KMOD_CTRL): self.redo_action(); return
        if event.key == pygame.K_r:
            if self.move_in_progress and 'orientation' in self.move_in_progress: self.move_in_progress['orientation'] = (self.move_in_progress['orientation'] + 90) % 360
            elif self.staged_moves: self.staged_moves[-1]['orientation'] = (self.staged_moves[-1]['orientation'] + 90) % 360
            self._validate_all_staged_moves(); self.message = "Rotated selection."
        elif event.key == pygame.K_ESCAPE:
            if self.move_in_progress: self.move_in_progress = None; self.message = "Selection cleared."
            else: self.staged_moves = []; self.message = "All staged moves cleared."
        elif event.key == pygame.K_s:
            if self.move_in_progress and 'tile_type' in self.move_in_progress:
                if len(self.staged_moves) >= C.MAX_PLAYER_ACTIONS: self.message = "Cannot stage more moves."; return
                coord = self.move_in_progress['coord']
                self.move_in_progress['action_type'] = 'exchange' if self.game.board.get_tile(*coord) else 'place'
                self.staged_moves.append(self.move_in_progress)
                self.move_in_progress = None
                self._validate_all_staged_moves()
                self.message = f"Staged {len(self.staged_moves)}/{C.MAX_PLAYER_ACTIONS}. Select next square."
            else: self.message = "Nothing to stage."
        elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
            self._commit_staged_moves(active_player)

    def _validate_all_staged_moves(self):
        # This method's logic is correct and does not need to change.
        player = self.game.get_active_player()
        all_hypothetical_moves = self.staged_moves[:]
        if self.move_in_progress and 'tile_type' in self.move_in_progress:
            all_hypothetical_moves.append(self.move_in_progress)
        for i, move_to_validate in enumerate(all_hypothetical_moves):
            other_moves = all_hypothetical_moves[:i] + all_hypothetical_moves[i+1:]
            coord_r, coord_c = move_to_validate['coord']
            action = 'exchange' if self.game.board.get_tile(coord_r, coord_c) else 'place'
            is_valid, reason = False, "Not enough info"
            if 'tile_type' in move_to_validate:
                orientation = move_to_validate.get('orientation', 0)
                if action == 'place': is_valid, reason = self.game.check_placement_validity(move_to_validate['tile_type'], orientation, coord_r, coord_c, hypothetical_moves=other_moves)
                else: is_valid, reason = self.game.check_exchange_validity(player, move_to_validate['tile_type'], orientation, coord_r, coord_c, hypothetical_moves=other_moves)
            move_to_validate['is_valid'] = is_valid

    # --- THIS IS THE FINAL, SIMPLIFIED FIX ---
    def _commit_staged_moves(self, player):
        """Attempts to commit all staged moves and then confirms the turn if complete."""
        if self.move_in_progress:
            self.message = "A move is being built. [S] to stage or [ESC] to clear."; return
        if not self.staged_moves:
            # This handles the case where the user presses Enter again after a successful commit.
            # Since _reset_staging is called, this will now be true, and we simply do nothing.
            return
        
        self._validate_all_staged_moves()

        if all(move.get('is_valid', False) for move in self.staged_moves):
            command = CombinedActionCommand(self.game, player, self.staged_moves)
            
            if self.game.command_history.execute_command(command):
                if self.game.actions_taken_this_turn >= self.game.MAX_PLAYER_ACTIONS:
                    self.game.confirm_turn()
                
                # After a successful commit, always reset the staging area.
                self._reset_staging()
            else:
                self.message = "Commit failed: Action limit would be exceeded."
        else:
            self.message = "Cannot commit: one or more moves are invalid (red)."

    def draw(self, screen):
        # This method's logic is correct and does not need to change.
        self.visualizer.draw_board(screen)
        if self.move_in_progress:
            self.visualizer.draw_selected_coord_highlight(screen, self.move_in_progress.get('coord'))
            if 'tile_type' in self.move_in_progress: self.visualizer.draw_live_preview(screen, self.move_in_progress)
        self.visualizer.draw_staged_moves(screen, self.staged_moves)
        if self.visualizer.debug_mode: self.visualizer.draw_debug_panel(screen, None)
        else:
            player = self.game.get_active_player()
            if player:
                selected_hand_idx = self.move_in_progress.get('hand_index') if self.move_in_progress else None
                self.current_hand_rects = self.visualizer.draw_hand(screen, player, self.staged_moves, selected_hand_idx)
        instr_text = "Click Square -> Click Hand -> [S] Stage -> [Enter] Commit"
        self.visualizer.draw_ui(screen, self.message, instr_text)

# --- Driving State ---

class DrivingState(GameState):
    """Handles input and drawing when players are driving trams."""
    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.message = "Roll die or select debug roll."
        self.last_roll: Optional[Any] = None

    def handle_event(self, event):
        if self._handle_common_clicks(event): return
        try:
            active_player = self.game.get_active_player()
            if active_player.player_state != PlayerState.DRIVING: return
        except IndexError: return

        roll_result: Optional[Any] = None
        if self.visualizer.debug_mode and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for face, rect in self.visualizer.debug_die_rects.items():
                if rect.collidepoint(event.pos):
                    roll_result = face; break
        elif not self.visualizer.debug_mode and event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            roll_result = self.game.roll_special_die()
        
        if roll_result is not None:
            self.last_roll = roll_result
            self.message = f"Rolled {roll_result}..."
            if not self.game.attempt_driving_move(active_player, roll_result):
                self.message = "Driving move failed to execute."

    def draw(self, screen):
        self.visualizer.draw_board(screen)
        self.visualizer.draw_ui(screen, self.message)
        roll_display = f"Last Roll: {self.last_roll if self.last_roll is not None else '--'}"
        self.visualizer.draw_text(screen, roll_display, C.UI_TEXT_X, C.DEBUG_DIE_AREA_Y - 30, size=20)

# --- Game Over State ---

class GameOverState(GameState):
    """Displays the game over message and winner."""
    def __init__(self, visualizer):
        super().__init__(visualizer)
        winner = self.game.winner
        self.message = f"GAME OVER! Player {winner.player_id} Wins!" if winner else "GAME OVER!"

    def handle_event(self, event):
        if self._handle_common_clicks(event): return

    def draw(self, screen):
        self.visualizer.draw_board(screen)
        self.visualizer.draw_ui(screen, self.message)
        try: font = pygame.font.SysFont(None, 40)
        except: font = pygame.font.Font(None, 40)
        text_surface = font.render(self.message, True, C.COLOR_STOP)
        text_rect = text_surface.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2))
        bg_rect = text_rect.inflate(20, 10)
        pygame.draw.rect(screen, C.COLOR_UI_BG, bg_rect, border_radius=5)
        pygame.draw.rect(screen, C.COLOR_BLACK, bg_rect, 2, border_radius=5)
        screen.blit(text_surface, text_rect)