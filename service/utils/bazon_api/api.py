import json
import uuid
from typing import Optional
import requests
from typing import Collection
from loguru import logger
from urllib3 import request
from rest_framework.exceptions import APIException


def bazon_response_check(func):
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        if response.status_code == 500:
            logger.error(f"Bazon response has 500 status code ({func.__name__}) \nargs({args}) \nkwargs({kwargs}) \ncontent - {response.content}")
            raise APIException(detail="bazon response error", code=500)
        try:
            data: dict = response.json()
        except requests.exceptions.JSONDecodeError as error:
            logger.error(f"Error to parse response body ({func.__name__}) args({args}) kwargs({kwargs})\n{error}")
            return response
        response_data: dict = data.get("response", {})
        try:
            for key, response_item in response_data.items():
                if error := response_item.get("error"):
                    logger.error( 
                        f"Ошибочный ответ от базона по методу {func.__name__} args({args}) kwargs({kwargs}):\n{error}"
                    )
                    if error == "invalid_lock":
                        raise APIException(detail="invalid_key_lock", code=403)
        except APIException:
            raise
        except Exception as err:
            pass
        return response

    return wrapper


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

    @bazon_response_check
    def get_auth_data(self) -> requests.Response:
        url = "https://a.baz-on.ru/login/user"

        payload = {"login": self._login, "password": self._password}

        response = requests.post(url=url, json=payload)
        return response

    @bazon_response_check
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

    @bazon_response_check
    def get_sale_documents(self, params: dict = {}) -> requests.Response:
        if params.get("order") is None:
            params["order"] = "desc"

        url = "https://kontrabaz.baz-on.ru/external-api/v1/getSaleDocuments"

        response = requests.get(url, headers=self._headers, params=params)
        return response

    @bazon_response_check
    def get_products(self, params: dict = {}) -> requests.Response:
        if params.get("order") is None:
            params["order"] = "desc"
        url = "https://kontrabaz.baz-on.ru/external-api/v1/getProducts"

        response = requests.get(url, headers=self._headers, params=params)
        return response

    @bazon_response_check
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

    @bazon_response_check
    def create_sale(
        self,
        source: str,
        manager_id: int,
        storage_id: int,
        sum: int = 0,
        type: str = "sale",
        state: str = "draft",
        contractor_id: int = 0,
        shipment_id: int = 0,
        transport_id: int = 0,
        manager_comment: str = "",
        paid: int = 0,
        number: int = 0,
        sum_full: int = 0,
    ):
        id = str(uuid.uuid4())[:23]
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

    @bazon_response_check
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

    @bazon_response_check
    def sale_recreate(self, document_id: int, lock_key: str):
        url = "https://kontrabaz.baz-on.ru/frontend-api/"
        data = {
            "request": {
                "saleRecreate": {"documentID": document_id, "lockKey": lock_key}
            }
        }
        response = requests.post(url, json=data, headers=self._headers)
        return response

    @bazon_response_check
    def cancel_sale(self, document_id: int, lock_key: str):
        url = "https://kontrabaz.baz-on.ru/frontend-api/"
        data = {
            "request": {"saleCancel": {"documentID": document_id, "lockKey": lock_key}}
        }
        response = requests.post(url, json=data, headers=self._headers)
        return response

    @bazon_response_check
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

    @bazon_response_check
    def get_check(self, id: int, print_type: str = "default"):
        url = "https://kontrabaz.baz-on.ru/frontend-api/"
        data = {
            "request": {
                "getDocumentFormPrint": {"id": id, "printType": print_type, "_": ""}
            }
        }
        response = requests.post(url, json=data, headers=self._headers)
        return response

    @bazon_response_check
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

    @bazon_response_check
    def edit_sale(self, id: int, data_to_edit: dict, lock_key: str):
        url = "https://kontrabaz.baz-on.ru/frontend-api/"
        data = {
            "request": {
                "saleEditData": {
                    "Document": {
                        **data_to_edit,
                    },
                    "documentID": id,
                    "lockKey": lock_key,
                }
            }
        }
        response = requests.post(url, json=data, headers=self._headers)
        return response

    @bazon_response_check
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

    @bazon_response_check
    def get_contractors(self, offset: int = 0, limit: int = 500):
        params = {"order": "desc", "limit": limit}
        if offset > 0:
            params["offset"] = offset
        url = "https://kontrabaz.baz-on.ru/external-api/v1/getContractors"
        response = requests.get(url, params=params, headers=self._headers)
        return response

    @bazon_response_check
    def get_contractor(self, contractor_id: int):

        payload = {"request": {"getContractor": {"id": contractor_id}}}

        url = "https://kontrabaz.baz-on.ru/frontend-api/?getContractor"

        return requests.post(url, json=payload, headers=self._headers)

    @bazon_response_check
    def get_items(
        self,
        offset: int = 0,
        limit: int = 250,
        category_id: int = 1,
        storages_ids=None,
        with_reverses: bool = True,
        search: str = None,
    ):

        if storages_ids is None:
            storages_ids = [1, 2, 3]
        data = {
            "request": {
                "getProducts": {
                    "offset": offset,
                    "limit": limit,
                    "sorter": [["id", "desc"]],
                    "calcFoundRows": True,
                    "filter": [],
                    "categoryID": category_id,
                    "viewMode": "category-1",
                    "storagesFilter": {
                        "withReserves": with_reverses,
                        "storagesIds": storages_ids,
                        "byStoragesRemnants": {},
                    },
                    "a11yGridSearchOn": 1,
                    "_": "",
                }
            },
            "meta": {
                "tabUID": "2024-09-02-05-15-36-410-034606",
                "appVersion": "20240416064347",
                "isFreezed": False,
                "frontendApiVersion": "3.1",
                "requestPrepareTime": {
                    "sentAt": "function Date() {\\n    [native code]\\n}",
                    "startedAt": 0.038,
                    "tokenRefreshedAt": None,
                },
            },
        }

        if search is not None:
            data["request"]["getProducts"]["searchByPartNumber"] = search

        response = requests.post(
            "https://kontrabaz.baz-on.ru/frontend-api/?getProducts",
            json=data,
            headers=self._headers,
        )
        return response

    @bazon_response_check
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
            "request": {
                "saleAddItems": {
                    "bufferItems": items,
                    "documentID": document_id,
                    "lockKey": lockKey,
                    "_": "",
                }
            },
            "meta": {
                "tabUID": "2024-09-02-05-15-36-410-034606",
                "appVersion": "20240416064347",
                "isFreezed": False,
                "frontendApiVersion": "3.1",
                "requestPrepareTime": {
                    "sentAt": "function Date() {\\n    [native code]\\n}",
                    "startedAt": 0.003,
                    "tokenRefreshedAt": None,
                },
            },
        }

        response = requests.post(
            "https://kontrabaz.baz-on.ru/frontend-api/?saleAddItems",
            headers=self._headers,
            json=data,
        )
        return response

    @bazon_response_check
    def drop_lock_key(self, document_id: id, lock_key: str):
        data = {
            "request": {
                "dropDocumentLock": {
                    "documentID": document_id,
                    "lockKey": lock_key,
                    "_": "",
                }
            }
        }

        response = requests.post(
            "https://kontrabaz.baz-on.ru/frontend-api/?dropDocumentLock",
            headers=self._headers,
            json=data,
        )
        return response

    @bazon_response_check
    def get_document_items_by_buffer(self, items: list[dict]):
        """items
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
            "request": {
                "getDocumentItemsByBuffer": {
                    "bufferItems": items,
                    "viewMode": "sale",
                    "_": "",
                }
            },
            "meta": {
                "tabUID": "2024-09-03-03-39-50-654-045684",
                "appVersion": "20240416064347",
                "isFreezed": False,
                "frontendApiVersion": "3.1",
                "requestPrepareTime": {
                    "sentAt": "function Date() {\\n    [native code]\\n}",
                    "startedAt": 0.003,
                    "tokenRefreshedAt": None,
                },
            },
        }

        response = requests.post(
            "https://kontrabaz.baz-on.ru/frontend-api/?getDocumentItemsByBuffer",
            headers=self._headers,
            json=data,
        )
        return response

    @bazon_response_check
    def remove_document_items(self, document_id: int, lock_key: str, items: list[int]):

        data = {
            "request": {
                "saleRemoveItems": {
                    "itemsIDs": items,
                    "documentID": document_id,
                    "lockKey": lock_key,
                    "_": "",
                }
            },
            "meta": {
                "tabUID": "2024-09-03-04-37-29-349-255981",
                "appVersion": "20240416064347",
                "isFreezed": False,
                "frontendApiVersion": "3.1",
                "requestPrepareTime": {
                    "sentAt": "function Date() {\\n    [native code]\\n}",
                    "startedAt": 0.001,
                    "tokenRefreshedAt": None,
                },
            },
        }

        response = requests.post(
            "https://kontrabaz.baz-on.ru/frontend-api/?saleRemoveItems",
            headers=self._headers,
            json=data,
        )
        return response

    @bazon_response_check
    def _sale_move(
        self, document_id: int, lock_key: str, method: str
    ) -> requests.Response:
        data = {
            "request": {
                method: {
                    "documentID": document_id,
                    "lockKey": lock_key,
                }
            }
        }
        return requests.post(
            f"https://kontrabaz.baz-on.ru/frontend-api/?{method}",
            headers=self._headers,
            json=data,
        )

    def sale_reserve(self, document_id: int, lock_key: str):
        return self._sale_move(document_id, lock_key, "saleReserve")

    def sale_cancel(self, document_id: int, lock_key: str):
        return self._sale_move(document_id, lock_key, "saleCancel")

    def sale_issue(self, document_id: int, lock_key: str):
        return self._sale_move(document_id, lock_key, "saleIssue")

    def generate_lock_key(self, document_number: str):
        response = self.set_lock_key(document_number)
        response.raise_for_status()
        lock_key = (
            response.json()
            .get("response", {})
            .get("setDocumentLock", {})
            .get("lockKey")
        )
        return lock_key

    @bazon_response_check
    def add_sale_pay(
        self,
        document_id: int,
        lock_key: str,
        pay_source: int,
        pay_sum: float,
        comment: str = "",
    ):
        payload = {
            "request": {
                "salePay": {
                    "sumByPaySources": {str(pay_source): str(pay_sum)},
                    "sum": str(pay_sum),
                    "comment": comment,
                    "documentID": document_id,
                    "lockKey": lock_key,
                }
            }
        }

        return requests.post(
            "https://kontrabaz.baz-on.ru/frontend-api/?salePay",
            headers=self._headers,
            json=payload,
        )

    @bazon_response_check
    def get_pay_sources(self):

        payload = {
            "request": {
                "getPaySources": {
                    "viewMode": "raw",
                    "where": {"type": ["cash", "bank"]},
                    "sorter": {"sorter": "asc"},
                }
            }
        }

        return requests.post(
            "https://kontrabaz.baz-on.ru/frontend-api/?getPaySources",
            headers=self._headers,
            json=payload,
        )

    @bazon_response_check
    def get_paid_sources(self, document_id: int):

        payload = {"request": {"getDocumentPaidSources": {"documentID": document_id}}}

        return requests.post(
            "https://kontrabaz.baz-on.ru/frontend-api/?getDocumentPaidSources",
            headers=self._headers,
            json=payload,
        )

    @bazon_response_check
    def sale_pay_back(self, document_id: int, lock_key: str, pay_source: int, sum: int):

        payload = {
            "request": {
                "saleRefund": {
                    "sumByPaySources": {
                        str(pay_source): sum,
                    },
                    "sum": sum,
                    "comment": "",
                    "documentID": document_id,
                    "lockKey": lock_key,
                }
            }
        }

        return requests.post(
            "https://kontrabaz.baz-on.ru/frontend-api/?saleRefund",
            headers=self._headers,
            json=payload,
        )

    @bazon_response_check
    def get_sources(self):
        payload = {"request": {"getSaleSourcesReference": {"where": {"isArchive": 0}}}}

        return requests.post(
            "https://kontrabaz.baz-on.ru/frontend-api/?getSaleSourcesReference",
            json=payload,
            headers=self._headers,
        )

    @bazon_response_check
    def get_storages(self):

        payload = {"request": {"getStoragesReference:full": {"_": ""}}}

        return requests.post(
            "https://kontrabaz.baz-on.ru/frontend-api/?getStoragesReference",
            json=payload,
            headers=self._headers,
        )

    @bazon_response_check
    def get_managers(self):

        payload = {"request": {"getUsersReference": {"_": ""}}}

        return requests.post(
            "https://kontrabaz.baz-on.ru/frontend-api/?getUsersReference",
            json=payload,
            headers=self._headers,
        )

    @bazon_response_check
    def get_form_print(self, document_id: int, print_type: str = "default"):

        payload = {
            "request": {
                "getDocumentFormPrint": {"id": document_id, "printType": print_type}
            }
        }

        return requests.post(
            "https://kontrabaz.baz-on.ru/frontend-api/?getDocumentFormPrint",
            headers=self._headers,
            json=payload,
        )

    @bazon_response_check
    def set_contractor(
        self,
        name: str,
        phone: str,
        id: Optional[int] = None,
        email: str = "",
        BIK: str = "",
        INN: str = "",
        KPP: str = "",
        bank_name: str = "",
        legal_name: str = "",
        legal_address: str = "",
        real_adress: str = "",
    ):
        payload = {
            "request": {
                "setContractor": {
                    "email": email,
                    "legalType": "organisation",
                    "name": name,
                    "phone": phone,
                    "printComment": "",
                    "legalData": {
                        "BIK": BIK,
                        "INN": INN,
                        "KPP": KPP,
                        "bankName": bank_name,
                        "name": legal_name,
                        "legalAddress": legal_address,
                        "realAddress": real_adress,
                    },
                }
            }
        }

        if id:
            payload["request"]["setContractor"]["id"] = id

        return requests.post(
            "https://kontrabaz.baz-on.ru/frontend-api/?setContractor",
            headers=self._headers,
            json=payload,
        )

    @bazon_response_check
    def edit_item_cost(self, items: dict[str, int], document_id: int, lock_key: str):
        data = {
            "request": {
                "saleEditItemCost": {
                    "items": items,
                    "documentID": document_id,
                    "lockKey": lock_key,
                }
            }
        }
        return requests.post(
            "https://kontrabaz.baz-on.ru/frontend-api/?saleEditItemCost",
            headers=self._headers,
            json=data,
        )
    
    @bazon_response_check
    def get_cash_machines(self):
        data = {
            "request": {
                "getCashMachines": {
                    "viewMode": "raw"
                }
            }
        }
        url = "https://kontrabaz.baz-on.ru/frontend-api/?getCashMachines"
        return requests.post(url, headers=self._headers, json=data)
    
    @bazon_response_check
    def generate_receipt_request(self, document_id: int, factory_number: str):
        logger.debug(f"generate_receipt_request({document_id}, {factory_number})")
        data = {
            "request": {
                "generateReceiptRequest": {
                    "documentID": document_id,
                    "factoryNumber": factory_number,
                    "_": ""
                },
                "getOperations": {
                    "viewMode": "raw",
                    "where": {
                        "documentID": document_id
                    },
                    "_": ""
                }
            }
        }
        return requests.post("https://kontrabaz.baz-on.ru/frontend-api/?generateReceiptRequest,getOperations", headers=self._headers, json=data)
    
    @bazon_response_check
    def get_receipt_state(self, document_id: int, receipt_id: int):
        data = {
            "request": {
                "getReceiptState": {
                    "documentID": document_id,
                    "receiptID": receipt_id
                }
            }
        }
        return requests.post("https://kontrabaz.baz-on.ru/frontend-api/?getReceiptState", headers=self._headers, json=data)

    @bazon_response_check
    def sale_receipt_process(self, 
                             document_id: int, 
                             factory_number: str, 
                             cash_machine: int, 
                             contact: str,
                             cash: int,
                             electron: int,
                             lock_key: str):
        data = {
            "request": {
                "saleReceiptProcess": {
                    "documentID": document_id,
                    "factoryNumber": factory_number,
                    "cashMachine": str(cash_machine),
                    "operationType": "SALE_PAY",
                    "customerContact": contact,
                    "ignoreState": False,
                    "sumParts": {
                        "CASH": cash,
                        "ELECTRON": electron
                    },
                    "sum": str(float(cash+electron)),
                    "lockKey": lock_key
                }
            }
        }
        return requests.post("https://kontrabaz.baz-on.ru/frontend-api/?saleReceiptProcess", headers=self._headers, json=data)