"""
Dialogue Renderer — renders discussion-mode chapters into 1920x1080 .mp4 files.
Layout:
  Left 50%: Mentor vs Student Dialogue
  Right 50%: Whiteboard (Code/Animations)
Includes Vedone Typography and 2.5s Flashcard Transitions.
"""
import os, math, re, io, tokenize, keyword
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import moviepy.editor as mp
from concurrent.futures import ThreadPoolExecutor, as_completed

VIDEO_DIR = "video_temp/video"
W, H = 1920, 1080
FPS  = 24
PAD  = 80

# Colors
BG          = (12, 12, 20)
MENTOR_BG   = (18, 25, 40)
STUDENT_BG  = (20, 18, 35)
BOARD_BG    = (22, 28, 22)
ACCENT_CYAN = (0, 212, 255)
ACCENT_ORANGE=(255, 140, 0)
ACCENT_GREEN= (78, 230, 100)
ACCENT_YELLOW=(255, 220, 50)
TEXT_WHITE  = (240, 240, 245)
TEXT_MUTED  = (140, 140, 160)

# Tokenizer colors
TOK_COMMENT = (110, 110, 130)
TOK_STRING  = (255, 165, 80)
TOK_NUMBER  = (200, 120, 255)
TOK_KEYWORD = (102, 153, 255)
TOK_FUNC    = (78, 230, 100)
_KW_SET     = set(keyword.kwlist)


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    paths = ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/courbd.ttf", "C:/Windows/Fonts/consola.ttf"] if bold else \
            ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/cour.ttf"]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words, lines, line = text.split(), [], []
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

def _parse_marked(text: str) -> list[tuple[str, bool]]:
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
    x, y = xy
    for offset in range(1, shadow_layers + 1):
        alpha = int(shadow_alpha / offset)
        draw.text((x + offset + 1, y + offset + 1), text, font=font, fill=(0, 0, 0, alpha))
    if glow_color:
        for r in range(1, 4):
            draw.text((x-r, y), text, font=font, fill=glow_color)
            draw.text((x+r, y), text, font=font, fill=glow_color)
            draw.text((x, y-r), text, font=font, fill=glow_color)
            draw.text((x, y+r), text, font=font, fill=glow_color)
    if outline > 0:
        for ox in range(-outline, outline + 1):
            for oy in range(-outline, outline + 1):
                if ox != 0 or oy != 0:
                    draw.text((x + ox, y + oy), text, font=font, fill=(0, 0, 0, 200))
    draw.text((x, y), text, font=font, fill=fill)

def _draw_marked_text(draw, xy, text, font, base_color, accent_color):
    x, y = xy
    for segment, is_kw in _parse_marked(text):
        color = accent_color if is_kw else base_color
        glow = accent_color if is_kw else None
        bb = draw.textbbox((x, y), segment, font=font)
        _draw_premium_text(draw, (x, y), segment, font, fill=color, outline=2, glow_color=glow)
        x = bb[2]
    return x

def _tokenize_code(code: str) -> list[list[tuple[str, tuple]]]:
    lines = code.split('\n')
    line_toks: list[list[tuple[str, tuple]]] = [[] for _ in lines]
    try:
        for tok_type, tok_str, (srow, _), _, _ in tokenize.generate_tokens(io.StringIO(code).readline):
            if tok_type == tokenize.COMMENT: color = TOK_COMMENT
            elif tok_type == tokenize.STRING: color = TOK_STRING
            elif tok_type == tokenize.NUMBER: color = TOK_NUMBER
            elif tok_type == tokenize.NAME:
                color = TOK_KEYWORD if tok_str in _KW_SET else TOK_FUNC
            elif tok_type in (tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING, tokenize.ENDMARKER):
                continue
            else:
                color = TEXT_WHITE
            idx = srow - 1
            if 0 <= idx < len(line_toks):
                line_toks[idx].append((tok_str, color))
    except tokenize.TokenError:
        pass
    result = []
    for i, raw in enumerate(lines):
        result.append(line_toks[i] if line_toks[i] else [(raw, TEXT_WHITE)])
    return result

def _gradient_bg(accent_rgb: tuple = ACCENT_CYAN) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        color = [int(BG[i] * (1-t) + (10, 10, 20)[i] * t) for i in range(3)]
        draw.line([(0, y), (W, y)], fill=tuple(color))
    glow_surface = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_surface)
    center = (W * 0.9, H * 0.9)
    for r in range(1200, 0, -20):
        alpha = int(15 * (1 - r/1200))
        gd.ellipse([center[0]-r, center[1]-r, center[0]+r, center[1]+r], fill=(*accent_rgb, alpha))
    img.paste(glow_surface, (0, 0), glow_surface)
    return img

