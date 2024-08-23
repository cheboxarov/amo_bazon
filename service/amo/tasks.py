from celery import shared_task
from .models import AmoAccount, Status, Manager
from amocrm.v2 import tokens, pipelines, users


@shared_task
def sync_amo_data():
    for amo_account in AmoAccount.objects.all():
        # Подключение к amoCRM для каждого аккаунта
        tokens.default_token_manager(
            access_token=amo_account.token,  # Токен из базы данных
            subdomain=amo_account.suburl,  # URL из базы данных
            storage=tokens.FileTokensStorage()  # Выберите нужный способ хранения токенов
        )

        # Синхронизация статусов (воронки)
        pipelines_data = list(pipelines.all())  # Получение всех воронок
        existing_status_ids = Status.objects.filter(amo_account=amo_account).values_list('amo_id', flat=True)

        for pipeline in pipelines_data:
            for status_data in pipeline.statuses:
                if status_data.id in existing_status_ids:
                    # Обновление существующего статуса
                    status = Status.objects.get(amo_id=status_data.id, amo_account=amo_account)
                    status.name = status_data.name
                    status.save()
                else:
                    # Добавление нового статуса
                    Status.objects.create(
                        amo_id=status_data.id,
                        name=status_data.name,
                        amo_account=amo_account
                    )

        # Удаление статусов, которых больше нет в amoCRM
        Status.objects.filter(amo_account=amo_account).exclude(amo_id__in=[s.id for p in pipelines_data for s in p.statuses]).delete()

        # Синхронизация менеджеров
        managers_data = list(users.all())  # Получение всех менеджеров
        existing_manager_ids = Manager.objects.filter(amo_account=amo_account).values_list('amo_id', flat=True)

        for manager_data in managers_data:
            if manager_data.id in existing_manager_ids:
                # Обновление существующего менеджера
                manager = Manager.objects.get(amo_id=manager_data.id, amo_account=amo_account)
                manager.name = manager_data.name
                manager.save()
            else:
                # Добавление нового менеджера
                Manager.objects.create(
                    amo_id=manager_data.id,
                    name=manager_data.name,
                    amo_account=amo_account
                )

        # Удаление менеджеров, которых больше нет в amoCRM
        Manager.objects.filter(amo_account=amo_account).exclude(amo_id__in=[m.id for m in managers_data]).delete()