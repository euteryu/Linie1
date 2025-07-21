# src/level_editor/sidebar.py
import pygame
from typing import List, Dict, Any, Optional, Tuple
from tkinter import messagebox

# Correct, fully qualified imports as requested
from common import constants as C
from common.rendering_utils import create_tile_surface, get_font, draw_text
from common.sound_manager import SoundManager

SIDEBAR_WIDTH = 250
ITEM_SIZE = 60
PADDING = 10
ACTION_BUTTON_HEIGHT = 40
HEADER_HEIGHT = 30
SCROLLBAR_WIDTH = 15
SEARCH_BAR_HEIGHT = 40

class Sidebar:
    def __init__(self, screen_height: int, screen_width: int):
        self.width = SIDEBAR_WIDTH
        self.height = screen_height
        self.rect = pygame.Rect(screen_width - self.width, 0, self.width, self.height)
        
        self.all_elements: List[Dict[str, Any]] = []
        self._filtered_elements: List[Dict[str, Any]] = []
        self.ui_rects: Dict[str, pygame.Rect] = {}
        self.selected_stamp_name: Optional[str] = None
        
        self.search_term = ""
        self.search_rect = pygame.Rect(self.rect.left + PADDING, PADDING, self.width - (2 * PADDING), SEARCH_BAR_HEIGHT)
        self.search_active = False

        self.scroll_offset = 0
        self.content_height = 0
        self.is_dragging_scrollbar = False
        scrollbar_y = self.search_rect.bottom + PADDING
        scrollbar_height = self.height - scrollbar_y - PADDING

        # The search bar's rect is now calculated dynamically with everything else.
        self.scrollbar_rect = pygame.Rect(self.rect.right - SCROLLBAR_WIDTH - 2, PADDING, SCROLLBAR_WIDTH, self.height - (2*PADDING))
        self.scrollbar_thumb_rect = pygame.Rect(self.scrollbar_rect.x, 0, SCROLLBAR_WIDTH, 0)

        self._create_ui_elements()
        self.filter_elements() # Set up the initial view

    def _create_ui_elements(self):
        """Creates the master list of all UI elements, ensuring each has a unique name."""
        self.all_elements.append({'type': 'header', 'text': 'File Operations', 'name': 'header_file'})
        for name in ["Save", "Load", "Export"]: self.all_elements.append({'type': 'action', 'name': name})
        self.all_elements.append({'type': 'header', 'text': 'Tools', 'name': 'header_tools'})
        self.all_elements.append({'type': 'search_bar', 'name': 'Search'})
        self.all_elements.append({'type': 'eraser', 'name': 'Eraser'})
        self.all_elements.append({'type': 'action', 'name': 'Mute Music'})
        self.all_elements.append({'type': 'header', 'text': 'Terminals (Pairs)', 'name': 'header_terminals'})
        for i in range(1, 7): self.all_elements.append({'type': 'terminal_pair', 'line_number': i, 'name': f"Terminal Pair {i}"})
        self.all_elements.append({'type': 'header', 'text': 'Buildings', 'name': 'header_buildings'})
        for building_id in sorted(C.BUILDING_COORDS.keys()): self.all_elements.append({'type': 'building', 'name': building_id})
        self.all_elements.append({'type': 'header', 'text': 'Track Tiles', 'name': 'header_tracks'})
        for name, details in C.TILE_DEFINITIONS.items(): self.all_elements.append({'type': 'tile', 'name': name, 'details': details})
        self.selected_stamp_name = 'Eraser'

    def filter_elements(self):
        """Updates the _filtered_elements list based on the search term."""
        if self.search_term == "":
            # If search is empty, show all elements.
            self._filtered_elements = self.all_elements[:]
        else:
            search_lower = self.search_term.lower()
            
            # Find the search bar element from the master list.
            search_bar_element = next((elem for elem in self.all_elements if elem['name'] == 'Search'), None)
            
            # Find all stamps that match the search term.
            matching_stamps = [
                elem for elem in self.all_elements 
                if elem['type'] not in ['header', 'action', 'search_bar'] and search_lower in elem['name'].lower()
            ]
            
            # The new filtered list is ALWAYS the search bar plus any matches.
            if search_bar_element:
                self._filtered_elements = [search_bar_element] + matching_stamps
            else: # Failsafe
                self._filtered_elements = matching_stamps

        # After filtering, always recalculate the layout for the newly visible items.
        self._calculate_rects()

    def _calculate_rects(self):
        """Calculates positions for the currently filtered elements."""
        self.ui_rects.clear()
        x, y = PADDING, PADDING
        row_width = self.width - (2 * PADDING) - SCROLLBAR_WIDTH
        
        for element in self._filtered_elements:
            name, elem_type = element['name'], element['type']
            
            if elem_type in ['header', 'action', 'terminal_pair', 'search_bar']:
                if x != PADDING: y += ITEM_SIZE + PADDING
                x = PADDING
                
                height = 0
                if elem_type == 'header': height = HEADER_HEIGHT
                elif elem_type == 'action': height = ACTION_BUTTON_HEIGHT
                elif elem_type == 'search_bar': height = SEARCH_BAR_HEIGHT
                else: height = ITEM_SIZE # Terminal Pair

                item_width = row_width if elem_type != 'terminal_pair' else ITEM_SIZE * 2 + 5
                self.ui_rects[name] = pygame.Rect(x, y, item_width, height)
                y += height + PADDING
            else:
                if x + ITEM_SIZE > row_width:
                    x = PADDING; y += ITEM_SIZE + PADDING
                self.ui_rects[name] = pygame.Rect(x, y, ITEM_SIZE, ITEM_SIZE)
                x += ITEM_SIZE + PADDING
        
        # After the loop, if we were in the middle of a grid row, add the final row's height.
        if x != PADDING:
            y += ITEM_SIZE + PADDING
        self.content_height = y

    def get_selected_stamp(self) -> Optional[Dict[str, Any]]:
        if not self.selected_stamp_name: return None
        return next((elem for elem in self.all_elements if elem['name'] == self.selected_stamp_name), None)

    def handle_event(self, event: pygame.event.Event) -> Optional[str]:
        """Handles all events for the sidebar, including text input for the search bar."""
        mouse_pos = pygame.mouse.get_pos()

        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(mouse_pos):
                self.scroll_offset -= event.y * 30; self._clamp_scroll()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            click_result = self._handle_click(mouse_pos)
            
            # The click handler now manages setting search_active
            if click_result:
                return click_result
            else:
                # If the click was on the sidebar but not on any button, deactivate search
                if self.rect.collidepoint(mouse_pos):
                    self.search_active = False

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.is_dragging_scrollbar = False

        elif event.type == pygame.MOUSEMOTION and self.is_dragging_scrollbar:
            scroll_ratio = (mouse_pos[1] - self.scrollbar_rect.top) / self.scrollbar_rect.height
            self.scroll_offset = scroll_ratio * (self.content_height - self.height)
            self._clamp_scroll()

        elif event.type == pygame.KEYDOWN and self.search_active:
            if event.key == pygame.K_BACKSPACE: self.search_term = self.search_term[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_ESCAPE): self.search_active = False
            else: self.search_term += event.unicode
            self.filter_elements(); return "ui_focus"
            
        return None

    def _handle_click(self, mouse_pos: Tuple[int, int]) -> Optional[str]:
        """Checks for clicks on any visible UI element."""
        # First, check for scrollbar click, as it's on top
        if self.scrollbar_thumb_rect.collidepoint(mouse_pos):
            self.is_dragging_scrollbar = True
            return "ui_focus"

        # Check all dynamically positioned elements
        for name, rect in self.ui_rects.items():
            hittest_rect = pygame.Rect(self.rect.left + rect.x, self.rect.top + rect.y - self.scroll_offset, rect.width, rect.height)
            
            if hittest_rect.collidepoint(mouse_pos):
                element = next((elem for elem in self.all_elements if elem['name'] == name), None)
                if not element: continue

                if element['type'] == 'search_bar':
                    self.search_active = True
                    return "ui_focus"
                elif element['type'] in ['eraser', 'terminal_pair', 'building', 'tile']:
                    self.search_active = False
                    self.selected_stamp_name = name; return "stamp"
                elif element['type'] == 'action':
                    self.search_active = False
                    return name
        return None

    def _clamp_scroll(self):
        self.scroll_offset = max(0, self.scroll_offset)
        max_scroll = self.content_height - self.height
        if max_scroll > 0: self.scroll_offset = min(self.scroll_offset, max_scroll)
        else: self.scroll_offset = 0

    def draw(self, screen: pygame.Surface, sounds: SoundManager):
        """
        Draws all UI elements, including the dynamically labeled Mute button.

        Args:
            screen (pygame.Surface): The main display surface.
            sounds (SoundManager): The game's sound manager instance.
        """
        pygame.draw.rect(screen, (40, 40, 60), self.rect)
        
        for element in self._filtered_elements:
            name, elem_type = element['name'], element['type']
            abs_rect = self.ui_rects.get(name)
            if not abs_rect: continue
            
            pos_x, pos_y = self.rect.left + abs_rect.x, self.rect.top + abs_rect.y - self.scroll_offset
            if pos_y > self.height or pos_y + abs_rect.height < 0: continue
            
            rect = pygame.Rect(pos_x, pos_y, abs_rect.width, abs_rect.height)

            if elem_type == 'search_bar':
                search_bg_color = (60, 60, 80) if self.search_active else (30, 30, 40)
                pygame.draw.rect(screen, search_bg_color, rect, border_radius=5)
                if self.search_active: pygame.draw.rect(screen, C.COLOR_HIGHLIGHT, rect, 2, border_radius=5)
                search_text, text_color = (self.search_term, C.COLOR_WHITE) if self.search_term or self.search_active else ("Search Stamps...", (150, 150, 150))
                draw_text(screen, search_text, rect.x + 10, rect.centery, text_color, 20, False, True)
            
            elif elem_type == 'header':
                draw_text(screen, element['text'], rect.left + 5, rect.centery, (180, 180, 200), 20, False, True)

            elif elem_type == 'action':
                # Use the passed-in sounds object to get the current mute state
                text = name
                if name == 'Mute Music':
                    text = "Unmute" if sounds.is_muted else "Mute"
                
                color = (100, 100, 130) if rect.collidepoint(pygame.mouse.get_pos()) else (80, 80, 100)
                pygame.draw.rect(screen, color, rect, border_radius=8)
                draw_text(screen, text, rect.centerx, rect.centery, C.COLOR_WHITE, 22, True, True)
                pygame.draw.rect(screen, (120, 120, 150), rect, 2, border_radius=8)
            
            else: # It's a stamp
                self._draw_stamp(screen, element, rect)
                if self.selected_stamp_name == name: pygame.draw.rect(screen, C.COLOR_HIGHLIGHT, rect, 3)
                else: pygame.draw.rect(screen, (80, 80, 100), rect, 1)

        # Draw the scrollbar (logic is now correct)
        if self.content_height > self.height:
            pygame.draw.rect(screen, (30, 30, 40), self.scrollbar_rect)
            thumb_height = max(20, (self.height / self.content_height) * self.scrollbar_rect.height)
            thumb_y_ratio = self.scroll_offset / (self.content_height - self.height) if self.content_height > self.height else 0
            thumb_y = self.scrollbar_rect.top + thumb_y_ratio * (self.scrollbar_rect.height - thumb_height)
            self.scrollbar_thumb_rect = pygame.Rect(self.scrollbar_rect.x, thumb_y, SCROLLBAR_WIDTH, thumb_height)
            pygame.draw.rect(screen, (100, 100, 120), self.scrollbar_thumb_rect, border_radius=4)
    # --- END OF CHANGE ---

    def _get_stamp_surface(self, element: Dict[str, Any], size: Tuple[int, int]) -> pygame.Surface:
        surf = pygame.Surface(size)
        if element['type'] == 'eraser':
            surf.fill((255, 100, 100)); draw_text(surf, "ERASE", size[0]//2, size[1]//2, C.COLOR_WHITE, 20, True, True)
        elif element['type'] == 'building':
            font = get_font(int(size[0] * 0.7)); surf.fill(C.COLOR_BUILDING_BG)
            text_surf = font.render(element['name'], True, C.COLOR_BUILDING_FG); surf.blit(text_surf, text_surf.get_rect(center=(size[0]//2, size[1]//2)))
        elif element['type'] == 'tile':
            dummy_type = type('TileType', (object,), {'name': element['name'], **element['details']}); surf = create_tile_surface(dummy_type, size[0])
        return surf

    def _draw_stamp(self, screen, element, rect):
        elem_type, name = element['type'], element['name']
        if elem_type == 'terminal_pair':
            pygame.draw.rect(screen, (30,30,50), rect)
            curve_size = rect.height
            base_curve = create_tile_surface(type('TileType', (object,), {'name': 'Curve', **C.TILE_DEFINITIONS['Curve']}), curve_size)
            curve_left = pygame.transform.rotate(base_curve, -90); curve_right = pygame.transform.rotate(base_curve, -180)
            left_bg_rect = pygame.Rect(rect.left, rect.top, curve_size, curve_size); right_bg_rect = pygame.Rect(rect.left + curve_size + 5, rect.top, curve_size, curve_size)
            pygame.draw.rect(screen, C.COLOR_WHITE, left_bg_rect); pygame.draw.rect(screen, C.COLOR_WHITE, right_bg_rect)
            screen.blit(curve_left, left_bg_rect.topleft); screen.blit(curve_right, right_bg_rect.topleft)
            font = get_font(int(rect.height * 0.4))
            text_surf = font.render(f"T{element['line_number']}", True, C.COLOR_WHITE, (0,0,0,150))
            screen.blit(text_surf, text_surf.get_rect(center=rect.center))
        else:
            if elem_type == 'tile': pygame.draw.rect(screen, C.COLOR_WHITE, rect)
            surf = self._get_stamp_surface(element, rect.size)
            screen.blit(surf, rect.topleft)