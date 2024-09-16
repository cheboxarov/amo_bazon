from rest_framework.exceptions import APIException
from amo.models import AmoAccount


class OriginCheckMixin:

    def check_origin(self, request):
        origin = request.headers.get("Origin", "")
        if not origin:
            raise APIException("Bad origin", code=400)
        origin_parts = origin.split("//")[-1].split(".")
        if len(origin_parts) < 1:
            raise APIException("Bad origin", code=400)
        subdomain = origin_parts[0]
        if not AmoAccount.objects.filter(suburl=subdomain).exists():
            raise APIException("bad_amo_account")
        return subdomain
