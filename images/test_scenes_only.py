import os
import sys
import time
import hashlib
import replicate
from PIL import Image

# reuse the color/scene dictionaries and exact-base compositing already
# defined in generate_backgrounds.py
from generate_backgrounds import (
    CARD_BG,
    COLOR_WORDS,
    SCENES,
    CHAR_NAMES,
    composite_with_exact_base,
)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scene_previews")
os.makedirs(OUT_DIR, exist_ok=True)

MODEL = "black-forest-labs/flux-1.1-pro"


# one single concrete noun-phrase per character -- deliberately much shorter
# than the full SCENES text, so the model has exactly one thing to gesture
# at instead of illustrating every element the full scene text names
CORE_MOTIF = {
    "1": "the water's still dark surface, depth beneath it",
    "2": "wet stones on a rocky shore, faint light",
    "3": "a tall tree in still light",
    "4": "a flat rock in golden light, empty but for a memory",
    "5": "a single beam of sunlight in a clearing",
    "6": "a narrow path vanishing into darkness",
    "7": "a single yellow feather falling",
    "8": "a burst of wild flowers",
    "9": "a flat rock with a long morning shadow",
    "10": "trees mirrored in still water",
    "11": "dark treetops against stars",
    "12": "a tree in moonlight, ground like a mirror",
    "13": "a lone baobab tree at dusk",
    "14": "a narrow path lit from one side",
    "15": "the sky reflected in still water",
    "16": "the moon reflected by an old tree at the water's edge",
    "17": "clouds seen from above",
    "18": "something small hidden in the grass",
    "19": "sand dunes in moonlight",
}
DEFAULT_MOTIF = "a soft, minimal natural feature"

# characters whose scene is meant to feel lush/leafy -- these get a denser,
# layered foliage treatment in the accent band instead of one single gesture
FOREST_NAMES = {"3", "4", "5", "6", "7", "9", "14", "18"}


# ============================================================================
# LOCKED WINNING FORMULA -- confirmed by Leo on 2_zuki_portrait_SCENEONLY and
# 19_silvana_portrait_SCENEONLY. Do not casually rewrite this template. If it
# needs to change, keep a copy of the working version first.
# ============================================================================
def build_locked_prompt(name):
    motif = CORE_MOTIF.get(name, DEFAULT_MOTIF)
    colors = COLOR_WORDS.get(name, "soft neutral tones")
    parts = [c.strip() for c in colors.split(",")]
    primary = parts[0]
    accent = parts[1] if len(parts) > 1 else parts[0]

    # be honest with the model about what the frame actually is -- our
    # post-processing always forces the real CARD_BG back in afterward, so if
    # that's a two-tone gradient, telling the model "flat, no gradient" just
    # contradicts what will actually appear and produces a muddled result
    top_rgb, bottom_rgb = CARD_BG.get(name, ((238, 227, 204), (238, 227, 204)))
    is_gradient = top_rgb != bottom_rgb
    if is_gradient:
        center_color_clause = (
            f"a soft, simple vertical gradient moving from {primary} at the "
            f"top to {accent} at the bottom"
        )
    else:
        center_color_clause = f"completely flat, solid {primary}"

    if name in FOREST_NAMES:
        edge_clause = (
            f"loose, lush foliage drawn the way a 4-year-old child would "
            f"draw it with a crayon and a fineliner pen -- clumsy, wobbly "
            f"outlines, crayon color scribbled on unevenly and going "
            f"outside the lines, simple leaf and undergrowth shapes with "
            f"no real proportion or skill, plus a few shaky fineliner "
            f"pen lines scribbled on top -- growing inward from the "
            f"edges. The shapes should still read clearly as leaves, "
            f"branches, or undergrowth, not pure random marks -- someone "
            f"looking at it should be able to tell it's foliage, evoking "
            f"{motif}, even though it's clumsy and childlike rather than "
            f"skilled"
        )
    else:
        edge_clause = (
            f"a loose gesture drawn the way a 4-year-old child would draw "
            f"it with a crayon and a fineliner pen -- clumsy, wobbly "
            f"outlines, crayon color scribbled on unevenly and going "
            f"outside the lines, a simple shape with no real proportion or "
            f"skill, plus a few shaky fineliner pen lines scribbled on top "
            f"-- growing inward from the edges. It should still read as a "
            f"recognizable hint of {motif}, not a pure random mark -- "
            f"someone looking at it should be able to tell roughly what it "
            f"is, even though it stays clumsy and childlike rather than "
            f"skilled or literal"
        )

    return (
        f"A piece of art drawn the way a 4-year-old child would draw it, "
        f"using only a wax crayon and a thin fineliner pen -- no paint, no "
        f"watercolor, no smooth gradients or washes anywhere, no adult "
        f"skill or polish, just clumsy, wobbly, naive crayon and fineliner "
        f"marks. The center of the image is completely empty and "
        f"untouched -- {center_color_clause}, pure, calm, and unbroken by "
        f"anything, taking up the large majority of the canvas as pure "
        f"negative space. All of the visual content in this piece lives "
        f"only right at the outer edges and corners of the canvas, "
        f"growing inward from the border like a world drawn in from "
        f"outside the frame -- {edge_clause}. This crayon-and-fineliner "
        f"content fades and thins out well before it reaches the center, "
        f"so the middle of the image stays completely empty and "
        f"untouched -- never let the marks spread inward far enough to "
        f"fill or crowd the center. A few tiny, sparse specks or grains "
        f"(stars, dust, or grain, barely-there) may drift into the empty "
        f"center. The edge content is drawn only in crayon and fineliner, "
        f"in muted grays, blacks, whites, and desaturated variants of "
        f"{accent}. No text, no "
        f"logos, no watermark."
    )


