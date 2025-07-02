# main.py
import pygame
from visualizer import Linie1Visualizer

if __name__ == '__main__':
    print("Starting Linie 1...")
    try:
        # --- NEW CONFIGURABLE SETUP ---
        
        # 1. Define the players and their AI type ('human', 'ai')
        #    Note: We no longer specify 'easy_ai' or 'hard_ai' strategy here.
        #          All AIs use the HardStrategy.
        # player_types = ['human', 'ai']
        # player_types = ['human', 'ai', 'ai']
        # player_types = ['ai', 'ai', 'human']
        # player_types = ['ai', 'ai', 'ai']
        player_types = ['ai', 'ai', 'ai', 'ai']
        # player_types = ['ai', 'ai', 'ai', 'ai', 'ai']
        # player_types = ['ai', 'ai', 'ai', 'ai', 'ai', 'ai']
        
        # 2. Set the difficulty for the entire game ('king' or 'normal')
        #    In 'king' mode, all AI players get the drawing advantage.
        # game_difficulty = 'king' 
        game_difficulty = 'normal'

        # The Visualizer will handle creating the correct players based on these settings.
        app = Linie1Visualizer(player_types=player_types, difficulty=game_difficulty)
        app.run()
    except ImportError as e:
         print(f"\nError: A required library is missing.")
         print(f"Details: {e}")
    except Exception as e:
         print("\nAn unexpected error occurred:")
         import traceback
         traceback.print_exc()