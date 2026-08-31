"""Render a Kebbet Zamen receipt directly to a raster image for ESC/POS
thermal printing, replacing the old "open HTML in the browser and print"
flow. Drawing everything ourselves (instead of relying on a browser) means
we can trim the image to the receipt's actual content height, so the paper
only feeds out as far as the last printed line plus a small tail -- not the
full configured maximum length.

Arabic text is shaped with real HarfBuzz OpenType shaping (uharfbuzz) and
rasterized glyph-by-glyph with FreeType (freetype-py), rather than through
Pillow's own text-drawing. Pillow's RTL/shaping support goes through its
`raqm` text-layout engine, which the official PyPI Windows wheel does not
build in at all (confirmed by inspecting the wheel: no raqm/fribidi/
harfbuzz DLLs anywhere in it) -- so `direction='rtl'` always raised
"setting text direction, language or font features is not supported
without libraqm" on a real install, dev environment or not. A first fix
attempt worked around that by hand-substituting legacy Arabic Presentation
Forms characters (arabic_reshaper + python-bidi) and drawing those with
Pillow's plain text(), but that only looks right if the font's cmap maps
those legacy codepoints to properly *joined* glyph artwork -- most modern
Arabic fonts only shape correctly through a real OpenType engine and don't
carry that, so letters came out disconnected/wrong. HarfBuzz does the
genuine contextual shaping instead, which is what actually looks correct.

uharfbuzz ships harfbuzz statically compiled into its .pyd extension
module (a normal Python import, unlike raqm's runtime-loaded plugin), and
freetype-py's bundled DLL has a maintained PyInstaller hook -- both bundle
reliably into the frozen exe.
"""
import os
import re
import sys

import freetype
import uharfbuzz as hb
from PIL import Image, ImageDraw, ImageFont

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (150, 150, 150)

_AR_RANGE = '؀-ۿݐ-ݿࢠ-ࣿ'
_AR_RUN_RE = re.compile(f'[{_AR_RANGE} ]+|[^{_AR_RANGE}]+')


def _split_runs(text):
    """Splits text into (is_arabic, chunk) runs. A space next to Arabic
    text is grouped into the Arabic run on either side of it, which is
    exactly the split real bidi text needs for our receipts (an Arabic
    label butting up against a Latin value/name, e.g. "فرع dbayeh")."""
    runs = []
    for chunk in _AR_RUN_RE.findall(text):
        is_ar = any('؀' <= ch <= 'ۿ' or 'ݐ' <= ch <= 'ݿ' or 'ࢠ' <= ch <= 'ࣿ'
                    for ch in chunk)
        runs.append((is_ar, chunk))
    return runs


def _fonts_dir():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'fonts')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')


# Cairo: a variable font (Weight axis 200-1000) designed for real Arabic
# OpenType shaping -- its cmap doesn't fully cover the legacy Arabic
# Presentation Forms block (that broke the earlier presentation-forms
# substitution approach), but its GSUB contextual-joining tables are
# exactly what HarfBuzz needs and are complete.
_FONT_FILE = 'Cairo.ttf'

_PIL_FONT_CACHE = {}
_HB_FACE = None
_HB_FONT_CACHE = {}
_FT_FACE_CACHE = {}


def _font_path():
    return os.path.join(_fonts_dir(), _FONT_FILE)


def _font(weight, size):
    """PIL font, used to draw/measure the non-Arabic (Latin/digit) runs --
    those don't need shaping, plain cmap-based glyph lookup is correct."""
    key = (weight, size)
    f = _PIL_FONT_CACHE.get(key)
    if f is None:
        f = ImageFont.truetype(_font_path(), size)
        f.set_variation_by_axes([weight, 0])
        _PIL_FONT_CACHE[key] = f
    return f


def _hb_font(weight, size):
    global _HB_FACE
    key = (weight, size)
    f = _HB_FONT_CACHE.get(key)
    if f is None:
        if _HB_FACE is None:
            _HB_FACE = hb.Face(hb.Blob.from_file_path(_font_path()))
        f = hb.Font(_HB_FACE)
        f.scale = (size * 64, size * 64)
        hb.ot_font_set_funcs(f)
        f.set_variations({'wght': weight, 'slnt': 0})
        _HB_FONT_CACHE[key] = f
    return f


def _ft_face(weight, size):
    key = (weight, size)
    f = _FT_FACE_CACHE.get(key)
    if f is None:
        f = freetype.Face(_font_path())
        f.set_char_size(size * 64)
        f.set_var_design_coords([weight, 0])
        _FT_FACE_CACHE[key] = f
    return f


