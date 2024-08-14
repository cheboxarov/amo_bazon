import requests
from typing import Collection


class Bazon:


    def __init__(self, login: str,
                 password: str,
                 refresh_token: Collection[str] = None,
                 access_token: Collection[str] = None):
        self._login = login
        self._password = password
        if refresh_token:
            self._refresh_token = refresh_token
            self._access_token = access_token
        else:
            auth_data = self.get_auth_data()
            if auth_data.status_code == 200:
                self._refresh_token = auth_data.json()['RT']
                self._access_token = auth_data.json()['AT']
            else:
                raise ValueError(f'Error to get token {auth_data.status_code}')
        self._headers = {
            'Authorization': f'Bearer {self._access_token}'
        }

    def get_refresh_token(self):
        return self._refresh_token

    def get_access_token(self):
        return self._access_token

    def get_auth_data(self):
        url = 'https://a.baz-on.ru/login/user'

        payload = {
            'login': self._login,
            'password': self._password
        }

        response = requests.post(url=url, json=payload)
        return response

    def refresh_tokens(self):
        url = 'https://a.baz-on.ru/refresh/user'

        payload = {
            'RT': self._refresh_token,
        }

        response = requests.post(url, headers=self._headers, json=payload)
        return response

    def get_sale_documents(self, params: dict = {}):
        if params.get('order') is None:
            params['order'] = 'desc'

        url = 'https://kontrabaz.baz-on.ru/external-api/v1/getSaleDocuments'

        response = requests.get(url, headers=self._headers, params=params)
        return response