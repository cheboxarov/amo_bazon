from rest_framework.serializers import ModelSerializer
from .models import SaleDocument


class BazonSaleDocumentSerializer(ModelSerializer):

    class Meta:
        model = SaleDocument
        fields = "__all__"
