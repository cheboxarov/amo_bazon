from amo.models import Status
from django.db.models import ObjectDoesNotExist


def on_lead_status_handler(data):
    print(data)
    lead_id = data.get("leads[status][0][id]")
    if lead_id is None:
        return
    print(lead_id)
    lead_status_id = data.get("leads[status][0][status_id]")
    if lead_status_id is None:
        return
    print(lead_status_id)
    try:
        amo_status = Status.objects.get(amo_id=int(lead_status_id))
    except ObjectDoesNotExist:
        print("Объект не найден")
        return
    bazon_status = amo_status.bazon_status
    if bazon_status is None:
        print(bazon_status)
        return
    print(bazon_status)
