# services/fun_text.py
# Unicode text styling utils (no persistence, no logging of user text)

from typing import Callable, Dict, List

# ---------- low-level helpers ----------

def _map_with_offsets(text: str, upper_base: int | None, lower_base: int | None, digit_base: int | None) -> str:
    out = []
    for ch in text:
        o = ord(ch)
        if 'A' <= ch <= 'Z' and upper_base is not None:
            out.append(chr(upper_base + (o - 65)))
        elif 'a' <= ch <= 'z' and lower_base is not None:
            out.append(chr(lower_base + (o - 97)))
        elif '0' <= ch <= '9' and digit_base is not None:
            out.append(chr(digit_base + (o - 48)))
        else:
            out.append(ch)
    return ''.join(out)

def _combine_each(text: str, *comb: str) -> str:
    out = []
    for ch in text:
        if ch.isspace():
            out.append(ch)
        else:
            out.append(ch + ''.join(comb))
    return ''.join(out)

def _space_between(text: str, spacer: str = " ") -> str:
    return spacer.join(list(text))

def _alt_case(text: str, start_upper: bool = True) -> str:
    res = []
    up = start_upper
    for c in text:
        if c.isalpha():
            res.append(c.upper() if up else c.lower())
            up = not up
        else:
            res.append(c)
    return ''.join(res)

# small-caps map (best effort)
_SMALL_CAPS = {
    'a':'ᴀ','b':'ʙ','c':'ᴄ','d':'ᴅ','e':'ᴇ','f':'ꜰ','g':'ɢ','h':'ʜ','i':'ɪ','j':'ᴊ',
    'k':'ᴋ','l':'ʟ','m':'ᴍ','n':'ɴ','o':'ᴏ','p':'ᴘ','q':'ǫ','r':'ʀ','s':'s','t':'ᴛ',
    'u':'ᴜ','v':'ᴠ','w':'ᴡ','x':'x','y':'ʏ','z':'ᴢ'
}
def _small_caps(t: str) -> str:
    out=[]
    for ch in t:
        if ch.isalpha():
            out.append(_SMALL_CAPS.get(ch.lower(), ch))
        else:
            out.append(ch)
    return ''.join(out)

# upside-down and mirror maps
_UPSIDE_MAP = {
    'a':'ɐ','b':'q','c':'ɔ','d':'p','e':'ǝ','f':'ɟ','g':'ƃ','h':'ɥ','i':'ᴉ','j':'ɾ','k':'ʞ','l':'ʃ','m':'ɯ',
    'n':'u','o':'o','p':'d','q':'b','r':'ɹ','s':'s','t':'ʇ','u':'n','v':'ʌ','w':'ʍ','x':'x','y':'ʎ','z':'z',
    'A':'∀','B':'𐐒','C':'Ɔ','D':'◖','E':'Ǝ','F':'Ⅎ','G':'⅁','H':'H','I':'I','J':'ſ','K':'ʞ','L':'˥','M':'W',
    'N':'N','O':'O','P':'Ԁ','Q':'Ό','R':'ɹ','S':'S','T':'⊥','U':'∩','V':'Λ','W':'M','X':'X','Y':'⅄','Z':'Z',
    '0':'0','1':'Ɩ','2':'ᄅ','3':'Ɛ','4':'ㄣ','5':'ϛ','6':'9','7':'ㄥ','8':'8','9':'6',
    '.':'˙',',':"'",'\'':',','"':',,','`':',',';':'؛','!':'¡','?':'¿','(' :')',')':'(','[':']',']':'[','{':'}','}':'{','<':'>','>':'<','_':'‾'
}
def _upside_down(t: str) -> str:
    return ''.join(_UPSIDE_MAP.get(ch, ch) for ch in t[::-1])

_MIRROR_MAP = {
    'a':'ɒ','b':'d','c':'ɔ','d':'b','e':'ɘ','f':'ɟ','g':'ƃ','h':'ʜ','i':'i','j':'ɿ','k':'ʞ','l':'l','m':'m',
    'n':'ᴎ','o':'o','p':'q','q':'p','r':'ɿ','s':'ƨ','t':'ʇ','u':'u','v':'v','w':'w','x':'x','y':'ʏ','z':'z',
    'A':'A','B':'ᙠ','C':'Ɔ','D':'ᗡ','E':'Ǝ','F':'ᖵ','G':'ꓨ','H':'H','I':'I','J':'Ⴑ','K':'⋊','L':'⅃','M':'M',
    'N':'N','O':'O','P':'ᖈ','Q':'Ọ','R':'Я','S':'Ƨ','T':'T','U':'Ⴎ','V':'Ʌ','W':'MX','X':'X','Y':'ʏ','Z':'Z'
}
def _mirror(t: str) -> str:
    return ''.join(_MIRROR_MAP.get(ch, ch) for ch in t[::-1])

