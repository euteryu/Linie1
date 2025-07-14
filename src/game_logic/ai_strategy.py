# src/game_logic/ai_strategy.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, TYPE_CHECKING, Tuple, Set
from collections import Counter
import pygame

if TYPE_CHECKING:
    from .game import Game
    from .player import Player, AIPlayer, RouteStep
    from .tile import TileType

from .enums import Direction
from .tile import PlacedTile
from common.constants import KING_AI_TREE_TILE_BIAS, MAX_TARGETS_FOR_COMBO_SEARCH
from .ai_actions import PotentialAction
from .commands import PlaceTileCommand, ExchangeTileCommand

class AIStrategy(ABC):
    """Abstract base class for all AI difficulty levels (brains)."""
    @abstractmethod
    def plan_turn(self, game: Game, player: AIPlayer) -> List[PotentialAction]:
        """Analyzes the game state and returns a list of planned actions."""
        pass

    def _calculate_ideal_route(self, game: 'Game', player: 'Player') -> Optional[List['RouteStep']]:
        """Calculates the theoretical best path for a player."""
        if not player.line_card or not player.route_card: return None
        stops = player.get_required_stop_coords(game)
        if stops is None: return None
        t1, t2 = game.get_terminal_coords(player.line_card.line_number)
        if not t1 or not t2: return None
        path1, cost1 = game.pathfinder.find_path(game, player, [t1] + stops + [t2], is_hypothetical=True)
        path2, cost2 = game.pathfinder.find_path(game, player, [t2] + stops + [t1], is_hypothetical=True)
        if cost1 == float('inf') and cost2 == float('inf'): return None
        return path1 if cost1 <= cost2 else path2
        
    def _gather_standard_actions(self, game: Game, player: AIPlayer, ideal_plan, target_squares: Set[Tuple[int, int]]) -> List[PotentialAction]:
        """Gathers all standard place/exchange moves for a given set of targets."""
        actions = []
        rule_engine = game.rule_engine
        unique_hand_tiles = list(set(player.hand))

        for r, c in target_squares:
            for tile in unique_hand_tiles:
                for o in [0, 90, 180, 270]:
                    if rule_engine.check_placement_validity(game, tile, o, r, c)[0]:
                        score, breakdown = self._score_move(game, player, ideal_plan, 'place', tile, o, r, c)
                        actions.append(PotentialAction(
                            action_type='place',
                            details={'tile': tile, 'orientation': o, 'coord': (r, c)},
                            score=score, score_breakdown=breakdown,
                            command_generator=lambda g, p, t=tile, orient=o, row=r, col=c: PlaceTileCommand(g, p, t, orient, row, col)
                        ))
                    if game.board.get_tile(r,c) and rule_engine.check_exchange_validity(game, player, tile, o, r, c)[0]:
                        score, breakdown = self._score_move(game, player, ideal_plan, 'exchange', tile, o, r, c)
                        actions.append(PotentialAction(
                            action_type='exchange',
                            details={'tile': tile, 'orientation': o, 'coord': (r, c)},
                            score=score, score_breakdown=breakdown,
                            command_generator=lambda g, p, t=tile, orient=o, row=r, col=c: ExchangeTileCommand(g, p, t, orient, row, col)
                        ))
        return actions

    def _score_move(self, game: 'Game', player: 'Player', ideal_plan: Optional[List[RouteStep]], move_type: str, tile: TileType, orientation: int, r: int, c: int) -> Tuple[float, Dict[str, float]]:
        """Scores a single potential move."""
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
        
    def _apply_potential_action_to_sim(self, sim_game, sim_player, action: PotentialAction):
        """Applies any PotentialAction to a simulated game state."""
        d = action.details
        if action.action_type == 'place':
            sim_game.board.set_tile(d['coord'][0], d['coord'][1], PlacedTile(d['tile'], d['orientation']))
            sim_player.hand.remove(d['tile'])
        elif action.action_type == 'exchange':
            old_tile = sim_game.board.get_tile(*d['coord'])
            sim_game.board.set_tile(d['coord'][0], d['coord'][1], PlacedTile(d['tile'], d['orientation']))
            sim_player.hand.remove(d['tile'])
            if old_tile: sim_player.hand.append(old_tile.tile_type)
        elif action.action_type == 'sell_tile':
            if d['tile'] in sim_player.hand: sim_player.hand.remove(d['tile'])
        elif action.action_type == 'priority_requisition':
            sim_player.hand.append(sim_game.tile_types['Curve'])

    def _score_board_state(self, game: Game, player: Player) -> float:
        """Scores the overall quality of the board from the AI's perspective."""
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
                    score += sum(5.0 for d in Direction if game.board.get_tile(r + d.value[0], c + d.value[1]))
                    if tile.tile_type.name.startswith("Tree"): score += 50.0
        return score

