# game_logic/ai_strategy.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, TYPE_CHECKING, Tuple, Set
from itertools import permutations
import random

if TYPE_CHECKING:
    from .game import Game
    from .player import Player, AIPlayer, RouteStep
    from .tile import TileType

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

    def _calculate_ideal_route(self, game: 'Game', player: 'Player') -> Optional[List[RouteStep]]:
        """Calculates the AI's 'wet dream' path assuming infinite tiles."""
        if not player.line_card or not player.route_card: return None
        stops = player.get_required_stop_coords(game)
        if stops is None: return None
        t1, t2 = game.get_terminal_coords(player.line_card.line_number)
        if not t1 or not t2: return None
        
        # Use the game's pathfinder, which is now an object on the game instance
        path1, cost1 = game.pathfinder.find_path(game, player, [t1] + stops + [t2], is_hypothetical=True)
        path2, cost2 = game.pathfinder.find_path(game, player, [t2] + stops + [t1], is_hypothetical=True)
        
        if cost1 == float('inf') and cost2 == float('inf'): return None
        return path1 if cost1 <= cost2 else path2

# --- EASY AI: A reliable sequential, greedy planner ---
class EasyStrategy(AIStrategy):
    """A straightforward AI that plans one move at a time, making locally optimal choices."""
    def plan_turn(self, game: Game, player: AIPlayer) -> List[Dict]:
        actions = []
        # Create a single simulation that will be modified
        sim_game = game.copy_for_simulation()
        sim_player = next(p for p in sim_game.players if p.player_id == player.player_id)

        for _ in range(game.MAX_PLAYER_ACTIONS):
            best_move = self._find_best_single_move(sim_game, sim_player)
            if best_move:
                actions.append(best_move)
                # Apply the chosen move to the simulation to plan the next one accurately
                self._apply_move_to_sim(sim_game, sim_player, best_move)
            else:
                break # No more valid moves found
        return actions

    def _find_best_single_move(self, game: Game, player: Player) -> Optional[Dict]:
        """Finds the single best action from the current state by scoring all valid moves."""
        ideal_plan = self._calculate_ideal_route(game, player)
        valid_moves = []
        
        # Use a set of hand tile names to avoid re-evaluating for duplicate tiles
        unique_hand_tiles = list(set(player.hand))

        for r in range(game.board.rows):
            for c in range(game.board.cols):
                for tile in unique_hand_tiles:
                    for o in [0, 90, 180, 270]:
                        # Placements
                        is_valid_place, _ = game.check_placement_validity(tile, o, r, c)
                        if is_valid_place:
                            score, breakdown = self._score_move(game, player, ideal_plan, "place", tile, o, r, c)
                            valid_moves.append({'type': 'place', 'details': (tile, o, r, c), 'score': score, 'score_breakdown': breakdown})
                        
                        # Exchanges
                        is_valid_exchange, _ = game.check_exchange_validity(player, tile, o, r, c)
                        if is_valid_exchange:
                            score, breakdown = self._score_move(game, player, ideal_plan, "exchange", tile, o, r, c)
                            valid_moves.append({'type': 'exchange', 'details': (tile, o, r, c), 'score': score, 'score_breakdown': breakdown})
        
        return max(valid_moves, key=lambda m: m['score']) if valid_moves else None

    def _apply_move_to_sim(self, sim_game: Game, sim_player: Player, move: Dict):
        """Helper to update a simulated game state with a chosen move."""
        action_type, details = move['type'], move['details']
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
    
    def _score_move(self, game: 'Game', player: 'Player', ideal_plan: Optional[List[RouteStep]], move_type: str, tile: TileType, orientation: int, r: int, c: int) -> Tuple[float, Dict[str, float]]:
        """Scores a pre-validated move based on a weighted heuristic."""
        score, breakdown = 1.0, {'base': 1.0}
        
        if ideal_plan:
            for i, step in enumerate(ideal_plan):
                if step.coord == (r, c):
                    path_score = 200.0 - (i * 5)
                    score += path_score
                    breakdown['ideal_path'] = path_score
                    break
        
        if player.route_card:
            for d in Direction:
                b_id = game.board.get_building_at(r + d.value[0], c + d.value[1])
                if b_id and b_id in player.route_card.stops and b_id not in game.board.buildings_with_stops:
                    conns = game.get_effective_connections(tile, orientation)
                    is_parallel = (d in [Direction.N, Direction.S] and game._has_ew_straight(conns)) or \
                                  (d in [Direction.E, Direction.W] and game._has_ns_straight(conns))
                    if is_parallel:
                        score += 150.0
                        breakdown['stop_creation'] = 150.0
                        
        conn_score = sum(10.0 for d in Direction if game.board.get_tile(r + d.value[0], c + d.value[1]))
        if conn_score > 0:
            score += conn_score
            breakdown['connectivity'] = conn_score
            
        if move_type == "exchange":
            score += 5.0
            breakdown['exchange_bonus'] = 5.0
            
        return score, breakdown


