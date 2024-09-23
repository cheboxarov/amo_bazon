from click.core import batch
from amo.amo_client import ContactClient
from bazon.models import Contractor, BazonAccount
from amo.models import AmoAccount
from pydantic import BaseModel, Field
from loguru import logger


class _Contractor(BaseModel):
    internal_id: int = Field(alias="id")
    email: str
    phone: str
    name: str
    type: str = Field(alias="legalType")
    balance_free: int = Field(alias="balanceFree")
    balance_reserve: int = Field(alias="balanceReserve")
    manager_comment: str = Field(alias="managerComment")
    balance: int



def on_create_contractor(contractor_data: dict, amo_account: AmoAccount, bazon_account: BazonAccount):
    if Contractor.objects.filter(internal_id=contractor_data.get("id")).exists():
        return
    contractor = Contractor.objects.create(amo_account=amo_account,
                                           **_Contractor.model_validate(contractor_data).model_dump(),
                                           bazon_account=bazon_account)
    api = ContactClient(amo_account.token, amo_account.suburl)
    custom_fields = []
    def append_value(field_id, value):
        custom_fields.append({
            "field_id": field_id,
            "values": [
                {
                    "value": value
                }
            ]
        })
    if amo_account.config.get("contact_phone_field") != 0:
        append_value(amo_account.config.get("contact_phone_field"), contractor.phone)
    if (contact_email_id := amo_account.config.get("contact_email_id")) != 0:
        append_value(contact_email_id, contractor.email)
    try:
        amo_contact = (api.create_contact(contractor.name, 0, custom_fields=custom_fields)
                       .get("_embedded",{})).get("contacts", [None])[0]
        print(amo_contact)
    except Exception as error:
        print(f"Error create contac: {error}")
        return
    if amo_contact is None:
        return
    contractor.amo_id = amo_contact.get("id")
    contractor.save()


def on_update_contractor(contractor_data: dict, amo_account: AmoAccount):
    print(f"Contractor updated: {contractor_data['name']}")
