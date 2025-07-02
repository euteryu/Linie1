# game_logic/ai_strategy.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, TYPE_CHECKING, Tuple, Set
from itertools import permutations
import random
from collections import Counter

if TYPE_CHECKING:
    from .game import Game
    from .player import Player, AIPlayer, RouteStep
    from .tile import TileType

from .enums import Direction
from .tile import PlacedTile
from constants import KING_AI_TREE_TILE_BIAS

class AIStrategy(ABC):
    # ... (AIStrategy base class is correct) ...
    pass

# --- EASY AI: A reliable sequential, greedy planner ---
class EasyStrategy(AIStrategy):
    # ... (plan_turn, _find_best_single_move, _calculate_ideal_route are correct) ...
    def plan_turn(self, game: Game, player: AIPlayer) -> List[Dict]:
        actions = []
        sim_game = game.copy_for_simulation()
        sim_player = next(p for p in sim_game.players if p.player_id == player.player_id)

        for _ in range(game.MAX_PLAYER_ACTIONS):
            best_move = self._find_best_single_move(sim_game, sim_player)
            if best_move:
                actions.append(best_move)
                self._apply_move_to_sim(sim_game, sim_player, best_move)
            else:
                break
        return actions

    def _find_best_single_move(self, game: Game, player: Player) -> Optional[Dict]:
        ideal_plan = self._calculate_ideal_route(game, player)
        valid_moves = []
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

    # _calculate_ideal_route is correctly inherited from AIStrategy or defined here
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

    def _apply_move_to_sim(self, sim_game: Game, sim_player: Player, move: Dict):
        """
        Helper to update a simulated game state with a chosen move.
        This method is now robust and can handle both the 'nested' structure from
        EasyStrategy and the 'flat' structure used internally by HardStrategy.
        """
        action_type = move['type']
        
        # Check if the move has a 'details' key (from EasyStrategy)
        if 'details' in move:
            tile, orientation, r, c = move['details']
        else: # Otherwise, it's a flat structure (from HardStrategy)
            tile = move['tile_type']
            orientation = move['orientation']
            r, c = move['coord']
        
        if action_type == "place":
            sim_game.board.set_tile(r, c, PlacedTile(tile, orientation))
            # Be careful with object identity when removing from hand
            if tile in sim_player.hand:
                sim_player.hand.remove(tile)
        elif action_type == "exchange":
            old_tile = sim_game.board.get_tile(r, c)
            if old_tile and tile in sim_player.hand:
                sim_player.hand.remove(tile)
                sim_player.hand.append(old_tile.tile_type)
                sim_game.board.set_tile(r, c, PlacedTile(tile, orientation))

    def _score_move(self, game: 'Game', player: 'Player', ideal_plan: Optional[List[RouteStep]], move_type: str, tile: TileType, orientation: int, r: int, c: int) -> Tuple[float, Dict[str, float]]:
        # This method is correct and does not need changes.
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



