from django.contrib import admin
from .models import AmoAccount, Status, Manager


# Register your models here.
admin.site.register(AmoAccount)
admin.site.register(Status)
admin.site.register(Manager)
