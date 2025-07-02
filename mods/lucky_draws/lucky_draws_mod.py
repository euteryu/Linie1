# mods/lucky_draws/lucky_draws_mod.py
import random
import os
import json # To read its own config
from typing import TYPE_CHECKING, List, Dict, Any, Tuple, Optional

from imod import IMod 

# --- THIS IS THE FIX ---
# Import the constants module to get access to UI layout values.
import constants as C
# --- END OF FIX ---

if TYPE_CHECKING:
    from game_logic.game import Game
    from game_logic.player import Player
    from visualizer import Linie1Visualizer

class LuckyDrawsMod(IMod):
    def __init__(self, mod_id: str, name: str, description: str, config: Dict[str, Any]):
        super().__init__(mod_id, name, description, config)
        self.bonus_draw_probability = self.config.get("bonus_draw_probability", 0.5)
        self.bonus_tile_type_name = self.config.get("bonus_tile_type", "Tree_JunctionTop")

    def on_game_setup(self, game: 'Game'):
        print(f"[{self.name}] Mod: Game setup detected.")

    def on_player_turn_start(self, game: 'Game', player: 'Player'):
        pass

    def on_player_turn_end(self, game: 'Game', player: 'Player'):
        pass

    def on_tile_drawn(self, game: 'Game', player: 'Player', base_tile_name: Optional[str], tile_draw_pile_names: List[str]) -> Tuple[bool, Optional[str]]:
        return False, None

    def get_ui_buttons(self, current_game_state_name: str) -> List[Dict[str, Any]]:
        return []

    def handle_ui_button_click(self, game: 'Game', player: 'Player', button_name: str) -> bool:
        return False
    
    def on_draw_ui_panel(self, screen: Any, visualizer: 'Linie1Visualizer', current_game_state_name: str):
        """Draws the mod's status text using globally defined constants."""
        if current_game_state_name == "LayingTrackState":
            # --- THIS IS THE FIX ---
            # Use the imported constants directly, not attributes of the visualizer.
            draw_x = C.UI_PANEL_X + 15
            draw_y = C.UI_PANEL_Y + C.UI_PANEL_HEIGHT - 120 # Adjusted y-pos for clarity
            visualizer.draw_text(screen, f"Mod: {self.name} ACTIVE", 
                                 draw_x, draw_y,
                                 size=16)
            # --- END OF FIX ---