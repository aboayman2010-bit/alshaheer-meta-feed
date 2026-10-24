"""Weekly 8-page JPG/PDF magazine from Easy Orders, for manual group sharing."""
import sys, os, io, re, json, random
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from PIL import Image, ImageDraw, ImageFont, ImageOps, features

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from export_feed import read_products, membership, SAVINGS_ID

OUT=ROOT/"magazine_output"
W,H=1080,1350
BG="#FAFBFC"; NAVY="#19314A"; BLUE="#2677B6"; RED="#D84D54"; SUB="#526476"
APP="https://play.google.com/store/apps/details?id=com.store.alshaheer"
SHOP="https://alshaheer.myeasyorders.com/"
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SECTIONS=[
 ("وفر أكثر",("savings",)),
 ("وفر أكثر",("savings",)),
 ("منتجات الثلاجة والألبان",("ثلاجة","جبن","لانشون","مخلل","ألبان","البان","لبن","زبادي","زبادى","بسطرم")),
 ("السلع الأساسية",("أرز","ارز","رز ","سكر","زيت","سمن","مكرون","دقيق","عدس","فول","بقول","ملح")),
 ("المشروبات والحلويات",("مشروب","عصير","مياه","غازية","بسكوت","شيبسي","شيبسى","شوكولات","حلويات","بوري","أوريو","كاراتيه","شاي","شاى","قهوة")),
 ("المجمدات والمتنوع",("مجمد","برجر","ستربس","استربس","فراخ","دجاج","فروزن","سجق","بسمة","بطاطس","لحوم","فريزر")),
]
def font(n,bold=False):
 return ImageFont.truetype(BOLD if bold else FONT,n)
def money(v):
 if v is None or isinstance(v,bool): return None
 try: d=Decimal(str(v).replace(",","").strip())
 except (InvalidOperation,ValueError): return None
 return d if d.is_finite() and d>0 else None
def image_url(obj):
 if isinstance(obj,str):
  u=obj.strip(); q=urlparse(u)
  return u if q.scheme=="https" and q.hostname and "." in q.hostname else None
 if isinstance(obj,dict):
  for key in ("url","src","image_url","original_url","thumb","image","path"):
   u=image_url(obj.get(key))
   if u:return u
 if isinstance(obj,list):
  for item in obj:
   u=image_url(item)
   if u:return u
 return None
def norm(p):
 if not isinstance(p,dict):return None
 if any(p.get(k) is True for k in ("is_hidden","hidden","deleted","is_deleted","archived")):return None
 if any(p.get(k) is False for k in ("is_active","active","is_visible","visible","available","in_stock")):return None
 # Easy Orders uses quantity=0 when stock tracking is disabled; do not mislabel it out-of-stock.
 if p.get("track_stock") is not False:
  for k in ("quantity","stock_quantity","stock","inventory_quantity"):
   if k in p and p[k] is not None:
    try:
     if Decimal(str(p[k]))<=1:return None
    except InvalidOperation:pass
    break
 name=next((p[k].strip() for k in ("name","title","product_name") if isinstance(p.get(k),str) and p[k].strip()),"")
 price=money(p.get("sale_price")) or money(p.get("price"))
 picture=None
 for k in ("thumb","image_url","image","thumbnail","images","product_images","photos"):
  picture=image_url(p.get(k))
  if picture:break
 if not (p.get("id") and name and price and picture):return None
 cat=p.get("categories",[])
 labels=[str(c.get("name",c.get("title",""))) for c in cat if isinstance(c,dict)] if isinstance(cat,list) else []
 for k in ("category","category_name"):
  v=p.get(k)
  labels.append(str(v.get("name","")) if isinstance(v,dict) else str(v or ""))
 cats=membership(p)
 return {"id":str(p["id"]),"name":name,"price":price,"image":picture,
  "search":(name+" "+" ".join(labels)).lower(),
  "savings":cats is not None and SAVINGS_ID in cats}
def choose(products,year,week):
 unique={}
 for p in (products.values() if isinstance(products,dict) else products):
  item=norm(p)
  if item:unique[item["id"]]=item
 eligible=list(unique.values())
 random.Random(f"alshaheer-{year}-W{week:02d}").shuffle(eligible)
 used=set(); sections=[]
 for label,terms in SECTIONS:
  if terms==("savings",):
   candidates=[p for p in eligible if p["savings"] and p["id"] not in used]
  else:
   candidates=[p for p in eligible if p["id"] not in used and any(t in p["search"] for t in terms)]
  if len(candidates)<6:raise ValueError(f"Not enough products for {label}: {len(candidates)} (need 6)")
  group=candidates[:6]
  used.update(p["id"] for p in group)
  sections.append((label,group))
 return sections,{"eligible":len(eligible),"confirmed_savings_eligible":sum(p["savings"] for p in eligible),"selected":len(used)}
