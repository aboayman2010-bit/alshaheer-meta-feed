"""Generate one branded 1080x1350 magazine prototype from EasyOrders public product fields."""
import json
import html
from pathlib import Path

def image_url(p):
    def candidate(v):
        if isinstance(v, str) and v.startswith(("https://", "http://")) and any(t in v.lower() for t in (".jpg",".png",".jpeg",".webp",".avif","image","upload","cdn")):
            return v
        if isinstance(v, dict):
            for k in ("url", "src", "image_url", "secure_url", "original", "path", "medium", "large"):
                z = candidate(v.get(k))
                if z: return z
        if isinstance(v, list):
            for item in v:
                z = candidate(item)
                if z: return z
        return None
    for k in ("images","image","main_image","thumbnail","featured_image","image_url","cover","photos","media"):
        v = candidate(p.get(k))
        if v: return v
    return None

def number(x):
    try:
        if isinstance(x,dict): x=x.get("amount",x.get("value"))
        return float(str(x).replace(",",""))
    except (ValueError, TypeError): return None

def make_page(products, out):
    found=[]
    for p in products.values():
        name = p.get("name") or p.get("title") or p.get("product_name") or ""
        img = image_url(p)
        price = next((number(p.get(k)) for k in ("sale_price","price","selling_price","final_price","retail_price") if number(p.get(k)) is not None),None)
        old = next((number(p.get(k)) for k in ("compare_at_price","old_price","original_price","regular_price") if number(p.get(k)) is not None),None)
        if not isinstance(name,str) or not name.strip() or not img or price is None or price<=0: continue
        if old is not None and old<=price: old=None
        found.append({"name":name.strip(),"image":img,"new":int(price) if price.is_integer() else round(price,2),"old":int(old) if old is not None and old.is_integer() else old})
        if len(found)==8: break
    if len(found)<8: raise RuntimeError("Not enough products with usable public images and prices for eight-card demo")
    data=json.dumps(found,ensure_ascii=False).replace("<","\\u003c")
    template=r'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>هايبر الشهير | صفحة تجريبية للمجلة</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#dadada;font-family:Tahoma,Arial,sans-serif;color:#4f0806}
