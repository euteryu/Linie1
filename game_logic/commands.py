# game_logic/commands.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Tuple, Optional, Dict, List
import copy

from .enums import PlayerState, Direction, GamePhase
from .tile import TileType, PlacedTile
# REMOVED: from .player import Player  <- This was the problem

# Avoid circular imports using TYPE_CHECKING
if TYPE_CHECKING:
    from .game import Game
    # THIS IS THE FIX: Only import Player for type hinting, not at runtime.
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

    # Optional: Add description for logging/UI
    def get_description(self) -> str:
        return self.__class__.__name__ # Default description is class name

class PlaceTileCommand(Command):
    def __init__(self, game: 'Game', player: Player, tile_type: TileType,
                 orientation: int, row: int, col: int):
        super().__init__(game)
        self.player = player
        self.tile_type = tile_type
        self.orientation = orientation
        self.row = row
        self.col = col
        # Store state needed for undo
        self._original_hand_contains_tile = False # Was tile originally in hand?
        self._stop_sign_placed = False
        self._building_id_stopped: Optional[str] = None

    def execute(self) -> bool:
        print(f"Executing Place: P{self.player.player_id} places {self.tile_type.name} at ({self.row},{self.col})")
        # 1. Check if player has the tile
        if self.tile_type not in self.player.hand:
            print(f"--> Place Failed: Player lacks {self.tile_type.name}.")
            return False
        self._original_hand_contains_tile = True

        # 2. Check board validity
        is_valid, message = self.game.check_placement_validity(
            self.tile_type, self.orientation, self.row, self.col
        )
        if not is_valid:
            print(f"--> Place Failed: {message}")
            return False

        # 3. Perform action
        self.player.hand.remove(self.tile_type)
        placed_tile = PlacedTile(self.tile_type, self.orientation)
        self.game.board.set_tile(self.row, self.col, placed_tile)

        # 4. Check for stop sign (Store info for undo)
        # Temporarily clear potential stop sign before check
        self._stop_sign_placed = False
        self._building_id_stopped = None
        # Find which building might get stop sign
        building_before = self.game.board.buildings_with_stops.copy()
        self.game._check_and_place_stop_sign(placed_tile, self.row, self.col)
        building_after = self.game.board.buildings_with_stops
        newly_stopped = building_after - building_before
        if newly_stopped:
             self._stop_sign_placed = True
             # Assuming only one stop per placement
             self._building_id_stopped = newly_stopped.pop()

        # Note: Action count increment moved to CommandHistory/Turn management
        print(f"--> Place SUCCESS.")
        return True

    def undo(self) -> bool:
        print(f"Undoing Place: Removing {self.tile_type.name} from ({self.row},{self.col})")
        # Reverse the actions in opposite order
        # 1. Remove stop sign if placed
        if self._stop_sign_placed and self._building_id_stopped:
            tile = self.game.board.get_tile(self.row, self.col)
            if tile and tile.has_stop_sign: # Check if sign is still there
                 tile.has_stop_sign = False
                 self.game.board.buildings_with_stops.discard(self._building_id_stopped)
                 if self._building_id_stopped in self.game.board.building_stop_locations:
                     del self.game.board.building_stop_locations[self._building_id_stopped]
                 print(f"    Undid stop sign for {self._building_id_stopped}")

        # 2. Remove tile from board
        self.game.board.set_tile(self.row, self.col, None)

        # 3. Return tile to hand (only if originally taken)
        if self._original_hand_contains_tile:
            self.player.hand.append(self.tile_type) # Add it back
            print(f"    Returned {self.tile_type.name} to P{self.player.player_id} hand.")

        # Note: Action count decrement handled by CommandHistory/Turn management
        print("--> Undo Place SUCCESS.")
        return True

