# src/levels/level.py
import json
import os
from typing import List, Dict, Any, Optional, Tuple

class Level:
    """
    A data class that loads and holds all the configuration for a single map
    from a .json file.
    """
    def __init__(self, filepath: str):
        """
        Initializes and loads the Level object.
        RAISES FileNotFoundError if the level file cannot be found or parsed.
        """
        self.filepath = filepath
        self.level_name: str = "Unknown"
        self.author: str = "Unknown"
        self.grid_rows: int = 0
        self.grid_cols: int = 0
        self.playable_rows: Tuple[int, int] = (0, 0)
        self.playable_cols: Tuple[int, int] = (0, 0)
        self.building_coords: Dict[str, Tuple[int, int]] = {}
        self.terminal_data: Dict[str, Any] = {}

        print(f"--- Loading level data from: {self.filepath} ---")
        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)

            self.level_name = data["level_name"]
            self.author = data["author"]
            self.grid_rows = data["grid_rows"]
            self.grid_cols = data["grid_cols"]
            self.playable_rows = tuple(data["playable_rows"])
            self.playable_cols = tuple(data["playable_cols"])
            self.building_coords = {k: tuple(v) for k, v in data["building_coords"].items()}
            self.terminal_data = data["terminal_data"]
            
            print(f"--- Level '{self.level_name}' loaded successfully. ---")

        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            # If the file is missing, invalid JSON, or missing a key,
            # print an error and re-raise the exception to signal failure.
            print(f"!!! CRITICAL ERROR: Could not load level file '{self.filepath}'. Reason: {e}")
            raise  # This is the crucial change

    def load(self):
        """Parses the .json file and populates the level data."""
        print(f"--- Loading level data from: {self.filepath} ---")
        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)

            self.level_name = data.get("level_name", "Unnamed Level")
            self.author = data.get("author", "Unknown Author")
            self.grid_rows = data.get("grid_rows", 14)
            self.grid_cols = data.get("grid_cols", 14)
            self.playable_rows = tuple(data.get("playable_rows", [1, 12]))
            self.playable_cols = tuple(data.get("playable_cols", [1, 12]))
            
            # Convert building coordinate lists back to tuples
            self.building_coords = {k: tuple(v) for k, v in data.get("building_coords", {}).items()}
            
            # The editor exports terminal_data, which is what the game needs
            self.terminal_data = data.get("terminal_data", {})
            
            print(f"--- Level '{self.level_name}' loaded successfully. ---")

        except FileNotFoundError:
            print(f"!!! CRITICAL ERROR: Level file not found at '{self.filepath}'.")
        except json.JSONDecodeError:
            print(f"!!! CRITICAL ERROR: Could not parse JSON in level file '{self.filepath}'.")
        except Exception as e:
            print(f"!!! CRITICAL ERROR: An unexpected error occurred loading level: {e}")

    @classmethod
    def scan_for_levels(cls, levels_dir: str) -> List[str]:
        """
        Scans the specified directory and returns a list of all found .json level files.

        Args:
            levels_dir (str): The absolute path to the 'src/levels' directory.

        Returns:
            List[str]: A list of filenames (e.g., ['default_12x12.json', 'tiny_5x5.json']).
        """
        if not os.path.isdir(levels_dir):
            print(f"WARNING: Levels directory not found at '{levels_dir}'")
            return []
        
        found_levels = [f for f in os.listdir(levels_dir) if f.endswith('.json')]
        print(f"--- Discovered {len(found_levels)} level files. ---")
        return found_levels