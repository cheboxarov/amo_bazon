from .base_serializer import BaseSerializer


class AmoContactToBazonContactSerializer(BaseSerializer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def serialize(self):
        serialized_data = {}
        serialized_data["contact_id"] = self.data.get('id')
        serialized_data["company_id"] = self.data.get("linked_company_id")
        serialized_data["responsible_user_id"] = self.data.get("manager_id")

        self._serialized_data = serialized_data

    def get_serialized_data(self, with_id: bool = True):
        if not with_id:
            self._serialized_data.pop("contact_id", None)
        return super().get_serialized_data()