def draw_text(d,x,y,s,size=30,color=NAVY,bold=False):
 d.text((x,y),str(s),font=font(size,bold),fill=color,direction="rtl",anchor="ra")
def title_fit(d,s,x,y,width):
 words=re.sub(r"\s+"," ",s).split()
 for sz in range(27,19,-1):
  if d.textlength(s,font=font(sz,True),direction="rtl")<=width:
   draw_text(d,x,y,s,sz,NAVY,True);return
 # Never remove words from product names: wrap instead.
 lines=[""]
 for word in words:
  t=(lines[-1]+" "+word).strip()
  if d.textlength(t,font=font(19,True),direction="rtl")<=width:lines[-1]=t
  else:lines.append(word)
 # Practical safety: refuse products requiring more than two lines.
 if len(lines)>2:raise ValueError("Product name cannot fit at readable size: "+s[:80])
 for i,line in enumerate(lines):draw_text(d,x,y+i*29,line,19,NAVY,True)
def frame(label,issue,page):
 im=Image.new("RGB",(W,H),BG);d=ImageDraw.Draw(im)
 d.rectangle((0,0,W,154),fill=NAVY)
 draw_text(d,1026,64,"هايبر الشهير",54,"white",True)
 draw_text(d,1026,124,label,28,"#DDEAF4")
 d.rounded_rectangle((50,177,1030,213),radius=12,fill="#ECF4FA")
 draw_text(d,997,181,f"مجلة عروض الشهير | العدد {issue}",21,NAVY)
 d.line((55,1287,W-55,1287),fill="#DDE4EB",width=2)
 draw_text(d,1025,1295,"المعلمين – شارع العطيفي – بجوار محطة المياه",21,SUB)
 d.text((55,1306),f"{page}/8",font=font(18,True),fill=SUB)
 return im,d
def download_image(url):
 req=Request(url,headers={"User-Agent":"Mozilla/5.0 (Alshaheer Magazine)"})
 with urlopen(req,timeout=18) as r:
  c=r.headers.get("content-type","").lower().split(";")[0]
  if c not in ("image/jpeg","image/png","image/webp","image/avif","application/octet-stream"):
   raise ValueError("Unexpected image content type")
  raw=r.read(6000001)
 if len(raw)>6000000:raise ValueError("Image too large")
 with Image.open(io.BytesIO(raw)) as obj:return ImageOps.exif_transpose(obj).convert("RGB")
def show_image(im,obj,bounds):
 x1,y1,x2,y2=bounds
 ImageDraw.Draw(im).rounded_rectangle(bounds,radius=14,fill="white")
 img=obj.copy();img.thumbnail((x2-x1-16,y2-y1-16),Image.Resampling.LANCZOS)
 im.paste(img,(int((x1+x2-img.width)/2),int((y1+y2-img.height)/2)))
def format_price(value):
 d=Decimal(value)
 return f"{d:,.0f}" if d==d.to_integral_value() else f"{d:,.2f}".rstrip("0").rstrip(".")
def product_page(label,items,issue,page,pictures):
 im,d=frame(label,issue,page)
 for i,p in enumerate(items):
  row,col=divmod(i,2)
  x=54+col*504;y=243+row*339
  d.rounded_rectangle((x,y,x+468,y+326),radius=21,fill="white",outline="#E3E9ED",width=2)
  title_fit(d,p["name"],x+450,y+30,430)
  show_image(im,pictures[p["id"]],(x+105,y+95,x+363,y+236))
  d.rounded_rectangle((x+18,y+255,x+450,y+310),radius=15,fill="#EAF3FA")
  draw_text(d,x+432,y+266,f"{format_price(p['price'])} جنيه",33,BLUE,True)
 return im
def cover(issue):
 im=Image.new("RGB",(W,H),BG);d=ImageDraw.Draw(im)
 d.rectangle((0,0,W,370),fill=NAVY)
 draw_text(d,1002,108,"هايبر الشهير",72,"white",True)
 draw_text(d,1002,230,"مجلة عروض الشهير",59,"white",True)
 draw_text(d,1002,312,f"العدد {issue} • 36 منتج مختار",30,"#C8E2F6")
 d.rounded_rectangle((78,425,1002,780),radius=34,fill="#ECF4FA")
 draw_text(d,950,521,"تسوّق وأنت في مكانك",45,NAVY,True)
 draw_text(d,950,613,"أسعار واضحة، ومنتجات من الهايبر",28,NAVY)
 draw_text(d,950,684,"وفر أكثر • الثلاجة • السلع الأساسية",28,BLUE,True)
 d.rounded_rectangle((78,840,1002,1110),radius=30,fill="white",outline="#DDE7EF",width=2)
 draw_text(d,950,930,"التوصيل داخل المعلمين 7 جنيه فقط",38,RED,True)
 draw_text(d,950,1014,"حمّل التطبيق وشوف باقي المنتجات",31,NAVY,True)
 d.line((78,1176,1002,1176),fill="#DDE4EB",width=2)
 draw_text(d,1002,1230,"المعلمين – شارع العطيفي – بجوار محطة المياه",24,SUB)
 draw_text(d,1002,1305,"alshaheer.myeasyorders.com",26,BLUE,True)
 return im
