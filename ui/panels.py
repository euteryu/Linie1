# ui/panels.py
import pygame
from ui.ui_component import IUIComponent
import constants as C
from rendering_utils import draw_text, get_font
from game_states import LayingTrackState, DrivingState, GameOverState

class GameInfoPanel(IUIComponent):
    """Displays turn number, active player, and action count."""
    def __init__(self, screen, theme):
        super().__init__(screen)
        self.theme = theme

    def draw(self, game, current_state):
        try:
            player = game.get_active_player()
            player_id, player_state_name = player.player_id, player.player_state.name
        except (IndexError, AttributeError):
            player_id, player_state_name = "?", "Unknown"

        turn_text = f"Turn {game.current_turn} - Player {player_id} ({player_state_name})"
        draw_text(self.screen, turn_text, C.UI_TEXT_X, C.UI_TURN_INFO_Y, self.theme["colors"]["text_light"])

        # --- START OF FIX ---
        # Determine which action count to display
        actions_to_display = game.actions_taken_this_turn
        if isinstance(current_state, LayingTrackState):
            # The total number of actions prepared is the sum of those already
            # committed (like selling) and those staged for placement.
            actions_to_display += len(current_state.staged_moves)

        action_text = f"Actions: {actions_to_display}/{C.MAX_PLAYER_ACTIONS}"
        # --- END OF FIX ---

        font = get_font(C.DEFAULT_FONT_SIZE)
        action_surf = font.render(action_text, True, self.theme["colors"]["text_light"])
        action_x = C.UI_PANEL_X + C.UI_PANEL_WIDTH - action_surf.get_width() - 15
        self.screen.blit(action_surf, (action_x, C.UI_TURN_INFO_Y))

class PlayerInfoPanel(IUIComponent):
    """Displays the active player's line card and route card stops."""
    def __init__(self, screen, theme):
        super().__init__(screen)
        self.theme = theme

    def draw(self, game, current_state):
        player = game.get_active_player()
        if not player: return

        line_info = f"Line {player.line_card.line_number}" if player.line_card else "Line: ?"
        stops_info = f"Stops: {' -> '.join(player.route_card.stops)}" if player.route_card else "Stops: ?"
        
        draw_text(self.screen, line_info, C.UI_TEXT_X, C.UI_ROUTE_INFO_Y, self.theme["colors"]["text_light"])
        draw_text(self.screen, stops_info, C.UI_TEXT_X, C.UI_ROUTE_INFO_Y + C.UI_LINE_HEIGHT, self.theme["colors"]["text_light"])

class HandPanel(IUIComponent):
    """Displays the player's hand of tiles."""
    def __init__(self, screen, hand_tile_surfaces, theme):
        super().__init__(screen)
        self.hand_tile_surfaces = hand_tile_surfaces
        self.theme = theme
        self.current_hand_rects = {}

    def draw(self, game, current_state):
        if not isinstance(current_state, LayingTrackState): return
        
        player = game.get_active_player()
        # --- START OF FIX ---
        # The state's parent is now 'scene'.
        if not player or current_state.scene.debug_mode: return

        draw_text(self.screen, f"Player {player.player_id}'s Hand:", C.HAND_AREA_X, C.UI_HAND_TITLE_Y, self.theme["colors"]["text_light"])

        self.current_hand_rects.clear()
        staged_hand_indices = {move['hand_index'] for move in current_state.staged_moves}
        selected_hand_index = current_state.move_in_progress.get('hand_index') if current_state.move_in_progress else None

        y_pos = C.HAND_AREA_Y
        for i, tile_type in enumerate(player.hand):
            if i >= C.HAND_TILE_LIMIT: break
            rect = pygame.Rect(C.HAND_AREA_X, y_pos, C.HAND_TILE_SIZE, C.HAND_TILE_SIZE)
            self.current_hand_rects[i] = rect

            pygame.draw.rect(self.screen, self.theme["colors"]["text_light"], rect) # Use white as background for tracks
            hand_surf = self.hand_tile_surfaces.get(tile_type.name)
            if hand_surf:
                self.screen.blit(hand_surf, rect.topleft)
            pygame.draw.rect(self.screen, self.theme["colors"]["panel_border"], rect, 1)

            if i in staged_hand_indices:
                 pygame.draw.rect(self.screen, self.theme["colors"]["text_muted"], rect, 3) 
            elif i == selected_hand_index:
                 pygame.draw.rect(self.screen, self.theme["colors"]["accent"], rect, 3)

            y_pos += C.HAND_TILE_SIZE + C.HAND_SPACING
        
        current_state.current_hand_rects = self.current_hand_rects

