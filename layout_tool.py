import pygame
import json
import sys
import math
from tkinter import filedialog, Tk

# --- Configuration ---
OUTPUT_FILE = 'ui_layout.json'
POLYGON_CLOSE_TOLERANCE = 15

# --- Colors and Fonts ---
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_RECT_FILL = (255, 165, 0, 150)
COLOR_RECT_BORDER = (255, 255, 0)
COLOR_SELECTED_BORDER = (255, 0, 255, 255)
COLOR_POLYGON_VERTEX = (0, 255, 0)
COLOR_POLYGON_LINE = (0, 200, 0)
COLOR_SNAP_CIRCLE = (0, 255, 255, 100)
FONT_SIZE = 22

class LayoutTool:
    def __init__(self):
        pygame.init()
        self.tk_root = Tk(); self.tk_root.withdraw()
        
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.screen_width, self.screen_height = self.screen.get_size()
        self.screen_rect = self.screen.get_rect() # Store screen rect for clamping
        
        pygame.display.set_caption("Linie 1 - Advanced UI Layout Tool")
        self.font = pygame.font.Font(None, FONT_SIZE)
        self.clock = pygame.time.Clock()
        self.background = pygame.Surface((self.screen_width, self.screen_height)); self.background.fill(COLOR_BLACK)
        
        self.layout_data = {"children": {}}
        self.selected_name = None
        self.mode = "select"; self.start_pos = None; self.current_polygon_points = []; self.history = []

    def load_mockup(self):
        filepath = filedialog.askopenfilename(title="Select Mockup Image")
        if filepath:
            try:
                self.background = pygame.image.load(filepath).convert()
                self.background = pygame.transform.scale(self.background, (self.screen_width, self.screen_height))
            except Exception as e: print(f"Error loading image: {e}")

    def export_layout(self):
        with open(OUTPUT_FILE, 'w') as f: json.dump(self.layout_data, f, indent=4)
        print(f"--- Layout exported to '{OUTPUT_FILE}' ---")

    def add_component(self, component_name, component_data):
        if component_name in self.layout_data['children']:
            print(f"Warning: Component name '{component_name}' already exists. Overwriting.")
        self.layout_data['children'][component_name] = component_data
        self.history.append(component_name)
        print(f"Added/Updated component: '{component_name}'")

    def undo_last_action(self):
        if not self.history: return
        last_name = self.history.pop()
        if last_name in self.layout_data['children']:
            del self.layout_data['children'][last_name]; print(f"Undone adding '{last_name}'")

    def handle_simple_input(self, prompt, default_text=""):
        input_text = default_text
        active = True
        
        # IMPROVEMENT: Key repeat for backspace
        backspace_timer = 0
        backspace_initial_delay = 500 # ms
        backspace_repeat_delay = 50 # ms

        while active:
            dt = self.clock.tick(60) # Get delta time for timers

            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN: active = False
                    elif event.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                        backspace_timer = -backspace_initial_delay # Start initial delay timer
                    else:
                        input_text += event.unicode
            
            # Handle backspace key repeat
            keys = pygame.key.get_pressed()
            if keys[pygame.K_BACKSPACE]:
                backspace_timer += dt
                if backspace_timer > backspace_repeat_delay:
                    input_text = input_text[:-1]
                    backspace_timer = 0 # Reset repeat timer
            
            self.draw() # Keep rendering the background scene
            box_rect = pygame.Rect(self.screen_width//2-250, self.screen_height//2-50, 500, 100)
            pygame.draw.rect(self.screen, (30,30,70), box_rect); pygame.draw.rect(self.screen, COLOR_WHITE, box_rect, 2)
            self.screen.blit(self.font.render(prompt, True, COLOR_WHITE), (box_rect.x+10, box_rect.y+10))
            self.screen.blit(self.font.render(input_text, True, COLOR_WHITE), (box_rect.x+10, box_rect.y+40))
            pygame.display.flip()
        return input_text

    def finalize_and_add_shape(self, shape_type, shape_data):
        comp_name = self.handle_simple_input(f"Enter unique name for new {shape_type}:")
        if not comp_name: print("Cancelled adding shape: No name provided."); return
        comp_type = self.handle_simple_input(f"Enter component type for '{comp_name}':", "Panel")
        if not comp_type: comp_type = "Panel"
        
        if shape_type == "polygon": shape_data = list(shape_data)

        self.add_component(comp_name, {
            "type": comp_type, "hierarchy": 10, # IMPROVEMENT: Default hierarchy is now 10
            "shape_type": shape_type, "shape_data": shape_data
        })

    def get_component_at_pos(self, pos):
        colliding = []
        for name, comp in self.layout_data['children'].items():
            if self.is_point_in_component(pos, comp):
                colliding.append((comp.get('hierarchy', 1), name))
        if not colliding: return None
        colliding.sort(key=lambda x: x[0], reverse=True)
        return colliding[0][1]

    def is_point_in_component(self, point, component):
        st = component['shape_type']; sd = component.get('shape_data', [])
        if not sd: return False
        if st == 'rectangle': return pygame.Rect(sd).collidepoint(point)
        if st == 'circle': return math.hypot(point[0]-sd[0], point[1]-sd[1]) <= sd[2]
        if st == 'polygon':
            x, y = point; n = len(sd); inside = False
            p1x, p1y = sd[0]
            for i in range(n + 1):
                p2x, p2y = sd[i % n]
                if y > min(p1y, p2y):
                    if y <= max(p1y, p2y):
                        if x <= max(p1x, p2x):
                            if p1y != p2y:
                                xinters = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                            if p1x == p2x or x <= xinters:
                                inside = not inside
                p1x, p1y = p2x, p2y
            return inside
        return False

    def draw_component(self, name, component):
        st = component['shape_type']; sd = component.get('shape_data', []); info_text = f"{name} ({component.get('type','?')}) H:{component.get('hierarchy',1)}"
        border_color = COLOR_SELECTED_BORDER if name == self.selected_name else COLOR_RECT_BORDER
        try:
            if not sd: return
            if st == "rectangle":
                rect = pygame.Rect(sd)
                s = pygame.Surface(rect.size, pygame.SRCALPHA); s.fill(COLOR_RECT_FILL); self.screen.blit(s, rect.topleft)
                pygame.draw.rect(self.screen, border_color, rect, 2)
                self.screen.blit(self.font.render(info_text, True, COLOR_BLACK, COLOR_WHITE), (rect.x + 5, rect.y + 5))
            elif st == "circle":
                center, r = (sd[0], sd[1]), sd[2]
                s = pygame.Surface((r*2, r*2), pygame.SRCALPHA); pygame.draw.circle(s, COLOR_RECT_FILL, (r,r), r); self.screen.blit(s, (center[0]-r, center[1]-r))
                pygame.draw.circle(self.screen, border_color, center, r, 2)
                self.screen.blit(self.font.render(info_text, True, COLOR_BLACK, COLOR_WHITE), (center[0]-r+5, center[1]-r+5))
            elif st == "polygon":
                min_x=min(p[0] for p in sd); max_x=max(p[0] for p in sd); min_y=min(p[1] for p in sd); max_y=max(p[1] for p in sd)
                bounds_rect = pygame.Rect(min_x, min_y, max_x-min_x, max_y-min_y)
                s = pygame.Surface(bounds_rect.size, pygame.SRCALPHA)
                relative_points = [(p[0]-bounds_rect.x, p[1]-bounds_rect.y) for p in sd]
                pygame.draw.polygon(s, COLOR_RECT_FILL, relative_points); self.screen.blit(s, bounds_rect.topleft)
                pygame.draw.polygon(self.screen, border_color, sd, 2)
                self.screen.blit(self.font.render(info_text, True, COLOR_BLACK, COLOR_WHITE), (sd[0][0]+5, sd[0][1]+5))
        except (ValueError, IndexError) as e: print(f"Error drawing '{name}': {e}. Shape data: {sd}")
    
    def draw(self):
        self.screen.blit(self.background, (0, 0))
        sorted_children = sorted(self.layout_data['children'].items(), key=lambda item: item[1].get('hierarchy', 1))
        for name, component in sorted_children: self.draw_component(name, component)
        help_text = [f"MODE: {self.mode.upper()} | SELECTED: {self.selected_name}", "[R]ect | [C]ircle | [G]eometry | [ESC] Select Mode", "Right-click selected to set Hierarchy | [M]ockup | [E]xport | [Ctrl+Z] Undo"]
        if self.mode == 'draw_polygon': help_text.append("Left-click to add point | Click near start OR Right-click to finish")
        for i, line in enumerate(help_text):
            surf = self.font.render(line, True, COLOR_WHITE)
            bg_rect = surf.get_rect(topleft=(10, 10+i*(FONT_SIZE+4))).inflate(8,8)
            s = pygame.Surface(bg_rect.size, pygame.SRCALPHA); s.fill((0,0,0,180)); self.screen.blit(s, bg_rect.topleft)
            self.screen.blit(surf, (14, 14+i*(FONT_SIZE+4)))

    def run(self):
        while True:
            mouse_pos = pygame.mouse.get_pos()
            clamped_mouse_pos = (max(0, min(self.screen_width-1, mouse_pos[0])), max(0, min(self.screen_height-1, mouse_pos[1])))

            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F4 and (pygame.key.get_mods() & pygame.KMOD_ALT): pygame.quit(); sys.exit()
                
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE: self.mode = "select"; self.current_polygon_points.clear()
                    elif event.key == pygame.K_r: self.mode = "draw_rectangle"
                    elif event.key == pygame.K_c: self.mode = "draw_circle"
                    elif event.key == pygame.K_g: self.mode = "draw_polygon"; self.current_polygon_points.clear()
                    elif event.key == pygame.K_m: self.load_mockup()
                    elif event.key == pygame.K_e: self.export_layout()
                    elif event.key == pygame.K_z and (pygame.key.get_mods() & pygame.KMOD_CTRL): self.undo_last_action()
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.mode == "select":
                        if event.button == 1: self.selected_name = self.get_component_at_pos(clamped_mouse_pos)
                        elif event.button == 3 and self.selected_name:
                            new_h = self.handle_simple_input(f"Set hierarchy for '{self.selected_name}' (higher is on top):")
                            try: self.layout_data['children'][self.selected_name]['hierarchy'] = int(new_h)
                            except (ValueError, KeyError): print("Invalid hierarchy value.")
                    
                    elif self.mode in ["draw_rectangle", "draw_circle"]: self.start_pos = clamped_mouse_pos
                    elif self.mode == "draw_polygon":
                        close_shape = event.button==1 and len(self.current_polygon_points)>=3 and math.hypot(clamped_mouse_pos[0]-self.current_polygon_points[0][0], clamped_mouse_pos[1]-self.current_polygon_points[0][1]) < POLYGON_CLOSE_TOLERANCE
                        if close_shape or (event.button==3 and len(self.current_polygon_points)>=3):
                            self.finalize_and_add_shape("polygon", self.current_polygon_points)
                            self.current_polygon_points.clear(); self.mode = "select"
                        elif event.button == 1: self.current_polygon_points.append(clamped_mouse_pos)

                if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.start_pos:
                    if self.mode == "draw_rectangle":
                        final_rect = pygame.Rect(min(self.start_pos[0],clamped_mouse_pos[0]), min(self.start_pos[1],clamped_mouse_pos[1]), abs(self.start_pos[0]-clamped_mouse_pos[0]), abs(self.start_pos[1]-clamped_mouse_pos[1]))
                        final_rect.clamp_ip(self.screen_rect) # IMPROVEMENT: Clamp rectangle to screen
                        if final_rect.width>5 and final_rect.height>5: self.finalize_and_add_shape("rectangle", [final_rect.x, final_rect.y, final_rect.width, final_rect.height])
                    elif self.mode == "draw_circle":
                        center_x, center_y = self.start_pos
                        radius = int(math.hypot(clamped_mouse_pos[0]-center_x, clamped_mouse_pos[1]-center_y))
                        # IMPROVEMENT: Clamp circle to screen
                        max_radius = min(center_x, self.screen_width - center_x, center_y, self.screen_height - center_y)
                        final_radius = min(radius, max_radius)
                        if final_radius > 5: self.finalize_and_add_shape("circle", [center_x, center_y, final_radius])
                    self.start_pos = None; self.mode = "select"
            
            self.draw()
            if self.start_pos: # Draw live previews
                if self.mode=="draw_rectangle": pygame.draw.rect(self.screen, COLOR_RECT_BORDER, (min(self.start_pos[0],clamped_mouse_pos[0]), min(self.start_pos[1],clamped_mouse_pos[1]), abs(self.start_pos[0]-clamped_mouse_pos[0]), abs(self.start_pos[1]-clamped_mouse_pos[1])), 2)
                elif self.mode=="draw_circle": pygame.draw.circle(self.screen, COLOR_RECT_BORDER, self.start_pos, int(math.hypot(clamped_mouse_pos[0]-self.start_pos[0], clamped_mouse_pos[1]-self.start_pos[1])), 2)
            if self.mode == "draw_polygon" and self.current_polygon_points:
                pygame.draw.lines(self.screen, COLOR_POLYGON_LINE, False, self.current_polygon_points + [clamped_mouse_pos], 2)
                for p in self.current_polygon_points: pygame.draw.circle(self.screen, COLOR_POLYGON_VERTEX, p, 4)
                if len(self.current_polygon_points) >= 2 and math.hypot(clamped_mouse_pos[0]-self.current_polygon_points[0][0], clamped_mouse_pos[1]-self.current_polygon_points[0][1]) < POLYGON_CLOSE_TOLERANCE:
                    s = pygame.Surface((POLYGON_CLOSE_TOLERANCE*2, POLYGON_CLOSE_TOLERANCE*2), pygame.SRCALPHA); pygame.draw.circle(s, COLOR_SNAP_CIRCLE, (POLYGON_CLOSE_TOLERANCE, POLYGON_CLOSE_TOLERANCE), POLYGON_CLOSE_TOLERANCE); self.screen.blit(s, (self.current_polygon_points[0][0]-POLYGON_CLOSE_TOLERANCE, self.current_polygon_points[0][1]-POLYGON_CLOSE_TOLERANCE))
            
            pygame.display.flip()

if __name__ == '__main__':
    tool = LayoutTool()
    tool.run()