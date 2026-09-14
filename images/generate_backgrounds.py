import os
import sys
import glob
import hashlib
import replicate
from PIL import Image, ImageFilter, ImageChops

# ---- config ----
# Point this at the folder with your character .webp/.png files
INPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = "/Users/leovickman/Documents/InfinityPuzzles/web/public/images/character pictures"
TMP_DIR = os.path.join(INPUT_DIR, "_tmp_work")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

STYLE = (
    "solid 2D blocky landscape illustration, representational and bold: the "
    "specific scene described below is rendered as a clear, easily readable "
    "environment -- like polished children's book background art -- with real "
    "depth and instantly recognizable elements (trees, roots, water, rocks, "
    "mist, sky, light) built as bold, confident, solid geometric shapes, never "
    "abstracted into unrecognizable blobs and never thin, wispy, or delicate "
    "linework standing in for a whole shape. No pine trees, no generic "
    "clipart-style trees -- only what is explicitly named in the scene, built "
    "as bold solid masses. Each shape has a smooth internal gradient shading "
    "from one tone to another for volume and directional light, while staying "
    "graphic and solid rather than soft or hazy. A heavy, clearly visible "
    "grain/noise texture sits over the entire image. The composition has a "
    "clear, calm sense of depth -- foreground, midground, and background -- "
    "using a small number of large, clearly readable shapes rather than "
    "excessive tiny scattered clutter. The palette stays strictly within the "
    "specified colors."
)

# exact base color (top, bottom) for each character, matched to their real card
# design in the app. If top == bottom it's a solid color, otherwise a soft
# vertical gradient. This is rendered in Python (not guessed by the AI) so the
# base tone is always pixel-accurate.
CARD_BG = {
    "1":  ((70, 150, 205), (70, 150, 205)),   # Dolores -- medium sky blue
    "2":  ((235, 165, 190), (235, 165, 190)), # Zuki -- soft dusty pink
    "3":  ((160, 135, 195), (160, 135, 195)), # Mani -- soft lavender purple
    "4":  ((60, 20, 25), (60, 20, 25)),       # Ziggy-Lou -- dark maroon red-brown
    "5":  ((210, 190, 60), (110, 110, 70)),   # Lana Manana -- mustard yellow to olive
    "6":  ((195, 215, 170), (195, 215, 170)), # Tanya -- light sage green
    "7":  ((140, 205, 190), (140, 205, 190)), # Mambo Viento -- soft teal mint
    "8":  ((195, 180, 215), (195, 180, 215)), # Salvador -- light lavender
    "9":  ((45, 80, 50), (45, 80, 50)),       # Pinto -- dark forest green
    "10": ((210, 155, 165), (210, 155, 165)), # Sixten -- dusty mauve pink
    "11": ((90, 190, 190), (110, 110, 110)),  # Coco -- cyan teal to gray
    "12": ((200, 180, 150), (120, 105, 115)), # Mona Moon -- tan beige to muted purple-gray
    "13": ((210, 195, 70), (75, 65, 40)),     # Borro -- mustard yellow to dark olive brown
    "14": ((90, 160, 210), (40, 90, 150)),    # Pepe -- sky blue to deep blue
    "15": ((95, 45, 80), (190, 120, 140)),    # Ronda -- dark magenta purple to dusty pink
    "16": ((25, 40, 70), (25, 40, 70)),       # Rumi -- dark navy blue
    "17": ((150, 125, 190), (150, 125, 190)), # Daffy Giraffy -- medium purple lavender
    "18": ((225, 130, 55), (170, 55, 45)),    # Jerry -- warm orange to deep red
    "19": ((55, 48, 45), (55, 48, 45)),       # Mira -- dark charcoal brown-gray
}

# color words for the prompt: the card's own base tone(s) plus that character's
# own illustration colors -- NOT a palette shared across all 19, so every
# background only ever uses colors that already belong to that specific card
COLOR_WORDS = {
    "1":  "medium sky blue, deep indigo purple, teal, mint green",
    "2":  "soft dusty pink, warm brown, cream",
    "3":  "soft lavender purple, jungle green, coral pink, golden yellow, sky blue",
    "4":  "dark maroon red-brown, cream",
    "5":  "mustard yellow, olive green, soft lavender purple, sky blue, orange",
    "6":  "light sage green, navy blue, sky blue, cream",
    "7":  "soft teal mint, mustard yellow, maroon, dusty pink",
    "8":  "light lavender, dark purple, teal, coral red",
    "9":  "dark forest green, burnt orange, near-black brown",
    "10": "dusty mauve pink, dark maroon, sage green",
    "11": "cyan teal, muted gray, navy blue, coral red, burnt orange, sky blue",
    "12": "tan beige, muted purple-gray, lavender, dusty pink",
    "13": "mustard yellow, dark olive brown, deep purple-gray, lavender",
    "14": "sky blue, deep blue, cream, burnt orange",
    "15": "dark magenta purple, dusty pink, teal mint",
    "16": "dark navy blue, forest green, coral red, deep purple, cream",
    "17": "medium purple lavender, mustard yellow, dark navy",
    "18": "warm orange, deep red, cream, dark maroon",
    "19": "dark charcoal brown-gray, dusty pink, coral red, cream",
}
DEFAULT_COLOR_WORDS = "colors matching the character's own illustration"

