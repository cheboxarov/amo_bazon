from utils.serializers import BazonSaleToAmoLeadSerializer
from bazon.models import BazonAccount
from amo.models import AmoAccount
from amo.amo_client import AmoCRMClient


def on_create_sale_document(sale_data: dict, bazon_account: BazonAccount):
    try:
        serializer = BazonSaleToAmoLeadSerializer(sale_data)
        serializer.serialize()
        serialized_data = serializer.get_serialized_data(with_id=False)
        print(serialized_data)
        amo_account = AmoAccount.objects.filter(bazon_accounts=bazon_account).first()
        print("Создаю клиент амо срм")
        amo_client = AmoCRMClient(amo_account.token, amo_account.suburl)
        print("клиент создан, кидаю запрос")
        response = amo_client.create_deal(serialized_data)
        print(f"Created sale document:\n{serialized_data}\n{sale_data}\n")
    except BaseException as error:
        print(error)


def on_update_sale_document(sale_data: dict, bazon_account: BazonAccount):
    serializer = BazonSaleToAmoLeadSerializer(sale_data)
    serializer.serialize()
    serialized_data = serializer.get_serialized_data(with_id=True)
    print(f"Updated sale document:\n{serialized_data}\n{sale_data}")
