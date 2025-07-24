import pygame
import importlib
from typing import Optional, List, Dict, Callable, Set, Tuple

from scenes.scene import Scene
from common.layout import LayoutConstants
from game_logic.game import Game
from game_logic.tile import TileType, PlacedTile
from game_logic.player import Player
from game_logic.enums import GamePhase, PlayerState, Direction
from states.game_states import GameState, LayingTrackState, DrivingState, GameOverState
from mods.mod_manager import ModManager
from common.sound_manager import SoundManager
from ui.ui_manager import UIManager
from common.rendering_utils import create_tile_surface, get_font, draw_text
import common.constants as C

class GameScene(Scene):
    def __init__(self, scene_manager, game_instance, sounds, mod_manager, asset_manager, layout_name: str, background_name: str):
        super().__init__(scene_manager)
        self.theme = scene_manager.theme
        self.game = game_instance
        self.sounds = sounds
        self.mod_manager = mod_manager
        self.asset_manager = asset_manager
        self.screen = scene_manager.screen
        
        self.background_image = self.asset_manager.load_background(background_name)

        self.imported_layout = None
        self.TILE_SIZE = 80
        self.board_bounds = pygame.Rect(200, 100, 800, 800)
        self.hand_tile_regions = {}; self.button_regions = {}; self.timetable_region = None
        self.hovered_ui_name = None
        self.strategy_view_active = True

        self._load_and_scale_layout(layout_name)
        self._load_ui_assets()

        self.tile_surfaces = {name: create_tile_surface(TileType(name=name, **details), self.TILE_SIZE) for name, details in C.TILE_DEFINITIONS.items()}
        self.pretty_tile_surfaces = {name: pygame.transform.scale(surf, (self.TILE_SIZE, self.TILE_SIZE)) if surf else None for name, surf in self.asset_manager.images['tiles'].items()}
        
        self.current_state: GameState = LayingTrackState(self)
        if game_instance: self.game.visualizer = self; self.update_current_state_for_player()

    def _load_and_scale_layout(self, layout_name: str):
        try:
            module_path = f"ui.layouts.{layout_name}"
            self.imported_layout = importlib.import_module(module_path)
        except ImportError:
            print(f"CRITICAL ERROR: Could not import layout '{layout_name}'.py."); return
        
        for name in [n.replace('_bounds', '') for n in dir(self.imported_layout) if n.endswith('_bounds')]:
            bounds = getattr(self.imported_layout, f"{name}_bounds"); data = getattr(self.imported_layout, f"{name}_data")
            region = {'bounds': bounds, 'data': data}
            if "at_hand" in name: self.hand_tile_regions[name] = region
            elif "button" in name: self.button_regions[name] = region
            elif "timetable" in name: self.timetable_region = region
            elif "game_board" in name:
                self.board_bounds = bounds
                if (cols := data.get('cols', 12)) > 0: self.TILE_SIZE = self.board_bounds.width // cols

    def _load_ui_assets(self):
        """Loads assets needed for this scene's specific UI."""
        self.view_lever_1_img = self.asset_manager.images['ui'].get('view_lever_1')
        self.view_lever_2_img = self.asset_manager.images['ui'].get('view_lever_2')
        self.timetable_font = get_font(18) # You might want to make this size dynamic

    def draw_board(self):
        # --- MODIFIED: Draw to a temporary surface for transparency ---
        board_surface = pygame.Surface(self.board_bounds.size, pygame.SRCALPHA)

        for r in range(self.game.board.rows):
            for c in range(self.game.board.cols):
                rect = pygame.Rect(c * self.TILE_SIZE, r * self.TILE_SIZE, self.TILE_SIZE, self.TILE_SIZE)
                placed_tile = self.game.board.get_tile(r, c)
                is_playable = self.game.board.is_playable_coordinate(r, c)
                
                bg_color = self.theme["colors"]["board_bg"] if is_playable else (0,0,0,0) # Transparent if not playable
                grid_color = self.theme["colors"]["grid_lines"]
                pygame.draw.rect(board_surface, bg_color, rect)
                pygame.draw.rect(board_surface, grid_color, rect, 1)

                if placed_tile:
                    surfaces = self.pretty_tile_surfaces if not self.strategy_view_active else self.tile_surfaces
                    tile_surf = surfaces.get(placed_tile.tile_type.name)
                    if tile_surf:
                        rotated_surf = pygame.transform.rotate(tile_surf, -placed_tile.orientation)
                        board_surface.blit(rotated_surf, rotated_surf.get_rect(center=rect.center))
        
        # Set transparency and draw the final board surface to the screen
        board_surface.set_alpha(int(255 * 0.89)) # 89% opaque
        self.screen.blit(board_surface, self.board_bounds.topleft)

    def draw_ui(self):
        player = self.game.get_active_player()
        if not player: return

        # --- Draw At-Hand Tiles ---
        for i in range(5):
            region = self.hand_tile_regions.get(f"at_hand_{i+1}")
            if region and i < len(player.hand):
                tile_image = self.pretty_tile_surfaces.get(player.hand[i].name)
                if tile_image: self.screen.blit(pygame.transform.scale(tile_image, region['bounds'].size), region['bounds'].topleft)
                # ... (code for selected/staged highlights) ...

        # --- Draw Buttons and Levers ---
        for name, region in self.button_regions.items():
            if name == 'view_lever_button':
                lever_img = self.view_lever_1_img if self.strategy_view_active else self.view_lever_2_img
                if lever_img: self.screen.blit(pygame.transform.scale(lever_img, region['bounds'].size), region['bounds'].topleft)
            else: # Draw generic stage/commit buttons
                color = (0,200,0) if "commit" in name else (200,120,0)
                if self.hovered_ui_name == name: color = tuple(min(255, c + 55) for c in color)
                pygame.draw.rect(self.screen, color, region['bounds'], border_radius=8)
                draw_text(self.screen, name.replace('_', ' ').title(), region['bounds'].centerx, region['bounds'].centery, COLOR_WHITE, center_x=True, center_y=True)

    def draw_timetable(self):
        """NEW: Draws player info table inside the defined timetable region."""
        if not self.timetable_region: return
        rect = self.timetable_region['bounds']
        
        # Draw a semi-transparent background for the timetable
        s = pygame.Surface(rect.size, pygame.SRCALPHA); s.fill((20, 20, 40, 180)); self.screen.blit(s, rect.topleft)
        pygame.draw.rect(self.screen, (100, 100, 120), rect, 1, border_radius=5)
        
        num_players = len(self.game.players)
        row_height = rect.height / (num_players + 1)
        col_widths = [rect.width * 0.3, rect.width * 0.2, rect.width * 0.5]

        # Draw Headers
        headers = ["Player", "Line", "Stops"]
        x_offset = rect.x
        for i, header in enumerate(headers):
            draw_text(self.screen, header, x_offset + col_widths[i] / 2, rect.y + row_height / 2, COLOR_WHITE, size=20, center_x=True, center_y=True)
            x_offset += col_widths[i]

        # Draw Player Rows
        for i, player in enumerate(self.game.players):
            y_pos = rect.y + row_height * (i + 1.5)
            x_offset = rect.x
            
            p_text = f"Player {player.player_id}"
            l_text = str(player.line_card.line_number) if player.line_card else "?"
            s_text = "-".join(player.route_card.stops) if player.route_card else "?"

            texts = [p_text, l_text, s_text]
            for j, text in enumerate(texts):
                draw_text(self.screen, text, x_offset + col_widths[j] / 2, y_pos, COLOR_WHITE, size=18, center_x=True, center_y=True)
                x_offset += col_widths[j]

    def draw(self, screen):
        if self.background_image: screen.blit(pygame.transform.scale(self.background_image, screen.get_size()), (0, 0))
        else: screen.fill(self.theme["colors"]["panel_bg"])
        if not self.imported_layout: return

        self.draw_board()
        self.draw_ui()
        self.draw_timetable()
        # ... (rest of draw method is the same) ...

    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos(); self.hovered_ui_name = None
        # Check all UI regions for hover
        all_ui_regions = {**self.button_regions, **self.hand_tile_regions}
        for name, region in all_ui_regions.items():
            if region['bounds'].collidepoint(mouse_pos): self.hovered_ui_name = name; break

        for event in events:
            # --- MODIFIED: Handle click on the new lever button ---
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.hovered_ui_name == 'view_lever_button':
                    self.strategy_view_active = not self.strategy_view_active
                    self.sounds.play('click') # Add a sound for feedback
                    # Don't pass the event to the state, as we've handled it.
                    continue 

            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE): self.scene_manager.go_to_scene("MAIN_MENU")
            grid_r, grid_c = self.screen_to_grid(event.pos[0], event.pos[1]) if hasattr(event, 'pos') else (-1, -1)
            event.grid_pos = (grid_r, grid_c); event.hovered_ui_name = self.hovered_ui_name
            if self.current_state: self.current_state.handle_event(event)

    # --- (The rest of the file is identical to the previous version and correct) ---
    def force_redraw(self, message: str = "..."):
        if self.background_image: self.screen.blit(pygame.transform.scale(self.background_image, self.screen.get_size()), (0, 0))
        else: self.screen.fill(self.theme["colors"]["panel_bg"])
        original_message = "";
        if self.current_state and hasattr(self.current_state,'message'): original_message=self.current_state.message; self.current_state.message=message
        self.draw_board(); self.draw_overlays(); self.draw_ui()
        if self.current_state:
            if hasattr(self.current_state,'message'): self.current_state.message=original_message
            self.current_state.draw(self.screen)
        pygame.display.flip()
    def grid_to_screen(self, r: int, c: int) -> Tuple[int, int]:
        x=self.board_bounds.x+c*self.TILE_SIZE; y=self.board_bounds.y+r*self.TILE_SIZE; return x,y
    def screen_to_grid(self, x: int, y: int) -> Tuple[int, int]:
        if not self.board_bounds.collidepoint(x,y): return -1,-1
        return (y-self.board_bounds.y)//self.TILE_SIZE, (x-self.board_bounds.x)//self.TILE_SIZE
    def update(self, dt: float): pass
    def update_current_state_for_player(self):
        if getattr(self.current_state,'is_transient_state',False): return
        try:
            active_player=self.game.get_active_player(); player_state=active_player.player_state; game_phase=self.game.game_phase
            target_state_class=None
            if game_phase==GamePhase.GAME_OVER: target_state_class=GameOverState
            elif player_state==PlayerState.DRIVING: target_state_class=DrivingState
            elif player_state==PlayerState.LAYING_TRACK: target_state_class=LayingTrackState
            if target_state_class and not isinstance(self.current_state,target_state_class):
                print(f"State Change: -> {target_state_class.__name__}"); self.current_state=target_state_class(self)
        except (IndexError,AttributeError): pass
    def draw_board(self):
        for r in range(self.game.board.rows):
            for c in range(self.game.board.cols):
                screen_x,screen_y=self.grid_to_screen(r, c); rect=pygame.Rect(screen_x,screen_y,self.TILE_SIZE,self.TILE_SIZE)
                placed_tile=self.game.board.get_tile(r, c); is_playable=self.game.board.is_playable_coordinate(r, c)
                bg_color=self.theme["colors"]["board_bg"] if is_playable else self.theme["colors"]["panel_bg"]
                grid_color=self.theme["colors"]["grid_lines"]
                if placed_tile and placed_tile.is_terminal: bg_color=self.theme["colors"]["panel_border"]
                pygame.draw.rect(self.screen,bg_color,rect); pygame.draw.rect(self.screen,grid_color,rect,1)
                if placed_tile:
                    surfaces=self.pretty_tile_surfaces if not self.strategy_view_active else self.tile_surfaces
                    tile_surf=surfaces.get(placed_tile.tile_type.name)
                    if tile_surf:
                        rotated_surf=pygame.transform.rotate(tile_surf, -placed_tile.orientation); self.screen.blit(rotated_surf,rotated_surf.get_rect(center=rect.center))
                building_id=self.game.board.get_building_at(r, c)
                if building_id and is_playable:
                    pygame.draw.rect(self.screen,self.theme["colors"]["building_bg"],rect)
                    b_font=get_font(int(self.TILE_SIZE*0.7)); b_surf=b_font.render(building_id,True,self.theme["colors"]["building_fg"])
                    self.screen.blit(b_surf,b_surf.get_rect(center=rect.center))
                if placed_tile and placed_tile.has_stop_sign: pygame.draw.circle(self.screen,self.theme["colors"]["negative"],rect.center,self.TILE_SIZE//4)
        for player in self.game.players:
            if player.player_state==PlayerState.DRIVING and player.streetcar_position:
                r,c=player.streetcar_position
                if self.game.board.is_valid_coordinate(r,c):
                    screen_x,screen_y=self.grid_to_screen(r,c); center_pos=(screen_x+self.TILE_SIZE//2,screen_y+self.TILE_SIZE//2); tram_radius=self.TILE_SIZE//3
                    p_color=C.PLAYER_COLORS[player.player_id%len(C.PLAYER_COLORS)]
                    pygame.draw.circle(self.screen,p_color,center_pos,tram_radius); pygame.draw.circle(self.screen,(0,0,0),center_pos,tram_radius,2)
    def draw_overlays(self):
        if isinstance(self.current_state,LayingTrackState):
            for move in self.current_state.staged_moves:
                r,c=move['coord']; screen_x,screen_y=self.grid_to_screen(r,c); rect=pygame.Rect(screen_x,screen_y,self.TILE_SIZE,self.TILE_SIZE)
                valid_color=(0,255,0,100); invalid_color=(255,0,0,100); color=valid_color if move.get('is_valid',False) else invalid_color
                s=pygame.Surface(rect.size,pygame.SRCALPHA); s.fill(color); self.screen.blit(s,rect.topleft)
            if self.current_state.move_in_progress and 'coord' in self.current_state.move_in_progress:
                 r,c=self.current_state.move_in_progress['coord']; screen_x,screen_y=self.grid_to_screen(r,c); rect=pygame.Rect(screen_x,screen_y,self.TILE_SIZE,self.TILE_SIZE)
                 color=(255,165,0,100); s=pygame.Surface(rect.size,pygame.SRCALPHA); s.fill(color); self.screen.blit(s,rect.topleft)