# a recurring surface-pattern motif borrowed from each character's own skin/fur,
# echoed subtly into the background so the whole set reads as one family
MOTIFS = {
    "1": "small overlapping crescent-moon scale shapes, like the creature's own hide, echoed faintly in the water texture",
    "2": "soft small round dot spots, like the fawn's own coat, echoed faintly in foliage clusters",
    "3": "gentle wavy parallel stripes, like the bird's own plumage, echoed faintly in leaf shapes",
    "4": "thin hand-drawn zigzag linework accents, like the creature's own fur markings, echoed faintly along branch silhouettes",
    "5": "soft rounded cloud-scallop shapes, like the llama's own coat pattern, echoed faintly in the sky clouds",
    "6": "flame-like organic stripe shapes, like the tiger's own coat, echoed faintly in shadow patterns",
    "7": "bold diagonal parallel stripes, like the dragon's own hide, echoed faintly in cloud streaks",
    "8": "small ring/circle spot shapes, like the creature's own markings, echoed faintly as background accents",
    "9": "organic rosette blob spots, like the leopard's own coat, echoed faintly in foliage shadows",
    "10": "sharp triangular zigzag spike stripes, like the cat's own fur, echoed faintly along the path edges",
    "11": "small oval dot clusters, like the bird's own wing pattern, echoed faintly in the foliage",
    "12": "soft rounded organic patch shapes, like the cow's own markings, echoed faintly in cloud shapes",
    "13": "small round dot texture, like the rhino's own skin, echoed faintly in ground texture",
    "14": "scalloped wave edges, like the penguin's own wing shape, echoed faintly in water/ice edges",
    "15": "small overlapping crescent-moon scale shapes, like the crocodile's own hide, echoed faintly in water ripples",
    "16": "thin dashed line accents, like the parrot's own markings, echoed faintly along vines",
    "17": "hexagonal patch shapes, like the giraffe's own coat, echoed faintly in cloud or grass-clump shapes",
    "18": "soft rounded organic patch shapes, like the dog's own coat, echoed faintly in ground texture",
    "19": "fine dash/tick-mark texture, like the camel's own coat, echoed faintly across the sand dunes",
}
DEFAULT_MOTIF = "a subtle geometric texture accent echoing the creature's own surface pattern"

ORIENTATIONS = {
    "portrait": (864, 1536),
    "landscape": (1536, 864),
}

MODEL = "black-forest-labs/flux-fill-pro"

# scene per character, keyed by filename (without extension)
# 1 Dolores/Narwhal, 2 Zuki/Deer, 3 Mani/Toucan, 4 Ziggy-Lou/Fox, 5 Lana Manana/Llama,
# 6 Tanya/Tiger, 7 Mambo Viento/Dragon, 8 Dali/Chameleon, 9 Pinto/Leopard,
# 10 Sixten/Cat, 11 Coco/Bird, 12 Mona Moon/Cow, 13 Borro/Rhino, 14 Pepe/Penguin,
# 15 Ronda/Crocodile, 16 Rumi/Parrot, 17 Daffy Thunder/Giraffe, 18 Jerry/Dog, 19 Mira/Camel
# scenes reflect each character's aura/essence from the character bible, not just their animal
SCENES = {
    "1": "a wide, dark water with no shores. Just the surface, and the depths below",
    "2": "a rocky shore on the far side of a river. Wet stones in faint light",
    "3": "a tall tree bathed in still light. Nothing moves but the air",
    "4": "a large flat rock in golden afternoon light. Nothing reveals who sat there",
    "5": "a sunlit clearing where the light falls as if it chose that exact spot",
    "6": "a narrow path disappearing into the darkness between the trees",
    "7": "dense jungle at dawn. A single yellow feather falls slowly to the ground",
    "8": "an explosion of wild flowers in every color. Dazzling in the middle of the day",
    "9": "a lone flat rock in open landscape. Early morning light, long shadows",
    "10": "the water's edge in the jungle. The surface so still the trees are mirrored perfectly",
    "11": "dark treetops against a starry sky. Nothing moves",
    "12": "a large tree in moonlight at midday. Mirror-smooth ground around it",
    "13": "an old, lonely baobab tree. Long shadows in evening light",
    "14": "a narrow path with dense vegetation on both sides. Light from only one direction",
    "15": "still water where the sky is reflected perfectly on the surface",
    "16": "beneath an old tree by the water. Evening. The moon reflected on the surface. Timeless",
    "17": "the sky seen from above. Clouds stretching in every direction",
    "18": "the jungle floor. Fallen leaves and thick roots. Something small lies hidden in the grass",
    "19": "desert in moonlight. Sand dunes as far as the eye can see. Absolute stillness",
}
DEFAULT_SCENE = "a soft, minimal natural landscape that suits this creature, gentle light"

