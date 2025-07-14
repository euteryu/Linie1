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
from .economic_commands import PriorityRequisitionCommand, SellToScrapyardCommand, FulfillPermitCommand

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
        starting_capital = self.config.get("starting_capital", 50)
        max_capital = self.config.get("max_capital", 200)
        for player in game.players:
            player.components[self.mod_id] = {
                'capital': starting_capital,
                'max_capital': max_capital,
                'sell_mode_active': False,
                'influence': 0,
                # --- START OF CHANGE: Initialize frozen capital tracker ---
                'frozen_capital': 0
                # --- END OF CHANGE ---
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
            # Button 1: Priority Requisition
            cost = self.config.get("cost_priority_requisition", 35)
            buttons.append({
                "text": f"Buy Permit (${cost})",
                "rect": pygame.Rect(CE.BUTTON_X, CE.BUTTON_Y_START, CE.BUTTON_WIDTH, CE.BUTTON_HEIGHT),
                "callback_name": "issue_priority_requisition"
            })
            
            # Button 2: Sell Tile to Scrapyard
            y_pos2 = CE.BUTTON_Y_START + CE.BUTTON_HEIGHT + CE.BUTTON_SPACING
            buttons.append({
                "text": "Sell Tile to Scrapyard",
                "rect": pygame.Rect(CE.BUTTON_X, y_pos2, CE.BUTTON_WIDTH, CE.BUTTON_HEIGHT),
                "callback_name": "activate_sell_mode"
            })

            # Button 3: Auction a Tile
            y_pos3 = y_pos2 + CE.BUTTON_HEIGHT + CE.BUTTON_SPACING
            buttons.append({
                "text": "Auction a Tile",
                "rect": pygame.Rect(CE.BUTTON_X, y_pos3, CE.BUTTON_WIDTH, CE.BUTTON_HEIGHT),
                "callback_name": "auction_a_tile"
            })

            # Button 4: Open Auction House
            y_pos4 = y_pos3 + CE.BUTTON_HEIGHT + CE.BUTTON_SPACING * 3 # Extra spacing
            buttons.append({
                "text": "Open Auction House",
                "rect": pygame.Rect(CE.BUTTON_X, y_pos4, CE.BUTTON_WIDTH, CE.BUTTON_HEIGHT),
                "callback_name": "open_auction_house"
            })

        return buttons

    def handle_ui_button_click(self, game: 'Game', player: 'Player', button_name: str) -> bool:
        """Handles the logic when the economic buttons are clicked."""
        if button_name == "issue_priority_requisition":
            cost = self.config.get("cost_priority_requisition", 35)
            permit = game.tile_types['Curve'].copy(); permit.is_requisition_permit = True; permit.name = REQUISITION_PERMIT_ID
            command = PriorityRequisitionCommand(game, player, cost, self.mod_id, permit)
            game.command_history.execute_command(command)
            return True
            
        elif button_name == "activate_sell_mode":
            player.components[self.mod_id]['sell_mode_active'] = True
            game.visualizer.current_state.message = "SELL MODE: Click a tile in your hand to sell."
            return True

        elif button_name == "open_auction_house":
            game.visualizer.request_state_change(AuctionHouseState)
            return True

        elif button_name == "auction_a_tile":
            # This requires another transient state to select the tile from hand.
            # We will implement this as a variation of the PaletteSelectionState.
            self._handle_auction_selection(game, player)
            return True

        return False

    def _handle_auction_selection(self, game, player):
        """Opens a palette for the player to choose which tile to auction."""
        scene = game.visualizer
        
        def on_tile_to_auction_selected(tile_to_auction: 'TileType'):
            # Now prompt for the minimum bid
            try:
                bid_str = simpledialog.askstring("Set Minimum Bid", f"Enter minimum bid for {tile_to_auction.name}:", parent=scene.tk_root)
                if not bid_str: return
                min_bid = int(bid_str)
                if min_bid <= 0: return

                command = AuctionTileCommand(game, player, self.mod_id, tile_to_auction, min_bid)
                if not game.command_history.execute_command(command):
                    messagebox.showerror("Error", "Could not auction tile.")
                scene.return_to_base_state()
            except (ValueError, TypeError):
                messagebox.showerror("Error", "Invalid input.")
                scene.return_to_base_state()

        # Request a state change to the palette UI
        scene.request_state_change(
            lambda v: PaletteSelectionState(
                scene=v,
                title="Select Tile to Auction",
                items=player.hand, # Show only tiles in the player's hand
                item_surfaces=scene.tile_surfaces,
                on_select_callback=on_tile_to_auction_selected
            )
        )


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

    def on_hand_tile_clicked(self, game: 'Game', player: 'Player', tile_type: 'TileType') -> bool:
        player_mod_data = player.components.get(self.mod_id)
        if not player_mod_data: return False

        if player_mod_data.get('sell_mode_active', False):
            player_mod_data['sell_mode_active'] = False
            market_price = self.get_market_price(game, tile_type)
            scrapyard_yield = self.config.get("scrapyard_yield", 0.3)
            reward = int(market_price * scrapyard_yield)
            command = SellToScrapyardCommand(game, player, self.mod_id, tile_type, reward)
            if game.command_history.execute_command(command):
                game.visualizer.current_state.message = f"Sold {tile_type.name} for ${reward}."
            return True

        if hasattr(tile_type, 'is_requisition_permit') and tile_type.is_requisition_permit:
            if game.visualizer:
                scene = game.visualizer
                
                def on_tile_selected(chosen_tile: 'TileType'):
                    cost = self.get_market_price(game, chosen_tile)
                    command = FulfillPermitCommand(game, player, self.mod_id, chosen_tile, tile_type, cost)
                    if game.command_history.execute_command(command):
                         scene.return_to_base_state()
                    else:
                        scene.current_state.message = "Could not complete purchase."

                economic_mod = game.mod_manager.available_mods[self.mod_id]
                
                # --- START OF CHANGE: Call PaletteSelectionState with 'scene=v' ---
                scene.request_state_change(
                    lambda v: PaletteSelectionState(
                        scene=v, # Use 'scene' keyword argument
                        title="Foundry Catalog - Select Tile to Purchase",
                        items=list(game.tile_types.values()),
                        item_surfaces=scene.tile_surfaces,
                        on_select_callback=on_tile_selected,
                        economic_mod_instance=economic_mod,
                        current_capital=player_mod_data.get('capital', 0)
                    )
                )
                # --- END OF CHANGE ---
            return True
        return False

    def get_market_price(self, game: 'Game', tile_type: 'TileType') -> int:
        """
        Calculates the dynamic market price of a tile based on its scarcity.
        """
        initial_supply = game.deck_manager.initial_tile_counts.get(tile_type.name, 0)
        if initial_supply == 0:
            # This tile was never supposed to be in the game, return a high price.
            return 999

        current_supply_in_pile = game.deck_manager.tile_draw_pile.count(tile_type)
        
        # Scarcity is based on how many have been REMOVED from the initial pile.
        # This includes tiles on the board and in player hands.
        tiles_removed = initial_supply - current_supply_in_pile
        scarcity_factor = tiles_removed / initial_supply
        
        base_cost = self.config.get("tile_base_cost", {}).get(tile_type.name, 1)
        price_multiplier = self.config.get("price_multiplier", 20)
        
        # Final price is base cost plus a premium based on scarcity.
        market_price = base_cost + (scarcity_factor * price_multiplier)
        
        return int(market_price)