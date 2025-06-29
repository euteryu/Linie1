# game_logic/player.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional, NamedTuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .game import Game # For type hinting

from .enums import PlayerState, GamePhase, Direction
from .tile import TileType
from .cards import LineCard, RouteCard

from constants import AI_ACTION_TIMER_EVENT

import pygame


class RouteStep(NamedTuple):
    coord: Tuple[int, int]
    is_goal_node: bool
    arrival_direction: Optional[Direction]

class Player(ABC):
    """Abstract base class for all players, containing shared attributes."""
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.hand: List[TileType] = []
        self.line_card: Optional[LineCard] = None
        self.route_card: Optional[RouteCard] = None
        self.player_state: PlayerState = PlayerState.LAYING_TRACK
        self.streetcar_path_index: int = 0
        self.required_node_index: int = 0
        self.start_terminal_coord: Optional[Tuple[int, int]] = None
        self.validated_route: Optional[List[RouteStep]] = None

    @abstractmethod
    def handle_turn_logic(self, game: Game):
        """The main entry point for a player's turn-based logic."""
        pass

    @property
    def streetcar_position(self) -> Optional[Tuple[int, int]]:
        if self.validated_route and 0 <= self.streetcar_path_index < len(self.validated_route):
            return self.validated_route[self.streetcar_path_index].coord
        return None
    
    @property
    def arrival_direction(self) -> Optional[Direction]:
        if self.validated_route and 0 <= self.streetcar_path_index < len(self.validated_route):
            return self.validated_route[self.streetcar_path_index].arrival_direction
        return None

    def to_dict(self) -> Dict:
        validated_route_data = None
        if self.validated_route:
            validated_route_data = [{"coord": s.coord, "is_goal": s.is_goal_node, "arrival_dir": s.arrival_direction.name if s.arrival_direction else None} for s in self.validated_route]
        return {
            "player_id": self.player_id, "is_ai": isinstance(self, AIPlayer), "hand": [t.name for t in self.hand],
            "line_card": self.line_card.line_number if self.line_card else None,
            "route_card": {"stops": self.route_card.stops, "variant": self.route_card.variant_index} if self.route_card else None,
            "player_state": self.player_state.name, "streetcar_path_index": self.streetcar_path_index,
            "required_node_index": self.required_node_index, "start_terminal_coord": self.start_terminal_coord,
            "validated_route": validated_route_data,
        }

    @staticmethod
    def from_dict(data: Dict, tile_types: Dict[str, 'TileType']) -> 'Player':
        is_ai = data.get("is_ai", False)
        player_class = AIPlayer if is_ai else HumanPlayer
        player = player_class(data["player_id"])
        player.hand = [tile_types[name] for name in data.get("hand", [])]
        if (lc_num := data.get("line_card")) is not None: player.line_card = LineCard(lc_num)
        if (rc_data := data.get("route_card")): player.route_card = RouteCard(rc_data["stops"], rc_data["variant"])
        player.player_state = PlayerState[data.get("player_state", "LAYING_TRACK")]
        player.streetcar_path_index = data.get("streetcar_path_index", 0)
        player.required_node_index = data.get("required_node_index", 0)
        player.start_terminal_coord = tuple(data["start_terminal_coord"]) if data.get("start_terminal_coord") else None
        if (route_data := data.get("validated_route")):
            player.validated_route = [RouteStep(tuple(s["coord"]), s["is_goal"], Direction[s["arrival_dir"]] if s["arrival_dir"] else None) for s in route_data]
        return player
    
    def get_required_stop_coords(self, game: 'Game') -> Optional[List[Tuple[int, int]]]:
        """
        Gets the sequence of STOP coordinates the player needs to visit.
        This is needed by all player types for validation and driving.
        """
        if not self.route_card: return []
        stop_coords = []
        for stop_id in self.route_card.stops:
            if (coord := game.board.building_stop_locations.get(stop_id)) is None: return None
            stop_coords.append(coord)
        return stop_coords

    def get_full_driving_sequence(self, game: 'Game') -> Optional[List[Tuple[int, int]]]:
        """
        Gets the full, ordered list of GOAL NODES for the DRIVING phase.
        This is needed by all player types for win condition checks.
        """
        if not self.line_card or not self.start_terminal_coord: return None
        stop_coords = self.get_required_stop_coords(game)
        if stop_coords is None: return None
        term1, term2 = game.get_terminal_coords(self.line_card.line_number)
        if not term1 or not term2: return None
        end_terminal = term2 if self.start_terminal_coord == term1 else term1
        return [self.start_terminal_coord] + stop_coords + [end_terminal]


class HumanPlayer(Player):
    """Represents a human-controlled player."""
    def handle_turn_logic(self, game: 'Game'):
        pass # Human logic is driven by Pygame events in the state machine.

