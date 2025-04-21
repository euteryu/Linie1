# -*- coding: utf-8 -*-
import random
from enum import Enum, auto
from typing import List, Dict, Tuple, Optional, Set, Any
import copy # Needed for deep copy in exchange check

# --- Constants (Keep All from Previous Correct Version) ---
GRID_ROWS = 12
GRID_COLS = 12
BUILDING_COORDS: Dict[str, Tuple[int, int]] = {
    'A': (7, 11), 'B': (10, 8), 'C': (11, 4), 'D': (7, 1), 'E': (4, 0),
    'F': (1, 3),  'G': (0, 7),  'H': (3, 10),'I': (5, 8),  'K': (8, 6),
    'L': (6, 3),  'M': (3, 5),
}
TILE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "Straight":           {"connections": [['N', 'S']], "is_swappable": True},
    "Curve":              {"connections": [['N', 'E']], "is_swappable": True},
    "StraightLeftCurve":  {"connections": [['N', 'S'], ['S', 'W']], "is_swappable": True},
    "StraightRightCurve": {"connections": [['N', 'S'], ['S', 'E']], "is_swappable": True},
    "DoubleCurveY":       {"connections": [['N', 'W'], ['N', 'E']], "is_swappable": True},
    "DiagonalCurve":      {"connections": [['S', 'W'], ['N', 'E']], "is_swappable": True},
    "Tree_JunctionTop":      {"connections": [['E', 'W'], ['W', 'N'], ['N', 'E']], "is_swappable": False},
    "Tree_JunctionRight":    {"connections": [['E', 'W'], ['N', 'E'], ['S', 'E']], "is_swappable": False},
    "Tree_Roundabout":       {"connections": [['W', 'N'], ['N', 'E'], ['E', 'S'], ['S', 'W']], "is_swappable": False},
    "Tree_Crossroad":        {"connections": [['N', 'S'], ['E', 'W']], "is_swappable": False},
    "Tree_StraightDiagonal1":{"connections": [['N', 'S'], ['S', 'W'], ['N', 'E']], "is_swappable": False},
    "Tree_StraightDiagonal2":{"connections": [['N', 'S'], ['N', 'W'], ['S', 'E']], "is_swappable": False},
}
TILE_COUNTS_BASE: Dict[str, int] = {
    "Straight": 21, "Curve": 20, "StraightLeftCurve": 10, "StraightRightCurve": 10,
    "DoubleCurveY": 10, "DiagonalCurve": 6, "Tree_JunctionTop": 6, "Tree_JunctionRight": 6,
    "Tree_Roundabout": 4, "Tree_Crossroad": 4, "Tree_StraightDiagonal1": 2, "Tree_StraightDiagonal2": 2,
}
TILE_COUNTS_5_PLUS_ADD: Dict[str, int] = {"Straight": 15, "Curve": 10,}
STARTING_HAND_TILES: Dict[str, int] = {"Straight": 3, "Curve": 2,}
ROUTE_CARD_VARIANTS: List[Dict[str, Dict[int, List[str]]]] = [
    { "2-4": { 1: ['A', 'F'], 2: ['G', 'L'], 3: ['C', 'F'], 4: ['D', 'F'], 5: ['A', 'L'], 6: ['C', 'E'] }, "5-6": { 1: ['A', 'C', 'L'], 2: ['C', 'G', 'K'], 3: ['D', 'H', 'I'], 4: ['C', 'E', 'M'], 5: ['A', 'B', 'M'], 6: ['E', 'I', 'K'] }},
    { "2-4": { 1: ['F', 'K'], 2: ['F', 'H'], 3: ['A', 'C'], 4: ['D', 'K'], 5: ['D', 'G'], 6: ['E', 'H'] }, "5-6": { 1: ['B', 'G', 'L'], 2: ['B', 'L', 'M'], 3: ['C', 'I', 'M'], 4: ['A', 'D', 'M'], 5: ['A', 'G', 'K'], 6: ['B', 'F', 'M'] }},
    { "2-4": { 1: ['C', 'M'], 2: ['F', 'L'], 3: ['H', 'K'], 4: ['E', 'K'], 5: ['D', 'I'], 6: ['B', 'L'] }, "5-6": { 1: ['C', 'G', 'M'], 2: ['G', 'H', 'L'], 3: ['C', 'D', 'M'], 4: ['A', 'E', 'I'], 5: ['D', 'F', 'I'], 6: ['E', 'K', 'L'] }},
    { "2-4": { 1: ['B', 'I'], 2: ['B', 'M'], 3: ['D', 'M'], 4: ['E', 'I'], 5: ['B', 'H'], 6: ['F', 'I'] }, "5-6": { 1: ['C', 'D', 'I'], 2: ['E', 'G', 'I'], 3: ['D', 'H', 'K'], 4: ['H', 'K', 'L'], 5: ['A', 'E', 'L'], 6: ['A', 'B', 'L'] }},
    { "2-4": { 1: ['B', 'D'], 2: ['B', 'E'], 3: ['B', 'G'], 4: ['H', 'L'], 5: ['A', 'M'], 6: ['A', 'D'] }, "5-6": { 1: ['F', 'I', 'K'], 2: ['F', 'H', 'K'], 3: ['G', 'M', 'L'], 4: ['E', 'F', 'K'], 5: ['E', 'H', 'K'], 6: ['B', 'F', 'I'] }},
    { "2-4": { 1: ['C', 'I'], 2: ['G', 'K'], 3: ['E', 'G'], 4: ['C', 'H'], 5: ['H', 'M'], 6: ['A', 'G'] }, "5-6": { 1: ['F', 'H', 'K'], 2: ['C', 'F', 'I'], 3: ['B', 'H', 'L'], 4: ['D', 'I', 'M'], 5: ['A', 'L', 'M'], 6: ['B', 'F', 'I'] }},
]

