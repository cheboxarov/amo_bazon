from django.db import transaction


def transaction_decorator(func):
    def wrapper(*args, **kwargs):
        with transaction.atomic():
            return func(*args, **kwargs)

    return wrapper