def _draw_vignette(img: Image.Image):
    draw = ImageDraw.Draw(img, "RGBA")
    for r in range(0, 150):
        alpha = int(120 * (r / 150))
        draw.rectangle([0, 0, W, r], fill=(0, 0, 0, alpha))
        draw.rectangle([0, H-r, W, H], fill=(0, 0, 0, alpha))
    return img


def _render_dialogue_frame(chapter: dict, progress: float = 0.5, duration: float = 120.0) -> np.ndarray:
    pill_color = ACCENT_CYAN
    img = _gradient_bg(accent_rgb=pill_color)
    img = _draw_vignette(img)
    draw = ImageDraw.Draw(img)

    font_mega   = _get_font(120, bold=True)
    font_title  = _get_font(46, bold=True)
    font_text   = _get_font(34)
    font_code   = _get_font(28)

    ch_name     = chapter.get("chapter", "").upper()
    mentor_line = chapter.get("mentor_line", "")
    student_line= chapter.get("student_line", "")
    mentor_resp = chapter.get("mentor_response", "")
    code        = chapter.get("code_snippet", "")
    on_screen   = chapter.get("on_screen_text", "")
    is_problem  = chapter.get("is_problem_statement", False)
    is_brute    = chapter.get("is_bruteforce", False)
    is_complex  = chapter.get("is_complexity_analysis", False)
    is_dry      = chapter.get("is_dry_run", False)
    
    # ── Phase 1: Flashcard Transition (Fixed 2.5 Seconds) ──────────────────────────────
    if (progress * duration) <= 2.5 and ch_name:
        lines = _wrap_text(ch_name, font_mega, W - 200, draw)
        y_offset = H // 2 - (len(lines) * 140) // 2
        for line in lines:
            bb = draw.textbbox((0, 0), line, font=font_mega)
            x_pos = (W - (bb[2] - bb[0])) // 2
            _draw_premium_text(draw, (x_pos, y_offset), line, font_mega, TEXT_WHITE, shadow_layers=8, outline=4, glow_color=pill_color)
            y_offset += 140
        return np.array(img)

    # ── Phase 2: Split Dialogue Presentation ──────────────────────────────────────────
    left_w = W // 2 - PAD * 1.5
    right_w = W // 2 - PAD * 1.5
    left_x = PAD
    right_x = W // 2 + PAD // 2
    
    # Dialogue Weight Math
    mlen = len(mentor_line)
    slen = len(student_line)
    rlen = len(mentor_resp)
    total_len = mlen + slen + rlen + 1
    
    p1 = mlen / total_len
    p2 = p1 + (slen / total_len)
    
    is_mentor_1 = progress < p1
    is_student  = (progress >= p1) and (progress < p2)
    is_mentor_2 = progress >= p2
    
    # ── Left Pane: Dialogue Boxes ──
    dy = PAD
    # Mentor Box 1
    if mentor_line:
        alpha_m1 = 255 if is_mentor_1 else 120
        c_m1 = TEXT_WHITE if is_mentor_1 else TEXT_MUTED
        draw.rounded_rectangle([left_x, dy, left_x + left_w, dy + 250], radius=16, fill=(*MENTOR_BG, alpha_m1))
        _draw_premium_text(draw, (left_x + 20, dy + 20), "ALEX (MENTOR)", font_title, ACCENT_CYAN if is_mentor_1 else TEXT_MUTED, outline=1)
        mlines = _wrap_text(mentor_line, font_text, left_w - 40, draw)
        ty = dy + 80
        for line in mlines[:4]:
            draw.text((left_x + 20, ty), line, font=font_text, fill=c_m1)
            ty += 40
        dy += 280

    # Student Box
    if student_line:
        alpha_s = 255 if is_student else 120
        c_s = TEXT_WHITE if is_student else TEXT_MUTED
        sb_h = 250
        draw.rounded_rectangle([left_x, dy, left_x + left_w, dy + sb_h], radius=16, fill=(*STUDENT_BG, alpha_s))
        _draw_premium_text(draw, (left_x + 20, dy + 20), "MAYA (STUDENT)", font_title, ACCENT_ORANGE if is_student else TEXT_MUTED, outline=1)
        slines = _wrap_text(student_line, font_text, left_w - 40, draw)
        ty = dy + 80
        for line in slines[:4]:
            draw.text((left_x + 20, ty), line, font=font_text, fill=c_s)
            ty += 40
        dy += sb_h + 30
        
    # Mentor Response Box (if exists)
    if mentor_resp:
        alpha_m2 = 255 if is_mentor_2 else 120
        c_m2 = TEXT_WHITE if is_mentor_2 else TEXT_MUTED
        draw.rounded_rectangle([left_x, dy, left_x + left_w, dy + 250], radius=16, fill=(*MENTOR_BG, alpha_m2))
        _draw_premium_text(draw, (left_x + 20, dy + 20), "ALEX", font_title, ACCENT_CYAN if is_mentor_2 else TEXT_MUTED, outline=1)
        mrlines = _wrap_text(mentor_resp, font_text, left_w - 40, draw)
        ty = dy + 80
        for line in mrlines[:4]:
            draw.text((left_x + 20, ty), line, font=font_text, fill=c_m2)
            ty += 40

    # ── Right Pane: Whiteboard / Code OR Problem ──
    draw.rounded_rectangle([right_x, PAD, W - PAD, H - PAD], radius=16, fill=BOARD_BG)
    _draw_premium_text(draw, (right_x + 24, PAD + 24), "WHITEBOARD", font_title, ACCENT_GREEN, shadow_layers=2)
    
    if is_problem and on_screen:
        # Render a large reading panel for the Problem Statement
        box_x1, box_y1 = right_x + 20, PAD + 90
        box_x2, box_y2 = W - PAD - 20, H - PAD - 40
        
        # Transparent overlay box
        draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=16, fill=(30, 40, 60, 220))
        draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=16, outline=pill_color, width=2)
        
        # Wrapped, readable text
        font_reading = _get_font(38)
        reading_lines = _wrap_text(on_screen, font_reading, right_w - 80, draw)
        
        ty = box_y1 + 40
        for rline in reading_lines:
            if ty > box_y2 - 50:
                break
            # Highlight keyword variables in accent colour natively
            _draw_marked_text(draw, (box_x1 + 40, ty), rline, font_reading, TEXT_WHITE, ACCENT_GREEN)
            ty += 45
            
    elif is_complex:
        # Massive 2-column Typographic Panel for Complexity
        panel_x1, panel_y1 = right_x + 20, PAD + 90
        panel_x2, panel_y2 = W - PAD - 20, H - PAD - 40
        draw.rounded_rectangle([panel_x1-5, panel_y1-5, panel_x2+5, panel_y2+5], radius=16, fill=(20, 25, 35))
        draw.rounded_rectangle([panel_x1-5, panel_y1-5, panel_x2+5, panel_y2+5], radius=16, outline=pill_color, width=3)
        
        # Time Complexity
        cy = panel_y1 + 50
        _draw_premium_text(draw, (panel_x1 + 40, cy), "TIME COMPLEXITY", font_text, TEXT_MUTED, shadow_layers=2)
        cy += 60
        time_val = "O(N)" if not is_brute else "O(N²)"
        _draw_premium_text(draw, (panel_x1 + 40, cy), time_val, font_mega, ACCENT_YELLOW, shadow_layers=6, glow_color=ACCENT_ORANGE)
        
        # Space Complexity
        cy += 200
        _draw_premium_text(draw, (panel_x1 + 40, cy), "SPACE COMPLEXITY", font_text, TEXT_MUTED, shadow_layers=2)
        cy += 60
        space_val = "O(N)" if not is_brute else "O(1)"
        _draw_premium_text(draw, (panel_x1 + 40, cy), space_val, font_mega, ACCENT_CYAN, shadow_layers=6, glow_color=ACCENT_CYAN)
    
    elif code.strip():
        # Theme: Red for Bruteforce, Normal for Optimal
        bg_color = (60, 20, 20) if is_brute else (30, 40, 60)
        outline_color = (255, 80, 80) if is_brute else (60, 70, 90)
        
        panel_x1, panel_y1 = right_x + 20, PAD + 90
        panel_x2, panel_y2 = W - PAD - 20, H - PAD - 40
        
        draw.rounded_rectangle([panel_x1-5, panel_y1-5, panel_x2+5, panel_y2+5], radius=10, fill=bg_color)
        draw.rounded_rectangle([panel_x1-5, panel_y1-5, panel_x2+5, panel_y2+5], radius=10, outline=outline_color, width=2)
        
        # Tab header
        header_color = (80, 20, 20) if is_brute else (40, 50, 70)
        draw.rounded_rectangle([panel_x1-5, panel_y1-5, panel_x2+5, panel_y1+35], radius=10, fill=header_color)
        tab_text = "bruteforce.py" if is_brute else "solution.py"
        draw.text((panel_x1+15, panel_y1+5), tab_text, font=font_code, fill=TEXT_MUTED if not is_brute else (255, 180, 180))

        token_lines = _tokenize_code(code)
        
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
                glow_pad = 5
                draw.rounded_rectangle([panel_x1, cy-glow_pad, panel_x2, cy+28+glow_pad], radius=5, fill=(60, 50, 20))
                draw.line([(panel_x1, cy-glow_pad), (panel_x1, cy+28+glow_pad)], fill=pill_color, width=4)
                
            line_text = "".join(s for s, _ in tok_segs)
            if len(line_text) > 45:
                # Truncate to fit half screen
                col = ACCENT_YELLOW if i == active_line else TEXT_WHITE
                draw.text((panel_x1 + 10, cy), line_text[:45], font=font_code, fill=col)
            else:
                tx = panel_x1 + 10
                for tok_str, colour in tok_segs:
                    disp_col = ACCENT_YELLOW if i == active_line else colour
                    bb2 = draw.textbbox((tx, cy), tok_str, font=font_code)
                    draw.text((tx, cy), tok_str, font=font_code, fill=disp_col)
                    tx = bb2[2]
            cy += 30

    # Bottom progress bar
    bar_y = H - 14
    draw.rectangle([0, bar_y, W, H], fill=(20, 20, 30))
    draw.rectangle([0, bar_y, int(W * progress), H], fill=pill_color)

    return np.array(img)


