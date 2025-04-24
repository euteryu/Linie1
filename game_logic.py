# game_logic.py
# -*- coding: utf-8 -*-
import random
from enum import Enum, auto
from typing import List, Dict, Tuple, Optional, Set, Any
import copy
from collections import deque
# Import constants needed for game logic
from constants import (GRID_ROWS, GRID_COLS, PLAYABLE_ROWS, PLAYABLE_COLS,
                       BUILDING_COORDS, TILE_DEFINITIONS, TILE_COUNTS_BASE,
                       TILE_COUNTS_5_PLUS_ADD, STARTING_HAND_TILES,
                       ROUTE_CARD_VARIANTS, TERMINAL_DATA, TERMINAL_COORDS,
                       HAND_TILE_LIMIT, MAX_PLAYER_ACTIONS)

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
        # *** CORRECTED: One statement per line ***
        if direction == Direction.N:
            return Direction.S
        elif direction == Direction.S:
            return Direction.N
        elif direction == Direction.E:
            return Direction.W
        elif direction == Direction.W:
            return Direction.E
        else:
             # This path should be unreachable if input is always a Direction enum member
             raise ValueError("Invalid direction provided to opposite()")

    @staticmethod
    def from_str(dir_str: str) -> 'Direction':
        try:
            # Directly access enum member using bracket notation after converting input to uppercase
            return Direction[dir_str.upper()]
        except KeyError:
            # Raise a ValueError if the input string doesn't match any enum member name
            raise ValueError(f"Invalid direction string: '{dir_str}'")

# --- Data Classes ---
class TileType:
    def __init__(self, name: str, connections: List[List[str]], is_swappable: bool):
        self.name = name
        self.connections_base = self._process_connections(connections)
        self.is_swappable = is_swappable

    def _process_connections(self, raw_connections: List[List[str]]) -> Dict[str, List[str]]:
        conn_map: Dict[str, List[str]] = {'N': [], 'E': [], 'S': [], 'W': []}
        for path in raw_connections:
            for i in range(len(path)):
                current_node = path[i]
                other_nodes = [path[j] for j in range(len(path)) if i != j]
                for other_node in other_nodes:
                    if current_node not in conn_map:
                        conn_map[current_node] = []
                    if other_node not in conn_map[current_node]:
                        conn_map[current_node].append(other_node)
        for key in conn_map:
            conn_map[key].sort()
        return conn_map

    def __repr__(self) -> str:
        return f"TileType({self.name}, Swappable={self.is_swappable})"

    def __eq__(self, other):
        if isinstance(other, TileType):
            return self.name == other.name
        return NotImplemented

    def __hash__(self):
        return hash(self.name)

class PlacedTile:
    def __init__(self, tile_type: TileType, orientation: int = 0, is_terminal: bool = False):
        self.tile_type = tile_type
        if orientation % 90 != 0:
            raise ValueError(f"Orientation must be multiple of 90, got {orientation}")
        self.orientation = orientation % 360
        self.has_stop_sign: bool = False
        self.is_terminal: bool = is_terminal

    def __repr__(self) -> str:
        term_str = " Term" if self.is_terminal else ""
        stop_str = " Stop" if self.has_stop_sign else ""
        return f"Placed({self.tile_type.name}, {self.orientation}deg{term_str}{stop_str})"

