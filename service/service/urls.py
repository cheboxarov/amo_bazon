"""
URL configuration for service project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from bazon.views import (
    BazonSaleView,
    BazonSaleDetailView,
    BazonSalesListView,
    BazonItemsListView,
    BazonItemsAddView,
    BazonDeleteItemView,
    BazonDealOrdrsView,
    BazonMoveSaleView,
    BazonAddSalePayView,
    BazonGetPaySourcesView,
    BazonGetPaidSourcesView,
    BazonSalePayBack,
)
from amo.views import AmoWebhookView


urlpatterns = [
    path(
        "amo-bazon/",
        include(
            [
                path("grappelli/", include("grappelli.urls")),
                path("admin/", admin.site.urls),
                path("bazon-sale/<int:amo_id>", BazonSaleView.as_view()),
                path("bazon-sale/<int:amo_id>/detail", BazonSaleDetailView.as_view()),
                path("bazon-sales", BazonSalesListView.as_view()),
                path("amo-webhook", AmoWebhookView.as_view()),
                path("bazon-items/<str:amo_url>", BazonItemsListView.as_view()),
                path(
                    "bazon-sale/<int:amo_lead_id>/add-item", BazonItemsAddView.as_view()
                ),
                path(
                    "bazon-sale/<int:amo_lead_id>/delete-item",
                    BazonDeleteItemView.as_view(),
                ),
                path(
                    "bazon-sale/<int:amo_lead_id>/orders", BazonDealOrdersView.as_view()
                ),
                path("bazon-sale/<int:amo_lead_id>/move", BazonMoveSaleView.as_view()),
                path(
                    "bazon-sale/<int:amo_lead_id>/add-pay",
                    BazonAddSalePayView.as_view(),
                ),
                path(
                    "bazon-sale/<int:amo_lead_id>/get-pay-sources",
                    BazonGetPaySourcesView.as_view(),
                ),
                path(
                    "bazon-sale/<int:amo_lead_id>/get-paid-sources",
                    BazonGetPaidSourcesView.as_view(),
                ),
                path(
                    "bazon-sale/<int:amo_lead_id>/pay-back", BazonSalePayBack.as_view()
                ),
            ]
        ),
    )
]
