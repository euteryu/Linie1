# main.py
import pygame
from visualizer import Linie1Visualizer

if __name__ == '__main__':
    print("Starting Linie 1...")
    try:
        app = Linie1Visualizer()
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