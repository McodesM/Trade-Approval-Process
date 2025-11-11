from django.db import models
from .enums import Direction, TradeState, Action

class Trade(models.Model):
    trading_entity = models.CharField(max_length=120)
    counterparty = models.CharField(max_length=120)
    direction = models.CharField(max_length=4, choices=Direction.choices)
    style = models.CharField(max_length=20, default="FORWARD")
    notional_currency = models.CharField(max_length=3)
    notional_amount = models.DecimalField(max_digits=20, decimal_places=2)
    underlying = models.JSONField(default=list)
    trade_date = models.DateField()
    value_date = models.DateField()
    delivery_date = models.DateField()
    strike = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    requester_id = models.CharField(max_length=64)
    approver_id = models.CharField(max_length=64, null=True, blank=True)
    state = models.CharField(max_length=32, choices=TradeState.choices, default=TradeState.DRAFT)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(trade_date__lte=models.F("value_date")), name="trade_le_value"),
            models.CheckConstraint(check=models.Q(value_date__lte=models.F("delivery_date")), name="value_le_delivery"),
            models.CheckConstraint(
                check=models.Q(state="Executed") | models.Q(strike__isnull=True),
                name="strike_only_when_executed"
            ),
        ]

class ActionLog(models.Model):
    trade = models.ForeignKey(Trade, on_delete=models.CASCADE, related_name="action_logs")
    action = models.CharField(max_length=32, choices=Action.choices)
    actor_user_id = models.CharField(max_length=64)
    before_state = models.CharField(max_length=32, choices=TradeState.choices)
    after_state = models.CharField(max_length=32, choices=TradeState.choices)
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

class TradeVersion(models.Model):
    trade = models.ForeignKey(Trade, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    state = models.CharField(max_length=32, choices=TradeState.choices)
    snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    actor_user_id = models.CharField(max_length=64)
    action = models.CharField(max_length=32, choices=Action.choices)