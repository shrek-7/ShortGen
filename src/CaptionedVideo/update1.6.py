import os
import pysrt
from google.colab import files
from moviepy.editor import VideoFileClip, ImageClip, TextClip, CompositeVideoClip, AudioFileClip, VideoClip
import numpy as np
from moviepy.video.fx.all import fadein, fadeout
import moviepy.audio.fx.all as afx

def scale_effect(t, duration, max_scale=1.1, scale_up=True):
    """
    Scale effect that zooms smoothly from 1.0 to max_scale or from max_scale to 1.0.
    """
    if scale_up:
        return 1 + (max_scale - 1) * (t / duration)
    else:
        return max_scale - (max_scale - 1) * (t / duration)

def shake_effect(t, start_time, duration, shake_amplitude=4, shake_frequency=2):
    """Simple shake effect by modifying image position."""
    relative_t = (t - start_time) / duration
    shake_x = shake_amplitude * np.sin(2 * np.pi * shake_frequency * relative_t)
    shake_y = shake_amplitude * np.cos(2 * np.pi * shake_frequency * relative_t)
    return int(shake_x), int(shake_y)

def create_background_image_sequence(config):
    """
    Create a sequence of background images that change over time with corresponding text and scale effect.
    """
    image_paths = config['background_images']
    durations = config['image_durations']
    max_scale = config.get('max_scale', 1.1)
    animations = config.get('animations', [])
    background_clips = []
    start_time = 0

    for i, (image_path, duration) in enumerate(zip(image_paths, durations)):
        image_clip = (ImageClip(image_path)
                      .set_duration(duration)
                      .set_start(start_time)
                      .resize(height=1920)
                      .set_position(('center', 'center')))

        # Apply animations based on the configuration
        for animation in animations:
            if animation == 'shake':
                def apply_shake(get_frame, t):
                    shake_x, shake_y = shake_effect(t, start_time, duration)
                    frame = get_frame(t)
                    frame = np.roll(frame, int(shake_x), axis=1)  # Roll along x-axis
                    frame = np.roll(frame, int(shake_y), axis=0)  # Roll along y-axis
                    return frame
                image_clip = image_clip.fl(lambda gf, t: apply_shake(gf, t))

            elif animation == 'scale':
                scale_up = i % 2 == 0
                image_clip = image_clip.resize(lambda t: scale_effect(t, 1, max_scale, True))

            elif animation == 'fade':
                image_clip = fadein(image_clip, duration=0.5, initial_color=0.2).fadeout(duration=0.7)

        background_clips.append(image_clip)
        start_time += duration

    return background_clips

from moviepy.editor import TextClip, ImageClip, CompositeVideoClip
import numpy as np

from moviepy.editor import TextClip, ImageClip, CompositeVideoClip
import numpy as np