from generate_backgrounds import ORIENTATIONS


def run_with_retry(model, input, max_attempts=6):
    for attempt in range(1, max_attempts + 1):
        try:
            return replicate.run(model, input=input)
        except replicate.exceptions.ReplicateError as e:
            if getattr(e, "status", None) == 429 and attempt < max_attempts:
                wait = 12
                print(f"  rate limited, waiting {wait}s before retry ({attempt}/{max_attempts})...")
                time.sleep(wait)
                continue
            raise


# RETIRED: the old "abstract expressionism, only 2 flat colors, zero
# shading" formula. Superseded on 2026-07-23 once Leo pointed at two much
# stronger results (2_zuki and 19_silvana) that broke that rule -- both used
# a huge flat dominant field PLUS one richly-shaded illustrated horizon band,
# not flat abstract dots. build_locked_prompt() now encodes that instead.
# Kept empty so every character (including 2 and 7) runs the new formula.
CUSTOM_PROMPTS = {}


def generate(name, orientation="portrait"):
    aspect = "9:16" if orientation == "portrait" else "16:9"
    prompt = CUSTOM_PROMPTS.get(name) or build_locked_prompt(name)
    # deterministic per-character seed so re-running the locked prompt gives
    # a stable, comparable result instead of a fresh random roll every time
    seed = int(hashlib.md5(name.encode()).hexdigest(), 16) % (2**31)
    print(f"Generating {name} ({orientation}), seed={seed}...")
    print(f"  prompt: {prompt}\n")

    output = run_with_retry(
        MODEL,
        input={
            "prompt": prompt,
            "aspect_ratio": aspect,
            "output_format": "png",
            "seed": seed,
        },
    )
    if isinstance(output, list):
        output = output[0]
    result_bytes = output.read() if hasattr(output, "read") else _fetch(output)

    raw_path = os.path.join(OUT_DIR, f"_raw_{name}_{orientation}.png")
    with open(raw_path, "wb") as f:
        f.write(result_bytes)

    # force the exact locked card color back in as the base -- the AI's own
    # words/interpretation of "pink" etc. is never trusted, only its decorative
    # shapes are kept, everywhere else snaps back to the real card color
    width, height = ORIENTATIONS[orientation]
    raw_img = Image.open(raw_path).convert("RGB")
    if raw_img.size != (width, height):
        raw_img = raw_img.resize((width, height), Image.LANCZOS)
    top_rgb, bottom_rgb = CARD_BG.get(name, ((238, 227, 204), (238, 227, 204)))
    final = composite_with_exact_base(raw_img, width, height, top_rgb, bottom_rgb)

    label = CHAR_NAMES.get(name, name)
    path = os.path.join(OUT_DIR, f"{name}_{label}_{orientation}_SCENEONLY.png")
    final.save(path)
    print(f"  saved {path}")


def build_freeform_all_prompt():
    # every character's motif, thrown in together with zero structural
    # rules -- no locked base color, no center/edge composition, no medium
    # restriction. Purely for exploration: let the model hallucinate freely
    # across the whole cast of scenes in one image.
    motifs = [CORE_MOTIF[k] for k in sorted(CORE_MOTIF.keys(), key=int)]
    motif_list = "; ".join(motifs)
    return (
        f"A single piece of abstract art that freely hallucinates and "
        f"blends together all of the following moments into one dreamlike "
        f"composition, mixing and overlapping them however feels right, "
        f"with no rules about composition, color, or realism: {motif_list}. "
        f"Interpret this with complete creative freedom -- any medium, any "
        f"palette, any level of abstraction, any composition. No text, no "
        f"logos, no watermark."
    )


def generate_freeform_all(orientation="portrait"):
    aspect = "9:16" if orientation == "portrait" else "16:9"
    prompt = build_freeform_all_prompt()
    print(f"Generating freeform-all ({orientation})...")
    print(f"  prompt: {prompt}\n")

    output = run_with_retry(
        MODEL,
        input={
            "prompt": prompt,
            "aspect_ratio": aspect,
            "output_format": "png",
        },
    )
    if isinstance(output, list):
        output = output[0]
    result_bytes = output.read() if hasattr(output, "read") else _fetch(output)

    path = os.path.join(OUT_DIR, f"freeform_all_{orientation}.png")
    with open(path, "wb") as f:
        f.write(result_bytes)
    print(f"  saved {path}")


def _fetch(url):
    import urllib.request
    with urllib.request.urlopen(url) as r:
        return r.read()


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    orientation_arg = sys.argv[2] if len(sys.argv) > 2 else "portrait"
    orientations = ["portrait", "landscape"] if orientation_arg == "both" else [orientation_arg]

    if only == "all":
        first = True
        for orientation in orientations:
            if not first:
                time.sleep(11)
            first = False
            generate_freeform_all(orientation)
    else:
        names = [only] if only else sorted(SCENES.keys(), key=int)
        first = True
        for name in names:
            for orientation in orientations:
                if not first:
                    time.sleep(11)  # stay under the reduced rate limit
                first = False
                generate(name, orientation)
