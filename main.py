# main.py
import pygame
from visualizer import Linie1Visualizer
from mod_manager import ModManager

if __name__ == '__main__':
    print("Starting Linie 1...")
    try:
        # --- THIS IS THE FIX for the AttributeError ---
        # 1. Create the ModManager singleton instance here.
        mod_manager = ModManager()
        mod_manager.discover_mods()

        # 2. Activate desired mods.
        # TODO: HOW TO ENSURE MOD INTER-DEPENENCY CLASH PREVENTION ?
        #       HOW TO LOAD WITHOUT MAIN.PY KNOWING NAME OF MODS SPECIFICALLY, IF USER MAKES / INSTALLS THEIR OWN MODS ?  API ?
        # mod_manager.activate_mod("lucky_draws")
        # mod_manager.activate_mod("trading_system")
        mod_manager.activate_mod("magic_system")

        # player_types = ['human', 'ai']
        # player_types = ['human', 'ai', 'ai']
        # player_types = ['ai', 'ai', 'human']
        # player_types = ['ai', 'ai', 'ai']
        # player_types = ['ai', 'ai', 'ai', 'ai']
        player_types = ['ai', 'ai', 'ai', 'ai', 'ai']
        # player_types = ['ai', 'ai', 'ai', 'ai', 'ai', 'ai']

        game_difficulty = 'normal'
        # game_difficulty = 'king'

        # 3. Pass the single mod_manager instance to the Visualizer.
        app = Linie1Visualizer(player_types=player_types, difficulty=game_difficulty, mod_manager=mod_manager)
        app.run()
    except Exception as e:
         print("\nAn unexpected error occurred:")
         import traceback
         traceback.print_exc()