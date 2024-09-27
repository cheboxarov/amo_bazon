from utils.serializers import BazonSaleToAmoLeadSerializer
from bazon.models import BazonAccount
from amo.models import AmoAccount
from amo.amo_client import DealClient
from bazon.models import SaleDocument, Contractor
from .contractors import on_create_contractor
from django.db import transaction
from loguru import logger


def create_deal(sale_data: dict, amo_account: AmoAccount):
    with transaction.atomic():
        sale_document = SaleDocument.objects.create(amo_account=amo_account, **sale_data)
        serializer = BazonSaleToAmoLeadSerializer(amo_account, sale_data)
        serializer.serialize()
        serialized_data = serializer.get_serialized_data(with_id=False)
        amo_client = DealClient(amo_account.token, amo_account.suburl)
        response = amo_client.create_deal(**serialized_data)
        amo_lead_id = response["_embedded"]["leads"][0]["id"]
        sale_document.amo_lead_id = amo_lead_id
        sale_document.amo_account = amo_account
        sale_document.save()


def on_create_sale_document(
    sale_data: dict,
    amo_account: AmoAccount
):
    create_deal(sale_data=sale_data, amo_account=amo_account)
    query = SaleDocument.objects.filter(internal_id=sale_data.get("internal_id"), amo_account=amo_account)
    if not query.exists():
        logger.error(f"Транзакция создания сделки закончилась с ошибкой.\nsale_data={sale_data}\namo_account={amo_account}")
        return
    
    sale_document = query.first()

    if sale_document.contractor_id:
        api = sale_document.get_api()
        contractor_response = api.get_contractor(sale_document.contractor_id)
        contractor_json = (contractor_response.json()
                        .get("response", {})
                        .get("getContractor", {})
                        .get("Contractor"))
        if contractor_json is None:
            return
        query = Contractor.objects.filter(internal_id=sale_document.contractor_id, amo_account=amo_account)
        if not query.exists():
            on_create_contractor(contractor_json,
                                bazon_account=sale_document.bazon_account,
                                amo_account=sale_document.amo_account)
        contractor = query.first()

def on_update_sale_document(sale_data: dict, amo_account: AmoAccount):
    print(f"Deal updated: {sale_data}")
    serializer = BazonSaleToAmoLeadSerializer(amo_account, sale_data)
    serializer.serialize()
    serialized_data = serializer.get_serialized_data(with_id=True)
    amo_client = DealClient(amo_account.token, amo_account.suburl)
    if serialized_data.get("id") is None:
        return
    response = amo_client.update_deal(**serialized_data)
