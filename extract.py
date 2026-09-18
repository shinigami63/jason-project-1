import re

SIZE_PATTERN = re.compile(r'^\d+\s*(G|g|ML|ml|kg|KG|pieces?|Piece|piece|gr|persons?)$', re.IGNORECASE)
WEIGHT_PATTERN = re.compile(r'^(\d+)\s*(G|g|gr|KG|kg)$', re.IGNORECASE)

QUANTITY_TYPES = {'quantity', 'qty', 'amount', 'count', 'number'}

# A customer comment on a line shows up as "message<comment>" -- the Toters
# message icon ligature immediately followed by the raw note.
COMMENT_PATTERN = re.compile(r'^message(.+)$')

# Cutlery rides with every order unless the customer ticked "no cutlery" on
# Toters, which shows up as one fixed note on the page -- "message" (the
# message icon ligature) followed by "Please do not send cutlery". That exact
# sentence is the whole signal: when it's there the receipt leaves the cutlery
# icon off, otherwise the icon prints.
NO_CUTLERY_PATTERN = re.compile(r'please\s+do\s+not\s+send\s+cutlery', re.IGNORECASE)

RAW_MEAT_ITEMS = {
    "raw kibbeh", "raw kebbeh", "kebbeh nayeh", "kibbeh nayeh",
    "raw tenderloin", "raw habra", "raw orfali", "raw liver",
    "raw kafta", "raw fitle", "raw meat"
}

COMBOS = {
    "kebbeh zghertawiyeh combo": {
        # kebbeh is a customer choice (Fat / Meat / Labneh)
        "kebbeh": 1.0, "salad": 0.5, "mezza": 0.5, "drink": 1.0, "water": 1.0,
    },
    "taouk combo": {
        # taouk and fries are fixed; only salad/mezza/drink are customer choices
        "salad": 0.5, "mezza": 0.5, "drink": 1.0, "water": 1.0,
    },
    "meat combo": {
        "salad": 0.5, "mezza": 0.5, "drink": 1.0, "water": 1.0,
    },
    "kafta combo": {
        "salad": 0.5, "mezza": 0.5, "drink": 1.0, "water": 1.0,
    },
    "mixed grill combo": {
        "salad": 0.5, "mezza": 0.5, "drink": 1.0, "water": 1.0,
    },
    "kebbe lovers box": {
        # all 3 kebbeh types are fixed; only salad/mezza are customer choices
        "salad": 1.0, "mezza": 1.0,
    },
    "family sharing combo": {
        # mixed grill and fries are fixed; salad/mezza/kebbeh type are choices
        "salad": 2.0, "mezza": 2.0, "kebbeh": 2.0,
    },
    "vegan combo": {
        # pumpkin kebbeh and fries are fixed; only salad/mezza/drink are choices
        "salad": 0.5, "mezza": 0.5, "drink": 1.0, "water": 1.0,
    },
    "kebbe tray combo": {
        # cucumber is fixed; kebbeh type (onions/meat stuffed) and mezza/drink are choices
        "kebbeh": 1.0, "mezza": 0.5, "drink": 1.0, "water": 1.0,
    },
}

# Biscuits & Raha is also sold on its own, where it prints with its plain
# dictionary translation ("بسكوت وراحة"). The two pieces that come inside a
# combo are a different line for the kitchen, so they get their own
# dictionary entry (editable on the Dictionary page like any other word).
BISCUITS_RAHA_COMBO_KEY = 'Biscuits & Raha (Combo)'
BISCUITS_RAHA_COMBO_AR = 'راحة وبسكوت حبتين'

COMBOS_WITH_BISCUITS_RAHA = {
    "kebbeh zghertawiyeh combo",
    "taouk combo",
    "meat combo",
    "kafta combo",
    "mixed grill combo",
    "vegan combo",
    "kebbe tray combo",
}

