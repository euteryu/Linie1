# src/app.py
import os
import pygame
import sys
import json
import tkinter as tk
from tkinter import messagebox

from scenes.level_selection_scene import LevelSelectionScene
from levels.level import Level
import subprocess

# Import your scenes
from common.asset_manager import AssetManager
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
    def __init__(self, root_dir: str, player_types: list[str], difficulty: str, mod_manager: ModManager, level_data: Level):
        """
        Initializes the main application.

        Args:
            root_dir (str): The project's root directory.
            player_types (list[str]): List of player types for the game.
            difficulty (str): AI difficulty.
            mod_manager (ModManager): The game's mod manager.
            level_data (Level): The loaded data for the map to be played.
        """
        pygame.init()
        self.screen = pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
        pygame.display.set_caption("Linie 1: Gilded Rails")
        self.clock = pygame.time.Clock()
        
        self.root_dir = root_dir

        theme_path = os.path.join(self.root_dir, 'src', 'assets', 'themes', 'ui_theme_dark.json')
        with open(theme_path, 'r') as f:
            self.theme = json.load(f)

        self.asset_manager = AssetManager(self.root_dir)
        self.sounds = SoundManager(self.root_dir)
        self.mod_manager = mod_manager
        
        self.settings = {'cutscenes_enabled': True}
        self.main_theme_playing = False

        self.asset_manager.load_all_assets(C.TILE_DEFINITIONS) 
        
        # Pass the level_data to the Game instance
        self.game_instance = Game(player_types, difficulty, mod_manager, level_data)
        
        try:
            self.tk_root = tk.Tk()
            self.tk_root.withdraw()
        except Exception as e:
            self.tk_root = None

        self.scenes = {
            "INTRO": IntroScene(self, self.asset_manager),
            "MAIN_MENU": MainMenuScene(self, self.asset_manager),
            "LEVEL_SELECTION": LevelSelectionScene(self, self.asset_manager),
            "GAME": GameScene(self, self.game_instance, self.sounds, self.mod_manager, self.asset_manager),
            "SETTINGS": SettingsScene(self, self.asset_manager)
        }
        
        self.current_scene = self.scenes["INTRO"]
        self.game_instance.visualizer = self.scenes["GAME"]

    def start_new_game(self, level_filename: str):
        """
        Creates a brand new Game and GameScene with the specified level file,
        now with robust error handling.
        """
        try:
            # 1. Attempt to load the selected level data. This may fail.
            level_path = os.path.join(self.root_dir, 'src', 'levels', level_filename)
            level_data = Level(level_path)

            # 2. If loading succeeds, create the new game instances.
            from game_logic.player import AIPlayer
            player_types = ['ai' if isinstance(p, AIPlayer) else 'human' for p in self.game_instance.players]
            difficulty = self.game_instance.difficulty
            
            new_game = Game(player_types, difficulty, self.mod_manager, level_data)
            new_game_scene = GameScene(self, new_game, self.sounds, self.mod_manager, self.asset_manager)
            
            # 3. Replace the old instances and switch to the game.
            self.game_instance = new_game
            self.scenes['GAME'] = new_game_scene
            self.go_to_scene('GAME')

        except Exception as e:
            # 4. If loading fails for any reason, show an error and return to the menu.
            print(f"!!! ERROR starting new game with level '{level_filename}': {e}")
            messagebox.showerror("Level Load Error", f"Failed to load level file:\n{level_filename}\n\nReason: {e}")
            self.go_to_scene('LEVEL_SELECTION')

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
        """Loads a new theme and re-initializes all scenes to apply it."""
        try:
            theme_path = os.path.join(self.root_dir, 'src', 'assets', 'themes', theme_file)
            with open(theme_path, 'r') as f:
                self.theme = json.load(f)
            
            self.scenes["MAIN_MENU"] = MainMenuScene(self, self.asset_manager)
            self.scenes["GAME"] = GameScene(self, self.game_instance, self.sounds, self.mod_manager, self.asset_manager)
            self.scenes["SETTINGS"] = SettingsScene(self, self.asset_manager)
            
            self.game_instance.visualizer = self.scenes["GAME"]
        except FileNotFoundError:
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
        if not self.tk_root: return
        filepath = tk.filedialog.askopenfilename(
            title="Load Game", filetypes=[("Linie 1 Saves", "*.json")]
        )
        if filepath:
            self.mod_manager = ModManager()
            loaded_game = Game.load_game(filepath, self.game_instance.tile_types, self.mod_manager)
            if loaded_game:
                self.game_instance = loaded_game
                self.scenes["GAME"] = GameScene(self, self.game_instance, self.sounds, self.mod_manager)
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