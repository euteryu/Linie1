# ui/components.py
import pygame

class Button:
    def __init__(self, text, rect, theme, callback):
        self.rect = rect
        self.text = text
        self.theme = theme
        self.callback = callback
        
        self.font = pygame.font.Font(self.theme["font"]["main"], self.theme["font"]["body_size"])
        self.is_hovered = False
        self.is_pressed = False
        
        self.base_color = self.theme["colors"]["accent"]
        self.hover_color = self.theme["colors"]["accent_hover"]
        self.text_color = self.theme["colors"]["text_dark"]

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_hovered:
            self.is_pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.is_pressed:
            self.is_pressed = False
            if self.is_hovered:
                # --- START OF CHANGE: The button now simply calls the callback. ---
                # It is no longer responsible for passing any arguments. The lambda
                # function that created the callback will provide the correct data.
                self.callback()
                # --- END OF CHANGE ---

    def draw(self, screen):
        color = self.hover_color if self.is_hovered else self.base_color
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

class Slider:
    def __init__(self, rect, theme, min_val, max_val, current_val, callback):
        self.rect = rect
        self.theme = theme
        self.min_val = min_val
        self.max_val = max_val
        self.current_val = current_val
        self.callback = callback
        
        self.knob_radius = rect.height // 2
        self.is_grabbed = False
        self.font = pygame.font.Font(theme["font"]["main"], theme["font"]["small_size"])

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.is_grabbed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.is_grabbed = False
        elif event.type == pygame.MOUSEMOTION and self.is_grabbed:
            # Update value based on mouse position
            mouse_x = event.pos[0]
            # Clamp mouse position to the slider's track
            x = max(self.rect.left, min(mouse_x, self.rect.right))
            # Convert position to a value in our range
            self.current_val = self.min_val + (self.max_val - self.min_val) * ((x - self.rect.left) / self.rect.width)
            self.callback(self.current_val)

    def draw(self, screen):
        # Draw the slider track
        track_rect = self.rect.inflate(0, -self.rect.height * 0.6)
        pygame.draw.rect(screen, self.theme["colors"]["background"], track_rect, border_radius=5)
        
        # Draw the knob
        knob_x_ratio = (self.current_val - self.min_val) / (self.max_val - self.min_val)
        knob_x = self.rect.left + self.rect.width * knob_x_ratio
        pygame.draw.circle(screen, self.theme["colors"]["accent_hover"], (knob_x, self.rect.centery), self.knob_radius)
        
        # Draw the value text
        value_text = f"{int(self.current_val * 100)}%"
        text_surf = self.font.render(value_text, True, self.theme["colors"]["text_muted"])
        screen.blit(text_surf, (self.rect.right + 10, self.rect.centery - text_surf.get_height() // 2))