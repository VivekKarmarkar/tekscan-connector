#!/usr/bin/env python3
"""
make_slides.py — render the instructional assembly slides (1920x1080) with Pillow.

One slide per narration beat. Each slide draws a clean schematic of the relevant
pieces (handle / sensor / laptop / weight) and glows the specific element being
described in colour, plus an on-screen caption that mirrors the narration.

Single source of truth: SEGMENTS below (also used to drive ElevenLabs TTS, so the
spoken line and the on-screen caption stay in lockstep).
"""

from __future__ import annotations

import math
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1920, 1080
OUT = Path(__file__).resolve().parent / "slides"
OUT.mkdir(parents=True, exist_ok=True)

# --- palette --------------------------------------------------------------- #
BG_TOP, BG_BOT = (11, 15, 26), (22, 30, 50)
INK, SUB = (238, 243, 252), (150, 170, 200)
BLUE, BLUE_GLOW = (54, 121, 255), (70, 200, 255)
GOLD = (224, 168, 74)
PAD = (240, 150, 60)
GREEN = (74, 222, 128)
YELLOW = (255, 210, 63)
FILM, FILM_EDGE = (205, 214, 228), (120, 135, 160)
HBODY, HEDGE = (46, 58, 88), (120, 140, 180)
LBODY, LEDGE, SCREEN = (44, 56, 82), (100, 120, 156), (12, 16, 26)
WEIGHT_C = (90, 110, 150)

FONTS = "/usr/share/fonts/truetype/dejavu/"
def font(sz, bold=True):
    return ImageFont.truetype(FONTS + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), sz)

F_TITLE, F_STEP, F_LABEL, F_CAP = font(40), font(30), font(26), font(46)
F_SMALL = font(22, bold=False)


# --- low-level helpers ----------------------------------------------------- #
def gradient_bg():
    img = Image.new("RGBA", (W, H))
    px = img.load()
    for y in range(H):
        t = y / (H - 1)
        r = int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t)
        for x in range(W):
            px[x, y] = (r, g, b, 255)
    return img


def glow_bbox(img, bbox, color, pad=18, blur=22, ring=True):
    x0, y0, x1, y1 = bbox
    box = (x0 - pad, y0 - pad, x1 + pad, y1 + pad)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(box, radius=pad + 12, outline=color + (190,), width=12)
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))
    if ring:
        ImageDraw.Draw(img).rounded_rectangle(box, radius=pad + 12, outline=color + (255,), width=4)


def arrow(draw, p0, p1, color, width=9, head=24):
    draw.line([p0, p1], fill=color, width=width)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for s in (1, -1):
        a = ang + s * math.radians(26)
        draw.line([p1, (p1[0] - head * math.cos(a), p1[1] - head * math.sin(a))],
                  fill=color, width=width)


def text_center(draw, cx, y, s, fnt, fill):
    w = draw.textlength(s, font=fnt)
    draw.text((cx - w / 2, y), s, font=fnt, fill=fill)


def callout(draw, anchor, text_xy, label, color=SUB):
    draw.line([anchor, text_xy], fill=color, width=2)
    draw.text(text_xy, label, font=F_LABEL, fill=INK)


# --- component drawings (return key bboxes) -------------------------------- #
def draw_handle(img, draw, cx, cy, w=360, h=170):
    body = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    draw.rounded_rectangle(body, radius=34, fill=HBODY, outline=HEDGE, width=5)
    # blue button on the top edge, left-of-centre
    bx, by, br = cx - w * 0.16, cy - h / 2, 30
    btn = (bx - br, by - br, bx + br, by + br)
    draw.ellipse(btn, fill=BLUE, outline=(220, 235, 255), width=4)
    # sensor slot at the right end
    slot = (cx + w / 2 - 6, cy - 34, cx + w / 2 + 22, cy + 34)
    draw.rounded_rectangle(slot, radius=6, fill=(8, 10, 16), outline=(150, 165, 195), width=3)
    # USB cable from the left end -> plug
    lx = cx - w / 2
    draw.line([(lx, cy), (lx - 110, cy + 30), (lx - 210, cy + 8)], fill=(70, 80, 105), width=10, joint="curve")
    plug = (lx - 250, cy - 12, lx - 210, cy + 24)
    draw.rounded_rectangle(plug, radius=4, fill=(180, 190, 210), outline=(90, 100, 125), width=3)
    return {"button": btn, "slot": slot, "slot_entry": (cx + w / 2 + 22, cy),
            "usb_plug": (plug[0], (plug[1] + plug[3]) / 2), "body": body}


