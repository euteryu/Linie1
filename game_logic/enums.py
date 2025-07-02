from enum import Enum, auto

class PlayerState(Enum):
    LAYING_TRACK = auto()
    DRIVING = auto()
    FINISHED = auto()
    ELIMINATED = auto() # NEW: For players who have forfeited

class GamePhase(Enum):
    SETUP = auto()
    LAYING_TRACK = auto()
    DRIVING = auto()
    GAME_OVER = auto()

class Direction(Enum):
    N = (-1, 0)
    E = (0, 1)
    S = (1, 0)
    W = (0, -1)

    @staticmethod
    def opposite(direction: 'Direction') -> 'Direction':
        # ... implementation ...
        if direction == Direction.N: return Direction.S
        elif direction == Direction.S: return Direction.N
        elif direction == Direction.E: return Direction.W
        elif direction == Direction.W: return Direction.E
        else: raise ValueError("Invalid direction")


    @staticmethod
    def from_str(dir_str: str) -> 'Direction':
        # ... implementation ...
        try: return Direction[dir_str.upper()]
        except KeyError: raise ValueError(f"Invalid direction string: '{dir_str}'")
