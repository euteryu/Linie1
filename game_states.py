# game_states.py
from typing import Optional, TypeVar
import pygame
# Import logic classes
from game_logic import Game, Player, TileType, PlayerState, GamePhase, Direction # Add Direction
# Import constants
import constants as C

class GameState:
    """Abstract base class for game states."""
    def __init__(self, visualizer):
        self.visualizer = visualizer
        self.game = visualizer.game

    def handle_event(self, event):
        raise NotImplementedError
    def update(self, dt):
        pass
    def draw(self, screen):
        raise NotImplementedError

class LayingTrackState(GameState):
    """State handling the tile laying phase."""
    def __init__(self, visualizer):
        super().__init__(visualizer)
        self.selected_tile_index: Optional[int] = None
        self.current_orientation = 0
        self.message = ""
        self.current_hand_rects: Dict[int, pygame.Rect] = {}

    def get_selected_tile_type(self) -> Optional[TileType]:
        if self.selected_tile_index is None: return None
        active_player = self.game.get_active_player()
        if 0 <= self.selected_tile_index < len(active_player.hand):
            return active_player.hand[self.selected_tile_index]
        return None

    def handle_event(self, event):
        active_player: Player = self.game.get_active_player()
        if active_player.player_state != PlayerState.LAYING_TRACK: return

        # Use imported constants (C.*)
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            # --- Hand Area Click Check ---
            clicked_hand_index = None
            for index, rect in self.current_hand_rects.items():
                if rect.collidepoint(mouse_pos):
                    clicked_hand_index = index; break

            if clicked_hand_index is not None:
                if event.button == 1: # Select Tile
                    if self.selected_tile_index != clicked_hand_index:
                         self.selected_tile_index = clicked_hand_index
                         self.current_orientation = 0
                         selected_type = self.get_selected_tile_type()
                         self.message = f"Selected: {selected_type.name}" if selected_type else "Error"
            # --- Board Area Click Check ---
            elif C.BOARD_X_OFFSET <= mouse_pos[0] < C.BOARD_X_OFFSET + C.BOARD_WIDTH and \
                 C.BOARD_Y_OFFSET <= mouse_pos[1] < C.BOARD_Y_OFFSET + C.BOARD_HEIGHT:
                # Use C.* constants for boundaries
                grid_col = (mouse_pos[0] - C.BOARD_X_OFFSET) // C.TILE_SIZE
                grid_row = (mouse_pos[1] - C.BOARD_Y_OFFSET) // C.TILE_SIZE

                if event.button == 1: # Try Place
                    selected_type = self.get_selected_tile_type()
                    if selected_type and self.game.board.is_valid_coordinate(grid_row, grid_col):
                        success = self.game.player_action_place_tile(
                            active_player, selected_type, self.current_orientation, grid_row, grid_col
                        )
                        if success:
                            self.message = f"Placed {selected_type.name}."; self.selected_tile_index = None; self.current_orientation = 0
                            if self.game.actions_taken_this_turn >= C.MAX_PLAYER_ACTIONS: # Use constant
                                self.end_turn_sequence()
                        else: self.message = "Invalid placement."
                    elif not selected_type: self.message = "Select tile first."

                elif event.button == 3: # Rotate
                    self.current_orientation = (self.current_orientation + 90) % 360
                    self.message = f"Orientation: {self.current_orientation} deg"

        elif event.type == pygame.KEYDOWN:
             if event.key == pygame.K_r: # Rotate
                  self.current_orientation = (self.current_orientation + 90) % 360
                  self.message = f"Orientation: {self.current_orientation} deg"
             elif event.key == pygame.K_SPACE: # End turn
                 if self.game.actions_taken_this_turn >= C.MAX_PLAYER_ACTIONS:
                    self.end_turn_sequence()
                 else: self.message = f"Need {C.MAX_PLAYER_ACTIONS - self.game.actions_taken_this_turn} more actions."

    def end_turn_sequence(self):
         self.game.end_player_turn(); self.message = ""; self.selected_tile_index = None; self.current_orientation = 0
         new_player = self.game.get_active_player()
         if new_player.player_state == PlayerState.LAYING_TRACK:
             if self.game.check_player_route_completion(new_player): self.game.handle_route_completion(new_player)

    def draw(self, screen):
        self.visualizer.draw_board(screen)
        self.current_hand_rects = self.visualizer.draw_hand(screen, self.game.get_active_player()) # Store rects
        selected_type = self.get_selected_tile_type()
        self.visualizer.draw_ui(screen, self.message, selected_type, self.current_orientation)
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
        self.visualizer.draw_text(screen, win_text, self.visualizer.SCREEN_WIDTH // 2 - 150, self.visualizer.SCREEN_HEIGHT // 2, size=40)