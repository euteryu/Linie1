# game_logic/game.py
import random
import json
import traceback
import copy
from collections import deque
from typing import List, Dict, Tuple, Optional, Set, Any

# Relative imports from within the package
from .enums import PlayerState, GamePhase, Direction
from .tile import TileType, PlacedTile
from .cards import LineCard, RouteCard
from .player import Player
from .board import Board

from constants import (TILE_DEFINITIONS, TILE_COUNTS_BASE, TILE_COUNTS_5_PLUS_ADD,
                       STARTING_HAND_TILES, ROUTE_CARD_VARIANTS, TERMINAL_COORDS,
                       HAND_TILE_LIMIT, MAX_PLAYER_ACTIONS, DIE_FACES, STOP_SYMBOL)


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
        # Initialize terminals *before* potentially loading a debug layout
        self.board._initialize_terminals(self.tile_types)
        self.players = [Player(i) for i in range(num_players)]
        self.tile_draw_pile: List[TileType] = []
        self.line_cards_pile: List[LineCard] = []
        self.active_player_index: int = 0
        self.game_phase: GamePhase = GamePhase.SETUP
        self.current_turn: int = 0
        self.winner: Optional[Player] = None # <--- ENSURE THIS IS HERE
        self.actions_taken_this_turn: int = 0
        # Only call setup_game if not loading a debug layout later
        # (Setup might be handled differently based on startup flags)
        self.setup_game() # Defer this call maybe?

    def get_active_player(self) -> Player:
        return self.players[self.active_player_index]

    def __repr__(self) -> str:
        return (f"Game({self.num_players}p, Ph: {self.game_phase.name}, "
                f"T: {self.current_turn}, P: {self.active_player_index}, "
                f"Actions: {self.actions_taken_this_turn})")

    def setup_game(self):
        if self.game_phase != GamePhase.SETUP:
            return
        print("")
        print("--- Starting Setup Steps 2+ ---")
        self._create_tile_and_line_piles()
        self._deal_starting_hands()
        self._deal_player_cards()
        self.game_phase = GamePhase.LAYING_TRACK
        self.active_player_index = 0
        self.current_turn = 1
        print("--- Setup Complete ---")
        print("")

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

    def check_placement_validity(self, tile_type: TileType, orientation: int, row: int, col: int) -> Tuple[bool, str]:
        """
        Checks if placing the given tile at the specified location is valid.

        Args:
            tile_type: The type of tile to place.
            orientation: The orientation (0, 90, 180, 270).
            row: The target row coordinate.
            col: The target column coordinate.

        Returns:
            A tuple containing:
                - bool: True if placement is valid, False otherwise.
                - str: A message indicating success or the reason for failure.
        """
        # === Initial Basic Checks ===

        # Rule: Must be within the playable grid area.
        if not self.board.is_playable_coordinate(row, col):
            return False, f"Placement Error ({row},{col}): Cannot place on border or outside playable area."

        # Rule: Cannot place on a building's designated square.
        building_at_target = self.board.get_building_at(row, col)
        if building_at_target is not None:
            return False, f"Placement Error ({row},{col}): Cannot place directly on Building {building_at_target}."

        # Rule: Cannot place on a square already occupied by another tile.
        existing_tile_at_target = self.board.get_tile(row, col)
        if existing_tile_at_target is not None:
            # Allow placing over None, but not over an existing PlacedTile object
             # (Terminals are PlacedTiles, so this prevents overwriting them too)
            return False, f"Placement Error ({row},{col}): Space already occupied by {existing_tile_at_target.tile_type.name}."

        # === Neighbor Connection Checks ===

        # Calculate the connections for the *new* tile being placed.
        new_tile_connections = self.get_effective_connections(tile_type, orientation)

        # Check all four neighbors (North, East, South, West)
        for direction in Direction: # Defined in enums.py
            dir_str = direction.name             # e.g., "N"
            opposite_dir = Direction.opposite(direction)
            opposite_dir_str = opposite_dir.name # e.g., "S"

            # Calculate neighbor coordinates
            dr, dc = direction.value
            nr, nc = row + dr, col + dc

            # --- Determine if the NEW tile intends to connect towards this neighbor ---
            # It connects if the direction string ('N', 'E', 'S', 'W') appears as an exit
            # in *any* of the connection pairs defined for the new tile.
            new_tile_connects_out = dir_str in {
                exit_dir
                for exits in new_tile_connections.values()
                for exit_dir in exits
            }

            # --- Check 1: Neighbor is Off the Grid Entirely ---
            if not self.board.is_valid_coordinate(nr, nc):
                # Rule A/E: If the new tile has a connection pointing off the grid, it's invalid.
                if new_tile_connects_out:
                    return False, f"Placement Error ({row},{col}): Tile points {dir_str} off the board edge."
                else:
                    continue # No connection out this way, so off-grid neighbor is fine.

            # --- Get info about the neighbor square ---
            neighbor_tile = self.board.get_tile(nr, nc)
            neighbor_building = self.board.get_building_at(nr, nc)

            # --- Check 2: Neighbor square contains another TILE ---
            if neighbor_tile is not None:
                # Calculate the neighbor tile's connections.
                neighbor_connections = self.get_effective_connections(
                    neighbor_tile.tile_type, neighbor_tile.orientation
                )
                # Determine if the *neighbor* tile has a connection pointing back towards us.
                neighbor_connects_back = opposite_dir_str in {
                    exit_dir
                    for exits in neighbor_connections.values()
                    for exit_dir in exits
                }

                # Rule D: The connection must match. If one connects and the other doesn't, it's invalid.
                if new_tile_connects_out != neighbor_connects_back:
                    reason = "has exit" if new_tile_connects_out else "no exit"
                    neighbor_reason = "has exit back" if neighbor_connects_back else "no exit back"
                    msg = (f"Placement Error ({row},{col}): Mismatch neighbor tile ({nr},{nc}). "
                           f"New:{reason} {dir_str}, Neighbor:{neighbor_reason} {opposite_dir_str}.")
                    return False, msg
                # Else: Connections match (both connect or both don't), continue checking other neighbors.

            # --- Check 3: Neighbor square contains a BUILDING ---
            elif neighbor_building is not None:
                # Rule B: If the new tile has a connection pointing towards the building, it's invalid.
                if new_tile_connects_out:
                    msg = (f"Placement Error ({row},{col}): Tile points {dir_str} "
                           f"into building {neighbor_building} at ({nr},{nc}).")
                    return False, msg
                # Else: New tile doesn't connect towards building, that's fine.

            # --- Check 4: Neighbor square is EMPTY ---
            else: # Neighbor is empty (None for tile, None for building)
                # Rule A/E variation: If the new tile points towards an empty square
                # that is *outside* the playable area (i.e., the border margin), it's invalid.
                if new_tile_connects_out:
                    if not self.board.is_playable_coordinate(nr, nc):
                         msg = (f"Placement Error ({row},{col}): Tile points {dir_str} "
                                f"into empty non-playable border square ({nr},{nc}).")
                         return False, msg
                    # Else: Points into an empty *playable* square, which is fine.

        # If all neighbor checks passed for all directions
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

    def find_path(self, start_row: int, start_col: int, end_row: int, end_col: int) -> Optional[List[Tuple[int, int]]]:
        """Finds a path using BFS and returns the list of coordinates, or None."""
        if not self.board.is_valid_coordinate(start_row, start_col) or \
           not self.board.is_valid_coordinate(end_row, end_col):
            return None
        if (start_row, start_col) == (end_row, end_col):
            return [(start_row, start_col)]
        start_tile = self.board.get_tile(start_row, start_col)
        if not start_tile:
            return None

        queue = deque([(start_row, start_col)])
        # Store path predecessors: Key = coord, Value = predecessor_coord
        predecessor: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {(start_row, start_col): None}

        path_found = False
        while queue:
            curr_row, curr_col = queue.popleft()

            if (curr_row, curr_col) == (end_row, end_col):
                path_found = True
                break # Found the end

            current_tile = self.board.get_tile(curr_row, curr_col)
            if not current_tile: continue

            current_connections = self.get_effective_connections(current_tile.tile_type, current_tile.orientation)
            current_exit_dirs_str = {exit_dir for exits in current_connections.values() for exit_dir in exits}

            # Shuffle neighbors for potentially less predictable paths if multiple exist
            directions_to_check = list(Direction)
            random.shuffle(directions_to_check)

            for direction in directions_to_check:
                dir_str = direction.name
                opposite_dir = Direction.opposite(direction)
                opposite_dir_str = opposite_dir.name

                dr, dc = direction.value
                nr, nc = curr_row + dr, curr_col + dc

                neighbor_coord = (nr, nc)

                if not self.board.is_valid_coordinate(nr, nc): continue
                if neighbor_coord in predecessor: continue # Already visited/queued

                neighbor_tile = self.board.get_tile(nr, nc)
                if not neighbor_tile: continue

                # Two-way check
                current_connects_towards_neighbor = dir_str in current_exit_dirs_str
                neighbor_connections = self.get_effective_connections(neighbor_tile.tile_type, neighbor_tile.orientation)
                neighbor_exit_dirs_str = {exit_dir for exits in neighbor_connections.values() for exit_dir in exits}
                neighbor_connects_back_to_current = opposite_dir_str in neighbor_exit_dirs_str

                if current_connects_towards_neighbor and neighbor_connects_back_to_current:
                    predecessor[neighbor_coord] = (curr_row, curr_col)
                    queue.append(neighbor_coord)

        # Reconstruct path if found
        if path_found:
            path: List[Tuple[int, int]] = []
            curr = (end_row, end_col)
            while curr is not None:
                path.append(curr)
                curr = predecessor[curr]
            return path[::-1] # Reverse to get start -> end
        else:
            return None

    def get_terminal_coords(self, line_number: int) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]: # Keep as is
        coords = TERMINAL_COORDS.get(line_number);
        if coords: return coords[0], coords[1]
        else: print(f"Warning: Terminal coordinates not defined for Line {line_number}"); return None, None

    def _is_valid_stop_entry(self, stop_coord: Tuple[int, int], entry_direction: Direction) -> bool:
        """Checks if entering the stop_coord from entry_direction is valid based on the parallel track rule."""
        placed_tile = self.board.get_tile(stop_coord[0], stop_coord[1])
        if not placed_tile or not placed_tile.has_stop_sign:
            # This shouldn't be called if there's no stop sign, but safety check
            # print(f"Debug: _is_valid_stop_entry called on non-stop tile {stop_coord}")
            return False # Or maybe True if rule doesn't apply? Assume False.

        tile_connections = self.get_effective_connections(placed_tile.tile_type, placed_tile.orientation)
        valid_entry = False
        # Stop sign requires a straight track parallel to the building edge.
        # The entry must be via that straight track.
        # If building is N/S, straight is E/W -> Entry must be E or W.
        # If building is E/W, straight is N/S -> Entry must be N or S.

        # Find which building caused the stop
        building_id = None
        for bid, bcoord in self.board.building_stop_locations.items():
             if bcoord == stop_coord:
                  building_id = bid
                  break
        if not building_id:
             # print(f"Debug: Cannot find building ID for stop at {stop_coord}")
             return False # Should not happen

        building_actual_coord = self.board.building_coords[building_id]

        # Determine building relative position (N/S or E/W of the stop tile)
        building_is_north_south = building_actual_coord[0] != stop_coord[0]
        building_is_east_west = building_actual_coord[1] != stop_coord[1]

        if building_is_north_south: # Building is N or S, required straight is E-W
             if self._has_ew_straight(tile_connections) and (entry_direction == Direction.E or entry_direction == Direction.W):
                  valid_entry = True
        elif building_is_east_west: # Building is E or W, required straight is N-S
             if self._has_ns_straight(tile_connections) and (entry_direction == Direction.N or entry_direction == Direction.S):
                  valid_entry = True
        # Else: Diagonal placement - should not have generated a stop sign.

        # print(f"Debug: Stop entry check at {stop_coord} from {entry_direction.name}. Valid: {valid_entry}")
        return valid_entry

    # Replace in Game class in game_logic.py

    def check_player_route_completion(self, player: Player) -> Tuple[bool, Optional[List[Tuple[int, int]]]]:
        """Checks if a player's route is complete, VALIDATING stop entries. Now with error handling."""
        try: # Add try block here
            if not player.line_card or not player.route_card:
                # print(f"Route Check Error P{player.player_id}: Missing cards.") # Optional debug
                return False, None
            line_num = player.line_card.line_number
            stops_ids = player.route_card.stops
            term1_coord, term2_coord = self.get_terminal_coords(line_num)
            if not term1_coord or not term2_coord:
                print(f"Route Check Error P{player.player_id}: No terminal coords for Line {line_num}.")
                return False, None

            required_stop_coords: Dict[str, Tuple[int, int]] = {}
            stop_coords_in_order: List[Tuple[int, int]] = []
            for stop_id in stops_ids:
                coord = self.board.building_stop_locations.get(stop_id)
                if coord is None:
                    # print(f"Route Check P{player.player_id}: Required stop {stop_id} not placed.") # Optional debug
                    return False, None # Required stop sign not placed
                required_stop_coords[stop_id] = coord
                stop_coords_in_order.append(coord)

            # --- Function to check a full sequence (remains the same internally) ---
            def check_sequence(start_terminal, end_terminal, stops) -> Optional[List[Tuple[int, int]]]:
                sequence = [start_terminal] + stops + [end_terminal]
                full_path: List[Tuple[int, int]] = []
                # print(f"Debug P{player.player_id}: Checking sequence {sequence}") # Debug print
                for i in range(len(sequence) - 1):
                    start_node = sequence[i]
                    end_node = sequence[i+1]
                    # print(f"Debug P{player.player_id}: Finding path segment {start_node} -> {end_node}") # Debug print
                    segment_path = self.find_path(start_node[0], start_node[1], end_node[0], end_node[1])

                    if not segment_path:
                        # print(f"Debug P{player.player_id}: Segment FAILED {start_node} -> {end_node} (No path)") # Debug print
                        return None # Segment failed

                    # --- Validate Stop Entry IF end_node is a required stop ---
                    is_required_stop = end_node in stop_coords_in_order
                    if is_required_stop:
                        if len(segment_path) < 2:
                            # print(f"Debug P{player.player_id}: Segment FAILED {start_node} -> {end_node} (Path too short for entry check)") # Debug print
                            return None # Cannot determine entry

                        previous_coord = segment_path[-2]
                        entry_direction = self._get_entry_direction(previous_coord, end_node)

                        if not entry_direction:
                            # print(f"Debug P{player.player_id}: Segment FAILED {start_node} -> {end_node} (Could not determine entry direction)") # Debug print
                            return None

                        if not self._is_valid_stop_entry(end_node, entry_direction):
                            # print(f"Debug P{player.player_id}: Segment FAILED {start_node} -> {end_node} (INVALID stop entry at {end_node} from {entry_direction.name})") # Debug print
                            return None # Stop entry validation failed
                        # else:
                            # print(f"Debug P{player.player_id}: Segment OK {start_node} -> {end_node} (VALID stop entry at {end_node} from {entry_direction.name})") # Debug print

                    # Append segment (avoiding duplicate node)
                    full_path.extend(segment_path if i == 0 else segment_path[1:])
                    # print(f"Debug P{player.player_id}: Segment OK {start_node} -> {end_node}. Path length now: {len(full_path)}") # Debug print

                # print(f"Debug P{player.player_id}: Full sequence check successful.") # Debug print
                return full_path # Entire sequence valid

            # --- Try both sequences ---
            path1 = check_sequence(term1_coord, term2_coord, stop_coords_in_order)
            if path1:
                print(f"Route Check P{player.player_id}: COMPLETE via sequence 1 (Term1 start).")
                return True, path1

            path2 = check_sequence(term2_coord, term1_coord, stop_coords_in_order)
            if path2:
                print(f"Route Check P{player.player_id}: COMPLETE via sequence 2 (Term2 start).")
                return True, path2

            # print(f"Route Check P{player.player_id}: FAILED both sequences.") # Optional debug
            return False, None

        except Exception as e: # Add except block here
             print(f"\n!!! EXCEPTION during check_player_route_completion for P{player.player_id} !!!")
             print(f"Error: {e}")
             import traceback
             traceback.print_exc() # Print full traceback for debugging
             return False, None # Ensure tuple return on error

    # --- Modify handle_route_completion to store path ---
    def handle_route_completion(self, player: Player, validated_path: List[Tuple[int, int]]):
        print(f"\n*** ROUTE COMPLETE for Player {player.player_id}! Storing path. ***")
        player.player_state = PlayerState.DRIVING
        player.validated_route = validated_path
        player.current_route_target_index = 0 # Index for the stops list + end terminal

        # Start position is the first element of the stored path
        if player.validated_route:
             player.streetcar_position = player.validated_route[0]
             print(f"Player {player.player_id} streetcar placed at {player.streetcar_position}.")
        else:
             print(f"Error: Route complete but no valid path stored for Player {player.player_id}")
             # Handle error state? Revert player state?

        # Check if game phase should change
        if self.game_phase == GamePhase.LAYING_TRACK:
             self.game_phase = GamePhase.DRIVING
             print(f"Game Phase changing to DRIVING.")
        # If already DRIVING, no change needed

    # --- NEW Driving Methods (Step 6) ---
    def roll_special_die(self) -> Any:
        """Rolls the special Linie 1 die."""
        return random.choice(DIE_FACES)

    def trace_track_steps(self, player: Player, num_steps: int) -> Tuple[int, int]:
        """Calculates the destination coordinate after moving num_steps along the validated route."""
        if not player.validated_route or player.streetcar_position is None:
            print("Error: Cannot trace steps without a validated route or current position.")
            return player.streetcar_position if player.streetcar_position else (-1,-1) # Error case

        try:
            current_index_on_path = player.validated_route.index(player.streetcar_position)
        except ValueError:
            print(f"Error: Streetcar position {player.streetcar_position} not found in validated route.")
            # Attempt to find nearest point? For now, return current position.
            return player.streetcar_position

        target_index = min(current_index_on_path + num_steps, len(player.validated_route) - 1)
        return player.validated_route[target_index]

    def find_next_feature_on_path(self, player: Player) -> Tuple[int, int]:
        """Finds the coordinate of the next stop sign or the end terminal along the validated route."""
        if not player.validated_route or player.streetcar_position is None:
            print("Error: Cannot find next feature without route/position.")
            return player.streetcar_position if player.streetcar_position else (-1,-1)

        try:
            current_index_on_path = player.validated_route.index(player.streetcar_position)
        except ValueError:
            print(f"Error: Streetcar position {player.streetcar_position} not found in validated route.")
            return player.streetcar_position # Cannot proceed

        # Iterate from the *next* step on the path
        for i in range(current_index_on_path + 1, len(player.validated_route)):
            coord = player.validated_route[i]

            # Check if it's the final destination terminal
            if i == len(player.validated_route) - 1:
                return coord # Always stop at the end terminal

            # Check if it's a stop sign location
            tile = self.board.get_tile(coord[0], coord[1])
            if tile and tile.has_stop_sign:
                 return coord # Found the next stop sign

            # Check if it's *any* terminal location (stops at other players' terminals too)
            # This requires iterating through TERMINAL_COORDS values
            for term_coords_pair in TERMINAL_COORDS.values():
                 if coord in term_coords_pair:
                      return coord # Found any terminal

        # Should only reach here if already at the last step
        return player.validated_route[-1]


    def _get_entry_direction(self, from_coord: Tuple[int,int], to_coord: Tuple[int,int]) -> Optional[Direction]:
         """ Determines the direction of entry INTO to_coord FROM from_coord. """
         if from_coord is None or to_coord is None: # Add check for None coords
              print("Warning: _get_entry_direction received None coordinate.")
              return None

         dr = to_coord[0] - from_coord[0]
         dc = to_coord[1] - from_coord[1]
         target_delta = (dr, dc) # The change we are looking for

         # Iterate through the enum members
         for dir_name, dir_enum_member in Direction.__members__.items():
              # Access the .value tuple (dr, dc) from the enum member
              r_change, c_change = dir_enum_member.value
              if target_delta == (r_change, c_change):
                   # We found the matching direction enum member
                   return dir_enum_member

         # If no match was found (e.g., coords not adjacent)
         print(f"Warning: Could not determine entry direction from {from_coord} to {to_coord}. Delta: {target_delta}")
         return None


    def move_streetcar(self, player: Player, target_coord: Tuple[int, int]):
        """Moves the streetcar and checks if a required stop was validly visited."""
        if not player.validated_route or player.streetcar_position is None:
             print("Error: Cannot move streetcar without route/position.")
             return

        previous_coord = player.streetcar_position
        player.streetcar_position = target_coord
        print(f"Player {player.player_id} moved from {previous_coord} to {target_coord}") # More debug info

        # Check if the target is the *next required* stop
        num_required_stops = len(player.route_card.stops) if player.route_card else 0

        if player.current_route_target_index < num_required_stops:
            required_stop_id = player.route_card.stops[player.current_route_target_index]
            required_stop_coord = self.board.building_stop_locations.get(required_stop_id)

            if target_coord == required_stop_coord:
                print(f"Debug P{player.player_id}: Landed on required stop {required_stop_id} tile at {target_coord}.") # Debug print
                entry_direction = self._get_entry_direction(previous_coord, target_coord)
                if entry_direction:
                    # Use the helper function now
                    if self._is_valid_stop_entry(target_coord, entry_direction):
                        print(f"--> VALID entry for stop {required_stop_id}. Advancing target.")
                        player.current_route_target_index += 1
                    else:
                        print(f"--> INVALID entry direction ({entry_direction.name}) for stop {required_stop_id}. Target not advanced.")
                else:
                     print(f"Error: Could not determine entry direction from {previous_coord} to {target_coord}")
            # else: Landed somewhere else, not the required stop. No index change.

    def check_win_condition(self, player: Player) -> bool:
        """Checks if the player has reached their destination terminal AFTER visiting all stops."""
        # --- Basic validity checks ---
        if player.player_state != PlayerState.DRIVING:
            # Cannot win if not driving
            return False
        if not player.validated_route or player.streetcar_position is None:
            # Cannot win without a calculated route and current position
            # print(f"Debug Win Check P{player.player_id}: No route or position.") # Optional debug
            return False

        # --- Identify the destination ---
        # The destination is the VERY LAST coordinate in the validated route list
        destination_coord = player.validated_route[-1]
        # print(f"Debug Win Check P{player.player_id}: Pos={player.streetcar_position}, Dest={destination_coord}") # Optional debug


        # --- Check if player is AT the destination ---
        if player.streetcar_position == destination_coord:
             # print(f"Debug Win Check P{player.player_id}: At destination.") # Optional debug
             # --- Check if all required stops have been accounted for ---
             num_required_stops = 0
             if player.route_card and player.route_card.stops:
                 num_required_stops = len(player.route_card.stops)

             # The target index should point *beyond* the last required stop index
             if player.current_route_target_index >= num_required_stops:
                  print(f"Debug Win Check P{player.player_id}: All stops visited ({player.current_route_target_index}/{num_required_stops}). WIN!") # Optional debug
                  # --- Conditions met: Set game over state ---
                  self.game_phase = GamePhase.GAME_OVER
                  self.winner = player # Store the winning player object
                  player.player_state = PlayerState.FINISHED # Mark player as finished
                  return True
             else:
                  # Reached end terminal physically, but logic didn't register all stop visits correctly
                  print(f"Debug Win Check P{player.player_id}: Reached end but stops mismatch ({player.current_route_target_index}/{num_required_stops}). No win.")
                  return False
        else:
            # Not at the destination coordinate
            return False

    # --- Modify end_player_turn for new start-of-turn check ---
    def end_player_turn(self):
        active_player = self.get_active_player()
        was_driving = active_player.player_state == PlayerState.DRIVING

        # --- Draw tiles for LAYING_TRACK players (only if turn is truly over) ---
        if active_player.player_state == PlayerState.LAYING_TRACK and self.actions_taken_this_turn >= MAX_PLAYER_ACTIONS:
             draw_count = 0
             while len(active_player.hand) < HAND_TILE_LIMIT and self.tile_draw_pile:
                 if self.draw_tile(active_player): draw_count += 1
             if draw_count > 0: print(f"Player {active_player.player_id} drew {draw_count} tiles (Hand: {len(active_player.hand)}).")
        elif was_driving:
             print(f"Player {active_player.player_id} finished driving move.")
        # If LAYING_TRACK and actions < MAX_PLAYER_ACTIONS, don't draw yet.

        # --- Advance Player Index ---
        self.active_player_index = (self.active_player_index + 1) % self.num_players

        # --- Increment Turn Counter (only when wrapping around to Player 0) ---
        if self.active_player_index == 0:
             self.current_turn += 1

        # --- Reset Actions for the NEW player ---
        self.actions_taken_this_turn = 0
        next_player = self.get_active_player()
        print(f"\n--- Starting Turn {self.current_turn} for Player {self.active_player_index} ({next_player.player_state.name}) ---")

        # --- <<<<<< CHECK ROUTE COMPLETION AT START OF NEW TURN >>>>>>> ---
        if next_player.player_state == PlayerState.LAYING_TRACK:
             # Call the check function which now returns path
             route_complete, path = self.check_player_route_completion(next_player)
             if route_complete and path:
                  # Call handler *with* the path
                  self.handle_route_completion(next_player, path)
                  # Player state is now DRIVING, their turn starts in DrivingState
                  print(f"Player {next_player.player_id} state changed to DRIVING at turn start.")
             # else: Route not complete, player continues in LAYING_TRACK state

    # --- SAVE GAME METHOD ---
    def save_game(self, filename: str):
        """Saves the current game state to a JSON file."""
        print(f"Saving game state to {filename}...")
        try:
            game_state_data = {
                "num_players": self.num_players,
                "board": self.board.to_dict(),
                "players": [p.to_dict() for p in self.players],
                "tile_draw_pile": [tile.name for tile in self.tile_draw_pile],
                "active_player_index": self.active_player_index,
                "game_phase": self.game_phase.name,
                "current_turn": self.current_turn,
                "actions_taken": self.actions_taken_this_turn,
                "winner_id": self.winner.player_id if self.winner else None,
                 # Save first_player_to_finish_route if needed for specific variants? Not currently used.
            }
            with open(filename, 'w') as f:
                json.dump(game_state_data, f, indent=4)
            print("Save successful.")
            return True
        except Exception as e:
            print(f"!!! Error saving game to {filename}: {e} !!!")
            traceback.print_exc()
            return False

    # --- LOAD GAME STATIC METHOD ---
    @staticmethod
    def load_game(filename: str, tile_types: Dict[str, 'TileType']) -> Optional['Game']:
        """Loads a game state from a JSON file."""
        print(f"Loading game state from {filename}...")
        try:
            with open(filename, 'r') as f:
                game_state_data = json.load(f)

            num_players = game_state_data.get("num_players")
            if num_players is None or not isinstance(num_players, int) or not 2 <= num_players <= 6:
                 raise ValueError("Invalid or missing 'num_players' in save file.")

            # Create a blank Game instance without calling __init__ directly
            # This avoids running the normal setup procedure.
            loaded_game = Game.__new__(Game)

            # Manually initialize necessary attributes before loading complex parts
            loaded_game.num_players = num_players
            loaded_game.tile_types = tile_types # Must pass in the global definitions

            # Load simple attributes
            loaded_game.active_player_index = game_state_data.get("active_player_index", 0)
            try:
                loaded_game.game_phase = GamePhase[game_state_data.get("game_phase", "LAYING_TRACK")]
            except KeyError:
                 print(f"Warning: Invalid game phase '{game_state_data.get('game_phase')}' found. Defaulting to LAYING_TRACK.")
                 loaded_game.game_phase = GamePhase.LAYING_TRACK
            loaded_game.current_turn = game_state_data.get("current_turn", 1)
            loaded_game.actions_taken_this_turn = game_state_data.get("actions_taken", 0)
            loaded_game.winner = None # Will be set below if applicable

            # Load Board
            board_data = game_state_data.get("board")
            if not board_data: raise ValueError("Missing 'board' data in save file.")
            loaded_game.board = Board.from_dict(board_data, tile_types)

            # Load Players
            players_data = game_state_data.get("players", [])
            if len(players_data) != num_players:
                 print(f"Warning: Number of players in save ({len(players_data)}) doesn't match 'num_players' field ({num_players}). Using loaded players.")
                 loaded_game.num_players = len(players_data) # Adjust num_players? Or error?

            loaded_game.players = [Player.from_dict(p_data, tile_types) for p_data in players_data]

            # Assign winner object
            winner_id = game_state_data.get("winner_id")
            if winner_id is not None:
                 for p in loaded_game.players:
                      if p.player_id == winner_id:
                           loaded_game.winner = p
                           break

            # Load Draw Pile
            pile_data = game_state_data.get("tile_draw_pile", [])
            loaded_game.tile_draw_pile = [tile_types[name] for name in pile_data if name in tile_types]
            # Ensure line cards pile is empty - it's not saved/restored
            loaded_game.line_cards_pile = []

            print(f"Load successful. Phase: {loaded_game.game_phase.name}, Turn: {loaded_game.current_turn}, Active P: {loaded_game.active_player_index}")
            return loaded_game

        except FileNotFoundError:
            print(f"Error: Save file not found at {filename}")
            return None
        except Exception as e:
            print(f"!!! Error loading game from {filename}: {e} !!!")
            traceback.print_exc()
            return None

    # Ensure methods copied here use relative imports if they need classes
    # from other files within the game_logic package (most won't, they use self.*)
    # For example, load_game uses Board.from_dict, Player.from_dict which are defined
    # in their respective files but called via the staticmethod mechanism.
