from celery import shared_task
from django.forms import model_to_dict

from bazon.models import BazonAccount, SaleDocument, Product
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
        response = bazon_api.get_sale_documents()
        if response.status_code != 200:
            bazon_account.refresh_auth()
            return
        data = response.json()

        for json_document in data["response"][0]["result"]["sale_documents"]:
            json_document["internal_id"] = json_document.pop("id")
            # document_detail = bazon_api.get_detail_document(
            #     int(sale_document["internal_id"])
            # )
            # print(f"{sale_document['internal_id']} - {document_detail.status_code}")
            # if document_detail.status_code == 200:
            #     print(document_detail.json())
            json_document["bazon_account"] = bazon_account
            if SaleDocument.objects.filter(
                internal_id=json_document["internal_id"]
            ).exists():
                # Проверяем существует ли сделка в бд, если да - проверяем изменена она или нет.
                sale_document = SaleDocument.objects.get(internal_id=json_document["internal_id"])
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

            sale_document = SaleDocument.objects.create(**sale_document)

            # Отправка сделки в амо CRM


@shared_task()
def get_products():
    for bazon_account in BazonAccount.objects.all():
        bazon_api = Bazon(
            login=bazon_account.login,
            password=bazon_account.password,
            refresh_token=bazon_account.refresh_token,
            access_token=bazon_account.access_token,
        )
        products_response = bazon_api.get_products()
        if products_response.status_code != 200:
            print(f"Ошибка при получении продуктов - {products_response.status_code}\n")
        for product_json in products_response.json()["response"][0]["result"]["products"]:
            product_json["internal_id"] = product_json.pop("id")
            product_json.pop("by_storages")
            if Product.objects.filter(internal_id=product_json["internal_id"]).exists():
                continue
            product = Product.objects.create(**product_json, bazon_account=bazon_account)