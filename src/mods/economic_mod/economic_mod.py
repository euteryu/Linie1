# mods/economic_mod/economic_mod.py
import pygame
from typing import TYPE_CHECKING, List, Dict, Any, Optional
from collections import Counter

from tkinter import simpledialog, messagebox

# Since this is a new mod, it needs its own imports
from common.rendering_utils import draw_text
from ..imod import IMod
from .economic_commands import BribeOfficialCommand, PriorityRequisitionCommand

from common import constants as C # Import base constants
from game_logic.ai_actions import PotentialAction
from game_logic.enums import PlayerState

from ui.palette_selection_state import PaletteSelectionState
from . import constants_economic as CE
from .headline_manager import HeadlineManager

from .economic_commands import PriorityRequisitionCommand, SellToScrapyardCommand, FulfillPermitCommand, AuctionTileCommand, PlaceBidCommand
from states.game_states import AuctionHouseState

if TYPE_CHECKING:
    from game_logic.game import Game
    from game_logic.player import Player, AIPlayer
    from scenes.game_scene import GameScene
    from game_logic.tile import TileType
    from game_logic.ai_strategy import AIStrategy, HardStrategy


# A unique identifier for our special tile's name
REQUISITION_PERMIT_ID = "REQUISITION_PERMIT"

def _ai_wants_to_use_influence(game, player) -> bool:
    """Helper logic to determine if an AI should spend an Influence point."""
    if not player.validated_route: return False
    
    # Find the next required goal in the validated path
    try:
        full_sequence = player.get_full_driving_sequence(game)
        if not full_sequence or player.required_node_index >= len(full_sequence):
            return False # Already at the end or no path
            
        next_goal_coord = full_sequence[player.required_node_index]
        next_goal_path_index = next(i for i, step in enumerate(player.validated_route) if i > player.streetcar_path_index and step.coord == next_goal_coord)
        
        dist_to_goal = next_goal_path_index - player.streetcar_path_index
        
        # Use influence if the goal is just out of reach of a 4-sided die roll
        if 0 < dist_to_goal <= 4:
            return True
            
    except (StopIteration, IndexError):
        return False # Could not find the next goal
        
    return False

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
        scene = game.visualizer
        player_mod_data = player.components.get(self.mod_id, {})
        def on_tile_to_auction_selected(tile_to_auction: 'TileType'):
            try:
                bid_str = simpledialog.askstring("Set Minimum Bid", f"Enter minimum bid for {tile_to_auction.name}:", parent=scene.tk_root)
                if not bid_str: scene.return_to_base_state(); return
                min_bid = int(bid_str)
                if min_bid <= 0: messagebox.showerror("Error", "Minimum bid must be a positive number."); scene.return_to_base_state(); return
                command = AuctionTileCommand(game, player, self.mod_id, tile_to_auction, min_bid)
                if not game.command_history.execute_command(command): messagebox.showerror("Error", "Could not auction tile.")
                scene.return_to_base_state()
            except (ValueError, TypeError):
                messagebox.showerror("Error", "Invalid input. Please enter a number.")
                scene.return_to_base_state()

        economic_mod = game.mod_manager.available_mods[self.mod_id]
        scene.request_state_change(
            lambda v: PaletteSelectionState(scene=v, title="Select Tile from Your Hand to Auction", items=player.hand, item_surfaces=scene.tile_surfaces, on_select_callback=on_tile_to_auction_selected, economic_mod_instance=economic_mod, current_capital=player_mod_data.get('capital', 0))
        )


    def plan_ai_turn(self, game: 'Game', player: 'AIPlayer', base_strategy: 'AIStrategy') -> Optional[List[PotentialAction]]:
        """The Economic Mod's complete AI planning override."""
        print(f"  [{self.name} AI] Planning turn for Player {player.player_id}...")
        ideal_plan = base_strategy._calculate_ideal_route(game, player)
        target_squares = base_strategy._get_high_value_target_squares(game, player, ideal_plan)
        if len(target_squares) > C.MAX_TARGETS_FOR_COMBO_SEARCH:
            target_squares = base_strategy._prune_targets(game, player, target_squares, ideal_plan)

        # 1. Gather all possible actions: standard and economic
        all_actions = base_strategy._gather_standard_actions(game, player, ideal_plan, target_squares)
        all_actions.extend(self._get_economic_actions(game, player, ideal_plan))
        
        if not all_actions: return []

        # 2. Separate actions by cost
        one_action_moves = [a for a in all_actions if a.action_cost == 1]
        two_action_moves = [a for a in all_actions if a.action_cost == 2]

        # 3. Find the best possible 2-action turn by combining two 1-action moves
        best_combo_score = -1.0; best_combo_plan = None
        if len(one_action_moves) >= 2:
            sorted_moves = sorted(one_action_moves, key=lambda a: a.score, reverse=True)[:10] # Prune to top 10
            for i in range(len(sorted_moves)):
                for j in range(i + 1, len(sorted_moves)):
                    action1, action2 = sorted_moves[i], sorted_moves[j]
                    if not base_strategy._is_combo_compatible(player, action1, action2): continue
                    sim_game, sim_player = game.copy_for_simulation(), next(p for p in game.copy_for_simulation().players if p.player_id == player.player_id)
                    base_strategy._apply_potential_action_to_sim(sim_game, sim_player, action1)
                    # (Further simulation logic as before) ...
                    combo_score = base_strategy._score_board_state(sim_game, sim_player) + action1.score + action2.score
                    if combo_score > best_combo_score: best_combo_score, best_combo_plan = combo_score, [action1, action2]

        # 4. Find the best possible 2-action turn from a single 2-action move
        best_single_move_score = -1.0; best_single_move_plan = None
        if two_action_moves:
            best_2_action_move = max(two_action_moves, key=lambda a: a.score)
            best_single_move_score, best_single_move_plan = best_2_action_move.score, [best_2_action_move]

        # 5. Compare and decide the final plan
        if best_combo_plan and best_combo_score > best_single_move_score: return best_combo_plan
        elif best_single_move_plan: return best_single_move_plan
        
        return [] # Return empty to trigger fallback in AIPlayer

    def _get_economic_actions(self, game: 'Game', player: 'AIPlayer', ideal_plan) -> List[PotentialAction]:
        actions: List[PotentialAction] = []
        mod_data = player.components.get(self.mod_id)
        if not mod_data: return []

        # Guard clause to prevent TypeError if no path is found
        if not ideal_plan:
            return actions

        capital = mod_data.get('capital', 0)
        
        # Action: Bribe Official (Cost: 2 actions)
        bribe_cost = self.config.get("cost_bribe_official", 80)
        path_cost = len(ideal_plan) if ideal_plan else 99
        if capital >= bribe_cost and path_cost <= 5:
             actions.append(PotentialAction(action_type='bribe_official', details={'cost': bribe_cost}, score=150.0, command_generator=lambda g,p,c=bribe_cost:BribeOfficialCommand(g,p,c,1,self.mod_id), action_cost=2))

        # Action: Buy Permit (Cost: 1 action)
        permit_cost = self.config.get("cost_priority_requisition", 35)
        if capital >= permit_cost and len(player.hand) < C.HAND_TILE_LIMIT:
             permit = game.tile_types['Curve'].copy(); permit.is_requisition_permit = True
             actions.append(PotentialAction(action_type='buy_permit', details={'cost': permit_cost}, score=50.0, command_generator=lambda g,p,c=permit_cost,t=permit:PriorityRequisitionCommand(g,p,c,self.mod_id,t), action_cost=1))

        # Action: Sell/Auction Tile (Cost: 1 action)
        for tile in set(player.hand):
            market_price = self.get_market_price(game, tile)
            # Auction high-value tiles the AI doesn't immediately need
            if not any(step.coord in base_strategy._get_high_value_target_squares(game, player, ideal_plan) for step in ideal_plan if ideal_plan) and market_price > 10:
                min_bid = int(market_price * 0.4)
                actions.append(PotentialAction(action_type='auction_tile', details={'tile':tile, 'min_bid':min_bid}, score=min_bid, command_generator=lambda g,p,t=tile,m=min_bid:AuctionTileCommand(g,p,self.mod_id,t,m), action_cost=1))
            # Sell low-value tiles directly if low on cash
            elif capital < permit_cost:
                yield_ = int(market_price * self.config.get("scrapyard_yield", 0.3))
                actions.append(PotentialAction(action_type='sell_tile', details={'tile':tile, 'reward':yield_}, score=yield_, command_generator=lambda g,p,t=tile,r=yield_:SellToScrapyardCommand(g,p,self.mod_id,t,r), action_cost=1))

        # Action: Bid on Auction (Cost: 1 action)
        for i, auction in enumerate(game.live_auctions):
            if auction['seller_id'] == player.player_id: continue # Can't bid on own auction
            tile_on_auction = game.tile_types[auction['tile_type_name']]
            market_price = self.get_market_price(game, tile_on_auction)
            my_bid = int(market_price * 0.6) # AI bids 60% of market value
            if capital - mod_data.get('frozen_capital', 0) > my_bid:
                 actions.append(PotentialAction(action_type='place_bid', details={'auction_index':i, 'amount':my_bid}, score=market_price*0.4, command_generator=lambda g,p,idx=i,amt=my_bid:PlaceBidCommand(g,p,self.mod_id,idx,amt), action_cost=1))

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

    
    def on_ai_driving_turn(self, game: 'Game', player: 'AIPlayer') -> bool:
        """
        The Economic Mod takes full control of the AI's driving turn to handle
        the strategic use of Influence points.
        """
        print(f"  [{self.name} AI] Handling DRIVING phase for Player {player.player_id}.")
        
        # 1. Make the standard roll. The move command does NOT end the turn.
        standard_roll = game.deck_manager.roll_special_die()
        print(f"  AI rolled a '{standard_roll}'.")
        game.attempt_driving_move(player, standard_roll, end_turn=False)

        # 2. Loop to spend influence points strategically
        while player.components[self.mod_id]['influence'] > 0:
            if _ai_wants_to_use_influence(game, player):
                print(f"  AI is using 1 Influence Point!")
                player.components[self.mod_id]['influence'] -= 1
                
                influence_roll = random.randint(1, 4) # Special 4-sided die
                print(f"  Influence Roll: {influence_roll}")
                
                # This move also does not end the turn.
                game.attempt_driving_move(player, influence_roll, end_turn=False)
            else:
                # AI decided not to use more influence this turn.
                break
        
        # 3. After all rolls are done, definitively end the turn.
        print(f"  AI driving turn for Player {player.player_id} is over.")
        pygame.event.post(pygame.event.Event(C.START_NEXT_TURN_EVENT, {'reason': 'ai_driving_turn_end'}))
        
        # 4. Return True to signify that this mod handled the turn.
        return True