# --- Enums ---
class PlayerState(Enum):
    LAYING_TRACK = auto()
    DRIVING = auto()
    FINISHED = auto()

class GamePhase(Enum):
    SETUP = auto()
    LAYING_TRACK = auto()
    DRIVING_TRANSITION = auto()
    DRIVING = auto()
    GAME_OVER = auto()

class Direction(Enum):
    N = (-1, 0)
    E = (0, 1)
    S = (1, 0)
    W = (0, -1)

    @staticmethod
    def opposite(direction: 'Direction') -> 'Direction':
        if direction == Direction.N:
            return Direction.S
        elif direction == Direction.S:
            return Direction.N
        elif direction == Direction.E:
            return Direction.W
        elif direction == Direction.W:
            return Direction.E
        else:
             raise ValueError("Invalid direction provided")

    @staticmethod
    def from_str(dir_str: str) -> 'Direction':
        try:
            return Direction[dir_str.upper()]
        except KeyError:
            raise ValueError(f"Invalid direction string: {dir_str}")

# --- Data Classes ---
class TileType:
    def __init__(self, name: str, connections: List[List[str]], is_swappable: bool):
        self.name = name
        self.connections_base = self._process_connections(connections) # Store base connections
        self.is_swappable = is_swappable

    def _process_connections(self, raw_connections: List[List[str]]) -> Dict[str, List[str]]:
        # Returns a dict like {'N': ['S'], 'S': ['N'], 'E': [], 'W': []} for Straight
        conn_map: Dict[str, List[str]] = {'N': [], 'E': [], 'S': [], 'W': []}
        for path in raw_connections:
            for i in range(len(path)):
                current_node = path[i]
                other_nodes = [path[j] for j in range(len(path)) if i != j]
                for other_node in other_nodes:
                    if other_node not in conn_map.get(current_node, []):
                        if current_node not in conn_map:
                             conn_map[current_node] = []
                        conn_map[current_node].append(other_node)
                        # Ensure lists are sorted for consistent comparison later
                        conn_map[current_node].sort()
        return conn_map

    def __repr__(self) -> str:
        return f"TileType({self.name}, Swappable={self.is_swappable})"

class PlacedTile:
    def __init__(self, tile_type: TileType, orientation: int = 0):
        self.tile_type = tile_type
        if orientation % 90 != 0:
            raise ValueError(f"Orientation must be a multiple of 90, got {orientation}")
        self.orientation = orientation % 360
        self.has_stop_sign: bool = False

    def __repr__(self) -> str:
        return f"Placed({self.tile_type.name}, {self.orientation}deg, Stop:{self.has_stop_sign})"

