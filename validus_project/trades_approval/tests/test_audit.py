import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from trades_approval.services.audit import log_action, get_trade_action_logs


class TestAuditUnit(unittest.TestCase):
    @patch("trades_approval.services.audit.ActionLog")
    def test_log_action_calls_orm_create(self, MockActionLog):
        trade = SimpleNamespace(id=123)
        MockActionLog.objects.create.return_value = "CREATED_ROW"

        out = log_action(
            trade=trade,
            action="Submit",
            actor_user_id="user_001",
            before_state="Draft",
            after_state="PendingApproval",
            note="Trade details provided",
        )

        MockActionLog.objects.create.assert_called_once_with(
            trade=trade,
            action="Submit",
            actor_user_id="user_001",
            before_state="Draft",
            after_state="PendingApproval",
            note="Trade details provided",
        )
        self.assertEqual(out, "CREATED_ROW")

    def test_get_trade_action_logs_transforms_rows(self):

        created1 = datetime(2025, 11, 11, 9, 30, 15)
        created2 = datetime(2025, 11, 11, 9, 45, 12)
        row1 = SimpleNamespace(
            created_at=created1,
            action="Submit",
            actor_user_id="user_001",
            before_state="Draft",
            after_state="PendingApproval",
            note="init",
        )
        row2 = SimpleNamespace(
            created_at=created2,
            action="Approve",
            actor_user_id="user_002",
            before_state="PendingApproval",
            after_state="Approved",
            note="ok",
        )

        order_by_mock = MagicMock(return_value=[row1, row2])
        action_logs_manager = SimpleNamespace(order_by=order_by_mock)
        trade = SimpleNamespace(action_logs=action_logs_manager)

        result = get_trade_action_logs(trade)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["action"], "Submit")
        self.assertEqual(result[0]["actorUserId"], "user_001")
        self.assertEqual(result[0]["fromState"], "Draft")
        self.assertEqual(result[0]["toState"], "PendingApproval")
        self.assertEqual(result[0]["note"], "init")
        self.assertEqual(result[0]["timestamp"], created1.isoformat())

        self.assertEqual(result[1]["action"], "Approve")
        self.assertEqual(result[1]["actorUserId"], "user_002")
        self.assertEqual(result[1]["fromState"], "PendingApproval")
        self.assertEqual(result[1]["toState"], "Approved")
        self.assertEqual(result[1]["note"], "ok")
        self.assertEqual(result[1]["timestamp"], created2.isoformat())

        order_by_mock.assert_called_once_with("created_at")
