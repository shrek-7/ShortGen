# Added background color to text

!pip install pysrt
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
import moviepy.audio.fx.all as afx

def scale_effect(t, duration, max_scale=1.1, scale_up=True):
    """
    Scale effect that zooms smoothly from 1.0 to max_scale or from max_scale to 1.0.
    """
    if scale_up:
        return 1 + (max_scale - 1) * (t / duration)
    else:
        return max_scale - (max_scale - 1) * (t / duration)

def shake_effect(t, start_time, duration, shake_amplitude=2, shake_frequency=2):
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
                image_clip = image_clip.resize(lambda t: scale_effect(t, duration, max_scale, scale_up))

            elif animation == 'fade':
                image_clip = fadein(image_clip, duration=0.5, initial_color=0.2).fadeout(duration=0.7)

        background_clips.append(image_clip)
        start_time += duration

    return background_clips

from moviepy.editor import TextClip, CompositeVideoClip

def blink_effect(get_frame, t, blink_duration=0.5):
    return get_frame(t) if (t % (2 * blink_duration)) < blink_duration else np.zeros_like(get_frame(t))

def wiggle_effect(t, amplitude=1, frequency=8):
    return amplitude * np.sin(2 * np.pi * frequency * t)

def flip_effect(gf, t, axis=0):
    frame = gf(t)
    return np.flip(frame, axis=axis)

def bounce_effect(t, duration, height=50):
    return 'center', height * abs(np.sin(2 * np.pi * t / duration))


def create_text_animation(word_clip, animation='fadein', fade_duration=0.5):
  if animation == 'fadein':
      word_clip = word_clip.fadein(fade_duration)
  elif animation == 'fadeout':
      word_clip = word_clip.fadeout(fade_duration)
  elif animation == 'crossfadein':
      word_clip = word_clip.crossfadein(fade_duration)
  elif animation == 'crossfadeout':
      word_clip = word_clip.crossfadeout(fade_duration)
  elif animation == 'scale':
      word_clip = word_clip.resize(lambda t: 1 + 0.1 * (5 * t))
  elif animation == 'slide_up':
      word_clip = word_clip.set_position(lambda t: ('center', 100 + t * 100))
  elif animation == 'rotate':
      word_clip = word_clip.rotate(lambda t: 45 * t)
  elif animation == 'wave':
      word_clip = word_clip.fl(lambda gf, t: np.roll(gf(t), int(5 * np.sin(t * 2 * np.pi)), axis=1))
  elif animation == 'blink':
      word_clip = word_clip.fl(lambda gf, t: blink_effect(gf, t))
  elif animation == 'bounce':
      word_clip = word_clip.set_position(lambda t: bounce_effect(t, fade_duration))
  elif animation == 'flip':
      word_clip = word_clip.fl(lambda gf, t: flip_effect(gf, t, axis=1))
  elif animation == 'swing':
      word_clip = word_clip.rotate(lambda t: swing_effect(t, fade_duration))
  elif animation == 'wiggle':
      word_clip = word_clip.set_position(lambda t: ('center', 840 + wiggle_effect(t)))
                



  return word_clip

def create_text_clips_from_subtitles(config):
    """
    Create a list of animated text clips from a subtitle file without affecting the overall video length.
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
    shadow_offset = config.get('shadow_offset', (5, 5))
    resize_scale = config.get('resize_scale', lambda t: min(1, 0.8 + 15 * t))
    words_per_clip = config.get('words_per_clip', 3)
    fade_duration = config.get('fade_duration', 0.5)
    text_animation = config.get('text_animation', 'fadein')
    bg_color = config.get('bg_color', None)
    
    subs = pysrt.open(subtitle_file)
    text_clips = []

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

            word_clip = TextClip(
                combined_words, 
                fontsize=fontsize, 
                color=color, 
                font=font,
                bg_color='transparent',
                stroke_width=5,
                stroke_color=color,
                method='caption',
                size=(900, None)
            ).set_start(word_start_time).set_duration(clip_duration).resize(resize_scale).set_position('center')

            # Apply text animations
            word_clip = create_text_animation(word_clip, text_animation, fade_duration)

            if shadow:
                shadow_word_clip = TextClip(
                    combined_words, 
                    fontsize=shadow_fontsize, 
                    color=shadow_color, 
                    font=font,
                    bg_color=bg_color, 
                    stroke_width=shadow_stroke_width,
                    stroke_color=shadow_color,
                    method='caption',
                    size=(900 + shadow_offset[0], None)
                ).set_start(word_start_time).set_duration(clip_duration).resize(resize_scale).set_position('center')

                # Apply text animations
                shadow_word_clip = create_text_animation(shadow_word_clip, text_animation, fade_duration)
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
    'background_images': ['1.jpg', '2.jpg', '3.jpg', '4.jpg', '5.jpg', '6.jpg', '7.jpg', '8.jpg'],
    'image_durations': [3, 3, 3, 3, 3, 3, 3, 3],
    'max_scale': 1.1,
    'animations': ['fade', 'scale', 'shake'],
    'text_animation': 'wiggle', # fadein fadeout crossfadein crossfadeout slide_up rotate scale wave
    'subtitle_file': '/content/kang.srt',
    'total_duration': 25,  # Should match the sum of image_durations
    'font': 'Bangers',
    'fontsize': 100,
    'color': 'yellow',
    'shadow': True,
    'shadow_color': 'turquoise1',
    'shadow_fontsize': 100,
    'shadow_stroke_width': 20,
    'shadow_offset': (10, 10),
    'resize_scale': lambda t: min(1, 0.8 + 15 * t),
    'words_per_clip': 3,
    'fade_duration': 1,
    'music_file': '/content/kang.wav',
    'output_filename': 'output_reel_with_subtitles.mp4',
    'bg_color': 'SpringGreen4' 
}

generate_final_video(config)
