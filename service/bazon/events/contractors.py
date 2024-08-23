from bazon.models import Contractor


def on_create_contractor(contractor: Contractor):
    print(f"Contractor created: {contractor.name}")


def on_update_contractor(contractor: Contractor):
    print(f"Contractor updated: {contractor.name}")
