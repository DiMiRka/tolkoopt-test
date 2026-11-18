import asyncio
import unittest
from decimal import Decimal

from starter import recommend_price, sample_fetch_offers


def source(offers, status="success"):
    async def fetch():
        return {"status": status, "offers": offers}
    return fetch


def offer(price, seller="PARTS", days=3):
    return {"seller": seller, "price": Decimal(price), "delivery_days": days}


class RecommendPriceTest(unittest.IsolatedAsyncioTestCase):
    async def test_sample(self):
        result = await recommend_price(sample_fetch_offers, Decimal("4900.00"), Decimal("4500.00"))
        self.assertEqual(result["price"], Decimal("4728.00"))
        self.assertIsInstance(result["price"], Decimal)
        self.assertEqual(result["decision"], "APPLY")

    async def test_timeout_holds_current_price(self):
        async def slow():
            await asyncio.sleep(1)
            return {"status": "success", "offers": [offer("100.00")]}

        result = await recommend_price(slow, Decimal("500.00"), Decimal("1.00"), timeout_s=0.05)
        self.assertEqual((result["price"], result["decision"]), (Decimal("500.00"), "HOLD"))

    async def test_source_error_holds_current_price(self):
        async def broken():
            raise ConnectionError("down")

        result = await recommend_price(broken, Decimal("500.00"), Decimal("1.00"))
        self.assertEqual((result["price"], result["decision"]), (Decimal("500.00"), "HOLD"))

    async def test_partial_status_holds(self):
        result = await recommend_price(source([offer("490.00")], status="partial"), Decimal("500.00"), Decimal("1.00"))
        self.assertEqual((result["price"], result["decision"]), (Decimal("500.00"), "HOLD"))

    async def test_no_suitable_offers_holds_even_below_min_price(self):
        offers = [offer("300.00", seller="MyShop"), offer("300.00", days=None), offer("300.00", days=7)]
        result = await recommend_price(source(offers), Decimal("400.00"), Decimal("450.00"))
        self.assertEqual((result["price"], result["decision"]), (Decimal("400.00"), "HOLD"))

    async def test_delivery_six_days_is_included(self):
        result = await recommend_price(source([offer("1000.00", days=6)]), Decimal("1000.00"), Decimal("1.00"))
        self.assertEqual(result["price"], Decimal("985.00"))

    async def test_rounds_down_to_kopeck(self):
        result = await recommend_price(source([offer("1000.99")]), Decimal("1000.00"), Decimal("1.00"))
        self.assertEqual(result["price"], Decimal("985.97"))

    async def test_min_price_is_floor(self):
        result = await recommend_price(source([offer("400.00")]), Decimal("500.00"), Decimal("450.00"))
        self.assertEqual((result["price"], result["decision"]), (Decimal("450.00"), "APPLY"))

    async def test_exactly_30_percent_up_applies(self):
        result = await recommend_price(source([offer("100.00")]), Decimal("1000.00"), Decimal("1300.00"))
        self.assertEqual((result["price"], result["decision"]), (Decimal("1300.00"), "APPLY"))

    async def test_over_30_percent_up_needs_review(self):
        result = await recommend_price(source([offer("100.00")]), Decimal("1000.00"), Decimal("1300.01"))
        self.assertEqual((result["price"], result["decision"]), (Decimal("1300.01"), "REVIEW"))

    async def test_exactly_30_percent_down_applies(self):
        result = await recommend_price(source([offer("710.66")]), Decimal("1000.00"), Decimal("1.00"))
        self.assertEqual((result["price"], result["decision"]), (Decimal("700.00"), "APPLY"))

    async def test_over_30_percent_down_needs_review(self):
        result = await recommend_price(source([offer("710.65")]), Decimal("1000.00"), Decimal("1.00"))
        self.assertEqual((result["price"], result["decision"]), (Decimal("699.99"), "REVIEW"))


if __name__ == "__main__":
    unittest.main()
