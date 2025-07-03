# mod_manager.py
import sys
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
        self.discover_mods()
        self._initialized = True

    def discover_mods(self):
        self.available_mods.clear()
        
        project_root = os.path.dirname(os.path.abspath(__file__))
        mods_dir_absolute = os.path.join(project_root, self.mods_directory)

        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        if not os.path.exists(mods_dir_absolute):
            print(f"Mods directory '{mods_dir_absolute}' not found.")
            return

        for mod_name in os.listdir(mods_dir_absolute):
            mod_path = os.path.join(mods_dir_absolute, mod_name)
            if os.path.isdir(mod_path) and os.path.exists(os.path.join(mod_path, "__init__.py")):
                try:
                    config_path = os.path.join(mod_path, "mod_config.json")
                    if not os.path.exists(config_path):
                        print(f"Skipping mod '{mod_name}': missing mod_config.json.")
                        continue
                    
                    with open(config_path, 'r') as f: config = json.load(f)
                    
                    mod_id = config.get("id")
                    mod_class_name = config.get("class_name")
                    main_module_name = config.get("main_module", f"{mod_name.replace('-', '_')}_mod")
                    
                    if not mod_id or not mod_class_name:
                        print(f"Skipping mod '{mod_name}': config missing 'id' or 'class_name'.")
                        continue

                    # --- THIS IS THE NEW, ROBUST IMPORT LOGIC ---
                    # 1. Construct the full package path, e.g., 'mods.magic_system.magic_system_mod'
                    full_module_path = f"mods.{mod_name}.{main_module_name}"
                    
                    # 2. Use importlib.import_module, which handles packages correctly.
                    module = importlib.import_module(full_module_path)
                    # --- END OF NEW LOGIC ---

                    mod_class = getattr(module, mod_class_name)
                    if not issubclass(mod_class, IMod):
                        print(f"Mod class '{mod_class_name}' in '{mod_name}' does not inherit from IMod.")
                        continue
                    
                    mod_instance = mod_class(mod_id, config.get("name", mod_name), config.get("description", ""), config)
                    self.available_mods[mod_id] = mod_instance
                    print(f"Discovered mod: {mod_instance.name} ({mod_id})")

                except Exception as e:
                    print(f"Error loading mod '{mod_name}': {e}")
                    import traceback
                    traceback.print_exc()


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

    def on_hand_tile_clicked(self, game: 'Game', player: 'Player', tile_type: 'TileType') -> bool:
        """
        Dispatches the hand tile click event to active mods.
        Returns True if any mod handled the event.
        """
        for mod in self.get_active_mods():
            if mod.on_hand_tile_clicked(game, player, tile_type):
                return True # A mod took over, stop processing
        return False

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