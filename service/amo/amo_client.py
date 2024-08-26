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
