import random
from enum import Enum, auto
from typing import List, Dict, Tuple, Optional, Set, Any

# --- Constants --- (Keep all constants from Phase 0, including corrected BUILDING_COORDS)
GRID_ROWS = 12
GRID_COLS = 12
BUILDING_COORDS: Dict[str, Tuple[int, int]] = {
    'A': (7, 11), 'B': (10, 8), 'C': (11, 4), 'D': (7, 1),
    'E': (4, 0),  'F': (1, 3),  'G': (0, 7),  'H': (3, 10),
    'I': (5, 8),  'K': (8, 6),  'L': (6, 3),  'M': (3, 5),
}
TILE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    # Corrected keys as per previous step
    "Straight":           {"connections": [['N', 'S']], "is_swappable": True},
    "Curve":              {"connections": [['N', 'E']], "is_swappable": True},
    "StraightLeftCurve":  {"connections": [['N', 'S'], ['S', 'W']], "is_swappable": True},
    "StraightRightCurve": {"connections": [['N', 'S'], ['S', 'E']], "is_swappable": True},
    "DoubleCurveY":       {"connections": [['N', 'W'], ['N', 'E']], "is_swappable": True},
    "DiagonalCurve":      {"connections": [['S', 'W'], ['N', 'E']], "is_swappable": True},
    "Tree_JunctionTop":      {"connections": [['E', 'W'], ['W', 'N'], ['N', 'E']], "is_swappable": False},
    "Tree_JunctionRight":    {"connections": [['E', 'W'], ['N', 'E'], ['S', 'E']], "is_swappable": False},
    "Tree_Roundabout":       {"connections": [['W', 'N'], ['N', 'E'], ['E', 'S'], ['S', 'W']], "is_swappable": False},
    "Tree_Crossroad":        {"connections": [['N', 'S'], ['E', 'W']], "is_swappable": False},
    "Tree_StraightDiagonal1":{"connections": [['N', 'S'], ['S', 'W'], ['N', 'E']], "is_swappable": False},
    "Tree_StraightDiagonal2":{"connections": [['N', 'S'], ['N', 'W'], ['S', 'E']], "is_swappable": False},
}
TILE_COUNTS_BASE: Dict[str, int] = {
    "Straight": 21, "Curve": 20, "StraightLeftCurve": 10, "StraightRightCurve": 10,
    "DoubleCurveY": 10, "DiagonalCurve": 6, "Tree_JunctionTop": 6, "Tree_JunctionRight": 6,
    "Tree_Roundabout": 4, "Tree_Crossroad": 4, "Tree_StraightDiagonal1": 2, "Tree_StraightDiagonal2": 2,
}
TILE_COUNTS_5_PLUS_ADD: Dict[str, int] = {"Straight": 15, "Curve": 10,}
STARTING_HAND_TILES: Dict[str, int] = {"Straight": 3, "Curve": 2,}

