# mods/economic_mod/economic_commands.py
from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from game_logic.commands import Command

if TYPE_CHECKING:
    from game_logic.game import Game
    from game_logic.player import Player
    from game_logic.tile import TileType

# PriorityRequisitionCommand is correct and remains here...
class PriorityRequisitionCommand(Command):
    # ... (implementation is correct from previous step)
    pass

# --- NEW COMMAND ---
class SellToScrapyardCommand(Command):
    """A command to handle selling a tile from hand for Capital."""
    def __init__(self, game: 'Game', player: 'Player', mod_id: str, tile_to_sell: 'TileType', capital_reward: int):
        super().__init__(game)
        self.player = player
        self.mod_id = mod_id
        self.tile_to_sell = tile_to_sell
        self.capital_reward = capital_reward
        self._tile_sold = False

    def execute(self) -> bool:
        if self.tile_to_sell not in self.player.hand:
            print(f"[{self.mod_id}] Sell Command Failed: Tile {self.tile_to_sell.name} not in hand.")
            return False

        capital_pool = self.player.components.get(self.mod_id)
        if not capital_pool:
            return False

        self.player.hand.remove(self.tile_to_sell)
        # For simplicity, sold tiles go back to the bottom of the draw pile.
        self.game.deck_manager.tile_draw_pile.insert(0, self.tile_to_sell)
        
        capital_pool['capital'] = min(capital_pool['max_capital'], capital_pool['capital'] + self.capital_reward)
        self._tile_sold = True
        
        print(f"[{self.mod_id}] Sold {self.tile_to_sell.name} for ${self.capital_reward} Capital.")
        return True

    def undo(self) -> bool:
        if not self._tile_sold:
            return False

        try:
            # Take the tile back from the draw pile (assuming it's the last one we added)
            # A more robust system would search, but for now, this works.
            if self.game.deck_manager.tile_draw_pile[0] == self.tile_to_sell:
                tile_to_return = self.game.deck_manager.tile_draw_pile.pop(0)
                self.player.hand.append(tile_to_return)
            else:
                # Fallback if the pile was shuffled or changed.
                self.game.deck_manager.tile_draw_pile.remove(self.tile_to_sell)
                self.player.hand.append(self.tile_to_sell)

            capital_pool = self.player.components.get(self.mod_id)
            if capital_pool:
                capital_pool['capital'] -= self.capital_reward
            
            print(f"[{self.mod_id}] Sell undone. {self.tile_to_sell.name} returned to hand.")
            return True
        except (ValueError, IndexError):
            print(f"[{self.mod_id}] Undo Sell Failed: Tile not found in draw pile.")
            return False
            
    def get_description(self) -> str:
        return f"Sell {self.tile_to_sell.name} for ${self.capital_reward}"