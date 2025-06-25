# game_logic/game.py
import random
import json
import traceback
import copy
from collections import deque
from typing import List, Dict, Tuple, Optional, Set, Any
from queue import PriorityQueue

# --- Relative imports from within the package ---
from .enums import PlayerState, GamePhase, Direction
from .tile import TileType, PlacedTile
from .cards import LineCard, RouteCard
from .player import Player
from .board import Board
from .command_history import CommandHistory
from .commands import (Command, PlaceTileCommand,
                     ExchangeTileCommand, MoveCommand)

# --- Constants ---
# Import only those needed directly by the Game class logic
from constants import (
    TILE_DEFINITIONS, TILE_COUNTS_BASE, TILE_COUNTS_5_PLUS_ADD,
    STARTING_HAND_TILES, ROUTE_CARD_VARIANTS, TERMINAL_COORDS,
    HAND_TILE_LIMIT, MAX_PLAYER_ACTIONS, DIE_FACES, STOP_SYMBOL,
    TERMINAL_DATA
)


class Game:
    """
    Manages the overall game state, rules, and player turns for Linie 1.
    Integrates a command history for undo/redo functionality.
    """
    def __init__(self, num_players: int):
        if not 1 <= num_players <= 6:
            raise ValueError("Players must be 1-6.")
        self.num_players = num_players

        self.tile_types: Dict[str, TileType] = {
            name: TileType(name=name, **details)
            for name, details in TILE_DEFINITIONS.items()
        }
        self.board = Board()
        self.board._initialize_terminals(self.tile_types)

        self.players = [Player(i) for i in range(num_players)]
        self.tile_draw_pile: List[TileType] = []
        self.line_cards_pile: List[LineCard] = [] # Only used during setup

        self.active_player_index: int = 0
        self.game_phase: GamePhase = GamePhase.SETUP
        self.current_turn: int = 0
        self.winner: Optional[Player] = None
        self.actions_taken_this_turn: int = 0

        self.command_history = CommandHistory()

        # Defer setup_game call to application entry point
        # self.setup_game()

    # === Core Game Access ===

    def get_active_player(self) -> Player:
        """Returns the player whose turn it currently is."""
        # Basic bounds check, though index should always be valid
        if 0 <= self.active_player_index < len(self.players):
             return self.players[self.active_player_index]
        else:
             # This case indicates a serious error state
             raise IndexError("Active player index out of bounds.")

    # === Game Setup ===

    def setup_game(self):
        """Initializes piles, deals starting hands and cards."""
        if self.game_phase != GamePhase.SETUP:
            print("Warning: setup_game called when not in SETUP phase.")
            return # Avoid re-running setup

        print("--- Starting Game Setup ---")
        self._create_tile_and_line_piles()
        self._deal_starting_hands()
        self._deal_player_cards()
        self.game_phase = GamePhase.LAYING_TRACK
        self.active_player_index = 0 # Start with Player 0
        self.current_turn = 1
        self.actions_taken_this_turn = 0
        self.command_history.clear() # Clear history for new game
        print("--- Setup Complete ---")

    def _create_tile_and_line_piles(self):
        """Creates and shuffles the tile draw pile."""
        print("Creating draw piles...")
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
                print(f"Warning: Tile type '{name}' not found for pile.")

        # Verification (optional but good)
        expected_total = sum(tile_counts.values())
        if len(self.tile_draw_pile) != expected_total:
             raise RuntimeError(f"Tile pile count mismatch!")

        random.shuffle(self.tile_draw_pile)
        print(f"Tile draw pile created: {len(self.tile_draw_pile)} tiles.")

        # Line cards dealt separately now
        # self.line_cards_pile = [LineCard(i) for i in range(1, 7)] # 6 Lines in Default game
        self.line_cards_pile = [LineCard(i) for i in range(1, 2)] # 1 Line in Test#1 game
        random.shuffle(self.line_cards_pile)

    def _deal_starting_hands(self):
        """Deals the initial 3 straights and 2 curves to each player."""
        print("Dealing starting hands...")
        straight_type = self.tile_types.get('Straight')
        curve_type = self.tile_types.get('Curve')
        if not straight_type or not curve_type:
            raise RuntimeError("Straight/Curve TileType missing.")

        # Check if enough tiles exist before dealing

        for player in self.players:
            player.hand = []
            # Efficiently find and remove starting tiles
            s_needed = STARTING_HAND_TILES['Straight']
            c_needed = STARTING_HAND_TILES['Curve']
            temp_pile = self.tile_draw_pile[:] # Work on a copy
            hand_tiles = []

            # Find Straights
            indices_s = [i for i, t in enumerate(temp_pile) if t == straight_type]
            if len(indices_s) < s_needed: raise RuntimeError("Not enough Straights")
            hand_tiles.extend([straight_type] * s_needed)
            # Mark chosen straights for removal later
            straights_to_remove = random.sample(indices_s, s_needed)

            # Find Curves
            indices_c = [i for i, t in enumerate(temp_pile) if t == curve_type]
            if len(indices_c) < c_needed: raise RuntimeError("Not enough Curves")
            hand_tiles.extend([curve_type] * c_needed)
            # Mark chosen curves for removal later
            curves_to_remove = random.sample(indices_c, c_needed)

            # Remove chosen tiles from the main draw pile efficiently
            all_indices_to_remove = sorted(straights_to_remove + curves_to_remove, reverse=True)
            if len(set(all_indices_to_remove)) != len(all_indices_to_remove):
                 # This indicates an overlap, which shouldn't happen with separate lists
                 raise RuntimeError("Logic error in selecting start tiles")
            for index in all_indices_to_remove:
                 del self.tile_draw_pile[index] # Remove from original pile

            player.hand = hand_tiles # Assign the collected tiles

        print(f"Finished dealing start hands. Pile: {len(self.tile_draw_pile)}")


    def _deal_player_cards(self):
        """Deals one Line card and one Route card to each player."""
        print("Dealing player cards...")
        if len(self.line_cards_pile) < self.num_players:
            raise RuntimeError("Not enough Line cards!")

        available_variants = list(range(len(ROUTE_CARD_VARIANTS)))
        random.shuffle(available_variants)
        if len(available_variants) < self.num_players:
             raise RuntimeError("Not enough Route card variants!")

        player_range = "1-4" if self.num_players <= 4 else "5-6"

        for player in self.players:
            player.line_card = self.line_cards_pile.pop()
            variant_index = available_variants.pop()
            try:
                line_num = player.line_card.line_number
                stops = ROUTE_CARD_VARIANTS[variant_index][player_range][line_num]
            except (KeyError, IndexError) as e:
                err_msg = (f"Error lookup route: Var={variant_index}, "
                           f"Rng={player_range}, Line={line_num}. Err: {e}")
                raise RuntimeError(err_msg)
            player.route_card = RouteCard(stops, variant_index)

        self.line_cards_pile = [] # Clear remaining pile

    # === Game Logic Helpers ===

    def _rotate_direction(self, direction: str, angle: int) -> str:
        """Rotates a direction string by a multiple of 90 degrees."""
        directions = ['N', 'E', 'S', 'W']
        try:
            current_index = directions.index(direction)
        except ValueError:
            raise ValueError(f"Invalid direction string: {direction}")

        angle = angle % 360
        if angle % 90 != 0:
            raise ValueError(f"Invalid rotation angle: {angle}.")

        steps = angle // 90
        new_index = (current_index + steps) % 4
        return directions[new_index]

    def get_effective_connections(self, tile_type: TileType,
                                 orientation: int) -> Dict[str, List[str]]:
        """Gets the connections for a tile type at a given orientation."""
        if orientation == 0:
            # Return a deep copy to prevent modification of base connections
            return copy.deepcopy(tile_type.connections_base)

        rotated_connections: Dict[str, List[str]] = \
            {'N': [], 'E': [], 'S': [], 'W': []}
        base_connections = tile_type.connections_base

        for base_entry_dir, base_exit_dirs in base_connections.items():
            actual_entry_dir = self._rotate_direction(base_entry_dir, orientation)
            # Ensure list exists before appending
            if actual_entry_dir not in rotated_connections:
                 rotated_connections[actual_entry_dir] = []

            for base_exit_dir in base_exit_dirs:
                actual_exit_dir = self._rotate_direction(base_exit_dir, orientation)
                # Avoid duplicates
                if actual_exit_dir not in rotated_connections[actual_entry_dir]:
                    rotated_connections[actual_entry_dir].append(actual_exit_dir)

        # Sort exits for consistency (optional but good for comparisons)
        for key in rotated_connections:
            rotated_connections[key].sort()
        return rotated_connections

    def _has_ns_straight(self, effective_connections: Dict[str, List[str]]) -> bool:
        """Checks if connections represent a North-South straight path."""
        return 'S' in effective_connections.get('N', [])

    def _has_ew_straight(self, effective_connections: Dict[str, List[str]]) -> bool:
        """Checks if connections represent an East-West straight path."""
        return 'W' in effective_connections.get('E', [])

    def _get_terminal_area_coords(self, line_number: int,
                                  terminal_coord: Tuple[int, int]
                                  ) -> Set[Tuple[int, int]]:
        """
        Helper to find the pair of coordinates defining the terminal area
        that includes the given terminal_coord for the specified line.
        Returns an empty set if not found or data is invalid.
        """
        # Use TERMINAL_DATA which holds the detailed pairs and orientations
        entrances = TERMINAL_DATA.get(line_number)
        if not entrances:
             print(f"Warning: No TERMINAL_DATA found for Line {line_number}")
             return set()

        # TERMINAL_DATA format: { line: ( entrance_a, entrance_b ) }
        # entrance_a format: ( ((r1,c1), orient1), ((r2,c2), orient2) )
        try:
            for entrance_pair_info in entrances: # Iterate through entrance_a, entrance_b
                 # Extract the two coordinates defining this entrance area
                 coord1 = entrance_pair_info[0][0]
                 coord2 = entrance_pair_info[1][0]
                 coords_in_pair = {coord1, coord2}
                 # Check if the given terminal_coord is one of these two
                 if terminal_coord in coords_in_pair:
                      # Found the matching pair, return the set of both coords
                      return coords_in_pair
        except (IndexError, TypeError) as e:
             print(f"Error parsing TERMINAL_DATA for Line {line_number}: {e}")
             # Fall through to return empty set if format is wrong

        # If the terminal_coord wasn't found in any defined pair for the line
        print(f"Warning: Coord {terminal_coord} not found in "
              f"TERMINAL_DATA pairs for Line {line_number}")
        return set()

    # === Placement/Exchange Validity Checks ===
    # (These are called by Commands or externally)

    def check_placement_validity(self, tile_type: TileType,
                                 orientation: int, row: int, col: int
                                 ) -> Tuple[bool, str]:
        """ Checks if placing the given tile is valid (Readable version). """
        # (Implementation from previous answer - kept readable)
        if not self.board.is_playable_coordinate(row, col): return False, f"Error ({row},{col}): Cannot place on border."
        building = self.board.get_building_at(row, col); # ... check building ...
        if building is not None: return False, f"Error ({row},{col}): Cannot place on Building {building}."
        existing = self.board.get_tile(row, col); # ... check existing ...
        if existing is not None: return False, f"Error ({row},{col}): Space occupied."
        new_conns = self.get_effective_connections(tile_type, orientation)
        for direction in Direction: # ... loop through neighbors ...
            dir_str = direction.name; opp_dir_str = Direction.opposite(direction).name
            dr, dc = direction.value; nr, nc = row + dr, col + dc
            new_connects_out = dir_str in {ex for exits in new_conns.values() for ex in exits}
            if not self.board.is_valid_coordinate(nr, nc): # Off grid
                if new_connects_out: return False, f"Error ({row},{col}): Points {dir_str} off grid."
                continue
            n_tile = self.board.get_tile(nr, nc); n_bldg = self.board.get_building_at(nr, nc)
            if n_tile: # Neighbor is Tile
                n_conns = self.get_effective_connections(n_tile.tile_type, n_tile.orientation)
                n_connects_back = opp_dir_str in {ex for exits in n_conns.values() for ex in exits}
                if new_connects_out != n_connects_back: return False, f"Error ({row},{col}): Mismatch {dir_str} neighbor ({nr},{nc})."
            elif n_bldg: # Neighbor is Building
                if new_connects_out: return False, f"Error ({row},{col}): Points {dir_str} into Building {n_bldg}."
            else: # Neighbor is Empty
                if new_connects_out and not self.board.is_playable_coordinate(nr, nc):
                    return False, f"Error ({row},{col}): Points {dir_str} into border space."
        return True, "Placement appears valid."


    def _check_and_place_stop_sign(self, placed_tile: PlacedTile,
                                   row: int, col: int):
        """ Checks neighbors and places stop sign if applicable. """
        # Ensure tile is actually on board at location (safety check)
        if self.board.get_tile(row, col) != placed_tile: return

        # Reset sign status (relevant if called after undo/redo)
        # This assumes _check is the SOLE source of truth for sign placement
        # placed_tile.has_stop_sign = False # Let command undo handle removal

        tile_connections = self.get_effective_connections(
            placed_tile.tile_type, placed_tile.orientation
        )

        for direction in Direction:
            dr, dc = direction.value
            nr, nc = row + dr, col + dc

            if not self.board.is_valid_coordinate(nr, nc): continue

            building_id = self.board.get_building_at(nr, nc)
            # Place sign only if building exists AND doesn't have one yet
            if building_id and building_id not in self.board.buildings_with_stops:
                has_parallel_track = False
                # Building North/South -> Check for E/W track on placed tile
                if direction == Direction.N or direction == Direction.S:
                    if self._has_ew_straight(tile_connections):
                        has_parallel_track = True
                # Building East/West -> Check for N/S track on placed tile
                elif direction == Direction.E or direction == Direction.W:
                    if self._has_ns_straight(tile_connections):
                        has_parallel_track = True

                if has_parallel_track:
                    placed_tile.has_stop_sign = True
                    self.board.buildings_with_stops.add(building_id)
                    self.board.building_stop_locations[building_id] = (row, col)
                    print(f"--> Placed stop sign at ({row},{col}) "
                          f"for Building {building_id}.")
                    break # Only one stop sign per tile placement action


    # check_exchange_validity - Keep stub or refactor for command use
    def check_exchange_validity(self, player: Player, new_tile_type: TileType,
                                new_orientation: int, row: int, col: int
                                ) -> Tuple[bool, str]:
        """ Checks if exchanging tile is valid (Basic checks only for now). """
        # TODO: Refactor to not need player hand and do full conn checks
        old_tile = self.board.get_tile(row, col)
        if not old_tile: return False, "No tile to exchange."
        if not self.board.is_playable_coordinate(row, col): return False, "Cannot exchange border."
        if old_tile.is_terminal: return False, "Cannot exchange terminal."
        if not old_tile.tile_type.is_swappable: return False, "Tile not swappable."
        if old_tile.has_stop_sign: return False, "Cannot exchange stop sign tile."
        # Missing: Connection preservation/validity checks
        return True, "Exchange basic checks passed (Connections not fully checked)."


    # === Tile Drawing ===

    def draw_tile(self, player: Player) -> bool:
        """ Player draws one tile into hand if possible. """
        if not self.tile_draw_pile:
            print("Warning: Draw pile empty!")
            return False
        if len(player.hand) >= HAND_TILE_LIMIT:
            print(f"Warning: Player {player.player_id} hand already full.")
            return False # Cannot draw if hand full

        tile = self.tile_draw_pile.pop()
        player.hand.append(tile)
        return True

    # === Player Actions (Using Command Pattern) ===

    def attempt_place_tile(self, player: Player, tile_type: TileType,
                           orientation: int, row: int, col: int) -> bool:
        """ Creates and executes a PlaceTileCommand. """
        if self.actions_taken_this_turn >= MAX_PLAYER_ACTIONS:
            print("Action Error: Max actions reached.")
            return False
        if player.player_state != PlayerState.LAYING_TRACK:
            print("Action Error: Not in laying track state.")
            return False

        command = PlaceTileCommand(self, player, tile_type,
                                   orientation, row, col)
        if self.command_history.execute_command(command):
            self.actions_taken_this_turn += 1
            return True
        return False

    def attempt_exchange_tile(self, player: Player, new_tile_type: TileType,
                              new_orientation: int, row: int, col: int
                              ) -> bool:
        """ Creates and executes an ExchangeTileCommand. """
        if self.actions_taken_this_turn >= MAX_PLAYER_ACTIONS:
            print("Action Error: Max actions reached.")
            return False
        if player.player_state != PlayerState.LAYING_TRACK:
            print("Action Error: Not in laying track state.")
            return False

        command = ExchangeTileCommand(self, player, new_tile_type,
                                      new_orientation, row, col)
        if self.command_history.execute_command(command):
            self.actions_taken_this_turn += 1
            return True
        return False

    def attempt_driving_move(self, player: Player, roll_result: Any) -> bool:
        """ Creates and executes MoveCommand after determining target. """
        if player.player_state != PlayerState.DRIVING: return False
        if self.actions_taken_this_turn > 0: return False

        # --- Check if required player attributes exist ---
        if player.start_terminal_coord is None or player.line_card is None:
             print("Error: Cannot drive - start terminal or line card missing.")
             # Maybe end turn automatically here?
             self.actions_taken_this_turn = MAX_PLAYER_ACTIONS
             self.confirm_turn() # End turn if essential data missing
             return False # Indicate failure

        target_coord: Optional[Tuple[int, int]] = None
        # --- Get the set of coordinates for the STARTING terminal area ---
        # <<< FIX: Pass BOTH arguments >>>
        start_term_area_to_avoid = self._get_terminal_area_coords(
            player.line_card.line_number,
            player.start_terminal_coord
        )
        if not start_term_area_to_avoid:
            # Warning if area couldn't be found, but proceed without avoid set
             print(f"Warning: Could not determine start terminal area for P{player.player_id}")


        # --- Determine target_coord using pathfinding (passing avoid set) ---
        if roll_result == STOP_SYMBOL:
             target_coord = self.find_next_feature_on_path(
                 player, start_term_area_to_avoid
             )
        elif isinstance(roll_result, int):
             target_coord = self.trace_track_steps(
                 player, roll_result, start_term_area_to_avoid
             )
        else:
             print(f"Driving Error: Invalid roll {roll_result}")
             self.actions_taken_this_turn = MAX_PLAYER_ACTIONS # End turn on bad roll
             self.confirm_turn()
             return False # Indicate failure

        # --- Handle cases where no target found or no move needed ---
        if target_coord is None:
             print(f"Driving Error: No target for roll {roll_result}.")
             self.actions_taken_this_turn = MAX_PLAYER_ACTIONS
             self.confirm_turn()
             return False # Indicate failure (though turn ends)

        if target_coord == player.streetcar_position:
            print(f"Driving Info: No move required for roll {roll_result}.")
            self.actions_taken_this_turn = MAX_PLAYER_ACTIONS
            self.confirm_turn()
            return True # Turn ends, no state change needed by command

        # --- Create and execute Move Command ---
        command = MoveCommand(self, player, target_coord)
        if self.command_history.execute_command(command):
             # Command handles position/index update and win check
             self.actions_taken_this_turn = MAX_PLAYER_ACTIONS
             if self.game_phase != GamePhase.GAME_OVER:
                  print("Auto-confirming driving turn...")
                  self.confirm_turn()
             return True
        else:
             print("Driving Error: Move command execution failed.")
             self.actions_taken_this_turn = MAX_PLAYER_ACTIONS
             self.confirm_turn() # End turn even if command fails? Maybe.
             return False


    def _heuristic(self, node_a: Tuple[int, int], node_b: Tuple[int, int]) -> int:
        """Calculates Manhattan distance heuristic."""
        (r1, c1) = node_a
        (r2, c2) = node_b
        return abs(r1 - r2) + abs(c1 - c2)

    def _find_any_path(self,
                       start_node: Tuple[int, int],
                       end_node: Tuple[int, int],
                       direction_of_arrival_at_start_node: Optional[Direction] = None
                      ) -> Optional[List[Tuple[int, int]]]:
        """
        Standard A* to find *a* shortest path.
        Only constraint: "no immediate U-turn" from start_node.
        (This is your existing A* with V2 debug prints, ensure it's complete)
        """
        # ... (Full implementation of your standard A* as previously debugged)
        # This needs to be the one that works correctly for general pathfinding.
        # For brevity, not repeated, but assume it's your functional A* from earlier.
        # It MUST correctly handle the 'direction_of_arrival_at_start_node' for U-turns.
        active_player_id = self.get_active_player().player_id if self.players and 0 <= self.active_player_index < len(self.players) else '?'
        print(f"--- Called _find_any_path (Std A*) for P{active_player_id}: {start_node} -> {end_node} "
              f"(Arrival at start: {direction_of_arrival_at_start_node}) ---")
        # Example (replace with your actual A* logic):
        if start_node == end_node: return [start_node]
        # This is a STUB - ensure your working A* is here.
        # if start_node==(0,3) and end_node==(1,3): return [(0,3),(1,3)] # Dummy success for testing
        return None # Default fail


    # --- ROUTE VALIDATION HELPERS ---
    def _get_player_sequence_data(self, player: Player,
                                   start_terminal_for_sequence: Tuple[int, int],
                                   end_terminal_for_sequence: Tuple[int, int]
                                   ) -> Tuple[Optional[List[Tuple[int, int]]],
                                              Optional[List[Tuple[int, int]]],
                                              Optional[Set[Tuple[int, int]]]]:
        """
        Gathers stop coordinates and forms the full node sequence for one direction.
        Returns (sequence_nodes, stop_coords_in_order, stop_coord_set),
        or (None, None, None) if required stops are not on the board.
        """
        if not player.route_card: # Should be checked by caller
            return None, None, None

        required_stops_ids = player.route_card.stops
        stop_coords_in_order: List[Tuple[int, int]] = []
        all_stops_found = True
        for stop_id in required_stops_ids:
            coord = self.board.building_stop_locations.get(stop_id)
            if coord is None:
                print(f"*** P{player.player_id}: Validating sequence: "
                      f"STOP SIGN MISSING for '{stop_id}' ***")
                all_stops_found = False
                break # Stop processing if a required stop sign is missing
            stop_coords_in_order.append(coord)

        if required_stops_ids and not all_stops_found:
            return None, None, None # Cannot form sequence

        # Construct the full sequence of nodes to visit
        sequence_nodes = ([start_terminal_for_sequence] +
                          stop_coords_in_order +
                          [end_terminal_for_sequence])
        stop_coord_set = set(stop_coords_in_order)

        return sequence_nodes, stop_coords_in_order, stop_coord_set


    def _validate_segment_strictly(self,
                                 player: Player,
                                 segment_start_node: Tuple[int, int],
                                 segment_end_node: Tuple[int, int],
                                 node_after_segment_end_in_sequence: Optional[Tuple[int, int]],
                                 is_segment_end_node_a_stop: bool,
                                 arrival_constraint_at_segment_start: Optional[Direction]
                                 ) -> Tuple[bool, Optional[Direction], int]:
        """
        Validates one segment A->B strictly.
        Returns (isSegmentValid, arrivalConstraintForNextSegment, segmentLength)
        """
        segment_length = 0
        print(f"  DBG P{player.player_id}: Validating Segment (Strict) "
              f"{segment_start_node} -> {segment_end_node}")
        # ... (debug print for initial U-turn constraint) ...
        arrival_constraint_desc = "None (no U-turn restriction from start)"
        if arrival_constraint_at_segment_start:
            arrival_constraint_desc = (f"Cannot exit {segment_start_node} via "
                                    f"{Direction.opposite(arrival_constraint_at_segment_start).name} "
                                    f"(U-turn from arrival {arrival_constraint_at_segment_start.name})")
        print(f"    Initial U-Turn Constraint for this A* call: {arrival_constraint_desc}")


        required_entries_at_target = None
        if is_segment_end_node_a_stop:
            required_entries_at_target = set()
            for dir_enum in Direction:
                if self._is_valid_stop_entry(segment_end_node, dir_enum):
                    required_entries_at_target.add(dir_enum)
            if not required_entries_at_target:
                print(f"    FAIL: Stop {segment_end_node} has NO valid entry directions.")
                return False, None, float('inf')
            print(f"    Target {segment_end_node} (Stop) requires entry via: "
                  f"{required_entries_at_target}")

        # --- Path to end_node using the strictly constrained A* ---
        path_to_end_node = self.find_path_astar_constrained(
            segment_start_node, segment_end_node,
            direction_of_arrival_at_start_node=arrival_constraint_at_segment_start,
            target_is_stop=is_segment_end_node_a_stop,
            required_entry_directions_at_target=required_entries_at_target
        )

        if not path_to_end_node:
            print(f"    FAIL: No path by find_path_astar_constrained for "
                  f"{segment_start_node} -> {segment_end_node}")
            return False, None, float('inf')
        segment_length += (len(path_to_end_node) - 1)
        print(f"    SUCCESS: Path to {segment_end_node} found: {path_to_end_node}")

        if len(path_to_end_node) < 2: return False, None, float('inf')

        actual_entry_direction_at_end_node = self._get_entry_direction(
            path_to_end_node[-2], segment_end_node
        )
        if not actual_entry_dir_at_end_node:
            print(f"    FAIL: Cannot determine actual entry into {segment_end_node}")
            return False, None, float('inf')

        # This will be the U-turn constraint for the *next* segment's A* call
        arrival_constraint_for_next_segment = actual_entry_dir_at_end_node

        if is_segment_end_node_a_stop:
            print(f"    Stop {segment_end_node} entered via {actual_entry_dir_at_end_node.name}.")

            # --- CORRECTED EXIT LOGIC ---
            # To continue "straight through" the stop, the exit direction
            # must be the SAME as the valid entry direction along that straight axis.
            required_exit_direction = actual_entry_dir_at_end_node
            # --- END CORRECTION ---
            print(f"    Stop {segment_end_node} requires EXIT via {required_exit_direction.name} "
                  f"(continuing along the straight from entry {actual_entry_dir_at_end_node.name})")

            stop_tile = self.board.get_tile(segment_end_node[0], segment_end_node[1])
            if not stop_tile: return False, None, float('inf')

            stop_connections = self.get_effective_connections(stop_tile.tile_type, stop_tile.orientation)

            # Determine the entry port used to enter the stop tile
            entry_port_for_stop = Direction.opposite(actual_entry_dir_at_end_node).name
            valid_exits_from_this_entry_port = stop_connections.get(entry_port_for_stop, [])

            # Check if the required_exit_direction is a valid exit FROM THAT ENTRY PORT
            if required_exit_direction.name not in valid_exits_from_this_entry_port:
                print(f"    FAIL: Stop tile {segment_end_node} (entered via {entry_port_for_stop}) "
                      f"does not connect to exit {required_exit_direction.name}. "
                      f"Valid exits were: {valid_exits_from_this_entry_port}")
                return False, None, float('inf')
            print(f"    Stop tile {segment_end_node} physically allows required exit {required_exit_direction.name}.")


            if node_after_segment_end_in_sequence:
                dr_ex, dc_ex = required_exit_dir.value
                step_out_coord = (segment_end_node[0] + dr_ex, segment_end_node[1] + dc_ex)

                if not self.board.is_valid_coordinate(step_out_coord[0], step_out_coord[1]):
                    print(f"    FAIL: Required exit leads off board from {segment_end_node}.")
                    return False, None, float('inf')

                print(f"    Checking path from exit-neighbor {step_out_coord} "
                      f"-> {node_after_segment_end_in_sequence}")
                # Path from step_out_coord: target is not typically a constrained stop for *this* sub-path call
                path_from_exit_n = self.find_path_astar_constrained( # Use constrained A*
                    start_node=step_out_coord,
                    end_node=node_after_segment_end_in_sequence,
                    direction_of_arrival_at_start_node=required_exit_dir, # Arrived at step_out via exit_dir
                    target_is_stop=False, # Usually False, unless next node is also a stop
                                          # and needs specific entry validation immediately.
                                          # For now, assume general connectivity.
                    required_entry_directions_at_target=None
                )
                if not path_from_exit_n:
                    print(f"    FAIL: No path from {step_out_coord} to {node_after_segment_end_in_sequence}.")
                    return False, None, float('inf')
                # segment_length += (len(path_from_exit_n) -1) # Add length if needed

            # If exit was successful, this required_exit_direction becomes the
            # arrival constraint for the start of the *next overall segment*.
            arrival_constraint_for_next_segment = required_exit_dir
            print(f"    Stop {segment_end_node} PASSED Strict. Next constraint: {arrival_constraint_for_next_segment.name}")

        return True, arrival_constraint_for_next_segment, segment_length


    def _validate_full_node_sequence(self,
                                   player: Player,
                                   sequence_nodes: List[Tuple[int, int]],
                                   stop_coord_set: Set[Tuple[int, int]]
                                   ) -> Tuple[bool, int]:
        """ Validates all segments in a given node sequence strictly. """
        print(f"DBG P{player.player_id}: Validating Full Sequence: {sequence_nodes}")
        arrival_constraint_for_segment_start: Optional[Direction] = None
        current_total_length = 0

        for i in range(len(sequence_nodes) - 1):
            start_node = sequence_nodes[i]
            end_node = sequence_nodes[i+1]
            node_after_current_end = sequence_nodes[i+2] if (i+2) < len(sequence_nodes) else None
            is_end_node_a_stop = end_node in stop_coord_set

            segment_valid, next_arrival_constraint, seg_len = self._validate_segment_strictly(
                player, start_node, end_node,
                node_after_segment_end_in_sequence=node_after_current_end, # Pass it here
                is_segment_end_node_a_stop=is_end_node_a_stop,
                arrival_constraint_at_segment_start=arrival_constraint_for_segment_start
            )

            if not segment_valid:
                print(f"DBG P{player.player_id}: Full Sequence FAILED at segment "
                      f"{start_node}->{end_node}")
                return False, float('inf')

            if seg_len == float('inf'): # Should be caught by segment_valid but safety
                return False, float('inf')
            current_total_length += seg_len
            arrival_constraint_for_segment_start = next_arrival_constraint

        print(f"DBG P{player.player_id}: Full Sequence VALIDATED: {sequence_nodes}, Length: {current_total_length}")
        return True, current_total_length


    # --- MAIN ORCHESTRATOR ---
    def check_player_route_completion(self, player: Player) -> Tuple[bool, Optional[Tuple[int, int]]]:
        """
        Orchestrates route completion check by validating both possible
        directional sequences and choosing an optimal start if valid.
        Returns (isComplete: bool, chosenStartTerminalCoord: Optional[Tuple[int,int]]).
        """
        print(f"--- Checking P{player.player_id} Route Completion (Refactored V4) ---")
        if not player.line_card or not player.route_card: return False, None

        line_num = player.line_card.line_number
        term1_coord, term2_coord = self.get_terminal_coords(line_num)
        if not term1_coord or not term2_coord:
            print(f"Error P{player.player_id}: No term coords for Line {line_num}")
            return False, None

        # --- Prepare sequence data (stops must be on board) ---
        # _get_player_sequence_data now just gets the stop coords and checks existence
        required_stops_ids = player.route_card.stops
        stop_coords_in_order: List[Tuple[int,int]] = []
        all_stops_on_board = True
        for stop_id in required_stops_ids:
            coord = self.board.building_stop_locations.get(stop_id)
            if coord is None:
                all_stops_on_board = False;
                print(f"*** P{player.player_id}: Required stop '{stop_id}' not on board. ***")
                break
            stop_coords_in_order.append(coord)

        if required_stops_ids and not all_stops_on_board:
            print(f"Route Check P{player.player_id}: FAILED - Not all stops placed.")
            return False, None
        
        stop_coord_set = set(stop_coords_in_order)

        # --- Validate Sequence 1: Term1 -> Stops -> Term2 ---
        seq1_nodes = [term1_coord] + stop_coords_in_order + [term2_coord]
        valid_from_t1, len_from_t1 = self._validate_full_node_sequence(
            player, seq1_nodes, stop_coord_set
        )
        print(f"DBG P{player.player_id}: Overall validation from T1 ({term1_coord}): {valid_from_t1}, Len: {len_from_t1}")

        # --- Validate Sequence 2: Term2 -> Stops -> Term1 ---
        seq2_nodes = [term2_coord] + stop_coords_in_order + [term1_coord]
        valid_from_t2, len_from_t2 = self._validate_full_node_sequence(
            player, seq2_nodes, stop_coord_set
        )
        print(f"DBG P{player.player_id}: Overall validation from T2 ({term2_coord}): {valid_from_t2}, Len: {len_from_t2}")

        # --- Determine Outcome and Choose Optimal Start ---
        if not valid_from_t1 and not valid_from_t2:
            print(f"Route Check P{player.player_id}: FAILED - No valid sequence direction.")
            return False, None

        chosen_start: Optional[Tuple[int, int]] = None

        if not stop_coords_in_order: # Only terminals to connect
            print(f"DBG P{player.player_id}: No stops; choosing based on sequence validity only.")
            if valid_from_t1: chosen_start = term1_coord
            elif valid_from_t2: chosen_start = term2_coord
            if valid_from_t1 and valid_from_t2 and len_from_t1 <= len_from_t2 : chosen_start = term1_coord # Prefer T1 if lengths are equal
            elif valid_from_t1 and valid_from_t2 and len_from_t2 < len_from_t1 : chosen_start = term2_coord
        else:
            # Compare *overall valid sequence lengths* if both are valid
            print(f"--- DBG P{player.player_id} Optimal Start (using full valid seq lengths) ---")
            print(f"  valid_from_term1: {valid_from_t1}, FULL_len_from_t1: {len_from_t1}")
            print(f"  valid_from_term2: {valid_from_t2}, FULL_len_from_t2: {len_from_t2}")

            if valid_from_t1 and valid_from_t2:
                if len_from_t1 <= len_from_t2: chosen_start = term1_coord
                else: chosen_start = term2_coord
            elif valid_from_t1:
                chosen_start = term1_coord
            elif valid_from_t2:
                chosen_start = term2_coord

            if chosen_start: print(f"  Choice based on full valid sequence length: {chosen_start}")
            else: print(f"  WARN P{player.player_id}: Logic error choosing start when one sequence should be valid.")


        if chosen_start:
             print(f"Route Check P{player.player_id}: FINAL COMPLETE. Chosen Start: {chosen_start}")
             player.start_terminal_coord = chosen_start # Set it for handle_route_completion
             return True, chosen_start
        else:
             print(f"*** Route Check P{player.player_id}: FINAL FAIL. No start chosen. ***")
             return False, None


    def find_path_astar_constrained(self,
                  start_node: Tuple[int, int],
                  end_node: Tuple[int, int],
                  # This is the direction of the step that LED TO start_node
                  # for this specific A* search instance.
                  direction_of_arrival_at_start_node: Optional[Direction] = None,
                  # Constraint parameters for the target (end_node)
                  target_is_stop: bool = False,
                  required_entry_directions_at_target: Optional[Set[Direction]] = None
                 ) -> Optional[List[Tuple[int, int]]]:
        """
        Finds the shortest path using A* search, PRUNING paths that violate
        entry constraints at the target_node if specified. Also handles
        "no U-turn" and valid exits from the current tile based on entry.
        """
        active_player_id = self.get_active_player().player_id if self.players and \
                           0 <= self.active_player_index < len(self.players) else '?'

        print(f"\n--- A* CONSTRAINED Search P{active_player_id}: {start_node} -> {end_node} ---")
        print(f"    Initial U-Turn Constraint (arrival at start_node {start_node}): {direction_of_arrival_at_start_node}")
        if target_is_stop:
            print(f"    Target {end_node} IS a Stop. Required Entries: {required_entry_directions_at_target}")
        else:
            print(f"    Target {end_node} is NOT a stop (no target entry constraint).")

        # --- 1. Basic Validation ---
        if not self.board.is_valid_coordinate(start_node[0], start_node[1]) or \
           not self.board.is_valid_coordinate(end_node[0], end_node[1]):
            print("    A* Constrained Fail: Invalid start/end coordinate.")
            return None
        if start_node == end_node:
            # Path to self is just the node. Entry constraint for a 0-step path is moot.
            print("    A* Constrained Success: Start node IS end node.")
            return [start_node]
        start_tile_obj = self.board.get_tile(start_node[0], start_node[1])
        if not start_tile_obj:
            print(f"    A* Constrained Fail: No tile at start node {start_node}.")
            return None

        # --- 2. A* Data Structure Initialization ---
        open_set = PriorityQueue()
        count = 0 # Tie-breaker for items with same priority in PriorityQueue
        # Initial g_score is 0, f_score = heuristic from start to end
        initial_f_score = self._heuristic(start_node, end_node)
        open_set.put((initial_f_score, count, start_node))
        # Keep track of nodes in open_set for O(1) lookup,
        # though Python's PriorityQueue doesn't directly support decrease-key.
        # We handle this by potentially having multiple entries for a node
        # and only processing the one with the lowest f_score when popped.
        open_set_hash = {start_node}

        # came_from: node -> (previous_node_coord, direction_of_step_from_previous_to_node)
        came_from: Dict[Tuple[int, int],
                        Optional[Tuple[Optional[Tuple[int, int]], Optional[Direction]]]] = \
            {start_node: (None, direction_of_arrival_at_start_node)}

        # g_score: cost from start_node to a given node
        g_score: Dict[Tuple[int, int], float] = {start_node: 0}

        # --- 3. A* Main Loop ---
        while not open_set.empty():
            current_f_score_val, _, current_node = open_set.get()

            # If already processed a better path to this node, skip
            if current_node not in open_set_hash:
                # print(f"    A* Skip: {current_node} already removed/processed with better path.") # Optional
                continue
            open_set_hash.remove(current_node) # Mark as effectively processed from open_set

            current_tile = self.board.get_tile(current_node[0], current_node[1])
            if not current_tile: # Should not happen if board is consistent
                # print(f"    A* Warn: No tile at {current_node} when dequeued. Skipping.") # Optional
                continue

            # Determine how current_node was reached (direction of the step)
            # This is 'None' only for the A* search's start_node if it had no prior arrival.
            _, direction_step_to_current = came_from.get(current_node, (None, None))

            # --- 3a. Goal Check ---
            if current_node == end_node:
                # If end_node is a stop, the entry constraint was checked when
                # end_node was added as a neighbor. So, if we dequeue it, it's valid.
                print(f"    A* Constrained Goal Reached (Dequeued): {end_node}!")
                path_list: List[Tuple[int, int]] = []
                curr_path_data_rec = (current_node, None)
                while curr_path_data_rec[0] is not None:
                    curr_n_rec = curr_path_data_rec[0]; path_list.append(curr_n_rec)
                    pred_data_rec = came_from.get(curr_n_rec)
                    curr_path_data_rec = pred_data_rec if pred_data_rec else (None, None)
                print(f"    A* Constrained Reconstructed Path: {path_list[::-1]}")
                return path_list[::-1]

            # --- 3b. Determine Entry Port and Valid Exits for current_node ---
            current_tile_connections_map = self.get_effective_connections(
                current_tile.tile_type, current_tile.orientation
            )
            entry_port_on_current_node: Optional[str] = None
            if current_node == start_node:
                # For the A* start_node, its "entry port" is opposite to how this search was initiated
                if direction_of_arrival_at_start_node:
                    entry_port_on_current_node = Direction.opposite(direction_of_arrival_at_start_node).name
            elif direction_step_to_current: # For subsequent nodes in A* path
                entry_port_on_current_node = Direction.opposite(direction_step_to_current).name
            
            valid_exits_from_this_entry: List[str] = []
            if entry_port_on_current_node:
                valid_exits_from_this_entry = current_tile_connections_map.get(entry_port_on_current_node, [])
            else: # No specific entry port (e.g., A* start_node with no prior arrival dir)
                valid_exits_from_this_entry = list(set(
                    ex_dir for exits in current_tile_connections_map.values() for ex_dir in exits
                ))
            valid_exit_set = set(valid_exits_from_this_entry)


            # --- 3c. Explore Neighbors ---
            for exit_dir_from_current in Direction: # Potential exit direction from current_node
                # Rule 1: U-Turn Check
                # Check based on how current_node was entered for THIS A* search
                u_turn_is_restricted = False
                if current_node == start_node and direction_of_arrival_at_start_node:
                    if exit_dir_from_current == Direction.opposite(direction_of_arrival_at_start_node):
                        u_turn_is_restricted = True
                elif direction_step_to_current: # For non-start nodes in this A* path
                    if exit_dir_from_current == Direction.opposite(direction_step_to_current):
                        u_turn_is_restricted = True
                if u_turn_is_restricted:
                    continue

                # Rule 2: Valid Exit from Current Tile (given its entry port for this path)
                if exit_dir_from_current.name not in valid_exit_set:
                    continue

                # Calculate neighbor
                dr, dc = exit_dir_from_current.value
                neighbor_node = (current_node[0] + dr, current_node[1] + dc)

                # Rule 3: Basic Neighbor Validity (on board, has tile)
                if not self.board.is_valid_coordinate(neighbor_node[0], neighbor_node[1]): continue
                neighbor_tile = self.board.get_tile(neighbor_node[0], neighbor_node[1])
                if not neighbor_tile: continue
                
                # Rule 4: Two-Way Track Check
                neighbor_conns_back = self.get_effective_connections(neighbor_tile.tile_type, neighbor_tile.orientation)
                req_entry_for_neighbor = Direction.opposite(exit_dir_from_current)
                if req_entry_for_neighbor.name not in {ex for exits in neighbor_conns_back.values() for ex in exits}:
                    continue

                # Rule 5: TARGET ENTRY CONSTRAINT CHECK
                # If this neighbor IS the end_node AND it's a stop,
                # the way we are entering it (exit_dir_from_current)
                # MUST be one of the allowed entry directions.
                if neighbor_node == end_node and target_is_stop:
                    if required_entry_directions_at_target is not None and \
                       exit_dir_from_current not in required_entry_directions_at_target:
                        # print(f"    A* Pruning: Invalid entry {exit_dir_from_current.name} for target stop {neighbor_node}") # Optional
                        continue # PRUNE THIS PATH: Invalid entry into target stop

                # If all checks passed, calculate scores and update
                tentative_g = g_score.get(current_node, float('inf')) + 1 # move_cost = 1
                if tentative_g < g_score.get(neighbor_node, float('inf')):
                    came_from[neighbor_node] = (current_node, exit_dir_from_current)
                    g_score[neighbor_node] = tentative_g
                    f_val = tentative_g + self._heuristic(neighbor_node, end_node)
                    # Add to open_set even if already there; lower f_score will be picked first.
                    # open_set_hash helps us skip processing it if a better path was already found and processed.
                    # A more complex PriorityQueue could handle decrease-key.
                    count += 1
                    open_set.put((f_val, count, neighbor_node))
                    open_set_hash.add(neighbor_node) # Mark as "to be processed"

        # If loop finishes and goal was not reached meeting all constraints
        print(f"--- A* Constrained FAILED: No path P{active_player_id} {start_node} -> {end_node} meeting all constraints. ---")
        return None


    def get_terminal_coords(self, line_number: int
            ) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
        """
        Retrieves the two primary terminal coordinates for a given line number.
        Always returns a tuple of two elements (coord or None).
        """
        coords_pair = TERMINAL_COORDS.get(line_number) # Use constant alias

        if coords_pair and isinstance(coords_pair, tuple) and len(coords_pair) == 2:
            term_a = coords_pair[0]
            term_b = coords_pair[1]
            # Basic validation of coordinate format
            valid_a = isinstance(term_a, tuple) and len(term_a) == 2
            valid_b = isinstance(term_b, tuple) and len(term_b) == 2

            if valid_a and valid_b:
                 return term_a, term_b
            else:
                 print(f"Warning: Invalid coord format in TERMINAL_COORDS "
                       f"for Line {line_number}: {coords_pair}")
                 return (term_a if valid_a else None), (term_b if valid_b else None)
        else:
            # Handles case where line_number not found OR data format wrong
            if coords_pair is not None: # Log if format was wrong
                 print(f"Warning: TERMINAL_COORDS data for Line {line_number} "
                       f"has unexpected format: {coords_pair}")
            # Ensure returning a tuple of two Nones
            return None, None

    def _is_valid_stop_entry(self, stop_coord: Tuple[int, int], entry_direction: Direction) -> bool:
        """Checks if entering the stop_coord from entry_direction is valid based on the parallel track rule."""
        placed_tile = self.board.get_tile(stop_coord[0], stop_coord[1])
        if not placed_tile or not placed_tile.has_stop_sign:
            return False # Cannot be valid if not a stop sign tile

        # --- CORRECT variable name here ---
        tile_connections = self.get_effective_connections(placed_tile.tile_type, placed_tile.orientation)

        # Find building ID and position
        building_id = None
        for bid, bcoord in self.board.building_stop_locations.items():
             if bcoord == stop_coord: building_id = bid; break
        if not building_id: return False # Should not happen
        building_actual_coord = self.board.building_coords[building_id]
        building_is_north_south = building_actual_coord[0] != stop_coord[0]
        building_is_east_west = building_actual_coord[1] != stop_coord[1]

        # Determine required straight axis based on building position
        validating_straight_exists = False
        required_straight_dirs = set()
        required_axis = "Unknown"

        # --- Use CORRECT variable name in checks below ---
        if building_is_north_south:
            required_axis = "E/W"
            # Check if tile has E-W straight using tile_connections
            if self._has_ew_straight(tile_connections): # <-- FIX HERE
                 validating_straight_exists = True
                 required_straight_dirs = {Direction.E, Direction.W}
        elif building_is_east_west:
            required_axis = "N/S"
            # Check if tile has N-S straight using tile_connections
            if self._has_ns_straight(tile_connections): # <-- FIX HERE
                 validating_straight_exists = True
                 required_straight_dirs = {Direction.N, Direction.S}

        # Actual validation check
        valid_entry = False
        if validating_straight_exists and entry_direction in required_straight_dirs:
             valid_entry = True

        # --- Debug Print (uses required_axis defined above) ---
        dr_from, dc_from = Direction.opposite(entry_direction).value
        from_coord = (stop_coord[0] + dr_from, stop_coord[1] + dc_from)
        # Ensure player ID access is safe if needed
        active_player_id = self.get_active_player().player_id if self.players else '?'
        print(f"DBG P{active_player_id}: Stop Entry Check AT {stop_coord} "
              f"FROM {from_coord} (Dir: {entry_direction.name}). "
              f"Requires parallel {required_axis} axis. "
              f"Result: {'VALID' if valid_entry else 'INVALID'}")

        return valid_entry


    def handle_route_completion(self, player: Player):
        if not player.start_terminal_coord: # Crucial check
             print(f"  ERROR: P{player.player_id} handle_route_completion called with NO chosen_start_terminal!")
             player.player_state = PlayerState.LAYING_TRACK # Revert state
             return

        player.player_state = PlayerState.DRIVING
        player.required_node_index = 0
        player.streetcar_position = player.start_terminal_coord
        player.arrival_direction = None

        print(f"  Player {player.player_id} start_terminal_coord SET TO: {player.start_terminal_coord}") # DEBUG
        print(f"  Player {player.player_id} streetcar placed at: {player.streetcar_position}")

        if self.game_phase == GamePhase.LAYING_TRACK:
             self.game_phase = GamePhase.DRIVING
             print(f"\n*** ROUTE COMPLETE for Player {player.player_id}! Entering Driving Phase. ***")

    # --- NEW Driving Methods (Step 6) ---
    def roll_special_die(self) -> Any:
        """Rolls the special Linie 1 die."""
        return random.choice(DIE_FACES)

    def _find_path_segment_for_driving(self, player: Player) -> Optional[List[Tuple[int, int]]]:
        """Helper to find the dynamic path segment from current pos to next node."""
        # --- Add Debug Prints ---
        print(f"--- DBG: _find_path_segment_for_driving for P{player.player_id} ---")
        print(f"Current Position: {player.streetcar_position} (Type: {type(player.streetcar_position)})")
        print(f"Current Arrival Dir: {player.arrival_direction}")
        print(f"Current Required Node Index: {player.required_node_index}")

        if player.streetcar_position is None:
             print("DBG: No current position, cannot find path segment.")
             return None

        target_node = player.get_next_target_node(self)
        print(f"Next Target Node: {target_node} (Type: {type(target_node)})")

        if not target_node:
             print("DBG: No next target node, cannot find path segment.")
             return None

        # --- Ensure start_node and end_node are tuples before calling find_path ---
        start_node_arg = player.streetcar_position
        end_node_arg = target_node

        if not isinstance(start_node_arg, tuple) or len(start_node_arg) != 2:
             print(f"*** ERROR: start_node_arg is NOT a valid coordinate tuple: {start_node_arg} ***")
             # Optionally raise an error here or return None
             return None
        if not isinstance(end_node_arg, tuple) or len(end_node_arg) != 2:
             print(f"*** ERROR: end_node_arg is NOT a valid coordinate tuple: {end_node_arg} ***")
             # Optionally raise an error here or return None
             return None

        print(f"Calling find_path_astar_constrained({start_node_arg=}, {end_node_arg=}, entry_dir={player.arrival_direction})")
        # --- End Add Debug Prints ---


        # Pass the player's arrival direction to find_path
        path_segment = self.find_path_astar_constrained(
            start_node=start_node_arg, # Use validated tuple
            end_node=end_node_arg,     # Use validated tuple
            direction_of_arrival_at_start_node=player.arrival_direction
            # Constraints like target_is_stop are handled inside check_segment_sequence now
            # find_path primarily needs start, end, and entry direction constraint
        )
        print(f"Resulting path_segment: {'Found' if path_segment else 'None'}") # DEBUG
        return path_segment

    def trace_track_steps(self, player: Player, num_steps: int) -> Optional[Tuple[int, int]]:
        """Calculates destination by finding path segment, then tracing steps."""
        path_segment = self._find_path_segment_for_driving(player)
        if not path_segment or len(path_segment) <= 1:
             print(f"Warning: Cannot find path segment from {player.streetcar_position} for trace.")
             return player.streetcar_position

        target_index_on_segment = min(num_steps, len(path_segment) - 1)
        # --- Determine arrival direction for the *next* move ---
        # If we moved (target_index > 0), calculate direction from prev step
        if target_index_on_segment > 0:
             prev_coord = path_segment[target_index_on_segment - 1]
             next_coord = path_segment[target_index_on_segment]
             player.arrival_direction = self._get_entry_direction(prev_coord, next_coord)
        # Else (staying put), keep old arrival direction? Or set to None? Let's keep old for now.

        return path_segment[target_index_on_segment]


    def find_next_feature_on_path(self, player: Player) -> Optional[Tuple[int, int]]:
        """Finds path segment, then finds first feature on THAT segment."""
        path_segment = self._find_path_segment_for_driving(player)
        if not path_segment or len(path_segment) <= 1:
             print(f"Warning: Cannot find path segment from {player.streetcar_position} for 'H' roll.")
             return player.streetcar_position

        target_node = path_segment[-1] # The required node we aimed for
        final_coord_found = target_node # Default to target node if no feature found earlier
        arrival_at_feature: Optional[Direction] = None

        # Iterate along the found path segment (starting from step 1)
        for i in range(1, len(path_segment)):
            coord = path_segment[i]
            feature_found = False

            if coord == target_node: feature_found = True # Reached the next required node

            tile = self.board.get_tile(coord[0], coord[1])
            if tile and tile.has_stop_sign: feature_found = True # Found any stop sign

            for term_coords_pair in TERMINAL_COORDS.values():
                 if coord in term_coords_pair: feature_found = True # Found any terminal

            if feature_found:
                 final_coord_found = coord
                 # Calculate arrival direction at this feature
                 if i > 0: # Should always be true here
                      prev_coord = path_segment[i-1]
                      arrival_at_feature = self._get_entry_direction(prev_coord, final_coord_found)
                 break # Stop at the first feature found

        # Update player's arrival direction for the next turn
        player.arrival_direction = arrival_at_feature
        return final_coord_found


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
        """Moves streetcar and increments target index if next required node coord is reached."""
        if player.streetcar_position is None: return # Safety check

        previous_pos = player.streetcar_position
        player.streetcar_position = target_coord # Update position FIRST
        print(f"Player {player.player_id} moved from {previous_pos} to {target_coord}")

        # --- DETAILED DEBUGGING FOR INDEX INCREMENT ---
        print(f"--- DBG move_streetcar P{player.player_id} Post-Move Checks ---")
        print(f"  Landed at: {target_coord}")
        print(f"  Index BEFORE check: {player.required_node_index}")

        # Get the node the player *was* aiming for
        current_target_stop_index = player.required_node_index
        sequence_nodes = player.get_required_nodes_sequence(self, is_driving_check=True)

        if not sequence_nodes:
             print(f"  DBG move_streetcar P{player.player_id}: ERROR - Cannot get sequence nodes!")
             return

        target_node_list_index = current_target_stop_index + 1

        if target_node_list_index < len(sequence_nodes):
             the_node_player_was_aiming_for = sequence_nodes[target_node_list_index]
             print(f"  Was Aiming For: Node #{target_node_list_index} at {the_node_player_was_aiming_for}")

             # Did the player LAND on the coordinate they were aiming for?
             if target_coord == the_node_player_was_aiming_for:
                 print(f"  MATCH: Landed on the target node coordinate.")

                 # --- CORRECTED LOGIC: Increment IF target node reached ---
                 # Whether it's a stop or the final terminal, reaching the
                 # target node means we advance the index for the *next* target.
                 print(f"  INCREMENTING index from {player.required_node_index} to {player.required_node_index + 1}")
                 player.required_node_index += 1

                 # Optional: Add a specific message if it was a stop vs terminal
                 num_required_stops = len(player.route_card.stops) if player.route_card else 0
                 if current_target_stop_index < num_required_stops:
                      required_stop_id = player.route_card.stops[current_target_stop_index]
                      print(f"  (Landed on required stop '{required_stop_id}')")
                 else:
                      print(f"  (Landed on FINAL TERMINAL)")
                 # --- End Corrected Logic ---

             else: # Landed somewhere else
                 print(f"  NO MATCH: Landed coord {target_coord} != target node coord {the_node_player_was_aiming_for}. No index change.")
        else: # Index already past end of sequence
             print(f"  Index {player.required_node_index} already pointing past final node "
                   f"(Sequence length {len(sequence_nodes)}). No index change.")

        print(f"  Index AFTER check: {player.required_node_index}")
        print(f"--- End DBG move_streetcar P{player.player_id} ---")

    def check_win_condition(self, player: Player) -> bool:
        """
        Checks if player is at EITHER destination terminal tile AND
        their target index indicates all required stops have been passed.
        (Assumes driving phase uses unconstrained pathfinding).
        """
        # --- Basic validity checks ---
        if player.player_state != PlayerState.DRIVING:
            return False
        if player.streetcar_position is None:
            print("Win Check Warn: No streetcar position.")
            return False
        if not player.line_card:
             print(f"Win Check Error P{player.player_id}: Missing line card.")
             return False # Should have line card if driving

        # --- Get Both Potential Destination Terminal Coordinates ---
        line_num = player.line_card.line_number
        term1_coord, term2_coord = self.get_terminal_coords(line_num)
        if not term1_coord or not term2_coord:
             print(f"Win Check Error P{player.player_id}: Cannot find term coords L{line_num}")
             return False

        current_pos = player.streetcar_position
        is_at_term1 = (current_pos == term1_coord)
        is_at_term2 = (current_pos == term2_coord)

        # --- Check 1: Is player physically at a terminal for their line? ---
        if is_at_term1 or is_at_term2:
            print(f"DBG Win Check P{player.player_id}: At a terminal ({current_pos}).") # Debug

            # --- Check 2: Has the player logically passed all required stops? ---
            num_required_stops = 0
            if player.route_card and player.route_card.stops:
                 num_required_stops = len(player.route_card.stops)

            # The player's index tracks the *next* node they are aiming for.
            # Index 0 = aiming for Stop 1 (Node index 1 in sequence)
            # ...
            # Index N = aiming for End Terminal (Node index N+1 in sequence)
            # where N = num_required_stops.
            # So, if the index is >= N+1, they have passed all stops.
            index_indicating_all_stops_passed = num_required_stops + 1

            print(f"DBG Win Check P{player.player_id}: Current Node Idx = {player.required_node_index}, "
                  f"Idx Needed >= {index_indicating_all_stops_passed} (Based on {num_required_stops} stops)") # Debug

            # --- Corrected Condition ---
            if player.required_node_index >= index_indicating_all_stops_passed:
                 # They are at a terminal AND their index shows they finished the sequence.
                 print(f"Win Check P{player.player_id}: Node index sufficient. WIN!") # Debug
                 self.game_phase = GamePhase.GAME_OVER
                 self.winner = player
                 player.player_state = PlayerState.FINISHED
                 return True
            else:
                 # Physically at a terminal, but sequence not complete according to index.
                 print(f"Win Check P{player.player_id}: At Terminal but node index too low. No win.") # Debug
                 return False
        else:
            # Not physically at either terminal coordinate.
            return False

    # === Turn Management & Undo/Redo ===

    def undo_last_action(self) -> bool:
        # --- Check if the action being undone belongs to the current turn ---
        # This requires commands to store player ID or turn number, or
        # for the history manager to track turn boundaries.
        # --- SIMPLER APPROACH: Only allow undo if actions > 0 THIS turn ---
        if self.actions_taken_this_turn <= 0:
             print("Undo Error: No actions taken yet this turn.")
             return False

        active_player = self.get_active_player()
        last_cmd_desc = self.command_history.get_last_action_description()

        if self.command_history.undo():
             # Decrement action count as it was undone THIS turn
             if last_cmd_desc in ["PlaceTileCommand", "ExchangeTileCommand", "MoveCommand"]:
                 self.actions_taken_this_turn -= 1
             # Driving move undo resets turn to allow re-roll
             if active_player.player_state == PlayerState.DRIVING:
                  self.actions_taken_this_turn = 0
             return True
        return False

    def redo_last_action(self) -> bool:
        active_player = self.get_active_player()
        # --- Check if the action being redone fits action limits ---
        if active_player.player_state == PlayerState.LAYING_TRACK:
             if self.actions_taken_this_turn >= MAX_PLAYER_ACTIONS:
                  print("Redo Error: Max actions already reached.")
                  return False

        cmd_to_redo = self.command_history.get_command_to_redo()
        if not cmd_to_redo: return False

        # --- SIMPLER APPROACH: Only allow redo within the current turn's actions ---
        # Check if redo points beyond the actions taken this turn conceptually
        # This requires more complex history tracking.
        # --- Let's allow redo for now, but it might cross turn boundaries ---
        # A better system would prevent redoing actions from previous turns.

        if self.command_history.redo():
             # Increment action count as it was redone THIS turn
             if isinstance(cmd_to_redo, (PlaceTileCommand, ExchangeTileCommand)):
                 self.actions_taken_this_turn += 1
             elif isinstance(cmd_to_redo, MoveCommand):
                 self.actions_taken_this_turn = MAX_PLAYER_ACTIONS # Driving turn done
             return True
        return False

    def confirm_turn(self) -> bool:
        """ Finalizes the current player's turn and advances state. """
        active_player = self.get_active_player()

        if self.game_phase == GamePhase.GAME_OVER: return False

        # Validation (Laying Track requires MAX actions)
        if active_player.player_state == PlayerState.LAYING_TRACK:
            if self.actions_taken_this_turn < MAX_PLAYER_ACTIONS:
                 print(f"Confirm Error: Need {MAX_PLAYER_ACTIONS} actions.")
                 return False
        # Driving automatically meets action requirement conceptually
        elif active_player.player_state == PlayerState.DRIVING:
             # Check if move was actually completed via action count
             if self.actions_taken_this_turn < MAX_PLAYER_ACTIONS:
                  print("Confirm Error: Driving move not yet completed.")
                  return False # Should not be called before move finishes

        print(f"Player {active_player.player_id} confirmed turn.")

        # --- End Turn Sequence ---
        # 1. Draw tiles if applicable
        if active_player.player_state == PlayerState.LAYING_TRACK:
             draw_count = 0
             # Draw up to the limit, considering tiles used this turn
             needed = HAND_TILE_LIMIT - len(active_player.hand)
             can_draw = min(needed, MAX_PLAYER_ACTIONS) # Can draw max 2
             for _ in range(can_draw):
                 if self.draw_tile(active_player): draw_count += 1
                 else: break # Stop if pile empty
             if draw_count > 0:
                  print(f"Player {active_player.player_id} drew {draw_count}.")

        # 2. Advance Player Index & Turn Counter
        self.active_player_index = (self.active_player_index + 1) % self.num_players
        if self.active_player_index == 0:
            self.current_turn += 1

        # 3. Reset state for the NEW player's turn
        self.actions_taken_this_turn = 0
        self.command_history.clear_redo_history()

        next_player = self.get_active_player()
        print(f"\n--- Starting Turn {self.current_turn} for "
              f"Player {self.active_player_index} ({next_player.player_state.name}) ---")

        # 4. Check route completion for the new player
        if next_player.player_state == PlayerState.LAYING_TRACK:
             if self.check_player_route_completion(next_player):
                  self.handle_route_completion(next_player)

        return True
    

    ###########################################################
    ###########################################################
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

            loaded_game.command_history = CommandHistory()

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