# ---------- base styles ----------

def s_bold(t):              return _map_with_offsets(t, 0x1D400, 0x1D41A, 0x1D7CE)
def s_italic(t):            return _map_with_offsets(t, 0x1D434, 0x1D44E, None)
def s_bold_italic(t):       return _map_with_offsets(t, 0x1D468, 0x1D482, None)
def s_sans(t):              return _map_with_offsets(t, 0x1D5A0, 0x1D5BA, 0x1D7E2)
def s_sans_bold(t):         return _map_with_offsets(t, 0x1D5D4, 0x1D5EE, 0x1D7EC)
def s_sans_italic(t):       return _map_with_offsets(t, 0x1D608, 0x1D622, None)
def s_sans_bold_italic(t):  return _map_with_offsets(t, 0x1D63C, 0x1D656, None)
def s_mono(t):              return _map_with_offsets(t, 0x1D670, 0x1D68A, 0x1D7F6)
def s_script_bold(t):       return _map_with_offsets(t, 0x1D4D0, 0x1D4EA, None)
def s_fraktur_bold(t):      return _map_with_offsets(t, 0x1D56C, 0x1D586, None)
def s_double_struck(t):     return _map_with_offsets(t, 0x1D538, 0x1D552, 0x1D7D8)

def s_circled(t):
    # circled letters & 1..10; handle 0 manually
    s = _map_with_offsets(t, 0x24B6, 0x24D0, 0x2460)
    return s.replace('0', '⓪')

def s_circled_inverse(t):   return _map_with_offsets(t, 0x1F150, 0x1F170, None)
def s_squared(t):           return _map_with_offsets(t, 0x1F130, 0x1F150, None)
def s_squared_inverse(t):   return _map_with_offsets(t, 0x1F170, 0x1F190, None)

def s_fullwidth(t):
    res=[]
    for ch in t:
        if ch == ' ':
            res.append('　')
        elif 33 <= ord(ch) <= 126:
            res.append(chr(ord(ch) + 0xFF00 - 0x20))
        else:
            res.append(ch)
    return ''.join(res)

def s_small_caps(t):        return _small_caps(t)
def s_superscript(t):
    table = str.maketrans({
        '0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹',
        'a':'ᵃ','b':'ᵇ','c':'ᶜ','d':'ᵈ','e':'ᵉ','f':'ᶠ','g':'ᵍ','h':'ʰ','i':'ⁱ','j':'ʲ','k':'ᵏ',
        'l':'ˡ','m':'ᵐ','n':'ⁿ','o':'ᵒ','p':'ᵖ','q':'ᑫ','r':'ʳ','s':'ˢ','t':'ᵗ','u':'ᵘ','v':'ᵛ',
        'w':'ʷ','x':'ˣ','y':'ʸ','z':'ᶻ','A':'ᴬ','B':'ᴮ','C':'ᶜ','D':'ᴰ','E':'ᴱ','F':'ᶠ','G':'ᴳ',
        'H':'ᴴ','I':'ᴵ','J':'ᴶ','K':'ᴷ','L':'ᴸ','M':'ᴹ','N':'ᴺ','O':'ᴼ','P':'ᴾ','Q':'Q','R':'ᴿ',
        'S':'ˢ','T':'ᵀ','U':'ᵁ','V':'ⱽ','W':'ᵂ','X':'ˣ','Y':'ʸ','Z':'ᶻ','+':'⁺','-':'⁻','=':'⁼','(':'⁽',')':'⁾'
    })
    return t.translate(table)

def s_subscript(t):
    table = str.maketrans({
        '0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅','6':'₆','7':'₇','8':'₈','9':'₉',
        'a':'ₐ','e':'ₑ','h':'ₕ','i':'ᵢ','j':'ⱼ','k':'ₖ','l':'ₗ','m':'ₘ','n':'ₙ','o':'ₒ',
        'p':'ₚ','r':'ᵣ','s':'ₛ','t':'ₜ','u':'ᵤ','v':'ᵥ','x':'ₓ','+':'₊','-':'₋','=':'₌','(':'₍',')':'₎'
    })
    return t.translate(table)

