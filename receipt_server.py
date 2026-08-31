import threading, os, sys, platform, subprocess, sqlite3, re, tempfile
from html import escape as _esc
try:
    import webview
    _HAS_WEBVIEW = True
except ImportError:
    _HAS_WEBVIEW = False
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import json

from receipt_image import render_receipt_image
from printer_client import print_receipt_image as send_to_printer

app = Flask(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────
def get_data_path(filename):
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

DICTIONARY_PATH = get_data_path('dictionary.json')
PREFERENCES_PATH = get_data_path('preferences.json')
COMBOS_PATH = get_data_path('combos.json')
HISTORY_DB_PATH = get_data_path('order_history.db')
_using_custom_dict = False

def get_ui_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'ui.html')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui.html')

# ── Default dictionary ────────────────────────────────────────────────────────
DEFAULT_DICTIONARY = {
    "1 head nifa": "نيفا",
    "1 person hummus fatteh": "فتة حمص",
    "1 person lsenet fatteh": "فتة لسانات",
    "7up": "سفن أب",
    "aadas bi hamoud": "عدس بالحامض",
    "arayes kafta": "عرايس كفتة",
    "bacha w assekrou": "باشا وعسكره",
    "baked kebbeh tray with meat stuffed": "كبة بالصينية باللحمة",
    "baked kebbeh tray with onions": "كبة بيصل بالصينية",
    "baked kebbeh with onions in a tray": "كبة بيصل بالصينية",
    "baked meat stuffed kebbeh in a tray": "كبة بالصينية باللحمة",
    "bamieh bil lahme & rice": "بامية باللحمة وأرز",
    "bazella bil lahme & rice": "بازيلا باللحمة وأرز",
    "beirut beer": "بيرة بيروت",
    "beirut beer light": "بيرة بيروت لايت",
    "biscuits & raha": "بسكوت وراحة",
    "biscuits and raha": "بسكوت وراحة",
    "borghol aa banadoura": "برغل بالبندورة",
    "cabbage salad": "سلطة ملفوف",
    "carob molasses": "دبس الخروب",
    "cheese rakakat": "رقاقات",
    "chicken liver in pomegranate molasses": "سودة دجاج بدبس الرمان",
    "cucumber with laban": "خيار بلبن",
    "daoud bacha & rice": "داوود باشا وأرز",
    "diet 7up": "سفن أب دايت",
    "diet pepsi": "بيبسي دايت",
    "djej w batata bil forn": "دجاج وبطاطا بالفرن",
    "fassoulia bi lahme & rice": "فاصوليا باللحمة وأرز",
    "fattouch": "فتوش",
    "fattoush": "فتوش",
    "fawaregh": "فوارغ",
    "french fries": "بطاطا مقلية",
    "fried fawaregh": "فوارغ مقلية",
    "frikeh djej": "فريكة دجاج",
    "goat labneh": "لبنة ماعز",
    "goat liver": "سودة ماعز مقلية",
    "grilled kafta": "كفتة مشوية",
    "grilled meat": "لحمة مشوي",
    "halewe": "حلاوة",
    "hindbeh dandelion greens": "هندبة بالزيت",
    "hrisse": "هريسة",
    "hummus": "حمص",
    "hummus balila": "حمص بيلة",
    "hummus fatteh": "فتة حمص",
    "hummus with meat": "حمص باللحمة",
    "iced tea": "شاي مثلج",
    "jebne darfiyeh": "جبنة ضرفية",
    "kafta bil sayniyeh & rice": "كفتة بالصينية وأرز",
    "kebbeh & shish barak with laban": "كبة و شيش برك باللبن",
    "kebbeh arnabieh & rice": "كبة أرنبية وأرز",
    "kebbeh bil labneh": "كبة باللبنة",
    "kebbeh labanieh zghertewiye": "كبة لبنية زغرتاوية",
    "kebbeh sajiyeh": "كبة صاجية",
    "kebbeh with oil": "كبة بالزيت",
    "kebbeh zghertawiye (fat)": "قرص بالدهن",
    "kebbeh zghertawiye (labneh)": "قرص باللبنة",
    "kebbeh zghertawiye (meat)": "قرص باللحمة",
    "kebbeh zghertawiye stuffed with butter": "قرص بالزبدة",
    "kebbeh zghertawiye stuffed with fat": "قرص بالدهن",
    "kebbeh zghertawiye stuffed with labneh": "قرص باللبنة",
    "kebbeh zghertawiye stuffed with meat": "قرص باللحمة",
    "kharouf mehche": "خروف محشي",
    "koussa bil laban": "كوسا باللبن",
    "laban emmo & rice": "لبن أمه وأرز",
    "labniye w shish barak": "لبنية وشيش برك",
    "lentil soup": "شوربة عدس",
    "loubieh bi zeit": "لوبيا بالزيت",
    "loubiyeh bi lahme & rice": "لوبيا باللحمة وأرز",
    "lsenet": "لسانات",
    "lsenet fatteh": "فتة لسانات",
    "makadem": "مقادم",
    "makadem fatteh": "فتة مقادم",
    "makanek": "مقانق",
    "makdous (3 to 4 pieces)": "مكدوس",
    "maqloubeh aubergines": "مقلوبة باذنجان",
    "meat stuffed vine leaves": "ورق عنب باللحمة",
    "meat stuffed vine leaves & zuchini": "ورق عنب وكوسا",
    "meat stuffed vine leaves & zuchini with cutlets": "ورق عنب وكوسا مع كستلاتة",
    "mehchi malfouf": "محشي ملفوف",
    "mezza beer": "بيرة مازة",
    "mini empty kebbeh": "كبة فارغة",
    "mini kebbeh stuffed with meat": "كبة محشية",
    "mirinda": "ميريندا",
    "mixed grills": "مشاوي مشكل",
    "mloukhieh djej & rice": "ملوخية دجاج وأرز",
    "moughrabieh": "مغربية",
    "mouhammara": "محمرة",
    "moujadara bi adas": "مجدرة بالعدس",
    "moujadara zghertewiye": "مجدرة زغرتاوية",
    "mousakaa aubergines": "مسقعة باذنجان",
    "moutabbal": "متبل",
    "nifa": "نيفا",
    "nkhahaat": "نخاعات",
    "oriental rice": "أرز معمر",
    "oriental salad": "سلطة عربية",
    "pepsi": "بيبسي",
    "pickles": "كبيس",
    "potatoes with garlic & coriander": "بطاطا بالثوم والكزبرة",
    "pumpkin kebbeh": "كبة لقطين",
    "pumpkin kebbeh (4 pcs)": "كبة لقطين (4 حبات)",
    "pumpkin kebbeh in a tray": "كبة لقطين بالصينية",
    "raheb eggplant": "بذنجان الراهب",
    "ras asfour": "لحمة رأس عصفور",
    "raw ftile": "فتيلة",
    "raw habra": "هبرة",
    "raw kafta": "كفتة نية",
    "raw kebbeh": "كبة نية",
    "raw liver": "سودة نية",
    "raw orfali": "اورفلية",
    "raw tebleh": "تابلة",
    "rim sparkling water": "مياه ريم غازية",
    "riz aa djej": "أرز بالدجاج",
    "sambousek": "سمبوسك لحمة",
    "sambousek stuffed with cheese": "سمبوسك بالجبنة",
    "shanklish": "شنكليش",
    "shish barak": "شيش برك باللبن",
    "siyadiyeh": "صيادية",
    "smidiyeh": "سميدية",
    "soft drinks": "مشروبات غازية",
    "soujouk": "سجق",
    "spaghetti bi laban": "سباغيتي باللبن",
    "spaghetti béchamel": "سباغيتي بيشاميل",
    "tabbouleh": "تبولة",
    "tajen samak": "طاجن سمك",
    "tannourine water": "مياه تنورين",
    "taouk": "طاووق",
    "tomatoes & onions salad": "سلطة بندورة وبصل",
    "vegetables": "جاط خضرة",
    "vine leaves in oil": "ورق عنب بالزيت",
    "water": "مياه",
    "yogurt": "لبن",
    "monday": "الاثنين",
    "tuesday": "الثلاثاء",
    "wednesday": "الأربعاء",
    "thursday": "الخميس",
    "friday": "الجمعة",
    "saturday": "السبت",
    "sunday": "الأحد",
}