# Fixed items always included in a combo that never appear as "Choose X > Y"
# on the Toters page. Listed first so they print at the top of each bag.
COMBO_FIXED_ITEMS = {
    "taouk combo": [
        {"name": "Taouk",        "portion": 1.0, "category": "Grills"},
        {"name": "French Fries", "portion": 0.5, "category": "Sides"},
    ],
    "meat combo": [
        {"name": "Grilled Meat", "portion": 1.0, "category": "Grills"},
        {"name": "French Fries", "portion": 0.5, "category": "Sides"},
    ],
    "kafta combo": [
        {"name": "Grilled Kafta", "portion": 1.0, "category": "Grills"},
        {"name": "French Fries",  "portion": 0.5, "category": "Sides"},
    ],
    "mixed grill combo": [
        {"name": "Mixed Grills", "portion": 1.0, "category": "Grills"},
        {"name": "French Fries", "portion": 0.5, "category": "Sides"},
    ],
    "kebbe lovers box": [
        {"name": "Kebbeh Zghertawiye (Fat)",    "portion": 1.0, "category": "Kebbeh"},
        {"name": "Kebbeh Zghertawiye (Meat)",   "portion": 1.0, "category": "Kebbeh"},
        {"name": "Kebbeh Zghertawiye (Labneh)", "portion": 1.0, "category": "Kebbeh"},
        {"name": "French Fries",                "portion": 1.0, "category": "Sides"},
    ],
    "family sharing combo": [
        {"name": "Mixed Grills", "portion": 1.0, "qty_label": "1KG", "category": "Grills"},
        {"name": "French Fries", "portion": 2.0, "category": "Sides"},
    ],
    "vegan combo": [
        {"name": "Pumpkin Kebbeh (4 pcs)", "portion": 1.0, "category": "Kebbeh"},
        {"name": "French Fries",           "portion": 0.5, "category": "Sides"},
    ],
    "kebbe tray combo": [
        {"name": "Cucumber With Laban", "portion": 0.5, "category": "Mezza"},
    ],
}

# Maps the "type" keyword used in a combo's customer-choice lines (e.g.
# "Choose Two Salads > ...") to the category label used in item reports.
CHOICE_TYPE_CATEGORIES = {
    "kebbeh": "Kebbeh",
    "salad":  "Salads",
    "mezza":  "Mezza",
    "drink":  "Beverages",
    "water":  "Water",
}


def _format_qty(total):
    whole = int(total)
    frac  = total - whole
    if abs(frac - 0.5) < 0.01:
        return '½' if whole == 0 else f'{whole}½'
    return str(whole) if abs(frac) < 0.01 else str(total)


def parse_order(text):
    text = re.sub(r'\r\n', '\n', text)
    lines = [l.strip() for l in text.split('\n')]
    return {
        'scheduled': 'SCHEDULED' in text,
        'customer':  _customer(text),
        'order_num': _order_num(text),
        'prepare_by': _prepare_by(text),
        'cutlery':   _cutlery(text),
        'items':     _items(lines)
    }

def _cutlery(text):
    """True when cutlery goes out with the order -- i.e. the page doesn't
    carry Toters' "Please do not send cutlery" note. An order that says
    nothing about cutlery gets cutlery."""
    return not NO_CUTLERY_PATTERN.search(text)

def _customer(text):
    m = re.search(r'Customer\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)', text)
    return m.group(1).strip().title() if m else 'Unknown'

def _order_num(text):
    m = re.search(r'Order#\s*\n?([0-9\-]+)', text)
    return m.group(1) if m else ''

def _prepare_by(text):
    m = re.search(r'Prepare by\s*\n?([\w]+\s+\d+,\s*\d+:\d+\s*(?:AM|PM))', text)
    return m.group(1).strip() if m else ''

_ARABIC_NUMS = ['١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩', '١٠']

def _item_comments(lines, start_i):
    """Customer comments belonging to the item that starts at start_i, kept
    verbatim (never translated). The block ends at the next item's "Qty" or at
    the order's "Additional Charge" section, whichever comes first."""
    out = []
    for j in range(start_i, len(lines)):
        if lines[j] in ('Qty', 'Additional Charge'):
            break
        m = COMMENT_PATTERN.match(lines[j])
        if m and m.group(1).strip():
            out.append(m.group(1).strip())
    return out

def _make_combo_item(name, portion, category='Other'):
    return {
        'qty':              _format_qty(portion),
        'name':             name,
        'variant':          None,
        'add_ons':          [],
        'original_add_ons': [],
        'category':         category,
        'is_raw':           False,
        'arabic_name':      name,
    }

