# mods/economic_mod/economic_mod.py
import pygame
from typing import TYPE_CHECKING, List, Dict, Any, Optional
from collections import Counter

# Since this is a new mod, it needs its own imports
from common.rendering_utils import draw_text
from ..imod import IMod
from .economic_commands import BribeOfficialCommand, PriorityRequisitionCommand

from common import constants as C # Import base constants
from game_logic.ai_actions import PotentialAction
from game_logic.enums import PlayerState
from .economic_commands import PriorityRequisitionCommand, SellToScrapyardCommand
from ui.palette_selection_state import PaletteSelectionState
from . import constants_economic as CE
from .headline_manager import HeadlineManager

if TYPE_CHECKING:
    from game_logic.game import Game
    from game_logic.player import Player, AIPlayer
    from scenes.game_scene import GameScene
    from game_logic.tile import TileType
    from game_logic.ai_strategy import AIStrategy, HardStrategy


# A unique identifier for our special tile's name
REQUISITION_PERMIT_ID = "REQUISITION_PERMIT"

class EconomicMod(IMod):
    """A mod that introduces Capital and market forces to the railway expansion."""

    def on_game_setup(self, game: 'Game'):
        """Initializes Capital and other mod-specific player data."""
        print(f"[{self.name}] Initializing player Capital pools...")
        starting_capital = self.config.get("starting_capital", 50)
        max_capital = self.config.get("max_capital", 200)
        for player in game.players:
            player.components[self.mod_id] = {
                'capital': starting_capital,
                'max_capital': max_capital,
                'sell_mode_active': False # Add a flag for our new mode
            }
        self.headline_manager = HeadlineManager()
        self.headline_manager.event_trigger_threshold = 2

    def on_player_turn_start(self, game: 'Game', player: 'Player'):
        """Called at the very start of a turn to tick the event manager."""
        new_event = self.headline_manager.tick(game)
        if new_event and game.visualizer and game.sounds:
            # You would need to add a sound file like 'headline_news.wav' for this to work
            # game.sounds.play('headline_news')
            pass

    def on_player_turn_end(self, game: 'Game', player: 'Player'):
        """Players regenerate Capital at the end of their turn."""
        if self.mod_id in player.components:
            capital_pool = player.components[self.mod_id]
            regen = self.config.get("capital_regen_per_turn", 5)
            capital_pool['capital'] = min(capital_pool['max_capital'], capital_pool['capital'] + regen)

    def on_hand_tile_clicked(self, game: 'Game', player: 'Player', tile_type: 'TileType') -> bool:
        """Handles special behavior when a hand tile is clicked."""
        player_mod_data = player.components.get(self.mod_id)
        if not player_mod_data:
            return False

        if player_mod_data.get('sell_mode_active', False):
            player_mod_data['sell_mode_active'] = False
            if hasattr(tile_type, 'is_requisition_permit') and tile_type.is_requisition_permit:
                game.visualizer.current_state.message = "Cannot sell a Requisition Permit."
                return True
            base_reward = self.config.get("sell_rewards", {}).get(tile_type.name, self.config.get("sell_rewards", {}).get("default", 0))
            reward = self.headline_manager.get_modified_sell_reward(base_reward)
            command = SellToScrapyardCommand(game, player, self.mod_id, tile_type, reward)
            if game.command_history.execute_command(command):
                game.visualizer.current_state.message = f"Sold {tile_type.name} for ${reward}."
            return True

        if hasattr(tile_type, 'is_requisition_permit') and tile_type.is_requisition_permit:
            if game.visualizer:
                scene = game.visualizer
                def on_tile_selected(chosen_tile: 'TileType'):
                    permit_index = next((i for i, t in enumerate(player.hand) if hasattr(t, 'is_requisition_permit') and t.is_requisition_permit), -1)
                    if permit_index != -1:
                        player.hand.pop(permit_index)
                        player.hand.append(chosen_tile)
                    scene.return_to_base_state()

                scene.request_state_change(
                    lambda v: PaletteSelectionState(v, "Fulfill Requisition", list(game.tile_types.values()), scene.tile_surfaces, on_tile_selected)
                )
            return True
        return False

    def on_draw_ui_panel(self, screen: Any, visualizer: 'GameScene', current_game_state_name: str):
        """Draws the current player's Capital and any active headlines."""
        active_player = visualizer.game.get_active_player()
        if self.mod_id in active_player.components:
            capital_pool = active_player.components[self.mod_id]
            capital_text = f"Capital: ${capital_pool.get('capital', 0)} / ${capital_pool.get('max_capital', 200)}"
            draw_text(screen, capital_text, CE.CAPITAL_DISPLAY_X, CE.CAPITAL_DISPLAY_Y, color=(118, 165, 32), size=20)

        if self.headline_manager.active_event:
            event = self.headline_manager.active_event
            bar_height = 55
            bar_rect = pygame.Rect(0, 0, C.SCREEN_WIDTH, bar_height)
            bar_surface = pygame.Surface(bar_rect.size, pygame.SRCALPHA)
            bar_surface.fill((0, 0, 0, 150))
            screen.blit(bar_surface, bar_rect.topleft)
            draw_text(screen, f"HEADLINE: {event['headline']}", C.SCREEN_WIDTH // 2, 15, C.COLOR_WHITE, size=22, center_x=True)
            draw_text(screen, f"{event['description']} (Rounds Remaining: {self.headline_manager.rounds_remaining})", C.SCREEN_WIDTH // 2, 38, (200, 200, 200), size=18, center_x=True)

    def get_ui_buttons(self, current_game_state_name: str) -> List[Dict[str, Any]]:
        """Adds buttons for all economic actions."""
        buttons = []
        if current_game_state_name == "LayingTrackState":
            base_cost = self.config.get("cost_priority_requisition", 25)
            cost = self.headline_manager.get_modified_requisition_cost(base_cost)
            buttons.append({
                "text": f"Priority Requisition (${cost})",
                "rect": pygame.Rect(CE.BUTTON_X, CE.BUTTON_Y_START, CE.BUTTON_WIDTH, CE.BUTTON_HEIGHT),
                "callback_name": "issue_priority_requisition"
            })
            y_pos_sell = CE.BUTTON_Y_START + CE.BUTTON_HEIGHT + CE.BUTTON_SPACING
            buttons.append({
                "text": "Sell Tile to Scrapyard",
                "rect": pygame.Rect(CE.BUTTON_X, y_pos_sell, CE.BUTTON_WIDTH, CE.BUTTON_HEIGHT),
                "callback_name": "activate_sell_mode"
            })
        return buttons

    def handle_ui_button_click(self, game: 'Game', player: 'Player', button_name: str) -> bool:
        """Handles the logic for the mod's buttons."""
        if button_name == "issue_priority_requisition":
            cost = self.headline_manager.get_modified_requisition_cost(self.config.get("cost_priority_requisition", 25))
            placeholder_tile = game.tile_types.get('Curve')
            if not placeholder_tile: return True
            requisition_permit = placeholder_tile.copy()
            requisition_permit.is_requisition_permit = True
            requisition_permit.name = REQUISITION_PERMIT_ID
            command = PriorityRequisitionCommand(game, player, cost, self.mod_id, requisition_permit)
            game.command_history.execute_command(command)
            return True
        elif button_name == "activate_sell_mode":
            player.components[self.mod_id]['sell_mode_active'] = True
            game.visualizer.current_state.message = "SELL MODE: Click a tile in your hand to sell."
            return True
        return False

    def plan_ai_turn(self, game: 'Game', player: 'AIPlayer', base_strategy: 'AIStrategy') -> Optional[List[PotentialAction]]:
        """
        The Economic Mod's complete takeover of the AI's turn planning.
        It gathers standard actions, adds its own economic actions, and finds the best
        2-action combination from the complete set.
        """
        print(f"  [{self.name} AI] Planning turn for Player {player.player_id}...")
        ideal_plan = base_strategy._calculate_ideal_route(game, player)

        # --- START OF FIX ---
        # 1. Generate and prune target squares using the base strategy's robust logic.
        target_squares = base_strategy._get_high_value_target_squares(game, player, ideal_plan)
        if len(target_squares) > C.MAX_TARGETS_FOR_COMBO_SEARCH:
            target_squares = base_strategy._prune_targets(game, player, target_squares, ideal_plan)

        # 2. Gather standard actions for those specific targets.
        all_actions = base_strategy._gather_standard_actions(game, player, ideal_plan, target_squares)
        # --- END OF FIX ---
        
        # 3. Add this mod's specific economic actions.
        all_actions.extend(self._get_economic_actions(game, player))
        
        if not all_actions:
            print(f"  [{self.name} AI] No possible actions found.")
            return []

        # 4. Separate actions by their cost.
        one_action_moves = [a for a in all_actions if a.action_cost == 1]
        two_action_moves = [a for a in all_actions if a.action_cost == 2]

        # 5. Find the best possible 2-action turn by combining two 1-action moves.
        best_combo_score = -1.0
        best_combo_plan = None
        if len(one_action_moves) >= 2:
            sorted_moves = sorted(one_action_moves, key=lambda a: a.score, reverse=True)
            for i in range(len(sorted_moves)):
                for j in range(i, len(sorted_moves)):
                    action1 = sorted_moves[i]
                    action2 = sorted_moves[j]
                    if not base_strategy._is_combo_compatible(player, action1, action2): continue
                    
                    sim_game = game.copy_for_simulation()
                    sim_player = next(p for p in sim_game.players if p.player_id == player.player_id)
                    base_strategy._apply_potential_action_to_sim(sim_game, sim_player, action1)
                    base_strategy._apply_potential_action_to_sim(sim_game, sim_player, action2)
                    
                    combo_score = base_strategy._score_board_state(sim_game, sim_player) + action1.score + action2.score
                    if combo_score > best_combo_score:
                        best_combo_score = combo_score
                        best_combo_plan = [action1, action2]

        # 6. Find the best possible 2-action turn from a single 2-action move.
        best_single_move_score = -1.0
        best_single_move_plan = None
        if two_action_moves:
            best_2_action_move = max(two_action_moves, key=lambda a: a.score)
            best_single_move_score = best_2_action_move.score
            best_single_move_plan = [best_2_action_move]

        # 7. Compare the best combo against the best single move and decide the turn plan.
        if best_combo_plan and best_combo_score > best_single_move_score:
            print(f"  [{self.name} AI] Chose combo plan with score {best_combo_score:.2f}")
            return best_combo_plan
        elif best_single_move_plan:
            print(f"  [{self.name} AI] Chose single 2-action plan with score {best_single_move_score:.2f}")
            return best_single_move_plan
        
        # 8. Fallback: If no 2-action plan is possible, take the best single action twice.
        if one_action_moves:
            print(f"  [{self.name} AI] No valid 2-action plan. Taking best single action twice.")
            best_single_action = max(one_action_moves, key=lambda a: a.score)
            return [best_single_action, best_single_action]
        
        return []

    def _get_economic_actions(self, game: 'Game', player: 'AIPlayer') -> List[PotentialAction]:
        """Helper to generate just the economic actions for the AI."""
        actions = []
        mod_data = player.components.get(self.mod_id)
        if not mod_data: return []

        current_capital = mod_data.get('capital', 0)
        max_capital = mod_data.get('max_capital', 200)
        urgency_modifier = 1.5 if current_capital < (max_capital * 0.25) else 1.0

        # Selling Tiles (1 Action)
        sell_rewards = self.config.get("sell_rewards", {})
        for tile in player.hand:
            base_reward = sell_rewards.get(tile.name, sell_rewards.get("default", 0))
            reward = self.headline_manager.get_modified_sell_reward(base_reward)
            if current_capital + reward <= max_capital:
                sell_score = 5.0 + (reward * urgency_modifier)
                actions.append(PotentialAction(
                    action_type='sell_tile',
                    details={'tile': tile, 'reward': reward},
                    score=sell_score, score_breakdown={'sell_value': sell_score},
                    command_generator=lambda g, p, t=tile, r=reward: SellToScrapyardCommand(g, p, self.mod_id, t, r),
                    action_cost=1
                ))

        # Priority Requisition (1 Action)
        base_req_cost = self.config.get("cost_priority_requisition", 25)
        req_cost = self.headline_manager.get_modified_requisition_cost(base_req_cost)
        if current_capital >= req_cost and len(player.hand) < game.HAND_TILE_LIMIT:
            req_score = 60.0 - req_cost
            permit_tile = game.tile_types['Curve'].copy()
            permit_tile.is_requisition_permit = True
            permit_tile.name = REQUISITION_PERMIT_ID
            actions.append(PotentialAction(
                action_type='priority_requisition',
                details={'cost': req_cost}, score=req_score,
                command_generator=lambda g, p, c=req_cost, t=permit_tile: PriorityRequisitionCommand(g, p, c, self.mod_id, t),
                action_cost=1
            ))

        # Bribe Official (2 Actions)
        bribe_cost = self.config.get("cost_bribe_official", 80)
        if current_capital >= bribe_cost:
            bribe_reward = self.config.get("reward_influence_from_bribe", 1)
            bribe_score = 50.0
            if player.player_state == PlayerState.DRIVING: bribe_score *= 1.5
            if current_capital == max_capital: bribe_score *= 1.2
            actions.append(PotentialAction(
                action_type='bribe_official',
                details={'cost': bribe_cost, 'reward': bribe_reward}, score=bribe_score,
                command_generator=lambda g, p, c=bribe_cost, r=bribe_reward: BribeOfficialCommand(g, p, c, r, self.mod_id),
                action_cost=2
            ))
            
        return actions