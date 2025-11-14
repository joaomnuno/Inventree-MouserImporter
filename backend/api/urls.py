from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health_check, name="health"),
    path("search/mouser/", views.MouserSearchView.as_view(), name="search-mouser"),
    path("search/digikey/", views.DigiKeySearchView.as_view(), name="search-digikey"),
    path("import/", views.ImportPartView.as_view(), name="import-part"),
]