def endpage():
 im=Image.new("RGB",(W,H),BG);d=ImageDraw.Draw(im)
 d.rectangle((0,0,W,360),fill=NAVY)
 draw_text(d,1005,120,"هايبر الشهير",72,"white",True)
 draw_text(d,1005,248,"عروضنا مستمرة",51,"white",True)
 draw_text(d,1005,317,"مشاهدة باقي المنتجات وطلبها من التطبيق",25,"#CDE5F7")
 d.rounded_rectangle((65,440,1015,845),radius=34,fill="#ECF4FA")
 draw_text(d,970,542,"اطلب من موبايلك",50,NAVY,True)
 draw_text(d,970,620,"كأنك بتتسوق داخل الهايبر",38,NAVY,True)
 draw_text(d,970,710,"حمّل تطبيق هايبر الشهير",31,BLUE,True)
 draw_text(d,970,778,"من Google Play",29,SUB)
 d.rounded_rectangle((65,906,1015,1090),radius=28,fill="white",outline="#DCE5ED",width=2)
 draw_text(d,980,976,"التوصيل داخل المعلمين 7 جنيه",32,RED,True)
 draw_text(d,980,1044,"المعلمين – شارع العطيفي – بجوار محطة المياه",22,SUB)
 draw_text(d,1014,1220,"الموقع: alshaheer.myeasyorders.com",25,BLUE,True)
 draw_text(d,1014,1285,"التطبيق: ابحث عن هايبر الشهير على Google Play",22,NAVY)
 return im
def generate(products,out=OUT,now=None,loader=download_image):
 now=now or datetime.now(timezone.utc)
 year,week,_=now.isocalendar();issue=f"{year}-{week:02d}"
 sections,stats=choose(products,year,week)
 chosen=[p for _,v in sections for p in v]
 pics={}
 for p in chosen:
  try:pics[p["id"]]=loader(p["image"])
  except Exception as exc:raise RuntimeError(f"Cannot load image for product {p['id']}: {type(exc).__name__}") from None
 if not features.check("raqm"):raise RuntimeError("Arabic text shaping unavailable: libraqm required")
 imgs=[cover(issue)]
 for i,(label,items) in enumerate(sections,start=2):imgs.append(product_page(label,items,issue,i,pics))
 imgs.append(endpage())
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 for i,img in enumerate(imgs,start=1):
  img.save(out/f"page-{i:02d}.jpg","JPEG",quality=88,optimize=True,subsampling=0)
 imgs[0].save(out/"alshaheer-magazine.pdf",format="PDF",save_all=True,append_images=imgs[1:],resolution=125)
 post=("عرض خاص 🛒✨\nمجلة عروض هايبر الشهير وصلت! 36 منتج مختار وأسعارها في الصور 👇\n"
       "شوف الصور، وقارن الأسعار، واطلب من موبايلك كأنك بتتسوق داخل الهايبر 📱✨\n"
       f"حمّل التطبيق: {APP}\nالموقع: {SHOP}\n"
       "🚚 التوصيل داخل المعلمين بـ7 جنيه فقط\n"
       "📍 المعلمين – شارع العطيفي – بجوار محطة المياه\n"
       "الأسعار تخضع للتحديث والتوفر وقت الطلب.\n")
 (out/"post.txt").write_text(post,encoding="utf-8")
 report={"issue":issue,"generated_utc":now.isoformat(),"source_products":len(products),
   **stats,"pages":8,"section_counts":{f"{i+2}: {label}":len(group) for i,(label,group) in enumerate(sections)},
   "selected_ids":[p["id"] for p in chosen]}
 (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
 print("MAGAZINE SUCCESS",json.dumps({k:v for k,v in report.items() if k!="selected_ids"},ensure_ascii=False),flush=True)
 return report
def main():
 key=os.getenv("EASYORDERS_API_KEY","").strip()
 if not key:raise RuntimeError("Missing EASYORDERS_API_KEY")
 generate(read_products(key))
if __name__=="__main__":
 try:main()
 except Exception as e:
  key=os.getenv("EASYORDERS_API_KEY","")
  print("MAGAZINE FAILED SAFELY:",str(e).replace(key,"[REDACTED]") if key else str(e),file=sys.stderr)
  sys.exit(1)
