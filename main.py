# main.py
import pygame
from visualizer import Linie1Visualizer

if __name__ == '__main__':
    print("Starting Linie 1...")
    try:
        # --- NEW CONFIGURABLE PLAYER SETUP ---
        # 'human', 'easy_ai', 'hard_ai'
        
        # Example 1: One easy AI vs one human
        player_setup = ['easy_ai', 'human']

        # Example 1: One human vs one easy AI
        # player_setup = ['human', 'easy_ai']
        
        # Example 2: One easy AI vs one hard AI
        # player_setup = ['easy_ai', 'hard_ai']

        # Example 3: One easy AI vs one easy AI
        # player_setup = ['easy_ai', 'easy_ai']
        
        # Example 4: One hard AI vs one hard AI vs one hard AI vs one hard AI
        # player_setup = ['hard_ai', 'hard_ai', 'hard_ai', 'hard_ai']

        # Example 5: Two humans
        # player_setup = ['human', 'human']

        app = Linie1Visualizer(players_config=player_setup)
        app.run()
    except ImportError as e:
         print(f"\nError: A required library is missing.")
         print(f"Details: {e}")
    except Exception as e:
         print("\nAn unexpected error occurred:")
         import traceback
         traceback.print_exc()