def _parse_combo_components(lines, start_i, combo_name, combo_qty_str):
    try:
        combo_qty = int(float(combo_qty_str))
    except (TypeError, ValueError):
        combo_qty = 1

    combo_name_lower = combo_name.lower().strip()
    combo_def = COMBOS.get(combo_name_lower, {})

    # A comment on a combo ("Pls send cutlery and bread") applies to the whole
    # bag, not to one of its components, so it rides on the bag header and
    # prints once under the bag title. Comments left on individual choice lines
    # land in the same block on the page and are treated the same way.
    comments = _item_comments(lines, start_i)

    # Build the item list for a single bag
    per_bag = []

    # 1. Fixed items always in this combo (not selectable by customer on Toters)
    for fixed in COMBO_FIXED_ITEMS.get(combo_name_lower, []):
        item = _make_combo_item(fixed['name'], fixed['portion'], fixed.get('category') or 'Other')
        if 'qty_label' in fixed:
            item['qty'] = fixed['qty_label']
        per_bag.append(item)

    # 2. Customer-chosen items (Choose X > Y lines)
    for j in range(start_i, len(lines)):
        if lines[j] in ('Qty', 'Additional Charge'):
            break
        if COMMENT_PATTERN.match(lines[j]):
            # Collected above; a comment is never read as a choice line.
            continue
        m = re.search(r'Choose\s+([\w\s]+?)\s*[>:]\s*(.+)', lines[j])
        if not m:
            continue
        raw_type = m.group(1).strip().lower()
        # Handle "Two Salads" → "salad", "Two Mezza" → "mezza", "Two Kebbeh" → "kebbeh"
        this_type = raw_type.split()[-1]
        if combo_def.get(this_type) is None and this_type.endswith('s'):
            this_type = this_type[:-1]
        item_name = m.group(2).strip()

        portion = combo_def.get(this_type, None)
        if portion is None:
            portion = 1.0
            if j > 0:
                qm = re.match(r'^(\d+(?:\.\d+)?)\s*x', lines[j - 1], re.IGNORECASE)
                if qm:
                    portion = float(qm.group(1))

        item_category = CHOICE_TYPE_CATEGORIES.get(this_type, this_type.title() if this_type else 'Other')
        per_bag.append(_make_combo_item(item_name, portion, item_category))

    # 3. Biscuits & Raha (always appended last for applicable combos)
    if combo_name_lower in COMBOS_WITH_BISCUITS_RAHA:
        per_bag.append({
            'qty':              '1',
            'name':             'Biscuits & Raha',
            'variant':          None,
            'add_ons':          [],
            'original_add_ons': [],
            'category':         'Desserts Zamen',
            'is_raw':           False,
            # The kitchen preps the combo portion differently from a
            # Biscuits & Raha ordered on its own, so it prints under its own
            # Arabic wording. 'name' stays the plain menu name (that's what
            # the sales reports group on); 'dict_key' is what the dictionary
            # is looked up by -- see translate_items() in receipt_server.py.
            'dict_key':         BISCUITS_RAHA_COMBO_KEY,
            'arabic_name':      BISCUITS_RAHA_COMBO_AR,
        })

    # Always wrap in a bag frame — even qty=1 gets a "كيس" frame.
    # Single combos use plain "كيس"; multiples use "كيس ١", "كيس ٢", etc.
    # bag_size tells the receipt renderer exactly how many items follow
    # this header so it can draw a tight frame around each bag.
    result = []
    for n in range(1, combo_qty + 1):
        if combo_qty == 1:
            ar_label = 'كيس'
        else:
            ar_num = _ARABIC_NUMS[n - 1] if n <= len(_ARABIC_NUMS) else str(n)
            ar_label = f'كيس {ar_num}'
        result.append({
            'qty':              '',
            'name':             f'Bag {n}',
            'arabic_name':      ar_label,
            'variant':          None,
            'add_ons':          [],
            'original_add_ons': [],
            'category':         'Combos',
            'is_raw':           False,
            'is_bag_header':    True,
            'bag_size':         len(per_bag),
            'comments':         list(comments),
        })
        result.extend(per_bag)
    return result

