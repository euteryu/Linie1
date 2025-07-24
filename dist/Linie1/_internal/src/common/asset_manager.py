import pygame
import os
import sys # <--- ADD THIS IMPORT
from typing import Dict, Any, Tuple, Optional, List
from common import constants as C

def resource_path(relative_path: str) -> str:
    """
    Get the absolute path to a resource, which works for both development
    and for a PyInstaller --onefile bundle.
    """
    try:
        # PyInstaller creates a temp folder and stores its path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If not running as a PyInstaller bundle, use the normal script path
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class AssetManager:
    """
    A centralized manager to load and store all game assets, such as images,
    fonts, and sounds, once at the start of the game.
    """
    def __init__(self):
        """
        Initializes the AssetManager. Does not require a root directory anymore,
        as resource_path handles path resolution.
        """
        self.images: Dict[str, Any] = {
            'tiles': {},
            'trains': {}
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
        """Loads and slices all image assets using the resource_path helper."""
        print("  Loading images...")
        
        try:
            # Use the reliable helper function
            tilemap_path = resource_path(os.path.join('src', 'assets', 'images', 'tilemap.png'))
            tilemap_image = pygame.image.load(tilemap_path).convert_alpha()

            for tile_name, details in tile_definitions.items():
                if 'asset_coords' in details:
                    coords = details['asset_coords']
                    tile_size = details.get('asset_size', (128, 128))
                    rect = pygame.Rect(coords[0], coords[1], tile_size[0], tile_size[1])
                    tile_surface = tilemap_image.subsurface(rect)
                    self.images['tiles'][tile_name] = tile_surface
            
            print(f"    - Successfully loaded and sliced {len(self.images['tiles'])} tiles from tilemap.")

        except pygame.error as e:
            print(f"!!! CRITICAL ERROR: Could not load tilemap.png. Error: {e}")
        except FileNotFoundError:
            print(f"!!! CRITICAL ERROR: Asset file not found at '{tilemap_path}'.")

        try:
            # Use the reliable helper function
            train_sheet_path = resource_path(os.path.join('src', 'assets', 'images', 'train_sprites.png'))
            train_sheet_image = pygame.image.load(train_sheet_path).convert_alpha()

            for line_num, coords in C.TRAIN_ASSETS.items():
                rect = pygame.Rect(coords[0], coords[1], C.TRAIN_ASSET_SIZE[0], C.TRAIN_ASSET_SIZE[1])
                train_surface = train_sheet_image.subsurface(rect)
                self.images['trains'][line_num] = train_surface
            
            print(f"    - Successfully loaded and sliced {len(self.images['trains'])} trains.")

        except FileNotFoundError:
            print(f"!!! WARNING: Asset file not found at '{train_sheet_path}'. Train sprites will not be available.")
        except (pygame.error, KeyError, AttributeError) as e:
            print(f"!!! WARNING: Could not load or slice train_sprites.png. Error: {e}")

    def get_tile_surface(self, tile_name: str) -> Optional[pygame.Surface]:
        """Convenience method to retrieve a specific tile's image surface."""
        return self.images['tiles'].get(tile_name)

    def _slice_spritesheet(self, sheet_path: str, frame_width: int, frame_height: int) -> List[pygame.Surface]:
        """A generic helper to slice any spritesheet into a list of frames."""
        frames = []
        try:
            # Use resource_path here as well for future-proofing
            full_path = resource_path(sheet_path)
            spritesheet = pygame.image.load(full_path).convert_alpha()
            sheet_width, sheet_height = spritesheet.get_size()
            for y in range(0, sheet_height, frame_height):
                for x in range(0, sheet_width, frame_width):
                    rect = pygame.Rect(x, y, frame_width, frame_height)
                    frames.append(spritesheet.subsurface(rect))
        except Exception as e:
            print(f"ERROR: Could not slice spritesheet at '{full_path}': {e}")
        return frames