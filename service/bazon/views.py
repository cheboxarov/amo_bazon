import time
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers import serialize
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework.response import Response
from rest_framework.status import *
from rest_framework.views import APIView
from loguru import logger
from utils.bazon_api import Bazon
from .events import on_create_sale_document
from .models import SaleDocument, BazonAccount
from .serializers import (
    BazonSaleDocumentSerializer,
    AddSalePaySerializer,
    PayBackSaleSerializer,
    CreateSaleSerializer
)
from amo.models import AmoAccount
from utils.serializers.bazon_serializers import ItemsListSerializer
import hashlib
from .mixins import OriginCheckMixin, SaleDocumentMixin, BazonApiMixin


class CustomAPIView(OriginCheckMixin, APIView):
    pass


class BazonSaleView(CustomAPIView, SaleDocumentMixin):

    def get(self, request, amo_id):
        subdomain = self.check_origin(request)
        logger.info(f"{subdomain}: BazonSaleView - Начало обработки запроса")

        sale_document = self.get_sale_document(amo_lead_id=amo_id)
        serializer = BazonSaleDocumentSerializer(sale_document)

        logger.info(
            f"{subdomain}: BazonSaleView - Успешное получение документа продажи"
        )
        return Response(serializer.data, status=HTTP_200_OK)


class BazonSaleDetailView(CustomAPIView, SaleDocumentMixin):

    def get(self, request, amo_id):
        subdomain = self.check_origin(request)
        logger.info(f"{subdomain}: BazonSaleDetailView - Начало обработки запроса")

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
            logger.info(
                f"{subdomain}: BazonSaleDetailView - Успешное получение деталей документа"
            )
            return Response(validated_data, status=HTTP_200_OK)

        logger.error(f"{subdomain}: BazonSaleDetailView - Ошибка подключения к Bazon")
        return Response({"Error": "Cant connect to bazon"}, status=HTTP_200_OK)


class BazonSalesListView(CustomAPIView):

    def get(self, request):
        subdomain = self.check_origin(request)
        logger.info(f"{subdomain}: BazonSalesListView - Начало обработки GET запроса")

        queryset = SaleDocument.objects
        serializer = BazonSaleDocumentSerializer(queryset.all(), many=True)
        logger.info(
            f"{subdomain}: BazonSalesListView - Успешное получение списка продаж"
        )
        return Response(serializer.data, status=HTTP_200_OK)

    def post(self, request):
        subdomain = self.check_origin(request)
        logger.info(f"{subdomain}: BazonSalesListView - Начало обработки POST запроса")

        data = request.data
        lead_ids = data.get("lead_ids", [])

        if len(lead_ids) == 0:
            logger.warning(f"{subdomain}: BazonSalesListView - Необходимы lead_ids")
            return Response({"Error": "Need lead_ids"}, status=HTTP_400_BAD_REQUEST)

        documents = (
            SaleDocument.objects.filter(amo_lead_id__in=lead_ids)
            .prefetch_related("bazon_account", "amo_account")
            .all()
        )
        serializer = BazonSaleDocumentSerializer(documents, many=True)
        logger.info(
            f"{subdomain}: BazonSalesListView - Успешное получение списка продаж по lead_ids"
        )
        return Response(serializer.data, status=HTTP_200_OK)