.toolbar{max-width:1080px;margin:10px auto;display:flex;gap:8px;justify-content:center;align-items:center;font-size:15px}.toolbar button{background:#ad0c11;color:white;border:0;border-radius:8px;padding:10px 18px;cursor:pointer}
.frame{width:1080px;height:1350px;margin:auto;position:relative;overflow:hidden;background:radial-gradient(ellipse at 50% 40%,#e82427 0,#a20714 64%,#63040b 100%);padding:22px 22px 15px;box-shadow:0 9px 38px #0005;direction:ltr}
.frame:before{content:"";position:absolute;inset:9px;border:3px solid #eeba42;border-radius:23px;pointer-events:none}
.heading{height:147px;display:flex;gap:13px;direction:ltr;align-items:center;position:relative;z-index:1}
.slogan,.brand{height:107px;display:flex;align-items:center;justify-content:center;text-align:center;border:5px solid #f6c85b;box-shadow:0 7px 2px #580600, inset 0 3px 18px #fff4;border-radius:22px;font-weight:900;white-space:nowrap}
.slogan{width:49%;background:linear-gradient(#b9131a,#750609);color:#ffde7a;font-size:63px;text-shadow:3px 4px #410000}
.brand{width:51%;background:linear-gradient(#fffbd8,#ffcf63);color:#a90816;font-size:62px;text-shadow:2px 3px #fff;position:relative}
.brand:before{content:"♛";position:absolute;top:-38px;font-size:49px;color:#ffcc55;text-shadow:2px 2px #690000}
.cols{display:grid;grid-template-columns:1.17fr 1fr 1fr;gap:12px;height:1005px;position:relative;z-index:1}
.column{display:grid;gap:12px;min-height:0}.column.large{grid-template-rows:1fr 1fr}.column.small{grid-template-rows:repeat(3,1fr)}
.card{position:relative;min-height:0;background:linear-gradient(145deg,#fff,#fff9ef);border:5px solid #f6bf4c;outline:2px solid #930509;border-radius:20px;overflow:hidden;box-shadow:inset 0 0 12px #f6e4ae,0 5px 9px #650000}
.card .name{position:absolute;left:8px;right:8px;top:11px;direction:rtl;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:center;font-size:26px;font-weight:900;color:#8e0a11}
.card.large .name{font-size:34px;top:19px}
.card .photo{position:absolute;top:19%;left:4%;height:54%;width:92%;object-fit:contain}
.card.large .photo{top:17%;height:63%}
.unit{position:absolute;left:10px;bottom:78px;background:#16873c;color:#fff;border-radius:12px;padding:3px 12px;font-size:18px;font-weight:bold;direction:rtl}
.card.large .unit{font-size:22px;bottom:91px}
.pricebox{position:absolute;bottom:9px;left:7px;right:7px;display:flex;align-items:center;justify-content:center;gap:6px;direction:ltr}
.old{background:#ffe0a0;border:2px solid #c9973b;border-radius:9px;font-size:23px;text-align:center;min-width:75px;color:#222;padding:3px 5px;position:relative}
.old del{text-decoration-color:#c5141d;text-decoration-thickness:3px}
.now{flex:1;background:linear-gradient(#e52a30,#96000d);border:3px solid #efc34f;border-radius:11px;color:white;min-height:64px;text-align:center;display:flex;flex-direction:column;align-items:center;justify-content:center;font-weight:bold}
.now small{font-size:15px;color:#ffe792}.now strong{font-size:35px;line-height:1.05}
.large .old{font-size:29px;min-width:104px}.large .now{min-height:76px}.large .now strong{font-size:45px}
.footer{height:145px;padding-top:17px;display:flex;direction:ltr;gap:14px;position:relative;z-index:1}
.footer>div{flex:1;text-align:center;background:linear-gradient(#d21c24,#850407);border:3px solid #f2c451;border-radius:20px;color:#fff5cd;padding:11px;font-size:25px;font-weight:900;direction:rtl;box-shadow:inset 0 1px 10px #ff9a783d}
.footer .small{font-size:20px;margin-top:8px;color:white}
.note{text-align:center;margin:11px;color:#555;font-size:15px}
@media(max-width:1100px){.frame{transform-origin:top left;transform:scale(var(--scale,1));margin:0 auto}.framewrap{height:calc(1350px * var(--scale,1));width:calc(1080px * var(--scale,1));margin:auto}}
@media print{@page{size:1080px 1350px;margin:0}body{background:white}.toolbar,.note{display:none}.framewrap{width:1080px!important;height:1350px!important}.frame{transform:none!important;box-shadow:none}}
</style></head><body>
<div class="toolbar">معاينة صفحة تجريبية من منتجات المتجر الحقيقية <button onclick="window.print()">طباعة / حفظ PDF</button></div>
<div class="framewrap"><main class="frame"><header class="heading"><div class="slogan">ملوك التوفير</div><div class="brand">هايبر الشهير</div></header>
<section class="cols"><div class="column large" id="left"></div><div class="column small" id="middle"></div><div class="column small" id="right"></div></section>
<footer class="footer"><div>📱 لينك تحميل تطبيق هايبر الشهير<div class="small">أول تعليق</div></div><div>🚚 خدمة التوصيل<div class="small">المعلمين 7 جنيه - الأربعين 10 جنيه</div></div></footer></main></div>
<p class="note">هذه تجربة أولى آلية للتصميم؛ الأسعار تعرض كما وردت من EasyOrders، ولا يُفترض وجود خصم إذا لم يتوفر سعر سابق موثوق.</p>
<script>const products=__DATA__;
function safe(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function card(p){let old=p.old==null?'': '<div class="old"><del>'+safe(p.old)+'</del></div>';return '<article class="card"><div class="name" title="'+safe(p.name)+'">'+safe(p.name)+'</div><img class="photo" src="'+safe(p.image)+'" alt="'+safe(p.name)+'"><span class="unit">قطعة</span><div class="pricebox">'+old+'<div class="now"><small>الآن فقط</small><strong>'+safe(p.new)+'</strong></div></div></article>'}
document.getElementById('left').innerHTML=products.slice(0,2).map(card).join('');
document.getElementById('middle').innerHTML=products.slice(2,5).map(card).join('');
document.getElementById('right').innerHTML=products.slice(5,8).map(card).join('');
function resize(){document.documentElement.style.setProperty('--scale',Math.min(1,(window.innerWidth-12)/1080))}
window.addEventListener('resize',resize);resize();
</script></body></html>'''
    out.mkdir(exist_ok=True)
    (out / "magazine-demo.html").write_text(template.replace("__DATA__",data),encoding="utf-8")
    print("Magazine demo: 8 store products selected")
