"""Offline prepaid-budget accounting: no inference, billing or OS workloads."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from os_goal_credits import CreditBudget, available_balance, credit_budget_argument


def limits(balance, **changes):
    credits = {"hasCredits": True, "unlimited": False, "balance": balance}
    credits.update(changes)
    return {"primary": {"usedPercent": 100}, "credits": credits}


class CreditBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ident = "a" * 32

    def guard(self, budget="100", **kwargs):
        return CreditBudget(self.root, self.ident, budget,
                            lambda p, v: p.write_text(json.dumps(v)), **kwargs)

    def test_decimal_spend_and_exact_threshold(self):
        guard = self.guard()
        first, stop = guard.observe(limits("58235.9614400000"))
        self.assertFalse(stop)
        self.assertEqual(first["spent"], "0")
        row, stop = guard.observe(limits("58135.9614400001"))
        self.assertFalse(stop)
        self.assertEqual(row["remaining"], "1E-10")
        row, stop = guard.observe(limits("58135.9614400000"))
        self.assertTrue(stop)
        self.assertEqual(row["remaining"], "0")

    def test_new_worker_retains_original_allowance(self):
        self.guard().observe(limits("1000"))
        self.guard(recovered=True).observe(limits("940"))
        row, stop = self.guard(recovered=True).observe(limits("900"))
        self.assertTrue(stop)
        self.assertEqual(row["initial_balance"], "1000")
        self.assertEqual(row["spent"], "100")

    def test_missing_record_cannot_reset_live_or_recovered_budget(self):
        guard = self.guard()
        guard.observe(limits("1000"))
        guard.path.unlink()
        for candidate in (guard, self.guard(recovered=True)):
            with self.assertRaisesRegex(ValueError, "no retained credit budget"):
                candidate.observe(limits("950"))

    def test_budget_change_refuses(self):
        self.guard().observe(limits("1000"))
        with self.assertRaisesRegex(ValueError, "budget or identity changed"):
            self.guard("200", recovered=True).observe(limits("950"))

    def test_out_of_order_balance_never_restores_allowance(self):
        guard = self.guard()
        guard.observe(limits("1000"))
        guard.observe(limits("940"))
        row, stop = guard.observe(limits("950"))
        self.assertFalse(stop)
        self.assertEqual(row["spent"], "60")
        self.assertEqual(row["remaining"], "40")
        self.assertEqual(row["minimum_balance"], "940")
        row, stop = self.guard(recovered=True).observe(limits("910"))
        self.assertTrue(stop)
        self.assertEqual(row["initial_balance"], "1000")
        self.assertEqual(row["spent"], "100")

    def test_topup_cannot_reset_spending(self):
        guard = self.guard()
        guard.observe(limits("1000"))
        guard.observe(limits("940"))
        row, stop = guard.observe(limits("1940"))
        self.assertFalse(stop)
        self.assertEqual(row["remaining"], "40")
        row, stop = self.guard(recovered=True).observe(limits("1900"))
        self.assertTrue(stop)
        self.assertEqual(row["spent"], "100")
        self.assertEqual(row["minimum_balance"], "940")

    def test_version_one_migration_preserves_existing_spend(self):
        guard = self.guard()
        guard.observe(limits("1000"))
        row = {"schema_version": 1, "id": self.ident, "budget": "100",
               "initial_balance": "1000", "minimum_balance": "940",
               "last_balance": "940", "spent": "60", "remaining": "40"}
        guard.path.write_text(json.dumps(row))
        migrated, stop = self.guard(recovered=True).observe(limits("950"))
        self.assertFalse(stop)
        self.assertEqual(migrated["schema_version"], 2)
        for key in ("id", "initial_balance", "minimum_balance", "spent", "remaining"):
            self.assertEqual(migrated[key], row[key])

    def test_corrupt_cumulative_spend_or_remaining_refuses(self):
        guard = self.guard()
        guard.observe(limits("1000"))
        row, _ = guard.observe(limits("940"))
        for key, value in (("spent", "0"), ("remaining", "100")):
            broken = dict(row)
            broken[key] = value
            guard.path.write_text(json.dumps(broken))
            with self.assertRaisesRegex(ValueError, "Inconsistent"):
                self.guard(recovered=True).observe(limits("930"))

    def test_unavailable_unknown_unlimited_and_invalid_balances_refuse(self):
        cases = [limits("0"), limits(None), limits("NaN"), limits("Infinity"),
                 limits("-1"), limits(True), limits("100", unlimited=True),
                 limits("100", hasCredits=False), {"credits": {}},
                 dict(limits("100"), spendControlReached={"reached": True})]
        for row in cases:
            with self.subTest(row=row), self.assertRaises(ValueError):
                available_balance(row)

    def test_invalid_identifiers_and_budgets_refuse(self):
        for value in ("0", "-1", "NaN", "Infinity", "1e99", "x"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                credit_budget_argument(value)
        for value in (None, "../other", "A" * 32):
            with self.subTest(value=value), self.assertRaises(ValueError):
                CreditBudget(self.root, value, "100", lambda p, v: None)

    def test_malformed_accounting_refuses(self):
        guard = self.guard()
        guard.observe(limits("1000"))
        for data in ([], {"schema_version": 1, "id": self.ident, "budget": "100",
                          "initial_balance": "1000", "minimum_balance": "1100",
                          "last_balance": "900"}):
            guard.path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                guard.observe(limits("900"))


if __name__ == "__main__":
    unittest.main()
