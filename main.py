# main.py
import pygame
import sys
import os

src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

from app import App
from mods.mod_manager import ModManager
from common.asset_manager import AssetManager
from levels.level import Level
from common.asset_manager import resource_path

if __name__ == '__main__':
    print("Starting Linie 1...")

    try:
        # 1. Define the path to the level using the reliable resource_path helper
        default_level_path = resource_path(os.path.join('src', 'levels', 'default_12x12.json'))
        
        # 2. Create an instance of the Level class
        level_to_play = Level(default_level_path)

        # 3. Create the ModManager
        mod_manager = ModManager()
        # mod_manager.activate_mod("economic_mod")

        # 4. Define game configuration
        # player_types = ['human', 'ai']
        # player_types = ['human', 'ai', 'ai', 'ai']
        player_types = ['ai', 'ai', 'human']
        # player_types = ['ai', 'ai', 'human', 'human']
        # player_types = ['ai', 'ai', 'ai']
        # player_types = ['ai', 'ai', 'ai', 'ai']
        # player_types = ['ai', 'ai', 'ai', 'ai', 'ai']
        # player_types = ['ai', 'ai', 'ai', 'ai', 'ai', 'ai']

        game_difficulty = 'normal'
        # game_difficulty = 'king'

        # 5. Create and run the main application object.
        # It no longer needs the project_root argument.
        app = App(player_types, game_difficulty, mod_manager, level_to_play)
        app.run()
        
    except Exception as e:
        print("\nAn unexpected error occurred:")
        import traceback
        traceback.print_exc()