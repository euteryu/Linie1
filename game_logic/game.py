from __future__ import annotations
from typing import List, Dict, Tuple, Optional, Any, TYPE_CHECKING
import random, json, traceback, copy
from queue import PriorityQueue
import pygame

if TYPE_CHECKING:
    from .pathfinding import Pathfinder

from .enums import PlayerState, GamePhase, Direction
from .tile import TileType, PlacedTile
from .cards import LineCard, RouteCard
from .player import Player, HumanPlayer, AIPlayer, RouteStep
from .board import Board
from .command_history import CommandHistory
from .commands import Command, PlaceTileCommand, ExchangeTileCommand, MoveCommand, CombinedActionCommand
from .pathfinding import AStarPathfinder, BFSPathfinder
from .ai_strategy import EasyStrategy, HardStrategy # Import the strategies

from constants import (
    TILE_DEFINITIONS, TILE_COUNTS_BASE, TILE_COUNTS_5_PLUS_ADD, HAND_TILE_LIMIT,
    MAX_PLAYER_ACTIONS, DIE_FACES, STOP_SYMBOL, TERMINAL_COORDS, STARTING_HAND_TILES,
    ROUTE_CARD_VARIANTS, TERMINAL_DATA, START_NEXT_TURN_EVENT
)

class Game:
    def __init__(self, players_config: List[str]):
        """
        Initializes the game with a flexible player configuration.
        Example: players_config = ['human', 'easy_ai', 'hard_ai']
        """
        if not 1 <= len(players_config) <= 6:
            raise ValueError("Total players must be 1-6.")

        self.num_players = len(players_config)
        self.players: List[Player] = []

        # Create players based on the config list
        for i, p_type in enumerate(players_config):
            if p_type.lower() == 'human':
                self.players.append(HumanPlayer(i))
            elif p_type.lower() == 'easy_ai':
                self.players.append(AIPlayer(i, EasyStrategy()))
            elif p_type.lower() == 'hard_ai':
                self.players.append(AIPlayer(i, HardStrategy()))
            else:
                raise ValueError(f"Unknown player type in config: {p_type}")

        self.tile_types = {name: TileType(name=name, **details) for name, details in TILE_DEFINITIONS.items()}
        self.board = Board()
        self.board._initialize_terminals(self.tile_types)
        
        # Initialize attributes that will be populated by setup_game
        self.tile_draw_pile: List[TileType] = []
        self.line_cards_pile: List[LineCard] = []
        self.active_player_index: int = 0
        self.game_phase: GamePhase = GamePhase.SETUP
        self.current_turn: int = 0
        self.winner: Optional[Player] = None
        self.actions_taken_this_turn: int = 0
        self.command_history = CommandHistory()
        self.pathfinder: Pathfinder = BFSPathfinder()
        self.MAX_PLAYER_ACTIONS = MAX_PLAYER_ACTIONS
        self.HAND_TILE_LIMIT = HAND_TILE_LIMIT

        self.setup_game()

    def setup_game(self):
        """Initializes piles, deals starting hands and cards for a new game."""
        if self.game_phase != GamePhase.SETUP:
            print("Warning: setup_game called on an already started game. Resetting.")
        
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

        # --- THIS IS THE FIX ---
        # After setup is complete, check if the first player is an AI.
        # If so, we must manually trigger their turn to start the game, as there
        # will be no human input to get the event loop rolling.
        first_player = self.get_active_player()
        if isinstance(first_player, AIPlayer):
            print(f"--- Game initiated by AI Player {first_player.player_id}. Kicking off turn... ---")
            # This is the proactive call that was missing.
            first_player.handle_turn_logic(self)
        # --- END OF FIX ---


    def _calculate_ai_ideal_route(self, player: AIPlayer) -> Optional[List[RouteStep]]:
        """Calculates the AI's 'wet dream' path assuming infinite tiles."""
        if not player.line_card or not player.route_card: return None
        
        stops = player.get_required_stop_coords(self)
        if stops is None: return None
        
        t1, t2 = self.get_terminal_coords(player.line_card.line_number)
        if not t1 or not t2: return None

        # Find the shortest path in both directions and choose the best one.
        path1, cost1 = self.pathfinder.find_path(self, [t1] + stops + [t2], is_hypothetical=True)
        path2, cost2 = self.pathfinder.find_path(self, [t2] + stops + [t1], is_hypothetical=True)
        
        if cost1 == float('inf') and cost2 == float('inf'):
            return None
        
        return path1 if cost1 <= cost2 else path2

    def _score_ai_move(self, player: AIPlayer, tile_to_place: TileType, orientation: int, r: int, c: int) -> int:
        """Scores a potential AI move based on its strategic value."""
        score = 0
        if not player.ideal_route_plan: return 0

        # High score for placing a tile that is part of the ideal plan
        for i, step in enumerate(player.ideal_route_plan):
            if step.coord == (r,c):
                # We would need to check if tile_to_place matches the required tile for this step
                # This is a simplification for now
                score += 100 - i # Higher score for earlier steps in the plan
                break

        # Score for connecting to existing track
        # (Simplified check)
        for direction in Direction:
            nr, nc = r + direction.value[0], c + direction.value[1]
            if self.board.get_tile(nr, nc):
                score += 10
        
        return score

    def _handle_ai_turn(self, player: AIPlayer):
        """Orchestrates the AI's entire turn during the LAYING_TRACK phase."""
        print(f"\n--- AI Player {player.player_id}'s Turn ---")
        
        for action_num in range(MAX_PLAYER_ACTIONS):
            # 1. Plan: Recalculate the ideal route
            player.ideal_route_plan = self._calculate_ai_ideal_route(player)
            if player.ideal_route_plan:
                print(f"  AI Action {action_num+1}: Ideal path found with {len(player.ideal_route_plan)} steps.")
            else:
                print(f"  AI Action {action_num+1}: No ideal path found. Placing randomly.")
            
            # 2. Evaluate and Select Best Move
            best_move = None
            best_score = -1

            for tile in player.hand:
                for r in range(self.board.rows):
                    for c in range(self.board.cols):
                        for orientation in [0, 90, 180, 270]:
                            is_valid, _ = self.check_placement_validity(tile, orientation, r, c)
                            if is_valid:
                                score = self._score_ai_move(player, tile, orientation, r, c)
                                if score > best_score:
                                    best_score = score
                                    best_move = (tile, orientation, r, c)
            
            # 3. Execute Move
            if best_move:
                tile, orientation, r, c = best_move
                print(f"  AI chooses to place {tile.name} at ({r},{c}) with orientation {orientation} (Score: {best_score})")
                self.attempt_place_tile(player, tile, orientation, r, c)
            else:
                print("  AI could not find any valid move.")
                # AI must still perform an action. This is a fallback.
                # In a real game, it might discard a tile. Here we just end its action.
        
        # End of AI's two actions
        self.confirm_turn()


    def get_active_player(self) -> Player:
        if 0 <= self.active_player_index < len(self.players): return self.players[self.active_player_index]
        else: raise IndexError("Active player index out of bounds.")

    def _create_tile_and_line_piles(self):
        """Creates and shuffles the tile draw pile and line card pile."""
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

        random.shuffle(self.tile_draw_pile)
        print(f"Tile draw pile created: {len(self.tile_draw_pile)} tiles.")

        # --- CORRECTED LOGIC ---
        # Dynamically create Line Cards based on the actual keys in TERMINAL_DATA.
        # This ensures that we always have the correct number of unique line cards
        # matching the game's configuration.
        self.line_cards_pile = [LineCard(line_num) for line_num in TERMINAL_DATA.keys()]
        random.shuffle(self.line_cards_pile)
        print(f"Line card pile created with {len(self.line_cards_pile)} cards for lines: {sorted(list(TERMINAL_DATA.keys()))}")
        # --- END CORRECTION ---

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
        """Deals one Line card and one Route card to each player and prints assignments for debugging."""
        print("--- Dealing Player Cards (DEBUG) ---")
        
        # --- ADDED ROBUSTNESS CHECKS ---
        if len(self.line_cards_pile) < self.num_players:
            print(f"FATAL ERROR: Not enough line cards ({len(self.line_cards_pile)}) for the number of players ({self.num_players}).")
            # This should not happen with correct setup, but we guard against it.
            # We will deal what we can to avoid a hard crash.
            while len(self.line_cards_pile) < self.num_players:
                print("WARNING: Synthesizing a dummy LineCard to prevent crash.")
                self.line_cards_pile.append(LineCard(1)) # Add a dummy card
        
        if len(ROUTE_CARD_VARIANTS) == 0:
            raise RuntimeError("FATAL ERROR: ROUTE_CARD_VARIANANTS in constants.py is empty.")
        # --- END ROBUSTNESS CHECKS ---

        available_variants = list(range(len(ROUTE_CARD_VARIANTS)))
        random.shuffle(available_variants)
        player_range = "1-4" if self.num_players <= 4 else "5-6"

        for player in self.players:
            # Another guard, just in case.
            if not self.line_cards_pile:
                print(f"CRITICAL: line_cards_pile became empty before dealing to Player {player.player_id}. This indicates a severe logic error.")
                # Assign a dummy card to prevent a crash and allow the game to continue for debugging.
                player.line_card = LineCard(1)
            else:
                player.line_card = self.line_cards_pile.pop()

            # Ensure we have route variants, recycle if we run out (for >6 players, though illegal)
            if not available_variants:
                available_variants = list(range(len(ROUTE_CARD_VARIANTS)))
                random.shuffle(available_variants)

            variant_index = available_variants.pop(0)
            
            try:
                line_num = player.line_card.line_number
                stops = ROUTE_CARD_VARIANTS[variant_index][player_range][line_num]
            except (KeyError, IndexError) as e:
                print(f"Warning: Route lookup failed for P{player.player_id} (Line {line_num}, Var {variant_index}). Assigning default.")
                # Assign a default route to prevent crash
                stops = ROUTE_CARD_VARIANTS[0]["1-4"][1]
            
            player.route_card = RouteCard(stops, variant_index)
            
            print(f"  Player {player.player_id} assigned: Line {player.line_card.line_number}, Stops {player.route_card.stops}")

        self.line_cards_pile = [] # Clear any remaining cards
        print("------------------------------------")

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

    # --- Helper function to query the board state, considering hypotheticals ---
    def _get_hypothetical_tile(self, r: int, c: int, hypothetical_moves: Optional[List[Dict]] = None) -> Optional[PlacedTile]:
        """Checks for a tile in staged moves first, then falls back to the real board."""
        if hypothetical_moves:
            for move in hypothetical_moves:
                if move['coord'] == (r, c):
                    # This move is on the square we're checking. Return a PlacedTile from it.
                    return PlacedTile(move['tile_type'], move['orientation'])
        # If not found in staged moves, check the real board
        return self.board.get_tile(r, c)

    # --- Modify the signature and logic of the validation functions ---
    def check_placement_validity(self, tile_type: TileType, orientation: int, r: int, c: int, hypothetical_moves: Optional[List[Dict]] = None) -> Tuple[bool, str]:
        """
        A definitive, correct, and final validation function that correctly
        handles all neighbor types: existing tiles, empty playable squares,
        buildings, and walls.
        """
        # 1. Basic check on the target square itself.
        if not self.board.is_playable_coordinate(r, c) or self.board.get_tile(r, c) or self.board.get_building_at(r, c):
            return False, "Target square is not empty and playable."

        new_connections = self.get_effective_connections(tile_type, orientation)

        # 2. Loop through all four directions (N, E, S, W).
        for direction in Direction:
            # A. Does our new tile have a track pointing in this `direction`?
            has_outgoing_track = any(direction.name in exits for exits in new_connections.values())
            
            # B. Get information about the neighbor.
            nr, nc = r + direction.value[0], c + direction.value[1]
            neighbor_tile = self._get_hypothetical_tile(nr, nc, hypothetical_moves)
            
            if neighbor_tile:
                # --- CASE 1: The neighbor is an existing tile. ---
                neighbor_connections = self.get_effective_connections(neighbor_tile.tile_type, neighbor_tile.orientation)
                required_neighbor_exit = Direction.opposite(direction).name
                neighbor_has_incoming_track = any(required_neighbor_exit in exits for exits in neighbor_connections.values())
                
                # The connection is valid ONLY if both have a track or neither has a track.
                if has_outgoing_track != neighbor_has_incoming_track:
                    return False, f"Connection mismatch with existing tile at ({nr},{nc})."
            
            else:
                # --- CASE 2: The neighbor is an empty space. ---
                # If our new tile has a track pointing out, that empty space cannot be a wall or a building.
                if has_outgoing_track:
                    if not self.board.is_playable_coordinate(nr, nc):
                        return False, f"Cannot have a track pointing into a wall at ({nr},{nc})."
                    if self.board.get_building_at(nr, nc):
                        return False, f"Cannot have a track pointing into a building at ({nr},{nc})."
        
        # If we looped through all 4 neighbors and found no illegal conditions, the placement is valid.
        return True, "Placement is valid."


    def check_exchange_validity(self, player: Player, new_tile_type: TileType, new_orientation: int, r: int, c: int, hypothetical_moves: Optional[List[Dict]] = None) -> Tuple[bool, str]:
        """
        A definitive, robust validation for exchanging a tile, correctly
        implementing all preservation and new-connection rules.
        """
        # --- Step 1 & 2: Basic Eligibility and Resource Checks ---
        old_tile = self.board.get_tile(r, c)
        if not old_tile: return False, "No tile to exchange."
        if not old_tile.tile_type.is_swappable: return False, "Tile is not swappable."
        if old_tile.has_stop_sign: return False, "Cannot exchange a Stop Sign tile."
        if old_tile.is_terminal: return False, "Cannot exchange a Terminal tile."
        if new_tile_type not in player.hand: return False, "Player does not have tile in hand."
        if old_tile.tile_type == new_tile_type: return False, "Cannot replace a tile with the same type."

        old_conns = self.get_effective_connections(old_tile.tile_type, old_tile.orientation)
        new_conns = self.get_effective_connections(new_tile_type, new_orientation)

        # Helper to get all unique connections as a set of frozensets
        def get_connection_set(conn_map: Dict[str, List[str]]) -> set:
            return {frozenset([entry, exit]) for entry, exits in conn_map.items() for exit in exits}

        old_conn_set = get_connection_set(old_conns)
        new_conn_set = get_connection_set(new_conns)

        # --- Step 3: Connection Preservation Check ---
        if not old_conn_set.issubset(new_conn_set):
            return False, f"Connection Preservation Failed. New tile does not have all connections of the old tile."

        # --- Step 4: New Connection Validity Check ---
        added_connections = new_conn_set - old_conn_set
        
        for conn_pair in added_connections:
            # For each new connection, we must validate that it's being placed legally.
            # We can check this by treating each end of the connection as an "outgoing" track.
            dir1_str, dir2_str = list(conn_pair)
            
            for exit_dir_str in [dir1_str, dir2_str]:
                exit_dir_enum = Direction.from_str(exit_dir_str)
                nr, nc = r + exit_dir_enum.value[0], c + exit_dir_enum.value[1]
                
                # neighbor_tile = self.board.get_tile(nr, nc)
                neighbor_tile = self._get_hypothetical_tile(nr, nc, hypothetical_moves)
                
                if neighbor_tile:
                    # If the neighbor is a tile, it MUST connect back.
                    neighbor_conns = self.get_effective_connections(neighbor_tile.tile_type, neighbor_tile.orientation)
                    required_neighbor_exit = Direction.opposite(exit_dir_enum).name
                    if not any(required_neighbor_exit in exits for exits in neighbor_conns.values()):
                        return False, f"New connection towards ({nr},{nc}) is invalid; neighbor does not connect back."
                else:
                    # If the neighbor is empty, it cannot be a wall or building.
                    if not self.board.is_playable_coordinate(nr, nc):
                        return False, f"New connection points into a wall at ({nr},{nc})."
                    if self.board.get_building_at(nr, nc):
                        return False, f"New connection points into a building at ({nr},{nc})."

        return True, "Exchange is valid."




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


    def draw_tile(self, player: Player) -> bool:
        if not self.tile_draw_pile: return False
        if len(player.hand) >= HAND_TILE_LIMIT: return False
        player.hand.append(self.tile_draw_pile.pop())
        return True

    def attempt_place_tile(self, player: Player, tile_type: TileType, orientation: int, r: int, c: int) -> bool:
        """ Creates and executes a PlaceTileCommand AFTER validation. """
        if self.actions_taken_this_turn >= self.MAX_PLAYER_ACTIONS: return False
        
        # --- ADDED DEBUG PRINT ---
        is_valid, reason = self.check_placement_validity(tile_type, orientation, r, c)
        print(f"--- [GAME] Checking place validity... Result: {is_valid} (Reason: {reason}) ---")
        
        if not is_valid:
            return False

        command = PlaceTileCommand(self, player, tile_type, orientation, r, c)
        if self.command_history.execute_command(command):
            self.actions_taken_this_turn += 1
            return True
        return False

    def attempt_exchange_tile(self, player: Player, new_tile_type: TileType, new_orientation: int, r: int, c: int) -> bool:
        """ Creates and executes an ExchangeTileCommand AFTER validation. """
        if self.actions_taken_this_turn >= self.MAX_PLAYER_ACTIONS: return False
        
        # --- ADDED DEBUG PRINT ---
        is_valid, reason = self.check_exchange_validity(player, new_tile_type, new_orientation, r, c)
        print(f"--- [GAME] Checking exchange validity... Result: {is_valid} (Reason: {reason}) ---")

        if not is_valid:
            return False

        command = ExchangeTileCommand(self, player, new_tile_type, new_orientation, r, c)
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

    def _find_sequential_goal_path(self, player: Player, full_node_sequence: List[Tuple[int, int]]) -> Tuple[Optional[List[RouteStep]], int]:
        """
        Finds the shortest valid path through a sequence of nodes, considering tile rules.
        This pathfinder can be configured (e.g., tile availability) for planning.
        """
        start_pos = full_node_sequence[0]
        # For planning, we need to simulate tiles, so the A* needs to know about the AI's hand.
        # This requires a more sophisticated pathfinder that can "query" tile availability.
        # For now, let's use the generic one and assume availability is checked during move evaluation.
        # The 'previous_target_node_for_exit_check' is passed to _get_valid_successors.
        previous_target_node_for_exit_check = None # This logic will be in the AI's move evaluation

        # The pathfinding for planning is complex. It needs to consider:
        # 1. Available tiles in hand.
        # 2. Valid placements on board (respecting existing tiles).
        # 3. Route constraints (stops, U-turns).
        # This might require a specialized planning pathfinder or a heavily parameterized one.
        # For now, let's assume our general pathfinder (BFS/A*) can be adapted to check *potential* placements.
        # The challenge is simulating tile availability during pathfinding.
        # A simpler approach for initial planning: find the theoretical shortest path, then score moves based on hand tiles matching path segments.
        
        # Reusing the sequential finder here for simplicity, but acknowledging it's not perfectly hand-aware yet.
        # The move evaluation will filter based on hand.
        path1, cost1 = self.pathfinder.find_path(self, player, [t1] + stops + [t2])
        path2, cost2 = self.pathfinder.find_path(self, player, [t2] + stops + [t1])
        
        valid1, valid2 = (cost1 != float('inf')), (cost2 != float('inf'))
        if not valid1 and not valid2: return None, float('inf')
        
        chosen_start, optimal_path = (t1, path1) if valid1 and (not valid2 or cost1 <= cost2) else (t2, path2)
        
        return chosen_start, optimal_path

    def check_player_route_completion(self, player: Player) -> Tuple[bool, Optional[Tuple[int, int]], Optional[List[RouteStep]]]:
        if not player.line_card or not player.route_card: return False, None, None
        stops = player.get_required_stop_coords(self)
        if stops is None: return False, None, None
        t1, t2 = self.get_terminal_coords(player.line_card.line_number)
        if not t1 or not t2: return False, None, None

        # --- PATHFINDING FOR ROUTE VALIDATION (uses general rules) ---
        path1, cost1 = self.pathfinder.find_path(self, player, [t1] + stops + [t2])
        path2, cost2 = self.pathfinder.find_path(self, player, [t2] + stops + [t1])

        # --- PATHFINDING FOR AI PLANNING (Hypothetical Ideal Route) ---
        # This call needs to know that it's planning and can use any tile.
        # We might need a dedicated planning pathfinder or a flag/filter.
        # For now, let's assume find_path can accept None for tile_filter,
        # and internally, if player is AI, it simulates unconstrained.
        # (This would be a change to Pathfinder.find_path signature)
        #
        # For now, let's assume the Pathfinder can be told its purpose.
        # If we create a PlanningPathfinder, this is where it's used.
        # For simplicity, let's assume pathfinder has a flag for 'planning_mode'
        # or it defaults to unconstrained if no filter is given for AI player.
        #
        # Let's adapt pathfinder to accept player type or a flag.
        # For now, we'll pass None for tile_filter to signify unconstrained search.
        # The pathfinder needs to distinguish between 'validation' and 'planning' IF rules differ.
        # If rules are same (just tile availability differs), we can manage that in evaluation.
        #
        # For the "wet dream" path, we don't need tile_filter, as it's unconstrained.
        # The pathfinder should simply use all available tile types.
        # So, we can likely reuse the existing find_path by passing `None` for filter.
        # The actual check against the HAND will happen in AIPlayer.evaluate_moves.

        # The existing pathfinding should inherently respect game rules for any tile type.
        # The validation aspect comes from the sequence.
        
        # path1, cost1 = self.pathfinder.find_path(self, player, [t1] + stops + [t2]) # Use the planning context
        # path2, cost2 = self.pathfinder.find_path(self, player, [t2] + stops + [t1]) # Use the planning context

        # (The rest of the logic for determining chosen_start and optimal_path remains the same)
        # ... The critical part is that the pathfinder used here MUST NOT be hand-constrained.
        # Our current BFSPathfinder and AStarPathfinder are *rule-constrained* but not *hand-constrained*.
        # So, they are already suitable for finding the 'ideal path'.

        valid1, valid2 = (cost1 != float('inf')), (cost2 != float('inf'))
        if not valid1 and not valid2: return False, None, None
        
        start, path = (t1, path1) if valid1 and (not valid2 or cost1 <= cost2) else (t2, path2)
        
        if start: return True, start, path
        return False, None, None

    def handle_route_completion(self, player: Player, chosen_start: Tuple[int, int], optimal_path: List[RouteStep]):
        player.player_state, player.start_terminal_coord, player.validated_route = PlayerState.DRIVING, chosen_start, optimal_path
        player.streetcar_path_index, player.required_node_index = 0, 1
        
        print(f"  Player {player.player_id} streetcar placed at: {player.streetcar_position}")
        
        # --- ADDED DEBUG OUTPUT FOR VALIDATED ROUTE ---
        print("--- Validated Route Path ---")
        if player.validated_route:
            for i, step in enumerate(player.validated_route):
                arr_dir_str = step.arrival_direction.name if step.arrival_direction else "Start"
                goal_marker = "[GOAL]" if step.is_goal_node else ""
                print(f"  Step {i:<2}: {step.coord} (Arrival: {arr_dir_str:<5}) {goal_marker}")
        else:
            print("  No validated route found.")
        print("--- End Validated Route ---")
        
        if self.game_phase == GamePhase.LAYING_TRACK:
             self.game_phase = GamePhase.DRIVING



    def _heuristic_manhattan(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> int:
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def _find_basic_path(self, start_pos: Tuple[int, int], end_pos: Tuple[int, int], arrival_dir_at_start: Optional[Direction], previous_target_node: Optional[Tuple[int, int]]) -> Optional[List[Tuple[int, int]]]:
        """
        A simple A* to find a path from A to B, respecting the U-turn rule and
        only forcing a straight-through exit if the start_pos was the required
        goal on the previous turn.
        """
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

            # --- FINAL CORRECTED LOGIC ---
            forced_exit_dir: Optional[Direction] = None
            if current_pos == start_pos:
                is_stop = start_pos in self.board.building_stop_locations.values()
                # Check if the tile we are starting from was the required goal of the PREVIOUS move.
                was_the_required_goal = (start_pos == previous_target_node)
                
                # The "forced straight" rule ONLY applies if all three are true:
                # 1. We are starting on a stop tile.
                # 2. That stop was our specific required goal last turn.
                # 3. We entered it validly.
                if is_stop and was_the_required_goal and arrival_dir_at_start and self._is_valid_stop_entry(start_pos, arrival_dir_at_start):
                    forced_exit_dir = arrival_dir_at_start
                    print(f"  (Pathfinding from REQUIRED GOAL stop {start_pos}, forcing exit via {forced_exit_dir.name})")

            current_conns = self.get_effective_connections(current_tile.tile_type, current_tile.orientation)
            valid_exit_dirs = []
            if forced_exit_dir:
                entry_port = Direction.opposite(arrival_dir_at_start).name if arrival_dir_at_start else None
                if entry_port and forced_exit_dir.name in current_conns.get(entry_port, []):
                    valid_exit_dirs.append(forced_exit_dir)
            else:
                # Standard logic for regular tiles OR non-required stops.
                entry_port = Direction.opposite(current_arrival_dir).name if current_arrival_dir else None
                if entry_port:
                    valid_exit_strs = current_conns.get(entry_port, [])
                else: 
                    valid_exit_strs = list(set(ex for exits in current_conns.values() for ex in exits))
                valid_exit_dirs = [Direction.from_str(s) for s in valid_exit_strs]
            # --- END FINAL CORRECTED LOGIC ---

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

    def trace_track_steps(self, player: Player, num_steps: int) -> Optional[Tuple[int, int]]:
        """
        Calculates destination by finding path segment.
        The tram moves up to num_steps, but MUST stop if it lands on its next required node.
        """
        sequence = player.get_full_driving_sequence(self)
        if not player.streetcar_position or not sequence:
            return player.streetcar_position

        next_target = sequence[player.required_node_index] if player.required_node_index < len(sequence) else None
        previous_target = sequence[player.required_node_index - 1] if player.required_node_index > 0 else None
        if not next_target: return player.streetcar_position

        path_segment = self._find_basic_path(player.streetcar_position, next_target, player.arrival_direction, previous_target)
        if not path_segment or len(path_segment) <= 1: return player.streetcar_position

        # --- CORRECTED MOVEMENT LOGIC ---
        path_length_to_node = len(path_segment) - 1

        if path_length_to_node <= num_steps:
            # If the roll is enough (or more than enough) to reach the next required node,
            # the destination IS the node.
            print(f"  (Roll of {num_steps} is sufficient to reach goal {path_length_to_node} steps away. Stopping at goal.)")
            return path_segment[-1]
        else:
            # If the roll is not enough to reach the goal, move exactly num_steps along the path.
            return path_segment[num_steps]

    def find_next_feature_on_path(self, player: Player) -> Optional[Tuple[int, int]]:
        """Finds path segment, then finds first feature on THAT segment."""
        sequence = player.get_full_driving_sequence(self)
        if not player.streetcar_position or not sequence:
            return player.streetcar_position

        # Determine the NEXT and PREVIOUS target nodes.
        next_target = sequence[player.required_node_index] if player.required_node_index < len(sequence) else None
        previous_target = sequence[player.required_node_index - 1] if player.required_node_index > 0 else None
        if not next_target: return player.streetcar_position
        
        path_segment = self._find_basic_path(player.streetcar_position, next_target, player.arrival_direction, previous_target)
        if not path_segment or len(path_segment) <= 1: return player.streetcar_position
        
        for i in range(1, len(path_segment)):
            coord = path_segment[i]
            tile = self.board.get_tile(coord[0], coord[1])
            is_any_terminal = any(coord in pair for pair in TERMINAL_COORDS.values())
            if (tile and tile.has_stop_sign) or is_any_terminal:
                return coord # Return first feature found
        
        return path_segment[-1] # No features, go to end of segment

    def roll_special_die(self) -> Any:
        return random.choice(DIE_FACES)


    def _get_entry_direction(self, from_coord: Tuple[int,int], to_coord: Tuple[int,int]) -> Optional[Direction]:
        if from_coord is None or to_coord is None: return None
        dr, dc = to_coord[0] - from_coord[0], to_coord[1] - from_coord[1]
        for d in Direction:
            if d.value == (dr, dc): return d
        return None

    def move_streetcar(self, player: Player, target_path_index: int):
        """Moves streetcar by updating its index in the validated path."""
        if not player.validated_route or not (0 <= target_path_index < len(player.validated_route)): return
        
        player.streetcar_path_index = target_path_index
        
        # Check if the new step is a goal node to update progress
        new_step = player.validated_route[target_path_index]
        if new_step.is_goal_node:
            print(f"  -> Reached required node at {new_step.coord}. Advancing sequence index.")
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


    def _find_sequential_goal_path(self, player: Player, full_node_sequence: List[Tuple[int, int]]) -> Tuple[Optional[List[RouteStep]], int]:
        """
        Performs a multi-goal A* search and returns a rich path of RouteStep objects.
        """
        print(f"--- SEQ A* P{player.player_id}: Validating sequence {full_node_sequence} ---")
        start_pos = full_node_sequence[0]
        start_state = PathState(pos=start_pos, arrival_dir=None, seq_idx=1)

        if not self.board.get_tile(start_pos[0], start_pos[1]): return None, float('inf')

        open_set = PriorityQueue()
        tie_breaker = 0
        f_score = self._heuristic_sequential(start_pos, 1, full_node_sequence)
        open_set.put((f_score, tie_breaker, start_state))

        g_scores = {start_state: 0}
        came_from = {start_state: None}
        goal_node_coords = set(full_node_sequence)
        stop_locations = set(self.board.building_stop_locations.values())

        while not open_set.empty():
            _, _, current_state = open_set.get()

            if current_state.seq_idx == len(full_node_sequence):
                # --- PATH RECONSTRUCTION WITH RouteStep OBJECTS ---
                path_steps: List[RouteStep] = []
                curr = current_state
                while curr is not None:
                    is_goal = curr.pos in goal_node_coords
                    step = RouteStep(
                        coord=curr.pos,
                        is_goal_node=is_goal,
                        arrival_direction=curr.arrival_dir
                    )
                    path_steps.append(step)
                    curr = came_from.get(curr)
                return path_steps[::-1], g_scores[current_state]

            # ... (the A* successor generation logic remains the same as before)
            current_g = g_scores[current_state]
            current_tile = self.board.get_tile(current_state.pos[0], current_state.pos[1])
            if not current_tile: continue
            current_conns = self.get_effective_connections(current_tile.tile_type, current_tile.orientation)
            entry_port = Direction.opposite(current_state.arrival_dir).name if current_state.arrival_dir else None
            if entry_port: valid_exit_strs = current_conns.get(entry_port, [])
            else: valid_exit_strs = list(set(ex for exits in current_conns.values() for ex in exits))
            for exit_dir_str in valid_exit_strs:
                exit_dir = Direction.from_str(exit_dir_str)
                dr, dc = exit_dir.value
                neighbor_pos = (current_state.pos[0] + dr, current_state.pos[1] + dc)
                if not self.board.is_valid_coordinate(neighbor_pos[0], neighbor_pos[1]): continue
                neighbor_tile = self.board.get_tile(neighbor_pos[0], neighbor_pos[1])
                if not neighbor_tile: continue
                neighbor_conns = self.get_effective_connections(neighbor_tile.tile_type, neighbor_tile.orientation)
                required_entry_port = Direction.opposite(exit_dir).name
                if required_entry_port not in {ex for exits in neighbor_conns.values() for ex in exits}: continue
                next_seq_idx = current_state.seq_idx
                target_node = full_node_sequence[current_state.seq_idx]
                if neighbor_pos == target_node:
                    if not (neighbor_pos in stop_locations) or self._is_valid_stop_entry(neighbor_pos, exit_dir):
                        next_seq_idx += 1
                neighbor_state = PathState(pos=neighbor_pos, arrival_dir=exit_dir, seq_idx=next_seq_idx)
                tentative_g = current_g + 1
                if tentative_g < g_scores.get(neighbor_state, float('inf')):
                    came_from[neighbor_state] = current_state
                    g_scores[neighbor_state] = tentative_g
                    f_score = tentative_g + self._heuristic_sequential(neighbor_pos, next_seq_idx, full_node_sequence)
                    tie_breaker += 1
                    open_set.put((f_score, tie_breaker, neighbor_state))
        
        return None, float('inf')

    def check_player_route_completion(self, player: Player) -> Tuple[bool, Optional[Tuple[int, int]], Optional[List[RouteStep]]]:
        if not player.line_card or not player.route_card: return False, None, None
        stops = player.get_required_stop_coords(self)
        if stops is None: return False, None, None
        t1, t2 = self.get_terminal_coords(player.line_card.line_number)
        if not t1 or not t2: return False, None, None

        # This is where the pathfinder is called. It returns the optimal path if one exists.
        path1, cost1 = self.pathfinder.find_path(self, player, [t1] + stops + [t2])
        path2, cost2 = self.pathfinder.find_path(self, player, [t2] + stops + [t1])

        valid1, valid2 = (cost1 != float('inf')), (cost2 != float('inf'))
        if not valid1 and not valid2: return False, None, None
        
        chosen_start, optimal_path = (t1, path1) if valid1 and (not valid2 or cost1 <= cost2) else (t2, path2)
        
        if chosen_start: return True, chosen_start, optimal_path
        return False, None, None

    def handle_route_completion(self, player: Player, chosen_start: Tuple[int, int], optimal_path: List[RouteStep]):
        player.player_state, player.start_terminal_coord, player.validated_route = PlayerState.DRIVING, chosen_start, optimal_path
        player.streetcar_path_index, player.required_node_index = 0, 1 # Start at index 0, aim for node at index 1
        
        print(f"  Player {player.player_id} streetcar placed at: {player.streetcar_position}")
        
        # --- ADDED DEBUG OUTPUT ---
        # Print the full validated route coordinates for clarity.
        print("--- Validated Route Path ---")
        for i, step in enumerate(player.validated_route):
            arr_dir_str = step.arrival_direction.name if step.arrival_direction else "Start"
            goal_marker = "[GOAL]" if step.is_goal_node else ""
            print(f"  Step {i:<2}: {step.coord} (Arrival: {arr_dir_str:<5}) {goal_marker}")
        print("--- End Validated Route ---")
        # --- END ADDED DEBUG OUTPUT ---
        
        if self.game_phase == GamePhase.LAYING_TRACK:
             self.game_phase = GamePhase.DRIVING

    # --- DRIVING PHASE LOGIC (REWRITTEN) ---

    def attempt_driving_move(self, player: Player, roll_result: Any) -> bool:
        """Determines target path index based on the stored validated path and creates a MoveCommand."""
        if player.player_state != PlayerState.DRIVING or not player.validated_route:
            return False
        if self.actions_taken_this_turn > 0: return False

        current_path_idx = player.streetcar_path_index
        
        # Find the index of the next goal node in the validated path
        next_goal_path_idx = -1
        for i in range(current_path_idx + 1, len(player.validated_route)):
            if player.validated_route[i].is_goal_node:
                next_goal_path_idx = i
                break
        
        if next_goal_path_idx == -1: # No more goals left
            self.confirm_turn()
            return True

        distance_to_goal = next_goal_path_idx - current_path_idx
        
        target_path_idx = current_path_idx
        if roll_result == STOP_SYMBOL:
            target_path_idx = next_goal_path_idx
        elif isinstance(roll_result, int):
            if roll_result >= distance_to_goal:
                target_path_idx = next_goal_path_idx
            else:
                target_path_idx = current_path_idx + roll_result
        
        if target_path_idx == current_path_idx:
            print(f"Driving Info: No move for roll {roll_result}. Ending turn.")
            self.actions_taken_this_turn = MAX_PLAYER_ACTIONS
            self.confirm_turn()
            return True

        command = MoveCommand(self, player, target_path_idx)
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
        """
        Finalizes the current player's turn, draws tiles, advances to the next player,
        and posts an event to signal the start of the next turn.
        """
        active_p = self.get_active_player()
        if self.game_phase == GamePhase.GAME_OVER: return False

        if isinstance(active_p, HumanPlayer):
            if active_p.player_state == PlayerState.LAYING_TRACK and self.actions_taken_this_turn < self.MAX_PLAYER_ACTIONS:
                return False

        if active_p.player_state == PlayerState.LAYING_TRACK:
            for _ in range(min(self.HAND_TILE_LIMIT - len(active_p.hand), self.MAX_PLAYER_ACTIONS)):
                self.draw_tile(active_p)
        
        self.active_player_index = (self.active_player_index + 1) % self.num_players
        if self.active_player_index == 0: self.current_turn += 1
        self.actions_taken_this_turn = 0
        self.command_history.clear_redo_history()
        
        next_p = self.get_active_player()
        print(f"\n--- Starting Turn {self.current_turn} for Player {next_p.player_id} ({next_p.player_state.name}) ---")

        if next_p.player_state == PlayerState.LAYING_TRACK:
            is_complete, start, path = self.check_player_route_completion(next_p)
            if is_complete and start and path:
                self.handle_route_completion(next_p, start, path)
        
        # --- THIS IS THE FIX ---
        # Instead of calling the logic directly, post an event.
        # This yields control back to the main loop, allowing a screen update.
        pygame.event.post(pygame.event.Event(START_NEXT_TURN_EVENT))
        # --- END OF FIX ---
        
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
        

    def copy_for_simulation(self) -> 'Game':
        """
        Creates a deep copy of the essential game state for AI planning.
        This is crucial for the AI to simulate its first move and then plan its second.
        """
        # Create a new Game instance without running its full __init__ setup
        sim_game = object.__new__(Game)
        
        # Copy essential attributes
        sim_game.num_players = self.num_players
        sim_game.tile_types = self.tile_types
        sim_game.pathfinder = self.pathfinder
        sim_game.MAX_PLAYER_ACTIONS = self.MAX_PLAYER_ACTIONS
        
        # Deep copy the mutable, important state
        sim_game.board = copy.deepcopy(self.board)
        sim_game.players = copy.deepcopy(self.players)
        
        return sim_game
