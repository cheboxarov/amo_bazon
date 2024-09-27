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
from utils.transaction import transaction_decorator


@shared_task
@transaction_decorator
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
            data: dict[str, list[dict[str, dict[str, list]]]] = response.json()
            for json_document in data["response"][0]["result"]["sale_documents"]:
                try:
                    json_document["internal_id"] = json_document.pop("id")
                except Exception as e:
                    print(json_document)
                    continue
                json_document["bazon_account"] = bazon_account
                if SaleDocument.objects.filter(
                    internal_id=json_document["internal_id"], amo_account=amo_account
                ).exists():
                    sale_document = SaleDocument.objects.get(
                        internal_id=json_document["internal_id"],
                        amo_account=amo_account,
                    )
                    document_dict = model_to_dict(sale_document)
                    document_dict.pop("id")
                    document_dict.pop("bazon_account")
                    document_dict.pop("amo_lead_id")
                    document_dict.pop("amo_account")
                    document_dict.pop("contractor_linked")
                    json_document.pop("bazon_account")
                    if document_dict != json_document:
                        for key, value in json_document.items():
                            if document_dict[key] != value:
                                setattr(sale_document, key, value)
                        sale_document.save()
                        on_update_sale_document(json_document, amo_account)
                    continue
                on_create_sale_document(json_document, amo_account)


@shared_task
def contractors_polling():
    return
    for bazon_account in BazonAccount.objects.all():
        bazon_api = Bazon(
            login=bazon_account.login,
            password=bazon_account.password,
            refresh_token=bazon_account.refresh_token,
            access_token=bazon_account.access_token,
        )
        response = bazon_api.get_contractors(limit=10)
        for amo_account in bazon_account.amo_accounts.all():
            data = response.json()
            for contractor_json in data["response"][0]["result"]["contractors"]:
                contractor_json["internal_id"] = contractor_json.pop("id")
                contractor_json["bazon_account"] = bazon_account
                contractor_query = Contractor.objects.filter(
                    internal_id=contractor_json["internal_id"], amo_account=amo_account
                )
                if contractor_query.exists():
                    # Проверяем существует ли сделка в бд, если да - проверяем изменена она или нет.
                    contractor = contractor_query.first()
                    contractor_dict = model_to_dict(contractor)
                    contractor_dict.pop("id")
                    contractor_dict.pop("bazon_account")
                    contractor_dict.pop("amo_id")
                    contractor_dict.pop("amo_account")
                    contractor_json.pop("bazon_account")
                    if contractor_dict != contractor_json:
                        # Если сделка с апи отличается от той что в бд - актуализируем ее
                        for key, value in contractor_json.items():
                            if contractor_dict[key] != value:
                                setattr(contractor, key, value)
                        contractor.save()
                        on_update_contractor(contractor_json, amo_account)
                    continue

                contractor = Contractor.objects.create(
                    **contractor_json, amo_account=amo_account
                )
                on_create_contractor(
                    contractor_json, amo_account
                )  # документ летит в событие
