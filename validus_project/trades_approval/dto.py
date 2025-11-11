from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional


@dataclass(frozen=True)
class TradeDTO:
    id: int
    trading_entity: str
    counterparty: str
    direction: str  
    style: str
    notional_currency: str
    notional_amount: Decimal
    underlying: List[str]
    trade_date: date
    value_date: date
    delivery_date: date
    strike: Optional[Decimal]
    requester_id: str
    approver_id: Optional[str]
    state: str
    version: int