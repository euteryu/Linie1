# mods/economic_mod/economic_mod.py
import pygame
from typing import TYPE_CHECKING, List, Dict, Any, Optional, Set, Tuple
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
                'frozen_capital': 0,
                'consecutive_auctions': 0,
                'auction_action_taken_this_turn': False
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
        """Players regenerate Capital and the auction streak is checked."""
        if self.mod_id in player.components:
            mod_data = player.components[self.mod_id]
            # Capital regen
            regen = self.config.get("capital_regen_per_turn", 5)
            mod_data['capital'] = min(mod_data['max_capital'], mod_data['capital'] + regen)

            # --- START OF CHANGE: Reset auction counter if no auction was made ---
            if not mod_data.get('auction_action_taken_this_turn', False):
                if mod_data['consecutive_auctions'] > 0:
                    print(f"  Player {player.player_id}'s auction streak has been reset.")
                mod_data['consecutive_auctions'] = 0
            # Reset the temporary flag for the next turn
            mod_data['auction_action_taken_this_turn'] = False
            # --- END OF CHANGE ---


    def on_draw_ui_panel(self, screen: Any, visualizer: 'GameScene', current_game_state_name: str):
        """Draws the current player's Capital and any active headlines."""
        active_player = visualizer.game.get_active_player()
        
        if self.mod_id in active_player.components:
            capital_pool = active_player.components[self.mod_id]
            capital_text = f"Capital: ${capital_pool.get('capital', 0)}"
            # --- START OF CHANGE: Add Influence display ---
            influence_text = f"Influence: {capital_pool.get('influence', 0)}★"
            # --- END OF CHANGE ---
            frozen_text = f" (Frozen: ${capital_pool.get('frozen_capital', 0)})"
            
            draw_text(screen, capital_text, CE.CAPITAL_DISPLAY_X, CE.CAPITAL_DISPLAY_Y, color=(255, 215, 0), size=20)
            if capital_pool.get('frozen_capital', 0) > 0:
                 draw_text(screen, frozen_text, CE.CAPITAL_DISPLAY_X + 100, CE.CAPITAL_DISPLAY_Y, color=(180, 180, 180), size=16)
            # --- START OF CHANGE: Draw the Influence text ---
            draw_text(screen, influence_text, CE.CAPITAL_DISPLAY_X, CE.CAPITAL_DISPLAY_Y + 25, color=(200, 100, 255), size=20)
            # --- END OF CHANGE ---

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

            # Button 5: Bribe Politician
            y_pos4 = y_pos3 + CE.BUTTON_HEIGHT + CE.BUTTON_SPACING * 3
            buttons.append({
                "text": "Open Auction House", 
                "rect": pygame.Rect(CE.BUTTON_X, y_pos4, CE.BUTTON_WIDTH, CE.BUTTON_HEIGHT), 
                "callback_name": "open_auction_house"
            })
            
            bribe_cost = self.config.get("cost_bribe_official", 80)
            y_pos5 = y_pos4 + CE.BUTTON_HEIGHT + CE.BUTTON_SPACING
            buttons.append({
                "text": f"Bribe Official (${bribe_cost})", 
                "rect": pygame.Rect(CE.BUTTON_X, y_pos5, CE.BUTTON_WIDTH, CE.BUTTON_HEIGHT), 
                "callback_name": "bribe_official"
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
            if player.components[self.mod_id].get('consecutive_auctions', 0) >= 3:
                messagebox.showwarning("Rule Limit", "You have auctioned tiles for 3 consecutive turns and cannot auction again this turn.")
                return True # Handled by showing a message
            self._handle_auction_selection(game, player)
            return True

        elif button_name == "bribe_official":
            bribe_cost = self.config.get("cost_bribe_official", 80)
            command = BribeOfficialCommand(game, player, bribe_cost, 1, self.mod_id)
            if not game.command_history.execute_command(command):
                 messagebox.showerror("Error", "Could not execute bribe. Check your available Capital.")
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
                if game.command_history.execute_command(command):
                    # --- START OF CHANGE: Increment counter on successful auction ---
                    player.components[self.mod_id]['consecutive_auctions'] += 1
                    player.components[self.mod_id]['auction_action_taken_this_turn'] = True
                    # --- END OF CHANGE ---
                else:
                    messagebox.showerror("Error", "Could not auction tile.")
                scene.return_to_base_state()
            except (ValueError, TypeError):
                messagebox.showerror("Error", "Invalid input. Please enter a number.")
                scene.return_to_base_state()

        economic_mod = game.mod_manager.available_mods[self.mod_id]
        scene.request_state_change(
            lambda v: PaletteSelectionState(scene=v, title="Select Tile from Your Hand to Auction", items=player.hand, item_surfaces=scene.tile_surfaces, on_select_callback=on_tile_to_auction_selected, economic_mod_instance=economic_mod, current_capital=player_mod_data.get('capital', 0))
        )


    def plan_ai_turn(self, game: 'Game', player: 'AIPlayer', base_strategy: 'AIStrategy') -> Optional[List[PotentialAction]]:
        """
        The Economic Mod's AI brain, now with a clear hierarchy of priorities.
        It will always prefer to build its route over purely economic moves.
        """
        print(f"  [{self.name} AI] Planning turn for Player {player.player_id}...")
        ideal_plan = base_strategy._calculate_ideal_route(game, player)
        target_squares = base_strategy._get_high_value_target_squares(game, player, ideal_plan)
        if len(target_squares) > C.MAX_TARGETS_FOR_COMBO_SEARCH:
            target_squares = base_strategy._prune_targets(game, player, target_squares, ideal_plan)

        # 1. Gather all possible actions, separated by type
        placements = base_strategy._gather_standard_actions(game, player, ideal_plan, target_squares)
        economics = self._get_economic_actions(game, player, ideal_plan, target_squares, base_strategy)

        # 2. Decision Hierarchy: Find the best plan based on clear priorities.
        best_plan = None
        
        # PRIORITY 1: The best plan is two standard placements.
        if len(placements) >= 2:
            best_plan = self._find_best_combo(placements, placements, base_strategy, game, player)

        # PRIORITY 2: If a 2-placement plan isn't possible, try a 1-placement + 1-economic plan.
        if placements and economics:
            mixed_plan = self._find_best_combo(placements, economics, base_strategy, game, player)
            # Only accept this mixed plan if it's better than the current best plan (if any)
            if not best_plan or (mixed_plan and mixed_plan[0].score + mixed_plan[1].score > best_plan[0].score + best_plan[1].score):
                best_plan = mixed_plan
        
        # PRIORITY 3: Only if no placements are possible, consider a purely economic turn.
        if not placements and len(economics) >= 2:
            print(f"  [{self.name} AI] No good placements found. Considering purely economic actions.")
            best_plan = self._find_best_combo(economics, economics, base_strategy, game, player)

        # Also consider single, high-value 2-action moves like Bribing
        two_action_economics = [a for a in economics if a.action_cost == 2]
        if two_action_economics:
            best_2_action_move = max(two_action_economics, key=lambda a: a.score)
            # Compare with the best combo plan found so far
            current_best_score = best_plan[0].score + best_plan[1].score if best_plan else -1
            if best_2_action_move.score > current_best_score:
                best_plan = [best_2_action_move]

        if best_plan:
             print(f"  [{self.name} AI] Chose plan with score {sum(a.score for a in best_plan):.2f}")
             return best_plan

        return [] # Returning empty will trigger the robust fallback in AIPlayer

    def _find_best_combo(self, list_a, list_b, base_strategy, game, player):
        """Helper to find the best 2-action combo from two lists of actions."""
        best_combo_score = -1.0
        best_combo_plan = None
        
        # Ensure we don't check the same pair twice if lists are the same
        is_same_list = (list_a is list_b)

        for i, action1 in enumerate(list_a):
            # If lists are the same, start inner loop from i+1 to avoid duplicates and identical pairs
            start_j = i + 1 if is_same_list else 0
            for j in range(start_j, len(list_b)):
                action2 = list_b[j]

                if not base_strategy._is_combo_compatible(player, action1, action2): continue
                
                sim_game = game.copy_for_simulation()
                sim_player = next(p for p in sim_game.players if p.player_id == player.player_id)
                base_strategy._apply_potential_action_to_sim(sim_game, sim_player, action1)
                base_strategy._apply_potential_action_to_sim(sim_game, sim_player, action2)

                # The score is a combination of the resulting board state and the inherent action scores
                combo_score = base_strategy._score_board_state(sim_game, sim_player) + action1.score + action2.score
                if combo_score > best_combo_score:
                    best_combo_score = combo_score
                    best_combo_plan = [action1, action2]
        return best_combo_plan

    def _get_economic_actions(self, game: 'Game', player: 'AIPlayer', ideal_plan: Optional[List['RouteStep']], target_squares: Set[Tuple[int, int]], base_strategy: 'AIStrategy') -> List[PotentialAction]:
        """
        Generates a list of all possible economic actions with intelligent, context-aware scoring.
        """
        actions: List[PotentialAction] = []
        mod_data = player.components.get(self.mod_id)
        if not mod_data:
            return []

        capital = mod_data.get('capital', 0)
        max_capital = self.config.get('max_capital', 200)
        permit_cost = self.config.get("cost_priority_requisition", 35)

        # --- HEURISTIC 1: Capital Urgency Modifier ---
        # The AI is more desperate for cash if it can't afford a permit.
        capital_modifier = 4.0 if capital < permit_cost * 1.5 else 1.0

        # --- HEURISTIC 2: Valuate Selling & Auctioning (with capital cap check) ---
        for tile in set(player.hand):
            # A tile is "useless" if it has no valid placements on key squares.
            sim_player_useless_check = player.copy()
            sim_player_useless_check.hand = [tile]
            is_useless = not base_strategy._gather_standard_actions(game, sim_player_useless_check, ideal_plan, target_squares)
            useless_modifier = 4.0 if is_useless else 1.0
            
            market_price = self.get_market_price(game, tile)
            
            # ACTION: Sell to Scrapyard
            scrapyard_yield = int(market_price * self.config.get("scrapyard_yield", 0.7))
            if capital + scrapyard_yield <= max_capital:  # Check capital limit BEFORE generating the action
                sell_score = scrapyard_yield * capital_modifier * useless_modifier
                actions.append(PotentialAction(action_type='sell_tile', details={'tile': tile, 'reward': scrapyard_yield}, score=sell_score, command_generator=lambda g,p,t=tile,r=scrapyard_yield:SellToScrapyardCommand(g,p,self.mod_id,t,r), action_cost=1))

            # ACTION: Auction a Tile (with spam prevention)
            if mod_data.get('consecutive_auctions', 0) < 3:
                min_bid = int(market_price * self.config.get("auction_min_bid_yield", 0.6))
                auction_score = min_bid * capital_modifier * useless_modifier
                actions.append(PotentialAction(action_type='auction_tile', details={'tile': tile, 'min_bid': min_bid}, score=auction_score, command_generator=lambda g,p,t=tile,m=min_bid:AuctionTileCommand(g,p,self.mod_id,t,m), action_cost=1))
        
        # --- HEURISTIC 3: Valuate Buying a Permit (Opportunity Cost) ---
        if capital >= permit_cost and len(player.hand) < C.HAND_TILE_LIMIT:
            best_potential_gain = 0
            for tile_type in set(game.deck_manager.tile_draw_pile):
                tile_market_price = self.get_market_price(game, tile_type)
                total_cost = permit_cost + tile_market_price
                if capital >= total_cost:
                    sim_player_permit = player.copy()
                    sim_player_permit.hand.append(tile_type)
                    possible_placements = base_strategy._gather_standard_actions(game, sim_player_permit, ideal_plan, target_squares)
                    if possible_placements:
                        best_placement_score = max(p.score for p in possible_placements)
                        net_gain = best_placement_score - total_cost
                        if net_gain > best_potential_gain:
                            best_potential_gain = net_gain
            
            if best_potential_gain > 0:
                permit = game.tile_types['Curve'].copy(); permit.is_requisition_permit = True
                actions.append(PotentialAction(action_type='buy_permit', details={'cost': permit_cost}, score=best_potential_gain, command_generator=lambda g,p,c=permit_cost,t=permit:PriorityRequisitionCommand(g,p,c,self.mod_id,t), action_cost=1))

        # --- HEURISTIC 4: Valuate Bidding on an Auction (Strategic Value) ---
        for i, auction in enumerate(game.live_auctions):
            if auction['seller_id'] == player.player_id: continue
            
            tile_on_auction = game.tile_types[auction['tile_type_name']]
            
            # Check if the AI has a use for this tile
            sim_player_bid_check = player.copy(); sim_player_bid_check.hand.append(tile_on_auction)
            if not base_strategy._gather_standard_actions(game, sim_player_bid_check, ideal_plan, target_squares):
                continue

            market_price = self.get_market_price(game, tile_on_auction)
            cost_via_permit = permit_cost + market_price
            current_high_bid = max([b['amount'] for b in auction['bids']], default=auction['min_bid'])
            
            if cost_via_permit > current_high_bid: # Only bid if it's a good deal
                savings = cost_via_permit - current_high_bid
                my_bid = current_high_bid + int(savings * 0.7)
                available_capital = capital - mod_data.get('frozen_capital', 0)
                if available_capital >= my_bid:
                    bid_score = savings  # The score IS the money saved
                    actions.append(PotentialAction(action_type='place_bid', details={'auction_index':i, 'amount':my_bid}, score=bid_score, command_generator=lambda g,p,idx=i,amt=my_bid:PlaceBidCommand(g,p,self.mod_id,idx,amt), action_cost=1))

        # --- HEURISTIC 5: Valuate Bribing for Influence ---
        bribe_cost = self.config.get("cost_bribe_official", 80)
        available_capital = capital - mod_data.get('frozen_capital', 0)
        if available_capital >= bribe_cost:
            path_cost = len(ideal_plan) if ideal_plan else 99
            if path_cost <= 5: # Only consider bribing when close to winning
                bribe_score = (100.0 / (path_cost + 1)) * 3
                if bribe_score > 30:
                     actions.append(PotentialAction(action_type='bribe_official', details={'cost': bribe_cost}, score=bribe_score, command_generator=lambda g,p,c=bribe_cost:BribeOfficialCommand(g,p,c,1,self.mod_id), action_cost=2))

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