# scenes/main_menu_scene.py
import pygame
import sys
from scenes.scene import Scene
from ui.components import Button # We'll create this component later
from common.layout import LayoutConstants

class MainMenuScene(Scene):
    def __init__(self, scene_manager, asset_manager, layout: LayoutConstants):
        super().__init__(scene_manager)
        self.asset_manager = asset_manager
        self.layout = layout # Store the layout object
        
        self.theme = scene_manager.theme
        self.font_title = pygame.font.Font(self.theme["font"]["main"], self.theme["font"]["title_size"])
        
        # Use dynamic layout constants ---
        center_x = self.layout.SCREEN_WIDTH // 2
        
        self.title_surf = self.font_title.render("Linie 1: Gilded Rails", True, self.theme["colors"]["text_light"])
        self.title_rect = self.title_surf.get_rect(center=(center_x, int(self.layout.SCREEN_HEIGHT * 0.2)))
        
        self.buttons = []
        button_texts = ["Play Game", "Load Game", "Settings", "Quit Game"]
        button_width = int(self.layout.SCREEN_WIDTH * 0.25)
        button_height = int(self.layout.SCREEN_HEIGHT * 0.08)
        
        for i, text in enumerate(button_texts):
            button_rect = pygame.Rect(0, 0, button_width, button_height)
            button_y = self.layout.SCREEN_HEIGHT * 0.35 + i * (button_height + int(self.layout.SCREEN_HEIGHT * 0.02))
            button_rect.center = (center_x, button_y)
            # This ensures that on_button_click receives the correct text argument.
            self.buttons.append(Button(text, button_rect, self.theme, lambda t=text: self.on_button_click(t)))

    def on_button_click(self, button_text):
        if button_text == "Play Game":
            self.scene_manager.go_to_scene("LEVEL_SELECTION")
        elif button_text == "Load Game":
            self.scene_manager.load_game_action()
        elif button_text == "Save Game":
            self.scene_manager.save_game_action()
        elif button_text == "Settings":
            self.scene_manager.go_to_scene("SETTINGS")
        elif button_text == "Quit Game":
            pygame.quit()
            sys.exit()
        else:
            print(f"Button '{button_text}' clicked (not implemented yet).")  # Test use

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
            for button in self.buttons:
                button.handle_event(event)

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill(self.theme["colors"]["background"])
        screen.blit(self.title_surf, self.title_rect)
        for button in self.buttons:
            button.draw(screen)