class Board:
    # Keep Board class as before (including simple_render)
    def __init__(self, rows: int = GRID_ROWS, cols: int = GRID_COLS):
        self.rows = rows; self.cols = cols
        self.grid: List[List[Optional[PlacedTile]]] = [[None for _ in range(cols)] for _ in range(rows)]
        self.building_coords = BUILDING_COORDS
        self.coord_to_building: Dict[Tuple[int, int], str] = {v: k for k, v in BUILDING_COORDS.items()}
        self.buildings_with_stops: Set[str] = set()
    def is_valid_coordinate(self, row: int, col: int) -> bool: return 0 <= row < self.rows and 0 <= col < self.cols
    def get_tile(self, row: int, col: int) -> Optional[PlacedTile]: return self.grid[row][col] if self.is_valid_coordinate(row, col) else None
    def set_tile(self, row: int, col: int, tile: Optional[PlacedTile]):
        if not self.is_valid_coordinate(row, col): raise IndexError(f"Coord ({row},{col}) out of bounds.")
        self.grid[row][col] = tile
    def get_building_at(self, row: int, col: int) -> Optional[str]: return self.coord_to_building.get((row, col))
    def get_neighbors(self, row: int, col: int) -> Dict[Direction, Tuple[int, int]]:
        neighbors = {};
        for direction in Direction:
            dr, dc = direction.value; nr, nc = row + dr, col + dc
            if self.is_valid_coordinate(nr, nc): neighbors[direction] = (nr, nc)
        return neighbors
    def simple_render(self, game=None) -> str:
        # Keep the improved simple_render from before
        conn_symbols = { frozenset(['N', 'S']): '│', frozenset(['E', 'W']): '─', frozenset(['N', 'E']): '└', frozenset(['N', 'W']): '┘', frozenset(['S', 'E']): '┌', frozenset(['S', 'W']): '┐', frozenset(['N', 'S', 'W']): '┤', frozenset(['N', 'S', 'E']): '├', frozenset(['E', 'W', 'N']): '┴', frozenset(['E', 'W', 'S']): '┬', frozenset(['N', 'W', 'E']): 'V', frozenset(['S', 'W', 'E']): 'Λ', frozenset(['S', 'W', 'N', 'E']): 'X', frozenset(['N', 'S', 'E', 'W']): '┼', frozenset(): '.', }
        default_symbol = '?'; col_width = 5; separator = "│"; cell_total_width = col_width + len(separator)
        header_parts = [" " * 3];
        for c in range(self.cols): col_num_str = str(c); padding_total = col_width - len(col_num_str); padding_left = padding_total // 2; padding_right = padding_total - padding_left; header_parts.append(" " * padding_left + col_num_str + " " * padding_right + separator)
        header = "".join(header_parts) + "\n"; h_line = "─" * col_width; top_connector = "┬"; top_border_line = h_line + (top_connector + h_line) * (self.cols - 1)
        top_border = "  ╭" + top_border_line + "╮\n"; board_str = header + top_border
        for r in range(self.rows):
            row_str_parts = [f"{r:<2}{separator}"]
            for c in range(self.cols):
                cell_content = ""; tile = self.grid[r][c]
                if tile:
                    stop = "S" if tile.has_stop_sign else ""; symbol = default_symbol
                    if game:
                        try:
                            connections = game.get_effective_connections(tile.tile_type, tile.orientation); connected_dirs = set()
                            for entry, exits in connections.items():
                                if exits: connected_dirs.add(entry); connected_dirs.update(exits)
                            symbol = conn_symbols.get(frozenset(connected_dirs), default_symbol)
                            if symbol == default_symbol:
                                if "Straight" in tile.tile_type.name and "Curve" in tile.tile_type.name: symbol = "T"
                                elif "Junction" in tile.tile_type.name: symbol = "J"
                                elif "Diagonal" in tile.tile_type.name: symbol = "X"
                                elif "Roundabout" in tile.tile_type.name: symbol = "O"
                                elif "Crossroad" in tile.tile_type.name: symbol = "┼"
                                elif tile.tile_type.name == "Straight": symbol = '│' if tile.orientation in [0, 180] else '─'
                                elif tile.tile_type.name == "Curve": symbol = 'C' # Simplified
                                else: symbol = tile.tile_type.name[0]
                        except Exception: symbol = 'E'
                    else: symbol = tile.tile_type.name[0] if tile.tile_type.name else '?'
                    cell_content = f"{symbol}{stop}"
                else: building = self.get_building_at(r, c); cell_content = f"[{building}]" if building else "·"
                padding_total = col_width - len(cell_content); padding_left = padding_total // 2; padding_right = padding_total - padding_left
                row_str_parts.append(" " * padding_left + cell_content + " " * padding_right + separator)
            board_str += "".join(row_str_parts) + "\n";
            if r < self.rows - 1: mid_connector = "┼"; mid_border_line = h_line + (mid_connector + h_line) * (self.cols - 1); board_str += "  ├" + mid_border_line + "┤\n"
            else: bot_connector = "┴"; bot_border_line = h_line + (bot_connector + h_line) * (self.cols - 1); board_str += "  ╰" + bot_border_line + "╯\n"
        return board_str

class LineCard: # Keep as is
    def __init__(self, line_number: int): self.line_number = line_number
    def __repr__(self) -> str: return f"LineCard(Line {self.line_number})"
class RouteCard: # Keep as is
    def __init__(self, stops: List[str], variant_index: int): self.stops = stops; self.variant_index = variant_index
    def __repr__(self) -> str: return f"RouteCard({'-'.join(self.stops)}, Var {self.variant_index})"
class Player: # Keep as is
    def __init__(self, player_id: int):
        self.player_id = player_id; self.hand: List[TileType] = []; self.line_card: Optional[LineCard] = None
        self.route_card: Optional[RouteCard] = None; self.player_state: PlayerState = PlayerState.LAYING_TRACK
        self.streetcar_position: Optional[Tuple[int, int]] = None; self.stops_visited_in_order: List[str] = []
    def __repr__(self) -> str: return f"Player {self.player_id} (State: {self.player_state.name}, Hand: {len(self.hand)})"

