import os
import sys
import glob
import random
import replicate
from PIL import Image, ImageFilter

from generate_backgrounds import CHAR_NAMES, MOTIFS, COLOR_WORDS
from test_scenes_only import run_with_retry

INPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(INPUT_DIR, "scene_previews")
TMP_DIR = os.path.join(INPUT_DIR, "_tmp_work")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

MODEL = "black-forest-labs/flux-fill-pro"

CANVAS_W, CANVAS_H = 1920, 1536
SEED = 42  # fixed so the scattered layout is reproducible between runs


def find_character_files():
    files = []
    for ext in ("*.webp", "*.png", "*.jpg", "*.jpeg"):
        files.extend(glob.glob(os.path.join(INPUT_DIR, ext)))
    # keep only ones whose stem is a plain number 1-19 (skip generated/temp files)
    numbered = []
    for f in files:
        stem = os.path.splitext(os.path.basename(f))[0]
        if stem.isdigit():
            numbered.append((int(stem), f))
    numbered.sort(key=lambda t: t[0])
    return numbered


def build_canvas_and_mask():
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (140, 140, 140, 255))
    mask = Image.new("L", (CANVAS_W, CANVAS_H), 255)  # 255 = fill, 0 = keep

    placements = []  # (char_resized, (x, y))
    files = find_character_files()
    print(f"Found {len(files)} numbered character files.")

    rng = random.Random(SEED)
    # scatter freely across the whole canvas -- randomized position and size,
    # pasted in shuffled order so characters can drift over/under each other
    # instead of sitting in neat grid cells
    order = list(range(len(files)))
    rng.shuffle(order)

    # base size roughly a fifth of the canvas height, with some variation,
    # so figures are large enough to overlap generously
    base_target = int(CANVAS_H * 0.34)

    for i in order:
        num, path = files[i]
        char = Image.open(path).convert("RGBA")
        cw, ch = char.size

        scale_jitter = rng.uniform(0.75, 1.15)
        target = int(base_target * scale_jitter)
        ratio = target / max(cw, ch)
        new_w, new_h = int(cw * ratio), int(ch * ratio)
        char_resized = char.resize((new_w, new_h), Image.LANCZOS)

        # allow generous overlap -- centers can land anywhere across the
        # canvas, including near/over the edges, not confined to grid cells
        cx = rng.uniform(0.05, 0.95) * CANVAS_W
        cy = rng.uniform(0.05, 0.95) * CANVAS_H
        x = int(cx - new_w / 2)
        y = int(cy - new_h / 2)

        canvas.paste(char_resized, (x, y), char_resized)
        alpha = char_resized.split()[-1]
        mask.paste(0, (x, y), alpha)
        placements.append((char_resized, (x, y)))

    # small buffer so decorative marks don't touch the characters directly
    mask = mask.filter(ImageFilter.MinFilter(5))

    return canvas.convert("RGB"), mask, placements


def build_prompt():
    # each character's own surface-pattern motif (skin/fur/plumage), and
    # each character's own locked card color -- the two things every
    # character actually owns. This is my best synthesis of everything that
    # worked well across all the single-character tests: soft painterly
    # medium, muted harmonious color, restrained but recognizable texture,
    # generous breathing room so the 19 characters stay the visual stars.
    patterns = [MOTIFS[k].split(",")[0].strip() for k in sorted(MOTIFS.keys(), key=int)]
    pattern_list = "; ".join(patterns)
    colors = [COLOR_WORDS[k].split(",")[0].strip() for k in sorted(COLOR_WORDS.keys(), key=int)]
    color_list = ", ".join(colors)

    return (
        f"A single, sprawling, quiet piece of painterly art -- soft "
        f"watercolor and waxy crayon combined, muted and sophisticated, "
        f"like a fine art print, not photorealistic or cartoonish. The "
        f"whole canvas is a gentle, harmonious color-field wash blending "
        f"together every one of these colors, softly and unevenly, "
        f"nowhere flat or perfectly smooth: {color_list}. Within that soft "
        f"wash, woven through as quiet texture rather than bold pattern, "
        f"the following surface motifs appear here and there, faint and "
        f"restrained, never dominating: {pattern_list}. Leave generous "
        f"open, breathing negative space throughout so nothing feels "
        f"crowded -- the background is calm and quiet, a supporting "
        f"stage, never competing for attention. A soft, fine grain sits "
        f"over the whole image. No text, no logos, no watermark."
    )


def generate():
    canvas, mask, placements = build_canvas_and_mask()

    canvas_path = os.path.join(TMP_DIR, "all_together_canvas.png")
    mask_path = os.path.join(TMP_DIR, "all_together_mask.png")
    canvas.save(canvas_path)
    mask.save(mask_path)

    prompt = build_prompt()
    print(f"prompt: {prompt}\n")

    output = run_with_retry(
        MODEL,
        input={
            "image": open(canvas_path, "rb"),
            "mask": open(mask_path, "rb"),
            "prompt": prompt,
            "output_format": "png",
        },
    )
    if isinstance(output, list):
        output = output[0]
    result_bytes = output.read() if hasattr(output, "read") else _fetch(output)

    raw_path = os.path.join(TMP_DIR, "all_together_raw.png")
    with open(raw_path, "wb") as f:
        f.write(result_bytes)

    bg = Image.open(raw_path).convert("RGBA")
    if bg.size != (CANVAS_W, CANVAS_H):
        bg = bg.resize((CANVAS_W, CANVAS_H), Image.LANCZOS)

    # paste every original character back on top, pixel-perfect, so the AI
    # output can never alter any of the 19 characters themselves
    for char_resized, pos in placements:
        bg.paste(char_resized, pos, char_resized)

    final_path = os.path.join(OUT_DIR, "ALL_CHARACTERS_TOGETHER.png")
    bg.save(final_path)
    print(f"saved {final_path}")


def _fetch(url):
    import urllib.request
    with urllib.request.urlopen(url) as r:
        return r.read()


if __name__ == "__main__":
    generate()