def _shape_arabic(chunk, weight, size):
    """Shapes one Arabic run with HarfBuzz. Returns (glyph_infos,
    glyph_positions, total_width_px) -- positions are already in the
    correct left-to-right *drawing* order (HarfBuzz pre-reverses an RTL
    buffer for you), so callers just walk the list and advance rightward."""
    buf = hb.Buffer()
    buf.add_str(chunk)
    buf.direction = 'rtl'
    buf.script = 'Arab'
    buf.language = 'ar'
    hb.shape(_hb_font(weight, size), buf)
    width = sum(p.x_advance for p in buf.glyph_positions) / 64
    return buf.glyph_infos, buf.glyph_positions, width


def _draw_arabic_run(img, chunk, weight, size, x, baseline_y, fill):
    infos, positions, _ = _shape_arabic(chunk, weight, size)
    face = _ft_face(weight, size)
    pen_x = x
    for info, pos in zip(infos, positions):
        face.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER)
        glyph = face.glyph
        bmp = glyph.bitmap
        if bmp.width and bmp.rows:
            mask = Image.frombytes('L', (bmp.width, bmp.rows), bytes(bmp.buffer))
            gx = round(pen_x + pos.x_offset / 64 + glyph.bitmap_left)
            gy = round(baseline_y - pos.y_offset / 64 - glyph.bitmap_top)
            img.paste(Image.new('RGB', mask.size, fill), (gx, gy), mask)
        pen_x += pos.x_advance / 64
        baseline_y -= pos.y_advance / 64
    return pen_x


class _Line:
    """Measures and draws one logical line of text that may mix Arabic
    and Latin/digit runs (e.g. "فرع dbayeh", "#1234", a plain Arabic
    phrase). Runs are laid out right-to-left in logical order, which is
    the correct visual result for the simple single-embedding-level
    strings a receipt actually contains (verified against real
    browser-rendered ground truth for both pure-Arabic and mixed lines)."""

    def __init__(self, draw, text, weight, size):
        self.draw = draw
        self.weight = weight
        self.size = size
        self.runs = _split_runs(text)
        font = _font(weight, size)
        self.ascent, self.descent = font.getmetrics()
        self._pil_font = font

    def width(self):
        total = 0
        for is_ar, chunk in self.runs:
            if is_ar:
                _, _, w = _shape_arabic(chunk, self.weight, self.size)
                total += w
            else:
                total += self.draw.textlength(chunk, font=self._pil_font)
        return total

    def draw_right_aligned(self, img, right_x, top_y, fill=BLACK):
        """Draws with the line's right edge at right_x and its top at
        top_y (matching the old anchor='ma'/'ra' top-anchored behaviour).
        Returns the left edge x reached, and the y just past the line."""
        baseline_y = top_y + self.ascent
        x = right_x
        for is_ar, chunk in self.runs:
            w = (self._shape_width(chunk) if is_ar else self.draw.textlength(chunk, font=self._pil_font))
            x -= w
            if is_ar:
                _draw_arabic_run(img, chunk, self.weight, self.size, x, baseline_y, fill)
            else:
                self.draw.text((x, baseline_y), chunk, font=self._pil_font, fill=fill, anchor='ls')
        return x, top_y + self.ascent + self.descent

    def _shape_width(self, chunk):
        _, _, w = _shape_arabic(chunk, self.weight, self.size)
        return w


