# game_logic/player.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional, NamedTuple, TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from .game import Game
    from ..common.sound_manager import SoundManager
    from .commands import CombinedActionCommand # For type hinting

from .enums import PlayerState, Direction, GamePhase
from .tile import TileType
from .cards import LineCard, RouteCard
from .ai_strategy import AIStrategy, EasyStrategy, HardStrategy
from .ai_actions import PotentialAction # AI needs to know about the action structure
import common.constants as C


class RouteStep(NamedTuple):
    coord: Tuple[int, int]
    is_goal_node: bool
    arrival_direction: Optional[Direction]


class Player(ABC):
    # This base class is correct and does not need changes.
    # ...
    def __init__(self, player_id: int, difficulty_mode: str):
        self.player_id = player_id
        self.difficulty_mode = difficulty_mode
        self.hand: List[TileType] = []
        self.line_card: Optional[LineCard] = None
        self.route_card: Optional[RouteCard] = None
        self.player_state: PlayerState = PlayerState.LAYING_TRACK
        self.components: Dict[str, Any] = {}
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
        data = { "player_id": self.player_id, "is_ai": isinstance(self, AIPlayer), "hand": [t.name for t in self.hand], "line_card": self.line_card.line_number if self.line_card else None, "route_card": {"stops": self.route_card.stops, "variant": self.route_card.variant_index} if self.route_card else None, "player_state": self.player_state.name, "streetcar_path_index": self.streetcar_path_index, "required_node_index": self.required_node_index, "start_terminal_coord": self.start_terminal_coord, "validated_route": validated_route_data, }
        if isinstance(self, AIPlayer):
            data['strategy'] = 'hard' if isinstance(self.strategy, HardStrategy) else 'easy'
        data['difficulty_mode'] = self.difficulty_mode
        data['components'] = self.components
        return data
    @staticmethod
    def from_dict(data: Dict, tile_types: Dict[str, 'TileType']) -> 'Player':
        is_ai = data.get("is_ai", False)
        player_id = data.get("player_id", -1)
        difficulty_mode = data.get('difficulty_mode', 'normal')
        if is_ai:
            strategy_name = data.get('strategy', 'easy')
            strategy = HardStrategy() if strategy_name == 'hard' else EasyStrategy()
            player = AIPlayer(player_id, strategy, difficulty_mode)
        else:
            player = HumanPlayer(player_id, difficulty_mode)
        player.hand = [tile_types[name] for name in data.get("hand", [])]
        if (lc_num := data.get("line_card")) is not None: player.line_card = LineCard(lc_num)
        if (rc_data := data.get("route_card")): player.route_card = RouteCard(rc_data.get("stops", []), rc_data.get("variant", 0))
        player.player_state = PlayerState[data.get("player_state", "LAYING_TRACK")]
        player.streetcar_path_index = data.get("streetcar_path_index", 0)
        player.required_node_index = data.get("required_node_index", 0)
        start_coord_data = data.get("start_terminal_coord")
        player.start_terminal_coord = tuple(start_coord_data) if start_coord_data else None
        if (route_data := data.get("validated_route")):
            player.validated_route = [RouteStep( coord=tuple(s["coord"]), is_goal_node=s["is_goal"], arrival_direction=Direction[s["arrival_dir"]] if s["arrival_dir"] else None ) for s in route_data]
        player.components = data.get('components', {})
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
    def __init__(self, player_id: int, difficulty_mode: str):
        super().__init__(player_id, difficulty_mode)
    def handle_turn_logic(self, game, visualizer, sounds):
        pass


class AIPlayer(Player):
    def __init__(self, player_id: int, strategy: AIStrategy, difficulty_mode: str):
        super().__init__(player_id, difficulty_mode)
        self.strategy = strategy

    def handle_turn_logic(self, game: 'Game', visualizer: Optional['GameScene'] = None, sounds: Optional['SoundManager'] = None):
        """
        AI's turn logic. It asks its strategy for a plan and then correctly
        evaluates the total action cost of that plan before executing.
        """
        # ... (imports for commands, checks for game phase are correct)

        if self.player_state == PlayerState.LAYING_TRACK:
            print(f"\n--- AI Player {self.player_id} ({self.strategy.__class__.__name__}) is thinking...")

            # 1. The strategy returns a list of chosen PotentialAction objects.
            chosen_actions: List[PotentialAction] = self.strategy.plan_turn(game, self)

            # --- START OF FIX: Calculate total action cost of the plan ---
            total_action_cost = sum(action.action_cost for action in chosen_actions)
            # --- END OF FIX ---

            # 2. Execute the plan if its total cost is sufficient, otherwise forfeit.
            if total_action_cost >= game.MAX_PLAYER_ACTIONS:
                print(f"  AI committing its plan with total action cost of {total_action_cost}...")
                if visualizer:
                    visualizer.force_redraw("AI committing moves...")
                    pygame.time.delay(C.AI_MOVE_DELAY_MS)
                
                # Execute the commands generated by the chosen actions
                for action in chosen_actions:
                    # The command_generator is a function that returns a Command instance.
                    command_to_execute = action.command_generator(game, self)
                    game.command_history.execute_command(command_to_execute)
            
            else:
                # The AI couldn't find a valid plan that uses all its actions.
                print(f"--- AI Player {self.player_id} could only find a plan with cost {total_action_cost}/{game.MAX_PLAYER_ACTIONS}. Forfeiting turn. ---")
                if sounds: sounds.play('eliminated')
                game.eliminate_player(self)
                # We must still post the event to advance the turn after a forfeit.
                pygame.event.post(pygame.event.Event(C.START_NEXT_TURN_EVENT, {'reason': 'ai_forfeit'}))