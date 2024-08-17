import os
import sys
import pysrt
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, AudioFileClip, TextClip, ColorClip, concatenate_videoclips
import numpy as np
from moviepy.video.fx.all import fadein, fadeout
from PIL import Image, ImageDraw, ImageFont, ImageColor
import moviepy.audio.fx.all as afx
from moviepy.config import change_settings
from moviepy.audio.AudioClip import CompositeAudioClip
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import cairosvg
import io

from font_theme import get_theme_colors

# Set the ImageMagick binary path based on the operating system
if sys.platform.startswith('win'):
    IMAGEMAGICK_BINARY = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"
else:
    IMAGEMAGICK_BINARY = r"/usr/local/bin/convert"

# Set the ImageMagick binary path
change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})

# Fix for ANTIALIAS deprecation
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS


def create_svg_watermark(svg_path, video_size, watermark_size, opacity=1.0):
    """
    Create a watermark clip from an SVG file, positioned at the top-left corner.

    :param svg_path: Path to the SVG file
    :param video_size: Tuple of (width, height) of the video
    :param watermark_size: Tuple of (width, height) for the watermark
    :param opacity: Opacity of the watermark (0.0 to 1.0)
    :return: ImageClip with the watermark positioned at the top-left
    """
    # Convert SVG to PNG
    png_data = cairosvg.svg2png(url=svg_path, output_width=watermark_size[0], output_height=watermark_size[1])

    # Create PIL Image from PNG data
    watermark_image = Image.open(io.BytesIO(png_data)).convert("RGBA")

    # Apply opacity
    watermark_image.putalpha(Image.eval(watermark_image.split()[3], lambda a: int(a * opacity)))

    # Create a transparent image the size of the video
    full_image = Image.new('RGBA', video_size, (0, 0, 0, 0))

    # Paste the watermark onto the full image at the top-left corner
    full_image.paste(watermark_image, (10, 0), watermark_image)

    # Convert to numpy array
    img_array = np.array(full_image)

    # Create ImageClip
    watermark_clip = ImageClip(img_array).set_duration(1)
    return watermark_clip

def scale_effect(t, duration, max_scale=1.1, scale_up=True):
    """
    Scale effect that zooms smoothly from 1.0 to max_scale or from max_scale to 1.0.
    """
    if scale_up:
        return 1 + (max_scale - 1) * (t / duration)
    else:
        return max_scale - (max_scale - 1) * (t / duration)

def create_background_image_sequence(config):
    """
    Create a sequence of background images with optimized processing.
    """
    image_paths = config['background_images']
    durations = config['image_durations']
    transition_config = config.get('transition_config', {}).get('image', {})
    animations = transition_config.get('animations', [])
    transition_duration = transition_config.get('duration', 0.5)
    swoosh_sound_path = transition_config.get('sound_path', '')
    max_scale = transition_config.get('max_scale', 1.1)

    audio_clips = []
    total_duration = sum(durations)

    def process_image(args):
        i, (image_path, duration) = args
        start_time = sum(durations[:i])

        image_clip = (ImageClip(image_path)
                      .set_duration(total_duration - start_time)
                      .set_start(start_time)
                      .resize(height=1920)
                      .set_position(('center', 'center')))

        for animation in animations:
            if animation == 'slide_up' and i > 0:
                image_clip = image_clip.set_position(lambda t: ('center', max(0, 1920 - (t / transition_duration) * 1920)))

                if swoosh_sound_path:
                    swoosh_audio = AudioFileClip(swoosh_sound_path).set_start(start_time).set_duration(transition_duration)
                    audio_clips.append(swoosh_audio)
            elif animation == 'scale':
                scale_up = i % 2 == 0
                image_clip = image_clip.resize(lambda t: scale_effect(t, duration, max_scale, scale_up))
            elif animation == 'fade':
                image_clip = fadein(image_clip, duration=0.5, initial_color=0.2).fadeout(duration=0.7)

        return image_clip

    with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        background_clips = list(executor.map(process_image, enumerate(zip(image_paths, durations))))

    return background_clips, audio_clips