def create_text_clips_from_subtitles(config):
    """
    Create a list of animated text clips with backgrounds from a subtitle file without affecting the overall video length.
    """
    subtitle_file = config['subtitle_file']
    total_duration = config['total_duration']
    font = config.get('font', 'Bangers')
    fontsize = config.get('fontsize', 90)
    color = config.get('color', 'white')
    shadow = config.get('shadow', False)
    shadow_color = config.get('shadow_color', 'black')
    shadow_fontsize = config.get('shadow_fontsize', 90)
    shadow_stroke_width = config.get('shadow_stroke_width', 15)
    shadow_offset = config.get('shadow_offset', (10, 10))
    resize_scale = config.get('resize_scale', lambda t: min(1, 0.8 + 15 * t))
    words_per_clip = config.get('words_per_clip', 3)
    fade_duration = config.get('fade_duration', 0.5)
    bg_color = config.get('bg_color', (0, 0, 0, 128))  # Semi-transparent black
    bg_padding = config.get('bg_padding', 5)  # Padding around text

    subs = pysrt.open(subtitle_file)
    text_clips = []

    def create_color_clip(size, color):
        """Create a solid color clip."""
        if len(color) == 3:
            color = list(color) + [255]  # Add full opacity if RGB
        color_array = np.tile(np.array(color, dtype=np.uint8), (size[1], size[0], 1))
        return ImageClip(color_array)

    for sub in subs:
        start_time = sub.start.ordinal / 1000
        end_time = sub.end.ordinal / 1000
        if end_time > total_duration:
            end_time = total_duration
        duration = end_time - start_time
        words = sub.text.replace('\n', ' ').split()
        num_clips = max(1, len(words) // words_per_clip + (1 if len(words) % words_per_clip else 0))
        clip_duration = duration / num_clips

        for i in range(num_clips):
            combined_words = ' '.join(words[i * words_per_clip:(i + 1) * words_per_clip])
            word_start_time = start_time + i * clip_duration
            word_end_time = word_start_time + clip_duration
            if word_end_time > total_duration:
                word_end_time = total_duration

            # Create text clip
            text_clip = TextClip(
                combined_words,
                fontsize=fontsize,
                color=color,
                font=font,
                stroke_width=5,
                stroke_color=color,
                method='caption',
                size=(900, None)
            )

            # Create background clip
            bg_clip = create_color_clip(
                (text_clip.w + bg_padding, text_clip.h + bg_padding),
                bg_color
            )

            # Composite text over background
            word_clip = CompositeVideoClip([bg_clip, text_clip.set_position('center')])
            word_clip = word_clip.set_start(word_start_time).set_duration(clip_duration)
            word_clip = word_clip.resize(resize_scale).set_position('center')
            word_clip = word_clip.fadein(fade_duration).fadeout(fade_duration)

            if shadow:
                shadow_text_clip = TextClip(
                    combined_words,
                    fontsize=shadow_fontsize,
                    color=shadow_color,
                    font=font,
                    stroke_width=shadow_stroke_width,
                    stroke_color=shadow_color,
                    method='caption',
                    size=(900, None)
                )
                shadow_bg_clip = create_color_clip(
                    (shadow_text_clip.w + bg_padding * 2 + shadow_offset[0], 
                     shadow_text_clip.h + bg_padding * 2 + shadow_offset[1]),
                    bg_color
                )
                shadow_word_clip = CompositeVideoClip([
                    shadow_bg_clip, 
                    shadow_text_clip.set_position((bg_padding + shadow_offset[0], bg_padding + shadow_offset[1]))
                ])
                shadow_word_clip = shadow_word_clip.set_start(word_start_time).set_duration(clip_duration)
                shadow_word_clip = shadow_word_clip.resize(resize_scale).set_position('center')
                shadow_word_clip = shadow_word_clip.fadein(fade_duration).fadeout(fade_duration)
                text_clips.append(shadow_word_clip)

            text_clips.append(word_clip)

    return text_clips

def generate_final_video(config):
    """
    Generate the final video based on the provided configuration.
    """
    # Create background image sequence
    background_clips = create_background_image_sequence(config)

    # Create text clips from subtitle file
    text_clips = create_text_clips_from_subtitles(config)

    # Combine all video clips
    video_clip = CompositeVideoClip(
        background_clips + text_clips,  # Combine background and text clips
        size=(1080, 1920)  # Adjust size as needed
    )

    # Add background music
    audio_clip = AudioFileClip(config['music_file'])
    # Loop the audio if it's shorter than the video
    if audio_clip.duration < video_clip.duration:
        audio_clip = audio_clip.fx(afx.audio_loop, duration=video_clip.duration)
    else:
        # Trim the audio if it's longer than the video
        audio_clip = audio_clip.subclip(0, video_clip.duration)

    # Set the audio of the video clip
    final_clip = video_clip.set_audio(audio_clip)

    # Write the final video
    output_filename = config.get('output_filename', 'output_video.mp4')
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

# Example usage
config = {
    # 'background_images': ['doom1.png','doom2.png','doom3.png','doom4.png','doom5.png','doom6.png','doom7.png', 'doom8.png', 'doom9.png', 'doom4.png'],
    'background_images': ['doom1.png'],
    'image_durations': [3],
    'max_scale': 1.1,
    'animations': ['scale', 'shake'],  # List of animations to apply
    'subtitle_file': '/content/doomSubs.srt',
    'total_duration': 30,  # Should match the sum of image_durations
    'font': 'Roboto',
    'fontsize': 100,
    'color': 'white',
    'shadow': True,
    'shadow_color': 'SeaGreen4',
    'shadow_fontsize': 100,
    'shadow_stroke_width': 20,
    'shadow_offset': (10, 10),
    'resize_scale': lambda t: min(1, 0.8 + 15 * t),
    'words_per_clip': 3,
    'fade_duration': 0.25,
    'music_file': '/content/naration.wav',
    'output_filename': 'output_reel_with_subtitles.mp4',
    'bg_color': (255,197,37, 255),  # Semi-transparent black (R, G, B, A)
    'bg_padding': 2,  # Padding around text
}

generate_final_video(config)