# ── Default combo definitions ─────────────────────────────────────────────────
DEFAULT_COMBOS = {
    "kebbeh zghertawiyeh combo": {
        "has_biscuits_raha": True,
        "fixed_items": [],
        "choice_items": [
            {"type": "kebbeh", "portion": 1.0},
            {"type": "salad",  "portion": 0.5},
            {"type": "mezza",  "portion": 0.5},
            {"type": "drink",  "portion": 1.0},
            {"type": "water",  "portion": 1.0},
        ],
    },
    "taouk combo": {
        "has_biscuits_raha": True,
        "fixed_items": [
            {"name": "Taouk",        "portion": 1.0, "category": "Grills"},
            {"name": "French Fries", "portion": 0.5, "category": "Sides"},
        ],
        "choice_items": [
            {"type": "salad",  "portion": 0.5},
            {"type": "mezza",  "portion": 0.5},
            {"type": "drink",  "portion": 1.0},
            {"type": "water",  "portion": 1.0},
        ],
    },
    "meat combo": {
        "has_biscuits_raha": True,
        "fixed_items": [
            {"name": "Grilled Meat", "portion": 1.0, "category": "Grills"},
            {"name": "French Fries", "portion": 0.5, "category": "Sides"},
        ],
        "choice_items": [
            {"type": "salad",  "portion": 0.5},
            {"type": "mezza",  "portion": 0.5},
            {"type": "drink",  "portion": 1.0},
            {"type": "water",  "portion": 1.0},
        ],
    },
    "kafta combo": {
        "has_biscuits_raha": True,
        "fixed_items": [
            {"name": "Grilled Kafta", "portion": 1.0, "category": "Grills"},
            {"name": "French Fries",  "portion": 0.5, "category": "Sides"},
        ],
        "choice_items": [
            {"type": "salad",  "portion": 0.5},
            {"type": "mezza",  "portion": 0.5},
            {"type": "drink",  "portion": 1.0},
            {"type": "water",  "portion": 1.0},
        ],
    },
    "mixed grill combo": {
        "has_biscuits_raha": True,
        "fixed_items": [
            {"name": "Mixed Grills", "portion": 1.0, "category": "Grills"},
            {"name": "French Fries", "portion": 0.5, "category": "Sides"},
        ],
        "choice_items": [
            {"type": "salad",  "portion": 0.5},
            {"type": "mezza",  "portion": 0.5},
            {"type": "drink",  "portion": 1.0},
            {"type": "water",  "portion": 1.0},
        ],
    },
    "kebbe lovers box": {
        "has_biscuits_raha": False,
        "fixed_items": [
            {"name": "Kebbeh Zghertawiye (Fat)",    "portion": 1.0, "category": "Kebbeh"},
            {"name": "Kebbeh Zghertawiye (Meat)",   "portion": 1.0, "category": "Kebbeh"},
            {"name": "Kebbeh Zghertawiye (Labneh)", "portion": 1.0, "category": "Kebbeh"},
            {"name": "French Fries",                "portion": 1.0, "category": "Sides"},
        ],
        "choice_items": [
            {"type": "salad",  "portion": 1.0},
            {"type": "mezza",  "portion": 1.0},
        ],
    },
    "family sharing combo": {
        "has_biscuits_raha": False,
        "fixed_items": [
            {"name": "Mixed Grills", "portion": 1.0, "qty_label": "1KG", "category": "Grills"},
            {"name": "French Fries", "portion": 2.0, "category": "Sides"},
        ],
        "choice_items": [
            {"type": "salad",   "portion": 2.0},
            {"type": "mezza",   "portion": 2.0},
            {"type": "kebbeh",  "portion": 2.0},
        ],
    },
    "vegan combo": {
        "has_biscuits_raha": True,
        "fixed_items": [
            {"name": "Pumpkin Kebbeh (4 pcs)", "portion": 1.0, "category": "Kebbeh"},
            {"name": "French Fries",           "portion": 0.5, "category": "Sides"},
        ],
        "choice_items": [
            {"type": "salad",  "portion": 0.5},
            {"type": "mezza",  "portion": 0.5},
            {"type": "drink",  "portion": 1.0},
            {"type": "water",  "portion": 1.0},
        ],
    },
    "kebbe tray combo": {
        "has_biscuits_raha": True,
        "fixed_items": [
            {"name": "Cucumber With Laban", "portion": 0.5, "category": "Mezza"},
        ],
        "choice_items": [
            {"type": "kebbeh", "portion": 1.0},
            {"type": "mezza",  "portion": 0.5},
            {"type": "drink",  "portion": 1.0},
            {"type": "water",  "portion": 1.0},
        ],
    },
}

