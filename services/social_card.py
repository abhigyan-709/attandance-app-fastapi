# services/social_card.py
from io import BytesIO
import base64
from typing import Tuple
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests

# Try to use a decent font; fall back if missing
def _load_font(size: int) -> ImageFont.FreeTypeFont:
    preferred = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    for p in preferred:
        try:
            return ImageFont.truetype(p, size)
        except:
            continue
    return ImageFont.load_default()

FONT_REG = _load_font(22)
FONT_MED = _load_font(18)
FONT_SMALL = _load_font(14)

def _fetch_avatar(avatar_url: str | None, initials: str, size: int, theme: str) -> Image.Image:
    bg = (245, 248, 250) if theme == "light" else (32, 35, 39)
    fg = (29, 161, 242) if theme == "light" else (255, 255, 255)
    im = Image.new("RGB", (size, size), bg)
    draw = ImageDraw.Draw(im)

    # Only try HTTP(S) URLs
    if avatar_url and avatar_url.lower().startswith(("http://", "https://")):
        try:
            r = requests.get(avatar_url, timeout=4)
            r.raise_for_status()
            av = Image.open(BytesIO(r.content)).convert("RGB").resize((size, size))
            return ImageOps.fit(av, (size, size), centering=(0.5, 0.5))
        except Exception:
            pass  # fall back to initials

    # initials avatar fallback
    draw.ellipse([0,0,size,size], fill=fg)
    f = _load_font(int(size*0.45))
    w,h = draw.textbbox((0,0), initials, font=f)[2:]
    draw.text(((size-w)/2,(size-h)/2), initials, fill=(255,255,255), font=f)
    return im


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=font) <= max_width:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def _verified_badge(theme: str) -> Image.Image:
    # simple blue circle + check
    size = 18
    im = Image.new("RGBA", (size,size), (0,0,0,0))
    draw = ImageDraw.Draw(im)
    blue = (29, 161, 242, 255) if theme == "light" else (56, 161, 243, 255)
    draw.ellipse([0,0,size-1,size-1], fill=blue)
    # check mark
    draw.line([(5,10),(8,13),(13,6)], fill=(255,255,255,255), width=2, joint="curve")
    return im

def _format_counts(n:int) -> str:
    if n is None: return "0"
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M".rstrip('0').rstrip('.')
    if n >= 1_000: return f"{n/1_000:.1f}K".rstrip('0').rstrip('.')
    return str(n)

def render_twitter(theme: str, display_name: str, username: str, verified: bool, text: str,
                   avatar_url: str | None, comments: int, reposts: int, likes: int,
                   minutes_ago: int) -> Image.Image:
    width = 900
    padding = 24
    bg = (255,255,255) if theme == "light" else (21,24,28)
    fg = (15,20,25) if theme == "light" else (231,233,234)
    sub = (83,100,113) if theme == "light" else (139,152,165)
    link = (29,161,242)

    # measure text to compute height
    temp = Image.new("RGB", (width, 600), bg)
    d = ImageDraw.Draw(temp)
    content_width = width - padding*2 - 60 - 12
    lines = _wrap_text(d, text, FONT_REG, content_width)
    text_height = sum(d.textbbox((0,0), line, font=FONT_REG)[3] for line in lines) + (len(lines)-1)*6

    height = padding*2 + 60 + text_height + 24 + 28 + 20
    im = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(im)

    # avatar
    initials = (display_name or username).strip()[:2].upper()
    avatar = _fetch_avatar(avatar_url, initials, 60, theme)
    im.paste(ImageOps.fit(avatar, (60,60)), (padding, padding))

    # name + handle
    x = padding + 60 + 12
    y = padding
    draw.text((x, y), display_name or username, fill=fg, font=FONT_REG)
    w_name = draw.textlength(display_name or username, font=FONT_REG)
    if verified:
        badge = _verified_badge(theme)
        im.alpha_composite(badge, (int(x + w_name + 6), y+6))
    y += 28
    handle = f"@{username.lstrip('@')}"
    draw.text((x, y), handle, fill=sub, font=FONT_MED)

    # content
    y = padding + 60 + 10
    for line in lines:
        draw.text((x, y), line, fill=fg, font=FONT_REG)
        y += draw.textbbox((0,0), line, font=FONT_REG)[3] + 6

    # meta row
    meta = f"{minutes_ago}m ·  { _format_counts(likes)} Likes  ·  {_format_counts(reposts)} Reposts  ·  {_format_counts(comments)} Replies"
    draw.text((x, y+8), meta, fill=sub, font=FONT_SMALL)

    # border
    draw.rectangle([0,0,width-1,height-1], outline=(230,236,240) if theme=="light" else (47,51,54))
    return im

def render_instagram(theme: str, username: str, text: str, avatar_url: str | None,
                     likes: int, minutes_ago: int, location: str | None) -> Image.Image:
    width = 900
    padding = 20
    bg = (255,255,255) if theme == "light" else (18,18,18)
    fg = (0,0,0) if theme == "light" else (245,245,245)
    sub = (115,115,115) if theme == "light" else (168,168,168)

    temp = Image.new("RGB", (width, 1000), bg)
    d = ImageDraw.Draw(temp)
    content_width = width - padding*2
    lines = _wrap_text(d, text, FONT_REG, content_width-20)
    text_height = sum(d.textbbox((0,0), line, font=FONT_REG)[3] for line in lines) + (len(lines)-1)*6

    # a post header + fake photo slot + caption + footer
    photo_h = 500
    height = padding + 50 + photo_h + 16 + text_height + 24 + padding
    im = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(im)

    # header
    av = _fetch_avatar(avatar_url, username[:2].upper(), 36, theme)
    im.paste(ImageOps.fit(av, (36,36)), (padding, padding+7))
    draw.text((padding+44, padding+8), username, fill=fg, font=FONT_MED)
    if location:
        draw.text((padding+44, padding+8+20), location, fill=sub, font=FONT_SMALL)

    # fake photo area
    draw.rectangle([0, padding+50, width, padding+50+photo_h], fill=(230,230,230) if theme=="light" else (38,38,38))
    # small camera glyph
    draw.rectangle([width/2-18, padding+50+photo_h/2-6, width/2-4, padding+50+photo_h/2+6], fill=(200,200,200) if theme=="light" else (58,58,58))
    draw.ellipse([width/2+2, padding+50+photo_h/2-8, width/2+18, padding+50+photo_h/2+8], outline=(180,180,180) if theme=="light" else (88,88,88), width=2)

    # caption
    y = padding + 50 + photo_h + 16
    draw.text((padding, y), f"{_format_counts(likes)} likes", fill=fg, font=FONT_MED)
    y += 22
    # username bold-ish effect by drawing twice
    draw.text((padding, y), f"{username} ", fill=fg, font=FONT_MED)
    uname_w = draw.textlength(f"{username} ", font=FONT_MED)
    cap_w = content_width - uname_w
    cap_lines = _wrap_text(draw, text, FONT_REG, cap_w)
    x = padding + int(uname_w)
    for i, line in enumerate(cap_lines):
        if i == 0:
            draw.text((x, y), line, fill=fg, font=FONT_REG)
        else:
            draw.text((padding, y), line, fill=fg, font=FONT_REG)
        y += draw.textbbox((0,0), line, font=FONT_REG)[3] + 6

    draw.text((padding, y+2), f"{minutes_ago} minutes ago", fill=sub, font=FONT_SMALL)

    draw.rectangle([0,0,width-1,height-1], outline=(219,219,219) if theme=="light" else (54,54,54))
    return im

def render_image_to_data_url(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"
