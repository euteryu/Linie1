# Linie 1: Game Overview

Linie 1 is a board game about building a streetcar network. Players collaborate to lay track tiles, but each player has a secret route they are trying to complete first.

Aim of the Game:

Be the first player to successfully run your streetcar along a continuous path of track from one of your assigned terminal entry points to the other, stopping at a specific set of required building locations along the way, in the exact order specified by your secret route card.

Components:

    Game Board (a grid of cobblestone squares with building markers and terminal areas around the edge)

    Track Tiles (various shapes: straights, curves, junctions)

    Stop Signs

    White Blocks (used with streetcars, not relevant for initial logic)

    Streetcar Stickers (for player streetcars)

    Route Cards (secret, define required stops)

    Line Cards (secret, define assigned terminals)

    Special Die (used in the second phase)

Player Count:

The game is designed for 2 to 5 players, with a variant for 6 players mentioned.

    2-4 Players: Use blue-framed Route Cards. Each player's route requires stopping at 2 specific buildings.

    5-6 Players: Use red-framed Route Cards. Each player's route requires stopping at 3 specific buildings.

    The total number of track tiles available in the draw pile also increases for 5-6 players (15 extra Straight, 10 extra Curve tiles).

Setup:

    Place the Game Board in the center of the play area.

    Sort Track Tiles into two piles: Starting Tiles (darker backs: 3 Straights, 2 Curves per player) and Main Draw Pile (lighter backs). Return extra starting tiles to the box.

    Shuffle the Main Draw Pile (lighter back tiles) face down and form 4 stacks next to the board.

    Each player takes 3 Straight and 2 Curve tiles from the Starting Tiles pile. These form their initial hand. (These are removed from the total tile count available).

    Shuffle the Line Cards and deal one face down to each player. Players keep this secret.

    Sort the Route Cards by frame color (blue/red). Use the appropriate set for the number of players. Shuffle the relevant Route Cards and deal one face down to each player. Players keep this secret.

    Unused Line and Route cards are returned face down to the box.

    Place Stop Signs and the Special Die near the board.

    Players choose their Streetcar (using stickers and white blocks) and place it near the board.

Gameplay - General:

The game proceeds in two main parts:

    Part 1: Laying Track: Players take turns placing and exchanging track tiles to build the network. This continues until at least one player has completed their secret route.

    Part 2: The Inaugural Trip: Players who have completed their routes stop laying track and instead use their turns to roll the special die and move their streetcar along their completed route. Players who haven't finished their routes continue laying track.

The first player to successfully complete their trip (reach their destination terminal) wins.

Gameplay - Part 1: Laying Track

    Players take turns clockwise. The oldest player starts.

    On your turn, you have 2 actions. An action can be either:

        Place a new tile: Choose one tile from your hand, choose an orientation (0, 90, 180, 270 degrees clockwise), and place it onto an empty square on the board.

        Exchange an existing tile: Choose one tile from your hand, choose an orientation, and replace an existing tile on the board with it.

    After taking your 2 actions (or fewer if you cannot make valid moves), you draw 2 tiles from the main draw stacks back into your hand, if available. Your hand size is normally 5 tiles at the start of your turn.

Rules for Placing a New Tile:

A tile placement onto an empty square is invalid if:

    It is placed outside the 12x12 cobblestone grid area.

    It is placed directly on a square occupied by a building marker (A-M coordinates).

    It is placed on a square already occupied by another tile.

    Any track segment on the new tile points directly towards an adjacent square that is a building marker location.

    Any track segment on the new tile points off the edge of the board, unless that edge is a defined entry/exit point for a terminal.

    It is placed adjacent to an existing track tile, and the connections do not match at the shared border (i.e., one tile has track pointing towards the border, but the other does not have track pointing back from that border). Both sides of a shared border must either connect track-to-track or have no track connecting (empty-to-empty conceptually).

Stop Sign Placement (Automatic Consequence):

    Immediately after a tile is successfully placed on an empty square (not exchanged), check its orthogonal neighbors (North, East, South, West).

    If a neighbor is a building marker location, check if that building marker does not already have a stop sign associated with it.

    If both conditions above are true, check if the placed tile contains a straight track segment that is parallel to the shared edge with that building marker.

        If the building is North or South of the tile, the tile needs an E-W straight segment.

        If the building is East or West of the tile, the tile needs an N-S straight segment.

    If all conditions (orthogonal adjacency, no existing stop sign for building, AND parallel straight track segment on the new tile) are met, place a stop sign token on the tile you just placed.

    A building marker can only ever have one stop sign associated with it for the entire game.

