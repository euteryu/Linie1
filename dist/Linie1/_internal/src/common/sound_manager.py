# sound_manager.py
import pygame
import os
from common.asset_manager import resource_path 

class SoundManager:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
        self.sounds = {}
        self.music_path = ""
        self.is_muted = False
        
        # Define paths relative to the project root for resource_path
        base_path = os.path.join('src', 'assets', 'sounds')

        self.sound_paths = {
            'click': os.path.join(base_path, 'ui', 'click.wav'),
            'click_hand': os.path.join(base_path, 'ui', 'click_at_hand.wav'),
            'place': os.path.join(base_path, 'tiles', 'place_tile.wav'),
            'error': os.path.join(base_path, 'ui', 'error.wav'),
            'commit': os.path.join(base_path, 'ui', 'commit_turn.wav'),
            'dice_roll': os.path.join(base_path, 'driving', 'dice_roll.mp3'),
            'train_move': os.path.join(base_path, 'driving', 'train_move.mp3'),
            'eliminated': os.path.join(base_path, 'condition', 'eliminated.mp3'),
            'auction_new_item': os.path.join(base_path, 'auctionhouse', 'auction_new_item.wav'),
        }
        self.music_paths = {
            'main_theme': os.path.join(base_path, 'music', 'background_theme.mp3'),
            'intro_theme': os.path.join(base_path, 'music', 'intro_audio.wav')
        }

    # --- MODIFIED METHOD ---
    def load_sounds(self):
        if not pygame.mixer: return

        for name, rel_path in self.sound_paths.items():
            full_path = resource_path(rel_path) # Use the helper
            if os.path.exists(full_path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(full_path)
                except pygame.error as e:
                    print(f"WARNING: Failed to load sound '{name}' at '{full_path}'. Error: {e}")
                    self.sounds[name] = None
            else:
                print(f"WARNING: Sound file not found for '{name}': {full_path}")
                self.sounds[name] = None

    def play(self, name, loops=0):
        """Play a loaded sound effect by its name."""
        if self.is_muted or not pygame.mixer: 
            return
        if name in self.sounds and self.sounds[name] is not None:
            self.sounds[name].play(loops)

    def play_music(self, name, loops=-1):
        if self.is_muted or not pygame.mixer or name not in self.music_paths:
            return
        
        music_file_rel_path = self.music_paths[name]
        music_file_full_path = resource_path(music_file_rel_path) # Use the helper

        if os.path.exists(music_file_full_path):
            if self.music_path != music_file_full_path:
                pygame.mixer.music.load(music_file_full_path)
                self.music_path = music_file_full_path
            pygame.mixer.music.play(loops)
        else:
            print(f"Music file not found: {music_file_full_path}")

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