# src/app.py
import os
import pygame
import sys
import json
import tkinter as tk

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

class App:
    """The main application class, now acting as a Scene Manager."""
    def __init__(self, root_dir: str, player_types: list[str], difficulty: str, mod_manager: ModManager):
        pygame.init()
        self.screen = pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
        pygame.display.set_caption("Linie 1: Gilded Rails")
        self.clock = pygame.time.Clock()
        
        self.root_dir = root_dir

        # 0. Load the theme dictionary. This MUST happen before scenes are created.
        theme_path = os.path.join(self.root_dir, 'src', 'assets', 'themes', 'ui_theme_dark.json')
        with open(theme_path, 'r') as f:
            self.theme = json.load(f)

        # 1. Initialize core managers first.
        self.asset_manager = AssetManager(self.root_dir)
        self.sounds = SoundManager(self.root_dir)
        self.mod_manager = mod_manager
        
        # Game-wide settings are stored here
        self.settings = {
            'cutscenes_enabled': True
        }
        self.main_theme_playing = False

        # 2. Load assets. This needs the TILE_DEFINITIONS which are part of the game logic constants.
        self.asset_manager.load_all_assets(C.TILE_DEFINITIONS) 
            
        # 3. Create the main game instance. This MUST happen before creating the GameScene.
        self.game_instance = Game(player_types, difficulty, mod_manager)
        
        # 4. Initialize Tkinter for file dialogs.
        try:
            self.tk_root = tk.Tk()
            self.tk_root.withdraw()
        except Exception as e:
            self.tk_root = None

        # 5. Now that all required objects exist, create the scenes.
        self.scenes = {
            "INTRO": IntroScene(self, self.asset_manager),
            "MAIN_MENU": MainMenuScene(self, self.asset_manager),
            "GAME": GameScene(self, self.game_instance, self.sounds, self.mod_manager, self.asset_manager),
            "SETTINGS": SettingsScene(self, self.asset_manager)
        }
        
        # 6. Set the starting scene.
        self.current_scene = self.scenes["INTRO"]
        
        # 7. Finally, link the game instance to its visualizer (the GameScene).
        self.game_instance.visualizer = self.scenes["GAME"]

    def go_to_scene(self, scene_name: str):
        """
        Switches the active scene and handles any on-enter logic, such as
        starting music or triggering AI turns.
        """
        if scene_name in self.scenes:
            self.current_scene = self.scenes[scene_name]
            print(f"Switching to scene: {scene_name}")

            # --- Scene-specific "on enter" logic goes here ---

            # If we are entering the MAIN_MENU for the first time, start the main theme.
            if scene_name == "MAIN_MENU":
                if not self.main_theme_playing:
                    self.sounds.play_music('main_theme') # This will loop by default
                    self.main_theme_playing = True

            # If we are entering the GAME scene, check if an AI needs to be activated.
            elif scene_name == "GAME":
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