# --- Exchange Command (More Complex Undo) ---
class ExchangeTileCommand(Command):
    def __init__(self, game: 'Game', player: Player, new_tile_type: TileType,
                 new_orientation: int, row: int, col: int):
        super().__init__(game)
        self.player = player
        self.new_tile_type = new_tile_type
        self.new_orientation = new_orientation
        self.row = row
        self.col = col
        # Store state needed for undo
        self._original_hand_contains_tile = False
        self._old_placed_tile_data: Optional[Dict] = None # Save old tile state

    def execute(self) -> bool:
        print(f"Executing Exchange: P{self.player.player_id} exchanges for {self.new_tile_type.name} at ({self.row},{self.col})")
        # 1. Check if player has the new tile
        if self.new_tile_type not in self.player.hand:
            print(f"--> Exchange Failed: Player lacks {self.new_tile_type.name}.")
            return False
        self._original_hand_contains_tile = True

        # 2. Check board validity (check_exchange_validity needs refactoring
        #    to not require player hand, or we duplicate logic here)
        # --- Simplified validity check for now ---
        old_placed_tile = self.game.board.get_tile(self.row, self.col)
        if not old_placed_tile: return False # No tile
        if not self.game.board.is_playable_coordinate(self.row, self.col): return False
        if old_placed_tile.is_terminal: return False
        if not old_placed_tile.tile_type.is_swappable: return False
        if old_placed_tile.has_stop_sign: return False
        # TODO: Add full connection validation check here, bypassing hand check!

        # 3. Store old tile data for undo
        self._old_placed_tile_data = old_placed_tile.to_dict()

        # 4. Perform exchange
        self.player.hand.remove(self.new_tile_type)
        self.player.hand.append(old_placed_tile.tile_type)
        new_placed_tile = PlacedTile(self.new_tile_type, self.new_orientation)
        self.game.board.set_tile(self.row, self.col, new_placed_tile)

        print("--> Exchange SUCCESS.")
        return True

    def undo(self) -> bool:
        print(f"Undoing Exchange at ({self.row},{self.col})")
        if self._old_placed_tile_data is None:
            print("--> Undo Exchange Failed: No old tile data saved.")
            return False

        # 1. Remove new tile from board and restore old one
        current_tile = self.game.board.get_tile(self.row, self.col) # This is the 'new' tile
        if not current_tile or current_tile.tile_type != self.new_tile_type:
            print("--> Undo Exchange Failed: Tile on board doesn't match expected.")
            return False

        old_tile = PlacedTile.from_dict(self._old_placed_tile_data, self.game.tile_types)
        if old_tile is None:
             print("--> Undo Exchange Failed: Could not reconstruct old tile.")
             return False
        self.game.board.set_tile(self.row, self.col, old_tile) # Restore old tile

        # 2. Swap tiles back in hand
        # Remove the tile that was returned from the board
        if old_tile.tile_type in self.player.hand:
             self.player.hand.remove(old_tile.tile_type)
        else: print(f"Warning: Tile {old_tile.tile_type.name} not found in hand during undo.")
        # Add back the tile that was used for the exchange
        if self._original_hand_contains_tile:
             self.player.hand.append(self.new_tile_type)

        print("--> Undo Exchange SUCCESS.")
        return True

# --- Driving Commands (Simpler Undo) ---
# game_logic/commands.py
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Tuple, Optional, Dict
from .enums import PlayerState, Direction, GamePhase # <-- ADDED GamePhase HERE
from .tile import TileType, PlacedTile
from .player import Player

if TYPE_CHECKING:
    from .game import Game

class Command(ABC):
    def __init__(self, game: 'Game'):
        self.game = game
    @abstractmethod
    def execute(self) -> bool: pass
    @abstractmethod
    def undo(self) -> bool: pass
    def get_description(self) -> str: return self.__class__.__name__

class PlaceTileCommand(Command):
    def __init__(self, game: 'Game', player: Player, tile_type: TileType, orientation: int, row: int, col: int):
        super().__init__(game)
        self.player, self.tile_type, self.orientation, self.row, self.col = player, tile_type, orientation, row, col
        self._original_hand_contains_tile, self._stop_sign_placed, self._building_id_stopped = False, False, None
    def execute(self) -> bool:
        # --- ADDED DEBUG PRINT ---
        print(f"--- [COMMAND] Executing PlaceTileCommand: P{self.player.player_id} places {self.tile_type.name} at ({self.row},{self.col}) ---")

        # 1. Check if player has the tile (already validated, but good practice)
        if self.tile_type not in self.player.hand:
            print(f"  [COMMAND-ERROR] Player lacks {self.tile_type.name}.")
            return False
        self._original_hand_contains_tile = True

        # 2. Perform action
        print(f"  [COMMAND-STATE] Removing '{self.tile_type.name}' from Player {self.player.player_id}'s hand.")
        self.player.hand.remove(self.tile_type)
        
        placed_tile = PlacedTile(self.tile_type, self.orientation)
        print(f"  [COMMAND-STATE] Setting tile on board at ({self.row},{self.col}) to: {placed_tile}")
        self.game.board.set_tile(self.row, self.col, placed_tile)

        # 3. Check for stop sign
        building_before = self.game.board.buildings_with_stops.copy()
        self.game._check_and_place_stop_sign(placed_tile, self.row, self.col)
        newly_stopped = self.game.board.buildings_with_stops - building_before
        if newly_stopped:
             self._stop_sign_placed = True
             self._building_id_stopped = newly_stopped.pop()
             print(f"  [COMMAND-STATE] Stop sign created for building {self._building_id_stopped}.")

        print(f"--- [COMMAND] PlaceTileCommand Execute SUCCESS ---")
        return True
    def undo(self) -> bool:
        if self._stop_sign_placed and self._building_id_stopped:
            tile = self.game.board.get_tile(self.row, self.col)
            if tile and tile.has_stop_sign:
                 tile.has_stop_sign = False
                 self.game.board.buildings_with_stops.discard(self._building_id_stopped)
                 if self._building_id_stopped in self.game.board.building_stop_locations:
                     del self.game.board.building_stop_locations[self._building_id_stopped]
        self.game.board.set_tile(self.row, self.col, None)
        if self._original_hand_contains_tile: self.player.hand.append(self.tile_type)
        return True

