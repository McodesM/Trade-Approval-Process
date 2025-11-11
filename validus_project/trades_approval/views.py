from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import Http404
from .models import Trade, TradeVersion
from .services.use_cases import (
    create_and_submit, approve_trade, cancel_trade, update_trade,
    send_to_execute_trade, book_trade
)
from .serializers import TradeDetailsSerializer, TradeUpdateSerializer, BookSerializer
from .services.trade_workflow import InvalidTransition, PermissionDenied
from .services.audit import get_trade_action_logs
from .services.versioning import diff_snapshots
from django.shortcuts import get_object_or_404

class TradeViewSet(viewsets.GenericViewSet):
    queryset = Trade.objects.all()

    @action(detail=False, methods=["post"])
    def submit(self, request):
        user_id = request.data.get("userId")
        if not user_id:
            return Response({"error": "userId is required."}, status=400)
        s = TradeDetailsSerializer(data=request.data.get("tradeDetails") or {})
        s.is_valid(raise_exception=True)
        try:
            trade = create_and_submit(trade_detail=s.validated_data, actor_id=user_id)
            return Response({"id": trade.id, "state": trade.state}, status=201)
        except Exception as e:
            return Response({"detail": f"Internal error: {str(e)}"}, status=500)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        trade = self.get_object()
        actor_id = request.data.get("userId")
        if not actor_id:
            return Response({"error": "userId is required."}, status=400)
        try:
            approve_trade(trade, actor_id=actor_id)
            return Response({"id": trade.id, "state": trade.state}, status=200)
        except (InvalidTransition, PermissionDenied) as e:
            return Response({"detail": str(e)}, status=400)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        trade = self.get_object()
        actor_id = request.data.get("userId")
        if not actor_id:
            return Response({"error": "userId is required."}, status=400)
        try:
            cancel_trade(trade, actor_id=actor_id)
            return Response({"id": trade.id, "state": trade.state}, status=200)
        except (InvalidTransition, PermissionDenied) as e:
            return Response({"detail": str(e)}, status=400)
        except Exception as e:
            return Response({"detail": f"Internal error: {str(e)}"}, status=500)

    @action(detail=True, methods=["patch"], url_path="update")
    def update_action(self, request, pk=None):
        trade = self.get_object()
        actor_id = request.data.get("userId")
        if not actor_id:
            return Response({"error": "userId is required."}, status=400)
        s = TradeUpdateSerializer(data=request.data.get("tradeUpdateDetails") or {}, context={"trade": trade})
        s.is_valid(raise_exception=True)
        try:
            update_trade(trade, actor_id=actor_id, trade_detail=s.validated_data)
            return Response({"id": trade.id, "state": trade.state}, status=200)
        except (InvalidTransition, PermissionDenied) as e:
            return Response({"detail": str(e)}, status=400)
        except Exception as e:
            return Response({"detail": f"Internal error: {str(e)}"}, status=500)

    @action(detail=True, methods=["post"], url_path="send-to-execute")
    def send_to_execute(self, request, pk=None):
        trade = self.get_object()
        actor_id = request.data.get("userId")
        if not actor_id:
            return Response({"error": "userId is required."}, status=400)
        try:
            send_to_execute_trade(trade, actor_id=actor_id)
            return Response({"id": trade.id, "state": trade.state}, status=200)
        except (InvalidTransition, PermissionDenied) as e:
            return Response({"detail": str(e)}, status=400)
        except Exception as e:
            return Response({"detail": f"Internal error: {str(e)}"}, status=500)

    @action(detail=True, methods=["post"])
    def book(self, request, pk=None):
        trade = self.get_object()
        s = BookSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            book_trade(trade, actor_id=s.validated_data["userId"], strike=s.validated_data["strike"])
            return Response({"id": trade.id, "state": trade.state, "strike": str(trade.strike)}, status=200)
        except (InvalidTransition, PermissionDenied) as e:
            return Response({"detail": str(e)}, status=400)
        except Exception as e:
            return Response({"detail": f"Internal error: {str(e)}"}, status=500)
    
    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        trade = self.get_object()
        try:
            trade_action_logs = get_trade_action_logs(trade)
            return Response({"tradeId": trade.id, "history": trade_action_logs}, status=200)
        except Exception as e:
            return Response({"detail": f"Internal error: {str(e)}"}, status=500)

    
    @action(detail=True, methods=["post"])
    def diff(self, request, pk=None):
        trade = self.get_object()
        body = request.data or {}
        try:
            v_from = int(body["fromVersion"]); v_to = int(body["toVersion"])
        except Exception:
            return Response({"detail": "fromVersion and toVersion are required integers."}, status=400)

        try:
            a = trade.versions.get(version_number=v_from).snapshot
            b = trade.versions.get(version_number=v_to).snapshot
            diffs = diff_snapshots(a, b)
            return Response({"diff": diffs}, status=200)
        except TradeVersion.DoesNotExist:
            return Response({"detail": "One or both specified versions do not exist."}, status=404)
        except Exception as e:
            return Response({"detail": f"Internal error: {str(e)}"}, status=500)
        
    
    @action(detail=True, methods=["get"], url_path=r"versions/(?P<version>\d+)")
    def version_snapshot(self, request, pk=None, version=None):
        trade = self.get_object()
        try:
            tv = get_object_or_404(trade.versions, version_number=version)
            return Response({
                "tradeId": trade.id,
                "version": tv.version_number,
                "state": tv.state,
                "snapshot": tv.snapshot,
                "createdAt": tv.created_at.isoformat(),
                "actorUserId": tv.actor_user_id,
                "action": tv.action,
            }, status=200)
        except Http404:
            return Response({"detail": "Specified version does not exist."}, status=404)
        except Exception as e:
            return Response({"detail": f"Internal error: {str(e)}"}, status=500)