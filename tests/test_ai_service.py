import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.infrastructure.ai.cache import AiMemoryCache
from backend.infrastructure.ai.fallbacks import (
    generate_sku_analysis_fallback,
    generate_supplier_letter_fallback,
    generate_supplier_summary_fallback,
)
from backend.infrastructure.ai.schemas import (
    SkuAnalysisRequest,
    SkuAnalysisResponse,
    SupplierLetterRequest,
    SupplierLetterResponse,
    SupplierSummaryRequest,
    SupplierSummaryResponse,
)
from backend.infrastructure.ai.service import AiProcurementService


class AiServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sample_sku_req = SkuAnalysisRequest(
            id="010500004_",
            sku="010500004_",
            vendor_code="MVA20-1-006-C",
            item_name="ВА47-29 (1ф) 6А IEK (12/144)",
            category="Модульное оборудование",
            supplier_name="IEK Казахстан",
            unit="шт",
            current_stock=140.0,
            in_transit=1200.0,
            transit_details="1 200 шт. по накл. ПП УТ-7848",
            daily_demand=45.2,
            days_of_stock=3.1,
            season_factor=1.242,
            calculated_need=600.0,
            adjusted_need=600.0,
            package_multiplicity=12.0,
            moq=12.0,
            unit_price=850.0,
            total_cost=510000.0,
            urgency="CRITICAL",
            reasoning="Остаток 140 исчерпается через 3 дня.",
            has_whale_outlier=False,
            stockout_recovered=True,
        )

        self.sample_summary_req = SupplierSummaryRequest(
            supplier_name="IEK Казахстан",
            total_items=10,
            total_budget=5196000.0,
            critical_count=3,
            planned_count=4,
            normal_count=3,
            season_name="Октябрь 2026",
            season_factor=1.242,
            top_critical_items=[
                {
                    "sku": "010500004_",
                    "item_name": "ВА47-29 6А",
                    "days_of_stock": 3.1,
                    "calculated_need": 600,
                    "total_cost": 510000,
                }
            ],
        )

        self.sample_letter_req = SupplierLetterRequest(
            supplier_name="IEK Казахстан",
            company_name="ТОО «Электрокомплект»",
            target_date="до 05.10.2026",
            items=[
                {
                    "sku": "010500004_",
                    "item_name": "ВА47-29 6А",
                    "quantity": 600,
                    "unit": "шт",
                    "unit_price": 850,
                    "total_cost": 510000,
                }
            ],
        )

    def test_sku_fallback_generation(self):
        res = generate_sku_analysis_fallback(self.sample_sku_req)
        self.assertIsInstance(res, SkuAnalysisResponse)
        self.assertTrue(res.is_fallback)
        self.assertIn("ВА47-29", res.summary)
        self.assertIn("1.24", res.root_cause)
        self.assertIn("600", res.recommendation_action)
        self.assertGreaterEqual(res.confidence_score, 0.9)

    def test_supplier_summary_fallback_generation(self):
        res = generate_supplier_summary_fallback(self.sample_summary_req)
        self.assertIsInstance(res, SupplierSummaryResponse)
        self.assertTrue(res.is_fallback)
        self.assertIn("IEK Казахстан", res.executive_summary)
        self.assertIn("5,196,000", res.budget_analysis)
        self.assertTrue(len(res.critical_risks) > 0)
        self.assertTrue(len(res.key_recommendations) > 0)

    def test_supplier_letter_fallback_generation(self):
        res = generate_supplier_letter_fallback(self.sample_letter_req)
        self.assertIsInstance(res, SupplierLetterResponse)
        self.assertTrue(res.is_fallback)
        self.assertIn("IEK", res.subject)
        self.assertIn("Электрокомплект", res.letter_body)
        self.assertIn("010500004_", res.items_table)

    def test_service_unconfigured_key_uses_fallback_without_error(self):
        service = AiProcurementService(api_key=None)
        res = asyncio.run(service.analyze_sku(self.sample_sku_req))
        self.assertTrue(res.is_fallback)
        self.assertIn("ВА47-29", res.summary)

    def test_memory_cache_hit(self):
        cache = AiMemoryCache(maxsize=10, ttl=60)
        key = cache.hash_key("test", {"a": 1})
        self.assertIsNone(cache.get(key))
        cache.set(key, "cached_result")
        self.assertEqual(cache.get(key), "cached_result")

    def test_service_caching_avoids_recomputation(self):
        service = AiProcurementService(api_key=None)
        first = asyncio.run(service.analyze_sku(self.sample_sku_req))
        second = asyncio.run(service.analyze_sku(self.sample_sku_req))
        self.assertIs(first, second)

    def test_service_graceful_degradation_on_openai_error(self):
        service = AiProcurementService(api_key="sk-dummy-test-key-12345")
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse = AsyncMock(
            side_effect=RuntimeError("Rate limit or connection failure")
        )
        service.client = mock_client

        # Call must NOT raise 500/RuntimeError, it must gracefully return fallback
        res = asyncio.run(service.analyze_sku(self.sample_sku_req))
        self.assertTrue(res.is_fallback)
        self.assertIn("ВА47-29", res.summary)


if __name__ == "__main__":
    unittest.main()
