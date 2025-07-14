# ui/palette_selection_state.py
from __future__ import annotations
import pygame
from typing import TYPE_CHECKING, Optional, Dict, List, Callable, Any

if TYPE_CHECKING:
    from game_logic.tile import TileType
    from game_logic.game import Game
    from mods.economic_mod.economic_mod import EconomicMod
    from scenes.game_scene import GameScene

from states.game_states import GameState
from common.rendering_utils import draw_text
import common.constants as C

class PaletteSelectionState(GameState):
    """
    A generic, transient game state that displays a palette of choices
    (like tiles) and executes a callback function with the chosen item.
    """
    # --- START OF CHANGE: The state is owned by a Scene. Changed 'visualizer' to 'scene' ---
    def __init__(self, scene: 'GameScene', title: str, items: List[Any],
                 item_surfaces: Dict[str, pygame.Surface], on_select_callback: Callable[[Any], None],
                 economic_mod_instance: Optional['EconomicMod'] = None,
                 current_capital: Optional[int] = None):
        super().__init__(scene) # Pass the scene to the parent constructor
        self.is_transient_state = True
        
        self.title = title
        self.message = "Choose an item, or press [ESC] / [X] to cancel."
        self.items_to_display = items
        self.item_surfaces = item_surfaces
        self.on_select_callback = on_select_callback
        
        self.palette_rects: Dict[int, pygame.Rect] = {}
        self.close_button_rect = pygame.Rect(C.SCREEN_WIDTH - 50, 10, 40, 40)

        self.eco_mod = economic_mod_instance
        self.current_capital = current_capital
    # --- END OF CHANGE ---

    def handle_event(self, event) -> bool:
        """Handles user input for the palette, now returning True if the event is consumed."""
        # Check for close keys first
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_BACKSPACE:
                self.scene.return_to_base_state()
                return True # Event was handled

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            # Check for close button click
            if self.close_button_rect.collidepoint(mouse_pos):
                self.scene.return_to_base_state()
                return True # Event was handled
            
            # Check for item selection
            for index, rect in self.palette_rects.items():
                if rect.collidepoint(mouse_pos):
                    chosen_item = self.items_to_display[index]
                    
                    if self.eco_mod and self.current_capital is not None:
                        price = self.eco_mod.get_market_price(self.game, chosen_item)
                        supply = self.game.deck_manager.tile_draw_pile.count(chosen_item)
                        if self.current_capital < price or supply == 0:
                            self.scene.sounds.play('error')
                            return True # Handled the invalid click

                    self.on_select_callback(chosen_item)
                    return True # Handled the valid click
        
        return False # Event was not handled by this state

    def draw(self, screen):
        overlay = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SRCALPHA); overlay.fill((20, 0, 40, 220)); screen.blit(overlay, (0, 0))
        draw_text(screen, self.title, 100, 50, C.COLOR_WHITE, size=36)
        draw_text(screen, self.message, 100, C.SCREEN_HEIGHT - 50, C.COLOR_WHITE, size=20)
        close_rect = self.close_button_rect; pygame.draw.rect(screen, (200, 50, 50), close_rect)
        if close_rect.collidepoint(pygame.mouse.get_pos()): pygame.draw.rect(screen, C.COLOR_WHITE, close_rect, 3)
        else: pygame.draw.rect(screen, C.COLOR_WHITE, close_rect, 1)
        draw_text(screen, "X", close_rect.centerx, close_rect.centery, C.COLOR_WHITE, 30, True, True)

        self.palette_rects.clear()
        x, y = 100, 120
        tiles_per_row, tile_size, spacing, y_spacing = 8, C.TILE_SIZE, 10, C.TILE_SIZE + 40
        for i, item in enumerate(self.items_to_display):
            rect = pygame.Rect(x, y, tile_size, tile_size)
            self.palette_rects[i] = rect
            is_affordable, is_in_stock, market_price, supply = True, True, 0, 0
            if self.eco_mod:
                market_price = self.eco_mod.get_market_price(self.game, item)
                supply = self.game.deck_manager.tile_draw_pile.count(item)
                if self.current_capital is not None and self.current_capital < market_price: is_affordable = False
                if supply == 0: is_in_stock = False
            if item_surf := self.item_surfaces.get(item.name):
                tile_image = item_surf.copy()
                if not is_affordable or not is_in_stock: tile_image.set_alpha(80)
                screen.blit(tile_image, rect.topleft)
            if rect.collidepoint(pygame.mouse.get_pos()) and is_affordable and is_in_stock: pygame.draw.rect(screen, C.COLOR_HIGHLIGHT, rect, 3)
            else: pygame.draw.rect(screen, C.COLOR_BLACK, rect, 1)
            price_color = C.COLOR_WHITE if is_affordable else (255, 80, 80)
            supply_color = C.COLOR_WHITE if is_in_stock else (255, 80, 80)
            draw_text(screen, f"${market_price}", rect.centerx, rect.bottom + 15, price_color, 18, True)
            draw_text(screen, f"Supply: {supply}", rect.centerx, rect.bottom + 30, supply_color, 14, True)
            x += tile_size + spacing
            if (i + 1) % tiles_per_row == 0: x, y = 100, y + y_spacing