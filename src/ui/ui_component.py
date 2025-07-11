# ui/ui_component.py
from abc import ABC, abstractmethod
import pygame

class IUIComponent(ABC):
    """
    Abstract Base Class for all UI components. Enforces that each
    component must have a draw method and can optionally handle events.
    """
    def __init__(self, screen):
        self.screen = screen

    @abstractmethod
    def draw(self, *args, **kwargs):
        """Draws the component on the screen."""
        pass

    def handle_event(self, event: pygame.event.Event, *args, **kwargs):
        """
        Handles a Pygame event. Most components won't need this, but
        interactive ones like button panels will.
        Returns True if the event was handled, False otherwise.
        """
        return False