# --- New Route Card Structure ---
# List index (0-5) represents the 6 unique physical Route Cards.
# Each card defines stops for ALL lines, separated by player count.
ROUTE_CARD_VARIANTS: List[Dict[str, Dict[int, List[str]]]] = [
    # Variant 0 (Corresponds to Card 1 in images)
    {
        "2-4": { 1: ['A', 'F'], 2: ['G', 'L'], 3: ['C', 'F'], 4: ['D', 'F'], 5: ['A', 'L'], 6: ['C', 'E'] },
        "5-6": { 1: ['A', 'C', 'L'], 2: ['C', 'G', 'K'], 3: ['D', 'H', 'I'], 4: ['C', 'E', 'M'], 5: ['A', 'B', 'M'], 6: ['E', 'I', 'K'] }
    },
    # Variant 1 (Corresponds to Card 2 in images)
    {
        "2-4": { 1: ['F', 'K'], 2: ['F', 'H'], 3: ['A', 'C'], 4: ['D', 'K'], 5: ['D', 'G'], 6: ['E', 'H'] },
        "5-6": { 1: ['B', 'G', 'L'], 2: ['B', 'L', 'M'], 3: ['C', 'I', 'M'], 4: ['A', 'D', 'M'], 5: ['A', 'G', 'K'], 6: ['B', 'F', 'M'] }
    },
    # Variant 2 (Corresponds to Card 3 in images)
    {
        "2-4": { 1: ['C', 'M'], 2: ['F', 'L'], 3: ['H', 'K'], 4: ['E', 'K'], 5: ['D', 'I'], 6: ['B', 'L'] },
        "5-6": { 1: ['C', 'G', 'M'], 2: ['G', 'H', 'L'], 3: ['C', 'D', 'M'], 4: ['A', 'E', 'I'], 5: ['D', 'F', 'I'], 6: ['E', 'K', 'L'] }
    },
    # Variant 3 (Corresponds to Card 4 in images)
    {
        "2-4": { 1: ['B', 'I'], 2: ['B', 'M'], 3: ['D', 'M'], 4: ['E', 'I'], 5: ['B', 'H'], 6: ['F', 'I'] },
        "5-6": { 1: ['C', 'D', 'I'], 2: ['E', 'G', 'I'], 3: ['D', 'H', 'K'], 4: ['H', 'K', 'L'], 5: ['A', 'E', 'L'], 6: ['A', 'B', 'L'] } # Stops from blue card image
    },
    # Variant 4 (Corresponds to Card 5 in images)
    {
        "2-4": { 1: ['B', 'D'], 2: ['B', 'E'], 3: ['B', 'G'], 4: ['H', 'L'], 5: ['A', 'M'], 6: ['A', 'D'] },
        "5-6": { 1: ['F', 'I', 'K'], 2: ['F', 'H', 'K'], 3: ['G', 'M', 'L'], 4: ['E', 'F', 'K'], 5: ['E', 'H', 'K'], 6: ['B', 'F', 'I'] } # Stops from blue card image
    },
    # Variant 5 (Corresponds to Card 6 in images)
    {
        "2-4": { 1: ['C', 'I'], 2: ['G', 'K'], 3: ['E', 'G'], 4: ['C', 'H'], 5: ['H', 'M'], 6: ['A', 'G'] },
        "5-6": { 1: ['F', 'H', 'K'], 2: ['C', 'F', 'I'], 3: ['B', 'H', 'L'], 4: ['D', 'I', 'M'], 5: ['A', 'L', 'M'], 6: ['B', 'F', 'I'] } # Stops from blue card image
    },
]

# --- Enums --- (Keep from Phase 0)
class PlayerState(Enum): LAYING_TRACK = auto(); DRIVING = auto(); FINISHED = auto()
class GamePhase(Enum): SETUP = auto(); LAYING_TRACK = auto(); DRIVING_TRANSITION = auto(); DRIVING = auto(); GAME_OVER = auto()
class Direction(Enum): NORTH = (-1, 0); EAST  = (0, 1); SOUTH = (1, 0); WEST  = (0, -1)

# --- Data Classes --- (Keep TileType, PlacedTile, Board, LineCard, Player from previous version)
# --- Make sure TileType uses is_swappable in __init__ and repr ---
class TileType:
    def __init__(self, name: str, connections: List[List[str]], is_swappable: bool): # Corrected signature
        self.name = name
        self.connections = self._process_connections(connections)
        self.is_swappable = is_swappable # Use the corrected argument name
    def _process_connections(self, raw_connections: List[List[str]]) -> Dict[str, List[str]]:
        conn_map: Dict[str, List[str]] = {'N': [], 'E': [], 'S': [], 'W': []}
        for path in raw_connections:
            for i in range(len(path)):
                current_node = path[i]
                for j in range(len(path)):
                    if i == j: continue
                    other_node = path[j]
                    if other_node not in conn_map[current_node]:
                         conn_map[current_node].append(other_node)
        return conn_map
    def __repr__(self) -> str:
         return f"TileType({self.name}, Swappable={self.is_swappable})"