class BazonItemsListView(CustomAPIView):

    def get(self, request, amo_url):
        subdomain = self.check_origin(request)
        logger.info(f"{subdomain}: BazonItemsListView - Начало обработки запроса")

        try:
            amo_account = AmoAccount.objects.get(suburl=amo_url)
        except ObjectDoesNotExist:
            logger.warning(f"{subdomain}: BazonItemsListView - AmoAccount не найден")
            return Response(
                {"Error": "AmoAccount not found"}, status=HTTP_400_BAD_REQUEST
            )

        bazon_account: BazonAccount = amo_account.bazon_accounts.first()
        bazon_api = bazon_account.get_api()
        search = self.request.query_params.get("search")
        storage_id = self.request.query_params.get("storage_id")

        if storage_id is None:
            logger.warning(f"{subdomain}: BazonItemsListView - Необходим storage id")
            return Response({"Error": "Need storage id"}, status=HTTP_400_BAD_REQUEST)

        response = bazon_api.get_items(
            limit=5000, search=search, storages_ids=[int(storage_id)]
        )

        if response.status_code == 200:
            serializer = ItemsListSerializer(response.json())
            serializer.serialize()
            logger.info(
                f"{subdomain}: BazonItemsListView - Успешное получение элементов"
            )
            return Response(serializer.get_serialized_data(), status=HTTP_200_OK)

        logger.error(
            f"{subdomain}: BazonItemsListView - Ошибка при получении элементов: {response.status_code}"
        )
        return Response(response.json(), status=HTTP_502_BAD_GATEWAY)


class BazonItemsAddView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def post(self, request, amo_lead_id):
        subdomain = self.check_origin(request)
        logger.info(f"{subdomain}: BazonItemsAddView - Начало обработки запроса")

        data = request.data
        deal_id = data.get("dealId")
        if deal_id is None:
            logger.warning(f"{subdomain}: BazonItemsAddView - Необходим dealId")
            return Response({"Error": "Need dealId"}, status=HTTP_400_BAD_REQUEST)

        items = data.get("items")
        if not isinstance(items, list):
            logger.warning(
                f"{subdomain}: BazonItemsAddView - Ожидается массив идентификаторов элементов"
            )
            return Response(
                {"Error": "Array of items expected"}, status=HTTP_400_BAD_REQUEST
            )

        sale_document = self.get_sale_document(amo_lead_id=deal_id)
        bazon_account: BazonAccount = sale_document.bazon_account
        bazon_api = bazon_account.get_api()

        with sale_document.generate_lock_key() as lock_key:
            if not isinstance(lock_key, str):
                logger.error(
                    f"{subdomain}: BazonItemsAddView - Не удалось получить lock key"
                )
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
            logger.info(
                f"{subdomain}: BazonItemsAddView - Успешное добавление элементов"
            )
            return Response({"Result": "Ok"}, status=HTTP_200_OK)

        logger.error(
            f"{subdomain}: BazonItemsAddView - Ошибка при добавлении элементов: {response.status_code}"
        )
        return self.return_response_error(response)


class BazonDeleteItemView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def post(self, request, amo_lead_id):
        subdomain = self.check_origin(request)
        logger.info(f"{subdomain}: BazonDeleteItemView - Начало обработки запроса")

        data = request.data
        deal_id = data.get("dealId")
        if deal_id is None:
            logger.warning(f"{subdomain}: BazonDeleteItemView - Необходим dealId")
            return Response({"Error": "Need dealId"}, status=HTTP_400_BAD_REQUEST)

        item: int = data.get("itemId")
        if not isinstance(item, int):
            logger.warning(
                f"{subdomain}: BazonDeleteItemView - Ожидается массив идентификаторов элементов"
            )
            return Response(
                {"Error": "Array of items expected"}, status=HTTP_400_BAD_REQUEST
            )

        sale_document = self.get_sale_document(amo_lead_id=deal_id)
        bazon_account: BazonAccount = sale_document.bazon_account
        bazon_api = bazon_account.get_api()

        with sale_document.generate_lock_key() as lock_key:
            response = bazon_api.remove_document_items(
                sale_document.internal_id, lock_key=lock_key, items=[item]
            )
            if response.status_code == 200:
                logger.info(
                    f"{subdomain}: BazonDeleteItemView - Успешное удаление элемента"
                )
                return Response({"Result": "ok"}, status=HTTP_200_OK)

        logger.error(
            f"{subdomain}: BazonDeleteItemView - Ошибка при удалении элемента: {response.status_code}"
        )
        return self.return_response_error(response)


