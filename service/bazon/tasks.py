from celery import shared_task
from bazon.models import BazonAccount, SaleDocument
from bazon_api.api import Bazon



@shared_task
def update_sale_documents():

    for bazon_account in BazonAccount.objects.all():
        bazon_api = Bazon(login=bazon_account.login,
                          password=bazon_account.password,
                          refresh_token=bazon_account.refresh_token,
                          access_token=bazon_account.access_token)
        data = bazon_api.get_sale_documents().json()
        for sale_document in data['response'][0]['result']['sale_documents']:
            sale_document['internal_id'] = sale_document.pop('id')
            sale_document['bazon_account'] = bazon_account
            if SaleDocument.objects.filter(internal_id=sale_document['internal_id']).exists():
                return
            SaleDocument.objects.create(**sale_document)
            # Отправка сделки в амо CRM

