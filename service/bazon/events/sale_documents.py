from django.core.serializers import serialize

from bazon.models import SaleDocument
from utils.serializers import BazonSaleToAmoLeadSerializer


def on_create_sale_document(sale_data):
    serializer = BazonSaleToAmoLeadSerializer(sale_data)
    serializer.serialize()
    serialized_data = serializer.get_serialized_data(with_id=False)
    print(f"Created sale document:\n{serialized_data}\n{sale_data}")

def on_update_sale_document(sale_data):
    serializer = BazonSaleToAmoLeadSerializer(sale_data)
    serializer.serialize()
    serialized_data = serializer.get_serialized_data(with_id=True)
    print(f"Updated sale document:\n{serialized_data}\n{sale_data}")