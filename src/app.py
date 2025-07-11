# src/app.py
import os
import pygame
import sys
import json
from tkinter import filedialog # Need to import this for save/load

# Import your scenes
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

        theme_path = os.path.join(self.root_dir, 'src', 'assets', 'themes', 'ui_theme_dark.json')
        with open(theme_path, 'r') as f:
            self.theme = json.load(f)
            
        # Create shared instances of the game and managers
        self.sounds = SoundManager(root_dir)
        self.mod_manager = mod_manager
        self.game_instance = Game(player_types, difficulty, mod_manager)
        
        # --- Tkinter Root for File Dialogs ---
        try:
            self.tk_root = tk.Tk()
            self.tk_root.withdraw()
        except Exception:
            self.tk_root = None

        # --- Create Scenes ---
        self.scenes = {
            "MAIN_MENU": MainMenuScene(self),
            "GAME": GameScene(self, self.game_instance, self.sounds, self.mod_manager),
            "SETTINGS": SettingsScene(self)
        }
        self.current_scene = self.scenes["MAIN_MENU"]

        # --- Link Game to Scene ---
        # The game object needs a reference to its scene (the old visualizer)
        # to request redraws.
        self.game_instance.visualizer = self.scenes["GAME"]

    def go_to_scene(self, scene_name: str):
        """Switches the active scene and handles any on-enter logic."""
        if scene_name in self.scenes:
            self.current_scene = self.scenes[scene_name]
            print(f"Switching to scene: {scene_name}")

            # If we are entering the game scene, check if we need to kick-start an AI player's turn.
            if scene_name == "GAME":
                from game_logic.player import AIPlayer
                active_player = self.game_instance.get_active_player()
                
                # --- START OF FIX ---
                # This check now covers two scenarios:
                # 1. The very start of the game (turn 1, 0 actions).
                # 2. Resuming the game when it's an AI's turn but no actions have been taken yet.
                if isinstance(active_player, AIPlayer) and self.game_instance.actions_taken_this_turn == 0:
                    print(f"Resuming/Starting AI Player {active_player.player_id}'s turn.")
                    pygame.event.post(pygame.event.Event(C.START_NEXT_TURN_EVENT))
                # --- END OF FIX ---
            
        else:
            print(f"Warning: Scene '{scene_name}' not found.")

    def load_theme(self, theme_file):
        """Loads a new theme and re-initializes all scenes to apply it."""
        try:
            theme_path = os.path.join(self.root_dir, 'src', 'assets', 'themes', theme_file)
            with open(theme_path, 'r') as f:
                self.theme = json.load(f)
            print(f"Theme '{theme_file}' loaded successfully.")

            # Re-create ALL scenes to apply the new theme
            self.scenes["MAIN_MENU"] = MainMenuScene(self)
            self.scenes["GAME"] = GameScene(self, self.game_instance, self.sounds, self.mod_manager)
            self.scenes["SETTINGS"] = SettingsScene(self)
            
            # --- START OF FIX ---
            # After creating the new GameScene, we MUST update the game instance's
            # reference to point to this new scene object.
            self.game_instance.visualizer = self.scenes["GAME"]
            # --- END OF FIX ---

        except FileNotFoundError:
            print(f"ERROR: Theme file '{theme_file}' not found.")
            # Revert to a default if loading fails
            default_theme_path = os.path.join(self.root_dir, 'src', 'assets', 'themes', 'ui_theme_dark.json')
            with open(default_theme_path, 'r') as f:
                self.theme = json.load(f)

    # --- Save/Load Logic Moved Here from GameState ---
    def save_game_action(self):
        if not self.tk_root: return
        filepath = filedialog.asksaveasfilename(
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
            loaded_game = Game.load_game(filepath, self.game_instance.tile_types, self.mod_manager)
            if loaded_game:
                self.game_instance = loaded_game
                # Re-create the game scene with the new game instance
                self.scenes["GAME"] = GameScene(self, self.game_instance, self.sounds, self.mod_manager)
                
                # --- START OF FIX ---
                # Update the new game instance's reference to point to the new scene
                self.game_instance.visualizer = self.scenes["GAME"]
                # --- END OF FIX ---
                
                self.go_to_scene("GAME")

    def run(self):
        self.sounds.load_sounds()
        self.sounds.play_music('main_theme')
        
        while True:
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