Rules for Exchanging an Existing Tile:

An exchange action (replacing an existing tile with one from your hand) is invalid if:

    There is no tile at the target location.

    The existing tile at the target location is a "Tree" tile (non-swappable).

    The existing tile at the target location currently has a Stop Sign on it.

    You do not have the chosen new tile type in your hand.

    The new tile, in its chosen orientation, does not preserve every single track connection that the original tile had.

    The new tile, in its chosen orientation, adds any new track connection that is invalid with respect to its neighbors after the swap (e.g., the added connection points into a building, off the board illegally, or mismatches/blocks an existing neighbor track).

Route Completion Check (End of Part 1):

    At the start of your turn, if you are currently in the LAYING_TRACK phase, you check if your secret route is complete.

    A route is complete if there is a continuous track path connecting:

        One of your assigned terminal entry points ->

        The tile with the stop sign for your first required building stop ->

        The tile with the stop sign for your second required building stop ->

        (... and so on for all required stops in the exact order listed on your route card) ->

        Your other assigned terminal entry point.

    Crucially, the tiles with the stop signs for all your required buildings must actually be on the board and have their stop signs placed.

    You must be able to trace this path sequentially from the first point to the last.

Gameplay - Part 2: The Inaugural Trip

    When a player successfully completes their route check at the start of their turn, they immediately transition to the DRIVING state. They reveal their Line and Route cards and show their path.

    The first player to complete their route triggers this transition and potentially changes the overall Game Phase (though other players might continue laying track).

    On a player's turn in the DRIVING state, they do not lay or exchange tiles.

    Instead, they roll the Special Die (faces: 1, 2, 3, 4, H, H).

    If a number (1-4) is rolled, the player moves their streetcar exactly that many track segments along their declared route, starting from their current position.

    If 'H' is rolled, the player moves their streetcar along their route to the next Stop Sign tile or Terminal tile, regardless of whether that stop/terminal is on their route card.

    Movement Rules:

        Movement must follow the track exactly.

        Movement is always forward along the path. You cannot reverse direction on a turn.

        You cannot make turns that are not supported by the track layout (e.g., turn 90 degrees onto an empty adjacent square if the tile only has a straight track segment).

        Streetcars can occupy the same space.

        Moving onto a terminal counts as one movement space.

Winning:

The first player whose streetcar successfully reaches their destination terminal (the second terminal listed for their line, having visited all required stops in order) wins the game immediately. You do not need to land on the terminal by exact count.
Digital Implementation Guide for an LLM Programmer

This section translates the game rules into specific requirements and checks for a digital Python implementation.

1. Game State Representation:

    Board: A 2D grid (e.g., List[List[Optional[PlacedTile]]]) representing the 12x12 cobblestone squares.

    Buildings: A dictionary mapping building IDs ('A' through 'M', skipping 'J') to their specific (row, col) grid coordinates (Dict[str, Tuple[int, int]]). Note that buildings occupy squares on the grid.

    Terminals: A dictionary mapping line numbers (1-6) to a tuple of their two (row, col) grid coordinates where a connecting track must terminate.

    Tile Types: A class (TileType) for each of the 12 unique tile types. Each instance needs:

        name (e.g., "Straight", "Curve", "Tree_Crossroad").

        connections_base: A representation of its track connectivity in a base orientation (e.g., Dict[str, List[str]] like {'N': ['S'], 'S': ['N']} for Straight, or {'N': ['E'], 'E': ['N']} for Curve, or {'N': ['S'], 'S': ['N', 'W'], 'W': ['S'], 'E': []} for StraightLeftCurve). Ensure consistency in how connections are represented (e.g., always sorted).

        is_swappable: A boolean.

    Placed Tiles: A class (PlacedTile) representing a tile on the board. Each instance needs:

        A reference to its TileType.

        orientation: An integer (0, 90, 180, 270).

        has_stop_sign: A boolean.

    Players: A class (Player) for each player. Each instance needs:

        player_id (e.g., 0, 1, 2...).

        hand: A list of TileType instances.

        line_card: A LineCard object (stores line number).

        route_card: A RouteCard object (stores an ordered List[str] of building IDs).

        player_state: An Enum (LAYING_TRACK, DRIVING, FINISHED).

        streetcar_position: Optional[Tuple[int, int]] when driving.

        stops_visited_in_order: A list of building IDs visited in the correct order during the driving phase (needed for strict route validation during the trip).

    Game: A class (Game) managing the overall state:

        List of Player objects.

        The Board object.

        tile_draw_pile: List[TileType] (shuffled).

        line_cards_pile, route_cards_pile (List of card objects, shuffled).

        active_player_index.

        game_phase: An Enum (SETUP, LAYING_TRACK, DRIVING, GAME_OVER).

        actions_taken_this_turn.

        first_player_to_finish_route: Optional[int].

        board.buildings_with_stops: Set[str] (building IDs that already have a stop sign).

        board.building_stop_locations: Dict[str, Tuple[int, int]] (mapping building ID to the (row, col) of the tile with its stop sign).

