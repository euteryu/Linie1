# src/app.py
import os
import pygame
import sys
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING

# from common.layout import LayoutConstants
import json
import tkinter as tk

from scenes.level_selection_scene import LevelSelectionScene
from levels.level import Level
import subprocess

# Import your scenes
from common.asset_manager import AssetManager, resource_path # Import the helper
from scenes.intro_scene import IntroScene
from scenes.main_menu_scene import MainMenuScene
from scenes.game_scene import GameScene
from scenes.settings_scene import SettingsScene
from game_logic.game import Game
from common.sound_manager import SoundManager
from mods.mod_manager import ModManager
from common import constants as C
from levels.level import Level

class App:
    """The main application class, now acting as a Scene Manager."""
    def __init__(self, player_types: list[str], difficulty: str, mod_manager: ModManager, level_data: Level):
        pygame.init()

        try:
            # We use the same icon file that the .spec file uses.
            # Pygame can load .ico files directly.
            icon_path = resource_path('src/assets/images/app_icon.ico')
            icon_surf = pygame.image.load(icon_path)
            pygame.display.set_icon(icon_surf)
        except Exception as e:
            print(f"Warning: Could not load application icon. Using default. Error: {e}")
        
        # 1. Load settings from settings.json using the resource_path helper
        self.settings_path = resource_path('settings.json')
        self.settings = self._load_settings()

        # 2. Create the screen using the loaded resolution
        initial_resolution = tuple(self.settings.get("resolution", [1600, 900]))

        if self.settings.get("fullscreen", False):
            flags = pygame.FULLSCREEN
        else:
            flags = pygame.RESIZABLE

        self.screen = pygame.display.set_mode(initial_resolution, flags)
        pygame.display.set_caption("Linie 1: Gilded Rails")
        self.clock = pygame.time.Clock()

        # 3. Load the theme using the resource_path helper
        theme_path = resource_path(os.path.join('src', 'assets', 'themes', 'ui_theme_dark.json'))
        with open(theme_path, 'r') as f:
            self.theme = json.load(f)

        # 4. Create the dynamic layout manager
        # self.layout = LayoutConstants(initial_resolution)

        # 5. Initialize all other managers (they no longer need root_dir)
        self.asset_manager = AssetManager()
        self.sounds = SoundManager()
        self.mod_manager = mod_manager
        
        self.main_theme_playing = False
        self.asset_manager.load_all_assets(C.TILE_DEFINITIONS) 
        
        # ... rest of __init__ is the same ...
        self.game_instance = Game(player_types, difficulty, mod_manager, level_data)
        try:
            self.tk_root = tk.Tk()
            self.tk_root.withdraw()
        except Exception as e:
            self.tk_root = None
        self.scenes: Dict[str, 'Scene'] = {"INTRO": IntroScene(self, self.asset_manager)}
        self._re_init_scenes(skip_intro=True)
        self.current_scene = self.scenes["INTRO"]
        self.game_instance.visualizer = self.scenes["GAME"]

    def change_resolution(self, new_size: Tuple[int, int], is_fullscreen: bool, confirm: bool = True):
        """
        Changes the screen resolution, now correctly handling the fullscreen flag.
        """
        previous_size = (self.layout.SCREEN_WIDTH, self.layout.SCREEN_HEIGHT)
        previous_fullscreen = (self.screen.get_flags() & pygame.FULLSCREEN) != 0
        
        if new_size == previous_size and is_fullscreen == previous_fullscreen:
            return

        # --- CHANGE HERE: Use exclusive FULLSCREEN flag ---
        if is_fullscreen:
            flags = pygame.FULLSCREEN
        else:
            flags = pygame.RESIZABLE
        # --- END OF CHANGE ---

        self.screen = pygame.display.set_mode(new_size, flags)
        
        self.layout.recalculate(new_size)
        self._re_init_scenes()
        
        if confirm:
            previous_state = (previous_size, previous_fullscreen)
            confirm_scene = ResolutionConfirmationScene(self, self.asset_manager, self.layout, new_size, previous_state)
            self.scenes["RESOLUTION_CONFIRM"] = confirm_scene
            self.go_to_scene("RESOLUTION_CONFIRM")
        else:
            self.current_scene = self.scenes["SETTINGS"]

    def _re_init_scenes(self, skip_intro: bool = False):
        """
        Creates fresh instances of all scenes that can be themed or resized.
        """
        print("Re-initializing scenes...")
        game_instance = self.game_instance if hasattr(self, 'game_instance') else None

        # The IntroScene is a one-time event and should not be re-created
        if not skip_intro:
            self.scenes["INTRO"] = IntroScene(self, self.asset_manager)

        # Re-create all other scenes that depend on themes and layout
        self.scenes["MAIN_MENU"] = MainMenuScene(self, self.asset_manager)
        self.scenes["LEVEL_SELECTION"] = LevelSelectionScene(self, self.asset_manager)
        self.scenes["GAME"] = GameScene(self, game_instance, self.sounds, self.mod_manager, self.asset_manager)
        self.scenes["SETTINGS"] = SettingsScene(self, self.asset_manager)
        
        # Ensure the game instance is linked to the new GameScene
        if game_instance:
            game_instance.visualizer = self.scenes["GAME"]

    def _load_settings(self) -> Dict[str, Any]:
        """Loads settings from settings.json, creating it if it doesn't exist."""
        try:
            with open(self.settings_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Create a default settings file
            default_settings = {
                "resolution": [1600, 900],
                "fullscreen": False,
                "cutscenes_enabled": True
            }
            with open(self.settings_path, 'w') as f:
                json.dump(default_settings, f, indent=2)
            return default_settings

    def save_settings(self):
        """Saves the current settings to settings.json."""
        with open(self.settings_path, 'w') as f:
            json.dump(self.settings, f, indent=2)

    def start_new_game(self, level_filename: str):
        try:
            # Use resource_path to find the level file
            level_path = resource_path(os.path.join('src', 'levels', level_filename))
            level_data = Level(level_path)

            from game_logic.player import AIPlayer
            player_types = ['ai' if isinstance(p, AIPlayer) else 'human' for p in self.game_instance.players]
            difficulty = self.game_instance.difficulty
            
            new_game = Game(player_types, difficulty, self.mod_manager, level_data)
            new_game_scene = GameScene(self, new_game, self.sounds, self.mod_manager, self.asset_manager)
            
            self.game_instance = new_game
            self.scenes['GAME'] = new_game_scene
            self.go_to_scene('GAME')

        except Exception as e:
            print(f"!!! ERROR starting new game with level '{level_filename}': {e}")
            messagebox.showerror("Level Load Error", f"Failed to load level file:\n{level_filename}\n\nReason: {e}")
            self.go_to_scene('LEVEL_SELECTION')

    # --- MODIFIED METHOD ---
    def launch_level_editor(self):
        try:
            editor_main_path = resource_path(os.path.join('src', 'level_editor', 'main.py'))
            subprocess.Popen([sys.executable, editor_main_path])
        except Exception as e:
            print(f"!!! ERROR launching level editor: {e}")
            messagebox.showerror("Editor Launch Error", f"Could not launch the level editor.\n\nReason: {e}")

    def go_to_scene(self, scene_name: str):
        """
        Switches the active scene and handles any on-enter logic, including
        recovering from an interrupted turn progression for the AI.
        """
        if scene_name in self.scenes:
            # First, stop the current scene's music if it's the main theme
            if self.current_scene == self.scenes["MAIN_MENU"]:
                self.main_theme_playing = False # Allow it to be restarted later

            self.current_scene = self.scenes[scene_name]
            print(f"Switching to scene: {scene_name}")

            # --- Scene-specific "on enter" logic ---

            # If entering the MAIN_MENU, start the main theme if it's not already playing.
            if scene_name == "MAIN_MENU":
                if not self.main_theme_playing:
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
        try:
            theme_path = resource_path(os.path.join('src', 'assets', 'themes', theme_file))
            with open(theme_path, 'r') as f:
                self.theme = json.load(f)
            print(f"Theme '{theme_file}' loaded successfully.")
            self._re_init_scenes(skip_intro=True)
            
            if isinstance(self.current_scene, SettingsScene):
                self.current_scene = self.scenes["SETTINGS"]
            elif isinstance(self.current_scene, MainMenuScene):
                 self.current_scene = self.scenes["MAIN_MENU"]
        except FileNotFoundError:
            print(f"ERROR: Theme file '{theme_file}' not found.")
            default_theme_path = resource_path(os.path.join('src', 'assets', 'themes', 'ui_theme_dark.json'))
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
        if not self.tk_root: return
        filepath = filedialog.askopenfilename(
            title="Load Game", filetypes=[("Linie 1 Saves", "*.json")]
        )
        if filepath:
            self.mod_manager = ModManager()
            
            # Use resource_path for the dummy level
            dummy_level_path = resource_path(os.path.join('src', 'levels', 'default_12x12.json'))
            dummy_level = Level(dummy_level_path)
            
            loaded_game = Game.load_game(filepath, C.TILE_DEFINITIONS, self.mod_manager, dummy_level)
            if loaded_game:
                self.game_instance = loaded_game
                self.scenes["GAME"] = GameScene(self, self.game_instance, self.sounds, self.mod_manager, self.asset_manager)
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