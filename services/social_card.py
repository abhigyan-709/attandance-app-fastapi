from io import BytesIO
import base64
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

# ---------- Fonts ----------
def _load_font(size: int) -> ImageFont.FreeTypeFont:
    preferred = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in preferred:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

# Twitter uses fixed-ish sizes; IG scales dynamically
FONT_REG = _load_font(22)
FONT_MED = _load_font(18)
FONT_SMALL = _load_font(14)

# ---------- Helpers ----------
def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=font) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def _verified_badge(theme: str) -> Image.Image:
    size = 18
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    blue = (29, 161, 242, 255) if theme == "light" else (56, 161, 243, 255)
    draw.ellipse([0, 0, size - 1, size - 1], fill=blue)
    draw.line([(5, 10), (8, 13), (13, 6)], fill=(255, 255, 255, 255), width=2, joint="curve")
    return im

def _format_counts(n: int | None) -> str:
    if not n:
        return "0"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M".rstrip("0").rstrip(".")
    if n >= 1_000:
        return f"{n/1_000:.1f}K".rstrip("0").rstrip(".")
    return str(n)

def _fetch_avatar(avatar_url: str | None, initials: str, size: int, theme: str) -> Image.Image:
    bg = (245, 248, 250) if theme == "light" else (32, 35, 39)
    fg = (29, 161, 242) if theme == "light" else (255, 255, 255)
    im = Image.new("RGB", (size, size), bg)
    draw = ImageDraw.Draw(im)

    if avatar_url and avatar_url.lower().startswith(("http://", "https://")):
        try:
            r = requests.get(avatar_url, timeout=4)
            r.raise_for_status()
            av = Image.open(BytesIO(r.content)).convert("RGB")
            return ImageOps.fit(av, (size, size), centering=(0.5, 0.5))
        except Exception:
            pass  # fall through to initials

    draw.ellipse([0, 0, size, size], fill=fg)
    f = _load_font(int(size * 0.45))
    w, h = draw.textbbox((0, 0), initials, font=f)[2:]
    draw.text(((size - w) / 2, (size - h) / 2), initials, fill=(255, 255, 255), font=f)
    return im

def _fetch_image(url: str, size: tuple[int, int], cover: bool = True) -> Image.Image | None:
    try:
        r = requests.get(url, timeout=4)
        r.raise_for_status()
        im = Image.open(BytesIO(r.content)).convert("RGB")
        if cover:
            return ImageOps.fit(im, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
        return im.resize(size, Image.Resampling.LANCZOS)
    except Exception:
        return None

def _circle_avatar(img: Image.Image, size: int) -> Image.Image:
    img = ImageOps.fit(img, (size, size), centering=(0.5, 0.5))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size, size], fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out

# ---------- Twitter ----------
def render_twitter(
    theme: str,
    display_name: str,
    username: str,
    verified: bool,
    text: str,
    avatar_url: str | None,
    comments: int,
    reposts: int,
    likes: int,
    minutes_ago: int,
) -> Image.Image:
    width = 900
    padding = 24
    bg = (255, 255, 255) if theme == "light" else (21, 24, 28)
    fg = (15, 20, 25) if theme == "light" else (231, 233, 234)
    sub = (83, 100, 113) if theme == "light" else (139, 152, 165)

    # measure height
    tmp = Image.new("RGB", (width, 600), bg)
    d = ImageDraw.Draw(tmp)
    content_width = width - padding * 2 - 60 - 12
    lines = _wrap_text(d, text, FONT_REG, content_width)
    text_height = sum(d.textbbox((0, 0), ln, font=FONT_REG)[3] for ln in lines) + (len(lines) - 1) * 6

    height = padding * 2 + 60 + text_height + 24 + 28 + 20
    im = Image.new("RGBA", (width, height), bg + (255,))
    draw = ImageDraw.Draw(im)

    # avatar
    initials = (display_name or username).strip()[:2].upper()
    avatar = _fetch_avatar(avatar_url, initials, 60, theme)
    im.paste(ImageOps.fit(avatar, (60, 60)), (padding, padding))

    # name + handle
    x = padding + 60 + 12
    y = padding
    draw.text((x, y), display_name or username, fill=fg, font=FONT_REG)
    w_name = draw.textlength(display_name or username, font=FONT_REG)
    if verified:
        badge = _verified_badge(theme)
        im.alpha_composite(badge, (int(x + w_name + 6), y + 6))
    y += 28
    handle = f"@{username.lstrip('@')}"
    draw.text((x, y), handle, fill=sub, font=FONT_MED)

    # content
    y = padding + 60 + 10
    for line in lines:
        draw.text((x, y), line, fill=fg, font=FONT_REG)
        y += draw.textbbox((0, 0), line, font=FONT_REG)[3] + 6

    # meta row
    meta = f"{minutes_ago}m ·  {_format_counts(likes)} Likes  ·  {_format_counts(reposts)} Reposts  ·  {_format_counts(comments)} Replies"
    draw.text((x, y + 8), meta, fill=sub, font=FONT_SMALL)

    # border
    draw.rectangle([0, 0, width - 1, height - 1], outline=(230, 236, 240) if theme == "light" else (47, 51, 54))

    return im.convert("RGB")

