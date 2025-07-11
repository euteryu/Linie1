# mods/economic_mod/economic_commands.py
from __future__ import annotations
from typing import TYPE_CHECKING, Optional

import pygame

from game_logic.commands import Command

import common.constants as C

if TYPE_CHECKING:
    from game_logic.game import Game
    from game_logic.player import Player
    from game_logic.tile import TileType

# This is a renamed and re-themed version of the CreateSuperTileCommand
class PriorityRequisitionCommand(Command):
    """A command to get a Requisition Permit, consuming one action."""
    def __init__(self, game: 'Game', player: 'Player', cost: int, mod_id: str, permit_tile_instance: 'TileType'):
        super().__init__(game)
        self.player = player
        self.cost = cost
        self.mod_id = mod_id
        self.permit_tile = permit_tile_instance
        self._capital_spent = False
        self._action_taken = False

    def execute(self) -> bool:
        # --- START OF FIX: Check and consume an action ---
        if self.game.actions_taken_this_turn >= self.game.MAX_PLAYER_ACTIONS:
            return False
        # --- END OF FIX ---
            
        capital_pool = self.player.components.get(self.mod_id)
        if not capital_pool or capital_pool.get('capital', 0) < self.cost:
            return False

        capital_pool['capital'] -= self.cost
        self.player.hand.append(self.permit_tile)
        self._capital_spent = True
        
        # --- START OF FIX: Increment action counter ---
        self.game.actions_taken_this_turn += 1
        self._action_taken = True
        # --- END OF FIX ---
        
        print(f"[{self.mod_id}] Priority Requisition approved. Permit added to hand.")
        return True

    def undo(self) -> bool:
        if not self._capital_spent:
            return False

        try:
            self.player.hand.remove(self.permit_tile)
            capital_pool = self.player.components.get(self.mod_id)
            if capital_pool:
                capital_pool['capital'] += self.cost
        except ValueError:
            # This could happen if the permit was already used and swapped
            print(f"[{self.mod_id}] Undo Info: Permit was already used, cannot remove from hand.")

        if self._action_taken:
            # --- START OF FIX ---
            # Remove the space from the variable name
            self.game.actions_taken_this_turn -= 1
            # --- END OF FIX ---
        
        print(f"[{self.mod_id}] Priority Requisition undone.")
        return True
            
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

class BribeOfficialCommand(Command):
    """A command to spend Capital for Influence, consuming the entire turn."""
    def __init__(self, game: 'Game', player: 'Player', cost: int, reward: int, mod_id: str):
        super().__init__(game)
        self.player = player
        self.cost = cost
        self.reward = reward
        self.mod_id = mod_id
        self._executed = False

    def execute(self) -> bool:
        # This command costs all actions for the turn.
        if self.game.actions_taken_this_turn > 0:
            return False
            
        capital_pool = self.player.components.get(self.mod_id)
        if not capital_pool or capital_pool.get('capital', 0) < self.cost:
            return False

        capital_pool['capital'] -= self.cost
        # Assuming influence is also stored in the component dictionary
        capital_pool['influence'] = capital_pool.get('influence', 0) + self.reward
        
        # Consume all actions for the turn
        self.game.actions_taken_this_turn = self.game.MAX_PLAYER_ACTIONS
        self._executed = True
        
        print(f"[{self.mod_id}] Bribed official for {self.reward} Influence. Cost: ${self.cost}")
        # This command must also end the turn
        pygame.event.post(pygame.event.Event(C.START_NEXT_TURN_EVENT, {'reason': 'bribe_action'}))
        return True

    def undo(self) -> bool:
        if not self._executed:
            return False
        
        capital_pool = self.player.components.get(self.mod_id)
        if capital_pool:
            capital_pool['capital'] += self.cost
            capital_pool['influence'] -= self.reward

        # Reset action counter
        self.game.actions_taken_this_turn = 0
        return True

    def get_description(self) -> str:
        return f"Bribe Official for {self.reward} Influence"