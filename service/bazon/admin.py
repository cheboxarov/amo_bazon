from django.contrib import admin
from .models import BazonAccount, SaleDocument, Contractor

admin.site.register(BazonAccount)


@admin.register(SaleDocument)
class SaleDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "internal_id",
        "number",
        "amo_account",
        "bazon_account",
        "status",
        "amo_lead_id",
    )
    list_filter = ("amo_account",)


@admin.register(Contractor)
class ContractorAdmin(admin.ModelAdmin):
    list_display = ("internal_id", "amo_account", "name", "amo_id", "amo_account")
    list_filter = ("amo_account",)