class MessagePanel(IUIComponent):
    """Displays the current contextual message and instructions."""
    def __init__(self, screen, theme):
        super().__init__(screen)
        self.theme = theme

    def draw(self, game, current_state):
        message = getattr(current_state, 'message', "...")
        
        lower_ui_start_y = C.UI_MESSAGE_Y
        if isinstance(current_state, LayingTrackState):
            # --- START OF FIX ---
            if current_state.scene.debug_mode:
                num_rows = (len(current_state.scene.debug_tile_types) + C.DEBUG_TILES_PER_ROW - 1) // C.DEBUG_TILES_PER_ROW
                lower_ui_start_y = C.DEBUG_PANEL_Y + num_rows * (C.DEBUG_TILE_SIZE + C.DEBUG_TILE_SPACING) + 10
            else:
                lower_ui_start_y = C.UI_SELECTED_TILE_Y
        elif isinstance(current_state, DrivingState) and current_state.scene.debug_mode:
            lower_ui_start_y = C.DEBUG_DIE_AREA_Y + C.DEBUG_DIE_BUTTON_SIZE + C.DEBUG_DIE_SPACING + 10
            # --- END OF FIX ---

        draw_text(self.screen, f"Msg: {message}", C.UI_TEXT_X, lower_ui_start_y, self.theme["colors"]["text_light"])

        instr_text = "..."
        if isinstance(current_state, LayingTrackState):
            instr_text = "[Click Square] > [Click Hand] > [S] Stage > [Enter] Commit | [Backspace] Cancel"
        elif isinstance(current_state, DrivingState):
            instr_text = "[SPACE] Roll | [Click Die]"
        elif isinstance(current_state, GameOverState):
            instr_text = "Game Over!"
        
        if not isinstance(current_state, GameOverState):
            instr_text += " | [Btn] Debug"
        
        draw_text(self.screen, instr_text, C.UI_TEXT_X, lower_ui_start_y + C.UI_LINE_HEIGHT, self.theme["colors"]["text_muted"], size=18)

class ButtonPanel(IUIComponent):
    """Draws and handles clicks for all standard game buttons."""
    def __init__(self, screen, theme):
        super().__init__(screen)
        self.theme = theme
        btn_w, btn_h, btn_s = C.BUTTON_WIDTH, C.BUTTON_HEIGHT, C.BUTTON_SPACING
        btn_y = C.UI_PANEL_Y + C.UI_PANEL_HEIGHT - btn_h - C.BUTTON_MARGIN_Y
        btn_x_start = C.UI_PANEL_X + C.BUTTON_MARGIN_X
        self.undo_rect = pygame.Rect(btn_x_start + 2 * (btn_w + btn_s), btn_y, btn_w, btn_h)
        self.redo_rect = pygame.Rect(btn_x_start + 3 * (btn_w + btn_s), btn_y, btn_w, btn_h)
        self.debug_rect = pygame.Rect(C.DEBUG_BUTTON_X, C.DEBUG_BUTTON_Y, C.DEBUG_BUTTON_WIDTH, C.DEBUG_BUTTON_HEIGHT)
        heatmap_y = self.redo_rect.y - btn_h - btn_s
        self.heatmap_rect = pygame.Rect(btn_x_start, heatmap_y, btn_w * 2 + btn_s, btn_h)

    def draw(self, game, current_state):
        self._draw_button(self.undo_rect, "Undo(Z)", game.command_history.can_undo())
        self._draw_button(self.redo_rect, "Redo(Y)", game.command_history.can_redo())
        debug_mode = current_state.scene.debug_mode
        self._draw_button(self.debug_rect, f"Debug: {'ON' if debug_mode else 'OFF'}", True, active_color=self.theme["colors"]["negative"] if debug_mode else self.theme["colors"]["accent"])
        heatmap_on = current_state.scene.show_ai_heatmap
        self._draw_button(self.heatmap_rect, f"Heatmap: {'ON' if heatmap_on else 'OFF'}", True, active_color=self.theme["colors"]["positive"] if heatmap_on else self.theme["colors"]["accent"])

    def handle_event(self, event, game, current_state):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1: return False
        mouse_pos = event.pos
        if self.undo_rect.collidepoint(mouse_pos): current_state.undo_action(); return True
        if self.redo_rect.collidepoint(mouse_pos): current_state.redo_action(); return True
        if self.debug_rect.collidepoint(mouse_pos): current_state.toggle_debug_action(); return True
        if self.heatmap_rect.collidepoint(mouse_pos): current_state.toggle_heatmap_action(); return True
        return False

    def _draw_button(self, rect, text, is_enabled, active_color=None, text_size=18):
        if active_color is None: active_color = self.theme["colors"]["accent"]
        bg_color = active_color if is_enabled else self.theme["colors"]["accent_disabled"]
        text_color = self.theme["colors"]["text_dark"] if is_enabled else self.theme["colors"]["text_muted"]
        pygame.draw.rect(self.screen, bg_color, rect, border_radius=5)
        pygame.draw.rect(self.screen, self.theme["colors"]["panel_border"], rect, 1, border_radius=5)
        draw_text(self.screen, text, rect.centerx, rect.centery, text_color, size=text_size, center_x=True, center_y=True)

class ModPanel(IUIComponent):
    """Draws and handles UI elements provided by active mods."""
    def __init__(self, screen, theme):
        super().__init__(screen)
        self.theme = theme
        self.mod_buttons = []

    def draw(self, game, current_state):
        mod_manager = current_state.scene.mod_manager
        mod_manager.draw_mod_ui_elements(self.screen, current_state.scene, current_state.__class__.__name__)
        self.mod_buttons = mod_manager.get_active_ui_buttons(current_state.__class__.__name__)
        for button_def in self.mod_buttons:
            pygame.draw.rect(self.screen, self.theme["colors"]["accent"], button_def['rect'], border_radius=5)
            pygame.draw.rect(self.screen, self.theme["colors"]["panel_border"], button_def['rect'], 1, border_radius=5)
            draw_text(self.screen, button_def['text'], button_def['rect'].x + 5, button_def['rect'].y + 7, self.theme["colors"]["text_dark"], size=18)
    
    def handle_event(self, event, game, current_state):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1: return False
        if isinstance(current_state, LayingTrackState):
            for button_def in self.mod_buttons:
                if button_def['rect'].collidepoint(event.pos):
                    game.mod_manager.handle_mod_ui_button_click(game, game.get_active_player(), button_def['callback_name'])
                    return True
        return False