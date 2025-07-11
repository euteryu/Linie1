# game_logic/ai_strategy.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, TYPE_CHECKING, Tuple, Set
from itertools import permutations
import random
from collections import Counter
import pygame

if TYPE_CHECKING:
    from .game import Game
    from .player import Player, AIPlayer, RouteStep
    from .tile import TileType

from .enums import Direction
from .tile import PlacedTile
from common.constants import KING_AI_TREE_TILE_BIAS, MAX_TARGETS_FOR_COMBO_SEARCH

class AIStrategy(ABC):
    """Abstract base class for all AI difficulty levels (brains)."""
    @abstractmethod
    def plan_turn(self, game: Game, player: AIPlayer) -> List[Dict]:
        """Analyzes the game state and returns a list of planned actions."""
        pass

    @abstractmethod
    def _calculate_ideal_route(self, game: 'Game', player: 'Player') -> Optional[List['RouteStep']]:
        """Calculates the theoretical best path for a player."""
        pass


class EasyStrategy(AIStrategy):
    """A greedy AI that finds the best single move sequentially."""
    def _calculate_ideal_route(self, game: 'Game', player: 'Player') -> Optional[List['RouteStep']]:
        if not player.line_card or not player.route_card: return None
        stops = player.get_required_stop_coords(game)
        if stops is None: return None
        t1, t2 = game.get_terminal_coords(player.line_card.line_number)
        if not t1 or not t2: return None
        path1, cost1 = game.pathfinder.find_path(game, player, [t1] + stops + [t2], is_hypothetical=True)
        path2, cost2 = game.pathfinder.find_path(game, player, [t2] + stops + [t1], is_hypothetical=True)
        if cost1 == float('inf') and cost2 == float('inf'): return None
        return path1 if cost1 <= cost2 else path2

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
        
        # --- START OF FIX ---
        # The AI needs to use the rule engine for checks, not the game object.
        rule_engine = game.rule_engine
        # --- END OF FIX ---

        for r in range(game.board.rows):
            for c in range(game.board.cols):
                for tile in unique_hand_tiles:
                    for o in [0, 90, 180, 270]:
                        if rule_engine.check_placement_validity(game, tile, o, r, c)[0]:
                            score, breakdown = self._score_move(game, player, ideal_plan, "place", tile, o, r, c)
                            valid_moves.append({'type': 'place', 'details': (tile, o, r, c), 'score': score, 'score_breakdown': breakdown})
                        
                        if rule_engine.check_exchange_validity(game, player, tile, o, r, c)[0]:
                            score, breakdown = self._score_move(game, player, ideal_plan, "exchange", tile, o, r, c)
                            valid_moves.append({'type': 'exchange', 'details': (tile, o, r, c), 'score': score, 'score_breakdown': breakdown})
        
        return max(valid_moves, key=lambda m: m['score']) if valid_moves else None

    def _apply_move_to_sim(self, sim_game: Game, sim_player: Player, move: Dict):
        action_type = move.get('type')
        details = move.get('details')
        if not action_type or not details:
             tile, orientation, r, c = move['tile_type'], move['orientation'], move['coord'][0], move['coord'][1]
        else:
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
        score, breakdown = 1.0, {'base': 1.0}
        if ideal_plan:
            for i, step in enumerate(ideal_plan):
                if step.coord == (r, c):
                    score += 200.0 - (i * 5)
                    breakdown['ideal_path'] = 200.0 - (i * 5)
                    break
        if player.route_card:
            for d in Direction:
                b_id = game.board.get_building_at(r + d.value[0], c + d.value[1])
                if b_id and b_id in player.route_card.stops and b_id not in game.board.buildings_with_stops:
                    conns = game.rule_engine.get_effective_connections(tile, orientation)
                    is_parallel = (d in [Direction.N, Direction.S] and 'S' in conns.get('N',[])) or \
                                  (d in [Direction.E, Direction.W] and 'W' in conns.get('E',[]))
                    if is_parallel:
                        score += 150.0
                        breakdown['stop_creation'] = 150.0
                        break
        conn_score = sum(10.0 for d in Direction if game.board.get_tile(r + d.value[0], c + d.value[1]))
        if conn_score > 0: score += conn_score; breakdown['connectivity'] = conn_score
        if move_type == "exchange": score += 5.0; breakdown['exchange_bonus'] = 5.0
        return score, breakdown