# ── Dictionary persistence ────────────────────────────────────────────────────
def load_dictionary():
    saved = {}
    if os.path.exists(DICTIONARY_PATH):
        try:
            with open(DICTIONARY_PATH, 'r', encoding='utf-8') as f:
                saved = json.load(f)
        except Exception:
            pass
    if _using_custom_dict:
        return saved
    d = dict(DEFAULT_DICTIONARY)
    d.update(saved)
    if d != saved:
        _write_dictionary(d)
    return d

def _write_dictionary(d):
    with open(DICTIONARY_PATH, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

# ── Preferences persistence ──────────────────────────────────────────────────
DEFAULT_PREFERENCES = {
    "frozen": "مجمد",
    "fried": "مقلي",
    "garlic & coriander": "ثوم وكزبرة",
    "with bread": "مع خبز",
    "without bread": "بدون خبز",
}

# Tray/portion size labels shown in the qty badge (e.g. "Choose Portion >
# Medium Tray") — translated separately from PREFERENCES since they replace
# the qty itself rather than appearing as a kitchen note.
QTY_LABELS = {
    "small tray": "صينية صغيرة",
    "medium tray": "صينية وسط",
    "large tray": "صينية كبيرة",
}

def load_preferences():
    saved = {}
    if os.path.exists(PREFERENCES_PATH):
        try:
            with open(PREFERENCES_PATH, 'r', encoding='utf-8') as f:
                saved = json.load(f)
        except Exception:
            pass
    d = dict(DEFAULT_PREFERENCES)
    d.update(saved)
    if d != saved:
        _write_preferences(d)
    return d

def _write_preferences(d):
    with open(PREFERENCES_PATH, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

# ── Combo persistence ────────────────────────────────────────────────────────
def load_combos():
    saved = {}
    if os.path.exists(COMBOS_PATH):
        try:
            with open(COMBOS_PATH, 'r', encoding='utf-8') as f:
                saved = json.load(f)
        except Exception:
            pass
    if not saved:
        return {k: dict(v) for k, v in DEFAULT_COMBOS.items()}
    return saved

def _write_combos(d):
    with open(COMBOS_PATH, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def _apply_combos(data):
    import extract
    combos = {}
    fixed = {}
    biscuits = set()
    for combo_name, cfg in data.items():
        choice_map = {}
        for ci in cfg.get('choice_items', []):
            if ci.get('type'):
                choice_map[ci['type']] = float(ci['portion'])
        combos[combo_name] = choice_map
        fi = []
        for item in cfg.get('fixed_items', []):
            if not item.get('name'):
                continue
            entry = {'name': item['name'], 'portion': float(item['portion'])}
            if item.get('qty_label'):
                entry['qty_label'] = item['qty_label']
            if item.get('category'):
                entry['category'] = item['category']
            fi.append(entry)
        if fi:
            fixed[combo_name] = fi
        if cfg.get('has_biscuits_raha'):
            biscuits.add(combo_name)
    extract.COMBOS = combos
    extract.COMBO_FIXED_ITEMS = fixed
    extract.COMBOS_WITH_BISCUITS_RAHA = biscuits

# ── Settings persistence ──────────────────────────────────────────────────────
DEFAULT_SETTINGS = {
    'branch': 'الأشرفية',
    # Network ESC/POS thermal printer -- receipts are rendered to an image
    # and sent straight to this printer, no browser/print-dialog involved.
    'printer_ip': '',
    'printer_port': 9100,
    'printer_width_px': 576,   # printable dots across the roll width
    'printer_width_mm': 72,
    'printer_expected_max_mm': 420,  # just a "warn if longer than usual" threshold
    'printer_cut_mode': 'FULL',      # 'FULL' or 'PART'
}

def load_settings():
    path = get_data_path('settings.json')
    saved = {}
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                saved = json.load(f)
        except Exception:
            pass
    d = dict(DEFAULT_SETTINGS)
    d.update(saved)
    if d != saved:
        _write_settings(d)
    return d

def _write_settings(s):
    path = get_data_path('settings.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(s, f, ensure_ascii=False, indent=2)

# ── In-memory state ───────────────────────────────────────────────────────────
SETTINGS = load_settings()
if 'custom_dict_path' in SETTINGS:
    _cp = SETTINGS['custom_dict_path']
    if _cp and os.path.exists(_cp):
        DICTIONARY_PATH = _cp
        _using_custom_dict = True

DICTIONARY = load_dictionary()
PREFERENCES = load_preferences()
COMBOS_DATA = load_combos()
_apply_combos(COMBOS_DATA)
PENDING_ORDER = None

# ── Order history (SQLite, stored inside the app's own data folder) ──────────
def _db():
    conn = sqlite3.connect(HISTORY_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_history_db():
    conn = _db()
    conn.execute('''CREATE TABLE IF NOT EXISTS orders (
        order_num          TEXT PRIMARY KEY,
        customer            TEXT,
        prepare_by          TEXT,
        delivery_date        TEXT,
        delivery_datetime    TEXT,
        scheduled            INTEGER,
        branch                TEXT,
        printed_at            TEXT,
        items_json            TEXT
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        order_num       TEXT,
        delivery_date    TEXT,
        name              TEXT,
        category           TEXT,
        qty                 TEXT
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(delivery_date)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_items_date ON order_items(delivery_date)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_items_order ON order_items(order_num)')
    conn.commit()
    conn.close()

init_history_db()

_MONTH_ABBR = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
               'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
_WEEKDAY_ABBR = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}

def parse_prepare_by_dt(prepare_by):
    s = (prepare_by or '').strip()
    m = re.match(r'^(\w+)\s+(\d{1,2}),\s*(\d{1,2}):(\d{2})\s*(AM|PM)$', s, re.IGNORECASE)
    if not m:
        return None
    token, day_s, hour_s, minute_s, ampm = m.groups()
    day = int(day_s)
    hour = int(hour_s) % 12
    if ampm.upper() == 'PM':
        hour += 12
    minute = int(minute_s)
    token_key = token.lower()[:3]
    now = datetime.now()

    if token_key in _MONTH_ABBR:
        try:
            dt = datetime(now.year, _MONTH_ABBR[token_key], day, hour, minute)
        except ValueError:
            return None
        # Orders printed near year-end for early-January delivery dates would
        # otherwise land a year in the future (or vice-versa); shift a year.
        if dt - now > timedelta(days=180):
            dt = dt.replace(year=dt.year - 1)
        elif now - dt > timedelta(days=180):
            dt = dt.replace(year=dt.year + 1)
        return dt

    if token_key in _WEEKDAY_ABBR:
        # Toters actually sends a weekday abbreviation here, not a month
        # (e.g. "Mon 20, 03:55 PM") — no month is given at all, so find the
        # nearby calendar date whose day-of-month and weekday both match.
        target_weekday = _WEEKDAY_ABBR[token_key]
        best = None
        for offset in range(-20, 40):
            candidate = (now + timedelta(days=offset)).date()
            if candidate.day == day and candidate.weekday() == target_weekday:
                candidate_dt = datetime(candidate.year, candidate.month, candidate.day, hour, minute)
                if best is None or abs((candidate_dt - now).total_seconds()) < abs((best - now).total_seconds()):
                    best = candidate_dt
        return best

    return None

def save_order_to_history(d):
    order_num = str(d.get('order_num') or '').strip()
    if not order_num:
        return
    dt = parse_prepare_by_dt(d.get('prepare_by', ''))
    delivery_date = dt.strftime('%Y-%m-%d') if dt else datetime.now().strftime('%Y-%m-%d')
    delivery_datetime = dt.isoformat() if dt else datetime.now().isoformat()
    items = d.get('items') or []

    conn = _db()
    conn.execute('DELETE FROM order_items WHERE order_num = ?', (order_num,))
    conn.execute('''INSERT INTO orders
            (order_num, customer, prepare_by, delivery_date, delivery_datetime, scheduled, branch, printed_at, items_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(order_num) DO UPDATE SET
            customer=excluded.customer, prepare_by=excluded.prepare_by,
            delivery_date=excluded.delivery_date, delivery_datetime=excluded.delivery_datetime,
            scheduled=excluded.scheduled, branch=excluded.branch,
            printed_at=excluded.printed_at, items_json=excluded.items_json''',
        (order_num, d.get('customer', ''), d.get('prepare_by', ''), delivery_date, delivery_datetime,
         1 if d.get('scheduled') else 0, SETTINGS.get('branch', ''), datetime.now().isoformat(),
         json.dumps(items, ensure_ascii=False)))
    for item in items:
        if item.get('is_bag_header'):
            continue
        conn.execute('INSERT INTO order_items (order_num, delivery_date, name, category, qty) VALUES (?, ?, ?, ?, ?)',
            (order_num, delivery_date, item.get('name', ''), (item.get('category') or '').strip() or 'Other', item.get('qty', '')))
    conn.commit()
    conn.close()

def get_stored_order(order_num):
    conn = _db()
    row = conn.execute('SELECT * FROM orders WHERE order_num = ?', (order_num,)).fetchone()
    conn.close()
    if not row:
        return None
    return {
        'order_num':  row['order_num'],
        'customer':   row['customer'],
        'prepare_by': row['prepare_by'],
        'scheduled':  bool(row['scheduled']),
        'items':      json.loads(row['items_json']),
    }

def history_list(date_from, date_to):
    conn = _db()
    rows = conn.execute('''
        SELECT o.order_num, o.customer, o.prepare_by, o.delivery_date, o.delivery_datetime, o.scheduled,
               (SELECT COUNT(*) FROM order_items oi WHERE oi.order_num = o.order_num) AS item_count
        FROM orders o
        WHERE o.delivery_date BETWEEN ? AND ?
        ORDER BY o.delivery_datetime DESC''', (date_from, date_to)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def parse_qty(qty_str):
    s = (qty_str or '').strip()
    if not s:
        return ('count', 0.0)
    m = re.match(r'^(\d+(?:\.\d+)?)\s*(KG|G)$', s, re.IGNORECASE)
    if m:
        val = float(m.group(1))
        grams = val * 1000 if m.group(2).upper() == 'KG' else val
        return ('weight', grams)
    m = re.match(r'^(\d+)?½$', s)
    if m:
        whole = int(m.group(1)) if m.group(1) else 0
        return ('count', whole + 0.5)
    m = re.match(r'^\d+(\.\d+)?$', s)
    if m:
        return ('count', float(s))
    return ('label', s)

def _fmt_count(v):
    whole = int(v)
    frac = v - whole
    if abs(frac - 0.5) < 0.01:
        return '½' if whole == 0 else f'{whole}½'
    if abs(v - whole) < 0.01:
        return str(whole)
    return f'{v:g}'

def _fmt_summed_qty(g):
    parts = []
    if g['count']:
        parts.append(_fmt_count(g['count']))
    if g['weight']:
        w = g['weight']
        parts.append(f'{w / 1000:g}KG' if w >= 1000 else f'{w:g}G')
    for label, cnt in sorted(g['labels'].items()):
        parts.append(f'{label} ×{cnt}')
    return ' + '.join(parts) if parts else '0'

def items_report(date_from, date_to):
    conn = _db()
    rows = conn.execute('SELECT category, name, qty FROM order_items WHERE delivery_date BETWEEN ? AND ?',
                         (date_from, date_to)).fetchall()
    order_count = conn.execute('SELECT COUNT(*) c FROM orders WHERE delivery_date BETWEEN ? AND ?',
                                (date_from, date_to)).fetchone()['c']
    conn.close()

    groups = {}
    for r in rows:
        cat = (r['category'] or 'Other').strip() or 'Other'
        name = r['name'] or 'Unknown'
        g = groups.setdefault(cat, {}).setdefault(name, {'count': 0.0, 'weight': 0.0, 'labels': {}})
        kind, val = parse_qty(r['qty'])
        if kind == 'count':
            g['count'] += val
        elif kind == 'weight':
            g['weight'] += val
        else:
            g['labels'][val] = g['labels'].get(val, 0) + 1

    categories = []
    for cat in sorted(groups.keys()):
        items = [{'name': name, 'qty_display': _fmt_summed_qty(groups[cat][name])}
                  for name in sorted(groups[cat].keys())]
        categories.append({'category': cat, 'items': items})
    return {'categories': categories, 'order_count': order_count, 'from': date_from, 'to': date_to}

def orders_report(date_from, date_to):
    conn = _db()
    rows = conn.execute('''SELECT order_num, customer, delivery_date, delivery_datetime FROM orders
                            WHERE delivery_date BETWEEN ? AND ? ORDER BY delivery_datetime DESC''',
                         (date_from, date_to)).fetchall()
    conn.close()
    days = {}
    for r in rows:
        days.setdefault(r['delivery_date'], []).append(
            {'order_num': r['order_num'], 'customer': r['customer'], 'delivery_datetime': r['delivery_datetime']})
    day_list = [{'date': d, 'orders': days[d], 'count': len(days[d])} for d in sorted(days.keys(), reverse=True)]
    return {'days': day_list, 'total_orders': len(rows), 'from': date_from, 'to': date_to}

# ── Translation ───────────────────────────────────────────────────────────────
def translate_word(name):
    key = name.lower().strip()
    return DICTIONARY.get(key, name)

def translate_add_ons(add_ons_list):
    return [PREFERENCES.get(ao.lower().strip(), ao) for ao in (add_ons_list or [])]

def translate_items(items):
    for item in items:
        if item.get('is_bag_header'):
            continue
        item['add_ons']     = translate_add_ons(item.get('add_ons', []))
        item['arabic_name'] = translate_word(item['name'])
        item['qty']         = QTY_LABELS.get(str(item.get('qty', '')).lower().strip(), item.get('qty'))
        name_key = item['name'].lower().strip()
        if item.get('category') == 'Combos' and 'biscuit' in name_key and 'raha' in name_key:
            item['arabic_name'] = 'بسكوت وراحة قطعتين مطبقين'
    return items

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    with open(get_ui_path(), encoding='utf-8') as f:
        return f.read()

@app.route('/parse', methods=['POST'])
def parse():
    from extract import parse_order
    raw = request.json.get('text', '')
    order = parse_order(raw)
    if not order['items']:
        return jsonify({'error': 'No items found — check the pasted text'}), 400
    translate_items(order['items'])
    return jsonify(order)

def _open_temp_html(html):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8')
    tmp.write(html)
    tmp.close()
    if platform.system() == 'Windows':
        os.startfile(tmp.name)
    elif platform.system() == 'Darwin':
        subprocess.Popen(['open', tmp.name])
    else:
        subprocess.Popen(['xdg-open', tmp.name])

@app.route('/receipt', methods=['POST'])
def receipt():
    try:
        d = request.json
        warning = print_receipt(d)
        save_order_to_history(d)
        resp = {'ok': True}
        if warning:
            resp['warning'] = warning
        return jsonify(resp)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/printer/test', methods=['POST'])
def printer_test():
    try:
        ctx = {
            'customer': 'Test Print', 'prepare_by': datetime.now().strftime('%b %d, %I:%M %p'),
            'order_num': '0000', 'branch': SETTINGS.get('branch', 'الأشرفية'),
            'time_lbl': 'وقت التجهيز', 'scheduled': False, 'day_ar': '',
            'items': [{'qty': '1', 'arabic_name': 'طباعة تجريبية', 'comments': ['إذا وصلك هذا فالطابعة تعمل بشكل صحيح']}],
        }
        img = render_receipt_image(ctx, width_px=int(SETTINGS.get('printer_width_px', 576)),
                                    width_mm=float(SETTINGS.get('printer_width_mm', 72)))
        send_to_printer(img, ip=SETTINGS.get('printer_ip', ''), port=int(SETTINGS.get('printer_port', 9100)),
                         cut_mode=SETTINGS.get('printer_cut_mode', 'FULL'))
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/dictionary', methods=['GET'])
def get_dictionary():
    return jsonify(DICTIONARY)

@app.route('/dictionary/save', methods=['POST'])
def save_dict():
    global DICTIONARY
    try:
        DICTIONARY = request.json
        _write_dictionary(DICTIONARY)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/dictionary/update', methods=['POST'])
def update_dict():
    global DICTIONARY
    try:
        updates = request.json
        DICTIONARY.update(updates)
        _write_dictionary(DICTIONARY)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/preferences', methods=['GET'])
def get_preferences():
    return jsonify(PREFERENCES)

@app.route('/preferences/update', methods=['POST'])
def update_preferences():
    global PREFERENCES
    try:
        updates = {k.lower().strip(): v for k, v in request.json.items() if k and v}
        PREFERENCES.update(updates)
        _write_preferences(PREFERENCES)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/preferences/save', methods=['POST'])
def save_preferences():
    global PREFERENCES
    try:
        PREFERENCES = {k.lower().strip(): v for k, v in request.json.items() if k and v}
        _write_preferences(PREFERENCES)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/settings', methods=['GET'])
def get_settings():
    return jsonify(SETTINGS)

@app.route('/settings/save', methods=['POST'])
def save_sett():
    global SETTINGS
    try:
        SETTINGS = request.json
        _write_settings(SETTINGS)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/combos', methods=['GET'])
def get_combos():
    return jsonify(COMBOS_DATA)

@app.route('/combos/save', methods=['POST'])
def save_combos():
    global COMBOS_DATA
    try:
        COMBOS_DATA = request.json
        _write_combos(COMBOS_DATA)
        _apply_combos(COMBOS_DATA)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/settings/set-json-file', methods=['POST'])
def set_json_file():
    global DICTIONARY, DICTIONARY_PATH, SETTINGS, _using_custom_dict
    path = request.json.get('path', '').strip()

    if not path:
        DICTIONARY_PATH = get_data_path('dictionary.json')
        _using_custom_dict = False
        SETTINGS.pop('custom_dict_path', None)
        _write_settings(SETTINGS)
        DICTIONARY = load_dictionary()
        return jsonify({'ok': True, 'count': len(DICTIONARY), 'path': ''})

    if not os.path.exists(path):
        return jsonify({'ok': False, 'error': 'File not found: ' + path}), 400

    try:
        with open(path, 'r', encoding='utf-8') as f:
            new_dict = json.load(f)
    except Exception as e:
        return jsonify({'ok': False, 'error': 'Invalid JSON: ' + str(e)}), 400

    if not isinstance(new_dict, dict):
        return jsonify({'ok': False, 'error': 'JSON file must contain an object (key/value pairs)'}), 400

    new_dict = {k.lower().strip(): v for k, v in new_dict.items()}

    # Clear old dictionary.json so previously saved entries are gone
    default_path = get_data_path('dictionary.json')
    if path != default_path:
        with open(default_path, 'w', encoding='utf-8') as f:
            json.dump({}, f)

    DICTIONARY_PATH = path
    _using_custom_dict = True
    DICTIONARY = new_dict
    SETTINGS['custom_dict_path'] = path
    _write_settings(SETTINGS)
    return jsonify({'ok': True, 'count': len(DICTIONARY), 'path': path})

# ── History & reports ─────────────────────────────────────────────────────────
def _range_args():
    date_from = request.args.get('from') or '0001-01-01'
    date_to = request.args.get('to') or '9999-12-31'
    return date_from, date_to

@app.route('/history', methods=['GET'])
def history_route():
    date_from, date_to = _range_args()
    return jsonify(history_list(date_from, date_to))

@app.route('/history/order/<order_num>', methods=['GET'])
def history_order_route(order_num):
    order = get_stored_order(order_num)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    return jsonify(order)

@app.route('/history/reprint/<order_num>', methods=['POST'])
def history_reprint_route(order_num):
    order = get_stored_order(order_num)
    if not order:
        return jsonify({'ok': False, 'error': 'Order not found'}), 404
    try:
        warning = print_receipt(order)
        save_order_to_history(order)
        resp = {'ok': True}
        if warning:
            resp['warning'] = warning
        return jsonify(resp)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/reports/items', methods=['GET'])
def reports_items_route():
    date_from, date_to = _range_args()
    return jsonify(items_report(date_from, date_to))

@app.route('/reports/orders', methods=['GET'])
def reports_orders_route():
    date_from, date_to = _range_args()
    return jsonify(orders_report(date_from, date_to))

@app.route('/reports/items/print', methods=['POST'])
def reports_items_print_route():
    data = request.json or {}
    date_from = data.get('from') or '0001-01-01'
    date_to = data.get('to') or '9999-12-31'
    try:
        html = build_items_report_html(items_report(date_from, date_to))
        _open_temp_html(html)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

@app.route('/reports/orders/print', methods=['POST'])
def reports_orders_print_route():
    data = request.json or {}
    date_from = data.get('from') or '0001-01-01'
    date_to = data.get('to') or '9999-12-31'
    try:
        html = build_orders_report_html(orders_report(date_from, date_to))
        _open_temp_html(html)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

# ── Chrome extension endpoints ───────────────────────────────────────────────
@app.route('/extension/parse', methods=['POST'])
def extension_parse():
    global PENDING_ORDER
    from extract import parse_order
    raw = request.json.get('text', '')
    order = parse_order(raw)
    if not order['items']:
        return jsonify({'error': 'No items found — check the Toters page'}), 400
    translate_items(order['items'])
    PENDING_ORDER = order
    return jsonify(order)

@app.route('/extension/pending', methods=['GET'])
def extension_pending():
    global PENDING_ORDER
    order = PENDING_ORDER
    PENDING_ORDER = None
    return jsonify(order) if order else jsonify(None)

@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

# ── Receipt printing ────────────────────────────────────────────────────────
def _receipt_context(d):
    EN_DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    dt = parse_prepare_by_dt(d.get('prepare_by', ''))
    day_ar = DICTIONARY.get(EN_DAYS[dt.weekday()], EN_DAYS[dt.weekday()]) if dt else ''
    return {
        'customer':   d.get('customer', ''),
        'prepare_by': d.get('prepare_by', ''),
        'order_num':  d.get('order_num', ''),
        'branch':     SETTINGS.get('branch', 'الأشرفية'),
        'time_lbl':   'تجهيز قبل' if d.get('scheduled') else 'وقت التجهيز',
        'scheduled':  bool(d.get('scheduled')),
        'day_ar':     day_ar,
        'items':      d.get('items') or [],
    }

def print_receipt(d):
    """Renders the receipt to an image and sends it straight to the
    configured ESC/POS printer, cutting after. Returns a warning string if
    the receipt ran unusually long (still printed in full either way), or
    None."""
    ctx = _receipt_context(d)
    width_px = int(SETTINGS.get('printer_width_px', 576))
    width_mm = float(SETTINGS.get('printer_width_mm', 72))
    img = render_receipt_image(ctx, width_px=width_px, width_mm=width_mm)

    send_to_printer(img, ip=SETTINGS.get('printer_ip', ''), port=int(SETTINGS.get('printer_port', 9100)),
                     cut_mode=SETTINGS.get('printer_cut_mode', 'FULL'))

    dpmm = width_px / width_mm
    length_mm = img.height / dpmm
    expected = float(SETTINGS.get('printer_expected_max_mm', 420))
    if length_mm > expected:
        return f'Receipt ran long: {length_mm:.0f}mm (usual max ~{expected:.0f}mm) — check the roll has enough paper left.'
    return None

# ── A4 report builders ────────────────────────────────────────────────────────
_REPORT_STYLE = '''
@page { size: A4; margin: 16mm; }
*{box-sizing:border-box}
body{font-family:Arial,Helvetica,sans-serif;color:#111;margin:0}
h1{font-size:21px;margin:0 0 2px}
.sub{color:#666;font-size:12.5px;margin-bottom:20px}
.cat-hd{background:#111;color:#fff;font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.5px;padding:6px 10px;margin-top:14px}
.day-hd{display:flex;justify-content:space-between;align-items:baseline;background:#f2f2f2;border-bottom:2px solid #111;padding:6px 10px;margin-top:14px;font-weight:700;font-size:13px}
.day-hd span{font-weight:400;color:#666;font-size:12px}
table{width:100%;border-collapse:collapse}
th{text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.4px;color:#666;border-bottom:1.5px solid #ccc;padding:5px 10px}
td{padding:5px 10px;border-bottom:1px solid #eee;font-size:12.5px}
.qty{text-align:right;font-weight:700;white-space:nowrap}
.foot{margin-top:24px;padding-top:10px;border-top:1px solid #ccc;font-size:11px;color:#888}
.empty{padding:16px 10px;color:#888;font-size:13px}
'''

def build_items_report_html(report):
    body = ''
    if not report['categories']:
        body = '<div class="empty">No items sold in this range.</div>'
    for cat in report['categories']:
        body += f'<div class="cat-hd">{_esc(cat["category"])}</div>'
        body += '<table><tbody>'
        for item in cat['items']:
            body += f'<tr><td>{_esc(item["name"])}</td><td class="qty">{_esc(item["qty_display"])}</td></tr>'
        body += '</tbody></table>'

    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Items Sold Report</title>
<style>{_REPORT_STYLE}</style></head>
<body>
<h1>Items Sold Report</h1>
<div class="sub">{report["from"]} &rarr; {report["to"]} &nbsp;|&nbsp; {report["order_count"]} order(s)</div>
{body}
<div class="foot">Kebbet Zamen &mdash; Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
<script>window.onload=()=>window.print()</script>
</body></html>'''

def build_orders_report_html(report):
    body = ''
    if not report['days']:
        body = '<div class="empty">No orders in this range.</div>'
    for day in report['days']:
        body += f'<div class="day-hd">{_esc(day["date"])}<span>{day["count"]} order(s)</span></div>'
        body += '<table><thead><tr><th>Order #</th><th>Customer</th><th>Delivery time</th></tr></thead><tbody>'
        for o in day['orders']:
            dt = None
            try:
                dt = datetime.fromisoformat(o['delivery_datetime'])
            except (ValueError, TypeError):
                pass
            time_str = dt.strftime('%b %d, %I:%M %p') if dt else (o['delivery_datetime'] or '')
            body += f'<tr><td>#{_esc(o["order_num"])}</td><td>{_esc(o["customer"])}</td><td>{_esc(time_str)}</td></tr>'
        body += '</tbody></table>'

    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Orders Report</title>
<style>{_REPORT_STYLE}</style></head>
<body>
<h1>Orders Report</h1>
<div class="sub">{report["from"]} &rarr; {report["to"]} &nbsp;|&nbsp; {report["total_orders"]} order(s) total</div>
{body}
<div class="foot">Kebbet Zamen &mdash; Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
<script>window.onload=()=>window.print()</script>
</body></html>'''

# ── Launch ────────────────────────────────────────────────────────────────────
def run_flask(host='127.0.0.1'):
    port = int(os.environ.get('PORT', 5001))
    app.run(host=host, port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    if _HAS_WEBVIEW:
        t = threading.Thread(target=run_flask, daemon=True)
        t.start()
        import time
        time.sleep(1)
        webview.create_window(
            'Kebbet Zamen — Receipt',
            'http://127.0.0.1:5001',
            width=800,
            height=700,
            resizable=True
        )
        webview.start()
    else:
        import socket
        ip = socket.gethostbyname(socket.gethostname())
        print(f'\n  Kebbet Zamen running at:')
        print(f'  → http://localhost:5001  (this machine)')
        print(f'  → http://{ip}:5001       (from phone on same WiFi)\n')
        run_flask(host='0.0.0.0')