class AIPlayer(Player):
    """Represents an AI-controlled player with strategic planning."""
    def __init__(self, player_id: int):
        super().__init__(player_id)
        self.ideal_route_plan: Optional[List[RouteStep]] = None
        self.actions_taken_this_turn: int = 0

    def handle_turn_logic(self, game: 'Game'):
        """Initiates the AI's turn by taking the FIRST action and setting a timer."""
        if game.game_phase == GamePhase.GAME_OVER: return

        print(f"\n--- AI Player {self.player_id}'s Turn (Action 1) ---")
        self.actions_taken_this_turn = 0
        
        self._plan_and_execute_action(game)
        self.actions_taken_this_turn += 1

        if game.game_phase != GamePhase.GAME_OVER:
            pygame.time.set_timer(AI_ACTION_TIMER_EVENT, 1, loops=1)
        
    def handle_delayed_action(self, game: 'Game'):
        """Handles the second action, triggered by the pygame timer event."""
        print(f"--- AI Player {self.player_id}'s Turn (Action 2) ---")
        if self.actions_taken_this_turn < game.MAX_PLAYER_ACTIONS:
            self._plan_and_execute_action(game)
            self.actions_taken_this_turn += 1

        print(f"--- AI Player {self.player_id} ends its turn. ---")
        game.confirm_turn()

    def _plan_and_execute_action(self, game: 'Game'):
        """Calculates the ideal path, evaluates all possible moves, and executes the best one."""
        self.ideal_route_plan = self._calculate_ideal_route(game)
        
        best_move, best_score = self._find_best_move(game)
        
        if best_move:
            action_type, details = best_move
            if action_type == "place":
                tile, orientation, r, c = details
                print(f"  AI chooses to PLACE {tile.name} at ({r},{c}) (Score: {best_score:.2f})")
                game.attempt_place_tile(self, tile, orientation, r, c)
            elif action_type == "exchange":
                tile, orientation, r, c = details
                print(f"  AI chooses to EXCHANGE for {tile.name} at ({r},{c}) (Score: {best_score:.2f})")
                game.attempt_exchange_tile(self, tile, orientation, r, c)
        else:
            # This should now only happen if the AI has no tiles and no valid exchanges.
            print("  AI has absolutely no legal moves available.")


    def _calculate_ideal_route(self, game: 'Game') -> Optional[List[RouteStep]]:
        if not self.line_card or not self.route_card: return None
        stops = self.get_required_stop_coords(game)
        if stops is None: return None
        t1, t2 = game.get_terminal_coords(self.line_card.line_number)
        if not t1 or not t2: return None
        path1, cost1 = game.pathfinder.find_path(game, self, [t1] + stops + [t2], is_hypothetical=True)
        path2, cost2 = game.pathfinder.find_path(game, self, [t2] + stops + [t1], is_hypothetical=True)
        if cost1 == float('inf') and cost2 == float('inf'): return None
        return path1 if cost1 <= cost2 else path2

    def _find_best_move(self, game: 'Game') -> Tuple[Optional[Tuple], float]:
        """
        Generates a list of all 100% legal moves and then scores them to find the best one.
        """
        valid_moves = []

        # 1. Evaluate all valid "place" moves
        for tile in self.hand:
            for r in range(game.board.rows):
                for c in range(game.board.cols):
                    for orientation in [0, 90, 180, 270]:
                        if game.check_placement_validity(tile, orientation, r, c)[0]:
                            # --- FIX: Pass 'orientation' to the scoring function ---
                            score = self._score_move(game, "place", tile, orientation, r, c)
                            valid_moves.append({'type': 'place', 'details': (tile, orientation, r, c), 'score': score})
        
        # 2. Evaluate all valid "exchange" moves
        for tile_in_hand in self.hand:
            for r in range(game.board.rows):
                for c in range(game.board.cols):
                    if game.board.get_tile(r, c) is None: continue
                    for orientation in [0, 90, 180, 270]:
                        if game.check_exchange_validity(self, tile_in_hand, orientation, r, c)[0]:
                            # --- FIX: Pass 'orientation' to the scoring function ---
                            score = self._score_move(game, "exchange", tile_in_hand, orientation, r, c)
                            valid_moves.append({'type': 'exchange', 'details': (tile_in_hand, orientation, r, c), 'score': score + 5.0})

        if not valid_moves:
            return None, -1.0
        
        best_move = max(valid_moves, key=lambda m: m['score'])
        return (best_move['type'], best_move['details']), best_move['score']

    def _score_move(self, game: 'Game', move_type: str, tile: TileType, orientation: int, r: int, c: int) -> float:
        """
        Scores a pre-validated move based on its strategic value.
        Now correctly accepts the 'orientation' parameter.
        """
        score = 0.1
        
        # Score for aligning with the ideal route plan
        if self.ideal_route_plan:
            for i, step in enumerate(self.ideal_route_plan):
                if step.coord == (r,c):
                    score += 100.0 - (i * 2) 
                    break
        
        # Score for connecting to existing track
        for direction in Direction:
            neighbor_pos = (r + direction.value[0], c + direction.value[1])
            if game.board.get_tile(neighbor_pos[0], neighbor_pos[1]):
                score += 10.0
        
        # Bonus for creating a required stop sign
        if self.route_card:
            for direction in Direction:
                neighbor_pos = (r + direction.value[0], c + direction.value[1])
                building_id = game.board.get_building_at(neighbor_pos[0], neighbor_pos[1])
                if building_id and building_id in self.route_card.stops:
                    # --- FIX: 'orientation' is now available to be used here ---
                    conns = game.get_effective_connections(tile, orientation)
                    is_parallel = (direction in [Direction.N, Direction.S] and game._has_ns_straight(conns)) or \
                                  (direction in [Direction.E, Direction.W] and game._has_ns_straight(conns))
                    if is_parallel:
                        score += 50.0
        
        return score