class PlacedTile: # Keep as is
    def __init__(self, tile_type: TileType, orientation: int = 0):
        self.tile_type = tile_type; self.orientation = orientation % 360
        self.has_stop_sign: bool = False
    def __repr__(self) -> str: return f"Placed({self.tile_type.name}, {self.orientation}deg, Stop:{self.has_stop_sign})"

class Board: # Keep as is
    def __init__(self, rows: int = GRID_ROWS, cols: int = GRID_COLS):
        self.rows = rows; self.cols = cols
        self.grid: List[List[Optional[PlacedTile]]] = [[None for _ in range(cols)] for _ in range(rows)]
        self.building_coords = BUILDING_COORDS
        self.buildings_with_stops: Set[str] = set()
    def __repr__(self) -> str: return f"Board({self.rows}x{self.cols})"

class LineCard: # Keep as is
    def __init__(self, line_number: int): self.line_number = line_number
    def __repr__(self) -> str: return f"LineCard(Line {self.line_number})"

# Modify RouteCard slightly - player_range is now implicit
class RouteCard:
    def __init__(self, stops: List[str], variant_index: int):
        self.stops = stops # List of building IDs in ORDER
        self.variant_index = variant_index # Store which of the 6 base cards it came from

    def __repr__(self) -> str:
        # Player range is determined by game context, not stored here anymore
        return f"RouteCard({'-'.join(self.stops)}, From Variant {self.variant_index})"

class Player: # Keep as is
    def __init__(self, player_id: int):
        self.player_id = player_id; self.hand: List[TileType] = []
        self.line_card: Optional[LineCard] = None; self.route_card: Optional[RouteCard] = None
        self.player_state: PlayerState = PlayerState.LAYING_TRACK
        self.streetcar_position: Optional[Tuple[int, int]] = None
        self.stops_visited_in_order: List[str] = []
    def __repr__(self) -> str: return f"Player {self.player_id} (State: {self.player_state.name}, Hand: {len(self.hand)})"

