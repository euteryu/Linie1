# visualizer.py
import pygame
from typing import Optional, List, Dict, Callable, Set, Tuple

# --- FIX: Add missing imports for type hints and class references ---
from game_logic.game import Game
from game_logic.tile import TileType, PlacedTile
from game_logic.player import Player, AIPlayer
from game_logic.enums import GamePhase, PlayerState, Direction
# --- END FIX ---

from game_states import GameState, LayingTrackState, DrivingState, GameOverState
from mod_manager import ModManager
from sound_manager import SoundManager
from ui.ui_manager import UIManager
from rendering_utils import create_tile_surface, get_font
import constants as C

class Linie1Visualizer:
    """
    Manages the rendering of the in-game scene, including the board,
    dynamic overlays, and the UI. It also manages the in-game state machine.
    """
    def __init__(self, screen: pygame.Surface, game: Game, sounds: SoundManager, mod_manager: ModManager):
        self.screen = screen
        self.game = game
        self.sounds = sounds
        self.mod_manager = mod_manager
        self.tk_root = None # Will be set by App

        self.TILE_SIZE = C.TILE_SIZE
        self.debug_mode = C.DEBUG_MODE
        self.show_ai_heatmap = False
        self.heatmap_data: Set[tuple[int, int]] = set()

        # --- State Machine ---
        self.current_state: GameState = LayingTrackState(self)
        self.next_state_constructor: Optional[Callable] = None
        self.update_current_state_for_player()
        
        # --- Pre-rendered Surfaces ---
        print("Generating tile surfaces...")
        self.tile_surfaces = {name: create_tile_surface(ttype, self.TILE_SIZE) for name, ttype in self.game.tile_types.items()}
        print("Tile surfaces generated.")
        
        # --- UI Manager ---
        # THE FIX: Pass `self.tile_surfaces` to the UIManager, not the `game` object.
        self.ui_manager = UIManager(self.screen, self.tile_surfaces, self.mod_manager)
        
        # --- Debug-specific attributes ---
        self.debug_tile_types: List[TileType] = list(self.game.tile_types.values())
        self.debug_tile_surfaces = {ttype.name: create_tile_surface(ttype, C.DEBUG_TILE_SIZE) for ttype in self.debug_tile_types}
        self.debug_die_surfaces = self._create_debug_die_surfaces()
        self.debug_tile_rects: Dict[int, pygame.Rect] = {}
        self.debug_die_rects: Dict[any, pygame.Rect] = {}


    def handle_event(self, event: pygame.event.Event):
        """Handles a single event, passing it to the current game state."""
        # The UIManager handles its own interactive elements first.
        # This is important for mod buttons that shouldn't reset staging.
        if self.ui_manager.handle_event(event, self.game, self.current_state):
            return

        # Handle turn-start events for AI
        if event.type == C.START_NEXT_TURN_EVENT:
            active_player = self.game.get_active_player()
            if isinstance(active_player, AIPlayer):
                active_player.handle_turn_logic(self.game, self, self.sounds)
            return
            
        # Let the current game state handle the rest
        if self.current_state:
            self.current_state.handle_event(event)

    def update(self, dt: float):
        """Updates the visualizer state, primarily for state transitions."""
        if self.next_state_constructor:
            print(f"Executing State Change Request...")
            self.current_state = self.next_state_constructor(self)
            self.next_state_constructor = None # Clear the request

    def draw(self):
        """
        Draws the entire in-game scene for the current frame.
        """
        if not self.current_state:
            from rendering_utils import draw_text
            draw_text(self.screen, "Error: Invalid State", 10, 10, C.COLOR_STOP)
            return

        # --- FIX: The visualizer is responsible for the standard draw calls ---
        # 1. Draw the board and pieces
        self.draw_board()
        # 2. Draw dynamic overlays like previews and highlights
        self.draw_overlays()
        # 3. Draw the entire UI panel
        self.ui_manager.draw(self.game, self.current_state)
        
        # 4. Allow the current state to draw any special, non-standard UI on top.
        #    (This will be used by ChooseAnyTileState but will do nothing for LayingTrackState).
        self.current_state.draw(self.screen)
        # --- END FIX ---

    def draw_board(self):
        """
        Draws the grid, tiles, buildings, terminals, and player streetcars.
        NOTE: Copy the implementation of this method from your original visualizer.py file.
        The logic inside is correct and does not need to change.
        """
        # (Implementation of draw_board from original file goes here)
        for r in range(C.GRID_ROWS):
            for c in range(C.GRID_COLS):
                screen_x = C.BOARD_X_OFFSET + (c - C.PLAYABLE_COLS[0]) * self.TILE_SIZE
                screen_y = C.BOARD_Y_OFFSET + (r - C.PLAYABLE_ROWS[0]) * self.TILE_SIZE
                rect = pygame.Rect(screen_x, screen_y, self.TILE_SIZE, self.TILE_SIZE)
                placed_tile = self.game.board.get_tile(r, c)
                is_playable = self.game.board.is_playable_coordinate(r, c)
                is_terminal = placed_tile is not None and placed_tile.is_terminal
                bg_color = C.COLOR_TERMINAL_BG if is_terminal else C.COLOR_BOARD_BG if is_playable else C.COLOR_GRID
                pygame.draw.rect(self.screen, bg_color, rect)
                pygame.draw.rect(self.screen, C.COLOR_GRID, rect, 1)

                if placed_tile:
                    tile_surf = self.tile_surfaces.get(placed_tile.tile_type.name)
                    if tile_surf:
                        rotated_surf = pygame.transform.rotate(tile_surf, -placed_tile.orientation)
                        self.screen.blit(rotated_surf, rotated_surf.get_rect(center=rect.center))

                building_id = self.game.board.get_building_at(r, c)
                if building_id and is_playable:
                    pygame.draw.rect(self.screen, C.COLOR_BUILDING_BG, rect)
                    b_font = get_font(int(self.TILE_SIZE * 0.7))
                    b_surf = b_font.render(building_id, True, C.COLOR_BUILDING_FG)
                    self.screen.blit(b_surf, b_surf.get_rect(center=rect.center))
                    pygame.draw.rect(self.screen, C.COLOR_GRID, rect, 1)

                if placed_tile and placed_tile.has_stop_sign and is_playable:
                    stop_radius = self.TILE_SIZE // 4
                    stop_surf = pygame.Surface((stop_radius * 2, stop_radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(stop_surf, C.COLOR_STOP + (128,), (stop_radius, stop_radius), stop_radius)
                    pygame.draw.circle(stop_surf, C.COLOR_BLACK + (128,), (stop_radius, stop_radius), stop_radius, 1)
                    self.screen.blit(stop_surf, stop_surf.get_rect(center=rect.center))

        terminal_font = get_font(int(self.TILE_SIZE * 0.5))
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
                     pygame.draw.rect(self.screen, C.COLOR_BLACK, bg_rect, border_radius=3)
                     self.screen.blit(term_surf, term_rect)
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
                     pygame.draw.circle(self.screen, p_color, (screen_x, screen_y), tram_radius)
                     pygame.draw.circle(self.screen, C.COLOR_BLACK, (screen_x, screen_y), tram_radius, 1)
                     id_font = get_font(int(tram_radius * 1.5))
                     id_surf = id_font.render(str(player.player_id), True, C.COLOR_WHITE)
                     self.screen.blit(id_surf, id_surf.get_rect(center=(screen_x, screen_y)))

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
        # NOTE: Copy implementation from your original visualizer.py
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
            highlight_color = (0, 255, 0, 100) if move['is_valid'] else (255, 0, 0, 100)
            highlight_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
            highlight_surface.fill(highlight_color)
            self.screen.blit(highlight_surface, rect.topleft)

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
        self.screen.fill(C.COLOR_UI_BG)
        original_message = getattr(self.current_state, 'message', "")
        if self.current_state:
            self.current_state.message = message
        self.draw()
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