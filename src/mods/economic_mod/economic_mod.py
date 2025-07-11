# mods/economic_mod/economic_mod.py
import pygame
from typing import TYPE_CHECKING, List, Dict, Any

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
    from game_logic.player import Player
    from scenes.game_scene import GameScene
    from game_logic.tile import TileType
    from game_logic.ai_actions import PotentialAction

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
        # Set how often events trigger based on player count
        self.headline_manager.event_trigger_threshold = 2 # Every 2 full rounds

    def on_player_turn_start(self, game: 'Game', player: 'Player'):
        """Called at the very start of a turn to tick the event manager."""
        new_event = self.headline_manager.tick(game)
        if new_event and game.visualizer and game.sounds:
            # If a new event was drawn, play a sound
            # You'll need to add a 'headline_news.wav' or similar to your sound manager
            game.sounds.play('headline_news') 

    def on_player_turn_end(self, game: 'Game', player: 'Player'):
        """Players regenerate Capital at the end of their turn."""
        if self.mod_id in player.components:
            capital_pool = player.components[self.mod_id]
            regen = self.config.get("capital_regen_per_turn", 5)
            capital_pool['capital'] = min(capital_pool['max_capital'], capital_pool['capital'] + regen)

    def on_hand_tile_clicked(self, game: 'Game', player: 'Player', tile_type: 'TileType') -> bool:
        """
        Handles special behavior when a hand tile is clicked. This method
        checks for sell mode first, then checks for special permit tiles.
        """
        player_mod_data = player.components.get(self.mod_id)
        if not player_mod_data:
            return False

        # --- Priority 1: Check if Sell Mode is active ---
        if player_mod_data.get('sell_mode_active', False):
            # ... (sell mode logic is correct from previous fixes)
            return True

        # --- START OF FIX: Restore the Requisition Permit logic ---
        # --- Priority 2: Check if the clicked tile is a Requisition Permit ---
        if hasattr(tile_type, 'is_requisition_permit') and tile_type.is_requisition_permit:
            if game.visualizer: # game.visualizer is the GameScene instance
                
                scene = game.visualizer 
                
                def on_tile_selected(chosen_tile: 'TileType'):
                    """This function is executed when the player picks a tile from the palette."""
                    permit_index = -1
                    for i, hand_tile in enumerate(player.hand):
                        if hasattr(hand_tile, 'is_requisition_permit') and hand_tile.is_requisition_permit:
                            permit_index = i
                            break
                    
                    if permit_index != -1:
                        player.hand.pop(permit_index)
                        player.hand.append(chosen_tile)
                        print(f"Permit was fulfilled and replaced with a '{chosen_tile.name}'.")
                    else:
                        print("Error: Could not find permit in hand to fulfill.")
                    
                    scene.return_to_base_state()

                # Request a state change to the generic PaletteSelectionState.
                scene.request_state_change(
                    lambda v: PaletteSelectionState(
                        visualizer=v,
                        title="Fulfill Requisition",
                        items=list(game.tile_types.values()),
                        item_surfaces=scene.tile_surfaces,
                        on_select_callback=on_tile_selected
                    )
                )
            return True # The click was handled by the mod.
        # --- END OF FIX ---
        
        # If neither of the above conditions were met, the mod does nothing with this click.
        return False

    def on_draw_ui_panel(self, screen: Any, visualizer: 'Linie1Visualizer', current_game_state_name: str):
        """Draws the current player's Capital on the UI panel using its own constants."""
        active_player = visualizer.game.get_active_player()
        if self.mod_id in active_player.components:
            capital_pool = active_player.components[self.mod_id]
            capital_text = f"Capital: ${capital_pool.get('capital', 0)} / ${capital_pool.get('max_capital', 200)}"
            
            # Use the new constants for positioning
            draw_text(screen, capital_text, CE.CAPITAL_DISPLAY_X, CE.CAPITAL_DISPLAY_Y, color=(118, 165, 32), size=20)

        # --- NEW: Draw the headline ticker ---
        if self.headline_manager.active_event:
            event = self.headline_manager.active_event
            
            # Create a semi-transparent background bar for the headline
            bar_height = 55
            bar_rect = pygame.Rect(0, 0, C.SCREEN_WIDTH, bar_height)
            bar_surface = pygame.Surface(bar_rect.size, pygame.SRCALPHA)
            bar_surface.fill((0, 0, 0, 150)) # Black, semi-transparent
            screen.blit(bar_surface, bar_rect.topleft)

            # Display the headline text
            headline_text = f"HEADLINE: {event['headline']}"
            draw_text(screen, headline_text, C.SCREEN_WIDTH // 2, 15, C.COLOR_WHITE, size=22, center_x=True)
            
            # Display the effect description and duration
            effect_text = f"{event['description']} (Rounds Remaining: {self.headline_manager.rounds_remaining})"
            draw_text(screen, effect_text, C.SCREEN_WIDTH // 2, 38, (200, 200, 200), size=18, center_x=True) # Light grey color

    def get_ui_buttons(self, current_game_state_name: str) -> List[Dict[str, Any]]:
        """Adds buttons for all economic actions using its own constants."""
        buttons = []
        if current_game_state_name == "LayingTrackState":
            # --- FIX: Get cost dynamically from the headline manager ---
            base_cost = self.config.get("cost_priority_requisition", 25)
            cost = self.headline_manager.get_modified_requisition_cost(base_cost)
            
            # Button 1: Priority Requisition
            buttons.append({
                "text": f"Priority Requisition (${cost})",
                "rect": pygame.Rect(CE.BUTTON_X, CE.BUTTON_Y_START, CE.BUTTON_WIDTH, CE.BUTTON_HEIGHT),
                "callback_name": "issue_priority_requisition"
            })
            
            # Button 2: Sell Tile
            y_pos_sell = CE.BUTTON_Y_START + CE.BUTTON_HEIGHT + CE.BUTTON_SPACING
            buttons.append({
                "text": "Sell Tile to Scrapyard",
                "rect": pygame.Rect(CE.BUTTON_X, y_pos_sell, CE.BUTTON_WIDTH, CE.BUTTON_HEIGHT),
                "callback_name": "activate_sell_mode"
            })

        return buttons

    def handle_ui_button_click(self, game: 'Game', player: 'Player', button_name: str) -> bool:
        """Handles the logic when the 'Priority Requisition' button is clicked."""
        if button_name == "issue_priority_requisition":
            cost = self.config.get("cost_priority_requisition", 25)
            
            placeholder_tile = game.tile_types.get('Curve')
            if not placeholder_tile: return True

            # Create the unique requisition permit instance for the command
            requisition_permit = placeholder_tile.copy()
            # Add a custom attribute to identify it
            requisition_permit.is_requisition_permit = True
            requisition_permit.name = REQUISITION_PERMIT_ID

            # Create and execute the command through the game's generic history manager
            command = PriorityRequisitionCommand(game, player, cost, self.mod_id, requisition_permit)
            game.command_history.execute_command(command)
            return True
        elif button_name == "activate_sell_mode":
            # Don't sell directly. Just activate the mode and inform the player.
            player.components[self.mod_id]['sell_mode_active'] = True
            game.visualizer.current_state.message = "SELL MODE: Click a tile in your hand to sell."
            print(f"[{self.name}] Player {player.player_id} activated Sell Mode.")
            return True

        return False

    def get_ai_potential_actions(self, game: 'Game', player: 'AIPlayer') -> List[PotentialAction]:
        """The mod provides fully-formed, scored actions for the AI to consider."""
        actions = []
        mod_data = player.components.get(self.mod_id)
        if not mod_data: return []

        current_capital = mod_data.get('capital', 0)
        max_capital = mod_data.get('max_capital', 200)
        urgency_modifier = 1.5 if current_capital < (max_capital * 0.25) else 1.0

        # --- Action 1: Selling Tiles (1 Action Cost) ---
        sell_rewards = self.config.get("sell_rewards", {})
        for tile in player.hand:
            reward = sell_rewards.get(tile.name, sell_rewards.get("default", 0))
            if current_capital + reward <= max_capital:
                sell_score = 5.0 + (reward * urgency_modifier)
                actions.append(PotentialAction(
                    action_type='sell_tile',
                    details={'tile': tile, 'reward': reward},
                    score=sell_score,
                    score_breakdown={'sell_value': sell_score},
                    command_generator=lambda g, p, t=tile, r=reward: SellToScrapyardCommand(g, p, self.mod_id, t, r),
                    action_cost=1
                ))

        # --- Action 2: Priority Requisition (1 Action Cost) ---
        # --- START OF FIX ---
        # Define 'req_cost' before using it.
        req_cost = self.config.get("cost_priority_requisition", 25)
        # --- END OF FIX ---
        if current_capital >= req_cost and len(player.hand) < game.HAND_TILE_LIMIT:
            req_score = 60.0 - req_cost
            permit_tile = game.tile_types['Curve'].copy()
            permit_tile.is_requisition_permit = True
            permit_tile.name = "REQUISITION_PERMIT"
            
            actions.append(PotentialAction(
                action_type='priority_requisition',
                details={'cost': req_cost},
                score=req_score,
                command_generator=lambda g, p, c=req_cost, t=permit_tile: PriorityRequisitionCommand(g, p, c, self.mod_id, t),
                action_cost=1
            ))

        # --- Action 3: Bribe Official (2 Action Cost) ---
        bribe_cost = self.config.get("cost_bribe_official", 80)
        if current_capital >= bribe_cost:
            bribe_reward = self.config.get("reward_influence_from_bribe", 1)
            bribe_score = 50.0
            if player.player_state == PlayerState.DRIVING: bribe_score *= 1.5
            if current_capital == max_capital: bribe_score *= 1.2

            actions.append(PotentialAction(
                action_type='bribe_official',
                details={'cost': bribe_cost, 'reward': bribe_reward},
                score=bribe_score,
                command_generator=lambda g, p, c=bribe_cost, r=bribe_reward: BribeOfficialCommand(g, p, c, r, self.mod_id),
                action_cost=2
            ))
            
        return actions