# -*- coding: utf-8 -*-
import random
from enum import Enum, auto
from typing import List, Dict, Tuple, Optional, Set, Any

# --- Constants ---
GRID_ROWS = 12
GRID_COLS = 12
BUILDING_COORDS: Dict[str, Tuple[int, int]] = {
    'A': (7, 11), 'B': (10, 8), 'C': (11, 4), 'D': (7, 1),
    'E': (4, 0),  'F': (1, 3),  'G': (0, 7),  'H': (3, 10),
    'I': (5, 8),  'K': (8, 6),  'L': (6, 3),  'M': (3, 5),
}
TILE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "Straight":           {"connections": [['N', 'S']], "is_swappable": True}, # Has N-S
    "Curve":              {"connections": [['N', 'E']], "is_swappable": True}, # No straight
    "StraightLeftCurve":  {"connections": [['N', 'S'], ['S', 'W']], "is_swappable": True}, # Has N-S
    "StraightRightCurve": {"connections": [['N', 'S'], ['S', 'E']], "is_swappable": True}, # Has N-S
    "DoubleCurveY":       {"connections": [['N', 'W'], ['N', 'E']], "is_swappable": True}, # No straight
    "DiagonalCurve":      {"connections": [['S', 'W'], ['N', 'E']], "is_swappable": True}, # No straight
    "Tree_JunctionTop":      {"connections": [['E', 'W'], ['W', 'N'], ['N', 'E']], "is_swappable": False},# Has E-W
    "Tree_JunctionRight":    {"connections": [['E', 'W'], ['N', 'E'], ['S', 'E']], "is_swappable": False},# Has E-W
    "Tree_Roundabout":       {"connections": [['W', 'N'], ['N', 'E'], ['E', 'S'], ['S', 'W']], "is_swappable": False},# No straight
    "Tree_Crossroad":        {"connections": [['N', 'S'], ['E', 'W']], "is_swappable": False},# Has N-S AND E-W
    "Tree_StraightDiagonal1":{"connections": [['N', 'S'], ['S', 'W'], ['N', 'E']], "is_swappable": False},# Has N-S
    "Tree_StraightDiagonal2":{"connections": [['N', 'S'], ['N', 'W'], ['S', 'E']], "is_swappable": False},# Has N-S
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
        self.connections = self._process_connections(connections)
        self.is_swappable = is_swappable

    def _process_connections(self, raw_connections: List[List[str]]) -> Dict[str, List[str]]:
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
        return conn_map

    def __repr__(self) -> str:
        return f"TileType({self.name}, Swappable={self.is_swappable})"

class PlacedTile:
    def __init__(self, tile_type: TileType, orientation: int = 0):
        self.tile_type = tile_type
        if orientation % 90 != 0:
            raise ValueError(f"Orientation must be multiple of 90, got {orientation}")
        self.orientation = orientation % 360
        self.has_stop_sign: bool = False

    def __repr__(self) -> str:
        return f"Placed({self.tile_type.name}, {self.orientation}deg, Stop:{self.has_stop_sign})"

