# game_logic/turn_manager.py
from __future__ import annotations
from typing import TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from .game import Game
    
from .player import HumanPlayer
from .enums import GamePhase, PlayerState
from constants import START_NEXT_TURN_EVENT, MAX_PLAYER_ACTIONS, HAND_TILE_LIMIT
from game_states import GameOverState # This import is safe

class TurnManager:
    """
    Manages the flow of turns, including confirmation, advancement,
    and triggering forfeit checks.
    """
    def confirm_turn(self, game: 'Game') -> bool:
        """
        Finalizes a turn, handles all end-game checks, and advances to the
        next valid player.
        """
        active_p = game.get_active_player()
        if game.game_phase == GamePhase.GAME_OVER:
            return False

        # --- Forfeit check for Human Players ---
        if isinstance(active_p, HumanPlayer) and active_p.player_state == PlayerState.LAYING_TRACK:
            if game.actions_taken_this_turn == 0:
                if not game.rule_engine.can_player_make_any_move(game, active_p):
                    # Player has no moves and tried to pass, eliminate them.
                    game.eliminate_player(active_p)
                else:
                    # Player has moves and tried to pass, which is not allowed.
                    print(f"--- Player {active_p.player_id} attempted to pass with valid moves. Turn not confirmed. ---")
                    return False
        
        # Draw tiles for players still laying track
        if active_p.player_state == PlayerState.LAYING_TRACK:
            for _ in range(min(HAND_TILE_LIMIT - len(active_p.hand), MAX_PLAYER_ACTIONS)):
                game.draw_tile(active_p)

        # --- Consolidated End-Game Check ---
        active_players = [p for p in game.players if p.player_state not in [PlayerState.ELIMINATED, PlayerState.FINISHED]]
        
        game_is_over = False
        if len(active_players) == 0:
            print(f"--- All players eliminated! The game is a DRAW. ---")
            game.game_phase = GamePhase.GAME_OVER
            game.winner = None
            game_is_over = True
        elif len(active_players) == 1 and game.num_players > 1:
            last_player = active_players[0]
            if last_player.player_state == PlayerState.DRIVING:
                print(f"--- Last Player Standing! Player {last_player.player_id} was driving and wins! ---")
                game.game_phase = GamePhase.GAME_OVER
                game.winner = last_player
                game_is_over = True
        
        if game_is_over:
            if game.visualizer:
                game.visualizer.request_state_change(GameOverState)
            return True # Stop the turn confirmation process, the game has ended.

        # --- Advance to the next valid player if the game is not over ---
        num_checked = 0
        while num_checked < game.num_players:
            game.active_player_index = (game.active_player_index + 1) % game.num_players
            if game.get_active_player().player_state != PlayerState.ELIMINATED:
                break
            num_checked += 1
        
        if game.active_player_index == 0:
            game.current_turn += 1
            
        game.actions_taken_this_turn = 0
        game.command_history.clear_redo_history()
        
        next_p = game.get_active_player()
        print(f"\n--- Starting Turn {game.current_turn} for Player {next_p.player_id} ({next_p.player_state.name}) ---")

        # Check if the next player has now completed their route
        if next_p.player_state == PlayerState.LAYING_TRACK:
            is_complete, start, path = game.check_player_route_completion(next_p)
            if is_complete and start and path:
                game.handle_route_completion(next_p, start, path)
        
        # Signal the main loop to kick off the next player's turn logic
        pygame.event.post(pygame.event.Event(START_NEXT_TURN_EVENT))
        
        return True