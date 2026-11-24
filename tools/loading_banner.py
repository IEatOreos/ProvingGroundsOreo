"""The loading banner's look (tools/loading_tag.py shows it at the top of MCC while the mod loads): a see-through dark
panel with ember corner marks, the badge (installer/linux/icon.png: Project Noble's logo), "PROJECT NOBLE", the
loading line, a sliding progress bar, and a light streak across it every few seconds. Drawn with Pillow into an RGBA
image; loading_tag.py puts each frame on a per-pixel-alpha window (UpdateLayeredWindow).

(upstream 0.3.0, build 20261119-1940) his banner. (custom, Nov 24) "PROJECT NOBLE" for his name, our logo as the badge,
and no hint line under the title: the owner skipped his loading message (#60), so nothing says when to open Multiplayer;
the eyebrow and the title sit lower in the space it left.

    frame(t, scale, fade) -> PIL.Image RGBA      t: seconds since it opened; fade 0..1 (opening and closing)
    python -I tools/loading_banner.py [out_dir]  -> PNG frames to look at (over a dark and a light backdrop)
"""
import math
import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BADGE = os.path.join(ROOT, "installer", "linux", "icon.png")
W, H = 600, 104                                   # at scale 1 (a 1080-line screen)
EMBER, HEADING, TEXT3, LINE = (240, 135, 46), (241, 232, 212), (174, 163, 139), (53, 58, 64)
STREAK_EVERY = 4.0                               # seconds between light streaks
TITLE = "Loading the bots"
NAME = "PROJECT NOBLE"                           # (custom, Nov 24) in place of his project's name
_fonts, _badges = {}, {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _fonts:
        names = (["bahnschrift.ttf"] if bold else ["bahnschrift.ttf"]) + ["segoeuib.ttf" if bold else "segoeui.ttf",
                                                                            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
        f = None
        for n in names:
            for d in (os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"), ""):
                try:
                    f = ImageFont.truetype(os.path.join(d, n) if d else n, size)
                    if n == "bahnschrift.ttf":
                        try:
                            f.set_variation_by_name("SemiBold" if bold else "Regular")
                        except Exception:
                            pass
                    break
                except Exception:
                    continue
            if f:
                break
        if f is None:
            try:
                f = ImageFont.load_default(size)
            except TypeError:
                f = ImageFont.load_default()
        _fonts[key] = f
    return _fonts[key]


def badge(px):
    if px not in _badges:
        try:
            _badges[px] = Image.open(BADGE).convert("RGBA").resize((px, px), Image.LANCZOS)
        except Exception:
            _badges[px] = None
    return _badges[px]


def spaced(d, xy, text, f, fill, track):
    """Text with letter spacing (the website's eyebrows)."""
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + track


def frame(t, scale=1.0, fade=1.0):
    s = scale
    w, h = int(W * s), int(H * s)
    r = int(16 * s)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    # the panel: a dark gradient, see-through, a hairline border
    grad = Image.new("RGBA", (1, h))
    for y in range(h):
        k = y / max(1, h - 1)
        grad.putpixel((0, y), (int(30 - 10 * k), int(34 - 11 * k), int(39 - 12 * k), int(212 + 10 * k)))
    panel = grad.resize((w, h))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    img.paste(panel, (0, 0), mask)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), r, outline=LINE + (235,), width=max(1, int(1 * s)))
    # a faint ember glow from the left, behind the badge
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((int(-60 * s), int(-50 * s), int(170 * s), h + int(50 * s)), fill=EMBER + (30,))
    glow = glow.filter(ImageFilter.GaussianBlur(28 * s))
    img = Image.composite(Image.alpha_composite(img, glow), img, mask)
    d = ImageDraw.Draw(img)
    # the corner marks (the website's panels)
    cm, lw = int(20 * s), max(2, int(2 * s))
    d.arc((0, 0, 2 * r, 2 * r), 180, 270, fill=EMBER + (230,), width=lw)
    d.line((r, 0, cm + r // 2, 0), fill=EMBER + (230,), width=lw)
    d.line((0, r, 0, cm + r // 2), fill=EMBER + (230,), width=lw)
    d.arc((w - 1 - 2 * r, h - 1 - 2 * r, w - 1, h - 1), 0, 90, fill=EMBER + (230,), width=lw)
    d.line((w - 1 - cm - r // 2, h - 1, w - 1 - r, h - 1), fill=EMBER + (230,), width=lw)
    d.line((w - 1, h - 1 - cm - r // 2, w - 1, h - 1 - r), fill=EMBER + (230,), width=lw)
    # the badge, breathing a little
    bp = int(68 * s)
    b = badge(bp)
    bx, by = int(18 * s), (h - bp) // 2 - int(2 * s)
    if b is not None:
        pulse = 0.5 + 0.5 * math.sin(t * 2.2)
        halo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(halo).ellipse((bx - int(6 * s), by - int(6 * s), bx + bp + int(6 * s), by + bp + int(6 * s)),
                                     fill=EMBER + (int(40 + 40 * pulse),))
        img = Image.alpha_composite(img, halo.filter(ImageFilter.GaussianBlur(10 * s)))
        img.alpha_composite(b, (bx, by))
    d = ImageDraw.Draw(img)
    # the words
    tx = bx + bp + int(18 * s)
    spaced(d, (tx, int(20 * s)), NAME, font(int(13 * s), True), EMBER + (255,), 2.6 * s)
    dots = "." * (1 + int(t * 2.2) % 3)
    d.text((tx, int(40 * s)), TITLE + dots, font=font(int(24 * s), True), fill=HEADING + (255,))
    # the progress bar under the words: a thin track, a glowing segment sliding along it
    track_x0, px1, by0 = tx, w - int(26 * s), h - int(17 * s)
    bh = max(3, int(3 * s))
    d.rounded_rectangle((track_x0, by0, px1, by0 + bh), 2, fill=LINE + (220,))
    span = px1 - track_x0
    seg = span * 0.30
    u = (t * 0.5) % 1.0
    u = u * u * (3 - 2 * u)                      # (eases at both ends)
    sx = track_x0 - seg + u * (span + seg)
    a0, a1 = max(track_x0, sx), min(px1, sx + seg)
    if a1 > a0:
        bar = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(bar).rounded_rectangle((int(a0), by0, int(a1), by0 + bh), 2, fill=EMBER + (255,))
        img = Image.alpha_composite(img, bar.filter(ImageFilter.GaussianBlur(3 * s)))
        img = Image.alpha_composite(img, bar)
    # the light streak: a soft slanted band crossing every STREAK_EVERY seconds
    ph = (t % STREAK_EVERY) / 1.1
    if ph < 1.0:
        band = Image.new("L", (w, h), 0)
        bdw = int(90 * s)
        cx = int(-bdw * 2 + ph * (w + bdw * 4))
        ImageDraw.Draw(band).polygon([(cx, 0), (cx + bdw, 0), (cx + bdw - int(40 * s), h), (cx - int(40 * s), h)],
                                     fill=int(70 * math.sin(ph * math.pi)))
        band = ImageChops.multiply(band.filter(ImageFilter.GaussianBlur(14 * s)), mask)
        shine = Image.new("RGBA", (w, h), (255, 236, 210, 0))
        shine.putalpha(band)
        img = Image.alpha_composite(img, shine)
    if fade < 1.0:
        a = img.getchannel("A").point(lambda v: int(v * max(0.0, fade)))
        img.putalpha(a)
    return img


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "logs", "tmp", "banner")
    os.makedirs(out, exist_ok=True)
    for scale in (1.0, 2.0, 0.75):
        f = frame(0.3, scale)
        for name, col in (("dark", (14, 24, 34, 255)), ("light", (190, 200, 210, 255))):
            bg = Image.new("RGBA", (f.width + 40, f.height + 40), col)
            bg.alpha_composite(f, (20, 20))
            bg.save(os.path.join(out, f"banner_{scale}_{name}.png"))
    for k, t in enumerate((0.15, 0.45, 0.75, 1.2, 2.0)):           # the streak and the bar moving
        bg = Image.new("RGBA", (W + 40, H + 40), (14, 24, 34, 255))
        bg.alpha_composite(frame(t), (20, 20))
        bg.save(os.path.join(out, f"banner_t{k}.png"))
    print("frames in", out)
