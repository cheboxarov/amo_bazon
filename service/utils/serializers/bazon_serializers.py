from .base_serializer import BaseSerializer
from amo.models import Status, Manager


class BazonSaleToAmoLeadSerializer(BaseSerializer):

    def serialize(self):
        serialized_data = {}
        serialized_data["name"] = self.data.get("number")
        bazon_status = self.data.get("status")
        if Status.objects.filter(bazon_status=bazon_status).exists():
            status = Status.objects.get(bazon_status=bazon_status)
            serialized_data["status_id"] = status.amo_id
        manager_id = self.data.get("manager_id")
        if Manager.objects.filter(bazon_id=manager_id).exists():
            manager = Manager.objects.get(bazon_id=manager_id)
            serialized_data["responsible_user_id"] = manager.amo_id
        self._serialized_data = serialized_data
