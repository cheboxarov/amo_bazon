from rest_framework.response import Response
from rest_framework.status import *
from rest_framework.views import APIView
from .models import SaleDocument


class BazonSaleView(APIView):
    def get(self, request, amo_id):
        queryset = SaleDocument.objects.filter(amo_lead_id=amo_id)
        if not queryset.exists():
            return Response({"Error": "Not found"}, status=HTTP_404_NOT_FOUND)
        sale_document = queryset.first()

        return Response({"goot": amo_id}, status=HTTP_200_OK)
