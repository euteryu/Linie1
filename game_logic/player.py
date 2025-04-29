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
        # Renamed for clarity: index into the sequence of required stops/terminals
        self.required_node_index: int = 0
        self.start_terminal_coord: Optional[Tuple[int, int]] = None
        self.arrival_direction: Optional[Direction] = None # Direction used to ENTER current streetcar_position

    def __repr__(self) -> str:
        # Removed reference to validated_route length
        # Added required_node_index for debugging info
        num_stops = 0
        if self.route_card and self.route_card.stops:
             num_stops = len(self.route_card.stops)

        # Target node index progresses from 0 (aiming for stop 1) up to num_stops (aiming for end terminal)
        # So total number of "targets" is num_stops + 1
        total_targets = num_stops + 1

        return (f"Player(id={self.player_id}, " # Use keyword args style for clarity
                f"State={self.player_state.name}, "
                f"Hand={len(self.hand)}, "
                # Show progress through required nodes
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
            # "validated_route": route_path_data, # <-- REMOVE or COMMENT OUT
            "required_node_index": self.required_node_index, # Keep this
            # Save arrival_direction if needed for loading mid-move? Maybe not necessary.
            # "arrival_direction": self.arrival_direction.name if self.arrival_direction else None,
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
        
        player.required_node_index = data.get("required_node_index", 0)
        # Load arrival direction if saved? Default to None otherwise.
        # arrival_str = data.get("arrival_direction")
        # player.arrival_direction = Direction[arrival_str] if arrival_str else None
        player.arrival_direction = None # Safer to reset on load
        return player

    def get_required_nodes_sequence(self, game: 'Game', is_driving_check: bool = False) -> Optional[List[Tuple[int, int]]]:
        """
        Gets the sequence of coordinates the player needs to visit.
        is_driving_check: If True, requires start_terminal_coord to be set.
                          If False (default), assumes nominal sequence for checking.
        """
        if not self.line_card or not self.route_card: 
            return None

        term1_coord, term2_coord = game.get_terminal_coords(self.line_card.line_number)
        if not term1_coord or not term2_coord:
            print(f"Error P{self.player_id}: Cannot get terminal coords for Line {self.line_card.line_number}")
            return None

        stop_coords = []
        # print(f"Debug P{self.player_id}: Required stops IDs: {self.route_card.stops}") # Debug
        for stop_id in self.route_card.stops:
            coord = game.board.building_stop_locations.get(stop_id)
            if coord is None:
                # print(f"Debug P{self.player_id}: Stop {stop_id} location not found.") # Debug
                return None # Required stop not placed yet
            stop_coords.append(coord)
        # print(f"Debug P{self.player_id}: Found stop coords: {stop_coords}") # Debug

        start_node: Optional[Tuple[int, int]] = None
        end_node: Optional[Tuple[int, int]] = None

        # If driving, the stored start terminal dictates the sequence
        # Use the is_driving_check flag passed in (or its default)
        if is_driving_check:
            if self.start_terminal_coord:
                start_node = self.start_terminal_coord
                end_node = term2_coord if start_node == term1_coord else term1_coord
            else:
                 # This is an error state if we expected driving check but start isn't set
                 print(f"ERROR P{self.player_id}: Driving check requested but start_terminal_coord not set!")
                 return None
        else: # Not a driving check (is_driving_check is False - the default)
             # Assume nominal sequence (term1 -> term2) for pre-drive completion check
             start_node = term1_coord
             end_node = term2_coord


        if start_node is None or end_node is None:
             # This path indicates an error in logic above
             print(f"ERROR P{self.player_id}: Failed to determine start/end nodes even with default.")
             return None

        sequence = [start_node] + stop_coords + [end_node]
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