looks like we already have established rules and code for tile replacement below!
Of course. Here is a detailed breakdown of the tile replacement/exchange rule in Linie 1, formatted to be clear for a third party or another LLM.
Linie 1: Tile Replacement (Exchange) Rule

Core Concept & Purpose:
During the "Laying Track" phase of the game, a player can use one of their two actions per turn to replace an existing tile on the board with a tile from their hand. This is a strategic move used to:
Re-route a track that is going in an unhelpful direction.
Add more connections to an existing intersection to benefit your own path.
Fix a section of track you previously placed incorrectly.
Potentially block an opponent's path (though this is often a secondary effect).
When Can You Replace a Tile?

A player can use one of their two actions to replace a tile if all the following conditions are met:
It is the player's turn.
The player is in the "Laying Track" phase (i.e., they have not yet declared their route complete and started driving).
The tile they want to replace is already on the board.
The player has the new tile they want to place in their hand.
What Tiles CANNOT Be Replaced? (The Restrictions)

A tile on the board is permanently locked and cannot be replaced if it meets any of these criteria:
It has a Stop Sign on it: Once a tile receives a stop sign for a building, it is locked in place for the rest of the game. This prevents players from moving the "official" stop for a building.
It is a "Tree" Tile: Certain special tiles (typically with a small tree icon printed on them) are designated as non-swappable. Once placed, they are permanent. In our code, this is handled by the TileType.is_swappable = False attribute.
It is a Terminal Tile: The initial terminal tiles placed on the border of the board during setup cannot be replaced.
It has a Tram on it: During Phase 2 (Driving), if a player's tram is currently on a tile, that tile cannot be exchanged by another player.
The "Preservation of Connections" Rule (The Most Important Constraint):
This is the most critical rule for a valid exchange. When replacing an old tile with a new one, the new tile must respect and preserve ALL existing track connections that the old tile had with its neighbors.
In simpler terms: If the old tile had a track leading North, the new tile (in its chosen orientation) must also have a track leading North to connect to the northern neighbor. If the old tile connected East to West, the new tile must also connect East to West.
Adding Connections: The new tile is allowed to have additional connections that the old tile did not have. For example, you can replace a "Straight" tile (connecting North-South) with a "Crossing" tile (connecting North-South and East-West). This is a valid exchange because the original North-South connection is preserved.
New Connection Validity: Any new connections created by the new tile must also be valid. For example, if you replace a Straight (N-S) with a Crossing (N-S, E-W) at a location where the eastern neighbor is a building, the exchange is invalid because the new East-facing track would point into a building. The validity of these new connections must be checked using the same rules as placing a brand new tile.