class ReceiptCanvas:
    def __init__(self, width_px, max_height_px, dpmm):
        self.w = width_px
        self.dpmm = dpmm
        self.pad = self.mm(4)
        self.img = Image.new('RGB', (width_px, max_height_px), WHITE)
        self.d = ImageDraw.Draw(self.img)
        self.y = self.mm(4)

    def mm(self, v):
        return round(v * self.dpmm)

    def advance(self, dy):
        self.y += dy

    # ── primitives ──────────────────────────────────────────────────────
    def center_text(self, text, weight, size, gap_after=0, fill=BLACK, spacing=0):
        if spacing:
            self._center_spaced(text, _font(weight, size), spacing, fill)
        else:
            line = _Line(self.d, text, weight, size)
            right_x = self.w / 2 + line.width() / 2
            _, self.y = line.draw_right_aligned(self.img, right_x, self.y, fill)
        self.y += gap_after

    def _center_spaced(self, text, font, spacing, fill):
        widths = [self.d.textlength(ch, font=font) for ch in text]
        total = sum(widths) + spacing * (len(text) - 1)
        x = (self.w - total) / 2
        ascent, descent = font.getmetrics()
        for ch, wch in zip(text, widths):
            self.d.text((x, self.y), ch, font=font, fill=fill, anchor='la')
            x += wch + spacing
        self.y += ascent + descent

    def dashed_line(self, gap_before=0, gap_after=0, dash=None, gap=None, width=None, fill=BLACK):
        self.y += gap_before
        width = width or max(1, self.mm(0.5))
        dash = dash or self.mm(1.6)
        gap = gap or self.mm(1)
        x, x2 = self.pad, self.w - self.pad
        while x < x2:
            self.d.line([(x, self.y), (min(x + dash, x2), self.y)], fill=fill, width=width)
            x += dash + gap
        self.y += width + gap_after

    def dotted_line(self, gap_before=0, gap_after=0, r=None, gap=None, fill=BLACK):
        self.y += gap_before
        r = r or max(1, self.mm(0.35))
        gap = gap or self.mm(1.4)
        x, x2 = self.pad, self.w - self.pad
        while x < x2:
            self.d.ellipse([x - r, self.y - r, x + r, self.y + r], fill=fill)
            x += gap
        self.y += r + gap_after

    def black_bar(self, text, size=26, weight=700, pad=None, gap_before=0, gap_after=0):
        self.y += gap_before
        pad = self.mm(1.5) if pad is None else pad
        line = _Line(self.d, text, weight, size)
        bar_h = (line.ascent + line.descent) + 2 * pad
        self.d.rectangle([self.pad, self.y, self.w - self.pad, self.y + bar_h], fill=BLACK)
        right_x = self.w / 2 + line.width() / 2
        line.draw_right_aligned(self.img, right_x, self.y + pad, WHITE)
        self.y += bar_h + gap_after

    def info_row(self, label, value, label_size=19, value_size=23):
        lline = _Line(self.d, label, 400, label_size)
        vline = _Line(self.d, str(value), 700, value_size)
        _, y_after_l = lline.draw_right_aligned(self.img, self.w - self.pad, self.y, BLACK)
        left_x, y_after_v = vline.draw_right_aligned(self.img, self.pad + vline.width(), self.y, BLACK)
        self.y += max(y_after_l, y_after_v) - self.y + self.mm(1.5)

    def wrapped_rtl(self, text, weight, size, right_x, max_width, fill=BLACK):
        words = text.split(' ')
        lines, cur = [], ''
        for word in words:
            trial = (cur + ' ' + word).strip()
            if not cur or _Line(self.d, trial, weight, size).width() <= max_width:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        line_h = None
        for text_line in lines:
            line = _Line(self.d, text_line, weight, size)
            if line_h is None:
                line_h = (line.ascent + line.descent) * 1.3
            line.draw_right_aligned(self.img, right_x, self.y, fill)
            self.y += line_h
        return len(lines)

    def qty_badge(self, qty, name, qty_size=28, name_size=28):
        qf = _font(900, qty_size)
        qty_str = str(qty)
        qb = self.d.textbbox((0, 0), qty_str, font=qf)
        badge_w = max(self.mm(8), (qb[2] - qb[0]) + 2 * self.mm(2))
        badge_h = (qb[3] - qb[1]) + self.mm(2)
        top = self.y
        left = self.w - self.pad - badge_w
        self.d.rounded_rectangle([left, top, left + badge_w, top + badge_h], radius=self.mm(0.6), fill=BLACK)
        self.d.text((left + badge_w / 2, top + badge_h / 2), qty_str, font=qf, fill=WHITE, anchor='mm')

        gap = self.mm(2)
        right_x = left - gap
        max_w = right_x - self.pad
        self.wrapped_rtl(name, 700, name_size, right_x, max_w)
        self.y = max(self.y, top + badge_h)

    def note(self, text, size=24):
        indent = self.mm(6)
        right_x = self.w - self.pad - indent
        max_w = right_x - self.pad
        top = self.y
        self.wrapped_rtl(text, 700, size, right_x, max_w)
        self.d.line([(right_x + self.mm(1.5), top), (right_x + self.mm(1.5), self.y)],
                    fill=BLACK, width=max(1, self.mm(0.5)))

    def render_item(self, item):
        self.qty_badge(item.get('qty', ''), item.get('arabic_name', ''))
        for c in item.get('comments') or []:
            if not c:
                continue
            self.advance(self.mm(1))
            self.note(c)

    def bag_frame(self, title, bag_items):
        self.y += self.mm(3)
        left, right = self.pad, self.w - self.pad
        border_w = max(2, self.mm(0.7))
        top = self.y

        line = _Line(self.d, title, 900, 26)
        title_h = (line.ascent + line.descent) + 2 * self.mm(2.5)
        self.d.rectangle([left, top, right, top + title_h], fill=BLACK)
        right_x = (left + right) / 2 + line.width() / 2
        line.draw_right_aligned(self.img, right_x, top + self.mm(2.5), WHITE)
        self.y = top + title_h + self.mm(1.5)

        for i, item in enumerate(bag_items):
            self.render_item(item)
            if i < len(bag_items) - 1:
                self.dotted_line(gap_before=self.mm(1.2), gap_after=self.mm(1.2), fill=GRAY)
        self.y += self.mm(1.5)

        self.d.rectangle([left, top, right, self.y], outline=BLACK, width=border_w)
        self.y += self.mm(2)

    # ── finish ──────────────────────────────────────────────────────────
    def finish(self, tail_mm=8, min_mm=25):
        # Crop down to the actual content height (plus a small tail so the
        # cut isn't flush against the last line) -- this is what makes
        # auto-cut work. Never crop *up* against the canvas height: the
        # canvas itself is sized generously (see ABSOLUTE_MAX_MM) so a long
        # order is never truncated here.
        final_h = min(self.img.height, max(self.mm(min_mm), self.y + self.mm(tail_mm)))
        return self.img.crop((0, 0, self.w, int(final_h)))


