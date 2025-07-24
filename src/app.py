import os
import pygame
import sys
import json
import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess

from typing import List, Dict, Tuple, Optional, Set, Any
from scenes.level_selection_scene import LevelSelectionScene
from scenes.resolution_confirmation_scene import ResolutionConfirmationScene
from levels.level import Level
from common.layout import LayoutConstants

from common.asset_manager import AssetManager
from scenes.intro_scene import IntroScene
from scenes.main_menu_scene import MainMenuScene
from scenes.game_scene import GameScene
from scenes.settings_scene import SettingsScene
from game_logic.game import Game
from common.sound_manager import SoundManager
from mods.mod_manager import ModManager
from common import constants as C

class App:
    def __init__(self, root_dir: str, player_types: list[str], difficulty: str, mod_manager: ModManager, level_data: Level):
        pygame.init()
        self.root_dir = root_dir
        self.settings_path = os.path.join(self.root_dir, 'settings.json')
        self.settings = self._load_settings()
        initial_resolution = tuple(self.settings.get("resolution", [1600, 900]))
        flags = pygame.RESIZABLE
        if self.settings.get("fullscreen", False): flags |= pygame.FULLSCREEN
        self.screen = pygame.display.set_mode(initial_resolution, flags)
        pygame.display.set_caption("Linie 1: Gilded Rails")
        self.clock = pygame.time.Clock()
        theme_path = os.path.join(self.root_dir, 'src', 'assets', 'themes', 'ui_theme_dark.json')
        with open(theme_path, 'r') as f: self.theme = json.load(f)
        self.layout = LayoutConstants(initial_resolution)
        self.asset_manager = AssetManager(self.root_dir)
        self.sounds = SoundManager(self.root_dir)
        self.mod_manager = mod_manager
        self.main_theme_playing = False
        self.asset_manager.load_all_assets(C.TILE_DEFINITIONS) 
        self.game_instance = Game(player_types, difficulty, mod_manager, level_data)
        try: self.tk_root = tk.Tk(); self.tk_root.withdraw()
        except Exception: self.tk_root = None
        self.scenes: Dict[str, 'Scene'] = {"INTRO": IntroScene(self, self.asset_manager)}
        self._re_init_scenes(skip_intro=True)
        self.current_scene = self.scenes["INTRO"]
        if self.game_instance and self.scenes.get("GAME"): self.game_instance.visualizer = self.scenes["GAME"]

    def _re_init_scenes(self, skip_intro: bool = False):
        """Creates fresh instances of all scenes that can be themed or resized."""
        print("Re-initializing scenes...")
        game_instance = self.game_instance if hasattr(self, 'game_instance') else None
        if not skip_intro: self.scenes["INTRO"] = IntroScene(self, self.asset_manager)

        self.scenes["MAIN_MENU"] = MainMenuScene(self, self.asset_manager, self.layout)
        self.scenes["LEVEL_SELECTION"] = LevelSelectionScene(self, self.asset_manager)
        
        # --- CRITICAL FIX HERE ---
        # Provide a default background name that matches the default level and layout.
        default_layout_name = "game_layout_12x12"
        default_background_name = "game_background_12x12"
        self.scenes["GAME"] = GameScene(self, game_instance, self.sounds, self.mod_manager, self.asset_manager, default_layout_name, default_background_name)
        
        self.scenes["SETTINGS"] = SettingsScene(self, self.asset_manager, self.layout)
        if game_instance and self.scenes.get("GAME"): game_instance.visualizer = self.scenes["GAME"]

    def start_new_game(self, level_filename: str, layout_name: str, background_name: str):
        """Creates a brand new Game and GameScene with all necessary assets."""
        try:
            level_path=os.path.join(self.root_dir,'src','levels',level_filename); level_data=Level(level_path)
            from game_logic.player import AIPlayer
            player_types=['ai' if isinstance(p,AIPlayer) else 'human' for p in self.game_instance.players]
            difficulty=self.game_instance.difficulty
            new_game=Game(player_types,difficulty,self.mod_manager,level_data)
            
            new_game_scene=GameScene(self,new_game,self.sounds,self.mod_manager,self.asset_manager,layout_name, background_name)
            
            self.game_instance=new_game; self.scenes['GAME']=new_game_scene; self.go_to_scene('GAME')
        except Exception as e:
            print(f"!!! ERROR starting new game with level '{level_filename}': {e}")
            messagebox.showerror("Load Error",f"Failed to load level or layout files.\nReason: {e}"); self.go_to_scene('LEVEL_SELECTION')

    def change_resolution(self, new_size: Tuple[int, int], confirm: bool = True):
        """
        Changes the screen resolution and, if required, enters the confirmation scene.
        """
        previous_size = (self.layout.SCREEN_WIDTH, self.layout.SCREEN_HEIGHT)
        if new_size == previous_size:
            return

        # This line was fixed previously and is correct.
        self.screen = pygame.display.set_mode(new_size, pygame.RESIZABLE)
        
        self.layout.recalculate(new_size)
        self._re_init_scenes()
        
        if confirm:
            confirm_scene = ResolutionConfirmationScene(self, self.asset_manager, self.layout, new_size, previous_size)
            self.scenes["RESOLUTION_CONFIRM"] = confirm_scene
            self.go_to_scene("RESOLUTION_CONFIRM")
        else:
            self.current_scene = self.scenes["SETTINGS"]


    def _load_settings(self) -> Dict[str, Any]:
        """Loads settings from settings.json, creating it if it doesn't exist."""
        try:
            with open(self.settings_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Create a default settings file
            default_settings = {
                "resolution": [1600, 900],
                "cutscenes_enabled": True
            }
            with open(self.settings_path, 'w') as f:
                json.dump(default_settings, f, indent=2)
            return default_settings

    def save_settings(self):
        """Saves the current settings to settings.json."""
        with open(self.settings_path, 'w') as f:
            json.dump(self.settings, f, indent=2)

    def change_resolution(self, new_size: Tuple[int, int], is_fullscreen: bool, confirm: bool = True):
        """
        Changes the screen resolution, now correctly handling the fullscreen flag.
        
        Args:
            new_size (Tuple[int, int]): The new (width, height) resolution.
            is_fullscreen (bool): Whether the new mode should be fullscreen.
            confirm (bool): If True, will enter the confirmation scene.
        """
        previous_size = (self.layout.SCREEN_WIDTH, self.layout.SCREEN_HEIGHT)
        previous_fullscreen = (self.screen.get_flags() & pygame.FULLSCREEN) != 0
        
        if new_size == previous_size and is_fullscreen == previous_fullscreen:
            return

        # 1. Determine the correct flags for the new display mode
        flags = pygame.RESIZABLE
        if is_fullscreen:
            flags |= pygame.FULLSCREEN

        # 2. Set the new display mode with the correct size and flags
        self.screen = pygame.display.set_mode(new_size, flags)
        
        # 3. Recalculate all dynamic layout values
        self.layout.recalculate(new_size)
        
        # 4. Re-create all scenes so their UI elements are scaled to the new size
        self._re_init_scenes()
        
        # 5. Enter the confirmation flow if required
        if confirm:
            previous_state = (previous_size, previous_fullscreen)
            confirm_scene = ResolutionConfirmationScene(self, self.asset_manager, self.layout, new_size, previous_state)
            self.scenes["RESOLUTION_CONFIRM"] = confirm_scene
            self.go_to_scene("RESOLUTION_CONFIRM")
        else:
            self.current_scene = self.scenes["SETTINGS"]

    def launch_level_editor(self):
        """Launches the level editor as a separate process."""
        try:
            editor_main_path = os.path.join(self.root_dir, 'src', 'level_editor', 'main.py')
            # Use Popen to launch it without blocking the main game menu
            subprocess.Popen([sys.executable, editor_main_path])
        except Exception as e:
            print(f"!!! ERROR launching level editor: {e}")

    def go_to_scene(self, scene_name: str):
        """
        Switches the active scene and handles all on-enter logic, with robust,
        type-based music management.
        """
        if scene_name in self.scenes:
            # --- START OF CHANGE: A complete rewrite of the music logic using isinstance ---
            
            # 1. Check the TYPE of the scene we are LEAVING.
            # If we are leaving a scene that is not a "menu" scene, it means we are returning
            # to the menu system and should prepare to play the theme music.
            current_is_non_menu = isinstance(self.current_scene, (IntroScene, GameScene))
            if current_is_non_menu:
                self.main_theme_playing = False
                self.sounds.stop_music()

            # 2. Switch to the new scene.
            self.current_scene = self.scenes[scene_name]
            print(f"Switching to scene: {scene_name}")

            # 3. Check the TYPE of the scene we are ENTERING.
            # If we are entering a "menu" scene and the theme is not already playing, start it.
            new_is_menu = scene_name in ["MAIN_MENU", "SETTINGS", "LEVEL_SELECTION"]
            if new_is_menu and not self.main_theme_playing:
                self.sounds.play_music('main_theme')
                self.main_theme_playing = True

            # If entering the GAME scene, check for and recover from a paused state.
            elif scene_name == "GAME":
                # RECOVERY STEP 1: Check if the previous turn was completed but never confirmed.
                if self.game_instance.actions_taken_this_turn >= C.MAX_PLAYER_ACTIONS:
                    print("Unconfirmed turn detected upon returning to game. Confirming now...")
                    self.game_instance.confirm_turn()

                # RECOVERY STEP 2: Now that the state is clean, check if the NEW active player is an AI that needs to be started.
                from game_logic.player import AIPlayer
                active_player = self.game_instance.get_active_player()
                if isinstance(active_player, AIPlayer) and self.game_instance.actions_taken_this_turn == 0:
                    print(f"Resuming/Starting AI Player {active_player.player_id}'s turn.")
                    active_player.handle_turn_logic(self.game_instance, self.scenes["GAME"], self.sounds)
        else:
            print(f"Warning: Scene '{scene_name}' not found.")

    def load_theme(self, theme_file):
        """Loads a new theme and correctly re-initializes scenes without restarting the intro."""
        try:
            theme_path = os.path.join(self.root_dir, 'src', 'assets', 'themes', theme_file)
            with open(theme_path, 'r') as f:
                self.theme = json.load(f)
            print(f"Theme '{theme_file}' loaded successfully.")

            # Re-create all scenes, but skip re-creating the IntroScene
            self._re_init_scenes(skip_intro=True)
            
            # Update the current scene to its new instance
            if isinstance(self.current_scene, SettingsScene):
                self.current_scene = self.scenes["SETTINGS"]
            elif isinstance(self.current_scene, MainMenuScene):
                 self.current_scene = self.scenes["MAIN_MENU"]
        except FileNotFoundError:
            print(f"ERROR: Theme file '{theme_file}' not found.")
            # Revert to a default if loading fails
            default_theme_path = os.path.join(self.root_dir, 'src', 'assets', 'themes', 'ui_theme_dark.json')
            with open(default_theme_path, 'r') as f:
                self.theme = json.load(f)

    def save_game_action(self):
        if not self.tk_root: return
        filepath = tk.filedialog.asksaveasfilename(
            title="Save Game", defaultextension=".json", filetypes=[("Linie 1 Saves", "*.json")]
        )
        if filepath:
            self.game_instance.save_game(filepath)

    def load_game_action(self):
        """Loads a saved game and correctly re-initializes the GameScene."""
        if not self.tk_root: return
        filepath = filedialog.askopenfilename(
            title="Load Game", filetypes=[("Linie 1 Saves", "*.json")]
        )
        if filepath:
            self.mod_manager = ModManager() # Ensure clean mod state
            
            # Create a dummy level object for the load function
            # The actual level data will be loaded from the save file's board data.
            dummy_level = Level(os.path.join(self.root_dir, 'src', 'levels', 'default_12x12.json'))
            
            loaded_game = Game.load_game(filepath, C.TILE_DEFINITIONS, self.mod_manager, dummy_level)
            if loaded_game:
                self.game_instance = loaded_game
                # Re-create the game scene with the new game instance and the layout object
                self.scenes["GAME"] = GameScene(self, self.game_instance, self.sounds, self.mod_manager, self.asset_manager, self.layout)
                
                # Update the new game instance's reference to point to the new scene
                self.game_instance.visualizer = self.scenes["GAME"]
                
                self.go_to_scene("GAME")

    # --- START OF CHANGE: The run method is the primary fix ---
    def run(self):
        self.sounds.load_sounds()
        # self.sounds.play_music('main_theme')  # Main Menu should be responsible for starting main theme
        
        # This flag must be declared OUTSIDE the loop to maintain its state.
        initial_ai_turn_triggered = False
        
        while True:
            # This check is now safe because the flag has the correct scope.
            if self.current_scene == self.scenes["GAME"] and not initial_ai_turn_triggered:
                # This logic is only for the very first turn of the game.
                # Subsequent resumes are handled by go_to_scene.
                from game_logic.player import AIPlayer
                active_player = self.game_instance.get_active_player()
                if self.game_instance.current_turn == 1 and isinstance(active_player, AIPlayer):
                    print("First player is an AI, triggering their turn directly.")
                    active_player.handle_turn_logic(self.game_instance, self.scenes["GAME"], self.sounds)
                # Set the flag to true to prevent this block from ever running again
                initial_ai_turn_triggered = True
            
            dt = self.clock.tick(C.FPS) / 1000.0
            events = pygame.event.get()
            
            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            self.current_scene.handle_events(events)
            self.current_scene.update(dt)
            self.current_scene.draw(self.screen)
            
            pygame.display.flip()
    # --- END OF CHANGE ---