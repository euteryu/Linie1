# game_logic.py
# -*- coding: utf-8 -*-
import random
from enum import Enum, auto
from typing import List, Dict, Tuple, Optional, Set, Any
import copy # Make sure copy is imported
from collections import deque # Make sure deque is imported
from constants import (GRID_ROWS, GRID_COLS, BUILDING_COORDS, TILE_DEFINITIONS,
                       TILE_COUNTS_BASE, TILE_COUNTS_5_PLUS_ADD, STARTING_HAND_TILES,
                       ROUTE_CARD_VARIANTS, TERMINAL_COORDS)

# --- Enums (Keep) ---
class PlayerState(Enum): LAYING_TRACK = auto(); DRIVING = auto(); FINISHED = auto()
class GamePhase(Enum): SETUP = auto(); LAYING_TRACK = auto(); DRIVING_TRANSITION = auto(); DRIVING = auto(); GAME_OVER = auto()
class Direction(Enum):
    N = (-1, 0); E = (0, 1); S = (1, 0); W = (0, -1)
    @staticmethod
    def opposite(direction: 'Direction') -> 'Direction':
        if direction == Direction.N: return Direction.S
        elif direction == Direction.S: return Direction.N
        elif direction == Direction.E: return Direction.W
        elif direction == Direction.W: return Direction.E
        else: raise ValueError("Invalid direction provided")
    @staticmethod
    def from_str(dir_str: str) -> 'Direction':
        try: return Direction[dir_str.upper()]
        except KeyError: raise ValueError(f"Invalid direction string: {dir_str}")

# --- Data Classes (Keep) ---
class TileType: # Keep as is
    def __init__(self, name: str, connections: List[List[str]], is_swappable: bool):
        self.name = name; self.connections_base = self._process_connections(connections); self.is_swappable = is_swappable
    def _process_connections(self, raw_connections: List[List[str]]) -> Dict[str, List[str]]:
        conn_map: Dict[str, List[str]] = {'N': [], 'E': [], 'S': [], 'W': []}
        for path in raw_connections:
            for i in range(len(path)):
                current_node = path[i]; other_nodes = [path[j] for j in range(len(path)) if i != j]
                for other_node in other_nodes:
                    if current_node not in conn_map: conn_map[current_node] = []
                    if other_node not in conn_map[current_node]: conn_map[current_node].append(other_node)
        for key in conn_map: conn_map[key].sort()
        return conn_map
    def __repr__(self) -> str: return f"TileType({self.name}, Swappable={self.is_swappable})"
class PlacedTile: # Keep as is
    def __init__(self, tile_type: TileType, orientation: int = 0):
        self.tile_type = tile_type
        if orientation % 90 != 0: raise ValueError(f"Orientation must be multiple of 90, got {orientation}")
        self.orientation = orientation % 360; self.has_stop_sign: bool = False
    def __repr__(self) -> str: return f"Placed({self.tile_type.name}, {self.orientation}deg, Stop:{self.has_stop_sign})"
