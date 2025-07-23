# src/states/game_states.py
from __future__ import annotations
from typing import Optional, Dict, Any, List, TYPE_CHECKING
import pygame
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
import copy

# --- FIX: Import from new, correct locations ---
from game_logic.commands import CombinedActionCommand, StageMoveCommand, UnstageAllCommand, PlaceTileCommand, ExchangeTileCommand
from common import constants as C
from common.rendering_utils import get_font
from game_logic.player import AIPlayer, HumanPlayer
from game_logic.enums import GamePhase, PlayerState, Direction
from game_logic.commands import CombinedActionCommand

from common.rendering_utils import get_font, draw_text

from mods.economic_mod.economic_commands import AuctionTileCommand, PlaceBidCommand

if TYPE_CHECKING:
    from game_logic.game import Game
    from game_logic.tile import TileType
    from scenes.game_scene import GameScene

class GameState:
    """Abstract base class for different game phases/states."""
    def __init__(self, scene):
        # --- START OF FIX ---
        # The state is owned by a Scene, not a Visualizer.
        self.scene = scene
        self.game: 'Game' = scene.game
        # --- END OF FIX ---
        self.is_transient_state: bool = False

    def handle_event(self, event) -> bool:
        """
        Handles a Pygame event.
        Returns True if the event was handled by this state, False otherwise.
        """
        return False # Default implementation handles nothing.

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

    def toggle_strategy_view_action(self):
        """Toggles the main board rendering between strategic and artistic views."""
        self.scene.strategy_view_active = not self.scene.strategy_view_active
        mode = "Strategy" if self.scene.strategy_view_active else "Artistic"
        self.set_message(f"View mode switched to: {mode}")

    def toggle_hint_action(self):
        """Toggles the display of the ideal route hint."""
        # The import must be absolute from the project's 'src' root.
        from game_logic.ai_strategy import HardStrategy 
        
        self.scene.show_hint_path = not self.scene.show_hint_path
        if self.scene.show_hint_path:
            # Calculate the ideal route for the current player
            player = self.game.get_active_player()
            strategy = HardStrategy()
            ideal_plan = strategy._calculate_ideal_route(self.game, player)
            if ideal_plan:
                # Store the coordinates of the path for the visualizer to draw
                self.scene.hint_path_data = {step.coord for step in ideal_plan}
                self.set_message("Hint Activated: Showing ideal route.")
            else:
                self.set_message("Hint: No valid route could be found.")
                self.scene.hint_path_data = set()
        else:
            self.set_message("Hint Deactivated.")
            self.scene.hint_path_data = set()

    def set_message(self, msg: str):
        if hasattr(self, 'message'): self.message = msg
        else: print(f"State Warning: Cannot set message '{msg}'")



