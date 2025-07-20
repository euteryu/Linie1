# scenes/main_menu_scene.py
import pygame
import sys
from scenes.scene import Scene
from ui.components import Button # We'll create this component later

class MainMenuScene(Scene):
    def __init__(self, scene_manager, asset_manager):
        super().__init__(scene_manager)
        # We now accept asset_manager, future UI elements can use it.
        self.asset_manager = asset_manager
        self.theme = scene_manager.theme
        self.font_title = pygame.font.Font(self.theme["font"]["main"], self.theme["font"]["title_size"])
        
        center_x = self.scene_manager.screen.get_width() // 2
        
        self.title_surf = self.font_title.render("Linie 1: Gilded Rails", True, self.theme["colors"]["text_light"])
        self.title_rect = self.title_surf.get_rect(center=(center_x, 150))
        
        self.buttons = []
        button_texts = ["Play Game", "Load Game", "Save Game", "Settings", "Quit Game"]
        for i, text in enumerate(button_texts):
            button_rect = pygame.Rect(0, 0, 300, 60)
            button_rect.center = (center_x, 260 + i * 80)
            self.buttons.append(Button(text, button_rect, self.theme, self.on_button_click))

        # self.scene_manager.sounds.play_music('main_theme')

    def on_button_click(self, button_text):
        if button_text == "Play Game":
            self.scene_manager.go_to_scene("GAME")
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