from click.core import batch
from amo.amo_client import AmoCRMClient
from bazon.models import Contractor, BazonAccount
from amo.models import AmoAccount
from pydantic import BaseModel, Field


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





def on_update_contractor(contractor_data: dict, amo_account: AmoAccount):
    print(f"Contractor updated: {contractor_data['name']}")
