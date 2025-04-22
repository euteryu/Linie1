'''
      
pygame.draw.arc(surface, color, rect, start_angle, stop_angle, width)

    surface: The pygame.Surface to draw on (our temp_surf).

    color: The color tuple (our track_color).

    rect: A pygame.Rect (tuple or object like (left, top, width, height)) that defines the bounding box of the ellipse the arc is drawn from. For our quarter circles, this rect should represent a circle centered on the tile corner.

    start_angle: The starting angle in radians. 0 is East (like the positive X-axis), angles increase counter-clockwise (CCW).

    stop_angle: The ending angle in radians. The arc is drawn CCW from start_angle to stop_angle.

    width: The line thickness.
'''

# debug_arcs.py
import pygame
import sys
import math

# --- Configuration ---
TILE_SIZE = 100 # Make it reasonably large for visibility
LINE_WIDTH = max(2, int(TILE_SIZE * 0.1)) # Same calculation
WINDOW_WIDTH = TILE_SIZE * 2 + 60 # Room for 2x2 tiles + padding
WINDOW_HEIGHT = TILE_SIZE * 2 + 60
PADDING = 30

COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_RED = (255, 0, 0)
COLOR_BLUE = (0, 0, 255)
COLOR_GREEN = (0, 255, 0)
COLOR_YELLOW = (255, 255, 0)
COLOR_GREY = (150, 150, 150)
TRACK_COLOR = (50, 50, 50)

# --- Angles (Radians) ---
angle_N = math.pi / 2
angle_W = math.pi
angle_S = 3 * math.pi / 2
angle_E = 0 # or 2*pi

# --- Main Setup ---
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Arc Debugger")
font = pygame.font.SysFont(None, 24)

# --- Define rects for the 4 test squares ---
rect_sq_NE = pygame.Rect(PADDING + TILE_SIZE, PADDING, TILE_SIZE, TILE_SIZE) # Top Right
rect_sq_NW = pygame.Rect(PADDING, PADDING, TILE_SIZE, TILE_SIZE)             # Top Left
rect_sq_SE = pygame.Rect(PADDING + TILE_SIZE, PADDING + TILE_SIZE, TILE_SIZE, TILE_SIZE) # Bottom Right
rect_sq_SW = pygame.Rect(PADDING, PADDING + TILE_SIZE, TILE_SIZE, TILE_SIZE)             # Bottom Left

# --- Calculate the bounding Rects for arcs, RELATIVE TO EACH SQUARE'S TOP-LEFT ---
# These calculations MUST mirror the logic in create_tile_surface's temp_surf approach
radius = TILE_SIZE // 2
# Rect centered at Target Corner (size, 0) RELATIVE to square top-left (x,y) -> Rect(x+radius, y-radius, TILE_SIZE, TILE_SIZE)
arc_rect_NE = pygame.Rect(rect_sq_NE.left + radius, rect_sq_NE.top - radius, TILE_SIZE, TILE_SIZE)
# Rect centered at Target Corner (0, 0) RELATIVE to square top-left (x,y) -> Rect(x-radius, y-radius, TILE_SIZE, TILE_SIZE)
arc_rect_NW = pygame.Rect(rect_sq_NW.left - radius, rect_sq_NW.top - radius, TILE_SIZE, TILE_SIZE)
# Rect centered at Target Corner (size, size) RELATIVE to square top-left (x,y) -> Rect(x+radius, y+radius, TILE_SIZE, TILE_SIZE)
arc_rect_SE = pygame.Rect(rect_sq_SE.left + radius, rect_sq_SE.top + radius, TILE_SIZE, TILE_SIZE)
# Rect centered at Target Corner (0, size) RELATIVE to square top-left (x,y) -> Rect(x-radius, y+radius, TILE_SIZE, TILE_SIZE)
arc_rect_SW = pygame.Rect(rect_sq_SW.left - radius, rect_sq_SW.top + radius, TILE_SIZE, TILE_SIZE)


# --- Game Loop ---
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # --- Drawing ---
    screen.fill(COLOR_WHITE)

    # Draw the squares
    pygame.draw.rect(screen, COLOR_GREY, rect_sq_NE, 1)
    pygame.draw.rect(screen, COLOR_GREY, rect_sq_NW, 1)
    pygame.draw.rect(screen, COLOR_GREY, rect_sq_SE, 1)
    pygame.draw.rect(screen, COLOR_GREY, rect_sq_SW, 1)

    # --- Draw the Arcs ---
    # N-E (Expected: OK)
    pygame.draw.arc(screen, COLOR_RED, arc_rect_NE, angle_N, angle_E + 2*math.pi, LINE_WIDTH)
    # S-E (Expected: OK based on previous fix)
    pygame.draw.arc(screen, COLOR_BLUE, arc_rect_SE, angle_E, angle_S, LINE_WIDTH)
    # N-W (Problematic?)
    pygame.draw.arc(screen, COLOR_GREEN, arc_rect_NW, angle_W, angle_N, LINE_WIDTH)
    # S-W (Problematic?)
    pygame.draw.arc(screen, COLOR_YELLOW, arc_rect_SW, angle_S, angle_W, LINE_WIDTH)

    # Draw Labels
    label_ne = font.render("N-E (Red)", True, COLOR_RED)
    screen.blit(label_ne, (rect_sq_NE.left + 5, rect_sq_NE.top + 5))
    label_nw = font.render("N-W (Green)", True, COLOR_GREEN)
    screen.blit(label_nw, (rect_sq_NW.left + 5, rect_sq_NW.top + 5))
    label_se = font.render("S-E (Blue)", True, COLOR_BLUE)
    screen.blit(label_se, (rect_sq_SE.left + 5, rect_sq_SE.top + 5))
    label_sw = font.render("S-W (Yellow)", True, COLOR_YELLOW)
    screen.blit(label_sw, (rect_sq_SW.left + 5, rect_sq_SW.top + 5))

    pygame.display.flip()

pygame.quit()
sys.exit()