# --- HARD AI: A smarter, multi-pass combinatorial planner ---
class HardStrategy(EasyStrategy):
    """
    An advanced AI that first looks for high-value combination plays.
    If no such play is found, it falls back to the reliable EasyStrategy.
    """
    def plan_turn(self, game: Game, player: AIPlayer) -> List[Dict]:
        print(f"  (HardStrategy starting... Looking for combo plays)")
        
        # --- PLAN A: Find a high-value two-move combination ---
        # 1. Identify a small set of high-value target squares
        ideal_plan = self._calculate_ideal_route(game, player)
        target_squares = self._get_high_value_target_squares(game, player, ideal_plan)
        
        # 2. Get all possible pairs of tiles from hand
        hand_indices = list(range(len(player.hand)))
        if len(hand_indices) < 2:
            print("  (HardStrategy: Not enough tiles for combo. Falling back to Easy.)")
            return super().plan_turn(game, player)

        hand_pairs = list(permutations(hand_indices, 2))
        random.shuffle(hand_pairs) # Prevents deterministic boring plays

        # 3. Iterate through promising pairs and check for valid combos
        for idx1, idx2 in hand_pairs:
            tile1, tile2 = player.hand[idx1], player.hand[idx2]
            
            # Iterate through pairs of target squares
            for r1, c1 in target_squares:
                for r2, c2 in target_squares:
                    if (r1, c1) == (r2, c2): continue

                    # Check all orientations for this specific pair
                    for o1 in [0, 90, 180, 270]:
                        for o2 in [0, 90, 180, 270]:
                            move1 = {'coord': (r1, c1), 'tile_type': tile1, 'orientation': o1}
                            move2 = {'coord': (r2, c2), 'tile_type': tile2, 'orientation': o2}

                            # Check validity of this specific pair
                            is_valid1, _ = game.check_placement_validity(tile1, o1, r1, c1, hypothetical_moves=[move2])
                            if not is_valid1: continue
                            is_valid2, _ = game.check_placement_validity(tile2, o2, r2, c2, hypothetical_moves=[move1])

                            if is_valid1 and is_valid2:
                                # FOUND A VALID COMBO! This is our move.
                                print(f"  (HardStrategy: Found a valid combo play!)")
                                action1 = {'type': 'place', 'details': (tile1, o1, r1, c1)}
                                action2 = {'type': 'place', 'details': (tile2, o2, r2, c2)}
                                return [action1, action2]
        
        # --- PLAN B: If no combo was found, fall back to the standard sequential plan ---
        print("  (HardStrategy: No combo found. Falling back to Easy.)")
        return super().plan_turn(game, player)

    def _get_high_value_target_squares(self, game: Game, player: Player, ideal_plan: Optional[List[RouteStep]]) -> Set[Tuple[int, int]]:
        """Identifies a small set of the most important squares to consider for moves."""
        targets: Set[Tuple[int, int]] = set()
        
        # 1. Add squares from the ideal path that are currently empty
        if ideal_plan:
            for step in ideal_plan:
                r, c = step.coord
                if not game.board.get_tile(r, c) and game.board.is_playable_coordinate(r, c):
                    targets.add((r,c))
        
        # 2. Add squares adjacent to required, un-stopped buildings
        if player.route_card:
            for building_id in player.route_card.stops:
                if building_id not in game.board.buildings_with_stops:
                    building_coord = game.board.building_coords.get(building_id)
                    if building_coord:
                        # Get neighbors of the building
                        for d in Direction:
                            nr, nc = building_coord[0] + d.value[0], building_coord[1] + d.value[1]
                            if game.board.is_playable_coordinate(nr, nc) and not game.board.get_tile(nr, nc):
                                targets.add((nr, nc))
        
        # As a fallback, if no targets are found, add some squares near the player's terminals
        if not targets and player.line_card:
            for term_coord in game.get_terminal_coords(player.line_card.line_number):
                if term_coord:
                    # Look at neighbors of the terminal entry point
                    for d in Direction:
                        nr, nc = term_coord[0] + d.value[0], term_coord[1] + d.value[1]
                        if game.board.is_playable_coordinate(nr, nc) and not game.board.get_tile(nr, nc):
                            targets.add((nr, nc))

        print(f"  (HardStrategy identified {len(targets)} high-value squares)")
        return targets