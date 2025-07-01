# game_logic/player.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional, NamedTuple, TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from .game import Game

from .enums import PlayerState, Direction, GamePhase
from .tile import TileType
from .cards import LineCard, RouteCard
from .ai_strategy import AIStrategy, EasyStrategy, HardStrategy
# Make sure to use the new constant for the delay
import constants as C


class RouteStep(NamedTuple):
    coord: Tuple[int, int]
    is_goal_node: bool
    arrival_direction: Optional[Direction]


class Player(ABC):
    # ... (No changes to the base Player class, to_dict, from_dict, etc.) ...
    # ... Your existing Player class is correct. ...
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
        """Serializes player data to a dictionary."""
        validated_route_data = None
        if self.validated_route:
            validated_route_data = [{"coord": s.coord, "is_goal": s.is_goal_node, "arrival_dir": s.arrival_direction.name if s.arrival_direction else None} for s in self.validated_route]
        
        # Base data common to all players
        data = {
            "player_id": self.player_id, "is_ai": isinstance(self, AIPlayer),
            "hand": [t.name for t in self.hand],
            "line_card": self.line_card.line_number if self.line_card else None,
            "route_card": {"stops": self.route_card.stops, "variant": self.route_card.variant_index} if self.route_card else None,
            "player_state": self.player_state.name, "streetcar_path_index": self.streetcar_path_index,
            "required_node_index": self.required_node_index, "start_terminal_coord": self.start_terminal_coord,
            "validated_route": validated_route_data,
        }
        
        # Add AI-specific data
        if isinstance(self, AIPlayer):
            data['strategy'] = 'hard' if isinstance(self.strategy, HardStrategy) else 'easy'
            
        return data

    @staticmethod
    def from_dict(data: Dict, tile_types: Dict[str, 'TileType']) -> 'Player':
        """
        Deserializes data into a HumanPlayer or AIPlayer object with the correct strategy.
        This is the single factory method for creating players from a save file.
        """
        is_ai = data.get("is_ai", False)
        player_id = data.get("player_id", -1)

        if is_ai:
            strategy_name = data.get('strategy', 'easy')
            strategy = HardStrategy() if strategy_name == 'hard' else EasyStrategy()
            player = AIPlayer(player_id, strategy)
        else:
            player = HumanPlayer(player_id)
        
        # Populate the common attributes for the newly created player object
        player.hand = [tile_types[name] for name in data.get("hand", [])]
        if (lc_num := data.get("line_card")) is not None: player.line_card = LineCard(lc_num)
        if (rc_data := data.get("route_card")): player.route_card = RouteCard(rc_data.get("stops", []), rc_data.get("variant", 0))
        player.player_state = PlayerState[data.get("player_state", "LAYING_TRACK")]
        player.streetcar_path_index = data.get("streetcar_path_index", 0)
        player.required_node_index = data.get("required_node_index", 0)
        start_coord_data = data.get("start_terminal_coord")
        player.start_terminal_coord = tuple(start_coord_data) if start_coord_data else None
        
        if (route_data := data.get("validated_route")):
            player.validated_route = [RouteStep(
                coord=tuple(s["coord"]),
                is_goal_node=s["is_goal"],
                arrival_direction=Direction[s["arrival_dir"]] if s["arrival_dir"] else None
            ) for s in route_data]
        
        return player

    
    def get_required_stop_coords(self, game: 'Game') -> Optional[List[Tuple[int, int]]]:
        if not self.route_card: return []
        stop_coords = []
        for stop_id in self.route_card.stops:
            if (coord := game.board.building_stop_locations.get(stop_id)) is None: return None
            stop_coords.append(coord)
        return stop_coords

    def get_full_driving_sequence(self, game: 'Game') -> Optional[List[Tuple[int, int]]]:
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
    """Represents an AI-controlled player that uses a pluggable strategy for planning."""
    def __init__(self, player_id: int, strategy: AIStrategy):
        super().__init__(player_id)
        self.strategy = strategy
        # actions_to_perform is no longer needed as the turn is synchronous
        # self.actions_to_perform: List[Dict] = []

    def handle_turn_logic(self, game: 'Game'):
        """
        Orchestrates the AI's entire turn synchronously.
        It plans, executes all its moves, and then confirms its own turn.
        """
        if game.game_phase == GamePhase.GAME_OVER:
            return

        if self.player_state == PlayerState.DRIVING:
            print(f"\n--- AI Player {self.player_id}'s Turn (Driving) ---")
            roll_result = game.roll_special_die()
            print(f"  AI Player {self.player_id} rolls a '{roll_result}'.")
            game.attempt_driving_move(self, roll_result)
        
        elif self.player_state == PlayerState.LAYING_TRACK:
            hand_str = ", ".join([t.name for t in self.hand])
            print(f"\n--- AI Player {self.player_id} ({self.strategy.__class__.__name__}) is thinking... (Hand: [{hand_str}]) ---")
            
            # The strategy plans the entire turn's worth of moves at once.
            planned_actions = self.strategy.plan_turn(game, self)
            
            if planned_actions:
                # Execute all planned actions sequentially.
                for move in planned_actions:
                    self._execute_action(game, move)
            else:
                print(f"--- AI Player {self.player_id} could not find any move. Passing turn. ---")
            
            # After all actions are done (or if none were possible), the AI confirms its own turn.
            print(f"--- AI Player {self.player_id} ends its turn. ---")
            game.confirm_turn()

    def _execute_action(self, game: 'Game', move: Dict):
        """Executes a single planned action."""
        action_type, details = move['type'], move['details']
        score_breakdown = move.get('score_breakdown', {})
        
        score_str = ", ".join([f"{k}: {v:.1f}" for k, v in score_breakdown.items() if v > 0])
        print(f"  AI chooses to {action_type.upper()} {details[0].name} at ({details[2]},{details[3]}) (Score: {move.get('score', 0):.2f} -> [{score_str}])")
        
        # We use the simple, non-command-based methods for the AI for speed.
        # The game state will be directly modified.
        success = False
        if action_type == "place":
            # This is a direct call to the game's logic, bypassing the command history for the AI.
            # This is acceptable as AI doesn't need undo/redo.
            success = game.attempt_place_tile(self, *details)
        elif action_type == "exchange":
            success = game.attempt_exchange_tile(self, *details)
        
        if not success:
            print(f"  AI WARNING: The chosen move ({action_type} at {details}) failed validation at execution time.")

    # handle_delayed_action is no longer needed and can be deleted.

    # to_dict and from_dict are correct and do not need changes.
    def to_dict(self) -> Dict:
        data = super().to_dict()
        data['strategy'] = 'hard' if isinstance(self.strategy, HardStrategy) else 'easy'
        return data