# ---------- Instagram ----------
def render_instagram(
    theme: str,
    username: str,
    text: str,
    avatar_url: str | None,
    likes: int,
    minutes_ago: int,
    location: str | None,
    photo_url: str | None = None,
    width: int | None = 900,
) -> Image.Image:
    width = width or 900
    pad = int(width * 0.022)           # ~20
    header_h = int(width * 0.055)      # ~50
    avatar_sz = int(width * 0.04)      # ~36
    photo_h = int(width * 0.56)        # ~500
    gap = int(width * 0.017)           # ~15

    # colors
    bg = (255, 255, 255) if theme == "light" else (18, 18, 18)
    panel = (255, 255, 255) if theme == "light" else (24, 24, 24)
    fg = (5, 5, 5) if theme == "light" else (245, 245, 245)
    sub = (115, 115, 115) if theme == "light" else (168, 168, 168)
    border = (219, 219, 219) if theme == "light" else (54, 54, 54)

    # fonts scale
    f_name = _load_font(max(16, int(width * 0.02)))
    f_meta = _load_font(max(12, int(width * 0.016)))
    f_text = _load_font(max(18, int(width * 0.022)))

    # tall canvas -> crop later; RGBA for overlays
    im = Image.new("RGBA", (width, width * 2), bg + (255,))
    draw = ImageDraw.Draw(im)

    # header strip
    draw.rectangle([0, 0, width, header_h + pad], fill=panel)

    # avatar (rounded)
    initials = username[:2].upper()
    av = _fetch_avatar(avatar_url, initials, avatar_sz, theme).convert("RGB")
    av = _circle_avatar(av, avatar_sz)
    im.alpha_composite(av, (pad, pad + (header_h - avatar_sz) // 2))

    # username + location
    text_x = pad + avatar_sz + int(width * 0.012)
    draw.text((text_x, pad + 6), username, fill=fg, font=f_name)
    if location:
        draw.text((text_x, pad + 6 + f_name.size), location, fill=sub, font=f_meta)

    # photo slot
    y = pad + header_h
    placed_photo = False
    if photo_url:
        photo = _fetch_image(photo_url, (width, photo_h))
        if photo:
            im.paste(photo, (0, y))
            placed_photo = True

    if not placed_photo:
        # nice placeholder with subtle vignette + camera glyph
        ph = Image.new("RGB", (width, photo_h), (40, 40, 40) if theme == "dark" else (230, 230, 230))
        overlay = Image.new("L", (width, photo_h), 0)
        ImageDraw.Draw(overlay).rectangle([0, 0, width, photo_h], fill=140)
        ph = Image.composite(ph.filter(ImageFilter.GaussianBlur(0.8)), ph, overlay)
        im.paste(ph, (0, y))

        cx, cy = width // 2, y + photo_h // 2
        cb = int(width * 0.03)  # camera body half-width
        draw.rectangle([cx - cb, cy - int(cb * 0.35), cx + cb, cy + int(cb * 0.35)],
                       fill=(70, 70, 70) if theme == "dark" else (200, 200, 200))
        r = int(width * 0.018)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     outline=(120, 120, 120) if theme == "dark" else (160, 160, 160), width=2)

    # caption block
    y = y + photo_h + gap
    draw.text((pad, y), f"{_format_counts(likes)} likes", fill=fg, font=f_name)
    y += f_name.size + int(gap * 0.2)

    uname = f"{username} "
    uname_w = draw.textlength(uname, font=f_name)
    cap_w = width - pad * 2 - int(uname_w)
    lines = _wrap_text(draw, text, f_text, cap_w)

    if lines:
        draw.text((pad, y), uname, fill=fg, font=f_name)
        draw.text((pad + int(uname_w), y), lines[0], fill=fg, font=f_text)
        y += max(f_text.size, f_name.size) + int(gap * 0.2)
        for line in lines[1:]:
            draw.text((pad, y), line, fill=fg, font=f_text)
            y += f_text.size + int(gap * 0.2)

    draw.text((pad, y), f"{minutes_ago} minutes ago", fill=sub, font=f_meta)
    y += f_meta.size + pad

    # border + crop
    draw.rectangle([0, 0, width - 1, y - 1], outline=border)
    im = im.crop((0, 0, width, y))
    return im.convert("RGB")

# ---------- Encode helper ----------
def render_image_to_data_url(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"