How the Exchange Works (Player's Action):
Player announces they are using an action to exchange a tile.
They choose a tile from their hand (the new tile).
They choose an eligible tile on the board to replace (the old tile).
They pick up the old tile from the board and place it into their hand.
They place the new tile from their hand onto the now-empty square in their chosen orientation.
This counts as one action.
Algorithmic Steps for check_exchange_validity(player, new_tile_type, new_orientation, row, col):
To verify if an exchange is legal, the program must check:
Get old_placed_tile: Retrieve the tile currently at (row, col) on the board.

Check Ineligibility:
if old_placed_tile is None: -> Fail (nothing to exchange).
if old_placed_tile.has_stop_sign: -> Fail.
if not old_placed_tile.tile_type.is_swappable: -> Fail ("Tree" tile).
if old_placed_tile.is_terminal: -> Fail.
if any_tram_is_at(row, col): -> Fail.
Check Hand: if new_tile_type not in player.hand: -> Fail.

Check Connection Preservation:
Get old_connections using get_effective_connections(old_placed_tile.tile_type, old_placed_tile.orientation).
Get new_connections using get_effective_connections(new_tile_type, new_orientation).
For every connection pair in old_connections (e.g., N connects to S), verify that the same connection pair exists in new_connections. If any old connection is missing from the new one, -> Fail. A good way to do this is to get a set of connection pairs for each and check if old_set.issubset(new_set).

Check New Connection Validity:
Identify which connections are new (i.e., exist in new_connections but not old_connections).

For each new_exit_direction:
Find the neighbor in that direction.
Check if connecting to that neighbor is valid (i.e., the neighbor is not a building, the neighbor is not an empty border square, or if it's another tile, that it has a connection pointing back). If any new connection is invalid, -> Fail.
If all these checks pass, the exchange is valid.

I'm curious - how do we currently handle orientations - say a curve tile connecting n and e, i suppose this is at orientation 0 at default? then when we wanna rotate that tile 270 degrees, how does code figure out which ports are now connected at that new orientation atm? like does code look at default and see "hmm 270 degrees from n would be this direction, and from e another direction etc.?" And Can clever mathematical / programming index / etc. any optimisations be made to here perhaps?


Regarding what happens on a given player turn - you perform two of the following actions: place or exchange. Since a player must perform exactly two actions, their turn can consist of one of these three combinations:
    Place + Place: Place a tile from your hand, then place another tile from your hand. This is the most common turn.

    Place + Exchange: Place a tile from your hand, then exchange a tile on the board with one from your hand (or vice-versa, the order doesn't matter).

    Exchange + Exchange: Exchange a tile on the board with one from your hand, then perform a second exchange on a different (or even the same, if rules permit) tile.

End of Turn:
    After the player has completed their two actions, their active turn ends. They then draw new tiles from the draw pile to replenish their hand back up to the hand limit (typically 5 tiles). In most interpretations, they draw a number of tiles equal to the number of tiles they placed from their hand during the turn (so if they did two exchanges, they would draw zero tiles, as they effectively "drew" two tiles from the board into their hand).


When AI places a tile, an "easy" approach is to step-by-step (high level overview):
1. look at its given line terminals to connect, and required stops to travel. evaluate fastest possible most ideal path possible (hypothetical, so imagine AI had its ideal pick from any possible TileType for this idealistic route.)
2. now look at actual non-hypothetical current 5 tiles in its hand per turn (e.g. at very start of its turn all players fairly have at hand 3 straights and 2 curves). we know 2 moves may be made per turn., so evaluate which move is optimal towards achieving primary goal of sticking to its idealistic route (e.g is any of its current at-hand tiles are applicable towards idealistic route's placement? If not should I change my route to accomodate available & likely-to-gain-next-via-withdrawal-or-competitors-placing-a-tile-i-want-placed-for-me-at-location-and-orientation-beneficial resources (as probabilistically given laid out tiles and knowledge of how many of each tiletype are in-game overall) and update ideal route expectations? Or should I reasonably expect I can stick to ideal route...?
3. repeat step 2 until complete route is found ready for entering driving phase!

Regarding step 2. above: evaluating an optimal move given current circumstance can get really complex. Even the order in which to place my tiles is also an important factor. There's an argument to be made that if an idealistic route would contain 13 straight tracks, and player has at-hand a straight tile(s), is it better to place that straight tile among any of its 13 tiles to fill towards idealistic complete route, or is it better to expand adjacently and systematically by joining up tiles already placed on board.
e.g. say player must connect up following coordinates for its ideal route: (0,0), (0,1), (1,1), (1,2), (1,3), (1,4), (2,4), (2,5). ideal route would necessitate tiles that have: a terminal at (0,0); a curve (west to south) track at (0,1); tile with vertical straight track at (1,1); tile with vertical straight track at (1,2); tile with vertical straight track at (1,3); tile with curve (north port to east) track at (1,4); tile with horizontal straight track at (2,4); terminal at (2,5). So at the very beginning of this player's turn, where should they utilise a tile from available tiles at-hand? maybe player could figure they could sequentially connect above coordinates in order shown above. If this were a 1-player game, this would be fine. But at 2+, other competitors may wanna place a tile with horizontal (but not vertical) straight track at (1,3). Then when turn comes back to my player, my idealist route planned out in my previous turn is now ruined owing to that horizontal track blocking my smooth connections! if in this turn I had access to a crossroad tile (which comprises both horizontal and vertical straight connections, meaning I can use it at (1,3) to both respect tile connection already there as well as fulfilling my idealistic route) I would be fine. But if I don't have such replacement tiles at-hand at-this-turn-in-which-I-must-evaluate-my-move, what then? Should I bet that I may receive a crossroad tile at some point in the future when drawing tiles to replenish my deck (back up to 5 at-hand after 2 moves rule), and just continue filling in rest of my coordinates as previously planned using available tiles at-hand? Or is that risky or likely given probability of number of crossroad tiles available? Or should i adjust my expectations and change up my idealistic route to one that accomodates this annoying horizontal track at (1,3) or ignores completely by figuring out a completely different route connecting my terminals and stops? And is placing sequentially following my idealistic placement per turn optimal, or should I consider placing a tile with straight track component as soon as I get chance to adjacent to my required station tiles to create a stop tile that best fits my ideal path to completion before somebody else places a tile with straight adjacent to that station and creating a stop tile at an orientation less beneficial towards my ideal route...?

You can appreciate how complex decision making becomes when number of players increase and thus their tile placements may not necessarily align with your most ideal route's. There's always a risk of should i change my ideal route if it became disrupted or hope to come across a replacement-able tree tile that I can use... What kind of heuristics / algorithms / thinking / parameters / resources / game theory must players consider & utilise for best outcome for them (which is to get to driving phase as quickly as possible by conncting required route!)

When the AI recalculates its "ideal path" during the laying phase every turn, it must always evaluate the entire path given board state to decide whether ideal path must change or may stay same from previous turn's evaluation.
