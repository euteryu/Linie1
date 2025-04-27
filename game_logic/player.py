# game_logic/player.py
from typing import List, Dict, Tuple, Optional
from .enums import PlayerState # Use relative import
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
        # self.validated_route: Optional[List[Tuple[int, int]]] = None # REMOVED
        # Renamed for clarity: index into the sequence of required stops/terminals
        self.required_node_index: int = 0
        self.start_terminal_coord: Optional[Tuple[int, int]] = None # Store which terminal they started from

    def __repr__(self) -> str: # ... implementation ...
        route_len = len(self.validated_route) if self.validated_route else 0; return (f"Player {self.player_id} (State: {self.player_state.name}, Hand: {len(self.hand)}, RouteIdx: {self.current_route_target_index}/{route_len})")

    def to_dict(self) -> Dict: # ... implementation ...
        hand_data = [tile.name for tile in self.hand]; line_card_data = self.line_card.line_number if self.line_card else None; # ... rest of implementation ...
        route_card_data = { "stops": self.route_card.stops, "variant": self.route_card.variant_index } if self.route_card else None; # ... rest of implementation ...
        route_path_data = [list(coord) for coord in self.validated_route] if self.validated_route else None; # ... rest of implementation ...
        return {
            "player_id": self.player_id,
            "hand": hand_data,
            "line_card": line_card_data,
            "route_card": route_card_data,
            "player_state": self.player_state.name,
            "streetcar_position": list(self.streetcar_position) if self.streetcar_position else None,
            "required_node_index": self.required_node_index,
            "start_terminal_coord": list(self.start_terminal_coord) if self.start_terminal_coord else None, # ADDED
        }

    @staticmethod
    def from_dict(data: Dict, tile_types: Dict[str, 'TileType']) -> 'Player': # ... implementation ...
        player_id = data.get("player_id", -1); # ... rest of implementation ...
        player = Player(player_id); player.hand = [tile_types[name] for name in data.get("hand", []) if name in tile_types]; # ... rest of implementation ...
        lc_num = data.get("line_card"); player.line_card = LineCard(lc_num) if lc_num is not None else None; # ... rest of implementation ...
        rc_data = data.get("route_card"); # ... rest of implementation ...
        if rc_data and isinstance(rc_data, dict): player.route_card = RouteCard(rc_data.get("stops",[]), rc_data.get("variant", 0))
        try: player.player_state = PlayerState[data.get("player_state", "LAYING_TRACK")]
        except KeyError: player.player_state = PlayerState.LAYING_TRACK
        pos_list = data.get("streetcar_position"); player.streetcar_position = tuple(pos_list) if isinstance(pos_list, list) and len(pos_list) == 2 else None; # ... rest of implementation ...
        route_list = data.get("validated_route")
        player.validated_route = [tuple(coord) for coord in route_list if isinstance(coord, list) and len(coord) == 2] if route_list else None; # ... rest of implementation ...
        player.current_route_target_index = data.get("current_route_target_index", 0)
        # Don't load validated_route
        player.required_node_index = data.get("required_node_index", 0) # Load this
        start_term_list = data.get("start_terminal_coord") # ADDED
        player.start_terminal_coord = tuple(start_term_list) if start_term_list else None # ADDED
        return player
        return player

    def get_required_nodes_sequence(self, game: 'Game') -> Optional[List[Tuple[int, int]]]:
        """Gets the sequence of coordinates the player needs to visit."""
        # print(f"Debug P{self.player_id}: Getting required nodes sequence...") # Debug
        if not self.line_card or not self.route_card: return None
        term1, term2 = game.get_terminal_coords(self.line_card.line_number)
        if not term1 or not term2: return None

        stop_coords = []
        # print(f"Debug P{self.player_id}: Required stops IDs: {self.route_card.stops}") # Debug
        for stop_id in self.route_card.stops:
            coord = game.board.building_stop_locations.get(stop_id)
            if coord is None:
                 # print(f"Debug P{self.player_id}: Stop {stop_id} location not found.") # Debug
                 return None # Required stop not placed yet
            stop_coords.append(coord)
        # print(f"Debug P{self.player_id}: Found stop coords: {stop_coords}") # Debug

        # --- Determine Start/End ---
        # Use the stored start terminal if available (implementing your suggestion)
        start_node = getattr(self, 'start_terminal_coord', None) # Check if attribute exists
        end_node = None
        if start_node == term1: end_node = term2
        elif start_node == term2: end_node = term1
        else:
            # Fallback if start_terminal_coord wasn't set (e.g., loading old save)
            # Default to term1 as start - this might be wrong!
            print(f"Warning P{self.player_id}: start_terminal_coord not set. Defaulting sequence start.")
            start_node = term1
            end_node = term2

        sequence = [start_node] + stop_coords + [end_node]
        # print(f"Debug P{self.player_id}: Final sequence: {sequence}") # Debug
        return sequence

    def get_next_target_node(self, game: 'Game') -> Optional[Tuple[int, int]]:
        """Gets the coordinate of the next node in the required sequence."""
        sequence = self.get_required_nodes_sequence(game)
        if not sequence:
            # print(f"Debug P{self.player_id}: Cannot get sequence for next target.") # Debug
            return None
        # The target node is the one *after* the current index in the sequence
        # Index 0 = Start Term, Index 1 = Stop 1, Index 2 = Stop 2 (if exists), etc.
        # required_node_index: 0 means aiming for stop1 (at sequence[1])
        # required_node_index: 1 means aiming for stop2 (at sequence[2]) or end_term
        target_list_index = self.required_node_index + 1

        # print(f"Debug P{self.player_id}: Current node index {self.required_node_index}, aiming for list index {target_list_index}") # Debug

        if target_list_index < len(sequence):
             target_node = sequence[target_list_index]
             # print(f"Debug P{self.player_id}: Next target node: {target_node}") # Debug
             return target_node
        else:
            # print(f"Debug P{self.player_id}: Already past last required node.") # Debug
            return None # Already passed the last required node (end terminal)