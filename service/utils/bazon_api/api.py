import hashlib
import json
import time

import requests
from typing import Collection

from kombu.pools import reset


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

    def create_sale(
        self,
        sum: int,
        type: str,
        state: str,
        contractor_id: int,
        storage_id: int,
        shipment_id: int,
        transport_id: int,
        manager_comment: str,
        paid: int,
        number: int,
        id: str,
        sum_full: int,
        manager_id: int,
        source: str,
    ):
        url = "https://kontrabaz.baz-on.ru/frontend-api/"
        data = {
            "request": {
                "saleCreate": {
                    "buffer": {
                        "sum": sum,
                        "type": type,
                        "state": state,
                        "contractorID": contractor_id,
                        "storageID": storage_id,
                        "shipmentID": shipment_id,
                        "transportID": transport_id,
                        "managerComment": manager_comment,
                        "paid": paid,
                        "number": number,
                        "id": id,
                        "sumFull": sum_full,
                        "managerID": manager_id,
                        "source": source,
                    },
                    "bufferItems": [],
                }
            }
        }

        response = requests.post(url, json=data, headers=self._headers)
        return response

    def set_lock_key(self, number: str, prev_lock_key=False, type: str = "sale"):
        url = "https://kontrabaz.baz-on.ru/frontend-api/"
        data = {
            "request": {
                "setDocumentLock": {
                    "type": type,
                    "number": number,
                    "prevLockKey": prev_lock_key,
                }
            }
        }
        response = requests.post(url, json=data, headers=self._headers)
        return response

    def sale_recreate(self, document_id: int, lock_key: str):
        url = "https://kontrabaz.baz-on.ru/frontend-api/"
        data = {
            "request": {
                "saleRecreate": {"documentID": document_id, "lockKey": lock_key}
            }
        }
        response = requests.post(url, json=data, headers=self._headers)
        return response

    def cancel_sale(self, document_id: int, lock_key: str):
        url = "https://kontrabaz.baz-on.ru/frontend-api/"
        data = {
            "request": {"saleCancel": {"documentID": document_id, "lockKey": lock_key}}
        }
        response = requests.post(url, json=data, headers=self._headers)
        return response

    def get_users(self, offset: int, limit: int):
        url = "https://kontrabaz.baz-on.ru/frontend-api/"
        data = {
            "request": {
                "getUsers": {
                    "offset": offset,
                    "limit": limit,
                    "sorter": [["id", "desc"]],
                    "calcFoundRows": True,
                    "filter": [
                        ["isSupportUser", False],
                        ["roleInCompany", ["", "super"]],
                    ],
                    "viewMode": "users-ui3",
                    "_": "",
                }
            }
        }
        response = requests.post(url, json=data, headers=self._headers)
        return response

    def get_check(self, id: int, print_type: str = "default"):
        url = "https://kontrabaz.baz-on.ru/frontend-api/"
        data = {
            "request": {
                "getDocumentFormPrint": {"id": id, "printType": print_type, "_": ""}
            }
        }
        response = requests.post(url, json=data, headers=self._headers)
        return response

    def get_document_items(self, document_number: str, document_type: str = "sale"):
        url = "https://kontrabaz.baz-on.ru/frontend-api/"
        data = {
            "request": {
                "getDocumentItems": {
                    "order": {"id": "asc"},
                    "viewMode": "sale",
                    "where": {
                        "documentNumber": document_number,
                        "documentType": document_type,
                        "state!=": ["removed", "removed_to_other_sale"],
                    },
                    "_": "",
                }
            }
        }
        response = requests.post(url, json=data, headers=self._headers)
        return response

    def edit_sale(self, id: int, data_to_edit: dict, lock_key: str):
        url = "https://kontrabaz.baz-on.ru/frontend-api/"
        data = {
            "request": {
                "saleEditData": {
                    "Document": {
                        "id": id,
                        **data_to_edit,
                    },
                    "documentID": id,
                    "lockKey": lock_key,
                }
            }
        }
        response = requests.post(url, json=data, headers=self._headers)
        return response

    def get_orders(
        self, offset: int = 0, limit: int = 500, for_sale_document: str = None
    ):
        params = {"order": "asc", "limit": limit}
        if offset > 0:
            params["offset"] = offset
        if for_sale_document is not None:
            params["for_sale_document"] = for_sale_document

        url = "https://kontrabaz.baz-on.ru/external-api/v1/getOrders"

        response = requests.get(url, params=params, headers=self._headers)
        return response

    def get_contractors(self, offset: int = 0, limit: int = 500):
        params = {"order": "asc", "limit": limit}
        if offset > 0:
            params["offset"] = offset
        url = "https://kontrabaz.baz-on.ru/external-api/v1/getContractors"
        response = requests.get(url, params=params, headers=self._headers)
        return response

    def get_items(self, offset: int = 0, limit: int = 250, category_id: int = 1, storages_ids=None, with_reverses: bool = True, search: str = None):

        if storages_ids is None:
            storages_ids = [1, 2, 3]
        data = {
            "request":
                {
                    "getProducts":
                        {
                            "offset":offset,
                            "limit":limit,
                            "sorter":
                                [
                                    ["id","desc"]
                                ],
                            "calcFoundRows":True,
                            "filter":[],
                            "categoryID":category_id,
                            "viewMode":"category-1",
                            "storagesFilter":
                                {
                                    "withReserves":with_reverses,
                                    "storagesIds":storages_ids,
                                    "byStoragesRemnants":{}
                                },
                            "a11yGridSearchOn":1,"_":""
                        }
                },
            "meta":
                {
                    "tabUID":"2024-09-02-05-15-36-410-034606",
                    "appVersion":"20240416064347",
                    "isFreezed":False,
                    "frontendApiVersion":"3.1",
                    "requestPrepareTime":
                        {
                            "sentAt":"function Date() {\\n    [native code]\\n}",
                            "startedAt":0.038,
                            "tokenRefreshedAt":None
                        }
                }
        }

        if search is not None:
            data["request"]["getProducts"]["searchByPartNumber"] = search

        response = requests.post('https://kontrabaz.baz-on.ru/frontend-api/?getProducts', json=data, headers=self._headers)
        return response

    def add_item_to_document(self, lockKey: str, document_id: int, items: list[dict]):

        """
        {
                                        "id":-1,
                                        "objectID":"3479",
                                        "objectType":"Product",
                                        "name":"Топливная рейка с форсунками Subaru Exiga YA5 EJ204 2005 (б/у)",
                                        "amount":1,
                                        "price":3000,
                                        "cost":3000,
                                        "storageID":"1",
                                        "state_":"Красноярск",
                                        "objectUsed":"Контракт",
                                        "order":0,
                                        "taxes":
                                            {
                                                "paymentSubjectType":"",
                                                "taxSystemCode":"",
                                                "taxVatCode":""
                                            },
                                        "availableAmount":"1"
                                    } items
        """

        data = {
            "request":
                {
                    "saleAddItems":
                        {
                            "bufferItems":
                                items,
                            "documentID":document_id,
                            "lockKey":lockKey,
                            "_":""
                        }
                },
            "meta":
                {
                    "tabUID":"2024-09-02-05-15-36-410-034606",
                    "appVersion":"20240416064347",
                    "isFreezed":False,
                    "frontendApiVersion":"3.1",
                    "requestPrepareTime":
                        {
                            "sentAt":"function Date() {\\n    [native code]\\n}",
                            "startedAt":0.003,
                            "tokenRefreshedAt":None
                        }
                }
        }

        response = requests.post('https://kontrabaz.baz-on.ru/frontend-api/?saleAddItems',
                                 headers=self._headers, json=data)
        return response

    def drop_lock_key(self, document_id: id, lock_key: str):
        data = {
            "request": {
                "dropDocumentLock": {
                    "documentID": document_id,
                    "lockKey": lock_key,
                    "_": ""
                }
            }
        }

        response = requests.post("https://kontrabaz.baz-on.ru/frontend-api/?dropDocumentLock", headers=self._headers, json=data)
        return response

    def get_document_items_by_buffer(self, items: list[dict]):
        """ items
        [
            {
                "objectID":3479,
                "amount":1,
                "storageID":"1",
                "objectType":"Product",
                "cost":3000,
                "price":3000,
                "order":0,
                "id":"-1"
            }
        ],"""
        data = {
            "request":
                {
                    "getDocumentItemsByBuffer":
                        {
                            "bufferItems":
                                items,
                            "viewMode":"sale",
                            "_":""
                        }
                },
            "meta":
                {
                    "tabUID":"2024-09-03-03-39-50-654-045684",
                    "appVersion":"20240416064347",
                    "isFreezed":False,
                    "frontendApiVersion":"3.1",
                    "requestPrepareTime":
                        {
                            "sentAt":"function Date() {\\n    [native code]\\n}",
                            "startedAt":0.003,
                            "tokenRefreshedAt":None
                        }
                }
        }

        response = requests.post(
            'https://kontrabaz.baz-on.ru/frontend-api/?getDocumentItemsByBuffer',
            headers=self._headers,
            json=data,
        )
        return response

    def remove_document_items(self, document_id: int, lock_key: str, items: list[int]):

        data = {
            "request":
                {
                    "saleRemoveItems":
                        {
                            "itemsIDs":items,
                            "documentID":document_id,
                            "lockKey":lock_key,
                            "_":""
                        }
                },
            "meta":
                {
                    "tabUID":"2024-09-03-04-37-29-349-255981",
                    "appVersion":"20240416064347",
                    "isFreezed":False,
                    "frontendApiVersion":"3.1",
                    "requestPrepareTime":
                        {
                            "sentAt":"function Date() {\\n    [native code]\\n}",
                            "startedAt":0.001,
                            "tokenRefreshedAt":None
                        }
                }
        }

        response = requests.post('https://kontrabaz.baz-on.ru/frontend-api/?saleRemoveItems',
                                 headers=self._headers, json=data)
        return response

    def sale_reserve(self, document_id: int, lock_key: str):
        data = {
            "request": {
                "saleReserve": {
                    "documentID": document_id,
                    "lockKey": lock_key,
                }
            }
        }
        return requests.post("https://kontrabaz.baz-on.ru/frontend-api/?saleReserve", headers=self._headers, json=data)

    def generate_lock_key(self, document_number: str):
        response = self.set_lock_key(document_number)
        response.raise_for_status()
        lock_key = response.json().get("response", {}).get("setDocumentLock", {}).get("lockKey")
        return lock_key
