from rest_framework.exceptions import APIException

class OriginCheckMixin:

    def check_origin(self, request):
        origin = request.headers.get("Origin", "")
        if not origin:
            raise APIException("Bad origin", code=400)
        origin_parts = origin.split("//")[-1].split(".")
        if len(origin_parts) < 1:
            raise APIException("Bad origin", code=400)
        return origin_parts[0]