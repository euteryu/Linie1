# game_logic/board.py
from typing import List, Dict, Tuple, Optional, Set
from .enums import Direction # Relative import
from .tile import PlacedTile, TileType # Relative import
# Import constants used *only* by Board
from constants import GRID_ROWS, GRID_COLS, PLAYABLE_ROWS, PLAYABLE_COLS, BUILDING_COORDS, TERMINAL_DATA

class Board:
    # ... (Implementation including _initialize_terminals, to_dict, from_dict as before) ...
    # Make sure _initialize_terminals uses PlacedTile correctly
    def __init__(self, rows: int = GRID_ROWS, cols: int = GRID_COLS): # ... implementation ...
        self.rows = rows; self.cols = cols; self.grid: List[List[Optional[PlacedTile]]] = [[None for _ in range(cols)] for _ in range(rows)]; self.building_coords = BUILDING_COORDS; self.coord_to_building: Dict[Tuple[int, int], str] = { v: k for k, v in self.building_coords.items() }; self.buildings_with_stops: Set[str] = set(); self.building_stop_locations: Dict[str, Tuple[int, int]] = {}
    def _initialize_terminals(self, tile_types: Dict[str, TileType]): # ... (implementation) ...
        print("Initializing Terminals by placing tiles...")
        curve_tile = tile_types.get("Curve"); # ... null check ...
        if not curve_tile: print("FATAL ERROR: Could not find 'Curve' TileType."); return
        # ... rest of terminal placement logic ...
        for line_num, entrances in TERMINAL_DATA.items():
             # ... validation ...
             entrance_a, entrance_b = entrances
             for entrance_pair in [entrance_a, entrance_b]:
                  # ... validation ...
                  cell1_info, cell2_info = entrance_pair
                  # ... validation ...
                  coord1, orient1 = cell1_info; coord2, orient2 = cell2_info
                  # Place tiles using PlacedTile constructor
                  if isinstance(coord1, tuple) and len(coord1) == 2 and isinstance(orient1, int):
                       if self.is_valid_coordinate(coord1[0], coord1[1]):
                            if self.grid[coord1[0]][coord1[1]] is None: self.grid[coord1[0]][coord1[1]] = PlacedTile(curve_tile, orient1, is_terminal=True)
                  if isinstance(coord2, tuple) and len(coord2) == 2 and isinstance(orient2, int):
                       if self.is_valid_coordinate(coord2[0], coord2[1]):
                           if self.grid[coord2[0]][coord2[1]] is None: self.grid[coord2[0]][coord2[1]] = PlacedTile(curve_tile, orient2, is_terminal=True)
        print("Finished placing terminal tiles.")
    
    def is_valid_coordinate(self, row: int, col: int) -> bool:
        return 0 <= row < self.rows and 0 <= col < self.cols

    def is_playable_coordinate(self, row: int, col: int) -> bool:
        return (PLAYABLE_ROWS[0] <= row <= PLAYABLE_ROWS[1] and
                PLAYABLE_COLS[0] <= col <= PLAYABLE_COLS[1])

    def get_tile(self, row: int, col: int) -> Optional[PlacedTile]:
        if self.is_valid_coordinate(row, col):
            return self.grid[row][col]
        return None

    def set_tile(self, row: int, col: int, tile: Optional[PlacedTile]):
        if not self.is_valid_coordinate(row, col):
            raise IndexError(f"Coordinate ({row},{col}) out of bounds.")
        existing = self.grid[row][col]
        if existing and existing.is_terminal and tile is not None and not tile.is_terminal:
             print(f"Warning: Cannot overwrite terminal at ({row},{col}).")
             return
        self.grid[row][col] = tile

    def get_building_at(self, row: int, col: int) -> Optional[str]:
        return self.coord_to_building.get((row, col))

    def get_neighbors(self, row: int, col: int) -> Dict[Direction, Tuple[int, int]]:
        neighbors = {}
        for direction in Direction:
            dr, dc = direction.value
            nr, nc = row + dr, col + dc
            if self.is_valid_coordinate(nr, nc):
                neighbors[direction] = (nr, nc)
        return neighbors

    def to_dict(self) -> Dict: # ... implementation ...
        grid_data = [[(tile.to_dict() if tile else None) for tile in row] for row in self.grid]; # ... rest of implementation ...
        return {"rows": self.rows, "cols": self.cols, "grid": grid_data, "buildings_with_stops": sorted(list(self.buildings_with_stops)), "building_stop_locations": {k: list(v) for k, v in self.building_stop_locations.items()},}
    @staticmethod
    def from_dict(data: Dict, tile_types: Dict[str, 'TileType']) -> 'Board': # ... implementation ...
        rows = data.get("rows", GRID_ROWS); cols = data.get("cols", GRID_COLS); board = Board(rows, cols); board.grid = [[None for _ in range(cols)] for _ in range(rows)]; # ... rest of implementation ...
        grid_data = data.get("grid", []); # ... loop through grid_data ...
        for r in range(min(len(grid_data), board.rows)):
            row_data = grid_data[r]
            for c in range(min(len(row_data), board.cols)):
                 tile_data = row_data[c]; board.grid[r][c] = PlacedTile.from_dict(tile_data, tile_types)
        board.buildings_with_stops = set(data.get("buildings_with_stops", [])); # ... rest of implementation ...
        loaded_stop_locs = data.get("building_stop_locations", {}); board.building_stop_locations = {k: tuple(v) for k, v in loaded_stop_locs.items() if isinstance(v, list) and len(v) == 2}; return board
