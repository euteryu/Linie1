# game_logic/pathfinding.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Generator, TYPE_CHECKING
from queue import PriorityQueue
from collections import deque, namedtuple

if TYPE_CHECKING:
    from .game import Game
    from .player import AIPlayer

from .enums import Direction
from .tile import TileType
from .player import RouteStep

PathState = namedtuple('PathState', ['pos', 'arrival_dir', 'seq_idx'])

def _get_valid_successors(game: 'Game', current_state: PathState, goal_node_sequence: List[Tuple[int, int]], previous_target_node: Optional[Tuple[int, int]]) -> Generator[PathState, None, None]:
    """
    Helper generator that yields all valid next states from a given state,
    incorporating all movement rules (U-turns, forced exits from GOAL stops).
    """
    current_pos, arrival_dir, seq_idx = current_state
    
    tile = game.board.get_tile(current_pos[0], current_pos[1])
    if not tile: return

    forced_exit_dir: Optional[Direction] = None
    is_stop = current_pos in game.board.building_stop_locations.values()
    was_the_required_goal = (current_pos == previous_target_node)
    
    # This block now correctly calls the rule engine
    if is_stop and was_the_required_goal and arrival_dir and game.rule_engine.is_valid_stop_entry(game, current_pos, arrival_dir):
        forced_exit_dir = arrival_dir
    
    # --- START OF FIX ---
    # Call get_effective_connections on the rule_engine, not the game object.
    conns = game.rule_engine.get_effective_connections(tile.tile_type, tile.orientation)
    # --- END OF FIX ---
    
    possible_exits: List[Direction] = []
    if forced_exit_dir:
        entry_port = Direction.opposite(arrival_dir).name if arrival_dir else None
        if entry_port and forced_exit_dir.name in conns.get(entry_port, []):
            possible_exits.append(forced_exit_dir)
    else:
        entry_port = Direction.opposite(arrival_dir).name if arrival_dir else None
        exit_strs = conns.get(entry_port, []) if entry_port else list(set(ex for exits in conns.values() for ex in exits))
        possible_exits = [Direction.from_str(s) for s in exit_strs]

    for exit_dir in possible_exits:
        n_pos = (current_pos[0] + exit_dir.value[0], current_pos[1] + exit_dir.value[1])
        if not game.board.is_valid_coordinate(n_pos[0], n_pos[1]): continue
        
        n_tile = game.board.get_tile(n_pos[0], n_pos[1])
        if not n_tile: continue
        
        # --- START OF FIX ---
        n_conns = game.rule_engine.get_effective_connections(n_tile.tile_type, n_tile.orientation)
        # --- END OF FIX ---
        
        req_entry = Direction.opposite(exit_dir).name
        if req_entry not in {ex for n_exits in n_conns.values() for ex in n_exits}: continue

        next_seq_idx = seq_idx
        if seq_idx < len(goal_node_sequence) and n_pos == goal_node_sequence[seq_idx]:
            # --- START OF FIX 3 ---
            # This check also needs to use the rule engine
            if not (n_pos in game.board.building_stop_locations.values()) or game.rule_engine.is_valid_stop_entry(game, n_pos, exit_dir):
                next_seq_idx += 1
            # --- END OF FIX 3 ---
        
        yield PathState(pos=n_pos, arrival_dir=exit_dir, seq_idx=next_seq_idx)

class Pathfinder(ABC):
    @abstractmethod
    def find_path(self, game: 'Game', player: 'Player', node_sequence: List[Tuple[int, int]], is_hypothetical: bool = False) -> Tuple[Optional[List[RouteStep]], int]:
        pass

class AStarPathfinder(Pathfinder):
    """The concrete implementation of the A* algorithm for finding the sequential route."""
    def _heuristic_sequential(self, pos: Tuple[int, int], idx: int, seq: List[Tuple[int, int]]) -> int:
        cost = 0
        if idx < len(seq): cost += abs(pos[0] - seq[idx][0]) + abs(pos[1] - seq[idx][1])
        for i in range(idx, len(seq) - 1): cost += abs(seq[i][0] - seq[i+1][0]) + abs(seq[i][1] - seq[i+1][1])
        return cost

    def find_path(self, game: 'Game', player: 'Player', full_node_sequence: List[Tuple[int, int]], is_hypothetical: bool = False) -> Tuple[Optional[List[RouteStep]], int]:
        start_pos = full_node_sequence[0]
        start_state = PathState(pos=start_pos, arrival_dir=None, seq_idx=1)
        if not game.board.get_tile(start_pos[0], start_pos[1]): return None, float('inf')
        
        open_set = PriorityQueue(); tie_breaker = 0
        f_score = self._heuristic_sequential(start_pos, 1, full_node_sequence)
        open_set.put((f_score, tie_breaker, start_state))
        
        g_scores, came_from = {start_state: 0}, {start_state: None}
        goal_node_coords = set(full_node_sequence)

        while not open_set.empty():
            _, _, current_state = open_set.get()
            if current_state.seq_idx == len(full_node_sequence):
                path: List[RouteStep] = []
                curr = current_state
                while curr:
                    is_goal = curr.pos in goal_node_coords
                    path.append(RouteStep(curr.pos, is_goal, curr.arrival_dir))
                    curr = came_from.get(curr)
                return path[::-1], g_scores[current_state]
            
            previous_target_node = full_node_sequence[current_state.seq_idx - 1] if current_state.seq_idx > 0 else None
            for successor_state in _get_valid_successors(game, current_state, full_node_sequence, previous_target_node):
                new_cost = g_scores[current_state] + 1
                if new_cost < g_scores.get(successor_state, float('inf')):
                    g_scores[successor_state], came_from[successor_state] = new_cost, current_state
                    f_score = new_cost + self._heuristic_sequential(successor_state.pos, successor_state.seq_idx, full_node_sequence)
                    tie_breaker += 1
                    open_set.put((f_score, tie_breaker, successor_state))
        return None, float('inf')

class BFSPathfinder(Pathfinder):
    """Brute-force pathfinder that guarantees the shortest path in number of steps."""
    def find_path(self, game: 'Game', player: 'Player', full_node_sequence: List[Tuple[int, int]], is_hypothetical: bool = False) -> Tuple[Optional[List[RouteStep]], int]:
        start_pos = full_node_sequence[0]
        start_state = PathState(pos=start_pos, arrival_dir=None, seq_idx=1)
        if not game.board.get_tile(start_pos[0], start_pos[1]): return None, float('inf')

        frontier = deque([start_state])
        came_from = {start_state: None}
        cost = {start_state: 0}
        goal_node_coords = set(full_node_sequence)

        while frontier:
            current_state = frontier.popleft()
            if current_state.seq_idx == len(full_node_sequence):
                path: List[RouteStep] = []
                curr = current_state
                while curr:
                    is_goal = curr.pos in goal_node_coords
                    path.append(RouteStep(curr.pos, is_goal, curr.arrival_dir))
                    curr = came_from.get(curr)
                return path[::-1], cost[current_state]
            
            previous_target_node = full_node_sequence[current_state.seq_idx - 1] if current_state.seq_idx > 0 else None
            for successor_state in _get_valid_successors(game, current_state, full_node_sequence, previous_target_node):
                if successor_state not in came_from:
                    came_from[successor_state] = current_state
                    cost[successor_state] = cost[current_state] + 1
                    frontier.append(successor_state)
        return None, float('inf')