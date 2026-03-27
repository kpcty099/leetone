"""
Video Renderer — renders each chapter into a .mp4 file.
Uses Pillow for frame composition + MoviePy for audio sync.
If animation_path exists, overlays Manim clip.
If not, renders code/text + step bullets with syntax-like coloring.
Phase 4: real tokenize-based syntax highlighting + [[keyword]] marker rendering.
"""

import os, sys, shutil, json, io, time, tokenize, gc, keyword, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import moviepy.editor as mp
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.core.tools.huggingface_tools import generate_huggingface_image

try:
    from src.core.tools.progress_tracker import tracker as _tracker
except Exception:
    _tracker = None

def safe_print(msg: str):
    """Prints a message to console in a Windows-safe way (UTF-8)."""
    try:
        sys.stdout.buffer.write((msg + "\n").encode('utf-8'))
        sys.stdout.flush()
    except Exception:
        print(msg.encode('ascii', errors='replace').decode('ascii'))

import sys

VIDEO_DIR = "video_temp/video"

# ── Color palette ──────────────────────────────────────────────────────────────
BG_DARK        = (14, 14, 18)
BG_CARD        = (22, 22, 30)
ACCENT_CYAN    = (0, 212, 255)
ACCENT_ORANGE  = (255, 140, 0)
ACCENT_GREEN   = (78, 230, 100)
ACCENT_PINK    = (255, 80, 140)
ACCENT_YELLOW  = (255, 220, 50)
TEXT_WHITE     = (240, 240, 245)
TEXT_MUTED     = (140, 140, 160)
CODE_BG        = (26, 28, 36)
CODE_COLOR     = (166, 226, 46)

W, H = 1920, 1080
FPS  = 24
PAD  = 80

# Token colour map (RGB)
TOK_KEYWORD  = (102, 153, 255)   # blue
TOK_STRING   = (255, 165, 80)    # orange
TOK_COMMENT  = (110, 110, 130)   # gray
TOK_NUMBER   = (200, 120, 255)   # purple
TOK_FUNC     = (78, 230, 100)    # green
TOK_DEFAULT  = TEXT_WHITE if False else (240, 240, 245)  # resolved below

# Keyword set
_KW_SET = set(keyword.kwlist)


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/Inter-Bold.ttf",
        "C:/Windows/Fonts/JetBrainsMono-Bold.ttf",
        "C:/Windows/Fonts/consola.ttf",   # Consolas
        "C:/Windows/Fonts/cour.ttf",      # Courier New
        "C:/Windows/Fonts/arial.ttf",     # Arial
    ] if bold else [
        "C:/Windows/Fonts/Inter-Regular.ttf",
        "C:/Windows/Fonts/JetBrainsMono-Regular.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/lucon.ttf",     # Lucida Console
        "C:/Windows/Fonts/cour.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _gradient_bg(accent_rgb: tuple = (20, 20, 45)) -> Image.Image:
    """Create a deep, premium gradient with a subtle corner glow."""
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)
    
    # Base gradient
    for y in range(H):
        t = y / H
        color = [
            int(BG_DARK[i] * (1-t) + (10, 10, 20)[i] * t)
            for i in range(3)
        ]
        draw.line([(0, y), (W, y)], fill=tuple(color))
    
    # Subtle radial glow from bottom-right (accent color)
    glow_surface = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_surface)
    center = (W * 0.9, H * 0.9)
    for r in range(1200, 0, -20):
        alpha = int(15 * (1 - r/1200)) # very subtle
        gd.ellipse([center[0]-r, center[1]-r, center[0]+r, center[1]+r], 
                   fill=(*accent_rgb, alpha))
    
    img.paste(glow_surface, (0, 0), glow_surface)
    return img


def _draw_vignette(img: Image.Image):
    """Adds a professional vignette to darken edges and focus center."""
    draw = ImageDraw.Draw(img, "RGBA")
    for r in range(0, 150):
        # radial mask from center
        alpha = int(120 * (r / 150))
        draw.rectangle([0, 0, W, r], fill=(0, 0, 0, alpha)) # Top
        draw.rectangle([0, H-r, W, H], fill=(0, 0, 0, alpha)) # Bottom
    return img


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines, line = [], []
    for w in words:
        test = " ".join(line + [w])
        bb = draw.textbbox((0, 0), test, font=font)
        if bb[2] - bb[0] > max_w and line:
            lines.append(" ".join(line))
            line = [w]
        else:
            line.append(w)
    if line:
        lines.append(" ".join(line))
    return lines


# ── Keyword marker rendering ───────────────────────────────────────────────────

