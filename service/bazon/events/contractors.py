from bazon.models import Contractor


def on_create_contractor(contractor_data):
    print(f"Contractor created: {contractor_data['name']}")

def on_update_contractor(contractor_data):
    print(f"Contractor updated: {contractor_data['name']}")