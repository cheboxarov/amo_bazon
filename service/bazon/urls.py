from django.urls import path
from .views import (
    BazonSaleView,
    BazonSaleDetailView,
    BazonSalesListView,
    BazonItemsListView,
    BazonItemsAddView,
    BazonDeleteItemView,
    BazonDealOrdersView,
    BazonMoveSaleView,
    BazonAddSalePayView,
    BazonGetPaySourcesView,
    BazonGetPaidSourcesView,
    BazonSalePayBack,
    BazonSourcesView,
    BazonStoragesView
)

urlpatterns = [
    path("bazon-sale/<int:amo_id>", BazonSaleView.as_view()),
    path("bazon-sale/<int:amo_id>/detail", BazonSaleDetailView.as_view()),
    path("bazon-sales", BazonSalesListView.as_view()),
    path("bazon-items/<str:amo_url>", BazonItemsListView.as_view()),
    path("bazon-sale/<int:amo_lead_id>/add-item", BazonItemsAddView.as_view()),
    path("bazon-sale/<int:amo_lead_id>/delete-item", BazonDeleteItemView.as_view()),
    path("bazon-sale/<int:amo_lead_id>/orders", BazonDealOrdersView.as_view()),
    path("bazon-sale/<int:amo_lead_id>/move", BazonMoveSaleView.as_view()),
    path("bazon-sale/<int:amo_lead_id>/add-pay", BazonAddSalePayView.as_view()),
    path(
        "bazon-sale/<int:amo_lead_id>/get-pay-sources", BazonGetPaySourcesView.as_view()
    ),
    path(
        "bazon-sale/<int:amo_lead_id>/get-paid-sources",
        BazonGetPaidSourcesView.as_view(),
    ),
    path("bazon-sale/<int:amo_lead_id>/pay-back", BazonSalePayBack.as_view()),
    path("bazon-sale/<int:amo_lead_id>/storages", BazonStoragesView.as_view()),
    path("bazon-sale/<int:amo_lead_id>/sources", BazonSourcesView.as_view())
]
