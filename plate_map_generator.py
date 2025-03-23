import argparse
from csv import DictReader
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont
import webcolors

arg_parser = argparse.ArgumentParser(
    prog="96-Well Plate Map Generator",
    description="Generate annotated plate maps from CSV input.",
    epilog="Script by Robert Pazdzior (2025) <rpazdzior@protonmail.com>."
)

arg_parser.add_argument('annotation_csv',
                        help='''Annotations CSV file containing columns: 
                                well, fill, label, label_color.''')

arg_parser.add_argument('-t', '--title',
                        help='''Title string.''')

arg_parser.add_argument('-s', '--subtitle',
                        help='''Subtitle string.''')

arg_parser.add_argument('-o', '--output',
                        help='''Specify the image output path.''')

arg_parser.add_argument('-d', '--date',
                        help='''Override the date text.''')

def import_annotations(annot_path:str) -> dict:
    # Read in CSV to list of dicts
    with open(annot_path, encoding='utf8') as annot:
        reader = DictReader(annot)
        annot_list_dicts = [row for row in reader]

    return annot_list_dicts

# Draw at a multiple of the output size for smoother appearance (supersampling)
RES_FACTOR = 4
DPI = 300 # Output DPI
IMG_SIZE = ( int(11 * DPI) * RES_FACTOR, int(8.5 * DPI) * RES_FACTOR)

# Constants for the grid layout
NUM_ROWS = 8
NUM_COLS = 12
WELL_DIAMETER = 0.7 * DPI * RES_FACTOR  # Scale well diameter for high resolution
WELL_PADDING = 0.1 * DPI * RES_FACTOR  # Scale WELL_PADDING for high resolution
OUTLINE_WIDTH = int(0.02 * RES_FACTOR * DPI)

# Calculate the starting position (top-left corner) for the first well
X_START = IMG_SIZE[0]/2 - ( (NUM_COLS * (WELL_DIAMETER+WELL_PADDING))/2)
Y_START = IMG_SIZE[1]/2 - ( (NUM_ROWS * (WELL_DIAMETER+WELL_PADDING))/2) + 0.5 * DPI * RES_FACTOR

# Define labels for rows (A to H) and columns (1 to 12)
ROW_LABELS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
COL_LABELS = [str(i) for i in range(1, NUM_COLS + 1)]

# Font sizes
ROW_COL_FONT_SIZE = 0.3 * DPI * RES_FACTOR  # Row/col labels
ANNOT_FONT_SIZE = 0.15 * DPI * RES_FACTOR   # Well annotations
TITLE_FONT_SIZE = 0.4 * DPI * RES_FACTOR    # Title and subtitles

def get_well_coords(well: str) -> tuple:
    '''Returns the center XY coordinates of the given well ('A2', 'H12', etc) as a tuple.'''
    VALID_ROWS = 'ABCDEFGH' # A-H
    VALID_COLS = [i for i in range(1,13,1)] # 1-12

    row = well[0]
    col = int(well[1:])
    
    row_idx = ROW_LABELS.index(row)
    col_idx = col - 1

    x = X_START + col_idx * (WELL_DIAMETER + WELL_PADDING) + WELL_DIAMETER/2
    y = Y_START + row_idx * (WELL_DIAMETER + WELL_PADDING) + WELL_DIAMETER/2

    return (x,y)

def draw_template_platemap(draw:ImageDraw.ImageDraw) -> None:
    '''Draws the base well map: well outlines and col/row labels.'''
    try:
        font = ImageFont.truetype("arial.ttf", ROW_COL_FONT_SIZE)  # Larger font for high-res image
    except IOError:
        font = ImageFont.load_default()

    # Draw the grid of wells
    for row in range(NUM_ROWS):
        for col in range(NUM_COLS):
            x = X_START + col * (WELL_DIAMETER + WELL_PADDING)
            y = Y_START + row * (WELL_DIAMETER + WELL_PADDING)
            
            # Draw the well with outline and fill
            draw.ellipse([x, y, x + WELL_DIAMETER, 
                        y + WELL_DIAMETER],
                        fill=None,
                        outline=(0, 0, 0), 
                        width=OUTLINE_WIDTH)

    # Add row labels (A to H)
    for row in range(NUM_ROWS):
        label_width = font.getbbox(ROW_LABELS[row])[2]
        label_height = font.getbbox(ROW_LABELS[row])[3]
        draw.text((X_START - label_width * 1.25, 
                Y_START + row * (WELL_DIAMETER + WELL_PADDING) + (WELL_DIAMETER-WELL_PADDING)/2 - 0.9*label_height/2), 
                ROW_LABELS[row], 
                font=font, 
                fill=(0, 0, 0))

    # Add column labels (1 to 12)
    for col in range(NUM_COLS):
        label_width = font.getbbox(COL_LABELS[col])[2]
        label_height = font.getbbox(COL_LABELS[col])[3]
        draw.text((X_START + col * (WELL_DIAMETER + WELL_PADDING) + WELL_DIAMETER/2 - label_width/2 * 1.2, 
                Y_START - label_height*1.25),
                COL_LABELS[col], font=font, fill=(0, 0, 0))

