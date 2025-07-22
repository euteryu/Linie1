# src/common/layout.py
from typing import Tuple

class LayoutConstants:
    """
    A class that calculates all UI layout dimensions and positions based on the
    current screen resolution, ensuring the game and editor scale correctly.
    """
    def __init__(self, initial_screen_size: Tuple[int, int]):
        # The resolution the game was originally designed and balanced for.
        # All original pixel values are based on this native resolution.
        self.NATIVE_WIDTH = 1920
        self.NATIVE_HEIGHT = 1080
        
        # Initialize all attributes to zero before calculation
        self.SCREEN_WIDTH = 0
        self.SCREEN_HEIGHT = 0
        self.scale = 1.0

        # Board and Grid
        self.VISIBLE_GRID_ROWS = 12
        self.VISIBLE_GRID_COLS = 12
        self.BOARD_AREA_HEIGHT = 0
        self.TILE_SIZE = 0
        self.BOARD_DRAW_WIDTH = 0
        self.BOARD_DRAW_HEIGHT = 0
        self.BOARD_X_OFFSET = 0
        self.BOARD_Y_OFFSET = 0
        
        # Main UI Panel
        self.UI_PANEL_MARGIN_LEFT = 0
        self.UI_PANEL_X = 0
        self.UI_PANEL_Y = 0
        self.UI_PANEL_WIDTH = 0
        self.UI_PANEL_HEIGHT = 0
        
        # UI Elements
        self.UI_TEXT_X = 0
        self.UI_LINE_HEIGHT = 0
        self.UI_TURN_INFO_Y = 0
        self.UI_ROUTE_INFO_Y = 0
        
        # Hand Panel
        self.HAND_TILE_SIZE = 0
        self.HAND_SPACING = 0
        self.HAND_TILE_COUNT = 5
        self.UI_HAND_TITLE_Y = 0
        self.HAND_AREA_X = 0
        self.HAND_AREA_Y = 0
        
        # Message Panel
        self.UI_SELECTED_TILE_Y = 0
        self.UI_MESSAGE_Y = 0
        
        # Buttons
        self.BUTTON_WIDTH = 0
        self.BUTTON_HEIGHT = 0
        self.BUTTON_SPACING = 0
        self.BUTTON_MARGIN_X = 0
        self.BUTTON_MARGIN_Y = 0
        
        # Debug Panel
        self.DEBUG_BUTTON_WIDTH = 0
        self.DEBUG_BUTTON_HEIGHT = 0
        self.DEBUG_BUTTON_X = 0
        self.DEBUG_BUTTON_Y = 0
        self.DEBUG_TILE_SIZE = 0
        self.DEBUG_TILE_SPACING = 0
        self.DEBUG_TILES_PER_ROW = 4
        self.DEBUG_PANEL_Y = 0
        
        # Run the calculation with the initial screen size
        self.recalculate(initial_screen_size)

    def recalculate(self, new_screen_size: Tuple[int, int]):
        """Updates all layout constants based on a new screen size."""
        self.SCREEN_WIDTH, self.SCREEN_HEIGHT = new_screen_size
        
        scale_w = self.SCREEN_WIDTH / self.NATIVE_WIDTH
        scale_h = self.SCREEN_HEIGHT / self.NATIVE_HEIGHT
        self.scale = min(scale_w, scale_h)

        # --- Recalculate all values based on the new scale factor ---
        
        # Board and Grid
        self.BOARD_AREA_HEIGHT = int(972 * self.scale)
        self.TILE_SIZE = self.BOARD_AREA_HEIGHT // self.VISIBLE_GRID_ROWS
        self.BOARD_DRAW_WIDTH = self.TILE_SIZE * self.VISIBLE_GRID_COLS
        self.BOARD_DRAW_HEIGHT = self.TILE_SIZE * self.VISIBLE_GRID_ROWS
        self.BOARD_X_OFFSET = int(77 * self.scale)
        self.BOARD_Y_OFFSET = (self.SCREEN_HEIGHT - self.BOARD_DRAW_HEIGHT) // 2
        
        # Main UI Panel
        self.UI_PANEL_MARGIN_LEFT = int(50 * self.scale)
        self.UI_PANEL_X = self.BOARD_X_OFFSET + self.BOARD_DRAW_WIDTH + self.UI_PANEL_MARGIN_LEFT
        self.UI_PANEL_Y = self.BOARD_Y_OFFSET
        self.UI_PANEL_WIDTH = self.SCREEN_WIDTH - self.UI_PANEL_X - int(40 * self.scale)
        self.UI_PANEL_HEIGHT = self.BOARD_DRAW_HEIGHT
        
        # UI Elements
        self.UI_TEXT_X = self.UI_PANEL_X + int(15 * self.scale)
        self.UI_LINE_HEIGHT = int(28 * self.scale)
        self.UI_TURN_INFO_Y = self.UI_PANEL_Y + int(15 * self.scale)
        self.UI_ROUTE_INFO_Y = self.UI_TURN_INFO_Y + self.UI_LINE_HEIGHT
        
        # Hand Panel
        self.HAND_TILE_SIZE = int(min(self.TILE_SIZE * 0.8, self.UI_PANEL_WIDTH * 0.7))
        self.HAND_SPACING = int(15 * self.scale)
        self.UI_HAND_TITLE_Y = self.UI_ROUTE_INFO_Y + self.UI_LINE_HEIGHT * 2
        self.HAND_AREA_X = self.UI_PANEL_X + int(15 * self.scale)
        self.HAND_AREA_Y = self.UI_HAND_TITLE_Y + self.UI_LINE_HEIGHT
        
        # Message Panel
        self.UI_SELECTED_TILE_Y = self.HAND_AREA_Y + self.HAND_TILE_COUNT * (self.HAND_TILE_SIZE + self.HAND_SPACING) + int(20 * self.scale)
        self.UI_MESSAGE_Y = self.UI_SELECTED_TILE_Y + self.UI_LINE_HEIGHT
        
        # Buttons
        self.BUTTON_WIDTH = int(120 * self.scale)
        self.BUTTON_HEIGHT = int(40 * self.scale)
        self.BUTTON_SPACING = int(8 * self.scale)
        self.BUTTON_MARGIN_X = int(10 * self.scale)
        self.BUTTON_MARGIN_Y = int(10 * self.scale)
        
        # Debug Panel
        self.DEBUG_BUTTON_WIDTH = int(150 * self.scale)
        self.DEBUG_BUTTON_HEIGHT = int(30 * self.scale)
        self.DEBUG_BUTTON_X = self.UI_PANEL_X + (self.UI_PANEL_WIDTH - self.DEBUG_BUTTON_WIDTH) // 2
        self.DEBUG_BUTTON_Y = self.UI_PANEL_Y + self.UI_PANEL_HEIGHT - self.DEBUG_BUTTON_HEIGHT - int(97 * self.scale)
        self.DEBUG_TILE_SIZE = self.TILE_SIZE // 2
        self.DEBUG_TILE_SPACING = int(5 * self.scale)
        self.DEBUG_PANEL_Y = self.UI_HAND_TITLE_Y + self.UI_LINE_HEIGHT