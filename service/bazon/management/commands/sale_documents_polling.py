
from django.forms import model_to_dict
from bazon.models import BazonAccount, SaleDocument, Contractor
from utils.bazon_api import Bazon
from bazon.events import (
    on_create_sale_document,
    on_update_sale_document,
)
from django.db import transaction
from django.core.management.base import BaseCommand



class Command(BaseCommand):

    def handle(self, *args, **options):
        while True:
            try:
                for bazon_account in BazonAccount.objects.all():
                    bazon_api = Bazon(
                        login=bazon_account.login,
                        password=bazon_account.password,
                        refresh_token=bazon_account.refresh_token,
                        access_token=bazon_account.access_token,
                    )
                    params = {"limit": 50}
                    response = bazon_api.get_sale_documents(params=params)
                    if response.status_code != 200:
                        bazon_account.refresh_auth()
                        return
                    
                    for amo_account in bazon_account.amo_accounts.all():
                        with transaction.atomic():
                            data = response.json()
                            for json_document in data["response"][0]["result"]["sale_documents"]:
                                try:
                                    json_document["internal_id"] = json_document.pop("id")
                                except KeyError:
                                    print(json_document)
                                    continue
                                
                                json_document["bazon_account"] = bazon_account
                                
                                sale_document, created = SaleDocument.objects.get_or_create(
                                    internal_id=json_document["internal_id"],
                                    amo_account=amo_account,
                                    defaults=json_document  # Если запись не найдена, создается с данными из json_document
                                )
                                
                                if not created:
                                    document_dict = model_to_dict(sale_document)
                                    document_dict.pop("id")
                                    document_dict.pop("bazon_account")
                                    document_dict.pop("amo_lead_id")
                                    document_dict.pop("amo_account")
                                    document_dict.pop("contractor_linked")
                                    json_document.pop("bazon_account")

                                    if document_dict != json_document:
                                        for key, value in json_document.items():
                                            if document_dict.get(key) != value:
                                                setattr(sale_document, key, value)
                                        sale_document.save()
                                        on_update_sale_document(json_document, amo_account)
                                else:
                                    on_create_sale_document(json_document, amo_account)
            except:
                pass
