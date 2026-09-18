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


def _draw_arabic_run(img, chunk, weight, size, x, baseline_y, fill, tracking=0):
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
        pen_x += pos.x_advance / 64 + tracking
        baseline_y -= pos.y_advance / 64
    return pen_x


class _Line:
    """Measures and draws one logical line of text that may mix Arabic
    and Latin/digit runs (e.g. "فرع dbayeh", "#1234", a plain Arabic
    phrase). Runs are laid out right-to-left in logical order, which is
    the correct visual result for the simple single-embedding-level
    strings a receipt actually contains (verified against real
    browser-rendered ground truth for both pure-Arabic and mixed lines)."""

    def __init__(self, draw, text, weight, size, tracking=0):
        self.draw = draw
        self.weight = weight
        self.size = size
        self.tracking = tracking  # CSS letter-spacing, in canvas px
        self.runs = _split_runs(text)
        self._pil_font = _font(weight, size)
        # Line box from the font's own hhea metrics, scaled unrounded --
        # this is what a browser does for `line-height:normal`, and it's
        # what the original receipt's line spacing was built on. Pillow's
        # getmetrics() rounds ascent and descent up separately instead,
        # which inflates every line by ~3% and compounds down the receipt.
        face = _ft_face(weight, size)
        upem = face.units_per_EM
        self.ascent = face.ascender / upem * size
        self.descent = -face.descender / upem * size
        self.line_h = round(self.ascent + self.descent)

    def width(self):
        return sum(self._run_width(is_ar, chunk) for is_ar, chunk in self.runs)

    def draw_right_aligned(self, img, right_x, top_y, fill=BLACK):
        """Draws with the line's right edge at right_x and its top at
        top_y (matching the old anchor='ma'/'ra' top-anchored behaviour).
        Returns the left edge x reached, and the y just past the line."""
        baseline_y = top_y + self.ascent
        x = right_x
        for is_ar, chunk in self.runs:
            x -= self._run_width(is_ar, chunk)
            if is_ar:
                _draw_arabic_run(img, chunk, self.weight, self.size, x, baseline_y, fill,
                                  tracking=self.tracking)
            elif self.tracking:
                cx = x
                for ch in chunk:
                    self.draw.text((cx, baseline_y), ch, font=self._pil_font, fill=fill, anchor='ls')
                    cx += self.draw.textlength(ch, font=self._pil_font) + self.tracking
            else:
                self.draw.text((x, baseline_y), chunk, font=self._pil_font, fill=fill, anchor='ls')
        return x, top_y + self.line_h

    def _run_width(self, is_ar, chunk):
        if is_ar:
            _, _, w = _shape_arabic(chunk, self.weight, self.size)
            # Tracking lands after every glyph, and shaping can merge
            # characters into fewer glyphs (ligatures), so count glyphs.
            if self.tracking:
                infos, _, _ = _shape_arabic(chunk, self.weight, self.size)
                w += self.tracking * len(infos)
            return w
        return self.draw.textlength(chunk, font=self._pil_font) + self.tracking * len(chunk)


def _bez(p0, p1, p2, steps=28):
    """Points along a quadratic bezier, for the curved edges of the cutlery
    icon -- Pillow draws polygons, not curves."""
    out = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        out.append((u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                    u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]))
    return out


