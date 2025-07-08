# mods/economic_mod/economic_mod.py
import pygame
from typing import TYPE_CHECKING, List, Dict, Any

# Since this is a new mod, it needs its own imports
from rendering_utils import draw_text
from imod import IMod
from mods.economic_mod.economic_commands import PriorityRequisitionCommand

import constants as C
from mods.economic_mod.economic_commands import PriorityRequisitionCommand, SellToScrapyardCommand
from ui.palette_selection_state import PaletteSelectionState
from mods.economic_mod import constants_economic as CE

if TYPE_CHECKING:
    from game_logic.game import Game
    from game_logic.player import Player
    from visualizer import Linie1Visualizer
    from game_logic.tile import TileType

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

    def on_player_turn_end(self, game: 'Game', player: 'Player'):
        """Players regenerate Capital at the end of their turn."""
        if self.mod_id in player.components:
            capital_pool = player.components[self.mod_id]
            regen = self.config.get("capital_regen_per_turn", 5)
            capital_pool['capital'] = min(capital_pool['max_capital'], capital_pool['capital'] + regen)

    def on_draw_ui_panel(self, screen: Any, visualizer: 'Linie1Visualizer', current_game_state_name: str):
        """Draws the current player's Capital on the UI panel using its own constants."""
        active_player = visualizer.game.get_active_player()
        if self.mod_id in active_player.components:
            capital_pool = active_player.components[self.mod_id]
            capital_text = f"Capital: ${capital_pool.get('capital', 0)} / ${capital_pool.get('max_capital', 200)}"
            
            # Use the new constants for positioning
            draw_text(screen, capital_text, CE.CAPITAL_DISPLAY_X, CE.CAPITAL_DISPLAY_Y, color=(118, 165, 32), size=20)

    def get_ui_buttons(self, current_game_state_name: str) -> List[Dict[str, Any]]:
        """Adds buttons for all economic actions using its own constants."""
        buttons = []
        if current_game_state_name == "LayingTrackState":
            cost = self.config.get("cost_priority_requisition", 25)
            
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

    def on_hand_tile_clicked(self, game: 'Game', player: 'Player', tile_type: 'TileType') -> bool:
        """Handles special behavior when a hand tile is clicked, now including sell mode."""
        player_mod_data = player.components.get(self.mod_id)
        if not player_mod_data:
            return False

        # --- Check for Sell Mode ---
        if player_mod_data.get('sell_mode_active', False):
            player_mod_data['sell_mode_active'] = False

            # --- START OF FIX: Use new reward values from config ---
            reward = 0
            if hasattr(tile_type, 'is_requisition_permit') and tile_type.is_requisition_permit:
                reward = self.config.get("capital_from_permit", 25)
            elif "Straight" in tile_type.name or "Curve" in tile_type.name:
                reward = self.config.get("capital_from_straight", 5) # Covers both Straight and Curve
            elif "Tree" in tile_type.name:
                reward = self.config.get("capital_from_junction", 15) # Covers all Tree/Junction types
            else: # All other special types
                reward = self.config.get("capital_from_special", 10)
            # --- END OF FIX ---

            command = SellToScrapyardCommand(game, player, self.mod_id, tile_type, reward)
            if game.command_history.execute_command(command):
                game.visualizer.current_state.message = f"Sold {tile_type.name} for ${reward}."
            else:
                game.visualizer.current_state.message = "Sell failed (no actions left?)."
            
            return True

        # --- Priority 2: Check if the clicked tile is a Requisition Permit ---
        if hasattr(tile_type, 'is_requisition_permit') and tile_type.is_requisition_permit:
            if game.visualizer:
                
                # Define the callback function to be executed upon tile selection.
                def on_tile_selected(chosen_tile: 'TileType'):
                    # Find and remove the first available permit from the hand.
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
                    
                    # Return to the main game state.
                    game.visualizer.return_to_base_state()

                # Request a state change to the generic palette selection UI.
                game.visualizer.request_state_change(
                    lambda v: PaletteSelectionState(
                        visualizer=v,
                        title="Fulfill Requisition",
                        items=list(game.tile_types.values()),
                        item_surfaces=game.visualizer.tile_surfaces,
                        on_select_callback=on_tile_selected
                    )
                )

            # Return True because the mod handled this click.
            return True
        
        # If neither of the above conditions were met, the mod does nothing with this click.
        return False