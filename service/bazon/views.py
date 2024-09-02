from django.core.exceptions import ObjectDoesNotExist
from rest_framework.response import Response
from rest_framework.status import *
from rest_framework.views import APIView
from .models import SaleDocument, BazonAccount
from .serializers import BazonSaleDocumentSerializer
from utils.bazon_api import Bazon
from amo.models import AmoAccount
from utils.serializers.bazon_serializers import ItemsListSerializer


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
        bazon_api = Bazon(
            bazon_account.login,
            bazon_account.password,
            bazon_account.refresh_token,
            bazon_account.access_token,
        )
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
        documents = SaleDocument.objects.filter(amo_lead_id__in=lead_ids).all()
        serializer = BazonSaleDocumentSerializer(documents, many=True)
        return Response(serializer.data, status=HTTP_200_OK)


class BazonItemsListView(APIView):
    def get(self, request, amo_url):
        try:
            amo_account = AmoAccount.objects.get(suburl=amo_url)
        except ObjectDoesNotExist:
            return Response({"Error": "AmoAccount not found"}, status=HTTP_400_BAD_REQUEST)
        bazon_account: BazonAccount = amo_account.bazon_accounts.first()
        bazon_api = Bazon(bazon_account.login,
                          bazon_account.password,
                          bazon_account.refresh_token,
                          bazon_account.access_token)
        search = self.request.query_params.get("search")
        response = bazon_api.get_items(limit=250, search=search)
        if response.status_code == 200:
            serializer = ItemsListSerializer(response.json())
            serializer.serialize()
            return Response(serializer.get_serialized_data(), status=HTTP_200_OK)
        else:
            response.raise_for_status()
            return Response(response.json(), status=HTTP_502_BAD_GATEWAY)