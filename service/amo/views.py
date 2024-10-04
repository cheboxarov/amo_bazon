from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .amo_webhooks import on_lead_status_handler, on_lead_update_handler


class AmoWebhookView(APIView):

    def post(self, request, subdomain):
        print(subdomain)
        data = request.data
        if data.get("leads[status][0][id]") is not None:
            on_lead_status_handler(data)
        if data.get("leads[update][0][id]") is not None:
            on_lead_update_handler(data)
        return Response({"Status": "Good"}, status=status.HTTP_200_OK)