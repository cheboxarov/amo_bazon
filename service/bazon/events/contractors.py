from bazon.models import Contractor
from amo.models import AmoAccount


def on_create_contractor(contractor_data: dict, amo_account: AmoAccount):
    print(f"Contractor created: {contractor_data['name']}")


def on_update_contractor(contractor_data: dict, amo_account: AmoAccount):
    print(f"Contractor updated: {contractor_data['name']}")