class Board:
    def __init__(self, rows: int = GRID_ROWS, cols: int = GRID_COLS):
        self.rows = rows
        self.cols = cols
        self.grid: List[List[Optional[PlacedTile]]] = [
            [None for _ in range(cols)] for _ in range(rows)
        ]
        self.building_coords = BUILDING_COORDS
        self.coord_to_building: Dict[Tuple[int, int], str] = {
            v: k for k, v in BUILDING_COORDS.items()
        }
        self.buildings_with_stops: Set[str] = set() # Tracks building IDs

    def is_valid_coordinate(self, row: int, col: int) -> bool:
        return 0 <= row < self.rows and 0 <= col < self.cols

    def get_tile(self, row: int, col: int) -> Optional[PlacedTile]:
        if self.is_valid_coordinate(row, col):
            return self.grid[row][col]
        return None

    def set_tile(self, row: int, col: int, tile: Optional[PlacedTile]):
        if not self.is_valid_coordinate(row, col):
            raise IndexError(f"Coordinate ({row},{col}) is out of board bounds.")
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

    def simple_render(self, game=None) -> str:
        # Using cleaner symbols
        conn_symbols = {
            frozenset(['N', 'S']): '│', frozenset(['E', 'W']): '─',
            frozenset(['N', 'E']): '└', frozenset(['N', 'W']): '┘',
            frozenset(['S', 'E']): '┌', frozenset(['S', 'W']): '┐',
            frozenset(['N', 'S', 'W']): '┤', frozenset(['N', 'S', 'E']): '├',
            frozenset(['E', 'W', 'N']): '┴', frozenset(['E', 'W', 'S']): '┬',
            # Combined symbols need careful checking based on type/orientation if needed
            frozenset(['N', 'W', 'E']): 'V', # Example for DoubleCurveY base
            frozenset(['S', 'W', 'N', 'E']): 'X', # Example for DiagonalCurve base
            frozenset(['N', 'S', 'E', 'W']): '┼', # Crossroad
            frozenset(): '.',
        }
        default_symbol = '?'
        col_width = 5
        separator = "│" # Use box drawing separator
        cell_total_width = col_width + len(separator)

        # --- Header Row ---
        header_parts = [" " * 3] # Space for "R │"
        for c in range(self.cols):
            col_num_str = str(c)
            padding_total = col_width - len(col_num_str)
            padding_left = padding_total // 2
            padding_right = padding_total - padding_left
            header_parts.append(" " * padding_left + col_num_str + " " * padding_right + separator)
        header = "".join(header_parts) + "\n"

        # --- Top Border ---
        h_line = "─" * col_width
        top_connector = "┬"
        top_border_line = h_line + (top_connector + h_line) * (self.cols - 1)
        top_border = "  ╭" + top_border_line + "╮\n" # Start and end corners

        board_str = header + top_border

        # --- Board Rows ---
        for r in range(self.rows):
            row_str_parts = [f"{r:<2}{separator}"] # Row number and first separator
            for c in range(self.cols):
                cell_content = ""
                tile = self.grid[r][c]
                if tile:
                    stop = "S" if tile.has_stop_sign else ""
                    symbol = default_symbol
                    if game: # Try to get a symbol based on effective connections
                        try:
                            connections = game.get_effective_connections(tile.tile_type, tile.orientation)
                            connected_dirs = set()
                            for entry, exits in connections.items():
                                if exits:
                                    connected_dirs.add(entry)
                                    connected_dirs.update(exits)
                            symbol = conn_symbols.get(frozenset(connected_dirs), default_symbol)
                            # Fallback for complex tiles not easily mapped by simple connections
                            if symbol == default_symbol:
                                if "Straight" in tile.tile_type.name and "Curve" in tile.tile_type.name: symbol = "T"
                                elif "Junction" in tile.tile_type.name: symbol = "J"
                                elif "Diagonal" in tile.tile_type.name: symbol = "X"
                                elif "Roundabout" in tile.tile_type.name: symbol = "O"
                                elif "Crossroad" in tile.tile_type.name: symbol = "┼" # Correct symbol
                                elif tile.tile_type.name == "Straight": symbol = '│' if tile.orientation in [0, 180] else '─'
                                elif tile.tile_type.name == "Curve": symbol = 'C' # Needs orientation logic
                                else: symbol = tile.tile_type.name[0] # Last resort

                        except Exception:
                            symbol = 'E' # Error during symbol lookup
                    else:
                        symbol = tile.tile_type.name[0] if tile.tile_type.name else '?'
                    cell_content = f"{symbol}{stop}"
                else:
                    building = self.get_building_at(r, c)
                    cell_content = f"[{building}]" if building else "·" # Use mid-dot for empty

                padding_total = col_width - len(cell_content)
                padding_left = padding_total // 2
                padding_right = padding_total - padding_left
                row_str_parts.append(" " * padding_left + cell_content + " " * padding_right + separator)

            board_str += "".join(row_str_parts) + "\n"
            # Row separator border
            if r < self.rows - 1:
                mid_connector = "┼"
                mid_border_line = h_line + (mid_connector + h_line) * (self.cols - 1)
                board_str += "  ├" + mid_border_line + "┤\n" # Start/end T connectors
            else: # Bottom border
                bot_connector = "┴"
                bot_border_line = h_line + (bot_connector + h_line) * (self.cols - 1)
                board_str += "  ╰" + bot_border_line + "╯\n" # Start/end bottom corners

        return board_str

class LineCard:
    def __init__(self, line_number: int):
        self.line_number = line_number
    def __repr__(self) -> str:
        return f"LineCard(Line {self.line_number})"

