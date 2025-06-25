# game_logic/player.py
from typing import List, Dict, Tuple, Optional
from .enums import PlayerState, Direction # Use relative import
from .tile import TileType # Use relative import
from .cards import LineCard, RouteCard # Use relative import

class Player:
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.hand: List[TileType] = []
        self.line_card: Optional[LineCard] = None
        self.route_card: Optional[RouteCard] = None
        self.player_state: PlayerState = PlayerState.LAYING_TRACK
        self.streetcar_position: Optional[Tuple[int, int]] = None
        self.required_node_index: int = 0
        self.start_terminal_coord: Optional[Tuple[int, int]] = None
        self.arrival_direction: Optional[Direction] = None

    def __repr__(self) -> str:
        num_stops = len(self.route_card.stops) if self.route_card and self.route_card.stops else 0
        total_targets = num_stops + 1
        return (f"Player(id={self.player_id}, "
                f"State={self.player_state.name}, "
                f"Hand={len(self.hand)}, "
                f"NodeIdx={self.required_node_index}/{total_targets})")

    def to_dict(self) -> Dict:
        """Converts Player state to a JSON-serializable dictionary."""
        hand_data = [tile.name for tile in self.hand]
        line_card_data = self.line_card.line_number if self.line_card else None
        route_card_data = { "stops": self.route_card.stops, "variant": self.route_card.variant_index } if self.route_card else None
        return {
            "player_id": self.player_id,
            "hand": hand_data,
            "line_card": line_card_data,
            "route_card": route_card_data,
            "player_state": self.player_state.name,
            "streetcar_position": list(self.streetcar_position) if self.streetcar_position else None,
            "required_node_index": self.required_node_index,
            "start_terminal_coord": list(self.start_terminal_coord) if self.start_terminal_coord else None,
            "arrival_direction": self.arrival_direction.name if self.arrival_direction else None,
        }

    @staticmethod
    def from_dict(data: Dict, tile_types: Dict[str, 'TileType']) -> 'Player':
        player_id = data.get("player_id", -1)
        player = Player(player_id)
        player.hand = [tile_types[name] for name in data.get("hand", []) if name in tile_types]
        lc_num = data.get("line_card")
        player.line_card = LineCard(lc_num) if lc_num is not None else None
        rc_data = data.get("route_card")
        if rc_data and isinstance(rc_data, dict):
             player.route_card = RouteCard(rc_data.get("stops",[]), rc_data.get("variant", 0))
        try:
            player.player_state = PlayerState[data.get("player_state", "LAYING_TRACK")]
        except KeyError:
            player.player_state = PlayerState.LAYING_TRACK
        pos_list = data.get("streetcar_position")
        player.streetcar_position = tuple(pos_list) if isinstance(pos_list, list) and len(pos_list) == 2 else None
        player.required_node_index = data.get("required_node_index", 0)
        start_term_list = data.get("start_terminal_coord")
        player.start_terminal_coord = tuple(start_term_list) if isinstance(start_term_list, list) and len(start_term_list) == 2 else None
        arrival_str = data.get("arrival_direction")
        try:
             player.arrival_direction = Direction[arrival_str] if arrival_str else None
        except KeyError:
             player.arrival_direction = None
        return player

    def get_required_stop_coords(self, game: 'Game') -> Optional[List[Tuple[int, int]]]:
        """
        Gets the sequence of STOP coordinates the player needs to visit.
        Returns None if any required stop sign is not yet on the board.
        Returns an empty list if the route card has no stops.
        """
        if not self.route_card:
            return [] # No stops required

        stop_coords = []
        for stop_id in self.route_card.stops:
            coord = game.board.building_stop_locations.get(stop_id)
            if coord is None:
                # A required stop for the route is not yet placed on the board
                return None
            stop_coords.append(coord)
        return stop_coords

    def get_full_driving_sequence(self, game: 'Game') -> Optional[List[Tuple[int, int]]]:
        """
        Gets the full, ordered list of nodes for the DRIVING phase, based on
        the determined start terminal.
        """
        if not self.line_card or not self.start_terminal_coord:
            return None # Cannot determine sequence if not set up for driving

        stop_coords = self.get_required_stop_coords(game)
        if stop_coords is None:
             return None # Driving phase assumes all stops are on board

        term1, term2 = game.get_terminal_coords(self.line_card.line_number)
        if not term1 or not term2:
            return None

        # Determine the end terminal based on the chosen start terminal
        end_terminal = term2 if self.start_terminal_coord == term1 else term1

        return [self.start_terminal_coord] + stop_coords + [end_terminal]

    def get_next_target_node(self, game: 'Game') -> Optional[Tuple[int, int]]:
        """
        Gets the coordinate of the very next node in the required sequence
        that the player must visit.
        """
        sequence = self.get_full_driving_sequence(game)
        if not sequence:
            return None

        # The target node is at the list index corresponding to the player's progress.
        # Example: required_node_index=0 means aiming for sequence[0] (start terminal).
        # This is for pathing TO the node. Once reached, index increments.
        target_list_index = self.required_node_index

        if target_list_index < len(sequence):
            return sequence[target_list_index]
        else:
            return None # Already passed all required nodes.