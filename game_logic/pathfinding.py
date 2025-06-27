# game_logic/pathfinding.py
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Generator
from queue import PriorityQueue
from collections import deque, namedtuple

# To avoid circular imports for type hinting
if False:
    from .game import Game
    from .player import Player

from .enums import Direction
from .player import RouteStep

PathState = namedtuple('PathState', ['pos', 'arrival_dir', 'seq_idx'])

def _get_valid_successors(game: 'Game', current_state: PathState, goal_node_sequence: List[Tuple[int, int]]) -> Generator[PathState, None, None]:
    """
    Helper generator that yields all valid next states from a given state,
    incorporating all movement rules (U-turns, forced exits from GOAL stops).
    """
    current_pos, arrival_dir, seq_idx = current_state
    
    tile = game.board.get_tile(current_pos[0], current_pos[1])
    if not tile: return

    # --- CORRECTED LOGIC FOR FORCED EXIT ---
    forced_exit_dir: Optional[Direction] = None
    
    # We only apply the "forced straight-through" rule if:
    # 1. We are currently at a tile that IS the player's next required goal (checked by seq_idx).
    # 2. That tile is indeed a stop tile (has a red dot).
    # 3. We entered that stop tile validly in the previous step (arrival_dir is valid and consistent).
    
    is_current_tile_a_stop = current_pos in game.board.building_stop_locations.values()
    
    # Check if the current position is the actual GOAL for the current sequence index.
    is_current_pos_the_goal = (seq_idx < len(goal_node_sequence) and current_pos == goal_node_sequence[seq_idx])
    
    if is_current_tile_a_stop and is_current_pos_the_goal and arrival_dir and game._is_valid_stop_entry(current_pos, arrival_dir):
        # If all conditions met, the forced exit is the direction of arrival.
        forced_exit_dir = arrival_dir
        print(f"  (Constraint: Leaving GOAL stop {current_pos}, must exit via {forced_exit_dir.name})")
    # --- END CORRECTED LOGIC ---
    
    conns = game.get_effective_connections(tile.tile_type, tile.orientation)
    
    possible_exits: List[Direction] = []
    if forced_exit_dir:
        entry_port = Direction.opposite(arrival_dir).name if arrival_dir else None
        if entry_port and forced_exit_dir.name in conns.get(entry_port, []):
            possible_exits.append(forced_exit_dir)
    else:
        # Standard logic for non-goal stops, regular tiles, or start terminal.
        entry_port = Direction.opposite(arrival_dir).name if arrival_dir else None
        exit_strs = conns.get(entry_port, []) if entry_port else list(set(ex for exits in conns.values() for ex in exits))
        possible_exits = [Direction.from_str(s) for s in exit_strs]

    for exit_dir in possible_exits:
        n_pos = (current_pos[0] + exit_dir.value[0], current_pos[1] + exit_dir.value[1])
        if not game.board.is_valid_coordinate(n_pos[0], n_pos[1]): continue
        n_tile = game.board.get_tile(n_pos[0], n_pos[1])
        if not n_tile: continue
        n_conns = game.get_effective_connections(n_tile.tile_type, n_tile.orientation)
        req_entry = Direction.opposite(exit_dir).name
        if req_entry not in {ex for n_exits in n_conns.values() for ex in n_exits}: continue

        next_seq_idx = seq_idx
        if seq_idx < len(goal_node_sequence) and n_pos == goal_node_sequence[seq_idx]:
            if not (n_pos in game.board.building_stop_locations.values()) or game._is_valid_stop_entry(n_pos, exit_dir):
                next_seq_idx += 1
        
        yield PathState(pos=n_pos, arrival_dir=exit_dir, seq_idx=next_seq_idx)

class Pathfinder(ABC):
    @abstractmethod
    def find_path(self, game: 'Game', player: 'Player', node_sequence: List[Tuple[int, int]]) -> Tuple[Optional[List[RouteStep]], int]:
        pass

class AStarPathfinder(Pathfinder):
    def _heuristic(self, pos: Tuple[int, int], idx: int, seq: List[Tuple[int, int]]) -> int:
        cost = 0
        if idx < len(seq): cost += abs(pos[0] - seq[idx][0]) + abs(pos[1] - seq[idx][1])
        for i in range(idx, len(seq) - 1): cost += abs(seq[i][0] - seq[i+1][0]) + abs(seq[i][1] - seq[i+1][1])
        return cost

    def find_path(self, game: 'Game', player: 'Player', full_node_sequence: List[Tuple[int, int]]) -> Tuple[Optional[List[RouteStep]], int]:
        start_pos = full_node_sequence[0]
        start_state = PathState(pos=start_pos, arrival_dir=None, seq_idx=1)
        if not game.board.get_tile(start_pos[0], start_pos[1]): return None, float('inf')
        
        open_set = PriorityQueue(); tie_breaker = 0
        open_set.put((self._heuristic(start_pos, 1, full_node_sequence), tie_breaker, start_state))
        g_scores, came_from = {start_state: 0}, {start_state: None}

        while not open_set.empty():
            _, _, current_state = open_set.get()
            if current_state.seq_idx == len(full_node_sequence):
                # Path reconstruction logic is identical for all pathfinders
                path: List[RouteStep] = []
                curr = current_state
                while curr:
                    is_goal = curr.pos in full_node_sequence
                    path.append(RouteStep(curr.pos, is_goal, curr.arrival_dir))
                    curr = came_from.get(curr)
                return path[::-1], g_scores[current_state]

            for successor_state in _get_valid_successors(game, current_state, full_node_sequence):
                new_cost = g_scores[current_state] + 1
                if new_cost < g_scores.get(successor_state, float('inf')):
                    g_scores[successor_state], came_from[successor_state] = new_cost, current_state
                    f_score = new_cost + self._heuristic(successor_state.pos, successor_state.seq_idx, full_node_sequence)
                    tie_breaker += 1
                    open_set.put((f_score, tie_breaker, successor_state))
        return None, float('inf')

class BFSPathfinder(Pathfinder):
    def find_path(self, game: 'Game', player: 'Player', full_node_sequence: List[Tuple[int, int]]) -> Tuple[Optional[List[RouteStep]], int]:
        start_pos = full_node_sequence[0]
        start_state = PathState(pos=start_pos, arrival_dir=None, seq_idx=1)
        if not game.board.get_tile(start_pos[0], start_pos[1]): return None, float('inf')

        frontier = deque([start_state])
        came_from = {start_state: None}
        cost = {start_state: 0}

        while frontier:
            current_state = frontier.popleft()
            if current_state.seq_idx == len(full_node_sequence):
                path: List[RouteStep] = []
                curr = current_state
                while curr:
                    is_goal = curr.pos in full_node_sequence
                    path.append(RouteStep(curr.pos, is_goal, curr.arrival_dir))
                    curr = came_from.get(curr)
                return path[::-1], cost[current_state]
            
            for successor_state in _get_valid_successors(game, current_state, full_node_sequence):
                if successor_state not in came_from:
                    came_from[successor_state] = current_state
                    cost[successor_state] = cost[current_state] + 1
                    frontier.append(successor_state)
        return None, float('inf')