class Board:
    def __init__(self, rows: int = GRID_ROWS, cols: int = GRID_COLS):
        self.rows = rows
        self.cols = cols
        self.grid: List[List[Optional[PlacedTile]]] = [
            [None for _ in range(cols)] for _ in range(rows)
        ]
        self.building_coords = BUILDING_COORDS
        self.coord_to_building: Dict[Tuple[int, int], str] = {
            v: k for k, v in self.building_coords.items()
        }
        self.buildings_with_stops: Set[str] = set()
        self.building_stop_locations: Dict[str, Tuple[int, int]] = {}
        # _initialize_terminals called from Game.__init__

    def _initialize_terminals(self, tile_types: Dict[str, TileType]):
        print("Initializing Terminals by placing tiles...")
        curve_tile = tile_types.get("Curve")
        if not curve_tile:
            print("FATAL ERROR: Could not find 'Curve' TileType.")
            return
        if not TERMINAL_DATA:
             print("Warning: TERMINAL_DATA dictionary is empty.")
             return

        for line_num, entrances in TERMINAL_DATA.items():
            # Validate structure before unpacking
            if not isinstance(entrances, tuple) or len(entrances) != 2:
                 print(f"Warning: Invalid entrance structure Line {line_num}."); continue
            entrance_a, entrance_b = entrances
            if not isinstance(entrance_a, tuple) or len(entrance_a) != 2 or \
               not isinstance(entrance_b, tuple) or len(entrance_b) != 2:
                 print(f"Warning: Invalid pair structure Line {line_num}."); continue

            for entrance_pair in [entrance_a, entrance_b]:
                if not isinstance(entrance_pair, tuple) or len(entrance_pair) != 2:
                     print(f"Warning: Invalid cell info structure pair L{line_num}."); continue
                cell1_info, cell2_info = entrance_pair
                if not isinstance(cell1_info, tuple) or len(cell1_info) != 2 or \
                   not isinstance(cell2_info, tuple) or len(cell2_info) != 2:
                      print(f"Warning: Invalid cell info structure pair L{line_num}."); continue

                coord1, orient1 = cell1_info
                coord2, orient2 = cell2_info

                # Place first curve of pair
                if isinstance(coord1, tuple) and len(coord1) == 2 and isinstance(orient1, int):
                    if self.is_valid_coordinate(coord1[0], coord1[1]):
                        if self.grid[coord1[0]][coord1[1]] is None:
                            self.grid[coord1[0]][coord1[1]] = PlacedTile(curve_tile, orient1, is_terminal=True)
                        # else: Optional warning if already occupied
                    # else: Optional warning if out of bounds
                # else: Optional warning about invalid data format

                # Place second curve of pair
                if isinstance(coord2, tuple) and len(coord2) == 2 and isinstance(orient2, int):
                    if self.is_valid_coordinate(coord2[0], coord2[1]):
                         if self.grid[coord2[0]][coord2[1]] is None:
                             self.grid[coord2[0]][coord2[1]] = PlacedTile(curve_tile, orient2, is_terminal=True)
                         # else: Optional warning if already occupied
                    # else: Optional warning if out of bounds
                # else: Optional warning about invalid data format
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

class Player: # DEFINED BEFORE Game
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


