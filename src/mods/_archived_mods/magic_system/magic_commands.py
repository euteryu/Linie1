# mods/magic_system/magic_commands.py
from __future__ import annotations
from typing import TYPE_CHECKING, Optional

# Import the base Command class from the core game logic
from game_logic.commands import Command

if TYPE_CHECKING:
    from game_logic.game import Game
    from game_logic.player import Player
    from game_logic.tile import TileType

class CreateSuperTileCommand(Command):
    """A command to handle the creation of a Super Tile, making it undoable."""
    def __init__(self, game: 'Game', player: 'Player', cost: int, mod_id: str, super_tile_instance: 'TileType'):
        super().__init__(game)
        self.player = player
        self.cost = cost
        self.mod_id = mod_id
        self.super_tile = super_tile_instance
        self._mana_spent = False

    def execute(self) -> bool:
        mana_pool = self.player.components.get(self.mod_id)
        if not mana_pool or mana_pool.get('mana', 0) < self.cost:
            print(f"[{self.mod_id}] Command Failed: Not enough mana.")
            return False

        # Perform the action
        mana_pool['mana'] -= self.cost
        self.player.hand.append(self.super_tile)
        self._mana_spent = True
        
        print(f"[{self.mod_id}] Super Tile created via command.")
        return True

    def undo(self) -> bool:
        if not self._mana_spent:
            return False
            
        # Reverse the action
        try:
            self.player.hand.remove(self.super_tile)
            mana_pool = self.player.components.get(self.mod_id)
            if mana_pool:
                mana_pool['mana'] += self.cost
            print(f"[{self.mod_id}] Super Tile creation undone.")
            return True
        except ValueError:
            print(f"[{self.mod_id}] Undo Failed: Super Tile not found in hand.")
            return False
            
    def get_description(self) -> str:
        return f"Create Super Tile (Cost: {self.cost})"