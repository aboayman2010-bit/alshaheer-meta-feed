import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from magazine.build_magazine import image_url, money, choose, norm
from export_feed import SAVINGS_ID
def fixture():
    names=["جبنة", "زيت", "بسكوت", "برجر"]
    p={}
    for i in range(90):
        name=f"منتج {names[((i-12)//18)%4]} {i}" if i>=12 else f"منتج توفير {i}"
        categories=[{"id":SAVINGS_ID,"name":"وفر أكثر"}] if i<12 else [{"id":str(i),"name":"أطعمة"}]
        p[str(i)]={"id":str(i),"name":name,"sale_price":30+i,
           "thumb":f"https://images.example.com/{i}.jpg","quantity":3,
           "is_hidden":False,"categories":categories}
    return p
class Tests(unittest.TestCase):
    def test_image_uses_https(self):
        self.assertIsNone(image_url("http://localhost/p.jpg"))
        self.assertEqual(image_url([{"src":"https://img.example.org/a.png"}]),"https://img.example.org/a.png")
    def test_out_of_stock_hidden_or_missing_price_excluded(self):
        p=fixture()["0"];p["quantity"]=0
        self.assertIsNone(norm(p))
        p["quantity"]=3;p["is_hidden"]=True
        self.assertIsNone(norm(p))
        p["is_hidden"]=False;p["sale_price"]=0
        self.assertIsNone(norm(p))
    def test_complete_magazine_selection(self):
        result,stats=choose(fixture(),2026,43)
        ids=[p["id"] for _,group in result for p in group]
        self.assertEqual(len(result),6)
        self.assertEqual(len(ids),36)
        self.assertEqual(len(set(ids)),36)
        self.assertTrue(all(p["savings"] for _,group in result[:2] for p in group))
    def test_non_sale_price_fallback(self):
        p=fixture()["0"];p.pop("sale_price");p["price"]=56
        self.assertEqual(norm(p)["price"],56)
if __name__=="__main__":unittest.main()
