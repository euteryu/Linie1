# game_logic/player.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional, NamedTuple, TYPE_CHECKING
import pygame

import copy

if TYPE_CHECKING:
    from .game import Game
    from ..common.sound_manager import SoundManager
    from .commands import CombinedActionCommand # For type hinting

from .enums import PlayerState, Direction, GamePhase
from .tile import TileType
from .cards import LineCard, RouteCard
from .ai_strategy import AIStrategy, HardStrategy, GreedySequentialStrategy
from .ai_actions import PotentialAction # AI needs to know about the action structure
import common.constants as C
from .commands import CombinedActionCommand


class RouteStep(NamedTuple):
    coord: Tuple[int, int]
    is_goal_node: bool
    arrival_direction: Optional[Direction]


class Player(ABC):
    def __init__(self, player_id: int, difficulty_mode: str):
        self.player_id = player_id
        self.difficulty_mode = difficulty_mode
        self.hand: List[TileType] = []
        self.mailbox: List[TileType] = []
        self.line_card: Optional[LineCard] = None
        self.route_card: Optional[RouteCard] = None
        self.player_state: PlayerState = PlayerState.LAYING_TRACK
        self.components: Dict[str, Any] = {}
        self.streetcar_path_index: int = 0
        self.required_node_index: int = 0
        self.start_terminal_coord: Optional[Tuple[int, int]] = None
        self.validated_route: Optional[List[RouteStep]] = None

    @property
    @abstractmethod
    def is_ai(self) -> bool:
        """Returns True if the player is an AI, False otherwise."""
        pass

    @abstractmethod
    def handle_turn_logic(self, game: Game, visualizer: Optional['GameScene'], sounds: Optional['SoundManager']):
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
        data['mailbox'] = [t.name for t in self.mailbox]
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
        player.mailbox = [tile_types[name] for name in data.get("mailbox", [])]
        player.components = data.get('components', {})
        return player

    def get_required_stop_coords(self, game: 'Game') -> Optional[List[Tuple[int, int]]]:
        """
        Gets the coordinates of the ACTUAL, PLACED STOP SIGNS required by the player's
        route card. This is used for official route validation.
        Returns None if not all stops have been created yet.
        """
        if not self.route_card:
            return []
        
        stop_coords = []
        for stop_id in self.route_card.stops:
            # This MUST check the dictionary of activated stop signs.
            if coord := game.board.building_stop_locations.get(stop_id):
                stop_coords.append(coord)
            else:
                # If any required stop sign doesn't exist, the route is not complete.
                return None
        return stop_coords

    def get_hypothetical_stop_coords(self, game: 'Game') -> Optional[List[Tuple[int, int]]]:
        """
        Gets the coordinates of the required BUILDINGS from the player's route card.
        This is used for AI and Hint pathfinding before stops are placed.
        """
        if not self.route_card:
            return []
        
        stop_coords = []
        for stop_id in self.route_card.stops:
            if coord := game.board.building_coords.get(stop_id):
                stop_coords.append(coord)
            else:
                return None # The route is impossible to calculate.
        return stop_coords

    def get_full_driving_sequence(self, game: 'Game') -> Optional[List[Tuple[int, int]]]:
        # This function is used AFTER a route is validated, so it should use the official method.
        if not self.line_card or not self.start_terminal_coord: return None
        stop_coords = self.get_required_stop_coords(game)
        if stop_coords is None: return None
        term1, term2 = game.get_terminal_coords(self.line_card.line_number)
        if not term1 or not term2: return None
        end_terminal = term2 if self.start_terminal_coord == term1 else term1
        return [self.start_terminal_coord] + stop_coords + [end_terminal]

    def copy(self) -> 'Player':
        """Creates a copy of the player for simulation. The hand must be deep-copied."""
        new_player = copy.copy(self)
        new_player.hand = copy.deepcopy(self.hand)
        return new_player



class HumanPlayer(Player):
    def __init__(self, player_id: int, difficulty_mode: str): super().__init__(player_id, difficulty_mode)
    
    # --- START OF CHANGE: Implement the driving phase logic ---
    def handle_turn_logic(self, game: 'Game', visualizer: Optional['GameScene'], sounds: Optional['SoundManager']):
        """Handles logic for human players, specifically triggering the first roll in the driving phase."""
        if self.player_state == PlayerState.DRIVING:
            # For a human, their action is to roll the die, which is handled by the DrivingState UI.
            # However, we need to prompt them if they want to use influence after their move.
            # To kick this off, we can just signal that the turn isn't over yet,
            # and the DrivingState's event handler will take care of the rest.
            print(f"--- Human Player {self.player_id}'s turn to drive. Waiting for input. ---")
            pass # The DrivingState handles the key/mouse presses for the roll.
    # --- END OF CHANGE ---
    
    @property
    def is_ai(self) -> bool:
        return False


