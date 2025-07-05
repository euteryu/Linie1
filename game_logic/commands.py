# game_logic/commands.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Tuple, Optional, Dict, List
import copy

from .enums import PlayerState, Direction, GamePhase
from .tile import TileType, PlacedTile

# Avoid circular imports using TYPE_CHECKING
if TYPE_CHECKING:
    from .game import Game
    from .player import Player

class Command(ABC):
    """Abstract base class for executable commands with undo."""
    def __init__(self, game: 'Game'):
        self.game = game # Store reference to the game model

    @abstractmethod
    def execute(self) -> bool:
        """Executes the command. Returns True on success, False on failure."""
        pass

    @abstractmethod
    def undo(self) -> bool:
        """Reverses the command. Returns True on success, False on failure."""
        pass

    def get_description(self) -> str:
        """Optional: Add description for logging/UI."""
        return self.__class__.__name__ # Default description is class name

class PlaceTileCommand(Command):
    def __init__(self, game: 'Game', player: 'Player', tile_type: TileType,
                 orientation: int, row: int, col: int):
        super().__init__(game)
        self.player = player
        self.tile_type = tile_type
        self.orientation = orientation
        self.row = row
        self.col = col
        # Store state needed for undo
        self._original_hand_contains_tile = False
        self._stop_sign_placed = False
        self._building_id_stopped: Optional[str] = None

    def execute(self) -> bool:
        print(f"Executing Place: P{self.player.player_id} places {self.tile_type.name} at ({self.row},{self.col})")
        
        if self.game.actions_taken_this_turn >= self.game.MAX_PLAYER_ACTIONS:
            print("--> Place Failed: Action limit reached.")
            return False

        if self.tile_type not in self.player.hand:
            print(f"--> Place Failed: Player lacks {self.tile_type.name}.")
            return False
        self._original_hand_contains_tile = True

        is_valid, message = self.game.check_placement_validity(
            self.tile_type, self.orientation, self.row, self.col
        )
        if not is_valid:
            print(f"--> Place Failed: {message}")
            return False

        self.player.hand.remove(self.tile_type)
        placed_tile = PlacedTile(self.tile_type, self.orientation)
        self.game.board.set_tile(self.row, self.col, placed_tile)

        building_before = self.game.board.buildings_with_stops.copy()
        self.game._check_and_place_stop_sign(placed_tile, self.row, self.col)
        newly_stopped = self.game.board.buildings_with_stops - building_before
        if newly_stopped:
             self._stop_sign_placed = True
             self._building_id_stopped = newly_stopped.pop()

        self.game.actions_taken_this_turn += 1
        print(f"--> Place SUCCESS.")
        return True

    def undo(self) -> bool:
        print(f"Undoing Place: Removing {self.tile_type.name} from ({self.row},{self.col})")
        
        if self._stop_sign_placed and self._building_id_stopped:
            tile = self.game.board.get_tile(self.row, self.col)
            if tile and tile.has_stop_sign:
                 tile.has_stop_sign = False
                 self.game.board.buildings_with_stops.discard(self._building_id_stopped)
                 if self._building_id_stopped in self.game.board.building_stop_locations:
                     del self.game.board.building_stop_locations[self._building_id_stopped]

        self.game.board.set_tile(self.row, self.col, None)
        if self._original_hand_contains_tile:
            self.player.hand.append(self.tile_type)

        self.game.actions_taken_this_turn -= 1
        print("--> Undo Place SUCCESS.")
        return True

