from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import TradeViewSet

router = DefaultRouter()
router.register(r"trades", TradeViewSet, basename="trade")

urlpatterns = [
    path("", include(router.urls)),
]
