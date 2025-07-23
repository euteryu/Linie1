# src/common/asset_manager.py (CORRECTED)
import pygame
import os
from typing import Dict, Any, Tuple, Optional, List
from common import constants as C

class AssetManager:
    """
    A centralized manager to load and store all game assets, such as images,
    fonts, and sounds, once at the start of the game.
    """
    def __init__(self, root_dir: str):
        """
        Initializes the AssetManager.
        
        Args:
            root_dir: The absolute path to the project's root directory.
        """
        self.root_dir = root_dir
        self.assets_path = os.path.join(self.root_dir, 'src', 'assets')

        # --- CRITICAL FIX: Initialize all sub-dictionaries ---
        self.images: Dict[str, Any] = {
            'tiles': {},
            'trains': {},
            'ui': {}  # This key was missing
        }
        
        self.fonts: Dict[str, pygame.font.Font] = {}
        self.sounds: Dict[str, pygame.mixer.Sound] = {}

    def load_all_assets(self, tile_definitions: Dict[str, Any]):
        """
        Master function to load all game assets into memory.
        This is called once when the application starts.
        """
        print("--- Loading all game assets... ---")
        self._load_images(tile_definitions)
        # self._load_fonts() # Placeholder for future font loading
        # self._load_sounds() # Placeholder for future sound loading
        print("--- Asset loading complete. ---")

    def _load_images(self, tile_definitions: Dict[str, Any]):
        """Loads and slices all image assets."""
        print("  Loading images...")
        
        # --- 1. Load and Slice the Tilemap ---
        try:
            tilemap_path = os.path.join(self.assets_path, 'images', 'sprites', 'tilemap.png')
            tilemap_image = pygame.image.load(tilemap_path).convert_alpha()

            for tile_name, details in tile_definitions.items():
                if 'asset_coords' in details:
                    coords = details['asset_coords']
                    tile_size = details.get('asset_size', (128, 128))
                    rect = pygame.Rect(coords[0], coords[1], tile_size[0], tile_size[1])
                    tile_surface = tilemap_image.subsurface(rect)
                    self.images['tiles'][tile_name] = tile_surface
            
            print(f"    - Successfully loaded and sliced {len(self.images['tiles'])} tiles from tilemap.")
        except (pygame.error, FileNotFoundError) as e:
            print(f"!!! WARNING: Could not load or slice tilemap. Error: {e}")

        # --- 2. Load and Slice the Train Sprites ---
        try:
            train_sheet_path = os.path.join(self.assets_path, 'images', 'sprites', 'train_sprites.png')
            train_sheet_image = pygame.image.load(train_sheet_path).convert_alpha()

            for line_num, coords in C.TRAIN_ASSETS.items():
                rect = pygame.Rect(coords[0], coords[1], C.TRAIN_ASSET_SIZE[0], C.TRAIN_ASSET_SIZE[1])
                train_surface = train_sheet_image.subsurface(rect)
                self.images['trains'][line_num] = train_surface
            
            print(f"    - Successfully loaded and sliced {len(self.images['trains'])} trains.")
        except (pygame.error, FileNotFoundError) as e:
            print(f"!!! WARNING: Could not load or slice train sprites. Error: {e}")
            
        # --- 3. Load all UI assets ---
        print("  Loading UI assets...")
        try:
            # Load the main menu background
            background_path = os.path.join(self.assets_path, 'images', 'backgrounds', 'main_menu_background.png')
            self.images['ui']['main_menu_background'] = pygame.image.load(background_path).convert()
            
            # Load the hover state for each button.
            # NOTE: You must have image files with these exact names in src/assets/images/ui/
            ui_elements_path = os.path.join(self.assets_path, 'images', 'ui')
            self.images['ui']['play_button_hover'] = pygame.image.load(os.path.join(ui_elements_path, 'play_button_hover.png')).convert_alpha()
            self.images['ui']['load_button_hover'] = pygame.image.load(os.path.join(ui_elements_path, 'load_button_hover.png')).convert_alpha()
            self.images['ui']['save_button_hover'] = pygame.image.load(os.path.join(ui_elements_path, 'save_button_hover.png')).convert_alpha()
            self.images['ui']['settings_button_hover'] = pygame.image.load(os.path.join(ui_elements_path, 'settings_button_hover.png')).convert_alpha()
            self.images['ui']['quit_button_hover'] = pygame.image.load(os.path.join(ui_elements_path, 'quit_button_hover.png')).convert_alpha()
            
            print("    - Successfully loaded UI backgrounds and elements.")
        except (pygame.error, FileNotFoundError) as e:
            print(f"!!! CRITICAL WARNING: Could not load essential UI assets. The UI may be invisible. Error: {e}")

    def load_background(self, background_name: str) -> Optional[pygame.Surface]:
        """Loads a single, full-screen background image from the backgrounds folder."""
        try:
            path = os.path.join(self.assets_path, 'images', 'backgrounds', f"{background_name}.png")
            image = pygame.image.load(path).convert()
            # Store it in the cache in case it's needed again
            self.images['ui'][background_name] = image
            print(f"    - Successfully loaded background: {background_name}.png")
            return image
        except (pygame.error, FileNotFoundError) as e:
            print(f"!!! CRITICAL WARNING: Could not load background '{background_name}.png'. Error: {e}")
            return None

    def get_tile_surface(self, tile_name: str) -> Optional[pygame.Surface]:
        """Convenience method to retrieve a specific tile's image surface."""
        return self.images['tiles'].get(tile_name)

    def _slice_spritesheet(self, sheet_path: str, frame_width: int, frame_height: int) -> List[pygame.Surface]:
        """A generic helper to slice any spritesheet into a list of frames."""
        frames = []
        try:
            spritesheet = pygame.image.load(sheet_path).convert_alpha()
            sheet_width, sheet_height = spritesheet.get_size()
            for y in range(0, sheet_height, frame_height):
                for x in range(0, sheet_width, frame_width):
                    rect = pygame.Rect(x, y, frame_width, frame_height)
                    frames.append(spritesheet.subsurface(rect))
        except Exception as e:
            print(f"ERROR: Could not slice spritesheet at '{sheet_path}': {e}")
        return frames