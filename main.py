# main.py
import pygame
from app import App
from mod_manager import ModManager

if __name__ == '__main__':
    print("Starting Linie 1...")
    try:
        # 1. Create the ModManager singleton instance here.
        mod_manager = ModManager()
        mod_manager.discover_mods()

        # 2. Activate desired mods.
        mod_manager.activate_mod("magic_system")

        # 3. Define game configuration
        # player_types = ['human', 'ai']
        # player_types = ['human', 'ai', 'ai']
        player_types = ['ai', 'ai', 'human']
        # player_types = ['ai', 'ai', 'ai']
        # player_types = ['ai', 'ai', 'ai', 'ai']
        # player_types = ['ai', 'ai', 'ai', 'ai', 'ai']
        # player_types = ['ai', 'ai', 'ai', 'ai', 'ai', 'ai']

        game_difficulty = 'normal'
        # game_difficulty = 'king'

        # 4. Create and run the main application object.
        app = App(player_types=player_types, difficulty=game_difficulty, mod_manager=mod_manager)
        app.run()
        
    except Exception as e:
        print("\nAn unexpected error occurred:")
        import traceback
        traceback.print_exc()