class BazonDealOrdersView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def get(self, request, amo_lead_id):
        subdomain = self.check_origin(request)
        logger.info(f"{subdomain}: BazonDealOrdersView - Начало обработки запроса")

        sale_document = self.get_sale_document(amo_lead_id=amo_lead_id)
        bazon_account: BazonAccount = sale_document.bazon_account
        bazon_api = bazon_account.get_api()
        response = bazon_api.get_orders(for_sale_document=sale_document.number)

        if response.status_code == 200:
            logger.info(
                f"{subdomain}: BazonDealOrdersView - Успешное получение заказов"
            )
            return Response(
                response.json()
                .get("response", [{}])[0]
                .get("result", {})
                .get("orders", []),
                status=HTTP_200_OK,
            )

        logger.error(
            f"{subdomain}: BazonDealOrdersView - Ошибка при получении заказов: {response.status_code}"
        )
        return self.return_response_error(response)


class BazonMoveSaleView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def post(self, request, amo_lead_id: int):
        subdomain = self.check_origin(request)
        logger.info(f"{subdomain}: BazonMoveSaleView - Начало обработки запроса")

        data = request.data
        state = data.get("state")
        if state is None:
            logger.error(
                f"{subdomain}: BazonMoveSaleView - Ошибка: Необходимо указать состояние"
            )
            return Response({"Error": "Need state"}, status=HTTP_400_BAD_REQUEST)
        if state not in ["reserve", "cancel", "recreate"]:
            logger.error(
                f"{subdomain}: BazonMoveSaleView - Ошибка: Неверное состояние {state}"
            )
            return Response({"Error": "Invalid state"}, status=HTTP_400_BAD_REQUEST)

        return self.move_deal(request, amo_lead_id, state)

    def move_deal(self, request, amo_lead_id, state):
        subdomain = self.check_origin(request)
        logger.info(
            f"{subdomain}: BazonMoveSaleView - Перемещение сделки с состоянием {state}"
        )

        sale_document = self.get_sale_document(amo_lead_id=amo_lead_id)
        bazon_account: BazonAccount = sale_document.bazon_account
        bazon_api = bazon_account.get_api()

        with sale_document.generate_lock_key() as lock_key:
            if lock_key is None:
                logger.error(f"{subdomain}: BazonMoveSaleView - Неверный lock_key")
                return Response({"Error": "bad_lock_key"}, status=HTTP_404_NOT_FOUND)

            response = None
            if state == "reserve":
                response = bazon_api.sale_reserve(sale_document.internal_id, lock_key)
            if state == "cancel":
                response = bazon_api.cancel_sale(sale_document.internal_id, lock_key)
            if state == "recreate":
                response = bazon_api.sale_recreate(sale_document.internal_id, lock_key)

        if response.status_code == 200:
            logger.info(f"{subdomain}: BazonMoveSaleView - Сделка успешно перемещена")
            return Response({"Result": "Moved"}, status=HTTP_200_OK)

        logger.error(
            f"{subdomain}: BazonMoveSaleView - Ошибка при перемещении сделки: {response.status_code}"
        )
        return self.return_response_error(response)


