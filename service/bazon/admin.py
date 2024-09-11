from django.contrib import admin
from .models import BazonAccount, SaleDocument, Contractor

admin.site.register(BazonAccount)


@admin.register(SaleDocument)
class SaleDocumentAdmin(admin.ModelAdmin):
    list_display = ('internal_id', 'amo_account', "bazon_account", "status", "amo_lead_id")

@admin.register(Contractor)
class ContractorAdmin(admin.ModelAdmin):
    list_display = ('internal_id', 'amo_account', 'name')
