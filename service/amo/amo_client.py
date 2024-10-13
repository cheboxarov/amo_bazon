import requests
from typing import Optional
from pydantic import BaseModel


class LinkMetadataModel(BaseModel):
    catalog_id: Optional[int] = None
    quantity: Optional[int] = None
    is_main: Optional[bool] = None
    updated_by: Optional[int] = None
    price_id: Optional[int] = None


class AmoCRMClient:

    AMO_API_URL = "https://{}.amocrm.ru/api/v4"

    def __init__(self, token, subdomain):
        self.token = token
        self.subdomain = subdomain
        self.base_url = self.AMO_API_URL.format(self.subdomain)
        self.session = requests.Session()
        self.session.headers = self._get_headers()

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    # Общие методы для всех сущностей
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
    
    def link_entity(self, to_type: str, to_id: int, e_type: str, e_id: str, metadata: Optional[dict] = None):
        """
        e_type - leads | contacts | companies | customers
        to_type - leads | contacts | companies | customers | catalog_elements
        """
        payload = [{
            "to_entity_id": to_id,
            "to_entity_type": to_type
        }]
        if metadata:
            payload["metadata"] = LinkMetadataModel.model_validate(metadata).model_dump()
        return self.session.post(f"{self.base_url}/{e_type}/{e_id}/link", json=payload)


class DealClient(AmoCRMClient):
    """
    Класс для работы со сделками в amoCRM.
    """

    def create_deal(
        self, name, status_id, responsible_user_id=None, price=None, custom_fields=None
    ):
        url = f"{self.base_url}/leads"
        data = {
            "name": name,
            "status_id": status_id,
        }
        if responsible_user_id is not None:
            data["responsible_user_id"] = responsible_user_id
        if price is not None:
            data["price"] = price
        if custom_fields is not None:
            data["custom_fields_values"] = custom_fields

        response = requests.post(url, headers=self._get_headers(), json=[data])
        if response.status_code != 200:
            print(response.json())
        response.raise_for_status()
        return response.json()

    def update_deal(
        self,
        id,
        name=None,
        status_id=None,
        responsible_user_id=None,
        price=None,
        custom_fields=None,
    ):
        url = f"{self.base_url}/leads/{id}"
        data = {}
        if name is not None:
            data["name"] = name
        if status_id is not None:
            data["status_id"] = status_id
        if responsible_user_id is not None:
            data["responsible_user_id"] = responsible_user_id
        if price is not None:
            data["price"] = price
        if custom_fields is not None:
            data["custom_fields_values"] = custom_fields

        response = requests.patch(url, headers=self._get_headers(), json=data)
        response.raise_for_status()
        return response.json()

    def delete_deal(self, deal_id):
        url = f"{self.base_url}/leads/{deal_id}"
        response = requests.delete(url, headers=self._get_headers())
        response.raise_for_status()
        if response.status_code == 204:
            return {"message": "Deal deleted successfully"}
        else:
            return response.json()


class ContactClient(AmoCRMClient):
    """
    Класс для работы с контактами в amoCRM.
    """

    def create_contact(
        self, name, responsible_user_id = None, custom_fields=None, company_id=None
    ):
        url = f"{self.base_url}/contacts"
        data = {"name": name}
        if responsible_user_id:
            data["responsible_user_id"] = responsible_user_id
        if custom_fields:
            data["custom_fields_values"] = custom_fields
        if company_id:
            data["company_id"] = company_id

        response = requests.post(url, headers=self._get_headers(), json=[data])
        response.raise_for_status()
        return response.json()

    def update_contact(
        self,
        contact_id,
        name=None,
        responsible_user_id=None,
        custom_fields=None,
        company_id=None,
    ):
        url = f"{self.base_url}/contacts/{contact_id}"
        data = {}
        if name:
            data["name"] = name
        if responsible_user_id:
            data["responsible_user_id"] = responsible_user_id
        if custom_fields:
            data["custom_fields_values"] = custom_fields
        if company_id:
            data["company_id"] = company_id

        response = requests.put(url, headers=self._get_headers(), json=data)
        response.raise_for_status()
        return response.json()

    def delete_contact(self, contact_id):
        url = f"{self.base_url}/contacts/{contact_id}"
        response = requests.delete(url, headers=self._get_headers())
        response.raise_for_status()
        if response.status_code == 204:
            return {"message": "Contact deleted successfully"}
        else:
            return response.json()


class CompanyClient(AmoCRMClient):
    """
    Класс для работы с компаниями в amoCRM.
    """

    def create_company(self, name, responsible_user_id, custom_fields=None):
        url = f"{self.base_url}/companies"
        data = {"name": name, "responsible_user_id": responsible_user_id}
        if custom_fields:
            data["custom_fields_values"] = custom_fields

        response = requests.post(url, headers=self._get_headers(), json=[data])
        response.raise_for_status()
        return response.json()

    def update_company(
        self, company_id, name=None, responsible_user_id=None, custom_fields=None
    ):
        url = f"{self.base_url}/companies/{company_id}"
        data = {}
        if name:
            data["name"] = name
        if responsible_user_id:
            data["responsible_user_id"] = responsible_user_id
        if custom_fields:
            data["custom_fields_values"] = custom_fields

        response = requests.patch(url, headers=self._get_headers(), json=data)
        response.raise_for_status()
        return response.json()

    def delete_company(self, company_id):
        url = f"{self.base_url}/companies/{company_id}"
        response = requests.delete(url, headers=self._get_headers())
        response.raise_for_status()
        if response.status_code == 204:
            return {"message": "Company deleted successfully"}
        else:
            return response.json()