def _parse_marked(text: str) -> list[tuple[str, bool]]:
    """Split text into (segment, is_keyword) pairs using [[...]] markers."""
    parts = re.split(r'(\[\[[^\]]+\]\])', text)
    result = []
    for p in parts:
        m = re.match(r'\[\[([^\]]+)\]\]', p)
        if m:
            result.append((m.group(1), True))
        elif p:
            result.append((p, False))
    return result


def _draw_premium_text(draw, xy, text, font, fill, shadow_layers=5, shadow_alpha=150, outline=2, glow_color=None):
    """Draws premium typography with depth shadows, outlines, and optional outer glow (extracted from vedone)."""
    x, y = xy
    
    # 1. Multi-layered Depth Shadow
    for offset in range(1, shadow_layers + 1):
        alpha = int(shadow_alpha / offset)
        draw.text((x + offset + 1, y + offset + 1), text, font=font, fill=(0, 0, 0, alpha))
        
    # 2. Outer Glow (if requested)
    if glow_color:
        for r in range(1, 4):
            draw.text((x-r, y), text, font=font, fill=glow_color)
            draw.text((x+r, y), text, font=font, fill=glow_color)
            draw.text((x, y-r), text, font=font, fill=glow_color)
            draw.text((x, y+r), text, font=font, fill=glow_color)
            
    # 3. Robust Outline (Black)
    if outline > 0:
        for ox in range(-outline, outline + 1):
            for oy in range(-outline, outline + 1):
                if ox != 0 or oy != 0:
                    draw.text((x + ox, y + oy), text, font=font, fill=(0, 0, 0, 200))
                    
    # 4. Main Text
    draw.text((x, y), text, font=font, fill=fill)

def _draw_marked_text(draw: ImageDraw.ImageDraw, xy: tuple, text: str,
                       font: ImageFont.FreeTypeFont, base_color: tuple,
                       accent_color: tuple) -> int:
    """
    Draw text that may contain [[keyword]] markers natively using premium typography.
    Returns the x-position after the last character drawn (for inline use).
    """
    x, y = xy
    for segment, is_kw in _parse_marked(text):
        color = accent_color if is_kw else base_color
        bb = draw.textbbox((x, y), segment, font=font)
        glow = accent_color if is_kw else None
        
        _draw_premium_text(draw, (x, y), segment, font, fill=color, outline=2, glow_color=glow)
        
        x = bb[2]
    return x


# ── Real Python syntax highlighting ───────────────────────────────────────────

def _tokenize_code(code: str) -> list[tuple[str, tuple]]:
    """
    Returns list of (text, colour) pairs for each line of code.
    Falls back to raw lines if tokenize fails.
    """
    lines = code.split('\n')
    # Build per-line colour segments: list of list of (token_str, colour)
    line_tokens: list[list[tuple[str, tuple]]] = [[] for _ in lines]
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
        for tok_type, tok_str, (srow, scol), (erow, ecol), _ in tokens:
            if tok_type == tokenize.COMMENT:
                colour = TOK_COMMENT
            elif tok_type == tokenize.STRING:
                colour = TOK_STRING
            elif tok_type == tokenize.NUMBER:
                colour = TOK_NUMBER
            elif tok_type == tokenize.NAME:
                if tok_str in _KW_SET:
                    colour = TOK_KEYWORD
                else:
                    colour = TOK_FUNC
            elif tok_type in (tokenize.NEWLINE, tokenize.NL, tokenize.INDENT,
                               tokenize.DEDENT, tokenize.ENCODING, tokenize.ENDMARKER):
                continue # These tokens don't need to be rendered directly
            else:
                colour = TEXT_WHITE
            line_idx = srow - 1
            if 0 <= line_idx < len(line_tokens):
                line_tokens[line_idx].append((tok_str, colour))
    except tokenize.TokenError:
        pass  # Partial parse is fine — fall through with collected tokens

    # If a line has no tokens, fall back to rendering the raw line in white
    result = []
    for i, raw_line in enumerate(lines):
        if line_tokens[i]:
            result.append(line_tokens[i])
        else:
            result.append([(raw_line, TEXT_WHITE)])
    return result


