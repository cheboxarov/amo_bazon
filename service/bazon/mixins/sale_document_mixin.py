from bazon.models import SaleDocument
from rest_framework.exceptions import APIException


class SaleDocumentMixin:

    def get_sale_document(self, amo_lead_id: int) -> SaleDocument:
        queryset = SaleDocument.objects.filter(amo_lead_id=amo_lead_id)
        if not queryset.exists():
            raise APIException("sale document not found", code=404)
        sale_document: SaleDocument = queryset.first()
        return sale_document