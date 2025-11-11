import unittest
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from trades_approval.dto import TradeDTO
from trades_approval.services import use_cases


def make_details(**overrides):
    base = {
        "tradingEntity": "Validus Capital Ltd",
        "counterparty": "Bank of England",
        "direction": "BUY",
        "style": "FORWARD",
        "notionalCurrency": "USD",
        "notionalAmount": Decimal("5000000.00"),
        "underlying": ["USD", "EUR"],
        "tradeDate": date(2025, 11, 1),
        "valueDate": date(2025, 11, 5),
        "deliveryDate": date(2025, 11, 10),
    }
    base.update(overrides)
    return base


class FakeTrade:
    def __init__(self, **kwargs):
        self.trading_entity = kwargs.get("trading_entity", "E")
        self.counterparty = kwargs.get("counterparty", "C")
        self.direction = kwargs.get("direction", "BUY")
        self.style = kwargs.get("style", "FORWARD")
        self.notional_currency = kwargs.get("notional_currency", "USD")
        self.notional_amount = kwargs.get("notional_amount", Decimal("0"))
        self.underlying = kwargs.get("underlying", ["USD"])
        self.trade_date = kwargs.get("trade_date", date.today())
        self.value_date = kwargs.get("value_date", date.today())
        self.delivery_date = kwargs.get("delivery_date", date.today())
        self.strike = kwargs.get("strike")
        self.requester_id = kwargs.get("requester_id", "req")
        self.approver_id = kwargs.get("approver_id")
        self.state = kwargs.get("state", "Draft")
        self.version = kwargs.get("version", 1)
        self.id = kwargs.get("id", 123)

    def full_clean(self): pass
    def save(self): pass


def dto_to_model_copy(dto: TradeDTO, trade: FakeTrade) -> FakeTrade:
    for name, value in dto.__dict__.items():
        if hasattr(trade, name):
            setattr(trade, name, value)
    return trade


def dto_from_model_copy(trade: FakeTrade) -> TradeDTO:
    return TradeDTO(
        id=trade.id,
        trading_entity=trade.trading_entity,
        counterparty=trade.counterparty,
        direction=trade.direction,
        style=trade.style,
        notional_currency=trade.notional_currency,
        notional_amount=trade.notional_amount,
        underlying=trade.underlying,
        trade_date=trade.trade_date,
        value_date=trade.value_date,
        delivery_date=trade.delivery_date,
        strike=trade.strike,
        requester_id=trade.requester_id,
        approver_id=trade.approver_id,
        state=trade.state,
        version=trade.version,
    )


@contextmanager
def _noop_atomic():
    yield


class TestUseCases(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patch("trades_approval.services.use_cases.Trade", FakeTrade),
            patch("trades_approval.services.use_cases.create_snapshot"),
            patch("trades_approval.services.use_cases.log_action"),
            patch("trades_approval.services.use_cases.dto_to_model", side_effect=dto_to_model_copy),
            patch("trades_approval.services.use_cases.dto_from_model", side_effect=dto_from_model_copy),
            patch("trades_approval.services.use_cases.transaction.atomic", _noop_atomic),
        ]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])

    def test_create_and_submit(self):
        trade = use_cases.create_and_submit(make_details(), actor_id="user_req")
        self.assertIsInstance(trade, FakeTrade)
        self.assertEqual(trade.requester_id, "user_req")
        self.assertEqual(trade.state, "PendingApproval")
        self.assertEqual(trade.version, 2)

    def test_approve_trade(self):
        trade = FakeTrade(state="PendingApproval", version=1, requester_id="req", approver_id=None)
        trade = use_cases.approve_trade(trade, actor_id="approver_1")
        self.assertEqual(trade.state, "Approved")
        self.assertEqual(trade.approver_id, "approver_1")
        self.assertEqual(trade.version, 2)

    def test_cancel_trade(self):
        trade = FakeTrade(state="PendingApproval", requester_id="req", version=2)
        trade = use_cases.cancel_trade(trade, actor_id="req")
        self.assertEqual(trade.state, "Cancelled")
        self.assertEqual(trade.version, 3)

    def test_update_trade(self):
        trade = FakeTrade(
            state="PendingApproval",
            requester_id="req",
            approver_id=None,
            counterparty="Bank A",
            version=2,
        )
        updated = use_cases.update_trade(
            trade, actor_id="approver_1", trade_detail={"counterparty": "Bank B"}
        )
        self.assertEqual(updated.approver_id, "approver_1")
        self.assertEqual(updated.counterparty, "Bank B")
        self.assertEqual(updated.state, "NeedsReapproval")
        self.assertEqual(updated.version, 3)

    def test_send_to_execute_trade(self):
        trade = FakeTrade(state="Approved", approver_id="approver_1", version=3)
        trade = use_cases.send_to_execute_trade(trade, actor_id="approver_1")
        self.assertEqual(trade.state, "SentToCounterparty")
        self.assertEqual(trade.version, 4)

    def test_book_trade(self):
        trade = FakeTrade(
            state="SentToCounterparty",
            requester_id="req",
            approver_id="approver_1",
            version=4,
        )
        trade = use_cases.book_trade(trade, actor_id="req", strike=1.2345)
        self.assertEqual(trade.state, "Executed")
        self.assertEqual(trade.version, 5)
        self.assertEqual(trade.strike, Decimal("1.2345"))
