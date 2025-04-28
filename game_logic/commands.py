# game_logic/commands.py
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from typing import Tuple, Optional
from .tile import TileType, PlacedTile
from .player import Player
from .enums import PlayerState # If needed

# Avoid circular imports using TYPE_CHECKING
if TYPE_CHECKING:
    from .game import Game

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
class MoveCommand(Command):
    def __init__(self, game: 'Game', player: Player,
                 target_coord: Tuple[int, int]):
        super().__init__(game)
        self.player = player
        self.target_coord = target_coord
        # Store state for undo
        self._original_pos: Optional[Tuple[int, int]] = None
        self._original_node_index: int = 0
        # Store whether index was advanced during execute for precise undo
        self._advanced_index_on_execute = False

    def execute(self) -> bool:
        print(f"Executing Move: P{self.player.player_id} target {self.target_coord}")
        if self.player.streetcar_position is None:
            print("--> Move Failed: Player has no current position.")
            return False

        # --- Store pre-move state for Undo ---
        self._original_pos = self.player.streetcar_position
        self._original_node_index = self.player.required_node_index
        self._advanced_index_on_execute = False # Reset flag

        # --- Perform the actual position update ---
        # Call the simple Game method to update the player attribute
        self.game.move_streetcar(self.player, self.target_coord)

        # --- Check if the NEW position reached the next required node ---
        next_required_node = self.player.get_next_target_node(self.game)
        if next_required_node and self.target_coord == next_required_node:
             print(f"   (Reached required node "
                   f"{self.player.required_node_index + 1})")
             self.player.required_node_index += 1
             self._advanced_index_on_execute = True # Mark index change

        # --- Check Win Condition AFTER position and index are updated ---
        # Note: check_win_condition itself sets game phase/winner if true
        win = self.game.check_win_condition(self.player)

        print(f"--> Move Execute SUCCESS. Landed at {self.target_coord}. Win: {win}")
        return True # Command execution was successful

    def undo(self) -> bool:
        print(f"Undoing Move: P{self.player.player_id} back to {self._original_pos}")
        if self._original_pos is None:
            print("--> Undo Move Failed: No original position saved.")
            return False

        # Check if game ended, revert if undoing winning move
        if self.game.game_phase == GamePhase.GAME_OVER and \
           self.game.winner == self.player:
             print("   (Undoing winning move, resetting game phase)")
             self.game.game_phase = GamePhase.DRIVING
             self.game.winner = None
             self.player.player_state = PlayerState.DRIVING # Ensure state is correct

        # --- Restore position and node index ---
        # Use simple Game method to update position
        self.game.move_streetcar(self.player, self._original_pos)
        # Only revert index if it was advanced during execute
        # This prevents decrementing index multiple times if undoing non-advancing moves
        # However, the current system resets action count on undo, allowing re-roll,
        # so restoring the exact original index is correct.
        self.player.required_node_index = self._original_node_index

        print(f"--> Undo Move SUCCESS. Pos: {self.player.streetcar_position}, "
              f"Idx: {self.player.required_node_index}")
        return True

    def get_description(self) -> str:
         return (f"Move P{self.player.player_id} to "
                 f"{self.target_coord}")