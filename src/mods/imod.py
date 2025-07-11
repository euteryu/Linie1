# imod.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, Any, List, Tuple

if TYPE_CHECKING:
    from game_logic.game import Game
    from game_logic.player import Player, AIPlayer
    from game_logic.ai_actions import PotentialAction # Add this import
    # from visualizer import Linie1Visualizer # For UI hooks
    import pygame

class IMod(ABC):
    """
    Abstract Base Class for all game mods.
    Each mod must inherit from this and implement its methods.
    """
    def __init__(self, mod_id: str, name: str, description: str, config: Dict[str, Any]):
        self.mod_id = mod_id
        self.name = name
        self.description = description
        self.config = config # Mod-specific configuration data
        self.is_active = False # Set by ModManager based on user selection

    # --- Game Lifecycle Hooks ---
    def on_game_setup(self, game: Game):
        """Called once when a new game starts or a saved game is loaded."""
        pass

    def on_player_turn_start(self, game: Game, player: Player):
        """Called at the very beginning of a player's turn."""
        pass

    def on_player_turn_end(self, game: Game, player: Player):
        """Called after a player's turn is confirmed."""
        pass

    def on_tile_drawn(self, game: Game, player: Player, drawn_tile_name: str, tile_draw_pile: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Called when a player is about to draw a tile.
        Mod can override draw logic. Return (True, chosen_tile_name) if mod handles draw,
        (False, None) to let base game handle.
        """
        return False, None

    # --- UI Hooks (More Complex) ---
    def get_ui_buttons(self, current_game_state_name: str) -> List[Dict[str, Any]]:
        """
        Return a list of UI button definitions specific to this mod
        for the current game state (e.g., LayingTrackState, DrivingState).
        Each dict should contain 'text', 'rect', 'callback_name'.
        """
        return []

    def handle_ui_button_click(self, game: Game, player: Player, button_name: str) -> bool:
        """
        Handles a click on a UI button provided by this mod.
        Returns True if the click was handled by this mod.
        """
        return False
    
    def on_draw_ui_panel(self, screen: 'pygame.Surface', visualizer: 'Linie1Visualizer', current_game_state_name: str):
        """
        Allows mods to draw custom elements directly onto the UI panel.
        Called during visualizer.draw_ui.
        """
        pass

    def on_hand_tile_clicked(self, game: 'Game', player: 'Player', tile_type: 'TileType') -> bool:
        """
        Called when a player clicks a tile in their hand.
        A mod can return True to signify it has handled this click,
        preventing the default game state logic from running.
        For example, a "Super Star Tile" mod would use this to trigger a special state.
        """
        return False # Default behavior: mod does not handle the click

    def get_ai_potential_actions(self, game: 'Game', player: 'AIPlayer') -> List['PotentialAction']:
        """
        Allows a mod to provide a list of its own special actions for the AI to consider.
        """
        return []

    # Add other hooks as needed (e.g., on_tile_placed, on_money_changed, on_route_validated)