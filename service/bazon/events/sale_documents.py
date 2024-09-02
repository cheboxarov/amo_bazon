from utils.serializers import BazonSaleToAmoLeadSerializer
from bazon.models import BazonAccount
from amo.models import AmoAccount
from amo.amo_client import DealClient
from bazon.models import SaleDocument


def on_create_sale_document(sale_data: dict, bazon_account: BazonAccount):
    serializer = BazonSaleToAmoLeadSerializer(sale_data)
    serializer.serialize()
    serialized_data = serializer.get_serialized_data(with_id=False)
    query = AmoAccount.objects.filter(bazon_accounts=bazon_account)
    if not query.exists():
        return
    amo_account = query.first()
    amo_client = DealClient(amo_account.token, amo_account.suburl)
    response = amo_client.create_deal(**serialized_data)
    lead_id = response["_embedded"]["leads"][0]["id"]
    sale_document = SaleDocument.objects.get(internal_id=sale_data["internal_id"])
    sale_document.amo_lead_id = lead_id
    sale_document.save()


def on_update_sale_document(sale_data: dict, bazon_account: BazonAccount):
    serializer = BazonSaleToAmoLeadSerializer(sale_data)
    serializer.serialize()
    serialized_data = serializer.get_serialized_data(with_id=True)
    query = AmoAccount.objects.filter(bazon_accounts=bazon_account)
    if not query.exists():
        return
    amo_account = query.first()
    amo_client = DealClient(amo_account.token, amo_account.suburl)
    if serialized_data.get("id") is None:
        return
    response = amo_client.update_deal(**serialized_data)