CHAR_NAMES = {
    "1": "dolores", "2": "zuki", "3": "mani", "4": "ziggy-lou", "5": "lana-manana",
    "6": "tanya", "7": "mambo-viento", "8": "dali", "9": "pinto", "10": "sixten",
    "11": "coco", "12": "mona-moon", "13": "borro", "14": "pepe", "15": "ronda",
    "16": "rumi", "17": "daffy-thunder", "18": "jerry", "19": "mira",
}


def build_prompt(orientation, name):
    scene = SCENES.get(name, DEFAULT_SCENE)
    motif = MOTIFS.get(name, DEFAULT_MOTIF)
    colors = COLOR_WORDS.get(name, DEFAULT_COLOR_WORDS)
    return (
        f"An abstract background composition filling the entire canvas edge to edge. Style: {STYLE}. "
        f"Use all of these colors throughout the composition, spread across the large shapes as rich "
        f"multi-hue gradients rather than confined to one corner: {colors}. The shapes are {scene}. "
        f"The large gradient-filled shapes spread across most of the frame, reaching close to the edges "
        f"on all sides. Only a small area immediately surrounding the central figure stays open and "
        f"calm, so the figure reads clearly against the composition."
    )


def make_gradient(width, height, top_rgb, bottom_rgb):
    grad = Image.new("RGB", (width, height))
    px = grad.load()
    for row in range(height):
        t = row / max(1, height - 1)
        r = int(top_rgb[0] + (bottom_rgb[0] - top_rgb[0]) * t)
        g = int(top_rgb[1] + (bottom_rgb[1] - top_rgb[1]) * t)
        b = int(top_rgb[2] + (bottom_rgb[2] - top_rgb[2]) * t)
        for col in range(width):
            px[col, row] = (r, g, b)
    return grad


def make_canvas_and_mask(char_path, name, width, height, scale=0.5):
    char = Image.open(char_path).convert("RGBA")
    cw, ch = char.size

    # scale character to fit within `scale` of the smaller canvas dimension
    target = int(min(width, height) * scale)
    ratio = target / max(cw, ch)
    new_w, new_h = int(cw * ratio), int(ch * ratio)
    char_resized = char.resize((new_w, new_h), Image.LANCZOS)

    x = (width - new_w) // 2
    y = (height - new_h) // 2

    top_rgb, bottom_rgb = CARD_BG.get(name, ((238, 227, 204), (238, 227, 204)))
    canvas = make_gradient(width, height, top_rgb, bottom_rgb).convert("RGBA")
    canvas.paste(char_resized, (x, y), char_resized)

    tight_keep = Image.new("L", (width, height), 0)
    alpha = char_resized.split()[-1]
    tight_keep.paste(alpha, (x, y))  # 255 = exact character silhouette

    mask = Image.new("L", (width, height), 255)  # 255 = fill, 0 = keep
    mask.paste(0, (x, y), alpha)
    # a small dilation of the "keep" zone -- enough that decorative colors
    # can't touch her silhouette directly, but not large enough to read as a
    # visible ring/frame
    mask = mask.filter(ImageFilter.MinFilter(7))

    # the buffer ring = dilated keep-zone minus the character's own exact
    # silhouette -- this is the small protected strip touching her edge that
    # we'll make transparent instead of flat opaque color, so it doesn't read
    # as a hard "frame"
    dilated_keep = mask.point(lambda p: 255 if p == 0 else 0)  # invert: 255=keep
    ring_mask = ImageChops.subtract(dilated_keep, tight_keep)

    return canvas.convert("RGB"), mask, char_resized, (x, y), ring_mask


def composite_with_exact_base(raw_img, width, height, top_rgb, bottom_rgb):
    """Keep the AI's own colors only where it actually drew something
    (decorative shapes); everywhere the AI left plain/untouched, force it back
    to our exact base gradient. This keeps the base tone pixel-accurate while
    letting decorative elements have their own real color."""
    from PIL import ImageChops

    raw_img = raw_img.convert("RGB")
    gradient_ref = make_gradient(width, height, top_rgb, bottom_rgb)

    diff = ImageChops.difference(raw_img, gradient_ref).convert("L")
    # amplify small differences so subtle shapes still show through, then
    # soften the edges so the blend isn't harsh
    diff = diff.point(lambda p: min(255, int(p * 3.5)))
    diff = diff.filter(ImageFilter.GaussianBlur(2))

    return Image.composite(raw_img, gradient_ref, diff)


