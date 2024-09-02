from amo.models import Status
from django.db.models import ObjectDoesNotExist


def on_lead_status_handler(data):
    lead_id_arr = data.get("leads[status][0][id]", [])
    if len(lead_id_arr) == 0:
        return
    lead_id = lead_id_arr[0]
    lead_status_id_arr = data.get("leads[status][0][status_id]", [])
    if len(lead_status_id_arr) == 0:
        return
    lead_status_id = lead_status_id_arr[0]
    try:
        amo_status = Status.objects.get(amo_id=int(lead_status_id))
    except ObjectDoesNotExist:
        return
    bazon_status = amo_status.bazon_status
    if bazon_status is None:
        return
    print(bazon_status)