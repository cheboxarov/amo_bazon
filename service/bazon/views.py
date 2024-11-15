from django.core.exceptions import ObjectDoesNotExist
from rest_framework.response import Response
from rest_framework.status import *
from rest_framework.views import APIView
from loguru import logger
from utils.bazon_api import Bazon
from .models import SaleDocument, BazonAccount
from .serializers import (
    BazonSaleDocumentSerializer,
    AddSalePaySerializer,
    PayBackSaleSerializer,
    CreateSaleSerializer,
    CreateReceiptSerializer,
    GenerateReceiptRequestSerializer
)
from amo.models import AmoAccount
from utils.serializers.bazon_serializers import ItemsListSerializer
from .mixins import OriginCheckMixin, SaleDocumentMixin, BazonApiMixin
import json
from .events import on_update_sale_document
from rest_framework.request import Request
from rest_framework.exceptions import APIException


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


class BazonSaleDetailView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def get(self, request, amo_id):
        subdomain = self.check_origin(request)
        logger.info(f"{subdomain}: BazonSaleDetailView - Начало обработки запроса")

        sale_document = self.get_sale_document(amo_lead_id=amo_id)
        bazon_account: BazonAccount = sale_document.bazon_account
        bazon_api = bazon_account.get_api()

        response = bazon_api.get_detail_document(int(sale_document.number))

        if response.status_code == 200:
            data = response.json()
            logger.debug(f"Сделка получена: {data}")
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
        return self.return_response(response)


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
                raise APIException(detail="invalid_key_lock", code=403)

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
            return self.return_response(response)

        logger.error(
            f"{subdomain}: BazonItemsAddView - Ошибка при добавлении элементов: {response.status_code}"
        )
        return self.return_response(response)


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
                return self.return_response(response)

        logger.error(
            f"{subdomain}: BazonDeleteItemView - Ошибка при удалении элемента: {response.status_code}"
        )
        return self.return_response(response)


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
        return self.return_response(response)


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
        if state not in ["reserve", "cancel", "recreate", "issue"]:
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
                raise APIException(detail="invalid_key_lock", code=403)

            response = None
            if state == "reserve":
                response = bazon_api.sale_reserve(sale_document.internal_id, lock_key)
            if state == "cancel":
                response = bazon_api.cancel_sale(sale_document.internal_id, lock_key)
            if state == "recreate":
                response = bazon_api.sale_recreate(sale_document.internal_id, lock_key)
            if state == "issue":
                response = bazon_api.sale_issue(sale_document.internal_id, lock_key)

        if response.status_code == 200:
            logger.info(f"{subdomain}: BazonMoveSaleView - Сделка успешно перемещена")
            return self.return_response(response)

        logger.error(
            f"{subdomain}: BazonMoveSaleView - Ошибка при перемещении сделки: {response.status_code}"
        )
        return self.return_response(response)


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
                raise APIException(detail="invalid_key_lock", code=403)

            response = bazon_api.add_sale_pay(
                sale_document.internal_id, lock_key, pay_source, pay_sum, comment
            )

        if response.status_code == 200:
            logger.info(
                f"{subdomain}: BazonAddSalePayView - Успешная обработка платежа"
            )
            return self.return_response(response)

        logger.error(
            f"{subdomain}: BazonAddSalePayView - Ошибка при обработке платежа: {response.status_code}"
        )
        return self.return_response(response)


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
        return self.return_response(response)


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
        return self.return_response(response)


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
                raise APIException(detail="invalid_key_lock", code=403)

            response = bazon_api.sale_pay_back(
                sale_document.internal_id, lock_key, pay_source, pay_sum
            )

        if response.status_code == 200:
            logger.info(f"{subdomain}: BazonSalePayBack - Успешная обработка")
            return Response({"Result": "Ok"}, status=HTTP_200_OK)

        logger.error(
            f"{subdomain}: BazonSalePayBack - Ошибка при обработке: {response.status_code}"
        )
        return self.return_response(response)


