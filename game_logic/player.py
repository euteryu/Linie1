# game_logic/player.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional, NamedTuple, TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from .game import Game
    from ..sound_manager import SoundManager
    from .commands import CombinedActionCommand # For type hinting

from .enums import PlayerState, Direction, GamePhase
from .tile import TileType
from .cards import LineCard, RouteCard
from .ai_strategy import AIStrategy, EasyStrategy, HardStrategy
import constants as C


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
    # This class is correct and does not need changes.
    # ...
    def __init__(self, player_id: int, difficulty_mode: str):
        super().__init__(player_id, difficulty_mode)
    def handle_turn_logic(self, game, visualizer, sounds):
        pass


class AIPlayer(Player):
    def __init__(self, player_id: int, strategy: AIStrategy, difficulty_mode: str):
        super().__init__(player_id, difficulty_mode)
        self.strategy = strategy

    def handle_turn_logic(self, game: 'Game', visualizer: Optional['Linie1Visualizer'] = None, sounds: Optional['SoundManager'] = None):
        """
        Orchestrates the AI's entire turn logic for both laying track and driving.
        """
        from .commands import CombinedActionCommand

        if game.game_phase == GamePhase.GAME_OVER:
            return

        if self.player_state == PlayerState.DRIVING:
            print(f"\n--- AI Player {self.player_id}'s Turn (Driving) ---")
            
            # --- START OF FIX ---
            # Call the method on the deck_manager, not the game object.
            roll_result = game.deck_manager.roll_special_die()
            # --- END OF FIX ---

            print(f"  AI Player {self.player_id} rolls a '{roll_result}'.")
            if sounds: sounds.play('dice_roll')
            
            if visualizer:
                visualizer.force_redraw(f"AI rolling... {roll_result}")
                pygame.time.delay(C.AI_MOVE_DELAY_MS)

            if not game.attempt_driving_move(self, roll_result):
                 if sounds: sounds.play('error')
                 # If the move fails (e.g., blocked path), the turn still ends.
                 game.confirm_turn()
        
        elif self.player_state == PlayerState.LAYING_TRACK:
            hand_str = ", ".join([t.name for t in self.hand])
            print(f"\n--- AI Player {self.player_id} ({self.strategy.__class__.__name__}) is thinking... (Hand: [{hand_str}]) ---")

            planned_actions = self.strategy.plan_turn(game, self)
            
            staged_moves_for_command = []
            for move in planned_actions:
                score_str = ", ".join([f"{k}: {v:.1f}" for k,v in move.get('score_breakdown', {}).items() if v>0])
                print(f"  AI plans to {move['type'].upper()} {move['details'][0].name} at {move['details'][2:]} (Score: {move.get('score', 0):.2f} -> [{score_str}])")
                
                tile_type, orientation, r, c = move['details']
                staged_moves_for_command.append({
                    'coord': (r, c),
                    'tile_type': tile_type,
                    'orientation': orientation,
                    'action_type': move['type'],
                    'is_valid': True
                })

            if len(staged_moves_for_command) >= game.MAX_PLAYER_ACTIONS:
                print(f"  AI committing its plan...")
                if visualizer:
                    visualizer.force_redraw("AI committing moves...")
                    pygame.time.delay(C.AI_MOVE_DELAY_MS)

                command = CombinedActionCommand(game, self, staged_moves_for_command)
                if not game.command_history.execute_command(command):
                    print("  CRITICAL AI ERROR: Planned combo command failed to execute.")
                    game.eliminate_player(self)
                    if sounds: sounds.play('error')
            else:
                print(f"--- AI Player {self.player_id} could only find {len(planned_actions)}/{game.MAX_PLAYER_ACTIONS} moves. Forfeiting turn. ---")
                if sounds: sounds.play('eliminated')
                game.eliminate_player(self)
            
            if game.game_phase != GamePhase.GAME_OVER:
                print(f"--- AI Player {self.player_id} ends its turn. ---")
                if self.player_state != PlayerState.ELIMINATED and sounds:
                    sounds.play('commit')
                game.confirm_turn()