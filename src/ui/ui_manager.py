# ui/ui_manager.py
import pygame
from ui.panels import GameInfoPanel, PlayerInfoPanel, HandPanel, MessagePanel, ButtonPanel, ModPanel
import common.constants as C
from common.layout import LayoutConstants # Import for type hinting


class UIManager:
    """
    Manages all the individual UI components (panels) for the in-game screen.
    It delegates drawing and event handling to the appropriate components.
    """
    def __init__(self, scene: 'GameScene', strategy_surfaces, pretty_surfaces, mod_manager, theme, layout: LayoutConstants):
        """
        Initializes the UI Manager.

        Args:
            scene: The parent GameScene.
            strategy_surfaces: A dictionary of the line-drawn tile surfaces.
            pretty_surfaces: A dictionary of the high-res asset tile surfaces.
            mod_manager: The game's mod manager instance.
            theme: The color and font theme dictionary.
            layout: The dynamic LayoutConstants object.
        """
        screen = scene.screen
        
        # Scale down surfaces for the hand panel using dynamic size
        scaled_strategy_surfaces = {name: pygame.transform.scale(surf, (layout.HAND_TILE_SIZE, layout.HAND_TILE_SIZE)) 
                                    for name, surf in strategy_surfaces.items()}
        scaled_pretty_surfaces = {name: pygame.transform.scale(surf, (layout.HAND_TILE_SIZE, layout.HAND_TILE_SIZE)) 
                                  for name, surf in pretty_surfaces.items()}

        # Pass the layout object to all child components
        self.components = [
            GameInfoPanel(screen, theme, layout),
            PlayerInfoPanel(screen, theme, layout),
            HandPanel(screen, scaled_strategy_surfaces, scaled_pretty_surfaces, theme, layout),
            MessagePanel(screen, theme, layout),
            ButtonPanel(screen, theme, layout),
            ModPanel(screen, theme, layout),
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