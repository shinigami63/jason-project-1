import threading, os, sys, platform, subprocess
try:
    import webview
    _HAS_WEBVIEW = True
except ImportError:
    _HAS_WEBVIEW = False
from datetime import datetime
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────
def get_data_path(filename):
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

DICTIONARY_PATH = get_data_path('dictionary.json')
PREFERENCES_PATH = get_data_path('preferences.json')
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

# ── Settings persistence ──────────────────────────────────────────────────────
def load_settings():
    path = get_data_path('settings.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'branch': 'الأشرفية'}

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
PENDING_ORDER = None

# ── Translation ───────────────────────────────────────────────────────────────
def translate_word(name):
    key = name.lower().strip()
    return DICTIONARY.get(key, name)

def translate_add_ons(add_ons_list):
    return [PREFERENCES.get(ao.lower().strip(), ao) for ao in (add_ons_list or [])]

def translate_items(items):
    for item in items:
        item['add_ons']     = translate_add_ons(item.get('add_ons', []))
        item['arabic_name'] = translate_word(item['name'])
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

@app.route('/receipt', methods=['POST'])
def receipt():
    try:
        html = build_receipt(request.json)
        import tempfile
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8')
        tmp.write(html)
        tmp.close()
        if platform.system() == 'Windows':
            os.startfile(tmp.name)
        elif platform.system() == 'Darwin':
            subprocess.Popen(['open', tmp.name])
        else:
            subprocess.Popen(['xdg-open', tmp.name])
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

# ── Receipt builder ───────────────────────────────────────────────────────────
def build_receipt(d):
    rows = ''
    for item in d['items']:
        notes_html = ''.join(
            f'<div class="note">{c}</div>'
            for c in item.get('comments', []) if c
        )
        rows += f'''
        <div class="item">
          <div class="row">
            <span class="qty">{item["qty"]}</span>
            <span class="iname">{item["arabic_name"]}</span>
          </div>
          {notes_html}
        </div>'''

    EN_DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    try:
        dt = datetime.strptime(d['prepare_by'], '%b %d, %I:%M %p').replace(year=datetime.now().year)
        day_ar = DICTIONARY.get(EN_DAYS[dt.weekday()], EN_DAYS[dt.weekday()])
    except (ValueError, KeyError):
        day_ar = ''

    sched    = '<div class="sched">مجدول ⏰</div>' if d.get('scheduled') else ''
    time_lbl = 'تجهيز قبل' if d.get('scheduled') else 'وقت التجهيز'
    branch   = SETTINGS.get('branch', 'الأشرفية')

    return f'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
*{{margin:0;padding:0;box-sizing:border-box;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
@page{{size:72mm auto;margin:0}}
body{{font-family:'Cairo',Arial,sans-serif;width:72mm;margin:0 auto;color:#000;font-size:11px;direction:rtl}}
.r{{padding:4mm}}
.hd{{text-align:center;padding-bottom:3mm;border-bottom:2px dashed #000}}
.logo{{font-size:20px;font-weight:900}}
.br{{font-size:12px;font-weight:600;margin-top:1mm}}
.toters{{font-size:18px;font-weight:900;color:#000;margin-top:2mm;letter-spacing:3px}}
.sched{{background:#000;color:#fff;text-align:center;padding:1mm;font-size:11px;font-weight:700;margin-top:1mm}}
.info{{padding:3mm 0;border-bottom:1px dashed #000}}
.ir{{display:flex;justify-content:space-between;margin-bottom:1.5mm;font-size:11px}}
.il{{color:#000}}
.iv{{font-weight:700;font-size:13px}}
.ih{{background:#000;color:#fff;text-align:center;padding:1.5mm;font-size:12px;font-weight:700;margin:2mm 0 0}}
.item{{padding:2.5mm 0;border-bottom:1px dotted #000}}
.row{{display:flex;align-items:center;gap:2mm}}
.qty{{background:#000;color:#fff;font-weight:900;font-size:16px;padding:0 2mm;border-radius:2px;flex-shrink:0;min-width:8mm;text-align:center;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.iname{{font-weight:700;font-size:16px}}
.note{{font-size:14px;font-weight:700;color:#000;margin-top:1mm;margin-right:6mm;border-right:3px solid #000;padding-right:1.5mm}}
.ft{{text-align:center;margin-top:4mm;padding-top:3mm;border-top:2px dashed #000;font-size:10px;color:#000}}
.ft b{{font-size:13px;color:#000}}
.day{{font-size:20px;font-weight:900;text-align:center;margin-top:2mm}}
</style></head>
<body>
<div class="r">
  <div class="hd">
    <div class="logo">كبة زمان</div>
    <div class="br">فرع {branch}</div>
    <div class="toters">TOTERS</div>
    {sched}
    {'<div class="day">' + day_ar + '</div>' if day_ar else ''}
  </div>
  <div class="info">
    <div class="ir"><span class="il">الزبون</span><span class="iv">{d["customer"]}</span></div>
    <div class="ir"><span class="il">{time_lbl}</span><span class="iv">{d["prepare_by"]}</span></div>
    <div class="ir"><span class="il">رقم الطلب</span><span class="iv">#{d["order_num"]}</span></div>
  </div>
  <div class="ih">الطلبية</div>
  {rows}
  <div class="ft"><b>شكراً!</b></div>
</div>
<script>window.onload=()=>window.print()</script>
</body></html>'''

# ── Launch ────────────────────────────────────────────────────────────────────
def run_flask(host='127.0.0.1'):
    app.run(host=host, port=5001, debug=False, use_reloader=False)

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
