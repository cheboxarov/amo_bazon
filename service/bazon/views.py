import time
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.response import Response
from rest_framework.status import *
from rest_framework.views import APIView
from .models import SaleDocument, BazonAccount
from .serializers import BazonSaleDocumentSerializer
from amo.models import AmoAccount
from utils.serializers.bazon_serializers import ItemsListSerializer
import hashlib


class BazonSaleView(APIView):

    def get(self, request, amo_id):
        queryset = SaleDocument.objects.filter(amo_lead_id=amo_id)
        if not queryset.exists():
            return Response({"Error": "Not found"}, status=HTTP_404_NOT_FOUND)
        sale_document = queryset.first()
        serializer = BazonSaleDocumentSerializer(sale_document)
        return Response(serializer.data, status=HTTP_200_OK)


class BazonSaleProductsView(APIView):
    def get(self, request, amo_id):
        queryset = SaleDocument.objects.filter(amo_lead_id=amo_id)
        if not queryset.exists():
            return Response({"Error": "Not found"}, status=HTTP_404_NOT_FOUND)
        sale_document: SaleDocument = queryset.first()
        bazon_account: BazonAccount = sale_document.bazon_account
        bazon_api = bazon_account.get_api()
        response = bazon_api.get_detail_document(int(sale_document.number))
        if response.status_code == 200:
            data = response.json()
            validated_data = {
                "document": data["response"]["getDocument"],
                "items": data.get("response", {})
                .get("getDocumentItems", {})
                .get("DocumentItemsList", {})
                .get("entitys", []),
            }
            return Response(validated_data, status=HTTP_200_OK)
        return Response({"Error": "Cant connect to bazon"}, status=HTTP_200_OK)


