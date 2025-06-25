# game_logic/game.py
import random
import json
import traceback
import copy
from collections import deque, namedtuple
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
from constants import (
    TILE_DEFINITIONS, TILE_COUNTS_BASE, TILE_COUNTS_5_PLUS_ADD,
    STARTING_HAND_TILES, ROUTE_CARD_VARIANTS, TERMINAL_COORDS,
    HAND_TILE_LIMIT, MAX_PLAYER_ACTIONS, DIE_FACES, STOP_SYMBOL,
    TERMINAL_DATA
)

# A readable and hashable state for our A* search algorithms
PathState = namedtuple('PathState', ['pos', 'arrival_dir', 'seq_idx'])


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
        self.line_cards_pile: List[LineCard] = []
        self.active_player_index: int = 0
        self.game_phase: GamePhase = GamePhase.SETUP
        self.current_turn: int = 0
        self.winner: Optional[Player] = None
        self.actions_taken_this_turn: int = 0
        self.command_history = CommandHistory()

    def get_active_player(self) -> Player:
        if 0 <= self.active_player_index < len(self.players):
             return self.players[self.active_player_index]
        else:
             raise IndexError("Active player index out of bounds.")

    def setup_game(self):
        if self.game_phase != GamePhase.SETUP:
            print("Warning: setup_game called when not in SETUP phase.")
            return
        print("--- Starting Game Setup ---")
        self._create_tile_and_line_piles()
        self._deal_starting_hands()
        self._deal_player_cards()
        self.game_phase = GamePhase.LAYING_TRACK
        self.active_player_index = 0
        self.current_turn = 1
        self.actions_taken_this_turn = 0
        self.command_history.clear()
        print("--- Setup Complete ---")

    def _create_tile_and_line_piles(self):
        print("Creating draw piles...")
        tile_counts = TILE_COUNTS_BASE.copy()
        if self.num_players >= 5:
            for name, count in TILE_COUNTS_5_PLUS_ADD.items():
                tile_counts[name] = tile_counts.get(name, 0) + count
        self.tile_draw_pile = []
        for name, count in tile_counts.items():
            tile_type = self.tile_types.get(name)
            if tile_type: self.tile_draw_pile.extend([tile_type] * count)
        random.shuffle(self.tile_draw_pile)
        print(f"Tile draw pile created: {len(self.tile_draw_pile)} tiles.")
        self.line_cards_pile = [LineCard(i) for i in TERMINAL_COORDS.keys()]
        random.shuffle(self.line_cards_pile)

    def _deal_starting_hands(self):
        print("Dealing starting hands...")
        straight_type = self.tile_types.get('Straight')
        curve_type = self.tile_types.get('Curve')
        if not straight_type or not curve_type:
            raise RuntimeError("Straight/Curve TileType missing.")
        for player in self.players:
            player.hand = []
            s_needed = STARTING_HAND_TILES['Straight']
            c_needed = STARTING_HAND_TILES['Curve']
            for _ in range(s_needed): player.hand.append(straight_type)
            for _ in range(c_needed): player.hand.append(curve_type)
            # This is a simplification; a full implementation would remove from the pile.

    def _deal_player_cards(self):
        print("Dealing player cards...")
        if len(self.line_cards_pile) < self.num_players:
            raise RuntimeError("Not enough Line cards!")
        available_variants = list(range(len(ROUTE_CARD_VARIANTS)))
        random.shuffle(available_variants)
        player_range = "1-4" if self.num_players <= 4 else "5-6"
        for player in self.players:
            player.line_card = self.line_cards_pile.pop()
            variant_index = available_variants.pop(0) if available_variants else 0
            try:
                line_num = player.line_card.line_number
                stops = ROUTE_CARD_VARIANTS[variant_index][player_range][line_num]
            except (KeyError, IndexError) as e:
                raise RuntimeError(f"Error lookup route: Var={variant_index}, Rng={player_range}, Line={line_num}. Err: {e}")
            player.route_card = RouteCard(stops, variant_index)
        self.line_cards_pile = []

    def _rotate_direction(self, direction: str, angle: int) -> str:
        directions = ['N', 'E', 'S', 'W']
        current_index = directions.index(direction)
        steps = (angle % 360) // 90
        return directions[(current_index + steps) % 4]

    def get_effective_connections(self, tile_type: TileType, orientation: int) -> Dict[str, List[str]]:
        if orientation == 0:
            return copy.deepcopy(tile_type.connections_base)
        rotated_connections: Dict[str, List[str]] = {'N': [], 'E': [], 'S': [], 'W': []}
        for base_entry, base_exits in tile_type.connections_base.items():
            actual_entry = self._rotate_direction(base_entry, orientation)
            rotated_connections[actual_entry] = [self._rotate_direction(ex, orientation) for ex in base_exits]
            rotated_connections[actual_entry].sort()
        return rotated_connections

    def _has_ns_straight(self, effective_connections: Dict[str, List[str]]) -> bool:
        return 'S' in effective_connections.get('N', [])
    def _has_ew_straight(self, effective_connections: Dict[str, List[str]]) -> bool:
        return 'W' in effective_connections.get('E', [])

    def check_placement_validity(self, tile_type: TileType, orientation: int, row: int, col: int) -> Tuple[bool, str]:
        if not self.board.is_playable_coordinate(row, col): return False, f"Cannot place on border."
        if self.board.get_building_at(row, col): return False, f"Cannot place on a building."
        if self.board.get_tile(row, col): return False, f"Space occupied."
        new_conns = self.get_effective_connections(tile_type, orientation)
        for direction in Direction:
            dir_str = direction.name
            opp_dir_str = Direction.opposite(direction).name
            dr, dc = direction.value
            nr, nc = row + dr, col + dc
            new_connects_out = dir_str in {ex for exits in new_conns.values() for ex in exits}
            if not self.board.is_valid_coordinate(nr, nc):
                if new_connects_out: return False, f"Points {dir_str} off grid."
                continue
            n_tile = self.board.get_tile(nr, nc)
            if n_tile:
                n_conns = self.get_effective_connections(n_tile.tile_type, n_tile.orientation)
                n_connects_back = opp_dir_str in {ex for exits in n_conns.values() for ex in exits}
                if new_connects_out != n_connects_back: return False, f"Mismatch with neighbor {dir_str}."
            elif self.board.get_building_at(nr, nc):
                if new_connects_out: return False, f"Points {dir_str} into a building."
        return True, "Placement appears valid."

    def _check_and_place_stop_sign(self, placed_tile: PlacedTile, row: int, col: int):
        if self.board.get_tile(row, col) != placed_tile: return
        tile_connections = self.get_effective_connections(placed_tile.tile_type, placed_tile.orientation)
        for direction in Direction:
            dr, dc = direction.value; nr, nc = row + dr, col + dc
            if not self.board.is_valid_coordinate(nr, nc): continue
            building_id = self.board.get_building_at(nr, nc)
            if building_id and building_id not in self.board.buildings_with_stops:
                is_parallel = False
                if direction in [Direction.N, Direction.S] and self._has_ew_straight(tile_connections): is_parallel = True
                if direction in [Direction.E, Direction.W] and self._has_ns_straight(tile_connections): is_parallel = True
                if is_parallel:
                    placed_tile.has_stop_sign = True
                    self.board.buildings_with_stops.add(building_id)
                    self.board.building_stop_locations[building_id] = (row, col)
                    print(f"--> Placed stop sign at ({row},{col}) for Building {building_id}.")
                    break

    def check_exchange_validity(self, player: Player, new_tile_type: TileType, new_orientation: int, row: int, col: int) -> Tuple[bool, str]:
        old_tile = self.board.get_tile(row, col)
        if not old_tile: return False, "No tile to exchange."
        if not old_tile.tile_type.is_swappable: return False, "Tile not swappable."
        if old_tile.has_stop_sign: return False, "Cannot exchange stop sign tile."
        return True, "Exchange basic checks passed."

    def draw_tile(self, player: Player) -> bool:
        if not self.tile_draw_pile: return False
        if len(player.hand) >= HAND_TILE_LIMIT: return False
        player.hand.append(self.tile_draw_pile.pop())
        return True

    def attempt_place_tile(self, player: Player, tile_type: TileType, orientation: int, row: int, col: int) -> bool:
        if self.actions_taken_this_turn >= MAX_PLAYER_ACTIONS: return False
        command = PlaceTileCommand(self, player, tile_type, orientation, row, col)
        if self.command_history.execute_command(command):
            self.actions_taken_this_turn += 1
            return True
        return False

    def attempt_exchange_tile(self, player: Player, new_tile_type: TileType, new_orientation: int, row: int, col: int) -> bool:
        if self.actions_taken_this_turn >= MAX_PLAYER_ACTIONS: return False
        command = ExchangeTileCommand(self, player, new_tile_type, new_orientation, row, col)
        if self.command_history.execute_command(command):
            self.actions_taken_this_turn += 1
            return True
        return False

    def get_terminal_coords(self, line_number: int) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
        coords = TERMINAL_COORDS.get(line_number)
        return (coords[0], coords[1]) if coords else (None, None)

    def _is_valid_stop_entry(self, stop_coord: Tuple[int, int], entry_direction: Direction) -> bool:
        placed_tile = self.board.get_tile(stop_coord[0], stop_coord[1])
        if not placed_tile or not placed_tile.has_stop_sign: return False
        tile_conns = self.get_effective_connections(placed_tile.tile_type, placed_tile.orientation)
        building_id = next((bid for bid, bcoord in self.board.building_stop_locations.items() if bcoord == stop_coord), None)
        if not building_id: return False
        building_pos = self.board.building_coords.get(building_id)
        if not building_pos: return False

        is_building_ns = building_pos[1] == stop_coord[1]
        if is_building_ns: # Building N/S of tile, requires E/W track
            return self._has_ew_straight(tile_conns) and entry_direction in [Direction.E, Direction.W]
        else: # Building E/W of tile, requires N/S track
            return self._has_ns_straight(tile_conns) and entry_direction in [Direction.N, Direction.S]

    # =========================================================================
    # === NEW: UNIFIED PATHFINDING AND ROUTE VALIDATION (MULTI-GOAL A*) ===
    # =========================================================================

    def _heuristic_sequential(self, current_pos: Tuple[int, int], seq_idx: int, full_sequence: List[Tuple[int, int]]) -> int:
        """Admissible heuristic for multi-goal A*."""
        cost = 0
        # Cost from current position to the next goal in the sequence
        if seq_idx < len(full_sequence):
            cost += abs(current_pos[0] - full_sequence[seq_idx][0]) + abs(current_pos[1] - full_sequence[seq_idx][1])
        # Add costs between all subsequent goals
        for i in range(seq_idx, len(full_sequence) - 1):
            pos1 = full_sequence[i]
            pos2 = full_sequence[i+1]
            cost += abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
        return cost

    def _find_sequential_goal_path(self, player: Player, full_node_sequence: List[Tuple[int, int]]) -> Tuple[Optional[List[Tuple[int, int]]], int]:
        """
        Performs a multi-goal A* search to find the shortest valid path that visits all nodes
        in the full_node_sequence in order, respecting all game rules.
        """
        print(f"--- SEQ A* P{player.player_id}: Validating sequence {full_node_sequence} ---")
        start_pos = full_node_sequence[0]
        # State: (position, arrival_direction, sequence_index)
        start_state = PathState(pos=start_pos, arrival_dir=None, seq_idx=1) # Start by aiming for index 1

        if not self.board.get_tile(start_pos[0], start_pos[1]):
            print("   -> FAIL: Start terminal has no tile.")
            return None, float('inf')

        open_set = PriorityQueue()
        tie_breaker = 0
        f_score = self._heuristic_sequential(start_pos, 1, full_node_sequence)
        open_set.put((f_score, tie_breaker, start_state))

        g_scores = {start_state: 0}
        came_from = {start_state: None}
        stop_locations = set(self.board.building_stop_locations.values())

        while not open_set.empty():
            _, _, current_state = open_set.get()

            # --- Goal Check ---
            if current_state.seq_idx == len(full_node_sequence):
                print(f"   -> SUCCESS: Reached final node {current_state.pos} having visited all prior nodes.")
                path = []
                curr = current_state
                while curr is not None:
                    path.append(curr.pos)
                    curr = came_from.get(curr)
                return path[::-1], g_scores[current_state]

            # --- Successor Generation ---
            current_g = g_scores[current_state]
            current_tile = self.board.get_tile(current_state.pos[0], current_state.pos[1])
            if not current_tile: continue

            current_conns = self.get_effective_connections(current_tile.tile_type, current_tile.orientation)
            entry_port = Direction.opposite(current_state.arrival_dir).name if current_state.arrival_dir else None
            
            # Determine valid exit directions from this entry port
            if entry_port:
                valid_exit_strs = current_conns.get(entry_port, [])
            else: # No entry constraint at start, all exits are potentially valid
                valid_exit_strs = list(set(ex for exits in current_conns.values() for ex in exits))

            for exit_dir_str in valid_exit_strs:
                exit_dir = Direction.from_str(exit_dir_str)
                dr, dc = exit_dir.value
                neighbor_pos = (current_state.pos[0] + dr, current_state.pos[1] + dc)

                if not self.board.is_valid_coordinate(neighbor_pos[0], neighbor_pos[1]): continue
                neighbor_tile = self.board.get_tile(neighbor_pos[0], neighbor_pos[1])
                if not neighbor_tile: continue

                # Check for a two-way connection
                neighbor_conns = self.get_effective_connections(neighbor_tile.tile_type, neighbor_tile.orientation)
                required_entry_port = Direction.opposite(exit_dir).name
                if required_entry_port not in {ex for exits in neighbor_conns.values() for ex in exits}: continue

                # Determine the sequence index for the neighbor state
                next_seq_idx = current_state.seq_idx
                target_node = full_node_sequence[current_state.seq_idx]
                if neighbor_pos == target_node:
                    is_stop = neighbor_pos in stop_locations
                    if not is_stop or self._is_valid_stop_entry(neighbor_pos, exit_dir):
                        next_seq_idx += 1 # Advance sequence progress

                neighbor_state = PathState(pos=neighbor_pos, arrival_dir=exit_dir, seq_idx=next_seq_idx)
                
                tentative_g = current_g + 1
                if tentative_g < g_scores.get(neighbor_state, float('inf')):
                    came_from[neighbor_state] = current_state
                    g_scores[neighbor_state] = tentative_g
                    f_score = tentative_g + self._heuristic_sequential(neighbor_pos, next_seq_idx, full_node_sequence)
                    tie_breaker += 1
                    open_set.put((f_score, tie_breaker, neighbor_state))

        print(f"   -> FAIL: No valid path found for sequence.")
        return None, float('inf')

    def check_player_route_completion(self, player: Player) -> Tuple[bool, Optional[Tuple[int, int]]]:
        """Orchestrates route completion check using the new sequential A* pathfinder."""
        print(f"--- Checking P{player.player_id} Route Completion (Unified A*) ---")
        if not player.line_card or not player.route_card: return False, None
        
        stop_coords = player.get_required_stop_coords(self)
        if stop_coords is None:
            print(f"Route Check P{player.player_id}: FAILED - Not all required stops are on the board.")
            return False, None

        term1, term2 = self.get_terminal_coords(player.line_card.line_number)
        if not term1 or not term2: return False, None

        # --- Validate Sequence 1: Term1 -> Stops -> Term2 ---
        seq1_nodes = [term1] + stop_coords + [term2]
        path1, cost1 = self._find_sequential_goal_path(player, seq1_nodes)

        # --- Validate Sequence 2: Term2 -> Stops -> Term1 ---
        seq2_nodes = [term2] + stop_coords + [term1]
        path2, cost2 = self._find_sequential_goal_path(player, seq2_nodes)

        # --- Determine Outcome ---
        is_valid1 = (cost1 != float('inf'))
        is_valid2 = (cost2 != float('inf'))

        if not is_valid1 and not is_valid2:
            print(f"Route Check P{player.player_id}: FAILED - No valid sequence direction found.")
            return False, None
        
        chosen_start = None
        if is_valid1 and is_valid2:
            chosen_start = term1 if cost1 <= cost2 else term2
        elif is_valid1:
            chosen_start = term1
        else: # is_valid2 must be true
            chosen_start = term2

        if chosen_start:
             print(f"Route Check P{player.player_id}: COMPLETE. Chosen Start: {chosen_start}")
             player.start_terminal_coord = chosen_start
             return True, chosen_start
        
        return False, None

    def handle_route_completion(self, player: Player):
        if not player.start_terminal_coord:
             player.player_state = PlayerState.LAYING_TRACK
             return
        player.player_state = PlayerState.DRIVING
        player.required_node_index = 0 # Start by aiming for node 0 (the start terminal)
        player.streetcar_position = player.start_terminal_coord
        player.arrival_direction = None
        # Once placed, the tram must move OFF the start terminal, so the index immediately advances.
        player.required_node_index = 1 # Now aiming for the first stop (or end terminal if no stops)
        print(f"  Player {player.player_id} streetcar placed at: {player.streetcar_position}")
        if self.game_phase == GamePhase.LAYING_TRACK:
             self.game_phase = GamePhase.DRIVING
             print(f"\n*** ROUTE COMPLETE for Player {player.player_id}! Entering Driving Phase. ***")

    # =====================================================================
    # === NEW: DRIVING PHASE LOGIC (Using a basic A* for segments) ===
    # =====================================================================

    def _heuristic_manhattan(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def _find_basic_path(self, start_pos: Tuple[int, int], end_pos: Tuple[int, int], arrival_dir_at_start: Optional[Direction]) -> Optional[List[Tuple[int, int]]]:
        """A simple A* to find a path from A to B, respecting the U-turn rule and FORCED EXITS from valid stops."""
        start_state = (start_pos, arrival_dir_at_start)
        open_set = PriorityQueue()
        tie_breaker = 0
        f_score = self._heuristic_manhattan(start_pos, end_pos)
        open_set.put((f_score, tie_breaker, start_pos, arrival_dir_at_start))
        
        g_scores = {start_state: 0}
        came_from = {start_state: None}
        
        while not open_set.empty():
            _, _, current_pos, current_arrival_dir = open_set.get()
            
            if current_pos == end_pos:
                path = []
                curr = (current_pos, current_arrival_dir)
                while curr is not None:
                    path.append(curr[0])
                    curr = came_from.get(curr)
                return path[::-1]

            current_tile = self.board.get_tile(current_pos[0], current_pos[1])
            if not current_tile: continue

            # --- REFACTORED LOGIC: Determine valid exits ---
            forced_exit_dir: Optional[Direction] = None
            # Check if we are starting from a validly-entered stop, which forces our exit.
            if current_pos == start_pos:
                is_stop = start_pos in self.board.building_stop_locations.values()
                if is_stop and arrival_dir_at_start and self._is_valid_stop_entry(start_pos, arrival_dir_at_start):
                    # Player just "stopped" correctly. The only valid exit is to continue straight.
                    forced_exit_dir = arrival_dir_at_start
                    print(f"  (Pathfinding from valid stop, forcing exit via {forced_exit_dir.name})")
            
            current_conns = self.get_effective_connections(current_tile.tile_type, current_tile.orientation)
            valid_exit_dirs = []
            if forced_exit_dir:
                # If exit is forced, only consider that direction if the tile physically allows it.
                entry_port = Direction.opposite(arrival_dir_at_start).name if arrival_dir_at_start else None
                if entry_port and forced_exit_dir.name in current_conns.get(entry_port, []):
                    valid_exit_dirs.append(forced_exit_dir)
            else:
                # Standard logic: get all non-U-turn exits based on how we entered the current tile.
                entry_port = Direction.opposite(current_arrival_dir).name if current_arrival_dir else None
                if entry_port:
                    valid_exit_strs = current_conns.get(entry_port, [])
                else: # No entry constraint (very start of path), all exits are possible.
                    valid_exit_strs = list(set(ex for exits in current_conns.values() for ex in exits))
                valid_exit_dirs = [Direction.from_str(s) for s in valid_exit_strs]
            # --- END REFACTORED LOGIC ---

            for exit_dir in valid_exit_dirs:
                dr, dc = exit_dir.value
                neighbor_pos = (current_pos[0] + dr, current_pos[1] + dc)

                if not self.board.is_valid_coordinate(neighbor_pos[0], neighbor_pos[1]): continue
                
                tentative_g = g_scores.get((current_pos, current_arrival_dir), float('inf')) + 1
                neighbor_state = (neighbor_pos, exit_dir)

                if tentative_g < g_scores.get(neighbor_state, float('inf')):
                    came_from[neighbor_state] = (current_pos, current_arrival_dir)
                    g_scores[neighbor_state] = tentative_g
                    f_score = tentative_g + self._heuristic_manhattan(neighbor_pos, end_pos)
                    tie_breaker += 1
                    open_set.put((f_score, tie_breaker, neighbor_pos, exit_dir))
        return None

    def roll_special_die(self) -> Any:
        return random.choice(DIE_FACES)

    def trace_track_steps(self, player: Player, num_steps: int) -> Optional[Tuple[int, int]]:
        next_target = player.get_next_target_node(self)
        if not player.streetcar_position or not next_target: return player.streetcar_position
        
        path_segment = self._find_basic_path(player.streetcar_position, next_target, player.arrival_direction)
        if not path_segment or len(path_segment) <= 1: return player.streetcar_position

        target_idx = min(num_steps, len(path_segment) - 1)
        return path_segment[target_idx]

    def find_next_feature_on_path(self, player: Player) -> Optional[Tuple[int, int]]:
        next_target = player.get_next_target_node(self)
        if not player.streetcar_position or not next_target: return player.streetcar_position

        path_segment = self._find_basic_path(player.streetcar_position, next_target, player.arrival_direction)
        if not path_segment or len(path_segment) <= 1: return player.streetcar_position
        
        # Check path for features (stops or any terminal)
        for i in range(1, len(path_segment)):
            coord = path_segment[i]
            tile = self.board.get_tile(coord[0], coord[1])
            is_any_terminal = any(coord in pair for pair in TERMINAL_COORDS.values())
            if (tile and tile.has_stop_sign) or is_any_terminal:
                return coord # Return first feature found
        
        return path_segment[-1] # No features, go to end of segment

    def _get_entry_direction(self, from_coord: Tuple[int,int], to_coord: Tuple[int,int]) -> Optional[Direction]:
        if from_coord is None or to_coord is None: return None
        dr, dc = to_coord[0] - from_coord[0], to_coord[1] - from_coord[1]
        for d in Direction:
            if d.value == (dr, dc): return d
        return None

    def move_streetcar(self, player: Player, target_coord: Tuple[int, int]):
        """Moves streetcar and only increments target index if the visit to a required node is valid."""
        if player.streetcar_position is None: return

        # Determine the direction of arrival for the new position
        arrival_direction = self._get_entry_direction(player.streetcar_position, target_coord)

        # Update player's state for the new position
        player.streetcar_position = target_coord
        player.arrival_direction = arrival_direction
        print(f"Player {player.player_id} moved to {target_coord}")

        # Check if the new position is a required node for the player
        sequence = player.get_full_driving_sequence(self)
        if not sequence: return

        # The node the player was aiming for is at their current sequence index
        if player.required_node_index < len(sequence):
            the_node_player_was_aiming_for = sequence[player.required_node_index]

            if player.streetcar_position == the_node_player_was_aiming_for:
                # Landed on the target coordinate. Now check if the visit was valid.
                is_stop_tile = player.streetcar_position in self.board.building_stop_locations.values()
                
                is_valid_visit = False
                if is_stop_tile:
                    # For a stop, the entry direction must be valid (i.e., straight-through)
                    if player.arrival_direction and self._is_valid_stop_entry(player.streetcar_position, player.arrival_direction):
                        is_valid_visit = True
                        print(f"  -> Validly stopped at {player.streetcar_position}.")
                    else:
                        arr_dir_name = player.arrival_direction.name if player.arrival_direction else "None"
                        print(f"  -> Landed on stop {player.streetcar_position} but entry via {arr_dir_name} was INVALID.")
                else:
                    # If it's not a stop (i.e., a terminal), landing on it is always a valid visit.
                    is_valid_visit = True
                    print(f"  -> Reached terminal node {player.streetcar_position}.")

                # Only advance the sequence if the visit was valid.
                if is_valid_visit:
                    print(f"  Advancing sequence index from {player.required_node_index} to {player.required_node_index + 1}.")
                    player.required_node_index += 1

    def check_win_condition(self, player: Player) -> bool:
        if player.player_state != PlayerState.DRIVING: return False
        if not player.streetcar_position or not player.line_card: return False
        
        # Win condition: player has passed all required nodes
        full_sequence = player.get_full_driving_sequence(self)
        if not full_sequence: return False
        
        if player.required_node_index >= len(full_sequence):
             # And is at the final destination
            if player.streetcar_position == full_sequence[-1]:
                print(f"WIN CONDITION MET for Player {player.player_id}!")
                self.game_phase = GamePhase.GAME_OVER
                self.winner = player
                player.player_state = PlayerState.FINISHED
                return True
        return False

    def attempt_driving_move(self, player: Player, roll_result: Any) -> bool:
        if player.player_state != PlayerState.DRIVING: return False
        if self.actions_taken_this_turn > 0: return False

        target_coord: Optional[Tuple[int, int]] = None
        if roll_result == STOP_SYMBOL:
             target_coord = self.find_next_feature_on_path(player)
        elif isinstance(roll_result, int):
             target_coord = self.trace_track_steps(player, roll_result)
        
        if target_coord is None or target_coord == player.streetcar_position:
            print(f"Driving Info: No move for roll {roll_result}. Ending turn.")
            self.actions_taken_this_turn = MAX_PLAYER_ACTIONS
            self.confirm_turn()
            return True # No move, but turn ends successfully

        command = MoveCommand(self, player, target_coord)
        if self.command_history.execute_command(command):
             self.actions_taken_this_turn = MAX_PLAYER_ACTIONS
             if self.game_phase != GamePhase.GAME_OVER:
                  self.confirm_turn()
             return True
        return False

    def undo_last_action(self) -> bool:
        if self.actions_taken_this_turn <= 0: return False
        if self.command_history.undo():
             self.actions_taken_this_turn -= 1
             if self.get_active_player().player_state == PlayerState.DRIVING:
                 self.actions_taken_this_turn = 0
             return True
        return False

    def redo_last_action(self) -> bool:
        if self.get_active_player().player_state == PlayerState.LAYING_TRACK and self.actions_taken_this_turn >= MAX_PLAYER_ACTIONS:
            return False
        cmd = self.command_history.get_command_to_redo()
        if not cmd: return False
        if self.command_history.redo():
             if isinstance(cmd, (PlaceTileCommand, ExchangeTileCommand)):
                 self.actions_taken_this_turn += 1
             elif isinstance(cmd, MoveCommand):
                 self.actions_taken_this_turn = MAX_PLAYER_ACTIONS
             return True
        return False

    def confirm_turn(self) -> bool:
        active_player = self.get_active_player()
        if self.game_phase == GamePhase.GAME_OVER: return False
        if active_player.player_state == PlayerState.LAYING_TRACK and self.actions_taken_this_turn < MAX_PLAYER_ACTIONS:
            return False
        if active_player.player_state == PlayerState.DRIVING and self.actions_taken_this_turn < MAX_PLAYER_ACTIONS:
            return False

        if active_player.player_state == PlayerState.LAYING_TRACK:
            needed = HAND_TILE_LIMIT - len(active_player.hand)
            for _ in range(min(needed, MAX_PLAYER_ACTIONS)): self.draw_tile(active_player)
        
        self.active_player_index = (self.active_player_index + 1) % self.num_players
        if self.active_player_index == 0: self.current_turn += 1
        self.actions_taken_this_turn = 0
        self.command_history.clear_redo_history()
        
        next_player = self.get_active_player()
        print(f"\n--- Starting Turn {self.current_turn} for Player {next_player.player_id} ({next_player.player_state.name}) ---")

        if next_player.player_state == PlayerState.LAYING_TRACK:
            is_complete, _ = self.check_player_route_completion(next_player)
            if is_complete:
                self.handle_route_completion(next_player)
        return True

    def save_game(self, filename: str) -> bool:
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
            }
            with open(filename, 'w') as f: json.dump(game_state_data, f, indent=4)
            print("Save successful.")
            return True
        except Exception as e:
            print(f"!!! Error saving game to {filename}: {e} !!!"); traceback.print_exc(); return False

    @staticmethod
    def load_game(filename: str, tile_types: Dict[str, 'TileType']) -> Optional['Game']:
        print(f"Loading game state from {filename}...")
        try:
            with open(filename, 'r') as f: data = json.load(f)
            num_players = data.get("num_players", 2)
            game = Game(num_players) # Create a fresh instance
            game.active_player_index = data.get("active_player_index", 0)
            game.game_phase = GamePhase[data.get("game_phase", "LAYING_TRACK")]
            game.current_turn = data.get("current_turn", 1)
            game.actions_taken_this_turn = data.get("actions_taken", 0)
            game.winner = None
            game.command_history = CommandHistory() # Reset history
            game.board = Board.from_dict(data["board"], tile_types)
            game.players = [Player.from_dict(p_data, tile_types) for p_data in data["players"]]
            winner_id = data.get("winner_id")
            if winner_id is not None: game.winner = game.players[winner_id]
            game.tile_draw_pile = [tile_types[name] for name in data.get("tile_draw_pile", [])]
            game.line_cards_pile = []
            print(f"Load successful. Phase: {game.game_phase.name}, Turn: {game.current_turn}, Active P: {game.active_player_index}")
            return game
        except Exception as e:
            print(f"!!! Error loading game from {filename}: {e} !!!"); traceback.print_exc(); return None