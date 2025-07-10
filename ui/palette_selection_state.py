# ui/palette_selection_state.py
from __future__ import annotations
import pygame
from typing import TYPE_CHECKING, Optional, Dict, List, Callable, Any

if TYPE_CHECKING:
    from visualizer import Linie1Visualizer
    from game_logic.tile import TileType

from game_states import GameState
from rendering_utils import draw_text
import constants as C

class PaletteSelectionState(GameState):
    """
    A generic, transient game state that displays a palette of choices
    (like tiles) and executes a callback function with the chosen item.
    """
    def __init__(self, visualizer: 'Linie1Visualizer', title: str, items: List[Any],
                 item_surfaces: Dict[str, pygame.Surface], on_select_callback: Callable[[Any], None]):
        super().__init__(visualizer)
        self.is_transient_state = True
        
        self.title = title
        self.message = "Choose an item, or press [ESC] / [X] to cancel."
        self.items_to_display = items
        self.item_surfaces = item_surfaces
        self.on_select_callback = on_select_callback
        
        self.palette_rects: Dict[int, pygame.Rect] = {}
        self.close_button_rect = pygame.Rect(C.SCREEN_WIDTH - 50, 10, 40, 40)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.visualizer.return_to_base_state()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = event.pos
            if self.close_button_rect.collidepoint(mouse_pos):
                self.visualizer.return_to_base_state()
                return
            for index, rect in self.palette_rects.items():
                if rect.collidepoint(mouse_pos):
                    chosen_item = self.items_to_display[index]
                    self.on_select_callback(chosen_item)
                    # The callback is now responsible for returning to the base state.
                    return

    def draw(self, screen):
        # Dimming overlay
        overlay = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((20, 0, 40, 190))
        screen.blit(overlay, (0, 0))

        # UI elements
        draw_text(screen, self.title, 100, 50, C.COLOR_WHITE, size=36)
        draw_text(screen, self.message, 100, C.SCREEN_HEIGHT - 50, C.COLOR_WHITE, size=20)
        
        # Close button
        close_rect = self.close_button_rect
        pygame.draw.rect(screen, (200, 50, 50), close_rect)
        if close_rect.collidepoint(pygame.mouse.get_pos()):
            pygame.draw.rect(screen, C.COLOR_WHITE, close_rect, 3)
        else:
            pygame.draw.rect(screen, C.COLOR_WHITE, close_rect, 1)
        draw_text(screen, "X", close_rect.centerx, close_rect.centery, C.COLOR_WHITE, size=30, center_x=True, center_y=True)

        # Draw the palette of items
        self.palette_rects.clear()
        x, y = 100, 120
        tiles_per_row, tile_size, spacing = 10, C.TILE_SIZE, 10
        for i, item in enumerate(self.items_to_display):
            rect = pygame.Rect(x, y, tile_size, tile_size)
            self.palette_rects[i] = rect
            pygame.draw.rect(screen, C.COLOR_UI_BG, rect)
            
            # Use the pre-rendered surfaces
            item_surf = self.item_surfaces.get(item.name)
            if item_surf:
                screen.blit(item_surf, rect.topleft)

            if rect.collidepoint(pygame.mouse.get_pos()):
                pygame.draw.rect(screen, C.COLOR_HIGHLIGHT, rect, 3)
            else:
                pygame.draw.rect(screen, C.COLOR_BLACK, rect, 1)
                
            x += tile_size + spacing
            if (i + 1) % tiles_per_row == 0:
                x = 100
                y += tile_size + spacing

    def on_hand_tile_clicked(self, game: 'Game', player: 'Player', tile_type: 'TileType') -> bool:
        """
        Handles special behavior when a hand tile is clicked. This method
        checks for sell mode first, then checks for special permit tiles.
        """
        player_mod_data = player.components.get(self.mod_id)
        if not player_mod_data:
            return False

        # --- Priority 1: Check if Sell Mode is active ---
        if player_mod_data.get('sell_mode_active', False):
            player_mod_data['sell_mode_active'] = False

            if hasattr(tile_type, 'is_requisition_permit') and tile_type.is_requisition_permit:
                game.visualizer.current_state.message = "Cannot sell a Requisition Permit."
                return True

            sell_rewards = self.config.get("sell_rewards", {})
            reward = sell_rewards.get(tile_type.name, sell_rewards.get("default", 0))

            command = SellToScrapyardCommand(game, player, self.mod_id, tile_type, reward)
            if game.command_history.execute_command(command):
                game.visualizer.current_state.message = f"Sold {tile_type.name} for ${reward}."
            else:
                pass # Command sets its own failure message
            
            return True

        # --- Priority 2: Check if the clicked tile is a Requisition Permit ---
        if hasattr(tile_type, 'is_requisition_permit') and tile_type.is_requisition_permit:
            if game.visualizer:
                
                # --- START OF FIX: The logic for the callback is now complete ---
                scene = game.visualizer # Get the scene instance
                
                def on_tile_selected(chosen_tile: 'TileType'):
                    """This function is executed when the player picks a tile from the palette."""
                    # 1. Find and remove the first available permit from the hand.
                    permit_index = -1
                    for i, hand_tile in enumerate(player.hand):
                        if hasattr(hand_tile, 'is_requisition_permit') and hand_tile.is_requisition_permit:
                            permit_index = i
                            break
                    
                    if permit_index != -1:
                        # 2. Perform the swap
                        player.hand.pop(permit_index)
                        player.hand.append(chosen_tile)
                        print(f"Permit was fulfilled and replaced with a '{chosen_tile.name}'.")
                    else:
                        print("Error: Could not find permit in hand to fulfill.")
                    
                    # 3. IMPORTANT: Return to the main game state.
                    scene.return_to_base_state()

                # Request a state change to the generic PaletteSelectionState.
                # Pass it the scene, title, items to show, and the callback function we just defined.
                scene.request_state_change(
                    lambda v: PaletteSelectionState(
                        visualizer=v, # 'v' is the scene instance
                        title="Fulfill Requisition",
                        items=list(game.tile_types.values()),
                        item_surfaces=scene.tile_surfaces,
                        on_select_callback=on_tile_selected
                    )
                )
                # --- END OF FIX ---

            return True # The click was handled by the mod.
        
        # If neither of the above conditions were met, the mod does nothing with this click.
        return False