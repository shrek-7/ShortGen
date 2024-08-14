# Install required libraries if not already installed
!pip install moviepy

import moviepy.editor as mp
import matplotlib.pyplot as plt
from PIL import Image

# Create a blank white background clip
background_color = (255, 255, 255)  # White background
background_size = (720, 480)  # Width x Height of the background

# Create the background clip
background_clip = mp.ColorClip(size=background_size, color=background_color, duration=5)

text_style_config = {
    'color': '#f23041',
    'fontSize': 90,
    'stroke_width': 5,
    'shadow_opacity': 0,
    'stroke_color': 'black',
    'shadow_color': 'black',
    'shadow_stroke_width': 30,
    'font': '/content/Bangers.ttf'
}

# Create the shadow text clip
shadow_text_clip = mp.TextClip(
    "Hello, World!",
    font=text_style_config['font'],
    fontsize=text_style_config['fontSize'],
    color=text_style_config['shadow_color'],  # Shadow color
    stroke_color=text_style_config['shadow_color'],  # Shadow stroke color
    stroke_width=text_style_config['shadow_stroke_width'],  # Shadow thickness
    method='caption',
    kerning=2
).set_duration(5).set_position(('center', 'center')).set_opacity(text_style_config['shadow_opacity'])

# Create the main text clip
text_clip = mp.TextClip(
    "Hello, World!",
    font=text_style_config['font'],
    fontsize=text_style_config['fontSize'],
    color=text_style_config['color'],
    stroke_color=text_style_config['stroke_color'],
    stroke_width=text_style_config['stroke_width'], # Main text color
    method='caption',
    kerning=2
).set_duration(5).set_position('center')

# Overlay the shadow text and the main text on the white background
final_clip = mp.CompositeVideoClip([background_clip, shadow_text_clip, text_clip])

# Display the final image
# Convert final_clip to an image and show it using matplotlib
final_clip = final_clip.set_duration(5).resize(width=720)  # Adjust the size if needed
final_frame = final_clip.get_frame(0)  # Get the first frame

# Convert numpy array to PIL Image
final_image = Image.fromarray(final_frame)

# Display the image
plt.imshow(final_image)
plt.axis('off')  # Hide axes
plt.show()
