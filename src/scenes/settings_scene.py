# scenes/settings_scene.py
import pygame
from scenes.scene import Scene
from ui.components import Button, Slider
from common.layout import LayoutConstants
from typing import List, Dict, Tuple, Optional, Set, Any


class SettingsScene(Scene):
    def __init__(self, scene_manager, asset_manager, layout: LayoutConstants):
        super().__init__(scene_manager)
        self.asset_manager = asset_manager
        self.layout = layout
        # --- END OF CHANGE ---

        self.theme = scene_manager.theme
        self.font_header = pygame.font.Font(self.theme["font"]["main"], self.theme["font"]["header_size"])
        
        # --- START OF CHANGE: Use dynamic layout constants ---
        center_x = self.layout.SCREEN_WIDTH // 2
        
        # Volume Control
        self.volume_label = self.font_header.render("Music Volume", True, self.theme["colors"]["text_light"])
        self.volume_slider = Slider(
            pygame.Rect(center_x - 100, int(self.layout.SCREEN_HEIGHT * 0.25), 200, 20), self.theme, 0.0, 1.0,
            pygame.mixer.music.get_volume(),
            self.scene_manager.sounds.set_music_volume
        )
        
        # Theme Selection
        self.theme_label = self.font_header.render("UI Theme", True, self.theme["colors"]["text_light"])
        self.theme_buttons = [
            Button("Light", pygame.Rect(center_x - 110, int(self.layout.SCREEN_HEIGHT * 0.4), 100, 40), self.theme, lambda: self.on_theme_change("Light")),
            Button("Dark", pygame.Rect(center_x + 10, int(self.layout.SCREEN_HEIGHT * 0.4), 100, 40), self.theme, lambda: self.on_theme_change("Dark"))
        ]

        # Resolution Selection
        self.resolution_label = self.font_header.render("Resolution", True, self.theme["colors"]["text_light"])
        self.resolution_buttons = []

        try:
            info = pygame.display.Info()
            native_resolution = (info.current_w, info.current_h)
        except pygame.error:
            native_resolution = (1920, 1080)

        # Create a list of desirable resolutions
        possible_resolutions = {
            "Fullscreen": (native_resolution[0], native_resolution[1], True),
            "1920x1080": (1920, 1080, False),
            "1600x900": (1600, 900, False),
            "1280x720": (1280, 720, False)
        }
        
        # Correctly filter the list to show all valid options
        valid_resolutions = {
            text: data for text, data in possible_resolutions.items()
            if data[0] <= native_resolution[0] and data[1] <= native_resolution[1]
        }
        
        # Ensure native resolution is always an option if not already present as fullscreen
        native_text = f"{native_resolution[0]}x{native_resolution[1]}"
        if native_text not in valid_resolutions and "Fullscreen" not in valid_resolutions:
             valid_resolutions[native_text] = (native_resolution[0], native_resolution[1], False)

        btn_width = 220
        start_x = center_x - ((len(valid_resolutions) * (btn_width + 10)) - 10) // 2
        
        for i, (text, data) in enumerate(valid_resolutions.items()):
            rect = pygame.Rect(start_x + i * (btn_width + 10), int(self.layout.SCREEN_HEIGHT * 0.55), btn_width, 40)
            self.resolution_buttons.append(Button(text, rect, self.theme, lambda r=data: self.on_resolution_change(r)))
        
        # Back Button
        back_button_y = self.layout.SCREEN_HEIGHT - int(self.layout.SCREEN_HEIGHT * 0.2)
        self.back_button = Button("Back to Menu", pygame.Rect(center_x - 150, back_button_y, 300, 60), self.theme, lambda: self.scene_manager.go_to_scene("MAIN_MENU"))

    def on_resolution_change(self, new_resolution_data: Tuple[int, int, bool]):
        """Tells the app to change the resolution, now with fullscreen support."""
        size = (new_resolution_data[0], new_resolution_data[1])
        is_fullscreen = new_resolution_data[2]
        print(f"Requesting resolution change to {size} (Fullscreen: {is_fullscreen})...")
        self.scene_manager.change_resolution(size, is_fullscreen)

    def on_theme_change(self, theme_name):
        self.scene_manager.load_theme(f"ui_theme_{theme_name.lower()}.json")
        # The App class will correctly pass the layout object again
        self.scene_manager.scenes["SETTINGS"] = SettingsScene(self.scene_manager, self.asset_manager, self.layout)
        self.scene_manager.current_scene = self.scene_manager.scenes["SETTINGS"]

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.scene_manager.go_to_scene("MAIN_MENU")
            self.volume_slider.handle_event(event)
            for button in self.theme_buttons:
                button.handle_event(event)
            for button in self.resolution_buttons: 
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
        # Draw Resolution screen
        screen.blit(self.resolution_label, self.resolution_label.get_rect(center=(screen.get_width() // 2, int(self.layout.SCREEN_HEIGHT * 0.5))))
        for button in self.resolution_buttons:
            button.draw(screen)
        # Draw back button
        self.back_button.draw(screen)