# game_logic/turn_manager.py
from __future__ import annotations
from typing import TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from .game import Game
    
from .player import HumanPlayer, AIPlayer
from .enums import GamePhase, PlayerState
from common.constants import START_NEXT_TURN_EVENT, MAX_PLAYER_ACTIONS, HAND_TILE_LIMIT
from states.game_states import GameOverState # This import is safe

class TurnManager:
    """
    Manages the flow of turns, including confirmation, advancement,
    and triggering forfeit checks.
    """
    def confirm_turn(self, game: 'Game') -> bool:
        """
        Finalizes a turn by checking for forfeits, drawing new tiles,
        advancing the player index, and checking for win/draw conditions.
        Returns True if the turn was successfully confirmed, False otherwise.
        """
        active_p = game.get_active_player()
        if game.game_phase == GamePhase.GAME_OVER:
            return False

        # --- Forfeit/End Turn Check for Human Players ---
        if isinstance(active_p, HumanPlayer) and active_p.player_state == PlayerState.LAYING_TRACK:
            # --- START OF FIX ---
            # A human player cannot end their turn unless they have used all their actions,
            # OR they have no possible moves left (which leads to elimination).
            if game.actions_taken_this_turn < game.MAX_PLAYER_ACTIONS:
                if game.rule_engine.can_player_make_any_move(game, active_p):
                    # Player has moves left and tried to pass, which is not allowed.
                    print(f"--- Player {active_p.player_id} attempted to end turn with only {game.actions_taken_this_turn}/{game.MAX_PLAYER_ACTIONS} actions. Turn not confirmed. ---")
                    # We need to set a message on the UI for the player
                    if game.visualizer:
                        game.visualizer.current_state.message = f"You must take {game.MAX_PLAYER_ACTIONS} actions to end your turn."
                    return False
                else:
                    # Player has no more moves and is trying to pass. This is a valid forfeit.
                    game.eliminate_player(active_p)
                    if game.visualizer and game.sounds:
                        game.sounds.play('eliminated')
            # --- END OF FIX ---
        
        # --- Draw Tiles for Players still in Laying Track Phase ---
        if active_p.player_state == PlayerState.LAYING_TRACK:
            num_to_draw = min(HAND_TILE_LIMIT - len(active_p.hand), game.actions_taken_this_turn)
            for _ in range(num_to_draw):
                # --- START OF FIX ---
                # Call the method on the deck_manager, not the game object.
                game.deck_manager.draw_tile(active_p)
                # --- END OF FIX ---

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
            return True

        # --- Advance to the next valid player ---
        num_checked = 0
        original_player_index = game.active_player_index
        while num_checked < game.num_players:
            game.active_player_index = (game.active_player_index + 1) % game.num_players
            if game.get_active_player().player_state not in [PlayerState.ELIMINATED, PlayerState.FINISHED]:
                break
            num_checked += 1
        
        if game.active_player_index <= original_player_index:
            game.current_turn += 1
            
        game.actions_taken_this_turn = 0
        game.command_history.clear_redo_history()
        game.turn_start_history_index = game.command_history.get_current_index()
        
        next_p = game.get_active_player()
        print(f"\n--- Starting Turn {game.current_turn} for Player {next_p.player_id} ({next_p.player_state.name}) ---")

        if next_p.player_state == PlayerState.LAYING_TRACK:
            is_complete, start, path = game.check_player_route_completion(next_p)
            if is_complete and start and path:
                print(f"  Player {next_p.player_id} completed their route!")
                game.handle_route_completion(next_p, start, path)
        
        if isinstance(next_p, AIPlayer):
             pygame.event.post(pygame.event.Event(START_NEXT_TURN_EVENT))
        
        return True