class HardStrategy(EasyStrategy):
    """
    An advanced AI that prunes a large set of possible moves down to the most
    promising, then runs a combinatorial search on that small subset.
    """
    def plan_turn(self, game: Game, player: AIPlayer) -> List[Dict]:
        print(f"  (HardStrategy starting... Looking for combo plays)")
        ideal_plan = self._calculate_ideal_route(game, player)
        target_squares = self._get_high_value_target_squares(game, player, ideal_plan)
        
        if len(target_squares) > MAX_TARGETS_FOR_COMBO_SEARCH:
            target_squares = self._prune_targets(game, player, target_squares, ideal_plan)
        
        if hasattr(game, 'visualizer') and game.visualizer and game.visualizer.show_ai_heatmap:
            game.visualizer.heatmap_data = target_squares
            game.visualizer.force_redraw(f"AI targeting {len(target_squares)} squares...")
            pygame.time.delay(1500)

        # --- START OF FIX ---
        rule_engine = game.rule_engine
        # --- END OF FIX ---
        
        possible_moves_for_targets = []
        unique_hand_tiles = list(set(player.hand))

        for r, c in target_squares:
            for tile in unique_hand_tiles:
                for o in [0, 90, 180, 270]:
                    if rule_engine.check_placement_validity(game, tile, o, r, c)[0]:
                        possible_moves_for_targets.append({'type': 'place', 'coord': (r, c), 'tile_type': tile, 'orientation': o})
                    if game.board.get_tile(r,c) and rule_engine.check_exchange_validity(game, player, tile, o, r, c)[0]:
                         possible_moves_for_targets.append({'type': 'exchange', 'coord': (r,c), 'tile_type': tile, 'orientation': o})

        if len(possible_moves_for_targets) < 2:
            print("  (HardStrategy: Not enough valid single moves for a combo. Falling back to Easy.)")
            return super().plan_turn(game, player)

        best_combo_score = -1.0
        best_combo_actions = None
        
        for i in range(len(possible_moves_for_targets)):
            for j in range(i + 1, len(possible_moves_for_targets)):
                move1, move2 = possible_moves_for_targets[i], possible_moves_for_targets[j]
                if move1['coord'] == move2['coord']: continue
                required_tiles = Counter([move1['tile_type'], move2['tile_type']])
                if any(count > Counter(player.hand)[tile] for tile, count in required_tiles.items()): continue

                is_valid1, _ = (rule_engine.check_placement_validity(game, move1['tile_type'], move1['orientation'], *move1['coord'], [move2]) if move1['type'] == 'place'
                                else rule_engine.check_exchange_validity(game, player, move1['tile_type'], move1['orientation'], *move1['coord'], [move2]))
                if not is_valid1: continue

                is_valid2, _ = (rule_engine.check_placement_validity(game, move2['tile_type'], move2['orientation'], *move2['coord'], [move1]) if move2['type'] == 'place'
                                else rule_engine.check_exchange_validity(game, player, move2['tile_type'], move2['orientation'], *move2['coord'], [move1]))

                if is_valid1 and is_valid2:
                    sim_game = game.copy_for_simulation()
                    sim_player = next(p for p in sim_game.players if p.player_id == player.player_id)
                    self._apply_move_to_sim(sim_game, sim_player, move1)
                    self._apply_move_to_sim(sim_game, sim_player, move2)
                    score = self._score_board_state(sim_game, sim_player)
                    if score > best_combo_score:
                        best_combo_score = score
                        action1 = {'type': move1['type'], 'details': (move1['tile_type'], move1['orientation'], *move1['coord']), 'score': score, 'score_breakdown': {'combo': score}}
                        action2 = {'type': move2['type'], 'details': (move2['tile_type'], move2['orientation'], *move2['coord']), 'score': 0, 'score_breakdown': {}}
                        best_combo_actions = [action1, action2]

        if best_combo_actions:
            print("  (HardStrategy: Found a valid combo play!)")
            return best_combo_actions

        print("  (HardStrategy: No valid combo found. Falling back to Easy.)")
        return super().plan_turn(game, player)

    def _prune_targets(self, game: Game, player: Player, targets: Set[Tuple[int, int]], ideal_plan: Optional[List[RouteStep]]) -> Set[Tuple[int, int]]:
        next_goal = None
        if ideal_plan:
            for step in ideal_plan:
                if step.is_goal_node:
                    tile = game.board.get_tile(*step.coord)
                    if not (tile and tile.has_stop_sign):
                        next_goal = step.coord
                        break
        if not next_goal: next_goal = (game.board.rows // 2, game.board.cols // 2)
        scored_targets = sorted([(abs(r - next_goal[0]) + abs(c - next_goal[1]), (r, c)) for r, c in targets])
        return {coord for _, coord in scored_targets[:MAX_TARGETS_FOR_COMBO_SEARCH]}

    def _get_high_value_target_squares(self, game: Game, player: Player, ideal_plan: Optional[List[RouteStep]]) -> Set[Tuple[int, int]]:
        targets: Set[Tuple[int, int]] = set()
        if ideal_plan:
            for step in ideal_plan:
                r, c = step.coord
                if not game.board.get_tile(r, c) and game.board.is_playable_coordinate(r, c):
                    targets.add((r, c))
        if player.route_card:
            for building_id in player.route_card.stops:
                if building_id not in game.board.buildings_with_stops:
                    if building_coord := game.board.building_coords.get(building_id):
                        for d in Direction:
                            nr, nc = building_coord[0] + d.value[0], building_coord[1] + d.value[1]
                            if game.board.is_playable_coordinate(nr, nc) and not game.board.get_tile(nr, nc):
                                targets.add((nr, nc))
        if not targets:
            print("  (Fallback: Looking for open track ends to extend...)")
            for r_idx in range(game.board.rows):
                for c_idx in range(game.board.cols):
                    if tile := game.board.get_tile(r_idx, c_idx):
                        conns = game.rule_engine.get_effective_connections(tile.tile_type, tile.orientation)
                        all_exits = {exit for exits in conns.values() for exit in exits}
                        for exit_dir_str in all_exits:
                            exit_dir = Direction.from_str(exit_dir_str)
                            nr, nc = r_idx + exit_dir.value[0], c_idx + exit_dir.value[1]
                            if game.board.is_playable_coordinate(nr, nc) and not game.board.get_tile(nr, nc):
                                targets.add((nr, nc))
        print(f"  (HardStrategy identified {len(targets)} high-value squares)")
        return targets
    
    def _score_board_state(self, game: Game, player: Player) -> float:
        score = 0.0
        ideal_plan = self._calculate_ideal_route(game, player)
        if ideal_plan:
            for i, step in enumerate(ideal_plan):
                if tile := game.board.get_tile(step.coord[0], step.coord[1]):
                    score += 100.0 - (i * 2)
                    if step.is_goal_node and tile.has_stop_sign: score += 200.0
        for r in range(game.board.rows):
            for c in range(game.board.cols):
                if tile := game.board.get_tile(r, c):
                    score += sum(10.0 for d in Direction if game.board.get_tile(r + d.value[0], c + d.value[1]))
                    if tile.tile_type.name.startswith("Tree"): score += 50.0
        return score