class AIPlayer(Player):
    def __init__(self, player_id: int, strategy: AIStrategy, difficulty_mode: str):
        super().__init__(player_id, difficulty_mode)
        self.strategy = strategy

    @property
    def is_ai(self) -> bool:
        return True

    def handle_turn_logic(self, game: 'Game', visualizer: Optional['GameScene'] = None, sounds: Optional['SoundManager'] = None):
        """
        Orchestrates the AI's turn. It gets a plan from a strategy and executes
        the actions within that plan, trusting that the plan is valid.
        """
        if game.game_phase == GamePhase.GAME_OVER: return

        if self.player_state == PlayerState.LAYING_TRACK:
            if not game.rule_engine.can_player_make_any_move(game, self):
                print(f"--- Player {self.player_id} has no more legal moves and is ELIMINATED! ---")
                if sounds: sounds.play('eliminated')
                game.eliminate_player(self)
                pygame.event.post(pygame.event.Event(C.START_NEXT_TURN_EVENT, {'reason': 'ai_eliminated'}))
                return
            
            print(f"\n--- AI Player {self.player_id} ({self.strategy.__class__.__name__}) is thinking...")
            final_plan: List[PotentialAction] = []
            
            # 1. Get a plan from a mod or the base strategy.
            mod_plan = game.mod_manager.on_ai_plan_turn(game, self, self.strategy)
            if mod_plan is not None:
                final_plan = mod_plan
            else:
                print(f"No mod override for AI planning. Using default strategy: {self.strategy.__class__.__name__}")
                final_plan = self.strategy.plan_turn(game, self)
            
            # 2. If the primary strategy failed, attempt the fallback.
            if not final_plan:
                print("Primary strategy failed to find a plan. Attempting fallback.")
                fallback_strategy = GreedySequentialStrategy()
                final_plan = fallback_strategy.plan_turn(game, self)

            # 3. Execute the final plan or forfeit.
            if final_plan:
                print(f"  AI committing its plan...")
                if visualizer:
                    visualizer.force_redraw("AI committing moves...")
                    pygame.time.delay(C.AI_MOVE_DELAY_MS)
                
                # Execute every command in the generated plan.
                # The plan is guaranteed by the AI to have a valid total action cost (e.g., 2).
                for action in final_plan:
                    command_to_run = action.command_generator(game, self)
                    game.command_history.execute_command(command_to_run)
                
                # After the plan is fully executed, end the turn.
                pygame.event.post(pygame.event.Event(C.START_NEXT_TURN_EVENT, {'reason': 'ai_actions_committed'}))
            else:
                # If even the fallback strategy failed, the player is truly stuck.
                print(f"--- AI Player {self.player_id} could not find any valid moves after fallback. Forfeiting turn. ---")
                if sounds: sounds.play('eliminated')
                game.eliminate_player(self)
                pygame.event.post(pygame.event.Event(C.START_NEXT_TURN_EVENT, {'reason': 'ai_forfeit'}))

        elif self.player_state == PlayerState.DRIVING:
            print(f"--- AI Player {self.player_id} is in DRIVING phase. ---")
            
            was_handled_by_mod = game.mod_manager.on_ai_driving_turn(game, self)

            if not was_handled_by_mod:
                print("  No mod override for driving. Performing standard roll.")
                if visualizer:
                    visualizer.force_redraw("AI Rolling...")
                    pygame.time.delay(C.AI_MOVE_DELAY_MS)
                roll_result = game.deck_manager.roll_special_die()
                print(f"  AI rolled a '{roll_result}'.")
                game.attempt_driving_move(self, roll_result, end_turn=True)


# HELPERS
def _ai_wants_to_use_influence(game: 'Game', player: 'AIPlayer') -> bool:
    """Helper logic to determine if an AI should spend an Influence point."""
    if not player.validated_route: return False
    try:
        full_sequence = player.get_full_driving_sequence(game)
        if not full_sequence or player.required_node_index >= len(full_sequence): return False
        next_goal_coord = full_sequence[player.required_node_index]
        next_goal_path_index = next(i for i, step in enumerate(player.validated_route) if i > player.streetcar_path_index and step.coord == next_goal_coord)
        dist_to_goal = next_goal_path_index - player.streetcar_path_index
        if 0 < dist_to_goal <= 4: return True
    except (StopIteration, IndexError): return False
    return False