def draw_sensor(img, draw, x_tab, y, length=560, pad_r=42):
    film = (x_tab, y - 19, x_tab + length, y + 19)
    draw.rounded_rectangle(film, radius=19, fill=FILM, outline=FILM_EDGE, width=4)
    # connector tab (two prongs) at the left/tab end
    for dy in (-9, 5):
        draw.rounded_rectangle((x_tab - 34, y + dy - 3, x_tab + 6, y + dy + 4), radius=3,
                               fill=GOLD, outline=(150, 110, 40), width=2)
    tab_bb = (x_tab - 36, y - 16, x_tab + 8, y + 16)
    # round sensing pad at the far tip
    pcx = x_tab + length
    pad_bb = (pcx - pad_r, y - pad_r, pcx + pad_r, y + pad_r)
    draw.ellipse(pad_bb, fill=PAD, outline=(150, 90, 30), width=4)
    draw.ellipse((pcx - pad_r * 0.45, y - pad_r * 0.45, pcx + pad_r * 0.45, y + pad_r * 0.45),
                 fill=(255, 200, 130))
    # "UP" marking printed on the film near the tab, with a "this way up" chevron
    ux = x_tab + 24
    draw.polygon([(ux + 2, y - 30), (ux + 18, y - 46), (ux + 34, y - 30)], fill=(150, 170, 200))
    draw.text((ux, y - 14), "UP", font=font(26), fill=(28, 32, 46))
    up_bb = (ux - 12, y - 50, ux + 76, y + 18)
    return {"tab": tab_bb, "pad": pad_bb, "up": up_bb, "tab_point": (x_tab - 36, y), "film": film}


def draw_laptop(img, draw, cx, cy, scale=1.0, check=False):
    sw, sh = 360 * scale, 230 * scale
    screen = (cx - sw / 2, cy - sh, cx + sw / 2, cy)
    draw.rounded_rectangle(screen, radius=14, fill=LBODY, outline=LEDGE, width=5)
    draw.rounded_rectangle((screen[0] + 14, screen[1] + 14, screen[2] - 14, screen[3] - 14),
                           radius=8, fill=SCREEN, outline=(40, 52, 78), width=2)
    # base
    base = [(cx - sw / 2 - 40, cy + 60 * scale), (cx + sw / 2 + 40, cy + 60 * scale),
            (cx + sw / 2, cy), (cx - sw / 2, cy)]
    draw.polygon(base, fill=(34, 44, 66), outline=LEDGE)
    # a USB port on the right side of the base
    port = (cx + sw / 2 + 6, cy + 16 * scale, cx + sw / 2 + 30, cy + 30 * scale)
    draw.rounded_rectangle(port, radius=3, fill=(10, 12, 18), outline=(150, 165, 195), width=2)
    if check:
        ccx, ccy = cx, cy - sh / 2
        draw.line([(ccx - 28, ccy), (ccx - 8, ccy + 22), (ccx + 34, ccy - 30)], fill=GREEN, width=12, joint="curve")
    return {"port": (port[0], (port[1] + port[3]) / 2), "screen": screen}


def draw_weight(img, draw, cx, cy, w=120, h=86):
    box = (cx - w / 2, cy - h, cx + w / 2, cy)
    draw.rounded_rectangle(box, radius=8, fill=WEIGHT_C, outline=(170, 185, 215), width=4)
    # little handle on top
    draw.arc((cx - 26, cy - h - 26, cx + 26, cy - h + 14), 180, 360, fill=(190, 200, 225), width=7)
    text_center(draw, cx, cy - h / 2 - 16, "1000 g", font(26), INK)
    return box


