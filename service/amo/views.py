from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .amo_webhooks import on_lead_status_handler, on_lead_update_handler
from bazon.mixins.origin_check_mixin import OriginCheckMixin
from .models import AmoAccount
from rest_framework.exceptions import NotFound


class AmoWebhookView(APIView):

    def post(self, request, subdomain):
        print(subdomain)
        data = request.data
        if data.get("leads[status][0][id]") is not None:
            on_lead_status_handler(data)
        if data.get("leads[update][0][id]") is not None:
            on_lead_update_handler(data)
        return Response({"Status": "Good"}, status=status.HTTP_200_OK)
    

class AmoGetFieldIdView(APIView, OriginCheckMixin):

    def get(self, request):
        subdomain = self.check_origin(request)
        amo_account = AmoAccount.objects.filter(suburl=subdomain).first()
        if amo_account is None:
            raise NotFound()
        config = amo_account.get_config()
        bazon_field_id = config.get("bazon_field", 0)
        return Response({
            "field_id": bazon_field_id
        })
        