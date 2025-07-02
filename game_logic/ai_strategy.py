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
from constants import KING_AI_TREE_TILE_BIAS, MAX_TARGETS_FOR_COMBO_SEARCH


class AIStrategy(ABC):
    """Abstract base class for all AI difficulty levels (brains)."""
    @abstractmethod
    def plan_turn(self, game: Game, player: AIPlayer) -> List[Dict]:
        """
        Analyzes the game state and returns a list of planned actions.
        An action is a dictionary, e.g., {'type': 'place', 'details': (...), ...}
        """
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
    An advanced AI that prunes a large set of possible moves down to the most
    promising, then runs a combinatorial search on that small subset.
    """
    def plan_turn(self, game: Game, player: AIPlayer) -> List[Dict]:
        print(f"  (HardStrategy starting... Looking for combo plays)")
        
        ideal_plan = self._calculate_ideal_route(game, player)
        target_squares = self._get_high_value_target_squares(game, player, ideal_plan)
        
        if len(target_squares) > MAX_TARGETS_FOR_COMBO_SEARCH:
            target_squares = self._prune_targets(game, player, target_squares, ideal_plan)
        
        # --- Heatmap Display Logic ---
        # If the visualizer is attached to the game object and the heatmap is on...
        if hasattr(game, 'visualizer') and game.visualizer and game.visualizer.show_ai_heatmap:
            # Update the visualizer's data with the squares we're about to process.
            game.visualizer.heatmap_data = target_squares
            # Force the screen to redraw with the heatmap highlights.
            game.visualizer.force_redraw(f"AI targeting {len(target_squares)} squares...")
            # Pause the game logic briefly so the human can see the heatmap.
            pygame.time.delay(1500) # 1.5 second delay
        
        # --- This section was missing, causing the NameError ---
        # Generate all possible individual moves based on targets and available tiles/orientations
        possible_moves_for_targets = []
        unique_hand_tiles = list(set(player.hand))

        for r, c in target_squares:
            for tile in unique_hand_tiles:
                for o in [0, 90, 180, 270]:
                    # Check placement validity
                    if game.check_placement_validity(tile, o, r, c)[0]:
                        possible_moves_for_targets.append({'type': 'place', 'coord': (r, c), 'tile_type': tile, 'orientation': o})
                    # Check exchange validity
                    if game.board.get_tile(r,c) and game.check_exchange_validity(player, tile, o, r, c)[0]:
                         possible_moves_for_targets.append({'type': 'exchange', 'coord': (r,c), 'tile_type': tile, 'orientation': o})
        # --- End of missing section ---

        if len(possible_moves_for_targets) < 2:
            print("  (HardStrategy: Not enough valid single moves to form a pair. Falling back to Easy.)")
            return super().plan_turn(game, player)

        best_combo_score = -1.0
        best_combo_actions = None

        # The rest of the combinatorial search logic is correct.
        # It iterates through the now-defined `possible_moves_for_targets`.
        for i in range(len(possible_moves_for_targets)):
            for j in range(i + 1, len(possible_moves_for_targets)):
                move1 = possible_moves_for_targets[i]
                move2 = possible_moves_for_targets[j]

                if move1['coord'] == move2['coord']: continue

                required_tiles = Counter([move1['tile_type'], move2['tile_type']])
                if any(count > Counter(player.hand)[tile] for tile, count in required_tiles.items()):
                    continue

                is_valid1, _ = (game.check_placement_validity(move1['tile_type'], move1['orientation'], *move1['coord'], [move2]) if move1['type'] == 'place'
                                else game.check_exchange_validity(player, move1['tile_type'], move1['orientation'], *move1['coord'], [move2]))
                if not is_valid1: continue

                is_valid2, _ = (game.check_placement_validity(move2['tile_type'], move2['orientation'], *move2['coord'], [move1]) if move2['type'] == 'place'
                                else game.check_exchange_validity(player, move2['tile_type'], move2['orientation'], *move2['coord'], [move1]))

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

    # --- NEW METHOD for pruning targets ---
    def _prune_targets(self, game: Game, player: Player, targets: Set[Tuple[int, int]], ideal_plan: Optional[List[RouteStep]]) -> Set[Tuple[int, int]]:
        """Scores and sorts a large set of targets, returning only the best ones."""
        # Find the player's *next* required stop to aim for.
        next_goal = None
        if ideal_plan:
            for step in ideal_plan:
                # Find the first goal node that isn't already on the board with a stop sign
                if step.is_goal_node:
                    tile = game.board.get_tile(*step.coord)
                    if not (tile and tile.has_stop_sign):
                        next_goal = step.coord
                        break
        
        # If no specific goal, just use the center of the board as a generic target
        if not next_goal:
            next_goal = (game.board.rows // 2, game.board.cols // 2)

        # Score each target based on Manhattan distance to the next goal
        scored_targets = []
        for r, c in targets:
            distance = abs(r - next_goal[0]) + abs(c - next_goal[1])
            scored_targets.append((distance, (r, c)))
        
        # Sort by score (distance), ascending
        scored_targets.sort()
        
        # Return the coordinates of the top N targets
        return {coord for _, coord in scored_targets[:MAX_TARGETS_FOR_COMBO_SEARCH]}

    def _get_high_value_target_squares(self, game: Game, player: Player, ideal_plan: Optional[List[RouteStep]]) -> Set[Tuple[int, int]]:
        """
        Identifies a small, highly relevant set of squares for the AI to consider,
        preventing combinatorial explosion and performance issues.
        """
        targets: Set[Tuple[int, int]] = set()
        
        # --- Priority 1: Squares on the ideal path ---
        if ideal_plan:
            for step in ideal_plan:
                r, c = step.coord
                if not game.board.get_tile(r, c) and game.board.is_playable_coordinate(r, c):
                    targets.add((r, c))
        
        # --- Priority 2: Squares to create necessary stop signs ---
        if player.route_card:
            for building_id in player.route_card.stops:
                if building_id not in game.board.buildings_with_stops:
                    building_coord = game.board.building_coords.get(building_id)
                    if building_coord:
                        for d in Direction:
                            nr, nc = building_coord[0] + d.value[0], building_coord[1] + d.value[1]
                            if game.board.is_playable_coordinate(nr, nc) and not game.board.get_tile(nr, nc):
                                targets.add((nr, nc))
        
        # --- Priority 3 (Fallback): Extend existing track segments ---
        # This is a much better fallback than checking every adjacent square.
        # It only runs if the first two priority checks found nothing.
        if not targets:
            print("  (Fallback: Looking for open track ends to extend...)")
            for r_idx in range(game.board.rows):
                for c_idx in range(game.board.cols):
                    tile = game.board.get_tile(r_idx, c_idx)
                    if not tile: continue
                    
                    # Check the connections of this tile
                    conns = game.get_effective_connections(tile.tile_type, tile.orientation)
                    all_exits = {exit for exits in conns.values() for exit in exits}
                    
                    for exit_dir_str in all_exits:
                        exit_dir = Direction.from_str(exit_dir_str)
                        nr, nc = r_idx + exit_dir.value[0], c_idx + exit_dir.value[1]
                        
                        # If a track points to an empty, playable square, it's a high-value target.
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