# --- chrome (title, caption) ----------------------------------------------- #
def draw_chrome(img, draw, step_idx, total, caption):
    draw.text((90, 64), "CONNECT YOUR TEKSCAN FORCE SENSOR", font=F_TITLE, fill=INK)
    draw.line([(92, 124), (92 + 760, 124)], fill=(60, 80, 120), width=3)
    pill = (W - 300, 60, W - 90, 116)
    draw.rounded_rectangle(pill, radius=28, fill=(30, 42, 66), outline=(80, 110, 160), width=2)
    text_center(draw, (pill[0] + pill[2]) / 2, 70, f"STEP {step_idx} / {total}", F_STEP, (180, 210, 255))
    # caption bar
    bar = (110, H - 250, W - 110, H - 90)
    panel = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(panel).rounded_rectangle(bar, radius=22, fill=(10, 14, 24, 205), outline=(70, 95, 140, 255), width=3)
    img.alpha_composite(panel)
    lines = textwrap.wrap(caption, width=52)
    y = (H - 250 + H - 90) / 2 - (len(lines) * 56) / 2 + 6
    for ln in lines:
        text_center(draw, W / 2, y, ln, F_CAP, INK)
        y += 56


# --- per-beat scenes ------------------------------------------------------- #
SEGMENTS = [
    {  # 1 overview
        "scene": "overview",
        "caption": "Three pieces: the handle, the sensor, and your laptop.",
        "narration": "Let's connect your Tekscan force sensor. Three pieces matter here — the handle, the sensor, and your laptop. Here's exactly what goes where.",
    },
    {  # 2 handle + usb to laptop
        "scene": "handle_usb",
        "caption": "Plug the handle's USB cable into your laptop.",
        "narration": "Start with the handle — the small unit with the blue button and the attached U S B cable. Plug that cable into any U S B port on your laptop.",
    },
    {  # 3 sensor anatomy
        "scene": "sensor",
        "caption": "Sensor: a round pad on one end, a flat tab marked “UP” on the other.",
        "narration": "Now the sensor — a thin, flexible strip. One end has a round pad; the other has a flat tab that plugs into the handle. Look for the word UP printed near the tab.",
    },
    {  # 4 insertion
        "scene": "insert",
        "caption": "“UP” faces the blue button. Press it, slide the tab in, release.",
        "narration": "Hold the sensor so UP faces the same side as the blue button. Press and hold the blue button, slide the tab in until it stops, then let go.",
    },
    {  # 5 no light on linux
        "scene": "confirm",
        "caption": "No beep on Linux — that's normal. I'll confirm it from the laptop.",
        "narration": "On Windows you would hear a beep. On your Linux laptop you won't — and that's completely fine. I'll confirm the connection from the laptop side.",
    },
    {  # 6 weight / next
        "scene": "weight",
        "caption": "Keep the 1000 g weight ready — you'll rest it on the round pad.",
        "narration": "Last thing — keep your one thousand gram weight handy. Once it's plugged in, I'll run a quick capture while you rest the weight on the round pad. That's it!",
    },
]