class GreedySequentialStrategy(AIStrategy):
    """
    A robust, greedy fallback strategy. It finds the best first move, simulates it,
    then finds the best second move from the new board state. Its only goal is
    to find a valid 2-action turn to avoid forfeiting.
    """
    def plan_turn(self, game: Game, player: AIPlayer) -> List[PotentialAction]:
        print(f"  (Fallback starting... Searching for a greedy sequential plan)")
        ideal_plan = self._calculate_ideal_route(game, player)
        all_playable_squares = {(r, c) for r in range(game.board.rows) for c in range(game.board.cols) if game.board.is_playable_coordinate(r,c)}
        
        # 1. Find the best possible first action
        possible_first_actions = self._gather_standard_actions(game, player, ideal_plan, all_playable_squares)
        if not possible_first_actions:
            print("  (Fallback: No valid first move found.)")
            return []
        best_first_action = max(possible_first_actions, key=lambda a: a.score)
        
        # 2. Simulate the best first action
        sim_game = game.copy_for_simulation()
        sim_player = next(p for p in sim_game.players if p.player_id == player.player_id)
        self._apply_potential_action_to_sim(sim_game, sim_player, best_first_action)

        # 3. From the simulated state, find the best possible second action
        possible_second_actions = self._gather_standard_actions(sim_game, sim_player, ideal_plan, all_playable_squares)
        if not possible_second_actions:
            print("  (Fallback: Found a first move, but no valid second move.)")
            return []
        best_second_action = max(possible_second_actions, key=lambda a: a.score)

        print("  (Fallback: Successfully found a 2-step sequential plan.)")
        return [best_first_action, best_second_action]