def _items(lines):
    items = []
    i = 0
    while i < len(lines):
        if lines[i] == 'Qty':
            i += 1
            qty = None
            while i < len(lines) and not qty:
                m = re.match(r'_*(\d+)_*', lines[i])
                if m and lines[i].replace('_','').isdigit():
                    qty = m.group(1)
                i += 1
            if not qty:
                continue

            while i < len(lines) and lines[i].lower() == 'x':
                i += 1

            content = []
            category = ''
            while i < len(lines):
                l = lines[i]
                if re.match(r'^in\s+\w', l):
                    category = l[3:].strip()
                    i += 1
                    break
                if re.match(r'^LBP', l): break
                if 'find_replace' in l: break
                if l == 'Qty': break
                if l == 'Additional Charge': break
                if l: content.append(l)
                i += 1

            if not content:
                continue

            if SIZE_PATTERN.match(content[0]):
                variant = content[0]
                name_parts = content[1:]
            else:
                variant = None
                name_parts = content

            name = ' '.join(name_parts).strip()
            if not name:
                continue

            # Combo: expand into individual components
            if 'combo' in category.lower():
                items.extend(_parse_combo_components(lines, i, name, qty))
                continue

            pref_type = None
            pref = None
            add_ons_list = []
            # Customer comments are kept verbatim — no translation — as their
            # own lines under the item.
            comments_list = _item_comments(lines, i)
            has_yogurt_side = False
            for j in range(i, len(lines)):
                if lines[j] in ('Qty', 'Additional Charge'):
                    break
                if COMMENT_PATTERN.match(lines[j]):
                    # Collected above; a comment is never read as an add-on.
                    continue
                m = re.search(r'(?:Choose|Add)\s+([\w\s]+?)\s*[>:]\s*(.+)', lines[j])
                if not m:
                    continue
                this_type = m.group(1).strip().lower()
                this_val  = m.group(2).strip()
                if this_type == 'portion' and pref is None:
                    pref_type = this_type
                    pref = this_val
                elif this_type in QUANTITY_TYPES and this_val.strip().isdigit():
                    qty = this_val
                elif this_type == 'ingredients' and 'yogurt' in this_val.lower():
                    # "Add Ingredients > Yogurt On The Side" is broken out into
                    # its own لبن line rather than kept as a kitchen note.
                    has_yogurt_side = True
                elif this_val and this_type.rstrip('s') == name.lower().rstrip('s'):
                    # Generic placeholder products (e.g. "Soft Drinks", "Water")
                    # present their real selection as "Choose Soft Drink >
                    # Diet 7Up" — use that as the actual item name instead of
                    # printing the generic category label.
                    name = this_val
                else:
                    add_ons_list.append(this_val)

            is_portion = pref_type == 'portion'

            # Detect raw meat
            is_raw = (
                'raw' in name.lower() or
                name.lower() in RAW_MEAT_ITEMS or
                'Raw' in category
            )

            # Calculate display qty
            display_qty = qty
            if is_portion and pref and not pref.lower().startswith('platter'):
                # A weight portion (e.g. "1KG") only replaces the qty outright
                # when a single one was ordered. With Qty > 1 (e.g. two 1KG
                # portions), multiply through to the total weight instead of
                # discarding the order count — same convention already used
                # for weight variants below.
                wm = WEIGHT_PATTERN.match(pref)
                if wm and qty and qty.isdigit() and int(qty) > 1:
                    grams = int(wm.group(1)) * int(qty)
                    if wm.group(2).lower() == 'kg':
                        grams = grams * 1000
                    if grams >= 1000:
                        kg = grams / 1000
                        display_qty = f'{kg:g}KG'
                    else:
                        display_qty = f'{grams}G'
                elif qty and qty.isdigit() and int(qty) > 1:
                    # A non-weight portion (a tray size, say) can't be summed
                    # into one number, so the count rides along with the label
                    # instead of being dropped — three medium trays are three
                    # trays to the kitchen, not one. translate_qty() in
                    # receipt_server.py turns this into "صينية وسط ×3".
                    display_qty = f'{qty} x {pref}'
                else:
                    display_qty = pref
            elif not is_portion and variant:
                wm = WEIGHT_PATTERN.match(variant)
                if wm:
                    grams = int(wm.group(1)) * int(qty)
                    if wm.group(2).lower() == 'kg':
                        grams = grams * 1000
                    if grams >= 1000:
                        kg = grams / 1000
                        display_qty = f'{kg:g}KG'
                    elif is_raw:
                        display_qty = f'{grams}G'

            items.append({
                'qty':              display_qty,
                'name':             name,
                'variant':          None,
                'add_ons':          add_ons_list,
                'original_add_ons': list(add_ons_list),
                'category':         category,
                'is_raw':           is_raw,
                'arabic_name':      name,
                'comments':         comments_list
            })

            if has_yogurt_side:
                items.append({
                    'qty':              qty,
                    'name':             'Yogurt',
                    'variant':          None,
                    'add_ons':          [],
                    'original_add_ons': [],
                    'category':         category,
                    'is_raw':           False,
                    'arabic_name':      'لبن',
                    'comments':         []
                })
        else:
            i += 1

    return items
