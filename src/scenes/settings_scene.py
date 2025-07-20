# scenes/settings_scene.py
import pygame
from scenes.scene import Scene
from ui.components import Button, Slider

class SettingsScene(Scene):
    def __init__(self, scene_manager, asset_manager):
        super().__init__(scene_manager)
        # We now accept asset_manager
        self.asset_manager = asset_manager
        self.theme = scene_manager.theme
        self.font_header = pygame.font.Font(self.theme["font"]["main"], self.theme["font"]["header_size"])
        
        center_x = self.scene_manager.screen.get_width() // 2
        
        # --- Volume Control ---
        self.volume_label = self.font_header.render("Music Volume", True, self.theme["colors"]["text_light"])
        self.volume_slider = Slider(
            pygame.Rect(center_x - 100, 150, 200, 20), self.theme, 0.0, 1.0,
            pygame.mixer.music.get_volume(),
            self.scene_manager.sounds.set_music_volume
        )
        
        # --- Theme Selection ---
        self.theme_label = self.font_header.render("UI Theme", True, self.theme["colors"]["text_light"])
        self.theme_buttons = [
            Button("Light", pygame.Rect(center_x - 110, 250, 100, 40), self.theme, self.on_theme_change),
            Button("Dark", pygame.Rect(center_x + 10, 250, 100, 40), self.theme, self.on_theme_change)
        ]
        
        # --- Back Button ---
        self.back_button = Button("Back to Menu", pygame.Rect(center_x - 150, 500, 300, 60), self.theme, lambda x: self.scene_manager.go_to_scene("MAIN_MENU"))

    def on_theme_change(self, theme_name):
        self.scene_manager.load_theme(f"ui_theme_{theme_name.lower()}.json")
        # Re-initialize scene to apply new theme immediately
        self.scene_manager.scenes["SETTINGS"] = SettingsScene(self.scene_manager, self.asset_manager)
        self.scene_manager.current_scene = self.scene_manager.scenes["SETTINGS"]

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.scene_manager.go_to_scene("MAIN_MENU")
            self.volume_slider.handle_event(event)
            for button in self.theme_buttons:
                button.handle_event(event)
            self.back_button.handle_event(event)
    
    def update(self, dt):
        pass

    def draw(self, screen):
        screen.fill(self.theme["colors"]["background"])
        # Draw volume
        screen.blit(self.volume_label, self.volume_label.get_rect(center=(screen.get_width() // 2, 110)))
        self.volume_slider.draw(screen)
        # Draw theme
        screen.blit(self.theme_label, self.theme_label.get_rect(center=(screen.get_width() // 2, 210)))
        for button in self.theme_buttons:
            button.draw(screen)
        # Draw back button
        self.back_button.draw(screen)