def apply_edge_fade(img, margin_ratio=0.08):
    """Fade the image's alpha to transparent right at the outer edges, so it
    blends into UI without a hard rectangular border."""
    from PIL import ImageChops

    img = img.convert("RGBA")
    w, h = img.size
    margin_x = max(1, int(w * margin_ratio))
    margin_y = max(1, int(h * margin_ratio))

    fade_mask = Image.new("L", (w, h), 255)
    px = fade_mask.load()
    for y in range(h):
        fade_y = min(1.0, min(y, h - 1 - y) / margin_y)
        for x in range(w):
            fade_x = min(1.0, min(x, w - 1 - x) / margin_x)
            px[x, y] = int(255 * min(fade_x, fade_y))

    r, g, b, a = img.split()
    new_alpha = ImageChops.multiply(a, fade_mask)
    return Image.merge("RGBA", (r, g, b, new_alpha))


def generate_one(char_path, name, orientation):
    os.makedirs(TMP_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    width, height = ORIENTATIONS[orientation]
    canvas, mask, char_resized, pos, ring_mask = make_canvas_and_mask(char_path, name, width, height)

    canvas_path = os.path.join(TMP_DIR, f"{name}_{orientation}_canvas.png")
    mask_path = os.path.join(TMP_DIR, f"{name}_{orientation}_mask.png")
    canvas.save(canvas_path)
    mask.save(mask_path)

    prompt = build_prompt(orientation, name)
    # same seed for portrait + landscape of the same character, so the AI's
    # creative choices (color mix, shape style) correlate between the two
    seed = int(hashlib.md5(name.encode()).hexdigest(), 16) % (2**31)

    print(f"  -> calling Replicate for {name} ({orientation})...")
    output = replicate.run(
        MODEL,
        input={
            "image": open(canvas_path, "rb"),
            "mask": open(mask_path, "rb"),
            "prompt": prompt,
            "output_format": "png",
            "outpaint": "None",
            "seed": seed,
        },
    )

    # replicate.run returns a FileOutput (or list of them) depending on version
    if isinstance(output, list):
        output = output[0]
    result_bytes = output.read() if hasattr(output, "read") else requests_get(output)

    os.makedirs(TMP_DIR, exist_ok=True)
    result_path_tmp = os.path.join(TMP_DIR, f"{name}_{orientation}_raw.png")
    with open(result_path_tmp, "wb") as f:
        f.write(result_bytes)

    bg = Image.open(result_path_tmp).convert("RGB")
    if bg.size != (width, height):
        # the model can return a slightly different bucketed resolution --
        # resize back to our exact canvas so the paste-back position lines up
        bg = bg.resize((width, height), Image.LANCZOS)

    # keep the AI's own colors only where it drew decorative shapes; force
    # everything else back to our exact base gradient
    top_rgb, bottom_rgb = CARD_BG.get(name, ((238, 227, 204), (238, 227, 204)))
    bg = composite_with_exact_base(bg, width, height, top_rgb, bottom_rgb).convert("RGBA")

    # paste the ORIGINAL unaltered character back on top, pixel-perfect,
    # so the AI output can never modify the character itself
    bg.paste(char_resized, pos, char_resized)

    # soft transparent fade at the outer edges so it blends into the app UI
    bg = apply_edge_fade(bg)

    label = CHAR_NAMES.get(name, name)
    final_path = os.path.join(OUTPUT_DIR, f"{name}_{label}_{orientation}.png")
    bg.save(final_path)
    print(f"  saved {final_path}")
    return final_path


def requests_get(url):
    import urllib.request
    with urllib.request.urlopen(url) as r:
        return r.read()


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    files = []
    for ext in ("*.webp", "*.png", "*.jpg", "*.jpeg"):
        files.extend(glob.glob(os.path.join(INPUT_DIR, ext)))
    files = sorted(set(files), key=lambda p: (len(os.path.splitext(os.path.basename(p))[0]), os.path.splitext(os.path.basename(p))[0]))
    if only:
        files = [f for f in files if os.path.splitext(os.path.basename(f))[0] == only]

    for path in files:
        name = os.path.splitext(os.path.basename(path))[0]
        print(f"Character {name}:")
        for orientation in ORIENTATIONS:
            generate_one(path, name, orientation)


if __name__ == "__main__":
    main()
