from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from django.urls import reverse
from rest_framework.test import APISimpleTestCase
from rest_framework import status
from django.http import Http404
from trades_approval.services.trade_workflow import InvalidTransition, PermissionDenied


def fake_trade(
    *,
    id=1,
    state="PendingApproval",
    approver_id=None,
    requester_id="user_001",
    strike=None,
    version=1,
):
    return SimpleNamespace(
        id=id,
        state=state,
        approver_id=approver_id,
        requester_id=requester_id,
        strike=strike,
        version=version
    )


class TestTradeViewSet(APISimpleTestCase):
    @patch("trades_approval.views.create_and_submit")
    def test_submit_success(self, mock_submit):
        t = fake_trade(state="PendingApproval", id=42)
        mock_submit.return_value = t

        url = reverse("trade-submit")
        payload = {
            "userId": "user_001",
            "tradeDetails": {
                "tradingEntity": "Validus Capital Ltd",
                "counterparty": "Bank of England",
                "direction": "BUY",
                "style": "FORWARD",
                "notionalCurrency": "USD",
                "notionalAmount": 5000000.00,
                "underlying": ["USD", "EUR"],
                "tradeDate": "2025-11-01",
                "valueDate": "2025-11-05",
                "deliveryDate": "2025-11-10",
            },
        }
        res = self.client.post(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["id"], 42)
        self.assertEqual(res.data["state"], "PendingApproval")
        _, kwargs = mock_submit.call_args
        self.assertEqual(kwargs["actor_id"], "user_001")
        self.assertIn("tradingEntity", kwargs["trade_detail"])

    def test_submit_missing_userid_400(self):
        url = reverse("trade-submit")
        res = self.client.post(url, {"tradeDetails": {}}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("trades_approval.views.approve_trade")
    @patch("trades_approval.views.TradeViewSet.get_object")
    def test_approve_success(self, mock_get_object, mock_approve):
        t = fake_trade(state="PendingApproval", id=10)
        mock_get_object.return_value = t
        mock_approve.return_value = t

        url = reverse("trade-approve", kwargs={"pk": t.id})
        res = self.client.post(url, {"userId": "user_002"}, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], 10)

    @patch("trades_approval.views.approve_trade")
    @patch("trades_approval.views.TradeViewSet.get_object")
    def test_approve_invalid_transition_400(self, mock_get_object, mock_approve):
        t = fake_trade(state="Draft", id=11)
        mock_get_object.return_value = t
        mock_approve.side_effect = InvalidTransition("bad state")

        url = reverse("trade-approve", kwargs={"pk": t.id})
        res = self.client.post(url, {"userId": "user_002"}, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", res.data)

    @patch("trades_approval.views.TradeViewSet.get_object")
    def test_approve_missing_userid_400(self, mock_get_object):
        mock_get_object.return_value = fake_trade(id=1)  # avoid DB
        url = reverse("trade-approve", kwargs={"pk": 1})
        res = self.client.post(url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("trades_approval.views.cancel_trade")
    @patch("trades_approval.views.TradeViewSet.get_object")
    def test_cancel_success(self, mock_get_object, mock_cancel):
        t = fake_trade(state="Approved", id=12)
        mock_get_object.return_value = t
        mock_cancel.return_value = t

        url = reverse("trade-cancel", kwargs={"pk": t.id})
        res = self.client.post(url, {"userId": "user_001"}, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], 12)

    @patch("trades_approval.views.cancel_trade")
    @patch("trades_approval.views.TradeViewSet.get_object")
    def test_cancel_permission_denied_400(self, mock_get_object, mock_cancel):
        t = fake_trade(state="PendingApproval", id=13, requester_id="req", approver_id="appr")
        mock_get_object.return_value = t
        mock_cancel.side_effect = PermissionDenied("nope")

        url = reverse("trade-cancel", kwargs={"pk": t.id})
        res = self.client.post(url, {"userId": "intruder"}, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", res.data)

    @patch("trades_approval.views.update_trade")
    @patch("trades_approval.views.TradeViewSet.get_object")
    def test_update_success(self, mock_get_object, mock_update):
        t = fake_trade(state="PendingApproval", id=14, approver_id="user_002")
        mock_get_object.return_value = t
        mock_update.return_value = t

        url = reverse("trade-update-action", kwargs={"pk": t.id})
        payload = {
            "userId": "user_002",
            "tradeUpdateDetails": {"notionalAmount": 2000000.00},
        }
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], 14)
        _, kwargs = mock_update.call_args
        self.assertEqual(kwargs["actor_id"], "user_002")
        self.assertIn("notionalAmount", kwargs["trade_detail"])

    @patch("trades_approval.views.update_trade")
    @patch("trades_approval.views.TradeViewSet.get_object")
    def test_update_permission_denied_400(self, mock_get_object, mock_update):
        t = fake_trade(state="PendingApproval", id=15, approver_id=None, requester_id="user_001")
        mock_get_object.return_value = t
        mock_update.side_effect = PermissionDenied("only approver can update")

        url = reverse("trade-update-action", kwargs={"pk": t.id})
        payload = {"userId": "user_001", "tradeUpdateDetails": {"style": "OPTION"}}
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", res.data)

    @patch("trades_approval.views.TradeViewSet.get_object")
    def test_update_missing_userid_400(self, mock_get_object):
        mock_get_object.return_value = fake_trade(id=1)  # avoid DB
        url = reverse("trade-update-action", kwargs={"pk": 1})
        res = self.client.patch(url, {"tradeUpdateDetails": {}}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("trades_approval.views.send_to_execute_trade")
    @patch("trades_approval.views.TradeViewSet.get_object")
    def test_send_to_execute_success(self, mock_get_object, mock_send):
        t = fake_trade(state="Approved", id=16, approver_id="user_002")
        mock_get_object.return_value = t
        mock_send.return_value = t

        url = reverse("trade-send-to-execute", kwargs={"pk": t.id})
        res = self.client.post(url, {"userId": "user_002"}, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], 16)

    @patch("trades_approval.views.send_to_execute_trade")
    @patch("trades_approval.views.TradeViewSet.get_object")
    def test_send_to_execute_invalid_state_400(self, mock_get_object, mock_send):
        t = fake_trade(state="PendingApproval", id=17, approver_id="user_002")
        mock_get_object.return_value = t
        mock_send.side_effect = InvalidTransition("must be Approved")

        url = reverse("trade-send-to-execute", kwargs={"pk": t.id})
        res = self.client.post(url, {"userId": "user_002"}, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", res.data)

    @patch("trades_approval.views.book_trade")
    @patch("trades_approval.views.TradeViewSet.get_object")
    def test_book_success(self, mock_get_object, mock_book):
        t = fake_trade(state="SentToCounterparty", id=18, approver_id="user_002")

        def _side_effect(trade, actor_id, strike):
            trade.state = "Executed"
            trade.strike = Decimal(str(strike))
            return trade

        mock_get_object.return_value = t
        mock_book.side_effect = _side_effect

        url = reverse("trade-book", kwargs={"pk": t.id})
        payload = {"userId": "user_001", "strike": "1.24567"}
        res = self.client.post(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], 18)
        self.assertEqual(res.data["state"], "Executed")
        self.assertEqual(res.data["strike"], "1.245670")

    @patch("trades_approval.views.book_trade")
    @patch("trades_approval.views.TradeViewSet.get_object")
    def test_book_unauthorized_400(self, mock_get_object, mock_book):
        t = fake_trade(state="SentToCounterparty", id=19, approver_id="user_002", requester_id="user_001")
        mock_get_object.return_value = t
        mock_book.side_effect = PermissionDenied("not allowed")

        url = reverse("trade-book", kwargs={"pk": t.id})
        res = self.client.post(url, {"userId": "intruder", "strike": "1.0"}, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", res.data)

    @patch("trades_approval.views.get_trade_action_logs")
    @patch("trades_approval.views.TradeViewSet.get_object")
    def test_history_success(self, mock_get_object, mock_history):
        t = fake_trade(state="Approved", id=20, approver_id="user_002")
        mock_get_object.return_value = t
        mock_history.return_value = [
            {"timestamp": datetime(2025, 11, 11, 9, 30).isoformat(),
             "action": "Submit", "actorUserId": "user_001", "fromState": "Draft", "toState": "PendingApproval", "note": "init"},
            {"timestamp": datetime(2025, 11, 11, 9, 45).isoformat(),
             "action": "Approve", "actorUserId": "user_002", "fromState": "PendingApproval", "toState": "Approved", "note": "ok"},
        ]

        url = reverse("trade-history", kwargs={"pk": t.id})
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["tradeId"], 20)
        self.assertEqual(len(res.data["history"]), 2)

    @patch("trades_approval.views.TradeViewSet.get_object")
    def test_diff_success(self, mock_get_object):
        t = fake_trade(state="Approved", id=21)

        ver1 = SimpleNamespace(snapshot={"notional_amount": "5000000.00"})
        ver2 = SimpleNamespace(snapshot={"notional_amount": "2000000.00"})

        versions_manager = MagicMock()
        versions_manager.get.side_effect = [ver1, ver2]
        t.versions = versions_manager

        mock_get_object.return_value = t

        url = reverse("trade-diff", kwargs={"pk": t.id})
        payload = {"fromVersion": 1, "toVersion": 2}
        res = self.client.post(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("diff", res.data)
        versions_manager.get.assert_any_call(version_number=1)
        versions_manager.get.assert_any_call(version_number=2)

    @patch("trades_approval.views.TradeViewSet.get_object")
    def test_diff_missing_versions_404(self, mock_get_object):
        t = fake_trade(state="Approved", id=22)

        versions_manager = MagicMock()
        class _DoesNotExist(Exception): ...
        versions_manager.get.side_effect = _DoesNotExist("no row")
        t.versions = versions_manager
        mock_get_object.return_value = t

        with patch("trades_approval.views.TradeVersion") as MockTV:
            MockTV.DoesNotExist = _DoesNotExist

            url = reverse("trade-diff", kwargs={"pk": t.id})
            res = self.client.post(url, {"fromVersion": 1, "toVersion": 99}, format="json")

            self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    @patch("trades_approval.views.TradeViewSet.get_object")
    def test_diff_missing_inputs_400(self, mock_get_object):
        mock_get_object.return_value = fake_trade(id=1)
        url = reverse("trade-diff", kwargs={"pk": 1})
        res = self.client.post(url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("trades_approval.views.get_object_or_404")
    @patch("trades_approval.views.TradeViewSet.get_object")
    def test_version_snapshot_200(self, mock_get_object, mock_get_obj_or_404):
        t = fake_trade(state="Approved", id=23)
        t.versions = MagicMock()
        tv = SimpleNamespace(
            version_number=1,
            state="PendingApproval",
            snapshot={"foo": "bar"},
            created_at=datetime(2025, 11, 11, 9, 0, 0),
            actor_user_id="user_001",
            action="Submit",
        )
        mock_get_object.return_value = t
        mock_get_obj_or_404.return_value = tv

        url = reverse("trade-version-snapshot", kwargs={"pk": t.id, "version": 1})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["version"], 1)
        self.assertEqual(res.data["tradeId"], 23)

    @patch("trades_approval.views.get_object_or_404")
    @patch("trades_approval.views.TradeViewSet.get_object")
    def test_version_snapshot_404(self, mock_get_object, mock_get_obj_or_404):
        t = fake_trade(state="Approved", id=24)
        t.versions = MagicMock()
        mock_get_object.return_value = t
        mock_get_obj_or_404.side_effect = Http404()

        url = reverse("trade-version-snapshot", kwargs={"pk": t.id, "version": 99})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