class Game:
    """Manages the overall game state and flow."""
    def __init__(self, num_players: int):
        # ... (initialization checks, board, players as before) ...
        if not 2 <= num_players <= 6:
            raise ValueError("Number of players must be between 2 and 6.")
        self.num_players = num_players

        self.board = Board()
        self.players = [Player(i) for i in range(num_players)]

        self.tile_types: Dict[str, TileType] = {
            name: TileType(name=name, **details)
            for name, details in TILE_DEFINITIONS.items()
        }
        self.tile_draw_pile: List[TileType] = []
        self.line_cards_pile: List[LineCard] = []
        # No route card pile needed here anymore

        self.active_player_index: int = 0
        self.game_phase: GamePhase = GamePhase.SETUP
        self.current_turn: int = 0
        self.first_player_to_finish_route: Optional[int] = None

        # --- Call Setup ---
        self.setup_game()

    def get_active_player(self) -> Player:
        return self.players[self.active_player_index]

    def __repr__(self) -> str:
        return f"Game({self.num_players} players, Phase: {self.game_phase.name}, Turn: {self.current_turn}, Active: P{self.active_player_index})"

    # --- Phase 1: Setup Methods ---

    def setup_game(self):
        """Orchestrates the game setup process."""
        if self.game_phase != GamePhase.SETUP:
            print("Warning: Game setup already completed or in progress.")
            return

        print("--- Starting Game Setup ---")
        self._create_tile_and_line_piles() # Renamed
        self._deal_starting_hands()
        self._deal_player_cards() # Logic completely changed

        self.game_phase = GamePhase.LAYING_TRACK
        self.active_player_index = 0
        self.current_turn = 1
        print("--- Game Setup Complete ---")

    def _create_tile_and_line_piles(self): # Renamed, removed route pile creation
        """Creates and shuffles the tile and line card draw piles."""
        # 1. Tile Pile (Same as before)
        tile_counts = TILE_COUNTS_BASE.copy()
        if self.num_players >= 5:
            for tile_name, count in TILE_COUNTS_5_PLUS_ADD.items():
                tile_counts[tile_name] = tile_counts.get(tile_name, 0) + count
        self.tile_draw_pile = []
        for tile_name, count in tile_counts.items():
            tile_type = self.tile_types.get(tile_name)
            if tile_type: self.tile_draw_pile.extend([tile_type] * count)
            else: print(f"Warning: Tile type '{tile_name}' not found.")
        random.shuffle(self.tile_draw_pile)
        print(f"Created tile draw pile with {len(self.tile_draw_pile)} tiles.")

        # 2. Line Card Pile (Same as before)
        self.line_cards_pile = [LineCard(i) for i in range(1, 7)]
        random.shuffle(self.line_cards_pile)
        print(f"Created line card pile with {len(self.line_cards_pile)} cards.")

    def _deal_starting_hands(self): # Same logic as before
        """Deals starting tiles (3 Straight, 2 Curve) and removes them from draw pile."""
        print("Dealing starting hands...")
        straight_type = self.tile_types['Straight']
        curve_type = self.tile_types['Curve']
        for player in self.players:
            player.hand = []
            needed = STARTING_HAND_TILES.copy()
            indices_to_remove = []
            found_indices = {'Straight': [], 'Curve': []}
            # Iterate through a copy to find indices in the original pile
            for i, tile in enumerate(self.tile_draw_pile):
                 if tile == straight_type and needed['Straight'] > 0:
                      found_indices['Straight'].append(i)
                      needed['Straight'] -= 1
                 elif tile == curve_type and needed['Curve'] > 0:
                      found_indices['Curve'].append(i)
                      needed['Curve'] -= 1
                 if needed['Straight'] == 0 and needed['Curve'] == 0: break

            if needed['Straight'] > 0 or needed['Curve'] > 0:
                 raise RuntimeError(f"Could not find enough starting tiles for Player {player.player_id}!")

            indices_to_remove = sorted(found_indices['Straight'] + found_indices['Curve'], reverse=True)
            if len(indices_to_remove) != sum(STARTING_HAND_TILES.values()):
                 raise RuntimeError(f"Logic error finding start tiles for Player {player.player_id}!")

            for index in indices_to_remove: player.hand.append(self.tile_draw_pile[index])
            for index in indices_to_remove: del self.tile_draw_pile[index]
        print(f"Finished dealing starting hands. Draw pile size: {len(self.tile_draw_pile)}")


    def _deal_player_cards(self): # *** ENTIRELY NEW LOGIC ***
        """Deals LineCard and determines RouteCard based on unique variants."""
        print("Dealing Line and Route cards...")
        if len(self.line_cards_pile) < self.num_players:
            raise RuntimeError("Not enough Line cards to deal to all players!")

        # Shuffle the indices representing the 6 unique Route Card variants
        available_variant_indices = list(range(len(ROUTE_CARD_VARIANTS)))
        random.shuffle(available_variant_indices)

        if len(available_variant_indices) < self.num_players:
             raise RuntimeError("Not enough Route Card variants for the number of players!") # Should not happen with 6 variants

        # Determine player range string once
        player_range = "2-4" if self.num_players <= 4 else "5-6"

        dealt_variants = [] # For tracking in tests

        for player in self.players:
            # 1. Deal Line Card
            player.line_card = self.line_cards_pile.pop()

            # 2. Deal a unique Route Card variant index
            variant_index = available_variant_indices.pop()
            dealt_variants.append(variant_index) # Track for testing

            # 3. Look up the specific stops based on Line#, variant index, and player range
            try:
                variant_data = ROUTE_CARD_VARIANTS[variant_index]
                stops = variant_data[player_range][player.line_card.line_number]
            except (KeyError, IndexError) as e:
                raise RuntimeError(f"Error looking up route card stops: Variant={variant_index}, Range={player_range}, Line={player.line_card.line_number}. Error: {e}")

            # 4. Create and assign the RouteCard
            player.route_card = RouteCard(stops, variant_index)

            # print(f"  Player {player.player_id}: {player.line_card}, {player.route_card}") # Detailed check

        print(f"Finished dealing cards. Dealt Route Variants: {sorted(dealt_variants)}")


