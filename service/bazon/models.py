from django.db import models
from bazon_api.api import Bazon


class BazonAccount(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    login = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    refresh_token = models.TextField(null=True, blank=True)
    access_token = models.TextField(null=True, blank=True)

    def auth(self):
        bazon = Bazon(login=self.login, password=self.password)
        self.refresh_token = bazon.get_refresh_token()
        self.access_token = bazon.get_access_token()

    def refresh_auth(self):
        bazon = Bazon(login=self.login, password=self.password)
        bazon.refresh_me()
        self.refresh_token = bazon.get_refresh_token()
        self.access_token = bazon.get_access_token()
        self.save()

    def save(self, *args, **kwargs):

        if not bool(self.id):
            self.auth()

        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# class Product(models.Model):
#     bazon_account = models.ForeignKey(BazonAccount, on_delete=models.CASCADE)
#     internal_id = models.PositiveIntegerField()
#     created_at = models.CharField(max_length=500)
#     name = models.CharField(max_length=500)
#     type = models.CharField(max_length=50)
#     price = models.PositiveIntegerField()
#     amount = models.PositiveIntegerField()
#     reserved = models.PositiveIntegerField()
#     last_rack = models.TextField()
#     in_storages = models.TextField()
#     in_movings_to = models.TextField()
# 
#     def __str__(self):
#         return f"{self.name} ({self.internal_id})"


class SaleDocument(models.Model):

    bazon_account = models.ForeignKey(BazonAccount, on_delete=models.CASCADE)
    internal_id = models.PositiveIntegerField(unique=True)
    number = models.CharField(max_length=255, null=True, blank=True)
    type = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    sum = models.PositiveIntegerField(null=True, blank=True)
    storage_id = models.PositiveIntegerField(null=True, blank=True)
    contractor_id = models.PositiveIntegerField(null=True, blank=True)
    contractor_name = models.CharField(max_length=255, null=True, blank=True)
    manager_id = models.PositiveIntegerField(null=True, blank=True)
    manager_name = models.CharField(max_length=255, null=True, blank=True)
    amo_lead_id = models.PositiveIntegerField(blank=True, null=True)
    # products = models.ManyToManyField(Product, null=True, blank=True)

    def __str__(self):
        return f"{self.internal_id} ({self.contractor_name})"
