from django.contrib import admin
from .models import Trade, ActionLog, TradeVersion

admin.site.register(Trade)
admin.site.register(ActionLog)
admin.site.register(TradeVersion)