# --- Example Initialization and Testing Phase 1 (Adjusted Tests) ---
if __name__ == "__main__":
    print("--- Testing Phase 1 (Corrected Route Card Logic) ---\n")

    try:
        # Test with 4 players (should use 2-stop routes from unique variants)
        print("== Test Case: 4 Players ==")
        game4 = Game(num_players=4)
        print(game4)
        total_starting_tiles = sum(STARTING_HAND_TILES.values()) * game4.num_players
        expected_draw_pile_size = sum(TILE_COUNTS_BASE.values()) - total_starting_tiles
        print(f"Expected Draw Pile Size: {expected_draw_pile_size}")
        print(f"Actual Draw Pile Size: {len(game4.tile_draw_pile)}")
        assert len(game4.tile_draw_pile) == expected_draw_pile_size, "Draw pile size mismatch!"

        assigned_lines = set()
        assigned_variants = set()
        for i, p in enumerate(game4.players):
            print(f" Player {i}: Hand Size={len(p.hand)}, Line={p.line_card}, Route={p.route_card}")
            assert len(p.hand) == sum(STARTING_HAND_TILES.values()), f"Player {i} hand size wrong!"
            assert p.line_card is not None
            assert p.route_card is not None
            assert len(p.route_card.stops) == 2 # 2-4 players -> 2 stops
            assigned_lines.add(p.line_card.line_number)
            assigned_variants.add(p.route_card.variant_index)
        assert len(assigned_lines) == game4.num_players, "Line numbers not unique!"
        assert len(assigned_variants) == game4.num_players, "Route card variants not unique!"
        print("4 Player Test OK\n")

        # Test with 5 players (should use 3-stop routes from unique variants)
        print("== Test Case: 5 Players ==")
        game5 = Game(num_players=5)
        print(game5)
        total_starting_tiles_5p = sum(STARTING_HAND_TILES.values()) * game5.num_players
        base_tiles = sum(TILE_COUNTS_BASE.values())
        extra_tiles = sum(TILE_COUNTS_5_PLUS_ADD.values())
        expected_draw_pile_size_5p = base_tiles + extra_tiles - total_starting_tiles_5p
        print(f"Expected Draw Pile Size: {expected_draw_pile_size_5p}")
        print(f"Actual Draw Pile Size: {len(game5.tile_draw_pile)}")
        assert len(game5.tile_draw_pile) == expected_draw_pile_size_5p, "Draw pile size mismatch!"

        assigned_lines_5p = set()
        assigned_variants_5p = set()
        for i, p in enumerate(game5.players):
            print(f" Player {i}: Hand Size={len(p.hand)}, Line={p.line_card}, Route={p.route_card}")
            assert len(p.hand) == sum(STARTING_HAND_TILES.values()), f"Player {i} hand size wrong!"
            assert p.line_card is not None
            assert p.route_card is not None
            assert len(p.route_card.stops) == 3 # 5-6 players -> 3 stops
            assigned_lines_5p.add(p.line_card.line_number)
            assigned_variants_5p.add(p.route_card.variant_index)
        assert len(assigned_lines_5p) == game5.num_players, "Line numbers not unique!"
        assert len(assigned_variants_5p) == game5.num_players, "Route card variants not unique!"
        print("5 Player Test OK\n")

    except (ValueError, RuntimeError) as e:
        print(f"Error during setup test: {e}")