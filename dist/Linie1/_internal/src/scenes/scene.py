# scenes/scene.py
from abc import ABC, abstractmethod

class Scene(ABC):
    def __init__(self, scene_manager):
        self.scene_manager = scene_manager

    @abstractmethod
    def handle_events(self, events):
        pass

    @abstractmethod
    def update(self, dt):
        pass

    @abstractmethod
    def draw(self, screen):
        pass