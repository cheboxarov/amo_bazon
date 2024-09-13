from rest_framework.response import Response
import requests
from loguru import loge


class BazonApiMixin:
    def return_response_error(self, response: requests.Response):
        try:
            return Response(response.json(), status=response.status_code)
        except:
            return Response({"Error": "bazon_api_error"}, status=response.status_code)
