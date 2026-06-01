import re

SIZE_PATTERN = re.compile(r'^\d+\s*(G|g|ML|ml|kg|KG|pieces?|Piece|piece|gr|persons?)$', re.IGNORECASE)
WEIGHT_PATTERN = re.compile(r'^(\d+)\s*(G|g|gr|KG|kg)$', re.IGNORECASE)

QUANTITY_TYPES = {'quantity', 'qty', 'amount', 'count', 'number'}

RAW_MEAT_ITEMS = {
    "raw kibbeh", "raw kebbeh", "kebbeh nayeh", "kibbeh nayeh",
    "raw tenderloin", "raw habra", "raw orfali", "raw liver",
    "raw kafta", "raw fitle", "raw meat"
}

COMBOS = {
    "kebbeh zghertawiyeh combo": {
        "kebbeh": 1.0, "salad": 0.5, "mezza": 0.5, "drink": 1.0, "water": 1.0,
    },
    "taouk combo": {
        "salad": 0.5, "fries": 0.5, "french fries": 0.5,
        "mezza": 0.5, "drink": 1.0, "water": 1.0,
    },
    "meat combo": {
        "salad": 0.5, "fries": 0.5, "french fries": 0.5,
        "mezza": 0.5, "drink": 1.0, "water": 1.0,
    },
    "kafta combo": {
        "salad": 0.5, "fries": 0.5, "french fries": 0.5,
        "mezza": 0.5, "drink": 1.0, "water": 1.0,
    },
    "mixed grill combo": {
        "salad": 0.5, "fries": 0.5, "french fries": 0.5,
        "mezza": 0.5, "drink": 1.0, "water": 1.0,
    },
    "kebbe lovers box": {
        "kebbeh": 3.0, "salad": 1.0, "fries": 1.0,
        "french fries": 1.0, "mezza": 1.0,
    },
    "family sharing combo": {
        "mixed grill": 1.0, "salad": 2.0, "mezza": 2.0,
        "fries": 2.0, "french fries": 2.0, "kebbeh": 2.0,
    },
    "vegan combo": {
        "kebbeh": 1.0, "fries": 0.5, "french fries": 0.5,
        "salad": 0.5, "mezza": 0.5, "drink": 1.0, "water": 1.0,
    },
    "kebbe tray combo": {
        "kebbeh": 1.0, "cucumber": 0.5, "mezza": 0.5,
        "drink": 1.0, "water": 1.0,
    },
}

COMBOS_WITH_BISCUITS_RAHA = {
    "kebbeh zghertawiyeh combo",
    "taouk combo",
    "meat combo",
    "kafta combo",
    "mixed grill combo",
    "vegan combo",
    "kebbe tray combo",
}

# Fixed items that are always included in a combo but never appear as
# "Choose X > Y" selections on the Toters page (so they'd be silently dropped).
COMBO_FIXED_ITEMS = {
    "vegan combo": [
        {"name": "Pumpkin Kebbeh", "portion": 1.0},
        {"name": "French Fries",   "portion": 0.5},
    ],
    "kebbe tray combo": [
        {"name": "Cucumber With Laban", "portion": 0.5},
    ],
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
        'items':     _items(lines)
    }

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

def _make_combo_item(name, portion):
    return {
        'qty':              _format_qty(portion),
        'name':             name,
        'variant':          None,
        'add_ons':          [],
        'original_add_ons': [],
        'category':         'Combos',
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

    # Build the item list for a single bag
    per_bag = []

    # 1. Fixed items always in this combo (not selectable by customer on Toters)
    for fixed in COMBO_FIXED_ITEMS.get(combo_name_lower, []):
        per_bag.append(_make_combo_item(fixed['name'], fixed['portion']))

    # 2. Customer-chosen items (Choose X > Y lines)
    for j in range(start_i, len(lines)):
        if lines[j] == 'Qty':
            break
        m = re.search(r'Choose\s+(\w+)\s*[>:]\s*(.+)', lines[j])
        if not m:
            continue
        this_type = m.group(1).strip().lower()
        item_name = m.group(2).strip()

        portion = combo_def.get(this_type, None)
        if portion is None:
            portion = 1.0
            if j > 0:
                qm = re.match(r'^(\d+(?:\.\d+)?)\s*x', lines[j - 1], re.IGNORECASE)
                if qm:
                    portion = float(qm.group(1))

        per_bag.append(_make_combo_item(item_name, portion))

    # 3. Biscuits & Raha (always appended last for applicable combos)
    if combo_name_lower in COMBOS_WITH_BISCUITS_RAHA:
        per_bag.append({
            'qty':              '1',
            'name':             'Biscuits & Raha',
            'variant':          None,
            'add_ons':          [],
            'original_add_ons': [],
            'category':         'Combos',
            'is_raw':           False,
            'arabic_name':      'بسكوت وراحة قطعتين مطبقين',
        })

    # Single combo: return flat list with no bag header
    if combo_qty <= 1:
        return per_bag

    # Multiple combos: split into clearly labelled bags
    result = []
    for n in range(1, combo_qty + 1):
        ar_num = _ARABIC_NUMS[n - 1] if n <= len(_ARABIC_NUMS) else str(n)
        result.append({
            'qty':              '',
            'name':             f'Bag {n}',
            'arabic_name':      f'كيس {ar_num}',
            'variant':          None,
            'add_ons':          [],
            'original_add_ons': [],
            'category':         'Combos',
            'is_raw':           False,
            'is_bag_header':    True,
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
            for j in range(i, len(lines)):
                if lines[j] == 'Qty':
                    break
                m = re.search(r'Choose\s+(\w+)\s*[>:]\s*(.+)', lines[j])
                if not m:
                    continue
                this_type = m.group(1).strip().lower()
                this_val  = m.group(2).strip()
                if this_type == 'portion' and pref is None:
                    pref_type = this_type
                    pref = this_val
                elif this_type in QUANTITY_TYPES and this_val.strip().isdigit():
                    qty = this_val
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
                'arabic_name':      name
            })
        else:
            i += 1

    return items
