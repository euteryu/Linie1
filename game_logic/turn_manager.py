# game_logic/turn_manager.py
from __future__ import annotations
from typing import TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from .game import Game
    
from .player import HumanPlayer
from .enums import GamePhase, PlayerState
from constants import START_NEXT_TURN_EVENT, MAX_PLAYER_ACTIONS, HAND_TILE_LIMIT

class TurnManager:
    """
    Manages the flow of turns, including confirmation, advancement,
    and triggering forfeit checks.
    """
    def confirm_turn(self, game: 'Game') -> bool:
        """
        Finalizes a turn. Also checks for game-ending conditions related to
        player elimination.
        """
        active_p = game.get_active_player()
        if game.game_phase == GamePhase.GAME_OVER: return False

        # --- Forfeit check for Human Players ---
        if isinstance(active_p, HumanPlayer) and active_p.player_state == PlayerState.LAYING_TRACK:
            if game.actions_taken_this_turn == 0:
                if game.rule_engine.can_player_make_any_move(game, active_p):
                    print(f"--- Player {active_p.player_id} attempted to pass with valid moves. Turn not confirmed. ---")
                    return False
                else:
                    game.eliminate_player(active_p)
                    # If the game just ended, stop here.
                    if game.game_phase == GamePhase.GAME_OVER: return True

        # Draw tiles for players who are still laying track
        if active_p.player_state == PlayerState.LAYING_TRACK:
            for _ in range(min(HAND_TILE_LIMIT - len(active_p.hand), MAX_PLAYER_ACTIONS)):
                game.draw_tile(active_p)

        # After the current player's turn is fully resolved, check for elimination win.
        game.rule_engine.check_elimination_win_condition(game)
        if game.game_phase == GamePhase.GAME_OVER:
            return True

        # --- Advance to the next non-eliminated player ---
        num_checked = 0
        while num_checked < game.num_players:
            game.active_player_index = (game.active_player_index + 1) % game.num_players
            if game.get_active_player().player_state != PlayerState.ELIMINATED:
                break
            num_checked += 1
        
        if game.active_player_index == 0: game.current_turn += 1
        game.actions_taken_this_turn = 0
        game.command_history.clear_redo_history()
        
        next_p = game.get_active_player()
        print(f"\n--- Starting Turn {game.current_turn} for Player {next_p.player_id} ({next_p.player_state.name}) ---")

        if next_p.player_state == PlayerState.LAYING_TRACK:
            is_complete, start, path = game.check_player_route_completion(next_p)
            if is_complete and start and path:
                game.handle_route_completion(next_p, start, path)
        
        pygame.event.post(pygame.event.Event(START_NEXT_TURN_EVENT))
        
        return True