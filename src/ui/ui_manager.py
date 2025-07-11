# ui/ui_manager.py
import pygame
from ui.panels import GameInfoPanel, PlayerInfoPanel, HandPanel, MessagePanel, ButtonPanel, ModPanel
import common.constants as C

class UIManager:
    """
    Manages all the individual UI components (panels) for the in-game screen.
    It delegates drawing and event handling to the appropriate components.
    """
    def __init__(self, screen, tile_surfaces, mod_manager, theme):
        """
        Initializes the UI Manager.

        Args:
            screen: The main pygame screen surface.
            tile_surfaces: A dictionary of pre-rendered tile surfaces from the Visualizer.
            mod_manager: The game's mod manager instance.
        """
        hand_tile_surfaces = {name: pygame.transform.scale(surf, (C.HAND_TILE_SIZE, C.HAND_TILE_SIZE)) 
                              for name, surf in tile_surfaces.items()}

        self.components = [
            GameInfoPanel(screen, theme),
            PlayerInfoPanel(screen, theme),
            HandPanel(screen, hand_tile_surfaces, theme),
            MessagePanel(screen, theme),
            ButtonPanel(screen, theme),
            ModPanel(screen, theme),
        ]

    def draw(self, game, current_state):
        """Draw all managed UI components."""
        for component in self.components:
            component.draw(game=game, current_state=current_state)

    def handle_event(self, event, game, current_state):
        """Pass an event to all managed UI components."""
        for component in self.components:
            if component.handle_event(event=event, game=game, current_state=current_state):
                return True # Stop processing if one component handles the event
        return False