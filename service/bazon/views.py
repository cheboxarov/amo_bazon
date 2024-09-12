import logging

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.response import Response
from rest_framework.status import *
from rest_framework.views import APIView

from amo.models import AmoAccount
from utils.serializers.bazon_serializers import ItemsListSerializer
from .mixins import OriginCheckMixin, SaleDocumentMixin, BazonApiMixin
from .models import SaleDocument, BazonAccount
from .serializers import (
    BazonSaleDocumentSerializer,
)

logger = logging.getLogger(__name__)


class CustomAPIView(OriginCheckMixin, APIView):
    pass


class BazonSaleView(CustomAPIView, SaleDocumentMixin):

    def get(self, request, amo_id):
        self.check_origin(request)
        sale_document = self.get_sale_document(amo_lead_id=amo_id)
        serializer = BazonSaleDocumentSerializer(sale_document)
        logger.info(f"[{request.META.get('HTTP_HOST')}] Получение документа продажи: {amo_id}")
        return Response(serializer.data, status=HTTP_200_OK)


class BazonSaleProductsView(CustomAPIView, SaleDocumentMixin):
    def get(self, request, amo_id):
        self.check_origin(request)
        sale_document = self.get_sale_document(amo_lead_id=amo_id)
        bazon_account: BazonAccount = sale_document.bazon_account
        bazon_api = bazon_account.get_api()
        logger.info(f"[{request.META.get('HTTP_HOST')}] Получение товаров для документа: {sale_document.number}")

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
        logger.error(f"[{request.META.get('HTTP_HOST')}] Ошибка при получении товаров: {response.text}")
        return Response({"Error": "Cant connect to bazon"}, status=HTTP_200_OK)


class BazonSalesListView(CustomAPIView):

    def get(self, request):
        self.check_origin(request)
        queryset = SaleDocument.objects
        serializer = BazonSaleDocumentSerializer(queryset.all(), many=True)
        logger.info(f"[{request.META.get('HTTP_HOST')}] Получение списка документов продаж")
        return Response(serializer.data, status=HTTP_200_OK)

    def post(self, request):
        self.check_origin(request)
        data = request.data
        lead_ids = data.get("lead_ids", [])
        if len(lead_ids) == 0:
            logger.warning(f"[{request.META.get('HTTP_HOST')}] Ошибка: отсутствуют lead_ids.")
            return Response({"Error": "Need lead_ids"}, status=HTTP_400_BAD_REQUEST)

        documents = (
            SaleDocument.objects.filter(amo_lead_id__in=lead_ids)
            .prefetch_related("bazon_account", "amo_account")
            .all()
        )
        serializer = BazonSaleDocumentSerializer(documents, many=True)
        logger.info(f"[{request.META.get('HTTP_HOST')}] Получение документов продаж по lead_ids: {lead_ids}")
        return Response(serializer.data, status=HTTP_200_OK)


class BazonItemsListView(CustomAPIView):
    def get(self, request, amo_url):
        self.check_origin(request)
        try:
            amo_account = AmoAccount.objects.get(suburl=amo_url)
        except ObjectDoesNotExist:
            logger.error(f"[{request.META.get('HTTP_HOST')}] Ошибка: аккаунт Amo не найден по URL: {amo_url}")
            return Response(
                {"Error": "AmoAccount not found"}, status=HTTP_400_BAD_REQUEST
            )

        bazon_account: BazonAccount = amo_account.bazon_accounts.first()
        bazon_api = bazon_account.get_api()
        search = self.request.query_params.get("search")
        storage_id = self.request.query_params.get("storage_id")
        if storage_id is None:
            logger.warning(f"[{request.META.get('HTTP_HOST')}] Ошибка: отсутствует ID склада.")
            return Response({"Error": "Need storage id"}, status=HTTP_400_BAD_REQUEST)

        response = bazon_api.get_items(
            limit=5000, search=search, storages_ids=[int(storage_id)]
        )
        if response.status_code == 200:
            serializer = ItemsListSerializer(response.json())
            serializer.serialize()
            logger.info(f"[{request.META.get('HTTP_HOST')}] Получение товаров из Bazon для склада: {storage_id}")
            return Response(serializer.get_serialized_data(), status=HTTP_200_OK)
        else:
            logger.error(f"[{request.META.get('HTTP_HOST')}] Ошибка при получении товаров: {response.json()}")
            return Response(response.json(), status=HTTP_502_BAD_GATEWAY)


