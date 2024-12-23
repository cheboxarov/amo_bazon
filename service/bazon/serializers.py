from django.core.serializers import serialize
from rest_framework.serializers import ModelSerializer
from .models import SaleDocument
from rest_framework import serializers


class BazonSaleDocumentSerializer(ModelSerializer):

    class Meta:
        model = SaleDocument
        fields = "__all__"


class AddSalePaySerializer(serializers.Serializer):
    pay_source = serializers.IntegerField(required=True)
    pay_sum = serializers.FloatField(required=True)
    comment = serializers.CharField(required=False, allow_blank=True)


class PayBackSaleSerializer(serializers.Serializer):
    pay_source = serializers.IntegerField(required=True)
    pay_sum = serializers.IntegerField(required=True)


class CreateSaleSerializer(serializers.Serializer):
    comment = serializers.CharField(required=True)
    source = serializers.CharField(required=True)
    storage = serializers.IntegerField(required=True)
    manager = serializers.IntegerField(required=True)
    amoLeadId = serializers.IntegerField(required=True)

class CreateReceiptSerializer(serializers.Serializer):
    factory_number = serializers.CharField(required=True)
    cash_machine = serializers.CharField(required=True)
    contact = serializers.CharField(required=True)
    cash = serializers.IntegerField(required=True)
    electron = serializers.IntegerField(required=True)

class GenerateReceiptRequestSerializer(serializers.Serializer):
    factory_number = serializers.CharField(required=True)