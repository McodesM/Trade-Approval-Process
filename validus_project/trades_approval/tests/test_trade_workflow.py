import unittest
from datetime import date
from decimal import Decimal

from trades_approval.dto import TradeDTO
from trades_approval.services.trade_workflow import (
    submit,
    approve,
    cancel,
    update,
    send_to_execute,
    book,
    InvalidTransition,
    PermissionDenied,
)
from trades_approval.validators import ValidationError

def make_dto(
    *,
    state: str = "Draft",
    version: int = 1,
    requester_id: str = "req-1",
    approver_id: str | None = None,
    strike=None,
    trading_entity: str = "EntityA",
    counterparty: str = "BankX",
    direction: str = "BUY",
    style: str = "FORWARD",
    notional_currency: str = "USD",
    notional_amount=Decimal("1000000"),
    underlying: list[str] = None,
    trade_date: date = date(2025, 11, 1),
    value_date: date = date(2025, 11, 2),
    delivery_date: date = date(2025, 11, 3),
) -> TradeDTO:
    if underlying is None:
        underlying = [notional_currency]
    return TradeDTO(
        id=None,
        trading_entity=trading_entity,
        counterparty=counterparty,
        direction=direction,
        style=style,
        notional_currency=notional_currency,
        notional_amount=notional_amount,
        underlying=underlying,
        trade_date=trade_date,
        value_date=value_date,
        delivery_date=delivery_date,
        strike=strike,
        requester_id=requester_id,
        approver_id=approver_id,
        state=state,
        version=version,
    )

class TestTradeWorkflow(unittest.TestCase):
    def test_submit_happy_path(self):
        dto = make_dto(state="Draft", version=1)
        out = submit(dto)
        self.assertEqual(out.state, "PendingApproval")
        self.assertEqual(out.version, 2)

    def test_submit_invalid_state_raises(self):
        dto = make_dto(state="Approved")
        with self.assertRaises(InvalidTransition):
            submit(dto)

    def test_approve_from_pending_by_approver_sets_approver_and_approved(self):
        dto = make_dto(state="PendingApproval", approver_id=None, requester_id="req", version=1)
        out = approve(dto, actor_id="approver")
        self.assertEqual(out.approver_id, "approver")
        self.assertEqual(out.state, "Approved")
        self.assertEqual(out.version, 2)

    def test_approve_from_pending_by_requester_denied(self):
        dto = make_dto(state="PendingApproval", requester_id="u1")
        with self.assertRaises(PermissionDenied):
            approve(dto, actor_id="u1")

    def test_reapprove_from_needs_reapproval_by_requester(self):
        dto = make_dto(state="NeedsReapproval", requester_id="req", approver_id="approver", version=3)
        out = approve(dto, actor_id="req")
        self.assertEqual(out.state, "Approved")
        self.assertEqual(out.version, 4)

    def test_reapprove_from_needs_reapproval_by_other_denied(self):
        dto = make_dto(state="NeedsReapproval", requester_id="req", approver_id="approver")
        with self.assertRaises(PermissionDenied):
            approve(dto, actor_id="other")

    def test_cancel_by_requester(self):
        dto = make_dto(state="PendingApproval", requester_id="req")
        out = cancel(dto, actor_id="req")
        self.assertEqual(out.state, "Cancelled")

    def test_cancel_invalid_state(self):
        dto = make_dto(state="Executed")
        with self.assertRaises(InvalidTransition):
            cancel(dto, actor_id="req")

    def test_cancel_by_unauthorized_denied(self):
        dto = make_dto(state="PendingApproval", requester_id="req", approver_id="approver")
        with self.assertRaises(PermissionDenied):
            cancel(dto, actor_id="intruder")

    def test_update_first_time_sets_approver_and_needs_reapproval(self):
        dto = make_dto(state="PendingApproval", approver_id=None, requester_id="req", version=1)
        changes = {"counterparty": "BankY"}
        out = update(dto, actor_id="approver", trade_update_details=changes)
        self.assertEqual(out.approver_id, "approver")
        self.assertEqual(out.counterparty, "BankY")
        self.assertEqual(out.state, "NeedsReapproval")
        self.assertEqual(out.version, 2)

    def test_update_by_requester_denied(self):
        dto = make_dto(state="PendingApproval", approver_id=None, requester_id="req")
        with self.assertRaises(PermissionDenied):
            update(dto, actor_id="req", trade_update_details={"style": "OPTION"})

    def test_update_by_non_assigned_approver_denied(self):
        dto = make_dto(state="NeedsReapproval", approver_id="approver", requester_id="req")
        with self.assertRaises(PermissionDenied):
            update(dto, actor_id="other", trade_update_details={"style": "OPTION"})

    def test_update_invalid_dates_raises_validation_error(self):
        dto = make_dto(state="PendingApproval")
        with self.assertRaises(ValidationError):
            update(
                dto,
                actor_id="approver",
                trade_update_details={
                    "valueDate": date(2025, 10, 1),
                },
            )

    def test_update_with_strike_raises_validation_error(self):
        dto = make_dto(state="PendingApproval")
        with self.assertRaises(ValidationError):
            update(dto, actor_id="approver", trade_update_details={"strike": 1.25})

    def test_send_to_execute_happy_path(self):
        dto = make_dto(state="Approved", approver_id="approver", version=5)
        out = send_to_execute(dto, actor_id="approver")
        self.assertEqual(out.state, "SentToCounterparty")
        self.assertEqual(out.version, 6)

    def test_send_to_execute_wrong_state(self):
        dto = make_dto(state="PendingApproval", approver_id="approver")
        with self.assertRaises(InvalidTransition):
            send_to_execute(dto, actor_id="approver")

    def test_send_to_execute_wrong_actor(self):
        dto = make_dto(state="Approved", approver_id="approver")
        with self.assertRaises(PermissionDenied):
            send_to_execute(dto, actor_id="not-approver")

    def test_book_happy_path(self):
        dto = make_dto(state="SentToCounterparty", requester_id="req", approver_id="approver", version=10)
        out = book(dto, actor_id="req", strike=1.2345)
        self.assertEqual(out.state, "Executed")
        self.assertEqual(out.version, 11)
        self.assertIsInstance(out.strike, Decimal)
        self.assertEqual(out.strike, Decimal("1.2345"))

    def test_book_wrong_state(self):
        dto = make_dto(state="Approved", requester_id="req", approver_id="approver")
        with self.assertRaises(InvalidTransition):
            book(dto, actor_id="req", strike=1.0)

    def test_book_unauthorized(self):
        dto = make_dto(state="SentToCounterparty", requester_id="req", approver_id="approver")
        with self.assertRaises(PermissionDenied):
            book(dto, actor_id="other", strike=1.0)