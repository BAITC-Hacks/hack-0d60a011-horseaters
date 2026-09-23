"""TEST-01: state transitions and invariants without a database or API."""

import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from backend.domain.entities.calculation_run import CalculationRun
from backend.domain.entities.enums import CalculationRunStatus, PurchaseOrderStatus, RecommendationStatus, Urgency
from backend.domain.entities.purchase_order import PurchaseOrder, PurchaseOrderItem
from backend.domain.entities.recommendation import Recommendation


NOW = datetime(2026, 9, 23, tzinfo=timezone.utc)
D = Decimal


class DomainWorkflowContractTests(unittest.TestCase):
    def run_entity(self, **changes):
        values = dict(
            started_by=uuid4(), forecast_horizon_days=30,
            source_cutoff_at=NOW, algorithm_version="test-1",
            parameters={"horizon_days": 30}, started_at=NOW,
        )
        values.update(changes)
        return CalculationRun(**values)

    def recommendation(self, **changes):
        values = dict(
            calculation_run_id=uuid4(), product_id=uuid4(), warehouse_id=uuid4(),
            supplier_id=uuid4(), forecast_quantity=D("20"), current_stock=D("5"),
            in_transit_quantity=D("2"), material_requirement_quantity=D("0"),
            safety_stock=D("3"), shortage_quantity=D("16"),
            quantity_before_rounding=D("16"), moq=D("5"), package_size=D("5"),
            recommended_quantity=D("20"), effective_quantity=D("20"),
            risk_score=D("0.5"), urgency=Urgency.MEDIUM,
            explanation="Calculated from demand and stock", calculation_details={},
            created_at=NOW, updated_at=NOW,
        )
        values.update(changes)
        return Recommendation(**values)

    def order(self):
        return PurchaseOrder(
            order_number="PO-1", supplier_id=uuid4(), warehouse_id=uuid4(),
            created_from_run_id=uuid4(), created_by=uuid4(), created_at=NOW,
        )

    def test_calculation_run_requires_import_and_valid_transition_order(self):
        run = self.run_entity()
        with self.assertRaisesRegex(ValueError, "at least one import"):
            run.start()
        batch = uuid4()
        run.attach_import(batch)
        run.start()
        self.assertEqual((run.status, run.import_batch_ids), (CalculationRunStatus.RUNNING, {batch}))
        with self.assertRaisesRegex(ValueError, "pending"):
            run.attach_import(uuid4())
        run.complete(finished_at=NOW + timedelta(seconds=1))
        self.assertEqual(run.status, CalculationRunStatus.COMPLETED)
        self.assertEqual(run.finished_at, NOW + timedelta(seconds=1))
        with self.assertRaises(ValueError):
            run.complete()
        with self.assertRaises(ValueError):
            run.fail({"message": "too late"})

    def test_calculation_failure_is_terminal_and_copies_error_details(self):
        error = {"message": "source unavailable"}
        run = self.run_entity()
        run.fail(error, finished_at=NOW + timedelta(seconds=1))
        error["message"] = "mutated outside"
        self.assertEqual(run.error_details["message"], "source unavailable")
        self.assertEqual(run.status, CalculationRunStatus.FAILED)
        with self.assertRaises(ValueError):
            run.start()
        with self.assertRaises(ValueError):
            run.complete()

    def test_domain_constructor_invariants(self):
        for changes in (
            {"forecast_horizon_days": 0},
            {"algorithm_version": "  "},
            {"source_cutoff_at": NOW.replace(tzinfo=None)},
            {"status": CalculationRunStatus.COMPLETED},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.run_entity(**changes)
        with self.assertRaisesRegex(ValueError, "moq"):
            self.recommendation(moq=D("0"))
        with self.assertRaisesRegex(ValueError, "risk_score"):
            self.recommendation(risk_score=D("1.01"))
        with self.assertRaisesRegex(ValueError, "version"):
            self.recommendation(version=0)

    def test_adjustment_records_snapshot_actor_time_and_version(self):
        recommendation = self.recommendation()
        actor = uuid4()
        changed_at = NOW + timedelta(minutes=1)
        adjustment = recommendation.adjust(
            D("12.5"), reason="  Supplier minimum changed  ",
            changed_by=actor, changed_at=changed_at,
        )
        self.assertEqual((adjustment.previous_quantity, adjustment.new_quantity), (D("20"), D("12.5")))
        self.assertEqual((adjustment.changed_by, adjustment.changed_at), (actor, changed_at))
        self.assertEqual((recommendation.status, recommendation.version), (RecommendationStatus.ADJUSTED, 2))
        self.assertEqual(recommendation.recommended_quantity, D("20"))
        self.assertEqual(recommendation.effective_quantity, D("12.5"))

    def test_invalid_or_closed_adjustment_does_not_mutate_recommendation(self):
        recommendation = self.recommendation()
        for quantity, reason in ((D("-1"), "reason"), (D("1"), "  ")):
            with self.subTest(quantity=quantity, reason=reason), self.assertRaises(ValueError):
                recommendation.adjust(quantity, reason=reason, changed_by=uuid4())
            self.assertEqual((recommendation.effective_quantity, recommendation.version), (D("20"), 1))
        recommendation.accept(changed_at=NOW + timedelta(seconds=1))
        recommendation.mark_converted_to_order(changed_at=NOW + timedelta(seconds=2))
        with self.assertRaisesRegex(ValueError, "closed"):
            recommendation.adjust(D("10"), reason="late", changed_by=uuid4())

    def test_order_cannot_approve_empty_or_export_draft(self):
        order = self.order()
        self.assertEqual(order.status, PurchaseOrderStatus.DRAFT)
        with self.assertRaisesRegex(ValueError, "empty"):
            order.approve(approved_by=uuid4())
        with self.assertRaisesRegex(ValueError, "approved"):
            order.mark_exported()
        self.assertIsNone(order.approved_at)

    def test_order_approval_and_export_preserve_audit_and_snapshot(self):
        order = self.order()
        item = PurchaseOrderItem(
            recommendation_id=uuid4(), product_id=uuid4(),
            recommended_quantity=D("20"), approved_quantity=D("15"),
        )
        order.add_item(item)
        with self.assertRaisesRegex(ValueError, "already included"):
            order.add_item(item)
        actor = uuid4()
        approved_at = NOW + timedelta(minutes=1)
        order.approve(approved_by=actor, approved_at=approved_at)
        self.assertEqual((order.status, order.approved_by, order.approved_at),
                         (PurchaseOrderStatus.APPROVED, actor, approved_at))
        self.assertEqual((order.items[0].recommended_quantity, order.items[0].approved_quantity),
                         (D("20"), D("15")))
        with self.assertRaisesRegex(ValueError, "draft"):
            order.approve(approved_by=uuid4())
        exported_at = NOW + timedelta(minutes=2)
        order.mark_exported(exported_at=exported_at)
        self.assertEqual((order.status, order.exported_at), (PurchaseOrderStatus.EXPORTED, exported_at))
        self.assertEqual(order.approved_by, actor)
        with self.assertRaisesRegex(ValueError, "approved"):
            order.mark_exported()


if __name__ == "__main__":
    unittest.main()