def _render_chapter_frame(chapter: dict, progress: float = 0.5, duration: float = 60.0) -> np.ndarray:
    """
    Render a single static frame for the chapter.
    progress ∈ [0,1] controls which step bullet is highlighted.
    """
    # 1. Background with chapter-specific accent tint
    bg_accent_name = chapter.get("bg_accent", "cyan").lower()
    accents = {
        "cyan": ACCENT_CYAN,
        "orange": ACCENT_ORANGE,
        "green": ACCENT_GREEN,
        "pink": ACCENT_PINK,
        "yellow": ACCENT_YELLOW,
        "purple": (180, 90, 255),
    }
    pill_color = accents.get(bg_accent_name, ACCENT_CYAN)
    
    # 2. Render Premium Base
    img = _gradient_bg(accent_rgb=pill_color)
    img = _draw_vignette(img)
    draw = ImageDraw.Draw(img)

    _draw_approach_flashcard(draw, chapter, pill_color)

    font_mega   = _get_font(120, bold=True)
    font_title  = _get_font(52, bold=True)
    font_sub    = _get_font(32)
    
    # Calculate robust font size for code to prevent line truncation
    code        = chapter.get("code_snippet", "")
    max_line_len = max([len(line.strip()) for line in code.split('\n')] + [1])
    code_size = 26
    if max_line_len > 45: code_size = 22
    if max_line_len > 60: code_size = 18
    if max_line_len > 80: code_size = 14
    
    font_code   = _get_font(code_size)
    font_bullet = _get_font(30)
    font_small  = _get_font(22)

    ch_name     = chapter.get("chapter", "").upper()
    on_screen   = chapter.get("on_screen_text", "")
    code        = chapter.get("code_snippet", "")
    steps       = chapter.get("highlight_steps", [])
    flashcard   = chapter.get("flashcard_concept", "")
    seg_id      = chapter.get("segment_id", 0)
    motion      = chapter.get("motion", {})
    is_problem  = chapter.get("is_problem_statement", False)
    is_brute    = chapter.get("is_bruteforce", False)
    is_complex  = chapter.get("is_complexity_analysis", False)
    is_dry      = chapter.get("is_dry_run", False)

    # ── Phase 1: Flashcard Transition (Fixed 2.5 Seconds) ──────────────────────────────
    if (progress * duration) <= 2.5 and ch_name:
        title_text = on_screen or ch_name
        lines = _wrap_text(title_text, font_mega, W - 200, draw)
        
        # Center block vertically
        y_offset = H // 2 - (len(lines) * 140) // 2
        for line in lines:
            bb = draw.textbbox((0, 0), line, font=font_mega)
            x_pos = (W - (bb[2] - bb[0])) // 2
            _draw_premium_text(draw, (x_pos, y_offset), line, font_mega, TEXT_WHITE, shadow_layers=8, outline=4, glow_color=pill_color)
            y_offset += 140
            
        return np.array(img)

    # ── Phase 2: Main Content Layout ──────────────────────────────────────────
    # ── Main title ────────────────────────────────────────────────────────────
    title_lines = _wrap_text(on_screen, font_title, W - 2*PAD, draw)
    y = 60
    for line in title_lines[:2]:
        _draw_premium_text(draw, (PAD, y), line, font_title, TEXT_WHITE, shadow_layers=3)
        y += 62

    # ── Divider ───────────────────────────────────────────────────────────────
    draw.line([(PAD, y + 10), (W - PAD, y + 10)], fill=pill_color, width=2)
    y += 30

    # ── Left panel: code OR flashcard OR problem statement ───────────────────
    left_w = int(W * 0.55) - PAD
    
    if is_problem and on_screen:
        box_x1, box_y1 = PAD, y
        box_x2, box_y2 = W - PAD, H - PAD - 40
        
        # Check for problem screenshot image
        img_path = chapter.get("content_image", "")
        if img_path and os.path.exists(img_path):
            try:
                ov_img = Image.open(img_path).convert("RGBA")
                # Resize to fit the box while maintaining aspect ratio
                max_w = (box_x2 - box_x1) - 40
                max_h = (box_y2 - box_y1) - 40
                ov_img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
                
                # Center it inside the box
                ix = box_x1 + (box_x2 - box_x1 - ov_img.width) // 2
                iy = box_y1 + (box_y2 - box_y1 - ov_img.height) // 2
                
                # Draw a premium border/shadow for the image
                border = 4
                shadow = 10
                draw.rectangle([ix-shadow, iy-shadow, ix+ov_img.width+shadow, iy+ov_img.height+shadow], fill=(0,0,0,100))
                draw.rectangle([ix-border, iy-border, ix+ov_img.width+border, iy+ov_img.height+border], outline=pill_color, width=border)
                
                img.paste(ov_img, (ix, iy), ov_img)
            except Exception as e:
                safe_print(f"  [renderer] Warning: Failed to render content image: {e}")
                # Fallback to text box (existing logic)
                draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=16, fill=(30, 40, 60, 220))
                draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=16, outline=pill_color, width=2)
        else:
            # Transparent overlay box (Original Text Fallback)
            draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=16, fill=(30, 40, 60, 220))
            draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=16, outline=pill_color, width=2)
        
        # Wrapped, readable text
        font_reading = _get_font(38)
        reading_lines = _wrap_text(on_screen, font_reading, W - (PAD * 3), draw)
        
        ty = box_y1 + 40
        for rline in reading_lines:
            if ty > box_y2 - 50:
                break
            # Highlight keyword variables in accent colour natively
            _draw_marked_text(draw, (box_x1 + 40, ty), rline, font_reading, TEXT_WHITE, ACCENT_GREEN)
            ty += 45
            
    elif is_complex:
        # Massive 2-column Typographic Panel for Complexity
        panel_x1, panel_y1 = PAD, y
        panel_x2, panel_y2 = PAD + left_w, H - PAD
        draw.rounded_rectangle([panel_x1-5, panel_y1-5, panel_x2+5, panel_y2+5], radius=16, fill=(20, 25, 35))
        draw.rounded_rectangle([panel_x1-5, panel_y1-5, panel_x2+5, panel_y2+5], radius=16, outline=pill_color, width=3)
        
        # Time Complexity (Top Half)
        cy = panel_y1 + 50
        _draw_premium_text(draw, (panel_x1 + 40, cy), "TIME COMPLEXITY", font_sub, TEXT_MUTED, shadow_layers=2)
        cy += 60
        time_val = chapter.get("time_complexity_str", "O(N)" if not is_brute else "O(N²)")
        _draw_premium_text(draw, (panel_x1 + 40, cy), time_val, font_mega, ACCENT_YELLOW, shadow_layers=6, glow_color=ACCENT_ORANGE)
        
        # Space Complexity (Bottom Half)
        cy += 200
        _draw_premium_text(draw, (panel_x1 + 40, cy), "SPACE COMPLEXITY", font_sub, TEXT_MUTED, shadow_layers=2)
        cy += 60
        space_val = chapter.get("space_complexity_str", "O(N)" if not is_brute else "O(1)")
        _draw_premium_text(draw, (panel_x1 + 40, cy), space_val, font_mega, ACCENT_CYAN, shadow_layers=6, glow_color=ACCENT_CYAN)

    elif code.strip():
        # Code panel
        panel_x1, panel_y1 = PAD, y
        panel_x2, panel_y2 = PAD + left_w, H - PAD
        
        # Theme: Red for Bruteforce, Normal for Optimal
        bg_color = (60, 20, 20) if is_brute else (30, 40, 60)
        outline_color = (255, 80, 80) if is_brute else (60, 70, 90)
        
        draw.rounded_rectangle([panel_x1-5, panel_y1-5, panel_x2+5, panel_y2+5], radius=10, fill=bg_color)
        draw.rounded_rectangle([panel_x1-5, panel_y1-5, panel_x2+5, panel_y2+5], radius=10, outline=outline_color, width=2)

        # Tab header
        header_color = (80, 20, 20) if is_brute else (40, 50, 70)
        draw.rounded_rectangle([panel_x1-5, panel_y1-5, panel_x2+5, panel_y1+35], radius=10, fill=header_color)
        
        tab_text = "bruteforce.py" if is_brute else "solution.py"
        draw.text((panel_x1+15, panel_y1+5), tab_text, font=font_small, fill=TEXT_MUTED if not is_brute else (255, 180, 180))

        # Windows
        radius = 5
        for idx, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            cx = panel_x2 - 60 + idx * 18
            cy = panel_y1 + 15
            draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=col)

        # Split and tokenize code
        token_lines = _tokenize_code(code)

        # Determine active line via char-weight math
        active_line = 0
        if token_lines:
            total_chars = sum(len("".join(s for s, _ in line)) for line in token_lines)
            if total_chars > 0:
                target_chars = progress * total_chars
                accumulated = 0
                for i, line in enumerate(token_lines):
                    accumulated += len("".join(s for s, _ in line))
                    if accumulated >= target_chars:
                        active_line = i
                        break
                else:
                    active_line = len(token_lines) - 1

        cy = panel_y1 + 50
        for i, tok_segs in enumerate(token_lines):
            if cy + 30 > panel_y2 - 10:
                break
            if i == active_line:
                # Active line highlight with glow
                glow_pad = 5
                draw.rounded_rectangle(
                    [panel_x1, cy-glow_pad, panel_x2, cy+28+glow_pad],
                    radius=5, fill=(60, 50, 20)
                )
                # Outer glow line
                draw.line([(panel_x1, cy-glow_pad), (panel_x1, cy+28+glow_pad)], 
                          fill=pill_color, width=4)

            # Draw each token with its colour
            tx = panel_x1 + 10
            for tok_str, colour in tok_segs:
                disp_colour = ACCENT_YELLOW if i == active_line else colour
                bb = draw.textbbox((tx, cy), tok_str, font=font_code)
                draw.text((tx, cy), tok_str, font=font_code, fill=disp_colour)
                tx = bb[2]
                if tx > panel_x2 - 10:
                    break
            cy += code_size + 4  # Scale line height with dynamic font size

    elif flashcard.strip():
        # Flashcard panel
        fx1, fy1 = PAD, y
        fx2, fy2 = PAD + left_w, y + 250
        draw.rounded_rectangle([fx1, fy1, fx2, fy2], radius=16, fill=(24, 28, 40))
        draw.rounded_rectangle([fx1, fy1, fx2, fy2], radius=16, outline=pill_color, width=3)
        
        # Premium Flashcard Header
        _draw_premium_text(draw, (fx1 + 20, fy1 + 15), "KEY INSIGHT", _get_font(24, bold=True), ACCENT_ORANGE, shadow_layers=1)
        draw.line([(fx1 + 20, fy1 + 50), (fx2 - 20, fy1 + 50)], fill=(80, 80, 100), width=2)
        
        # Render flashcard text with [[keyword]] highlighting
        fc_lines = _wrap_text(flashcard, font_sub, left_w - 40, draw)
        fcy = fy1 + 75
        for line in fc_lines[:6]:
            _draw_marked_text(draw, (fx1 + 20, fcy), line, font_sub, TEXT_WHITE, ACCENT_PINK)
            fcy += 40

    # ── Right panel: step-by-step bullets OR Data Structure Visualizer ────────
    right_x = PAD + left_w + 60
    right_w = W - right_x - PAD
    
    # Node #4: Dry Run Animation Engine (Simplified SVG-like logic)
    if "dry run" in ch_name.lower() or chapter.get("animation_type") == "push_pop":
        # Render a "Stack" visualizer on the right instead of just bullets
        stack_y = y + 50
        draw.text((right_x, stack_y - 40), "MEMORY STACK", font=font_small, fill=pill_color)
        
        # Draw stack container
        stack_w = 200
        draw.line([(right_x, stack_y), (right_x, stack_y + 400)], fill=TEXT_MUTED, width=2)
        draw.line([(right_x + stack_w, stack_y), (right_x + stack_w, stack_y + 400)], fill=TEXT_MUTED, width=2)
        draw.line([(right_x, stack_y + 400), (right_x + stack_w, stack_y + 400)], fill=TEXT_MUTED, width=2)
        
        # Draw some "pushed" items based on progress
        stack_items = ["(", "{", "["] # Mock for valid-parentheses
        item_h = 60
        for i, item in enumerate(stack_items[:int(progress * 4)]):
            item_y = stack_y + 400 - (i+1)*item_h - 5
            draw.rounded_rectangle([right_x + 10, item_y, right_x + stack_w - 10, item_y + item_h - 5],
                                    radius=8, fill=(40, 40, 60))
            draw.text((right_x + stack_w//2 - 10, item_y + 10), item, font=font_bullet, fill=TEXT_WHITE)

    # ── Render Bullets (Overlayed or below) ───────────────────────────────────
    # Calculate weighted active step based on character length
    active_step = 0
    if steps:
        total_step_chars = sum(len(step) for step in steps)
        if total_step_chars > 0:
            target_step_chars = progress * total_step_chars
            accumulated_steps = 0
            for i, step in enumerate(steps):
                accumulated_steps += len(step)
                if accumulated_steps >= target_step_chars:
                    active_step = i
                    break
            else:
                active_step = len(steps) - 1
    
    bullet_start_y = y + 50 if "dry run" not in ch_name.lower() else y + 500
    step_y = bullet_start_y

    for i, step in enumerate(steps):
        is_active = (i == active_step)
        step_color = TEXT_WHITE if is_active else TEXT_MUTED

        # Bullet indicator
        if is_active:
            draw.ellipse([right_x, step_y + 8, right_x + 14, step_y + 22],
                          fill=pill_color)
        else:
            draw.ellipse([right_x, step_y + 8, right_x + 14, step_y + 22],
                          outline=TEXT_MUTED, width=1)

        # Render step text with [[keyword]] markers highlighted
        bullet_lines = _wrap_text(step, font_bullet, right_w - 30, draw)
        for j, bline in enumerate(bullet_lines[:2]):
            _draw_marked_text(
                draw, (right_x + 24, step_y + j * 34),
                bline, font_bullet, step_color, pill_color
            )
        step_y += 80 + (20 if is_active else 0)

    # ── Bottom progress bar ───────────────────────────────────────────────────
    bar_y = H - 14
    draw.rectangle([0, bar_y, W, H], fill=(20, 20, 30))
    draw.rectangle([0, bar_y, int(W * progress), H], fill=pill_color)

    # ── Apply cinematic motion (Zoom) ─────────────────────────────────────────
    zoom_target = motion.get("zoom", 1.0)
    if zoom_target != 1.0:
        # Dynamic zoom over progress
        current_zoom = 1.0 + (zoom_target - 1.0) * progress
        new_w, new_h = int(W * current_zoom), int(H * current_zoom)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        # Center crop
        left = (new_w - W) // 2
        top = (new_h - H) // 2
        img = img.crop((left, top, left + W, top + H))

    return np.array(img)


def _draw_approach_flashcard(draw: ImageDraw.Draw, chapter: dict, accent_color: tuple):
    """
    Renders a premium flashcard in the top-right corner indicating the approach type.
    Requested: Brute Force Approach: [Name] or Optimal Approach: [Name].
    """
    is_brute   = chapter.get("is_bruteforce", False)
    is_optimal = chapter.get("is_optimal_code", False)
    if not (is_brute or is_optimal):
        return

    type_label = "BRUTE FORCE APPROACH" if is_brute else "OPTIMAL APPROACH"
    # Try to find a named algorithm in tags or chapter name
    name = ""
    tags = chapter.get("tags", [])
    if tags: 
        name = tags[0].replace("-", " ").title()
    elif "dry run" in chapter.get("chapter", "").lower():
        name = "Visualization"
    
    # Overlay box
    card_w, card_h = 450, 100
    card_x, card_y = W - card_w - PAD, PAD
    
    # Glow / Shadow
    for r in range(1, 15):
        alpha = int(60 * (1 - r/15))
        draw.rounded_rectangle([card_x-r, card_y-r, card_x+card_w+r, card_y+card_h+r], 
                                radius=12, fill=(0, 0, 0, alpha))
    
    # Main Card
    draw.rounded_rectangle([card_x, card_y, card_x+card_w, card_y+card_h], 
                            radius=10, fill=BG_CARD, outline=accent_color, width=3)
    
    font_small = _get_font(20, bold=True)
    font_large = _get_font(32, bold=True)
    
    # Text
    draw.text((card_x + 25, card_y + 15), type_label, font=font_small, fill=accent_color)
    draw.text((card_x + 25, card_y + 40), name, font=font_large, fill=TEXT_WHITE)


# ──────────────────────────────────────────────────────────────────────────────
# Cinematic Title Card & Approach Banner
# ──────────────────────────────────────────────────────────────────────────────

def _render_title_card_frame(chapter: dict, t: float = 0.0) -> np.ndarray:
    """
    Render a full-screen 2.5s cinematic title card for the chapter.
    Uses a bold color that varies by chapter type (red=brute, green=optimal, etc.)
    `t` ∈ [0, 2.5] controls the fade-in/out animation.
    """
    is_brute    = chapter.get("is_bruteforce", False)
    is_optimal  = chapter.get("is_optimal_code", False)
    is_dry      = chapter.get("is_dry_run", False)
    is_analysis = chapter.get("is_complexity_analysis", False)

    # Color palette based on chapter type
    if is_brute:
        accent = (220, 60, 60)
        label  = "BRUTE FORCE"
    elif is_optimal:
        accent = (60, 220, 110)
        label  = "OPTIMAL APPROACH"
    elif is_dry:
        accent = (255, 210, 50)
        label  = "DRY RUN"
    elif is_analysis:
        accent = (170, 100, 255)
        label  = "COMPLEXITY ANALYSIS"
    else:
        accent = (0, 210, 255)
        label  = "SECTION"

    ch_name = chapter.get("chapter", label)
    seg_id  = chapter.get("segment_id", 0)

    # Fade-in from 0→1 in first 0.5s, stay, fade-out in last 0.5s
    alpha = 1.0
    if t < 0.5:
        alpha = t / 0.5
    elif t > 2.0:
        alpha = (2.5 - t) / 0.5
    alpha = max(0.0, min(1.0, alpha))

    # Base background (Default Gradient)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    # 1. Attempt to load HF Background
    hf_bg_path = f"video_temp/hf_bg/seg_{seg_id}.png"
    if os.path.exists(hf_bg_path):
        try:
            hf_img = Image.open(hf_bg_path).convert("RGBA").resize((W, H))
            # Apply subtle blur and darken
            hf_img = hf_img.filter(ImageFilter.GaussianBlur(10))
            overlay = Image.new("RGBA", (W, H), (10, 10, 20, 160)) # Deep tint
            hf_img.paste(overlay, (0, 0), overlay)
            img = hf_img
            draw = ImageDraw.Draw(img)
        except Exception:
            pass

    if not os.path.exists(hf_bg_path):
        # Gradient sweep (Fallback)
        for y in range(H):
            t_frac = y / H
            r = int(BG_DARK[0] * (1 - t_frac) + (accent[0] * 0.15) * t_frac)
            g = int(BG_DARK[1] * (1 - t_frac) + (accent[1] * 0.15) * t_frac)
            b = int(BG_DARK[2] * (1 - t_frac) + (accent[2] * 0.15) * t_frac)
            draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Divider lines
    for offset in [-3, 0, 3]:
        draw.line([(PAD, H // 2 - 80 + offset), (W - PAD, H // 2 - 80 + offset)],
                  fill=accent, width=2 if offset == 0 else 1)
        draw.line([(PAD, H // 2 + 80 + offset), (W - PAD, H // 2 + 80 + offset)],
                  fill=accent, width=2 if offset == 0 else 1)

    # Label text (small)
    font_label = _get_font(36, bold=True)
    font_big   = _get_font(90, bold=True)

    lw = draw.textbbox((0, 0), label, font=font_label)[2]
    draw.text(((W - lw) // 2, H // 2 - 65), label, font=font_label, fill=accent)

    # Main chapter name
    cw = draw.textbbox((0, 0), ch_name.upper(), font=font_big)[2]
    _draw_premium_text(
        draw, ((W - cw) // 2, H // 2 - 15),
        ch_name.upper(), font_big, TEXT_WHITE,
        shadow_layers=8, outline=3, glow_color=accent
    )

    # Apply fade alpha
    if alpha < 1.0:
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, int((1 - alpha) * 255)))
        img.paste(overlay, (0, 0), overlay)

    return np.array(img.convert("RGB"))


def _apply_ken_burns(frame_array: np.ndarray, t: float, duration: float) -> np.ndarray:
    """
    Applies a Ken Burns effect: a subtle slow progressive zoom-in during the chapter.
    Scale goes from 1.0 → 1.06 over the chapter duration.
    """
    progress = min(t / max(duration, 1.0), 1.0)
    zoom = 1.0 + 0.06 * progress   # 0% → 6% zoom over chapter

    img = Image.fromarray(frame_array)
    new_w = int(W * zoom)
    new_h = int(H * zoom)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    # Center-crop back to original size
    left = (new_w - W) // 2
    top  = (new_h - H) // 2
    img  = img.crop((left, top, left + W, top + H))
    return np.array(img)


def _make_chapter_video(chapter: dict, video_dir: str = VIDEO_DIR) -> dict:
    """
    Render a single chapter to .mp4 using its audio file.
    If animation_path exists, overlays Manim clip on top.
    """
    seg_id       = chapter["segment_id"]
    audio_path   = chapter.get("audio_path")
    anim_path    = chapter.get("animation_path")
    target_dur   = chapter.get("duration_sec", 60)
    out_path     = os.path.join(video_dir, f"ch{seg_id:02d}.mp4")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
        safe_print(f"  [renderer] Ch{seg_id}: skipping rendering (file exists)")
        return {**chapter, "video_path": out_path}

    safe_print(f"  [renderer] Ch{seg_id}: rendering '{chapter['chapter']}'...")

    # ── Attempt to generate HF Title Background ────────────────────────────
    hf_bg_dir = "video_temp/hf_bg"
    os.makedirs(hf_bg_dir, exist_ok=True)
    hf_path = os.path.join(hf_bg_dir, f"seg_{seg_id}.png")
    if not os.path.exists(hf_path):
        prompt = f"Cinematic abstract coding background, {chapter['chapter']}, coding motif, dark aesthetic, neon {chapter.get('bg_accent','cyan')} accents, 4k"
        generate_huggingface_image(prompt, hf_path)

    for attempt in range(2):
        try:
            # Cleanup previous attempt
            if os.path.exists(out_path):
                try: os.remove(out_path)
                except: pass

            # ── Determine duration ─────────────────────────────────────────────
            if audio_path and os.path.exists(audio_path):
                audio_clip = mp.AudioFileClip(audio_path)
                duration = audio_clip.duration
            else:
                audio_clip = None
                duration = float(target_dur)

            total_frames = int(duration * FPS)
    
            # ── Build video frames ─────────────────────────────────────────────────
            if anim_path and os.path.exists(anim_path):
                # Use Manim clip as base video, resize to 1920x1080
                safe_print(f"  [renderer] Ch{seg_id}: using Manim animation")
                manim_clip = mp.VideoFileClip(anim_path).resize((W, H))
                
                # Dynamically speed up or slow down Manim clip to EXACTLY match audio
                # Built-in Manim animations usually hit keyframes, so stretching maintains sync to audio
                manim_clip = manim_clip.fx(mp.vfx.speedx, final_duration=duration)
                video_clip = manim_clip.subclip(0, duration)
            else:
                # ── Title Card (first 2.5s) + Content (remainder) + Ken Burns zoom ───────
                TITLE_CARD_SECS = 2.5
    
                def make_frame(t):
                    try:
                        CROSS_FADE_SECS = 0.5
                        if t < TITLE_CARD_SECS - CROSS_FADE_SECS:
                            return _render_title_card_frame(chapter, t=t)
                        
                        # Handle cross-fade between title card and content
                        content_t   = (t - TITLE_CARD_SECS)
                        content_dur = max(duration - TITLE_CARD_SECS, 1.0)
                        progress    = min(max(content_t, 0.0) / content_dur, 1.0)
                        
                        rendered_content_frame = _render_chapter_frame(chapter, progress, duration=content_dur)
                        
                        if t < TITLE_CARD_SECS:
                            # Cross-fade region
                            title_frame = _render_title_card_frame(chapter, t=t)
                            fade_progress = (t - (TITLE_CARD_SECS - CROSS_FADE_SECS)) / CROSS_FADE_SECS
                            return (title_frame * (1 - fade_progress) + rendered_content_frame * fade_progress).astype(np.uint8)

                        # Memory management: periodic GC
                        if int(t * FPS) % 30 == 0: 
                            gc.collect()
                        
                        return _apply_ken_burns(rendered_content_frame, content_t, content_dur)
                    except Exception as e:
                        # Fallback to avoid crashing the entire render pipe
                        return _render_title_card_frame(chapter, t=0)
    
                video_clip = mp.VideoClip(make_frame, duration=duration)
                video_clip = video_clip.set_fps(FPS)
    
            # ── Attach audio ───────────────────────────────────────────────────────
            if audio_clip:
                video_clip = video_clip.set_audio(audio_clip)
    
            # ── Write chapter video ────────────────────────────────────────────────
            temp_audio = f"{out_path}.temp_audio.m4a"
            video_clip.write_videofile(
                out_path,
                fps=FPS,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=temp_audio,
                threads=4,
                preset="fast",
                verbose=False,
                logger=None,
            )
            
            # Free Windows File Handles
            # Free Windows File Handles
            if audio_clip:
                audio_clip.close()
            video_clip.close()
    
            if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
                size_mb = os.path.getsize(out_path) / 1024 / 1024
                # Use standard '->' instead of unicode '→' to avoid Windows console errors
                safe_print(f"  [renderer] Ch{seg_id}: [OK] {size_mb:.1f}MB -> {out_path} (Attempt {attempt+1})")
                if _tracker:
                    _tracker.chapter_done(seg_id, "video")
                return {**chapter, "video_path": out_path}
            else:
                raise Exception("Produced empty or 48-byte MP4")

        except Exception as e:
            if attempt == 0:
                safe_print(f"  [renderer] Ch{seg_id}: Attempt 1 FAILED ({e}). Retrying...")
                import time
                time.sleep(2) # Cooldown for Windows file handles
                continue
            
            import traceback
            err_log = os.path.join(VIDEO_DIR, "renderer_errors.txt")
            with open(err_log, "a", encoding="utf-8") as f:
                f.write(f"--- Chapter {seg_id} Error ---\n")
                f.write(traceback.format_exc())
                f.write("\n")
            safe_print(f"  [renderer] Ch{seg_id}: ERROR — caught and logged to {err_log}")
            chapter["video_path"] = None
            chapter["error"] = res.get("error", "Unknown Render Error")
            return chapter

    # We use max_workers=1 or 2 to avoid RAM overload with Manim/MoviePy on Windows
    updated_chapters = []
    with ThreadPoolExecutor(max_workers=1) as pool:
        futures = {pool.submit(run_rendering, ch): ch for ch in chapters}
        for fut in as_completed(futures):
            try:
                updated_chapters.append(fut.result())
            except Exception as e:
                ch = futures[fut]
                safe_print(f"  [renderer] Ch{ch['segment_id']}: fatal worker crash — {e}")
                updated_chapters.append({**ch, "video_path": None, "error": str(e)})

    # Sort back by segment_id
    updated_chapters.sort(key=lambda c: c["segment_id"])
    success = sum(1 for c in updated_chapters if c.get("video_path"))
    errors = [c.get("error") for c in updated_chapters if c.get("error")]
    
    safe_print(f"[renderer_node] [OK] {success}/{len(chapters)} chapters rendered")

    if success == 0:
        return {"chapters": updated_chapters, "error": "renderer_node: all renders failed"}
        
    if errors:
        return {"chapters": updated_chapters, "errors": state.get("errors", []) + errors}

    return {"chapters": updated_chapters, "error": ""}
