from celery import shared_task
from django.forms import model_to_dict

from bazon.models import BazonAccount, SaleDocument, Contractor
from utils.bazon_api import Bazon
from .events import (
    on_create_sale_document,
    on_update_sale_document,
    on_create_contractor,
    on_update_contractor,
)


@shared_task
def sale_documents_polling():

    for bazon_account in BazonAccount.objects.all():
        bazon_api = Bazon(
            login=bazon_account.login,
            password=bazon_account.password,
            refresh_token=bazon_account.refresh_token,
            access_token=bazon_account.access_token,
        )
        params = {
            "limit": 50,
        }
        response = bazon_api.get_sale_documents(params=params)
        if response.status_code != 200:
            bazon_account.refresh_auth()
            return
        for amo_account in bazon_account.amo_accounts.all():
            data = response.json()
            for json_document in data["response"][0]["result"]["sale_documents"]:
                try:
                    json_document["internal_id"] = json_document.pop("id")
                except Exception as e:
                    print(json_document)
                    continue
                json_document["bazon_account"] = bazon_account
                if SaleDocument.objects.filter(
                    internal_id=json_document["internal_id"],
                    amo_account=amo_account
                ).exists():
                    # Проверяем существует ли сделка в бд, если да - проверяем изменена она или нет.
                    sale_document = SaleDocument.objects.get(
                        internal_id=json_document["internal_id"],
                        amo_account=amo_account
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
                        on_update_sale_document(json_document, amo_account)
                    continue
                try:
                    SaleDocument.objects.create(**json_document, amo_account=amo_account)
                except:
                    pass
                on_create_sale_document(
                    json_document, amo_account
                )  # документ летит в событие

                # Отправка сделки в амо CRM


@shared_task
def contractors_polling():
    for bazon_account in BazonAccount.objects.all():
        bazon_api = Bazon(
            login=bazon_account.login,
            password=bazon_account.password,
            refresh_token=bazon_account.refresh_token,
            access_token=bazon_account.access_token,
        )
        response = bazon_api.get_contractors(limit=10)
        data = response.json()
        for contractor_json in data["response"][0]["result"]["contractors"]:
            contractor_json["internal_id"] = contractor_json.pop("id")
            contractor_json["bazon_account"] = bazon_account
            if Contractor.objects.filter(
                internal_id=contractor_json["internal_id"]
            ).exists():
                # Проверяем существует ли сделка в бд, если да - проверяем изменена она или нет.
                contractor = Contractor.objects.get(
                    internal_id=contractor_json["internal_id"],
                )
                contractor_dict = model_to_dict(contractor)
                contractor_dict.pop("id")
                contractor_dict.pop("bazon_account")
                contractor_dict.pop("amo_id")
                contractor_json.pop("bazon_account")
                if contractor_dict != contractor_json:
                    # Если сделка с апи отличается от той что в бд - актуализируем ее
                    for key, value in contractor_json.items():
                        if contractor_dict[key] != value:
                            setattr(contractor, key, value)
                    contractor.save()
                    on_update_contractor(contractor_json, bazon_account)
                continue

            contractor = Contractor.objects.create(**contractor_json)
            on_create_contractor(
                contractor_json, bazon_account
            )  # документ летит в событие
