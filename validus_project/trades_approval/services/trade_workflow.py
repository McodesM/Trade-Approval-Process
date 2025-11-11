from dataclasses import replace
from ..dto import TradeDTO
from ..validators import (
    _assert_dates,
    _assert_underlying_contains_notional,
    _assert_no_strike_until_executed,
    _authorized_as_approver,
    _authorized_as_requester,
)
from decimal import Decimal

class InvalidTransition(Exception): pass
class PermissionDenied(Exception): pass

def submit(dto: TradeDTO) -> TradeDTO:
    if dto.state != "Draft":
        raise InvalidTransition("Submit is only allowed from Draft.")
    _assert_dates(dto)
    _assert_underlying_contains_notional(dto)
    _assert_no_strike_until_executed(dto)
    return replace(dto, state="PendingApproval", version=dto.version + 1)

def approve(dto: TradeDTO, actor_id: str) -> TradeDTO:
    if dto.state not in {"PendingApproval", "NeedsReapproval"}:
        raise InvalidTransition("Approve requires PendingApproval or NeedsReapproval.")
    
    if dto.state == "PendingApproval":
        if actor_id == dto.requester_id:
            raise PermissionDenied("Requester cannot approve submission.")
        return replace(dto, approver_id=actor_id,state="Approved", version=dto.version + 1)
    else:  
        if not _authorized_as_requester(dto, actor_id):
            raise PermissionDenied("Only the requester can reapprove after updates.")
    return replace(dto, state="Approved", version=dto.version + 1)

def cancel(dto: TradeDTO, actor_id: str) -> TradeDTO:
    if dto.state in {"Executed", "Cancelled"}:
        raise InvalidTransition("Cannot cancel a terminal trade.")
    if actor_id not in {dto.requester_id, dto.approver_id}:
        raise PermissionDenied("Only requester or approver can cancel.")
    return replace(dto, state="Cancelled", version=dto.version + 1)

def update(dto: TradeDTO, actor_id: str, trade_update_details) -> TradeDTO:
    if dto.state not in {"PendingApproval", "NeedsReapproval"}:
        raise InvalidTransition("Update is only allowed from PendingApproval or NeedsReapproval.")
    if dto.approver_id is None:
        if actor_id == dto.requester_id:
            raise PermissionDenied("Requester cannot perform approver-only update.")
        working = replace(dto, approver_id=actor_id)
    else:
        if actor_id != dto.approver_id:
            raise PermissionDenied("Only the assigned approver can update details.")
        working = dto

    res_dto=replace(working,
                    trading_entity=trade_update_details.get("tradingEntity", dto.trading_entity),
                    counterparty=trade_update_details.get("counterparty", dto.counterparty),
                    direction=trade_update_details.get("direction", dto.direction),
                    style=trade_update_details.get("style", dto.style),
                    notional_currency=trade_update_details.get("notionalCurrency", dto.notional_currency),
                    notional_amount=trade_update_details.get("notionalAmount", dto.notional_amount),
                    underlying=trade_update_details.get("underlying", dto.underlying),
                    trade_date=trade_update_details.get("tradeDate", dto.trade_date),
                    value_date=trade_update_details.get("valueDate", dto.value_date),
                    delivery_date=trade_update_details.get("deliveryDate", dto.delivery_date),
                    strike=trade_update_details.get("strike", dto.strike),
                    state="NeedsReapproval",
                    version=dto.version + 1)
    _assert_dates(res_dto)
    _assert_underlying_contains_notional(res_dto)
    _assert_no_strike_until_executed(res_dto)
    return res_dto

def send_to_execute(dto: TradeDTO, actor_id: str) -> TradeDTO:
    if dto.state != "Approved":
        raise InvalidTransition("SendToExecute is only allowed from Approved.")
    if not _authorized_as_approver(dto, actor_id):
        raise PermissionDenied("Only the assigned approver can send to execute.")
    return replace(dto, state="SentToCounterparty", version=dto.version + 1)

def book(dto: TradeDTO, actor_id: str, strike) -> TradeDTO:
    if dto.state != "SentToCounterparty":
        raise InvalidTransition("Book is only allowed from SentToCounterparty.")
    if actor_id not in {dto.requester_id, dto.approver_id}:
        raise PermissionDenied("Only requester or approver can book the trade.")
    return replace(dto, strike=Decimal(str(strike)), state="Executed", version=dto.version + 1)