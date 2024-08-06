# Install required libraries
!apt update &> /dev/null
!apt install imagemagick &> /dev/null
!apt install ffmpeg &> /dev/null
!pip install moviepy pysrt
!sed -i '/<policy domain="path" rights="none" pattern="@\*"/d' /etc/ImageMagick-6/policy.xml

import os
import pysrt
from google.colab import files
from moviepy.editor import VideoFileClip, ImageClip, TextClip, CompositeVideoClip, AudioFileClip, VideoClip
import numpy as np
from moviepy.video.fx.all import fadein, fadeout

# def scale_effect(t, start_time, duration, min_scale=1.2, max_scale=1.4):
#     """Scale effect that zooms in smoothly."""
#     relative_t = (t - start_time) / duration
#     return min_scale + (max_scale - min_scale) * relative_t

def scale_effect(t, start_time, duration, min_scale=1.0, max_scale=1.2):
    """Scale effect that zooms in smoothly."""
    relative_t = (t - start_time) / duration
    return min_scale + (max_scale - min_scale) * relative_t

def shake_effect(t, start_time, duration, shake_amplitude=3, shake_frequency=25):
    """Simple shake effect by modifying image position."""
    relative_t = (t - start_time) / duration
    shake_x = shake_amplitude * np.sin(2 * np.pi * shake_frequency * relative_t)
    shake_y = 0 * np.cos(2 * np.pi * shake_frequency * relative_t)
    return int(shake_x), int(shake_y)

def create_background_image_sequence(image_paths, durations):
    """
    Create a sequence of background images that change over time with corresponding text and scale effect.
    
    :param image_paths: List of paths to background images
    :param durations: List of durations for each image
    :return: List of ImageClip and TextClip objects
    """
    background_clips = []
    start_time = 0
    
    for image_path, duration in zip(image_paths, durations):
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
        image_clip = image_clip.fl(lambda gf, t: apply_shake(gf, t))
        
        # Apply scale effect
        # mage_clip = image_clip.resize(lambda t: scale_effect(t, start_time, duration))

        # Apply the alpha mask to the image clip
        image_clip = fadein(image_clip, duration=2, initial_color=0.2).fadeout(duration=2)
        
        background_clips.append(image_clip)
        
        start_time += duration
    
    return background_clips

def create_text_clips_from_subtitles(subtitle_file, total_duration, font='Bangers', fontsize=90, color='white', shadow=False, shadow_color='black', shadow_fontsize=90, shadow_stroke_width=15, shadow_offset=(10, 10), resize_scale=lambda t: min(1, 0.8 + 15 * t)):
    """
    Create a list of text clips from a subtitle file without affecting the overall video length.
    
    :param subtitle_file: Path to the subtitle file
    :param total_duration: Total duration of the video
    :param font: Font for the text
    :param fontsize: Font size for the text
    :param color: Color for the text
    :param shadow: Whether to add shadow to the text
    :param shadow_color: Color for the shadow
    :param shadow_fontsize: Font size for the shadow
    :param shadow_stroke_width: Stroke width for the shadow
    :param shadow_offset: Offset for the shadow
    :param resize_scale: Function to apply scaling effect
    :return: List of TextClip objects
    """
    subs = pysrt.open(subtitle_file)
    text_clips = []
    
    for sub in subs:
        start_time = sub.start.ordinal / 1000
        end_time = sub.end.ordinal / 1000
        if end_time > total_duration:
            end_time = total_duration
        duration = end_time - start_time
        text = sub.text.replace('\n', ' ')

        text_clip = TextClip(
            text, 
            fontsize=fontsize, 
            color=color, 
            font=font,
            bg_color='transparent',
            stroke_width=5,
            stroke_color=color,
            method='caption',
            size=(900, None)
        ).set_start(start_time).set_duration(duration).resize(resize_scale).set_position('center')

        if shadow:
            shadow_textclip = TextClip(
                text, 
                fontsize=shadow_fontsize, 
                color=shadow_color, 
                font=font,
                bg_color='transparent', 
                stroke_width=shadow_stroke_width,
                stroke_color=shadow_color,
                method='caption',
                size=(900 + shadow_offset[0], None)
            ).set_start(start_time).set_duration(duration).resize(resize_scale).set_position('center')
            text_clips.append(shadow_textclip)

        text_clips.append(text_clip)
    
    return text_clips

# Main execution
background_images = ['imageA.png', 'imageB.png', 'imageC.png']

# Check if all required images are present
missing_images = [img for img in background_images if not os.path.exists(img)]
if missing_images:
    raise FileNotFoundError(f"The following images are missing: {', '.join(missing_images)}")

# Prompt user to upload background music
music_file_path = '/content/aarambh.mp3'
# Uncomment the following lines if you need to upload the music file manually
# print("Please upload your background music file (e.g., background_music.mp3)")
# uploaded = files.upload()
# music_file_path = list(uploaded.keys())[0]

# Define image durations
image_durations = [3, 3, 3]
total_duration = sum(image_durations)

# Create background image sequence
background_clips = create_background_image_sequence(background_images, image_durations)

# Define subtitle file path
subtitle_file_path = '/content/example.srt'

# Check if subtitle file is present
if not os.path.exists(subtitle_file_path):
    raise FileNotFoundError(f"The subtitle file is missing: {subtitle_file_path}")

# Create text clips from subtitle file
text_clips = create_text_clips_from_subtitles(subtitle_file_path, total_duration, 'Bangers', 90, 'white', True, 'tomato4')

# Combine all video clips
video_clip = CompositeVideoClip(
    background_clips + text_clips,  # Combine background and text clips
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
output_filename = "output_reel_with_subtitles.mp4"
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

print("Video creation complete with subtitles. The download should start automatically.")
