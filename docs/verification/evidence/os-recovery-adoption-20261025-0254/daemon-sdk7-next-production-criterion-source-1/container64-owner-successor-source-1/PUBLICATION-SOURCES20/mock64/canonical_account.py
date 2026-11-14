"""Explicit prepaid-credit budgets, retained across supervised worker recovery."""
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path


def amount(value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("Credit amount must be a finite number")
    text = str(value)
    if len(text) > 64:
        raise ValueError("Credit amount is too long")
    try:
        number = Decimal(text)
    except InvalidOperation as error:
        raise ValueError("Invalid credit amount") from error
    if not number.is_finite() or number < 0 or number > Decimal("1e12"):
        raise ValueError("Credit amount is outside the supported range")
    if positive and number == 0:
        raise ValueError("Credit budget must be positive")
    return number


def credit_budget_argument(value):
    return str(amount(value, positive=True))


def available_balance(limits):
    if not isinstance(limits, dict) or not isinstance(limits.get("credits"), dict):
        raise ValueError("Prepaid-credit balance is unknown")
    credits = (limits or {}).get("credits") or {}
    if credits.get("hasCredits") is not True or credits.get("unlimited") is not False:
        raise ValueError("A finite available prepaid-credit balance is required")
    balance = amount(credits.get("balance"))
    if balance <= 0:
        raise ValueError("Prepaid credits are exhausted")
    if (limits or {}).get("spendControlReached"):
        raise ValueError("Account spending control has been reached")
    return balance


def billing_policy(args):
    budget = getattr(args, "credit_budget", None)
    return {"mode": "prepaid_credits" if budget is not None else "included_only",
            "credit_budget": budget,
            "automatic_credit_purchase": False, "api_key_billing": False,
            "account_wide_balance_guard": budget is not None,
            "in_flight_charges_may_settle_after_stop": budget is not None}


class CreditBudget:
    def __init__(self, directory, identifier, budget, write_json, *, recovered=False):
        if (not isinstance(identifier, str) or len(identifier) != 32
                or any(c not in "0123456789abcdef" for c in identifier)):
            raise ValueError("Invalid credit-run identifier")
        self.identifier = identifier
        self.budget = amount(budget, positive=True)
        self.path = Path(directory) / "credit-runs" / (identifier + ".json")
        self.write_json, self.recovered = write_json, recovered
        self.initialized = False

    def observe(self, limits):
        balance = available_balance(limits)
        if self.path.exists():
            saved = json.loads(self.path.read_text())
            if (not isinstance(saved, dict) or type(saved.get("schema_version")) is not int
                    or saved.get("schema_version") not in (1, 2) or saved.get("id") != self.identifier
                    or amount(saved.get("budget"), positive=True) != self.budget):
                raise ValueError("Credit-run budget or identity changed")
            initial = amount(saved.get("initial_balance"))
            minimum = amount(saved.get("minimum_balance"))
            previous = amount(saved.get("last_balance"))
            spent = amount(saved.get("spent"))
            remaining = amount(saved.get("remaining"))
            if (minimum > initial or minimum > previous
                    or spent < initial - minimum
                    or remaining != max(Decimal(0), self.budget - spent)
                    or (saved["schema_version"] == 1
                        and (previous > initial or spent != initial - minimum))):
                raise ValueError("Inconsistent retained credit-run accounting")
            # Poll responses and notifications can arrive out of balance order.
            # Count only downward steps and never refund allowance on an upward
            # snapshot. A stale down/up/down sequence may count conservatively;
            # it cannot erase observed spending or extend the user's allowance.
            spent += max(Decimal(0), previous - balance)
        else:
            if self.recovered or self.initialized:
                raise ValueError("Recovery has no retained credit budget; refusing a new allowance")
            initial = minimum = balance
            spent = Decimal(0)
        minimum = min(minimum, balance)
        saved = {"schema_version": 2, "id": self.identifier,
                 "budget": str(self.budget), "initial_balance": str(initial),
                 "minimum_balance": str(minimum), "last_balance": str(balance),
                 "spent": str(spent), "remaining": str(max(Decimal(0), self.budget - spent)),
                 "scope": "Cumulative account-wide observed balance decreases; increases never restore allowance; stale snapshots may count conservatively; in-flight charges can settle later"}
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Persist before allowing inference, including the exhausted state.
        self.write_json(self.path, saved)
        self.initialized = True
        return saved, spent >= self.budget
