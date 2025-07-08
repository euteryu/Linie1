# mods/economic_mod/constants_economic.py

import constants as C # Import the base constants for reference

# --- UI Panel Positions ---
# We position our mod's UI elements relative to the main UI panel for consistency.
PANEL_X_OFFSET = 150
PANEL_Y_OFFSET = C.UI_ROUTE_INFO_Y + (C.UI_LINE_HEIGHT * 2) + 50

# Capital Display
CAPITAL_DISPLAY_X = C.UI_PANEL_X + PANEL_X_OFFSET
CAPITAL_DISPLAY_Y = PANEL_Y_OFFSET

# Buttons
BUTTON_X = C.UI_PANEL_X + PANEL_X_OFFSET
BUTTON_Y_START = PANEL_Y_OFFSET + C.UI_LINE_HEIGHT + 10 # Place buttons below the Capital display
BUTTON_WIDTH = 180
BUTTON_HEIGHT = 30
BUTTON_SPACING = 5