# --- HARD AI: The new combinatorial planner ---
class HardStrategy(EasyStrategy):
    """
    An advanced AI that first identifies high-value squares, then attempts
    to find the best pair of moves within that limited subset.
    Falls back to EasyStrategy if no good combinations are found.
    """
    def plan_turn(self, game: Game, player: AIPlayer) -> List[Dict]:
        print(f"  (HardStrategy starting... Looking for combo plays)")
        
        ideal_plan = self._calculate_ideal_route(game, player)
        target_squares = self._get_high_value_target_squares(game, player, ideal_plan)
        
        if not target_squares:
            print("  (HardStrategy: No target squares identified. Falling back to Easy.)")
            return super().plan_turn(game, player)

        # Get all unique tile types in hand and their available orientations
        # --- THIS IS THE FIX: The dictionary was incorrectly named in the check ---
        hand_options_by_tile = {}
        for tile in player.hand:
            # Check against the dictionary we are building, not the tile object
            if tile.name not in hand_options_by_tile:
                hand_options_by_tile[tile.name] = {
                    'tile_type': tile,
                    'orientations': [0, 90, 180, 270]
                }
        # --- END OF FIX ---
        
        # Generate all possible individual moves based on targets and available tiles/orientations
        possible_moves_for_targets = []
        for r, c in target_squares:
            # --- THIS IS THE FIX: Iterate over the correctly named dictionary ---
            for tile_name, options in hand_options_by_tile.items():
            # --- END OF FIX ---
                tile = options['tile_type']
                for o in options['orientations']:
                    # Check placement validity
                    is_valid_place, _ = game.check_placement_validity(tile, o, r, c)
                    if is_valid_place:
                        possible_moves_for_targets.append({
                            'type': 'place', 'coord': (r, c), 'tile_type': tile,
                            'orientation': o, 'is_valid': True
                        })
                    # Check exchange validity
                    if game.board.get_tile(r,c) and game.check_exchange_validity(player, tile, o, r, c):
                         possible_moves_for_targets.append({
                            'type': 'exchange', 'coord': (r,c), 'tile_type': tile,
                            'orientation': o, 'is_valid': True
                        })
        
        if len(possible_moves_for_targets) < 2:
            print("  (HardStrategy: Not enough valid single moves to form a pair. Falling back to Easy.)")
            return super().plan_turn(game, player)

        best_combo_score = -1.0
        best_combo_actions = None

        # Iterate through all unique pairs of possible moves.
        for i in range(len(possible_moves_for_targets)):
            for j in range(i + 1, len(possible_moves_for_targets)):
                move1 = possible_moves_for_targets[i]
                move2 = possible_moves_for_targets[j]

                if move1['coord'] == move2['coord']: continue

                # Check hand availability for the pair
                required_tiles = Counter()
                required_tiles[move1['tile_type']] += 1
                required_tiles[move2['tile_type']] += 1
                
                player_hand_counts = Counter(player.hand)
                
                hand_available = True
                for tile, count_needed in required_tiles.items():
                    if player_hand_counts.get(tile, 0) < count_needed:
                        hand_available = False
                        break
                if not hand_available: continue

                # Interdependent Validation
                is_valid1 = False
                if move1['type'] == 'place':
                    is_valid1, _ = game.check_placement_validity(move1['tile_type'], move1['orientation'], *move1['coord'], hypothetical_moves=[move2])
                else: # exchange
                    is_valid1, _ = game.check_exchange_validity(player, move1['tile_type'], move1['orientation'], *move1['coord'], hypothetical_moves=[move2])
                
                if not is_valid1: continue
                
                is_valid2 = False
                if move2['type'] == 'place':
                    is_valid2, _ = game.check_placement_validity(move2['tile_type'], move2['orientation'], *move2['coord'], hypothetical_moves=[move1])
                else: # exchange
                    is_valid2, _ = game.check_exchange_validity(player, move2['tile_type'], move2['orientation'], *move2['coord'], hypothetical_moves=[move1])
                
                if is_valid1 and is_valid2:
                    # Valid combo found! Score it.
                    sim_game_for_scoring = game.copy_for_simulation()
                    sim_player_for_scoring = next(p for p in sim_game_for_scoring.players if p.player_id == player.player_id)
                    
                    self._apply_move_to_sim(sim_game_for_scoring, sim_player_for_scoring, move1)
                    self._apply_move_to_sim(sim_game_for_scoring, sim_player_for_scoring, move2)
                    
                    current_combo_score = self._score_board_state(sim_game_for_scoring, sim_player_for_scoring)
                    
                    if current_combo_score > best_combo_score:
                        best_combo_score = current_combo_score
                        action1 = {'type': move1['type'], 'details': (move1['tile_type'], move1['orientation'], *move1['coord']), 'score': current_combo_score, 'score_breakdown': {'combo': current_combo_score}}
                        action2 = {'type': move2['type'], 'details': (move2['tile_type'], move2['orientation'], *move2['coord']), 'score': 0, 'score_breakdown': {}}
                        best_combo_actions = [action1, action2]

        if best_combo_actions:
            print("  (HardStrategy: Found a valid combo play!)")
            return best_combo_actions

        print("  (HardStrategy: No valid combo found. Falling back to Easy.)")
        return super().plan_turn(game, player)

    def _get_high_value_target_squares(self, game: Game, player: Player, ideal_plan: Optional[List[RouteStep]]) -> Set[Tuple[int, int]]:
        """
        Identifies a small set of the most important squares to consider for moves.
        This is crucial for making Hard AI efficient and preventing combinatorial explosion.
        """
        targets: Set[Tuple[int, int]] = set()
        
        # 1. Add squares from the ideal path that are currently empty on the REAL board.
        if ideal_plan:
            for step in ideal_plan:
                r, c = step.coord
                if not game.board.get_tile(r, c) and game.board.is_playable_coordinate(r, c):
                    targets.add((r,c))
        
        # 2. Add squares adjacent to required, un-stopped buildings.
        if player.route_card:
            for building_id in player.route_card.stops:
                if building_id not in game.board.buildings_with_stops:
                    # --- This was a bug in previous version, it should check building_coords ---
                    building_coord = game.board.building_coords.get(building_id)
                    if building_coord:
                        for d in Direction:
                            nr, nc = building_coord[0] + d.value[0], building_coord[1] + d.value[1]
                            if game.board.is_playable_coordinate(nr, nc) and not game.board.get_tile(nr, nc):
                                targets.add((nr, nc))
        
        # 3. Add squares adjacent to terminals as a fallback.
        if player.line_card:
            for term_coord in game.get_terminal_coords(player.line_card.line_number):
                if term_coord:
                    for d in Direction:
                        nr, nc = term_coord[0] + d.value[0], term_coord[1] + d.value[1]
                        # --- THIS IS THE FIX ---
                        # Corrected from game.game.board to game.board
                        if game.board.is_playable_coordinate(nr, nc) and not game.board.get_tile(nr, nc):
                            targets.add((nr, nc))
                        # --- END OF FIX ---

        # 4. If no strategic squares are found, add a few central fallback squares.
        if not targets:
            center_r, center_c = game.board.rows // 2, game.board.cols // 2
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    nr, nc = center_r + dr, center_c + dc
                    if game.board.is_playable_coordinate(nr, nc) and not game.board.get_tile(nr, nc):
                        targets.add((nr, nc))
        
        print(f"  (HardStrategy identified {len(targets)} high-value squares)")
        return targets
    
    def _score_board_state(self, game: Game, player: Player) -> float:
        score = 0.0
        ideal_plan = self._calculate_ideal_route(game, player)
        if ideal_plan:
            for i, step in enumerate(ideal_plan):
                if game.board.get_tile(step.coord[0], step.coord[1]): score += 100.0 - (i * 2)
                if step.is_goal_node:
                     if game.board.get_tile(step.coord[0], step.coord[1]) and game.board.get_tile(step.coord[0], step.coord[1]).has_stop_sign: score += 200.0
        for r in range(game.board.rows):
            for c in range(game.board.cols):
                tile = game.board.get_tile(r, c)
                if tile:
                    score += sum(10.0 for d in Direction if game.board.get_tile(r + d.value[0], c + d.value[1]))
                    if tile.tile_type.name.startswith("Tree"): score += 50.0
        return score