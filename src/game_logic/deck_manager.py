# game_logic/deck_manager.py
from __future__ import annotations
from typing import List, Dict, TYPE_CHECKING
import random

if TYPE_CHECKING:
    from .game import Game
    from .player import Player, AIPlayer
    from .tile import TileType
    from .cards import LineCard, RouteCard

from .cards import LineCard, RouteCard
import common.constants as C

class DeckManager:
    """Manages all game decks: tiles, line cards, and route cards."""
    def __init__(self, game: 'Game'):
        self.game = game
        self.tile_draw_pile: List['TileType'] = []
        self.line_cards_pile: List['LineCard'] = []
        # --- START OF CHANGE ---
        self.initial_tile_counts: Dict[str, int] = {}
        # --- END OF CHANGE ---

    def create_and_shuffle_piles(self):
        """Creates and shuffles the tile draw pile and line card pile."""
        print("Creating draw piles...")
        # Create tile pile
        tile_counts = C.TILE_COUNTS_BASE.copy()
        if self.game.num_players >= 5:
            for name, count in C.TILE_COUNTS_5_PLUS_ADD.items():
                tile_counts[name] = tile_counts.get(name, 0) + count

        # --- START OF CHANGE ---
        # Create a permanent record of the initial supply before shuffling.
        self.initial_tile_counts = tile_counts.copy()
        print(f"Initial tile supply recorded: {sum(self.initial_tile_counts.values())} total tiles.")
        # --- END OF CHANGE ---

        self.tile_draw_pile = []
        for name, count in tile_counts.items():
            if tile_type := self.game.tile_types.get(name):
                self.tile_draw_pile.extend([tile_type] * count)
        random.shuffle(self.tile_draw_pile)
        print(f"Tile draw pile created: {len(self.tile_draw_pile)} tiles.")

        # Create line card pile
        self.line_cards_pile = [LineCard(line_num) for line_num in C.TERMINAL_DATA.keys()]
        random.shuffle(self.line_cards_pile)
        print(f"Line card pile created with {len(self.line_cards_pile)} cards.")

    def deal_starting_hands_and_cards(self):
        """Deals starting tiles and mission cards to all players."""
        print("Dealing starting hands and cards...")
        straight_type = self.game.tile_types.get('Straight')
        curve_type = self.game.tile_types.get('Curve')
        if not straight_type or not curve_type:
            raise RuntimeError("Straight/Curve TileType missing for dealing.")

        for player in self.game.players:
            player.hand = []
            for _ in range(C.STARTING_HAND_TILES['Straight']):
                player.hand.append(straight_type)
            for _ in range(C.STARTING_HAND_TILES['Curve']):
                player.hand.append(curve_type)

        available_variants = list(range(len(C.ROUTE_CARD_VARIANTS)))
        random.shuffle(available_variants)
        player_range = "1-4" if self.game.num_players <= 4 else "5-6"

        for player in self.game.players:
            if not self.line_cards_pile:
                raise RuntimeError("Not enough line cards for all players.")
            player.line_card = self.line_cards_pile.pop()

            if not available_variants:
                available_variants = list(range(len(C.ROUTE_CARD_VARIANTS)))
            variant_index = available_variants.pop(0)
            
            try:
                stops = C.ROUTE_CARD_VARIANTS[variant_index][player_range][player.line_card.line_number]
            except (KeyError, IndexError):
                stops = C.ROUTE_CARD_VARIANTS[0]["1-4"][1]
            
            player.route_card = RouteCard(stops, variant_index)
        
    def draw_tile(self, player: 'Player') -> bool:
        """Draws a tile for a player, considering difficulty biases and mods."""
        from .player import AIPlayer
        
        if not self.tile_draw_pile or len(player.hand) >= C.HAND_TILE_LIMIT:
            return False

        handled_by_mod, name = self.game.mod_manager.on_tile_drawn(self.game, player, None, [t.name for t in self.tile_draw_pile])
        if handled_by_mod and name and (chosen_tile := next((t for t in self.tile_draw_pile if t.name == name), None)):
            self.tile_draw_pile.remove(chosen_tile)
            player.hand.append(chosen_tile)
            return True

        if isinstance(player, AIPlayer) and player.difficulty_mode == 'king':
            tree_tiles = [t for t in self.tile_draw_pile if t.name.startswith("Tree")]
            if tree_tiles:
                weights = [C.KING_AI_TREE_TILE_BIAS if t.name.startswith("Tree") else 1 for t in self.tile_draw_pile]
                chosen_tile = random.choices(self.tile_draw_pile, weights=weights, k=1)[0]
                self.tile_draw_pile.remove(chosen_tile)
                player.hand.append(chosen_tile)
                return True

        drawn_tile = self.tile_draw_pile.pop()
        player.hand.append(drawn_tile)
        return True
    
    def roll_special_die(self) -> Any:
        """Returns a random face from the special game die."""
        return random.choice(C.DIE_FACES)