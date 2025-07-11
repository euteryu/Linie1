# mods/economic_mod/economic_commands.py
from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from game_logic.commands import Command

if TYPE_CHECKING:
    from game_logic.game import Game
    from game_logic.player import Player
    from game_logic.tile import TileType

# This is a renamed and re-themed version of the CreateSuperTileCommand
class PriorityRequisitionCommand(Command):
    """A command to handle the creation of a special order tile, making it undoable."""
    def __init__(self, game: 'Game', player: 'Player', cost: int, mod_id: str, requisitioned_tile_instance: 'TileType'):
        super().__init__(game)
        self.player = player
        self.cost = cost
        self.mod_id = mod_id
        # This is the "blank check" tile that appears in the hand
        self.requisitioned_tile = requisitioned_tile_instance
        self._capital_spent = False

    def execute(self) -> bool:
        capital_pool = self.player.components.get(self.mod_id)
        if not capital_pool or capital_pool.get('capital', 0) < self.cost:
            print(f"[{self.mod_id}] Command Failed: Not enough Capital.")
            return False

        capital_pool['capital'] -= self.cost
        self.player.hand.append(self.requisitioned_tile)
        self._capital_spent = True
        
        print(f"[{self.mod_id}] Priority Requisition approved. Permit added to hand.")
        return True

    def undo(self) -> bool:
        if not self._capital_spent:
            return False
            
        try:
            self.player.hand.remove(self.requisitioned_tile)
            capital_pool = self.player.components.get(self.mod_id)
            if capital_pool:
                capital_pool['capital'] += self.cost
            print(f"[{self.mod_id}] Priority Requisition undone.")
            return True
        except ValueError:
            print(f"[{self.mod_id}] Undo Failed: Requisition Permit not found in hand.")
            return False
            
    def get_description(self) -> str:
        return f"Priority Requisition (Cost: {self.cost})"
    
class SellToScrapyardCommand(Command):
    """A command to handle selling a tile from hand for Capital, consuming one action."""
    def __init__(self, game: 'Game', player: 'Player', mod_id: str, tile_to_sell: 'TileType', capital_reward: int):
        super().__init__(game)
        self.player = player
        self.mod_id = mod_id
        self.tile_to_sell = tile_to_sell
        self.capital_reward = capital_reward
        self._tile_sold = False

    def execute(self) -> bool:
        """Executes the sell action, now with a Capital cap check."""
        # Check action limit
        if self.game.actions_taken_this_turn >= self.game.MAX_PLAYER_ACTIONS:
            print(f"[{self.mod_id}] Sell Command Failed: Action limit reached.")
            return False

        # Check if player has the tile
        if self.tile_to_sell not in self.player.hand:
            print(f"[{self.mod_id}] Sell Command Failed: Tile {self.tile_to_sell.name} not in hand.")
            return False

        capital_pool = self.player.components.get(self.mod_id)
        if not capital_pool:
            return False

        # --- START OF FIX: Enforce Capital Cap ---
        current_capital = capital_pool.get('capital', 0)
        max_capital = capital_pool.get('max_capital', 200)
        
        if current_capital + self.capital_reward > max_capital:
            print(f"[{self.mod_id}] Sell Command Failed: Sale would exceed Capital limit ({current_capital + self.capital_reward} / {max_capital}).")
            # We need to inform the player via the UI message
            self.game.visualizer.current_state.message = "Cannot sell: Exceeds Capital limit."
            return False
        # --- END OF FIX ---

        self.player.hand.remove(self.tile_to_sell)
        self.game.deck_manager.tile_draw_pile.insert(0, self.tile_to_sell)
        
        capital_pool['capital'] += self.capital_reward # No longer need min() check because of the guard clause above
        self._tile_sold = True
        
        self.game.actions_taken_this_turn += 1
        
        print(f"[{self.mod_id}] Sold {self.tile_to_sell.name} for ${self.capital_reward} Capital. Actions used: {self.game.actions_taken_this_turn}/{self.game.MAX_PLAYER_ACTIONS}")
        return True

    def undo(self) -> bool:
        if not self._tile_sold:
            return False

        try:
            if self.game.deck_manager.tile_draw_pile[0] == self.tile_to_sell:
                tile_to_return = self.game.deck_manager.tile_draw_pile.pop(0)
                self.player.hand.append(tile_to_return)
            else:
                self.game.deck_manager.tile_draw_pile.remove(self.tile_to_sell)
                self.player.hand.append(self.tile_to_sell)

            capital_pool = self.player.components.get(self.mod_id)
            if capital_pool:
                capital_pool['capital'] -= self.capital_reward
            
            # --- START OF FIX 3: Decrement action counter ---
            self.game.actions_taken_this_turn -= 1
            # --- END OF FIX 3 ---

            print(f"[{self.mod_id}] Sell undone. {self.tile_to_sell.name} returned to hand.")
            return True
        except (ValueError, IndexError):
            print(f"[{self.mod_id}] Undo Sell Failed: Tile not found in draw pile.")
            return False
            
    def get_description(self) -> str:
        return f"Sell {self.tile_to_sell.name} for ${self.capital_reward}"