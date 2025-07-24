# src/level_editor/main.py
import os
import sys
import pygame

# --- START OF CHANGE: Definitive and Final Path Correction ---

# 1. Get the absolute path to the directory containing this script (level_editor).
#    e.g., C:\Users\...\Linie1\src\level_editor
script_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Get the path to the parent directory of 'level_editor', which is 'src'.
#    e.g., C:\Users\...\Linie1\src
src_dir = os.path.dirname(script_dir)

# 3. Add the 'src' directory to the Python path. This is the crucial step.
#    This allows any script to import modules using 'common' or 'level_editor'
#    as a top-level package.
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# 4. NOW, with the path corrected, we can safely import from our project modules.
#    These imports are now relative to the 'src' directory.
# from common.sound_manager import SoundManager
from level_editor.editor_app import EditorApp

# --- END OF CHANGE ---

if __name__ == '__main__':
    print("Starting Linie 1 Level Editor...")
    try:
        pygame.init() 
        
        # The project root is one level above the 'src' directory
        project_root = os.path.dirname(src_dir)
        # sounds = SoundManager(project_root)
        # sounds.load_sounds()
        # sounds.play_music('main_theme')
        
        app = EditorApp()
        app.run()
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()