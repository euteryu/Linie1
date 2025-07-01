# game_logic/ai_strategy.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, TYPE_CHECKING, Tuple
from itertools import permutations

if TYPE_CHECKING:
    from .game import Game
    from .player import Player, AIPlayer
    from .tile import TileType
    from .player import RouteStep

from .enums import Direction
from .tile import PlacedTile

class AIStrategy(ABC):
    """Abstract base class for all AI difficulty levels (brains)."""
    @abstractmethod
    def plan_turn(self, game: Game, player: AIPlayer) -> List[Dict]:
        """
        Analyzes the game state and returns a list of planned actions.
        An action is a dictionary, e.g., {'type': 'place', 'details': (...), ...}
        """
        pass

# --- EASY AI: The original sequential, greedy planner ---
class EasyStrategy(AIStrategy):
    """A straightforward AI that plans one move at a time."""
    def plan_turn(self, game: Game, player: AIPlayer) -> List[Dict]:
        actions = []
        sim_game = game.copy_for_simulation()
        sim_player = next(p for p in sim_game.players if p.player_id == player.player_id)

        for _ in range(game.MAX_PLAYER_ACTIONS):
            best_move = self._find_best_move_in_state(sim_game, sim_player)
            if best_move:
                actions.append(best_move)
                # Apply the move to the simulation for planning the second action
                action_type, details = best_move['type'], best_move['details']
                tile, orientation, r, c = details
                if action_type == "place":
                    sim_game.board.set_tile(r, c, PlacedTile(tile, orientation))
                    if tile in sim_player.hand: sim_player.hand.remove(tile)
                elif action_type == "exchange":
                    old_tile = sim_game.board.get_tile(r, c)
                    if old_tile and tile in sim_player.hand:
                        sim_player.hand.remove(tile)
                        sim_player.hand.append(old_tile.tile_type)
                        sim_game.board.set_tile(r, c, PlacedTile(tile, orientation))
            else:
                break # No more valid moves found
        return actions

    def _find_best_move_in_state(self, game: Game, player: Player) -> Optional[Dict]:
        """Finds the single best action from the current state."""
        ideal_plan = self._calculate_ideal_route(game, player)
        valid_moves = []

        # Generate all legal moves (place and exchange)
        for tile in set(player.hand): # Use set to avoid re-calculating for duplicate tiles
            for r in range(game.board.rows):
                for c in range(game.board.cols):
                    for o in [0, 90, 180, 270]:
                        # Placements
                        if game.check_placement_validity(tile, o, r, c)[0]:
                            score, breakdown = self._score_move(game, player, ideal_plan, "place", tile, o, r, c)
                            valid_moves.append({'type': 'place', 'details': (tile, o, r, c), 'score': score, 'score_breakdown': breakdown})
                        # Exchanges
                        if game.board.get_tile(r,c) and game.check_exchange_validity(player, tile, o, r, c)[0]:
                            score, breakdown = self._score_move(game, player, ideal_plan, "exchange", tile, o, r, c)
                            valid_moves.append({'type': 'exchange', 'details': (tile, o, r, c), 'score': score, 'score_breakdown': breakdown})
        
        return max(valid_moves, key=lambda m: m['score']) if valid_moves else None
    
    # _calculate_ideal_route and _score_move are moved here from AIPlayer
    def _calculate_ideal_route(self, game: 'Game', player: 'Player') -> Optional[List[RouteStep]]:
        if not player.line_card or not player.route_card: return None
        stops = player.get_required_stop_coords(game)
        if stops is None: return None
        t1, t2 = game.get_terminal_coords(player.line_card.line_number)
        if not t1 or not t2: return None
        
        path1, cost1 = game.pathfinder.find_path(game, player, [t1] + stops + [t2], is_hypothetical=True)
        path2, cost2 = game.pathfinder.find_path(game, player, [t2] + stops + [t1], is_hypothetical=True)
        
        if cost1 == float('inf') and cost2 == float('inf'): return None
        return path1 if cost1 <= cost2 else path2

    def _score_move(self, game: 'Game', player: 'Player', ideal_plan: Optional[List[RouteStep]], move_type: str, tile: TileType, orientation: int, r: int, c: int) -> Tuple[float, Dict[str, float]]:
        score, breakdown = 1.0, {'base': 1.0}
        if ideal_plan:
            for i, step in enumerate(ideal_plan):
                if step.coord == (r, c):
                    path_score = 200.0 - (i * 5); score += path_score; breakdown['ideal_path'] = path_score; break
        if player.route_card:
            for d in Direction:
                b_id = game.board.get_building_at(r + d.value[0], c + d.value[1])
                if b_id and b_id in player.route_card.stops and b_id not in game.board.buildings_with_stops:
                    conns = game.get_effective_connections(tile, orientation)
                    is_parallel = (d in [Direction.N, Direction.S] and game._has_ew_straight(conns)) or \
                                  (d in [Direction.E, Direction.W] and game._has_ns_straight(conns))
                    if is_parallel: score += 150.0; breakdown['stop_creation'] = 150.0
        conn_score = sum(10.0 for d in Direction if game.board.get_tile(r + d.value[0], c + d.value[1]))
        if conn_score > 0: score += conn_score; breakdown['connectivity'] = conn_score
        if move_type == "exchange": score += 5.0; breakdown['exchange_bonus'] = 5.0
        return score, breakdown


