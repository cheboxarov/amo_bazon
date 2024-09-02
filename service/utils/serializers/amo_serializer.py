from amo.models import Status, Manager
from .base_serializer import BaseSerializer


class AmoLeadToBazonSaleDocument(BaseSerializer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def serialize(self):
        serialized_data = {}
        serialized_data["manager_comment"] = self.data.get("name")
        price = self.data.get("price")
        if price:
            serialized_data["sum"] = price
        status_id = self.data.get("status_id")
        if Status.objects.filter(amo_id=status_id).exists():
            status = Status.objects.get(amo_id=status_id)
            serialized_data["state"] = status.bazon_status

        self._serialized_data = serialized_data
        responsible_user_id = self.data.get("responsible_user_id")
        if Manager.objects.filter(amo_id=responsible_user_id).exists():
            manager = Manager.objects.get(amo_id=responsible_user_id)
            serialized_data["manager_id"] = manager.bazon_id
        self._serialized_data = serialized_data

    def get_serialized_data(self, with_id: bool = True):
        if not with_id:
            self._serialized_data.pop("contact_id", None)
        return super().get_serialized_data()