def draw_annotations(draw:ImageDraw.ImageDraw, annots:dict) -> None:
    for annot in annots:
        coords = get_well_coords(annot['well'])
        fill_color = webcolors.name_to_rgb(annot['fill']) if annot['fill'] else (255,255,255)
        draw.circle(coords, 
                    WELL_DIAMETER/2, 
                    fill=fill_color,
                    outline=(0,0,0),
                    width=OUTLINE_WIDTH)

        label = annot['label'].replace('\\n', '\n')
        annot_font = ImageFont.truetype("arial.ttf", ANNOT_FONT_SIZE) 
        annot_width = draw.textbbox((0,0), label, align='center', font=annot_font)[2]
        annot_height = draw.textbbox((0,0), label, align='center', font=annot_font)[3]

        red_annot_font_size = ANNOT_FONT_SIZE
        while annot_width > WELL_DIAMETER:
            red_annot_font_size = red_annot_font_size * 0.7
            annot_font = ImageFont.truetype("arial.ttf", red_annot_font_size) 
            annot_width = draw.textbbox((0,0), label, align='center', font=annot_font)[2]
            annot_height = draw.textbbox((0,0), label, align='center', font=annot_font)[3]

        label_color = webcolors.name_to_rgb(annot['label_color']) if annot['label_color'] else (0,0,0)
        draw.text((coords[0] - annot_width/2,
                coords[1] - annot_height/2),
                text=label,
                align='center',
                fill=label_color,
                font=annot_font)

def draw_title(draw:ImageDraw.ImageDraw, text:str) -> None:
    title_font = ImageFont.truetype("arial.ttf", TITLE_FONT_SIZE)
    draw.text((X_START,
            title_font.getmetrics()[0]*0.5),
            text,
            fill=(0,0,0),
            font=title_font)

def draw_subtitle(draw:ImageDraw.ImageDraw, text:str) -> None:
    title_font = ImageFont.truetype("arial.ttf", TITLE_FONT_SIZE)
    subtitle_font = ImageFont.truetype("arial.ttf", TITLE_FONT_SIZE * 0.5)

    draw.text((X_START + subtitle_font.getmetrics()[1]*1,
            title_font.getmetrics()[0]*1.8),
            text.replace('\\n', '\n'),
            fill=(0,0,0),
            font=subtitle_font)

def draw_date(draw:ImageDraw.ImageDraw, text:str = None) -> None:
    title_font = ImageFont.truetype("arial.ttf", TITLE_FONT_SIZE)
    date_font = ImageFont.truetype("arial.ttf", TITLE_FONT_SIZE * 0.5)
    date = text if text else datetime.now().strftime("%Y.%m.%d")
    draw.text((IMG_SIZE[0] - X_START - WELL_PADDING,
              title_font.getmetrics()[0]*1),
              text=date,
              anchor="rt",
              fill=(0,0,0),
              font=date_font)

if __name__ == "__main__":
    args = arg_parser.parse_args()

    title = args.title
    subtitle = args.subtitle
    annots = import_annotations(args.annotation_csv)
    date_text = args.date
    out_dir = args.output

    image = Image.new('RGB', IMG_SIZE, color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    draw_template_platemap(draw)
    draw_annotations(draw, annots)
    if title:
        draw_title(draw, title)
    if subtitle:
        draw_subtitle(draw, subtitle)
    
    draw_date(draw, date_text)
    
    outfile = out_dir
    if not out_dir:
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        outfile = f'{timestamp}_plate_map.png'

    resized_img = image.resize((11 * DPI, int(8.5 * DPI)),
                               resample=Image.Resampling.LANCZOS)
    resized_img.save(outfile)