# Hard safety ceiling for the canvas itself -- independent of the
# operator-configured "expected" length (e.g. 420mm). This only exists to
# stop a runaway/corrupted order from generating an unbounded image; no
# realistic order should ever get close to it, and reaching it is a bug to
# investigate, not something to design around.
ABSOLUTE_MAX_MM = 1500


def render_receipt_image(ctx, width_px=576, width_mm=72):
    """ctx is the dict shape produced by _receipt_context() in
    receipt_server.py: customer, prepare_by, order_num, branch, time_lbl,
    scheduled (bool), day_ar (str, possibly empty), items (already
    translated -- see translate_items()).

    Returns the cropped PIL image. However long the order actually is, the
    full receipt is always drawn and printed -- nothing is cut off. Compare
    the returned image's height against the operator's configured "expected"
    max length (in mm) if you want to warn that an order ran unusually long.

    Every size below is the original browser/CSS receipt's px value (the
    one the operator is used to) times 28/16 -- the scale that keeps the
    qty badge and item name at the 28px this renderer already used, so
    everything else (header 20px, branch 12px, TOTERS 18px, sched badge
    11px, day 20px, info label/value 11/13px, black bars 12px, note
    14px, bag title 15px, footer 13px) stays in the same proportion to
    them as the original design, instead of being eyeballed per element.
    """
    dpmm = width_px / width_mm
    hard_h = round(ABSOLUTE_MAX_MM * dpmm)
    c = ReceiptCanvas(width_px, hard_h, dpmm)

    c.center_text('كبة زمان', 900, 35)
    c.advance(c.mm(1))
    c.center_text(f'فرع {ctx["branch"]}', 600, 21)
    c.advance(c.mm(2))
    c.center_text('TOTERS', 900, 32, spacing=c.mm(1.1))
    if ctx.get('scheduled'):
        c.advance(c.mm(1.5))
        c.black_bar('مجدول', size=19, weight=700, pad=c.mm(1))
    if ctx.get('day_ar'):
        c.advance(c.mm(2))
        c.center_text(ctx['day_ar'], 900, 35)
    c.dashed_line(gap_before=c.mm(3), gap_after=c.mm(3))

    c.info_row('الزبون', ctx['customer'])
    c.info_row(ctx['time_lbl'], ctx['prepare_by'])
    c.info_row('رقم الطلب', f'#{ctx["order_num"]}')
    c.dashed_line(gap_before=c.mm(1.5))

    c.black_bar('الطلبية', size=21, weight=700, gap_before=c.mm(2), gap_after=c.mm(2))

    items = ctx['items']
    idx = 0
    is_first = True
    while idx < len(items):
        item = items[idx]
        if item.get('is_bag_header'):
            bag_size = item.get('bag_size', 0)
            bag_items = items[idx + 1: idx + 1 + bag_size]
            idx += 1 + bag_size
            c.bag_frame(item['arabic_name'], bag_items)
        else:
            if not is_first:
                c.dotted_line(gap_before=c.mm(1.2), gap_after=c.mm(1.2))
            c.render_item(item)
            idx += 1
        is_first = False

    c.dashed_line(gap_before=c.mm(4), gap_after=c.mm(3))
    c.center_text('شكراً!', 700, 23)

    return c.finish()
