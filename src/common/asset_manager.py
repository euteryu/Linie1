# src/common/asset_manager.py
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

        self.images: Dict[str, Any] = {
            'tiles': {},
            'trains': {} # This key was missing
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
            # Construct the path to the tilemap
            tilemap_path = os.path.join(self.assets_path, 'images', 'tilemap.png')
            tilemap_image = pygame.image.load(tilemap_path).convert_alpha()

            # Iterate through the tile definitions to slice the map
            for tile_name, details in tile_definitions.items():
                if 'asset_coords' in details:
                    coords = details['asset_coords']
                    # Assuming all tiles on the map are the same size
                    tile_size = details.get('asset_size', (128, 128)) # Default to 128x128
                    
                    # Define the rectangle area for the subsurface
                    rect = pygame.Rect(coords[0], coords[1], tile_size[0], tile_size[1])
                    
                    # Cut out the tile and store it
                    tile_surface = tilemap_image.subsurface(rect)
                    self.images['tiles'][tile_name] = tile_surface
            
            print(f"    - Successfully loaded and sliced {len(self.images['tiles'])} tiles from tilemap.")

        except pygame.error as e:
            print(f"!!! CRITICAL ERROR: Could not load tilemap.png. Error: {e}")
        except FileNotFoundError:
            print(f"!!! CRITICAL ERROR: Asset file not found at '{tilemap_path}'.")

        # --- 2. Load and Slice the Train Sprites ---
        try:
            train_sheet_path = os.path.join(self.assets_path, 'images', 'train_sprites.png')
            train_sheet_image = pygame.image.load(train_sheet_path).convert_alpha()

            # The constants are now correctly imported and accessible
            for line_num, coords in C.TRAIN_ASSETS.items():
                rect = pygame.Rect(coords[0], coords[1], C.TRAIN_ASSET_SIZE[0], C.TRAIN_ASSET_SIZE[1])
                train_surface = train_sheet_image.subsurface(rect)
                self.images['trains'][line_num] = train_surface
            
            print(f"    - Successfully loaded and sliced {len(self.images['trains'])} trains.")

        except FileNotFoundError:
            print(f"!!! WARNING: Asset file not found at '{train_sheet_path}'. Train sprites will not be available.")
        except (pygame.error, KeyError, AttributeError) as e:
            # Catch multiple potential errors for clearer debugging
            print(f"!!! WARNING: Could not load or slice train_sprites.png. Error: {e}")
            
        # --- 2. Future Asset Loading ---
        # When you have a TV screen asset, you would add its loading logic here:
        # tv_path = os.path.join(self.assets_path, 'images', 'tv_animation.png')
        # self.images['headline_tv_frames'] = self._slice_spritesheet(tv_path, ...)

    def get_tile_surface(self, tile_name: str) -> Optional[pygame.Surface]:
        """Convenience method to retrieve a specific tile's image surface."""
        return self.images['tiles'].get(tile_name)

    # --- Example of future methods ---
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