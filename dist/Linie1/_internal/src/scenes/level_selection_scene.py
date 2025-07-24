# src/scenes/level_selection_scene.py
import pygame
import sys
import os
from scenes.scene import Scene
from ui.components import Button
from levels.level import Level

class LevelSelectionScene(Scene):
    """
    A new scene where the player chooses which map to play on.
    """
    def __init__(self, scene_manager, asset_manager):
        super().__init__(scene_manager)
        self.asset_manager = asset_manager
        self.theme = scene_manager.theme
        self.font_title = pygame.font.Font(self.theme["font"]["main"], self.theme["font"]["title_size"])
        
        center_x = self.scene_manager.screen.get_width() // 2
        
        self.title_surf = self.font_title.render("Select a Level", True, self.theme["colors"]["text_light"])
        self.title_rect = self.title_surf.get_rect(center=(center_x, 100))
        
        # Define the buttons for our pre-set levels and the editor
        self.buttons = []
        level_options = {
            "Original (12x12)": "default_12x12.json",
            "Tiny (5x5)": "tiny_5x5.json", # Assumes you have created this file
            "Puzzle (4x8)": "puzzle_4x8.json", # Assumes you have created this file
            "Create Your Own": "launch_editor"
        }
        
        for i, (text, action) in enumerate(level_options.items()):
            button_rect = pygame.Rect(0, 0, 400, 70)
            button_rect.center = (center_x, 220 + i * 100)
            self.buttons.append(Button(text, button_rect, self.theme, lambda t=text, a=action: self.on_button_click(t, a)))

    def on_button_click(self, button_text: str, action: str):
        """Handles clicks on the level selection buttons."""
        if action == "launch_editor":
            print("Launching Level Editor...")
            self.scene_manager.launch_level_editor()
        else:
            # This is a level file. Tell the App to start a new game with it.
            print(f"Starting new game with level: {action}")
            self.scene_manager.start_new_game(action)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                # Pressing Escape on this screen goes back to the main menu
                self.scene_manager.go_to_scene("MAIN_MENU")
            for button in self.buttons:
                button.handle_event(event)

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill(self.theme["colors"]["background"])
        screen.blit(self.title_surf, self.title_rect)
        for button in self.buttons:
            button.draw(screen)