from .dto import TradeDTO
from .models import Trade
from typing import Dict, Any

def dto_from_model(m: Trade) -> TradeDTO:
    return TradeDTO(
        id=m.id,
        trading_entity=m.trading_entity,
        counterparty=m.counterparty,
        direction=m.direction,
        style=m.style,
        notional_currency=m.notional_currency,
        notional_amount=m.notional_amount,
        underlying=list(m.underlying or []),
        trade_date=m.trade_date,
        value_date=m.value_date,
        delivery_date=m.delivery_date,
        strike=m.strike,
        requester_id=m.requester_id,
        approver_id=m.approver_id,
        state=m.state,
        version=m.version,
    )

def dto_to_model(dto: TradeDTO, trade: Trade) -> Trade:
    model_field_names = {f.name for f in trade._meta.fields}
    skip = {"id", "created_at", "updated_at"}

    for name in model_field_names:
        if name in skip:
            continue
        if not hasattr(dto, name):
            continue

        dto_val = getattr(dto, name)
        model_val = getattr(trade, name)

        if isinstance(dto_val, list) and not isinstance(model_val, list):
            model_val = list(model_val or [])

        if dto_val != model_val:
            setattr(trade, name, dto_val)

    return trade

def snapshot_model_dict(trade: Trade) -> Dict[str, Any]:
    return {
        "id": trade.id,
        "trading_entity": trade.trading_entity,
        "counterparty": trade.counterparty,
        "direction": trade.direction,
        "style": trade.style,
        "notional_currency": trade.notional_currency,
        "notional_amount": str(trade.notional_amount),
        "underlying": list(trade.underlying or []),
        "trade_date": trade.trade_date.isoformat() if trade.trade_date else None,
        "value_date": trade.value_date.isoformat() if trade.value_date else None,
        "delivery_date": trade.delivery_date.isoformat() if trade.delivery_date else None,
        "strike": str(trade.strike) if trade.strike is not None else None,
        "requester_id": trade.requester_id,
        "approver_id": trade.approver_id,
        "state": trade.state,
        "version": trade.version,
    }