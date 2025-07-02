# sound_manager.py
import pygame
import os

class SoundManager:
    def __init__(self):
        # Initialize the mixer with recommended settings
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
        self.sounds = {}
        self.music_path = ""
        self.is_muted = False
        
        # Define sound paths relative to the assets directory
        self.sound_paths = {
            'click': os.path.join('assets', 'sounds', 'ui', 'click.wav'),
            'click_hand': os.path.join('assets', 'sounds', 'ui', 'click_at_hand.wav'),
            'place': os.path.join('assets', 'sounds', 'tiles', 'place_tile.wav'),
            'error': os.path.join('assets', 'sounds', 'ui', 'error.wav'),
            'commit': os.path.join('assets', 'sounds', 'ui', 'commit_turn.wav'),
            'dice_roll': os.path.join('assets', 'sounds', 'driving', 'dice_roll.mp3'),
            'train_move': os.path.join('assets', 'sounds', 'driving', 'train_move.mp3'),
            'eliminated': os.path.join('assets', 'sounds', 'condition', 'eliminated.mp3'),
        }
        self.music_paths = {
            'main_theme': os.path.join('assets', 'sounds', 'music', 'background_theme.wav')
        }

    def load_sounds(self):
        """Load all defined sound effects into memory."""
        for name, path in self.sound_paths.items():
            if os.path.exists(path):
                self.sounds[name] = pygame.mixer.Sound(path)
            else:
                print(f"Sound file not found: {path}")
                self.sounds[name] = None # Handle missing files gracefully

    def play(self, name, loops=0):
        """Play a loaded sound effect by its name."""
        if self.is_muted or name not in self.sounds or self.sounds[name] is None:
            return
        self.sounds[name].play(loops)

    def play_music(self, name, loops=-1):
        """Load and play a music track by name. Loops forever by default."""
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
            
    def set_volume(self, sound_volume, music_volume):
        """Set volume for sound effects and music (0.0 to 1.0)."""
        for sound in self.sounds.values():
            if sound:
                sound.set_volume(sound_volume)
        pygame.mixer.music.set_volume(music_volume)

    def toggle_mute(self):
        """Mute or unmute all audio."""
        self.is_muted = not self.is_muted
        if self.is_muted:
            pygame.mixer.music.pause()
        else:
            pygame.mixer.music.unpause()