2. Core Mechanics - Phase 1: Laying Track Logic

    Helper: get_effective_connections(tile_type, orientation):

        Input: TileType instance and orientation.

        Output: A Dict[str, List[str]] representing the tile's connections rotated to the given orientation. For a Straight N-S at 90°, this would be {'E': ['W'], 'W': ['E'], 'N': [], 'S': []}. This is crucial for checking validity and pathfinding. Must handle all 12 tile types correctly.

    Helper: _has_ns_straight(connections) and _has_ew_straight(connections):

        Input: A Dict[str, List[str]] of connections (either base or effective).

        Output: Boolean indicating if there's a connection pair ('N', 'S') or ('S', 'N') (for N-S) or ('E', 'W') or ('W', 'E') (for E-W) within the connections. Note: _process_connections should store pairs consistently (e.g., always sorted) or these helpers need to check both orders. Checking S in connections.get('N', []) is a common way if N-S implies S-N.

    Function: check_placement_validity(tile_type, orientation, row, col):

        Input: TileType, orientation, target (row, col).

        Output: Tuple[bool, str] (isValid, message).

        Checks (Return False immediately if any fail):

            Is (row, col) off the board?

            Is there a building at (row, col)?

            Is there already a tile at (row, col)?

            Calculate effective_connections for the tile_type at orientation.

            Determine all directions this tile connects out to (all_connected_dirs_out).

            For each direction (N, E, S, W) from (row, col) to a neighbor (nr, nc):

                Is there a neighbor_tile at (nr, nc)?

                    If yes: Get neighbor_effective_connections. Determine if neighbor connects back towards (row, col) (neighbor_connects_back). If new_tile_connects_out_dir != neighbor_connects_back, return False (Mismatch/Blocking).

                If no neighbor tile exists at (nr, nc):

                    If new_tile_connects_out_dir is true:

                        Is (nr, nc) off the board? If yes AND (nr, nc) is not a valid terminal coordinate, return False (Off-board illegally).

                        Is there a building at (nr, nc)? If yes, return False (Points into building illegally).

            If all checks pass for all neighbors, return True.

    Function: player_action_place_tile(player, tile_type, orientation, row, col):

        Input: Player, TileType, orientation, target (row, col).

        Output: bool (success).

        Checks if player.hand contains tile_type.

        Calls check_placement_validity. If False, print message and return False.

        If valid: Remove tile_type from player.hand. Create PlacedTile(tile_type, orientation). Set board.grid[row][col] to the PlacedTile. Call _check_and_place_stop_sign(PlacedTile, row, col). Increment actions_taken_this_turn. Return True.

    Function: _check_and_place_stop_sign(placed_tile, row, col):

        Input: The newly placed PlacedTile, its (row, col).

        Logic: Iterates through orthogonal neighbors of (row, col). If a neighbor (nr, nc) is a building location: Check if building_id at (nr, nc) is NOT in board.buildings_with_stops. If not, get placed_tile.effective_connections. Check if parallel straight exists (_has_ns_straight or _has_ew_straight based on neighbor direction). If parallel straight exists, set placed_tile.has_stop_sign = True, add building_id to board.buildings_with_stops, add building_id -> (row, col) to board.building_stop_locations, and stop checking (only one stop sign per placement).

    Function: check_exchange_validity(player, new_tile_type, new_orientation, row, col):

        Input: Player, TileType from hand, new orientation, target (row, col).

        Output: Tuple[bool, str].

        Checks:

            Is there a tile old_placed_tile at (row, col)?

            Is old_placed_tile.tile_type.is_swappable false?

            Is old_placed_tile.has_stop_sign true?

            Does player.hand contain new_tile_type?

            Get old_connections and new_connections. Check if all connection pairs in old_connections are present in new_connections. If not, return False (Does not preserve connections).

            Identify added connection pairs in new_connections that were not in old_connections. For each direction corresponding to an added connection: Check its validity against the neighbor using the same logic as placing a new tile (off-board, building, mismatch/block). If any added connection is invalid, return False.

            If all checks pass, return True.

    Function: player_action_exchange_tile(player, new_tile_type, new_orientation, row, col):

        Input: Player, TileType from hand, new orientation, target (row, col).

        Output: bool (success).

        Calls check_exchange_validity. If False, print message and return False.

        If valid: Get old_placed_tile. Remove new_tile_type from player.hand. Add old_placed_tile.tile_type to player.hand. Create new_placed_tile(new_tile_type, new_orientation). Set board.grid[row][col] to new_placed_tile. Increment actions_taken_this_turn. Return True.

