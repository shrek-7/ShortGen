# Install required libraries

!apt update &> /dev/null
!apt install imagemagick &> /dev/null
!apt install ffmpeg &> /dev/null
!pip install moviepy
!sed -i '/<policy domain="path" rights="none" pattern="@\*"/d' /etc/ImageMagick-6/policy.xml

import os
from google.colab import files
from moviepy.editor import VideoFileClip, ImageClip, TextClip, CompositeVideoClip, AudioFileClip, VideoClip
import numpy as np

from moviepy.video.fx.all import fadein, fadeout

def createTextClip(
    wrappedText, 
    start, 
    duration,
    position='center', 
    fontsize=60, 
    color='white', 
    font='Arial-Bold', 
    shadow=False, 
    shadow_color='black', 
    shadow_fontsize=60,
    shadow_stroke_width=10, 
    shadow_offset=(10, 10), 
    resize_scale=lambda t: min(1, 0.8 + 15 * t),
):
    textbox_size_x = 900

    text_clips = []

    # Define positions based on the 'position' argument
    if position == 'top':
        text_position = ('center', 'top')
    elif position == 'bottom':
        text_position = ('center', 'bottom')
    else:  # Default to 'center'
        text_position = ('center', 'center')

    # Main text clip
    new_textclip = TextClip(
        wrappedText, 
        fontsize=fontsize, 
        color=color, 
        font=font,
        bg_color='transparent',
        stroke_width=5,
        stroke_color=color,
        method='caption',
        size=(textbox_size_x, None)
    ).set_start(start).set_duration(duration).resize(resize_scale).set_position(text_position)

    if shadow:
        # Shadow text clip
        shadow_text_clip = TextClip(
            wrappedText, 
            fontsize=shadow_fontsize, 
            color=shadow_color, 
            font=font,
            bg_color='transparent', 
            stroke_width=shadow_stroke_width,
            stroke_color=shadow_color,
            method='caption',
            size=(textbox_size_x + shadow_offset[0], None)
        ).set_start(start).set_duration(duration).resize(resize_scale).set_position(text_position)
        
        return [shadow_text_clip, new_textclip]
    else:
        return [new_textclip]

def scale_effect(t, start_time, duration, min_scale=0.9, max_scale=1.2):
    """Scale effect that zooms in smoothly."""
    relative_t = (t - start_time) / duration
    scale = min_scale + (max_scale - min_scale) * relative_t
    return max(scale, 1.0)

def shake_effect(t, start_time, duration, shake_amplitude=10, shake_frequency=5):
    """Simple shake effect by modifying image position."""
    relative_t = (t - start_time) / duration
    shake_x = shake_amplitude * np.sin(2 * np.pi * shake_frequency * relative_t)
    shake_y = shake_amplitude * np.cos(2 * np.pi * shake_frequency * relative_t)
    return int(shake_x), int(shake_y)

def create_background_image_sequence(image_paths, durations, texts):
    """
    Create a sequence of background images that change over time with corresponding text and scale effect.
    
    :param image_paths: List of paths to background images
    :param durations: List of durations for each image
    :param texts: List of texts for each image
    :return: List of ImageClip and TextClip objects
    """
    background_clips = []
    text_clips = []
    start_time = 0
    
    for image_path, duration, text in zip(image_paths, durations, texts):
        # Create image clip with scale effect
        image_clip = (ImageClip(image_path)
                      .set_duration(duration)
                      .set_start(start_time)
                      .resize(height=1920)  # Adjust size as needed
                      .set_position(('center', 'center')))
        
        # Apply shake effect by modifying the position
        def apply_shake(get_frame, t):
            shake_x, shake_y = shake_effect(t, start_time, duration)
            frame = get_frame(t)
            frame = np.roll(frame, int(shake_x), axis=1)  # Roll along x-axis
            frame = np.roll(frame, int(shake_y), axis=0)  # Roll along y-axis
            return frame

        # Apply shake effect
        #image_clip = image_clip.fl(lambda gf, t: apply_shake(gf, t))
        
        # Apply scale effect
        #image_clip = image_clip.resize(lambda t: scale_effect(t, start_time, duration))

        # Apply the alpha mask to the image clip
        image_clip = fadein(image_clip, duration=2, initial_color=0.2).fadeout(duration=2)
        
        background_clips.append(image_clip)
        
        # Create text clip for this image
        text_clip = createTextClip(text, start_time, duration, 'center', 60, 'Black', 'Roboto', True, 'Red')
        text_clips.append(text_clip)
        
        start_time += duration
    
    return background_clips, text_clips

# Main execution
background_images = ['imageA.png', 'imageB.png', 'imageC.png']
text_for_images = [
    "First image text", 
    "Second image text", 
    "Third image text"
]

# Check if all required images are present
missing_images = [img for img in background_images if not os.path.exists(img)]
if missing_images:
    raise FileNotFoundError(f"The following images are missing: {', '.join(missing_images)}")

# Prompt user to upload background music
music_file_path = '/content/bg.mp3'
# Uncomment the following lines if you need to upload the music file manually
# print("Please upload your background music file (e.g., background_music.mp3)")
# uploaded = files.upload()
# music_file_path = list(uploaded.keys())[0]

# Define image durations
image_durations = [3, 3, 3]

# Create background image sequence and text clips
background_clips, text_clips = create_background_image_sequence(background_images, image_durations, text_for_images)

# Flatten text clips for easy combination
# text_clips_flattened = [clip for sublist in text_clips for clip in sublist]

# Combine all video clips
video_clip = CompositeVideoClip(
    background_clips + [clip for sublist in text_clips for clip in sublist], # Flatten the text_clips list
    size=(1080, 1920)  # Adjust size as needed
)

# Add background music
audio_clip = AudioFileClip(music_file_path)
# Loop the audio if it's shorter than the video
if audio_clip.duration < video_clip.duration:
    audio_clip = audio_clip.fx(afx.audio_loop, duration=video_clip.duration)
else:
    # Trim the audio if it's longer than the video
    audio_clip = audio_clip.subclip(0, video_clip.duration)

# Set the audio of the video clip
final_clip = video_clip.set_audio(audio_clip)

# Write the final video
output_filename = "output_reel_with_zoom_effect.mp4"
final_clip.write_videofile(
    output_filename,
    codec="libx264",
    audio_codec="aac",
    threads=8,
    preset='ultrafast',
    fps=30
)

# Download the created video
files.download(output_filename)

print("Video creation complete with zoom effect. The download should start automatically.")
