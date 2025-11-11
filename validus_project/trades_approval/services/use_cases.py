from typing import Any, Dict, Callable, Optional
from django.db import transaction
from ..models import Trade
from ..mappers import dto_to_model, dto_from_model
from .trade_workflow import submit, approve, cancel, update, send_to_execute, book
from .versioning import create_snapshot
from .audit import log_action

def _default_note(action: str, before_state: str) -> str:
    if action == "Submit":
        return "Trade details provided"
    if action == "Approve":
        return "Requester reapproves updated trade details" if before_state == "NeedsReapproval" else "Approver confirms trade"
    if action == "Cancel":
        return "Trade cancelled"
    if action == "Update":
        return "Trade details updated"
    if action == "SendToExecute":
        return "Trade sent to execution"
    if action == "Book":
        return "Trade booked with strike"
    return ""


def _run_transition(
    *,
    trade: Trade,
    actor_id: str,
    wf_fn: Callable[..., Any],
    action_name: str,
    wf_kwargs: Optional[Dict[str, Any]] = None,
) -> Trade:
    wf_kwargs = wf_kwargs or {}
    with transaction.atomic():
        dto_before = dto_from_model(trade)
        before_state = trade.state

        dto_after = wf_fn(dto_before, actor_id, **wf_kwargs)

        dto_to_model(dto_after, trade)
        trade.full_clean()
        trade.save()

        create_snapshot(trade, actor_user_id=actor_id, action=action_name)
        log_action(
            trade=trade,
            action=action_name,
            actor_user_id=actor_id,
            before_state=before_state,
            after_state=trade.state,
            note=_default_note(action_name, before_state),
        )
        return trade

def create_and_submit(trade_detail: Dict[str, Any], actor_id: str) -> Trade:
    with transaction.atomic():
        trade = Trade(
            trading_entity=trade_detail["tradingEntity"],
            counterparty=trade_detail["counterparty"],
            direction=trade_detail["direction"],
            style=trade_detail.get("style", "FORWARD"),
            notional_currency=trade_detail["notionalCurrency"],
            notional_amount=trade_detail["notionalAmount"],
            underlying=trade_detail["underlying"],
            trade_date=trade_detail["tradeDate"],
            value_date=trade_detail["valueDate"],
            delivery_date=trade_detail["deliveryDate"],
            requester_id=actor_id,
            state="Draft",
            version=1,
        )
        trade.full_clean()
        trade.save()

    return _run_transition(
        trade=trade,
        actor_id=actor_id,
        wf_fn=lambda dto, actor: submit(dto),
        action_name="Submit",
    )


def approve_trade(trade: Trade, actor_id: str) -> Trade:
    return _run_transition(
        trade=trade,
        actor_id=actor_id,
        wf_fn=approve,
        action_name="Approve",
    )


def cancel_trade(trade: Trade, actor_id: str) -> Trade:
    return _run_transition(
        trade=trade,
        actor_id=actor_id,
        wf_fn=cancel,
        action_name="Cancel",
    )


def update_trade(trade: Trade, actor_id: str, trade_detail: Dict[str, Any]) -> Trade:
    return _run_transition(
        trade=trade,
        actor_id=actor_id,
        wf_fn=update,
        action_name="Update",
        wf_kwargs={"trade_update_details": trade_detail},
    )


def send_to_execute_trade(trade: Trade, actor_id: str) -> Trade:
    return _run_transition(
        trade=trade,
        actor_id=actor_id,
        wf_fn=send_to_execute,
        action_name="SendToExecute",
    )


def book_trade(trade: Trade, actor_id: str, strike: float) -> Trade:
    return _run_transition(
        trade=trade,
        actor_id=actor_id,
        wf_fn=book,
        action_name="Book",
        wf_kwargs={"strike": strike},
    )
