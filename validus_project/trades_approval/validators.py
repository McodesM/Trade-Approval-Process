from .dto import TradeDTO

class ValidationError(Exception): pass

def _assert_dates(dto: TradeDTO):
    if not (dto.trade_date <= dto.value_date <= dto.delivery_date):
        raise ValidationError("Trade Date ≤ Value Date ≤ Delivery Date must hold.")


def _assert_underlying_contains_notional(dto: TradeDTO):
    if dto.notional_currency not in dto.underlying:
        raise ValidationError("Notional currency must be included in the underlying.")


def _assert_no_strike_until_executed(dto: TradeDTO):
    if dto.state != "Executed" and dto.strike is not None:
        raise ValidationError("Strike may only be set when booking (to Executed).")

def _authorized_as_approver(dto: TradeDTO, actor_id: str) -> bool:
    return dto.approver_id is None or actor_id == dto.approver_id

def _authorized_as_requester(dto: TradeDTO, actor_id: str) -> bool:
    return actor_id == dto.requester_id
