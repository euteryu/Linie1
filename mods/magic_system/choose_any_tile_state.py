# mods/magic_system/choose_any_tile_state.py
from __future__ import annotations
import pygame
from typing import TYPE_CHECKING, Optional, Dict

if TYPE_CHECKING:
    from visualizer import Linie1Visualizer
    from game_logic.tile import TileType

from game_states import GameState, LayingTrackState
import constants as C

class ChooseAnyTileState(GameState):
    """
    A temporary game state for the Magic System mod. It handles the selection
    of a tile from the palette to REPLACE the Super Tile in the player's hand,
    then correctly transitions back to the main game.
    """
    def __init__(self, visualizer: 'Linie1Visualizer', super_tile_instance: 'TileType'):
        super().__init__(visualizer)
        self.is_transient_state = True # Mark this as a special mod state
        self.super_tile_to_consume = super_tile_instance
        self.all_tile_types = list(self.game.tile_types.values())
        self.message = "Choose a tile to craft, or press [ESC] / [X] to cancel."
        self.palette_rects: Dict[int, pygame.Rect] = {}
        self.close_button_rect = pygame.Rect(C.SCREEN_WIDTH - 50, 10, 40, 40)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            # --- THIS IS THE FIX ---
            # Request a return to the base game state.
            self.visualizer.return_to_base_state()
            # --- END OF FIX ---
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            
            if self.close_button_rect.collidepoint(mouse_pos):
                # --- THIS IS THE FIX ---
                self.visualizer.return_to_base_state()
                # --- END OF FIX ---
                return

            for index, rect in self.palette_rects.items():
                if rect.collidepoint(mouse_pos):
                    chosen_tile = self.all_tile_types[index]
                    self._perform_tile_swap(chosen_tile)
                    return

    def _perform_tile_swap(self, chosen_tile: 'TileType'):
        """Replaces the Super Tile in the player's hand with the chosen tile."""
        player = self.game.get_active_player()
        
        tile_to_remove = None
        for i, hand_tile in enumerate(player.hand):
            if hasattr(hand_tile, 'is_super_tile') and hand_tile.is_super_tile and hand_tile == self.super_tile_to_consume:
                tile_to_remove = i
                break
        
        if tile_to_remove is not None:
            player.hand.pop(tile_to_remove)
            player.hand.append(chosen_tile)
            print(f"Super Tile was replaced with a '{chosen_tile.name}'.")
        else:
            print("Warning: Super Tile instance not found in hand. No swap occurred.")
        
        # The spell is complete. Transition back to the normal game state.
        # self.visualizer.update_current_state_for_player()  # obsolete - don't directly change state, request state change
        self.visualizer.return_to_base_state()

    def draw(self, screen):
        """Renders the spell-casting UI on top of the main game screen."""
        # 1. Draw the base game screen completely.
        # It's better to ask the visualizer to do this rather than creating a temp state.
        self.visualizer.draw_board(screen)
        self.visualizer.draw_ui(screen, "Casting Spell...", "")
        # This will also draw the player's hand, which is good context.
        if isinstance(self.visualizer.current_state, LayingTrackState):
             self.visualizer.current_state.draw(screen)

        # 2. Draw the dimming overlay.
        overlay = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((20, 0, 40, 190))
        screen.blit(overlay, (0, 0))

        # 3. Draw this state's specific UI elements on top.
        self.visualizer.draw_text(screen, "Craft Your Tile", 100, 50, C.COLOR_WHITE, size=36)
        self.visualizer.draw_text(screen, self.message, 100, C.SCREEN_HEIGHT - 50, C.COLOR_WHITE, size=20)
        
        self.palette_rects.clear()
        # ... (palette drawing logic is correct) ...
        x, y = 100, 120
        tiles_per_row, tile_size, spacing = 10, C.TILE_SIZE, 10
        for i, tile_type in enumerate(self.all_tile_types):
            rect = pygame.Rect(x, y, tile_size, tile_size)
            self.palette_rects[i] = rect
            pygame.draw.rect(screen, C.COLOR_UI_BG, rect)
            tile_surf = self.visualizer.tile_surfaces.get(tile_type.name)
            if tile_surf: screen.blit(tile_surf, rect.topleft)
            if rect.collidepoint(pygame.mouse.get_pos()):
                pygame.draw.rect(screen, C.COLOR_HIGHLIGHT, rect, 3)
            else:
                pygame.draw.rect(screen, C.COLOR_BLACK, rect, 1)
            x += tile_size + spacing
            if (i + 1) % tiles_per_row == 0: x = 100; y += tile_size + spacing
        
        # Close button
        close_rect = self.close_button_rect
        pygame.draw.rect(screen, (200, 50, 50), close_rect)
        if close_rect.collidepoint(pygame.mouse.get_pos()):
            pygame.draw.rect(screen, C.COLOR_WHITE, close_rect, 3)
        else:
            pygame.draw.rect(screen, C.COLOR_WHITE, close_rect, 1)
        self.visualizer.draw_text(screen, "X", close_rect.centerx - 8, close_rect.centery - 12, C.COLOR_WHITE, size=30)