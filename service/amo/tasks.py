from celery import shared_task
from .models import AmoAccount, Status, Manager
from .amo_client import AmoCRMClient


@shared_task
def sync_amo_data():
    for amo_account in AmoAccount.objects.all():
        client = AmoCRMClient(token=amo_account.token, subdomain=amo_account.suburl)

        # Синхронизация статусов
        statuses_data = client.get_statuses()
        existing_status_ids = Status.objects.filter(
            amo_account=amo_account
        ).values_list("amo_id", flat=True)

        for pipeline in statuses_data["_embedded"]["pipelines"]:
            for status_data in pipeline["statuses"]:
                # Используем filter вместо get, чтобы избежать MultipleObjectsReturned
                status_queryset = Status.objects.filter(
                    amo_id=status_data["id"], amo_account=amo_account
                )
                if status_queryset.exists():
                    # Обновление всех найденных записей (если их несколько)
                    status_queryset.update(name=status_data["name"])
                else:
                    # Добавление нового статуса
                    Status.objects.create(
                        amo_id=status_data["id"],
                        name=status_data["name"],
                        amo_account=amo_account,
                    )

        # Удаление статусов, которых больше нет в amoCRM
        Status.objects.filter(amo_account=amo_account).exclude(
            amo_id__in=[
                s["id"]
                for p in statuses_data["_embedded"]["pipelines"]
                for s in p["statuses"]
            ]
        ).delete()

        # Синхронизация менеджеров
        managers_data = client.get_managers()
        existing_manager_ids = Manager.objects.filter(
            amo_account=amo_account
        ).values_list("amo_id", flat=True)

        for manager_data in managers_data["_embedded"]["users"]:
            # Используем filter вместо get, чтобы избежать MultipleObjectsReturned
            manager_queryset = Manager.objects.filter(
                amo_id=manager_data["id"], amo_account=amo_account
            )
            if manager_queryset.exists():
                # Обновление всех найденных записей (если их несколько)
                manager_queryset.update(name=manager_data["name"])
            else:
                # Добавление нового менеджера
                Manager.objects.create(
                    amo_id=manager_data["id"],
                    name=manager_data["name"],
                    amo_account=amo_account,
                )

        # Удаление менеджеров, которых больше нет в amoCRM
        Manager.objects.filter(amo_account=amo_account).exclude(
            amo_id__in=[m["id"] for m in managers_data["_embedded"]["users"]]
        ).delete()
