# mods/economic_mod/headline_manager.py
import json
import random
from pathlib import Path
from typing import List, Dict, Optional, Any

class HeadlineManager:
    """Manages the deck, drawing, and effects of Headline News events."""
    def __init__(self):
        self.event_deck: List[Dict] = self._load_events()
        random.shuffle(self.event_deck)
        self.active_event: Optional[Dict] = None
        self.rounds_remaining: int = 0
        self.event_trigger_turn_counter: int = 0
        self.event_trigger_threshold: int = 2 # Default, will be updated by mod

    def _load_events(self) -> List[Dict]:
        """Loads event card data from the JSON file."""
        try:
            # Use pathlib for robust path handling
            path = Path(__file__).parent / "headline_events.json"
            with open(path, 'r') as f:
                events = json.load(f)
                print(f"[HeadlineManager] Loaded {len(events)} events successfully.")
                return events
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"[HeadlineManager] CRITICAL ERROR: Could not load headline_events.json: {e}")
            return []

    def tick(self, game) -> Optional[Dict]:
        """
        Called at the start of each player's turn. Manages event duration and triggers new events.
        Returns the new event if one was just drawn, otherwise None.
        """
        if game.active_player_index == 0:
            # A full round has passed
            self.event_trigger_turn_counter += 1
            if self.rounds_remaining > 0:
                self.rounds_remaining -= 1
                if self.rounds_remaining == 0:
                    print(f"[HeadlineManager] Event '{self.active_event['headline']}' has expired.")
                    self.active_event = None
        
        # Check if it's time to draw a new event
        if not self.active_event and self.event_trigger_turn_counter >= self.event_trigger_threshold:
            self.event_trigger_turn_counter = 0 # Reset counter
            return self.draw_new_event()
            
        return None

    def draw_new_event(self) -> Optional[Dict]:
        """Draws a new event from the deck, sets it as active, and returns it."""
        if not self.event_deck:
            print("[HeadlineManager] Event deck is empty. Reshuffling...")
            self.event_deck = self._load_events()
            random.shuffle(self.event_deck)
            if not self.event_deck: return None # Still no events

        # For now, we only have Economic events, so we draw one.
        # Later, we will use the 45%/45%/10% probabilities here.
        economic_events = [e for e in self.event_deck if e['category'] == 'Economic']
        if not economic_events:
            print("[HeadlineManager] No Economic events left to draw.")
            return None

        self.active_event = random.choice(economic_events)
        self.event_deck.remove(self.active_event) # Don't draw the same card twice in a row
        self.rounds_remaining = self.active_event["duration_rounds"]
        
        print(f"[HeadlineManager] NEW EVENT: {self.active_event['headline']} (Duration: {self.rounds_remaining} rounds)")
        return self.active_event

    def get_modified_sell_reward(self, base_reward: int) -> int:
        """Applies the current event's modifier to a sell reward, if any."""
        if self.active_event and self.active_event["effects"]["type"] == "SELL_REWARD_MODIFIER":
            multiplier = self.active_event["effects"]["multiplier"]
            return int(base_reward * multiplier)
        return base_reward

    def get_modified_requisition_cost(self, base_cost: int) -> int:
        """Applies the current event's modifier to a requisition cost, if any."""
        if self.active_event and self.active_event["effects"]["type"] == "REQUISITION_COST_MODIFIER":
            multiplier = self.active_event["effects"]["multiplier"]
            return int(base_cost * multiplier)
        return base_cost