class Board: # Add helper to find stop sign locations
    def __init__(self, rows: int = GRID_ROWS, cols: int = GRID_COLS):
        self.rows = rows; self.cols = cols
        self.grid: List[List[Optional[PlacedTile]]] = [[None for _ in range(cols)] for _ in range(rows)]
        self.building_coords = BUILDING_COORDS
        self.coord_to_building: Dict[Tuple[int, int], str] = {v: k for k, v in BUILDING_COORDS.items()}
        self.buildings_with_stops: Set[str] = set()
        # New: Map building ID to the coordinate of the tile holding its stop sign
        self.building_stop_locations: Dict[str, Tuple[int, int]] = {}
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
    def simple_render(self, game=None) -> str: # Keep as is
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
                            connections = game.get_effective_connections(tile.tile_type, tile.orientation); connected_dirs = set();
                            for entry, exits in connections.items():
                                if exits: connected_dirs.add(entry); connected_dirs.update(exits)
                            symbol = conn_symbols.get(frozenset(connected_dirs), default_symbol)
                            if symbol == default_symbol:
                                if "Crossroad" in tile.tile_type.name: symbol = "┼"
                                elif "Straight" in tile.tile_type.name and "Curve" in tile.tile_type.name: symbol = "T"
                                elif tile.tile_type.name == "Straight": symbol = '│' if tile.orientation in [0, 180] else '─'
                                else: symbol = tile.tile_type.name[0]
                        except Exception: symbol = 'E'
                    else: symbol = tile.tile_type.name[0] if tile.tile_type.name else '?'
                    cell_content = f"{symbol}{stop}"
                else: building = self.get_building_at(r, c); cell_content = f"[{building}]" if building else "·"
                padding_total = col_width - len(cell_content); padding_left = padding_total // 2; padding_right = padding_total - padding_left; row_str_parts.append(" " * padding_left + cell_content + " " * padding_right + separator)
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
    # Keep __init__ and setup methods
    def __init__(self, num_players: int):
        if not 2 <= num_players <= 6: raise ValueError("Players must be 2-6.")
        self.num_players = num_players; self.board = Board(); self.players = [Player(i) for i in range(num_players)]
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
    def _create_tile_and_line_piles(self):
        """Creates the full tile pile BEFORE dealing starting hands."""
        print("DEBUG: Creating tile pile...") # Add debug start
        tile_counts = TILE_COUNTS_BASE.copy()
        if self.num_players >= 5:
            for name, count in TILE_COUNTS_5_PLUS_ADD.items():
                tile_counts[name] = tile_counts.get(name, 0) + count
        print(f"DEBUG: Calculated tile counts: {tile_counts}") # Debug counts

        # Ensure the pile is empty before creating
        self.tile_draw_pile = [] # Start with an empty list

        # *** Iterate through the calculated counts ***
        for name, count in tile_counts.items():
            tile_type = self.tile_types.get(name) # Get the TileType instance
            if tile_type:
                # Add 'count' copies of this specific TileType instance
                self.tile_draw_pile.extend([tile_type] * count)
                # print(f"DEBUG: Added {count} x {name}") # Optional: Verify each addition
            else:
                # This error indicates a mismatch between TILE_COUNTS keys and TILE_DEFINITIONS keys
                print(f"FATAL WARNING: Tile type '{name}' in counts not found in definitions.")
                # You might want to raise an error here instead of just printing

        # *** Verify the final count ***
        expected_total = sum(tile_counts.values())
        actual_total = len(self.tile_draw_pile)
        print(f"DEBUG: Expected total tiles = {expected_total}")
        print(f"DEBUG: Actual total tiles created = {actual_total}")

        if actual_total != expected_total:
             # This would indicate a logic error in the loop above
             raise RuntimeError(f"Logic Error: Tile draw pile count mismatch after creation! Expected {expected_total}, got {actual_total}")

        random.shuffle(self.tile_draw_pile)
        print(f"Created and shuffled tile draw pile with {len(self.tile_draw_pile)} tiles.") # Final confirmation

        # Line card pile creation remains the same
        self.line_cards_pile = [LineCard(i) for i in range(1, 7)]
        random.shuffle(self.line_cards_pile)
        # print(f"Created line card pile with {len(self.line_cards_pile)} cards.")
    def _deal_starting_hands(self):
        """Deals starting hands from the already created and shuffled tile pile."""
        print("Dealing start hands...")
        straight_type = self.tile_types['Straight']
        curve_type = self.tile_types['Curve']
        needed_s_total = STARTING_HAND_TILES['Straight'] * self.num_players
        needed_c_total = STARTING_HAND_TILES['Curve'] * self.num_players

        # *** Perform check AFTER creating the pile ***
        # Add Debug Prints:
        print(f"DEBUG: Checking starting hand sufficiency.")
        print(f"DEBUG: Needed Straights = {needed_s_total}, Needed Curves = {needed_c_total}")
        current_s = sum(1 for tile in self.tile_draw_pile if tile == straight_type)
        current_c = sum(1 for tile in self.tile_draw_pile if tile == curve_type)
        print(f"DEBUG: Available Straights in pile = {current_s}")
        print(f"DEBUG: Available Curves in pile = {current_c}")
        print(f"DEBUG: Total tiles in pile before dealing = {len(self.tile_draw_pile)}")

        if current_s < needed_s_total or current_c < needed_c_total:
             # If it fails, print the counts again for clarity
             print(f"ERROR DETAILS: Have S:{current_s}/C:{current_c}, Need S:{needed_s_total}/C:{needed_c_total}")
             raise RuntimeError(f"FATAL: Draw pile insufficient for starting hands!")

        # Now deal (Keep the rest of the dealing logic the same)
        for player in self.players:
            player.hand = []
            dealt_s = 0
            dealt_c = 0
            indices_found = []
            # Iterate through the current draw pile state to find tiles
            # Using indices is safer if the pile could somehow change during iteration
            current_pile_indices = list(range(len(self.tile_draw_pile)))
            random.shuffle(current_pile_indices) # Shuffle indices to randomize which specific tiles are taken

            for i in current_pile_indices:
                 # Check if index is still valid (it should be if we remove carefully later)
                 if i >= len(self.tile_draw_pile): continue

                 tile = self.tile_draw_pile[i]

                 # Avoid re-selecting an index already marked for removal for this player
                 # (Indices_found is only relevant within this player's loop)

                 if tile == straight_type and dealt_s < STARTING_HAND_TILES['Straight']:
                     # Mark index for removal *after* finding all for this player
                     indices_found.append(i)
                     dealt_s += 1
                 elif tile == curve_type and dealt_c < STARTING_HAND_TILES['Curve']:
                     # Mark index for removal
                     indices_found.append(i)
                     dealt_c += 1

                 if dealt_s == STARTING_HAND_TILES['Straight'] and dealt_c == STARTING_HAND_TILES['Curve']:
                     break # Found enough for this player

            if dealt_s != STARTING_HAND_TILES['Straight'] or dealt_c != STARTING_HAND_TILES['Curve']:
                 raise RuntimeError(f"Logic Error: Couldn't find start hand tiles for P{player.player_id} after check passed.")

            # Add tiles to hand *before* removing from pile to avoid index issues
            for index in indices_found:
                 player.hand.append(self.tile_draw_pile[index])
            player.hand.reverse() # Optional: Keep hand order consistent

            # Remove from pile using indices (sort reverse to avoid shifting issues)
            indices_found.sort(reverse=True)
            for index in indices_found:
                # Add a check to prevent index error if something went wrong
                if index < len(self.tile_draw_pile):
                    del self.tile_draw_pile[index]
                else:
                    print(f"WARNING: Attempted to delete index {index} beyond pile bounds ({len(self.tile_draw_pile)}) for P{player.player_id}.")


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

    def _rotate_direction(self, direction: str, angle: int) -> str: # Keep corrected version
        directions = ['N', 'E', 'S', 'W'];
        try: current_index = directions.index(direction)
        except ValueError: raise ValueError(f"Invalid direction string: {direction}")
        angle = angle % 360
        if angle % 90 != 0: raise ValueError(f"Invalid rotation angle: {angle}. Must be multiple of 90.")
        steps = angle // 90; new_index = (current_index + steps) % 4
        return directions[new_index]

    def get_effective_connections(self, tile_type: TileType, orientation: int) -> Dict[str, List[str]]: # Keep as is
        if orientation == 0: return copy.deepcopy(tile_type.connections_base)
        rotated_connections: Dict[str, List[str]] = {'N': [], 'E': [], 'S': [], 'W': []}
        base_connections = tile_type.connections_base
        for base_entry_dir, base_exit_dirs in base_connections.items():
            actual_entry_dir = self._rotate_direction(base_entry_dir, orientation)
            if actual_entry_dir not in rotated_connections: rotated_connections[actual_entry_dir] = []
            for base_exit_dir in base_exit_dirs:
                actual_exit_dir = self._rotate_direction(base_exit_dir, orientation)
                if actual_exit_dir not in rotated_connections[actual_entry_dir]: rotated_connections[actual_entry_dir].append(actual_exit_dir)
        for key in rotated_connections:
            rotated_connections[key].sort()
        return rotated_connections

    def _has_ns_straight(self, effective_connections: Dict[str, List[str]]) -> bool:
        return 'S' in effective_connections.get('N', [])

    def _has_ew_straight(self, effective_connections: Dict[str, List[str]]) -> bool:
        return 'W' in effective_connections.get('E', [])

    def check_placement_validity(self, tile_type: TileType, orientation: int, row: int, col: int) -> Tuple[bool, str]:
        """ Checks rules for placing a NEW tile onto an EMPTY space. Returns (isValid, message)."""
        # Rule: On Board?
        if not self.board.is_valid_coordinate(row, col):
            return False, f"Placement Error ({row},{col}): Off board."

        # *** NEW CHECK: Is the target square a building location? ***
        if self.board.get_building_at(row, col) is not None:
            return False, f"Placement Error ({row},{col}): Cannot place tile directly on Building {self.board.get_building_at(row, col)}."

        # Rule: Space Empty (of other tiles)?
        if self.board.get_tile(row, col) is not None:
            # This check might be redundant if buildings occupy squares exclusively,
            # but good to keep for robustness.
            return False, f"Placement Error ({row},{col}): Space occupied by another tile."

        # --- Continue with connection checks as before ---
        effective_connections = self.get_effective_connections(tile_type, orientation)
        # ... (rest of the neighbor and connection checking logic remains the same) ...
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
        # --> Add placed tile coord to mapping temporarily if successful
        placed_tile.has_stop_sign = False; tile_connections = self.get_effective_connections(placed_tile.tile_type, placed_tile.orientation)
        building_that_got_stop = None
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
                    building_that_got_stop = building_id # Record which building got the stop
                    print(f"--> Placed stop sign on tile ({row},{col}) for Building {building_id} (Parallel rule met)."); break
        # Add to the location mapping *after* potentially setting the sign
        if placed_tile.has_stop_sign and building_that_got_stop:
             self.board.building_stop_locations[building_that_got_stop] = (row, col)

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
    def check_exchange_validity(self, player: Player, new_tile_type: TileType, new_orientation: int, row: int, col: int) -> Tuple[bool, str]: # Keep corrected version
        old_placed_tile = self.board.get_tile(row, col);
        if not old_placed_tile: return False, f"Exchange Error ({row},{col}): No tile exists."
        if not old_placed_tile.tile_type.is_swappable: return False, f"Exchange Error ({row},{col}): Tile {old_placed_tile.tile_type.name} is not swappable."
        if old_placed_tile.has_stop_sign: return False, f"Exchange Error ({row},{col}): Cannot exchange tile with a stop sign."
        if new_tile_type not in player.hand: return False, f"Exchange Error: Player does not have {new_tile_type.name} in hand."
        old_connections = self.get_effective_connections(old_placed_tile.tile_type, old_placed_tile.orientation); new_connections = self.get_effective_connections(new_tile_type, new_orientation)
        old_connected_pairs = set();
        for entry, exits in old_connections.items():
            for exit_dir in exits: old_connected_pairs.add(tuple(sorted((entry, exit_dir))))
        new_connected_pairs = set();
        for entry, exits in new_connections.items():
            for exit_dir in exits: new_connected_pairs.add(tuple(sorted((entry, exit_dir))))
        if not old_connected_pairs.issubset(new_connected_pairs): missing = old_connected_pairs - new_connected_pairs; msg = (f"Exchange Error ({row},{col}): New tile {new_tile_type.name}({new_orientation}°) does not preserve all connections of old tile {old_placed_tile.tile_type.name}({old_placed_tile.orientation}°). Missing: {missing}"); return False, msg
        added_connections_dirs = set();
        for pair in new_connected_pairs - old_connected_pairs: added_connections_dirs.add(pair[0]); added_connections_dirs.add(pair[1])
        for direction_str in added_connections_dirs:
            direction = Direction.from_str(direction_str); opposite_dir_str = Direction.opposite(direction).name; dr, dc = direction.value; nr, nc = row + dr, col + dc
            neighbor_tile = self.board.get_tile(nr, nc); is_neighbor_on_board = self.board.is_valid_coordinate(nr, nc); neighbor_building = self.board.get_building_at(nr, nc) if is_neighbor_on_board else None
            if neighbor_tile:
                neighbor_effective_connections = self.get_effective_connections(neighbor_tile.tile_type, neighbor_tile.orientation)
                # Check if neighbor connects back *towards* the new connection
                neighbor_all_connected_dirs = set(d for exits in neighbor_effective_connections.values() for d in exits) | set(neighbor_effective_connections.keys())
                neighbor_connects_back = opposite_dir_str in neighbor_all_connected_dirs
                if not neighbor_connects_back: msg = (f"Exchange Error ({row},{col}): New connection {direction_str} from {new_tile_type.name}({new_orientation}°) is invalid, neighbor {neighbor_tile.tile_type.name}({neighbor_tile.orientation}°) at ({nr},{nc}) doesn't connect back {opposite_dir_str}."); return False, msg
            else:
                if not is_neighbor_on_board:
                    is_terminal_spot = False # TODO: Terminal check
                    if not is_terminal_spot: msg = (f"Exchange Error ({row},{col}): New connection {direction_str} from {new_tile_type.name}({new_orientation}°) leads off board (not a valid terminal)."); return False, msg
                elif neighbor_building: msg = (f"Exchange Error ({row},{col}): New connection {direction_str} from {new_tile_type.name}({new_orientation}°) points into building {neighbor_building} at ({nr},{nc})."); return False, msg
        return True, "Exchange appears valid."
    def player_action_exchange_tile(self, player: Player, new_tile_type: TileType, new_orientation: int, row: int, col: int) -> bool: # Keep corrected version
        print(f"\nAttempting P{player.player_id} exchange: {new_tile_type.name}({new_orientation}°) at ({row},{col})")
        is_valid, message = self.check_exchange_validity(player, new_tile_type, new_orientation, row, col);
        if not is_valid: print(f"--> {message}"); return False
        old_placed_tile = self.board.get_tile(row, col);
        if old_placed_tile is None: print(f"--> Internal Error: Tile disappeared before exchange at ({row},{col})."); return False
        player.hand.remove(new_tile_type); player.hand.append(old_placed_tile.tile_type); new_placed_tile = PlacedTile(new_tile_type, new_orientation); self.board.set_tile(row, col, new_placed_tile)
        self.actions_taken_this_turn += 1; print(f"--> SUCCESS exchanging {old_placed_tile.tile_type.name}({old_placed_tile.orientation}°) for {new_tile_type.name}({new_orientation}°) at ({row},{col}). Actions taken: {self.actions_taken_this_turn}/{2}"); return True

    # --- Keep Pathfinding Logic ---
    def find_path_exists(self, start_row: int, start_col: int, end_row: int, end_col: int) -> bool:
        # print(f"Pathfinding: Checking path from ({start_row},{start_col}) to ({end_row},{end_col})") # Optional debug print
        if not self.board.is_valid_coordinate(start_row, start_col) or not self.board.is_valid_coordinate(end_row, end_col): return False # Off board
        if (start_row, start_col) == (end_row, end_col): return True # Same square
        start_tile = self.board.get_tile(start_row, start_col);
        if not start_tile: return False # No start tile

        queue = deque([(start_row, start_col)]); visited: Set[Tuple[int, int]] = {(start_row, start_col)}
        while queue:
            curr_row, curr_col = queue.popleft(); current_tile = self.board.get_tile(curr_row, curr_col);
            if not current_tile: continue
            current_connections = self.get_effective_connections(current_tile.tile_type, current_tile.orientation)
            all_connected_dirs_out = set();
            for entry_dir, exit_dirs in current_connections.items():
                 if exit_dirs: all_connected_dirs_out.add(entry_dir); all_connected_dirs_out.update(exit_dirs)
            for direction_str in all_connected_dirs_out:
                direction = Direction.from_str(direction_str); opposite_dir = Direction.opposite(direction); opposite_dir_str = opposite_dir.name
                dr, dc = direction.value; nr, nc = curr_row + dr, curr_col + dc
                if (nr, nc) == (end_row, end_col):
                     neighbor_tile = self.board.get_tile(nr, nc)
                     if neighbor_tile:
                          neighbor_connections = self.get_effective_connections(neighbor_tile.tile_type, neighbor_tile.orientation)
                          neighbor_all_connected_dirs = set(d for exits in neighbor_connections.values() for d in exits) | set(neighbor_connections.keys())
                          if opposite_dir_str in neighbor_all_connected_dirs:
                               # print(f"Pathfinding Success: Reached target ({end_row},{end_col}) from ({curr_row},{curr_col}) via {direction_str}.")
                               return True
                          # else: Reached coord, but target doesn't connect back this way
                     continue # Don't proceed further if target check failed or no tile at target

                if self.board.is_valid_coordinate(nr, nc) and (nr, nc) not in visited:
                    neighbor_tile = self.board.get_tile(nr, nc)
                    if neighbor_tile:
                         neighbor_connections = self.get_effective_connections(neighbor_tile.tile_type, neighbor_tile.orientation)
                         neighbor_all_connected_dirs = set(d for exits in neighbor_connections.values() for d in exits) | set(neighbor_connections.keys())
                         if opposite_dir_str in neighbor_all_connected_dirs:
                             visited.add((nr, nc)); queue.append((nr, nc))
        # print(f"Pathfinding Failure: Queue empty, target ({end_row},{end_col}) not reached.")
        return False

    # --- Phase 5: Route Completion Logic ---

    def get_terminal_coords(self, line_number: int) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
        """Gets the two potential endpoint coordinates for a given line number."""
        # Replace with actual terminal coordinates based on the board image/rules
        # Example using TERMINAL_COORDS dict:
        coords = TERMINAL_COORDS.get(line_number)
        if coords:
            return coords[0], coords[1]
        else:
            print(f"Warning: Terminal coordinates not defined for Line {line_number}")
            return None, None

    def check_player_route_completion(self, player: Player) -> bool:
        """Checks if the player has connected terminals and stops in order."""
        if not player.line_card or not player.route_card:
            print(f"Route Check Error: Player {player.player_id} missing Line or Route card.")
            return False

        line_num = player.line_card.line_number
        stops = player.route_card.stops # Ordered list of building IDs

        # 1. Get Terminal Coordinates
        term1_coord, term2_coord = self.get_terminal_coords(line_num)
        if not term1_coord or not term2_coord:
             print(f"Route Check Error: Could not find terminal coordinates for Line {line_num}.")
             return False

        # 2. Get Stop Sign Coordinates for required stops
        stop_coords = []
        for stop_id in stops:
            coord = self.board.building_stop_locations.get(stop_id)
            if coord is None:
                 print(f"Route Check Info: Player {player.player_id} - Required stop '{stop_id}' has no stop sign placed yet.")
                 return False # Route incomplete if any required stop isn't placed
            stop_coords.append(coord)

        # 3. Check path segments in both directions (Terminal1 -> Stops -> Terminal2) AND (Terminal2 -> Stops -> Terminal1)
        #    Because the player can start at either terminal.

        # Path Sequence 1: Term1 -> Stop1 -> Stop2 -> ... -> Term2
        path1_possible = True
        sequence1 = [term1_coord] + stop_coords + [term2_coord]
        print(f"Route Check P{player.player_id} Seq1: {sequence1}")
        for i in range(len(sequence1) - 1):
            start_node = sequence1[i]
            end_node = sequence1[i+1]
            if not self.find_path_exists(start_node[0], start_node[1], end_node[0], end_node[1]):
                print(f"Route Check P{player.player_id} Seq1 FAIL: No path {start_node} -> {end_node}")
                path1_possible = False
                break # No need to check further segments in this sequence

        if path1_possible:
            print(f"Route Check P{player.player_id}: COMPLETE via sequence 1.")
            return True # Found a valid path

        # Path Sequence 2: Term2 -> Stop1 -> Stop2 -> ... -> Term1
        path2_possible = True
        sequence2 = [term2_coord] + stop_coords + [term1_coord]
        print(f"Route Check P{player.player_id} Seq2: {sequence2}")
        for i in range(len(sequence2) - 1):
            start_node = sequence2[i]
            end_node = sequence2[i+1]
            if not self.find_path_exists(start_node[0], start_node[1], end_node[0], end_node[1]):
                print(f"Route Check P{player.player_id} Seq2 FAIL: No path {start_node} -> {end_node}")
                path2_possible = False
                break # No need to check further segments in this sequence

        if path2_possible:
            print(f"Route Check P{player.player_id}: COMPLETE via sequence 2.")
            return True # Found a valid path

        # If neither sequence worked
        print(f"Route Check P{player.player_id}: INCOMPLETE - No valid path sequence found.")
        return False

    def handle_route_completion(self, player: Player):
        """Updates player and game state when a route is completed."""
        print(f"\n*** ROUTE COMPLETE for Player {player.player_id}! ***")
        player.player_state = PlayerState.DRIVING

        # Determine starting terminal (player choice, or default to one)
        # For now, let's default to term1 from the definition
        term1_coord, term2_coord = self.get_terminal_coords(player.line_card.line_number)
        if term1_coord: # Should exist if route check passed
             player.streetcar_position = term1_coord
             print(f"Player {player.player_id} streetcar placed at start terminal {term1_coord}.")
        else:
             print(f"Error: Could not determine start terminal for Player {player.player_id}")
             # Handle error state? For now, may cause issues in driving phase.

        # Update game phase if first completion
        if self.first_player_to_finish_route is None:
            self.first_player_to_finish_route = player.player_id
            # Change phase - players still laying track finish their turn,
            # then driving starts / mixed turns begin.
            # DRIVING_TRANSITION might be useful if rules require finishing the round.
            # For simplicity now, let's switch directly.
            self.game_phase = GamePhase.DRIVING
            print(f"Game Phase changing to DRIVING.")

    # --- Keep End Turn Logic ---
    def end_player_turn(self):
        active_player = self.get_active_player()
        # --- Check for route completion BEFORE drawing ---
        # (Only if the player was laying track this turn)
        route_just_completed = False
        if active_player.player_state == PlayerState.LAYING_TRACK:
            if self.check_player_route_completion(active_player):
                self.handle_route_completion(active_player)
                route_just_completed = True # Flag to skip drawing maybe?

        # --- Drawing Tiles (Only if still laying track) ---
        if active_player.player_state == PlayerState.LAYING_TRACK:
            draw_count = 0
            while len(active_player.hand) < 5 and self.tile_draw_pile:
                 if self.draw_tile(active_player):
                      draw_count += 1
            if draw_count > 0:
                 print(f"Player {active_player.player_id} drew {draw_count} tiles (Hand: {len(active_player.hand)}).")
        elif route_just_completed:
             print(f"Player {player.player_id} completed route, does not draw.")
             # Player might leave unused tiles face up? TBD rule.

        # --- Advance Turn ---
        self.active_player_index = (self.active_player_index + 1) % self.num_players
        if self.active_player_index == 0:
            self.current_turn += 1
        self.actions_taken_this_turn = 0

        next_player = self.get_active_player()
        print(f"\n--- End Turn - Starting Turn {self.current_turn} for Player {self.active_player_index} ({next_player.player_state.name}) ---")