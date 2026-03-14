import threading, webview, os, sys
from flask import Flask, request, jsonify
import re, json, urllib.request, urllib.parse

app = Flask(__name__)

DICTIONARY = {
   "Beirut Beer Light": "بيرة بيروت لايت",
"Beirut Beer": "بيرة بيروت",
"Mezza Beer": "بيرة مزة",
"Iced Tea": "شاي مثلج",
"Rim Sparkling Water": "مياه ريم الغازية",
"Soft Drinks": "مشروبات غازية",
"Tannourine Water": "مياه تنورين",
"Hindbeh Dandelion Greens": "هندبة",
"Moutabbal": "متبل",
"Pickles": "مخللات",
"Vegetables": "خضار",
"Raheb Eggplant": "راهب",
"Goat Labneh": "لبنة ماعز",
"Makdous (3 To 4 Pieces)": "مكدوس",
"Shanklish": "شنكليش",
"Mouhammara": "محمرة",
"Jebne Darfiyeh": "جبنة ضرفية",
"Yogurt": "لبن",
"Vine Leaves In Oil": "ورق عريش بالزيت",
"Hummus": "حمص",
"Nifa": "نيفة",
"Lsenet": "لسانات",
"Nkhahaat": "نخاعات",
"Kebbeh Labanieh Zghertewiye": "كبة لبنية زغرتاوية",
"Makadem": "مقادم",
"Meat Stuffed Vine Leaves & Zuchini With Cutlets": "ورق عريش وكوسا محشي مع كستلاتة",
"Meat Stuffed Vine Leaves & Zuchini": "ورق عريش وكوسا محشي",
"Fried Fawaregh": "فوارغ مقلية",
"Shish Barak": "شيش برك",
"Kebbeh & Shish Barak With Laban": "كبة وشيش برك باللبن",
"Meat Stuffed Vine Leaves": "ورق عريش محشي",
"Fawaregh": "فوارغ",
"Carob Molasses": "دبس الخروب",
"Smidiyeh": "سميدية",
"Halewe": "حلاوة",
"Biscuits & Raha": "بسكويت وراحة",
"Hummus Fatteh": "فتة حمص",
"Lsenet Fatteh": "فتة لسانات",
"Makadem Fatteh": "فتة مقادم",
"Grilled Kafta": "كفتة مشوية",
"Taouk": "تاووك",
"Grilled Meat": "لحم مشوي",
"Mixed Grills": "مشاوي مشكلة",
"Arayes Kafta": "عرايس كفتة",
"Ras Asfour": "لحمة رأس عصفور",
"Soujouk": "سجق",
"Chicken Liver In Pomegranate Molasses": "سودة دجاج بدبس الرمان",
"Makanek": "مقانق",
"Hummus With Meat": "حمص باللحم",
"Hummus Balila": "حمص بليلة",
"Goat Liver": "سودة ماعز مقلي",
"French Fries": "بطاطا مقلية",
"Potatoes With Garlic & Coriander": "بطاطا بالثوم والكزبرة",
"Kebbeh Zghertawiye": "كبة زغرتاوية",
"Kebbeh Sajiyeh": "كبة صاجية",
"Kebbeh With Oil": "كبة بالزيت",
"Baked Kebbeh With Onions In A Tray": "كبة بالصينية مع بصل و صنوبر",
"Baked Meat Stuffed Kebbeh In A Tray": "كبة محشية بالصينية",
"Sambousek": "سمبوسك",
"Cheese Rakakat": "رقاقات جبنة",
"Sambousek Stuffed With Cheese": "سمبوسك بالجبنة",
"Pumpkin Kebbeh": "كبة لقطين",
"Mini Kebbeh Stuffed With Meat": "كباكيب محشي",
"Mini Empty Kebbeh": "كباكيب فارغ",
"Moughrabieh": "مغربية",
"Aadas Bi Hamoud": "عدس بحامض",
"Kharouf Mehche": "خروف محشي",
"Mloukhieh Djej & Rice": "ملوخية دجاج وأرز",
"Lentil Soup": "شوربة عدس",
"Pumpkin Kebbeh In A Tray": "كبة لقطين بالصينية",
"Bacha w Assekrou": "باشا وعسكرو",
"Spaghetti Bachchamel": "سباغيتي بشاميل",
"Laban Emmo & Rice": "لبن إمه وأرز",
"Kebbeh Bil Labneh": "كبة باللبنة",
"Borghol aA Banadoura": "برغل على بندورة",
"Bazella Bil Lahme & Rice": "بازيلا باللحمة وأرز",
"Daoud Bacha & Rice": "داود باشا وأرز",
"Oriental Rice": "أرز شرقي",
"Tajen Samak": "طاجن سمك",
"Loubiyeh Bi Lahme & Rice": "لوبية باللحمة وأرز",
"Loubieh Bi Zeit": "لوبية بالزيت",
"Labniye W Shish Barak": "لبنية وشيش برك",
"Bamieh Bil Lahme & Rice": "بامية باللحمة وأرز",
"Koussa Bil Laban": "كوسا باللبن",
"Moujadara Bi Adas": "مجدرة بالعدس",
"Frikeh Djej": "فريكة دجاج",
"Djej W Batata Bil Forn": "دجاج وبطاطا بالفرن",
"Kafta Bil Sayniyeh & Rice": "كفتة بالصينية وأرز",
"Spaghetti Bi Laban": "سباغيتي باللبن",
"Fassoulia Bi Lahme & Rice": "فاصوليا باللحمة وأرز",
"Kebbeh Arnabieh & Rice": "كبة أرنبية وأرز",
"Maqloubeh Aubergines": "مقلوبة باذنجان",
"Mehchi Malfouf": "محشي ملفوف",
"Riz Aa Djej": "أرز على دجاج",
"Mousakaa Aubergines": "مسقعة باذنجان",
"Hrisse": "هريسة",
"Moujadara Zghertewiye": "مجدرة زغرتاوية",
"Siyadiyeh": "صيادية",
"Raw Liver": "سودة نية",
"Raw Orfali": "أورفلية",
"Raw Tebleh": "تابلة",
"Raw Habra": "هبرة",
"Raw Kafta": "كفتة نية",
"Raw Ftile": "فتيلة نية",
"Raw Kebbeh": "كبة نية",
"Cabbage Salad": "سلطة ملفوف",
"Fattouch": "فتوش",
"Oriental Salad": "سلطة عربية",
"Tabbouleh": "تبولة",
"Tomatoes & Onions Salad": "سلطة بندورة وبصل",
"Cucumber With Laban": "خيار باللبن",
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

def get_ui_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'ui.html')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui.html')

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
        os.startfile(tmp.name)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})

