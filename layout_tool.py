import pygame
import json
import sys
import os
from tkinter import filedialog, Tk

# --- Configuration ---
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
OUTPUT_FILE = 'ui_layout.json'

# --- Colors and Fonts ---
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_RECT = (255, 165, 0, 150) # Orange, semi-transparent
COLOR_RECT_BORDER = (255, 255, 0) # Yellow
FONT_SIZE = 18

class LayoutTool:
    """
    A visual tool to define UI element rectangles over a mockup image
    and export them to a JSON file for data-driven layout in the game.
    """
    def __init__(self):
        pygame.init()
        self.tk_root = Tk()
        self.tk_root.withdraw()

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Visual UI Layout Helper (Press 'M' to load mockup, 'E' to export)")
        self.font = pygame.font.Font(None, FONT_SIZE)
        self.clock = pygame.time.Clock()

        self.background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.background.fill(COLOR_BLACK)

        self.rects = {}
        self.current_rect_start = None
        self.is_drawing = False
        
        print("\n--- Visual UI Layout Tool Initialized ---")
        print("Press 'M' to select your mockup image.")
        print("Press 'L' to load an existing layout file to edit.")

    def load_mockup(self):
        """Opens a file dialog for the user to select the mockup background image."""
        filepath = filedialog.askopenfilename(
            title="Select Mockup Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")]
        )
        if not filepath:
            print("No mockup file selected.")
            return

        try:
            self.background = pygame.image.load(filepath).convert()
            self.background = pygame.transform.scale(self.background, (SCREEN_WIDTH, SCREEN_HEIGHT))
            print(f"Loaded mockup: {filepath}")
        except Exception as e:
            print(f"Error loading image '{filepath}': {e}")
            self.background.fill(COLOR_BLACK)

    def load_existing_layout(self):
        """Loads a previously saved layout JSON file for further editing."""
        filepath = filedialog.askopenfilename(
            title="Load Layout File",
            filetypes=[("JSON files", "*.json")],
            initialfile=OUTPUT_FILE
        )
        if not filepath:
            print("No layout file selected.")
            return
        
        try:
            with open(filepath, 'r') as f:
                loaded_data = json.load(f)
            
            self.rects.clear()
            for name, rect_data in loaded_data.items():
                self.rects[name] = pygame.Rect(rect_data)
            print(f"Successfully loaded {len(self.rects)} rectangles from {filepath}")
        except Exception as e:
             print(f"Error loading layout file '{filepath}': {e}")


    def handle_input_box(self, prompt):
        """Creates a temporary loop to handle text input directly in the Pygame window."""
        input_text = ""
        active = True
        while active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        active = False
                    elif event.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                    else:
                        input_text += event.unicode

            self.draw()
            box_rect = pygame.Rect(SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 50, 400, 100)
            pygame.draw.rect(self.screen, (30, 30, 70), box_rect)
            pygame.draw.rect(self.screen, COLOR_WHITE, box_rect, 2)
            prompt_surf = self.font.render(prompt, True, COLOR_WHITE)
            self.screen.blit(prompt_surf, (box_rect.x + 10, box_rect.y + 10))
            input_surf = self.font.render(input_text, True, COLOR_WHITE)
            self.screen.blit(input_surf, (box_rect.x + 10, box_rect.y + 40))
            pygame.display.flip()
        return input_text

    def export_layout(self):
        """Saves the current dictionary of named rectangles to the output JSON file."""
        export_data = {name: [rect.x, rect.y, rect.width, rect.height] for name, rect in self.rects.items()}
        
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(export_data, f, indent=4)
        
        print(f"\n--- Layout successfully exported to '{OUTPUT_FILE}'! ---")
        print("You can now close this tool or continue editing.")


    def run(self):
        """The main loop for the application."""
        running = True
        while running:
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_m: self.load_mockup()
                    if event.key == pygame.K_l: self.load_existing_layout()
                    if event.key == pygame.K_e: self.export_layout()
                    if event.key == pygame.K_z and pygame.key.get_mods() & pygame.KMOD_CTRL:
                        if self.rects:
                            last_key = list(self.rects.keys())[-1]
                            del self.rects[last_key]
                            print(f"Removed last rectangle: '{last_key}'")

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.current_rect_start = mouse_pos
                    self.is_drawing = True

                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if self.is_drawing and self.current_rect_start:
                        x1, y1 = self.current_rect_start
                        x2, y2 = mouse_pos
                        new_rect = pygame.Rect(min(x1, x2), min(y1, y2), abs(x1 - x2), abs(y1 - y2))
                        
                        if new_rect.width > 5 and new_rect.height > 5:
                            rect_name = self.handle_input_box("Enter a unique name for this rectangle:")
                            if rect_name:
                                if rect_name in self.rects:
                                    print(f"Warning: Name '{rect_name}' already exists. Overwriting.")
                                self.rects[rect_name] = new_rect
                                print(f"Added/Updated rectangle: '{rect_name}'")
                    self.is_drawing = False
                    self.current_rect_start = None

            self.draw()
            if self.is_drawing and self.current_rect_start:
                x1, y1 = self.current_rect_start
                x2, y2 = mouse_pos
                current_drawn_rect = pygame.Rect(min(x1, x2), min(y1, y2), abs(x1 - x2), abs(y1 - y2))
                s = pygame.Surface(current_drawn_rect.size, pygame.SRCALPHA)
                s.fill(COLOR_RECT)
                self.screen.blit(s, current_drawn_rect.topleft)
                pygame.draw.rect(self.screen, COLOR_RECT_BORDER, current_drawn_rect, 2)

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

    def draw(self):
        """Handles all drawing for the tool."""
        self.screen.blit(self.background, (0, 0))
        
        for name, rect in self.rects.items():
            s = pygame.Surface(rect.size, pygame.SRCALPHA)
            s.fill(COLOR_RECT)
            self.screen.blit(s, rect.topleft)
            pygame.draw.rect(self.screen, COLOR_RECT_BORDER, rect, 2)
            text_surf = self.font.render(f"{name}: {rect.w}x{rect.h}", True, COLOR_BLACK, COLOR_WHITE)
            self.screen.blit(text_surf, (rect.x + 5, rect.y + 5))

        instructions = [
            "INSTRUCTIONS:",
            " - Click and drag to draw a rectangle.",
            " - Press 'M' to load a mockup image.",
            " - Press 'L' to load an existing layout.json to edit.",
            " - Press 'E' to export the layout to ui_layout.json.",
            " - Press 'Ctrl+Z' to undo the last added rectangle."
        ]
        for i, line in enumerate(instructions):
            inst_surf = self.font.render(line, True, COLOR_WHITE)
            bg_rect = inst_surf.get_rect(topleft=(10, 10 + i * (FONT_SIZE + 2))).inflate(4, 4)
            
            # --- THIS IS THE FIX ---
            # Create a dedicated surface for the semi-transparent background
            bg_surface = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
            bg_surface.fill((0, 0, 0, 128))  # Fill with semi-transparent black
            self.screen.blit(bg_surface, bg_rect.topleft) # Blit this surface
            # --- END OF FIX ---

            # Draw the text on top of the transparent background
            self.screen.blit(inst_surf, (12, 12 + i * (FONT_SIZE + 2)))

if __name__ == '__main__':
    tool = LayoutTool()
    tool.run()