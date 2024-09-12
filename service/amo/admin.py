from django.contrib import admin
from .models import AmoAccount, Status, Manager


admin.site.register(AmoAccount)

@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    fields = ("name", "amo_account", "bazon_status")

@admin.register(Manager)
class AdminManager(admin.ModelAdmin):
    fields = ("name", "amo_account")
