from celery import shared_task
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
        response = bazon_api.get_sale_documents()
        if response.status_code != 200:
            bazon_account.refresh_token()
            return
        data = response.json()

        for sale_document in data["response"][0]["result"]["sale_documents"]:
            sale_document["internal_id"] = sale_document.pop("id")
            document_detail = bazon_api.get_detail_document(
                int(sale_document["internal_id"])
            )
            print(f"{sale_document['internal_id']} - {document_detail.status_code}")
            if document_detail.status_code == 200:
                print(document_detail.json())
            sale_document["bazon_account"] = bazon_account
            if SaleDocument.objects.filter(
                internal_id=sale_document["internal_id"]
            ).exists():
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
