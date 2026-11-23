#!/usr/bin/env python3
"""Render the GEM RUSH Day 1 vs Day 7 video (post-tiktok v2).

Deterministic: no clock, no randomness, no network. Frames are drawn with PIL
from a fixed simulation (one jump, same coordinates on Day 1 and Day 7), then
ffmpeg composites make.fun's OFFICIAL 9:16 referral end card (transparent
webm, fetched in-session from the press pack, sha256-verified) over the last
2.5 s, with the clip blurred/desaturated underneath and the referral code
typed into the card's field once it comes to rest.

Usage:
  python3 render.py --card /path/to/card-9x16-transparent.webm [--out-dir DIR]
Writes $MAKEFUN_OUTPUT_DIR/entry.mp4 when set, else <out-dir>/entry.mp4
(default ./output/entry.mp4). Exit 0 on success.
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from math import cos, pi, sin, sqrt

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 24
DUR = 18.0
N_FRAMES = int(DUR * FPS)  # 432
GROUND_Y = 1560
MINER = 90
MINER_X = 495
REFERRAL_CODE = "j9vvzrcw"
CARD_SHA256 = "286b76c671fa3bf3b1580a7c71675d7b7e502f4fb374b56d30f1104044808cd1"

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

PARTICLE_COLORS = [
    (255, 210, 31), (255, 122, 26), (55, 224, 255), (255, 92, 168),
    (126, 208, 126), (255, 255, 255), (255, 210, 31), (55, 224, 255),
    (255, 92, 168), (126, 208, 126), (255, 122, 26), (255, 255, 255),
    (55, 224, 255), (255, 210, 31), (255, 92, 168), (126, 208, 126),
]
PLATFORMS = [(120, 1180, 300, 36), (700, 980, 320, 36), (180, 780, 280, 36)]


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def centre_text(draw, cx, y, text, fnt, fill):
    box = draw.textbbox((0, 0), text, font=fnt)
    w = box[2] - box[0]
    draw.text((cx - w / 2 - box[0], y), text, font=fnt, fill=fill)


def pill(draw, x, y, w, h, fill, text, fnt, text_fill):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=fill)
    box = draw.textbbox((0, 0), text, font=fnt)
    tw = box[2] - box[0]
    th = box[3] - box[1]
    draw.text((x + (w - tw) / 2 - box[0], y + (h - th) / 2 - box[1]),
              text, font=fnt, fill=text_fill)


def jump_u(t, start):
    """Parabola parameter 0..1 for a jump starting at `start`, lasting 3 s."""
    u = (t - start) / 3.0
    return u if 0.0 <= u <= 1.0 else None


def miner_feet_y(t, start):
    u = jump_u(t, start)
    if u is None:
        return GROUND_Y
    return GROUND_Y - 410 * 4 * u * (1 - u)


def gem_pos(t, start):
    """Gem falls from (540, 250) to (540, 1100) by the jump apex, then gone."""
    if t < start or t > start + 1.5:
        return None
    f = (t - start) / 1.5
    return (540, int(250 + (1100 - 250) * f))


def draw_miner(draw, feet_y, day7):
    x0, y0 = MINER_X, int(feet_y) - MINER
    if day7:
        draw.rectangle([x0, y0, x0 + MINER, y0 + MINER],
                       fill=(255, 122, 26), outline=(200, 90, 0), width=4)
        draw.rectangle([x0 + 4, y0 + 4, x0 + MINER - 4, y0 + 26],
                       fill=(255, 210, 31))
        draw.arc([x0 + 24, y0 + 48, x0 + 66, y0 + 78], 20, 160,
                 fill=(60, 30, 0), width=5)
        draw.ellipse([x0 + 26, y0 + 40, x0 + 36, y0 + 50], fill=(60, 30, 0))
        draw.ellipse([x0 + 54, y0 + 40, x0 + 64, y0 + 50], fill=(60, 30, 0))
    else:
        draw.rectangle([x0, y0, x0 + MINER, y0 + MINER],
                       fill=(154, 154, 154), outline=(110, 110, 110), width=4)
        draw.rectangle([x0 + 26, y0 + 36, x0 + 40, y0 + 54], fill=(40, 40, 40))
        draw.rectangle([x0 + 50, y0 + 36, x0 + 64, y0 + 54], fill=(40, 40, 40))


def draw_gem(base, pos, day7, glow=0.0):
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    cx, cy = pos
    if day7:
        for r, a in ((110, 28), (85, 50), (62, 80)):
            d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)],
                      fill=(55, 224, 255, a))
        d.polygon([(cx, cy - 46), (cx + 46, cy), (cx, cy + 46), (cx - 46, cy)],
                  fill=(55, 224, 255, 255), outline=(0, 179, 214))
    else:
        d.polygon([(cx, cy - 42), (cx + 42, cy), (cx, cy + 42), (cx - 42, cy)],
                  fill=(201, 201, 201, 255), outline=(138, 138, 138))
    base.alpha_composite(overlay)


def draw_particles(base, t, apex_t, gem_xy):
    p = (t - apex_t) / 1.0
    if p < 0 or p > 1:
        return
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for i, col in enumerate(PARTICLE_COLORS):
        ang = i * (360.0 / 16) * pi / 180.0
        dist = 190 * p
        x = gem_xy[0] + int(dist * cos(ang))
        y = gem_xy[1] + int(dist * sin(ang)) - int(60 * p)
        r = max(4, int(14 * (1 - p) + 4))
        a = int(255 * (1 - p))
        d.ellipse([x - r, y - r, x + r, y + r], fill=col + (a,))
    base.alpha_composite(overlay)


def day1_bg(platforms=True):
    img = Image.new("RGB", (W, H), (30, 30, 30))
    d = ImageDraw.Draw(img)
    for gx in range(32, W, 64):
        for gy in range(32, GROUND_Y, 64):
            d.ellipse([gx - 3, gy - 3, gx + 3, gy + 3], fill=(74, 74, 74))
    if platforms:
        for (x, y, w, h) in PLATFORMS:
            d.rectangle([x, y, x + w, y + h], fill=(106, 106, 106))
    d.rectangle([0, GROUND_Y, W, H], fill=(46, 46, 46))
    d.rectangle([0, GROUND_Y, W, GROUND_Y + 6], fill=(85, 85, 85))
    return img


def day7_bg():
    img = Image.new("RGB", (W, H), (47, 111, 214))
    d = ImageDraw.Draw(img)
    for y in range(H):
        f = y / H
        r = int(47 + (142 - 47) * f)
        g = int(111 + (201 - 111) * f)
        b = int(214 + (242 - 214) * f)
        d.line([(0, y), (W, y)], fill=(r, g, b))
    for (x, y, w, h) in PLATFORMS:
        d.rectangle([x, y, x + w, y + h], fill=(47, 143, 91))
        d.rectangle([x, y, x + w, y + 8], fill=(126, 208, 126))
    d.rectangle([0, GROUND_Y, W, H], fill=(53, 160, 63))
    d.rectangle([0, GROUND_Y, W, GROUND_Y + 6], fill=(126, 208, 126))
    for gx in range(60, W, 120):
        d.ellipse([gx, 1700, gx + 34, 1726], fill=(43, 130, 52))
    return img


def draw_cloud(d, x, y, s):
    for (dx, dy, r) in ((0, 0, 52), (48, -18, 62), (104, 0, 54), (52, 14, 58)):
        d.ellipse([x + dx * s, y + dy * s, x + (dx + 2 * r) * s,
                   y + (dy + 2 * r) * s], fill=(255, 255, 255))


def draw_sun(d, frame):
    cx, cy, r = 880, 260, 110
    for k in range(12):
        ang = (k * 30 + frame * 0.1) * pi / 180.0
        x1 = cx + int((r + 18) * cos(ang))
        y1 = cy + int((r + 18) * sin(ang))
        x2 = cx + int((r + 58) * cos(ang))
        y2 = cy + int((r + 58) * sin(ang))
        d.line([(x1, y1), (x2, y2)], fill=(255, 210, 31), width=10)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 210, 31))


def draw_chips(d):
    chips = [("MAGNET", (255, 210, 31)), ("2x GEMS", (255, 92, 168)),
             ("SHIELD", (55, 224, 255))]
    fnt = font(FONT_BOLD, 48)
    x = 70
    for label, col in chips:
        w = 300
        d.rounded_rectangle([x, 1700, x + w, 1800], radius=50,
                            fill=(28, 28, 40), outline=col, width=4)
        box = d.textbbox((0, 0), label, font=fnt)
        tw = box[2] - box[0]
        th = box[3] - box[1]
        d.text((x + (w - tw) / 2 - box[0], 1700 + (100 - th) / 2 - box[1]),
               label, font=fnt, fill=col)
        x += 320


def frame_at(i, bg1, bg7, hold, bg1_hook=None):
    t = i / FPS
    f_big = font(FONT_BOLD, 120)
    f_med = font(FONT_BOLD, 56)
    f_hud = font(FONT_BOLD, 64)

    if t < 3.0:
        img = (bg1_hook if bg1_hook is not None else bg1).copy()
        d = ImageDraw.Draw(img)
        pill(d, 48, 48, 230, 92, (85, 85, 85), "DAY 1", font(FONT_BOLD, 56),
             (255, 255, 255))
        d.text((1032 - d.textbbox((0, 0), "SCORE 0", font=f_hud)[2], 48),
               "SCORE 0", font=f_hud, fill=(255, 255, 255))
        draw_miner(d, GROUND_Y, day7=False)
        gem = gem_pos(t, 3.5)
        if gem is None:
            gem = (540, 250)
        img_rgba = img.convert("RGBA")
        draw_gem(img_rgba, gem, day7=False)
        img = img_rgba.convert("RGB")
        d = ImageDraw.Draw(img)
        centre_text(d, 540, 620, "Same jump.", f_big, (255, 255, 255))
        centre_text(d, 540, 770, "Day 1 vs Day 7.", f_big, (255, 255, 255))
        centre_text(d, 540, 950, "one AI agent, zero humans", f_med,
                    (255, 210, 31))
        return img

    if t < 8.0:
        img = bg1.copy()
        d = ImageDraw.Draw(img)
        pill(d, 48, 48, 230, 92, (85, 85, 85), "DAY 1", font(FONT_BOLD, 56),
             (255, 255, 255))
        d.text((1032 - d.textbbox((0, 0), "SCORE 0", font=f_hud)[2], 48),
               "SCORE 0", font=f_hud, fill=(255, 255, 255))
        draw_miner(d, miner_feet_y(t, 3.5), day7=False)
        gem = gem_pos(t, 3.5)
        img_rgba = img.convert("RGBA")
        if gem is not None:
            draw_gem(img_rgba, gem, day7=False)
        img = img_rgba.convert("RGB")
        return img

    if t < 13.0:
        img = bg7.copy()
        d = ImageDraw.Draw(img)
        draw_sun(d, i)
        for (bx, by, s) in ((80, 420, 1.0), (620, 640, 0.8), (240, 900, 0.7)):
            cx = (bx + int(i * 0.5)) % (W + 400) - 200
            draw_cloud(d, cx, by, s)
        score = 0 if t < 10.0 else min(120, int((t - 10.0) / 2.5 * 120))
        d.text((48, 48), f"SCORE {score}", font=f_hud, fill=(255, 255, 255))
        pill(d, 802, 48, 230, 92, (255, 122, 26), "DAY 7",
             font(FONT_BOLD, 56), (255, 255, 255))
        if t >= 10.0:
            centre_text(d, 540, 330, "COMBO x5", font(FONT_BOLD, 72),
                        (255, 210, 31))
        draw_miner(d, miner_feet_y(t, 8.5), day7=True)
        gem = gem_pos(t, 8.5)
        img_rgba = img.convert("RGBA")
        if gem is not None:
            draw_gem(img_rgba, gem, day7=True)
        if t >= 10.0:
            draw_particles(img_rgba, t, 10.0, (540, 1100))
        img = img_rgba.convert("RGB")
        d = ImageDraw.Draw(img)
        draw_chips(d)
        return img

    if t < 15.5:
        img = bg7.copy()
        d = ImageDraw.Draw(img)
        draw_sun(d, i)
        for (bx, by, s) in ((80, 420, 1.0), (620, 640, 0.8), (240, 900, 0.7)):
            cx = (bx + int(i * 0.5)) % (W + 400) - 200
            draw_cloud(d, cx, by, s)
        d.text((48, 48), "SCORE 120", font=f_hud, fill=(255, 255, 255))
        pill(d, 802, 48, 230, 92, (255, 122, 26), "DAY 7",
             font(FONT_BOLD, 56), (255, 255, 255))
        centre_text(d, 540, 330, "COMBO x5", font(FONT_BOLD, 72),
                    (255, 210, 31))
        draw_miner(d, GROUND_Y, day7=True)
        draw_chips(d)
        return img

    # 15.5-18.0: hold the t=15.5 frame, blur + desaturate easing over 0.8 s.
    s = max(0.0, min(1.0, (t - 15.5) / 0.8))
    s = s * s * (3 - 2 * s)
    img = hold.filter(ImageFilter.GaussianBlur(radius=28 * s))
    img = ImageEnhance.Color(img).enhance(1 - 0.75 * s)
    return img


def verify_card(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    digest = h.hexdigest()
    if digest != CARD_SHA256:
        print(f"card sha256 mismatch: got {digest}, want {CARD_SHA256}",
              file=sys.stderr)
        sys.exit(1)
    print(f"card verified: {path} sha256 {digest[:16]}...")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", default=None,
                    help="official 9:16 referral end card webm")
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    card = args.card or os.environ.get("CARD_9X16")
    if not card:
        for cand in ("card-9x16-transparent.webm",
                     "../assets/card-9x16-transparent.webm"):
            if os.path.exists(cand):
                card = cand
                break
    if not card or not os.path.exists(card):
        print("official end card webm not found; fetch it from "
              "https://make.fun/press/manifest.json first", file=sys.stderr)
        sys.exit(1)
    verify_card(card)

    out_dir = (args.out_dir or os.environ.get("MAKEFUN_OUTPUT_DIR")
               or "./output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "entry.mp4")

    bg1 = day1_bg()
    bg1_hook = day1_bg(platforms=False)
    bg7 = day7_bg()
    # Hold image = the last frame of the Day 7 hold scene (frame 371,
    # t=15.458); frames from 15.5 s blur/desaturate this image.
    hold = frame_at(int(15.5 * FPS) - 1, bg1, bg7, None, bg1_hook)

    tmp = tempfile.mkdtemp(prefix="tt2-frames-")
    try:
        for i in range(N_FRAMES):
            frame_at(i, bg1, bg7, hold, bg1_hook).save(
                os.path.join(tmp, f"f{i:04d}.png"))
        print(f"rendered {N_FRAMES} frames to {tmp}")

        filt = (
            "[1:v]format=yuva420p,setpts=PTS+15.5/TB[card];"
            "[0:v]format=yuv420p[base];"
            "[base][card]overlay=0:0:format=yuv420[ov];"
            "[ov]drawbox=x=208:y=1230:w=9:h=82:color=white:t=fill:"
            "enable='gte(t,16.93)'[bx];"
            "[bx]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/"
            "DejaVuSansMono-Bold.ttf:text='j9vvzrcw':fontsize=62:"
            "fontcolor=#191419:x=210:y=1242:enable='gte(t,16.93)'[out]"
        )
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-framerate", str(FPS), "-i", os.path.join(tmp, "f%04d.png"),
            "-i", card,
            "-filter_complex", filt,
            "-map", "[out]", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-r", str(FPS), "-crf", "18", "-preset", "medium",
            "-an", "-t", str(DUR), out_path,
        ]
        subprocess.run(cmd, check=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    h = hashlib.sha256()
    with open(out_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    print(f"wrote {out_path} ({os.path.getsize(out_path)} bytes) "
          f"sha256 {h.hexdigest()}")


if __name__ == "__main__":
    main()
