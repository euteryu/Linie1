# app.py
import pygame
import sys
import tkinter as tk

from visualizer import Linie1Visualizer
from sound_manager import SoundManager
from mod_manager import ModManager
from game_logic.game import Game
from game_logic.player import AIPlayer # <--- FIX #1: Add correct import
import constants as C

class App:
    """
    The main application class. It initializes Pygame, manages high-level
    application state (e.g., main menu, in-game), and owns the main game loop.
    """
    def __init__(self, player_types: list[str], difficulty: str, mod_manager: ModManager):
        # --- Core Initializations ---
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((C.SCREEN_WIDTH, C.SCREEN_HEIGHT))
        pygame.display.set_caption("Linie 1")
        self.clock = pygame.time.Clock()

        # --- Manager & Engine Initializations ---
        self.sounds = SoundManager()
        self.mod_manager = mod_manager
        
        try:
            self.game = Game(player_types=player_types, difficulty=difficulty, mod_manager=mod_manager)
        except Exception as e:
            print(f"FATAL: Game initialization failed: {e}")
            import traceback
            traceback.print_exc()
            self.quit()

        # --- Scene/Visualizer Initialization ---
        # The App owns the visualizer for the "in-game" scene.
        self.visualizer = Linie1Visualizer(self.screen, self.game, self.sounds, self.mod_manager)
        self.game.visualizer = self.visualizer # Link back for the game to request redraws

        # --- High-Level Application State ---
        # This can be expanded for Main Menus, Settings, etc.
        # e.g., self.app_state = "MAIN_MENU"
        self.app_state = "IN_GAME"

        # Initialize Tkinter for file dialogs
        try:
            self.tk_root = tk.Tk()
            self.tk_root.withdraw()
            self.visualizer.tk_root = self.tk_root # Give the visualizer access
        except Exception as e:
            print(f"Warning: Tkinter init failed ({e}). File dialogs disabled.")
            self.tk_root = None

    def run(self):
        """Main application loop."""
        self.sounds.load_sounds()
        self.sounds.play_music('main_theme')

        # Post event to kick off the first turn if it's an AI
        # --- FIX #2: Remove the incorrect 'C.' prefix ---
        if isinstance(self.game.get_active_player(), AIPlayer):
            pygame.event.post(pygame.event.Event(C.START_NEXT_TURN_EVENT))

        running = True
        while running:
            # --- Event Handling ---
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                
                # Let the current scene/state handle its own events
                if self.app_state == "IN_GAME":
                    self.visualizer.handle_event(event)

            # --- State Updates & Drawing ---
            self.screen.fill(C.COLOR_UI_BG) # Clear screen

            if self.app_state == "IN_GAME":
                self.visualizer.update(self.clock.get_time() / 1000.0)
                self.visualizer.draw()
            # elif self.app_state == "MAIN_MENU":
            #     self.main_menu.update()
            #     self.main_menu.draw(self.screen)
            # elif self.app_state == "SETTINGS":
            #     self.settings.update()
            #     self.settings.draw(self.screen)

            # --- Final Rendering ---
            pygame.display.flip()
            self.clock.tick(C.FPS)

        self.quit()

    def quit(self):
        """Shuts down the application cleanly."""
        pygame.quit()
        if self.tk_root:
            self.tk_root.destroy()
        sys.exit()