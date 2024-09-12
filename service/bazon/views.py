import time
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework.response import Response
from rest_framework.status import *
from rest_framework.views import APIView

from utils.bazon_api import Bazon
from .models import SaleDocument, BazonAccount
from .serializers import BazonSaleDocumentSerializer, AddSalePaySerializer, PayBackSaleSerializer
from amo.models import AmoAccount
from utils.serializers.bazon_serializers import ItemsListSerializer
import hashlib
from .mixins import OriginCheckMixin, SaleDocumentMixin, BazonApiMixin


class CustomAPIView(OriginCheckMixin, APIView):
    pass


class BazonSaleView(CustomAPIView, SaleDocumentMixin):

    def get(self, request, amo_id):
        self.check_origin(request)
        sale_document = self.get_sale_document(amo_lead_id=amo_id)
        serializer = BazonSaleDocumentSerializer(sale_document)
        return Response(serializer.data, status=HTTP_200_OK)


class BazonSaleProductsView(CustomAPIView, SaleDocumentMixin):
    def get(self, request, amo_id):
        self.check_origin(request)
        sale_document = self.get_sale_document(amo_lead_id=amo_id)
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


class BazonSalesListView(CustomAPIView):

    def get(self, request):
        self.check_origin(request)
        queryset = SaleDocument.objects
        serializer = BazonSaleDocumentSerializer(queryset.all(), many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    def post(self, request):
        self.check_origin(request)
        data = request.data
        lead_ids = data.get("lead_ids", [])
        if len(lead_ids) == 0:
            return Response({"Error": "Need lead_ids"}, status=HTTP_400_BAD_REQUEST)
        documents = SaleDocument.objects.filter(amo_lead_id__in=lead_ids).prefetch_related("bazon_account", "amo_account").all()
        serializer = BazonSaleDocumentSerializer(documents, many=True)
        return Response(serializer.data, status=HTTP_200_OK)


class BazonItemsListView(CustomAPIView):
    def get(self, request, amo_url):
        self.check_origin(request)
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


class BazonItemsAddView(CustomAPIView, SaleDocumentMixin):

    def post(self, request, amo_lead_id):
        data = request.data
        self.check_origin(request)
        deal_id = data.get("dealId")
        if deal_id is None:
            return Response({"Error": "Need dealId"}, status=HTTP_400_BAD_REQUEST)
        items = data.get("items")
        if not isinstance(items, list):
            return Response({"Error": "Array of items expected"}, status=HTTP_400_BAD_REQUEST)
        sale_document = self.get_sale_document(amo_lead_id=deal_id)
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


class BazonDeleteItemView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def post(self, request, amo_lead_id):
        data = request.data
        self.check_origin(request)
        deal_id = data.get("dealId")
        if deal_id is None:
            return Response({"Error": "Need dealId"}, status=HTTP_400_BAD_REQUEST)
        item: int = data.get("itemId")
        if not isinstance(item, int):
            return Response({"Error": "Array of items expected"}, status=HTTP_400_BAD_REQUEST)
        sale_document = self.get_sale_document(amo_lead_id=deal_id)
        bazon_account: BazonAccount = sale_document.bazon_account
        bazon_api = bazon_account.get_api()
        with sale_document.generate_lock_key() as lock_key:
            response = bazon_api.remove_document_items(sale_document.internal_id, lock_key=lock_key, items=[item])
            if response.status_code == 200:
                return Response({"Result": "ok"}, status=HTTP_200_OK)
        return self.return_response_error(response)


class BazonDealOrdersView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def get(self, request, amo_lead_id):
        self.check_origin(request)
        sale_document = self.get_sale_document(amo_lead_id=amo_lead_id)
        bazon_account: BazonAccount = sale_document.bazon_account
        bazon_api = bazon_account.get_api()
        response = bazon_api.get_orders(for_sale_document=sale_document.number)
        if response.status_code == 200:
            return Response(response.json().get("response",[{}])[0].get("result", {}).get("orders",[]), status=HTTP_200_OK)

        return self.return_response_error(response)


class BazonMoveSaleView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    """
    Вью для перемещения сделок amo-bazon/bazon-sale/<amo_lead_id>/move
    в теле запроса обязательно должен быть {
    """

    def post(self, request, amo_lead_id: int):
        self.check_origin(request)
        data = request.data
        state = data.get("state")
        if state is None:
            return Response({"Error": "Need state"}, status=HTTP_400_BAD_REQUEST)
        if state not in ["reserve", "cancel", "recreate"]:
            return Response({"Error", "Invalid state"}, status=HTTP_400_BAD_REQUEST)
        return self.move_deal(request, amo_lead_id, state)

    def move_deal(self, request, amo_lead_id, state):
        self.check_origin(request)
        sale_document = self.get_sale_document(amo_lead_id=amo_lead_id)
        bazon_account: BazonAccount = sale_document.bazon_account
        bazon_api = bazon_account.get_api()

        with sale_document.generate_lock_key() as lock_key:
            if lock_key is None:
                return Response({"Error": "bad_lock_key"}, status=HTTP_404_NOT_FOUND)
            response = None
            if state == "reserve":
                response = bazon_api.sale_reserve(sale_document.internal_id, lock_key)
            if state == "cancel":
                response = bazon_api.cancel_sale(sale_document.internal_id, lock_key)
            if state == "recreate":
                response = bazon_api.sale_recreate(sale_document.internal_id, lock_key)

        if response.status_code == 200:
            return Response({"Result": "Moved"}, status=HTTP_200_OK)

        return self.return_response_error(response)


class BazonAddSalePayView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def post(self, request, amo_lead_id):
        self.check_origin(request)
        sale_document = self.get_sale_document(amo_lead_id=amo_lead_id)

        serializer = AddSalePaySerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        pay_source = validated_data.get("pay_source")
        pay_sum = validated_data.get("pay_sum")
        comment = validated_data.get("comment")

        bazon_api = sale_document.bazon_account.get_api()

        with sale_document.generate_lock_key() as lock_key:
            if lock_key is None:
                return Response({"Error": "bad_lock_key"}, status=HTTP_423_LOCKED)
            response = bazon_api.add_sale_pay(sale_document.internal_id, lock_key, pay_source, pay_sum, comment)

        if response.status_code == 200:
            return Response({"result": "ok"}, status=HTTP_200_OK)

        return self.return_response_error(response)


class BazonGetPaySourcesView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def get(self, request, amo_lead_id):

        self.check_origin(request)

        sale_document = self.get_sale_document(amo_lead_id)

        bazon_api = sale_document.get_api()
        response = bazon_api.get_pay_sources()
        if response.status_code == 200:
            response_json = response.json()
            sources = response_json.get("response", {}).get("getPaySources", {}).get("PaySourcesList", {}).get("entitys", [])
            return Response(sources, status=HTTP_200_OK)

        return self.return_response_error(response)


class BazonGetPaidSourcesView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def get(self, request, amo_lead_id):

        sale_document = self.get_sale_document(amo_lead_id)
        bazon_api = sale_document.bazon_account.get_api()

        response = bazon_api.get_paid_sources(sale_document.internal_id)

        if response.status_code == 200:
            data = response.json()
            return Response(data.get("response", {}).get("getDocumentPaidSources", {}).get("paidSources", {}), status=HTTP_200_OK)

        return self.return_response_error(response)


class BazonSalePayBack(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def post(self, request, amo_lead_id):

        self.check_origin(request)

        sale_document = self.get_sale_document(amo_lead_id)
        bazon_api = sale_document.bazon_account.get_api()

        serializer = PayBackSaleSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        pay_source = validated_data.get("pay_source")
        pay_sum = validated_data.get("pay_sum")

        with sale_document.generate_lock_key() as lock_key:
            if lock_key is None:
                return Response({"Error": "bad_lock_key"}, status=HTTP_502_BAD_GATEWAY)
            response = bazon_api.sale_pay_back(sale_document.internal_id, lock_key, pay_source, pay_sum)

        if response.status_code == 200:
            return Response({"Result": "Ok"}, status=HTTP_200_OK)

        return self.return_response_error(response)