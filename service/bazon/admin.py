from django.contrib import admin
from .models import BazonAccount, SaleDocument, Contractor


# Register your models here.
admin.site.register(BazonAccount)
admin.site.register(SaleDocument)
admin.site.register(Contractor)
