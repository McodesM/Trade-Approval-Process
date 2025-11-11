from ..models import Trade, ActionLog

def log_action(*, trade, action, actor_user_id, before_state, after_state, note=""):
    return ActionLog.objects.create(
        trade=trade,
        action=action,
        actor_user_id=actor_user_id,
        before_state=before_state,
        after_state=after_state,
        note=note,
    )

def get_trade_action_logs(trade: Trade) -> list[dict]:
    logs = trade.action_logs.order_by("created_at")
    data = [
        {
            "timestamp": log.created_at.isoformat(),
            "action": log.action,
            "actorUserId": log.actor_user_id,
            "fromState": log.before_state,
            "toState": log.after_state,
            "note": log.note,
        }
        for log in logs
    ]
    return data