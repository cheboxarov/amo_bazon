from rest_framework.response import Response
from rest_framework.status import *
from rest_framework.views import APIView
from .models import SaleDocument, BazonAccount
from .serializers import BazonSaleDocumentSerializer
from utils.bazon_api import Bazon


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
        bazon_api = Bazon(bazon_account.login,
                          bazon_account.password,
                          bazon_account.refresh_token,
                          bazon_account.access_token)
        response = bazon_api.get_detail_document(sale_document.number)
        if response.status_code == 200:
            data = response.json()
            validated_data = {
                "document": data["response"]["getDocument"],
                "items": data.get("response", {}).get("getDocumentItems", {}).get("DocumentItemsList", {}).get("entitys", [])
            }
            return Response(validated_data, status=HTTP_200_OK)
        return Response({"Error": "Cant connect to bazon"}, status=HTTP_200_OK)
