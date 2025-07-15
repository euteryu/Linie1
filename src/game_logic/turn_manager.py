# game_logic/turn_manager.py
from __future__ import annotations
from typing import TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from .game import Game
    
from .player import HumanPlayer, AIPlayer
from .enums import GamePhase, PlayerState
from common.constants import START_NEXT_TURN_EVENT, MAX_PLAYER_ACTIONS, HAND_TILE_LIMIT
from states.game_states import GameOverState

class TurnManager:
    """
    Manages the flow of turns, including confirmation, advancement,
    and triggering forfeit checks.
    """
    def confirm_turn(self, game: 'Game') -> bool:
        """
        Finalizes a turn, resolves auctions, draws tiles, and advances to the next player.
        """
        active_p = game.get_active_player()
        if game.game_phase == GamePhase.GAME_OVER: return False
        
        # --- START OF CHANGE: Resolve auctions at the START of the next turn ---
        # This means an auction listed by Player 1 resolves when Player 1 starts their *next* turn.
        game.resolve_auctions_for_player(active_p)
        # --- END OF CHANGE ---

        if isinstance(active_p, HumanPlayer) and active_p.player_state == PlayerState.LAYING_TRACK:
            if game.actions_taken_this_turn < game.MAX_PLAYER_ACTIONS:
                if game.rule_engine.can_player_make_any_move(game, active_p):
                    if game.visualizer: game.visualizer.current_state.message = f"You must take {game.MAX_PLAYER_ACTIONS} actions to end your turn."
                    return False
                else:
                    game.eliminate_player(active_p)
                    if game.visualizer and game.sounds: game.sounds.play('eliminated')
        
        if active_p.player_state == PlayerState.LAYING_TRACK:
            tiles_to_draw = HAND_TILE_LIMIT - len(active_p.hand)
            if tiles_to_draw > 0:
                for _ in range(tiles_to_draw): game.deck_manager.draw_tile(active_p)
        
        active_players = [p for p in game.players if p.player_state not in [PlayerState.ELIMINATED, PlayerState.FINISHED]]
        
        game_is_over = False
        if not active_players: game.game_phase = GamePhase.GAME_OVER; game.winner = None; game_is_over = True
        elif len(active_players) == 1 and game.num_players > 1:
            if active_players[0].player_state == PlayerState.DRIVING: game.game_phase = GamePhase.GAME_OVER; game.winner = active_players[0]; game_is_over = True
        
        if game_is_over:
            if game.visualizer: game.visualizer.request_state_change(GameOverState)
            return True

        original_player_index = game.active_player_index
        for _ in range(game.num_players):
            game.active_player_index = (game.active_player_index + 1) % game.num_players
            if game.get_active_player().player_state not in [PlayerState.ELIMINATED, PlayerState.FINISHED]: break
        
        if game.active_player_index <= original_player_index: game.current_turn += 1
            
        game.actions_taken_this_turn = 0; game.command_history.clear_redo_history(); game.turn_start_history_index = game.command_history.get_current_index()
        next_p = game.get_active_player()
        print(f"\n--- Starting Turn {game.current_turn} for Player {next_p.player_id} ({next_p.player_state.name}) ---")

        game.mod_manager.on_player_turn_start(game, next_p)

        # If the player was eliminated by the hook, their state will be updated.
        if next_p.player_state == PlayerState.ELIMINATED:
            # The elimination itself would have posted a next turn event, so we can just stop.
            return True

        if next_p.player_state == PlayerState.LAYING_TRACK:
            is_complete, start, path = game.check_player_route_completion(next_p)
            if is_complete and start and path:
                game.handle_route_completion(next_p, start, path)
        
        if next_p.is_ai: # Use the property here to be safe
             pygame.event.post(pygame.event.Event(START_NEXT_TURN_EVENT))

        return True