class Game:
    # Keep __init__, setup methods, print_board, helpers etc. from previous version
    def __init__(self, num_players: int):
        if not 2 <= num_players <= 6:
            raise ValueError("Players must be 2-6.")
        self.num_players = num_players; self.board = Board()
        self.players = [Player(i) for i in range(num_players)]
        self.tile_types: Dict[str, TileType] = { name: TileType(name=name, **details) for name, details in TILE_DEFINITIONS.items()}
        self.tile_draw_pile: List[TileType] = []; self.line_cards_pile: List[LineCard] = []
        self.active_player_index: int = 0; self.game_phase: GamePhase = GamePhase.SETUP
        self.current_turn: int = 0; self.first_player_to_finish_route: Optional[int] = None; self.actions_taken_this_turn: int = 0
        self.setup_game()

    def get_active_player(self) -> Player: return self.players[self.active_player_index]
    def __repr__(self) -> str: return (f"Game({self.num_players}p, Ph: {self.game_phase.name}, T: {self.current_turn}, P: {self.active_player_index}, Actions: {self.actions_taken_this_turn})")
    def print_board(self): print(self.board.simple_render(self))
    def setup_game(self): # Keep setup logic
        if self.game_phase != GamePhase.SETUP: return
        print("--- Starting Setup ---"); self._create_tile_and_line_piles(); self._deal_starting_hands(); self._deal_player_cards()
        self.game_phase = GamePhase.LAYING_TRACK; self.active_player_index = 0; self.current_turn = 1; print("--- Setup Complete ---")
    def _create_tile_and_line_piles(self): # Keep setup logic
        tile_counts = TILE_COUNTS_BASE.copy()
        if self.num_players >= 5:
            for name, count in TILE_COUNTS_5_PLUS_ADD.items(): tile_counts[name] = tile_counts.get(name, 0) + count
        self.tile_draw_pile = [];
        for name, count in tile_counts.items():
            tile_type = self.tile_types.get(name);
            if tile_type: self.tile_draw_pile.extend([tile_type] * count)
        random.shuffle(self.tile_draw_pile); self.line_cards_pile = [LineCard(i) for i in range(1, 7)]; random.shuffle(self.line_cards_pile)
    def _deal_starting_hands(self): # Keep corrected setup logic
        print("Dealing start hands..."); straight_type = self.tile_types['Straight']; curve_type = self.tile_types['Curve']
        needed_s_total = STARTING_HAND_TILES['Straight'] * self.num_players; needed_c_total = STARTING_HAND_TILES['Curve'] * self.num_players
        current_s = sum(1 for tile in self.tile_draw_pile if tile == straight_type); current_c = sum(1 for tile in self.tile_draw_pile if tile == curve_type)
        if current_s < needed_s_total or current_c < needed_c_total: raise RuntimeError(f"FATAL: Draw pile insufficient for starting hands!")
        for player in self.players:
            player.hand = []; dealt_s = 0; dealt_c = 0; indices_found = []
            for i in range(len(self.tile_draw_pile)):
                 tile = self.tile_draw_pile[i]
                 if i not in indices_found:
                     if tile == straight_type and dealt_s < STARTING_HAND_TILES['Straight']: indices_found.append(i); dealt_s += 1
                     elif tile == curve_type and dealt_c < STARTING_HAND_TILES['Curve']: indices_found.append(i); dealt_c += 1
                 if dealt_s == STARTING_HAND_TILES['Straight'] and dealt_c == STARTING_HAND_TILES['Curve']: break
            if dealt_s != STARTING_HAND_TILES['Straight'] or dealt_c != STARTING_HAND_TILES['Curve']: raise RuntimeError(f"Logic Error: Couldn't find start hand tiles for P{player.player_id}")
            indices_found.sort(reverse=True)
            for index in indices_found: player.hand.append(self.tile_draw_pile.pop(index))
            player.hand.reverse()
        print(f"Finished dealing start hands. Draw pile size: {len(self.tile_draw_pile)}")
    def _deal_player_cards(self): # Keep corrected setup logic
        print("Dealing player cards..."); available_variant_indices = list(range(len(ROUTE_CARD_VARIANTS))); random.shuffle(available_variant_indices)
        player_range = "2-4" if self.num_players <= 4 else "5-6"
        for player in self.players:
            if not self.line_cards_pile: raise RuntimeError("Ran out of Line cards!");
            if not available_variant_indices: raise RuntimeError("Ran out of Route card variants!")
            player.line_card = self.line_cards_pile.pop(); variant_index = available_variant_indices.pop()
            try: stops = ROUTE_CARD_VARIANTS[variant_index][player_range][player.line_card.line_number]
            except (KeyError, IndexError) as e: raise RuntimeError(f"Error lookup route stops: Var={variant_index}, Range={player_range}, Line={player.line_card.line_number}. Err: {e}")
            player.route_card = RouteCard(stops, variant_index)
        # print("Finished dealing cards.")
    def _rotate_direction(self, direction: str, angle: int) -> str:
        """Rotates a direction string ('N', 'E', 'S', 'W') clockwise."""
        directions = ['N', 'E', 'S', 'W']
        try:
            current_index = directions.index(direction)
        except ValueError:
             # This should ideally not happen if called with 'N','E','S','W'
             raise ValueError(f"Invalid direction string: {direction}")

        angle = angle % 360
        if angle % 90 != 0:
            # Invalid angle - should not proceed
            raise ValueError(f"Invalid rotation angle: {angle}. Must be multiple of 90.")

        # *** CORRECTED LOGIC: Calculate steps for valid angles ***
        steps = angle // 90
        new_index = (current_index + steps) % 4
        return directions[new_index]
    def get_effective_connections(self, tile_type: TileType, orientation: int) -> Dict[str, List[str]]: # Keep as is
        if orientation == 0: return tile_type.connections_base
        rotated_connections: Dict[str, List[str]] = {'N': [], 'E': [], 'S': [], 'W': []}
        base_connections = tile_type.connections_base
        for base_entry_dir, base_exit_dirs in base_connections.items():
            actual_entry_dir = self._rotate_direction(base_entry_dir, orientation)
            if actual_entry_dir not in rotated_connections: rotated_connections[actual_entry_dir] = []
            for base_exit_dir in base_exit_dirs:
                actual_exit_dir = self._rotate_direction(base_exit_dir, orientation)
                if actual_exit_dir not in rotated_connections[actual_entry_dir]: rotated_connections[actual_entry_dir].append(actual_exit_dir)
        # Ensure inner lists are sorted for consistent comparison
        for key in rotated_connections: rotated_connections[key].sort()
        return rotated_connections
    def _has_ns_straight(self, effective_connections: Dict[str, List[str]]) -> bool: return 'S' in effective_connections.get('N', [])
    def _has_ew_straight(self, effective_connections: Dict[str, List[str]]) -> bool: return 'W' in effective_connections.get('E', [])
    def check_placement_validity(self, tile_type: TileType, orientation: int, row: int, col: int) -> Tuple[bool, str]: # Keep corrected version
        if not self.board.is_valid_coordinate(row, col): return False, f"Placement Error ({row},{col}): Off board."
        if self.board.get_tile(row, col) is not None: return False, f"Placement Error ({row},{col}): Space occupied."
        effective_connections = self.get_effective_connections(tile_type, orientation)
        all_connected_dirs_out = set();
        for entry_dir, exit_dirs in effective_connections.items():
            if exit_dirs: all_connected_dirs_out.add(entry_dir); all_connected_dirs_out.update(exit_dirs)
        for direction in Direction:
            dir_str = direction.name; opposite_dir_str = Direction.opposite(direction).name; dr, dc = direction.value; nr, nc = row + dr, col + dc
            neighbor_tile = self.board.get_tile(nr, nc); is_neighbor_on_board = self.board.is_valid_coordinate(nr, nc)
            neighbor_building = self.board.get_building_at(nr, nc) if is_neighbor_on_board else None
            new_tile_connects_out_dir = dir_str in all_connected_dirs_out
            if neighbor_tile:
                neighbor_effective_connections = self.get_effective_connections(neighbor_tile.tile_type, neighbor_tile.orientation)
                neighbor_all_connected_dirs_out = set();
                for entry_dir, exit_dirs in neighbor_effective_connections.items():
                     if exit_dirs: neighbor_all_connected_dirs_out.add(entry_dir); neighbor_all_connected_dirs_out.update(exit_dirs)
                neighbor_connects_back = opposite_dir_str in neighbor_all_connected_dirs_out
                if new_tile_connects_out_dir != neighbor_connects_back:
                    reason = "connects" if new_tile_connects_out_dir else "doesn't connect"; neighbor_reason = "connects back" if neighbor_connects_back else "doesn't connect back"
                    msg = (f"Placement Error ({row},{col}): Tile {tile_type.name}({orientation}°) {reason} {dir_str}, but neighbor {neighbor_tile.tile_type.name}({neighbor_tile.orientation}°) at ({nr},{nc}) {neighbor_reason} {opposite_dir_str} (Mismatch/Blocking)."); return False, msg
            else:
                if new_tile_connects_out_dir:
                    if not is_neighbor_on_board:
                        is_terminal_spot = False # TODO: Terminal check
                        if not is_terminal_spot: msg = (f"Placement Error ({row},{col}): Tile leads off board towards {direction.name} at ({nr},{nc}) (not a valid terminal)."); return False, msg
                    elif neighbor_building: msg = (f"Placement Error ({row},{col}): Tile track points {dir_str} directly into building {neighbor_building} at ({nr},{nc})."); return False, msg
        return True, "Placement appears valid."
    def _check_and_place_stop_sign(self, placed_tile: PlacedTile, row: int, col: int): # Keep corrected version
        placed_tile.has_stop_sign = False; tile_connections = self.get_effective_connections(placed_tile.tile_type, placed_tile.orientation)
        for direction in Direction:
            dr, dc = direction.value; nr, nc = row + dr, col + dc; building_id = self.board.get_building_at(nr, nc)
            if building_id and building_id not in self.board.buildings_with_stops:
                has_parallel_track = False
                if direction == Direction.N or direction == Direction.S:
                    if self._has_ew_straight(tile_connections): has_parallel_track = True
                elif direction == Direction.E or direction == Direction.W:
                    if self._has_ns_straight(tile_connections): has_parallel_track = True
                if has_parallel_track:
                    placed_tile.has_stop_sign = True; self.board.buildings_with_stops.add(building_id)
                    print(f"--> Placed stop sign on tile ({row},{col}) for Building {building_id} (Parallel rule met)."); break
    def draw_tile(self, player: Player) -> bool: # Keep as is
        if not self.tile_draw_pile: print("Warning: Draw pile empty!"); return False
        tile = self.tile_draw_pile.pop(); player.hand.append(tile); return True
    def player_action_place_tile(self, player: Player, tile_type: TileType, orientation: int, row: int, col: int) -> bool: # Keep as is
        print(f"\nAttempting P{player.player_id} place: {tile_type.name}({orientation}°) at ({row},{col})")
        if tile_type not in player.hand: print(f"--> Action Error: Player {player.player_id} does not have {tile_type.name} in hand."); return False
        is_valid, message = self.check_placement_validity(tile_type, orientation, row, col);
        if not is_valid: print(f"--> {message}"); return False
        player.hand.remove(tile_type); placed_tile = PlacedTile(tile_type, orientation); self.board.set_tile(row, col, placed_tile)
        self._check_and_place_stop_sign(placed_tile, row, col); self.actions_taken_this_turn += 1
        print(f"--> SUCCESS placing {tile_type.name} at ({row},{col}). Actions taken: {self.actions_taken_this_turn}/{2}"); return True

    # --- Phase 3: Exchange Logic ---

    def _compare_connections(self, conn1: Dict[str, List[str]], conn2: Dict[str, List[str]]) -> bool:
        """Checks if two connection dictionaries are functionally identical."""
        # Normalize by converting to sets and comparing keys and sorted value lists
        keys1 = set(conn1.keys())
        keys2 = set(conn2.keys())
        if keys1 != keys2:
            return False
        for key in keys1:
            # Check if lists contain the same elements, order doesn't matter
            if set(conn1.get(key, [])) != set(conn2.get(key, [])):
                return False
        return True

    def check_exchange_validity(self, player: Player, new_tile_type: TileType, new_orientation: int, row: int, col: int) -> Tuple[bool, str]:
        """Checks if exchanging the tile at (row, col) is valid based on revised rules."""
        # Check 1: Tile exists?
        old_placed_tile = self.board.get_tile(row, col)
        if not old_placed_tile:
            return False, f"Exchange Error ({row},{col}): No tile exists."

        # Check 2: Is old tile swappable?
        if not old_placed_tile.tile_type.is_swappable:
            return False, f"Exchange Error ({row},{col}): Tile {old_placed_tile.tile_type.name} is not swappable."

        # Check 3: Does old tile have a stop sign?
        if old_placed_tile.has_stop_sign:
            return False, f"Exchange Error ({row},{col}): Cannot exchange tile with a stop sign."

        # Check 4: Player has the new tile?
        if new_tile_type not in player.hand:
             return False, f"Exchange Error: Player does not have {new_tile_type.name} in hand."

        # --- Connection Checks ---
        old_connections = self.get_effective_connections(old_placed_tile.tile_type, old_placed_tile.orientation)
        new_connections = self.get_effective_connections(new_tile_type, new_orientation)

        # Check 5: Preservation of OLD connections
        old_connected_pairs = set()
        for entry, exits in old_connections.items():
            for exit_dir in exits:
                 # Store as sorted tuple to handle bidirectional check easily
                 old_connected_pairs.add(tuple(sorted((entry, exit_dir))))

        new_connected_pairs = set()
        for entry, exits in new_connections.items():
            for exit_dir in exits:
                 new_connected_pairs.add(tuple(sorted((entry, exit_dir))))

        if not old_connected_pairs.issubset(new_connected_pairs):
            # Find missing connections for better error message (optional)
            missing = old_connected_pairs - new_connected_pairs
            msg = (f"Exchange Error ({row},{col}): New tile {new_tile_type.name}({new_orientation}°) "
                   f"does not preserve all connections of old tile "
                   f"{old_placed_tile.tile_type.name}({old_placed_tile.orientation}°). Missing: {missing}")
            return False, msg

        # Check 6: Validity of NEW connections added
        added_connections_dirs = set() # Directions where a new connection points *out*
        for pair in new_connected_pairs - old_connected_pairs:
             added_connections_dirs.add(pair[0])
             added_connections_dirs.add(pair[1])

        for direction_str in added_connections_dirs:
            direction = Direction.from_str(direction_str)
            opposite_dir_str = Direction.opposite(direction).name
            dr, dc = direction.value
            nr, nc = row + dr, col + dc # Neighbor coordinate for the new connection

            neighbor_tile = self.board.get_tile(nr, nc)
            is_neighbor_on_board = self.board.is_valid_coordinate(nr, nc)
            neighbor_building = self.board.get_building_at(nr, nc) if is_neighbor_on_board else None

            # Does this *newly added* connection point OUT in this direction?
            # (We know it does by definition of added_connections_dirs)

            if neighbor_tile:
                neighbor_effective_connections = self.get_effective_connections(
                    neighbor_tile.tile_type, neighbor_tile.orientation
                )
                neighbor_connects_back = opposite_dir_str in [
                    exit_dir for exits in neighbor_effective_connections.values() for exit_dir in exits
                ]
                # If the neighbor *doesn't* connect back, this new connection is invalid
                if not neighbor_connects_back:
                    msg = (f"Exchange Error ({row},{col}): New connection {direction_str} from {new_tile_type.name}"
                           f"({new_orientation}°) is invalid, neighbor {neighbor_tile.tile_type.name}"
                           f"({neighbor_tile.orientation}°) at ({nr},{nc}) doesn't connect back {opposite_dir_str}.")
                    return False, msg
            else: # No neighbor tile
                if not is_neighbor_on_board: # Points off board
                    is_terminal_spot = False # TODO: Terminal check
                    if not is_terminal_spot:
                         msg = (f"Exchange Error ({row},{col}): New connection {direction_str} from {new_tile_type.name}"
                               f"({new_orientation}°) leads off board (not a valid terminal).")
                         return False, msg
                elif neighbor_building: # Points into building
                    msg = (f"Exchange Error ({row},{col}): New connection {direction_str} from {new_tile_type.name}"
                           f"({new_orientation}°) points into building {neighbor_building} at ({nr},{nc}).")
                    return False, msg
                # else: points into empty space -> VALID

        return True, "Exchange appears valid."


    def player_action_exchange_tile(self, player: Player, new_tile_type: TileType, new_orientation: int, row: int, col: int) -> bool:
        """Player attempts to exchange a tile based on revised rules."""
        print(f"\nAttempting P{player.player_id} exchange: {new_tile_type.name}({new_orientation}°) at ({row},{col})")

        # Use the revised validity check
        is_valid, message = self.check_exchange_validity(player, new_tile_type, new_orientation, row, col)

        if not is_valid:
            print(f"--> {message}")
            return False

        # --- Perform exchange ---
        old_placed_tile = self.board.get_tile(row, col)
        if old_placed_tile is None: # Safety check
             print(f"--> Internal Error: Tile at ({row},{col}) disappeared before exchange.")
             return False

        # Swap tiles between board and hand
        player.hand.remove(new_tile_type)
        player.hand.append(old_placed_tile.tile_type)
        new_placed_tile = PlacedTile(new_tile_type, new_orientation)
        # Stop sign check/transfer is NOT needed due to exchange rules
        self.board.set_tile(row, col, new_placed_tile)

        self.actions_taken_this_turn += 1
        print(f"--> SUCCESS exchanging {old_placed_tile.tile_type.name}({old_placed_tile.orientation}°) "
              f"for {new_tile_type.name}({new_orientation}°) at ({row},{col}). "
              f"Actions taken: {self.actions_taken_this_turn}/{2}")

        return True

    # --- End Turn Logic ---
    def end_player_turn(self):
        # Keep end_player_turn as is
        active_player = self.get_active_player();
        if active_player.player_state != PlayerState.LAYING_TRACK: print(f"Warning: Cannot end turn for Player {active_player.player_id} in state {active_player.player_state}"); return
        draw_count = 0
        while len(active_player.hand) < 5 and self.tile_draw_pile:
             if self.draw_tile(active_player): draw_count += 1
        if draw_count > 0: print(f"Player {active_player.player_id} drew {draw_count} tiles (Hand: {len(active_player.hand)}).")
        self.active_player_index = (self.active_player_index + 1) % self.num_players
        if self.active_player_index == 0: self.current_turn += 1
        self.actions_taken_this_turn = 0; print(f"\n--- End Turn - Starting Turn {self.current_turn} for Player {self.active_player_index} ---")