class BazonAddSalePayView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def post(self, request, amo_lead_id):
        subdomain = self.check_origin(request)
        logger.info(f"{subdomain}: BazonAddSalePayView - Начало обработки запроса")

        sale_document = self.get_sale_document(amo_lead_id=amo_lead_id)

        serializer = AddSalePaySerializer(data=request.data)

        if not serializer.is_valid():
            logger.error(
                f"{subdomain}: BazonAddSalePayView - Ошибка валидации: {serializer.errors}"
            )
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        pay_source = validated_data.get("pay_source")
        pay_sum = validated_data.get("pay_sum")
        comment = validated_data.get("comment")

        bazon_api = sale_document.bazon_account.get_api()

        with sale_document.generate_lock_key() as lock_key:
            if lock_key is None:
                logger.error(f"{subdomain}: BazonAddSalePayView - Неверный lock_key")
                return Response({"Error": "bad_lock_key"}, status=HTTP_423_LOCKED)

            response = bazon_api.add_sale_pay(
                sale_document.internal_id, lock_key, pay_source, pay_sum, comment
            )

        if response.status_code == 200:
            logger.info(
                f"{subdomain}: BazonAddSalePayView - Успешная обработка платежа"
            )
            return Response({"result": "ok"}, status=HTTP_200_OK)

        logger.error(
            f"{subdomain}: BazonAddSalePayView - Ошибка при обработке платежа: {response.status_code}"
        )
        return self.return_response_error(response)


class BazonGetPaySourcesView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def get(self, request, amo_lead_id):
        subdomain = self.check_origin(request)
        logger.info(f"{subdomain}: BazonGetPaySourcesView - Начало обработки запроса")

        sale_document = self.get_sale_document(amo_lead_id)

        bazon_api = sale_document.get_api()
        response = bazon_api.get_pay_sources()

        if response.status_code == 200:
            response_json = response.json()
            sources = (
                response_json.get("response", {})
                .get("getPaySources", {})
                .get("PaySourcesList", {})
                .get("entitys", [])
            )
            logger.info(
                f"{subdomain}: BazonGetPaySourcesView - Успешное получение источников платежей"
            )
            return Response(sources, status=HTTP_200_OK)

        logger.error(
            f"{subdomain}: BazonGetPaySourcesView - Ошибка при получении источников платежей: {response.status_code}"
        )
        return self.return_response_error(response)


class BazonGetPaidSourcesView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def get(self, request, amo_lead_id):
        subdomain = self.check_origin(request)
        logger.info(
            f"{subdomain}: Получение источников платежей для сделки {amo_lead_id}"
        )

        sale_document = self.get_sale_document(amo_lead_id)
        bazon_api = sale_document.bazon_account.get_api()

        response = bazon_api.get_paid_sources(sale_document.internal_id)

        if response.status_code == 200:
            data = response.json()
            logger.info(
                f"{subdomain}: Источники платежей успешно получены для сделки {amo_lead_id}"
            )
            return Response(
                data.get("response", {})
                .get("getDocumentPaidSources", {})
                .get("paidSources", {}),
                status=HTTP_200_OK,
            )

        logger.error(
            f"{subdomain}: Ошибка при получении источников платежей для сделки {amo_lead_id}"
        )
        return self.return_response_error(response)


