# visualizer.py
import pygame
from typing import Optional, List, Dict, Callable, Set, Tuple

from scenes.scene import Scene

# --- FIX: Add missing imports for type hints and class references ---
from game_logic.game import Game
from game_logic.tile import TileType, PlacedTile
from game_logic.player import Player, AIPlayer
from game_logic.enums import GamePhase, PlayerState, Direction
# --- END FIX ---

from states.game_states import GameState, LayingTrackState, DrivingState, GameOverState
from mods.mod_manager import ModManager
from common.sound_manager import SoundManager
from ui.ui_manager import UIManager
from common.rendering_utils import create_tile_surface, get_font
import common.constants as C

class GameScene(Scene):
    def __init__(self, scene_manager, game_instance, sounds, mod_manager):
        super().__init__(scene_manager)
        self.theme = scene_manager.theme # Get theme from the manager
        self.game = game_instance
        self.sounds = sounds
        self.mod_manager = mod_manager
        
        # --- All __init__ logic from your old visualizer.py ---
        self.screen = scene_manager.screen
        self.tk_root = scene_manager.tk_root
        self.TILE_SIZE = C.TILE_SIZE
        self.debug_mode = C.DEBUG_MODE
        self.show_ai_heatmap = False
        self.heatmap_data: Set[tuple[int, int]] = set()

        self.current_state: GameState = LayingTrackState(self)
        self.next_state_constructor: Optional[Callable] = None
        self.update_current_state_for_player()
        
        self.tile_surfaces = {name: create_tile_surface(ttype, self.TILE_SIZE) for name, ttype in self.game.tile_types.items()}
        self.ui_manager = UIManager(self.screen, self.tile_surfaces, self.mod_manager, self.theme)
        
        self.debug_tile_types: List[TileType] = list(self.game.tile_types.values())
        self.debug_tile_surfaces = {ttype.name: create_tile_surface(ttype, C.DEBUG_TILE_SIZE) for ttype in self.debug_tile_types}
        self.debug_die_surfaces = self._create_debug_die_surfaces()
        self.debug_tile_rects: Dict[int, pygame.Rect] = {}
        self.debug_die_rects: Dict[any, pygame.Rect] = {}

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.scene_manager.go_to_scene("MAIN_MENU")
                return

            # --- START OF FIX: Simplified and Corrected Turn Logic ---
            if event.type == C.START_NEXT_TURN_EVENT:
                # 1. First, confirm the turn of the player who just finished.
                #    This advances the player index and updates game state.
                self.game.confirm_turn()

                # 2. After confirmation, get the NEW active player.
                active_player = self.game.get_active_player()

                # 3. If this new player is an AI and it's their turn to act,
                #    tell them to start their logic.
                if isinstance(active_player, AIPlayer) and self.game.actions_taken_this_turn == 0:
                    active_player.handle_turn_logic(self.game, self, self.sounds)
                
                # This event has been fully handled.
                continue
            # --- END OF FIX ---

            # Standard UI and game state event handling
            if self.ui_manager.handle_event(event, self.game, self.current_state):
                continue
            if self.current_state:
                self.current_state.handle_event(event)

    def update(self, dt: float):
        if self.next_state_constructor:
            print(f"Executing State Change Request...")
            # --- FIX: The lambda now correctly passes 'self' (the scene) ---
            self.current_state = self.next_state_constructor(self)
            self.next_state_constructor = None

    def draw(self, screen):
        """Implementation of the abstract method."""
        screen.fill(self.theme["colors"]["panel_bg"])
        
        if not self.current_state:
            draw_text(screen, "Error: Invalid State", 10, 10, self.theme["colors"]["negative"])
            return

        self.draw_board()
        self.draw_overlays()
        self.ui_manager.draw(self.game, self.current_state)
        self.current_state.draw(screen)

    def draw_board(self):
        """
        Draws the grid, tiles, buildings, terminals, and player streetcars.
        """
        # --- START OF FIX ---
        # Replace all instances of 'screen' with 'self.screen'
        for r in range(C.GRID_ROWS):
            for c in range(C.GRID_COLS):
                rect = pygame.Rect(
                    C.BOARD_X_OFFSET + (c - C.PLAYABLE_COLS[0]) * self.TILE_SIZE,
                    C.BOARD_Y_OFFSET + (r - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE,
                    self.TILE_SIZE, self.TILE_SIZE
                )
                placed_tile = self.game.board.get_tile(r, c)
                is_playable = self.game.board.is_playable_coordinate(r, c)
                is_terminal = placed_tile is not None and placed_tile.is_terminal
                
                # Use theme colors
                bg_color = self.theme["colors"]["board_bg"] if is_playable else self.theme["colors"]["background"]
                grid_color = self.theme["colors"]["grid_lines"]
                
                if is_terminal: # Terminals can have a slightly different look if desired
                    bg_color = self.theme["colors"]["panel_border"]

                pygame.draw.rect(self.screen, bg_color, rect)
                pygame.draw.rect(self.screen, grid_color, rect, 1)

                if placed_tile:
                    tile_surf = self.tile_surfaces.get(placed_tile.tile_type.name)
                    if tile_surf:
                        # Re-color the track to match the new theme
                        # This is an advanced step, for now we assume original track color is fine
                        # To do this properly, you would have a create_tile_surface that accepts a color
                        rotated_surf = pygame.transform.rotate(tile_surf, -placed_tile.orientation)
                        self.screen.blit(rotated_surf, rotated_surf.get_rect(center=rect.center))

                building_id = self.game.board.get_building_at(r, c)
                if building_id and is_playable:
                    pygame.draw.rect(self.screen, self.theme["colors"]["building_bg"], rect)
                    b_font = get_font(int(self.TILE_SIZE * 0.7))
                    b_surf = b_font.render(building_id, True, self.theme["colors"]["building_fg"])
                    self.screen.blit(b_surf, b_surf.get_rect(center=rect.center))
                    pygame.draw.rect(self.screen, grid_color, rect, 1)

                if placed_tile and placed_tile.has_stop_sign and is_playable:
                    stop_radius = self.TILE_SIZE // 4
                    stop_surf = pygame.Surface((stop_radius * 2, stop_radius * 2), pygame.SRCALPHA)
                    stop_color = self.theme["colors"]["negative"]
                    pygame.draw.circle(stop_surf, stop_color + [128], (stop_radius, stop_radius), stop_radius)
                    pygame.draw.circle(stop_surf, (0,0,0,128), (stop_radius, stop_radius), stop_radius, 1)
                    self.screen.blit(stop_surf, stop_surf.get_rect(center=rect.center))

        terminal_font = get_font(int(self.TILE_SIZE * 0.5))
        for line_num, entrances in C.TERMINAL_DATA.items():
            try:
                for entrance_pair in entrances:
                    cell1_coord = entrance_pair[0][0]
                    cell2_coord = entrance_pair[1][0]
                    rect1_x = C.BOARD_X_OFFSET + (cell1_coord[1] - C.PLAYABLE_COLS[0]) * self.TILE_SIZE
                    rect1_y = C.BOARD_Y_OFFSET + (cell1_coord[0] - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE
                    rect2_x = C.BOARD_X_OFFSET + (cell2_coord[1] - C.PLAYABLE_COLS[0]) * self.TILE_SIZE
                    rect2_y = C.BOARD_Y_OFFSET + (cell2_coord[0] - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE
                    center_x = (rect1_x + rect2_x + self.TILE_SIZE) // 2
                    center_y = (rect1_y + rect2_y + self.TILE_SIZE) // 2
                    
                    term_surf = terminal_font.render(str(line_num), True, self.theme["colors"]["text_light"])
                    term_rect = term_surf.get_rect(center=(center_x, center_y))
                    bg_rect = term_rect.inflate(6, 4)
                    
                    pygame.draw.rect(self.screen, self.theme["colors"]["background"], bg_rect, border_radius=3)
                    self.screen.blit(term_surf, term_rect)
            except Exception as e:
                 print(f"Error processing TERMINAL_DATA for Line {line_num}: {e}")

        for player in self.game.players:
            if player.player_state == PlayerState.DRIVING and player.streetcar_position:
                 r, c = player.streetcar_position
                 if self.game.board.is_valid_coordinate(r, c):
                     screen_x = C.BOARD_X_OFFSET + (c - C.PLAYABLE_COLS[0]) * self.TILE_SIZE + C.TILE_SIZE // 2
                     screen_y = C.BOARD_Y_OFFSET + (r - C.PLAYABLE_ROWS[0]) * C.TILE_SIZE + C.TILE_SIZE // 2
                     tram_radius = C.TILE_SIZE // 3
                     p_color = C.PLAYER_COLORS[player.player_id % len(C.PLAYER_COLORS)]
                     pygame.draw.circle(self.screen, p_color, (screen_x, screen_y), tram_radius)
                     pygame.draw.circle(self.screen, self.theme["colors"]["background"], (screen_x, screen_y), tram_radius, 2)
                     id_font = get_font(int(tram_radius * 1.5))
                     id_surf = id_font.render(str(player.player_id), True, self.theme["colors"]["text_light"])
                     self.screen.blit(id_surf, id_surf.get_rect(center=(screen_x, screen_y)))
        # --- END OF FIX ---

    def draw_overlays(self):
        """Draws all dynamic elements on top of the board, like highlights and previews."""
        if isinstance(self.current_state, LayingTrackState):
            self.draw_staged_moves(self.current_state.staged_moves)
            if self.current_state.move_in_progress:
                self.draw_selected_coord_highlight(self.current_state.move_in_progress.get('coord'))
                if 'tile_type' in self.current_state.move_in_progress:
                    self.draw_live_preview(self.current_state.move_in_progress)

        self.draw_ai_heatmap()

    def draw_staged_moves(self, staged_moves: List[Dict]):
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
                self.screen.blit(rotated_surf, rotated_surf.get_rect(center=rect.center))

            # --- START OF FIX: Use SRCALPHA for transparency ---
            # Define colors for valid (green) and invalid (red) moves
            valid_color = (0, 255, 0, 100) # Green, semi-transparent
            invalid_color = (255, 0, 0, 100) # Red, semi-transparent
            
            highlight_color = valid_color if move.get('is_valid', False) else invalid_color
            
            # Create a new surface with a per-pixel alpha format
            highlight_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
            highlight_surface.fill(highlight_color)
            self.screen.blit(highlight_surface, rect.topleft)
            # --- END OF FIX ---

    def draw_live_preview(self, move_in_progress: Dict):
        # NOTE: Copy implementation from your original visualizer.py
        if not move_in_progress or 'tile_type' not in move_in_progress: return
        r, c = move_in_progress['coord']
        tile_type = move_in_progress['tile_type']
        orientation = move_in_progress.get('orientation', 0)
        is_valid = move_in_progress.get('is_valid', False)
        screen_x = C.BOARD_X_OFFSET + (c - C.PLAYABLE_COLS[0]) * self.TILE_SIZE
        screen_y = C.BOARD_Y_OFFSET + (r - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE
        rect = pygame.Rect(screen_x, screen_y, self.TILE_SIZE, self.TILE_SIZE)
        tile_surf = self.tile_surfaces.get(tile_type.name)
        if tile_surf:
            rotated_surf = pygame.transform.rotate(tile_surf.copy(), -orientation)
            rotated_surf.set_alpha(150)
            self.screen.blit(rotated_surf, rotated_surf.get_rect(center=rect.center))
        highlight_color = (0, 255, 0, 100) if is_valid else (255, 0, 0, 100)
        highlight_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        highlight_surface.fill(highlight_color)
        self.screen.blit(highlight_surface, rect.topleft)

    def draw_selected_coord_highlight(self, coord: Optional[Tuple[int, int]]):
        # NOTE: Copy implementation from your original visualizer.py
        if not coord: return
        r, c = coord
        if not self.game.board.is_playable_coordinate(r, c): return
        screen_x = C.BOARD_X_OFFSET + (c - C.PLAYABLE_COLS[0]) * self.TILE_SIZE
        screen_y = C.BOARD_Y_OFFSET + (r - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE
        rect = pygame.Rect(screen_x, screen_y, self.TILE_SIZE, self.TILE_SIZE)
        highlight_color = (255, 165, 0, 100)
        temp_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        temp_surf.fill(highlight_color)
        self.screen.blit(temp_surf, rect.topleft)
        pygame.draw.rect(self.screen, (255, 165, 0), rect, 2)

    def draw_ai_heatmap(self):
        # NOTE: Copy implementation from your original visualizer.py
        if not self.show_ai_heatmap or not self.heatmap_data: return
        highlight_color = (0, 255, 255, 90)
        border_color = (0, 200, 200)
        for r, c in self.heatmap_data:
            if not self.game.board.is_valid_coordinate(r, c): continue
            screen_x = C.BOARD_X_OFFSET + (c - C.PLAYABLE_COLS[0]) * self.TILE_SIZE
            screen_y = C.BOARD_Y_OFFSET + (r - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE
            rect = pygame.Rect(screen_x, screen_y, self.TILE_SIZE, self.TILE_SIZE)
            temp_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
            temp_surf.fill(highlight_color)
            self.screen.blit(temp_surf, rect.topleft)
            pygame.draw.rect(self.screen, border_color, rect, 2)

    def draw_preview(self, tile_to_preview: Optional[TileType], orientation: int):
        # NOTE: Copy implementation from your original visualizer.py
        if tile_to_preview is None: return
        mouse_pos = pygame.mouse.get_pos()
        grid_col_rel = (mouse_pos[0] - C.BOARD_X_OFFSET) // self.TILE_SIZE
        grid_row_rel = (mouse_pos[1] - C.BOARD_Y_OFFSET) // self.TILE_SIZE
        grid_col = grid_col_rel + C.PLAYABLE_COLS[0]
        grid_row = grid_row_rel + C.PLAYABLE_ROWS[0]
        if self.game.board.is_playable_coordinate(grid_row, grid_col):
            screen_x = C.BOARD_X_OFFSET + grid_col_rel * self.TILE_SIZE
            screen_y = C.BOARD_Y_OFFSET + grid_row_rel * self.TILE_SIZE
            rect = pygame.Rect(screen_x, screen_y, self.TILE_SIZE, self.TILE_SIZE)
            tile_surf = self.tile_surfaces.get(tile_to_preview.name)
            if tile_surf:
                rotated_surf = pygame.transform.rotate(tile_surf.copy(), -orientation)
                rotated_surf.set_alpha(150)
                new_rect = rotated_surf.get_rect(center=rect.center)
                self.screen.blit(rotated_surf, new_rect.topleft)

    def request_state_change(self, new_state_constructor: Callable):
        self.next_state_constructor = new_state_constructor

    def return_to_base_state(self):
        target_state_class = LayingTrackState
        try:
            player_state = self.game.get_active_player().player_state
            if self.game.game_phase == GamePhase.GAME_OVER:
                target_state_class = GameOverState
            elif player_state == PlayerState.DRIVING:
                target_state_class = DrivingState
        except Exception as e:
            print(f"Error determining base state: {e}")
        self.request_state_change(target_state_class)

    def update_current_state_for_player(self):
        if getattr(self.current_state, 'is_transient_state', False): return
        try:
            active_player = self.game.get_active_player()
            player_state = active_player.player_state
            game_phase = self.game.game_phase
            target_state_class = None
            if game_phase == GamePhase.GAME_OVER:
                target_state_class = GameOverState
            elif player_state == PlayerState.DRIVING:
                target_state_class = DrivingState
            elif player_state == PlayerState.LAYING_TRACK:
                target_state_class = LayingTrackState
            if target_state_class and not isinstance(self.current_state, target_state_class):
                print(f"State Change: -> {target_state_class.__name__}")
                self.current_state = target_state_class(self)
        except (IndexError, AttributeError) as e:
            print(f"Error updating state: {e}")
        
    def force_redraw(self, message: str = "Processing..."):
        """Forces an immediate, one-off redraw of the entire screen."""
        self.screen.fill(self.theme["colors"]["panel_bg"])
        original_message = ""
        if self.current_state:
            original_message = getattr(self.current_state, 'message', "")
            self.current_state.message = message
        
        # --- START OF FIX ---
        # The draw method now requires the 'screen' argument.
        self.draw(self.screen)
        # --- END OF FIX ---
        
        if self.current_state:
            self.current_state.message = original_message
        pygame.display.flip()
        
    def _create_debug_die_surfaces(self):
        # NOTE: Copy implementation from your original visualizer.py
        unique_faces = set(C.DIE_FACES)
        ordered_unique_faces = []
        if C.STOP_SYMBOL in unique_faces: ordered_unique_faces.append(C.STOP_SYMBOL)
        numbers = sorted([f for f in unique_faces if isinstance(f, int)])
        ordered_unique_faces.extend(numbers)
        surfaces = {}
        size = C.DEBUG_DIE_BUTTON_SIZE
        font = get_font(int(size * 0.7))
        for face in ordered_unique_faces:
             surf = pygame.Surface((size, size))
             surf.fill(C.COLOR_WHITE)
             pygame.draw.rect(surf, C.COLOR_BLACK, surf.get_rect(), 1)
             text_surf = font.render(str(face), True, C.COLOR_BLACK)
             text_rect = text_surf.get_rect(center=(size // 2, size // 2))
             surf.blit(text_surf, text_rect)
             surfaces[face] = surf
        return surfaces