def s_upside_down(t):       return _upside_down(t)
def s_mirror(t):            return _mirror(t)
def s_underline(t):         return _combine_each(t, '\u0332')
def s_double_underline(t):  return _combine_each(t, '\u0333')
def s_wave_underline(t):    return _combine_each(t, '\u0347')  # dotted below-ish
def s_dotted_underline(t):  return _combine_each(t, '\u0324')

# ---------- decorators ----------

def d_none(t):              return t
def d_sparkles(t):          return f"✨ {t} ✨"
def d_fire(t):              return f"🔥 {t} 🔥"
def d_stars(t):             return f"★彡 {t} 彡★"
def d_arrows(t):            return f"➤ {t} ◀"
def d_hearts(t):            return f"♥ {t} ♥"
def d_brackets(t):          return f"『 {t} 』"
def d_curly(t):             return f"⟬ {t} ⟭"

def _box(text: str, heavy: bool = False) -> str:
    lines = text.splitlines() or [text]
    w = max(len(line) for line in lines)
    if heavy:
        top, side, bot, fill = "┏", "┃", "┗", "━"
    else:
        top, side, bot, fill = "┌", "│", "└", "─"
    t = top + fill * w + ("┓" if heavy else "┐")
    b = bot + fill * w + ("┛" if heavy else "┘")
    mid = [f"{side}{line.ljust(w)}{( '┃' if heavy else '│')}" for line in lines]
    return '\n'.join([t, *mid, b])

def d_box_light(t):         return _box(t, heavy=False)
def d_box_heavy(t):         return _box(t, heavy=True)
def d_wave_space(t):        return _space_between(t, " ~ ")
def d_aesthetic_space(t):   return _space_between(t, " ")
def d_dot_space(t):         return _space_between(t, "·")
def d_alt_case_upper(t):    return _alt_case(t, True)
def d_alt_case_lower(t):    return _alt_case(t, False)

# ---------- registries ----------

STYLE_FUNCS: Dict[str, Callable[[str], str]] = {
    "bold": s_bold,
    "italic": s_italic,
    "bold_italic": s_bold_italic,
    "sans": s_sans,
    "sans_bold": s_sans_bold,
    "sans_italic": s_sans_italic,
    "sans_bold_italic": s_sans_bold_italic,
    "mono": s_mono,
    "script_bold": s_script_bold,
    "fraktur_bold": s_fraktur_bold,
    "double_struck": s_double_struck,
    "circled": s_circled,
    "circled_inverse": s_circled_inverse,
    "squared": s_squared,
    "squared_inverse": s_squared_inverse,
    "fullwidth": s_fullwidth,
    "small_caps": s_small_caps,
    "superscript": s_superscript,
    "subscript": s_subscript,
    "upside_down": s_upside_down,
    "mirror": s_mirror,
    "underline": s_underline,
    "double_underline": s_double_underline,
    "wave_underline": s_wave_underline,
    "dotted_underline": s_dotted_underline,
}

DECORATOR_FUNCS: Dict[str, Callable[[str], str]] = {
    "none": d_none,
    "sparkles": d_sparkles,
    "fire": d_fire,
    "stars": d_stars,
    "arrows": d_arrows,
    "hearts": d_hearts,
    "brackets": d_brackets,
    "curly": d_curly,
    "box_light": d_box_light,
    "box_heavy": d_box_heavy,
    "wave_space": d_wave_space,
    "aesthetic_space": d_aesthetic_space,
    "dot_space": d_dot_space,
    "alt_case_upper": d_alt_case_upper,
    "alt_case_lower": d_alt_case_lower,
}

def list_styles() -> List[str]:
    return list(STYLE_FUNCS.keys())

def list_decorators() -> List[str]:
    return list(DECORATOR_FUNCS.keys())

def render(text: str, style: str, decorator: str = "none") -> str:
    # core render – pure, stateless
    style_fn = STYLE_FUNCS.get(style)
    if style_fn is None:
        raise ValueError(f"Unknown style: {style}")
    deco_fn = DECORATOR_FUNCS.get(decorator, d_none)
    return deco_fn(style_fn(text))
