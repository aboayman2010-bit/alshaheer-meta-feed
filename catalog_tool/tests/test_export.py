import sys
import tempfile
import unittest
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from catalog_tool.export import evaluate, export

FRIDGE = {"id": "fridge-id", "name": "منتجات الثلاجة", "slug": "fridge"}
SPICES = {"id": "spices-id", "name": "عطارة و توابل و خلطات", "slug": "SPICES"}

def product(pid, name, categories=None, **updates):
    row = {"id": pid, "name": name, "categories": categories if categories is not None else [FRIDGE],
           "hidden": False, "track_stock": True, "quantity": 3, "price": 50,
           "thumb": "https://example.com/product.png"}
    row.update(updates)
    return row

class CatalogTests(unittest.TestCase):
    def test_hidden_never_enters_magazine(self):
        catalog, rows = evaluate([
            product("1", "Visible"), product("2", "Hidden", hidden=True),
            product("3", "Insufficient", quantity=1),
            product("4", "No image", thumb=""),
            product("5", "No price", price=0),
            product("6", "No stock tracking", track_stock=False, quantity=0),
            product("7", "Uncertain visibility", hidden=None),
            product("8", "Multiple categories", categories=[FRIDGE, SPICES]),
        ], public_ids={"1", "2", "3", "4", "5", "6", "7", "8"})
        self.assertTrue(rows["1"]["magazine_eligible"])
        self.assertTrue(rows["6"]["magazine_eligible"])
        self.assertTrue(rows["8"]["magazine_eligible"])
        for pid in ("2", "3", "4", "5", "7"):
            self.assertFalse(rows[pid]["magazine_eligible"])
        self.assertEqual(rows["2"]["status"], "hidden")
        self.assertEqual(rows["7"]["status"], "unknown")
        self.assertEqual(len(catalog), 2)

    def test_no_public_proof_blocks_all_magazine_products(self):
        _, rows = evaluate([product("1", "Apparently visible")])
        self.assertFalse(rows["1"]["magazine_eligible"])
        self.assertIn("public_listing_unverified", rows["1"]["reasons"])
        _, checked = evaluate([product("1", "Apparently visible")], public_ids={"other-id"})
        self.assertFalse(checked["1"]["magazine_eligible"])
        self.assertIn("not_on_public_listing", checked["1"]["reasons"])

    def test_audit_includes_hidden_but_magazine_does_not(self):
        with tempfile.TemporaryDirectory() as folder:
            export([product("1", "Published"), product("2", "Secret", hidden=True),
                    product("3", "Spice", categories=[SPICES])], folder, public_ids={"1", "2", "3"})
            cats = json.loads((Path(folder) / "categories.json").read_text())
            fridge = next(c for c in cats if c["slug"] == "fridge")
            self.assertEqual(fridge["total"], 2)
            self.assertEqual(fridge["hidden"], 1)
            good = json.loads((Path(folder) / "magazine_ready" / (fridge["file_stem"] + ".json")).read_text())
            audit = json.loads((Path(folder) / "audit_all" / (fridge["file_stem"] + ".json")).read_text())
            self.assertEqual([x["name"] for x in good["products"]], ["Published"])
            self.assertEqual(len(audit["products"]), 2)

if __name__ == "__main__":
    unittest.main()
