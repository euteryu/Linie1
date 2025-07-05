# game_logic/rule_engine.py
from __future__ import annotations
from typing import TYPE_CHECKING, Tuple, List, Dict, Optional
import copy

if TYPE_CHECKING:
    from .game import Game
    from .player import Player
    from .tile import TileType, PlacedTile

from .enums import Direction, GamePhase, PlayerState
from game_states import GameOverState

class RuleEngine:
    """A stateless service that contains all the core validation logic for the game."""
    
    def _rotate_direction(self, direction: str, angle: int) -> str:
        directions = ['N', 'E', 'S', 'W']
        current_index = directions.index(direction)
        steps = (angle % 360) // 90
        return directions[(current_index + steps) % 4]

    def get_effective_connections(self, tile_type: 'TileType', orientation: int) -> Dict[str, List[str]]:
        if orientation == 0:
            return copy.deepcopy(tile_type.connections_base)
        rotated_connections: Dict[str, List[str]] = {'N': [], 'E': [], 'S': [], 'W': []}
        for base_entry, base_exits in tile_type.connections_base.items():
            actual_entry = self._rotate_direction(base_entry, orientation)
            rotated_connections[actual_entry] = [self._rotate_direction(ex, orientation) for ex in base_exits]
            rotated_connections[actual_entry].sort()
        return rotated_connections

    def _get_hypothetical_tile(self, game: 'Game', r: int, c: int, hypothetical_moves: Optional[List[Dict]] = None) -> Optional['PlacedTile']:
        from .tile import PlacedTile
        if hypothetical_moves:
            for move in hypothetical_moves:
                if move['coord'] == (r, c):
                    return PlacedTile(move['tile_type'], move['orientation'])
        return game.board.get_tile(r, c)

    def check_placement_validity(self, game: 'Game', tile_type: 'TileType', orientation: int, r: int, c: int, hypothetical_moves: Optional[List[Dict]] = None) -> Tuple[bool, str]:
        if not game.board.is_playable_coordinate(r, c) or game.board.get_tile(r, c) or game.board.get_building_at(r, c):
            return False, "Target square is not empty and playable on the real board."

        # --- START OF FIX ---
        # Call the method on 'self' (the RuleEngine instance), not on 'game'.
        new_connections = self.get_effective_connections(tile_type, orientation)
        # --- END OF FIX ---

        for direction in Direction:
            has_outgoing_track = any(direction.name in exits for exits in new_connections.values())
            nr, nc = r + direction.value[0], c + direction.value[1]
            
            neighbor_tile = self._get_hypothetical_tile(game, nr, nc, hypothetical_moves)
            
            if neighbor_tile:
                # --- START OF FIX ---
                neighbor_connections = self.get_effective_connections(neighbor_tile.tile_type, neighbor_tile.orientation)
                # --- END OF FIX ---
                required_neighbor_exit = Direction.opposite(direction).name
                neighbor_has_incoming_track = any(required_neighbor_exit in exits for exits in neighbor_connections.values())
                
                if has_outgoing_track != neighbor_has_incoming_track:
                    return False, f"Connection mismatch with tile at ({nr},{nc})."
            else:
                if has_outgoing_track:
                    if not game.board.is_playable_coordinate(nr, nc):
                        return False, f"Track points into a wall at ({nr},{nc})."
                    if game.board.get_building_at(nr, nc):
                        return False, f"Track points into a building at ({nr},{nc})."
        
        return True, "Placement is valid."
    
    def check_exchange_validity(self, game: 'Game', player: 'Player', new_tile_type: 'TileType', new_orientation: int, r: int, c: int, hypothetical_moves: Optional[List[Dict]] = None) -> Tuple[bool, str]:
        old_tile = game.board.get_tile(r, c)
        if not old_tile or not old_tile.tile_type.is_swappable or old_tile.has_stop_sign or old_tile.is_terminal:
            return False, "Tile is not exchangeable."
        if new_tile_type not in player.hand: return False, "Player does not have tile."
        if old_tile.tile_type == new_tile_type: return False, "Cannot replace with same type."

        # --- START OF FIX ---
        old_conns = self.get_effective_connections(old_tile.tile_type, old_tile.orientation)
        new_conns = self.get_effective_connections(new_tile_type, new_orientation)
        # --- END OF FIX ---
        
        def get_connection_set(conn_map: Dict[str, List[str]]) -> set:
            return {frozenset([entry, exit]) for entry, exits in conn_map.items() for exit in exits}

        if not get_connection_set(old_conns).issubset(get_connection_set(new_conns)):
            return False, "Connection Preservation Failed."

        added_connections = get_connection_set(new_conns) - get_connection_set(old_conns)
        for conn_pair in added_connections:
            dir1_str, dir2_str = list(conn_pair)
            for exit_dir_str in [dir1_str, dir2_str]:
                exit_dir_enum = Direction.from_str(exit_dir_str)
                nr, nc = r + exit_dir_enum.value[0], c + exit_dir_enum.value[1]
                
                neighbor_tile = self._get_hypothetical_tile(game, nr, nc, hypothetical_moves)
                
                if neighbor_tile:
                    # --- START OF FIX ---
                    neighbor_conns = self.get_effective_connections(neighbor_tile.tile_type, neighbor_tile.orientation)
                    # --- END OF FIX ---
                    required_neighbor_exit = Direction.opposite(exit_dir_enum).name
                    if not any(required_neighbor_exit in exits for exits in neighbor_conns.values()):
                        return False, f"New connection to ({nr},{nc}) invalid."
                else:
                    if not game.board.is_playable_coordinate(nr, nc): return False, f"New connection to wall at ({nr},{nc})."
                    if game.board.get_building_at(nr, nc): return False, f"New connection to building at ({nr},{nc})."

        return True, "Exchange is valid."

    def check_win_condition(self, game: 'Game', player: 'Player') -> bool:
        if player.player_state != PlayerState.DRIVING or not player.streetcar_position or not player.line_card:
            return False
        
        full_sequence = player.get_full_driving_sequence(game)
        if not full_sequence: return False
        
        if player.required_node_index >= len(full_sequence) and player.streetcar_position == full_sequence[-1]:
            print(f"WIN CONDITION MET for Player {player.player_id}!")
            game.game_phase = GamePhase.GAME_OVER
            game.winner = player
            player.player_state = PlayerState.FINISHED
            
            if game.visualizer:
                game.visualizer.request_state_change(GameOverState)
            return True
        return False

    def check_and_place_stop_sign(self, game: 'Game', placed_tile: 'PlacedTile', row: int, col: int):
        """
        Checks if a newly placed tile creates a stop sign for an adjacent
        building and updates the board state if it does.
        """
        if game.board.get_tile(row, col) != placed_tile:
            return

        def has_ns_straight(conns): return 'S' in conns.get('N', [])
        def has_ew_straight(conns): return 'W' in conns.get('E', [])

        tile_connections = self.get_effective_connections(placed_tile.tile_type, placed_tile.orientation)

        for direction in Direction:
            dr, dc = direction.value
            nr, nc = row + dr, col + dc
            if not game.board.is_valid_coordinate(nr, nc):
                continue
            
            building_id = game.board.get_building_at(nr, nc)
            if building_id and building_id not in game.board.buildings_with_stops:
                is_parallel = False
                if direction in [Direction.N, Direction.S] and has_ew_straight(tile_connections):
                    is_parallel = True
                if direction in [Direction.E, Direction.W] and has_ns_straight(tile_connections):
                    is_parallel = True
                
                if is_parallel:
                    placed_tile.has_stop_sign = True
                    game.board.buildings_with_stops.add(building_id)
                    game.board.building_stop_locations[building_id] = (row, col)
                    print(f"--> Placed stop sign at ({row},{col}) for Building {building_id}.")
                    break # A tile can only create one stop sign

    def is_valid_stop_entry(self, game: 'Game', stop_coord: Tuple[int, int], entry_direction: Direction) -> bool:
        """
        Checks if a tram arriving at a stop tile is doing so on the correct
        (parallel) track segment.
        """
        placed_tile = game.board.get_tile(stop_coord[0], stop_coord[1])
        if not placed_tile or not placed_tile.has_stop_sign:
            return False

        def has_ns_straight(conns): return 'S' in conns.get('N', [])
        def has_ew_straight(conns): return 'W' in conns.get('E', [])
        
        tile_conns = self.get_effective_connections(placed_tile.tile_type, placed_tile.orientation)
        
        # Find the building associated with this stop
        building_id = next((bid for bid, bcoord in game.board.building_stop_locations.items() if bcoord == stop_coord), None)
        if not building_id: return False
        
        building_pos = game.board.building_coords.get(building_id)
        if not building_pos: return False

        # If the building is North/South of the stop tile, the track must be East/West
        is_building_ns = building_pos[1] == stop_coord[1]
        if is_building_ns:
            return has_ew_straight(tile_conns) and entry_direction in [Direction.E, Direction.W]
        else: # Building is East/West, so track must be North/South
            return has_ns_straight(tile_conns) and entry_direction in [Direction.N, Direction.S]

    def can_player_make_any_move(self, game: 'Game', player: 'Player') -> bool:
        """Performs an exhaustive check to see if a player has any possible legal move."""
        print(f"--- Performing exhaustive move check for Player {player.player_id}... ---")
        for tile in set(player.hand):
            for r in range(game.board.rows):
                for c in range(game.board.cols):
                    for o in [0, 90, 180, 270]:
                        if self.check_placement_validity(game, tile, o, r, c)[0]:
                            print(f"  (Found possible move: Place {tile.name} at ({r},{c}))")
                            return True
                        if self.check_exchange_validity(game, player, tile, o, r, c)[0]:
                            print(f"  (Found possible move: Exchange for {tile.name} at ({r},{c}))")
                            return True
        print("  (No possible moves found for this player.)")
        return False