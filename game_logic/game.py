# game_logic/game.py
import random
import json
import traceback
import copy
from collections import deque
from typing import List, Dict, Tuple, Optional, Set, Any

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
        if not 2 <= num_players <= 6:
            raise ValueError("Players must be 2-6.")
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
        # turn_confirmed might not be needed if confirm logic is in UI state
        # self.turn_confirmed: bool = False

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
        self.line_cards_pile = [LineCard(i) for i in range(1, 7)]
        random.shuffle(self.line_cards_pile)

    def _deal_starting_hands(self):
        """Deals the initial 3 straights and 2 curves to each player."""
        print("Dealing starting hands...")
        straight_type = self.tile_types.get('Straight')
        curve_type = self.tile_types.get('Curve')
        if not straight_type or not curve_type:
            raise RuntimeError("Straight/Curve TileType missing.")

        # Check if enough tiles exist before dealing
        # ... (Add checks similar to original code if needed) ...

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

        player_range = "2-4" if self.num_players <= 4 else "5-6"

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

    # Modify find_path to accept the direction the search ARRIVED from at the start node
    def find_path(self, start_row: int, start_col: int, end_row: int, end_col: int,
                  entry_direction_at_start: Optional[Direction] = None) -> Optional[List[Tuple[int, int]]]:
        """
        Finds a path using BFS, preventing immediate backtracking from the start node.
        Returns the list of coordinates, or None.
        entry_direction_at_start: The direction used to ENTER (start_row, start_col).
                                   Neighbors in the opposite direction won't be explored initially.
        """
        start_coord = (start_row, start_col)
        end_coord = (end_row, end_col)
        # coords_to_avoid = avoid_coords if avoid_coords is not None else set() <-- redundant as BFS logic already handles visited nodes using the predecessor dictionary

        # --- Basic Input Validation ---
        if not self.board.is_valid_coordinate(start_row, start_col) or \
           not self.board.is_valid_coordinate(end_row, end_col): return None
        if (start_row, start_col) == (end_row, end_col): return [(start_row, start_col)]
        start_tile = self.board.get_tile(start_row, start_col)
        if not start_tile: return None

        # Store path predecessors AND the direction taken to reach the node
        # Value: (predecessor_coord, direction_from_predecessor)
        predecessor: Dict[Tuple[int, int], Optional[Tuple[Optional[Tuple[int, int]], Optional[Direction]]]] = \
            {(start_row, start_col): (None, entry_direction_at_start)} # Store initial entry if provided

        queue = deque([(start_row, start_col)]) # No need to store direction in queue itself

        path_found = False
        while queue:
            curr_row, curr_col = queue.popleft()
            current_coord = (curr_row, curr_col)

            if current_coord == (end_row, end_col):
                path_found = True
                break

            current_tile = self.board.get_tile(curr_row, curr_col)
            if not current_tile: continue

            current_connections = self.get_effective_connections(current_tile.tile_type, current_tile.orientation)
            current_exit_dirs_str = {exit_dir for exits in current_connections.values() for exit_dir in exits}

            # Get the direction used to arrive at THIS node (from predecessor dict)
            _, arrived_from_direction = predecessor[current_coord] # Direction entering current_coord

            directions_to_check = list(Direction)
            random.shuffle(directions_to_check) # Keep shuffle for variety

            for exit_direction in directions_to_check: # Direction to EXIT current_coord
                # --- "NO BACKWARDS" RULE CHECK ---
                # If we arrived from a certain direction, don't immediately exit back that way
                if arrived_from_direction is not None and exit_direction == Direction.opposite(arrived_from_direction):
                    # print(f"BFS Skip: Trying to exit {exit_direction.name} from {current_coord}, but arrived via {arrived_from_direction.name}") # Debug
                    continue # Skip exploring this direction

                # Check if the current tile actually supports exiting this way
                exit_dir_str = exit_direction.name
                if exit_dir_str not in current_exit_dirs_str:
                    continue # Current tile doesn't connect out this way

                # --- Check Neighbor ---
                dr, dc = exit_direction.value
                nr, nc = curr_row + dr, col + dc
                neighbor_coord = (nr, nc)

                if not self.board.is_valid_coordinate(nr, nc): continue
                if neighbor_coord in predecessor: continue # Already visited/queued

                neighbor_tile = self.board.get_tile(nr, nc)
                if not neighbor_tile: continue

                # Check if neighbor connects back (two-way check still needed)
                neighbor_connects_back = Direction.opposite(exit_direction).name in {
                    ex_dir for n_exits in self.get_effective_connections(neighbor_tile.tile_type, neighbor_tile.orientation).values() for ex_dir in n_exits
                }

                if neighbor_connects_back: # Valid forward connection
                    # Record predecessor and the direction taken to get there
                    predecessor[neighbor_coord] = (current_coord, exit_direction)
                    queue.append(neighbor_coord)

        # --- Reconstruct path (no change needed here) ---
        if path_found:
            path: List[Tuple[int, int]] = []; curr_data = ((end_row, end_col), None) # Store coord and entry dir for reconstruction if needed
            while curr_data[0] is not None:
                 coord = curr_data[0]
                 path.append(coord)
                 pred_data = predecessor.get(coord)
                 curr_data = pred_data if pred_data else (None, None) # Move to predecessor
            return path[::-1]
        else:
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

    def check_player_route_completion(self, player: Player) -> bool: # No longer returns path
        """Checks if a valid path visiting stops in order currently exists."""
        try:
            sequence_nodes = player.get_required_nodes_sequence(self)
            if not sequence_nodes: return False # Missing cards or stops

            # --- Function to check connectivity between adjacent nodes in sequence ---
            def check_segment(start_node, end_node) -> bool:
                segment_path = self.find_path(start_node[0], start_node[1], end_node[0], end_node[1])
                if not segment_path: return False # No path for this segment

                # --- Validate Stop Entry IF end_node is a required stop ---
                # Need to know which coords are stops vs terminals
                stop_coords = set(c for s_id, c in self.board.building_stop_locations.items() if s_id in player.route_card.stops)
                is_required_stop = end_node in stop_coords
                if is_required_stop:
                    if len(segment_path) < 2: return False # Cannot determine entry
                    previous_coord = segment_path[-2]
                    entry_direction = self._get_entry_direction(previous_coord, end_node)
                    if not entry_direction or not self._is_valid_stop_entry(end_node, entry_direction):
                         return False # Stop entry validation failed

                return True # Segment is valid

            # Check connectivity for all segments in the sequence
            for i in range(len(sequence_nodes) - 1):
                if not check_segment(sequence_nodes[i], sequence_nodes[i+1]):
                    # print(f"Debug P{player.player_id}: Route check fail segment {i}") # Optional debug
                    return False # Found an invalid segment

            print(f"Route Check P{player.player_id}: COMPLETE sequence possible.")
            return True # All segments are validly connectable right now

        except Exception as e:
             print(f"\n!!! EXCEPTION during check_player_route_completion for P{player.player_id} !!!\nError: {e}")
             traceback.print_exc(); return False

    def handle_route_completion(self, player: Player): # No longer takes path arg
        print(f"\n*** ROUTE COMPLETE for Player {player.player_id}! Entering Driving Phase. ***")

        # --- Determine Optimal Start Terminal ---
        start_pos = None
        term1_coord, term2_coord = self.get_terminal_coords(player.line_card.line_number)
        sequence_nodes = player.get_required_nodes_sequence(self) # Temporarily call to get stops

        if not sequence_nodes or len(sequence_nodes) < 2:
            print(f"Error P{player.player_id}: Cannot determine sequence for start calc.")
            first_stop_coord = None # Cannot determine first stop
        else:
            first_stop_coord = sequence_nodes[1] # First stop is always index 1

        path1_len = float('inf')
        path2_len = float('inf')

        if term1_coord and first_stop_coord:
             path1 = self.find_path(term1_coord[0], term1_coord[1], first_stop_coord[0], first_stop_coord[1])
             if path1: path1_len = len(path1)

        if term2_coord and first_stop_coord:
             path2 = self.find_path(term2_coord[0], term2_coord[1], first_stop_coord[0], first_stop_coord[1])
             if path2: path2_len = len(path2)

        # Choose the shorter path, default to term1 if equal or errors
        if path1_len <= path2_len and term1_coord:
             start_pos = term1_coord
             print(f"Debug P{player.player_id}: Starting at Term1 ({term1_coord}), Path Len: {path1_len if path1_len != float('inf') else 'N/A'}")
        elif term2_coord:
             start_pos = term2_coord
             print(f"Debug P{player.player_id}: Starting at Term2 ({term2_coord}), Path Len: {path2_len if path2_len != float('inf') else 'N/A'}")
        else:
             print(f"Error P{player.player_id}: Cannot determine valid start terminal.")
             # Handle error: Revert state? Use default?
             player.player_state = PlayerState.LAYING_TRACK
             return

        # --- Set Player State ---
        player.player_state = PlayerState.DRIVING
        player.required_node_index = 0 # Start aiming for the first stop
        player.arrival_direction = None # Reset arrival direction at start
        player.streetcar_position = start_pos
        player.start_terminal_coord = start_pos # Store the chosen start

        print(f"Player {player.player_id} streetcar placed at {player.streetcar_position}.")

        if self.game_phase == GamePhase.LAYING_TRACK:
             self.game_phase = GamePhase.DRIVING
             print(f"Game Phase changing to DRIVING.")

    # --- NEW Driving Methods (Step 6) ---
    def roll_special_die(self) -> Any:
        """Rolls the special Linie 1 die."""
        return random.choice(DIE_FACES)

    def _find_path_segment_for_driving(self, player: Player) -> Optional[List[Tuple[int, int]]]:
        """Helper to find the dynamic path segment from current pos to next node."""
        if player.streetcar_position is None: return None
        target_node = player.get_next_target_node(self)
        if not target_node: return None

        # Pass the player's arrival direction to find_path
        path_segment = self.find_path(
            player.streetcar_position[0], player.streetcar_position[1],
            target_node[0], target_node[1],
            player.arrival_direction # Pass how we got here
        )
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

            for term_coords_pair in C.TERMINAL_COORDS.values():
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


    # --- Update move_streetcar to ONLY update position ---
    def move_streetcar(self, player: Player, target_coord: Tuple[int, int]):
        """ONLY updates the player's streetcar position attribute."""
        # Basic check
        if not isinstance(target_coord, tuple) or len(target_coord) != 2:
             print(f"Error: Invalid target_coord {target_coord} for move_streetcar.")
             return

        # Update position - visualizer reads this for drawing
        player.streetcar_position = target_coord
        # Log moved here, NOT in the command execute, to track visual state change
        # print(f"Player {player.player_id} position updated to {target_coord}")

    def check_win_condition(self, player: Player) -> bool:
        """Checks if player is at EITHER destination terminal tile AND all nodes visited."""
        if player.player_state != PlayerState.DRIVING or player.streetcar_position is None:
             return False

        # --- Get the player's specific line and required stops ---
        if not player.line_card: return False # Should have line card if driving
        line_num = player.line_card.line_number
        num_required_stops = 0
        if player.route_card and player.route_card.stops:
             num_required_stops = len(player.route_card.stops)

        # --- Get BOTH potential destination terminal coordinates ---
        term1_coord, term2_coord = self.get_terminal_coords(line_num)
        if not term1_coord or not term2_coord:
             print(f"Win Check Error P{player.player_id}: Cannot find terminal coords for Line {line_num}")
             return False

        # --- Determine which terminal was the nominal START based on the path ---
        # (This assumes handle_route_completion sets the initial position correctly)
        # We need to know which of the two terminals is the actual target destination.
        # Let's refine the assumption: If the required_node_index indicates they are
        # aiming for the final destination (i.e., index > num_stops), then the
        # destination is the terminal they *didn't* start at.

        # Get the sequence to know the nominal start/end based on initial placement
        # We might need a more robust way to store the start terminal if loading saves.
        # Quick Fix Assumption: If current pos isn't term1, assume term1 was start, term2 is dest. Vice-versa.
        # This is flawed if they are mid-route.
        # Better: Store the nominal start terminal when player starts driving.

        # --- Let's simplify: Check if current position IS one of the line's terminals ---
        current_pos = player.streetcar_position
        is_at_term1 = (current_pos == term1_coord)
        is_at_term2 = (current_pos == term2_coord)

        # --- Check if player is AT EITHER destination terminal ---
        if is_at_term1 or is_at_term2:
            # Determine which terminal they *should* be aiming for as the true destination.
            # If player.required_node_index implies they are past the stops, they *must* be at the destination.
            # The sequence has N stops, plus start term, plus end term = N+2 nodes.
            # Target index goes from 0 (start) to N+1 (end). Index > N means aiming for end.
            is_aiming_for_final_node = player.required_node_index > num_required_stops

            if is_aiming_for_final_node:
                 # No need to check which terminal was start/end if index is correct.
                 # Reaching *any* terminal when aiming for the end means they finished.
                 print(f"Win Check P{player.player_id}: At a Terminal ({current_pos}) & Nodes Visited ({player.required_node_index}/{num_required_stops+1} nodes). WIN!")
                 self.game_phase = GamePhase.GAME_OVER
                 self.winner = player
                 player.player_state = PlayerState.FINISHED
                 return True
            else:
                 # They landed on a terminal tile, but haven't logically passed all stops yet.
                 print(f"Win Check P{player.player_id}: Landed on Terminal ({current_pos}) but node index too low ({player.required_node_index}/{num_required_stops+1} nodes). No win.")
                 return False
        else:
            # Not at either of the destination terminal coordinates
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
