import threading, webview, os, sys, platform, subprocess
from datetime import datetime
from flask import Flask, request, jsonify
import json, urllib.request, urllib.parse

app = Flask(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────
def get_data_path(filename):
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

DICTIONARY_PATH = get_data_path('dictionary.json')
_using_custom_dict = False

def get_ui_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'ui.html')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui.html')

# ── Default dictionary ────────────────────────────────────────────────────────
DEFAULT_DICTIONARY = {
    "hummus": "حمص",
    "moutabbal": "متبل",
    "eggplant raheb": "باذنجان الراهب",
    "mohamara": "محمرة",
    "goat labneh": "لبنة ماعز",
    "labneh": "لبنة",
    "shanklish": "شنكليش",
    "vine leaves in oil": "ورق عنب بالزيت",
    "hindbeh dandelion greens": "هندبة بالزيت",
    "hindbeh": "هندبة",
    "makdous": "مكدوس",
    "pickles": "مخلل",
    "vegetables": "خضار",
    "hummus with meat": "حمص باللحمة",
    "hummus babla": "حمص بيلة",
    "french fries": "بطاطا مقلية",
    "potatoes with garlic & coriander": "بطاطا بالثوم والكزبرة",
    "potatoes with garlic and coriander": "بطاطا بالثوم والكزبرة",
    "soujou": "سجق",
    "sausages": "نقانق",
    "ras asfour": "رأس عصفور",
    "goat liver": "كبدة ماعز",
    "chicken liver in pomegranate molasses": "كبدة دجاج بدبس الرمان",
    "tabbouleh": "تبولة",
    "tabboule": "تبولة",
    "fattouch": "فتوش",
    "fattoush": "فتوش",
    "cabbage salad": "سلطة ملفوف",
    "tomatoes and onions salad": "سلطة بندورة وبصل",
    "cucumber in laban": "خيار بلبن",
    "oriental salad": "سلطة عربية",
    "raw kibbeh": "كبة نية",
    "raw kebbeh": "كبة نية",
    "kebbeh nayeh": "كبة نية",
    "kibbeh nayeh": "كبة نية",
    "raw tenderloin": "فيليه نيء",
    "raw habra": "هبرة نية",
    "raw orfali": "أورفالي نيء",
    "raw liver": "كبدة نية",
    "raw kafta": "كفتة نية",
    "raw fitle": "فتلة نية",
    "fatteh makadem": "فتة مقادم",
    "fatteh hummus": "فتة حمص",
    "fatteh lsenet": "فتة لسانات",
    "meat stuffed vine leaves & zucchini with cutlets": "ورق عنب وكوسا محشية مع كستلاتة",
    "meat stuffed vine leaves & zucchini": "ورق عنب وكوسا محشية",
    "meat stuffed vine leaves": "ورق عنب محشي باللحمة",
    "vine leaves": "ورق عنب",
    "kebbeh labanieh zghertewiye": "كبة لبنية زغرتاوية",
    "kebbeh labaniyeh zghertewiye": "كبة لبنية زغرتاوية",
    "kebbeh labanieh": "كبة لبنية",
    "shish barak": "شيش برك",
    "kebbeh & shish barak in laban": "كبة وشيش برك باللبن",
    "fawaregh stuffed sheep sausages": "فوارغ",
    "fawaregh": "فوارغ",
    "fried fawaregh": "فوارغ مقلية",
    "lsenet": "لسانات",
    "nikhaat": "نخاعات",
    "makadem": "مقادم",
    "nifa": "نيفا",
    "taouk skewers": "أسياخ طاووق",
    "grilled kafta": "كفتة مشوية",
    "kafta": "كفتة",
    "grilled meat": "لحمة مشوية",
    "arayes kafta": "عرايس كفتة",
    "mixed grill": "مشاوي مشكلة",
    "shish taouk": "شيش طاووق",
    "kebbeh zghertawiye": "كبة زغرتاوية",
    "kebbeh zghertewiye stuffed with fat": "كبة بالدهن",
    "kebbeh zghertewiye stuffed with meat": "كبة باللحمة",
    "kebbeh zghertewiye stuffed with labneh": "كبة باللبنة",
    "kebbeh zghertewiye stuffed with butter": "كبة بالزبدة",
    "kebbeh sajiyeh": "كبة صاجية",
    "baked meat stuffed kebbeh in a tray": "كبة بالصينية باللحمة",
    "baked kebbeh with onions in a tray": "كبة بالصينية بالبصل",
    "baked kebbeh in oil in a tray": "كبة بالزيت بالصينية",
    "mini kebbeh empty": "كبة فارغة",
    "mini kebbeh stuffed with meat": "كبة محشية باللحمة",
    "sambousek": "سمبوسك",
    "sambousek stuffed with cheese": "سمبوسك بالجبنة",
    "rkakat cheese": "رقاقات جبنة",
    "kebbeh pumpkin": "كبة لقطين",
    "shish barak pack": "شيش برك",
    "smidiyeh": "سميدية",
    "mafrouket festo2": "مفروكة فستق",
    "mafrouket fistok": "مفروكة فستق",
    "biscuits and raha": "بسكوت وراحة",
    "carob molasses": "دبس الخروب",
    "debs kharroub": "دبس الخروب",
    "halewe": "حلاوة",
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
PENDING_ORDER = None

# ── Translation ───────────────────────────────────────────────────────────────
def translate_word(name):
    key = name.lower().strip()
    if key in DICTIONARY:
        return DICTIONARY[key]
    for k, v in DICTIONARY.items():
        if k in key or key in k:
            return v
    try:
        params = urllib.parse.urlencode({'q': name, 'langpair': 'en|ar'})
        url = f'https://api.mymemory.translated.net/get?{params}'
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
            result = data['responseData']['translatedText']
            if result and result != name:
                return result
    except Exception:
        pass
    return name

def translate_items(items):
    for item in items:
        item['arabic_name'] = translate_word(item['name'])
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
        note = f'<div class="note">{item["comment"]}</div>' if item.get('comment') else ''
        rows += f'''
        <div class="item">
          <div class="row">
            <span class="qty">{item["qty"]}</span>
            <span class="iname">{item["arabic_name"]}</span>
          </div>
          {note}
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
def run_flask():
    app.run(host='127.0.0.1', port=5001, debug=False, use_reloader=False)

if __name__ == '__main__':
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
