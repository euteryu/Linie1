# sound_manager.py
import pygame
import os

class SoundManager:
    def __init__(self, root_dir: str):
        # Initialize the mixer with recommended settings
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
        self.sounds = {}
        self.music_path = ""
        self.is_muted = False
        
        assets_path = os.path.join(root_dir, 'src', 'assets', 'sounds')

        # Define sound paths relative to the assets directory
        self.sound_paths = {
            'click': os.path.join(assets_path, 'ui', 'click.wav'),
            'click_hand': os.path.join(assets_path, 'ui', 'click_at_hand.wav'),
            'place': os.path.join(assets_path, 'tiles', 'place_tile.wav'),
            'error': os.path.join(assets_path, 'ui', 'error.wav'),
            'commit': os.path.join(assets_path, 'ui', 'commit_turn.wav'),
            'dice_roll': os.path.join(assets_path, 'driving', 'dice_roll.mp3'),
            'train_move': os.path.join(assets_path, 'driving', 'train_move.mp3'),
            'eliminated': os.path.join(assets_path, 'condition', 'eliminated.mp3'),
            'auction_new_item': os.path.join(assets_path, 'auctionhouse', 'auction_new_item.wav'),
        }
        self.music_paths = {
            'main_theme': os.path.join(assets_path, 'music', 'background_theme.mp3'),
            'intro_theme': os.path.join(assets_path, 'music', 'intro_audio.wav')
        }

    def load_sounds(self):
        """Load all defined sound effects into memory gracefully."""
        if not pygame.mixer: return # Do nothing if mixer failed to init

        for name, path in self.sound_paths.items():
            if os.path.exists(path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(path)
                except pygame.error as e:
                    print(f"WARNING: Failed to load sound '{name}' at '{path}'. Error: {e}")
                    self.sounds[name] = None # Set to None to avoid future errors
            else:
                print(f"WARNING: Sound file not found for '{name}': {path}")
                self.sounds[name] = None

    def play(self, name, loops=0):
        """Play a loaded sound effect by its name."""
        if self.is_muted or not pygame.mixer: 
            return
        if name in self.sounds and self.sounds[name] is not None:
            self.sounds[name].play(loops)

    def play_music(self, name, loops=-1):
        """Load and play a music track by name. Loops forever by default."""
        if self.is_muted or not pygame.mixer:
            return
        if self.is_muted or name not in self.music_paths:
            return
        
        music_file = self.music_paths[name]
        if os.path.exists(music_file):
            if self.music_path != music_file: # Don't restart if it's already playing
                pygame.mixer.music.load(music_file)
                self.music_path = music_file
            pygame.mixer.music.play(loops)
        else:
            print(f"Music file not found: {music_file}")

    def stop_music(self):
        """Stops any currently playing music."""
        if not pygame.mixer: return
        pygame.mixer.music.stop()
        self.music_path = "" # Clear the path so the next track can start fresh
            
    def toggle_mute(self):
        """Toggles the master mute state for all sounds and music."""
        self.is_muted = not self.is_muted
        if self.is_muted:
            pygame.mixer.music.pause()
        else:
            pygame.mixer.music.unpause()
        print(f"Sound has been {'Muted' if self.is_muted else 'Unmuted'}.")

    def set_music_volume(self, volume: float):
        """Sets the music volume. Volume should be between 0.0 and 1.0."""
        # Clamp volume between 0.0 and 1.0
        clamped_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(clamped_volume)

    def set_sfx_volume(self, volume: float):
        """Sets the sound effects volume."""
        clamped_volume = max(0.0, min(1.0, volume))
        for sound in self.sounds.values():
            if sound:
                sound.set_volume(clamped_volume)

    def toggle_mute(self):
        """Mute or unmute all audio."""
        self.is_muted = not self.is_muted
        if self.is_muted:
            pygame.mixer.music.pause()
        else:
            pygame.mixer.music.unpause()