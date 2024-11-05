import json
from django.db import models
from .amo_client import AmoCRMClient, DealClient, CompanyClient, ContactClient


class AmoAccount(models.Model):
    suburl = models.CharField(max_length=255, unique=True, verbose_name="Поддомен")
    token = models.TextField(verbose_name="Токен")
    bazon_accounts = models.ManyToManyField('bazon.BazonAccount', related_name='amo_accounts', verbose_name="Аккаунты Bazon")
    config = models.JSONField(default=json.dumps({
        "contact_phone_field": 0,
        "contact_email_field": 0,
        "company_phone_field": 0,
        "company_email_field": 0,
        "company_inn_field": 0,
        "bazon_field": 0
    }))


    def __str__(self):
        return self.suburl

    class Meta:
        verbose_name = "Аккаунт AmoCRM"
        verbose_name_plural = "Аккаунты AmoCRM"

    def get_amo_client(self):
        return AmoCRMClient(self.token, self.suburl)
    
    def get_deal_client(self):
        return DealClient(self.token, self.suburl)
    
    def get_contact_client(self):
        return ContactClient(self.token, self.suburl)
    
    def get_company_client(self):
        return CompanyClient(self.token, self.suburl)
    
    def get_config(self) -> dict:
        return json.loads(self.config)

class Status(models.Model):
    BAZON_STATUSES = [
        ('draft', 'Новый'),
        ('reserve', 'В работе'),
        ('issued', 'Выданные'),
        ('canceled', 'Не реализованные'),
    ]

    amo_id = models.IntegerField(verbose_name="ID в AmoCRM")
    name = models.CharField(max_length=255, verbose_name="Имя")
    pipeline_name = models.CharField(max_length=255, verbose_name="Название воронки")
    pipeline_id = models.PositiveBigIntegerField(verbose_name="Айди воронки")
    bazon_status = models.CharField(max_length=20, choices=BAZON_STATUSES, blank=True, null=True, verbose_name="Статус в Bazon")
    amo_account = models.ForeignKey(AmoAccount, on_delete=models.CASCADE, related_name='statuses', verbose_name="Аккаунт в AmoCRM")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Статус воронки"
        verbose_name_plural = "Статусы воронок"
        constraints = [
            models.UniqueConstraint(fields=['pipeline_id', 'amo_id'], name="unique_pipeline_id_amo_id")
        ]


class Manager(models.Model):
    name = models.CharField(max_length=255, verbose_name="Имя")
    amo_id = models.IntegerField(verbose_name="ID в AmoCRM")
    bazon_id = models.IntegerField(blank=True, null=True, verbose_name="ID в Bazon")
    amo_account = models.ForeignKey(AmoAccount, on_delete=models.CASCADE, related_name='managers', verbose_name="Аккаунт AmoCRM")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Менеджер"
        verbose_name_plural = "Менеджеры"
