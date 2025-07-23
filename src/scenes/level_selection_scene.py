import pygame
import sys
import os
from scenes.scene import Scene
from ui.components import Button
from levels.level import Level

class LevelSelectionScene(Scene):
    def __init__(self, scene_manager, asset_manager):
        super().__init__(scene_manager)
        self.asset_manager = asset_manager
        self.theme = scene_manager.theme
        self.font_title = pygame.font.Font(self.theme["font"]["main"], self.theme["font"]["title_size"])
        
        center_x = self.scene_manager.screen.get_width() // 2
        
        self.title_surf = self.font_title.render("Select a Level", True, self.theme["colors"]["text_light"])
        self.title_rect = self.title_surf.get_rect(center=(center_x, 100))

        self.buttons = []
        
        level_options = {
            # Text: (level_data_file, layout_name, background_asset_name)
            "Original (12x12)": ("default_12x12.json", "game_layout_12x12", "game_background_12x12"),
            "Tiny (5x5)":       ("tiny_5x5.json", "game_layout_5x5", "game_background_5x5"),
            "Puzzle (4x8)":     ("puzzle_4x8.json", "game_layout_4x8", "game_background_4x8"),
            "Create Your Own":  ("launch_editor", None, None)
        }
        
        for i, (text, (action, layout_name, bg_name)) in enumerate(level_options.items()):
            button_rect = pygame.Rect(0, 0, 400, 70)
            button_rect.center = (center_x, 220 + i * 100)
            self.buttons.append(Button(text, button_rect, self.theme, lambda a=action, ln=layout_name, bn=bg_name: self.on_button_click(a, ln, bn)))

    def on_button_click(self, action: str, layout_name: str | None, background_name: str | None):
        """Handles clicks, now passing all three necessary pieces of info."""
        if action == "launch_editor":
            self.scene_manager.launch_level_editor()
        else:
            print(f"Starting new game with level: {action}, layout: {layout_name}, background: {background_name}")
            self.scene_manager.start_new_game(action, layout_name, background_name)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: self.scene_manager.go_to_scene("MAIN_MENU")
            for button in self.buttons: button.handle_event(event)
    def update(self, dt): pass
    def draw(self, screen):
        screen.fill(self.theme["colors"]["background"])
        screen.blit(self.title_surf, self.title_rect)
        for button in self.buttons: button.draw(screen)