# --- HARD AI: The new combinatorial planner ---
class HardStrategy(EasyStrategy):
    """
    A more advanced AI that considers pairs of moves together, allowing it
    to solve complex board situations that the Easy AI cannot see.
    It inherits from EasyStrategy to reuse its scoring and ideal route logic.
    """
    def plan_turn(self, game: Game, player: AIPlayer) -> List[Dict]:
        best_pair_of_actions = []
        best_score = -1

        # Generate all possible pairs of moves from the player's hand
        # This is computationally intensive! We can add optimizations later.
        hand_indices = list(range(len(player.hand)))
        
        # Consider all 2-move combinations
        for hand_idx1, hand_idx2 in permutations(hand_indices, 2):
            tile1, tile2 = player.hand[hand_idx1], player.hand[hand_idx2]
            
            # Iterate through all possible board locations for the pair of moves
            for r1 in range(game.board.rows):
                for c1 in range(game.board.cols):
                    # Check if this is a valid square to interact with
                    if not self._is_interactable(game, r1, c1): continue
                    
                    for r2 in range(game.board.rows):
                        for c2 in range(game.board.cols):
                            if (r1, c1) == (r2, c2): continue # Moves must be on different squares
                            if not self._is_interactable(game, r2, c2): continue
                            
                            # Now we have a pair of tiles and a pair of coordinates.
                            # We need to check if this combination is valid.
                            sim_game = game.copy_for_simulation()
                            sim_player = next(p for p in sim_game.players if p.player_id == player.player_id)
                            
                            # Simulate placing BOTH moves
                            move1 = {'coord': (r1, c1), 'tile_type': tile1, 'orientation': 0} # Assume orientation 0 for now
                            move2 = {'coord': (r2, c2), 'tile_type': tile2, 'orientation': 0}
                            
                            # A simple validity check for the pair
                            is_valid1, _ = sim_game.check_placement_validity(tile1, 0, r1, c1, hypothetical_moves=[move2])
                            is_valid2, _ = sim_game.check_placement_validity(tile2, 0, r2, c2, hypothetical_moves=[move1])

                            if is_valid1 and is_valid2:
                                # This pair is valid! Now score it.
                                # A simple scoring method: score the board state *after* the moves.
                                final_score = self._score_board_state(sim_game, sim_player)
                                if final_score > best_score:
                                    best_score = final_score
                                    # Create the action dictionaries to return
                                    action1 = {'type': 'place', 'details': (tile1, 0, r1, c1), 'score': final_score, 'score_breakdown': {'combo_score': final_score}}
                                    action2 = {'type': 'place', 'details': (tile2, 0, r2, c2), 'score': 0, 'score_breakdown': {}}
                                    best_pair_of_actions = [action1, action2]
        
        # If no valid pair was found, fall back to the Easy strategy
        if not best_pair_of_actions:
            return super().plan_turn(game, player)

        return best_pair_of_actions

    def _is_interactable(self, game: Game, r: int, c: int) -> bool:
        """Helper to check if a square can be part of a move."""
        if not game.board.is_playable_coordinate(r,c): return False
        if game.board.get_building_at(r,c): return False
        tile = game.board.get_tile(r,c)
        if tile and (tile.is_terminal or not tile.tile_type.is_swappable): return False
        return True

    def _score_board_state(self, game: Game, player: Player) -> float:
        """Scores an entire board state, e.g., based on ideal path completion."""
        ideal_plan = self._calculate_ideal_route(game, player)
        if not ideal_plan: return 0.0
        
        score = 0.0
        # Higher score for having more of the ideal path tiles on the board
        for step in ideal_plan:
            if game.board.get_tile(step.coord[0], step.coord[1]):
                score += 100
        return score