class RouteCard:
    def __init__(self, stops: List[str], variant_index: int):
        self.stops = stops
        self.variant_index = variant_index
    def __repr__(self) -> str:
        return f"RouteCard({'-'.join(self.stops)}, Var {self.variant_index})"

class Player:
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.hand: List[TileType] = []
        self.line_card: Optional[LineCard] = None
        self.route_card: Optional[RouteCard] = None
        self.player_state: PlayerState = PlayerState.LAYING_TRACK
        self.streetcar_position: Optional[Tuple[int, int]] = None
        self.stops_visited_in_order: List[str] = []
    def __repr__(self) -> str:
        return f"Player {self.player_id} (State: {self.player_state.name}, Hand: {len(self.hand)})"

class Game:
    def __init__(self, num_players: int):
        if not 2 <= num_players <= 6:
            raise ValueError("Players must be 2-6.")
        self.num_players = num_players
        self.board = Board()
        self.players = [Player(i) for i in range(num_players)]
        self.tile_types: Dict[str, TileType] = {
            name: TileType(name=name, **details)
            for name, details in TILE_DEFINITIONS.items()
        }
        self.tile_draw_pile: List[TileType] = []
        self.line_cards_pile: List[LineCard] = []
        self.active_player_index: int = 0
        self.game_phase: GamePhase = GamePhase.SETUP
        self.current_turn: int = 0
        self.first_player_to_finish_route: Optional[int] = None
        self.actions_taken_this_turn: int = 0
        self.setup_game()

    def get_active_player(self) -> Player:
        return self.players[self.active_player_index]

    def __repr__(self) -> str:
        return (f"Game({self.num_players}p, Ph: {self.game_phase.name}, "
                f"T: {self.current_turn}, P: {self.active_player_index}, "
                f"Actions: {self.actions_taken_this_turn})")

    def print_board(self):
        print(self.board.simple_render(self))

    def setup_game(self):
        if self.game_phase != GamePhase.SETUP:
            print("Warning: Setup called when not in SETUP phase.")
            return
        print("--- Starting Setup ---")
        self._create_tile_and_line_piles()
        self._deal_starting_hands()
        self._deal_player_cards()
        self.game_phase = GamePhase.LAYING_TRACK
        self.active_player_index = 0
        self.current_turn = 1
        print("--- Setup Complete ---")

    def _create_tile_and_line_piles(self):
        tile_counts = TILE_COUNTS_BASE.copy()
        if self.num_players >= 5:
            for name, count in TILE_COUNTS_5_PLUS_ADD.items():
                tile_counts[name] = tile_counts.get(name, 0) + count
        self.tile_draw_pile = []
        for name, count in tile_counts.items():
            tile_type = self.tile_types.get(name)
            if tile_type:
                self.tile_draw_pile.extend([tile_type] * count)
            else:
                # This should not happen if TILE_DEFINITIONS is correct
                print(f"Warning: Tile type '{name}' from counts not found in definitions.")
        random.shuffle(self.tile_draw_pile)
        self.line_cards_pile = [LineCard(i) for i in range(1, 7)]
        random.shuffle(self.line_cards_pile)

    def _deal_starting_hands(self):
        print("Dealing start hands...")
        straight_type = self.tile_types['Straight']
        curve_type = self.tile_types['Curve']
        needed_straights_total = STARTING_HAND_TILES['Straight'] * self.num_players
        needed_curves_total = STARTING_HAND_TILES['Curve'] * self.num_players
        current_straights = sum(1 for tile in self.tile_draw_pile if tile == straight_type)
        current_curves = sum(1 for tile in self.tile_draw_pile if tile == curve_type)

        if current_straights < needed_straights_total or current_curves < needed_curves_total:
             raise RuntimeError(f"FATAL: Draw pile insufficient for starting hands!")

        for player in self.players:
            player.hand = []
            dealt_straights = 0
            dealt_curves = 0
            indices_found = []
            # Iterate copy to allow safe removal later? No, iterate original and track indices.
            for i in range(len(self.tile_draw_pile)):
                 tile = self.tile_draw_pile[i]
                 if i not in indices_found: # Ensure we don't pick the same index twice
                     if tile == straight_type and dealt_straights < STARTING_HAND_TILES['Straight']:
                         indices_found.append(i)
                         dealt_straights += 1
                     elif tile == curve_type and dealt_curves < STARTING_HAND_TILES['Curve']:
                         indices_found.append(i)
                         dealt_curves += 1
                 if dealt_straights == STARTING_HAND_TILES['Straight'] and dealt_curves == STARTING_HAND_TILES['Curve']:
                     break # Found enough for this player

            if dealt_straights != STARTING_HAND_TILES['Straight'] or dealt_curves != STARTING_HAND_TILES['Curve']:
                 raise RuntimeError(f"Logic Error: Couldn't find needed start hand tiles for P{player.player_id}")

            # Add found tiles to hand (lookup by index now) and remove from draw pile
            indices_found.sort(reverse=True) # Sort for safe removal from end
            for index in indices_found:
                 player.hand.append(self.tile_draw_pile.pop(index)) # Pop removes and returns
            # Reverse hand so order isn't based on removal order (cosmetic)
            player.hand.reverse()


        print(f"Finished dealing start hands. Draw pile size: {len(self.tile_draw_pile)}")

    def _deal_player_cards(self):
        print("Dealing player cards...")
        available_variant_indices = list(range(len(ROUTE_CARD_VARIANTS)))
        random.shuffle(available_variant_indices)
        player_range = "2-4" if self.num_players <= 4 else "5-6"

        for player in self.players:
            if not self.line_cards_pile:
                 raise RuntimeError("Ran out of Line cards during dealing!")
            if not available_variant_indices:
                 raise RuntimeError("Ran out of Route card variants during dealing!")

            player.line_card = self.line_cards_pile.pop()
            variant_index = available_variant_indices.pop()
            try:
                stops = ROUTE_CARD_VARIANTS[variant_index][player_range][player.line_card.line_number]
            except (KeyError, IndexError) as e:
                raise RuntimeError(f"Error looking up route stops: Var={variant_index}, Range={player_range}, Line={player.line_card.line_number}. Error: {e}")
            player.route_card = RouteCard(stops, variant_index)
        # print("Finished dealing cards.")

    def _rotate_direction(self, direction: str, angle: int) -> str:
        directions = ['N', 'E', 'S', 'W']
        try:
            current_index = directions.index(direction)
        except ValueError:
             raise ValueError(f"Invalid direction string: {direction}")
        angle = angle % 360
        if angle % 90 != 0:
            raise ValueError(f"Invalid rotation angle: {angle}. Must be multiple of 90.")
        steps = angle // 90
        new_index = (current_index + steps) % 4
        return directions[new_index]

    def get_effective_connections(self, tile_type: TileType, orientation: int) -> Dict[str, List[str]]:
        if orientation == 0:
            return tile_type.connections # Use original if no rotation

        rotated_connections: Dict[str, List[str]] = {'N': [], 'E': [], 'S': [], 'W': []}
        base_connections = tile_type.connections

        for base_entry_dir, base_exit_dirs in base_connections.items():
            actual_entry_dir = self._rotate_direction(base_entry_dir, orientation)
            # Ensure the entry direction key exists
            if actual_entry_dir not in rotated_connections:
                 rotated_connections[actual_entry_dir] = []

            for base_exit_dir in base_exit_dirs:
                actual_exit_dir = self._rotate_direction(base_exit_dir, orientation)
                # Add exit direction if not already present for this entry
                if actual_exit_dir not in rotated_connections[actual_entry_dir]:
                    rotated_connections[actual_entry_dir].append(actual_exit_dir)
        return rotated_connections

    def _has_ns_straight(self, effective_connections: Dict[str, List[str]]) -> bool:
        """Checks if the effective connections include a North-South straight path."""
        return 'S' in effective_connections.get('N', []) # N connects S is sufficient

    def _has_ew_straight(self, effective_connections: Dict[str, List[str]]) -> bool:
        """Checks if the effective connections include an East-West straight path."""
        return 'W' in effective_connections.get('E', []) # E connects W is sufficient

    def check_placement_validity(self, tile_type: TileType, orientation: int, row: int, col: int) -> Tuple[bool, str]:
        """ Checks rules for placing a NEW tile onto an EMPTY space. Returns (isValid, message)."""
        if not self.board.is_valid_coordinate(row, col):
            return False, f"Placement Error ({row},{col}): Off board."
        if self.board.get_tile(row, col) is not None:
            return False, f"Placement Error ({row},{col}): Space occupied."

        effective_connections = self.get_effective_connections(tile_type, orientation)

        # Determine all directions this tile connects *out* to
        all_connected_dirs_out = set()
        for entry_dir, exit_dirs in effective_connections.items():
            if exit_dirs: # If there are exits from this entry
                all_connected_dirs_out.add(entry_dir) # The entry implies a connection
                all_connected_dirs_out.update(exit_dirs) # Add all exits

        for direction in Direction:
            dir_str = direction.name
            opposite_dir_str = Direction.opposite(direction).name
            dr, dc = direction.value
            nr, nc = row + dr, col + dc # Neighbor coordinate

            neighbor_tile = self.board.get_tile(nr, nc)
            is_neighbor_on_board = self.board.is_valid_coordinate(nr, nc)
            neighbor_building = self.board.get_building_at(nr, nc) if is_neighbor_on_board else None

            # *** Corrected Check: Does the new tile connect out in this 'direction'? ***
            new_tile_connects_out_dir = dir_str in all_connected_dirs_out

            if neighbor_tile:
                neighbor_effective_connections = self.get_effective_connections(
                    neighbor_tile.tile_type, neighbor_tile.orientation
                )
                # Determine all directions the neighbor connects *out* to
                neighbor_all_connected_dirs_out = set()
                for entry_dir, exit_dirs in neighbor_effective_connections.items():
                     if exit_dirs:
                          neighbor_all_connected_dirs_out.add(entry_dir)
                          neighbor_all_connected_dirs_out.update(exit_dirs)

                # Does the *neighbor* connect *back* towards the new tile's location?
                neighbor_connects_back = opposite_dir_str in neighbor_all_connected_dirs_out

                # Rule D Check: INVALID if connections don't match at the border
                if new_tile_connects_out_dir != neighbor_connects_back:
                    reason = "connects" if new_tile_connects_out_dir else "doesn't connect"
                    neighbor_reason = "connects back" if neighbor_connects_back else "doesn't connect back"
                    msg = (f"Placement Error ({row},{col}): Tile {tile_type.name}({orientation}°) "
                           f"{reason} {dir_str}, but neighbor {neighbor_tile.tile_type.name}"
                           f"({neighbor_tile.orientation}°) at ({nr},{nc}) {neighbor_reason} {opposite_dir_str} (Mismatch/Blocking).")
                    return False, msg

            else: # No neighbor tile
                if new_tile_connects_out_dir: # New tile points towards (nr, nc)...
                    if not is_neighbor_on_board: # ...and (nr, nc) is off the board
                        is_terminal_spot = False # TODO: Implement terminal check
                        if not is_terminal_spot:
                             msg = (f"Placement Error ({row},{col}): Tile leads off board "
                                   f"towards {direction.name} at ({nr},{nc}) (not a valid terminal).")
                             return False, msg
                    elif neighbor_building: # ...and (nr, nc) IS a building location
                        # Rule B Check: Points directly into building
                        msg = (f"Placement Error ({row},{col}): Tile track points {dir_str} "
                               f"directly into building {neighbor_building} at ({nr},{nc}).")
                        return False, msg
                    # else: points into an empty space ON the board -> VALID

        # If all neighbor checks passed for all directions
        return True, "Placement appears valid."

    # --- Stop Sign Logic (Revised Helper) ---
    def _check_and_place_stop_sign(self, placed_tile: PlacedTile, row: int, col: int):
        """Checks orthogonal neighbors and applies stop sign based on refined parallel track rule."""
        placed_tile.has_stop_sign = False # Default

        tile_connections = self.get_effective_connections(placed_tile.tile_type, placed_tile.orientation)

        for direction in Direction: # Check N, E, S, W neighbors relative to placed tile (r, c)
            dr, dc = direction.value
            nr, nc = row + dr, col + dc # Neighbor coordinate (potential building location)

            building_id = self.board.get_building_at(nr, nc)

            # Condition 1 & 2: Is neighbor a building without a stop sign?
            if building_id and building_id not in self.board.buildings_with_stops:

                # Condition 3: Does placed tile have PARALLEL straight track?
                has_parallel_track = False
                if direction == Direction.N or direction == Direction.S:
                    # Building N or S => Need E-W track on placed tile
                    if self._has_ew_straight(tile_connections):
                        has_parallel_track = True
                elif direction == Direction.E or direction == Direction.W:
                    # Building E or W => Need N-S track on placed tile
                    if self._has_ns_straight(tile_connections):
                        has_parallel_track = True

                # If all conditions met, place stop sign
                if has_parallel_track:
                    placed_tile.has_stop_sign = True
                    self.board.buildings_with_stops.add(building_id)
                    print(f"--> Placed stop sign on tile ({row},{col}) for Building {building_id} (Parallel rule met).")
                    break # Only one stop sign per tile placement
            # else: No building, or building already has stop sign, or parallel rule not met

    # --- Draw Tile Logic ---
    def draw_tile(self, player: Player) -> bool:
        if not self.tile_draw_pile:
            print("Warning: Draw pile empty!")
            return False
        tile = self.tile_draw_pile.pop()
        player.hand.append(tile)
        return True

    # --- Player Action: Place Tile ---
    def player_action_place_tile(self, player: Player, tile_type: TileType, orientation: int, row: int, col: int) -> bool:
        """Player attempts to place a tile as one of their actions."""
        print(f"\nAttempting P{player.player_id} place: {tile_type.name}({orientation}°) at ({row},{col})")

        if tile_type not in player.hand:
            print(f"--> Action Error: Player {player.player_id} does not have {tile_type.name} in hand.")
            return False

        is_valid, message = self.check_placement_validity(tile_type, orientation, row, col)

        if not is_valid:
            print(f"--> {message}")
            return False

        # --- Perform placement ---
        player.hand.remove(tile_type)
        placed_tile = PlacedTile(tile_type, orientation)
        self.board.set_tile(row, col, placed_tile)
        self._check_and_place_stop_sign(placed_tile, row, col) # Use refined logic

        self.actions_taken_this_turn += 1
        print(f"--> SUCCESS placing {tile_type.name} at ({row},{col}). Actions taken: {self.actions_taken_this_turn}/{2}")

        return True

    # TODO: Implement player_action_exchange_tile

    # --- End Turn Logic ---
    def end_player_turn(self):
        """Handles drawing tiles and advancing to the next player."""
        active_player = self.get_active_player()
        if active_player.player_state != PlayerState.LAYING_TRACK:
            print(f"Warning: Cannot end turn for Player {active_player.player_id} in state {active_player.player_state}")
            # TODO: Handle driving phase turn end later
            return

        # Draw tiles back up to 5
        draw_count = 0
        while len(active_player.hand) < 5 and self.tile_draw_pile:
             if self.draw_tile(active_player):
                  draw_count += 1
        if draw_count > 0:
             print(f"Player {active_player.player_id} drew {draw_count} tiles (Hand: {len(active_player.hand)}).")

        # Advance turn
        self.active_player_index = (self.active_player_index + 1) % self.num_players
        if self.active_player_index == 0:
            self.current_turn += 1
        self.actions_taken_this_turn = 0

        print(f"\n--- End Turn - Starting Turn {self.current_turn} for Player {self.active_player_index} ---")