# --- Game Class ---
class Game:
    def __init__(self, num_players: int):
        if not 2 <= num_players <= 6:
            raise ValueError("Players must be 2-6.")
        self.num_players = num_players
        self.tile_types: Dict[str, TileType] = {
            name: TileType(name=name, **details)
            for name, details in TILE_DEFINITIONS.items()
        }
        self.board = Board()
        self.board._initialize_terminals(self.tile_types) # Init terminals now
        self.players = [Player(i) for i in range(num_players)]
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

    def setup_game(self):
        if self.game_phase != GamePhase.SETUP:
            return
        print("--- Starting Setup Steps 2+ ---")
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
        expected_total = sum(tile_counts.values())
        actual_total = len(self.tile_draw_pile)
        if actual_total != expected_total:
             raise RuntimeError(f"Tile pile count error! Expected {expected_total}, got {actual_total}")
        random.shuffle(self.tile_draw_pile)
        print(f"Created tile draw pile with {len(self.tile_draw_pile)} tiles.")
        self.line_cards_pile = [LineCard(i) for i in range(1, 7)]
        random.shuffle(self.line_cards_pile)

    def _deal_starting_hands(self):
        print("Dealing start hands...")
        straight_type = self.tile_types.get('Straight')
        curve_type = self.tile_types.get('Curve')
        if not straight_type or not curve_type:
            raise RuntimeError("Straight/Curve TileType missing.")
        needed_s = STARTING_HAND_TILES['Straight'] * self.num_players
        needed_c = STARTING_HAND_TILES['Curve'] * self.num_players
        current_s = sum(1 for tile in self.tile_draw_pile if tile == straight_type)
        current_c = sum(1 for tile in self.tile_draw_pile if tile == curve_type)
        # print(f"DEBUG: Need S={needed_s}, C={needed_c}. Have S={current_s}, C={current_c}") # Optional
        if current_s < needed_s or current_c < needed_c:
             raise RuntimeError(f"FATAL: Draw pile insufficient!")
        for player in self.players:
            player.hand = []
            dealt_s = 0; dealt_c = 0
            indices_to_remove = []
            available_indices = list(range(len(self.tile_draw_pile)))
            random.shuffle(available_indices)
            for i in available_indices:
                if dealt_s == STARTING_HAND_TILES['Straight'] and dealt_c == STARTING_HAND_TILES['Curve']:
                    break
                # Ensure index is valid before accessing
                if i < len(self.tile_draw_pile):
                    tile = self.tile_draw_pile[i]
                    if i not in indices_to_remove: # Check before processing
                        if tile == straight_type and dealt_s < STARTING_HAND_TILES['Straight']:
                            indices_to_remove.append(i)
                            dealt_s += 1
                        elif tile == curve_type and dealt_c < STARTING_HAND_TILES['Curve']:
                            indices_to_remove.append(i)
                            dealt_c += 1
            # Verification
            if dealt_s != STARTING_HAND_TILES['Straight'] or dealt_c != STARTING_HAND_TILES['Curve']:
                 raise RuntimeError(f"Logic Error: Couldn't find start tiles for P{player.player_id}.")
            # Add to hand and remove from pile
            indices_to_remove.sort(reverse=True)
            temp_hand = []
            for index in indices_to_remove:
                 if index < len(self.tile_draw_pile): # Double check index before pop
                     temp_hand.append(self.tile_draw_pile.pop(index))
                 else: raise RuntimeError(f"Logic Error: Invalid index {index} removing start hand P{player.player_id}.")
            player.hand = temp_hand
            player.hand.reverse()
        print(f"Finished dealing start hands. Draw pile size: {len(self.tile_draw_pile)}")

    def _deal_player_cards(self):
        print("Dealing player cards...")
        available_variant_indices = list(range(len(ROUTE_CARD_VARIANTS)))
        random.shuffle(available_variant_indices)
        player_range = "2-4" if self.num_players <= 4 else "5-6"
        if len(self.line_cards_pile) < self.num_players:
            raise RuntimeError("Not enough Line cards!")
        if len(available_variant_indices) < self.num_players:
             raise RuntimeError("Not enough Route card variants!")
        for player in self.players:
            player.line_card = self.line_cards_pile.pop()
            variant_index = available_variant_indices.pop()
            try:
                stops = ROUTE_CARD_VARIANTS[variant_index][player_range][player.line_card.line_number]
            except (KeyError, IndexError) as e:
                raise RuntimeError(f"Error lookup route stops: Var={variant_index}, Rng={player_range}, Line={player.line_card.line_number}. Err: {e}")
            player.route_card = RouteCard(stops, variant_index)

    # --- Keep Helper Methods ---
    def _rotate_direction(self, direction: str, angle: int) -> str:
        directions = ['N', 'E', 'S', 'W'];
        try: current_index = directions.index(direction)
        except ValueError: raise ValueError(f"Invalid direction string: {direction}")
        angle = angle % 360
        if angle % 90 != 0: raise ValueError(f"Invalid rotation angle: {angle}.")
        steps = angle // 90; new_index = (current_index + steps) % 4
        return directions[new_index]
    def get_effective_connections(self, tile_type: TileType, orientation: int) -> Dict[str, List[str]]:
        if orientation == 0: return copy.deepcopy(tile_type.connections_base)
        rotated_connections: Dict[str, List[str]] = {'N': [], 'E': [], 'S': [], 'W': []}
        base_connections = tile_type.connections_base
        for base_entry_dir, base_exit_dirs in base_connections.items():
            actual_entry_dir = self._rotate_direction(base_entry_dir, orientation)
            if actual_entry_dir not in rotated_connections: rotated_connections[actual_entry_dir] = []
            for base_exit_dir in base_exit_dirs:
                actual_exit_dir = self._rotate_direction(base_exit_dir, orientation)
                if actual_exit_dir not in rotated_connections[actual_entry_dir]: rotated_connections[actual_entry_dir].append(actual_exit_dir)
        for key in rotated_connections: rotated_connections[key].sort()
        return rotated_connections
    def _has_ns_straight(self, effective_connections: Dict[str, List[str]]) -> bool: return 'S' in effective_connections.get('N', [])
    def _has_ew_straight(self, effective_connections: Dict[str, List[str]]) -> bool: return 'W' in effective_connections.get('E', [])

    # --- Keep Placement Validity Check ---
    def check_placement_validity(self, tile_type: TileType, orientation: int, row: int, col: int) -> Tuple[bool, str]:
        if not self.board.is_playable_coordinate(row, col): return False, f"Placement Error ({row},{col}): Cannot place on border."
        building = self.board.get_building_at(row, col)
        if building is not None: return False, f"Placement Error ({row},{col}): Cannot place on Building {building}."
        existing_tile = self.board.get_tile(row, col)
        if existing_tile is not None: return False, f"Placement Error ({row},{col}): Space occupied by {existing_tile.tile_type.name}."
        effective_connections = self.get_effective_connections(tile_type, orientation)
        for direction in Direction:
            dir_str = direction.name; opposite_dir = Direction.opposite(direction); opposite_dir_str = opposite_dir.name
            dr, dc = direction.value; nr, nc = row + dr, col + dc
            if not self.board.is_valid_coordinate(nr, nc):
                has_exit_this_way = dir_str in [ex for exits in effective_connections.values() for ex in exits]
                if has_exit_this_way: return False, f"Placement Error ({row},{col}): Tile points {dir_str} off grid."
                continue
            neighbor_tile = self.board.get_tile(nr, nc); neighbor_building = self.board.get_building_at(nr, nc)
            new_tile_has_exit_towards_neighbor = dir_str in [ex for exits in effective_connections.values() for ex in exits]
            if neighbor_tile:
                neighbor_effective_connections = self.get_effective_connections(neighbor_tile.tile_type, neighbor_tile.orientation)
                neighbor_has_exit_back = opposite_dir_str in [ex for exits in neighbor_effective_connections.values() for ex in exits]
                if new_tile_has_exit_towards_neighbor != neighbor_has_exit_back:
                    reason = "has exit" if new_tile_has_exit_towards_neighbor else "no exit"; neighbor_reason = "has exit back" if neighbor_has_exit_back else "no exit back"
                    msg = (f"Placement Error ({row},{col}): Mismatch neighbor tile ({nr},{nc}). New:{reason} {dir_str}, Neighbor:{neighbor_reason} {opposite_dir_str}."); return False, msg
            elif neighbor_building:
                if new_tile_has_exit_towards_neighbor: msg = (f"Placement Error ({row},{col}): Tile points {dir_str} into building {neighbor_building} at ({nr},{nc})."); return False, msg
            else: # Empty neighbor square
                if new_tile_has_exit_towards_neighbor:
                     if not self.board.is_playable_coordinate(nr, nc): msg = (f"Placement Error ({row},{col}): Tile points {dir_str} into empty border square ({nr},{nc})."); return False, msg
        return True, "Placement appears valid."

    # --- Keep _check_and_place_stop_sign ---
    def _check_and_place_stop_sign(self, placed_tile: PlacedTile, row: int, col: int):
        if self.board.get_tile(row, col) != placed_tile: return
        placed_tile.has_stop_sign = False; tile_connections = self.get_effective_connections(placed_tile.tile_type, placed_tile.orientation); building_that_got_stop = None
        for direction in Direction:
            dr, dc = direction.value; nr, nc = row + dr, col + dc
            if not self.board.is_valid_coordinate(nr, nc): continue
            building_id = self.board.get_building_at(nr, nc)
            if building_id and building_id not in self.board.buildings_with_stops:
                has_parallel_track = False
                if direction == Direction.N or direction == Direction.S:
                    if self._has_ew_straight(tile_connections): has_parallel_track = True
                elif direction == Direction.E or direction == Direction.W:
                    if self._has_ns_straight(tile_connections): has_parallel_track = True
                if has_parallel_track:
                    placed_tile.has_stop_sign = True; self.board.buildings_with_stops.add(building_id); self.board.building_stop_locations[building_id] = (row, col); building_that_got_stop = building_id
                    print(f"--> Placed stop sign on tile ({row},{col}) for Building {building_id}."); break

    # *** ADD draw_tile METHOD DEFINITION ***
    def draw_tile(self, player: Player) -> bool:
        """Player draws one tile from the draw pile into their hand."""
        if not self.tile_draw_pile:
            print("Warning: Draw pile empty!")
            return False # Cannot draw
        # Optional: Check if hand is full
        # if len(player.hand) >= HAND_TILE_LIMIT:
        #    print(f"Warning: Player {player.player_id} hand is full.")
        #    return False

        # Take tile from end of pile
        tile = self.tile_draw_pile.pop()
        player.hand.append(tile)
        # print(f"Debug: Player {player.player_id} drew {tile.name}. Hand size: {len(player.hand)}") # Optional
        return True # Successfully drew

    # --- Keep player_action_place_tile ---
    def player_action_place_tile(self, player: Player, tile_type: TileType, orientation: int, row: int, col: int) -> bool:
        print(f"\nAttempting P{player.player_id} place: {tile_type.name}({orientation}°) at ({row},{col})")
        if tile_type not in player.hand: print(f"--> Action Error: Player {player.player_id} lacks {tile_type.name}."); return False
        is_valid, message = self.check_placement_validity(tile_type, orientation, row, col);
        if not is_valid: print(f"--> {message}"); return False
        player.hand.remove(tile_type); placed_tile = PlacedTile(tile_type, orientation); self.board.set_tile(row, col, placed_tile)
        self._check_and_place_stop_sign(placed_tile, row, col); self.actions_taken_this_turn += 1
        print(f"--> SUCCESS placing {tile_type.name} at ({row},{col}). Actions: {self.actions_taken_this_turn}/{MAX_PLAYER_ACTIONS}"); return True

    # --- Keep _check_single_neighbor_validity_for_exchange and check_exchange_validity ---
    def _check_single_neighbor_validity_for_exchange( self, new_tile_type: TileType, new_orientation: int, row: int, col: int, direction_to_neighbor: Direction ) -> Tuple[bool, str]:
        new_tile_has_exit = True; dir_str = direction_to_neighbor.name; opposite_dir = Direction.opposite(direction_to_neighbor); opposite_dir_str = opposite_dir.name
        dr, dc = direction_to_neighbor.value; nr, nc = row + dr, col + dc
        if not self.board.is_valid_coordinate(nr, nc):
            is_terminal_spot = False # TODO: Terminal check
            if not is_terminal_spot: return False, f"Points {dir_str} off grid edge."
            return True, ""
        neighbor_tile = self.board.get_tile(nr, nc); neighbor_building = self.board.get_building_at(nr, nc)
        if neighbor_tile:
            neighbor_effective_connections = self.get_effective_connections(neighbor_tile.tile_type, neighbor_tile.orientation)
            neighbor_has_exit_back = opposite_dir_str in [ex for exits in neighbor_effective_connections.values() for ex in exits]
            if not neighbor_has_exit_back: msg = (f"New conn {dir_str} invalid, neighbor ({nr},{nc}) no exit back {opposite_dir_str}."); return False, msg
        elif neighbor_building: msg = (f"New conn {dir_str} points into building {neighbor_building} at ({nr},{nc})."); return False, msg
        else: # Empty neighbor square
             if not self.board.is_playable_coordinate(nr, nc): msg = (f"New conn {dir_str} points into empty border square ({nr},{nc})."); return False, msg
        return True, ""
    def check_exchange_validity(self, player: Player, new_tile_type: TileType, new_orientation: int, row: int, col: int) -> Tuple[bool, str]:
        if not self.board.is_playable_coordinate(row, col): return False, f"Exchange Error ({row},{col}): Cannot exchange border."
        old_placed_tile = self.board.get_tile(row, col);
        if not old_placed_tile: return False, f"Exchange Error ({row},{col}): No tile."
        if old_placed_tile.is_terminal: return False, f"Exchange Error ({row},{col}): Cannot exchange terminal."
        if not old_placed_tile.tile_type.is_swappable: return False, f"Exchange Error ({row},{col}): Not swappable."
        if old_placed_tile.has_stop_sign: return False, f"Exchange Error ({row},{col}): Has stop sign."
        if new_tile_type not in player.hand: return False, f"Exchange Error: Player lacks {new_tile_type.name}."
        old_connections = self.get_effective_connections(old_placed_tile.tile_type, old_placed_tile.orientation); new_connections = self.get_effective_connections(new_tile_type, new_orientation)
        def get_connection_pairs(conn_dict): return { frozenset((entry, exit_dir)) for entry, exits in conn_dict.items() for exit_dir in exits }
        old_connected_pairs = get_connection_pairs(old_connections); new_connected_pairs = get_connection_pairs(new_connections)
        if not old_connected_pairs.issubset(new_connected_pairs): missing = old_connected_pairs - new_connected_pairs; msg = (f"Exchange Error ({row},{col}): Doesn't preserve old connections. Missing: {missing}"); return False, msg
        added_connection_pairs = new_connected_pairs - old_connected_pairs
        if added_connection_pairs:
            old_exits = {ex for exits in old_connections.values() for ex in exits}; new_exits = {ex for exits in new_connections.values() for ex in exits}
            added_exit_directions = new_exits - old_exits
            for direction_str in added_exit_directions:
                 direction_enum = Direction.from_str(direction_str)
                 is_valid, message = self._check_single_neighbor_validity_for_exchange(new_tile_type, new_orientation, row, col, direction_enum)
                 if not is_valid: return False, f"Exchange Error ({row},{col}): Added connection {direction_str} invalid. Reason: {message}"
        return True, "Exchange appears valid."

    # --- Keep player_action_exchange_tile ---
    def player_action_exchange_tile(self, player: Player, new_tile_type: TileType, new_orientation: int, row: int, col: int) -> bool:
        print(f"\nAttempting P{player.player_id} exchange: {new_tile_type.name}({new_orientation}°) at ({row},{col})")
        is_valid, message = self.check_exchange_validity(player, new_tile_type, new_orientation, row, col);
        if not is_valid: print(f"--> {message}"); return False
        old_placed_tile = self.board.get_tile(row, col);
        if old_placed_tile is None: print(f"--> Internal Error: Tile disappeared at ({row},{col})."); return False
        player.hand.remove(new_tile_type); player.hand.append(old_placed_tile.tile_type); new_placed_tile = PlacedTile(new_tile_type, new_orientation); self.board.set_tile(row, col, new_placed_tile)
        self.actions_taken_this_turn += 1; print(f"--> SUCCESS exchanging {old_placed_tile.tile_type.name}({old_placed_tile.orientation}°) for {new_tile_type.name}({new_orientation}°) at ({row},{col}). Actions: {self.actions_taken_this_turn}/{MAX_PLAYER_ACTIONS}"); return True

    # --- Keep Pathfinding & Route Completion ---
    def find_path_exists(self, start_row: int, start_col: int, end_row: int, end_col: int) -> bool:
        """Checks if a continuous track path exists between two coordinates using BFS."""
        # 1. Validate Start/End Coordinates
        if not self.board.is_valid_coordinate(start_row, start_col) or \
           not self.board.is_valid_coordinate(end_row, end_col):
            # print(f"BFS Debug: Invalid Start/End Coord ({start_row},{start_col})->({end_row},{end_col})") # Optional debug
            return False

        # 2. Handle Trivial Case (Path to self)
        if (start_row, start_col) == (end_row, end_col):
            return True # Path always exists if start and end are the same valid coordinate

        # 3. Check if Start Tile Exists
        start_tile = self.board.get_tile(start_row, start_col)
        if not start_tile:
            # print(f"BFS Debug: No tile at Start ({start_row},{start_col})") # Optional debug
            return False # Cannot start path from an empty square

        # 4. Initialize BFS
        queue = deque([(start_row, start_col)])
        visited: Set[Tuple[int, int]] = {(start_row, start_col)}

        # 5. BFS Loop
        while queue:
            curr_row, curr_col = queue.popleft()

            # --- Optimization: Check if we dequeued the destination ---
            # (Can sometimes find the path faster than waiting to explore from its neighbor)
            # if (curr_row, curr_col) == (end_row, end_col):
            #     return True # Reached destination

            current_tile = self.board.get_tile(curr_row, curr_col)
            # This check should ideally not be needed if only valid tiles are added, but good safety.
            if not current_tile:
                continue

            current_connections = self.get_effective_connections(current_tile.tile_type, current_tile.orientation)
            # Determine all directions this tile has an *explicit* exit towards
            current_exit_dirs_str = {exit_dir for exits in current_connections.values() for exit_dir in exits}

            # 6. Explore Neighbors
            for direction in Direction: # Iterate through N, E, S, W
                dir_str = direction.name # e.g., "N"
                opposite_dir = Direction.opposite(direction)
                opposite_dir_str = opposite_dir.name # e.g., "S"

                dr, dc = direction.value
                nr, nc = curr_row + dr, curr_col + dc

                # 7. Check Neighbor Validity & Visited Status
                if not self.board.is_valid_coordinate(nr, nc):
                    continue # Skip coordinates outside the board grid
                if (nr, nc) in visited:
                    continue # Skip already processed nodes

                neighbor_tile = self.board.get_tile(nr, nc)
                if not neighbor_tile:
                    continue # Skip empty squares - cannot path through them

                # --- 8. THE CRUCIAL TWO-WAY CONNECTION CHECK ---
                # Check 1: Does the CURRENT tile have an exit pointing TOWARDS the neighbor?
                current_connects_towards_neighbor = dir_str in current_exit_dirs_str

                # Check 2: Does the NEIGHBOR tile have an exit pointing BACK towards the current tile?
                neighbor_connections = self.get_effective_connections(neighbor_tile.tile_type, neighbor_tile.orientation)
                neighbor_exit_dirs_str = {exit_dir for exits in neighbor_connections.values() for exit_dir in exits}
                neighbor_connects_back_to_current = opposite_dir_str in neighbor_exit_dirs_str

                # 9. Add to Queue if Valid Connection
                if current_connects_towards_neighbor and neighbor_connects_back_to_current:
                    # A valid track segment exists between (curr_row, curr_col) and (nr, nc)
                    visited.add((nr, nc))
                    queue.append((nr, nc))

                    # --- Optimization: Check if the added neighbor IS the destination ---
                    if (nr, nc) == (end_row, end_col):
                        return True # Found the path!

        # 10. Queue is empty, destination not reached
        # print(f"BFS Debug: Path not found from ({start_row},{start_col}) to ({end_row},{end_col})") # Optional debug
        return False

    def get_terminal_coords(self, line_number: int) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]: # Keep as is
        coords = TERMINAL_COORDS.get(line_number);
        if coords: return coords[0], coords[1]
        else: print(f"Warning: Terminal coordinates not defined for Line {line_number}"); return None, None
    def check_player_route_completion(self, player: Player) -> bool: # Keep as is
        if not player.line_card or not player.route_card: print(f"Route Check Error: Player {player.player_id} missing cards."); return False
        line_num = player.line_card.line_number; stops = player.route_card.stops
        term1_coord, term2_coord = self.get_terminal_coords(line_num);
        if not term1_coord or not term2_coord: print(f"Route Check Error: No terminal coords for Line {line_num}."); return False
        stop_coords = [];
        for stop_id in stops:
            coord = self.board.building_stop_locations.get(stop_id)
            if coord is None: return False
            stop_coords.append(coord)
        path1_possible = True; sequence1 = [term1_coord] + stop_coords + [term2_coord]
        for i in range(len(sequence1) - 1):
            start_node = sequence1[i]; end_node = sequence1[i+1]
            if not self.find_path_exists(start_node[0], start_node[1], end_node[0], end_node[1]): path1_possible = False; print(f"Route Check P{player.player_id} Seq1 FAIL: {start_node} -> {end_node}"); break
        if path1_possible: print(f"Route Check P{player.player_id}: COMPLETE via sequence 1."); return True
        path2_possible = True; sequence2 = [term2_coord] + stop_coords + [term1_coord]
        for i in range(len(sequence2) - 1):
            start_node = sequence2[i]; end_node = sequence2[i+1]
            if not self.find_path_exists(start_node[0], start_node[1], end_node[0], end_node[1]): path2_possible = False; print(f"Route Check P{player.player_id} Seq2 FAIL: {start_node} -> {end_node}"); break
        if path2_possible: print(f"Route Check P{player.player_id}: COMPLETE via sequence 2."); return True
        return False
    def handle_route_completion(self, player: Player): # Keep as is
        print(f"\n*** ROUTE COMPLETE for Player {player.player_id}! ***"); player.player_state = PlayerState.DRIVING
        term1_coord, term2_coord = self.get_terminal_coords(player.line_card.line_number)
        if term1_coord: player.streetcar_position = term1_coord; print(f"Player {player.player_id} streetcar placed at {term1_coord}.")
        else: print(f"Error: Could not determine start terminal for Player {player.player_id}")
        if self.first_player_to_finish_route is None: self.first_player_to_finish_route = player.player_id; self.game_phase = GamePhase.DRIVING; print(f"Game Phase changing to DRIVING.")

    # --- Keep End Turn Logic (Corrected draw_tile call) ---
    def end_player_turn(self):
        active_player = self.get_active_player(); route_just_completed = False
        if active_player.player_state == PlayerState.LAYING_TRACK:
            if self.check_player_route_completion(active_player):
                 self.handle_route_completion(active_player);
                 route_just_completed = True

        if active_player.player_state == PlayerState.LAYING_TRACK and not route_just_completed:
            draw_count = 0
            while len(active_player.hand) < HAND_TILE_LIMIT and self.tile_draw_pile:
                 # *** Use the correct method name ***
                 if self.draw_tile(active_player):
                      draw_count += 1
            if draw_count > 0:
                 print(f"Player {active_player.player_id} drew {draw_count} tiles (Hand: {len(active_player.hand)}).")
        elif route_just_completed:
             print(f"Player {active_player.player_id} completed route, does not draw.")

        self.active_player_index = (self.active_player_index + 1) % self.num_players
        if self.active_player_index == 0:
            self.current_turn += 1
        self.actions_taken_this_turn = 0 # Reset action count
        next_player = self.get_active_player()
        print(f"\n--- End Turn - Starting Turn {self.current_turn} for Player {self.active_player_index} ({next_player.player_state.name}) ---")