# game_logic/rule_engine.py
'''RuleEngine: This class is now a "service" that purely contains logic.
It doesn't store any data (self.board, etc.).
Instead, it receives the game object in its methods and operates on it.
This makes the rules testable in isolation.'''

from __future__ import annotations
from typing import TYPE_CHECKING, Tuple, List, Dict, Optional

if TYPE_CHECKING:
    from .game import Game
    from .player import Player
    from .tile import TileType

from .enums import Direction, GamePhase, PlayerState

class RuleEngine:
    """
    A stateless service that contains all the core validation logic for the game.
    It operates on a given game state but does not hold state itself.
    """
    def check_placement_validity(self, game: 'Game', tile_type: 'TileType', orientation: int, r: int, c: int, hypothetical_moves: Optional[List[Dict]] = None) -> Tuple[bool, str]:
        """A definitive validation function that can check against a hypothetical future board state."""
        if not game.board.is_playable_coordinate(r, c) or game.board.get_tile(r, c) or game.board.get_building_at(r, c):
            return False, "Target square is not empty and playable on the real board."

        new_connections = game.get_effective_connections(tile_type, orientation)

        for direction in Direction:
            has_outgoing_track = any(direction.name in exits for exits in new_connections.values())
            nr, nc = r + direction.value[0], c + direction.value[1]
            
            neighbor_tile = game._get_hypothetical_tile(nr, nc, hypothetical_moves)
            
            if neighbor_tile:
                neighbor_connections = game.get_effective_connections(neighbor_tile.tile_type, neighbor_tile.orientation)
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
        """A definitive validation for exchanging a tile that can check against a hypothetical future board state."""
        old_tile = game.board.get_tile(r, c)
        if not old_tile: return False, "No tile to exchange on real board."
        if not old_tile.tile_type.is_swappable: return False, "Tile is not swappable."
        if old_tile.has_stop_sign: return False, "Cannot exchange a Stop Sign tile."
        if old_tile.is_terminal: return False, "Cannot exchange a Terminal tile."
        if new_tile_type not in player.hand: return False, "Player does not have tile in hand."
        if old_tile.tile_type == new_tile_type: return False, "Cannot replace a tile with the same type."

        old_conns = game.get_effective_connections(old_tile.tile_type, old_tile.orientation)
        new_conns = game.get_effective_connections(new_tile_type, new_orientation)
        
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
                
                neighbor_tile = game._get_hypothetical_tile(nr, nc, hypothetical_moves)
                
                if neighbor_tile:
                    neighbor_conns = game.get_effective_connections(neighbor_tile.tile_type, neighbor_tile.orientation)
                    required_neighbor_exit = Direction.opposite(exit_dir_enum).name
                    if not any(required_neighbor_exit in exits for exits in neighbor_conns.values()):
                        return False, f"New connection to ({nr},{nc}) invalid; neighbor does not connect back."
                else:
                    if not game.board.is_playable_coordinate(nr, nc): return False, f"New connection points into a wall at ({nr},{nc})."
                    if game.board.get_building_at(nr, nc): return False, f"New connection points into a building at ({nr},{nc})."

        return True, "Exchange is valid."

    def check_win_condition(self, game: 'Game', player: 'Player') -> bool:
        """Checks if a player has met the driving-based win condition."""
        if player.player_state != PlayerState.DRIVING: return False
        if not player.streetcar_position or not player.line_card: return False
        
        full_sequence = player.get_full_driving_sequence(game)
        if not full_sequence: return False
        
        if player.required_node_index >= len(full_sequence):
            if player.streetcar_position == full_sequence[-1]:
                print(f"WIN CONDITION MET for Player {player.player_id}!")
                game.game_phase = GamePhase.GAME_OVER
                game.winner = player
                player.player_state = PlayerState.FINISHED
                return True
        return False

    def check_elimination_win_condition(self, game: 'Game'):
        """
        Checks for a win condition after a player is eliminated.
        A "last player standing" win is only granted if that player is
        already in the DRIVING phase.
        """
        active_players = [p for p in game.players if p.player_state not in [PlayerState.ELIMINATED, PlayerState.FINISHED]]
        
        if len(active_players) == 1 and game.num_players > 1:
            last_player = active_players[0]
            if last_player.player_state == PlayerState.DRIVING:
                print(f"--- Last Player Standing! Player {last_player.player_id} was driving and wins by default! ---")
                game.game_phase = GamePhase.GAME_OVER
                game.winner = last_player
                last_player.player_state = PlayerState.FINISHED
            else:
                print(f"--- Last Player Standing (Player {last_player.player_id}) is also stuck. The game is a DRAW! ---")
                game.game_phase = GamePhase.GAME_OVER
                game.winner = None
                last_player.player_state = PlayerState.ELIMINATED

        elif len(active_players) == 0:
            print(f"--- All players have been eliminated! The game is a DRAW. ---")
            game.game_phase = GamePhase.GAME_OVER
            game.winner = None

    def can_player_make_any_move(self, game: 'Game', player: 'Player') -> bool:
        """
        Performs an exhaustive check to see if a player has any possible legal move.
        """
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