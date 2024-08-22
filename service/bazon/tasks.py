from celery import shared_task
from django.forms import model_to_dict

from bazon.models import BazonAccount, SaleDocument
from bazon_api.api import Bazon


@shared_task
def update_sale_documents():

    for bazon_account in BazonAccount.objects.all():
        bazon_api = Bazon(
            login=bazon_account.login,
            password=bazon_account.password,
            refresh_token=bazon_account.refresh_token,
            access_token=bazon_account.access_token,
        )
        params = {
            "limit": 500,
        }
        response = bazon_api.get_sale_documents(params=params)
        if response.status_code != 200:
            bazon_account.refresh_auth()
            return
        data = response.json()

        for json_document in data["response"][0]["result"]["sale_documents"]:
            json_document["internal_id"] = json_document.pop("id")
            json_document["bazon_account"] = bazon_account
            if SaleDocument.objects.filter(
                internal_id=json_document["internal_id"]
            ).exists():
                # Проверяем существует ли сделка в бд, если да - проверяем изменена она или нет.
                sale_document = SaleDocument.objects.get(
                    internal_id=json_document["internal_id"]
                )
                document_dict = model_to_dict(sale_document)
                document_dict.pop("id")
                document_dict.pop("bazon_account")
                document_dict.pop("amo_lead_id")
                json_document.pop("bazon_account")
                if document_dict != json_document:
                    # Если сделка с апи отличается от той что в бд - актуализируем ее
                    for key, value in json_document.items():
                        if document_dict[key] != value:
                            setattr(sale_document, key, value)
                    sale_document.save()
                continue

            sale_document = SaleDocument.objects.create(**json_document)

            # Отправка сделки в амо CRM
