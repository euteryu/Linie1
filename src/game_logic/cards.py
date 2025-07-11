# game_logic/cards.py
from typing import List

class LineCard:
    def __init__(self, line_number: int):
        self.line_number = line_number
    def __repr__(self) -> str:
        return f"LineCard(Line {self.line_number})"

class RouteCard:
    def __init__(self, stops: List[str], variant_index: int):
        self.stops = stops
        self.variant_index = variant_index
    def __repr__(self) -> str:
        return f"RouteCard({'-'.join(self.stops)}, Var {self.variant_index})"
