# game_logic/game.py
from __future__ import annotations
from typing import List, Dict, Tuple, Optional, Any, TYPE_CHECKING
import random, json, traceback, copy
import pygame

if TYPE_CHECKING:
    from .pathfinding import Pathfinder
    from .visualizer import Linie1Visualizer
    from .mod_manager import ModManager
    from ..scenes.game_scene import GameScene
    from ..states.game_states import InfluenceDecisionState
    from ..levels.level import Level

from .enums import PlayerState, GamePhase, Direction
from .tile import TileType, PlacedTile
from .cards import LineCard, RouteCard
from .player import Player, HumanPlayer, AIPlayer, RouteStep
from .board import Board
from .command_history import CommandHistory
from .commands import MoveCommand
from .pathfinding import BFSPathfinder
from .rule_engine import RuleEngine
from .turn_manager import TurnManager
from .deck_manager import DeckManager
import common.constants as C

class Game:
    def __init__(self, player_types: List[str], difficulty: str, mod_manager: 'ModManager', level_data: Level):
        """
        Initializes the main Game object.

        Args:
            player_types (List[str]): A list of player types ('human' or 'ai').
            difficulty (str): The AI difficulty ('normal' or 'king').
            mod_manager (ModManager): The game's mod manager instance.
            level_data (Level): The data object for the map to be played.
        """
        if not 1 <= len(player_types) <= 6:
            raise ValueError("Total players must be 1-6.")

        # --- Store Core Data & Managers ---
        self.level_data = level_data
        self.rule_engine = RuleEngine()
        self.turn_manager = TurnManager()
        self.deck_manager = DeckManager(self)
        self.pathfinder: Pathfinder = BFSPathfinder()
        self.mod_manager = mod_manager
        self.visualizer: Optional['GameScene'] = None
        self.command_history = CommandHistory()
        
        # --- Game State Attributes ---
        self.num_players = len(player_types)
        self.difficulty = difficulty.lower()
        self.players: List[Player] = []
        self.tile_types = {name: TileType(name=name, **details) for name, details in C.TILE_DEFINITIONS.items()}
        
        # The Board is now created using the level data
        self.board = Board(level_data)
        
        self.active_player_index: int = 0
        self.game_phase: GamePhase = GamePhase.SETUP
        self.current_turn: int = 1
        self.winner: Optional[Player] = None
        self.actions_taken_this_turn: int = 0
        self.turn_start_history_index: int = -1
        self.live_auctions: List[Dict[str, Any]] = []
        self.rail_foundation_capital: int = 0

        # --- Game Constants ---
        self.MAX_PLAYER_ACTIONS = C.MAX_PLAYER_ACTIONS
        self.HAND_TILE_LIMIT = C.HAND_TILE_LIMIT

        # --- Player Creation ---
        from .ai_strategy import HardStrategy, GreedySequentialStrategy
        for i, p_type in enumerate(player_types):
            if p_type.lower() == 'human':
                self.players.append(HumanPlayer(i, self.difficulty))
            elif p_type.lower() == 'ai':
                self.players.append(AIPlayer(i, HardStrategy(), self.difficulty))
            else:
                raise ValueError(f"Unknown player type in config: {p_type}")
        
        # --- Final Setup Call ---
        self.setup_game()

    def setup_game(self):
        """Initializes the game by delegating setup tasks using loaded level data."""
        # Initialize the board's terminals using data from the level object
        self.board._initialize_terminals(self.tile_types, self.level_data.terminal_data)
        
        # Call mod hooks
        self.mod_manager.on_game_setup(self)

        # Create and deal cards and tiles
        self.deck_manager.create_and_shuffle_piles()
        self.deck_manager.deal_starting_hands_and_cards()
        
        # Set the initial game state
        self.game_phase = GamePhase.LAYING_TRACK
        self.current_turn = 1
        self.turn_start_history_index = -1

    # --- Core Public API ---
    def get_active_player(self) -> Player:
        if 0 <= self.active_player_index < len(self.players):
            return self.players[self.active_player_index]
        raise IndexError("Active player index out of bounds.")

    def get_terminal_coords(self, line_number: int) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        line_num_str = str(line_number)
        if line_num_str in self.level_data.terminal_data:
            pairs = self.level_data.terminal_data[line_num_str]
            # We need to find the "primary" tile of each pair to represent the terminal location.
            # A simple rule is to take the first tile listed in each pair.
            t1 = tuple(pairs[0][0][0])
            t2 = tuple(pairs[1][0][0])
            return t1, t2
        return None

    def confirm_turn(self) -> bool:
        """Delegates turn confirmation to the TurnManager."""
        return self.turn_manager.confirm_turn(self)

    def attempt_driving_move(self, player: Player, roll_result: Any, end_turn: bool = True) -> bool:
        """Creates a MoveCommand based on a dice roll."""
        if player.player_state != PlayerState.DRIVING or not player.validated_route:
            return False
        
        current_idx = player.streetcar_path_index
        next_goal_idx = -1
        try:
            full_sequence = player.get_full_driving_sequence(self)
            if not full_sequence: return self.confirm_turn()
            next_goal_in_sequence = full_sequence[player.required_node_index]
            next_goal_idx = next(i for i, step in enumerate(player.validated_route) if i > current_idx and step.coord == next_goal_in_sequence)
        except (IndexError, StopIteration):
            return self.confirm_turn()

        dist_to_goal = next_goal_idx - current_idx
        target_idx = current_idx

        if roll_result == C.STOP_SYMBOL:
            target_idx = next_goal_idx
        elif isinstance(roll_result, int):
            if roll_result >= dist_to_goal: target_idx = next_goal_idx
            else: target_idx = current_idx + roll_result
        
        if target_idx == current_idx:
            # If no move is made, the turn always ends.
            pygame.event.post(pygame.event.Event(C.START_NEXT_TURN_EVENT, {'reason': 'no_drive_move'}))
            return True

        # Pass the 'end_turn' flag to the command
        command = MoveCommand(self, player, target_idx, end_turn_on_execute=end_turn)
        
        if self.command_history.execute_command(command):
            # After a successful move, check if a human player should be prompted to use influence
            eco_mod = self.mod_manager.available_mods.get('economic_mod')
            if eco_mod and isinstance(player, HumanPlayer) and player.components[eco_mod.mod_id].get('influence', 0) > 0 and not end_turn:
                if self.visualizer:
                    # Instead of ending the turn, switch to the decision state
                    self.visualizer.request_state_change(InfluenceDecisionState)
            elif end_turn:
                 pygame.event.post(pygame.event.Event(C.START_NEXT_TURN_EVENT, {'reason': 'driving_move'}))
            return True
        else:
            # If the command fails, the turn must end to prevent a stuck game.
            pygame.event.post(pygame.event.Event(C.START_NEXT_TURN_EVENT, {'reason': 'driving_move_failed'}))
            return False
        
    def check_player_route_completion(self, player: Player) -> Tuple[bool, Optional[Tuple[int, int]], Optional[List[RouteStep]]]:
        """
        Checks if the player's track constitutes a valid, complete route.
        Delegates pathfinding to the pathfinder service.
        """
        if not player.line_card or not player.route_card:
            return False, None, None

        # This will return None if not all required stop signs are on the board.
        stops = player.get_required_stop_coords(self)
        if stops is None: return False, None, None
        
        t1, t2 = self.get_terminal_coords(player.line_card.line_number)
        if not t1 or not t2: return False, None, None

        path1, cost1 = self.pathfinder.find_path(self, player, [t1] + stops + [t2])
        path2, cost2 = self.pathfinder.find_path(self, player, [t2] + stops + [t1])

        valid1, valid2 = (cost1 != float('inf')), (cost2 != float('inf'))
        if not valid1 and not valid2: return False, None, None
        
        chosen_start, optimal_path = (t1, path1) if valid1 and (not valid2 or cost1 <= cost2) else (t2, path2)
        
        if chosen_start:
            return True, chosen_start, optimal_path
        return False, None, None

    def handle_route_completion(self, player: Player, chosen_start: Tuple[int, int], optimal_path: List[RouteStep]):
        """Transitions a player to the DRIVING phase."""
        player.player_state = PlayerState.DRIVING
        player.start_terminal_coord = chosen_start
        player.validated_route = optimal_path
        player.streetcar_path_index = 0
        player.required_node_index = 1
        
        print(f"  Player {player.player_id} streetcar placed at: {player.streetcar_position}")
        
        if self.game_phase == GamePhase.LAYING_TRACK:
             self.game_phase = GamePhase.DRIVING

    def undo_last_action(self) -> bool:
        """Undoes the last command, respecting the current turn's boundary."""
        if self.command_history.get_current_index() > self.turn_start_history_index:
            return self.command_history.undo()
        print("Cannot undo actions from a previous turn.")
        return False

    def redo_last_action(self) -> bool:
        """Redoes the last undone command."""
        return self.command_history.redo()

    def eliminate_player(self, player: Player):
        """Eliminates a player, returning their tiles to the draw pile."""
        if player.player_state == PlayerState.ELIMINATED: return

        print(f"--- Player {player.player_id} has no more legal moves and is ELIMINATED! ---")
        player.player_state = PlayerState.ELIMINATED
        
        if player.hand:
            print(f"  Returning {len(player.hand)} tiles to the draw pile.")
            self.deck_manager.tile_draw_pile.extend(player.hand)
            random.shuffle(self.deck_manager.tile_draw_pile)
            player.hand = []

    def can_player_make_any_move(self, player: Player) -> bool:
        """Performs an exhaustive check for any possible legal move."""
        return self.rule_engine.can_player_make_any_move(self, player)

    def save_game(self, filename: str) -> bool:
        """Saves the current game state to a file."""
        print(f"Saving game state to {filename}...")
        try:
            game_state_data = {
                "num_players": self.num_players,
                "difficulty": self.difficulty,
                "board": self.board.to_dict(),
                "players": [p.to_dict() for p in self.players],
                "tile_draw_pile": [tile.name for tile in self.deck_manager.tile_draw_pile],
                "active_player_index": self.active_player_index,
                "game_phase": self.game_phase.name,
                "current_turn": self.current_turn,
                "actions_taken": self.actions_taken_this_turn,
                "winner_id": self.winner.player_id if self.winner else None,
                "mod_manager": self.mod_manager.to_dict()
            }
            with open(filename, 'w') as f:
                json.dump(game_state_data, f, indent=4)
            print("Save successful.")
            return True
        except Exception as e:
            print(f"!!! Error saving game to {filename}: {e} !!!"); traceback.print_exc(); return False

    @staticmethod
    def load_game(filename: str, tile_types: Dict[str, 'TileType'], mod_manager: 'ModManager') -> Optional['Game']:
        """Loads a game state from a file."""
        print(f"Loading game state from {filename}...")
        try:
            with open(filename, 'r') as f: data = json.load(f)

            player_data = data.get("players", [])
            player_types = ['ai' if p.get('is_ai') else 'human' for p in player_data]
            difficulty = data.get('difficulty', 'normal')

            game = Game(player_types=player_types, difficulty=difficulty, mod_manager=mod_manager)
            
            game.active_player_index = data.get("active_player_index", 0)
            game.game_phase = GamePhase[data.get("game_phase", "LAYING_TRACK")]
            game.current_turn = data.get("current_turn", 1)
            game.actions_taken_this_turn = data.get("actions_taken", 0)
            
            game.board = Board.from_dict(data["board"], tile_types)
            game.players = [Player.from_dict(p_data, tile_types) for p_data in player_data]
            
            winner_id = data.get("winner_id")
            game.winner = game.players[winner_id] if winner_id is not None else None
                
            game.deck_manager.tile_draw_pile = [tile_types[name] for name in data.get("tile_draw_pile", [])]
            game.deck_manager.line_cards_pile = [] # Cards are considered fully dealt
            
            mod_manager.deactivate_all_mods()
            for mod_id in data.get("mod_manager", {}).get("active_mod_ids", []):
                mod_manager.activate_mod(mod_id)

            print(f"Load successful. Phase: {game.game_phase.name}, Turn: {game.current_turn}, Active P: {game.active_player_index}")
            return game
        except Exception as e:
            print(f"!!! Error loading game from {filename}: {e} !!!"); traceback.print_exc(); return None
        
    def copy_for_simulation(self) -> 'Game':
        """Creates a deep copy of the essential game state for AI planning."""
        sim_game = object.__new__(Game)
        
        sim_game.rule_engine = self.rule_engine
        sim_game.pathfinder = self.pathfinder
        sim_game.tile_types = self.tile_types
        sim_game.num_players = self.num_players
        sim_game.MAX_PLAYER_ACTIONS = self.MAX_PLAYER_ACTIONS
        sim_game.level_data = self.level_data
        
        sim_game.board = copy.deepcopy(self.board)
        sim_game.players = copy.deepcopy(self.players)
        
        sim_game.game_phase = self.game_phase
        sim_game.active_player_index = self.active_player_index
        
        # --- START OF CHANGE: Ensure the simulation copy also has these attributes ---
        sim_game.live_auctions = copy.deepcopy(self.live_auctions)
        # --- END OF CHANGE ---
        
        return sim_game
    
    def resolve_auctions_for_player(self, player: Player):
        """
        Resolves auctions, now enforcing the capital cap and donating excess to the Rail Foundation.
        """
        eco_mod = self.mod_manager.available_mods.get('economic_mod')
        if not eco_mod: return

        for i in range(len(self.live_auctions) - 1, -1, -1):
            auction = self.live_auctions[i]
            if auction['seller_id'] == player.player_id and auction['turn_of_resolution'] <= self.current_turn:
                seller = self.players[auction['seller_id']]
                seller_mod_data = seller.components.get('economic_mod')
                if not seller_mod_data: continue

                tile_type = self.tile_types[auction['tile_type_name']]
                payout = 0
                
                # Case 1: No bids
                if not auction['bids']:
                    market_price = eco_mod.get_market_price(self, tile_type)
                    scrapyard_yield = eco_mod.config.get("scrapyard_yield", 0.3)
                    payout = int(market_price * scrapyard_yield)
                    self.deck_manager.initial_tile_counts[tile_type.name] -= 1
                    print(f"Auction for {tile_type.name} received no bids. Defaulting to scrapyard for ${payout}.")
                
                # Case 2: Bids exist
                else:
                    winner_bid = max(auction['bids'], key=lambda b: b['amount'])
                    winner = self.players[winner_bid['bidder_id']]
                    payout = winner_bid['amount']

                    if len(winner.hand) >= self.HAND_TILE_LIMIT:
                        winner.mailbox.append(tile_type)
                        print(f"  Winner P{winner.player_id}'s hand is full. Tile sent to mailbox.")
                    else:
                        winner.hand.append(tile_type)

                    winner.components['economic_mod']['capital'] -= payout
                    winner.hand.append(tile_type)
                    
                    for bid in auction['bids']:
                        self.players[bid['bidder_id']].components['economic_mod']['frozen_capital'] -= bid['amount']
                    print(f"Auction for {tile_type.name} won by P{winner.player_id} for ${payout}.")

                # --- START OF CHANGE: Enforce capital cap and donate excess ---
                current_capital = seller_mod_data.get('capital', 0)
                max_capital = seller_mod_data.get('max_capital', 200)
                
                if current_capital + payout > max_capital:
                    excess = (current_capital + payout) - max_capital
                    self.rail_foundation_capital += excess
                    seller_mod_data['capital'] = max_capital
                    print(f"  Player {seller.player_id} reached max capital. ${excess} donated to the Rail Foundation.")
                else:
                    seller_mod_data['capital'] += payout
                # --- END OF CHANGE ---
                
                self.live_auctions.pop(i)