# --- Laying Track State ---
class LayingTrackState(GameState):
    def __init__(self, scene):
        super().__init__(scene)
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
    def _handle_mouse_down(self, event):
        """Handles all left-clicks, now aware of data-driven UI regions."""
        hovered_name = event.hovered_ui_name

        # --- NEW: Handle clicks on UI elements defined in the layout ---
        if hovered_name:
            if "at_hand" in hovered_name:
                try:
                    hand_index = int(hovered_name.split('_')[-1]) - 1
                    self._on_hand_tile_click(hand_index)
                except (ValueError, IndexError): 
                    pass
            
            elif hovered_name == "stage_button":
                print("Stage button clicked via UI")
                self._stage_current_move()
                
            elif hovered_name == "commit_button":
                print("Commit button clicked via UI")
                self._commit_staged_moves()
            
            elif hovered_name == "settings_button":
                print("Settings button clicked via UI")
                self.scene.scene_manager.go_to_scene("MAIN_MENU")
            
            return

        # --- EXISTING: Handle clicks on the game board ---
        grid_r, grid_c = event.grid_pos
        if self.game.board.is_valid_coordinate(grid_r, grid_c):
            # ... (the existing logic for selecting a board square is perfect here) ...
            self.scene.sounds.play('click')
            self.move_in_progress = None
            self._validate_all_staged_moves()
            if self.game.board.get_building_at(grid_r, grid_c): self.message = "Cannot place on a building."; return
            if any(m['coord'] == (grid_r, grid_c) for m in self.staged_moves): self.message = "Square already staged."; return
            target_tile = self.game.board.get_tile(grid_r, grid_c)
            if target_tile and (target_tile.is_terminal or not target_tile.tile_type.is_swappable): self.message = "Tile is permanent."; return
            self.move_in_progress = {'coord': (grid_r, grid_c)}
            self.message = f"Selected {self.move_in_progress['coord']}. Click a hand tile."

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
            # The logic to modify the orientation was correct, but it was missing
            # from the final version I provided. This restores it.
            if self.move_in_progress and 'orientation' in self.move_in_progress:
                self.move_in_progress['orientation'] = (self.move_in_progress['orientation'] + 45) % 360
            elif self.staged_moves:
                # Rotate the most recently staged move
                self.staged_moves[-1]['orientation'] = (self.staged_moves[-1]['orientation'] + 45) % 360
            
            self._validate_all_staged_moves()
            self.message = "Rotated selection."
            return # Explicitly return after handling

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
        
        elif event.key == C.pygame.K_s: # Using C to be safe
            if self.move_in_progress and 'tile_type' in self.move_in_progress:
                if len(self.staged_moves) + self.game.actions_taken_this_turn >= C.MAX_PLAYER_ACTIONS:
                    self.message = "Cannot stage more moves."
                    return
                self.move_in_progress['action_type'] = 'exchange' if self.game.board.get_tile(*self.move_in_progress['coord']) else 'place'
                
                # This now works because StageMoveCommand is imported correctly.
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
        if self.move_in_progress:
            self.message = "A move is being built. [S] to stage or [ESC] to clear."
            return
        
        if self.staged_moves:
            self._validate_all_staged_moves()
            if all(move.get('is_valid', False) for move in self.staged_moves):
                command = CombinedActionCommand(self.game, player, self.staged_moves)
                if self.game.command_history.execute_command(command):
                    self.scene.sounds.play('commit')
                    self._reset_staging()
                    # --- FIX: No longer calls confirm_turn() here. ---
                    # The command now posts an event to handle this.
                else:
                    self.message = "Commit failed: Action limit would be exceeded."
            else:
                self.message = "Cannot commit: one or more moves are invalid (red)."
                self.scene.sounds.play('error')
        else:
            # Forfeit logic now also posts the event to be safe.
            pygame.event.post(pygame.event.Event(C.START_NEXT_TURN_EVENT, {'reason': 'forfeit_attempt'}))

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
        # Draw a big "Game Over" message in the center of the screen
        font = get_font(50)
        text_surface = font.render(self.message, True, C.COLOR_STOP)
        text_rect = text_surface.get_rect(center=(C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2))
        
        bg_rect = text_rect.inflate(40, 20)
        pygame.draw.rect(screen, C.COLOR_UI_BG, bg_rect, border_radius=10)
        pygame.draw.rect(screen, C.COLOR_BLACK, bg_rect, 3, border_radius=10)
        
        screen.blit(text_surface, text_rect)