def build_receipt(d):
    rows = ''
    for item in d['items']:
        note = f'<div class="note">← {item["comment"]}</div>' if item.get('comment') else ''
        rows += f'''
        <div class="item">
          <div class="row">
            <span class="qty">{item["qty"]}</span>
            <span class="iname">{item["arabic_name"]}</span>
          </div>
          {note}
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
.hd{{text-align:center;padding-bottom:3mm;border-bottom:2px dashed #000}}
.logo{{font-size:20px;font-weight:900}}
.br{{font-size:12px;font-weight:600;margin-top:1mm}}
.toters{{font-size:18px;font-weight:900;color:#000;margin-top:2mm;letter-spacing:3px}}
.sched{{background:#000;color:#fff;text-align:center;padding:1mm;font-size:11px;font-weight:700;margin-top:1mm}}
.info{{padding:3mm 0;border-bottom:1px dashed #000}}
.ir{{display:flex;justify-content:space-between;margin-bottom:1.5mm;font-size:11px}}
.il{{color:#000}}
.iv{{font-weight:900;font-size:16px}}
.ih{{background:#000;color:#fff;text-align:center;padding:1.5mm;font-size:12px;font-weight:700;margin:2mm 0 0}}
.item{{padding:2.5mm 0;border-bottom:1px dotted #000}}
.row{{display:flex;align-items:center;gap:2mm}}
.qty{{background:#000;color:#fff;font-weight:900;font-size:16px;padding:0 2mm;border-radius:2px;flex-shrink:0;min-width:8mm;text-align:center;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.iname{{font-weight:700;font-size:16px}}
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