def render(seg, idx, total):
    img = gradient_bg()
    draw = ImageDraw.Draw(img)
    scene = seg["scene"]
    midy = 470

    if scene == "overview":
        h = draw_handle(img, draw, 430, midy)
        s = draw_sensor(img, draw, 770, midy + 120, length=420)
        lp = draw_laptop(img, draw, 1560, midy + 30)
        callout(draw, (430, midy + 95), (360, midy + 150), "HANDLE")
        callout(draw, (980, midy + 120), (900, midy + 230), "SENSOR")
        callout(draw, (1560, lp["screen"][1] - 10), (1500, midy - 120), "LAPTOP")

    elif scene == "handle_usb":
        h = draw_handle(img, draw, 620, midy, w=400, h=190)
        lp = draw_laptop(img, draw, 1420, midy + 30)
        arrow(draw, (h["usb_plug"][0] - 30, h["usb_plug"][1]), (lp["port"][0] - 8, lp["port"][1]), GREEN)
        glow_bbox(img, (h["button"]), BLUE_GLOW)
        glow_bbox(img, (h["usb_plug"][0] - 60, h["usb_plug"][1] - 22,
                        h["usb_plug"][0] - 10, h["usb_plug"][1] + 22), GREEN, pad=10)
        callout(draw, ((h["button"][0] + h["button"][2]) / 2, h["button"][1]), (520, 250), "BLUE BUTTON")
        callout(draw, (lp["port"][0], lp["port"][1]), (1560, 300), "USB PORT")

    elif scene == "sensor":
        s = draw_sensor(img, draw, 540, midy + 30, length=820, pad_r=54)
        glow_bbox(img, s["up"], YELLOW)
        glow_bbox(img, s["pad"], PAD)
        callout(draw, ((s["pad"][0] + s["pad"][2]) / 2, s["pad"][3]), (1300, midy + 170), "ROUND PAD")
        callout(draw, ((s["tab"][0] + s["tab"][2]) / 2, s["tab"][3]), (470, midy + 170), "TAB → into handle")

    elif scene == "insert":
        # handle on the LEFT (slot facing right); sensor to the RIGHT with its TAB
        # pointing left into the slot — the tab is the end that inserts.
        h = draw_handle(img, draw, 600, midy, w=380, h=190)
        s = draw_sensor(img, draw, 1015, midy, length=520, pad_r=46)
        slot_x = h["slot_entry"][0]
        tab_x = s["tab_point"][0]
        arrow(draw, (tab_x - 6, midy), (slot_x + 28, midy), GREEN, width=11, head=28)
        glow_bbox(img, h["slot"], GREEN, pad=8)
        glow_bbox(img, h["button"], BLUE_GLOW)
        glow_bbox(img, s["up"], YELLOW)
        text_center(draw, (tab_x + slot_x) / 2, midy - 74, "← slide tab in", F_LABEL, GREEN)
        callout(draw, ((h["button"][0] + h["button"][2]) / 2, h["button"][1]),
                (h["button"][0] - 150, 250), "press & hold")

    elif scene == "confirm":
        h = draw_handle(img, draw, 760, midy, w=360, h=180)
        lp = draw_laptop(img, draw, 1360, midy + 30, scale=1.15, check=True)
        arrow(draw, (h["usb_plug"][0] - 30, h["usb_plug"][1]), (lp["port"][0] - 8, lp["port"][1]), (90, 105, 130), width=7)
        glow_bbox(img, lp["screen"], GREEN, pad=12)
        text_center(draw, 1360, midy - 250, "11DA:0012 detected", F_STEP, GREEN)

    elif scene == "weight":
        s = draw_sensor(img, draw, 560, midy + 60, length=760, pad_r=60)
        pcx = (s["pad"][0] + s["pad"][2]) / 2
        wbox = draw_weight(img, draw, pcx, s["pad"][1] - 14)
        glow_bbox(img, s["pad"], PAD)
        glow_bbox(img, wbox, YELLOW, pad=10)
        arrow(draw, (pcx, wbox[3] + 4), (pcx, s["pad"][1] - 6), YELLOW, width=7, head=18)

    draw_chrome(img, draw, idx, total, seg["caption"])
    out = OUT / f"slide_{idx:02d}.png"
    img.convert("RGB").save(out)
    return out


if __name__ == "__main__":
    total = len(SEGMENTS)
    for i, seg in enumerate(SEGMENTS, 1):
        p = render(seg, i, total)
        print(f"rendered {p.name}")
    # also dump narration lines for the TTS step
    (OUT.parent / "narration.txt").write_text(
        "\n".join(f"{i}\t{s['narration']}" for i, s in enumerate(SEGMENTS, 1))
    )
    print("done ->", OUT)
