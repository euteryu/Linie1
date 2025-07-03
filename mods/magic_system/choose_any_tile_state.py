# mods/magic_system/choose_any_tile_state.py
from __future__ import annotations
import pygame
from typing import TYPE_CHECKING, Optional, Dict

if TYPE_CHECKING:
    from visualizer import Linie1Visualizer
    from game_logic.tile import TileType

# Use absolute import paths relative to your project root (or the 'mods' dir if it's on sys.path)
# Since 'mods' is added to sys.path, we can import from 'game_states' and 'game_logic' directly.
from game_states import GameState
from game_logic.commands import PlaceTileCommand
import constants as C # Constants should be imported directly from the root if on sys.path

class ChooseAnyTileState(GameState):
    """
    A temporary game state triggered by the Magic System mod.
    Allows the player to select any tile from the game to place on the board.
    """
    def __init__(self, visualizer: 'Linie1Visualizer', super_tile_instance: 'TileType'):
        super().__init__(visualizer)
        self.super_tile_to_consume = super_tile_instance
        self.all_tile_types = list(self.game.tile_types.values())
        self.selected_tile_index: Optional[int] = None
        self.current_orientation = 0
        self.message = "Super Tile! Choose any tile to place."
        self.palette_rects: Dict[int, pygame.Rect] = {}

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.visualizer.update_current_state_for_player()
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            # 1. Check for click on the tile palette
            for index, rect in self.palette_rects.items():
                if rect.collidepoint(mouse_pos):
                    self.selected_tile_index = index
                    self.current_orientation = 0
                    self.message = f"Selected: {self.all_tile_types[index].name}. Place on board."
                    return
            
            # 2. Check for click on the board
            if self.selected_tile_index is not None:
                if C.BOARD_X_OFFSET <= mouse_pos[0] < C.BOARD_X_OFFSET + C.BOARD_DRAW_WIDTH and \
                   C.BOARD_Y_OFFSET <= mouse_pos[1] < C.BOARD_Y_OFFSET + C.BOARD_DRAW_HEIGHT:
                    
                    grid_r = (mouse_pos[1] - C.BOARD_Y_OFFSET) // C.TILE_SIZE + C.PLAYABLE_ROWS[0]
                    grid_c = (mouse_pos[0] - C.BOARD_X_OFFSET) // C.TILE_SIZE + C.PLAYABLE_COLS[0]
                    
                    chosen_tile = self.all_tile_types[self.selected_tile_index]
                    player = self.game.get_active_player()

                    if self.game.check_placement_validity(chosen_tile, self.current_orientation, grid_r, grid_c)[0]:
                        player.hand.append(chosen_tile)
                        # We must check if the super tile is still in hand before removing,
                        # in case of rapid clicks or edge cases.
                        if self.super_tile_to_consume in player.hand:
                            player.hand.remove(self.super_tile_to_consume)
                        
                        command = PlaceTileCommand(self.game, player, chosen_tile, self.current_orientation, grid_r, grid_c)
                        if self.game.command_history.execute_command(command):
                             self.game.actions_taken_this_turn += 1
                             self.message = "Magic tile placed!"
                             self.visualizer.update_current_state_for_player()
                        else:
                            # Revert hand changes if command failed
                            if chosen_tile in player.hand: player.hand.remove(chosen_tile)
                            player.hand.append(self.super_tile_to_consume)
                            self.message = "Placement failed."
                    else:
                        self.message = "Invalid placement location."
        
        # Add rotation
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            self.current_orientation = (self.current_orientation + 90) % 360

    def draw(self, screen):
        self.visualizer.draw_board(screen)
        
        overlay = pygame.Surface((C.SCREEN_WIDTH, C.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        self.visualizer.draw_text(screen, "Choose Your Magical Tile", 100, 50, C.COLOR_WHITE, size=36)
        
        self.palette_rects.clear()
        x, y = 100, 100
        tiles_per_row = 10
        for i, tile_type in enumerate(self.all_tile_types):
            rect = pygame.Rect(x, y, C.TILE_SIZE, C.TILE_SIZE)
            self.palette_rects[i] = rect

            pygame.draw.rect(screen, C.COLOR_UI_BG, rect)
            tile_surf = self.visualizer.tile_surfaces.get(tile_type.name)
            if tile_surf: screen.blit(tile_surf, rect.topleft)
            pygame.draw.rect(screen, C.COLOR_BLACK, rect, 1)

            if self.selected_tile_index == i:
                pygame.draw.rect(screen, C.COLOR_SELECTED, rect, 3)

            x += C.TILE_SIZE + 10
            if (i + 1) % tiles_per_row == 0:
                x = 100
                y += C.TILE_SIZE + 10

        if self.selected_tile_index is not None:
            tile_to_preview = self.all_tile_types[self.selected_tile_index]
            # We need to call the visualizer's preview method if it exists
            # This shows the dependency, making it clear.
            if hasattr(self.visualizer, 'draw_preview'):
                self.visualizer.draw_preview(screen, tile_to_preview, self.current_orientation)