# src/scenes/intro_scene.py
import pygame
import os
from scenes.scene import Scene

# --- START OF CHANGE: Use OpenCV for video playback ---
import cv2
import numpy
# --- END OF CHANGE ---

class IntroScene(Scene):
    """
    A dedicated scene to play an introductory video cutscene using the robust
    OpenCV library for video decoding.
    """
    def __init__(self, scene_manager, asset_manager):
        super().__init__(scene_manager)
        self.asset_manager = asset_manager
        self.ended = False

        # Stop any currently playing music (like the main theme if returning to the menu)
        # self.scene_manager.sounds.stop_music()
        # Play the dedicated intro audio
        self.scene_manager.sounds.play_music('intro_theme', loops=0) # Play only once

        try:
            video_path = os.path.join(self.asset_manager.assets_path, 'videos', 'intro.mp4')
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found at {video_path}")

            # --- START OF CHANGE: Use cv2.VideoCapture ---
            self.cap = cv2.VideoCapture(video_path)
            self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.clock = pygame.time.Clock() # Use a dedicated clock to sync to video FPS
            
            # Get video dimensions
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Calculate scaling to fit screen height
            self.screen_rect = self.scene_manager.screen.get_rect()
            scale = self.screen_rect.height / height
            self.final_size = (int(width * scale), int(height * scale))

            # Center the video
            self.video_pos = ( (self.screen_rect.width - self.final_size[0]) // 2, 0 )
            # --- END OF CHANGE ---

            print("IntroScene: Video loaded successfully with OpenCV.")
        except Exception as e:
            print(f"!!! CRITICAL ERROR: Could not load intro video with OpenCV. Skipping. Error: {e}")
            self.ended = True

    def _end_scene(self):
        """Cleans up and transitions to the main menu."""
        if not self.ended:
            self.ended = True
            # --- START OF CHANGE: Release the video capture object ---
            if hasattr(self, 'cap'):
                self.cap.release()
            # --- END OF CHANGE ---
            self.scene_manager.go_to_scene("MAIN_MENU")

    def handle_events(self, events):
        """Listens for a skip key press."""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE]:
                    print("Intro skipped by user.")
                    self._end_scene()

    def update(self, dt):
        """Update is not needed as drawing drives the video forward."""
        pass

    def draw(self, screen):
        """Reads the next frame, converts it, and draws it to the screen."""
        if self.ended:
            screen.fill((0, 0, 0))
            return

        screen.fill((0, 0, 0)) # Black background
        
        # --- START OF CHANGE: Frame-by-frame processing with OpenCV ---
        try:
            # Read one frame from the video capture
            success, frame = self.cap.read()

            if success:
                # OpenCV loads images in BGR format, so we must convert to RGB for Pygame.
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Resize the frame
                resized_frame = cv2.resize(frame_rgb, self.final_size, interpolation=cv2.INTER_LANCZOS4)

                # Convert the NumPy array to a Pygame surface
                video_surface = pygame.surfarray.make_surface(resized_frame.swapaxes(0, 1))
                
                # Draw the frame onto the screen
                screen.blit(video_surface, self.video_pos)
            else:
                # If success is False, the video has ended.
                print("Intro video finished.")
                self._end_scene()

            # Tick the clock to match the video's native framerate
            self.clock.tick(self.video_fps)

        except Exception as e:
            print(f"Video rendering error: {e}")
            self._end_scene()
        # --- END OF CHANGE ---