from django.db import models
from utils.bazon_api import Bazon


class BazonAccount(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    login = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    refresh_token = models.TextField(null=True, blank=True)
    access_token = models.TextField(null=True, blank=True)

    def get_api(self) -> Bazon:
        if self.access_token is None or self.refresh_token is None:
            return None
        bazon = Bazon(self.login, self.password, self.refresh_token, self.access_token)
        return bazon

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

    class Meta:
        verbose_name = "Аккаунт Bazon"
        verbose_name_plural = "Аккаунты Bazon"


class SaleDocument(models.Model):

    bazon_account = models.ForeignKey(BazonAccount, on_delete=models.CASCADE)
    amo_account = models.ForeignKey("amo.AmoAccount", on_delete=models.CASCADE)
    internal_id = models.PositiveIntegerField()
    number = models.CharField(max_length=255, null=True, blank=True)
    type = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    sum = models.PositiveIntegerField(null=True, blank=True)
    storage_id = models.PositiveIntegerField(null=True, blank=True)
    contractor_id = models.PositiveIntegerField(null=True, blank=True)
    contractor_linked = models.BooleanField(default=False)
    contractor_name = models.CharField(max_length=255, null=True, blank=True)
    manager_id = models.PositiveIntegerField(null=True, blank=True)
    manager_name = models.CharField(max_length=255, null=True, blank=True)
    amo_lead_id = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["amo_account", "internal_id"],
                name="unique_internal_id_per_amo_account",
            )
        ]

    def get_api(self):
        return self.bazon_account.get_api()

    class _GenerateLockKey:

        def __init__(self, sale_document: "SaleDocument"):
            self.sale_document = sale_document
            self.lock_key = None

        def __enter__(self):
            api = self.sale_document.get_api()
            lock_key = api.generate_lock_key(self.sale_document.number)
            if lock_key is None:
                print("Error to generate lock key")
            self.lock_key = lock_key
            return self.lock_key

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.lock_key is not None:
                api = self.sale_document.get_api()
                api.drop_lock_key(self.sale_document.internal_id, self.lock_key)

    def generate_lock_key(self):
        return self._GenerateLockKey(self)

    class Meta:
        verbose_name = "Сделка в Bazon"
        verbose_name_plural = "Сделки в Bazon"

    def __str__(self):
        return f"Заявка с Bazon №{self.internal_id}"


class Contractor(models.Model):
    bazon_account = models.ForeignKey(BazonAccount, on_delete=models.CASCADE)
    amo_account = models.ForeignKey("amo.AmoAccount", on_delete=models.CASCADE)
    internal_id = models.PositiveIntegerField()
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50)
    phone = models.CharField(max_length=50, null=True, blank=True)
    email = models.CharField(max_length=50, null=True, blank=True)
    manager_comment = models.TextField(null=True, blank=True)
    balance_free = models.PositiveIntegerField()
    balance_reserve = models.PositiveIntegerField()
    balance = models.PositiveIntegerField()
    amo_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["amo_account", "internal_id"], name="unique_internal_id_per_amo"
            ),
        ]

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Контрагент в Bazon"
        verbose_name_plural = "Контрагенты в Bazon"
