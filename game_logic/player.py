# game_logic/player.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional, NamedTuple, TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from .game import Game

from .enums import PlayerState, Direction, GamePhase
from .tile import TileType, PlacedTile
from .cards import LineCard, RouteCard
from constants import AI_ACTION_TIMER_EVENT, MAX_PLAYER_ACTIONS


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
        """Deserializes data into a HumanPlayer or AIPlayer object."""
        # Use 'is_ai' flag from the save file to determine which class to instantiate
        is_ai = data.get("is_ai", False)
        player_class = AIPlayer if is_ai else HumanPlayer
        player = player_class(data.get("player_id", -1))
        
        player.hand = [tile_types[name] for name in data.get("hand", [])]
        if (lc_num := data.get("line_card")) is not None: player.line_card = LineCard(lc_num)
        if (rc_data := data.get("route_card")): player.route_card = RouteCard(rc_data.get("stops", []), rc_data.get("variant", 0))
        player.player_state = PlayerState[data.get("player_state", "LAYING_TRACK")]
        player.streetcar_path_index = data.get("streetcar_path_index", 0)
        player.required_node_index = data.get("required_node_index", 0)
        player.start_terminal_coord = tuple(data["start_terminal_coord"]) if data.get("start_terminal_coord") else None
        
        if (route_data := data.get("validated_route")):
            player.validated_route = [RouteStep(tuple(s["coord"]), s["is_goal"], Direction[s["arrival_dir"]] if s["arrival_dir"] else None) for s in route_data]
        
        # If it's an AI player, load its specific state
        if isinstance(player, AIPlayer):
            # AI state can be loaded here if needed in the future
            pass
            
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
    """Represents an AI-controlled player with a sophisticated, resilient strategic engine."""
    def __init__(self, player_id: int):
        super().__init__(player_id)
        self.ideal_route_plan: Optional[List[RouteStep]] = None
        self.actions_to_perform: List[Dict] = []

    def handle_turn_logic(self, game: 'Game'):
        """Orchestrates the AI's entire turn, from planning to execution with delays."""
        if game.game_phase == GamePhase.GAME_OVER: return

        # --- ADDED: Print AI's hand for debugging ---
        hand_str = ", ".join([t.name for t in self.hand])
        print(f"\n--- AI Player {self.player_id} is thinking... (Hand: [{hand_str}]) ---")
        
        self._plan_full_turn(game)
        
        if self.actions_to_perform:
            self._execute_next_action(game)
            if self.actions_to_perform:
                pygame.time.set_timer(AI_ACTION_TIMER_EVENT, 1, loops=1)
            else: 
                print(f"--- AI Player {self.player_id} only had one valid move. Ending turn. ---")
                game.confirm_turn()
        else:
            # --- MODIFIED: Halt gracefully instead of crashing ---
            print("="*50)
            print(f"FATAL LOGIC ERROR: AI Player {self.player_id} could not find a single legal move.")
            print(f"Hand: {[t.name for t in self.hand]}")
            print("The game will now halt for this AI. Please inspect the board.")
            print("="*50)
            # End the turn without making a move. This passes control and keeps the game alive.
            game.confirm_turn()
            # --- END MODIFICATION ---

    def handle_delayed_action(self, game: 'Game'):
        """Executes the second planned action."""
        if self.actions_to_perform:
            self._execute_next_action(game)
        
        print(f"--- AI Player {self.player_id} ends its turn. ---")
        game.confirm_turn()

    def _execute_next_action(self, game: 'Game'):
        """Pops the next action from the planned list and executes it."""
        move = self.actions_to_perform.pop(0)
        action_type, details, score_breakdown = move['type'], move['details'], move['score_breakdown']
        
        score_str = ", ".join([f"{k}: {v:.1f}" for k, v in score_breakdown.items() if v > 0])
        print(f"  AI chooses to {action_type.upper()} {details[0].name} at ({details[2]},{details[3]}) (Total Score: {move['score']:.2f} -> [{score_str}])")
        
        if action_type == "place":
            game.attempt_place_tile(self, *details)
        elif action_type == "exchange":
            game.attempt_exchange_tile(self, *details)


    def _plan_full_turn(self, game: 'Game'):
        """The AI's brain: Plans the best two actions for the turn by simulating."""
        self.actions_to_perform = []
        sim_game = game.copy_for_simulation()
        sim_player = next(p for p in sim_game.players if p.player_id == self.player_id)

        for i in range(MAX_PLAYER_ACTIONS):
            best_move = self._find_best_move_in_state(sim_game, sim_player)
            if best_move:
                self.actions_to_perform.append(best_move)
                # Apply the move to the simulation for accurate planning of the second action
                action_type, details = best_move['type'], best_move['details']
                tile, orientation, r, c = details
                if action_type == "place":
                    sim_game.board.set_tile(r, c, PlacedTile(tile, orientation))
                    if tile in sim_player.hand: sim_player.hand.remove(tile)
                elif action_type == "exchange":
                    old_tile = sim_game.board.get_tile(r,c)
                    if old_tile and tile in sim_player.hand:
                        sim_player.hand.remove(tile)
                        sim_player.hand.append(old_tile.tile_type)
                        sim_game.board.set_tile(r,c, PlacedTile(tile, orientation))
            else:
                break

    def _find_best_move_in_state(self, game: 'Game', player: 'Player') -> Optional[Dict]:
        """Analyzes a game state and finds the single best action to take. Never gives up."""
        ideal_plan = self._calculate_ideal_route(game, player)
        valid_moves = []

        # 1. Generate all legal moves and score them.
        for tile in player.hand:
            # Placements
            for r in range(game.board.rows):
                for c in range(game.board.cols):
                    for o in [0, 90, 180, 270]:
                        if game.check_placement_validity(tile, o, r, c)[0]:
                            score, breakdown = self._score_move(game, player, ideal_plan, "place", tile, o, r, c)
                            valid_moves.append({'type': 'place', 'details': (tile, o, r, c), 'score': score, 'score_breakdown': breakdown})
            # Exchanges
            for r in range(game.board.rows):
                for c in range(game.board.cols):
                    if game.board.get_tile(r, c):
                        for o in [0, 90, 180, 270]:
                            if game.check_exchange_validity(player, tile, o, r, c)[0]:
                                score, breakdown = self._score_move(game, player, ideal_plan, "exchange", tile, o, r, c)
                                valid_moves.append({'type': 'exchange', 'details': (tile, o, r, c), 'score': score, 'score_breakdown': breakdown})

        if not valid_moves:
            return None
        
        return max(valid_moves, key=lambda m: m['score'])

    def _calculate_ideal_route(self, game: 'Game', player: 'Player') -> Optional[List[RouteStep]]:
        """Calculates the AI's 'wet dream' path assuming infinite tiles."""
        if not player.line_card or not player.route_card: return None
        stops = player.get_required_stop_coords(game)
        if stops is None: return None
        t1, t2 = game.get_terminal_coords(player.line_card.line_number)
        if not t1 or not t2: return None
        
        path1, cost1 = game.pathfinder.find_path(game, player, [t1] + stops + [t2], is_hypothetical=True)
        path2, cost2 = game.pathfinder.find_path(game, player, [t2] + stops + [t1], is_hypothetical=True)
        
        if cost1 == float('inf') and cost2 == float('inf'): return None
        return path1 if cost1 <= cost2 else path2

    def _score_move(self, game: 'Game', player: 'Player', ideal_plan: Optional[List[RouteStep]], move_type: str, tile: TileType, orientation: int, r: int, c: int) -> Tuple[float, Dict[str, float]]:
        """Scores a pre-validated move and returns the score breakdown."""
        score = 1.0  # Base score for any legal move, ensuring AI never passes.
        breakdown = {'base': score}

        # Priority 1: Fulfilling the Ideal Plan
        if ideal_plan:
            for i, step in enumerate(ideal_plan):
                if step.coord == (r, c):
                    # Higher score for moves earlier in the plan
                    path_score = 200.0 - (i * 5)
                    score += path_score
                    breakdown['ideal_path'] = path_score
                    break # Stop after finding the first match
        
        # Priority 2: Creating a Required Stop
        if player.route_card:
            for d in Direction:
                building_id = game.board.get_building_at(r + d.value[0], c + d.value[1])
                # Check if this building is a required stop AND doesn't have a stop sign yet
                if building_id and building_id in player.route_card.stops and building_id not in game.board.buildings_with_stops:
                    conns = game.get_effective_connections(tile, orientation)
                    is_parallel = (d in [Direction.N, Direction.S] and game._has_ew_straight(conns)) or \
                                  (d in [Direction.E, Direction.W] and game._has_ns_straight(conns))
                    if is_parallel:
                        score += 150.0
                        breakdown['stop_creation'] = 150.0
        
        # Priority 3: Working Backwards from Terminals (Plan B)
        # If the move doesn't fit the ideal plan, see if it helps build from the end
        if 'ideal_path' not in breakdown and player.line_card:
            _, term2 = game.get_terminal_coords(player.line_card.line_number)
            if term2:
                dist = abs(r - term2[0]) + abs(c - term2[1])
                # Lower score than ideal path, but better than random
                backwards_score = 50.0 - dist
                score += backwards_score
                breakdown['backwards_plan'] = backwards_score

        # Priority 4: General Connectivity
        connectivity_score = 0
        for d in Direction:
            if game.board.get_tile(r + d.value[0], c + d.value[1]):
                connectivity_score += 10.0
        if connectivity_score > 0:
            score += connectivity_score
            breakdown['connectivity'] = connectivity_score
                
        if move_type == "exchange":
            score += 5.0
            breakdown['exchange_bonus'] = 5.0

        return score, breakdown