class ReceiptCanvas:
    def __init__(self, width_px, max_height_px, dpmm):
        self.w = width_px
        self.dpmm = dpmm
        self.pad = self.mm(4)          # .r{padding:4mm}
        # Extra inset applied to whatever is nested one level deeper than the
        # receipt body -- i.e. the bag frame's own border, while its items are
        # being drawn. 0 at the top level.
        self.inset = 0
        self.img = Image.new('RGB', (width_px, max_height_px), WHITE)
        self.d = ImageDraw.Draw(self.img)
        self.y = self.mm(4)

    def mm(self, v):
        return round(v * self.dpmm)

    def advance(self, dy):
        self.y += dy

    # ── horizontal geometry ─────────────────────────────────────────────
    # An item box spans the full content width, but its *contents* (qty
    # badge, name, notes) sit inside its own 2mm padding -- .item{padding:
    # 2.5mm 2mm} -- so they're inset 2mm further than the bars and rules.
    def box_left(self):
        return self.pad + self.inset

    def box_right(self):
        return self.w - self.pad - self.inset

    def item_left(self):
        return self.box_left() + self.mm(2)

    def item_right(self):
        return self.box_right() - self.mm(2)

    # ── primitives ──────────────────────────────────────────────────────
    def center_text(self, text, weight, size, gap_after=0, fill=BLACK, spacing=0):
        line = _Line(self.d, text, weight, size, tracking=spacing)
        right_x = self.w / 2 + line.width() / 2
        _, self.y = line.draw_right_aligned(self.img, right_x, self.y, fill)
        self.y += gap_after

    # Rule metrics below are measured off the original CSS borders rendered
    # in a real browser at this canvas's density: a 2px dashed border comes
    # out 4px thick with 13px dashes and 8px gaps, a 1px dashed border 2px
    # thick with 6px dashes and 4px gaps, and a 1px dotted border as 2px
    # dots on a 4px pitch.
    def dashed_line(self, gap_before=0, gap_after=0, dash=None, gap=None, width=None, fill=BLACK):
        self.y += gap_before
        width = width or self.px(2)
        dash = dash or self.px(6)
        gap = gap or self.px(3.75)
        x, x2 = self.box_left(), self.box_right()
        while x < x2:
            self.d.line([(x, self.y), (min(x + dash, x2), self.y)], fill=fill, width=width)
            x += dash + gap
        self.y += width + gap_after

    def thin_dashed_line(self, gap_before=0, gap_after=0, fill=BLACK):
        self.dashed_line(gap_before=gap_before, gap_after=gap_after, fill=fill,
                          width=self.px(1), dash=self.px(3), gap=self.px(2))

    def dotted_line(self, gap_before=0, gap_after=0, dot=None, gap=None, width=None, fill=BLACK):
        self.y += gap_before
        width = width or self.px(1)
        dot = dot or self.px(1)
        gap = gap or self.px(1)
        x, x2 = self.box_left(), self.box_right()
        while x < x2:
            self.d.line([(x, self.y), (min(x + dot - 1, x2), self.y)], fill=fill, width=width)
            x += dot + gap
        self.y += width + gap_after

    def px(self, css_px):
        """A CSS px from the original stylesheet, in canvas pixels. CSS
        resolves px against a fixed 96dpi reference; this canvas is
        normally 203.2dpi (8 dots/mm)."""
        return max(1, round(css_px * self.dpmm * 25.4 / 96))

    def black_bar(self, text, size=26, weight=700, pad=None, gap_before=0, gap_after=0):
        self.y += gap_before
        pad = self.mm(1.5) if pad is None else pad
        line = _Line(self.d, text, weight, size)
        bar_h = line.line_h + 2 * pad
        self.d.rectangle([self.box_left(), self.y, self.box_right(), self.y + bar_h], fill=BLACK)
        right_x = self.w / 2 + line.width() / 2
        line.draw_right_aligned(self.img, right_x, self.y + pad, WHITE)
        self.y += bar_h + gap_after

    def info_row(self, label, value, label_size=23, value_size=28):
        lline = _Line(self.d, label, 400, label_size)
        vline = _Line(self.d, str(value), 700, value_size)
        _, y_after_l = lline.draw_right_aligned(self.img, self.box_right(), self.y, BLACK)
        left_x, y_after_v = vline.draw_right_aligned(self.img, self.box_left() + vline.width(), self.y, BLACK)
        self.y += max(y_after_l, y_after_v) - self.y + self.mm(1.5)

    def big_time(self, time_text, gap_before=0):
        """The prepare-by time, centered and big, sitting directly under the
        Arabic day. It used to be one of three small info rows between the
        customer's name and the order number, where the kitchen kept reading
        straight past it -- the day and the time are what they act on, so
        they read as one block at the top of the receipt."""
        self.y += gap_before
        # A parsed time ("11:30 AM", the widest shape it takes, ~400px of
        # the 512px content width) still fits at 96, but the raw fallback
        # can be anything Toters wrote there, so step the size down until it
        # does rather than letting it run off the paper.
        size = 96
        max_w = self.box_right() - self.box_left()
        while size > 26 and _Line(self.d, time_text, 900, size).width() > max_w:
            size -= 2
        self.center_text(time_text, 900, size)

    # The three pieces and the gap between them, as fractions of the icon's
    # height -- a fork, a knife and a spoon standing side by side.
    _CUTLERY_PARTS = (('fork', 0.22), ('knife', 0.20), ('spoon', 0.20))
    _CUTLERY_GAP = 0.10

    def _cutlery_icon_w(self, h):
        parts = self._CUTLERY_PARTS
        return sum(f for _, f in parts) * h + self._CUTLERY_GAP * h * (len(parts) - 1)

    # Supersampling factor the icon's geometry is laid out at before it's
    # scaled down onto the receipt. Drawn straight at final size, a 12mm
    # icon's curves land on ~100 pixels and come out visibly faceted; drawn
    # 8x larger and resampled, the outline follows the real curve.
    _CUTLERY_SS = 8

    @staticmethod
    def _cutlery_handle(d, cx, y0, y1, w0, w1, fill):
        """A handle narrowing from w0 down to w1, with a rounded foot."""
        d.polygon([(cx - w0 / 2, y0), (cx + w0 / 2, y0),
                   (cx + w1 / 2, y1), (cx - w1 / 2, y1)], fill=fill)
        d.ellipse([cx - w1 / 2, y1 - w1 / 2, cx + w1 / 2, y1 + w1 / 2], fill=fill)

    @classmethod
    def _cutlery_fork(cls, d, cx, top, h, w, fill, hole, tines=4):
        # The head is filled solid and the gaps between the tines are cut back
        # out: drawn as four separate bars they come out a pixel or two apart
        # once scaled down, which a thermal printer closes into one block.
        d.rounded_rectangle([cx - w / 2, top + h * 0.02, cx + w / 2, top + h * 0.34],
                            radius=w * 0.14, fill=fill)
        gap = w * 0.13
        for k in range(1, tines):
            x = cx - w / 2 + k * w / tines
            d.rectangle([x - gap / 2, top - 1, x + gap / 2, top + h * 0.27], fill=hole)
        # The shoulders curve in from the head to meet the handle.
        d.polygon(
            _bez((cx - w / 2, top + h * 0.30), (cx - w * 0.30, top + h * 0.40), (cx - h * 0.035, top + h * 0.46)) +
            list(reversed(_bez((cx + w / 2, top + h * 0.30), (cx + w * 0.30, top + h * 0.40), (cx + h * 0.035, top + h * 0.46)))),
            fill=fill)
        cls._cutlery_handle(d, cx, top + h * 0.44, top + h * 0.97, h * 0.07, h * 0.055, fill)

    @classmethod
    def _cutlery_knife(cls, d, cx, top, h, w, fill, hole):
        # Straight back on the left, the belly curving out to the right, and a
        # rounded tip -- the handle carries straight on down from the back.
        x_back = cx - w / 2
        cx_h = cx - w * 0.06
        hw = h * 0.07
        y_top, y_bot = top + h * 0.03, top + h * 0.50
        belly = _bez((x_back + w * 0.12, y_top), (cx + w * 0.55, top + h * 0.20),
                     (cx_h + hw / 2, y_bot))
        d.polygon([(x_back, y_top + w * 0.14), (x_back, top + h * 0.44),
                   (cx_h - hw / 2, y_bot)] + list(reversed(belly)), fill=fill)
        d.ellipse([x_back, y_top, x_back + w * 0.28, y_top + w * 0.28], fill=fill)
        cls._cutlery_handle(d, cx_h, y_bot - 1, top + h * 0.97, hw, h * 0.055, fill)

    @classmethod
    def _cutlery_spoon(cls, d, cx, top, h, w, fill, hole):
        # An egg-shaped bowl: widest below its middle, drawn as two curves per
        # side so it necks into the handle instead of stopping at an ellipse.
        y0, y_wide = top + h * 0.02, top + h * 0.21
        side = []
        for s in (1, -1):
            # Both controls sit on the bowl's widest line, so the two curves
            # meet with the same tangent and the join doesn't show as a corner.
            half = (_bez((cx, y0), (cx + s * w / 2, y0 + h * 0.03), (cx + s * w / 2, y_wide)) +
                    _bez((cx + s * w / 2, y_wide), (cx + s * w / 2, top + h * 0.33),
                         (cx + s * h * 0.035, top + h * 0.44)))
            side.append(half if s == 1 else list(reversed(half)))
        d.polygon(side[0] + side[1], fill=fill)
        cls._cutlery_handle(d, cx, top + h * 0.42, top + h * 0.97, h * 0.07, h * 0.055, fill)

    def _cutlery_icon(self, right_x, top, h):
        """Fork, knife and spoon drawn as plain filled shapes, sized to h and
        ending at right_x. Nothing font-based: the Arabic font carries no
        cutlery glyph, and an emoji would print as a box on a thermal
        printer.

        The three pieces are laid out on their own supersampled mask and
        scaled down onto the receipt. The printer driver thresholds whatever
        it is handed into pure black and white (escpos converts to mode "1"),
        so the mask is thresholded here too rather than pasted with soft
        edges -- what survives to paper is the accurate silhouette, not the
        anti-aliasing."""
        ss = self._CUTLERY_SS
        w = self._cutlery_icon_w(h)
        mask = Image.new('L', (round(w * ss), round(h * ss)), 0)
        md = ImageDraw.Draw(mask)
        draw = {'fork': self._cutlery_fork, 'knife': self._cutlery_knife,
                'spoon': self._cutlery_spoon}
        x = 0
        for name, frac in self._CUTLERY_PARTS:
            piece_w = frac * h * ss
            draw[name](md, x + piece_w / 2, 0, h * ss, piece_w, 255, 0)
            x += piece_w + self._CUTLERY_GAP * h * ss
        mask = mask.resize((round(w), round(h)), Image.LANCZOS).point(lambda v: 255 if v >= 128 else 0)
        self.img.paste(BLACK, (round(right_x - w), round(top)), mask)

    def cutlery_mark(self, gap_before=0, gap_after=0, height_mm=12):
        """The cutlery icon on its own, centered. Only called for an order
        that gets cutlery -- an order carrying Toters' "Please do not send
        cutlery" note prints nothing here at all."""
        h = self.mm(height_mm)
        w = self._cutlery_icon_w(h)
        top = self.y + gap_before
        self._cutlery_icon((self.w + w) / 2, top, h)
        self.y = top + h + gap_after

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
                line_h = line.line_h
            line.draw_right_aligned(self.img, right_x, self.y, fill)
            self.y += line_h
        return len(lines)

    def qty_badge(self, qty, name, qty_size=34, name_size=34):
        # .qty{min-width:8mm;padding:0 2mm;border-radius:2px} sitting in a
        # flex row with the name, so the badge is as tall as the row's line
        # box and the two are 2mm apart (.row{gap:2mm}).
        # The qty is usually a number ("2", "1KG"), but a tray order puts an
        # Arabic size label in there instead ("صينية وسط"), so it goes through
        # _Line like every other string on the receipt -- Pillow's own text()
        # can't shape or reverse Arabic without libraqm (see module docstring).
        qty_line = _Line(self.d, str(qty), 900, qty_size)
        qty_w = qty_line.width()
        badge_w = max(self.mm(8), qty_w + 2 * self.mm(2))
        badge_h = _Line(self.d, '', 700, name_size).line_h
        top = self.y
        left = self.item_right() - badge_w
        self.d.rounded_rectangle([left, top, left + badge_w, top + badge_h],
                                  radius=self.px(2), fill=BLACK)
        qty_line.draw_right_aligned(self.img, left + (badge_w + qty_w) / 2,
                                     top + (badge_h - qty_line.line_h) / 2, WHITE)

        right_x = left - self.mm(2)
        max_w = right_x - self.item_left()
        self.wrapped_rtl(name, 700, name_size, right_x, max_w)
        self.y = max(self.y, top + badge_h)

    def note(self, text, size=30):
        # .note{margin-right:6mm;border-right:3px;padding-right:1.5mm}
        note_right = self.item_right() - self.mm(6)
        bar_w = self.px(3)
        right_x = note_right - bar_w - self.mm(1.5)
        max_w = right_x - self.item_left()
        top = self.y
        self.wrapped_rtl(text, 700, size, right_x, max_w)
        self.d.rectangle([note_right - bar_w, top, note_right, self.y], fill=BLACK)

    def render_item(self, item):
        self.y += self.mm(2.5)
        self.qty_badge(item.get('qty', ''), item.get('arabic_name', ''))
        for c in item.get('comments') or []:
            if not c:
                continue
            self.advance(self.mm(1))
            self.note(c)
        self.y += self.mm(2.5)

    def bag_frame(self, title, bag_items, comments=None):
        # .bag-frame{border:2.5px solid;border-radius:3px;margin:3mm 0 2mm},
        # with the title bar and the items sitting inside that border -- so
        # while its items are drawn, everything is inset by the border.
        self.y += self.mm(3)
        left, right = self.box_left(), self.box_right()
        border_w = self.px(2)   # Chrome computes the declared 2.5px down to 2px
        top = self.y

        line = _Line(self.d, title, 900, 32, tracking=self.px(2))
        title_h = line.line_h + 2 * self.mm(2.5)
        self.d.rectangle([left + border_w, top + border_w, right - border_w, top + title_h], fill=BLACK)
        right_x = (left + right) / 2 + line.width() / 2
        line.draw_right_aligned(self.img, right_x, top + border_w + self.mm(2.5), WHITE)
        self.y = top + title_h

        self.inset += border_w
        # A comment left on the combo itself is about the whole bag, so it
        # prints once under the title instead of against one component.
        bag_notes = [c for c in (comments or []) if c]
        for c in bag_notes:
            self.y += self.mm(2)
            self.note(c)
        if bag_notes:
            self.y += self.mm(2)
            self.dotted_line(fill=GRAY)
        for i, item in enumerate(bag_items):
            self.render_item(item)
            if i < len(bag_items) - 1:
                self.dotted_line(fill=GRAY)
        self.inset -= border_w

        self.d.rounded_rectangle([left, top, right, self.y], radius=self.px(3),
                                  outline=BLACK, width=border_w)
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
    receipt_server.py: customer, prepare_by, prepare_time, order_num,
    branch, time_lbl, scheduled (bool), day_ar (str, possibly empty),
    cutlery (bool, defaults to True when absent),
    items (already translated -- see translate_items()).

    Returns the cropped PIL image. However long the order actually is, the
    full receipt is always drawn and printed -- nothing is cut off. Compare
    the returned image's height against the operator's configured "expected"
    max length (in mm) if you want to warn that an order ran unusually long.

    Every size below is the original browser/CSS receipt's px value (the
    one the operator is used to -- header 20px, branch 12px, TOTERS 18px,
    sched badge 11px, day 20px, info label/value 11/13px, black bars
    12px, qty/item name 16px, note 14px, bag title 15px, footer 13px)
    times 203.2/96: CSS renders those px at a fixed 96dpi reference
    regardless of screen, and this canvas is 8 dots/mm (203.2dpi) at the
    default width_px/width_mm, so that ratio is what actually reproduces
    the original's physical size on the printed paper -- verified by
    rendering the original CSS in a real browser at matching dpi and
    reading back each element's computed font-size. (A first pass here
    scaled everything by 28/16, anchored on a qty-badge size that had
    itself only been eyeballed -- right proportions, wrong absolute
    scale, so everything came out a uniform ~17% too small.)
    """
    dpmm = width_px / width_mm
    hard_h = round(ABSOLUTE_MAX_MM * dpmm)
    c = ReceiptCanvas(width_px, hard_h, dpmm)

    c.center_text('كبة زمان', 900, 42)
    c.advance(c.mm(1))
    c.center_text(f'فرع {ctx["branch"]}', 600, 25)
    c.advance(c.mm(2))
    c.center_text('TOTERS', 900, 38, spacing=c.px(3))
    if ctx.get('scheduled'):
        c.advance(c.mm(1.5))
        c.black_bar('مجدول', size=23, weight=700, pad=c.mm(1))
    if ctx.get('day_ar'):
        c.advance(c.mm(2))
        c.center_text(ctx['day_ar'], 900, 42)
    # The day, then the time right under it -- prepare_time is the time half
    # of prepare_by. When the "Prepare by" text didn't parse (an ASAP order,
    # an unfamiliar format) there's no day either, so the raw string prints
    # here instead and nothing is lost.
    time_text = ctx.get('prepare_time') or ctx.get('prepare_by') or ''
    if time_text:
        c.big_time(time_text, gap_before=c.mm(1.5) if ctx.get('day_ar') else c.mm(2))
    c.dashed_line(gap_before=c.mm(3), gap_after=c.mm(3))

    c.info_row('الزبون', ctx['customer'])
    c.info_row('رقم الطلب', f'#{ctx["order_num"]}')
    # .info's rule is a 1px dashed border, thinner than .hd's/.ft's 2px ones
    c.thin_dashed_line(gap_before=c.mm(1.5))

    # Cutlery unless the order asked for none -- see _cutlery() in extract.py.
    if ctx.get('cutlery', True) is not False:
        c.cutlery_mark(gap_before=c.mm(2.5))

    c.black_bar('الطلبية', size=25, weight=700, gap_before=c.mm(2))

    items = ctx['items']
    idx = 0
    while idx < len(items):
        item = items[idx]
        if item.get('is_bag_header'):
            bag_size = item.get('bag_size', 0)
            bag_items = items[idx + 1: idx + 1 + bag_size]
            idx += 1 + bag_size
            c.bag_frame(item['arabic_name'], bag_items, item.get('comments'))
        else:
            c.render_item(item)
            # .item's dotted bottom border, on every item including the
            # last: `.item:last-child{border-bottom:none}` never matches at
            # this level, since the footer div follows the items. (It does
            # match inside a bag frame, which bag_frame() handles.)
            c.dotted_line()
            idx += 1

    c.dashed_line(gap_before=c.mm(4), gap_after=c.mm(3))
    c.center_text('شكراً!', 700, 28)

    return c.finish()