class BazonItemsAddView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def post(self, request, amo_lead_id):
        data = request.data
        self.check_origin(request)
        deal_id = data.get("dealId")
        if deal_id is None:
            logger.warning(f"[{request.META.get('HTTP_HOST')}] Ошибка: отсутствует dealId.")
            return Response({"Error": "Need dealId"}, status=HTTP_400_BAD_REQUEST)

        items = data.get("items")
        if not isinstance(items, list):
            logger.warning(f"[{request.META.get('HTTP_HOST')}] Ошибка: ожидался массив товаров.")
            return Response(
                {"Error": "Array of items expected"}, status=HTTP_400_BAD_REQUEST
            )

        sale_document = self.get_sale_document(amo_lead_id=deal_id)
        bazon_account: BazonAccount = sale_document.bazon_account
        bazon_api = bazon_account.get_api()
        logger.info(f"[{request.META.get('HTTP_HOST')}] Добавление товаров к документу: {deal_id}")

        with sale_document.generate_lock_key() as lock_key:
            if not isinstance(lock_key, str):
                logger.error(f"[{request.META.get('HTTP_HOST')}] Ошибка: не удалось получить ключ блокировки.")
                return Response(
                    {"Error": "Cant get lock key"}, status=HTTP_502_BAD_GATEWAY
                )
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
                items_to_add.append(
                    {
                        "objectID": item.get("productId"),
                        "objectType": "Product",
                        "amount": amount,
                        "storageID": storage_id,
                        "id": "-1",
                    }
                )
                item_to_add = [
                    {
                        "objectID": item.get("productId"),
                        "objectType": "Product",
                        "amount": amount,
                        "storageID": storage_id,
                        "id": "-1",
                    }
                ]
                response = bazon_api.add_item_to_document(
                    lock_key, document_id=sale_document.internal_id, items=item_to_add
                )
        if response.status_code == 200:
            logger.info(f"[{request.META.get('HTTP_HOST')}] Товары успешно добавлены к документу: {deal_id}")
            return Response({"Result": "Ok"}, status=HTTP_200_OK)

        logger.error(f"[{request.META.get('HTTP_HOST')}] Ошибка при добавлении товаров: {response.text}")
        return self.return_response_error(response)


class BazonDeleteItemView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def post(self, request, amo_lead_id):
        data = request.data
        self.check_origin(request)
        deal_id = data.get("dealId")
        if deal_id is None:
            logger.warning(f"[{request.META.get('HTTP_HOST')}] Ошибка: отсутствует dealId.")
            return Response({"Error": "Need dealId"}, status=HTTP_400_BAD_REQUEST)

        item: int = data.get("itemId")
        if not isinstance(item, int):
            logger.warning(f"[{request.META.get('HTTP_HOST')}] Ошибка: ожидался целочисленный ID товара.")
            return Response(
                {"Error": "Array of items expected"}, status=HTTP_400_BAD_REQUEST
            )

        sale_document = self.get_sale_document(amo_lead_id=deal_id)
        bazon_account: BazonAccount = sale_document.bazon_account
        bazon_api = bazon_account.get_api()
        logger.info(f"[{request.META.get('HTTP_HOST')}] Удаление товара из документа: {deal_id}, itemId: {item}")

        with sale_document.generate_lock_key() as lock_key:
            response = bazon_api.remove_document_items(
                sale_document.internal_id, lock_key=lock_key, items=[item]
            )
            if response.status_code == 200:
                logger.info(
                    f"[{request.META.get('HTTP_HOST')}] Товар успешно удален из документа: {deal_id}, itemId: {item}")
                return Response({"Result": "Ok"}, status=HTTP_200_OK)
            logger.error(f"[{request.META.get('HTTP_HOST')}] Ошибка при удалении товара: {response.text}")
            return self.return_response_error(response)
