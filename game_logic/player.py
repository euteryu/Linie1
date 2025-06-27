# game_logic/player.py
from typing import List, Dict, Tuple, Optional, NamedTuple
from .enums import PlayerState, Direction # Use relative import
from .tile import TileType # Use relative import
from .cards import LineCard, RouteCard # Use relative import

# NEW: A self-contained, descriptive object for each step of the validated route.
class RouteStep(NamedTuple):
    coord: Tuple[int, int]
    is_goal_node: bool
    arrival_direction: Optional[Direction]

class Player:
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.hand: List[TileType] = []
        self.line_card: Optional[LineCard] = None
        self.route_card: Optional[RouteCard] = None
        self.player_state: PlayerState = PlayerState.LAYING_TRACK
        
        # The single source of truth for the tram's location on its path.
        self.streetcar_path_index: int = 0
        
        # Tracks which of the required NODES (stops/terminals) is the next goal.
        self.required_node_index: int = 0
        
        self.start_terminal_coord: Optional[Tuple[int, int]] = None
        
        # The "database" of the full, optimal path.
        self.validated_route: Optional[List[RouteStep]] = None

    @property
    def streetcar_position(self) -> Optional[Tuple[int, int]]:
        """The streetcar's coordinate, derived from its path index."""
        if self.validated_route and 0 <= self.streetcar_path_index < len(self.validated_route):
            return self.validated_route[self.streetcar_path_index].coord
        return None
    
    @property
    def arrival_direction(self) -> Optional[Direction]:
        """The direction of arrival, derived from the current step in the path."""
        if self.validated_route and 0 <= self.streetcar_path_index < len(self.validated_route):
            return self.validated_route[self.streetcar_path_index].arrival_direction
        return None

    def to_dict(self) -> Dict:
        """Converts Player state to a JSON-serializable dictionary."""
        hand_data = [tile.name for tile in self.hand]
        line_card_data = self.line_card.line_number if self.line_card else None
        route_card_data = { "stops": self.route_card.stops, "variant": self.route_card.variant_index } if self.route_card else None
        
        # Serialize the validated route into a list of simple dictionaries
        validated_route_data = None
        if self.validated_route:
            validated_route_data = [
                {
                    "coord": step.coord,
                    "is_goal": step.is_goal_node,
                    "arrival_dir": step.arrival_direction.name if step.arrival_direction else None
                } for step in self.validated_route
            ]

        return {
            "player_id": self.player_id,
            "hand": hand_data,
            "line_card": line_card_data,
            "route_card": route_card_data,
            "player_state": self.player_state.name,
            "streetcar_path_index": self.streetcar_path_index,
            "required_node_index": self.required_node_index,
            "start_terminal_coord": list(self.start_terminal_coord) if self.start_terminal_coord else None,
            "validated_route": validated_route_data,
        }

    @staticmethod
    def from_dict(data: Dict, tile_types: Dict[str, 'TileType']) -> 'Player':
        player = Player(data.get("player_id", -1))
        player.hand = [tile_types[name] for name in data.get("hand", []) if name in tile_types]
        lc_num = data.get("line_card")
        player.line_card = LineCard(lc_num) if lc_num is not None else None
        rc_data = data.get("route_card")
        if rc_data and isinstance(rc_data, dict): player.route_card = RouteCard(rc_data.get("stops",[]), rc_data.get("variant", 0))
        try: player.player_state = PlayerState[data.get("player_state", "LAYING_TRACK")]
        except KeyError: player.player_state = PlayerState.LAYING_TRACK
        
        player.streetcar_path_index = data.get("streetcar_path_index", 0)
        player.required_node_index = data.get("required_node_index", 0)
        start_term_list = data.get("start_terminal_coord")
        player.start_terminal_coord = tuple(start_term_list) if isinstance(start_term_list, list) and len(start_term_list) == 2 else None
        
        # Reconstruct the validated route from the list of dictionaries
        validated_route_data = data.get("validated_route")
        if validated_route_data:
            player.validated_route = []
            for step_data in validated_route_data:
                dir_name = step_data.get("arrival_dir")
                try:
                    arrival_dir = Direction[dir_name] if dir_name else None
                except KeyError:
                    arrival_dir = None
                player.validated_route.append(RouteStep(
                    coord=tuple(step_data["coord"]),
                    is_goal_node=step_data["is_goal"],
                    arrival_direction=arrival_dir
                ))
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