from typing import Dict, Any
from ..models import Trade, TradeVersion
from ..mappers import snapshot_model_dict


def create_snapshot(trade: Trade, *, actor_user_id: str, action: str) -> TradeVersion:
    snap = snapshot_model_dict(trade)
    return TradeVersion.objects.create(
        trade=trade,
        version_number=trade.version,
        state=trade.state,
        snapshot=snap,
        actor_user_id=actor_user_id,
        action=action,
    )


def diff_snapshots(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, tuple]:
    keys = set(a.keys()) | set(b.keys())
    diff_kv = {}
    for k in keys:
        if a.get(k) != b.get(k):
            diff_kv[k] = (a.get(k), b.get(k))
    return diff_kv