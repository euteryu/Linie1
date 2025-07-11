# src/game_logic/ai_actions.py
from __future__ import annotations
from typing import Dict, Any, Callable, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from .game import Game
    from .player import Player
    from .commands import Command

@dataclass
class PotentialAction:
    """A standardized structure for any action an AI can consider."""
    action_type: str
    details: Dict[str, Any]
    command_generator: Callable
    score: float = 0.0
    score_breakdown: Dict[str, float] = None
    # --- NEW FIELD ---
    action_cost: int = 1 # Default to 1 action