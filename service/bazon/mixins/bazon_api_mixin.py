from rest_framework.response import Response
import requests
import json


class BazonApiMixin:

    @staticmethod
    def return_response(response: requests.Response):
        try:
            return Response(response.json(), status=response.status_code)
        except json.JSONDecodeError:
            return Response({"Error": "bazon_api_error"}, status=response.status_code)
