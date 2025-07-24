# rendering_utils.py
import pygame
import math
import common.constants as C

def create_tile_surface(tile_type: 'TileType', size: int) -> pygame.Surface:
    """ Creates a Pygame Surface using lines and arcs for a tile type. """
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill(C.COLOR_TRANSPARENT)
    line_width = max(2, int(size * C.TRACK_WIDTH_RATIO))
    track_color = C.COLOR_TRACK

    half_size = size // 2
    ptN, ptS, ptE, ptW = (half_size, 0), (half_size, size), (size, half_size), (0, half_size)
    rect_TR = pygame.Rect(half_size, -half_size, size, size)
    rect_TL = pygame.Rect(-half_size, -half_size, size, size)
    rect_BR = pygame.Rect(half_size, half_size, size, size)
    rect_BL = pygame.Rect(-half_size, half_size, size, size)

    angle_N, angle_E, angle_S, angle_W = math.radians(90), math.radians(0), math.radians(270), math.radians(180)
    tile_name = tile_type.name

    if tile_name == "Straight": pygame.draw.line(surf, track_color, ptN, ptS, line_width)
    elif tile_name == "Curve": pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E, line_width)
    elif tile_name == "StraightLeftCurve":
        pygame.draw.line(surf, track_color, ptN, ptS, line_width)
        pygame.draw.arc(surf, track_color, rect_BL, angle_S, angle_W, line_width)
    elif tile_name == "StraightRightCurve":
        pygame.draw.line(surf, track_color, ptN, ptS, line_width)
        pygame.draw.arc(surf, track_color, rect_BR, angle_E, angle_S, line_width)
    elif tile_name == "DoubleCurveY":
        pygame.draw.arc(surf, track_color, rect_TL, angle_W, angle_N, line_width)
        pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E, line_width)
    elif tile_name == "DiagonalCurve":
        pygame.draw.arc(surf, track_color, rect_BL, angle_S, angle_W, line_width)
        pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E, line_width)
    elif tile_name == "Tree_JunctionTop":
        pygame.draw.line(surf, track_color, ptW, ptE, line_width)
        pygame.draw.arc(surf, track_color, rect_TL, angle_W, angle_N, line_width)
        pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E, line_width)
    elif tile_name == "Tree_JunctionRight":
        pygame.draw.line(surf, track_color, ptW, ptE, line_width)
        pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E, line_width)
        pygame.draw.arc(surf, track_color, rect_BR, angle_E, angle_S, line_width)
    elif tile_name == "Tree_Roundabout":
        pygame.draw.arc(surf, track_color, rect_TL, angle_W, angle_N, line_width)
        pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E, line_width)
        pygame.draw.arc(surf, track_color, rect_BR, angle_E, angle_S, line_width)
        pygame.draw.arc(surf, track_color, rect_BL, angle_S, angle_W, line_width)
    elif tile_name == "Tree_Crossroad":
        pygame.draw.line(surf, track_color, ptN, ptS, line_width)
        pygame.draw.line(surf, track_color, ptW, ptE, line_width)
    elif tile_name == "Tree_StraightDiagonal1":
        pygame.draw.line(surf, track_color, ptN, ptS, line_width)
        pygame.draw.arc(surf, track_color, rect_BL, angle_S, angle_W, line_width)
        pygame.draw.arc(surf, track_color, rect_TR, angle_N, angle_E, line_width)
    elif tile_name == "Tree_StraightDiagonal2":
        pygame.draw.line(surf, track_color, ptN, ptS, line_width)
        pygame.draw.arc(surf, track_color, rect_TL, angle_W, angle_N, line_width)
        pygame.draw.arc(surf, track_color, rect_BR, angle_E, angle_S, line_width)
    else: # Fallback for unknown or special mod tiles
        pygame.draw.rect(surf, C.COLOR_GRID, surf.get_rect(), 1)
        font = get_font(12)
        text_surf = font.render(tile_name, True, C.COLOR_TRACK, C.COLOR_UI_BG)
        text_rect = text_surf.get_rect(center=(half_size, half_size))
        surf.blit(text_surf, text_rect)
        
    return surf

# Centralized font management
_font_cache = {}
def get_font(size: int) -> pygame.font.Font:
    """Gets a font from the cache or creates it, with a fallback."""
    if size not in _font_cache:
        try:
            _font_cache[size] = pygame.font.SysFont(None, size)
        except Exception:
            _font_cache[size] = pygame.font.Font(None, size)
    return _font_cache[size]

def draw_text(surface, text, x, y, color=C.COLOR_UI_TEXT, size=C.DEFAULT_FONT_SIZE, center_x=False, center_y=False):
    """A robust text drawing function that can also center text."""
    try:
        font_to_use = get_font(size)
        text_surface = font_to_use.render(text, True, color)
        rect = text_surface.get_rect()
        draw_pos = [x, y]
        if center_x:
            draw_pos[0] = x - rect.width // 2
        if center_y:
            draw_pos[1] = y - rect.height // 2
        
        surface.blit(text_surface, draw_pos)
    except Exception as e:
        print(f"Error rendering text '{text}': {e}")