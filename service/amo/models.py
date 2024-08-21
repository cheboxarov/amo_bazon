from django.db import models


class AmoAccount(models.Model):
    suburl = models.CharField(max_length=255)
    token = models.CharField(max_length=255)
    bazon_accounts = models.ManyToManyField('bazon.BazonAccount', related_name='amo_accounts')

    def __str__(self):
        return self.suburl


class Status(models.Model):
    BAZON_STATUSES = [
        ('NEW', 'Новый'),
        ('WORK', 'В работе'),
        ('ISSUED', 'Выданные'),
        ('NOT_IMPLEMENTED', 'Не реализованные'),
    ]

    amo_id = models.IntegerField()
    name = models.CharField(max_length=255)
    bazon_status = models.CharField(max_length=20, choices=BAZON_STATUSES, blank=True, null=True)
    amo_account = models.ForeignKey(AmoAccount, on_delete=models.CASCADE, related_name='statuses')

    def __str__(self):
        return self.name


class Manager(models.Model):
    name = models.CharField(max_length=255)
    amo_id = models.IntegerField()
    bazon_id = models.IntegerField(blank=True, null=True)
    amo_account = models.ForeignKey(AmoAccount, on_delete=models.CASCADE, related_name='managers')

    def __str__(self):
        return self.name
