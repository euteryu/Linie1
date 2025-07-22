# src/scenes/resolution_confirmation_scene.py
import pygame
from scenes.scene import Scene
from ui.components import Button
from common.rendering_utils import draw_text

class ResolutionConfirmationScene(Scene):
    """A transient scene to confirm a display resolution change."""
    def __init__(self, scene_manager, asset_manager, layout, new_res, prev_state):
        super().__init__(scene_manager)
        self.asset_manager = asset_manager
        self.layout = layout
        self.theme = scene_manager.theme
        self.new_resolution = new_res
        self.previous_resolution, self.previous_fullscreen = prev_state # Unpack the previous state
        self.is_new_fullscreen = (self.scene_manager.screen.get_flags() & pygame.FULLSCREEN) != 0

        self.start_time = pygame.time.get_ticks()
        self.countdown_duration = 15000  # 15 seconds in milliseconds

        center_x = self.layout.SCREEN_WIDTH // 2
        center_y = self.layout.SCREEN_HEIGHT // 2

        self.confirm_button = Button("Confirm", pygame.Rect(center_x - 160, center_y + 50, 150, 50), self.theme, self._confirm)
        self.revert_button = Button("Revert", pygame.Rect(center_x + 10, center_y + 50, 150, 50), self.theme, self._revert)

    def _confirm(self, _=None):
        self.scene_manager.settings['resolution'] = self.new_resolution
        self.scene_manager.settings['fullscreen'] = self.is_new_fullscreen
        self.scene_manager.save_settings()
        self.scene_manager.go_to_scene("SETTINGS")

    def _revert(self, _=None):
        print("Reverting resolution...")
        # Pass the full previous state back to change_resolution
        self.scene_manager.change_resolution(self.previous_resolution, self.previous_fullscreen, confirm=False)
        self.scene_manager.go_to_scene("SETTINGS")

    def handle_events(self, events):
        for event in events:
            self.confirm_button.handle_event(event)
            self.revert_button.handle_event(event)

    def update(self, dt):
        if pygame.time.get_ticks() - self.start_time > self.countdown_duration:
            self._revert()

    def draw(self, screen):
        # Draw a semi-transparent overlay
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Draw text
        remaining_seconds = (self.countdown_duration - (pygame.time.get_ticks() - self.start_time)) // 1000 + 1
        draw_text(screen, "Keep this resolution?", screen.get_width() // 2, screen.get_height() // 2 - 50, self.theme["colors"]["text_light"], 48, True, True)
        draw_text(screen, f"Reverting in {remaining_seconds} seconds...", screen.get_width() // 2, screen.get_height() // 2, self.theme["colors"]["text_muted"], 24, True, True)
        
        # Draw buttons
        self.confirm_button.draw(screen)
        self.revert_button.draw(screen)