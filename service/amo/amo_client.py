import requests


class AmoCRMClient:
    def __init__(self, token, subdomain):
        self.token = token
        self.subdomain = subdomain
        self.base_url = f"https://{subdomain}.amocrm.ru/api/v4"

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def get_statuses(self):
        url = f"{self.base_url}/leads/pipelines"
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    def get_managers(self):
        url = f"{self.base_url}/users"
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    def create_deal(self, deal_payload: dict, custom_fields=None):
        """
        Метод для создания сделки в amoCRM.
        """
        url = f"{self.base_url}/leads"
        data = deal_payload

        if custom_fields is not None:
            data["custom_fields_values"] = custom_fields
        response = requests.post(url, headers=self._get_headers(), json=[data])
        response.raise_for_status()
        return response.json()

    def update_deal(self, deal_payload: dict, custom_fields=None):
        """
        Метод для обновления сделки в amoCRM.
        """
        url = f"{self.base_url}/leads/{deal_payload['id']}"

        data = deal_payload

        if custom_fields is not None:
            data["custom_fields_values"] = custom_fields

        response = requests.patch(url, headers=self._get_headers(), json=data)

        response.raise_for_status()
        return response.json()

    def delete_deal(self, deal_id):
        """
        Метод для удаления сделки в amoCRM.
        """
        url = f"{self.base_url}/leads/{deal_id}"

        response = requests.delete(url, headers=self._get_headers())

        response.raise_for_status()

        if response.status_code == 204:
            return {"message": "Deal deleted successfully"}
        else:
            return response.json()