# --- Keep ALL classes and methods as they are NOW (with corrected check_placement_validity) ---

# --- Example Initialization and Testing ---
if __name__ == "__main__":
    print("\n--- Testing Phase 2: Tile Placement (Corrected Crossroad Test) ---\n")
    try:
        game = Game(num_players=2)
        player0 = game.players[0]
        player1 = game.players[1]
        straight = game.tile_types['Straight'] # N-S
        curve = game.tile_types['Curve'] # N-E
        crossroad = game.tile_types['Tree_Crossroad'] # N-S & E-W
        tree_ew_junc = game.tile_types['Tree_JunctionTop'] # E-W straight

        # Force hands for specific tests (Ensure P0 has enough straights)
        player0.hand = [straight, straight, curve, curve, crossroad, straight, straight]
        player1.hand = [curve, curve, curve, straight, tree_ew_junc, straight]

        print("Initial Board & Hands:")
        game.print_board()
        print(f"P0 Hand: {[t.name for t in player0.hand]}")
        print(f"P1 Hand: {[t.name for t in player1.hand]}")
        print("-" * 20)

        # --- P0 Turn 1 ---
        print(f"\n--- P0 Turn {game.current_turn} ---")
        # Action 1: Place Straight N-S at (6,2) West of Building L (6,3). -> YES STOP SIGN
        success = game.player_action_place_tile(player0, straight, 0, 6, 2)
        assert success, "Test Fail: P0 T1 A1 placement"
        tile_6_2 = game.board.get_tile(6, 2); assert tile_6_2 and tile_6_2.has_stop_sign, "Test Fail: P0 T1 A1 Stop Sign L"
        assert 'L' in game.board.buildings_with_stops; assert game.actions_taken_this_turn == 1
        # game.print_board() # Optional print

        # Action 2: Place Straight E-W at (7,3) South of Building L (6,3). -> NO STOP SIGN (L taken)
        success = game.player_action_place_tile(player0, straight, 90, 7, 3)
        assert success, "Test Fail: P0 T1 A2 place"
        tile_7_3 = game.board.get_tile(7, 3); assert tile_7_3 and not tile_7_3.has_stop_sign, "Test Fail: P0 T1 A2 Stop Sign L"
        assert game.actions_taken_this_turn == 2
        # game.print_board() # Optional print
        game.end_player_turn()

        # --- P1 Turn 1 ---
        print(f"\n--- P1 Turn {game.current_turn} ---")
        # Action 1: Place Curve N-E at (2,5) North of Building M (3,5). -> NO STOP SIGN
        success = game.player_action_place_tile(player1, curve, 0, 2, 5)
        assert success, "Test Fail: P1 T1 A1 place"
        tile_2_5 = game.board.get_tile(2, 5); assert tile_2_5 and not tile_2_5.has_stop_sign, "Test Fail: P1 T1 A1 Stop Sign M"
        assert 'M' not in game.board.buildings_with_stops; assert game.actions_taken_this_turn == 1
        # game.print_board() # Optional print

        # Action 2: Place Straight E-W at (4,5) South of Building M (3,5). -> YES STOP SIGN
        success = game.player_action_place_tile(player1, straight, 90, 4, 5)
        assert success, "Test Fail: P1 T1 A2 (Actual) place"
        tile_4_5 = game.board.get_tile(4, 5); assert tile_4_5 and tile_4_5.has_stop_sign, "Test Fail: P1 T1 A2 Stop Sign M"
        assert 'M' in game.board.buildings_with_stops; assert game.actions_taken_this_turn == 2
        # game.print_board() # Optional print
        game.end_player_turn()

        # --- P0 Turn 2 ---
        print(f"\n--- P0 Turn {game.current_turn} ---")
        # Action 1 Attempt: Place Crossroad at (3,4) West of M(3,5). -> INVALID (points E into M)
        success = game.player_action_place_tile(player0, crossroad, 0, 3, 4)
        assert not success, "Test Fail: P0 T2 A1 place (Crossroad into M) should fail!"
        assert game.board.get_tile(3, 4) is None
        assert game.actions_taken_this_turn == 0 # Action count unchanged

        # Action 1 (Actual): Place Straight N-S at (3,4) West of Building M (3,5).
        # Building is E, needs N-S track. Straight has N-S. VALID, but M taken -> NO STOP SIGN
        success = game.player_action_place_tile(player0, straight, 0, 3, 4)
        assert success, "Test Fail: P0 T2 A1 (Actual) place"
        tile_3_4 = game.board.get_tile(3, 4); assert tile_3_4 and not tile_3_4.has_stop_sign, "Test Fail: P0 T2 A1 Stop Sign M (Should be NO - M taken)"
        assert game.actions_taken_this_turn == 1
        game.print_board() # Show board after this action

        # Action 2: Place Straight N-S at (6,4) East of Building L (6,3).
        # Building is W, needs N-S track. Straight has N-S. Valid, but L taken -> NO STOP SIGN
        success = game.player_action_place_tile(player0, straight, 0, 6, 4)
        assert success, "Test Fail: P0 T2 A2 place"
        tile_6_4 = game.board.get_tile(6, 4); assert tile_6_4 and not tile_6_4.has_stop_sign, "Test Fail: P0 T2 A2 Stop Sign L (Should be NO - L taken)"
        assert game.actions_taken_this_turn == 2
        game.print_board() # Show board after this action
        game.end_player_turn()


        print("\n--- Phase 2 All Tests OK (Corrected Building/Crossroad Placement) ---")

    except (ValueError, RuntimeError, AssertionError) as e:
        print(f"\n--- ERROR during Phase 2 Test ---")
        print(f"Error Type: {type(e).__name__}")
        print(e)
        # import traceback
        # traceback.print_exc()
    except Exception as e:
        print(f"\n--- UNEXPECTED ERROR during Phase 2 Test ---")
        print(f"Error Type: {type(e).__name__}")
        print(e)
        import traceback
        traceback.print_exc()