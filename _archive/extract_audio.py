# extract_audio.py
from moviepy import VideoFileClip
import os

# Define paths
video_path = os.path.join('C:/Users/minse/Desktop/Game/Linie1/src', 'assets', 'videos', 'intro.mp4')
audio_output_path = os.path.join('C:/Users/minse/Desktop/Game/Linie1/src', 'assets', 'sounds', 'music', 'intro_audio.wav')

print(f"Loading video from: {video_path}")
try:
    # Load the video clip
    video_clip = VideoFileClip(video_path)
    
    # Extract the audio
    audio_clip = video_clip.audio
    
    # Write the audio to a .wav file
    audio_clip.write_audiofile(audio_output_path, codec='pcm_s16le') # Use WAV for high compatibility
    
    # Clean up
    audio_clip.close()
    video_clip.close()
    
    print(f"Successfully extracted audio to: {audio_output_path}")

except Exception as e:
    print(f"An error occurred: {e}")