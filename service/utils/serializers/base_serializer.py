class BaseSerializer:
    def __init__(self, data: dict):
        self.data = data
        self._serialized_data = None

    def serialize(self):
        self._serialized_data = self.data

    def get_serialized_data(self):
        if self._serialized_data is None:
            raise ValueError("Data is not serialized, please use serialize()")
        return self._serialized_data

