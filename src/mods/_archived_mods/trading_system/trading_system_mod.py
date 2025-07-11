# mods/trading_system/trading_system_mod.py
from typing import TYPE_CHECKING, List, Dict, Any

import pygame

from imod import IMod

if TYPE_CHECKING:
    from game_logic.game import Game
    from game_logic.player import Player
    from visualizer import Linie1Visualizer
    
import constants as C

class TradingSystemMod(IMod):
    """
    A mod that introduces money and allows players to buy tiles.
    """
    def on_game_setup(self, game: 'Game'):
        """Initializes the money component for every player."""
        print(f"[{self.name}] Initializing player wallets...")
        starting_money = self.config.get("starting_money", 100)
        for player in game.players:
            # --- CORRECT USAGE: Add data to the namespaced component dictionary ---
            player.components[self.mod_id] = {
                'money': starting_money
            }

    def on_draw_ui_panel(self, screen: Any, visualizer: 'Linie1Visualizer', current_game_state_name: str):
        """Draws the current player's money on the UI panel."""
        active_player = visualizer.game.get_active_player()
        
        # Check if this mod's component has been initialized for the player
        if self.mod_id in active_player.components:
            money = active_player.components[self.mod_id].get('money', 0)
            money_text = f"Money: ${money}"
            
            # Define a position for the money display
            draw_x = C.UI_PANEL_X + 15
            draw_y = C.UI_ROUTE_INFO_Y + (C.UI_LINE_HEIGHT * 2)
            
            visualizer.draw_text(screen, money_text, draw_x, draw_y, size=20)
    
    def get_ui_buttons(self, current_game_state_name: str) -> List[Dict[str, Any]]:
        """Adds a 'Buy Tile' button during the Laying Track phase."""
        if current_game_state_name == "LayingTrackState":
            # Define button properties, could be loaded from constants
            btn_x = C.UI_PANEL_X + 15
            btn_y = C.UI_ROUTE_INFO_Y + (C.UI_LINE_HEIGHT * 3)
            return [{
                "text": "Buy Tile ($50)",
                "rect": pygame.Rect(btn_x, btn_y, 120, 30),
                "callback_name": "buy_tile_clicked" # Unique name for this button's action
            }]
        return []

    def handle_ui_button_click(self, game: 'Game', player: 'Player', button_name: str) -> bool:
        """Handles the logic when the 'Buy Tile' button is clicked."""
        if button_name == "buy_tile_clicked":
            player_wallet = player.components.get(self.mod_id)
            if not player_wallet: return True # Mod not initialized for this player
            
            cost = 50
            if player_wallet.get('money', 0) >= cost:
                # Deduct money and add a specific tile (e.g., a Straight)
                player_wallet['money'] -= cost
                straight_tile = game.tile_types.get('Straight')
                if straight_tile:
                    player.hand.append(straight_tile)
                    print(f"[{self.name}] Player {player.player_id} bought a Straight tile.")
                else:
                    print(f"[{self.name}] ERROR: Could not find 'Straight' tile type.")
            else:
                print(f"[{self.name}] Player {player.player_id} cannot afford to buy a tile.")

            return True # The click was handled by this mod
        return False
        
    # ... (other IMod methods can be left as `pass` or empty returns) ...