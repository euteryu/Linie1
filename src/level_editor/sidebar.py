# src/level_editor/sidebar.py
import pygame
from typing import List, Dict, Any, Optional, Tuple

from common import constants as C
from common.rendering_utils import create_tile_surface, get_font, draw_text

SIDEBAR_WIDTH = 250
ITEM_SIZE = 60
PADDING = 10
ACTION_BUTTON_HEIGHT = 40
HEADER_HEIGHT = 30
SCROLLBAR_WIDTH = 15

class Sidebar:
    def __init__(self, screen_height: int, screen_width: int):
        self.width = SIDEBAR_WIDTH
        self.height = screen_height
        self.rect = pygame.Rect(screen_width - self.width, 0, self.width, self.height)
        
        # UI Elements
        self.ui_elements: List[Dict[str, Any]] = []
        self.ui_rects: Dict[str, pygame.Rect] = {}
        self.selected_stamp_name: Optional[str] = None
        
        # Scroll State
        self.scroll_offset = 0
        self.content_height = 0
        self.is_dragging_scrollbar = False
        self.scrollbar_rect = pygame.Rect(self.rect.right - SCROLLBAR_WIDTH - 2, 2, SCROLLBAR_WIDTH, self.height - 4)
        self.scrollbar_thumb_rect = pygame.Rect(self.scrollbar_rect.x, 0, SCROLLBAR_WIDTH, 0)

        self._create_ui_elements()
        self._calculate_rects()

    def _create_ui_elements(self):
        """Creates a structured list of all UI elements, ensuring each has a unique name."""
        self.ui_elements = []
        self.ui_elements.append({'type': 'header', 'text': 'File Operations', 'name': 'header_file'})
        for name in ["Save", "Load", "Export"]: 
            self.ui_elements.append({'type': 'action', 'name': name})

        self.ui_elements.append({'type': 'header', 'text': 'Tools', 'name': 'header_tools'})
        self.ui_elements.append({'type': 'action', 'name': 'Search'}) # New Search button
        self.ui_elements.append({'type': 'eraser', 'name': 'Eraser'})

        self.ui_elements.append({'type': 'header', 'text': 'Terminals (Pairs)', 'name': 'header_terminals'})
        for i in range(1, 7): 
            self.ui_elements.append({'type': 'terminal_pair', 'line_number': i, 'name': f"Terminal Pair {i}"})
        self.ui_elements.append({'type': 'header', 'text': 'Buildings', 'name': 'header_buildings'})
        for building_id in sorted(C.BUILDING_COORDS.keys()): 
            self.ui_elements.append({'type': 'building', 'name': building_id})
        self.ui_elements.append({'type': 'header', 'text': 'Track Tiles', 'name': 'header_tracks'})
        for name, details in C.TILE_DEFINITIONS.items(): 
            self.ui_elements.append({'type': 'tile', 'name': name, 'details': details})
        self.selected_stamp_name = 'Eraser'

    def _calculate_rects(self):
        """Calculates the absolute position and size for each UI element with a grid layout."""
        self.ui_rects.clear()
        x, y = PADDING, PADDING
        row_width = self.width - (2 * PADDING) - SCROLLBAR_WIDTH
        
        for element in self.ui_elements:
            name, elem_type = element['name'], element['type']
            
            # Full-width items reset the x-coordinate and move to the next line
            if elem_type in ['header', 'action', 'terminal_pair']:
                if x != PADDING:  # If we are in the middle of a grid row, break to a new line
                    y += ITEM_SIZE + PADDING
                x = PADDING
                
                height = HEADER_HEIGHT if elem_type == 'header' else ACTION_BUTTON_HEIGHT if elem_type == 'action' else ITEM_SIZE
                self.ui_rects[name] = pygame.Rect(x, y, row_width, height)
                y += height + PADDING
            
            # Grid items (buildings, tiles, eraser) are placed horizontally
            else:
                if x + ITEM_SIZE > row_width:
                    x = PADDING
                    y += ITEM_SIZE + PADDING
                self.ui_rects[name] = pygame.Rect(x, y, ITEM_SIZE, ITEM_SIZE)
                x += ITEM_SIZE + PADDING
        
        # After the loop, if we were in the middle of a grid row, add the final row's height
        if x != PADDING:
            y += ITEM_SIZE + PADDING

        self.content_height = y

    def get_selected_stamp(self) -> Optional[Dict[str, Any]]:
        if not self.selected_stamp_name: return None
        return next((elem for elem in self.ui_elements if elem['name'] == self.selected_stamp_name), None)

    def handle_event(self, event: pygame.event.Event):
        """Handles all events for the sidebar, including clicks, scroll wheel, and scrollbar dragging."""
        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self.scroll_offset -= event.y * 30
                self._clamp_scroll()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.scrollbar_thumb_rect.collidepoint(event.pos):
                self.is_dragging_scrollbar = True
                return # Don't process other clicks
            
            click_result = self._handle_click(event.pos)
            return click_result # This will be 'Save', 'Load', 'stamp', etc.

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.is_dragging_scrollbar = False

        elif event.type == pygame.MOUSEMOTION and self.is_dragging_scrollbar:
            mouse_y = event.pos[1]
            scroll_ratio = (mouse_y - self.scrollbar_rect.top) / self.scrollbar_rect.height
            self.scroll_offset = scroll_ratio * (self.content_height - self.height)
            self._clamp_scroll()
            
    def _handle_click(self, mouse_pos: Tuple[int, int]) -> Optional[str]:
        if not self.rect.collidepoint(mouse_pos): return None
        
        for name, rect in self.ui_rects.items():
            hittest_rect = pygame.Rect(self.rect.left + rect.x, self.rect.top + rect.y - self.scroll_offset, rect.width, rect.height)
            if hittest_rect.collidepoint(mouse_pos):
                element = next(elem for elem in self.ui_elements if elem['name'] == name)
                if element['type'] in ['eraser', 'terminal_pair', 'building', 'tile']:
                    self.selected_stamp_name = name; return "stamp"
                elif element['type'] == 'action':
                    return name
        return None
        

    def _clamp_scroll(self):
        """Ensures the scroll offset doesn't go out of bounds."""
        self.scroll_offset = max(0, self.scroll_offset)
        max_scroll = self.content_height - self.height
        if max_scroll > 0:
            self.scroll_offset = min(self.scroll_offset, max_scroll)
        else:
            self.scroll_offset = 0

    def draw(self, screen: pygame.Surface):
        pygame.draw.rect(screen, (40, 40, 60), self.rect)
        
        # --- Draw all UI elements, scrolled ---
        for element in self.ui_elements:
            name, elem_type = element['name'], element['type']
            abs_rect = self.ui_rects[name]
            pos_x = self.rect.left + abs_rect.x
            pos_y = self.rect.top + abs_rect.y - self.scroll_offset
            
            if pos_y > self.height or pos_y + abs_rect.height < 0: continue
            
            rect = pygame.Rect(pos_x, pos_y, abs_rect.width, abs_rect.height)

            if elem_type == 'header':
                draw_text(screen, element['text'], rect.left + 5, rect.centery, (180, 180, 200), 20, False, True)
            elif elem_type == 'action':
                color = (100, 100, 130) if rect.collidepoint(pygame.mouse.get_pos()) else (80, 80, 100)
                pygame.draw.rect(screen, color, rect, border_radius=8)
                draw_text(screen, name, rect.centerx, rect.centery, C.COLOR_WHITE, 22, True, True)
                pygame.draw.rect(screen, (120, 120, 150), rect, 2, border_radius=8)
            else: # It's a stamp
                self._draw_stamp(screen, element, rect)
                if self.selected_stamp_name == name:
                    pygame.draw.rect(screen, C.COLOR_HIGHLIGHT, rect, 3)
                else:
                    pygame.draw.rect(screen, (80, 80, 100), rect, 1)

        # --- Draw the scrollbar ---
        if self.content_height > self.height:
            # Track
            pygame.draw.rect(screen, (30, 30, 40), self.scrollbar_rect)
            # Thumb
            thumb_height = (self.height / self.content_height) * self.scrollbar_rect.height
            thumb_y_ratio = self.scroll_offset / (self.content_height - self.height)
            thumb_y = self.scrollbar_rect.top + thumb_y_ratio * (self.scrollbar_rect.height - thumb_height)
            self.scrollbar_thumb_rect = pygame.Rect(self.scrollbar_rect.x, thumb_y, SCROLLBAR_WIDTH, thumb_height)
            pygame.draw.rect(screen, (100, 100, 120), self.scrollbar_thumb_rect, border_radius=4)

    def _draw_stamp(self, screen, element, rect):
        """Helper to draw a single stamp element."""
        elem_type, name = element['type'], element['name']

        if elem_type == 'terminal_pair':
            pygame.draw.rect(screen, (30,30,50), rect) # Use a darker background for the pair
            
            # --- START OF CHANGE: Draw the visual representation correctly ---
            base_curve = create_tile_surface(type('TileType', (object,), {'name': 'Curve', **C.TILE_DEFINITIONS['Curve']}), rect.height)
            curve_left = pygame.transform.rotate(base_curve, -90)
            curve_right = pygame.transform.rotate(base_curve, -180)

            # Create white backgrounds for the individual curves
            left_bg_rect = pygame.Rect(rect.left, rect.top, rect.height, rect.height)
            right_bg_rect = pygame.Rect(rect.left + rect.height + 5, rect.top, rect.height, rect.height)
            pygame.draw.rect(screen, C.COLOR_WHITE, left_bg_rect)
            pygame.draw.rect(screen, C.COLOR_WHITE, right_bg_rect)
            
            screen.blit(curve_left, left_bg_rect.topleft)
            screen.blit(curve_right, right_bg_rect.topleft)
            
            # Draw a single, centered label over the whole thing
            font = get_font(int(rect.height * 0.4))
            text_surf = font.render(f"T-{element['line_number']}", True, C.COLOR_WHITE, (0,0,0,150))
            screen.blit(text_surf, text_surf.get_rect(center=rect.center))
            # --- END OF CHANGE ---

        else: # Eraser, Building, Tile
            size = rect.width
            surf = pygame.Surface((size, size))
            if elem_type == 'eraser':
                surf.fill((255, 100, 100))
                draw_text(surf, "ERASE", size//2, size//2, C.COLOR_WHITE, 20, True, True)
            elif elem_type == 'building':
                font = get_font(int(size * 0.7))
                surf.fill(C.COLOR_BUILDING_BG)
                text_surf = font.render(name, True, C.COLOR_BUILDING_FG)
                surf.blit(text_surf, text_surf.get_rect(center=(size//2, size//2)))
            elif elem_type == 'tile':
                dummy_type = type('TileType', (object,), {'name': name, **element['details']})
                surf_tile = create_tile_surface(dummy_type, size)
                surf.fill(C.COLOR_WHITE)
                surf.blit(surf_tile, (0,0))
            screen.blit(surf, rect.topleft)