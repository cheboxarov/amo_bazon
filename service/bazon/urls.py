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
    BazonStoragesView,
    BazonManagersView,
    BazonCreateDealView,
    BazonPrintFromView,
    BazonSaleEditView,
    BazonContractorApiView,
    BazonContractorsListView,
    BazonSaleUpdate,
    BazonItemEditCost,
    BazonGetCashMachinesView, 
    BazonCreateReceiptView,
    BazonGenerateReceiptRequest,
    BazonReceiptState,
    BazonGetReceiptsView,
    BazonRefundReceiptView
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
    path("storages", BazonStoragesView.as_view()),
    path("sources", BazonSourcesView.as_view()),
    path("managers", BazonManagersView.as_view()),
    path("create-sale-document", BazonCreateDealView.as_view()),
    path("bazon-sale/<int:amo_lead_id>/print-form", BazonPrintFromView.as_view()),
    path("bazon-sale/<int:amo_lead_id>/edit", BazonSaleEditView.as_view()),
    path("bazon-sale/<int:amo_lead_id>/contractor", BazonContractorApiView.as_view()),
    path(
        "bazon-sale/<int:amo_lead_id>/contractors", BazonContractorsListView.as_view()
    ),
    path("bazon-sale/<int:amo_lead_id>/update", BazonSaleUpdate.as_view()),
    path("bazon-sale/<int:amo_lead_id>/items-edit-const", BazonItemEditCost.as_view()),
    path("bazon-sale/<int:amo_lead_id>/cash-machines", BazonGetCashMachinesView.as_view()),
    path("bazon-sale/<int:amo_lead_id>/receipt", BazonCreateReceiptView.as_view()),
    path("bazon-sale/<int:amo_lead_id>/receipt-refund", BazonRefundReceiptView.as_view()),
    path("bazon-sale/<int:amo_lead_id>/receipt-gen", BazonGenerateReceiptRequest.as_view()),
    path("bazon-sale/<int:amo_lead_id>/receipt/<int:receipt_id>", BazonReceiptState.as_view()),
    path("bazon-sale/<int:amo_lead_id>/receipts", BazonGetReceiptsView.as_view())
]
