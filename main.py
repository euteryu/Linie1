# main.py
import pygame
import sys
import os

# Add the 'src' directory to the system path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

from app import App
from mods.mod_manager import ModManager

if __name__ == '__main__':
    print("Starting Linie 1...")
    project_root = os.path.dirname(os.path.abspath(__file__))
    try:
        # 1. Create the ModManager singleton instance here.
        mod_manager = ModManager()
        mod_manager.discover_mods()

        # 2. Activate desired mods.
        # mod_manager.activate_mod("magic_system")
        # mod_manager.activate_mod("economic_mod")

        # 3. Define game configuration
        # player_types = ['human', 'ai']
        # player_types = ['human', 'ai', 'ai', 'ai']
        # player_types = ['ai', 'ai', 'human']
        # player_types = ['ai', 'ai', 'human', 'human']
        # player_types = ['ai', 'ai', 'ai']
        # player_types = ['ai', 'ai', 'ai', 'ai']
        player_types = ['ai', 'ai', 'ai', 'ai', 'ai']
        # player_types = ['ai', 'ai', 'ai', 'ai', 'ai', 'ai']

        game_difficulty = 'normal'
        # game_difficulty = 'king'

        # 4. Create and run the main application object.
        app = App(project_root, player_types, game_difficulty, mod_manager)
        app.run()
        
    except Exception as e:
        print("\nAn unexpected error occurred:")
        import traceback
        traceback.print_exc()