class AuctionHouseState(GameState):
    """
    A transient state for viewing market prices and participating in auctions.
    """
    def __init__(self, scene: 'GameScene'):
        super().__init__(scene)
        self.is_transient_state = True
        self.eco_mod = self.game.mod_manager.available_mods.get('economic_mod')
        self.font = get_font(18)
        self.header_font = get_font(24)
        
        # Tabs
        self.tabs = ["Market Prices", "Live Auctions"]
        self.active_tab = "Market Prices"
        self.tab_rects = {
            "Market Prices": pygame.Rect(50, 50, 200, 40),
            "Live Auctions": pygame.Rect(260, 50, 200, 40)
        }
        
        # UI Elements
        self.close_button_rect = pygame.Rect(C.SCREEN_WIDTH - 50, 10, 40, 40)
        self.scroll_offset = 0
        self.bid_buttons: Dict[int, pygame.Rect] = {} # auction_index -> rect

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.scene.return_to_base_state()
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left click
                if self.close_button_rect.collidepoint(event.pos):
                    self.scene.return_to_base_state()
                    return
                # Handle tab clicks
                for tab_name, rect in self.tab_rects.items():
                    if rect.collidepoint(event.pos):
                        self.active_tab = tab_name
                        self.scroll_offset = 0
                        return
                # Handle bid button clicks
                if self.active_tab == "Live Auctions":
                    for auction_idx, rect in self.bid_buttons.items():
                        if rect.collidepoint(event.pos):
                            self._handle_bid_action(auction_idx)
                            return
            # Mouse wheel scrolling
            elif event.button == 4: self.scroll_offset = max(0, self.scroll_offset - 30)
            elif event.button == 5: self.scroll_offset += 30

    def _handle_bid_action(self, auction_index: int):
        """Opens a dialog for the user to enter their bid amount."""
        if not self.scene.tk_root: return
        
        auction = self.game.live_auctions[auction_index]
        min_bid = max([b['amount'] for b in auction['bids']], default=auction['min_bid']) + 1

        try:
            bid_str = simpledialog.askstring("Place Bid", f"Enter your bid amount (minimum: ${min_bid}):", parent=self.scene.tk_root)
            if not bid_str: return

            bid_amount = int(bid_str)
            if bid_amount < min_bid:
                messagebox.showerror("Error", f"Bid must be at least ${min_bid}.")
                return

            player = self.game.get_active_player()
            command = PlaceBidCommand(self.game, player, 'economic_mod', auction_index, bid_amount)
            if not self.game.command_history.execute_command(command):
                 messagebox.showerror("Error", "Could not place bid. Check your available Capital.")
            else:
                 self.scene.return_to_base_state()
        except (ValueError, TypeError):
             messagebox.showerror("Error", "Invalid input. Please enter a number.")

    def draw(self, screen):
        # Background Overlay
        overlay = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((20, 0, 40, 220)); screen.blit(overlay, (0, 0))
        
        # Close button
        pygame.draw.rect(screen, (200, 50, 50), self.close_button_rect)
        draw_text(screen, "X", self.close_button_rect.centerx, self.close_button_rect.centery, C.COLOR_WHITE, 30, True, True)

        # Draw Tabs
        for name, rect in self.tab_rects.items():
            color = (80, 80, 120) if self.active_tab == name else (40, 40, 60)
            pygame.draw.rect(screen, color, rect, border_top_left_radius=8, border_top_right_radius=8)
            draw_text(screen, name, rect.centerx, rect.centery, C.COLOR_WHITE, 20, True, True)

        # Content Panel
        panel_rect = pygame.Rect(50, 90, C.SCREEN_WIDTH - 100, C.SCREEN_HEIGHT - 150)
        pygame.draw.rect(screen, (30, 30, 50), panel_rect)

        # Draw content based on active tab
        if self.active_tab == "Market Prices":
            self._draw_market_prices(screen, panel_rect)
        elif self.active_tab == "Live Auctions":
            self._draw_live_auctions(screen, panel_rect)

    def _draw_market_prices(self, screen, panel_rect):
        y_pos = panel_rect.top + 20 - self.scroll_offset
        for tile_type in self.game.tile_types.values():
            if y_pos > panel_rect.bottom - 40 or y_pos < panel_rect.top:
                y_pos += 40; continue
            
            price = self.eco_mod.get_market_price(self.game, tile_type)
            supply = self.game.deck_manager.tile_draw_pile.count(tile_type)
            initial_supply = self.game.deck_manager.initial_tile_counts.get(tile_type.name, 0)
            
            color = C.COLOR_WHITE if supply > 0 else (100, 100, 100)
            
            draw_text(screen, f"{tile_type.name}:", panel_rect.left + 20, y_pos, color, 20)
            draw_text(screen, f"Market Price: ${price}", panel_rect.left + 300, y_pos, color, 20)
            draw_text(screen, f"Supply: {supply}/{initial_supply}", panel_rect.left + 550, y_pos, color, 20)
            y_pos += 40

    def _draw_live_auctions(self, screen, panel_rect):
        self.bid_buttons.clear()
        if not self.game.live_auctions:
            draw_text(screen, "No active auctions.", panel_rect.centerx, panel_rect.centery, (150, 150, 150), 30, True, True)
            return

        y_pos = panel_rect.top + 20 - self.scroll_offset
        for i, auction in enumerate(self.game.live_auctions):
            if y_pos > panel_rect.bottom - 80 or y_pos < panel_rect.top:
                y_pos += 80; continue

            seller = self.game.players[auction['seller_id']]
            tile_name = auction['tile_type_name']
            current_high_bid = max([b['amount'] for b in auction['bids']], default=auction['min_bid'])

            draw_text(screen, f"Item: {tile_name}", panel_rect.left + 20, y_pos, C.COLOR_WHITE, 20)
            draw_text(screen, f"Seller: Player {seller.player_id}", panel_rect.left + 20, y_pos + 25, (200, 200, 200), 18)
            draw_text(screen, f"Current Bid: ${current_high_bid}", panel_rect.left + 350, y_pos, C.COLOR_WHITE, 20)
            draw_text(screen, f"Ends in: {auction['turn_of_resolution'] - self.game.current_turn} turn(s)", panel_rect.left + 350, y_pos + 25, (200, 200, 200), 18)
            
            # Draw Bid button
            bid_button_rect = pygame.Rect(panel_rect.right - 170, y_pos + 10, 150, 40)
            self.bid_buttons[i] = bid_button_rect
            pygame.draw.rect(screen, (0, 150, 100), bid_button_rect, border_radius=5)
            draw_text(screen, "Place Bid", bid_button_rect.centerx, bid_button_rect.centery, C.COLOR_WHITE, 20, True, True)
            
            y_pos += 80

