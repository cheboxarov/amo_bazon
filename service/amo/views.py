from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status


class AmoWebhookView(APIView):

    def post(self, request):
        data = request.data
        print(data)
        return Response({"Status": "Good"}, status=status.HTTP_200_OK)