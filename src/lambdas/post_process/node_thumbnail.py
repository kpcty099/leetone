"""
Thumbnail & Intro Card Generator — Phase 4 addition.

Produces:
  • A 4-second cinematic 1920×1080 intro title card (MoviePy ImageClip)
  • A 1280×720 YouTube thumbnail PNG saved to output/<slug>_thumbnail.png

Both use Pillow for rendering.  No external dependencies beyond existing ones.
"""
import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import moviepy.editor as mp

OUTPUT_DIR = "output"
W, H = 1920, 1080
TW, TH = 1280, 720   # Thumbnail dimensions
FPS = 24
INTRO_DUR = 4.0       # seconds

# ── Palette ──────────────────────────────────────────────────────────────────
BG_TOP     = (8,  10, 25)
BG_BOT     = (18, 12, 35)
C_EASY     = (78, 230, 100)    # green
C_MEDIUM   = (255, 178, 50)    # amber
C_HARD     = (255, 70, 80)     # red
C_CYAN     = (0, 212, 255)
C_WHITE    = (240, 240, 248)
C_MUTED    = (120, 120, 145)
C_ACCENT2  = (180, 90, 255)    # purple accent for number badge


def _difficulty_color(difficulty: str) -> tuple:
    d = difficulty.lower()
    if d == "easy":   return C_EASY
    if d == "hard":   return C_HARD
    return C_MEDIUM


def _font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf",   # Arial Bold
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/cour.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _gradient_bg(width: int, height: int) -> Image.Image:
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        t = y / height
        arr[y, :] = [int(BG_TOP[i] * (1-t) + BG_BOT[i] * t) for i in range(3)]
    return Image.fromarray(arr, "RGB")


def _draw_tag_chips(draw: ImageDraw.ImageDraw, tags: list, x: int, y: int,
                    font: ImageFont.FreeTypeFont) -> None:
    """Draw coloured pill-shaped tag chips horizontally."""
    chip_colors = [C_CYAN, C_ACCENT2, (255, 140, 0), C_EASY, C_MEDIUM]
    cx = x
    for i, tag in enumerate(tags[:5]):
        color = chip_colors[i % len(chip_colors)]
        bb = draw.textbbox((cx, y), tag, font=font)
        tw, th = bb[2]-bb[0], bb[3]-bb[1]
        pad = 10
        draw.rounded_rectangle(
            [cx - pad, y - 4, cx + tw + pad, y + th + 4],
            radius=8,
            fill=(*color, 40) if False else (30, 30, 50),  # fixed
            outline=color, width=1
        )
        draw.text((cx, y), tag, font=font, fill=color)
        cx += tw + 2*pad + 8


