# visualizer.py
import pygame
import sys
import math
# Import game logic classes needed
from game_logic import Game, PlacedTile, TileType, GamePhase
# Import state classes
from game_states import GameState, LayingTrackState, DrivingState, GameOverState
# Import constants (layout, grid dimensions, colors etc.)
import constants as C # Use an alias for brevity

# --- Main Visualizer Class ---
class Linie1Visualizer:
    # ... (__init__, run, check_game_phase, drawing helpers need updates below) ...
    def __init__(self):
        pygame.init()
        # Use imported constants for screen setup
        self.screen = pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
        pygame.display.set_caption("Linie 1")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)

        self.game = Game(num_players=2) # Game logic instance

        # Use imported constants for calculations
        self.TILE_SIZE = C.TILE_SIZE
        self.HAND_TILE_SIZE = C.HAND_TILE_SIZE

        # --- Regenerate surfaces using the NEW drawing function ---
        print("Generating tile surfaces...")
        self.tile_surfaces: Dict[str, pygame.Surface] = {
            name: create_tile_surface(ttype, self.TILE_SIZE)
            for name, ttype in self.game.tile_types.items()
        }
        self.hand_tile_surfaces: Dict[str, pygame.Surface] = {
             name: create_tile_surface(ttype, self.HAND_TILE_SIZE)
             for name, ttype in self.game.tile_types.items()
        }
        print("Tile surfaces generated.")

        self.current_state: GameState = LayingTrackState(self)

    # --- Other Visualizer methods (run, check_game_phase, draw_text, etc. keep as is) ---
    def run(self): # Keep as is
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                self.current_state.handle_event(event)
            self.current_state.update(dt)
            self.check_game_phase()
            self.screen.fill(C.COLOR_UI_BG)
            self.current_state.draw(self.screen)
            pygame.display.flip()
        pygame.quit(); sys.exit()
    def check_game_phase(self): # Keep as is
        model_phase = self.game.game_phase
        if model_phase == GamePhase.LAYING_TRACK and not isinstance(self.current_state, LayingTrackState): self.current_state = LayingTrackState(self)
        elif model_phase == GamePhase.DRIVING and not isinstance(self.current_state, DrivingState): self.current_state = DrivingState(self)
        elif model_phase == GamePhase.GAME_OVER and not isinstance(self.current_state, GameOverState): self.current_state = GameOverState(self)
    def draw_text(self, surface, text, x, y, color=C.COLOR_UI_TEXT, size=24): # Keep as is
        font = pygame.font.SysFont(None, size); text_surface = font.render(text, True, color); surface.blit(text_surface, (x, y))
    def draw_board(self, screen): # Keep as is
        for r in range(C.GRID_ROWS):
            for c in range(C.GRID_COLS):
                screen_x = C.BOARD_X_OFFSET + c * self.TILE_SIZE; screen_y = C.BOARD_Y_OFFSET + r * self.TILE_SIZE; rect = pygame.Rect(screen_x, screen_y, self.TILE_SIZE, self.TILE_SIZE)
                pygame.draw.rect(screen, C.COLOR_BOARD_BG, rect); pygame.draw.rect(screen, C.COLOR_GRID, rect, 1)
                placed_tile: Optional[PlacedTile] = self.game.board.get_tile(r, c)
                if placed_tile:
                    tile_surf = self.tile_surfaces.get(placed_tile.tile_type.name)
                    if tile_surf:
                        rotated_surf = pygame.transform.rotate(tile_surf, -placed_tile.orientation)
                        new_rect = rotated_surf.get_rect(center=rect.center); screen.blit(rotated_surf, new_rect.topleft)
                        if placed_tile.has_stop_sign: pygame.draw.circle(screen, C.COLOR_STOP, rect.center, self.TILE_SIZE // 4)
                    else: self.draw_text(screen, "?", rect.centerx - 5, rect.centery - 10)
                building_id = self.game.board.get_building_at(r, c)
                if building_id: b_font = pygame.font.SysFont(None, 20); b_surf = b_font.render(building_id, True, C.COLOR_BUILDING); screen.blit(b_surf, (screen_x + 2, screen_y + 2))

    def draw_hand(self, screen, player):
        """Draws the player's hand tiles in the UI panel."""
        # Hand Title is now drawn in draw_ui
        # self.draw_text(screen, f"Player {player.player_id}'s Hand:", C.HAND_AREA_X, C.HAND_AREA_Y - C.UI_LINE_HEIGHT) # Removed Title
        hand_rects = {}
        for i, tile_type in enumerate(player.hand):
            if i >= C.HAND_TILE_COUNT: break
            screen_x = C.HAND_AREA_X
            # Use C.HAND_AREA_Y which is positioned correctly now
            screen_y = C.HAND_AREA_Y + i * (self.HAND_TILE_SIZE + C.HAND_SPACING)
            rect = pygame.Rect(screen_x, screen_y, self.HAND_TILE_SIZE, self.HAND_TILE_SIZE)
            hand_rects[i] = rect

            pygame.draw.rect(screen, C.COLOR_WHITE, rect)
            hand_surf = self.hand_tile_surfaces.get(tile_type.name)
            if hand_surf:
                 img_rect = hand_surf.get_rect(center=rect.center)
                 screen.blit(hand_surf, img_rect.topleft)
            pygame.draw.rect(screen, C.COLOR_BLACK, rect, 1)

            # Highlight selected tile
            if isinstance(self.current_state, LayingTrackState) and self.current_state.selected_tile_index == i:
                pygame.draw.rect(screen, C.COLOR_SELECTED, rect, 3)
        return hand_rects

    def draw_ui(self, screen, message, selected_tile, orientation):
        """Draws general UI elements in the UI panel with better spacing and route info."""
        player = self.game.get_active_player()

        # --- Player and Turn Info ---
        turn_text = f"Turn {self.game.current_turn} - Player {player.player_id} ({player.player_state.name})"
        self.draw_text(screen, turn_text, C.UI_TEXT_X, C.UI_TURN_INFO_Y) # Use constant Y

        action_text = f"Actions: {self.game.actions_taken_this_turn}/{C.MAX_PLAYER_ACTIONS}"
        # Position actions text separately for clarity
        action_text_width = self.font.render(action_text, True, C.COLOR_UI_TEXT).get_width()
        self.draw_text(screen, action_text, C.UI_PANEL_X + C.UI_PANEL_WIDTH - action_text_width - 10, C.UI_TURN_INFO_Y) # Align Right

        # --- Player's Route Info ---
        line_info = "Line: ?"
        if player.line_card:
            term1, term2 = self.game.get_terminal_coords(player.line_card.line_number)
            # TODO: Map terminal coords back to names/locations if desired
            term1_str = f"T{player.line_card.line_number}a" # Placeholder names
            term2_str = f"T{player.line_card.line_number}b"
            line_info = f"Line {player.line_card.line_number} ({term1_str} <-> {term2_str})"

        stops_info = "Stops: ?"
        if player.route_card:
            stops_str = " -> ".join(player.route_card.stops)
            stops_info = f"Stops: {stops_str}"

        self.draw_text(screen, line_info, C.UI_TEXT_X, C.UI_ROUTE_INFO_Y) # Use constant Y
        self.draw_text(screen, stops_info, C.UI_TEXT_X, C.UI_ROUTE_INFO_Y + C.UI_LINE_HEIGHT) # Next line

        # --- Hand Title --- (Moved below route info)
        self.draw_text(screen, f"Player {player.player_id}'s Hand:", C.UI_TEXT_X, C.UI_HAND_TITLE_Y) # Use constant Y

        # --- Selection / Message / Instructions (Positioned at bottom) ---
        if isinstance(self.current_state, LayingTrackState):
             sel_text = "Selected: None"
             if selected_tile:
                  sel_text = f"Selected: {selected_tile.name} ({orientation}°)"
             self.draw_text(screen, sel_text, C.UI_TEXT_X, C.UI_SELECTED_TILE_Y) # Use constant Y

             self.draw_text(screen, f"Msg: {message}", C.UI_TEXT_X, C.UI_MESSAGE_Y) # Use constant Y
             self.draw_text(screen, "[RMB/R] Rotate | [LMB] Place/Select | [SPACE] End", C.UI_TEXT_X, C.UI_INSTRUCTIONS_Y, size=18) # Use constant Y

    def draw_preview(self, screen, selected_tile, orientation): # Keep as is
         if not isinstance(self.current_state, LayingTrackState) or selected_tile is None: return
         mouse_pos = pygame.mouse.get_pos(); grid_col = (mouse_pos[0] - C.BOARD_X_OFFSET) // self.TILE_SIZE; grid_row = (mouse_pos[1] - C.BOARD_Y_OFFSET) // self.TILE_SIZE
         if self.game.board.is_valid_coordinate(grid_row, grid_col):
             screen_x = C.BOARD_X_OFFSET + grid_col * self.TILE_SIZE; screen_y = C.BOARD_Y_OFFSET + grid_row * self.TILE_SIZE; rect = pygame.Rect(screen_x, screen_y, self.TILE_SIZE, self.TILE_SIZE)
             tile_surf = self.tile_surfaces.get(selected_tile.name)
             if tile_surf:
                 rotated_surf = pygame.transform.rotate(tile_surf.copy(), -orientation); rotated_surf.set_alpha(128)
                 new_rect = rotated_surf.get_rect(center=rect.center); screen.blit(rotated_surf, new_rect.topleft)


def create_tile_surface(tile_type: TileType, size: int) -> pygame.Surface:
    """Creates a Pygame Surface using lines and simple arcs, handling pairs correctly."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0)) # Transparent background

    center_x, center_y = size // 2, size // 2
    # Adjust margin slightly if needed for arc appearance
    margin = size * 0.05
    line_width = max(2, int(size * 0.1)) # Make lines a bit thicker relative to size
    track_color = C.COLOR_TRACK

    # Edge connection points (closer to edge now)
    ptN = (center_x, 0) # Start arcs from edge
    ptS = (center_x, size)
    ptE = (size, center_y)
    ptW = (0, center_y)

    connections = tile_type.connections_base
    drawn_pairs = set()

    # Define rects for arcs covering the full tile quadrant for smoother look
    # Make width/height equal to size/2 for quarter circles
    half_size = size / 2.0
    rect_ne = pygame.Rect(center_x, 0, half_size, half_size)        # Top-right
    rect_nw = pygame.Rect(0, 0, half_size, half_size)               # Top-left
    rect_se = pygame.Rect(center_x, center_y, half_size, half_size) # Bottom-right
    rect_sw = pygame.Rect(0, center_y, half_size, half_size)        # Bottom-left

    for start_key, end_keys in connections.items():
        for end_key in end_keys:
            # Use frozenset for the pair to handle ('N','E') and ('E','N') as the same
            pair = frozenset((start_key, end_key))
            if pair in drawn_pairs:
                continue

            # --- Draw based on connection pair ---
            if pair == frozenset(('N', 'S')): # Straight Vertical
                pygame.draw.line(surf, track_color, (center_x, 0), (center_x, size), line_width)
            elif pair == frozenset(('E', 'W')): # Straight Horizontal
                pygame.draw.line(surf, track_color, (0, center_y), (size, center_y), line_width)
            elif pair == frozenset(('N', 'E')): # Curve Top-Right
                pygame.draw.arc(surf, track_color, rect_ne, math.pi / 2, math.pi, line_width) # 90 to 180 deg
            elif pair == frozenset(('N', 'W')): # Curve Top-Left
                pygame.draw.arc(surf, track_color, rect_nw, 0, math.pi / 2, line_width) # 0 to 90 deg
            elif pair == frozenset(('S', 'E')): # Curve Bottom-Right
                pygame.draw.arc(surf, track_color, rect_se, math.pi, 3 * math.pi / 2, line_width) # 180 to 270 deg
            elif pair == frozenset(('S', 'W')): # Curve Bottom-Left
                pygame.draw.arc(surf, track_color, rect_sw, 3 * math.pi / 2, 2 * math.pi, line_width) # 270 to 360 deg
            else:
                # This case should now be truly unreachable if connections are defined correctly
                print(f"Warning: Unexpected connection pair {pair} for {tile_type.name}")

            drawn_pairs.add(pair) # Add the frozenset pair

    return surf