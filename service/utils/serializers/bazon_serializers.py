from .base_serializer import BaseSerializer
from amo.models import Status, Manager
from bazon.models import SaleDocument
from django.db.models import ObjectDoesNotExist


class BazonSaleToAmoLeadSerializer(BaseSerializer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def serialize(self):

        serialized_data = {"name": f"Сделка с Bazon №{self.data.get('number')}"}
        try:
            sale_document = SaleDocument.objects.get(
                internal_id=self.data.get("internal_id")
            )
            amo_lead_id = sale_document.amo_lead_id
            if amo_lead_id:
                serialized_data["id"] = amo_lead_id
        except ObjectDoesNotExist:
            pass
        sum = self.data.get("sum")
        if sum:
            serialized_data["price"] = sum
        bazon_status = self.data.get("status")
        if Status.objects.filter(bazon_status=bazon_status).exists():
            status = Status.objects.get(bazon_status=bazon_status)
            serialized_data["status_id"] = status.amo_id
        manager_id = self.data.get("manager_id")
        if Manager.objects.filter(bazon_id=manager_id).exists():
            manager = Manager.objects.get(bazon_id=manager_id)
            serialized_data["responsible_user_id"] = manager.amo_id
        self._serialized_data = serialized_data

    def get_serialized_data(self, with_id: bool = True):
        if not with_id:
            try:
                self._serialized_data.pop("id")
            except KeyError:
                pass
        return super().get_serialized_data()


class ContractorToAmoClient(BaseSerializer):
    def __init(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def serialize(self):
        pass