class ExchangeTileCommand(Command):
    def __init__(self, game: 'Game', player: 'Player', new_tile_type: TileType,
                 new_orientation: int, row: int, col: int):
        super().__init__(game)
        self.player = player
        self.new_tile_type = new_tile_type
        self.new_orientation = new_orientation
        self.row = row
        self.col = col
        self._original_hand_contains_tile = False
        self._old_placed_tile_data: Optional[Dict] = None

    def execute(self) -> bool:
        print(f"Executing Exchange: P{self.player.player_id} exchanges for {self.new_tile_type.name} at ({self.row},{self.col})")
        
        if self.game.actions_taken_this_turn >= self.game.MAX_PLAYER_ACTIONS:
            print("--> Exchange Failed: Action limit reached.")
            return False

        if self.new_tile_type not in self.player.hand:
            print(f"--> Exchange Failed: Player lacks {self.new_tile_type.name}.")
            return False
        self._original_hand_contains_tile = True

        # Simplified validity check for brevity; full logic is in RuleEngine
        old_placed_tile = self.game.board.get_tile(self.row, self.col)
        if not self.game.check_exchange_validity(self.player, self.new_tile_type, self.new_orientation, self.row, self.col)[0]:
            print("--> Exchange Failed: Move is invalid.")
            return False

        self._old_placed_tile_data = old_placed_tile.to_dict()

        self.player.hand.remove(self.new_tile_type)
        self.player.hand.append(old_placed_tile.tile_type)
        new_placed_tile = PlacedTile(self.new_tile_type, self.new_orientation)
        self.game.board.set_tile(self.row, self.col, new_placed_tile)
        
        self.game.actions_taken_this_turn += 1
        print("--> Exchange SUCCESS.")
        return True

    def undo(self) -> bool:
        print(f"Undoing Exchange at ({self.row},{self.col})")
        if self._old_placed_tile_data is None:
            return False

        old_tile = PlacedTile.from_dict(self._old_placed_tile_data, self.game.tile_types)
        if old_tile is None:
             return False
        self.game.board.set_tile(self.row, self.col, old_tile)

        if old_tile.tile_type in self.player.hand:
             self.player.hand.remove(old_tile.tile_type)
        if self._original_hand_contains_tile:
             self.player.hand.append(self.new_tile_type)
        
        self.game.actions_taken_this_turn -= 1
        print("--> Undo Exchange SUCCESS.")
        return True

class MoveCommand(Command):
    def __init__(self, game: 'Game', player: Player, target_path_index: int):
        super().__init__(game)
        self.player = player
        self.target_path_index = target_path_index
        self._original_path_index: int = 0
        self._original_node_index: int = 0
        self._was_game_over = False

    def execute(self) -> bool:
        print(f"Executing Move: P{self.player.player_id} to path index {self.target_path_index}")
        self._original_path_index = self.player.streetcar_path_index
        self._original_node_index = self.player.required_node_index
        self._was_game_over = self.game.game_phase == GamePhase.GAME_OVER

        self.game.move_streetcar(self.player, self.target_path_index)
        
        win = self.game.rule_engine.check_win_condition(self.game, self.player)

        # Driving is a full turn's action.
        self.game.actions_taken_this_turn = self.game.MAX_PLAYER_ACTIONS
        
        print(f"--> Move Execute SUCCESS. Landed at {self.player.streetcar_position}. Win: {win}")
        return True

    def undo(self) -> bool:
        print(f"Undoing Move: P{self.player.player_id} back to path index {self._original_path_index}")
        if not self._was_game_over and self.game.game_phase == GamePhase.GAME_OVER:
             self.game.game_phase = GamePhase.DRIVING
             self.game.winner = None
             self.player.player_state = PlayerState.DRIVING

        self.player.streetcar_path_index = self._original_path_index
        self.player.required_node_index = self._original_node_index

        # Undoing a driving move resets the action counter for that turn.
        self.game.actions_taken_this_turn = 0

        print(f"--> Undo Move SUCCESS. Pos: {self.player.streetcar_position}, Node Idx: {self.player.required_node_index}")
        return True

    def get_description(self) -> str:
         return f"Move P{self.player.player_id} to path index {self.target_path_index}"
    
