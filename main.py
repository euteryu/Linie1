# main.py
import pygame
from visualizer import Linie1Visualizer

if __name__ == '__main__':
    print("Starting Linie 1...")
    try:
        # Example: To start a game with 1 human and 1 AI player, you would change this line.
        # For now, we'll keep it as 1 human player.
        # You can change this to: app = Linie1Visualizer(num_players=1, num_ai=1)
        app = Linie1Visualizer(num_players=0, num_ai=3) 
        app.run()
    except ImportError as e:
         print(f"\nError: Pygame not found or import failed.")
         print(f"Please install pygame: pip install pygame")
         print(f"Details: {e}")
    except Exception as e:
         print("\nAn unexpected error occurred:")
         print(e)
         import traceback
         traceback.print_exc()