def _draw_grid_lines(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    """Draw subtle tech-grid lines in the background."""
    line_color = (255, 255, 255, 12)  # Very faint
    for x in range(0, width, 80):
        draw.line([(x, 0), (x, height)], fill=(20, 25, 50), width=1)
    for y in range(0, height, 80):
        draw.line([(0, y), (width, y)], fill=(20, 25, 50), width=1)


def _render_card(
    title: str,
    slug: str,
    difficulty: str,
    tags: list,
    width: int,
    height: int,
) -> np.ndarray:
    """Render a single static frame for the intro/thumbnail card."""
    img = _gradient_bg(width, height)
    draw = ImageDraw.Draw(img)

    scale = width / 1920  # Fonts scale with resolution

    f_huge   = _font(int(88 * scale))
    f_title  = _font(int(72 * scale))
    f_sub    = _font(int(40 * scale))
    f_tag    = _font(int(28 * scale))
    f_brand  = _font(int(26 * scale))

    diff_color = _difficulty_color(difficulty)
    pad = int(80 * scale)

    # ── Grid overlay ──────────────────────────────────────────────────────────
    _draw_grid_lines(draw, width, height)

    # ── Diagonal accent bar (top-right) ───────────────────────────────────────
    for i in range(8):
        offset = i * int(18 * scale)
        alpha = 255 - i * 28
        if alpha < 0: break
        col = (*C_CYAN[:3],) if False else C_CYAN  # solid
        draw.line(
            [(width - offset - int(300*scale), 0),
             (width - offset, int(260*scale))],
            fill=(*C_CYAN[:2], C_CYAN[2], alpha) if False else (0, 60, 80),
            width=2
        )

    # ── LeetCode branding (top left) ─────────────────────────────────────────
    brand = "LeetCode Explainer"
    draw.text((pad, int(28 * scale)), brand, font=f_brand, fill=C_MUTED)

    # ── Difficulty badge (top right) ──────────────────────────────────────────
    diff_text = difficulty.upper()
    diff_bb = draw.textbbox((0, 0), diff_text, font=f_sub)
    diff_w = diff_bb[2] - diff_bb[0]
    diff_x = width - pad - diff_w - 30
    diff_y = int(22 * scale)
    draw.rounded_rectangle(
        [diff_x - 14, diff_y - 4, diff_x + diff_w + 14, diff_y + diff_bb[3] - diff_bb[1] + 10],
        radius=8, fill=(15, 15, 25), outline=diff_color, width=2
    )
    draw.text((diff_x, diff_y), diff_text, font=f_sub, fill=diff_color)

    # ── Central glowing circle (number badge) ────────────────────────────────
    # Extract problem number from slug (e.g. two-sum → no number; use DB lookup style only)
    cx = int(width * 0.18)
    cy = int(height * 0.48)
    r  = int(90 * scale)
    # Outer glow rings
    for glow_r in range(r + int(30*scale), r - 1, -4):
        alpha_f = max(0, 1 - (glow_r - r) / (30 * scale))
        g_col = tuple(int(c * alpha_f * 0.35) for c in C_ACCENT2)
        draw.ellipse(
            [cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r],
            outline=g_col, width=1
        )
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(18, 12, 40), outline=C_ACCENT2, width=3)
    lc_text = "LC"
    lc_bb = draw.textbbox((0, 0), lc_text, font=f_sub)
    draw.text(
        (cx - (lc_bb[2]-lc_bb[0])//2, cy - (lc_bb[3]-lc_bb[1])//2),
        lc_text, font=f_sub, fill=C_ACCENT2
    )

    # ── Main title ────────────────────────────────────────────────────────────
    title_x = int(width * 0.32)
    title_y = int(height * 0.30)
    max_title_w = width - title_x - pad

    # Word-wrap title
    words = title.split()
    lines, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        bb = draw.textbbox((0, 0), test, font=f_title)
        if bb[2]-bb[0] > max_title_w and cur:
            lines.append(" ".join(cur)); cur = [w]
        else:
            cur.append(w)
    if cur: lines.append(" ".join(cur))

    ty = title_y
    for line in lines[:3]:
        # Shadow
        draw.text((title_x + 3, ty + 3), line, font=f_title, fill=(0, 0, 0))
        draw.text((title_x, ty), line, font=f_title, fill=C_WHITE)
        ty += int(85 * scale)

    # ── Horizontal divider ────────────────────────────────────────────────────
    div_y = ty + int(10 * scale)
    draw.line([(title_x, div_y), (width - pad, div_y)], fill=diff_color, width=2)

    # ── Tag chips ─────────────────────────────────────────────────────────────
    if tags:
        _draw_tag_chips(draw, tags, title_x, div_y + int(24 * scale), f_tag)

    # ── Bottom bar ────────────────────────────────────────────────────────────
    bar_h = int(6 * scale)
    # Gradient bar via individual rectangles
    for x in range(width):
        t = x / width
        r2 = int(C_ACCENT2[0] * (1-t) + C_CYAN[0] * t)
        g2 = int(C_ACCENT2[1] * (1-t) + C_CYAN[1] * t)
        b2 = int(C_ACCENT2[2] * (1-t) + C_CYAN[2] * t)
        draw.line([(x, height - bar_h), (x, height)], fill=(r2, g2, b2))

    return np.array(img)


# ── Public API ────────────────────────────────────────────────────────────────

def generate_intro_clip(
    title: str,
    slug: str,
    difficulty: str,
    tags: list,
    duration: float = INTRO_DUR,
) -> mp.ImageClip:
    """
    Returns a MoviePy ImageClip suitable for prepending to the final video.
    Adds a subtle fade-in and a slow Ken Burns zoom.
    """
    frame = _render_card(title, slug, difficulty, tags, W, H)
    clip = mp.ImageClip(frame).set_duration(duration).set_fps(FPS)

    # Ken Burns: very slight zoom from 1.0 → 1.04
    def zoom(t):
        scale = 1.0 + 0.01 * (t / duration)
        new_w = int(W * scale)
        new_h = int(H * scale)
        img = Image.fromarray(frame).resize((new_w, new_h), Image.LANCZOS)
        # Centre crop
        left = (new_w - W) // 2
        top  = (new_h - H) // 2
        img = img.crop((left, top, left + W, top + H))
        return np.array(img)

    zoomed = mp.VideoClip(zoom, duration=duration).set_fps(FPS)
    return zoomed.crossfadein(0.5)


def generate_thumbnail(
    title: str,
    slug: str,
    difficulty: str,
    tags: list,
) -> str:
    """
    Saves a 1280×720 YouTube thumbnail PNG.
    Returns the path.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"{slug}_thumbnail.png")
    frame = _render_card(title, slug, difficulty, tags, TW, TH)
    img = Image.fromarray(frame)
    img.save(out_path)
    print(f"[thumbnail] Saved thumbnail -> {out_path}")
    return out_path


def thumbnail_node(state: dict) -> dict:
    """
    LangGraph node: generate intro clip metadata and YouTube thumbnail.
    Stores thumbnail_path in state.
    """
    title      = state.get("problem_title", "Unknown Problem")
    slug       = state.get("problem_slug", "problem")
    difficulty = state.get("difficulty", "Medium")
    chapters   = state.get("chapters", [])
    tags = []
    if chapters:
        tags = chapters[0].get("tags", [])

    print(f"[thumbnail_node] Generating thumbnail for '{title}' ({difficulty})")
    try:
        thumb_path = generate_thumbnail(title, slug, difficulty, tags)
        return {"thumbnail_path": thumb_path, "error": ""}
    except Exception as e:
        print(f"[thumbnail_node] WARNING: {e}")
        return {"thumbnail_path": "", "error": ""}