class CombinedActionCommand(Command):
    """
    A single command that executes multiple sub-actions (place/exchange) atomically.
    This allows validating an entire turn's worth of moves before committing.
    """
    def __init__(self, game: 'Game', player: 'Player', staged_moves: List[Dict]):
        super().__init__(game)
        self.player = player
        self.moves_to_perform = copy.deepcopy(staged_moves)
        self._undo_data = []

    def execute(self) -> bool:
        print(f"--- [COMMAND] Executing CombinedAction for P{self.player.player_id} ---")
        
        if self.game.actions_taken_this_turn + len(self.moves_to_perform) > self.game.MAX_PLAYER_ACTIONS:
            print(f"Command Error: Cannot perform {len(self.moves_to_perform)} actions. "
                  f"({self.game.actions_taken_this_turn}/{self.game.MAX_PLAYER_ACTIONS} already taken).")
            return False

        self._undo_data = []
        try:
            for move in self.moves_to_perform:
                coord = tuple(move['coord'])
                r, c = coord
                tile_type = next(t for t in self.game.tile_types.values() if t.name == move['tile_type'].name)
                
                if move['action_type'] == 'place':
                    undo_entry = {'type': 'place', 'coord': coord, 'tile_type_name': tile_type.name, 'stop_placed': False, 'building_id': None}
                    self.player.hand.remove(tile_type)
                    placed_tile = PlacedTile(tile_type, move['orientation'])
                    self.game.board.set_tile(r, c, placed_tile)

                    building_before = self.game.board.buildings_with_stops.copy()
                    self.game._check_and_place_stop_sign(placed_tile, r, c)
                    newly_stopped = self.game.board.buildings_with_stops - building_before
                    if newly_stopped:
                        undo_entry['stop_placed'] = True
                        undo_entry['building_id'] = newly_stopped.pop()
                    self._undo_data.append(undo_entry)
                
                elif move['action_type'] == 'exchange':
                    old_placed_tile = self.game.board.get_tile(r, c)
                    if not old_placed_tile: raise ValueError(f"Exchange failed: No tile at {coord}.")
                    self._undo_data.append({'type': 'exchange', 'coord': coord, 'new_tile_type_name': tile_type.name, 'old_placed_tile_data': old_placed_tile.to_dict()})
                    self.player.hand.remove(tile_type)
                    self.player.hand.append(old_placed_tile.tile_type)
                    new_placed_tile = PlacedTile(tile_type, move['orientation'])
                    self.game.board.set_tile(r, c, new_placed_tile)

            self.game.actions_taken_this_turn += len(self.moves_to_perform)
            print(f"--- [COMMAND] CombinedAction Execute SUCCESS. Actions taken this turn: {self.game.actions_taken_this_turn} ---")
            return True

        except (ValueError, KeyError, IndexError) as e:
            print(f"--- [COMMAND-ERROR] CombinedAction failed: {e}. Rolling back... ---")
            self.undo() # Roll back any partial execution
            return False

    def undo(self) -> bool:
        print(f"--- [COMMAND] Undoing CombinedAction for P{self.player.player_id} ---")
        
        self.game.actions_taken_this_turn -= len(self._undo_data)
        
        for undo_action in reversed(self._undo_data):
            coord = undo_action['coord']
            r, c = coord
            
            if undo_action['type'] == 'place':
                tile_to_return = self.game.tile_types[undo_action['tile_type_name']]
                if undo_action['stop_placed'] and (building_id := undo_action['building_id']):
                    tile = self.game.board.get_tile(r, c)
                    if tile and tile.has_stop_sign:
                        tile.has_stop_sign = False
                        self.game.board.buildings_with_stops.discard(building_id)
                        if building_id in self.game.board.building_stop_locations:
                            del self.game.board.building_stop_locations[building_id]
                self.game.board.set_tile(r, c, None)
                self.player.hand.append(tile_to_return)

            elif undo_action['type'] == 'exchange':
                old_tile = PlacedTile.from_dict(undo_action['old_placed_tile_data'], self.game.tile_types)
                new_tile_type = self.game.tile_types[undo_action['new_tile_type_name']]
                if not old_tile: return False
                self.game.board.set_tile(r, c, old_tile)
                if old_tile.tile_type in self.player.hand: self.player.hand.remove(old_tile.tile_type)
                self.player.hand.append(new_tile_type)

        self._undo_data = []
        print(f"--- [COMMAND] CombinedAction Undo SUCCESS. Actions taken this turn: {self.game.actions_taken_this_turn} ---")
        return True

    def get_description(self) -> str:
        return f"Commit {len(self.moves_to_perform)} staged actions"