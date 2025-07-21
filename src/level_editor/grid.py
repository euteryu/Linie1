# src/level_editor/grid.py
import pygame
from typing import List, Dict, Any, Optional, Tuple

# --- START OF CHANGE: Correct the import paths ---
from common import constants as C
from common.rendering_utils import create_tile_surface, get_font
# --- END OF CHANGE ---

class Grid:
    def __init__(self, playable_rows: int, playable_cols: int, sidebar_width: int, screen_width: int, screen_height: int):
        """
        Initializes the Grid.
        
        Args:
            playable_rows (int): The number of rows for the playable area.
            playable_cols (int): The number of columns for the playable area.
            sidebar_width (int): The width of the sidebar UI element.
            screen_width (int): The total width of the application window.
            screen_height (int): The total height of the application window.
        """
        self.playable_rows = playable_rows
        self.playable_cols = playable_cols
        
        self.total_rows = playable_rows + 2
        self.total_cols = playable_cols + 2
        
        # Use the passed-in screen dimensions to calculate tile size and offsets
        available_width = screen_width - sidebar_width
        available_height = screen_height
        self.tile_size = min(available_width // self.total_cols, available_height // self.total_rows)
        
        self.width = self.total_cols * self.tile_size
        self.height = self.total_rows * self.tile_size
        
        self.x_offset = (available_width - self.width) // 2
        self.y_offset = (available_height - self.height) // 2

        self.grid_data: List[List[Optional[Dict[str, Any]]]] = [[None for _ in range(self.total_cols)] for _ in range(self.total_rows)]
        self.stamp_surfaces = self._create_stamp_surfaces()

    def _create_stamp_surfaces(self) -> Dict[str, pygame.Surface]:
        """Creates a dictionary of all visual assets scaled to the current tile size."""
        surfaces = {}
        # Tiles (including the base curve for terminals)
        for name, details in C.TILE_DEFINITIONS.items():
            dummy_tile_type = type('TileType', (object,), {'name': name, **details})
            surf = create_tile_surface(dummy_tile_type, self.tile_size)
            surfaces[name] = surf
        
        # Buildings
        font = get_font(int(self.tile_size * 0.7))
        for building_id in C.BUILDING_COORDS.keys():
            surf = pygame.Surface((self.tile_size, self.tile_size))
            surf.fill(C.COLOR_BUILDING_BG)
            text_surf = font.render(building_id, True, C.COLOR_BUILDING_FG)
            surf.blit(text_surf, text_surf.get_rect(center=(self.tile_size // 2, self.tile_size // 2)))
            surfaces[building_id] = surf
        return surfaces

    def handle_click(self, mouse_pos: Tuple[int, int], current_stamp: Dict[str, Any], orientation: int):
        """Places the selected stamp onto the grid with correct validation and orientation logic."""
        col = (mouse_pos[0] - self.x_offset) // self.tile_size
        row = (mouse_pos[1] - self.y_offset) // self.tile_size
        
        if not (0 <= row < self.total_rows and 0 <= col < self.total_cols):
            return # Click was outside the grid

        # --- Eraser Logic ---
        if current_stamp['type'] == 'eraser':
            self.grid_data[row][col] = None
            return

        # --- Terminal Pair Logic ---
        if current_stamp['type'] == 'terminal_pair':
            is_on_border = not (1 <= row < self.total_rows - 1 and 1 <= col < self.total_cols - 1)
            if not is_on_border:
                print("Validation Error: Terminals can only be placed on the outer border.")
                return

            # Define the relative positions and orientations for the pair based on the main rotation
            # [ (dr1, dc1, orient1), (dr2, dc2, orient2) ]
            pair_configs = {
                0:   [(0, 0, 90), (0, 1, 180)],   # Facing right (for top/bottom border)
                90:  [(0, 0, 180), (1, 0, 270)],  # Facing down (for right border)
                180: [(0, 0, 270), (0, -1, 0)],   # Facing left (for top/bottom border)
                270: [(0, 0, 0), (-1, 0, 90)],    # Facing up (for left border)
            }
            
            config = pair_configs[orientation]
            pos1 = (row + config[0][0], col + config[0][1])
            pos2 = (row + config[1][0], col + config[1][1])

            # Check if both parts of the pair are on the grid
            if not (0 <= pos1[0] < self.total_rows and 0 <= pos1[1] < self.total_cols and \
                    0 <= pos2[0] < self.total_rows and 0 <= pos2[1] < self.total_cols):
                print("Cannot place terminal pair: part of it would be off-grid.")
                return

            # Place the two individual terminal stamps
            stamp_base = {'type': 'terminal', 'line_number': current_stamp['line_number']}
            self.grid_data[pos1[0]][pos1[1]] = {**stamp_base, 'name': f"Terminal {current_stamp['line_number']}", 'orientation': config[0][2]}
            self.grid_data[pos2[0]][pos2[1]] = {**stamp_base, 'name': f"Terminal {current_stamp['line_number']}", 'orientation': config[1][2]}
            print(f"Placed Terminal Pair {current_stamp['line_number']} with rotation {orientation}deg.")
            return

        # --- Standard Tile and Building Logic ---
        is_playable = (1 <= row < self.total_rows - 1 and 1 <= col < self.total_cols - 1)
        if current_stamp['type'] in ['tile', 'building'] and not is_playable:
            print("Validation Error: Standard tiles and buildings can only be placed in the playable area.")
            return
            
        new_stamp_data = current_stamp.copy()
        if new_stamp_data['type'] == 'tile':
            new_stamp_data['orientation'] = orientation
        self.grid_data[row][col] = new_stamp_data
        print(f"Placed '{current_stamp['name']}' at ({row}, {col})")

    def get_grid_data(self) -> List[List[Optional[Dict[str, Any]]]]:
        """Returns the entire grid data for saving."""
        return self.grid_data

    def set_grid_data(self, data: List[List[Optional[Dict[str, Any]]]]):
        """Sets the entire grid data when loading a file."""
        if isinstance(data, list) and len(data) == self.total_rows:
            self.grid_data = data
            print("Grid data loaded successfully.")
        else:
            print("ERROR: Failed to load grid data due to mismatch in dimensions.")

    def draw(self, screen: pygame.Surface):
        """Draws the grid and all placed stamps, now rendering terminals correctly."""
        for r in range(self.total_rows):
            for c in range(self.total_cols):
                rect = pygame.Rect(self.x_offset + c * self.tile_size, self.y_offset + r * self.tile_size, self.tile_size, self.tile_size)
                
                # Differentiate playable area from terminal border
                is_playable = (1 <= r < self.total_rows - 1) and (1 <= c < self.total_cols - 1)
                bg_color = C.COLOR_BOARD_BG if is_playable else (50, 50, 70)
                
                pygame.draw.rect(screen, bg_color, rect)
                pygame.draw.rect(screen, C.COLOR_GRID, rect, 1)

                # Draw the stamp if one exists at this cell
                stamp_data = self.grid_data[r][c]
                if stamp_data:
                    # --- START OF CHANGE: New drawing logic for different stamp types ---
                    stamp_type = stamp_data['type']
                    stamp_name = stamp_data['name']
                    
                    if stamp_type == 'terminal':
                        base_surf = self.stamp_surfaces.get('Curve') # Terminals are always visually curves
                        if base_surf:
                            # Draw a white background for the track
                            pygame.draw.rect(screen, C.COLOR_WHITE, rect)
                            
                            orientation = stamp_data.get('orientation', 0)
                            rotated_surf = pygame.transform.rotate(base_surf, -orientation)
                            
                            # Center the rotated surface inside the grid cell
                            draw_rect = rotated_surf.get_rect(center=rect.center)
                            screen.blit(rotated_surf, draw_rect)
                            
                            # Draw the line number on top
                            font = get_font(int(self.tile_size * 0.5))
                            text_surf = font.render(str(stamp_data['line_number']), True, C.COLOR_BLACK)
                            screen.blit(text_surf, text_surf.get_rect(center=rect.center))
                    
                    elif stamp_type == 'tile':
                        base_surf = self.stamp_surfaces.get(stamp_name)
                        if base_surf:
                            # Draw a white background for the track
                            pygame.draw.rect(screen, C.COLOR_WHITE, rect)
                            
                            orientation = stamp_data.get('orientation', 0)
                            rotated_surf = pygame.transform.rotate(base_surf, -orientation)
                            
                            draw_rect = rotated_surf.get_rect(center=rect.center)
                            screen.blit(rotated_surf, draw_rect)
                    
                    elif stamp_type == 'building':
                         base_surf = self.stamp_surfaces.get(stamp_name)
                         if base_surf:
                             screen.blit(base_surf, rect.topleft)
                    # --- END OF CHANGE ---

    def is_mouse_over(self, mouse_pos: Tuple[int, int]) -> bool:
        """Checks if the mouse is within the grid's boundaries."""
        return self.x_offset <= mouse_pos[0] < self.x_offset + self.width and \
               self.y_offset <= mouse_pos[1] < self.y_offset + self.height