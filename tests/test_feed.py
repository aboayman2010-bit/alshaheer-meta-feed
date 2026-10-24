import unittest
from export_feed import membership, make_feed, SAVINGS_ID

class TestFeed(unittest.TestCase):
    def test_category(self):
        self.assertEqual(membership({"categories": [{"id": SAVINGS_ID}]}), {SAVINGS_ID})
        self.assertIsNone(membership({"name": "unknown"}))
    def test_filter(self):
        rows = {str(i): {"id": str(i), "categories": [{"id": SAVINGS_ID if i < 42 else "other"}]} for i in range(600)}
        data, report = make_feed(rows)
        self.assertEqual(report["confirmed_savings"], 42)
        self.assertIn("0,وفر اكثر", data.decode("utf-8-sig"))
        self.assertIn("500,other", data.decode("utf-8-sig"))
    def test_missing_categories_blocks(self):
        rows = {str(i): {"id": str(i)} for i in range(600)}
        with self.assertRaises(RuntimeError):
            make_feed(rows)

if __name__ == "__main__":
    unittest.main()
