# ui/ui_manager.py
import pygame
from ui.panels import GameInfoPanel, PlayerInfoPanel, HandPanel, MessagePanel, ButtonPanel, ModPanel
import common.constants as C

class UIManager:
    """
    Manages all the individual UI components (panels) for the in-game screen.
    It delegates drawing and event handling to the appropriate components.
    """
    def __init__(self, screen, strategy_tile_surfaces, pretty_tile_surfaces, mod_manager, theme):
        """
        Initializes the UI Manager.
        
        Args:
            screen: The main pygame screen surface.
            strategy_tile_surfaces: A dictionary of the line-drawn tile surfaces.
            pretty_tile_surfaces: A dictionary of the high-res asset tile surfaces.
            mod_manager: The game's mod manager instance.
        """
        # Scale down both sets of surfaces for the hand panel
        scaled_strategy_surfaces = {name: pygame.transform.scale(surf, (C.HAND_TILE_SIZE, C.HAND_TILE_SIZE)) 
                                    for name, surf in strategy_tile_surfaces.items()}
        scaled_pretty_surfaces = {name: pygame.transform.scale(surf, (C.HAND_TILE_SIZE, C.HAND_TILE_SIZE)) 
                                  for name, surf in pretty_tile_surfaces.items()}

        self.components = [
            GameInfoPanel(screen, theme),
            PlayerInfoPanel(screen, theme),
            # Pass both dictionaries to the HandPanel
            HandPanel(screen, scaled_strategy_surfaces, scaled_pretty_surfaces, theme),
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