3. Core Mechanics - Phase 2: Driving Trip Logic

    Helper: find_path_exists(start_row, start_col, end_row, end_col): (Already implemented in Phase 4). Confirms reachability based on track connections.

    Helper: get_terminal_coords(line_number): Returns the (start_coord, end_coord) tuple for the line.

    Function: check_player_route_completion(player):

        Input: Player. Output: bool.

        Get player.line_card.line_number and player.route_card.stops.

        Get terminal coords using get_terminal_coords.

        For each required stop_id in player.route_card.stops, look up its coordinate in board.building_stop_locations. If any stop_id is missing from this dictionary, return False (Required stop sign not placed).

        Construct the sequence of coordinates: [Term1_coord] + [Stop_coords_in_order] + [Term2_coord].

        Check path segments: find_path_exists(seq[i], seq[i+1]) for all i. If any segment fails, Sequence 1 is not complete.

        Construct the reverse sequence: [Term2_coord] + [Stop_coords_in_order] + [Term1_coord].

        Check path segments for the reverse sequence. If any segment fails, Sequence 2 is not complete.

        Return True if Sequence 1 OR Sequence 2 is complete. Return False otherwise.

    Function: handle_route_completion(player):

        Input: Player. Updates player and game state.

        Sets player.player_state = PlayerState.DRIVING.

        Gets terminal coords. Player chooses/defaults to one as player.streetcar_position.

        If first_player_to_finish_route is None, set it to player.player_id and change game_phase to DRIVING (or DRIVING_TRANSITION).

    Function: roll_die(): Returns a random choice from [1, 2, 3, 4, 'H', 'H'].

    Function: get_valid_moves(player, steps): (Needed for actual driving, Phase 6). Calculates possible next positions from player.streetcar_position following track for steps, respecting forward movement only.

    Function: get_next_stop_or_terminal(player): (Needed for 'H' roll, Phase 6). Finds the coordinate of the next stop sign or terminal tile along the player's declared route path from their current position.

    Function: player_action_drive(player): (Needed for driving turn, Phase 6). Rolls die, calls get_valid_moves or get_next_stop_or_terminal, updates player.streetcar_position. Checks if the new position is the destination terminal (Term2 or Term1 depending on start) to determine a win.

4. Game Flow & State Management:

    The main game loop iterates turns.

    At the start of a player's turn:

        If player.player_state == LAYING_TRACK: Check check_player_route_completion. If true, call handle_route_completion, player's turn actions are skipped. If false, player performs 2 actions (player_action_place_tile or player_action_exchange_tile), then end_player_turn draws tiles.

        If player.player_state == DRIVING: Call player_action_drive. end_player_turn does not draw tiles.

        If player.player_state == FINISHED: Skip turn.

    The game ends when player_action_drive determines a player reached their destination terminal.