def create_high_quality_text_clip(text, font_path, font_size, color, stroke_width=0, stroke_color=None, bg_color=None):
    canvas_size = (1920 * 2, 1080 * 2)
    text_layer = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)

    font = ImageFont.truetype(font_path, font_size * 2)

    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    position = ((canvas_size[0] - text_width) // 2, (canvas_size[1] - text_height) // 2)

    if stroke_width > 0:
        for adj in range(stroke_width * 2):
            x = position[0] + (adj - stroke_width)
            y = position[1] + (adj - stroke_width)
            draw.text((x, y), text, font=font, fill=stroke_color)

    draw.text(position, text, font=font, fill=color)

    text_layer = text_layer.resize((1920, 1080), Image.LANCZOS)

    return ImageClip(np.array(text_layer))

def create_text_animation(word_clip, animation='fadein', fade_duration=0.5):
    if animation == 'fadein':
        return word_clip.fadein(fade_duration)
    elif animation == 'fadeout':
        return word_clip.fadeout(fade_duration)
    elif animation == 'scale':
        return word_clip.resize(lambda t: 1 + 0.1 * (5 * t))
    elif animation == 'wiggle':
        return word_clip.set_position(lambda t: ('center', 840 + np.sin(2 * np.pi * 2 * t) * 5))
    return word_clip

def create_text_clips_from_subtitles(config):
    """
    Create text clips from subtitles with optimized processing.
    """
    text_style_config = config['text_style_config']
    subtitle_file = config['subtitle_file']
    total_duration = config['total_duration']

    if not os.path.exists(subtitle_file):
        print(f"Subtitle file '{subtitle_file}' not found. Skipping text clip creation.")
        return []

    font = text_style_config.get('font', 'Bangers')
    fontsize = text_style_config.get('fontSize')
    color = text_style_config.get('color', 'white')
    stroke_width = text_style_config.get('stroke_width', 0)
    stroke_color = text_style_config.get('stroke_color', 'black')
    shadow_opacity = text_style_config.get('shadow_opacity', 0.6)
    bg_color = text_style_config.get('bg_color', None)
    shadow_color = text_style_config.get('shadow_color', 'black')
    shadow_stroke_width = text_style_config.get('shadow_stroke_width', 20)
    shadow = text_style_config.get('shadow', False)
    position = text_style_config.get('position', 'center')

    words_per_clip = config.get('words_per_clip', 3)
    transition_config = config.get('transition_config', {}).get('text', {})
    fade_duration = transition_config.get('duration', 0.5)
    text_animation = transition_config.get('animation', 'fadein')

    subs = pysrt.open(subtitle_file)

    text_position = {
        'top': ('center', 'top'),
        'bottom': ('center', 'bottom'),
        'center': ('center', 'center')
    }.get(position, ('center', 'center'))

    def process_subtitle(sub):
        start_time = sub.start.ordinal / 1000
        end_time = min(sub.end.ordinal / 1000, total_duration)
        duration = end_time - start_time
        words = sub.text.replace('\n', ' ').split()
        num_clips = max(1, len(words) // words_per_clip + (1 if len(words) % words_per_clip else 0))
        clip_duration = duration / num_clips

        clips = []
        for i in range(num_clips):
            combined_words = ' '.join(words[i * words_per_clip:(i + 1) * words_per_clip])
            word_start_time = start_time + i * clip_duration
            word_end_time = min(word_start_time + clip_duration, total_duration)

            word_clip = create_high_quality_text_clip(
                combined_words, font, fontsize, color, stroke_width, stroke_color, bg_color
            ).set_start(word_start_time).set_duration(word_end_time - word_start_time).set_position(text_position)

            word_clip = create_text_animation(word_clip, text_animation, fade_duration)

            if shadow:
                shadow_word_clip = create_high_quality_text_clip(
                    combined_words, font, fontsize, shadow_color, shadow_stroke_width, shadow_color, bg_color
                ).set_start(word_start_time).set_duration(word_end_time - word_start_time).set_position(text_position).set_opacity(shadow_opacity)

                shadow_word_clip = create_text_animation(shadow_word_clip, text_animation, fade_duration)
                clips.append(shadow_word_clip)

            clips.append(word_clip)

        return clips

    with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        text_clips = list(executor.map(process_subtitle, subs))

    return [clip for sublist in text_clips for clip in sublist]

def generate_final_video(config):
    """
    Generate the final video with optimized processing.
    """
    video_size = (1080, 1920)  # Adjust to your video's dimensions

    audio_clip = AudioFileClip(config['background_audio'])
    audio_len = audio_clip.duration
    num_images = len(config['background_images'])
    constant_image_duration = audio_len / num_images

    config['image_durations'] = [constant_image_duration] * num_images
    config['total_duration'] = audio_len

    background_clips, swoosh_audio_clips = create_background_image_sequence(config)
    text_clips = create_text_clips_from_subtitles(config)

    # Create watermark
    watermark = create_svg_watermark(
        config['watermark_svg'],
        video_size=video_size,
        watermark_size=(500, 100),  # Adjust size as needed
    )
    watermark = watermark.set_duration(audio_len)

    main_video = CompositeVideoClip(
        background_clips + text_clips + [watermark],
        size=video_size
    ).set_duration(audio_len)

    final_audio = CompositeAudioClip([audio_clip] + swoosh_audio_clips)
    final_clip = main_video.set_audio(final_audio)

    output_filename = config.get('output_filename', 'output_video.mp4')
    final_clip.write_videofile(
        output_filename,
        codec="libx264",
        audio_codec="aac",
        threads=multiprocessing.cpu_count(),
        preset='faster',
        fps=30
    )

    print(f"Video creation complete. Output file: {output_filename}")

if __name__ == "__main__":
    # Configuration

    theme_colors = get_theme_colors('hulk', 'secondary')
    config = {
        'background_images': ['1.png'],
        # 'background_images': ['1.png', '2.png', '3.png', '4.png', '5.png', '6.png', '7.png', '8.png', '9.png'],
        'subtitle_file': 'subtitle.srt',
        'background_audio': 'background.wav',
        'words_per_clip': 2,
        'output_filename': 'output_reel_with_subtitles.mp4',
        'text_style_config': {
            'color': theme_colors['color'],
            'fontSize': 180,
            'stroke_width': 10,
            'shadow': True,
            'stroke_color': 'black',
            'shadow_opacity': 0.9,
            'shadow_color': theme_colors['shadow'],
            'shadow_stroke_width': 20,
            'bg_color': None,
            'font': 'Fonts/Bangers.ttf',
            'position': 'center'
        },
        'transition_config': {
            'image': {
                'duration': 0.25,
                'animations': ['slide_up', 'fade'],
                'sound_path': 'swoosh.mp3',
                'max_scale': 1.2
            },
            'text': {
                'duration': 0.25,
                'animation': 'wiggle',
            }
        },
        'watermark_svg': 'Images/water_mark.svg'
    }

    generate_final_video(config)