class BazonSalePayBack(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def post(self, request, amo_lead_id):
        subdomain = self.check_origin(request)
        logger.info(f"{subdomain}: BazonSalePayBack - Начало обработки запроса")

        sale_document = self.get_sale_document(amo_lead_id)
        bazon_api = sale_document.bazon_account.get_api()

        serializer = PayBackSaleSerializer(data=request.data)

        if not serializer.is_valid():
            logger.error(
                f"{subdomain}: BazonSalePayBack - Ошибка валидации: {serializer.errors}"
            )
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        pay_source = validated_data.get("pay_source")
        pay_sum = validated_data.get("pay_sum")

        with sale_document.generate_lock_key() as lock_key:
            if lock_key is None:
                logger.error(f"{subdomain}: BazonSalePayBack - Неверный lock_key")
                return Response({"Error": "bad_lock_key"}, status=HTTP_502_BAD_GATEWAY)

            response = bazon_api.sale_pay_back(
                sale_document.internal_id, lock_key, pay_source, pay_sum
            )

        if response.status_code == 200:
            logger.info(f"{subdomain}: BazonSalePayBack - Успешная обработка")
            return Response({"Result": "Ok"}, status=HTTP_200_OK)

        logger.error(
            f"{subdomain}: BazonSalePayBack - Ошибка при обработке: {response.status_code}"
        )
        return self.return_response_error(response)


class BazonSourcesView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def get(self, request):
        subdomain = self.check_origin(request)
        logger.info(f"[{subdomain}] Запрос на получение источников заявок.")
        amo_account = AmoAccount.objects.get(suburl=subdomain)
        api = amo_account.bazon_accounts.first().get_api()
        response = api.get_sources()

        if response.status_code != 200:
            logger.error(f"[{subdomain}] Bazon ответил ошибкой при получении источников ({response.status_code})")
            return self.return_response_error(response)

        data = response.json()
        logger.info(f"[{subdomain}] Запрос на получение источников обработан.")
        return Response(
            data.get("response", {})
            .get("getSaleSourcesReference", {})
            .get("SaleSourcesReference", {}),
            status=HTTP_200_OK,
        )

class BazonStoragesView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def get(self, request):

        subdomain = self.check_origin(request)
        logger.info(f"[{subdomain}] Запрос на получение складов.")
        amo_account = AmoAccount.objects.get(suburl=subdomain)
        api = amo_account.bazon_accounts.first().get_api()

        response = api.get_storages()
        if response.status_code != 200:
            logger.error(f"[{subdomain}] Bazon ответил ошибкой при попытке получить склады ({response.status_code})")
            return self.return_response_error(response)

        data = response.json()
        return Response(
            data.get("response", {})
            .get("getStoragesReference:full", {})
            .get("StoragesReference", {}),
            status=HTTP_200_OK
        )


class BazonCreateDealView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def post(self, request):

        subdomain = self.check_origin(request)
        amo_account = AmoAccount.objects.get(suburl=subdomain)
        logger.info(f"[{subdomain}] Запрос на создание сделки.")
        api: Bazon = amo_account.bazon_accounts.first().get_api()

        data = request.data
        serializer = CreateSaleSerializer(data=data)
        if not serializer.is_valid():
            logger.error(f"[{subdomain}] Ошибка валидации запроса: {serializer.errors}")
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        comment = validated_data.get("comment")
        source = validated_data.get("source")
        storage = validated_data.get("storage")
        manager = validated_data.get("manager")
        amo_lead_id = validated_data.get("amoLeadId")

        response = api.create_sale(f"id:{source}", manager, storage, manager_comment=comment)

        logger.debug(f"Ответ от базона при создании сделки: {response}")

        if response.status_code != 200:
            logger.error(f"[{subdomain}] Bazon ответил ошибкой при попытке создания сделки ({response.status_code})")
            return self.return_response_error(response)

        document_json = request.data.get("response", {}).get("saleCreate", {}).get("Document")
        if document_json is None:
            logger.error(f"[{subdomain}] Не вышло получить сделку при создании {response.json()}")
            return self.return_response_error(response)
        document_json["internal_id"] = document_json.pop("id")
        SaleDocument.objects.create(
            **document_json, amo_account=amo_account, amo_lead_id=amo_lead_id
        )

        return Response(status=HTTP_204_NO_CONTENT)


class BazonManagersView(CustomAPIView, BazonApiMixin):

    def get(self, request):
        subdomain = self.check_origin(request)
        logger.info(f"[{subdomain}] Запрос на получение менеджеров.")
        amo_account = AmoAccount.objects.get(suburl=subdomain)
        api: Bazon = amo_account.bazon_accounts.first().get_api()
        response = api.get_managers()
        if response.status_code != 200:
            logger.warning(f"[{subdomain}] При получении менеджеров Bazon ответил ошибкой ({response.status_code})")
            return self.return_response_error(response)
        logger.info(f"[{subdomain}] Запрос на получение менеджеров обрsаботан.")
        return Response(response.json().get("response", {})
                        .get("getUsersReference", {})
                        .get("UsersReference", {}),
                        status=HTTP_200_OK)
