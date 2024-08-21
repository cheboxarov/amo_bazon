import json

import requests
from typing import Collection


class Bazon:

    def __init__(
        self,
        login: str,
        password: str,
        refresh_token: Collection[str] = None,
        access_token: Collection[str] = None,
    ):
        self._login = login
        self._password = password
        if refresh_token:
            self._refresh_token = refresh_token
            self._access_token = access_token
        else:
            auth_data = self.get_auth_data()
            if auth_data.status_code == 200:
                self._refresh_token = auth_data.json()["RT"]
                self._access_token = auth_data.json()["AT"]
            else:
                raise ValueError(f"Error to get token {auth_data.status_code}")
        self._headers = {"Authorization": f"Bearer {self._access_token}"}

    def get_refresh_token(self):
        return self._refresh_token

    def get_access_token(self):
        return self._access_token

    def get_auth_data(self) -> requests.Response:
        url = "https://a.baz-on.ru/login/user"

        payload = {"login": self._login, "password": self._password}

        response = requests.post(url=url, json=payload)
        return response

    def refresh_tokens(self):
        url = "https://a.baz-on.ru/refresh/user"

        payload = {
            "RT": self._refresh_token,
        }

        response = requests.post(url, headers=self._headers, json=payload)
        return response

    def refresh_me(self):
        refresh_data = self.refresh_tokens()
        print(f"REFRESH: {refresh_data}\nREFRESH_DATA:{refresh_data.json()}")
        self._refresh_token = refresh_data.json()["RT"]
        self._access_token = refresh_data.json()["AT"]

    def get_sale_documents(self, params: dict = {}) -> requests.Response:
        if params.get("order") is None:
            params["order"] = "desc"

        url = "https://kontrabaz.baz-on.ru/external-api/v1/getSaleDocuments"

        response = requests.get(url, headers=self._headers, params=params)
        return response

    def get_products(self, params: dict = {}) -> requests.Response:
        if params.get("order") is None:
            params["order"] = "desc"
        url = "https://kontrabaz.baz-on.ru/external-api/v1/getProducts"

        response = requests.get(url, headers=self._headers, params=params)
        return response

    def get_detail_document(
        self, document_id: int, params: dict = None
    ) -> requests.Response:
        data = {
            "request": {
                "getDocument": {"number": str(document_id), "type": "sale", "_": ""},
                "getDocumentItems": {
                    "order": {"id": "asc"},
                    "viewMode": "sale",
                    "where": {
                        "documentNumber": str(document_id),
                        "documentType": "sale",
                        "state!=": ["removed", "removed_to_other_sale"],
                    },
                    "_": "",
                },
            },
            "meta": {
                "tabUID": "2024-08-14-04-10-17-021-102215",
                "appVersion": "20240416064347",
                "isFreezed": False,
                "frontendApiVersion": "3.1",
                "requestPrepareTime": {
                    "sentAt": "function Date() { [native code] }",
                    "startedAt": 0.033,
                    "tokenRefreshedAt": None,
                },
            },
        }
        headers = self._headers
        headers["content-type"] = "text/plain"
        response = requests.post(
            "https://kontrabaz.baz-on.ru/frontend-api/?getSaleSourcesReference,getCompanyConfig,7",
            headers=headers,
            data=json.dumps(data),
            params=params,
        )
        return response
