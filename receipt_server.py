from flask import Flask, request, jsonify
import re, json, urllib.request, urllib.parse, os

app = Flask(__name__)

DICTIONARY = {
    # COLD MEZZA
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
    # HOT MEZZA
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
    # SALADS
    "tabbouleh": "تبولة",
    "tabboule": "تبولة",
    "fattouch": "فتوش",
    "fattoush": "فتوش",
    "cabbage salad": "سلطة ملفوف",
    "tomatoes and onions salad": "سلطة بندورة وبصل",
    "cucumber in laban": "خيار بلبن",
    "oriental salad": "سلطة عربية",
    # RAW MEATS
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
    # FATTEH
    "fatteh makadem": "فتة مقادم",
    "fatteh hummus": "فتة حمص",
    "fatteh lsenet": "فتة لسانات",
    # CUISINE ZAMEN
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
    # FROM THE GRILL
    "taouk skewers": "أسياخ طاووق",
    "grilled kafta": "كفتة مشوية",
    "kafta": "كفتة",
    "grilled meat": "لحمة مشوية",
    "arayes kafta": "عرايس كفتة",
    "mixed grill": "مشاوي مشكلة",
    "shish taouk": "شيش طاووق",
    # KEBBEH
    "kebbeh zghertawiye": "كبة زغرتاوية",
    "kebbeh zghertewiye stuffed with fat": "كبة بالدهن",
    "kebbeh zghertewiye stuffed with meat": "كبة باللحمة",
    "kebbeh zghertewiye stuffed with labneh": "كبة باللبنة",
    "kebbeh zghertewiye stuffed with butter": "كبة بالزبدة",
    "kebbeh sajiyeh": "كبة صاجية",
    "baked meat stuffed kebbeh in a tray": "كبة بالصينية باللحمة",
    "baked kebbeh with onions in a tray": "كبة بالصينية بالبصل",
    "baked kebbeh in oil in a tray": "كبة بالزيت بالصينية",
    # MOUAJANAT
    "mini kebbeh empty": "كبة فارغة",
    "mini kebbeh stuffed with meat": "كبة محشية باللحمة",
    "sambousek": "سمبوسك",
    "sambousek stuffed with cheese": "سمبوسك بالجبنة",
    "rkakat cheese": "رقاقات جبنة",
    "kebbeh pumpkin": "كبة لقطين",
    "shish barak pack": "شيش برك",
    # DESSERTS
    "smidiyeh": "سميدية",
    "mafrouket festo2": "مفروكة فستق",
    "mafrouket fistok": "مفروكة فستق",
    "biscuits and raha": "بسكوت وراحة",
    "carob molasses": "دبس الخروب",
    "debs kharroub": "دبس الخروب",
    "halewe": "حلاوة",
}

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

@app.route('/')
def index():
    ui_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui.html')
    with open(ui_path, encoding='utf-8') as f:
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
    return build_receipt(request.json)

def build_receipt(d):
    rows = ''
    for item in d['items']:
        parts = []
        if item.get('variant'):    parts.append(item['variant'])
        if item.get('preference'): parts.append(item['preference'])
        detail = f'<div class="det" dir="ltr">{" · ".join(parts)}</div>' if parts else ''
        note = f'<div class="note">← {item["comment"]}</div>' if item.get('comment') else ''
        rows += f'''
        <div class="item">
          <div class="row">
            <span class="qty">{item["qty"]}</span>
            <span class="iname">{item["arabic_name"]}</span>
          </div>
          {detail}{note}
        </div>'''

    sched = '<div class="sched">مجدول ⏰</div>' if d.get('scheduled') else ''
    time_lbl = 'تجهيز قبل' if d.get('scheduled') else 'وقت التجهيز'

    return f'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
*{{margin:0;padding:0;box-sizing:border-box;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
@page{{size:72mm auto;margin:0}}
body{{font-family:'Cairo',Arial,sans-serif;width:72mm;margin:0 auto;color:#000;font-size:11px;direction:rtl}}
.r{{padding:4mm}}
.hd{{text-align:center;padding-bottom:3mm;border-bottom:2px dashed #333}}
.logo{{font-size:20px;font-weight:900}}
.br{{font-size:12px;font-weight:600;margin-top:1mm}}.toters{{font-size:18px;font-weight:900;color:#000;margin-top:2mm;letter-spacing:3px}}
.sched{{background:#e65100;color:#fff;text-align:center;padding:1mm;font-size:11px;font-weight:700;margin-top:1mm;border-radius:2px}}
.info{{padding:3mm 0;border-bottom:1px dashed #aaa}}
.ir{{display:flex;justify-content:space-between;margin-bottom:1.5mm;font-size:11px}}
.il{{color:#000}}
.iv{{font-weight:700;font-size:13px}}
.ih{{background:#111;color:#fff;text-align:center;padding:1.5mm;font-size:12px;font-weight:700;margin:2mm 0 0}}
.item{{padding:2.5mm 0;border-bottom:1px dotted #ccc}}
.row{{display:flex;align-items:center;gap:2mm}}
.qty{{background:#111;color:#fff;font-weight:900;font-size:16px;padding:0 2mm;border-radius:2px;flex-shrink:0;min-width:8mm;text-align:center}}
.iname{{font-weight:700;font-size:16px}}
.det{{font-size:10px;color:#000;margin-top:.5mm;margin-right:6mm}}
.note{{font-size:10px;color:#000;font-style:italic;margin-top:.5mm;margin-right:6mm;border-right:2px solid #000;padding-right:1.5mm}}
.ft{{text-align:center;margin-top:4mm;padding-top:3mm;border-top:2px dashed #000;font-size:10px;color:#000}}
.ft b{{font-size:13px;color:#000}}
</style></head>
<body>
<div class="r">
  <div class="hd">
    <div class="logo">كبة زمن</div>
    <div class="br">فرع الأشرفية</div>
    <div class="toters">TOTERS</div>
    {sched}
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