class HardStrategy(AIStrategy):
    """An advanced AI that finds the best combination of two actions."""
    
    def plan_turn(self, game: Game, player: AIPlayer) -> List[PotentialAction]:
        print(f"  (HardStrategy starting... Analyzing options)")
        ideal_plan = self._calculate_ideal_route(game, player)
        target_squares = self._get_high_value_target_squares(game, player, ideal_plan)
        if len(target_squares) > MAX_TARGETS_FOR_COMBO_SEARCH:
            target_squares = self._prune_targets(game, player, target_squares, ideal_plan)
        
        one_action_moves = self._gather_standard_actions(game, player, ideal_plan, target_squares)
        
        best_combo_score = -1.0; best_combo_plan = None
        if len(one_action_moves) >= 2:
            sorted_moves = sorted(one_action_moves, key=lambda a: a.score, reverse=True)
            for i in range(len(sorted_moves)):
                for j in range(i + 1, len(sorted_moves)):
                    action1, action2 = sorted_moves[i], sorted_moves[j]
                    if not self._is_combo_compatible(player, action1, action2): continue
                    sim_game, sim_player = game.copy_for_simulation(), next(p for p in game.copy_for_simulation().players if p.player_id == player.player_id)
                    self._apply_potential_action_to_sim(sim_game, sim_player, action1)
                    details2 = action2.details
                    is_valid2 = False
                    if action2.action_type == 'place': is_valid2, _ = sim_game.rule_engine.check_placement_validity(sim_game, details2['tile'], details2['orientation'], *details2['coord'])
                    elif action2.action_type == 'exchange': is_valid2, _ = sim_game.rule_engine.check_exchange_validity(sim_game, sim_player, details2['tile'], details2['orientation'], *details2['coord'])
                    else: is_valid2 = True
                    if not is_valid2: continue
                    self._apply_potential_action_to_sim(sim_game, sim_player, action2)
                    combo_score = self._score_board_state(sim_game, sim_player)
                    if combo_score > best_combo_score: best_combo_score, best_combo_plan = combo_score, [action1, action2]
        if best_combo_plan:
            print(f"  (HardStrategy: Found a valid combo plan with score {best_combo_score:.2f})")
            return best_combo_plan
        print("  (HardStrategy: No valid 2-action plan found.)")
        return []

    def _get_high_value_target_squares(self, game: Game, player: Player, ideal_plan: Optional[List[RouteStep]]) -> Set[Tuple[int, int]]:
        targets: Set[Tuple[int, int]] = set()
        if ideal_plan:
            for step in ideal_plan:
                r, c = step.coord
                if not game.board.get_tile(r, c) and game.board.is_playable_coordinate(r, c): targets.add((r, c))
        if player.route_card:
            for building_id in player.route_card.stops:
                if building_id not in game.board.buildings_with_stops:
                    if building_coord := game.board.building_coords.get(building_id):
                        for d in Direction:
                            nr, nc = building_coord[0] + d.value[0], building_coord[1] + d.value[1]
                            if game.board.is_playable_coordinate(nr, nc) and not game.board.get_tile(nr, nc): targets.add((nr, nc))
        if not targets:
            for r_idx in range(game.board.rows):
                for c_idx in range(game.board.cols):
                    if tile := game.board.get_tile(r_idx, c_idx):
                        conns = game.rule_engine.get_effective_connections(tile.tile_type, tile.orientation)
                        all_exits = {exit_dir for exits in conns.values() for exit_dir in exits}
                        for exit_dir_str in all_exits:
                            exit_dir = Direction.from_str(exit_dir_str)
                            nr, nc = r_idx + exit_dir.value[0], c_idx + exit_dir.value[1]
                            if game.board.is_playable_coordinate(nr, nc) and not game.board.get_tile(nr, nc): targets.add((nr, nc))
        print(f"  (HardStrategy identified {len(targets)} high-value squares)")
        return targets

    def _prune_targets(self, game: Game, player: Player, targets: Set[Tuple[int, int]], ideal_plan: Optional[List[RouteStep]]) -> Set[Tuple[int, int]]:
        next_goal = None
        if ideal_plan:
            for step in ideal_plan:
                if step.is_goal_node and not (game.board.get_tile(*step.coord) and game.board.get_tile(*step.coord).has_stop_sign):
                    next_goal = step.coord; break
        if not next_goal: next_goal = (game.board.rows // 2, game.board.cols // 2)
        scored_targets = sorted([(abs(r - next_goal[0]) + abs(c - next_goal[1]), (r, c)) for r, c in targets])
        pruned_set = {coord for _, coord in scored_targets[:MAX_TARGETS_FOR_COMBO_SEARCH]}
        print(f"  (Pruned {len(targets)} targets down to {len(pruned_set)})")
        return pruned_set

    def _is_combo_compatible(self, player: AIPlayer, action1: PotentialAction, action2: PotentialAction) -> bool:
        coord1, coord2 = action1.details.get('coord'), action2.details.get('coord')
        if coord1 and coord2 and coord1 == coord2: return False
        required_tiles = Counter()
        if tile1 := action1.details.get('tile'): required_tiles[tile1] += 1
        if tile2 := action2.details.get('tile'): required_tiles[tile2] += 1
        player_hand_counts = Counter(player.hand)
        for tile, required_count in required_tiles.items():
            if player_hand_counts[tile] < required_count: return False
        return True