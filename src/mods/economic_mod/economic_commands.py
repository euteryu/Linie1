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
        super().__init__(game); self.player = player; self.cost = cost; self.mod_id = mod_id; self.permit_tile = permit_tile_instance; self._capital_spent = False; self._action_taken = False; self._discarded_tile: Optional['TileType'] = None
    def execute(self) -> bool:
        if self.game.actions_taken_this_turn >= self.game.MAX_PLAYER_ACTIONS: return False
        capital_pool = self.player.components.get(self.mod_id)
        if not capital_pool: return False

        available_capital = capital_pool.get('capital', 0) - capital_pool.get('frozen_capital', 0)
        if available_capital < self.cost: return False

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

class FulfillPermitCommand(Command):
    """A command to swap a permit for a specific tile from the supply, paying its market price."""
    def __init__(self, game: 'Game', player: 'Player', mod_id: str, chosen_tile: 'TileType', permit_tile: 'TileType', cost: int):
        super().__init__(game); self.player = player; self.mod_id = mod_id; self.chosen_tile = chosen_tile; self.permit_tile = permit_tile; self.cost = cost; self._executed = False
    
    def execute(self) -> bool:
        capital_pool = self.player.components.get(self.mod_id)
        if not capital_pool: return False

        available_capital = capital_pool.get('capital', 0) - capital_pool.get('frozen_capital', 0)
        if available_capital < self.cost: return False

        if self.permit_tile not in self.player.hand: return False
        if self.game.deck_manager.tile_draw_pile.count(self.chosen_tile) == 0: return False
        capital_pool['capital'] -= self.cost; self.player.hand.remove(self.permit_tile); self.player.hand.append(self.chosen_tile); self.game.deck_manager.tile_draw_pile.remove(self.chosen_tile); self._executed = True
        return True

    def undo(self) -> bool:
        if not self._executed: return False
        
        # Reverse the transaction
        self.game.deck_manager.tile_draw_pile.insert(0, self.chosen_tile)
        self.player.hand.remove(self.chosen_tile)
        self.player.hand.append(self.permit_tile)
        if capital_pool := self.player.components.get(self.mod_id):
            capital_pool['capital'] += self.cost
            
        return True

    def get_description(self) -> str:
        return f"Fulfilled Permit for {self.chosen_tile.name} (Cost: ${self.cost})"


class AuctionTileCommand(Command):
    """Lists a tile from the player's hand on the open market."""
    def __init__(self, game: 'Game', player: 'Player', mod_id: str, tile_to_auction: 'TileType', min_bid: int):
        super().__init__(game)
        self.player = player
        self.mod_id = mod_id
        self.tile_to_auction = tile_to_auction
        self.min_bid = min_bid
        self._executed = False

    def execute(self) -> bool:
        if self.game.actions_taken_this_turn >= self.game.MAX_PLAYER_ACTIONS: return False
        if self.tile_to_auction not in self.player.hand: return False
        
        self.player.hand.remove(self.tile_to_auction)
        
        auction_data = {
            "seller_id": self.player.player_id,
            "tile_type_name": self.tile_to_auction.name,
            "min_bid": self.min_bid,
            "bids": [],
            "turn_of_resolution": self.game.current_turn + 1
        }
        self.game.live_auctions.append(auction_data)
        
        self.game.actions_taken_this_turn += 1
        self._executed = True
        return True

    def undo(self) -> bool:
        if not self._executed: return False
        
        # Find and remove the auction this command created
        for i, auction in enumerate(self.game.live_auctions):
            if auction['seller_id'] == self.player.player_id and auction['tile_type_name'] == self.tile_to_auction.name:
                self.game.live_auctions.pop(i)
                break
                
        self.player.hand.append(self.tile_to_auction)
        self.game.actions_taken_this_turn -= 1
        return True

    def get_description(self) -> str:
        return f"Auction {self.tile_to_auction.name} (Min Bid: ${self.min_bid})"

class PlaceBidCommand(Command):
    """Places a sealed bid on an active auction."""
    def __init__(self, game: 'Game', player: 'Player', mod_id: str, auction_index: int, bid_amount: int):
        super().__init__(game)
        self.player = player
        self.mod_id = mod_id
        self.auction_index = auction_index
        self.bid_amount = bid_amount
        self._executed = False

    def execute(self) -> bool:
        if self.game.actions_taken_this_turn >= self.game.MAX_PLAYER_ACTIONS: return False
        if not (0 <= self.auction_index < len(self.game.live_auctions)): return False
        
        mod_data = self.player.components.get(self.mod_id)
        if not mod_data or mod_data.get('consecutive_auctions', 0) >= 3:
            return False

        capital_pool = self.player.components.get(self.mod_id)
        if not capital_pool: return False
        
        available_capital = capital_pool.get('capital', 0) - capital_pool.get('frozen_capital', 0)
        if available_capital < self.bid_amount: return False
        
        auction = self.game.live_auctions[self.auction_index]
        
        # Check if bid is high enough
        current_high_bid = max([b['amount'] for b in auction['bids']], default=auction['min_bid'])
        # Allow bidding equal to the minimum, but must be greater than existing high bid
        if self.bid_amount < auction['min_bid'] or (auction['bids'] and self.bid_amount <= current_high_bid):
            return False
        
        capital_pool['frozen_capital'] = capital_pool.get('frozen_capital', 0) + self.bid_amount
        auction['bids'].append({'bidder_id': self.player.player_id, 'amount': self.bid_amount})
        
        self.game.actions_taken_this_turn += 1
        self._executed = True

        mod_data['consecutive_auctions'] += 1
        mod_data['auction_action_taken_this_turn'] = True
        print(f"  Player {self.player.player_id} auction streak is now {mod_data['consecutive_auctions']}.")

        if self.game.visualizer and self.game.visualizer.sounds:
            self.game.visualizer.sounds.play('auction_new_item')
        return True

    def undo(self) -> bool:
        if not self._executed: return False

        if capital_pool := self.player.components.get(self.mod_id):
            capital_pool['frozen_capital'] -= self.bid_amount
        
        auction = self.game.live_auctions[self.auction_index]
        auction['bids'] = [b for b in auction['bids'] if b['bidder_id'] != self.player.player_id]
        
        self.game.actions_taken_this_turn -= 1

        if mod_data := self.player.components.get(self.mod_id):
            mod_data['consecutive_auctions'] -= 1
        return True

    def get_description(self) -> str:
        return f"Bid ${self.bid_amount} on auction"