class BazonSourcesView(CustomAPIView, SaleDocumentMixin, BazonApiMixin):

    def get(self, request):
        subdomain = self.check_origin(request)
        logger.info(f"[{subdomain}] Запрос на получение источников заявок.")
        amo_account = AmoAccount.objects.get(suburl=subdomain)
        api = amo_account.bazon_accounts.first().get_api()
        response = api.get_sources()

        if response.status_code != 200:
            logger.error(
                f"[{subdomain}] Bazon ответил ошибкой при получении источников ({response.status_code})"
            )
            return self.return_response(response)

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
            logger.error(
                f"[{subdomain}] Bazon ответил ошибкой при попытке получить склады ({response.status_code})"
            )
            return self.return_response(response)

        data = response.json()
        return Response(
            data.get("response", {})
            .get("getStoragesReference:full", {})
            .get("StoragesReference", {}),
            status=HTTP_200_OK,
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

        response = api.create_sale(
            f"id:{source}", manager, storage, manager_comment=comment
        )

        logger.debug(f"Ответ от базона при создании сделки: {response}")

        if response.status_code != 200:
            logger.error(
                f"[{subdomain}] Bazon ответил ошибкой при попытке создания сделки ({response.status_code})"
            )
            return self.return_response(response)

        document_json = (
            response.json().get("response", {}).get("saleCreate", {}).get("Document")
        )
        if document_json is None:
            logger.error(
                f"[{subdomain}] Не вышло получить сделку при создании {response.json()}"
            )
            return self.return_response(response)
        document_json["internal_id"] = document_json.pop("id")
        SaleDocument.objects.create(
            internal_id=document_json.get("internal_id"),
            bazon_account=amo_account.bazon_accounts.first(),
            number=document_json.get("number"),
            amo_account=amo_account,
            amo_lead_id=amo_lead_id,
        )

        return self.return_response(response)


class BazonManagersView(CustomAPIView, BazonApiMixin):

    def get(self, request):
        subdomain = self.check_origin(request)
        logger.info(f"[{subdomain}] Запрос на получение менеджеров.")
        amo_account = AmoAccount.objects.get(suburl=subdomain)
        api: Bazon = amo_account.bazon_accounts.first().get_api()
        response = api.get_managers()
        if response.status_code != 200:
            logger.warning(
                f"[{subdomain}] При получении менеджеров Bazon ответил ошибкой ({response.status_code})"
            )
            return self.return_response(response)
        logger.info(f"[{subdomain}] Запрос на получение менеджеров обрsаботан.")
        return Response(
            response.json()
            .get("response", {})
            .get("getUsersReference", {})
            .get("UsersReference", {}),
            status=HTTP_200_OK,
        )


class BazonPrintFromView(CustomAPIView, BazonApiMixin, SaleDocumentMixin):

    def get(self, request, amo_lead_id):

        subdomain = self.check_origin(request)
        logger.info(f"[{subdomain}] Запрос на получения чека и накладной.")
        sale_document = self.get_sale_document(amo_lead_id)
        api = sale_document.get_api()

        response = api.get_form_print(sale_document.internal_id)
        if response.status_code != 200:
            log = f"[{subdomain}] Bazon ответил ошибкой на получение чека и накладной {response.status_code}"
            try:
                log += f"\n {response.json()}"
            except json.JSONDecodeError:
                pass
            logger.error(log)
            return self.return_response(response)
        html = (
            response.json()
            .get("response", {})
            .get("getDocumentFormPrint", {})
            .get("html")
        )
        if html is None:
            log = f"[{subdomain}] Bazon ответил ошибкой на получение чека и накладной {response.status_code}"
            try:
                log += f"\n {response.json()}"
            except json.JSONDecodeError:
                pass
            logger.error(log)
            return self.return_response(response)
        return Response({"html": html})


class BazonSaleEditView(CustomAPIView, BazonApiMixin, SaleDocumentMixin):

    def post(self, request, amo_lead_id: int):
        subdomain = self.check_origin(request)
        logger.info(f"[{subdomain}] Начало обработки запроса изменения сделки")
        sale_document = self.get_sale_document(amo_lead_id)
        api = sale_document.get_api()

        with sale_document.generate_lock_key() as lock_key:
            response = api.edit_sale(sale_document.internal_id, request.data, lock_key)
            on_update_sale_document(
                sale_document=sale_document, amo_account=sale_document.amo_account
            )
            logger.debug(
                f"[{subdomain}] Базон ответил на изменение сделки {response.json()} \n Тело запроса: {request.data}"
            )

        return self.return_response(response)


class BazonContractorsListView(CustomAPIView, BazonApiMixin, SaleDocumentMixin):

    def get(self, request: Request, amo_lead_id):
        subdomain = self.check_origin(request)
        sale_docoument: SaleDocument = self.get_sale_document(amo_lead_id)
        params = request.query_params
        offset, limit = 0, 500
        if (params_offset := params.get("offset")) is not None:
            try:
                offset = int(params_offset)
            except ValueError:
                pass
        if (params_limit := params.get("limit")) is not None:
            try:
                limit = int(params_limit)
            except ValueError:
                pass
        bazon_api = sale_docoument.get_api()
        response = bazon_api.get_contractors(offset, limit)
        return Response(response.json(), response.status_code)


class BazonContractorApiView(CustomAPIView, BazonApiMixin, SaleDocumentMixin):

    def get(self, request, amo_lead_id: int):
        subdomain = self.check_origin(request)
        logger.info(f"[{subdomain}] Начало обработки запроса на получение контрагента")

        sale_docoument = self.get_sale_document(amo_lead_id)
        contractor_id = sale_docoument.contractor_id
        if contractor_id is None:
            logger.info(f"[{subdomain}] У сделки не найден контрагент")
            return Response({"error": "not found contractor"}, status=404)
        api = sale_docoument.get_api()
        response = api.get_contractor(contractor_id)
        logger.info(
            f"[{subdomain}] Получен контрагент с базона, статус ответа: {response.status_code}\nBody: {response.json()}"
        )
        return Response(response.json(), response.status_code)

    def post(self, request, amo_lead_id: int):
        subdomain = self.check_origin(request)
        logger.info(f"[{subdomain}] Начало обработки запроса создания клиента")
        sale_document = self.get_sale_document(amo_lead_id)
        api = sale_document.get_api()
        data = request.data
        response = api.set_contractor(**data)
        response_json = response.json()
        on_update_sale_document(
            sale_document=sale_document, amo_account=sale_document.amo_account
        )
        return Response(response_json, status=response.status_code)


class BazonSaleUpdate(CustomAPIView, BazonApiMixin, SaleDocumentMixin):

    def get(self, request, amo_lead_id: int):
        subdomain = self.check_origin(request)
        logger.info(f"[{subdomain}] Начало обработки запроса на обновление сделки")
        sale_document = self.get_sale_document(amo_lead_id)
        bazon_api = sale_document.get_api()
        sale_document_data = bazon_api.get_detail_document(
            int(sale_document.number)
        ).json()
        logger.debug(f"Акутализирую сделку - {sale_document_data}")
        document_json = sale_document_data["response"]["getDocument"]["Document"]
        document_json["internal_id"] = document_json.pop("id")
        try:
            on_update_sale_document(
                sale_data=document_json, amo_account=sale_document.amo_account
            )
            return Response(data={"status": "ok"}, status=200)
        except Exception as err:
            return Response(status=500)


class BazonItemEditCost(CustomAPIView, BazonApiMixin, SaleDocumentMixin):

    def post(self, request: Request, amo_lead_id: int):
        subdomain = self.check_origin(request)
        logger.info(f"[{subdomain}] Начало обработки запроса на изменение цены товара")
        sale_document = self.get_sale_document(amo_lead_id)
        bazon_api = sale_document.get_api()
        data = request.data
        with sale_document.generate_lock_key() as lock_key:
            response = bazon_api.edit_item_cost(
                data.get("items"), sale_document.internal_id, lock_key
            )
        return Response(data=response.json(), status=response.status_code)


class BazonGetCashMachinesView(CustomAPIView, BazonApiMixin, SaleDocumentMixin):

    def get(self, request: Request, amo_lead_id):
        subdomain = self.check_origin(request)
        logger.debug(f"[{subdomain}] Начало обработки запроса на получение кеш машин")
        sale_document = self.get_sale_document(amo_lead_id)
        api = sale_document.get_api()
        response = api.get_cash_machines()
        return Response(response.json(), response.status_code)


class BazonCreateReceiptView(CustomAPIView, BazonApiMixin, SaleDocumentMixin):

    def post(self, request: Request, amo_lead_id: int):
        subdomain = self.check_origin(request)
        logger.debug(f"[{subdomain}] Начало обработки запроса печати чека")
        sale_document = self.get_sale_document(amo_lead_id)
        bazon_api = sale_document.get_api()
        data = request.data
        serializer = CreateReceiptSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        valid_data = serializer.validated_data
        with sale_document.generate_lock_key() as lock_key:
            response = bazon_api.receipt_pay(sale_document.internal_id,
                                           valid_data.get("factory_number"),
                                           valid_data.get("cash_machine"),
                                           valid_data.get("contact"),
                                           valid_data.get("cash"),
                                           valid_data.get("electron"),
                                           lock_key)
        return Response(response.json(), response.status_code)

class BazonRefundReceiptView(CustomAPIView, BazonApiMixin, SaleDocumentMixin):

    def post(self, request: Request, amo_lead_id: int):
        subdomain = self.check_origin(request)
        logger.debug(f"[{subdomain}] Начало обработки запроса печати чека")
        sale_document = self.get_sale_document(amo_lead_id)
        bazon_api = sale_document.get_api()
        data = request.data
        serializer = CreateReceiptSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        valid_data = serializer.validated_data
        with sale_document.generate_lock_key() as lock_key:
            response = bazon_api.receipt_refund(sale_document.internal_id,
                                           valid_data.get("factory_number"),
                                           valid_data.get("cash_machine"),
                                           valid_data.get("contact"),
                                           valid_data.get("cash"),
                                           valid_data.get("electron"),
                                           lock_key)
        return Response(response.json(), response.status_code)

class BazonGenerateReceiptRequest(CustomAPIView, BazonApiMixin, SaleDocumentMixin):
    
    def post(self, request: Request, amo_lead_id: int):
        subdomain = self.check_origin(request)
        logger.debug(f"[{subdomain}] BazonGenerateReceiptRequest")
        data = request.data
        serializer = GenerateReceiptRequestSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        factory_number = validated_data.get("factory_number")
        sale_document = self.get_sale_document(amo_lead_id)
        api = sale_document.get_api()
        response = api.generate_receipt_request(sale_document.internal_id, factory_number)
        return Response(response.json(), response.status_code)
        

class BazonReceiptState(CustomAPIView, BazonApiMixin, SaleDocumentMixin):
    
    def get(self, request: Request, amo_lead_id: int, receipt_id: int):
        subdomain = self.check_origin(request)
        logger.debug(f"[{subdomain}] BazonReceiptState")
        sale_document = self.get_sale_document(amo_lead_id)
        api = sale_document.get_api()
        response = api.get_receipt_state(sale_document.internal_id, receipt_id)
        return Response(response.json(), response.status_code)
    

class BazonGetReceiptsView(CustomAPIView, BazonApiMixin, SaleDocumentMixin):

    def get(self, request: Request, amo_lead_id: int):
        subdomain = self.check_origin(request)
        logger.debug(f"[{subdomain}] BazonReceiptState start")
        sale_document = self.get_sale_document(amo_lead_id)
        api = sale_document.get_api()
        response = api.get_receipts(sale_document.internal_id)
        return Response(response.json(), response.status_code)