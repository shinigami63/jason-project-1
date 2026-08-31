"""Render a Kebbet Zamen receipt directly to a raster image for ESC/POS
thermal printing, replacing the old "open HTML in the browser and print"
flow. Drawing everything ourselves (instead of relying on a browser) means
we can trim the image to the receipt's actual content height, so the paper
only feeds out as far as the last printed line plus a small tail -- not the
full configured maximum length.
"""
import os
import sys

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (150, 150, 150)


def _shape(text):
    """Reshapes Arabic letters into their joined presentation forms and
    reorders the string into visual (left-to-right rendering) order via
    the Unicode bidi algorithm, so it can be drawn with a plain text()
    call. We do this ourselves in pure Python instead of using Pillow's
    direction=/language=/features= kwargs (which route through raqm) --
    raqm is a native library that a PyInstaller-frozen exe doesn't
    reliably bundle, which throws "setting text direction, language or
    font features is not supported without libraqm" at print time on a
    real install even though it worked fine in dev. Safe no-op on
    plain ASCII text (numbers, "TOTERS", English times/names)."""
    return get_display(arabic_reshaper.reshape(text))


def _fonts_dir():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'fonts')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')


# Amiri instead of a variable-weight font like Cairo: it's one of the few
# open Arabic faces whose cmap fully covers the legacy Arabic Presentation
# Forms codepoints that arabic_reshaper substitutes in (see _shape() above)
# -- most modern Arabic webfonts, Cairo included, only shape correctly
# through an OpenType engine like harfbuzz/raqm and render as broken/missing
# glyphs otherwise. Amiri only ships Regular/Bold, no Black, so any
# requested weight >=700 maps to Bold and everything else to Regular.
_FONT_FILES = {False: 'Amiri-Regular.ttf', True: 'Amiri-Bold.ttf'}

_FONT_CACHE = {}


def _font(weight, size):
    bold = weight >= 700
    key = (bold, size)
    f = _FONT_CACHE.get(key)
    if f is None:
        f = ImageFont.truetype(os.path.join(_fonts_dir(), _FONT_FILES[bold]), size)
        _FONT_CACHE[key] = f
    return f


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
        font = _font(weight, size)
        if spacing:
            self._center_spaced(text, font, spacing, fill)
        else:
            text = _shape(text)
            bbox = self.d.textbbox((0, 0), text, font=font)
            self.d.text((self.w / 2, self.y), text, font=font, fill=fill, anchor='ma')
            # anchor='ma' positions self.y at the font's ascender line, which
            # sits above the glyphs' visual top -- advance by the bbox's
            # bottom offset (not its height) or the next element overlaps.
            self.y += bbox[3]
        self.y += gap_after

    def _center_spaced(self, text, font, spacing, fill):
        widths = [self.d.textlength(ch, font=font) for ch in text]
        total = sum(widths) + spacing * (len(text) - 1)
        x = (self.w - total) / 2
        bbox = self.d.textbbox((0, 0), text, font=font)
        for ch, wch in zip(text, widths):
            self.d.text((x, self.y), ch, font=font, fill=fill, anchor='la')
            x += wch + spacing
        self.y += bbox[3]

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
        font = _font(weight, size)
        text = _shape(text)
        bbox = self.d.textbbox((0, 0), text, font=font)
        bar_h = (bbox[3] - bbox[1]) + 2 * pad
        self.d.rectangle([self.pad, self.y, self.w - self.pad, self.y + bar_h], fill=BLACK)
        self.d.text((self.w / 2, self.y + bar_h / 2), text, font=font, fill=WHITE, anchor='mm')
        self.y += bar_h + gap_after

    def info_row(self, label, value, label_size=22, value_size=26):
        lf, vf = _font(400, label_size), _font(700, value_size)
        label, value = _shape(label), _shape(str(value))
        lb = self.d.textbbox((0, 0), label, font=lf)
        vb = self.d.textbbox((0, 0), value, font=vf)
        self.d.text((self.w - self.pad, self.y), label, font=lf, fill=BLACK, anchor='ra')
        self.d.text((self.pad, self.y), value, font=vf, fill=BLACK, anchor='la')
        # anchor='.a' draws relative to the ascender line, not the glyph top
        # -- advance past whichever bbox's *bottom* offset extends further.
        self.y += max(lb[3], vb[3]) + self.mm(1.5)

    def wrapped_rtl(self, text, font, right_x, max_width, fill=BLACK):
        # Reshape (letter-joining forms) but don't reorder yet -- word-wrap
        # needs to walk the text in logical order, same as the original
        # string. Each finished line is bidi-reordered on its own right
        # before drawing, once its content is fixed.
        words = arabic_reshaper.reshape(text).split(' ')
        lines, cur = [], ''
        for word in words:
            trial = (cur + ' ' + word).strip()
            if not cur or self.d.textlength(trial, font=font) <= max_width:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        probe = self.d.textbbox((0, 0), 'Aأج', font=font)
        line_h = (probe[3] - probe[1]) * 1.3
        for line in lines:
            self.d.text((right_x, self.y), get_display(line), font=font, fill=fill, anchor='ra')
            self.y += line_h
        return len(lines)

    def qty_badge(self, qty, name, qty_size=28, name_size=28):
        qf, nf = _font(900, qty_size), _font(700, name_size)
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
        self.wrapped_rtl(name, nf, right_x, max_w)
        self.y = max(self.y, top + badge_h)

    def note(self, text, size=22):
        f = _font(700, size)
        indent = self.mm(6)
        right_x = self.w - self.pad - indent
        max_w = right_x - self.pad
        top = self.y
        self.wrapped_rtl(text, f, right_x, max_w)
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

        title_font = _font(900, 26)
        title = _shape(title)
        tb = self.d.textbbox((0, 0), title, font=title_font)
        title_h = (tb[3] - tb[1]) + 2 * self.mm(2.5)
        self.d.rectangle([left, top, right, top + title_h], fill=BLACK)
        self.d.text(((left + right) / 2, top + title_h / 2), title, font=title_font, fill=WHITE,
                    anchor='mm')
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
    """
    dpmm = width_px / width_mm
    hard_h = round(ABSOLUTE_MAX_MM * dpmm)
    c = ReceiptCanvas(width_px, hard_h, dpmm)

    c.center_text('كبة زمان', 900, 42)
    c.advance(c.mm(1))
    c.center_text(f'فرع {ctx["branch"]}', 700, 22)
    c.advance(c.mm(2))
    c.center_text('TOTERS', 900, 34, spacing=c.mm(1.1))
    if ctx.get('scheduled'):
        c.advance(c.mm(1.5))
        c.black_bar('مجدول', size=20, weight=700, pad=c.mm(1))
    if ctx.get('day_ar'):
        c.advance(c.mm(2))
        c.center_text(ctx['day_ar'], 900, 36)
    c.dashed_line(gap_before=c.mm(3), gap_after=c.mm(3))

    c.info_row('الزبون', ctx['customer'])
    c.info_row(ctx['time_lbl'], ctx['prepare_by'])
    c.info_row('رقم الطلب', f'#{ctx["order_num"]}')
    c.dashed_line(gap_before=c.mm(1.5))

    c.black_bar('الطلبية', size=22, weight=700, gap_before=c.mm(2), gap_after=c.mm(2))

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
    c.center_text('شكراً!', 700, 24)

    return c.finish()