class ExchangeTileCommand(Command):
    def __init__(self, game: 'Game', player: Player, new_tile_type: TileType, new_orientation: int, row: int, col: int):
        super().__init__(game)
        self.player, self.new_tile_type, self.new_orientation, self.row, self.col = player, new_tile_type, new_orientation, row, col
        self._original_hand_contains_tile, self._old_placed_tile_data = False, None
    def execute(self) -> bool:
        # --- ADDED DEBUG PRINT ---
        print(f"--- [COMMAND] Executing ExchangeTileCommand: P{self.player.player_id} at ({self.row},{self.col}) with {self.new_tile_type.name} ---")
        
        if self.new_tile_type not in self.player.hand:
            print(f"  [COMMAND-ERROR] Player lacks {self.new_tile_type.name}.")
            return False
        self._original_hand_contains_tile = True

        old_placed_tile = self.game.board.get_tile(self.row, self.col)
        if not old_placed_tile:
            print(f"  [COMMAND-ERROR] No tile on board at ({self.row},{self.col}) to exchange.")
            return False

        # Store old tile data for undo
        self._old_placed_tile_data = old_placed_tile.to_dict()
        print(f"  [COMMAND-STATE] Storing old tile for undo: {old_placed_tile}")

        # Perform exchange
        print(f"  [COMMAND-STATE] Removing '{self.new_tile_type.name}' from Player {self.player.player_id}'s hand.")
        self.player.hand.remove(self.new_tile_type)
        print(f"  [COMMAND-STATE] Adding '{old_placed_tile.tile_type.name}' to Player {self.player.player_id}'s hand.")
        self.player.hand.append(old_placed_tile.tile_type)
        
        new_placed_tile = PlacedTile(self.new_tile_type, self.new_orientation)
        print(f"  [COMMAND-STATE] Setting tile on board at ({self.row},{self.col}) to: {new_placed_tile}")
        self.game.board.set_tile(self.row, self.col, new_placed_tile)

        print("--- [COMMAND] ExchangeTileCommand Execute SUCCESS ---")
        return True
    def undo(self) -> bool:
        if self._old_placed_tile_data is None: return False
        old_tile = PlacedTile.from_dict(self._old_placed_tile_data, self.game.tile_types)
        if not old_tile: return False
        self.game.board.set_tile(self.row, self.col, old_tile)
        if old_tile.tile_type in self.player.hand: self.player.hand.remove(old_tile.tile_type)
        if self._original_hand_contains_tile: self.player.hand.append(self.new_tile_type)
        return True

class MoveCommand(Command):
    def __init__(self, game: 'Game', player: Player, target_path_index: int):
        super().__init__(game)
        self.player = player
        self.target_path_index = target_path_index
        # Store state for undo
        self._original_path_index: int = 0
        self._original_node_index: int = 0
        self._was_game_over = False

    def execute(self) -> bool:
        print(f"Executing Move: P{self.player.player_id} to path index {self.target_path_index}")

        self._original_path_index = self.player.streetcar_path_index
        self._original_node_index = self.player.required_node_index
        self._was_game_over = self.game.game_phase == GamePhase.GAME_OVER

        self.game.move_streetcar(self.player, self.target_path_index)
        
        # --- THIS IS THE FIX ---
        # The command's execution triggers the win condition check via the rule engine.
        win = self.game.rule_engine.check_win_condition(self.game, self.player)
        # --- END OF FIX ---

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
        
        # --- THIS IS THE FIX ---
        # The command MUST check against the game's state before running.
        if self.game.actions_taken_this_turn + len(self.moves_to_perform) > self.game.MAX_PLAYER_ACTIONS:
            print(f"Command Error: Cannot perform {len(self.moves_to_perform)} actions. "
                  f"({self.game.actions_taken_this_turn}/{self.game.MAX_PLAYER_ACTIONS} already taken).")
            return False
        # --- END OF FIX ---

        self._undo_data = []
        try:
            for move in self.moves_to_perform:
                coord = tuple(move['coord'])
                r, c = coord
                # Re-fetch the tile type object to ensure it's not a stale reference
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

            # --- THIS IS THE SECOND PART OF THE FIX ---
            # The command is the single source of truth for how many actions it represents.
            # It must update the game's counter.
            self.game.actions_taken_this_turn += len(self.moves_to_perform)
            print(f"--- [COMMAND] CombinedAction Execute SUCCESS. Actions taken this turn: {self.game.actions_taken_this_turn} ---")
            # --- END OF FIX ---
            return True

        except (ValueError, KeyError, IndexError) as e:
            print(f"--- [COMMAND-ERROR] CombinedAction failed: {e}. Rolling back... ---")
            self.undo() # Roll back any partial execution
            return False

    def undo(self) -> bool:
        print(f"--- [COMMAND] Undoing CombinedAction for P{self.player.player_id} ---")
        
        # --- THIS IS THE FIX FOR UNDO ---
        # The command must correctly decrement the action counter it previously incremented.
        self.game.actions_taken_this_turn -= len(self._undo_data)
        # --- END OF FIX ---
        
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