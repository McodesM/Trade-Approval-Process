import unittest
from unittest.mock import patch

from trades_approval.services.versioning import create_snapshot, diff_snapshots


class TestVersioning(unittest.TestCase):
    @patch("trades_approval.services.versioning.TradeVersion")
    @patch("trades_approval.services.versioning.snapshot_model_dict")
    def test_create_snapshot_calls_orm_with_normalized_payload(self, mock_snap, MockTradeVersion):
        trade = type("T", (), {})()
        trade.id = 7
        trade.version = 3
        trade.state = "PendingApproval"

        mock_snap.return_value = {
            "id": 7,
            "notional_amount": "5000000.00",
            "state": "PendingApproval",
        }
        MockTradeVersion.objects.create.return_value = "CREATED_SNAPSHOT"
        out = create_snapshot(trade, actor_user_id="user_abc", action="Submit")

        mock_snap.assert_called_once_with(trade)
        MockTradeVersion.objects.create.assert_called_once_with(
            trade=trade,
            version_number=3,
            state="PendingApproval",
            snapshot=mock_snap.return_value,
            actor_user_id="user_abc",
            action="Submit",
        )
        self.assertEqual(out, "CREATED_SNAPSHOT")

    def test_diff_snapshots_pure_function(self):
        a = {"x": 1, "y": 2, "only_a": "A"}
        b = {"x": 1, "y": 3, "only_b": "B"}

        diff = diff_snapshots(a, b)
        self.assertEqual(diff["y"], (2, 3))

        self.assertEqual(diff["only_a"], ("A", None))
        self.assertEqual(diff["only_b"], (None, "B"))
        self.assertNotIn("x", diff)
