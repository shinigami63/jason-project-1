import re

SIZE_PATTERN = re.compile(r'^\d+\s*(G|g|ML|ml|kg|KG|pieces?|Piece|piece|gr|persons?)$', re.IGNORECASE)
WEIGHT_PATTERN = re.compile(r'^(\d+)\s*(G|g|gr|KG|kg)$', re.IGNORECASE)

RAW_MEAT_ITEMS = {
    "raw kibbeh", "raw kebbeh", "kebbeh nayeh", "kibbeh nayeh",
    "raw tenderloin", "raw habra", "raw orfali", "raw liver",
    "raw kafta", "raw fitle", "raw meat"
}

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

            pref_type = None
            pref = None
            extra_prefs = []
            for j in range(i, len(lines)):
                if lines[j] == 'Qty':
                    break
                m = re.search(r'Choose\s+(\w+)\s*[>:]\s*(.+)', lines[j])
                if not m:
                    continue
                this_type = m.group(1).strip().lower()
                this_val = m.group(2).strip()
                if this_type == 'portion' and pref is None:
                    pref_type = this_type
                    pref = this_val
                else:
                    extra_prefs.append(this_val)

            is_portion = pref_type == 'portion'
            preference_raw = ', '.join(extra_prefs) if extra_prefs else None

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
                'qty': display_qty,
                'name': name,
                'variant': None,
                'preference': preference_raw,
                'original_preference': preference_raw,
                'category': category,
                'is_raw': is_raw,
                'arabic_name': name
            })
        else:
            i += 1

    return items