# --- Example Initialization and Testing (Revised Exchange Tests) ---
if __name__ == "__main__":
    print("\n--- Testing Phase 3: Tile Exchange (Corrected Exchange Rule) ---\n")
    try:
        game = Game(num_players=2)
        p0 = game.players[0]; p1 = game.players[1]
        straight = game.tile_types['Straight'] # N-S
        curve = game.tile_types['Curve'] # N-E
        slc = game.tile_types['StraightLeftCurve'] # N-S, S-W
        src = game.tile_types['StraightRightCurve'] # N-S, S-E
        tree_cross = game.tile_types['Tree_Crossroad']

        # Force hands AFTER setup for tests
        p0.hand = [straight, slc, slc, src, straight, curve]
        p1.hand = [tree_cross, straight, curve, curve, curve, curve]

        print("Initial Board & Hands:")
        game.print_board()
        print(f"P0 Hand: {[t.name for t in p0.hand]}")
        print(f"P1 Hand: {[t.name for t in p1.hand]}")
        print("-" * 20)

        # --- Setup board state ---
        print(f"\n--- P0 Turn {game.current_turn} (Setup) ---")
        # Place Straight(0) N-S at (5,5) - Swappable, No Stop
        game.player_action_place_tile(p0, straight, 0, 5, 5)
        # Place Curve(0) N-E at (4,5) - Swappable, No Stop
        game.player_action_place_tile(p0, curve, 0, 4, 5)
        game.end_player_turn()
        print(f"\n--- P1 Turn {game.current_turn} (Setup) ---")
        # Place Straight(0) N-S at (6,2) - Gets Stop Sign L
        game.player_action_place_tile(p1, straight, 0, 6, 2)
        # Place Tree_Crossroad at (8,8) - Non-swappable
        game.player_action_place_tile(p1, tree_cross, 0, 8, 8)
        game.end_player_turn()

        print("\nBoard state before P0 exchange tests:")
        game.print_board()
        print(f"P0 Hand: {[t.name for t in p0.hand]}") # After draw
        print(f"P1 Hand: {[t.name for t in p1.hand]}") # After draw
        print("-" * 20)

        # --- P0 Turn for Exchange Tests ---
        print(f"\n--- P0 Turn {game.current_turn} (Exchange Tests) ---")
        # Ensure P0 has needed tiles
        assert slc in p0.hand, "P0 missing SLC"
        assert src in p0.hand, "P0 missing SRC"
        assert curve in p0.hand, "P0 missing Curve"

        # Test 1: Invalid - Target non-swappable (Tree)
        success = game.player_action_exchange_tile(p0, slc, 0, 8, 8) # Target Tree at (8,8)
        assert not success, "Test Fail: Exchange non-swappable"
        assert game.actions_taken_this_turn == 0

        # Test 2: Invalid - Target has stop sign
        success = game.player_action_exchange_tile(p0, slc, 0, 6, 2) # Target Straight at (6,2)
        assert not success, "Test Fail: Exchange tile with stop"
        assert game.actions_taken_this_turn == 0

        # Test 3: Invalid - Missing required connection
        # Target: Straight(0) N-S at (5,5). Replace with Curve(0) N-E. Fails preservation.
        success = game.player_action_exchange_tile(p0, curve, 0, 5, 5)
        assert not success, "Test Fail: Exchange missing connection (S->N)"
        assert game.actions_taken_this_turn == 0

        # Test 4: Valid - Adding a valid connection
        # Target: Straight(0) N-S at (5,5). Replace with SLC(0) N-S & S-W.
        # Preserves N-S. Adds S-W. Check neighbor West (5,4) = empty. Valid.
        # Action 1
        original_hand_size = len(p0.hand)
        old_tile = game.board.get_tile(5,5).tile_type
        success = game.player_action_exchange_tile(p0, slc, 0, 5, 5)
        assert success, "Test Fail: Exchange valid add connection (Straight -> SLC)"
        assert game.actions_taken_this_turn == 1
        assert game.board.get_tile(5,5).tile_type == slc
        assert old_tile in p0.hand
        assert len(p0.hand) == original_hand_size
        game.print_board()

        # Test 5: Invalid - Added connection is invalid (Mismatch/Block)
        # Target: Curve(0) N-E at (4,5). Replace with SLC(0) N-S & S-W.
        # Preserves N-E? NO. Fails preservation.
        success = game.player_action_exchange_tile(p0, slc, 0, 4, 5)
        assert not success, "Test Fail: Exchange invalid add (Curve -> SLC) - Preservation Fail"
        assert game.actions_taken_this_turn == 1 # Still 1 action

        # Test 6: Invalid - Added connection points into building
        # Let's place SLC(90) [E-W, W-N] at (6,4) to test new N connection into L(6,3)
        # First, place a tile P0 can exchange at (6,4) - e.g., N-S straight
        # Action 2: Place Straight(90) N-S at (6,4)
        success_place = game.player_action_place_tile(p0, straight, 0, 6, 4)
        assert success_place, "Test Fail: Placement for Test 6 setup"
        assert game.actions_taken_this_turn == 2
        game.print_board()
        # Now attempt the exchange in the *next* turn

        game.end_player_turn() # P0 draws
        game.end_player_turn() # Skip P1's turn, back to P0

        print(f"\n--- P0 Turn {game.current_turn} (Exchange Test 6 Cont.) ---")
        print(f"P0 Hand: {[t.name for t in p0.hand]}")
        assert slc in p0.hand, "P0 needs SLC for Test 6"

        # Target: Straight(90) E-W at (6,4). Replace with SLC(90) E-W & W-N.
        # Preserves E-W. Adds W-N. Neighbor North is L(6,3) Building. -> INVALID.
        success = game.player_action_exchange_tile(p0, slc, 0, 6, 4)
        assert not success, "Test Fail: Exchange invalid add (Points into Building L)"
        assert game.actions_taken_this_turn == 0 # No action taken this turn yet
        assert game.board.get_tile(6,4).tile_type == straight # Verify tile didn't change

        print("\n--- Phase 3 All Tests OK (Corrected Exchange Rule) ---")

    except (ValueError, RuntimeError, AssertionError) as e:
        print(f"\n--- ERROR during Phase 3 Test ---")
        print(f"Error Type: {type(e).__name__}")
        print(e)
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n--- UNEXPECTED ERROR during Phase 3 Test ---")
        print(f"Error Type: {type(e).__name__}")
        print(e)
        import traceback
        traceback.print_exc()