class InfluenceDecisionState(GameState):
    """A transient state to ask the player if they want to use an Influence point."""
    def __init__(self, scene: 'GameScene'):
        super().__init__(scene)
        self.is_transient_state = True
        self.message = "Spend 1 Influence (★) to roll again?"
        self.yes_rect = pygame.Rect(C.SCREEN_WIDTH // 2 - 110, C.SCREEN_HEIGHT // 2, 100, 50)
        self.no_rect = pygame.Rect(C.SCREEN_WIDTH // 2 + 10, C.SCREEN_HEIGHT // 2, 100, 50)

    def handle_event(self, event) -> bool:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_y:
                self._use_influence()
                return True
            elif event.key == pygame.K_n:
                self._end_turn()
                return True
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.yes_rect.collidepoint(event.pos):
                self._use_influence()
                return True
            elif self.no_rect.collidepoint(event.pos):
                self._end_turn()
                return True
        return False

    def _use_influence(self):
        """Handles the logic for spending influence and re-rolling."""
        player = self.game.get_active_player()
        eco_mod = self.game.mod_manager.available_mods.get('economic_mod')
        if eco_mod and player.components[eco_mod.mod_id]['influence'] > 0:
            player.components[eco_mod.mod_id]['influence'] -= 1
            
            influence_roll = random.randint(1, 4)
            print(f"  Player {player.player_id} used Influence and rolled a {influence_roll}.")
            
            # Make the move, but crucially, DO NOT end the turn.
            self.game.attempt_driving_move(player, influence_roll, end_turn=False)
            
            # After the move, return to the base driving state. If they still have influence,
            # the game will trigger this decision state again.
            self.scene.return_to_base_state() 
        else:
            self._end_turn()

    def _end_turn(self):
        """Ends the current player's turn."""
        print("  Player chose not to use Influence. Ending turn.")
        pygame.event.post(pygame.event.Event(C.START_NEXT_TURN_EVENT, {'reason': 'driving_turn_end'}))
        self.scene.return_to_base_state()

    def draw(self, screen):
        # Dimming overlay
        overlay = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((20, 0, 40, 190)); screen.blit(overlay, (0, 0))
        
        # Message
        draw_text(screen, self.message, C.SCREEN_WIDTH // 2, C.SCREEN_HEIGHT // 2 - 50, C.COLOR_WHITE, 30, True, True)
        
        # Buttons
        pygame.draw.rect(screen, (0, 150, 0), self.yes_rect, border_radius=8)
        draw_text(screen, "[Y] Yes", self.yes_rect.centerx, self.yes_rect.centery, C.COLOR_WHITE, 24, True, True)
        pygame.draw.rect(screen, (150, 0, 0), self.no_rect, border_radius=8)
        draw_text(screen, "[N] No", self.no_rect.centerx, self.no_rect.centery, C.COLOR_WHITE, 24, True, True)
# --- END OF CHANGE ---