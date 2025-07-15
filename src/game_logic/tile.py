# game_logic/tile.py
from typing import List, Dict, Optional, Any
import copy
# Assuming constants like TILE_DEFINITIONS might be needed here or passed in
# If constants are needed, import them: from constants import ...

class TileType:
    def __init__(self, name: str, connections: List[List[str]], is_swappable: bool):
        self.name = name
        self.connections_base = self._process_connections(connections)
        self.is_swappable = is_swappable

    def copy(self) -> 'TileType':
        """Creates a deep copy of this TileType object."""
        # We can use Python's built-in copy module for a true deep copy.
        return copy.deepcopy(self)

    def _process_connections(self, raw_connections: List[List[str]]) -> Dict[str, List[str]]:
        """Processes raw connection pairs into a two-way connection map."""
        conn_map: Dict[str, List[str]] = {'N': [], 'E': [], 'S': [], 'W': []}
        processed_pairs = set() # Keep track of pairs to avoid duplicates

        for path in raw_connections:
            # Assuming each sublist in raw_connections defines ONE connection pair, e.g., ['N', 'S'] or ['N', 'E']
            if len(path) == 2:
                node1, node2 = path[0], path[1]
                pair = frozenset((node1, node2)) # Use frozenset for unordered pair tracking

                if pair not in processed_pairs:
                    # Add connection in both directions
                    if node2 not in conn_map[node1]:
                        conn_map[node1].append(node2)
                    if node1 not in conn_map[node2]:
                        conn_map[node2].append(node1)
                    processed_pairs.add(pair)
            # Handle more complex paths (like 3-way junctions) if needed
            elif len(path) > 2:
                 # Example for a T-junction N-S, S-E defined as ['N', 'S', 'E']?
                 # This interpretation might need adjustment based on TILE_DEFINITIONS format
                 # Assuming N-S is one path, S-E is another
                 # Add N <-> S
                 if 'S' not in conn_map['N']: conn_map['N'].append('S')
                 if 'N' not in conn_map['S']: conn_map['S'].append('N')
                 # Add S <-> E
                 if 'E' not in conn_map['S']: conn_map['S'].append('E')
                 if 'S' not in conn_map['E']: conn_map['E'].append('S')
                 # Maybe N<->E too? Depends on how junctions are defined.
                 # Let's stick to the explicit pairs from constants for now.

        # Re-check constants.py TILE_DEFINITIONS format
        # If TILE_DEFINITIONS["Straight"] = {"connections": [['N', 'S']], ...}
        # The code above works.

        # If TILE_DEFINITIONS["Tree_JunctionTop"] = {"connections": [['E', 'W'], ['W', 'N'], ['N', 'E']], ...}
        # The code above works for this too.

        # Sort for consistency
        for key in conn_map:
            conn_map[key].sort()
        return conn_map

    def __repr__(self) -> str: return f"TileType({self.name}, Swappable={self.is_swappable})"
    def __eq__(self, other): 
        if isinstance(other, TileType): 
            return self.name == other.name
        return NotImplemented
    def __hash__(self): return hash(self.name)


class PlacedTile:
    def __init__(self, tile_type: TileType, orientation: int = 0, is_terminal: bool = False):
        self.tile_type = tile_type
        # if orientation % 90 != 0:
        #     raise ValueError(f"Orientation must be multiple of 90, got {orientation}")
        self.orientation = orientation % 360
        self.has_stop_sign: bool = False
        self.is_terminal: bool = is_terminal
        self.is_terminal: bool = is_terminal
    def __repr__(self) -> str: # ... implementation ...
        term_str = " Term" if self.is_terminal else ""; stop_str = " Stop" if self.has_stop_sign else ""; return f"Placed({self.tile_type.name}, {self.orientation}deg{term_str}{stop_str})"
    def to_dict(self) -> Dict: # ... implementation ...
        return {"type_name": self.tile_type.name, "orientation": self.orientation, "has_stop_sign": self.has_stop_sign, "is_terminal": self.is_terminal,}
    @staticmethod
    def from_dict(data: Optional[Dict], tile_types: Dict[str, 'TileType']) -> Optional['PlacedTile']: # ... implementation ...
        if data is None: return None
        tile_type = tile_types.get(data.get("type_name")); # ... rest of implementation ...
        if not tile_type: return None
        try:
             orientation = int(data.get("orientation", 0)); # ... rest of implementation ...
             tile = PlacedTile(tile_type, orientation, data.get("is_terminal", False)); # ... rest of implementation ...
             tile.has_stop_sign = data.get("has_stop_sign", False); return tile
        except Exception as e: print(f"Error creating PlacedTile from dict {data}: {e}"); return None
