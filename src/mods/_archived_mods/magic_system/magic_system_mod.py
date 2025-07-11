# mods/magic_system/magic_system_mod.py
import pygame
from typing import TYPE_CHECKING, List, Dict, Any

# --- FIX #1: Import the standalone draw_text function ---
from rendering_utils import draw_text
from mods.magic_system.choose_any_tile_state import ChooseAnyTileState
from imod import IMod 

if TYPE_CHECKING:
    from game_logic.game import Game
    from game_logic.player import Player
    from visualizer import Linie1Visualizer
    from game_logic.tile import TileType
    
import constants as C

SUPER_TILE_ID = "SUPER_STAR_TILE"

class MagicSystemMod(IMod):
    """A mod that introduces mana and allows players to cast spells like creating a Super Tile."""
    
    def on_game_setup(self, game: 'Game'):
        """Initializes the mana component for every player."""
        print(f"[{self.name}] Initializing player mana pools...")
        starting_mana = self.config.get("starting_mana", 50)
        max_mana = self.config.get("max_mana", 100)
        for player in game.players:
            player.components[self.mod_id] = {'mana': starting_mana, 'max_mana': max_mana}

    def on_player_turn_end(self, game: 'Game', player: 'Player'):
        """Players regenerate mana at the end of their turn."""
        if self.mod_id in player.components:
            mana_pool = player.components[self.mod_id]
            regen = self.config.get("mana_regen_per_turn", 10)
            mana_pool['mana'] = min(mana_pool['max_mana'], mana_pool['mana'] + regen)

    def on_draw_ui_panel(self, screen: Any, visualizer: 'Linie1Visualizer', current_game_state_name: str):
        """Draws the current player's mana on the UI panel."""
        active_player = visualizer.game.get_active_player()
        if self.mod_id in active_player.components:
            mana = active_player.components[self.mod_id].get('mana', 0)
            max_mana = active_player.components[self.mod_id].get('max_mana', 100)
            mana_text = f"Mana: {mana} / {max_mana}"
            
            draw_x = C.UI_PANEL_X + 15
            draw_y = C.UI_ROUTE_INFO_Y + (C.UI_LINE_HEIGHT * 2)
            
            # --- FIX #2: Call the imported function directly, not as a method ---
            # The 'screen' object is passed in this method's signature.
            draw_text(screen, mana_text, draw_x, draw_y, color=(0, 100, 255), size=20)

    def get_ui_buttons(self, current_game_state_name: str) -> List[Dict[str, Any]]:
        """Adds a 'Create Super Tile' button."""
        if current_game_state_name == "LayingTrackState":
            cost = self.config.get("spell_cost_super_tile", 25)
            btn_x = C.UI_PANEL_X + 15
            btn_y = C.UI_ROUTE_INFO_Y + (C.UI_LINE_HEIGHT * 3)
            return [{
                "text": f"Super Tile ({cost} Mana)",
                "rect": pygame.Rect(btn_x, btn_y, 140, 30),
                "callback_name": "create_super_tile"
            }]
        return []

    def handle_ui_button_click(self, game: 'Game', player: 'Player', button_name: str) -> bool:
        """Handles the logic when the 'Create Super Tile' button is clicked."""
        if button_name == "create_super_tile":
            mana_pool = player.components.get(self.mod_id)
            if not mana_pool: return True

            cost = self.config.get("spell_cost_super_tile", 25)
            if mana_pool.get('mana', 0) >= cost:
                mana_pool['mana'] -= cost
                
                placeholder_tile = game.tile_types.get('Curve')
                if placeholder_tile:
                    super_tile = placeholder_tile.copy() 
                    super_tile.mod_id = self.mod_id 
                    super_tile.is_super_tile = True
                    super_tile.name = SUPER_TILE_ID
                    
                    player.hand.append(super_tile)
                    print(f"[{self.name}] Player {player.player_id} created a Super Star Tile!")
                else:
                    print(f"[{self.name}] ERROR: Could not find placeholder 'Curve' tile type.")
            else:
                print(f"[{self.name}] Not enough mana to create a Super Tile.")
            return True
        return False

    def on_hand_tile_clicked(self, game: 'Game', player: 'Player', tile_type: 'TileType') -> bool:
        """Triggers the spell when a super tile is clicked in hand."""
        if hasattr(tile_type, 'is_super_tile') and tile_type.is_super_tile:
            if game.visualizer:
                game.visualizer.request_state_change(
                    lambda v: ChooseAnyTileState(v, tile_type)
                )
            return True
        return False