def _render_dialogue_chapter(chapter: dict) -> dict:
    seg_id    = chapter["segment_id"]
    audio_path= chapter.get("audio_path")
    anim_path = chapter.get("animation_path")
    out_path  = os.path.join(VIDEO_DIR, f"ch{seg_id:02d}.mp4")

    print(f"  [dialogue_renderer] Ch{seg_id}: rendering '{chapter['chapter']}'...")

    try:
        if audio_path and os.path.exists(audio_path):
            audio_clip = mp.AudioFileClip(audio_path)
            duration = audio_clip.duration
        else:
            audio_clip = None
            duration = float(chapter.get("duration_sec", 120))

        if anim_path and os.path.exists(anim_path):
            # If there's a Manim animation, overlay it on the right side of the split screen
            print(f"  [dialogue_renderer] Ch{seg_id}: handling Manim anim...")
            manim_clip = mp.VideoFileClip(anim_path)
            manim_clip = manim_clip.fx(mp.vfx.speedx, final_duration=duration)
            
            def composite_frame(t):
                progress = min(t / max(duration, 1), 1.0)
                base = _render_dialogue_frame(chapter, progress, duration)
                
                # Do not overlay Manim during the Flashcard transition
                if (progress * duration) <= 2.5 and chapter.get("chapter"):
                    return base
                    
                m_frame = manim_clip.get_frame(t)
                
                # Resize manim frame to fit Right pane
                target_w = W // 2 - PAD * 2
                target_h = int(m_frame.shape[0] * (target_w / m_frame.shape[1]))
                m_img = Image.fromarray(m_frame).resize((target_w, target_h), Image.LANCZOS)
                
                base_img = Image.fromarray(base)
                rx = W // 2 + PAD
                ry = PAD + 100
                if m_img.height < (H - PAD*2 - 100):
                    base_img.paste(m_img, (rx, ry))
                else:
                    m_img = m_img.resize((target_w, H - PAD*2 - 100), Image.LANCZOS)
                    base_img.paste(m_img, (rx, ry))
                    
                return np.array(base_img)
            
            video_clip = mp.VideoClip(composite_frame, duration=duration).set_fps(FPS)

        else:
            def make_frame(t):
                progress = min(t / max(duration, 1), 1.0)
                return _render_dialogue_frame(chapter, progress, duration)

            video_clip = mp.VideoClip(make_frame, duration=duration).set_fps(FPS)

        if audio_clip:
            video_clip = video_clip.set_audio(audio_clip)

        temp_audio = f"{out_path}.temp_audio.m4a"
        video_clip.write_videofile(
            out_path, fps=FPS, codec="libx264", audio_codec="aac",
            temp_audiofile=temp_audio, verbose=False, logger=None
        )
        
        # Free Windows File Handles
        if audio_clip:
            audio_clip.close()
        video_clip.close()
        print(f"  [dialogue_renderer] Ch{seg_id}: ✓ Saved to {out_path}")
        return {**chapter, "video_path": out_path}

    except Exception as e:
        print(f"  [dialogue_renderer] Ch{seg_id}: ERROR — {e}")
        return {**chapter, "video_path": None}


def dialogue_renderer_node(state: dict) -> dict:
    chapters = state.get("chapters", [])
    if not chapters: return {"error": "no chapters"}
    os.makedirs(VIDEO_DIR, exist_ok=True)
    updated = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(_render_dialogue_chapter, ch): ch for ch in chapters}
        for fut in as_completed(futures):
            try:
                updated.append(fut.result())
            except Exception as e:
                updated.append({**futures[fut], "video_path": None})
    updated.sort(key=lambda c: c["segment_id"])
    return {"chapters": updated, "error": ""}