class BazonSalesListView(APIView):

    def get(self, request):
        queryset = SaleDocument.objects
        serializer = BazonSaleDocumentSerializer(queryset.all(), many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    def post(self, request):
        data = request.data
        lead_ids = data.get("lead_ids", [])
        if len(lead_ids) == 0:
            return Response({"Error": "Need lead_ids"}, status=HTTP_400_BAD_REQUEST)
        documents = SaleDocument.objects.filter(amo_lead_id__in=lead_ids).prefetch_related("bazon_account", "amo_account").all()
        serializer = BazonSaleDocumentSerializer(documents, many=True)
        return Response(serializer.data, status=HTTP_200_OK)


class BazonItemsListView(APIView):
    def get(self, request, amo_url):
        try:
            amo_account = AmoAccount.objects.get(suburl=amo_url)
        except ObjectDoesNotExist:
            return Response({"Error": "AmoAccount not found"}, status=HTTP_400_BAD_REQUEST)
        bazon_account: BazonAccount = amo_account.bazon_accounts.first()
        bazon_api = bazon_account.get_api()
        search = self.request.query_params.get("search")
        storage_id = self.request.query_params.get("storage_id")
        if storage_id is None:
            return Response({"Error": "Need storage id"}, status=HTTP_400_BAD_REQUEST)
        response = bazon_api.get_items(limit=5000, search=search, storages_ids=[int(storage_id)])
        if response.status_code == 200:
            serializer = ItemsListSerializer(response.json())
            serializer.serialize()
            return Response(serializer.get_serialized_data(), status=HTTP_200_OK)
        else:
            response.raise_for_status()
            return Response(response.json(), status=HTTP_502_BAD_GATEWAY)


class BazonItemsAddView(APIView):

    def post(self, request, amo_lead_id):
        data = request.data
        headers = request.headers
        try:
            headers.get("Origin", "").split("//")[-1].split(".")[0]
        except Exception:
            return Response({"Error": "Bad origin"}, status=HTTP_400_BAD_REQUEST)
        deal_id = data.get("dealId")
        if deal_id is None:
            return Response({"Error": "Need dealId"}, status=HTTP_400_BAD_REQUEST)
        items = data.get("items")
        if not isinstance(items, list):
            return Response({"Error": "Array of items expected"}, status=HTTP_400_BAD_REQUEST)
        query = SaleDocument.objects.filter(amo_lead_id=deal_id)
        if not query.exists():
            return Response({"Error": "Sale document not found"}, status=HTTP_404_NOT_FOUND)
        sale_document: SaleDocument = query.first()
        bazon_account: BazonAccount = sale_document.bazon_account
        bazon_api = bazon_account.get_api()
        hash_token = hashlib.md5()
        hash_token.update(str(time.time()).encode("utf-8"))
        token = hash_token.hexdigest()[:16]
        response = bazon_api.set_lock_key(sale_document.number, token)
        response.raise_for_status()
        lock_key = response.json().get("response", {}).get("setDocumentLock", {}).get("lockKey")
        if not isinstance(lock_key, str):
            return Response({"Error": "Cant get lock key"}, status=HTTP_502_BAD_GATEWAY)
        print(lock_key)
        items_to_add = []
        for item in items:
            storage_id = item.get("storageId")
            if storage_id is None:
                continue
            product_id = item.get("productId")
            if product_id is None:
                continue
            amount = item.get("quantity")
            if amount is None:
                continue
            items_to_add.append({
                "objectID": item.get("productId"),
                "objectType": "Product",
                "amount": amount,
                "storageID": storage_id,
                "id": "-1"
            })
            item_to_add = [
                {
                    "objectID": item.get("productId"),
                    "objectType": "Product",
                    "amount": amount,
                    "storageID": storage_id,
                    "id": "-1"
                }
            ]
            response = bazon_api.add_item_to_document(lock_key, document_id=sale_document.internal_id, items=item_to_add)
        try:
            response.raise_for_status()
        except Exception as error:
            bazon_api.drop_lock_key(sale_document.internal_id, lock_key)
            return Response({"Error": "Cant add items"}, status=HTTP_500_INTERNAL_SERVER_ERROR)
        bazon_api.drop_lock_key(sale_document.internal_id, lock_key)
        cache.delete(sale_document.number)
        return Response({"Result": "Ok"}, status=HTTP_200_OK)


class BazonDeleteItemView(APIView):

    def post(self, request, amo_lead_id):
        data = request.data
        headers = request.headers
        try:
            amo_url = headers.get("Origin", "").split("//")[-1].split(".")[0]
            if amo_url is None:
                return Response({"Error": "Bad origin"}, status=HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({"Error": "Bad origin"}, status=HTTP_400_BAD_REQUEST)
        deal_id = data.get("dealId")
        if deal_id is None:
            return Response({"Error": "Need dealId"}, status=HTTP_400_BAD_REQUEST)
        item: int = data.get("itemId")
        if not isinstance(item, int):
            return Response({"Error": "Array of items expected"}, status=HTTP_400_BAD_REQUEST)
        query = SaleDocument.objects.filter(amo_lead_id=deal_id)
        if not query.exists():
            return Response({"Error": "Sale document not found"}, status=HTTP_404_NOT_FOUND)
        sale_document: SaleDocument = query.first()
        bazon_account: BazonAccount = sale_document.bazon_account
        bazon_api = bazon_account.get_api()
        lock_key = bazon_api.generate_lock_key(sale_document.number)
        if not isinstance(lock_key, str):
            return Response({"Error": "Cant get lock key"}, status=HTTP_502_BAD_GATEWAY)
        response = bazon_api.remove_document_items(sale_document.internal_id, lock_key=lock_key, items=[item])
        bazon_api.drop_lock_key(sale_document.internal_id, lock_key)
        return Response({"Result": "ok"}, status=HTTP_200_OK)


class BazonDealOrdersView(APIView):

    def get(self, request, amo_lead_id):
        document_query = SaleDocument.objects.filter(amo_lead_id=amo_lead_id)
        if not document_query.exists():
            return Response({"Error": "Document not exists"}, status=HTTP_404_NOT_FOUND)
        sale_document: SaleDocument = document_query.first()
        bazon_account: BazonAccount = sale_document.bazon_account
        bazon_api = bazon_account.get_api()
        response = bazon_api.get_orders(for_sale_document=sale_document.number)
        if response.status_code == 200:
            return Response(response.json().get("response",[{}])[0].get("result", {}).get("orders",[]), status=HTTP_200_OK)
        return Response({"Result": "Ok"}, status=HTTP_200_OK)


class BazonMoveSaleView(APIView):

    """
    Вью для перемещения сделок amo-bazon/bazon-sale/<amo_lead_id>/move
    в теле запроса обязательно должен быть {
    """

    def post(self, request, amo_lead_id: int):
        data = request.data
        state = data.get("state")
        if state is None:
            return Response({"Error": "Need state"}, status=HTTP_400_BAD_REQUEST)
        if state not in ["reserve", "cancel"]:
            return Response({"Error", "Invalid state"}, status=HTTP_400_BAD_REQUEST)
        self.move_deal(request, amo_lead_id, state)
        return Response({"Result": "ok"}, status=HTTP_200_OK)

    def move_deal(self, request, amo_lead_id, state):
        headers = request.headers
        try:
            amo_url = headers.get("Origin", "").split("//")[-1].split(".")[0]
        except Exception:
            return Response({"Error": "Bad origin"}, status=HTTP_400_BAD_REQUEST)
        query = SaleDocument.objects.filter(amo_lead_id=amo_lead_id)
        if not query.exists():
            return Response({"Error": "Sale document not found"}, status=HTTP_404_NOT_FOUND)
        sale_document: SaleDocument = query.first()
        bazon_account: BazonAccount = sale_document.bazon_account
        bazon_api = bazon_account.get_api()

        lock_key = bazon_api.generate_lock_key(sale_document.number)
        if lock_key is None:
            return Response({"Error": "bad_lock_key"}, status=HTTP_404_NOT_FOUND)

        if state == "reserve":
            bazon_api.sale_reserve(sale_document.internal_id, lock_key)
        if state == "cancel":
            bazon_api.cancel_sale(sale_document.internal_id, lock_key)

        bazon_api.drop_lock_key(sale_document.internal_id, lock_key)

        return Response({"Result": "Moved"}, status=HTTP_200_OK)