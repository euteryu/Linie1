# mod_manager.py
import os
import importlib.util
import json
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING

from imod import IMod

# The TYPE_CHECKING block is still essential for the imports themselves.
if TYPE_CHECKING:
    from game_logic.game import Game
    from game_logic.player import Player
    from visualizer import Linie1Visualizer

class ModManager:
    _instance: Optional['ModManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.mods_directory = "mods"
        self.available_mods: Dict[str, IMod] = {}
        self.active_mod_ids: List[str] = []
        self._initialized = True
        self.discover_mods()

    def discover_mods(self):
        # ... (This method is correct and does not need changes) ...
        self.available_mods.clear()
        if not os.path.exists(self.mods_directory):
            print(f"Mods directory '{self.mods_directory}' not found.")
            return
        for mod_name in os.listdir(self.mods_directory):
            mod_path = os.path.join(self.mods_directory, mod_name)
            if os.path.isdir(mod_path):
                config_path = os.path.join(mod_path, "mod_config.json")
                module_path = os.path.join(mod_path, f"{mod_name.replace('-', '_')}_mod.py")
                if not os.path.exists(config_path) or not os.path.exists(module_path):
                    continue
                try:
                    with open(config_path, 'r') as f: config = json.load(f)
                    mod_id = config.get("id")
                    mod_class_name = config.get("class_name")
                    if not mod_id or not mod_class_name: continue
                    spec = importlib.util.spec_from_file_location(mod_id, module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    mod_class = getattr(module, mod_class_name)
                    if not issubclass(mod_class, IMod): continue
                    mod_instance = mod_class(mod_id, config.get("name", mod_name), config.get("description", ""), config)
                    self.available_mods[mod_id] = mod_instance
                    print(f"Discovered mod: {mod_instance.name} ({mod_id})")
                except Exception as e:
                    print(f"Error loading mod '{mod_name}': {e}")


    def activate_mod(self, mod_id: str):
        # ... (This method is correct and does not need changes) ...
        if mod_id in self.available_mods:
            self.available_mods[mod_id].is_active = True
            if mod_id not in self.active_mod_ids:
                self.active_mod_ids.append(mod_id)
            print(f"Mod '{mod_id}' activated.")

    def deactivate_mod(self, mod_id: str):
        # ... (This method is correct and does not need changes) ...
        if mod_id in self.available_mods:
            self.available_mods[mod_id].is_active = False
            if mod_id in self.active_mod_ids:
                self.active_mod_ids.remove(mod_id)
            print(f"Mod '{mod_id}' deactivated.")


    def get_active_mods(self) -> List[IMod]:
        return [self.available_mods[mod_id] for mod_id in self.active_mod_ids]

    # --- THIS IS THE FIX: Using Forward References (strings) for type hints ---
    def on_game_setup(self, game: 'Game'):
        for mod in self.get_active_mods():
            mod.on_game_setup(game)

    def on_player_turn_start(self, game: 'Game', player: 'Player'):
        for mod in self.get_active_mods():
            mod.on_player_turn_start(game, player)

    def on_player_turn_end(self, game: 'Game', player: 'Player'):
        for mod in self.get_active_mods():
            mod.on_player_turn_end(game, player)

    def on_tile_drawn(self, game: 'Game', player: 'Player', base_tile_name: Optional[str], tile_draw_pile_names: List[str]) -> Tuple[bool, Optional[str]]:
        for mod in self.get_active_mods():
            handled, mod_chosen_tile_name = mod.on_tile_drawn(game, player, base_tile_name, tile_draw_pile_names)
            if handled:
                return True, mod_chosen_tile_name
        return False, None

    def get_active_ui_buttons(self, current_game_state_name: str) -> List[Dict[str, Any]]:
        buttons = []
        for mod in self.get_active_mods():
            buttons.extend(mod.get_ui_buttons(current_game_state_name))
        return buttons
    
    def handle_mod_ui_button_click(self, game: 'Game', player: 'Player', button_name: str) -> bool:
        for mod in self.get_active_mods():
            if mod.handle_ui_button_click(game, player, button_name):
                return True
        return False

    def draw_mod_ui_elements(self, screen: Any, visualizer: 'Linie1Visualizer', current_game_state_name: str):
        for mod in self.get_active_mods():
            mod.on_draw_ui_panel(screen, visualizer, current_game_state_name)

    def to_dict(self) -> Dict:
        return {"active_mod_ids": self.active_mod_ids}
    
    def from_dict(self, data: Dict):
        self.active_mod_ids = []
        self.deactivate_all_mods() # Helper method might be useful here
        for mod_id in data.get("active_mod_ids", []):
            self.activate_mod(mod_id)

    def deactivate_all_mods(self):
        """Helper to deactivate all mods, useful when loading a game."""
        for mod in self.available_mods.values():
            mod.is_active = False
        self.active_mod_ids.clear()
    # --- END OF FIX ---