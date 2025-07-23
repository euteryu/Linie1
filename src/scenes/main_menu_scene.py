import pygame
import sys
import math
import importlib

from scenes.scene import Scene
from common.layout import LayoutConstants

# --- THE NATIVE BLUEPRINT ---
# This is the fallback layout if a resolution-specific one isn't found.
# It's best to use your highest resolution layout here.
NATIVE_LAYOUT_MODULE = "main_menu_layout" 
NATIVE_RESOLUTION = (1280, 720)

class MainMenuScene(Scene):
    def __init__(self, scene_manager, asset_manager, layout_constants: LayoutConstants):
        super().__init__(scene_manager)
        self.asset_manager = asset_manager
        self.layout_constants = layout_constants
        self.theme = scene_manager.theme

        self.background_image = None
        self.hover_images = {}
        self.hovered_region_name = None
        
        self.scaled_regions = {}
        self.native_layout = None
        self.interactive_regions = {}

        # This sequence correctly loads the layout, defines the interactive parts, and then loads assets.
        self._load_and_scale_layout()

        if self.native_layout:
            region_names = [name.replace('_bounds', '') for name in dir(self.native_layout) if name.endswith('_bounds')]
            callback_map = {
                "play_button": self.go_to_level_selection,
                "load_button": self.load_game,
                "save_button": self.save_game,
                "settings_button": self.go_to_settings,
                "quit_button": self.quit_game,
            }
            self.interactive_regions = {name: callback_map[name] for name in region_names if name in callback_map}

        self._load_assets()
            
    def _load_and_scale_layout(self):
        """
        Dynamically imports the best layout file for the current resolution
        and scales its regions to fit the screen perfectly.
        """
        current_w = self.layout_constants.SCREEN_WIDTH
        current_h = self.layout_constants.SCREEN_HEIGHT
        
        try:
            layout_module_name = f"ui.layouts.main_menu_layout_{current_w}x{current_h}"
            self.native_layout = importlib.import_module(layout_module_name)
            scale_x, scale_y = 1.0, 1.0
            print(f"INFO: Successfully loaded resolution-specific layout: {layout_module_name}")
        except ImportError:
            print(f"INFO: Specific layout for {current_w}x{current_h} not found. Falling back to scaling '{NATIVE_LAYOUT_MODULE}'.")
            try:
                self.native_layout = importlib.import_module(f"ui.layouts.{NATIVE_LAYOUT_MODULE}")
                native_res = NATIVE_RESOLUTION
                scale_x = current_w / native_res[0]
                scale_y = current_h / native_res[1]
            except ImportError:
                print(f"ERROR: Default layout blueprint '{NATIVE_LAYOUT_MODULE}.py' not found in src/ui/layouts/!")
                return

        region_names = [name.replace('_bounds', '') for name in dir(self.native_layout) if name.endswith('_bounds')]

        for name in region_names:
            bounds = getattr(self.native_layout, f"{name}_bounds")
            data = getattr(self.native_layout, f"{name}_data")
            scaled_bounds = pygame.Rect(int(bounds.x * scale_x), int(bounds.y * scale_y), int(bounds.width * scale_x), int(bounds.height * scale_y))
            scaled_data = {'shape': data['shape']}
            if data['shape'] == 'circle':
                scaled_data['center'] = (int(data['center'][0] * scale_x), int(data['center'][1] * scale_y))
                scaled_data['radius'] = int(data['radius'] * (scale_x + scale_y) / 2)
            elif data['shape'] == 'polygon':
                scaled_data['points'] = [(int(p[0] * scale_x), int(p[1] * scale_y)) for p in data['points']]
            self.scaled_regions[name] = {'bounds': scaled_bounds, 'data': scaled_data}

    def _load_assets(self):
        """Loads all necessary images for this scene from the AssetManager."""
        try:
            self.background_image = self.asset_manager.images['ui']['main_menu_background']
            # This line can now safely access self.interactive_regions.
            self.hover_images = {
                name: self.asset_manager.images['ui'].get(f"{name}_hover") 
                for name in self.interactive_regions.keys()
            }
        except KeyError:
            print("Warning: 'main_menu_background' not found in asset_manager. The main menu may not look correct.")

    # --- Action methods (The "Callbacks") ---
    def go_to_level_selection(self): self.scene_manager.go_to_scene("LEVEL_SELECTION")
    def load_game(self): self.scene_manager.load_game_action()
    def save_game(self): print("Action: Save game (not implemented in main menu).")
    def go_to_settings(self): self.scene_manager.go_to_scene("SETTINGS")
    def quit_game(self): pygame.quit(); sys.exit()

    def handle_events(self, events):
        if not self.native_layout: return
        mouse_pos = pygame.mouse.get_pos()
        self.hovered_region_name = None
        
        # Check for hover by iterating through the scaled regions
        for name in self.interactive_regions.keys():
            region = self.scaled_regions.get(name)
            if region and region['bounds'].collidepoint(mouse_pos) and is_point_in_shape(mouse_pos, region['data']):
                self.hovered_region_name = name
                break
        
        for event in events:
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE): self.quit_game()
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.hovered_region_name:
                if callback := self.interactive_regions.get(self.hovered_region_name):
                    callback()

    def update(self, dt): pass

    def draw(self, screen):
        # Step 1: Draw the beautiful background art, stretched to fit the current screen.
        if self.background_image:
            scaled_background = pygame.transform.scale(self.background_image, screen.get_size())
            screen.blit(scaled_background, (0, 0))
        else:
            screen.fill(self.theme["colors"]["background"]) # Fallback if art is missing

        # Step 2: If hovering over an interactive region, draw its "hover" image on top.
        if self.hovered_region_name:
            hover_image = self.hover_images.get(self.hovered_region_name)
            region = self.scaled_regions.get(self.hovered_region_name)
            if hover_image and region:
                scaled_hover = pygame.transform.scale(hover_image, region['bounds'].size)
                screen.blit(scaled_hover, region['bounds'].topleft)

# --- UTILITY FUNCTION ---
def is_point_in_shape(point, shape_data):
    shape_type = shape_data.get('shape')
    if shape_type == 'rectangle': return True
    if shape_type == 'circle':
        center=shape_data.get('center'); radius=shape_data.get('radius')
        if not center or radius is None: return False
        return math.hypot(point[0]-center[0], point[1]-center[1]) <= radius
    if shape_type == 'polygon':
        points = shape_data.get('points')
        if not points or len(points) < 3: return False
        x, y = point; n = len(points); inside = False; p1x, p1y = points[0]
        for i in range(n + 1):
            p2x, p2y = points[i % n]
            if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
                if p1y != p2y: xinters = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                if p1x == p2x or x <= xinters: inside = not inside
            p1x, p1y = p2x, p2y
        return inside
    return False