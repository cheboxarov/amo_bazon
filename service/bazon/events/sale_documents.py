from bazon.models import SaleDocument


def on_create_sale_document(sale: SaleDocument):
    print(f"новый документ {sale.internal_id}")


def on_update_sale_document(sale: SaleDocument):
    print(f"sale document updated {sale.internal_id}")
